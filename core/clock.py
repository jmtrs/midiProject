import time


class Clock:
    """
    Reloj simple para disparar pasos a resolución fija (por defecto semicorcheas).
    """

    def __init__(self, bpm: int = 174, steps_per_beat: int = 4) -> None:
        self.steps_per_beat = steps_per_beat
        self.energy = 3  # Valor por defecto para energía
        self.set_bpm(bpm)

    def set_bpm(self, bpm: int) -> None:
        bpm = int(bpm)
        if bpm < 40:
            bpm = 40
        if bpm > 260:
            bpm = 260
        self.bpm = bpm
        seconds_per_beat = 60.0 / self.bpm
        self.step_duration = seconds_per_beat / self.steps_per_beat

    def get_step_duration(self) -> float:
        return self.step_duration

    def sleep_step(self) -> None:
        time.sleep(self.step_duration)
