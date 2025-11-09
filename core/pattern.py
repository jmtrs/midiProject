import random
from dataclasses import dataclass
from typing import Optional, List

from core.pattern_packs import get_pattern

DARK_SCALES = {
    "darktech": [0, 3, 5, 6, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
}


@dataclass
class TrackConfig:
    name: str
    role: str
    root: int
    scale: str
    density: float
    steps: int = 16
    # Estilo/tema global (dark_174, makina_180, industrial_172, custom...)
    style: str = "custom"


class TrackPattern:
    """
    Generador de notas por pista basado en rol + estilo.
    Si hay un pattern pack para (style, role), se usa como esqueleto y
    se le añaden variaciones según densidad y energía.
    """

    def __init__(self, cfg: TrackConfig) -> None:
        self.cfg = cfg
        self.scale = DARK_SCALES.get(cfg.scale, DARK_SCALES["darktech"])

        # Modo (bass base/gallop, etc.)
        self.mode = "base"

        # Motivo sencillo para bass/lead
        self._motif: List[int] = [0, 3, 5, 3]
        self._motif_pos: int = 0

        # Control compases/fills
        self.bar_count: int = 0
        self.fill_requested: bool = False

        # Estilo + patrón base opcional
        self.style = cfg.style
        self.base_pattern: Optional[List[int]] = get_pattern(
            self.style, self.cfg.role, self.cfg.steps
        )

    # Utilidades

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    def next_motif_interval(self) -> int:
        iv = self._motif[self._motif_pos]
        self._motif_pos = (self._motif_pos + 1) % len(self._motif)
        return iv

    # --- Patrones por rol ---

    def _kick(self, step: int, energy: int) -> Optional[int]:
        if self.base_pattern:
            if self.base_pattern[step]:
                return self.cfg.root
            # Ghosts suaves en huecos cuando hay energía
            if energy >= 4 and step % 4 in (2, 6, 10, 14) and random.random() < 0.2:
                return self.cfg.root
            return None

        # Fallback genérico
        if step % 4 == 0:
            return self.cfg.root
        if energy >= 4 and step in (2, 6, 10, 14) and random.random() < 0.3:
            return self.cfg.root
        return None

    def _bass(self, step: int, energy: int) -> Optional[int]:
        if self.base_pattern:
            if self.base_pattern[step]:
                if self.mode == "gallop":
                    interval = self.next_motif_interval()
                else:
                    interval = random.choice(self.scale)
                return self.cfg.root + interval
            # Notas extra suaves
            if energy >= 3 and random.random() < 0.04:
                interval = random.choice(self.scale)
                return self.cfg.root + interval

        # Fallback genérico
        if self.mode == "gallop":
            base_hits = [0, 3, 4, 8, 11, 12]
        else:
            base_hits = [0, 4, 8, 12]

        if step in base_hits:
            if self.mode == "gallop":
                interval = self.next_motif_interval()
            else:
                interval = random.choice(self.scale)
            return self.cfg.root + interval

        if energy >= 3 and random.random() < 0.06:
            interval = random.choice(self.scale)
            return self.cfg.root + interval

        return None

    def _hats_perc(self, step: int, energy: int) -> Optional[int]:
        if self.base_pattern:
            if self.base_pattern[step]:
                return self.cfg.root
            if energy >= 3 and random.random() < self.cfg.density * 0.4:
                return self.cfg.root
            return None

        # Fallback genérico
        offbeat = (step % 4 == 2)
        if offbeat and random.random() < 0.9:
            return self.cfg.root
        if energy >= 3 and step % 2 == 1 and random.random() < self.cfg.density:
            return self.cfg.root + random.choice([0, 1])
        return None

    def _stab_lead(self, step: int, energy: int) -> Optional[int]:
        if energy < 2:
            return None

        if self.base_pattern and self.base_pattern[step]:
            interval = self.next_motif_interval()
            return self.cfg.root + interval + random.choice([0, 12])

        if step in (1, 5, 9, 13) and random.random() < self.cfg.density:
            interval = self.next_motif_interval()
            return self.cfg.root + interval + random.choice([0, 12])

        if energy >= 4 and random.random() < 0.03:
            interval = random.choice(self.scale)
            return self.cfg.root + interval + 12

        return None

    def _pad(self, step: int, energy: int) -> Optional[int]:
        if self.base_pattern:
            # Un pad largo al inicio del ciclo si hay patrón
            if step == 0 and any(self.base_pattern):
                return self.cfg.root
            return None

        if step == 0 and random.random() < 0.9:
            return self.cfg.root
        return None

    def _fx(self, step: int, energy: int) -> Optional[int]:
        if self.base_pattern and self.base_pattern[step]:
            interval = random.choice(self.scale)
            return self.cfg.root + interval + random.choice([0, 12, 24])

        if energy >= 3 and random.random() < 0.02:
            interval = random.choice(self.scale)
            return self.cfg.root + interval + random.choice([0, 12, 24])
        return None

    def _raw(self, step: int, energy: int) -> Optional[int]:
        if self.base_pattern and self.base_pattern[step]:
            interval = random.choice(self.scale)
            return self.cfg.root + interval

        if random.random() < self.cfg.density * (0.3 + 0.15 * energy):
            interval = random.choice(self.scale)
            return self.cfg.root + interval
        return None

    # --- API principal ---

    def step_note(self, step_index: int, energy: int) -> Optional[int]:
        r = self.cfg.role

        if r == "kick":
            return self._kick(step_index, energy)
        if r == "bass":
            return self._bass(step_index, energy)
        if r in ("hats", "perc"):
            return self._hats_perc(step_index, energy)
        if r in ("stab", "lead"):
            return self._stab_lead(step_index, energy)
        if r == "pad":
            return self._pad(step_index, energy)
        if r == "fx":
            return self._fx(step_index, energy)
        if r == "raw":
            return self._raw(step_index, energy)

        return None

    def randomize_mode(self) -> None:
        if self.cfg.role == "bass":
            self.mode = random.choice(["base", "gallop"])
        else:
            self.mode = "base"

    def randomize_density_soft(self) -> None:
        jitter = random.uniform(-0.15, 0.15)
        self.cfg.density = max(0.05, min(1.0, self.cfg.density + jitter))

    def request_fill(self) -> None:
        self.fill_requested = True

    def advance_bar(self) -> None:
        self.bar_count += 1
        if self.fill_requested:
            # Aquí se puede meter lógica de fill más adelante.
            self.fill_requested = False

    def clone_for_export(self) -> "TrackPattern":
        cfg = self.cfg
        cloned_cfg = TrackConfig(
            name=cfg.name,
            role=cfg.role,
            root=cfg.root,
            scale=cfg.scale,
            density=cfg.density,
            steps=cfg.steps,
            style=cfg.style,
        )
        cloned = TrackPattern(cloned_cfg)
        cloned.mode = self.mode
        cloned._motif = list(self._motif)
        cloned._motif_pos = self._motif_pos
        cloned.bar_count = self.bar_count
        cloned.fill_requested = self.fill_requested
        return cloned
