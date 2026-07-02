from __future__ import annotations

import json
import socket
import time
from typing import Any


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 6001


def send_commands(
    commands: list[dict[str, Any]],
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    delay: float = 0.0,
) -> None:
    """Send commands to the listener as a simulated external client.

    This is intentionally client-side code. Use it from tests or debug tools,
    not from the listener server thread itself.
    """

    with socket.create_connection((host, port), timeout=2.0) as client:
        for command in commands:
            line = json.dumps(command) + "\n"
            client.sendall(line.encode("utf-8"))

            if delay > 0:
                time.sleep(delay)

