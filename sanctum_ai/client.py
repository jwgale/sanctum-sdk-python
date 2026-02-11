"""SanctumClient — the main entry point for AI agents to access Sanctum."""

import hashlib
import os
import socket
from typing import Any, Dict, List, Optional, Tuple, Union

from nacl.signing import SigningKey
from nacl.secret import SecretBox

from sanctum_ai.exceptions import AuthError, VaultError
from sanctum_ai.protocol import send, recv, raise_on_error


class SanctumClient:
    """Client for the Sanctum credential vault.

    Supports Unix socket and TCP connections, Ed25519 challenge-response
    authentication, credential retrieval with automatic lease tracking,
    and the use-not-retrieve pattern.

    Usage::

        with SanctumClient("my-agent") as client:
            secret = client.retrieve("openai/api_key")
            print(secret)
    """

    DEFAULT_SOCKET = "~/.sanctum/vault.sock"
    DEFAULT_KEY_DIR = "~/.sanctum/keys"

    def __init__(
        self,
        agent_name: str,
        *,
        socket_path: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        key_path: Optional[str] = None,
        passphrase: Optional[str] = None,
    ):
        self.agent_name = agent_name
        self._socket_path = socket_path
        self._host = host
        self._port = port
        self._key_path = key_path
        self._passphrase = passphrase
        self._sock: Optional[socket.socket] = None
        self._session_id: Optional[str] = None
        self._req_id = 0
        self._leases: List[str] = []

    # -- lifecycle ----------------------------------------------------------

    def connect(
        self,
        target: Optional[Union[str, Tuple[str, int], Dict[str, Any]]] = None,
    ) -> "SanctumClient":
        """Connect to the Sanctum daemon and authenticate.

        Args:
            target: Optional override — a Unix socket path (str), a
                ``(host, port)`` tuple, or a dict ``{"host": ..., "port": ...}``.
                If *None*, uses constructor parameters or the default socket.
        """
        if target is not None:
            if isinstance(target, str):
                self._socket_path = target
                self._host = None
            elif isinstance(target, dict):
                self._host = target["host"]
                self._port = target["port"]
                self._socket_path = None
            elif isinstance(target, (list, tuple)):
                self._host, self._port = target[0], target[1]
                self._socket_path = None

        if self._host and self._port:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.connect((self._host, self._port))
        else:
            path = os.path.expanduser(self._socket_path or self.DEFAULT_SOCKET)
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._sock.connect(path)

        self._authenticate()
        return self

    def close(self) -> None:
        """Release all tracked leases and disconnect."""
        for lid in list(self._leases):
            try:
                self.release_lease(lid)
            except VaultError:
                pass
        if self._sock:
            self._sock.close()
            self._sock = None
        self._session_id = None

    def __enter__(self) -> "SanctumClient":
        return self.connect()

    def __exit__(self, *exc: Any) -> bool:
        self.close()
        return False

    # -- RPC ----------------------------------------------------------------

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _call(self, method: str, params: dict) -> dict:
        if self._sock is None:
            raise VaultError("Not connected", code="INTERNAL_ERROR")
        send(self._sock, {"id": self._next_id(), "method": method, "params": params})
        resp = recv(self._sock)
        raise_on_error(resp)
        return resp.get("result", {})

    # -- auth ---------------------------------------------------------------

    def _resolve_key(self) -> SigningKey:
        if self._key_path:
            p = os.path.expanduser(self._key_path)
        else:
            base = os.path.expanduser(self.DEFAULT_KEY_DIR)
            enc = os.path.join(base, f"{self.agent_name}.key.enc")
            plain = os.path.join(base, f"{self.agent_name}.key")
            if os.path.exists(enc) and self._passphrase:
                return self._load_encrypted_key(enc, self._passphrase)
            p = plain
        return self._load_signing_key(p)

    @staticmethod
    def _load_signing_key(path: str) -> SigningKey:
        with open(path, "r") as f:
            raw = f.read().strip()
        seed = bytes.fromhex(raw)
        if len(seed) != 32:
            raise AuthError(
                f"Key file has {len(seed)} bytes, expected 32", code="AUTH_FAILED"
            )
        return SigningKey(seed)

    @staticmethod
    def _load_encrypted_key(path: str, passphrase: str) -> SigningKey:
        with open(path, "r") as f:
            blob = bytes.fromhex(f.read().strip())
        salt, nonce, ct = blob[:16], blob[16:40], blob[40:]
        dk = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 100_000, dklen=32)
        box = SecretBox(dk)
        seed = box.decrypt(ct, nonce)
        return SigningKey(seed)

    def _authenticate(self) -> None:
        sk = self._resolve_key()
        r = self._call("authenticate", {"agent_name": self.agent_name})
        self._session_id = r["session_id"]
        challenge = bytes.fromhex(r["challenge"])
        sig = sk.sign(challenge).signature
        r = self._call(
            "challenge_response",
            {"session_id": self._session_id, "signature": sig.hex()},
        )
        if not r.get("authenticated"):
            raise AuthError("Authentication not confirmed", code="AUTH_FAILED")

    # -- operations ---------------------------------------------------------

    def retrieve(self, path: str, *, ttl: Optional[int] = None) -> str:
        """Retrieve a credential value as a UTF-8 string.

        The lease is tracked and auto-released on :meth:`close`.
        """
        params: Dict[str, Any] = {"session_id": self._session_id, "path": path}
        if ttl is not None:
            params["ttl"] = ttl
        r = self._call("retrieve", params)
        self._leases.append(r["lease_id"])
        return bytes.fromhex(r["value"]).decode("utf-8", errors="replace")

    def retrieve_raw(self, path: str, *, ttl: Optional[int] = None) -> dict:
        """Like :meth:`retrieve` but returns the full result dict."""
        params: Dict[str, Any] = {"session_id": self._session_id, "path": path}
        if ttl is not None:
            params["ttl"] = ttl
        r = self._call("retrieve", params)
        self._leases.append(r["lease_id"])
        return r

    def list(self) -> list:
        """List credentials the agent has access to."""
        r = self._call("list", {"session_id": self._session_id})
        return r.get("credentials", [])

    def release_lease(self, lease_id: str) -> None:
        """Explicitly release a credential lease."""
        self._call("release_lease", {"lease_id": lease_id})
        if lease_id in self._leases:
            self._leases.remove(lease_id)

    def use(
        self,
        path: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Use-not-retrieve: execute an operation using a credential without exposing it.

        Args:
            path: Credential path (e.g. ``"openai/api_key"``).
            operation: Operation name (e.g. ``"http_header"``).
            params: Additional parameters for the operation.

        Returns:
            Result dict from the vault.
        """
        rpc_params: Dict[str, Any] = {
            "session_id": self._session_id,
            "path": path,
            "operation": operation,
        }
        if params:
            rpc_params["params"] = params
        return self._call("use", rpc_params)
