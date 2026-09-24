"""Simple desktop controls for the Teams live voice translator."""

from __future__ import annotations

import asyncio
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import sounddevice as sd

from translator import Devices, INPUT_RATE, OUTPUT_RATE, run


class TranslatorWindow:
    POLL_MS = 100
    MAX_TRANSCRIPT_LINES = 500

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("LiveVoice — Traducción para Teams")
        self.root.geometry("920x680")
        self.root.minsize(760, 560)

        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.stop_event: threading.Event | None = None
        self.input_devices: dict[str, int] = {}
        self.output_devices: dict[str, int] = {}

        self.status_var = tk.StringVar(value="Listo para iniciar")
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()

        self._build_ui()
        self._load_devices()
        self.root.after(self.POLL_MS, self._poll_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        header = ttk.Frame(self.root, padding=(18, 16, 18, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="LiveVoice", font=("Segoe UI", 21, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Habla en español; la voz inglesa traducida se envía a Teams por VB-CABLE.",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        controls = ttk.LabelFrame(self.root, text="Audio", padding=12)
        controls.grid(row=1, column=0, sticky="ew", padx=18, pady=(4, 10))
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(3, weight=1)

        ttk.Label(controls, text="Micrófono físico").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.input_combo = ttk.Combobox(
            controls, textvariable=self.input_var, state="readonly", width=42
        )
        self.input_combo.grid(row=0, column=1, sticky="ew", padx=(0, 14))
        ttk.Label(controls, text="Salida (CABLE Input)").grid(
            row=0, column=2, sticky="w", padx=(0, 8)
        )
        self.output_combo = ttk.Combobox(
            controls, textvariable=self.output_var, state="readonly", width=42
        )
        self.output_combo.grid(row=0, column=3, sticky="ew")

        button_row = ttk.Frame(controls)
        button_row.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        self.start_button = ttk.Button(button_row, text="Iniciar traducción", command=self.start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(
            button_row, text="Detener", command=self.stop, state="disabled"
        )
        self.stop_button.pack(side="left", padx=(8, 0))
        self.refresh_button = ttk.Button(
            button_row, text="Actualizar dispositivos", command=self._load_devices
        )
        self.refresh_button.pack(side="right")

        translations = ttk.LabelFrame(self.root, text="Transcripción en vivo", padding=10)
        translations.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 10))
        translations.columnconfigure(0, weight=1)
        translations.columnconfigure(1, weight=1)
        translations.rowconfigure(1, weight=1)
        ttk.Label(translations, text="ES · Lo que dices").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Label(translations, text="EN · Traducción hablada por Gemini").grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        self.es_text = self._transcript_box(translations, row=1, column=0)
        self.en_text = self._transcript_box(translations, row=1, column=1)

        footer = ttk.Frame(self.root, padding=(18, 0, 18, 14))
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(1, weight=1)
        ttk.Label(footer, text="Estado:", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        self.status_label = ttk.Label(footer, textvariable=self.status_var)
        self.status_label.grid(row=0, column=1, sticky="w")
        ttk.Label(
            footer,
            text="En Teams selecciona CABLE Output como micrófono.",
            foreground="#555555",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

    @staticmethod
    def _transcript_box(parent: ttk.LabelFrame, row: int, column: int) -> tk.Text:
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=column, sticky="nsew", padx=(0, 6) if column == 0 else (6, 0), pady=(5, 0))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        text = tk.Text(frame, wrap="word", state="disabled", font=("Segoe UI", 10), height=15)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        return text

    def _load_devices(self) -> None:
        try:
            devices = sd.query_devices()
            host_apis = sd.query_hostapis()
        except Exception as exc:
            self._set_status(f"No se pudieron consultar los dispositivos: {exc}", error=True)
            return

        old_input, old_output = self.input_var.get(), self.output_var.get()
        self.input_devices.clear()
        self.output_devices.clear()
        for index, device in enumerate(devices):
            host = host_apis[device["hostapi"]]["name"]
            label = f"{index} — {device['name']} [{host}]"
            if device["max_input_channels"] > 0:
                self.input_devices[label] = index
            if device["max_output_channels"] > 0:
                self.output_devices[label] = index

        self.input_combo["values"] = tuple(self.input_devices)
        self.output_combo["values"] = tuple(self.output_devices)
        self.input_var.set(
            old_input
            if old_input in self.input_devices
            else self._preferred(
                self.input_devices,
                ("BlackShark V3 X [Windows DirectSound]", "BlackShark", "Microphone", "Micr"),
            )
        )
        self.output_var.set(
            old_output
            if old_output in self.output_devices
            else self._preferred(
                self.output_devices,
                (
                    "CABLE Input (VB-Audio Virtual Cable) [Windows DirectSound]",
                    "CABLE Input",
                ),
            )
        )
        if not self.input_devices or not self.output_devices:
            self._set_status("No se encontraron dispositivos de entrada y salida.", error=True)
        else:
            self._set_status(f"Dispositivos listos ({INPUT_RATE} Hz entrada, {OUTPUT_RATE} Hz salida).")

    @staticmethod
    def _preferred(options: dict[str, int], tokens: tuple[str, ...]) -> str:
        for token in tokens:
            match = next((label for label in options if token.casefold() in label.casefold()), None)
            if match:
                return match
        return next(iter(options), "")

    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        input_index = self.input_devices.get(self.input_var.get())
        output_index = self.output_devices.get(self.output_var.get())
        if input_index is None or output_index is None:
            messagebox.showerror("Faltan dispositivos", "Selecciona un micrófono y una salida de audio.")
            return

        self.stop_event = threading.Event()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.input_combo.configure(state="disabled")
        self.output_combo.configure(state="disabled")
        self.refresh_button.configure(state="disabled")
        self._set_status("Iniciando…")
        self._append(self.es_text, "— Sesión nueva —")
        self._append(self.en_text, "— New session —")
        self.worker = threading.Thread(
            target=self._run_worker,
            args=(Devices(input_index, output_index), self.stop_event),
            name="livevoice-translator",
            daemon=True,
        )
        self.worker.start()

    def _run_worker(self, devices: Devices, stop_event: threading.Event) -> None:
        try:
            asyncio.run(run(devices, True, self._enqueue_event, stop_event))
        except Exception as exc:
            self._enqueue_event("error", str(exc))
        finally:
            self._enqueue_event("finished", "")

    def stop(self) -> None:
        if self.stop_event:
            self.stop_event.set()
            self.stop_button.configure(state="disabled")
            self._set_status("Deteniendo audio…")

    def _enqueue_event(self, kind: str, message: str) -> None:
        self.events.put((kind, message))

    def _poll_events(self) -> None:
        try:
            while True:
                kind, message = self.events.get_nowait()
                if kind == "transcript":
                    label, _, transcript = message.partition(":")
                    target = self.es_text if label == "ES" else self.en_text
                    self._append(target, transcript.strip())
                elif kind == "status":
                    self._set_status(message)
                elif kind == "warning":
                    self._set_status(message, warning=True)
                elif kind == "error":
                    self._set_status(message, error=True)
                elif kind == "stopped":
                    self._set_status(message)
                elif kind == "finished":
                    self._reset_controls()
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(self.POLL_MS, self._poll_events)

    def _append(self, box: tk.Text, line: str) -> None:
        box.configure(state="normal")
        box.insert("end", line + "\n")
        line_count = int(box.index("end-1c").split(".")[0])
        if line_count > self.MAX_TRANSCRIPT_LINES:
            box.delete("1.0", f"{line_count - self.MAX_TRANSCRIPT_LINES}.0")
        box.see("end")
        box.configure(state="disabled")

    def _set_status(self, message: str, error: bool = False, warning: bool = False) -> None:
        self.status_var.set(message)
        color = "#a12622" if error else "#8a5a00" if warning else "#1f5f36"
        self.status_label.configure(foreground=color)

    def _reset_controls(self) -> None:
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.input_combo.configure(state="readonly")
        self.output_combo.configure(state="readonly")
        self.refresh_button.configure(state="normal")

    def _on_close(self) -> None:
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno("Salir", "La traducción está activa. ¿Detenerla y cerrar?"):
                return
            if self.stop_event:
                self.stop_event.set()
            self.root.after(self.POLL_MS, self._wait_for_worker)
            return
        self.root.destroy()

    def _wait_for_worker(self) -> None:
        if self.worker and self.worker.is_alive():
            self.root.after(self.POLL_MS, self._wait_for_worker)
        else:
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    TranslatorWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
