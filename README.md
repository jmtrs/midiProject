# Dark Makina (POC)

Secuenciador generativo en terminal orientado a hard/dark techno, makina e industrial.
Pensado para integrarse con un DAW (Ardour, etc.) y sintetizadores (Surge XT, Monique,
Tyrell, etc.) mediante puertos MIDI virtuales.

No es un plugin gráfico ni un juguete aleatorio: es una máquina de patrones
para sacar grooves rápidos, probar ideas y exportarlas a MIDI.

## Características actuales

- Interfaz TUI tipo groovebox:
    - Barra de pasos animada.
    - Estado por pista: ACTIVE / MUTE / SOLO / LOCK.
- Configuración flexible:
    - Elección de “tema” base (`dark_174`, `makina_180`, `industrial_172`, `custom`).
    - Múltiples pistas definidas por el usuario (1–8).
    - Roles por pista:
        - `kick`, `bass`, `hats`, `perc`, `stab`, `lead`, `pad`, `fx`, `raw`.
    - Asignación de puerto MIDI por pista.
    - Nota raíz, escala y densidad configurables.
- Perfiles:
    - Carga de perfiles con `--profile`.
    - Guardado automático de la última sesión como `last_session`.
- Lógica musical por rol:
    - `kick`: 4x4 sólido con pequeños ghosts según energía.
    - `bass`: patrones base/gallop sobre escalas oscuras.
    - `hats` / `perc`: offbeats y subdivisiones en función de densidad/energía.
    - `stab` / `lead`: eventos puntuales, más presentes con energía alta.
    - `pad` / `fx`: capas esporádicas.
    - `raw`: canal libre gobernado por densidad.
- Control en tiempo real:
    - Play / Pause.
    - BPM +/-.
    - Energía +/-.
    - Mute / Solo por pista.
    - Random suave por pista (si no está lock).
    - Lock/Unlock por pista.
    - Densidad +/- por pista.
    - Transpose +/- por pista.
    - Trigger de fills (marcador interno).
    - **Scenes (novedad)**: Guarda y carga snapshots de estado (mute/solo/lock/densidad/root/energy/BPM).
- Salida MIDI real:
    - `mido` + `python-rtmidi`.
    - Enrutamiento a cualquier DAW/sinte vía puertos virtuales.

## Sistema de Scenes (novedad)

Las **Scenes** permiten guardar y recuperar snapshots completos del estado actual sin cambiar puertos ni roles. Es perfecto para transiciones en directo o para comparar variaciones rápidamente.

### ¿Qué guarda una Scene?

- **Global**:
  - BPM actual (opcional)
  - Nivel de energía (1-5)
- **Por pista**:
  - Estado de mute/solo/lock
  - Densidad (override temporal)
  - Nota raíz (para cambios de tonalidad por escena)

### ¿Qué NO guarda una Scene?

- Puertos MIDI
- Roles de las pistas
- Número o estructura de pistas

### Uso en tiempo real

- **Guardar Scene**: Mayúscula + número (SHIFT+1 a SHIFT+9)
- **Cargar Scene**: Tecla de número (1 a 9)
- La escena activa se muestra en la UI: `MODE: Jam | SCENE: 3`

### Flujo de trabajo típico

1. **Configuración base**: Define tus pistas, puertos y roles desde perfil
2. **Escena 1 (intro)**: Configura un estado minimalista (solo kick y bass), pulsa SHIFT+1
3. **Escena 2 (main groove)**: Añade más pistas, ajusta energía, pulsa SHIFT+2
4. **Escena 3 (break)**: Mutea algunas pistas, cambia densidad, pulsa SHIFT+3
5. **En directo**: Cambia entre escenas con las teclas 1, 2, 3 según necesites

Las scenes viven solo en memoria durante la sesión. Para guardarlas permanentemente, guarda el perfil completo.

## Atajos de teclado

### Control principal
- `[ESPACIO]` - Play/Pause
- `1-8` - Seleccionar pista
- `Q` - Mutea pista seleccionada
- `W` - Solo pista seleccionada
- `L` - Lock/Unlock pista seleccionada
- `E` - Random suave (si no está lockeada)
- `ESC` - Salir y guardar sesión

### Parámetros globales
- `A/S` - BPM -/+
- `Z/X` - Energía -/+

### Parámetros por pista
- `O/P` - Densidad -/+
- `,/.` - Transpose -/+
- `F` - Trigger fill

### Systema de scenes
- `SHIFT+1-9` - Guardar escena actual en slot 1-9
- `1-9` - Cargar escena desde slot 1-9

### Export MIDI
- `r` - Export rápido (todas las pistas activas, 4 compases)
- `R` - Export avanzado (con menú de opciones)

## Exportar loops a MIDI

Puedes congelar lo que está sonando:

- Pulsa `R` durante el jam.
- Se exportan 4 ciclos completos (`bars=4`) de todas las pistas **no muteadas**.
- Cada pista activa se escribe como pista independiente en un `.mid`.
- Los archivos se guardan en `out/loop_YYYYMMDD_HHMMSS.mid`.

Uso típico:

1. Configuras roles y puertos según tu setup.
2. Jameas hasta que salga algo con groove.
3. Bloqueas las pistas que te gusten (LOCK).
4. Pulsas `R`.
5. Arrastras el `.mid` a tu DAW y sigues trabajando ahí.

## Requisitos

- Python 3.9+ recomendado.
- `pip install -r requirements.txt`
- Sistema con puertos MIDI:
    - macOS: IAC Driver activado.
    - Linux/Windows: loopMIDI / ALSA / similar.
- DAW con:
    - Pistas MIDI escuchando los puertos configurados.
    - Sintetizadores cargados en esas pistas.

## Uso rápido

```bash
pip install -r requirements.txt
python main.py
