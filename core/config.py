import mido
from dataclasses import dataclass
from typing import List, Dict

# Roles disponibles. El rol define el comportamiento rítmico/melódico.
ROLES = ["kick", "bass", "hats", "perc", "stab", "lead", "pad", "fx", "raw"]

# Plantillas opcionales (no obligan, solo inicializan valores).
THEMES: Dict[str, Dict] = {
    "dark_174": {
        "label": "Dark 174",
        "bpm": 174,
        "steps": 16,
        "energy": 3,
    },
    "makina_180": {
        "label": "Makina 180",
        "bpm": 180,
        "steps": 16,
        "energy": 4,
    },
    "industrial_172": {
        "label": "Industrial 172",
        "bpm": 172,
        "steps": 16,
        "energy": 4,
    },
}


@dataclass
class TrackSetup:
    name: str
    role: str
    port_name: str
    root: int
    scale: str
    density: float
    steps: int


@dataclass
class SessionConfig:
    bpm: int
    steps: int
    energy: int
    tracks: List[TrackSetup]


def _ask_int(prompt: str, default: int, min_v: int, max_v: int) -> int:
    raw = input(f"{prompt} [{default}]: ").strip()
    if not raw:
        return default
    try:
        v = int(raw)
    except ValueError:
        return default
    return max(min_v, min(max_v, v))


def _ask_choice(prompt: str, options: List[str], default_idx: int = 0) -> str:
    for i, o in enumerate(options, start=1):
        print(f"  {i}. {o}")
    raw = input(f"{prompt} [{default_idx + 1}]: ").strip()
    if not raw:
        return options[default_idx]
    try:
        i = int(raw) - 1
        if 0 <= i < len(options):
            return options[i]
    except ValueError:
        pass
    return options[default_idx]


def _list_ports() -> List[str]:
    return mido.get_output_names()


def _propose_quick_setup(ports: List[str]) -> SessionConfig:
    """Propone una configuración rápida y razonable."""
    print("\n=== Configuración rápida ===")
    print("\nConfiguración propuesta:")
    print(f"  BPM: 174  |  Energy: 3  |  Pasos: 16\n")
    
    default_port = ports[0] if ports else "IAC Driver Bus 1"
    
    configs = [
        ("KICK", "kick", 36, "darktech", 1.0),
        ("BASS", "bass", 42, "darktech", 0.8),
        ("HATS", "hats", 70, "darktech", 0.6),
        ("LEAD", "lead", 60, "phrygian", 0.3),
    ]
    
    for name, role, root, scale, density in configs:
        print(f"  Pista {name:6} → [{default_port}] ({role}, root {root})")
    
    print("\n¿Aceptar esta configuración?")
    accept = input("[Enter = Sí, N = Editar paso a paso]: ").strip().lower()
    
    if accept != "n":
        tracks = [
            TrackSetup(
                name=name,
                role=role,
                port_name=default_port,
                root=root,
                scale=scale,
                density=density,
                steps=16,
            )
            for name, role, root, scale, density in configs
        ]
        return SessionConfig(bpm=174, steps=16, energy=3, tracks=tracks)
    
    return None


def initial_setup() -> SessionConfig:
    print("=== DARK MAQUINA - Configuración inicial ===")
    
    # Puertos MIDI
    ports = _list_ports()
    if not ports:
        raise SystemExit("No hay puertos MIDI de salida disponibles.")

    print("\nPuertos MIDI detectados:")
    for i, p in enumerate(ports, start=1):
        print(f"  {i}. {p}")
    
    # Intentar configuración rápida
    quick = _propose_quick_setup(ports)
    if quick:
        return quick
    
    # Si rechazan quick setup, modo manual completo
    print("\n=== Configuración manual ===")

    # Elegir tema base
    theme_keys = list(THEMES.keys()) + ["custom"]
    print("\nTemas disponibles:")
    for i, k in enumerate(theme_keys, start=1):
        if k == "custom":
            print(f"  {i}. Custom (configuración manual)")
        else:
            t = THEMES[k]
            print(f"  {i}. {t['label']} ({k}) - {t['bpm']} BPM")

    choice = input("> ").strip()
    try:
        idx = int(choice) - 1
    except ValueError:
        idx = 0
    if idx < 0 or idx >= len(theme_keys):
        idx = 0

    theme_key = theme_keys[idx]

    if theme_key == "custom":
        bpm = _ask_int("BPM inicial", 174, 40, 260)
        steps = _ask_int("Pasos por ciclo (16/32)", 16, 4, 64)
        energy = _ask_int("Energía inicial (1-5)", 3, 1, 5)
    else:
        t = THEMES[theme_key]
        bpm = t["bpm"]
        steps = t.get("steps", 16)
        energy = t.get("energy", 3)
        print(f"Usando plantilla {t['label']} - BPM {bpm}, pasos {steps}, energía {energy}")

    # Número de pistas
    num_tracks = _ask_int("\nNúmero de pistas (1-8)", 4, 1, 8)

    tracks: List[TrackSetup] = []

    for i in range(num_tracks):
        print(f"\nConfigurar pista {i + 1}:")

        # Nombre sugerido
        sugeridos = ["KICK", "BASS", "HATS", "LEAD"]
        name_default = sugeridos[i] if i < len(sugeridos) else f"TRK{i + 1}"
        name = input(f"Nombre pista [{name_default}]: ").strip().upper() or name_default

        # Rol musical
        print("Rol disponible:")
        role = _ask_choice("Selecciona rol", ROLES, default_idx=min(i, len(ROLES) - 1))

        # Puerto MIDI
        print("Selecciona puerto para esta pista:")
        port = _ask_choice("Puerto MIDI de salida", ports, default_idx=0)

        # Defaults según rol
        if role == "kick":
            root_default = 36
            scale_default = "darktech"
            density_default = 1.0
        elif role == "bass":
            root_default = 42
            scale_default = "darktech"
            density_default = 0.8
        elif role in ("hats", "perc"):
            root_default = 70
            scale_default = "darktech"
            density_default = 0.6
        elif role in ("stab", "lead"):
            root_default = 60
            scale_default = "phrygian"
            density_default = 0.3
        else:
            root_default = 48
            scale_default = "darktech"
            density_default = 0.4

        root = _ask_int("Nota raíz MIDI", root_default, 12, 100)
        scale = input(f"Escala [{scale_default}]: ").strip().lower() or scale_default

        dens_raw = input(f"Densidad 0.0-1.0 [{density_default}]: ").strip()
        if dens_raw:
            try:
                density = float(dens_raw)
            except ValueError:
                density = density_default
            density = max(0.0, min(1.0, density))
        else:
            density = density_default

        tracks.append(
            TrackSetup(
                name=name,
                role=role,
                port_name=port,
                root=root,
                scale=scale,
                density=density,
                steps=steps,
            )
        )

    print("\nConfiguración completada.\n")
    return SessionConfig(bpm=bpm, steps=steps, energy=energy, tracks=tracks)
