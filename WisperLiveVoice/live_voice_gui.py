"""Ventana para ver en vivo la transcripción y traducción de WisperLiveVoice."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import sounddevice as sd


class LiveVoiceWindow:
    MODEL_LABELS = {
        "Flash v2.5 · menor latencia": "flash",
        "v3 Conversational · más expresivo": "v3",
    }

    def __init__(self, root: tk.Tk, voice_id: str, tts_model: str = "flash") -> None:
        self.root = root
        self.root.title("WisperLiveVoice")
        self.root.geometry("940x650")
        self.events: queue.Queue[str | None] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None
        self.inputs: dict[str, int] = {}
        self.outputs: dict[str, int] = {}
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.voice_var = tk.StringVar(value=voice_id)
        initial_model = next(label for label, value in self.MODEL_LABELS.items() if value == tts_model)
        self.model_var = tk.StringVar(value=initial_model)
        self.threshold_var = tk.StringVar(value="0.004")
        self.pause_var = tk.StringVar(value="600")
        self.status_var = tk.StringVar(value="Listo")
        self.level_var = tk.StringVar(value="Micrófono: esperando inicio")
        self._build()
        self._load_devices()
        self.root.after(100, self._poll)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        controls = ttk.LabelFrame(self.root, text="Audio", padding=12)
        controls.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(3, weight=1)
        ttk.Label(controls, text="Micrófono").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.input_combo = ttk.Combobox(controls, textvariable=self.input_var, state="readonly")
        self.input_combo.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ttk.Label(controls, text="Salida (CABLE Input)").grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.output_combo = ttk.Combobox(controls, textvariable=self.output_var, state="readonly")
        self.output_combo.grid(row=0, column=3, sticky="ew")
        ttk.Label(controls, text="ID de voz ElevenLabs").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.voice_entry = ttk.Entry(controls, textvariable=self.voice_var)
        self.voice_entry.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=(10, 0))
        self.start_button = ttk.Button(controls, text="Iniciar", command=self.start)
        self.start_button.grid(row=1, column=2, sticky="ew", pady=(10, 0))
        self.stop_button = ttk.Button(controls, text="Detener", command=self.stop, state="disabled")
        self.stop_button.grid(row=1, column=3, sticky="ew", pady=(10, 0))
        ttk.Label(controls, text="Sensibilidad (umbral)").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.threshold_entry = ttk.Entry(controls, textvariable=self.threshold_var)
        self.threshold_entry.grid(row=2, column=1, sticky="w", pady=(10, 0))
        ttk.Label(controls, text="Modelo ElevenLabs").grid(row=2, column=2, sticky="w", pady=(10, 0))
        self.model_combo = ttk.Combobox(
            controls, textvariable=self.model_var, state="readonly",
            values=tuple(self.MODEL_LABELS),
        )
        self.model_combo.grid(row=2, column=3, sticky="ew", pady=(10, 0))
        ttk.Label(controls, text="Pausa para enviar (ms)").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.pause_entry = ttk.Entry(controls, textvariable=self.pause_var)
        self.pause_entry.grid(row=3, column=1, sticky="w", pady=(10, 0))

        feedback = ttk.Frame(self.root, padding=(16, 0))
        feedback.grid(row=1, column=0, sticky="ew")
        ttk.Label(feedback, textvariable=self.status_var).pack(anchor="w")
        ttk.Label(feedback, textvariable=self.level_var).pack(anchor="w")

        panes = ttk.Frame(self.root, padding=(14, 8, 14, 8))
        panes.grid(row=2, column=0, sticky="nsew")
        panes.columnconfigure(0, weight=1)
        panes.columnconfigure(1, weight=1)
        panes.rowconfigure(0, weight=1)
        self.source_text = self._pane(panes, 0, "ES · Lo que dices")
        self.translation_text = self._pane(panes, 1, "EN · Traducción enviada a ElevenLabs")

        log_frame = ttk.LabelFrame(self.root, text="Estado de Whisper y ElevenLabs", padding=8)
        log_frame.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))
        self.log_text = tk.Text(log_frame, height=5, wrap="word", state="disabled")
        self.log_text.pack(fill="x")

    @staticmethod
    def _pane(parent: ttk.Frame, column: int, title: str) -> tk.Text:
        frame = ttk.LabelFrame(parent, text=title, padding=8)
        frame.grid(row=0, column=column, sticky="nsew", padx=(0, 5) if column == 0 else (5, 0))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        box = tk.Text(frame, wrap="word", state="disabled", font=("Segoe UI", 11))
        box.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, command=box.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        box.configure(yscrollcommand=scroll.set)
        return box

    def _load_devices(self) -> None:
        devices = sd.query_devices()
        hosts = sd.query_hostapis()
        for index, device in enumerate(devices):
            label = f"{index} · {device['name']} [{hosts[device['hostapi']]['name']}]"
            if device["max_input_channels"]:
                self.inputs[label] = index
            if device["max_output_channels"]:
                self.outputs[label] = index
        self.input_combo["values"] = tuple(self.inputs)
        self.output_combo["values"] = tuple(self.outputs)
        directsound_mic = next(
            (label for label in self.inputs if "BlackShark V3 X" in label and "[Windows DirectSound]" in label),
            "",
        )
        self.input_var.set(directsound_mic or self._preferred(self.inputs, ("BlackShark", "Microphone", "Micrófono")))
        self.output_var.set(self._preferred(self.outputs, ("CABLE Input (VB-Audio Virtual Cable) [Windows DirectSound]", "CABLE Input")))

    @staticmethod
    def _preferred(options: dict[str, int], names: tuple[str, ...]) -> str:
        for name in names:
            found = next((label for label in options if name.casefold() in label.casefold()), None)
            if found:
                return found
        return next(iter(options), "")

    def start(self) -> None:
        if self.process and self.process.poll() is None:
            return
        voice = self.voice_var.get().strip()
        model_choice = self.MODEL_LABELS.get(self.model_var.get())
        if not voice or self.input_var.get() not in self.inputs or self.output_var.get() not in self.outputs or not model_choice:
            messagebox.showerror("Configuración incompleta", "Elige micrófono, salida e ID de voz.")
            return
        try:
            threshold = float(self.threshold_var.get())
            if not 0 < threshold < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Sensibilidad inválida", "El umbral debe ser un número entre 0 y 1.")
            return
        try:
            pause_ms = int(self.pause_var.get())
            if not 100 <= pause_ms <= 1500:
                raise ValueError
        except ValueError:
            messagebox.showerror("Pausa inválida", "La pausa debe ser un número entero entre 100 y 1500 ms.")
            return
        if getattr(sys, "frozen", False):
            engine = Path(sys.executable).parent / "engine" / "WisperLiveVoiceEngine.exe"
            if not engine.is_file():
                messagebox.showerror("Motor no encontrado", f"No se encontró el motor de Whisper: {engine}")
                return
            command = [str(engine)]
        else:
            command = [sys.executable, "-u", str(Path(__file__).with_name("live_voice.py"))]
        command += [
            "--input", str(self.inputs[self.input_var.get()]),
            "--output", str(self.outputs[self.output_var.get()]),
            "--voice-id", voice,
            "--tts-model", model_choice,
            "--mic-threshold", str(threshold),
            "--pause-ms", str(pause_ms),
        ]
        try:
            self.process = subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                bufsize=1, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            messagebox.showerror("No se pudo iniciar", str(exc))
            return
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.input_combo.configure(state="disabled")
        self.output_combo.configure(state="disabled")
        self.voice_entry.configure(state="disabled")
        self.threshold_entry.configure(state="disabled")
        self.pause_entry.configure(state="disabled")
        self.model_combo.configure(state="disabled")
        self.status_var.set("Iniciando Whisper en GPU…")
        threading.Thread(target=self._read_output, args=(self.process,), daemon=True).start()

    def _read_output(self, process: subprocess.Popen[str]) -> None:
        assert process.stdout is not None
        for line in process.stdout:
            self.events.put(line.rstrip("\r\n"))
        process.wait()
        self.events.put(None)

    def _poll(self) -> None:
        try:
            while True:
                line = self.events.get_nowait()
                if line is None:
                    self._finished()
                elif line.startswith("ES: "):
                    self._append(self.source_text, line[4:])
                elif line.startswith("EN: "):
                    self._append(self.translation_text, line[4:])
                elif line.startswith("Micrófono: ["):
                    self.level_var.set(line)
                elif line:
                    self.status_var.set(line)
                    self._append(self.log_text, line)
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(100, self._poll)

    @staticmethod
    def _append(box: tk.Text, line: str) -> None:
        box.configure(state="normal")
        box.insert("end", line + "\n")
        count = int(box.index("end-1c").split(".")[0])
        if count > 300:
            box.delete("1.0", f"{count - 300}.0")
        box.see("end")
        box.configure(state="disabled")

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.status_var.set("Deteniendo…")

    def _finished(self) -> None:
        code = self.process.returncode if self.process else None
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.input_combo.configure(state="readonly")
        self.output_combo.configure(state="readonly")
        self.voice_entry.configure(state="normal")
        self.threshold_entry.configure(state="normal")
        self.pause_entry.configure(state="normal")
        self.model_combo.configure(state="readonly")
        self.status_var.set(f"Detenido (código {code}).")

    def _close(self) -> None:
        self.stop()
        self.root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "")
    if not voice_id and sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as user_environment:
                voice_id = winreg.QueryValueEx(user_environment, "ELEVENLABS_VOICE_ID")[0]
        except FileNotFoundError:
            pass
    parser.add_argument("--voice-id", default=voice_id, help="ID de voz inicial de ElevenLabs")
    parser.add_argument("--tts-model", choices=("flash", "v3"), default="flash",
                        help="Modelo inicial de ElevenLabs")
    args = parser.parse_args()
    root = tk.Tk()
    LiveVoiceWindow(root, args.voice_id, args.tts_model)
    root.mainloop()


if __name__ == "__main__":
    main()
