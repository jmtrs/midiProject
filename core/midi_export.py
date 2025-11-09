import mido
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from core.pattern import TrackPattern


class MidiExporter:
    """
    Exporta loops generados a archivos MIDI.
    Se usa para capturar el estado musical actual (patrones) a un .mid
    que luego puedes arrastrar al DAW.
    """

    def __init__(self, output_dir: str = "out") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def render_loop(
            self,
            patterns: List[TrackPattern],
            track_names: List[str],
            bars: int,
            steps_per_bar: int,
            bpm: int,
            energy: int,
            filename: Optional[str] = None,
    ) -> str:
        """
        Renderiza N compases de los patrones actuales a un archivo MIDI.

        patterns:
            Lista de TrackPattern (normalmente clones para no tocar el jam en vivo).
        track_names:
            Nombres de las pistas (misma longitud que patterns).
        bars:
            Número de compases/ciclos a renderizar.
        steps_per_bar:
            Pasos por compás/ciclo. En tu motor actual equivale a session.steps.
        bpm:
            BPM para metadatos del MIDI.
        energy:
            Nivel de energía que se usará al llamar a step_note.
        filename:
            Nombre base opcional (sin extensión). Si None, se genera con timestamp.

        Devuelve:
            Ruta absoluta del archivo MIDI creado (str).
        """
        if not patterns or not track_names or len(patterns) != len(track_names):
            raise ValueError("patterns y track_names deben tener la misma longitud y no estar vacíos.")

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"loop_{timestamp}"

        mid = mido.MidiFile(ticks_per_beat=480)
        tempo = mido.bpm2tempo(bpm)

        total_steps = bars * steps_per_bar
        # Usamos semicorcheas como unidad base (4 por negra -> 16 por compás clásico)
        # En tu engine, steps_per_bar ya representa el ciclo completo; aquí se respeta.
        ticks_per_step = mid.ticks_per_beat // 4

        for pattern, name in zip(patterns, track_names):
            track = mido.MidiTrack()
            mid.tracks.append(track)

            # Nombre de pista y tempo
            track.append(mido.MetaMessage("track_name", name=name, time=0))
            track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))

            note_events = []  # (time_ticks, note, velocity, is_on)

            # Reinicio de estado de compases para export (opcional; se asume ya viene preparado)
            # pattern.bar_count se usa tal cual venga del clon.

            for step in range(total_steps):
                local_step = step % steps_per_bar
                note = pattern.step_note(local_step, energy)

                if note is not None:
                    start_time = step * ticks_per_step
                    duration = ticks_per_step

                    role = pattern.cfg.role
                    if role == "kick":
                        vel = 120
                    elif role == "bass":
                        vel = 112
                    elif role in ("hats", "perc"):
                        vel = 70
                    elif role in ("stab", "lead"):
                        vel = 90
                    elif role == "pad":
                        vel = 80
                        duration = ticks_per_step * 4
                    else:
                        vel = 90

                    note_events.append((start_time, note, vel, True))
                    note_events.append((start_time + duration, note, 0, False))

                # Cuando termina un "bar" lógico, avanzamos contador interno del patrón
                if (step + 1) % steps_per_bar == 0:
                    pattern.advance_bar()

            # Ordenar eventos: primero por tiempo, y en el mismo tiempo primero note_off luego note_on
            note_events.sort(key=lambda x: (x[0], not x[3]))

            current_time = 0
            for event_time, note, vel, is_on in note_events:
                delta = event_time - current_time
                msg_type = "note_on" if is_on else "note_off"
                track.append(mido.Message(msg_type, note=note, velocity=vel, time=delta))
                current_time = event_time

            track.append(mido.MetaMessage("end_of_track", time=0))

        filepath = (self.output_dir / f"{filename}.mid").resolve()
        mid.save(filepath)
        return str(filepath)
