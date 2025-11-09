import yaml
from pathlib import Path
from typing import Optional
from dataclasses import asdict

from core.config import SessionConfig, TrackSetup


class ProfileManager:
    """
    Gestiona perfiles de configuración guardados en YAML.
    """

    def __init__(self, profiles_dir: str = "profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(exist_ok=True)

    def load_profile(self, profile_name: str) -> Optional[SessionConfig]:
        """
        Carga un perfil desde archivo YAML.
        """
        profile_path = self.profiles_dir / f"{profile_name}.yml"
        if not profile_path.exists():
            return None

        try:
            with open(profile_path, "r") as f:
                data = yaml.safe_load(f)

            tracks = [
                TrackSetup(
                    name=t["name"],
                    role=t["role"],
                    port_name=t["port_name"],
                    root=t["root"],
                    scale=t["scale"],
                    density=t["density"],
                    steps=t.get("steps", data["steps"]),
                )
                for t in data["tracks"]
            ]

            theme = data.get("theme", "custom")

            return SessionConfig(
                bpm=data["bpm"],
                steps=data["steps"],
                energy=data.get("energy", 3),
                tracks=tracks,
                theme=theme,
            )
        except Exception as e:
            print(f"Error cargando perfil '{profile_name}': {e}")
            return None

    def save_profile(self, profile_name: str, session: SessionConfig) -> bool:
        """
        Guarda una sesión como perfil.
        """
        profile_path = self.profiles_dir / f"{profile_name}.yml"
        try:
            data = {
                "bpm": session.bpm,
                "steps": session.steps,
                "energy": session.energy,
                "theme": getattr(session, "theme", "custom"),
                "tracks": [asdict(t) for t in session.tracks],
            }
            with open(profile_path, "w") as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                )
            return True
        except Exception as e:
            print(f"Error guardando perfil '{profile_name}': {e}")
            return False

    def list_profiles(self) -> list[str]:
        return [p.stem for p in self.profiles_dir.glob("*.yml")]

    def delete_profile(self, profile_name: str) -> bool:
        profile_path = self.profiles_dir / f"{profile_name}.yml"
        try:
            profile_path.unlink()
            return True
        except FileNotFoundError:
            return False
