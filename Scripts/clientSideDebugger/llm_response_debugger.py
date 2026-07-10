from __future__ import annotations

import json
import queue
import sys
import threading
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox, ttk


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Scripts.aiIntegration.CommandClient import DEFAULT_HOST, DEFAULT_PORT, send_commands
from Scripts.aiIntegration.ElevenLabsClient import (
    DEFAULT_TTS_VOICE_ID,
    add_voice_design_to_library,
    create_speak_command,
    create_voice_design_previews,
)


VOICE_LIBRARY_PATH = REPO_ROOT / "dataLibrary" / "voice_library.json"


def load_expression_names() -> list[str]:
    expressions_path = REPO_ROOT / "dataLibrary" / "expressions.json"

    with open(expressions_path, "r") as file:
        expression_data = json.load(file)

    states = expression_data.get("states")
    if not isinstance(states, dict) or not states:
        raise ValueError(f"No expression states found in {expressions_path}.")

    default_state = expression_data.get("default_state")
    expression_names = list(states.keys())

    if default_state in states:
        expression_names.remove(default_state)
        return [default_state, *expression_names]

    return expression_names


def load_saved_voice_records() -> list[dict]:
    if not VOICE_LIBRARY_PATH.exists():
        return []

    with open(VOICE_LIBRARY_PATH, "r") as file:
        data = json.load(file)

    voices = data.get("voices", [])
    if not isinstance(voices, list):
        raise ValueError(f"'voices' in {VOICE_LIBRARY_PATH} must be a list.")

    return [
        voice
        for voice in voices
        if isinstance(voice, dict) and isinstance(voice.get("voice_id"), str)
    ]


def save_voice_record(voice_record: dict) -> list[dict]:
    voice_id = voice_record["voice_id"].strip()
    if not voice_id:
        raise ValueError("Cannot save an empty voice ID.")

    saved_voices = load_saved_voice_records()
    updated_voices = []
    record_was_updated = False

    for saved_voice in saved_voices:
        if saved_voice.get("voice_id") == voice_id:
            updated_voices.append(voice_record)
            record_was_updated = True
            continue

        updated_voices.append(saved_voice)

    if not record_was_updated:
        updated_voices.append(voice_record)

    VOICE_LIBRARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(VOICE_LIBRARY_PATH, "w") as file:
        json.dump(
            {
                "version": 1,
                "voices": updated_voices,
            },
            file,
            indent=2,
        )

    return updated_voices


def build_saved_voice_label(voice_record: dict) -> str:
    voice_name = voice_record.get("voice_name") or "Saved voice"
    voice_id = voice_record.get("voice_id", "")
    return f"{voice_name} ({voice_id})"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00",
        "Z",
    )


class LLMResponseDebugger(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("LLM Response Debugger")
        self.minsize(560, 420)

        self.startup_messages = []
        try:
            self.saved_voices = load_saved_voice_records()
        except Exception as exc:
            self.saved_voices = []
            self.startup_messages.append(f"ERROR: could not load saved voices: {exc}")

        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        self.port_var = tk.IntVar(value=DEFAULT_PORT)
        self.debug_elevenlabs_var = tk.BooleanVar(value=True)
        self.expression_names = load_expression_names()
        self.expression_var = tk.StringVar(value=self.expression_names[0])
        self.saved_voice_var = tk.StringVar(value="")
        self.saved_voice_lookup = {}
        self.speech_voice_id_var = tk.StringVar(value=DEFAULT_TTS_VOICE_ID)
        self.voice_preview_var = tk.StringVar(value="")
        self.voice_result_var = tk.StringVar(
            value=f"Loaded {len(self.saved_voices)} saved voice(s)."
        )
        self.voice_previews = []
        self.voice_preview_description = ""
        self.status_var = tk.StringVar(value="Ready")
        self.log_queue: queue.Queue[object] = queue.Queue()
        self.action_buttons = []

        self._build_ui()
        self._refresh_saved_voice_options()
        for message in self.startup_messages:
            self._append_log(message)
        self.after(100, self._drain_log_queue)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        connection_frame = ttk.Frame(self, padding=(12, 12, 12, 6))
        connection_frame.grid(row=0, column=0, sticky="ew")
        connection_frame.columnconfigure(1, weight=1)

        ttk.Label(connection_frame, text="Host").grid(row=0, column=0, sticky="w")
        ttk.Entry(connection_frame, textvariable=self.host_var, width=18).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(6, 16),
        )

        ttk.Label(connection_frame, text="Port").grid(row=0, column=2, sticky="w")
        ttk.Entry(connection_frame, textvariable=self.port_var, width=8).grid(
            row=0,
            column=3,
            sticky="w",
            padx=(6, 16),
        )

        ttk.Checkbutton(
            connection_frame,
            text="Debug ElevenLabs",
            variable=self.debug_elevenlabs_var,
        ).grid(row=0, column=4, sticky="w")

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 6))

        self.speech_tab = ttk.Frame(self.notebook)
        voice_design_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.speech_tab, text="Speech")
        self.notebook.add(voice_design_tab, text="Voice Design")

        self._build_speech_tab(self.speech_tab)
        self._build_voice_design_tab(voice_design_tab)

        log_frame = ttk.Frame(self, padding=(12, 6, 12, 12))
        log_frame.grid(row=2, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)

        ttk.Label(log_frame, textvariable=self.status_var).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.log_text = tk.Text(log_frame, wrap="word", height=7, state="disabled")
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

    def _build_speech_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        expression_frame = ttk.Frame(parent, padding=(0, 8, 0, 6))
        expression_frame.grid(row=0, column=0, sticky="ew")
        expression_frame.columnconfigure(3, weight=1)

        ttk.Label(expression_frame, text="Expression").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            expression_frame,
            textvariable=self.expression_var,
            values=self.expression_names,
            state="readonly",
            width=24,
        ).grid(row=0, column=1, sticky="w", padx=(6, 0))

        ttk.Label(expression_frame, text="Voice ID").grid(
            row=0,
            column=2,
            sticky="w",
            padx=(16, 0),
        )
        ttk.Entry(
            expression_frame,
            textvariable=self.speech_voice_id_var,
            width=36,
        ).grid(row=0, column=3, sticky="ew", padx=(6, 0))

        ttk.Label(expression_frame, text="Saved Voice").grid(
            row=1,
            column=0,
            sticky="w",
            pady=(6, 0),
        )
        self.saved_voice_combo = ttk.Combobox(
            expression_frame,
            textvariable=self.saved_voice_var,
            values=[],
            state="readonly",
        )
        self.saved_voice_combo.grid(
            row=1,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=(6, 0),
            pady=(6, 0),
        )
        self.saved_voice_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._load_selected_saved_voice(),
        )

        text_frame = ttk.Frame(parent)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(1, weight=1)

        ttk.Label(text_frame, text="LLM response").grid(row=0, column=0, sticky="w")
        self.response_text = tk.Text(text_frame, wrap="word", height=10)
        self.response_text.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self.response_text.insert("1.0", "Hello from the client-side debugger.")

        button_frame = ttk.Frame(parent, padding=(0, 8, 0, 0))
        button_frame.grid(row=2, column=0, sticky="ew")

        self.send_button = ttk.Button(
            button_frame,
            text="Send Speak Command",
            command=self._send_speak_command,
        )
        self.send_button.grid(row=0, column=0, sticky="w")
        self.action_buttons.append(self.send_button)

        self.stop_button = ttk.Button(
            button_frame,
            text="Stop Speech",
            command=self._send_stop_speech,
        )
        self.stop_button.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.action_buttons.append(self.stop_button)

        ttk.Button(
            button_frame,
            text="Clear",
            command=lambda: self.response_text.delete("1.0", "end"),
        ).grid(row=0, column=2, sticky="w", padx=(8, 0))

    def _build_voice_design_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        ttk.Label(parent, text="Voice description").grid(
            row=0,
            column=0,
            sticky="w",
            pady=(8, 0),
        )

        self.voice_description_text = tk.Text(parent, wrap="word", height=8)
        self.voice_description_text.grid(row=1, column=0, sticky="nsew", pady=(4, 8))
        self.voice_description_text.insert(
            "1.0",
            "A warm, confident assistant voice with a clear tone and natural pacing.",
        )

        preview_frame = ttk.Frame(parent)
        preview_frame.grid(row=2, column=0, sticky="ew")
        preview_frame.columnconfigure(1, weight=1)

        ttk.Label(preview_frame, text="Preview").grid(row=0, column=0, sticky="w")
        self.voice_preview_combo = ttk.Combobox(
            preview_frame,
            textvariable=self.voice_preview_var,
            values=[],
            state="readonly",
            width=48,
        )
        self.voice_preview_combo.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.voice_preview_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._sync_selected_preview_to_speech_voice_id(),
        )

        button_frame = ttk.Frame(parent, padding=(0, 8, 0, 0))
        button_frame.grid(row=3, column=0, sticky="ew")

        self.voice_design_send_button = ttk.Button(
            button_frame,
            text="Send Voice Design",
            command=self._send_voice_design,
        )
        self.voice_design_send_button.grid(row=0, column=0, sticky="w")
        self.action_buttons.append(self.voice_design_send_button)

        self.voice_design_play_button = ttk.Button(
            button_frame,
            text="Play Preview",
            command=self._play_voice_preview,
        )
        self.voice_design_play_button.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.action_buttons.append(self.voice_design_play_button)
        self.voice_design_play_button.configure(state="disabled")

        self.voice_design_use_button = ttk.Button(
            button_frame,
            text="Use In Speech",
            command=self._use_voice_preview_in_speech,
        )
        self.voice_design_use_button.grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.action_buttons.append(self.voice_design_use_button)
        self.voice_design_use_button.configure(state="disabled")

        self.voice_design_approve_button = ttk.Button(
            button_frame,
            text="Approve Voice",
            command=self._approve_voice_design,
        )
        self.voice_design_approve_button.grid(row=0, column=3, sticky="w", padx=(8, 0))
        self.action_buttons.append(self.voice_design_approve_button)
        self.voice_design_approve_button.configure(state="disabled")

        ttk.Label(parent, textvariable=self.voice_result_var).grid(
            row=4,
            column=0,
            sticky="w",
            pady=(8, 0),
        )

    def _send_speak_command(self) -> None:
        text = self.response_text.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Missing text", "Enter an LLM response first.")
            return

        self._run_in_worker(
            "Sending speak command...",
            lambda: self._create_and_send_speak_command(text),
        )

    def _send_stop_speech(self) -> None:
        self._run_in_worker(
            "Sending stop command...",
            lambda: send_commands(
                [{"type": "stop_speech"}],
                host=self.host_var.get(),
                port=self.port_var.get(),
            ),
        )

    def _send_voice_design(self) -> None:
        voice_description = self.voice_description_text.get("1.0", "end").strip()
        if not voice_description:
            messagebox.showwarning(
                "Missing voice description",
                "Enter a voice description first.",
            )
            return

        self._run_in_worker(
            "Generating voice previews...",
            lambda: self._create_voice_design_previews(voice_description),
        )

    def _play_voice_preview(self) -> None:
        preview = self._selected_voice_preview()
        if preview is None:
            messagebox.showwarning(
                "Missing voice preview",
                "Generate and select a voice preview first.",
            )
            return

        self._run_in_worker(
            "Playing selected voice preview...",
            lambda: self._send_voice_preview_audio(preview),
        )

    def _use_voice_preview_in_speech(self) -> None:
        if not self._sync_selected_preview_to_speech_voice_id():
            messagebox.showwarning(
                "Missing voice preview",
                "Generate and select a voice preview first.",
            )
            return

        self.notebook.select(self.speech_tab)
        self.debug_elevenlabs_var.set(False)
        self._append_log(
            f"Speech voice ID set to preview {self.speech_voice_id_var.get()}. "
            "Debug ElevenLabs disabled."
        )

    def _approve_voice_design(self) -> None:
        generated_voice_id = self.voice_preview_var.get().strip()
        if not generated_voice_id:
            messagebox.showwarning(
                "Missing voice preview",
                "Generate and select a voice preview first.",
            )
            return

        voice_description = (
            self.voice_preview_description
            or self.voice_description_text.get("1.0", "end").strip()
        )

        self._run_in_worker(
            "Approving voice design...",
            lambda: self._add_voice_design_to_library(
                generated_voice_id,
                voice_description,
            ),
        )

    def _create_and_send_speak_command(self, text: str) -> None:
        debug_elevenlabs = self.debug_elevenlabs_var.get()
        expression_name = self.expression_var.get()
        voice_id = self.speech_voice_id_var.get().strip() or None
        commands = [
            {"type": "expression", "name": expression_name},
            *create_speak_command(text, debug=debug_elevenlabs, voice_id=voice_id),
        ]
        send_commands(
            commands,
            host=self.host_var.get(),
            port=self.port_var.get(),
        )
        self.log_queue.put(
            f"Sent {len(commands)} command(s). Expression={expression_name}. "
            f"Voice ID={voice_id}. Debug ElevenLabs={debug_elevenlabs}"
        )

    def _create_voice_design_previews(self, voice_description: str) -> None:
        previews = create_voice_design_previews(voice_description)
        self.log_queue.put(("VOICE_PREVIEWS", voice_description, previews))

    def _send_voice_preview_audio(self, preview: dict) -> None:
        generated_voice_id = preview["generated_voice_id"]
        send_commands(
            [{"type": "play", "audio": preview["audio_base64"]}],
            host=self.host_var.get(),
            port=self.port_var.get(),
        )
        self.log_queue.put(f"Played voice preview {generated_voice_id}")

    def _add_voice_design_to_library(
        self,
        generated_voice_id: str,
        voice_description: str,
    ) -> None:
        voice = add_voice_design_to_library(
            generated_voice_id=generated_voice_id,
            voice_description=voice_description,
        )
        self.log_queue.put(("VOICE_APPROVED", voice))

    def _run_in_worker(self, status: str, action) -> None:
        self.status_var.set(status)
        self._set_action_buttons_state("disabled")

        def worker() -> None:
            try:
                action()
            except Exception as exc:
                self.log_queue.put(f"ERROR: {exc}")
            finally:
                self.log_queue.put("READY")

        threading.Thread(target=worker, daemon=True).start()

    def _drain_log_queue(self) -> None:
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if message == "READY":
                self.status_var.set("Ready")
                self._set_action_buttons_state("normal")
                self._refresh_voice_preview_action_state()
                continue

            if isinstance(message, tuple):
                if message[0] == "VOICE_PREVIEWS":
                    self._handle_voice_previews(message[1], message[2])
                    continue

                if message[0] == "VOICE_APPROVED":
                    self._handle_voice_approved(message[1])
                    continue

                self._append_log(f"UNKNOWN EVENT: {message[0]}")
                continue

            self._append_log(message)

        self.after(100, self._drain_log_queue)

    def _handle_voice_previews(self, voice_description: str, previews) -> None:
        self.voice_previews = previews
        self.voice_preview_description = voice_description

        preview_ids = [preview["generated_voice_id"] for preview in previews]
        self.voice_preview_combo.configure(values=preview_ids)
        self.voice_preview_var.set(preview_ids[0])
        self._sync_selected_preview_to_speech_voice_id()
        self.voice_result_var.set(
            f"{len(preview_ids)} preview(s) generated. Select one and approve it."
        )
        self._append_log(
            "Generated voice previews: " + ", ".join(preview_ids)
        )
        self._refresh_voice_preview_action_state()

    def _handle_voice_approved(self, voice) -> None:
        voice_id = voice["voice_id"]
        generated_voice_id = voice["generated_voice_id"]
        self.speech_voice_id_var.set(voice_id)
        self.debug_elevenlabs_var.set(False)
        print(f"Approved ElevenLabs voice ID: {voice_id}")
        self.voice_result_var.set(f"Approved voice ID: {voice_id}")
        self._append_log(
            f"Approved voice ID: {voice_id} from preview {generated_voice_id}"
        )

        voice_record = {
            "voice_id": voice_id,
            "voice_name": voice.get("voice_name") or "Designed voice",
            "generated_voice_id": generated_voice_id,
            "description": self.voice_preview_description,
            "approved_at": utc_timestamp(),
        }

        try:
            self.saved_voices = save_voice_record(voice_record)
        except Exception as exc:
            self._append_log(
                "ERROR: approved voice was added to ElevenLabs, "
                f"but local voice logging failed: {exc}"
            )
            return

        self._refresh_saved_voice_options(selected_voice_id=voice_id)
        self._append_log(f"Saved voice ID to {VOICE_LIBRARY_PATH}")

    def _set_action_buttons_state(self, state: str) -> None:
        for button in self.action_buttons:
            button.configure(state=state)

    def _refresh_voice_preview_action_state(self) -> None:
        if self.voice_preview_var.get().strip():
            self.voice_design_play_button.configure(state="normal")
            self.voice_design_use_button.configure(state="normal")
            self.voice_design_approve_button.configure(state="normal")
            return

        self.voice_design_play_button.configure(state="disabled")
        self.voice_design_use_button.configure(state="disabled")
        self.voice_design_approve_button.configure(state="disabled")

    def _sync_selected_preview_to_speech_voice_id(self) -> bool:
        generated_voice_id = self.voice_preview_var.get().strip()
        if not generated_voice_id:
            return False

        self.speech_voice_id_var.set(generated_voice_id)
        return True

    def _selected_voice_preview(self):
        generated_voice_id = self.voice_preview_var.get().strip()
        if not generated_voice_id:
            return None

        for preview in self.voice_previews:
            if preview["generated_voice_id"] == generated_voice_id:
                return preview

        return None

    def _load_selected_saved_voice(self) -> bool:
        selected_label = self.saved_voice_var.get()
        voice_record = self.saved_voice_lookup.get(selected_label)

        if voice_record is None:
            return False

        self.speech_voice_id_var.set(voice_record["voice_id"])
        self.debug_elevenlabs_var.set(False)
        self._append_log(
            f"Loaded saved voice ID {voice_record['voice_id']} into Speech."
        )
        return True

    def _refresh_saved_voice_options(self, selected_voice_id: str | None = None) -> None:
        self.saved_voice_lookup = {
            build_saved_voice_label(voice_record): voice_record
            for voice_record in self.saved_voices
        }

        labels = list(self.saved_voice_lookup.keys())
        self.saved_voice_combo.configure(values=labels)

        if selected_voice_id is None:
            if self.saved_voice_var.get() not in self.saved_voice_lookup:
                self.saved_voice_var.set("")
            return

        for label, voice_record in self.saved_voice_lookup.items():
            if voice_record.get("voice_id") == selected_voice_id:
                self.saved_voice_var.set(label)
                return

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


if __name__ == "__main__":
    app = LLMResponseDebugger()
    app.mainloop()
