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
- Salida MIDI real:
    - `mido` + `python-rtmidi`.
    - Enrutamiento a cualquier DAW/sinte vía puertos virtuales.

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
