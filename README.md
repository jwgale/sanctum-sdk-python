# SanctumAI Python SDK

[![PyPI version](https://img.shields.io/pypi/v/sanctum-ai.svg)](https://pypi.org/project/sanctum-ai/)
[![Python](https://img.shields.io/pypi/pyversions/sanctum-ai.svg)](https://pypi.org/project/sanctum-ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/jwgale/sanctum-sdk-python/actions/workflows/ci.yml/badge.svg)](https://github.com/jwgale/sanctum-sdk-python/actions/workflows/ci.yml)

> Part of the [SanctumAI](https://github.com/jwgale/sanctum) ecosystem — secure credential management for AI agents.

Python SDK for interacting with a SanctumAI vault. Supports Unix sockets and TCP, Ed25519 authentication, automatic lease tracking, and the **use-not-retrieve** pattern.

## Installation

```bash
pip install sanctum-ai
```

Requires **Python 3.9+**.

## Quick Start

```python
from sanctum_ai import SanctumClient

with SanctumClient("my-agent") as client:
    # List available credentials
    for cred in client.list():
        print(f"  {cred.path} (tags: {cred.tags})")

    # Retrieve a credential (lease auto-tracked, released on close)
    api_key = client.retrieve("openai/api_key")
    print(f"Key starts with: {api_key[:8]}...")

    # Use-not-retrieve — credential never leaves the vault
    result = client.use("openai/api_key", "http_header")
    # result["header"] → "Authorization: Bearer sk-..."
    # The secret was used server-side; your process never saw it.
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

## Use-Not-Retrieve

The **use-not-retrieve** pattern lets agents perform operations that require a credential without ever exposing the secret to the agent process. The vault executes the operation server-side and returns only the result.

```python
# Sign a request — private key never leaves the vault
signed = client.use("signing/key", "sign_payload", {"payload": "data-to-sign"})

# Inject as HTTP header — agent never sees the raw token
header = client.use("openai/api_key", "http_header")

# Encrypt data — encryption key stays in the vault
encrypted = client.use("encryption/key", "encrypt", {"plaintext": "sensitive data"})
```

This is the recommended pattern for production agents. It minimizes the blast radius if an agent is compromised — secrets never exist in agent memory.

## Error Handling

All exceptions inherit from `VaultError` and carry structured context:

```python
from sanctum_ai import SanctumClient
from sanctum_ai.exceptions import (
    VaultError, AuthError, AccessDenied,
    CredentialNotFound, VaultLocked, LeaseExpired,
    RateLimited, SessionExpired,
)

with SanctumClient("my-agent") as client:
    try:
        secret = client.retrieve("openai/api_key")
    except AccessDenied as e:
        print(f"No access: {e.detail}")
        print(f"Suggestion: {e.suggestion}")
    except CredentialNotFound as e:
        print(f"Path not found: {e.detail}")
    except AuthError:
        print("Authentication failed — check your Ed25519 key")
    except VaultLocked:
        print("Vault is sealed — an operator needs to unseal it")
    except VaultError as e:
        # Catch-all for any vault error
        print(f"[{e.code}] {e.detail}")
        if e.docs_url:
            print(f"Docs: {e.docs_url}")
```

### Exception Reference

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

| Method | Returns | Description |
|---|---|---|
| `connect(target=None)` | `SanctumClient` | Connect and authenticate |
| `retrieve(path, *, ttl=None)` | `str` | Retrieve credential (lease auto-tracked) |
| `retrieve_raw(path, *, ttl=None)` | `dict` | Full result with `lease_id`, `ttl`, etc. |
| `list()` | `list` | List accessible credentials |
| `release_lease(lease_id)` | `None` | Explicitly release a lease |
| `use(path, operation, params=None)` | `dict` | Use-not-retrieve operation |
| `close()` | `None` | Release all leases and disconnect |

## Protocol

The SDK communicates via JSON-RPC over Unix sockets or TCP with 4-byte big-endian length-prefix framing. Authentication uses Ed25519 challenge-response.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

MIT — see [LICENSE](LICENSE).

## Links

- 🏠 **Main project:** [github.com/jwgale/sanctum](https://github.com/jwgale/sanctum)
- 🌐 **Website:** [sanctumai.dev](https://sanctumai.dev)
- 📦 **Node.js SDK:** [sanctum-sdk-node](https://github.com/jwgale/sanctum-sdk-node)
- 🦀 **Rust SDK:** [sanctum-sdk-rust](https://github.com/jwgale/sanctum-sdk-rust)
- 🐹 **Go SDK:** [sanctum-sdk-go](https://github.com/jwgale/sanctum-sdk-go)
- 🐛 **Issues:** [github.com/jwgale/sanctum-sdk-python/issues](https://github.com/jwgale/sanctum-sdk-python/issues)
