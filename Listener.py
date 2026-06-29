"""TCP listener for external face-renderer commands.

This module deliberately does not import pygame or the face scene classes.
It receives newline-delimited JSON commands on a local TCP port and places
validated command dictionaries onto a thread-safe queue. The main pygame loop
should drain that queue and apply commands on the main thread.
"""

from __future__ import annotations

import json
import queue
import socket
import threading
from dataclasses import dataclass
from typing import Any


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 6001


CommandQueue = queue.Queue[dict[str, Any]]


@dataclass
class ListenerHandle:
    """Handle returned by start_listener so the caller can stop it cleanly."""

    thread: threading.Thread
    stop_event: threading.Event
    host: str
    port: int

    def stop(self) -> None:
        self.stop_event.set()

        # Nudge the blocking accept() call so the listener can notice stop_event.
        try:
            with socket.create_connection((self.host, self.port), timeout=0.2):
                pass
        except OSError:
            pass


def start_listener(
    command_queue: CommandQueue,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> ListenerHandle:
    """Start a background TCP server that enqueues newline-delimited JSON.

    Expected wire format:
        {"type": "expression", "name": "happy"}\n
        {"type": "speak", "syllables": [["a", 0.22], ["m", 0.12]]}\n

    The listener accepts one client at a time. If the client disconnects, the
    server keeps running and accepts the next connection.
    """

    stop_event = threading.Event()
    thread = threading.Thread(
        target=_run_server,
        args=(command_queue, host, port, stop_event),
        name="FaceCommandListener",
        daemon=True,
    )
    thread.start()
    return ListenerHandle(thread=thread, stop_event=stop_event, host=host, port=port)


def _run_server(
    command_queue: CommandQueue,
    host: str,
    port: int,
    stop_event: threading.Event,
) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(1)
        server.settimeout(0.5)

        print(f"Listener active on {host}:{port}")

        while not stop_event.is_set():
            try:
                client, address = server.accept()
            except socket.timeout:
                continue
            except OSError as exc:
                if not stop_event.is_set():
                    print(f"Listener accept error: {exc}")
                continue

            print(f"Listener connected: {address}")
            with client:
                _read_client(client, command_queue, stop_event)


def _read_client(
    client: socket.socket,
    command_queue: CommandQueue,
    stop_event: threading.Event,
) -> None:
    client.settimeout(0.5)
    buffer = ""

    while not stop_event.is_set():
        try:
            chunk = client.recv(4096)
        except socket.timeout:
            continue
        except OSError as exc:
            print(f"Listener client error: {exc}")
            return

        if not chunk:
            return

        buffer += chunk.decode("utf-8", errors="replace")

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            command = parse_command_line(line)

            if command is not None:
                command_queue.put(command)


def parse_command_line(line: str) -> dict[str, Any] | None:
    """Parse one JSON line into a minimally validated command dictionary."""

    line = line.strip()
    if not line:
        return None

    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        print(f"Listener ignored invalid JSON: {exc}")
        return None

    if not isinstance(payload, dict):
        print("Listener ignored non-object JSON payload")
        return None

    command_type = payload.get("type")
    if command_type not in {"expression", "speak", "stop_speech"}:
        print(f"Listener ignored unknown command type: {command_type}")
        return None

    return payload


def drain_commands(command_queue: CommandQueue) -> list[dict[str, Any]]:
    """Return all currently queued commands without blocking."""

    commands: list[dict[str, Any]] = []

    while True:
        try:
            commands.append(command_queue.get_nowait())
        except queue.Empty:
            return commands

