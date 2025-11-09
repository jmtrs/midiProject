import random
from dataclasses import dataclass
from typing import Optional, List


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


class TrackPattern:
    """
    Generador con personalidad según rol:

    - kick: 4x4 sólido con posibles ghost hits.
    - bass: patrones tipo makina/dark (base/gallop) en escala.
    - hats/perc: rejilla rítmica con probabilidad ligada a energía.
    - stab/lead: notas esporádicas en escala, más presentes con energía alta.
    - pad: notas largas al inicio del ciclo.
    - fx: eventos raros, más con energía alta.
    - raw: canal genérico dependiente de densidad.
    """

    def __init__(self, cfg: TrackConfig) -> None:
        self.cfg = cfg
        self.scale = DARK_SCALES.get(cfg.scale, DARK_SCALES["darktech"])
        self.mode = "base"
        self._motif = [0, 3, 5, 3]
        self._motif_pos = 0

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    def next_motif_interval(self) -> int:
        iv = self._motif[self._motif_pos]
        self._motif_pos = (self._motif_pos + 1) % len(self._motif)
        return iv

    def _kick(self, step: int, energy: int) -> Optional[int]:
        if step % 4 == 0:
            return self.cfg.root
        if energy >= 4 and step in (2, 6, 10, 14) and random.random() < 0.3:
            return self.cfg.root
        return None

    def _bass(self, step: int, energy: int) -> Optional[int]:
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
        offbeat = (step % 4 == 2)
        if offbeat and random.random() < 0.9:
            return self.cfg.root
        if energy >= 3 and step % 2 == 1 and random.random() < self.cfg.density:
            return self.cfg.root + random.choice([0, 1])
        return None

    def _stab_lead(self, step: int, energy: int) -> Optional[int]:
        if energy < 2:
            return None
        if step in (1, 5, 9, 13) and random.random() < self.cfg.density:
            interval = self.next_motif_interval()
            return self.cfg.root + interval + random.choice([0, 12])
        if energy >= 4 and random.random() < 0.03:
            interval = random.choice(self.scale)
            return self.cfg.root + interval + 12
        return None

    def _pad(self, step: int, energy: int) -> Optional[int]:
        if step == 0 and random.random() < 0.9:
            return self.cfg.root
        return None

    def _fx(self, step: int, energy: int) -> Optional[int]:
        if energy >= 3 and random.random() < 0.02:
            interval = random.choice(self.scale)
            return self.cfg.root + interval + random.choice([0, 12, 24])
        return None

    def _raw(self, step: int, energy: int) -> Optional[int]:
        if random.random() < self.cfg.density * (0.3 + 0.15 * energy):
            interval = random.choice(self.scale)
            return self.cfg.root + interval
        return None

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
