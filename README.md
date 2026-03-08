# SanctumAI Python SDK

[![PyPI version](https://img.shields.io/pypi/v/sanctum-ai.svg)](https://pypi.org/project/sanctum-ai/)
[![Python](https://img.shields.io/pypi/pyversions/sanctum-ai.svg)](https://pypi.org/project/sanctum-ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Python SDK for [SanctumAI](https://github.com/SanctumSec/sanctum) — a local-first credential vault for AI agents.

Your agent authenticates with the vault, then uses credentials *without ever seeing them*. Keys never enter agent memory.

## Install

```bash
pip install sanctum-ai
```

Requires Python 3.9+.

## Quick Start

```python
from sanctum_ai import SanctumClient

with SanctumClient("my-agent") as client:
    # Make an API call — agent never sees the key
    response = client.use_credential("openai/api-key", "http_request", {
        "method": "POST",
        "url": "https://api.openai.com/v1/chat/completions",
        "headers": {"Content-Type": "application/json"},
        "body": '{"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}',
        "header_type": "bearer",
    })
    print(response["status"])   # 200
    print(response["body"])     # {"choices": [...]}
```

The agent sent a request through the vault. The API key was injected server-side — it never existed in your process.

## Use Don't Retrieve

This is the core idea. Instead of retrieving a secret and using it yourself, you tell the vault *what to do* with the secret. The vault does it and returns the result.

### Proxy an HTTP Request

The most common operation. The vault injects the credential into the request and makes it on your behalf:

```python
# Call any API through the vault
result = client.use_credential("openai/api-key", "http_request", {
    "method": "POST",
    "url": "https://api.openai.com/v1/chat/completions",
    "headers": {"Content-Type": "application/json"},
    "body": '{"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}',
    "header_type": "bearer",  # bearer | api_key | basic | custom
})
# Returns: {"status": 200, "headers": {...}, "body": "..."}
```

Supported `header_type` values:

| Type | Header |
|---|---|
| `bearer` | `Authorization: Bearer <secret>` |
| `api_key` | `X-API-Key: <secret>` |
| `basic` | `Authorization: Basic <base64>` |
| `custom` | You specify the header name via `header_name` param |

### Get an HTTP Header

If you need to make the request yourself (e.g., streaming), get just the header:

```python
result = client.use_credential("github/token", "http_header", {
    "header_type": "bearer",
})
# Returns: {"header_name": "Authorization", "header_value": "Bearer ghp_..."}

# Use it in your own request
import urllib.request
req = urllib.request.Request("https://api.github.com/user")
req.add_header(result["header_name"], result["header_value"])
```

### Sign Data

HMAC-sign a payload without exposing the signing key:

```python
result = client.use_credential("webhook/secret", "sign", {
    "algorithm": "hmac-sha256",
    "data": "payload-to-sign",
})
# Returns: {"signature": "base64-encoded-signature"}
```

### Encrypt and Decrypt

```python
# Encrypt
encrypted = client.use_credential("encryption/key", "encrypt", {
    "data": "sensitive data",
})
# Returns: {"ciphertext": "..."}

# Decrypt
decrypted = client.use_credential("encryption/key", "decrypt", {
    "data": encrypted["ciphertext"],
})
# Returns: {"plaintext": "sensitive data"}
```

### When to Use `retrieve` Instead

Sometimes you need the raw secret (e.g., passing it to a library that manages its own connections). That's fine — `retrieve` is still available:

```python
api_key = client.retrieve("openai/api-key")
# Lease is auto-tracked and released when the client closes
```

But prefer `use_credential` whenever possible. It's safer.

## Connecting

```python
# Unix socket (default: ~/.sanctum/vault.sock)
with SanctumClient("my-agent") as client:
    ...

# TCP connection
with SanctumClient("my-agent", host="127.0.0.1", port=7600) as client:
    ...

# Custom socket path
with SanctumClient("my-agent", socket_path="/tmp/sanctum.sock") as client:
    ...

# Manual connect/close
client = SanctumClient("my-agent", host="127.0.0.1", port=7600)
client.connect()
# ... do work ...
client.close()
```

The client authenticates automatically on connect using Ed25519 challenge-response. Keys are loaded from `~/.sanctum/keys/<agent_name>.key` by default, or specify `key_path` explicitly.

## API Reference

### `SanctumClient(agent_name, *, socket_path=None, host=None, port=None, key_path=None, passphrase=None)`

| Parameter | Description |
|---|---|
| `agent_name` | Agent identity for authentication |
| `socket_path` | Unix socket path (default: `~/.sanctum/vault.sock`) |
| `host` / `port` | TCP connection (default port: `7600`) |
| `key_path` | Path to Ed25519 key file (default: `~/.sanctum/keys/{agent_name}.key`) |
| `passphrase` | Passphrase for encrypted `.key.enc` files |

### Methods

| Method | Returns | Description |
|---|---|---|
| `connect(target=None)` | `SanctumClient` | Connect and authenticate |
| `use_credential(path, operation, params=None)` | `dict` | Use a credential without seeing it |
| `retrieve(path, *, ttl=None)` | `str` | Retrieve credential value (lease auto-tracked) |
| `retrieve_raw(path, *, ttl=None)` | `dict` | Full result with `lease_id`, `ttl`, etc. |
| `list()` | `list` | List accessible credentials |
| `release_lease(lease_id)` | `None` | Explicitly release a lease |
| `close()` | `None` | Release all leases and disconnect |

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
        result = client.use_credential("openai/api-key", "http_request", {
            "method": "POST",
            "url": "https://api.openai.com/v1/chat/completions",
            "headers": {"Content-Type": "application/json"},
            "body": '{"model": "gpt-4", "messages": [{"role": "user", "content": "Hi"}]}',
            "header_type": "bearer",
        })
    except AccessDenied as e:
        print(f"No access: {e.detail}")
        print(f"Suggestion: {e.suggestion}")
    except CredentialNotFound:
        print("Credential path not found")
    except AuthError:
        print("Authentication failed — check your Ed25519 key")
    except VaultLocked:
        print("Vault is sealed — an operator needs to unseal it")
    except VaultError as e:
        print(f"[{e.code}] {e.detail}")
```

### Exception Reference

| Exception | Error Code | When |
|---|---|---|
| `VaultError` | — | Base exception |
| `AuthError` | `AUTH_FAILED` | Bad key or agent not registered |
| `AccessDenied` | `ACCESS_DENIED` | Agent lacks permission for this credential |
| `CredentialNotFound` | `CREDENTIAL_NOT_FOUND` | Path doesn't exist in the vault |
| `VaultLocked` | `VAULT_LOCKED` | Vault is sealed |
| `LeaseExpired` | `LEASE_EXPIRED` | Lease timed out |
| `RateLimited` | `RATE_LIMITED` | Too many requests |
| `SessionExpired` | `SESSION_EXPIRED` | Re-authenticate needed |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Submit a pull request

## License

MIT — see [LICENSE](LICENSE).

## Links

- [SanctumAI](https://github.com/SanctumSec/sanctum) — main project
- [Node.js SDK](https://github.com/SanctumSec/sanctum-sdk-node)
- [Rust SDK](https://github.com/SanctumSec/sanctum-sdk-rust)
- [Go SDK](https://github.com/SanctumSec/sanctum-sdk-go)
- [Issues](https://github.com/SanctumSec/sanctum-sdk-python/issues)
