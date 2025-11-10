import random
from dataclasses import dataclass
from typing import Dict, Optional

from core.config import SessionConfig


@dataclass
class SceneTrack:
    """
    Estado de una pista dentro de una escena.
    Solo guarda el estado dinámico, no la configuración base.
    """
    muted: bool = False
    solo: bool = False
    locked: bool = False
    density: Optional[float] = None  # None = usar el valor actual
    root: Optional[int] = None  # None = usar el valor actual


@dataclass
class Scene:
    """
    Una escena es un snapshot del estado dinámico de la sesión.
    No guarda roles, puertos ni estructura de pistas.
    """
    bpm: Optional[int] = None
    energy: int = 3
    tracks: list[SceneTrack] = None
    
    def __post_init__(self):
        if self.tracks is None:
            self.tracks = []


class SceneManager:
    """
    Gestiona hasta 9 escenas numeradas (1-9).
    Permite guardar y recargar escenas en tiempo de ejecución.
    """
    
    def __init__(self):
        self.scenes: Dict[int, Scene] = {}
        self.current_scene: Optional[int] = None
    
    def save_scene(self, slot: int, session: SessionConfig, clock, 
                  track_states, track_cfgs, energy: int) -> bool:
        """
        Guarda el estado actual en un slot de escena.
        """
        if not 1 <= slot <= 9:
            return False
        
        # Capturar estado global
        scene = Scene()
        scene.bpm = clock.bpm
        scene.energy = energy
        
        # Capturar estado por pista
        for track_state, track_cfg in zip(track_states, track_cfgs):
            track_scene = SceneTrack(
                muted=track_state.muted,
                solo=track_state.solo,
                locked=track_state.locked,
                density=track_cfg.density,
                root=track_cfg.root
            )
            scene.tracks.append(track_scene)
        
        self.scenes[slot] = scene
        return True
    
    def load_scene(self, slot: int, clock, track_states, track_cfgs, energy_var) -> bool:
        """
        Carga una escena y aplica el estado guardado.
        energy_var debe ser un objeto con atributo 'value' o una variable mutable.
        """
        if not 1 <= slot <= 9 or slot not in self.scenes:
            return False
        
        scene = self.scenes[slot]
        self.current_scene = slot
        
        # Aplicar estado global
        if scene.bpm is not None:
            clock.set_bpm(scene.bpm)
        
        if hasattr(energy_var, 'value'):
            energy_var.value = scene.energy  # Actualizar variable de energía si es un objeto
        
        # Intentar actualizar energía en clock si existe
        if hasattr(clock, 'energy'):
            clock.energy = scene.energy
        
        # Aplicar estado por pista
        for i, track_scene in enumerate(scene.tracks):
            if i < len(track_states) and i < len(track_cfgs):
                # Estado de pistas
                track_states[i].muted = track_scene.muted
                track_states[i].solo = track_scene.solo
                track_states[i].locked = track_scene.locked
                
                # Configuración de pistas
                if track_scene.density is not None:
                    track_cfgs[i].density = track_scene.density
                if track_scene.root is not None:
                    track_cfgs[i].root = track_scene.root
        
        return True
    
    def has_scene(self, slot: int) -> bool:
        """Verifica si existe una escena en el slot."""
        return slot in self.scenes
    
    def clear_scene(self, slot: int) -> bool:
        """Elimina una escena."""
        if slot in self.scenes:
            del self.scenes[slot]
            if self.current_scene == slot:
                self.current_scene = None
            return True
        return False
    
    def get_scene_summary(self, slot: int) -> str:
        """Devuelve un resumen simple de una escena para la UI."""
        if slot not in self.scenes:
            return "Vacío"
        
        scene = self.scenes[slot]
        parts = []
        
        if scene.bpm is not None:
            parts.append(f"BPM:{scene.bpm}")
        
        parts.append(f"E:{scene.energy}")
        
        # Contar pistas muted/solo/locked
        muted_count = sum(1 for t in scene.tracks if t.muted)
        solo_count = sum(1 for t in scene.tracks if t.solo)
        locked_count = sum(1 for t in scene.tracks if t.locked)
        
        if muted_count > 0:
            parts.append(f"M:{muted_count}")
        if solo_count > 0:
            parts.append(f"S:{solo_count}")
        if locked_count > 0:
            parts.append(f"L:{locked_count}")
        
        return " | ".join(parts)
