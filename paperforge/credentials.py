"""Python credential authority (#173 / C1, #138).

The sole credential provider.  Resolution precedence: explicit canonical
process environment → OS keyring → missing.  Keyring is the only durable
authority; there is NO plaintext fallback, no silent degrade, and no
process-global secret cache.  Legacy sources (.env, HKCU, legacy env names,
SecretStorage, plugin settings) are migration input only and are never
consulted by this module.

The seam is a small functional module per #138: no provider registry, no
URI references, no secret-returning CLI command.  ``keyring`` is imported
lazily; a canonical environment credential satisfies a request without ever
initializing the keyring backend (CI stays keyring-free).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, Protocol

SERVICE = "paperforge"

CredentialKind = Literal["ocr", "embedding"]

_PROFILE_RE_PARTS = ("[a-z][a-z0-9_]{0,63}")


@dataclass(frozen=True)
class CredentialKey:
    kind: CredentialKind
    profile: str = "default"

    def __post_init__(self) -> None:
        import re

        if self.kind not in ("ocr", "embedding"):
            raise ValueError(f"invalid credential kind: {self.kind!r}")
        if not re.fullmatch(_PROFILE_RE_PARTS, self.profile):
            raise ValueError(f"invalid credential profile: {self.profile!r}")

    @property
    def env_name(self) -> str:
        """Canonical explicit env var: PAPERFORGE_CREDENTIAL_<KIND>__<PROFILE>.

        Profile ids are lowercase/digit/underscore, so uppercasing is
        reversible and collision-free.
        """
        return f"PAPERFORGE_CREDENTIAL_{self.kind.upper()}__{self.profile.upper()}"

    @property
    def keyring_username(self) -> str:
        return f"{self.kind}:{self.profile}"

    @property
    def display(self) -> str:
        return f"{self.kind}:{self.profile}"


@dataclass(frozen=True)
class CredentialStatus:
    key: CredentialKey
    state: Literal[
        "available",
        "missing",
        "backend_unavailable",
        "backend_locked",
        "permission_denied",
        "backend_error",
    ]
    source: Literal["environment", "keyring"] | None = None
    backend: str | None = None
    remediation_code: str | None = None


class CredentialError(RuntimeError):
    """Typed credential failure with a stable code."""

    code: str
    details: dict[str, object]

    def __init__(self, code: str, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


MISSING = "credential.missing"
BACKEND_UNAVAILABLE = "credential.backend_unavailable"
BACKEND_LOCKED = "credential.backend_locked"
PERMISSION_DENIED = "credential.permission_denied"
BACKEND_ERROR = "credential.backend_error"
INPUT_REQUIRED = "credential.input_required"
CONFLICT = "credential.conflict"
INVALID_PROFILE = "credential.invalid_profile"

_REMEDIATION = {
    MISSING: "credential.set_required",
    BACKEND_UNAVAILABLE: "credential.backend_unavailable_remediation",
    BACKEND_LOCKED: "credential.backend_locked_remediation",
    PERMISSION_DENIED: "credential.permission_denied_remediation",
    BACKEND_ERROR: "credential.backend_error_remediation",
}

class _KeyringErrors(Protocol):
    PasswordDeleteError: type[BaseException]


class KeyringProtocol(Protocol):
    """The keyring surface C1 consumes (satisfied by the keyring package
    and by the in-memory test fake)."""

    errors: _KeyringErrors

    def get_password(self, service: str, username: str) -> str | None: ...
    def set_password(self, service: str, username: str, password: str) -> None: ...
    def delete_password(self, service: str, username: str) -> None: ...
    def get_keyring(self) -> object: ...


# Test seam (#138 §8): tests inject an in-memory fake keyring here.  When
# set, it is used INSTEAD of importing keyring.  Never shipped to production.
_keyring_override: KeyringProtocol | None = None

_keyring_module: KeyringProtocol | None = None  # lazy import cache


def _get_keyring() -> KeyringProtocol:
    """Lazily imported keyring backend wrapper (test seam respected)."""
    global _keyring_module
    if _keyring_override is not None:
        return _keyring_override
    if _keyring_module is None:
        # Test/deployment control: an explicitly set backend name wins.
        override = os.environ.get("PAPERFORGE_KEYRING_BACKEND")
        if override:
            os.environ["PYTHON_KEYRING_BACKEND"] = override
        import keyring as _kr

        _keyring_module = _kr  # type: ignore[assignment]  # satisfies the protocol
    return _keyring_module


def set_keyring_override(backend: KeyringProtocol | None) -> None:
    """Inject a fake keyring for tests; None restores production keyring."""
    global _keyring_override
    _keyring_override = backend


def env_value(key: CredentialKey, env: Mapping[str, str] | None = None) -> str:
    """Explicit canonical environment value for the key, or ""."""
    source = os.environ if env is None else env
    return str(source.get(key.env_name, "") or "").strip()


def _map_keyring_error(exc: BaseException, *, op: str) -> CredentialError:
    """Map a keyring exception to a stable PaperForge credential code."""
    name = type(exc).__name__.lower()
    message = str(exc)
    if (
        "backend unavailable" in name
        or "nosuchbackend" in message.lower()
        or "no recommended backend" in message.lower()
        or "no backend available" in message.lower()
    ):
        return CredentialError(BACKEND_UNAVAILABLE, f"no secure keyring backend ({op})")
    if "locked" in name or "unlock" in message.lower():
        return CredentialError(BACKEND_LOCKED, f"keyring is locked ({op})")
    if "permission" in name or "access denied" in message.lower() or "denied" in name:
        return CredentialError(PERMISSION_DENIED, f"keyring access denied ({op})")
    return CredentialError(BACKEND_ERROR, f"keyring {op} failed: {message}")


def resolve(
    key: CredentialKey,
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    """Return the secret from explicit environment or keyring.

    Raises CredentialError with a stable code; a value is never copied into
    the exception message, logs, or any structured result.
    """
    explicit = env_value(key, env)
    if explicit:
        return explicit
    try:
        kr = _get_keyring()
        value = kr.get_password(SERVICE, key.keyring_username)
    except CredentialError:
        raise
    except Exception as exc:  # noqa: BLE001 — keyring backend surface
        raise _map_keyring_error(exc, op="get") from exc
    if value is None or value == "":
        raise CredentialError(
            MISSING,
            f"no credential for {key.display} — set it or supply {key.env_name}",
        )
    return value


def store(
    key: CredentialKey,
    secret: str,
    *,
    replace: bool = False,
) -> None:
    """Write to keyring, read back, and restore/delete on verification failure.

    Refuses to replace an existing different value unless ``replace``.
    """
    if not secret:
        raise CredentialError(INPUT_REQUIRED, "empty secret rejected")
    try:
        kr = _get_keyring()
    except Exception as exc:  # noqa: BLE001
        raise _map_keyring_error(exc, op="backend") from exc
    try:
        existing = kr.get_password(SERVICE, key.keyring_username)
    except Exception as exc:  # noqa: BLE001
        raise _map_keyring_error(exc, op="read") from exc
    if existing is not None and existing != "" and existing != secret and not replace:
        raise CredentialError(
            CONFLICT,
            f"a different durable value exists for {key.display} — replace explicitly",
        )
    try:
        kr.set_password(SERVICE, key.keyring_username, secret)
        verified = kr.get_password(SERVICE, key.keyring_username)
    except Exception as exc:  # noqa: BLE001
        # #173 corrective: ANY failure after the write began must restore the
        # previous value (or delete the partial write when none existed) —
        # the write/verify phase is one transaction.  Restoration is best
        # effort; the primary contract is never returning success on an
        # unverified write and never leaving an unknown durable state.
        _restore_prior(kr, key, existing)
        raise _map_keyring_error(exc, op="write") from exc
    if verified != secret:
        _restore_prior(kr, key, existing)
        raise CredentialError(
            BACKEND_ERROR,
            f"keyring write verification failed for {key.display}",
        )


def _restore_prior(kr, key: CredentialKey, prior: str | None) -> None:
    """Restore the previous durable value; delete the partial write when
    there was none.  Best effort — restoration failure is logged nowhere
    sensitive and never masks the original error."""
    try:
        if prior is not None and prior != "":
            kr.set_password(SERVICE, key.keyring_username, prior)
        else:
            try:
                kr.delete_password(SERVICE, key.keyring_username)
            except kr.errors.PasswordDeleteError:
                pass
    except Exception:  # noqa: BLE001
        pass


def delete(key: CredentialKey) -> bool:
    """Delete the keyring entry; False when absent (idempotent at the API)."""
    try:
        kr = _get_keyring()
    except Exception as exc:  # noqa: BLE001
        raise _map_keyring_error(exc, op="backend") from exc
    try:
        kr.delete_password(SERVICE, key.keyring_username)
        return True
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, kr.errors.PasswordDeleteError):
            return False
        raise _map_keyring_error(exc, op="delete") from exc


def status(
    key: CredentialKey,
    *,
    env: Mapping[str, str] | None = None,
) -> CredentialStatus:
    """Report availability/source/backend without returning the value.

    ``status`` may retrieve a value into local memory (keyring has no
    presence-only operation) but returns only state/source/backend.
    """
    explicit = env_value(key, env)
    if explicit:
        return CredentialStatus(
            key=key, state="available", source="environment", backend=None,
            remediation_code=None,
        )
    try:
        kr = _get_keyring()
    except Exception as exc:  # noqa: BLE001
        error = _map_keyring_error(exc, op="backend")
        return _status_from_error(key, error)
    try:
        backend = str(getattr(kr, "get_keyring", lambda: None)())
    except Exception:  # noqa: BLE001
        backend = None
    try:
        value = kr.get_password(SERVICE, key.keyring_username)
    except Exception as exc:  # noqa: BLE001
        error = _map_keyring_error(exc, op="read")
        return _status_from_error(key, error)
    if value is None or value == "":
        return CredentialStatus(
            key=key, state="missing", source=None, backend=backend,
            remediation_code=_REMEDIATION[MISSING],
        )
    return CredentialStatus(
        key=key, state="available", source="keyring", backend=backend,
        remediation_code=None,
    )


def _status_from_error(key: CredentialKey, error: CredentialError) -> CredentialStatus:
    state: Literal[
        "available", "missing", "backend_unavailable", "backend_locked",
        "permission_denied", "backend_error",
    ] = {
        BACKEND_UNAVAILABLE: "backend_unavailable",
        BACKEND_LOCKED: "backend_locked",
        PERMISSION_DENIED: "permission_denied",
    }.get(error.code, "backend_error")
    return CredentialStatus(
        key=key, state=state, source=None, backend=None,
        remediation_code=_REMEDIATION.get(error.code),
    )
