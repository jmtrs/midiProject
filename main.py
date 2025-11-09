import sys
import threading
import queue
import argparse
from pathlib import Path

import readchar

from core.clock import Clock
from core.config import initial_setup, SessionConfig, TrackSetup
from core.pattern import TrackPattern, TrackConfig
from core.synth import MidiSynth
from core.profiles import ProfileManager
from ui.dashboard import LiveDashboard, TrackState


KEY_QUEUE = queue.Queue()
LAST_SESSION_FILE = Path("last_session.yml")


def input_worker():
    while True:
        try:
            key = readchar.readkey()
        except Exception:
            continue
        KEY_QUEUE.put(key)
        if key == "\x1b":
            break


def get_session_config(args) -> SessionConfig:
    """Determina la configuración según argumentos CLI."""
    profile_mgr = ProfileManager()
    
    # 1. Si se pasa --profile, usar ese perfil
    if args.profile:
        print(f"Cargando perfil '{args.profile}'...")
        session = profile_mgr.load_profile(args.profile)
        if session:
            print(f"✓ Perfil '{args.profile}' cargado.\n")
            return session
        else:
            print(f"✗ Perfil '{args.profile}' no encontrado.")
            print(f"Perfiles disponibles: {', '.join(profile_mgr.list_profiles())}\n")
            sys.exit(1)
    
    # 2. Si existe last_session.yml, preguntar si cargar
    if LAST_SESSION_FILE.exists():
        print("Se encontró una sesión anterior.")
        choice = input("¿Cargar última sesión? [Enter = Sí, N = Nueva]: ").strip().lower()
        if choice != "n":
            session = profile_mgr.load_profile("../last_session")
            if session:
                print("✓ Última sesión cargada.\n")
                return session
    
    # 3. Setup interactivo
    return initial_setup()


def save_last_session(session: SessionConfig) -> None:
    """Guarda la configuración actual como última sesión."""
    profile_mgr = ProfileManager()
    profile_mgr.save_profile("../last_session", session)


def build_patterns(session: SessionConfig):
    cfgs = [
        TrackConfig(
            name=t.name,
            role=t.role,
            root=t.root,
            scale=t.scale,
            density=t.density,
            steps=t.steps,
        )
        for t in session.tracks
    ]
    patterns = [TrackPattern(cfg) for cfg in cfgs]
    states = [TrackState(cfg.name) for cfg in cfgs]
    return cfgs, patterns, states


def main():
    parser = argparse.ArgumentParser(description="Dark Maquina - Secuenciador generativo")
    parser.add_argument(
        "--profile",
        "-p",
        type=str,
        help="Cargar perfil de configuración (ej: studio_home, live_berlin)",
    )
    args = parser.parse_args()
    
    session = get_session_config(args)

    clock = Clock(bpm=session.bpm)
    dash = LiveDashboard(steps=session.steps)

    track_cfgs, track_patterns, track_states = build_patterns(session)
    synths = [MidiSynth(t.port_name) for t in session.tracks]

    selected_track = 0
    playing = True
    current_step = 0
    energy = session.energy

    t = threading.Thread(target=input_worker, daemon=True)
    t.start()

    try:
        while True:
            # Entrada de teclado
            while not KEY_QUEUE.empty():
                key = KEY_QUEUE.get()

                if key == " ":
                    playing = not playing

                elif key in ("1", "2", "3", "4", "5", "6", "7", "8"):
                    idx = int(key) - 1
                    if 0 <= idx < len(track_states):
                        selected_track = idx

                elif key.lower() == "a":
                    clock.set_bpm(clock.bpm - 2)

                elif key.lower() == "s":
                    clock.set_bpm(clock.bpm + 2)

                elif key.lower() == "z":
                    energy = max(1, energy - 1)

                elif key.lower() == "x":
                    energy = min(5, energy + 1)

                elif key.lower() == "q":
                    ts = track_states[selected_track]
                    ts.muted = not ts.muted
                    if ts.muted:
                        ts.solo = False

                elif key.lower() == "w":
                    target = track_states[selected_track]
                    if target.solo:
                        target.solo = False
                    else:
                        for i, ts in enumerate(track_states):
                            ts.solo = (i == selected_track)
                            if ts.solo:
                                ts.muted = False

                elif key.lower() == "e":
                    # Randomize solo si no está locked
                    ts = track_states[selected_track]
                    if not ts.locked:
                        p = track_patterns[selected_track]
                        p.randomize_mode()
                        p.randomize_density_soft()

                elif key.lower() == "l":
                    # Lock/unlock pista seleccionada
                    ts = track_states[selected_track]
                    ts.locked = not ts.locked

                elif key.lower() == "o":
                    # Bajar densidad
                    cfg = track_cfgs[selected_track]
                    cfg.density = max(0.0, cfg.density - 0.1)

                elif key.lower() == "p":
                    # Subir densidad
                    cfg = track_cfgs[selected_track]
                    cfg.density = min(1.0, cfg.density + 0.1)

                elif key == ",":
                    # Bajar root (transponer abajo)
                    cfg = track_cfgs[selected_track]
                    cfg.root = max(12, cfg.root - 1)

                elif key == ".":
                    # Subir root (transponer arriba)
                    cfg = track_cfgs[selected_track]
                    cfg.root = min(100, cfg.root + 1)

                elif key.lower() == "f":
                    # Solicitar fill en todas las pistas
                    for p in track_patterns:
                        p.request_fill()

                elif key == "\x1b":
                    raise KeyboardInterrupt

            # Render
            dash.draw(
                bpm=clock.bpm,
                energy=energy,
                mode="Jam",
                current_step=current_step,
                tracks=track_states,
            )

            # Generación
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
                    
                    # Ajustes de velocity y length según rol y energía
                    energy_boost = (energy - 3) * 5  # -10 a +10
                    
                    if role == "kick":
                        vel, length = 120 + energy_boost, 0.04
                    elif role == "bass":
                        vel, length = 112 + energy_boost, 0.09
                    elif role in ("hats", "perc"):
                        # Hats más presentes con alta energía
                        vel, length = 70 + (energy_boost * 2), 0.02
                    elif role in ("stab", "lead"):
                        vel, length = 90 + energy_boost, 0.11
                    elif role == "pad":
                        vel, length = 80 + energy_boost, 0.25
                    else:
                        vel, length = 90 + energy_boost, 0.08
                    
                    # Clamp velocity a rango MIDI válido
                    vel = max(1, min(127, vel))

                    note = pattern.step_note(current_step, energy)
                    if note is not None:
                        synth.schedule_note(note, velocity=vel, length=length)

                for s in synths:
                    s.process_pending()

                current_step = (current_step + 1) % session.steps
                
                # Avanzar contador de compases al completar ciclo
                if current_step == 0:
                    for p in track_patterns:
                        p.advance_bar()
                
                clock.sleep_step()
            else:
                for s in synths:
                    s.process_pending()
                clock.sleep_step()

    except KeyboardInterrupt:
        for s in synths:
            s.process_pending()
        
        # Guardar sesión al salir
        print("\nGuardando sesión...")
        save_last_session(session)
        print("✓ Sesión guardada.")
        sys.exit(0)


if __name__ == "__main__":
    main()
