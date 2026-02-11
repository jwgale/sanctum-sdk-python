# SanctumAI Python SDK

[![PyPI version](https://img.shields.io/pypi/v/sanctum-ai.svg)](https://pypi.org/project/sanctum-ai/)
[![Python](https://img.shields.io/pypi/pyversions/sanctum-ai.svg)](https://pypi.org/project/sanctum-ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Python SDK for [SanctumAI](https://github.com/jwgale/sanctum) — secure credential management for AI agents.

## Installation

```bash
pip install sanctum-ai
```

## Quick Start

```python
from sanctum_ai import SanctumClient

with SanctumClient("my-agent") as client:
    # Retrieve a credential
    api_key = client.retrieve("openai/api_key")

    # List available credentials
    creds = client.list()

    # Use-not-retrieve (credential never leaves the vault)
    result = client.use("openai/api_key", "http_header")
```

## Connecting

```python
# Unix socket (default: ~/.sanctum/vault.sock)
client = SanctumClient("my-agent")
client.connect()

# Custom socket path
client = SanctumClient("my-agent", socket_path="/tmp/sanctum.sock")
client.connect()

# TCP connection
client = SanctumClient("my-agent", host="127.0.0.1", port=8200)
client.connect()
```

## API Reference

### `SanctumClient(agent_name, *, socket_path=None, host=None, port=None, key_path=None, passphrase=None)`

Create a new client instance.

| Parameter | Description |
|---|---|
| `agent_name` | Agent identity for authentication |
| `socket_path` | Unix socket path (default: `~/.sanctum/vault.sock`) |
| `host` / `port` | TCP connection (alternative to socket) |
| `key_path` | Path to Ed25519 key file (default: `~/.sanctum/keys/{agent_name}.key`) |
| `passphrase` | Passphrase for encrypted `.key.enc` files |

### Methods

#### `connect(target=None) → SanctumClient`
Connect and authenticate. Optionally pass a socket path, `(host, port)` tuple, or `{"host": ..., "port": ...}` dict.

#### `retrieve(path, *, ttl=None) → str`
Retrieve a credential as a UTF-8 string. Lease is auto-tracked and released on `close()`.

#### `retrieve_raw(path, *, ttl=None) → dict`
Like `retrieve()` but returns the full result including `lease_id`, `ttl`, etc.

#### `list() → list`
List credentials the agent has access to.

#### `release_lease(lease_id) → None`
Explicitly release a credential lease.

#### `use(path, operation, params=None) → dict`
Use-not-retrieve pattern — execute an operation using a credential without exposing the secret.

#### `close() → None`
Release all tracked leases and disconnect.

### Exceptions

| Exception | Error Code | Description |
|---|---|---|
| `VaultError` | — | Base exception |
| `AuthError` | `AUTH_FAILED` | Authentication failed |
| `AccessDenied` | `ACCESS_DENIED` | Insufficient permissions |
| `CredentialNotFound` | `CREDENTIAL_NOT_FOUND` | Path doesn't exist |
| `VaultLocked` | `VAULT_LOCKED` | Vault is sealed |
| `LeaseExpired` | `LEASE_EXPIRED` | Lease timed out |
| `RateLimited` | `RATE_LIMITED` | Too many requests |
| `SessionExpired` | `SESSION_EXPIRED` | Re-authenticate needed |

All exceptions carry `.code`, `.detail`, `.suggestion`, `.docs_url`, and `.context` attributes.

## Protocol

The SDK communicates via JSON-RPC over Unix sockets or TCP with 4-byte big-endian length-prefix framing. Authentication uses Ed25519 challenge-response.

## License

MIT — see [LICENSE](LICENSE).

## Links

- **Main project:** [github.com/jwgale/sanctum](https://github.com/jwgale/sanctum)
- **Issues:** [github.com/jwgale/sanctum-sdk-python/issues](https://github.com/jwgale/sanctum-sdk-python/issues)
