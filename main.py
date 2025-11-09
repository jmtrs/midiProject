import sys
import threading
import queue
import argparse
import random
from pathlib import Path

import readchar

from core.clock import Clock
from core.config import SessionConfig
from core.config import initial_setup
from core.pattern import TrackPattern, TrackConfig
from core.synth import MidiSynth
from core.profiles import ProfileManager
from core.midi_export import MidiExporter
from ui.dashboard import LiveDashboard, TrackState

KEY_QUEUE: "queue.Queue[str]" = queue.Queue()
LAST_SESSION_FILE = Path("last_session.yml")


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
    """
    cfgs = []
    patterns = []
    states = []

    for t in session.tracks:
        cfg = TrackConfig(
            name=t.name,
            role=t.role,
            root=t.root,
            scale=t.scale,
            density=t.density,
            steps=t.steps,
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

    track_cfgs, track_patterns, track_states = build_patterns(session)
    synths = [MidiSynth(t.port_name) for t in session.tracks]

    selected_track = 0
    playing = True
    current_step = 0
    energy = session.energy
    last_export: str | None = None

    # Hilo para lectura de teclado
    t = threading.Thread(target=input_worker, daemon=True)
    t.start()

    try:
        while True:
            # Procesar teclas pendientes
            while not KEY_QUEUE.empty():
                key = KEY_QUEUE.get()

                # Play/Pause
                if key == " ":
                    playing = not playing

                # Selección de pista (1-8)
                elif key in ("1", "2", "3", "4", "5", "6", "7", "8"):
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

                # Fill: pedir fill (placeholder, depende de tu implementación interna)
                elif key.lower() == "f":
                    for p in track_patterns:
                        p.request_fill()

                # Export rápido: todas las pistas activas, 4 compases, dir por defecto
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

                    if not active_patterns:
                        print("\n[Export] No hay pistas activas para exportar.")
                    else:
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
                        print(
                            f"\n[Export] Loop ({bars}x{steps_per_bar}) exportado en: {path}"
                        )

                # Export avanzado (visual, sin flags)
                elif key == "R":
                    print("\n[Export avanzado]")
                    print("1) Todas pistas activas")
                    print("2) Solo pista seleccionada")
                    print("3) Solo drums (kick/hats/perc)")
                    mode_choice = input("Modo [1]: ").strip() or "1"

                    bars_input = input("Compases [4]: ").strip()
                    try:
                        bars = int(bars_input) if bars_input else 4
                    except ValueError:
                        bars = 4
                    if bars < 1:
                        bars = 1

                    dir_input = input("Directorio [out]: ").strip()
                    export_dir = dir_input if dir_input else "out"

                    steps_per_bar = session.steps
                    patterns_to_export = []
                    names_to_export = []

                    for idx, (cfg, pattern, ts) in enumerate(
                            zip(track_cfgs, track_patterns, track_states)
                    ):
                        if ts.muted:
                            continue

                        if mode_choice == "2" and idx != selected_track:
                            continue

                        if (
                                mode_choice == "3"
                                and cfg.role not in ("kick", "hats", "perc")
                        ):
                            continue

                        cloned = pattern.clone_for_export()
                        patterns_to_export.append(cloned)
                        names_to_export.append(cfg.name)

                    if not patterns_to_export:
                        print("\n[Export] Nada que exportar con estos filtros.")
                    else:
                        adv_exporter = MidiExporter(output_dir=export_dir)
                        path = adv_exporter.render_loop(
                            patterns=patterns_to_export,
                            track_names=names_to_export,
                            bars=bars,
                            steps_per_bar=steps_per_bar,
                            bpm=clock.bpm,
                            energy=energy,
                            filename=None,
                        )
                        last_export = path
                        print(
                            f"\n[Export] Loop avanzado ({bars}x{steps_per_bar}) exportado en: {path}"
                        )

                # ESC -> salir
                elif key == "\x1b":
                    raise KeyboardInterrupt

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

            # Render UI
            dash.draw(
                bpm=clock.bpm,
                energy=energy,
                mode="Jam",
                current_step=current_step,
                tracks=track_states,
                selected_index=selected_track,
                selected_info=selected_info,
                last_export=last_export,
                seed=seed_value,
            )

            # Lógica de generación
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

                clock.sleep_step()
            else:
                # Pausa: solo mantenemos limpieza de notas
                for s in synths:
                    s.process_pending()
                clock.sleep_step()

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
