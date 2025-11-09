from typing import Dict, List, Optional

Pattern = List[int]

# Pattern packs por estilo/tema.
# 1 = evento fuerte sugerido en ese step, 0 = libre.
# Se usan como base y encima se aplican variaciones existentes.

PATTERN_PACKS: Dict[str, Dict[str, Pattern]] = {
    "dark_174": {
        # 4x4 sólido
        "kick": [1 if i % 4 == 0 else 0 for i in range(16)],
        # Hats en offbeat
        "hats": [1 if i % 4 == 2 else 0 for i in range(16)],
        # Perc sutil
        "perc": [1 if i in (7, 15) else 0 for i in range(16)],
        # Bass en negras
        "bass": [1 if i in (0, 4, 8, 12) else 0 for i in range(16)],
    },
    "makina_180": {
        "kick": [1 if i % 4 == 0 else 0 for i in range(16)],
        # Hats casi constantes (1/8)
        "hats": [1 if i % 2 == 0 else 0 for i in range(16)],
        # Perc más viva
        "perc": [1 if i in (3, 7, 11, 15) else 0 for i in range(16)],
        # Bass gallop típico makina
        "bass": [1 if i in (0, 3, 4, 7, 8, 11, 12, 15) else 0 for i in range(16)],
        # Entradas rítmicas para lead
        "lead": [1 if i in (1, 5, 9, 13) else 0 for i in range(16)],
    },
    "industrial_172": {
        # Kick con extras para más mala leche
        "kick": [1 if (i % 4 == 0 or i in (7, 15)) else 0 for i in range(16)],
        # Hats marcando offbeat
        "hats": [1 if i in (2, 6, 10, 14) else 0 for i in range(16)],
        # Perc cuadrada
        "perc": [1 if i in (1, 5, 9, 13) else 0 for i in range(16)],
        # Bass muy espaciado
        "bass": [1 if i in (0, 8) else 0 for i in range(16)],
        # FX puntuales
        "fx": [1 if i in (4, 12) else 0 for i in range(16)],
    },
}


def get_pattern(style: str, role: str, steps: int) -> Optional[Pattern]:
    """
    Devuelve un patrón base (0/1) para (style, role), adaptado a `steps`.
    Si no hay pack para ese estilo/rol, devuelve None.
    """
    style_pack = PATTERN_PACKS.get(style)
    if not style_pack:
        return None

    base = style_pack.get(role)
    if not base:
        return None

    if len(base) == steps:
        return list(base)

    if len(base) == 0:
        return None

    # Repetimos o recortamos si el tamaño no coincide.
    out: Pattern = []
    for i in range(steps):
        out.append(base[i % len(base)])
    return out
