"""Wire-level helpers for the Sanctum JSON-RPC protocol.

Framing: 4-byte big-endian length prefix followed by a JSON payload.
"""

import json
import socket
import struct
from typing import Dict

from sanctum_ai.exceptions import VaultError, CODE_TO_EXCEPTION

MAX_MESSAGE_SIZE = 4 * 1024 * 1024  # 4 MiB


def send(sock: socket.socket, obj: dict) -> None:
    """Encode and send a length-prefixed JSON-RPC message."""
    payload = json.dumps(obj, separators=(",", ":")).encode()
    sock.sendall(struct.pack(">I", len(payload)) + payload)


def recv(sock: socket.socket) -> dict:
    """Read a length-prefixed JSON-RPC message from the socket."""
    length = struct.unpack(">I", _read_exact(sock, 4))[0]
    if length > MAX_MESSAGE_SIZE:
        raise VaultError("Response too large", code="INTERNAL_ERROR")
    return json.loads(_read_exact(sock, length))


def raise_on_error(resp: dict) -> None:
    """Inspect an RPC response and raise a typed exception on error."""
    err = resp.get("error")
    if err is None:
        return
    # Legacy string errors
    if isinstance(err, str):
        raise VaultError(err)
    # Structured errors
    code = err.get("code", "INTERNAL_ERROR")
    cls = CODE_TO_EXCEPTION.get(code, VaultError)
    raise cls(
        err.get("message", "Unknown error"),
        code=code,
        detail=err.get("detail"),
        suggestion=err.get("suggestion"),
        docs_url=err.get("docs_url"),
        context=err.get("context", {}),
    )


def encode_frame(obj: dict) -> bytes:
    """Encode a dict into a length-prefixed frame (useful for testing)."""
    payload = json.dumps(obj, separators=(",", ":")).encode()
    return struct.pack(">I", len(payload)) + payload


def decode_frame(data: bytes) -> tuple:
    """Decode a length-prefixed frame, returning (dict, remaining_bytes)."""
    if len(data) < 4:
        raise VaultError("Incomplete frame header", code="INTERNAL_ERROR")
    length = struct.unpack(">I", data[:4])[0]
    if len(data) < 4 + length:
        raise VaultError("Incomplete frame body", code="INTERNAL_ERROR")
    obj = json.loads(data[4 : 4 + length])
    return obj, data[4 + length :]


def _read_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise VaultError("Connection closed", code="INTERNAL_ERROR")
        buf.extend(chunk)
    return bytes(buf)
