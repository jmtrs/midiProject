import sys
import threading
import queue

import readchar

from core.clock import Clock
from core.config import initial_setup, SessionConfig, TrackSetup
from core.pattern import TrackPattern, TrackConfig
from core.synth import MidiSynth
from ui.dashboard import LiveDashboard, TrackState


KEY_QUEUE = queue.Queue()


def input_worker():
    while True:
        try:
            key = readchar.readkey()
        except Exception:
            continue
        KEY_QUEUE.put(key)
        if key == "\x1b":
            break


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
    session = initial_setup()

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
                    p = track_patterns[selected_track]
                    p.randomize_mode()
                    p.randomize_density_soft()

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
                    if role == "kick":
                        vel, length = 120, 0.04
                    elif role == "bass":
                        vel, length = 112, 0.09
                    elif role in ("hats", "perc"):
                        vel, length = 70, 0.02
                    elif role in ("stab", "lead"):
                        vel, length = 90, 0.11
                    elif role == "pad":
                        vel, length = 80, 0.25
                    else:
                        vel, length = 90, 0.08

                    note = pattern.step_note(current_step, energy)
                    if note is not None:
                        synth.schedule_note(note, velocity=vel, length=length)

                for s in synths:
                    s.process_pending()

                current_step = (current_step + 1) % session.steps
                clock.sleep_step()
            else:
                for s in synths:
                    s.process_pending()
                clock.sleep_step()

    except KeyboardInterrupt:
        for s in synths:
            s.process_pending()
        sys.exit(0)


if __name__ == "__main__":
    main()
