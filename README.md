# Traductor de voz local para Teams (prueba)

Hablas español al micrófono físico. Gemini Live Translate devuelve audio en inglés, que la app reproduce en un cable de audio virtual. Teams usa el otro extremo del cable como micrófono. Esta versión **usa la traducción y voz de Gemini**; no integra Whisper ni ElevenLabs todavía.

## Preparación en Windows

1. Instala Python 3.11 o posterior y [VB-CABLE](https://vb-audio.com/Cable/) (reinicia si el instalador lo pide).
2. En PowerShell, desde esta carpeta:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   $env:GEMINI_API_KEY = "TU_API_KEY"
   python translator.py --list-devices
   ```

3. Identifica el número de tu micrófono físico (entrada) y **CABLE Input** (salida/reproducción). Los nombres pueden incluir `VB-Audio Virtual Cable`. No elijas **CABLE Output** como entrada de esta aplicación: haría un bucle.
4. Ejecuta, sustituyendo los números:

   ```powershell
   python translator.py --input 1 --output 5
   ```

   En este equipo (comprobado el 24/09/2026), funcionan `--input 14` para el
   micrófono BlackShark V3 X y `--output 21` para CABLE Input. Son los
   dispositivos Windows DirectSound. Los índices pueden cambiar tras reiniciar
   o conectar otros equipos; vuelve a ejecutar `--list-devices` antes de usarlos.

   La prueba real en Teams del 24/09/2026 funcionó con esta configuración.
   Teams usó CABLE Output como micrófono y los audífonos BlackShark V3 X como
   altavoz.

5. En Teams → Configuración → Dispositivos → Micrófono, selecciona **CABLE Output** (grabación). Mantén tus audífonos como altavoz de Teams. Haz una llamada de prueba y habla en español. Para finalizar, pulsa `Ctrl+C` en PowerShell.

## Comprobación y límites

- La entrada a Gemini es PCM mono de 16 kHz en bloques de 100 ms; la salida es PCM mono de 24 kHz. El programa verifica que Windows admita ambas frecuencias en los dispositivos escogidos.
- La app muestra transcripción de entrada y de salida para detectar errores. Las transcripciones pueden llegar en fragmentos y no son un historial consolidado.
- La salida **no se reproduce en tus audífonos**: va al cable virtual. Para escucharla, puedes activar temporalmente “Escuchar este dispositivo” en las propiedades de grabación de CABLE Output en Windows; esto puede añadir demora. En Teams, usa una llamada de prueba para comprobar lo que reciben los demás.
- El idioma de salida está fijado en inglés; si hablas inglés, el modelo queda en silencio (`echo_target_language=False`).
- Usa audífonos para el audio de Teams. Evita que la voz inglesa o los demás participantes se filtren al micrófono físico.
- Esta app no graba audio ni incluye API keys en el paquete. La API de Gemini necesita internet, acceso al modelo y puede generar costes. El modelo es *preview*.
- Si el hardware no acepta 16 kHz/24 kHz directamente, configura un dispositivo que acepte esas tasas o añade remuestreo en una siguiente versión.

Documentación: [traducción Gemini Live](https://ai.google.dev/gemini-api/docs/live-api/live-translate) y [VB-CABLE](https://vb-audio.com/Cable/).
