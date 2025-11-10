import sys
import threading
import queue
import argparse
import random
import time
from pathlib import Path
from time import monotonic as now

import readchar

from core.clock import Clock
from core.config import SessionConfig
from core.config import initial_setup
from core.pattern import TrackPattern, TrackConfig
from core.synth import MidiSynth
from core.profiles import ProfileManager
from core.midi_export import MidiExporter
from core.scenes import SceneManager
from ui.dashboard import LiveDashboard, TrackState

KEY_QUEUE: "queue.Queue[str]" = queue.Queue()
LAST_SESSION_FILE = Path("profiles/last_session.yml")


def input_worker() -> None:
    """
    Hilo dedicado a lectura no bloqueante de teclado.
    Envía las teclas a KEY_QUEUE.
    """
    while True:
        try:
            key = readchar.readkey()
        except Exception:
            continue

        # Detectar si se mantiene pulsada tecla Shift
        if len(key) == 1 and key.isupper():
            KEY_QUEUE.put("SHIFT+" + key.lower())
        else:
            KEY_QUEUE.put(key)

        if key == "\x1b":  # ESC
            break


def get_session_config(args) -> SessionConfig:
    """
    Determina la configuración según argumentos CLI.

    Prioridad:
    1. --profile: carga un perfil nombrado.
    2. last_session.yml: si existe, pregunta si quieres continuar.
    3. Configuración interactiva inicial.
    """
    profile_mgr = ProfileManager()

    # Perfil explícito
    if args.profile:
        print(f"Cargando perfil '{args.profile}'...")
        session = profile_mgr.load_profile(args.profile)
        if session:
            print(f"✓ Perfil '{args.profile}' cargado.\n")
            return session
        else:
            print(f"✗ Perfil '{args.profile}' no encontrado.")
            available = profile_mgr.list_profiles()
            if available:
                print(f"Perfiles disponibles: {', '.join(available)}")
            sys.exit(1)

    # Última sesión
    if LAST_SESSION_FILE.exists():
        print("Se encontró una sesión anterior.")
        choice = input("¿Cargar última sesión? [Enter = Sí, N = Nueva]: ").strip().lower()
        if choice != "n":
            session = profile_mgr.load_profile("last_session")
            if session:
                print("✓ Última sesión cargada.\n")
                return session
            else:
                print("No se pudo cargar la última sesión. Iniciando nueva.\n")

    # Setup interactivo
    return initial_setup()


def save_last_session(session: SessionConfig) -> None:
    """
    Guarda la configuración actual como última sesión.
    """
    profile_mgr = ProfileManager()
    profile_mgr.save_profile("last_session", session)


def build_patterns(session: SessionConfig):
    """
    Construye TrackConfig, TrackPattern y TrackState a partir de SessionConfig.
    Inyecta el theme como 'style' para activar pattern packs por estilo.
    """
    cfgs = []
    patterns = []
    states = []

    style = getattr(session, "theme", "custom")

    for t in session.tracks:
        cfg = TrackConfig(
            name=t.name,
            role=t.role,
            root=t.root,
            scale=t.scale,
            density=t.density,
            steps=t.steps,
            style=style,
        )
        cfgs.append(cfg)
        patterns.append(TrackPattern(cfg))
        states.append(TrackState(cfg.name))

    return cfgs, patterns, states


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dark Makina - Secuenciador generativo en terminal"
    )
    parser.add_argument(
        "--profile",
        "-p",
        type=str,
        help="Cargar perfil de configuración (ej: studio_home, live_berlin)",
    )
    args = parser.parse_args()

    # Seed opcional (visual, sin flags)
    seed_value = None
    seed_input = input("Seed (Enter = aleatorio): ").strip()
    if seed_input:
        try:
            seed_value = int(seed_input)
        except ValueError:
            # Permitir seeds de texto: las hashamos
            seed_value = abs(hash(seed_input)) % (2**31)
        random.seed(seed_value)
        print(f"Usando seed: {seed_value}\n")

    session = get_session_config(args)

    clock = Clock(bpm=session.bpm)
    dash = LiveDashboard(steps=session.steps)
    exporter = MidiExporter()  # export rápido (dir por defecto)

    # Sistema de escenas
    scene_mgr = SceneManager()

    track_cfgs, track_patterns, track_states = build_patterns(session)
    synths = [MidiSynth(t.port_name) for t in session.tracks]

    selected_track = 0
    playing = True
    current_step = 0
    energy = session.energy
    last_export: str | None = None
    scene_mode = False  # Si está True, números cargan escenas; si está False, números seleccionan pistas

    ui_update_counter = 0  # Contador para dibujar UI solo cada N iteraciones
    UI_UPDATE_INTERVAL = 4  # Actualizar UI cada 4 steps

    # Hilo para lectura de teclado
    t = threading.Thread(target=input_worker, daemon=True)
    t.start()

    try:
        while True:
            step_start_time = now()  # Marca exacta del inicio del step

            # Procesar solo UNA tecla por iteración para no bloquear el audio
            if not KEY_QUEUE.empty():
                key = KEY_QUEUE.get()

                # Play/Pause
                if key == " ":
                    playing = not playing

                # Modo de escenas - activar/desactivar
                elif key.lower() == "i":
                    scene_mode = not scene_mode
                    mode_label = "Scene" if scene_mode else "Jam"
                    print(f"\n→ Modo: {mode_label}")

                # Selección de pista (1-8) o carga de escena (1-9 si scene_mode)
                elif key in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
                    if scene_mode:
                        # Modo escenas: números cargan escenas
                        slot = int(key)
                        # Crear un wrapper simple para pasar energía
                        class _EnergyHolder:
                            pass
                        holder = _EnergyHolder()
                        holder.value = energy

                        if scene_mgr.load_scene(slot, clock, track_states, track_cfgs, holder):
                            energy = scene_mgr.scenes[slot].energy
                            print(f"✓ Escena {slot} cargada")
                        else:
                            print(f"✗ Escena {slot} no encontrada")
                    else:
                        # Modo Jam: números seleccionan pistas (1-8)
                        if key != "9":  # 9 solo en scene_mode
                            idx = int(key) - 1
                            if 0 <= idx < len(track_states):
                                selected_track = idx

                # BPM -
                elif key.lower() == "a":
                    clock.set_bpm(clock.bpm - 2)

                # BPM +
                elif key.lower() == "s":
                    clock.set_bpm(clock.bpm + 2)

                # Energy -
                elif key.lower() == "z":
                    energy = max(1, energy - 1)

                # Energy +
                elif key.lower() == "x":
                    energy = min(5, energy + 1)

                # Mute pista seleccionada
                elif key.lower() == "q":
                    ts = track_states[selected_track]
                    ts.muted = not ts.muted
                    if ts.muted:
                        ts.solo = False

                # Solo pista seleccionada
                elif key.lower() == "w":
                    target = track_states[selected_track]
                    if target.solo:
                        target.solo = False
                    else:
                        for i, ts in enumerate(track_states):
                            ts.solo = (i == selected_track)
                            if ts.solo:
                                ts.muted = False

                # Random suave pista seleccionada (si no está lock)
                elif key.lower() == "e":
                    ts = track_states[selected_track]
                    if not ts.locked:
                        p = track_patterns[selected_track]
                        p.randomize_mode()
                        p.randomize_density_soft()

                # Lock / Unlock pista seleccionada
                elif key.lower() == "l":
                    ts = track_states[selected_track]
                    ts.locked = not ts.locked

                # Densidad - pista seleccionada
                elif key.lower() == "o":
                    cfg = track_cfgs[selected_track]
                    cfg.density = max(0.0, cfg.density - 0.1)

                # Densidad + pista seleccionada
                elif key.lower() == "p":
                    cfg = track_cfgs[selected_track]
                    cfg.density = min(1.0, cfg.density + 0.1)

                # Transpose - pista seleccionada
                elif key == ",":
                    cfg = track_cfgs[selected_track]
                    cfg.root = max(12, cfg.root - 1)

                # Transpose + pista seleccionada
                elif key == ".":
                    cfg = track_cfgs[selected_track]
                    cfg.root = min(100, cfg.root + 1)

                # Fill: pedir fill
                elif key.lower() == "f":
                    for p in track_patterns:
                        p.request_fill()

                # Export rápido: todas las pistas activas, 4 compases
                elif key == "r":
                    bars = 4
                    steps_per_bar = session.steps
                    active_patterns = []
                    active_names = []
                    for cfg, pattern, ts in zip(
                            track_cfgs, track_patterns, track_states
                    ):
                        if ts.muted:
                            continue
                        cloned = pattern.clone_for_export()
                        active_patterns.append(cloned)
                        active_names.append(cfg.name)

                    if active_patterns:
                        path = exporter.render_loop(
                            patterns=active_patterns,
                            track_names=active_names,
                            bars=bars,
                            steps_per_bar=steps_per_bar,
                            bpm=clock.bpm,
                            energy=energy,
                            filename=None,
                        )
                        last_export = path

                # Guardar escena (Shift+1-9)
                elif key.startswith("SHIFT+") and key[6:] in "123456789":
                    slot = int(key[6:])
                    # Guardar el estado de energía actual
                    scene_mgr.save_scene(slot, session, clock, track_states, track_cfgs, energy)

                # ESC -> salir
                elif key == "\x1b":
                    raise KeyboardInterrupt

            # Actualizar UI solo cada N iteraciones para no bloquear audio
            ui_update_counter += 1
            if ui_update_counter >= UI_UPDATE_INTERVAL:
                ui_update_counter = 0

                # Construir línea de info de la pista seleccionada
                if 0 <= selected_track < len(track_states):
                    cfg = track_cfgs[selected_track]
                    setup = session.tracks[selected_track]
                    ts = track_states[selected_track]
                    selected_info = (
                        f"SEL: {cfg.name} | ROLE: {cfg.role} | PORT: {setup.port_name} | "
                        f"ROOT: {cfg.root} | SCALE: {cfg.scale} | DENS: {cfg.density:.2f} | "
                        f"LOCK: {'YES' if ts.locked else 'NO'}"
                    )
                else:
                    selected_info = ""

                # Render UI (operación costosa - solo cada N iteraciones)
                dash.draw(
                    bpm=clock.bpm,
                    energy=energy,
                    mode="Scene" if scene_mode else "Jam",
                    current_step=current_step,
                    tracks=track_states,
                    selected_index=selected_track,
                    selected_info=selected_info,
                    last_export=last_export,
                    seed=seed_value,
                    current_scene=scene_mgr.current_scene,
                )

            # Lógica de generación (ocurre ANTES del sleep para precisión de timing)
            if playing:
                any_solo = any(ts.solo for ts in track_states)

                for cfg, pattern, ts, synth in zip(
                        track_cfgs, track_patterns, track_states, synths
                ):
                    if any_solo and not ts.solo:
                        continue
                    if ts.muted:
                        continue

                    role = cfg.role
                    energy_boost = (energy - 3) * 5  # -10 a +10

                    if role == "kick":
                        vel, length = 120 + energy_boost, 0.04
                    elif role == "bass":
                        vel, length = 112 + energy_boost, 0.09
                    elif role in ("hats", "perc"):
                        vel, length = 70 + (energy_boost * 2), 0.02
                    elif role in ("stab", "lead"):
                        vel, length = 90 + energy_boost, 0.11
                    elif role == "pad":
                        vel, length = 80 + energy_boost, 0.25
                    else:
                        vel, length = 90 + energy_boost, 0.08

                    vel = max(1, min(127, vel))

                    note = pattern.step_note(current_step, energy)
                    if note is not None:
                        synth.schedule_note(note=note, velocity=vel, length=length)

                # Procesar note_off pendientes
                for s in synths:
                    s.process_pending()

                # Avanzar step
                current_step = (current_step + 1) % session.steps

                # Si hemos completado ciclo, avisar a patrones (para fills, etc.)
                if current_step == 0:
                    for p in track_patterns:
                        p.advance_bar()
            else:
                # Pausa: solo mantenemos limpieza de notas
                for s in synths:
                    s.process_pending()

            # Dormir el tiempo exacto que falta para el siguiente step
            # Esto hace el timing preciso sin depender de console.clear()
            elapsed = now() - step_start_time
            sleep_time = clock.get_step_duration() - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        # Apagar notas y guardar sesión
        for s in synths:
            s.process_pending()

        print("\nGuardando sesión...")
        save_last_session(session)
        print("✓ Sesión guardada.")
        sys.exit(0)


if __name__ == "__main__":
    main()
