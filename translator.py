"""Microphone -> Gemini Live Translate -> chosen playback device (virtual cable)."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import queue
import sys
import threading
from dataclasses import dataclass
from typing import Callable

import sounddevice as sd
from google import genai
from google.genai import types

MODEL = "gemini-3.5-live-translate-preview"
# Languages listed in Google's Live Translate documentation (BCP-47 codes).
SUPPORTED_LANGUAGES = (
    ("af", "Afrikaans"), ("ak", "Akan"), ("sq", "Albanian"),
    ("am", "Amharic"), ("ar", "Arabic"), ("hy", "Armenian"),
    ("az", "Azerbaijani"), ("eu", "Basque"), ("be", "Belarusian"),
    ("bn", "Bengali"), ("bg", "Bulgarian"), ("my", "Burmese"),
    ("ca", "Catalan"), ("zh-Hans", "Chinese (Simplified)"),
    ("zh-Hant", "Chinese (Traditional)"), ("hr", "Croatian"),
    ("cs", "Czech"), ("da", "Danish"), ("nl", "Dutch"),
    ("en", "English"), ("et", "Estonian"), ("fil", "Filipino"),
    ("fi", "Finnish"), ("fr", "French"), ("gl", "Galician"),
    ("ka", "Georgian"), ("de", "German"), ("el", "Greek"),
    ("gu", "Gujarati"), ("ha", "Hausa"), ("he", "Hebrew"),
    ("hi", "Hindi"), ("hu", "Hungarian"), ("is", "Icelandic"),
    ("id", "Indonesian"), ("it", "Italian"), ("ja", "Japanese"),
    ("jv", "Javanese"), ("kn", "Kannada"), ("kk", "Kazakh"),
    ("km", "Khmer"), ("rw", "Kinyarwanda"), ("ko", "Korean"),
    ("lo", "Lao"), ("lv", "Latvian"), ("lt", "Lithuanian"),
    ("mk", "Macedonian"), ("ms", "Malay"), ("ml", "Malayalam"),
    ("mr", "Marathi"), ("mn", "Mongolian"), ("ne", "Nepali"),
    ("no", "Norwegian"), ("nb", "Norwegian Bokmål"),
    ("fa", "Persian"), ("pl", "Polish"),
    ("pt-BR", "Portuguese (Brazil)"), ("pt-PT", "Portuguese (Portugal)"),
    ("pa", "Punjabi"), ("ro", "Romanian"), ("ru", "Russian"),
    ("sr", "Serbian"), ("sd", "Sindhi"), ("si", "Sinhala"),
    ("sk", "Slovak"), ("sl", "Slovenian"), ("es", "Spanish"),
    ("su", "Sundanese"), ("sw", "Swahili"), ("sv", "Swedish"),
    ("ta", "Tamil"), ("te", "Telugu"), ("th", "Thai"),
    ("tr", "Turkish"), ("uk", "Ukrainian"), ("ur", "Urdu"),
    ("uz", "Uzbek"), ("vi", "Vietnamese"), ("zu", "Zulu"),
)
LANGUAGE_NAMES = dict(SUPPORTED_LANGUAGES)
INPUT_RATE = 16000
OUTPUT_RATE = 24000
INPUT_FRAMES = 1600  # 100 ms, per Google's translation API guidance.
OUTPUT_FRAMES = 480  # 20 ms playback blocks.
MAX_INPUT_CHUNKS = 20
MAX_OUTPUT_SECONDS = 3
MAX_OUTPUT_BYTES = OUTPUT_RATE * 2 * MAX_OUTPUT_SECONDS
EventCallback = Callable[[str, str], None]


def emit_event(callback: EventCallback | None, kind: str, message: str) -> None:
    if callback:
        callback(kind, message)
    elif kind == "transcript":
        print(f"\n{message}", flush=True)
    elif kind in {"status", "warning", "error"}:
        print(message, file=sys.stderr if kind in {"warning", "error"} else sys.stdout, flush=True)


@dataclass(frozen=True)
class Devices:
    input_index: int
    output_index: int


def list_devices() -> None:
    print("ID   IN OUT   NAME")
    for index, device in enumerate(sd.query_devices()):
        print(f"{index:<4} {device['max_input_channels']:<2} {device['max_output_channels']:<3}   {device['name']}")
    print("\nChoose your physical microphone as --input and CABLE Input (playback) as --output.")
    print("In Teams select CABLE Output (recording) as your microphone.")


def list_languages() -> None:
    print("CODE    LANGUAGE")
    for code, name in SUPPORTED_LANGUAGES:
        print(f"{code:<7} {name}")


def validate_devices(devices: Devices) -> None:
    for index, direction, rate in (
        (devices.input_index, "input", INPUT_RATE),
        (devices.output_index, "output", OUTPUT_RATE),
    ):
        info = sd.query_devices(index)
        if info[f"max_{direction}_channels"] < 1:
            raise ValueError(f"Device {index} has no {direction} channel: {info['name']}")
        getattr(sd, f"check_{direction}_settings")(
            device=index, channels=1, dtype="int16", samplerate=rate
        )


class AudioBridge:
    def __init__(self, loop: asyncio.AbstractEventLoop, on_event: EventCallback | None = None):
        self.loop = loop
        self.on_event = on_event
        self.input_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=MAX_INPUT_CHUNKS)
        self.output_queue: queue.Queue[bytes] = queue.Queue()
        self.output_bytes = 0
        self.pending = bytearray()
        self.playback_lock = threading.Lock()
        self.dropped_input = 0
        self.dropped_output = 0

    def input_callback(self, indata, frames, time_info, status) -> None:
        if status:
            emit_event(self.on_event, "warning", f"Entrada de audio: {status}")
        data = bytes(indata)

        def enqueue() -> None:
            if self.input_queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    self.input_queue.get_nowait()
                    self.dropped_input += 1
            self.input_queue.put_nowait(data)

        self.loop.call_soon_threadsafe(enqueue)

    def add_output(self, data: bytes) -> None:
        if not data:
            return
        with self.playback_lock:
            while self.output_bytes + len(self.pending) + len(data) > MAX_OUTPUT_BYTES:
                try:
                    old = self.output_queue.get_nowait()
                    self.output_bytes -= len(old)
                except queue.Empty:
                    # A single oversized chunk is unusual; keep its latest samples.
                    data = data[-MAX_OUTPUT_BYTES:]
                    self.pending.clear()
                    break
                self.dropped_output += 1
            self.output_queue.put_nowait(data)
            self.output_bytes += len(data)

    def output_callback(self, outdata, frames, time_info, status) -> None:
        if status:
            emit_event(self.on_event, "warning", f"Salida de audio: {status}")
        requested = frames * 2  # mono int16
        with self.playback_lock:
            while len(self.pending) < requested:
                try:
                    chunk = self.output_queue.get_nowait()
                    self.output_bytes -= len(chunk)
                    self.pending.extend(chunk)
                except queue.Empty:
                    break
            available = min(requested, len(self.pending))
            outdata[:available] = self.pending[:available]
            if available < requested:
                outdata[available:requested] = bytes(requested - available)
            del self.pending[:available]


async def send_audio(session, bridge: AudioBridge) -> None:
    while True:
        chunk = await bridge.input_queue.get()
        await session.send_realtime_input(
            audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
        )


async def receive_audio(
    session, bridge: AudioBridge, show_text: bool, on_event: EventCallback | None,
    target_language: str,
) -> None:
    async for response in session.receive():
        content = response.server_content
        if content is None:
            continue
        if show_text:
            for label, transcript in (
                ("ES", content.input_transcription),
                (target_language.upper(), content.output_transcription),
            ):
                if transcript and transcript.text:
                    emit_event(on_event, "transcript", f"{label}: {transcript.text}")
        if content.model_turn:
            for part in content.model_turn.parts:
                if part.inline_data and part.inline_data.data:
                    bridge.add_output(part.inline_data.data)
        # Translation is continuous; do not discard queued audio at turn_complete.
    raise ConnectionError("Gemini closed the translation stream")


async def wait_for_stop(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        await asyncio.sleep(0.1)


async def run(
    devices: Devices,
    show_text: bool,
    on_event: EventCallback | None = None,
    stop_event: threading.Event | None = None,
    target_language: str = "en",
) -> None:
    if target_language not in LANGUAGE_NAMES:
        raise ValueError(f"Unsupported target language: {target_language}")
    key = os.environ.get("GEMINI_API_KEY")
    if not key and sys.platform == "win32":
        # setx writes to the user registry; an existing Explorer process may
        # launch the installed app before its environment has been refreshed.
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as user_environment:
                key = winreg.QueryValueEx(user_environment, "GEMINI_API_KEY")[0]
        except FileNotFoundError:
            pass
    if not key:
        raise ValueError("Set GEMINI_API_KEY in your environment before running")
    validate_devices(devices)
    loop = asyncio.get_running_loop()
    bridge = AudioBridge(loop, on_event)
    stop_event = stop_event or threading.Event()
    client = genai.Client(api_key=key, http_options={"api_version": "v1beta"})
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        translation_config=types.TranslationConfig(
            target_language_code=target_language, echo_target_language=False
        ),
    )
    emit_event(on_event, "status", "Conectando con Gemini Live Translate…")
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            with sd.RawOutputStream(
                samplerate=OUTPUT_RATE, blocksize=OUTPUT_FRAMES, channels=1,
                dtype="int16", device=devices.output_index, callback=bridge.output_callback,
                latency="low",
            ), sd.RawInputStream(
                samplerate=INPUT_RATE, blocksize=INPUT_FRAMES, channels=1,
                dtype="int16", device=devices.input_index, callback=bridge.input_callback,
                latency="low",
            ):
                emit_event(
                    on_event, "status",
                    f"Activo: habla en español; Teams recibe la traducción en {LANGUAGE_NAMES[target_language]}.",
                )
                sender = asyncio.create_task(send_audio(session, bridge))
                receiver = asyncio.create_task(
                    receive_audio(session, bridge, show_text, on_event, target_language)
                )
                stopper = asyncio.create_task(wait_for_stop(stop_event))
                try:
                    done, _ = await asyncio.wait(
                        (sender, receiver, stopper), return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in done:
                        if task is not stopper:
                            await task
                finally:
                    for task in (sender, receiver, stopper):
                        task.cancel()
                    await asyncio.gather(sender, receiver, stopper, return_exceptions=True)
    finally:
        emit_event(on_event, "stopped", "Traducción detenida.")
        if bridge.dropped_input or bridge.dropped_output:
            emit_event(
                on_event,
                "warning",
                f"Bloques descartados: entrada={bridge.dropped_input}, salida={bridge.dropped_output}",
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--list-languages", action="store_true")
    parser.add_argument("--input", type=int, help="Physical microphone device ID")
    parser.add_argument("--output", type=int, help="Virtual cable playback device ID")
    parser.add_argument(
        "--target-language", choices=LANGUAGE_NAMES, default="en", metavar="CODE",
        help="Translation target language BCP-47 code (default: en).",
    )
    parser.add_argument("--no-text", action="store_true", help="Hide transcripts")
    args = parser.parse_args()
    if args.list_languages:
        list_languages()
        return
    if args.list_devices:
        list_devices()
        return
    if args.input is None or args.output is None:
        parser.error("--input and --output are required; use --list-devices first")
    try:
        asyncio.run(run(
            Devices(args.input, args.output), not args.no_text,
            target_language=args.target_language,
        ))
    except KeyboardInterrupt:
        print("\nStopped.")
    except (ValueError, sd.PortAudioError, ConnectionError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
