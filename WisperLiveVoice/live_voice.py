"""Micrófono -> Whisper (traducción al inglés) -> ElevenLabs -> salida de audio."""

from __future__ import annotations

import argparse
import asyncio
import base64
import collections
import json
import os
import queue
import sys
import threading
from urllib.parse import quote, urlencode

import numpy as np
import sounddevice as sd
import websockets
import ctranslate2
from faster_whisper import WhisperModel

INPUT_RATE = 16000
OUTPUT_RATE = 24000
FRAME_MS = 20
INPUT_FRAMES = INPUT_RATE * FRAME_MS // 1000
OUTPUT_FRAMES = OUTPUT_RATE * FRAME_MS // 1000
SILENCE_FRAMES = 30  # 600 ms
MIN_SPEECH_FRAMES = 15  # 300 ms
MAX_UTTERANCE_FRAMES = 400  # 8 s
DEFAULT_RMS_THRESHOLD = 0.004
ELEVENLABS_MODELS = {
    "flash": "eleven_flash_v2_5",
    "v3": "eleven_v3_conversational",
}
FLASH_VOICE_SETTINGS = {
    "speed": 0.73,
    "stability": 0.30,
    "similarity_boost": 1.0,
    "style": 0.0,
}


def list_devices() -> None:
    print("ID   IN OUT  DEVICE")
    for index, device in enumerate(sd.query_devices()):
        print(f"{index:<4} {device['max_input_channels']:<2} {device['max_output_channels']:<3}  {device['name']}")


def validate_devices(input_index: int, output_index: int) -> None:
    for index, direction, rate in ((input_index, "input", INPUT_RATE), (output_index, "output", OUTPUT_RATE)):
        info = sd.query_devices(index)
        if info[f"max_{direction}_channels"] < 1:
            raise ValueError(f"El dispositivo {index} no admite {direction}: {info['name']}")
        getattr(sd, f"check_{direction}_settings")(
            device=index, channels=1, dtype="int16", samplerate=rate
        )


class PhraseDetector:
    """Corta el audio en frases usando volumen y pausas; conserva 200 ms previos."""

    def __init__(self, threshold: float = DEFAULT_RMS_THRESHOLD) -> None:
        self.threshold = threshold
        self.level = 0.0
        self.preroll: collections.deque[bytes] = collections.deque(maxlen=10)
        self.frames: list[bytes] = []
        self.speech_frames = 0
        self.silent_frames = 0

    def feed(self, frame: bytes) -> bytes | None:
        samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0
        self.level = float(np.sqrt(np.mean(samples * samples)))
        voiced = self.level >= self.threshold
        if not self.frames:
            self.preroll.append(frame)
            if not voiced:
                return None
            self.frames = list(self.preroll)
            self.preroll.clear()
        else:
            self.frames.append(frame)
        if voiced:
            self.speech_frames += 1
            self.silent_frames = 0
        else:
            self.silent_frames += 1
        if self.silent_frames >= SILENCE_FRAMES or len(self.frames) >= MAX_UTTERANCE_FRAMES:
            return self.finish()
        return None

    def finish(self) -> bytes | None:
        result = b"".join(self.frames) if self.speech_frames >= MIN_SPEECH_FRAMES else None
        self.frames = []
        self.speech_frames = 0
        self.silent_frames = 0
        self.preroll.clear()
        return result


class Playback:
    def __init__(self) -> None:
        self.chunks: queue.Queue[bytes] = queue.Queue()
        self.pending = bytearray()
        self.queued_bytes = 0
        self.lock = threading.Lock()
        self.max_bytes = OUTPUT_RATE * 2 * 5

    def add(self, data: bytes) -> None:
        with self.lock:
            if len(data) > self.max_bytes:
                data = data[-self.max_bytes:]
            while self.queued_bytes + len(self.pending) + len(data) > self.max_bytes:
                try:
                    old = self.chunks.get_nowait()
                    self.queued_bytes -= len(old)
                except queue.Empty:
                    self.pending.clear()
                    break
            self.chunks.put_nowait(data)
            self.queued_bytes += len(data)

    def callback(self, outdata, frames, time_info, status) -> None:
        needed = frames * 2
        with self.lock:
            while len(self.pending) < needed:
                try:
                    chunk = self.chunks.get_nowait()
                except queue.Empty:
                    break
                self.queued_bytes -= len(chunk)
                self.pending.extend(chunk)
            available = min(needed, len(self.pending))
            outdata[:available] = self.pending[:available]
            outdata[available:needed] = bytes(needed - available)
            del self.pending[:available]


def recognize_text(model: WhisperModel, pcm: bytes, language: str, task: str) -> str:
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    segments, _ = model.transcribe(
        audio, language=language, task=task, beam_size=5 if task == "translate" else 1,
        condition_on_previous_text=False, vad_filter=False,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()


def elevenlabs_api_key() -> str | None:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key or sys.platform != "win32":
        return key
    # setx updates the Windows user variable but not an already-open terminal.
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as user_environment:
            return winreg.QueryValueEx(user_environment, "ELEVENLABS_API_KEY")[0]
    except FileNotFoundError:
        return None


def synthesis_request(text: str, voice_id: str, model_choice: str) -> tuple[str, list[dict]]:
    """Build the URL and messages for the selected ElevenLabs WebSocket protocol."""
    model_id = ELEVENLABS_MODELS[model_choice]
    query = {"model_id": model_id, "output_format": "pcm_24000"}
    if model_choice == "flash":
        query["auto_mode"] = "true"
        query["language_code"] = "es"
        path = f"text-to-speech/{quote(voice_id, safe='')}/stream-input"
        messages = [
            {"text": " ", "voice_settings": FLASH_VOICE_SETTINGS},
            {"text": text, "flush": True},
            {"text": ""},
        ]
    else:
        path = "text-to-dialogue/stream-input"
        messages = [
            {"voices": [voice_id]},
            {"inputs": [{"text": text, "voice_id": voice_id, "new_turn": False}]},
            {"close_socket": True},
        ]
    return f"wss://api.elevenlabs.io/v1/{path}?{urlencode(query)}", messages


async def synthesize(
    text: str, voice_id: str, api_key: str, playback: Playback, model_choice: str
) -> int:
    url, messages = synthesis_request(text, voice_id, model_choice)
    received = 0
    async with websockets.connect(url, additional_headers={"xi-api-key": api_key}, open_timeout=15) as ws:
        print(f"ElevenLabs ({ELEVENLABS_MODELS[model_choice]}): conectado; generando voz…", flush=True)
        for item in messages:
            await ws.send(json.dumps(item))
        async with asyncio.timeout(60):
            async for message in ws:
                response = json.loads(message)
                if response.get("error"):
                    raise RuntimeError(f"ElevenLabs: {response['error']}")
                if response.get("audio"):
                    chunk = base64.b64decode(response["audio"])
                    playback.add(chunk)
                    received += len(chunk)
                    if received == len(chunk):
                        print("ElevenLabs: llegó audio; reproduciendo…", flush=True)
                if response.get("isFinal") or response.get("is_final"):
                    break
    if not received:
        raise RuntimeError("ElevenLabs terminó sin enviar audio")
    return received


async def run(args: argparse.Namespace) -> None:
    api_key = elevenlabs_api_key()
    if not api_key:
        raise ValueError("Define ELEVENLABS_API_KEY en el entorno")
    validate_devices(args.input, args.output)
    if ctranslate2.get_cuda_device_count() < 1:
        raise RuntimeError("Whisper requiere una GPU NVIDIA con CUDA; no se detectó ninguna")
    print(f"Cargando Whisper {args.whisper_model} en GPU (CUDA, float16)…", flush=True)
    model = await asyncio.to_thread(WhisperModel, args.whisper_model, device="cuda", compute_type="float16")
    loop = asyncio.get_running_loop()
    input_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=100)
    phrase_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=3)
    text_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=3)
    playback = Playback()
    detector = PhraseDetector(args.mic_threshold)

    def input_callback(indata, frames, time_info, status) -> None:
        data = bytes(indata)

        def enqueue() -> None:
            if input_queue.full():
                input_queue.get_nowait()
            input_queue.put_nowait(data)

        if not loop.is_closed():
            loop.call_soon_threadsafe(enqueue)

    async def collect() -> None:
        while True:
            was_active = bool(detector.frames)
            phrase = detector.feed(await input_queue.get())
            if not was_active and detector.frames:
                print("Micrófono: voz detectada…", flush=True)
            if phrase:
                print(f"Micrófono: frase capturada ({len(phrase) / (INPUT_RATE * 2):.1f} s); en cola para Whisper.", flush=True)
                if phrase_queue.full():
                    phrase_queue.get_nowait()
                    print("Aviso: se descartó una frase pendiente para evitar atraso.", file=sys.stderr)
                phrase_queue.put_nowait(phrase)

    async def recognize() -> None:
        while True:
            pcm = await phrase_queue.get()
            print("Whisper: traduciendo…", flush=True)
            english = await asyncio.to_thread(recognize_text, model, pcm, args.source_language, "translate")
            if english:
                print(f"EN: {english}", flush=True)
                if text_queue.full():
                    text_queue.get_nowait()
                    print("Aviso: se descartó una traducción pendiente para evitar atraso.", file=sys.stderr)
                text_queue.put_nowait(english)
            else:
                print("Whisper: no se detectó texto en esa frase.", flush=True)
            # The TTS worker can start streaming while this second pass labels the source.
            source = await asyncio.to_thread(recognize_text, model, pcm, args.source_language, "transcribe")
            if source:
                print(f"{args.source_language.upper()}: {source}", flush=True)

    async def speak() -> None:
        while True:
            english = await text_queue.get()
            try:
                received = await synthesize(english, args.voice_id, api_key, playback, args.tts_model)
                print(f"ElevenLabs: voz recibida ({received / (OUTPUT_RATE * 2):.1f} s de audio).", flush=True)
            except Exception as exc:
                print(f"Error de ElevenLabs: {exc}", file=sys.stderr, flush=True)

    async def show_input_level() -> None:
        while True:
            await asyncio.sleep(1)
            bars = min(20, int(detector.level / detector.threshold * 5))
            print(
                f"Micrófono: [{'#' * bars}{'.' * (20 - bars)}] "
                f"nivel={detector.level:.3f} umbral={detector.threshold:.3f}",
                flush=True,
            )

    with sd.RawOutputStream(
        samplerate=OUTPUT_RATE, blocksize=OUTPUT_FRAMES, channels=1,
        dtype="int16", device=args.output, callback=playback.callback, latency="low",
    ), sd.RawInputStream(
        samplerate=INPUT_RATE, blocksize=INPUT_FRAMES, channels=1,
        dtype="int16", device=args.input, callback=input_callback, latency="low",
    ):
        print("Activo. Habla en español; pulsa Ctrl+C para detener.", flush=True)
        await asyncio.gather(collect(), recognize(), speak(), show_input_level())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--input", type=int, help="Índice del micrófono físico")
    parser.add_argument("--output", type=int, help="Índice de CABLE Input u otra salida")
    parser.add_argument("--voice-id", help="ID de voz de ElevenLabs")
    parser.add_argument("--tts-model", choices=ELEVENLABS_MODELS, default="flash",
                        help="Modelo de voz: flash (menor latencia) o v3 (más expresivo)")
    parser.add_argument("--source-language", default="es", help="Código de idioma de entrada (por defecto: es)")
    parser.add_argument("--whisper-model", default="large-v3", choices=("tiny", "base", "small", "medium", "large-v3"))
    parser.add_argument("--mic-threshold", type=float, default=DEFAULT_RMS_THRESHOLD,
                        help="Umbral de voz RMS (por defecto: 0.004; baja el valor si no detecta tu voz)")
    args = parser.parse_args()
    if args.list_devices:
        list_devices()
        return
    if args.input is None or args.output is None or not args.voice_id:
        parser.error("--input, --output y --voice-id son obligatorios; usa --list-devices")
    if not 0 < args.mic_threshold < 1:
        parser.error("--mic-threshold debe estar entre 0 y 1")
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nDetenido.")
    except (ValueError, sd.PortAudioError, RuntimeError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
