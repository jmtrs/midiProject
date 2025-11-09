# Dark Maquina v0.1 (POC)

Pequeño secuenciador generativo en terminal orientado a hard/dark techno y makina,
pensado para integrarse con un DAW (Ardour) y sintes como Surge XT a través de
puertos MIDI virtuales (IAC en macOS).

Este POC no pretende ser un producto final, sino una prueba seria de concepto:
¿es útil, inspira, se siente como una máquina con groove o solo como un script más?

## Características (v0.1)

- Interfaz TUI en terminal con aspecto de groovebox.
- 4 pistas lógicas:
    - KICK: patrón 4x4 sólido.
    - BASS: línea en escala oscura (dark/phrygian-like).
    - HATS: patrones con probabilidad.
    - LEAD: eventos ocasionales para textura.
- Control en tiempo real:
    - Barra de pasos animada.
    - Play / Pause.
    - Ajuste de BPM.
    - Mute / Solo / Randomize sencillos.
- Salida MIDI real usando `mido` + `python-rtmidi`.
- Pensado para usarse con:
    - macOS
    - IAC Driver
    - Ardour con Surge XT (u otro sinte) escuchando el puerto.

## Lo que NO hace (a propósito)

Para mantener el POC limpio, quedan fuera:

- Cambio de presets del sinte.
- Automatización avanzada de CC.
- Integración por OSC con Ardour.
- Multipuerto fino por pista.
- Guardado/carga de escenas o proyectos.
- Cualquier dependencia de "IA pesada".

Si esto demuestra utilidad (fluye, suena, inspira), esos puntos son candidatos para una v0.2+.

## Requisitos

- Python 3.9+ recomendado.
- macOS con IAC Driver activado.
- `pip install -r requirements.txt`
- DAW (ej. Ardour) con:
    - Una pista de instrumento (Surge XT, Monique, Tyrell, etc.).
    - Esa pista conectada a un puerto IAC que contenga el texto `Surge`
      o el nombre que configures.

## Configuración rápida (entorno típico con Ardour + Surge XT)

1. Activa IAC Driver en macOS (Configuración Audio MIDI).
2. Crea un puerto, por ejemplo: `Driver IAC PythonToSurge`.
3. En Ardour:
    - Crea pista MIDI con Surge XT como instrumento.
    - Conecta `Driver IAC PythonToSurge` a la entrada MIDI de esa pista.
    - Asegúrate de que la salida de la pista va al Master y suena.
4. En Surge XT, selecciona un preset adecuado para bajo/lead/bombo sintético.

## Uso

Desde la carpeta `darkmaquina_poc`:

```bash
pip install -r requirements.txt
python main.py
