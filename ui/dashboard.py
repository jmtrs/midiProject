from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class TrackState:
    def __init__(self, name: str) -> None:
        self.name = name
        self.solo = False
        self.muted = False

    @property
    def label(self) -> str:
        if self.solo:
            return "[SOLO]"
        if self.muted:
            return "[MUTED]"
        return "[ACTIVE]"


class Dashboard:
    def __init__(self, steps: int = 16) -> None:
        self.steps = steps

    def _bar(self, current_step: int) -> str:
        return "".join("▓" if i == current_step else "░" for i in range(self.steps))

    def render(
            self,
            bpm: int,
            energy: int,
            mode: str,
            current_step: int,
            tracks: List[TrackState],
    ):
        table = Table.grid(padding=(0, 1))
        table.add_row(f"BPM: {bpm}", f"ENERGY: {energy}", f"MODE: {mode}")
        table.add_row("")
        bar = self._bar(current_step)

        for t in tracks:
            name = t.name.ljust(6)
            table.add_row(f"{name} {bar}  {t.label}")

        help1 = "[1-8] Sel pista  [Q] Mute  [W] Solo  [E] Random pista"
        help2 = "[A/S] BPM-/+  [Z/X] Energy-/+  [SPACE] Play/Pause  [ESC] Quit"

        panel = Panel.fit(table, title="DARK MAQUINA", border_style="white")

        console.clear()
        console.print(panel)
        console.print(help1)
        console.print(help2)


class LiveDashboard:
    def __init__(self, steps: int = 16) -> None:
        self.dashboard = Dashboard(steps=steps)

    def draw(self, bpm, energy, mode, current_step, tracks: List[TrackState]) -> None:
        self.dashboard.render(bpm, energy, mode, current_step, tracks)
