from __future__ import annotations

import json
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from CommandClient import DEFAULT_HOST, DEFAULT_PORT, send_commands
from ElevenLabsClient import create_speak_command


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


class LLMResponseDebugger(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("LLM Response Debugger")
        self.minsize(560, 420)

        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        self.port_var = tk.IntVar(value=DEFAULT_PORT)
        self.debug_elevenlabs_var = tk.BooleanVar(value=True)
        self.expression_names = load_expression_names()
        self.expression_var = tk.StringVar(value=self.expression_names[0])
        self.status_var = tk.StringVar(value="Ready")
        self.log_queue: queue.Queue[str] = queue.Queue()

        self._build_ui()
        self.after(100, self._drain_log_queue)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

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

        expression_frame = ttk.Frame(self, padding=(12, 0, 12, 6))
        expression_frame.grid(row=1, column=0, sticky="ew")
        expression_frame.columnconfigure(1, weight=1)

        ttk.Label(expression_frame, text="Expression").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            expression_frame,
            textvariable=self.expression_var,
            values=self.expression_names,
            state="readonly",
            width=24,
        ).grid(row=0, column=1, sticky="w", padx=(6, 0))

        text_frame = ttk.Frame(self, padding=(12, 6))
        text_frame.grid(row=2, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(1, weight=1)

        ttk.Label(text_frame, text="LLM response").grid(row=0, column=0, sticky="w")
        self.response_text = tk.Text(text_frame, wrap="word", height=10)
        self.response_text.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self.response_text.insert("1.0", "Hello from the client-side debugger.")

        button_frame = ttk.Frame(self, padding=(12, 6))
        button_frame.grid(row=3, column=0, sticky="ew")

        self.send_button = ttk.Button(
            button_frame,
            text="Send Speak Command",
            command=self._send_speak_command,
        )
        self.send_button.grid(row=0, column=0, sticky="w")

        ttk.Button(
            button_frame,
            text="Stop Speech",
            command=self._send_stop_speech,
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))

        ttk.Button(
            button_frame,
            text="Clear",
            command=lambda: self.response_text.delete("1.0", "end"),
        ).grid(row=0, column=2, sticky="w", padx=(8, 0))

        log_frame = ttk.Frame(self, padding=(12, 6, 12, 12))
        log_frame.grid(row=4, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)

        ttk.Label(log_frame, textvariable=self.status_var).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.log_text = tk.Text(log_frame, wrap="word", height=7, state="disabled")
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

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

    def _create_and_send_speak_command(self, text: str) -> None:
        debug_elevenlabs = self.debug_elevenlabs_var.get()
        expression_name = self.expression_var.get()
        commands = [
            {"type": "expression", "name": expression_name},
            *create_speak_command(text, debug=debug_elevenlabs),
        ]
        send_commands(
            commands,
            host=self.host_var.get(),
            port=self.port_var.get(),
        )
        self.log_queue.put(
            f"Sent {len(commands)} command(s). Expression={expression_name}. "
            f"Debug ElevenLabs={debug_elevenlabs}"
        )

    def _run_in_worker(self, status: str, action) -> None:
        self.status_var.set(status)
        self.send_button.configure(state="disabled")

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
                self.send_button.configure(state="normal")
                continue

            self._append_log(message)

        self.after(100, self._drain_log_queue)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


if __name__ == "__main__":
    app = LLMResponseDebugger()
    app.mainloop()
