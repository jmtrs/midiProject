import mido
import time
from typing import List
from collections import deque


class MidiSynth:
    """
    Envoltorio para enviar notas a un puerto MIDI concreto.
    """

    def __init__(self, port_name: str) -> None:
        ports: List[str] = mido.get_output_names()
        if port_name not in ports:
            raise SystemExit(
                f"Puerto MIDI '{port_name}' no disponible.\n"
                f"Puertos detectados: {ports}"
            )
        self.port_name = port_name
        self.port = mido.open_output(port_name)
        self.pending = deque()

    def schedule_note(self, note: int, velocity: int, length: float) -> None:
        if note < 0 or note > 127:
            return
        self.port.send(mido.Message("note_on", note=note, velocity=velocity))
        off_time = time.monotonic() + max(0.01, length)
        self.pending.append((off_time, note))

    def process_pending(self) -> None:
        now = time.monotonic()
        while self.pending and self.pending[0][0] <= now:
            _, note = self.pending.popleft()
            self.port.send(mido.Message("note_off", note=note, velocity=0))
