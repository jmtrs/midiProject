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
    - bass: patrones tipo makina/dark (base/gallop/rolling) en escala.
    - hats/perc: rejilla rítmica con micro-acentos y fills.
    - stab/lead: notas esporádicas en escala, más presentes con energía alta.
    - pad: notas largas al inicio del ciclo.
    - fx: eventos raros, más con energía alta.
    - raw: canal genérico dependiente de densidad.
    
    Sistema de compases:
    - Trabaja con bloques de 1, 2, 4, 8 compases.
    - Patrón base estable en compases 1-3.
    - Variación/fill en compas 4 según energía.
    """

    def __init__(self, cfg: TrackConfig) -> None:
        self.cfg = cfg
        self.scale = DARK_SCALES.get(cfg.scale, DARK_SCALES["darktech"])
        self.mode = "base"
        self._motif = [0, 3, 5, 3]
        self._motif_pos = 0
        self.bar_count = 0  # Contador de compases
        self.fill_requested = False  # Para fill manual

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    def next_motif_interval(self) -> int:
        iv = self._motif[self._motif_pos]
        self._motif_pos = (self._motif_pos + 1) % len(self._motif)
        return iv

    def _kick(self, step: int, energy: int, bar_num: int) -> Optional[int]:
        """Kick: casi intocable, base sólida. Muy pocos cambios automáticos."""
        # 4x4 sólido
        if step % 4 == 0:
            return self.cfg.root
        
        # Ghosts muy sutiles solo con alta energía y en compas 4
        if energy >= 4 and bar_num % 4 == 3:
            if step in (2, 6, 10, 14) and random.random() < 0.15:
                return self.cfg.root
        
        return None

    def _bass(self, step: int, energy: int, bar_num: int) -> Optional[int]:
        """Bass: corazón del groove. Modos: base, offbeat, gallop, rolling."""
        # Determinar patrón según modo
        if self.mode == "gallop":
            base_hits = [0, 3, 4, 8, 11, 12]  # Gallop rápido
        elif self.mode == "rolling":
            base_hits = [0, 2, 4, 6, 8, 10, 12, 14]  # Rolling bass line
        elif self.mode == "offbeat":
            base_hits = [2, 6, 10, 14]  # Solo offbeats
        else:
            base_hits = [0, 4, 8, 12]  # Base clásico 4x4

        if step in base_hits:
            if self.mode == "gallop":
                # Gallop usa motif para crear melodía
                interval = self.next_motif_interval()
            else:
                # Otros modos priorizan tónica
                if random.random() < 0.7:  # 70% en tónica
                    interval = 0
                else:
                    interval = random.choice(self.scale[:3])  # Solo primeros intervalos
            return self.cfg.root + interval

        # Variaciones en compas 4 con energía >= 3
        if energy >= 3 and bar_num % 4 == 3 and random.random() < 0.1:
            interval = random.choice(self.scale)
            return self.cfg.root + interval

        return None

    def _hats_perc(self, step: int, energy: int, bar_num: int) -> Optional[int]:
        """Hats/perc: patrón base con micro-acentos y fills según energía."""
        # Patrón base: offbeat seguro
        offbeat = (step % 4 == 2)
        if offbeat and random.random() < 0.95:
            return self.cfg.root
        
        # Semicorcheas según densidad y energía
        if step % 2 == 1:
            prob = self.cfg.density * (0.3 + 0.15 * energy)
            if random.random() < prob:
                # Micro-acentos: variaciones sutiles de nota
                return self.cfg.root + random.choice([0, 1, 2])
        
        # Fill en compas 4 si energía alta
        if bar_num % 4 == 3 and energy >= 3:
            if step >= 12 and random.random() < 0.7:  # Último beat lleno
                return self.cfg.root + random.choice([0, 1])
        
        return None

    def _stab_lead(self, step: int, energy: int, bar_num: int) -> Optional[int]:
        """Lead/stab: no spamear. Pocas notas bien colocadas ligadas a escala."""
        if energy < 2:
            return None
        
        # Stabs en posiciones musicales clave (downbeats y upbeats)
        if step in (0, 4, 8, 12) and random.random() < (self.cfg.density * 0.5):
            interval = self.next_motif_interval()
            return self.cfg.root + interval + random.choice([0, 12])
        
        # Runs cortos en compas 4 si energía >= 4
        if energy >= 4 and bar_num % 4 == 3:
            if step in (13, 14, 15) and random.random() < 0.4:
                interval = random.choice(self.scale)
                return self.cfg.root + interval + 12
        
        return None

    def _pad(self, step: int, energy: int, bar_num: int) -> Optional[int]:
        """Pad: eventos largos, poco frecuentes, para dar atmósfera."""
        # Pad al inicio de cada compas, menos frecuente con baja energía
        if step == 0:
            if energy >= 3 or random.random() < 0.5:
                return self.cfg.root
        
        # Pad adicional cada 4 compases en posición 8
        if bar_num % 4 == 0 and step == 8 and random.random() < 0.6:
            return self.cfg.root + random.choice(self.scale[:2])
        
        return None

    def _fx(self, step: int, energy: int, bar_num: int) -> Optional[int]:
        """FX: eventos raros para textura, más con energía alta."""
        # FX solo cada varios compases
        if bar_num % 8 == 7 and energy >= 3:
            if random.random() < 0.08:
                interval = random.choice(self.scale)
                return self.cfg.root + interval + random.choice([12, 24])
        
        return None

    def _raw(self, step: int, energy: int, bar_num: int) -> Optional[int]:
        """Raw: canal genérico dependiente de densidad."""
        if random.random() < self.cfg.density * (0.3 + 0.15 * energy):
            interval = random.choice(self.scale)
            return self.cfg.root + interval
        return None

    def step_note(self, step_index: int, energy: int) -> Optional[int]:
        """Genera nota para el paso actual considerando compases."""
        # Calcular número de compas (cada 16 pasos = 1 compas)
        bar_num = self.bar_count
        
        r = self.cfg.role

        if r == "kick":
            return self._kick(step_index, energy, bar_num)
        if r == "bass":
            return self._bass(step_index, energy, bar_num)
        if r in ("hats", "perc"):
            return self._hats_perc(step_index, energy, bar_num)
        if r in ("stab", "lead"):
            return self._stab_lead(step_index, energy, bar_num)
        if r == "pad":
            return self._pad(step_index, energy, bar_num)
        if r == "fx":
            return self._fx(step_index, energy, bar_num)
        if r == "raw":
            return self._raw(step_index, energy, bar_num)

        return None
    
    def advance_bar(self) -> None:
        """Avanza el contador de compases."""
        self.bar_count += 1

    def randomize_mode(self) -> None:
        """Randomiza el modo de la pista."""
        if self.cfg.role == "bass":
            self.mode = random.choice(["base", "gallop", "rolling", "offbeat"])
        else:
            self.mode = "base"
    
    def request_fill(self) -> None:
        """Solicita un fill en el próximo compas."""
        self.fill_requested = True

    def randomize_density_soft(self) -> None:
        jitter = random.uniform(-0.15, 0.15)
        self.cfg.density = max(0.05, min(1.0, self.cfg.density + jitter))
