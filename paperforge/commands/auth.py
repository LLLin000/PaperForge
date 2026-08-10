"""`paperforge auth` — credential authority CLI (#173 / C1, #138).

status / set / delete / migrate.  Secrets are NEVER accepted as argv and
never echoed; `auth set` reads getpass (TTY) or stdin (--stdin).  Legacy
sources are migration input only — `auth migrate` reads them once, verifies
the keyring write, then scrubs or guides deletion; no runtime fallback.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.credentials import (
    MISSING,
    CredentialError,
    CredentialKey,
    delete as credential_delete,
    resolve,
    status as credential_status,
    store as credential_store,
)

# Legacy source names accepted ONLY by explicit migration.
LEGACY_OCR_NAMES = ("PADDLEOCR_API_TOKEN", "PADDLEOCR_API_KEY", "OCR_TOKEN")
LEGACY_EMBEDDING_NAMES = ("VECTOR_DB_API_KEY", "OPENAI_API_KEY")
LEGACY_NAMES = LEGACY_OCR_NAMES + LEGACY_EMBEDDING_NAMES


def _parse_key(args: argparse.Namespace) -> CredentialKey:
    return CredentialKey(
        kind=args.kind,
        profile=getattr(args, "profile", None) or "default",
    )


_CODE_MAP = {
    "credential.missing": ErrorCode.CREDENTIAL_MISSING,
    "credential.backend_unavailable": ErrorCode.CREDENTIAL_BACKEND_UNAVAILABLE,
    "credential.backend_locked": ErrorCode.CREDENTIAL_BACKEND_LOCKED,
    "credential.permission_denied": ErrorCode.CREDENTIAL_PERMISSION_DENIED,
    "credential.backend_error": ErrorCode.CREDENTIAL_BACKEND_ERROR,
    "credential.input_required": ErrorCode.CREDENTIAL_INPUT_REQUIRED,
    "credential.conflict": ErrorCode.CREDENTIAL_CONFLICT,
    "credential.invalid_profile": ErrorCode.CREDENTIAL_INVALID_PROFILE,
    "credential.confirm_required": ErrorCode.CREDENTIAL_CONFIRM_REQUIRED,
}


def _error_result(command: str, error: CredentialError) -> PFResult:
    return PFResult(
        ok=False,
        command=command,
        version=PF_VERSION,
        error=PFError(
            code=_CODE_MAP.get(error.code, ErrorCode.INTERNAL_ERROR),
            message=str(error),
            details=error.details,
        ),
    )


# ── status ────────────────────────────────────────────────────────────────

def _status_data(key: CredentialKey) -> dict[str, Any]:
    st = credential_status(key)
    return {
        "kind": key.kind,
        "profile": key.profile,
        "state": st.state,
        "source": st.source,
        "backend": st.backend,
        "remediation_code": st.remediation_code,
    }


def run_status(args: argparse.Namespace) -> int:
    """`auth status [KIND] [--profile]` — checks one key, or the vault's
    credential profiles when KIND is omitted."""
    json_output = bool(getattr(args, "json", False))

    if getattr(args, "kind", None):
        key = _parse_key(args)
        credentials = [_status_data(key)]
    else:
        # Vault credential profiles: OCR + embedding default profiles.
        credentials = [_status_data(CredentialKey("ocr")), _status_data(CredentialKey("embedding"))]
    data = {"schema_version": 1, "credentials": credentials}

    result = PFResult(ok=True, command="auth.status", version=PF_VERSION, data=data)
    if json_output:
        print(result.to_json())
    else:
        for cred in credentials:
            print(
                f"{cred['kind']}:{cred['profile']}  {cred['state']}"
                + (f"  ({cred['source']})" if cred["source"] else "")
            )
    return 0


# ── set ───────────────────────────────────────────────────────────────────

def _read_secret(args: argparse.Namespace) -> str:
    """Secret input: getpass on TTY, --stdin otherwise.  Never argv."""
    if getattr(args, "stdin", False):
        secret = sys.stdin.read()
        if secret.endswith("\n"):
            secret = secret[:-1]
        if secret.endswith("\r"):
            secret = secret[:-1]
    else:
        import getpass

        secret = getpass.getpass(f"Secret for {_parse_key(args).display}: ")
    return secret


def run_set(args: argparse.Namespace) -> int:
    """`auth set KIND [--profile] [--stdin] [--replace]` — keyring write with
    read-back verification; never argv."""
    json_output = bool(getattr(args, "json", False))
    key = _parse_key(args)
    try:
        secret = _read_secret(args)
        if not secret:
            raise CredentialError(MISSING.replace("missing", "input_required"), "empty secret rejected")
    except CredentialError as error:
        result = _error_result("auth.set", error)
        if json_output:
            print(result.to_json())
        else:
            print(result.error.message if result.error else "", file=sys.stderr)
        return 1

    try:
        credential_store(key, secret, replace=bool(getattr(args, "replace", False)))
    except CredentialError as error:
        result = _error_result("auth.set", error)
        if json_output:
            print(result.to_json())
        else:
            print(result.error.message if result.error else "", file=sys.stderr)
        return 1

    st = credential_status(key)
    data = {
        "schema_version": 1,
        "kind": key.kind,
        "profile": key.profile,
        "state": st.state,
        "source": st.source,
    }
    result = PFResult(ok=True, command="auth.set", version=PF_VERSION, data=data)
    if json_output:
        print(result.to_json())
    else:
        print(f"{key.display}: stored ({st.source})")
    return 0


# ── delete ────────────────────────────────────────────────────────────────

def run_delete(args: argparse.Namespace) -> int:
    """`auth delete KIND [--profile] --yes` — keyring entry only."""
    json_output = bool(getattr(args, "json", False))
    key = _parse_key(args)

    if not getattr(args, "yes", False):
        result = PFResult(
            ok=False,
            command="auth.delete",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.CREDENTIAL_CONFIRM_REQUIRED,
                message="confirm with --yes",
                details={},
            ),
        )
        if json_output:
            print(result.to_json())
        else:
            print(result.error.message if result.error else "", file=sys.stderr)
        return 2

    from paperforge.credentials import env_value

    env_override = bool(env_value(key))
    try:
        deleted = credential_delete(key)
    except CredentialError as error:
        result = _error_result("auth.delete", error)
        if json_output:
            print(result.to_json())
        else:
            print(result.error.message if result.error else "", file=sys.stderr)
        return 1

    warnings: list[str] = []
    if env_override:
        warnings.append(
            f"{key.env_name} is still set in the environment — resolution "
            "remains environment-backed; unset it to fully remove the credential"
        )
    data = {
        "schema_version": 1,
        "kind": key.kind,
        "profile": key.profile,
        "deleted": deleted,
        "environment_override_present": env_override,
    }
    result = PFResult(ok=True, command="auth.delete", version=PF_VERSION, data=data, warnings=warnings)
    if json_output:
        print(result.to_json())
    else:
        print(f"{key.display}: {'deleted' if deleted else 'no keyring entry'}")
        for warning in warnings:
            print(f"[WARN] {warning}")
    return 0


# ── migrate ───────────────────────────────────────────────────────────────

def _dotenv_values(path: Path) -> dict[str, str]:
    """Parse a .env file into {name: value} (no interpolation, no expansion)."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name:
            out[name] = value
    return out


def _scrub_dotenv_key(path: Path, name: str) -> bool:
    """Atomically remove one secret assignment from a .env file."""
    if not path.exists():
        return False
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    kept = [line for line in lines if not line.lstrip().startswith(name + "=")]
    if len(kept) == len(lines):
        return False
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    os.replace(tmp, path)
    return True


def _discover_sources(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Discover legacy credential sources for the requested origin."""
    source = args.source
    entries: list[dict[str, Any]] = []

    if source == "dotenv":
        vault: Path = args.vault_path
        candidates = [
            vault / ".env",
            vault / "System" / "PaperForge" / ".env",
        ]
        for path in candidates:
            values = _dotenv_values(path)
            for name, value in values.items():
                if name in LEGACY_NAMES:
                    entries.append({"origin": "dotenv", "path": str(path), "name": name, "value": value})
    elif source == "environment":
        for name in LEGACY_NAMES:
            value = os.environ.get(name, "")
            if value:
                entries.append({"origin": "environment", "path": None, "name": name, "value": value})
    elif source == "windows-registry":
        import sys as _sys

        if _sys.platform != "win32":
            return entries
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as env_key:
                for name in LEGACY_NAMES:
                    try:
                        value, _ = winreg.QueryValueEx(env_key, name)
                    except OSError:
                        continue
                    if value:
                        entries.append({"origin": "windows-registry", "path": None, "name": name, "value": str(value)})
        except Exception:
            return entries
    return entries


def _target_key_for(name: str, args: argparse.Namespace) -> CredentialKey:
    """Legacy name → credential key; explicit KIND/PROFILE overrides."""
    if getattr(args, "kind", None):
        return _parse_key(args)
    if name in LEGACY_OCR_NAMES:
        return CredentialKey("ocr")
    return CredentialKey("embedding")


def run_migrate(args: argparse.Namespace) -> int:
    """`auth migrate --from dotenv|environment|windows-registry [--dry-run] [--replace]`.

    Reads legacy sources ONCE, stores with read-back verification, then
    scrubs what PaperForge can safely mutate (.env); environment and HKCU
    return exact manual-deletion identifiers instead of being silently
    deleted.  Legacy sources never become runtime fallbacks.
    """
    json_output = bool(getattr(args, "json", False))
    dry_run = bool(getattr(args, "dry_run", False))
    replace = bool(getattr(args, "replace", False))

    entries = _discover_sources(args)
    migrated: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    cleanup_pending: list[dict[str, Any]] = []
    manual: list[str] = []

    for entry in entries:
        key = _target_key_for(entry["name"], args)
        record = {
            "origin": entry["origin"],
            "source_name": entry["name"],
            "target": key.display,
        }
        if dry_run:
            migrated.append(record)
            continue

        existing = None
        try:
            existing = resolve(key)
        except CredentialError as error:
            if error.code != MISSING:
                result = _error_result("auth.migrate", error)
                if json_output:
                    print(result.to_json())
                else:
                    print(result.error.message if result.error else "", file=sys.stderr)
                return 1
        if existing is not None and existing != entry["value"] and not replace:
            conflicts.append({**record, "reason": "different durable value exists"})
            continue

        try:
            credential_store(key, entry["value"], replace=replace or existing is not None)
        except CredentialError as error:
            result = _error_result("auth.migrate", error)
            if json_output:
                print(result.to_json())
            else:
                print(result.error.message if result.error else "", file=sys.stderr)
            return 1

        record["verified"] = True
        migrated.append(record)

        # Scrub the source AFTER verified storage.
        if entry["origin"] == "dotenv":
            scrubbed = _scrub_dotenv_key(Path(entry["path"]), entry["name"])
            if not scrubbed:
                cleanup_pending.append({**record, "reason": "dotenv write-back failed"})
        else:
            # Environment and HKCU are never silently deleted.
            manual.append(f"{entry['origin']}:{entry['name']}")

    data = {
        "schema_version": 1,
        "source": args.source,
        "dry_run": dry_run,
        "migrated": migrated,
        "conflicts": conflicts,
        "cleanup_pending": cleanup_pending,
        "manual_cleanup": manual,
    }
    ok = dry_run or not conflicts
    result = PFResult(ok=ok, command="auth.migrate", version=PF_VERSION, data=data)
    if json_output:
        print(result.to_json())
    else:
        for item in migrated:
            print(f"{item['origin']}:{item['source_name']} -> {item['target']} {'(dry-run)' if dry_run else ''}")
        for item in conflicts:
            print(f"[CONFLICT] {item['origin']}:{item['source_name']} ({item['reason']})")
        for name in manual:
            print(f"[MANUAL] remove {name}")
        for item in cleanup_pending:
            print(f"[CLEANUP-PENDING] {item['origin']}:{item['source_name']} ({item['reason']})")
    return 0 if ok else 1


# ── dispatch ──────────────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> int:
    verb = args.auth_verb
    if verb == "status":
        return run_status(args)
    if verb == "set":
        return run_set(args)
    if verb == "delete":
        return run_delete(args)
    if verb == "migrate":
        return run_migrate(args)
    print(f"Error: unsupported auth verb '{verb}'", file=sys.stderr)
    return 2
