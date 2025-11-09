from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class TrackState:
    """
    Estado visual de cada pista en la TUI.
    Lógica de control (mute/solo/lock) se maneja en main.py.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.solo: bool = False
        self.muted: bool = False
        self.locked: bool = False
        self.last_step_hit: bool = False

    @property
    def label(self) -> str:
        """
        Texto corto de estado: [LOCK,SOLO], [MUTE], [ON], etc.
        """
        flags = []
        if self.locked:
            flags.append("LOCK")
        if self.solo:
            flags.append("SOLO")
        if self.muted:
            flags.append("MUTE")
        if not flags:
            flags.append("ON")
        return "[" + ",".join(flags) + "]"


class Dashboard:
    def __init__(self, steps: int = 16) -> None:
        self.steps = steps

    def _bar(self, current_step: int) -> str:
        """
        Barra simple con el step actual marcado.
        """
        return "".join("▓" if i == current_step else "░" for i in range(self.steps))

    def render(
            self,
            bpm: int,
            energy: int,
            mode: str,
            current_step: int,
            tracks: List[TrackState],
            selected_index: int,
            selected_info: Optional[str] = None,
            last_export: Optional[str] = None,
            seed: Optional[int] = None,
    ) -> None:
        table = Table.grid(padding=(0, 1))

        header_1 = f"BPM: {bpm}"
        header_2 = f"ENERGY: {energy}"
        header_3 = f"MODE: {mode}"
        if seed is not None:
            header_3 += f" | SEED: {seed}"

        table.add_row(header_1, header_2, header_3)
        table.add_row("")

        bar = self._bar(current_step)

        for i, t in enumerate(tracks):
            prefix = ">" if i == selected_index else " "
            name = t.name.ljust(10)
            table.add_row(f"{prefix}{name} {bar}  {t.label}")

        if selected_info:
            table.add_row("")
            table.add_row(selected_info)

        panel = Panel.fit(table, title="DARK MAKINA", border_style="white")

        console.clear()
        console.print(panel)

        if last_export:
            console.print(f"Last export: {last_export}", style="dim")

        console.print(
            "[SPACE] Play/Pause  [1-8] Sel  [Q] Mute  [W] Solo  [L] Lock  "
            "[E] Rand  [A/S] BPM-/+  [Z/X] Energy-/+  "
            "[O/P] Density-/+  [,/.] Root-/+  "
            "[r] Export rápido  [R] Export avanzado  [ESC] Quit",
            style="dim",
        )


class LiveDashboard:
    def __init__(self, steps: int = 16) -> None:
        self.dashboard = Dashboard(steps=steps)

    def draw(
            self,
            bpm: int,
            energy: int,
            mode: str,
            current_step: int,
            tracks: List[TrackState],
            selected_index: int,
            selected_info: Optional[str] = None,
            last_export: Optional[str] = None,
            seed: Optional[int] = None,
    ) -> None:
        self.dashboard.render(
            bpm=bpm,
            energy=energy,
            mode=mode,
            current_step=current_step,
            tracks=tracks,
            selected_index=selected_index,
            selected_info=selected_info,
            last_export=last_export,
            seed=seed,
        )
