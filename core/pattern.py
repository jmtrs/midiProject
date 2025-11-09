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
    Generador de notas por pista basado en un rol musical.
    El rol define el comportamiento básico. La energía modula la agresividad.
    """

    def __init__(self, cfg: TrackConfig) -> None:
        self.cfg = cfg
        self.scale = DARK_SCALES.get(cfg.scale, DARK_SCALES["darktech"])

        # 'mode' se usa sobre todo en bass (base/gallop/etc).
        self.mode = "base"

        # Motivo sencillo para leads/bass gallop.
        self._motif: List[int] = [0, 3, 5, 3]
        self._motif_pos: int = 0

        # Control de compases y fills.
        self.bar_count: int = 0
        self.fill_requested: bool = False

    # Utilidades internas

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    def next_motif_interval(self) -> int:
        iv = self._motif[self._motif_pos]
        self._motif_pos = (self._motif_pos + 1) % len(self._motif)
        return iv

    # Patrones por rol

    def _kick(self, step: int, energy: int) -> Optional[int]:
        # Base 4x4 sólida
        if step % 4 == 0:
            return self.cfg.root

        # Ghosts ligeros con energía alta
        if energy >= 4 and step in (2, 6, 10, 14) and random.random() < 0.3:
            return self.cfg.root

        return None

    def _bass(self, step: int, energy: int) -> Optional[int]:
        # Patrones típicos: base o gallop
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

        # Alguna nota extra con energía media/alta
        if energy >= 3 and random.random() < 0.06:
            interval = random.choice(self.scale)
            return self.cfg.root + interval

        return None

    def _hats_perc(self, step: int, energy: int) -> Optional[int]:
        # Offbeat casi constante
        offbeat = (step % 4 == 2)
        if offbeat and random.random() < 0.9:
            return self.cfg.root

        # Relleno según densidad y energía
        if energy >= 3 and step % 2 == 1 and random.random() < self.cfg.density:
            return self.cfg.root + random.choice([0, 1])

        return None

    def _stab_lead(self, step: int, energy: int) -> Optional[int]:
        if energy < 2:
            return None

        # Golpes rítmicos
        if step in (1, 5, 9, 13) and random.random() < self.cfg.density:
            interval = self.next_motif_interval()
            return self.cfg.root + interval + random.choice([0, 12])

        # Ornamentación con energía alta
        if energy >= 4 and random.random() < 0.03:
            interval = random.choice(self.scale)
            return self.cfg.root + interval + 12

        return None

    def _pad(self, step: int, energy: int) -> Optional[int]:
        # Notas largas al inicio del ciclo
        if step == 0 and random.random() < 0.9:
            return self.cfg.root
        return None

    def _fx(self, step: int, energy: int) -> Optional[int]:
        # Eventos esporádicos
        if energy >= 3 and random.random() < 0.02:
            interval = random.choice(self.scale)
            return self.cfg.root + interval + random.choice([0, 12, 24])
        return None

    def _raw(self, step: int, energy: int) -> Optional[int]:
        # Canal libre controlado por densidad y energía
        if random.random() < self.cfg.density * (0.3 + 0.15 * energy):
            interval = random.choice(self.scale)
            return self.cfg.root + interval
        return None

    # API principal

    def step_note(self, step_index: int, energy: int) -> Optional[int]:
        """
        Devuelve la nota MIDI para este step o None si no hay evento.
        No maneja fills aquí: se podrían integrar aprovechando bar_count/fill_requested.
        """
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
        """
        Cambios suaves: en bass alterna entre base/gallop, en otros roles vuelve a base.
        """
        if self.cfg.role == "bass":
            self.mode = random.choice(["base", "gallop"])
        else:
            self.mode = "base"

    def randomize_density_soft(self) -> None:
        """
        Ajuste suave de densidad, manteniendo patrón utilizable.
        """
        jitter = random.uniform(-0.15, 0.15)
        self.cfg.density = max(0.05, min(1.0, self.cfg.density + jitter))

    def request_fill(self) -> None:
        """
        Marca que se desea un fill en el próximo compás/ciclo.
        La lógica concreta de fill se puede refinar.
        """
        self.fill_requested = True

    def advance_bar(self) -> None:
        """
        Se llama al completar un ciclo de `steps`.
        Aquí se puede aplicar lógica de fills basada en bar_count.
        """
        self.bar_count += 1

        # Placeholder: se podría usar self.fill_requested y self.bar_count
        # para disparar variaciones más agresivas en ciertos compases.
        if self.fill_requested:
            # Por ahora simplemente reseteamos la marca.
            self.fill_requested = False

    def clone_for_export(self) -> "TrackPattern":
        """
        Crea una copia del patrón para exportar a MIDI sin modificar
        el estado usado en el jam en vivo.
        """
        cfg = self.cfg
        cloned_cfg = TrackConfig(
            name=cfg.name,
            role=cfg.role,
            root=cfg.root,
            scale=cfg.scale,
            density=cfg.density,
            steps=cfg.steps,
        )

        cloned = TrackPattern(cloned_cfg)
        cloned.mode = self.mode
        cloned._motif = list(self._motif)
        cloned._motif_pos = self._motif_pos
        cloned.bar_count = self.bar_count
        cloned.fill_requested = self.fill_requested

        return cloned
