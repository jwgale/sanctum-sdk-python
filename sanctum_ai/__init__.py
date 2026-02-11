"""SanctumAI Python SDK — secure credential management for AI agents."""

from sanctum_ai.client import SanctumClient
from sanctum_ai.exceptions import (
    VaultError,
    AuthError,
    AccessDenied,
    CredentialNotFound,
    VaultLocked,
    LeaseExpired,
    RateLimited,
    SessionExpired,
)

__version__ = "0.1.0"

__all__ = [
    "SanctumClient",
    "VaultError",
    "AuthError",
    "AccessDenied",
    "CredentialNotFound",
    "VaultLocked",
    "LeaseExpired",
    "RateLimited",
    "SessionExpired",
    "__version__",
]
