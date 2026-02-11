"""Typed exceptions for SanctumAI SDK."""

from typing import Any, Dict, Optional


class VaultError(Exception):
    """Base exception. Carries structured error fields when available."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "UNKNOWN",
        detail: Optional[str] = None,
        suggestion: Optional[str] = None,
        docs_url: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.detail = detail
        self.suggestion = suggestion
        self.docs_url = docs_url
        self.context = context or {}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, msg={str(self)!r})"


class AuthError(VaultError):
    """Authentication failed."""


class AccessDenied(VaultError):
    """Agent lacks permission for the requested credential."""


class CredentialNotFound(VaultError):
    """Requested credential path does not exist."""


class VaultLocked(VaultError):
    """Vault is locked and cannot serve credentials."""


class LeaseExpired(VaultError):
    """Credential lease has expired."""


class RateLimited(VaultError):
    """Too many requests."""


class SessionExpired(VaultError):
    """Session has expired; re-authenticate."""


CODE_TO_EXCEPTION = {
    "AUTH_FAILED": AuthError,
    "ACCESS_DENIED": AccessDenied,
    "CREDENTIAL_NOT_FOUND": CredentialNotFound,
    "VAULT_LOCKED": VaultLocked,
    "LEASE_EXPIRED": LeaseExpired,
    "RATE_LIMITED": RateLimited,
    "SESSION_EXPIRED": SessionExpired,
}
