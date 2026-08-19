"""PaperForge — canonical configuration authority (#142 / C0).

Python is the ONLY parser, validator, resolver, and writer of
``paperforge.json``.  All consumers use this module or the
``paperforge config`` CLI adapter.

Resolution order (fixed):

    built-in default < canonical paperforge.json < process environment < explicit invocation override

Fail-closed contract:

    - missing / corrupt / legacy (migration_required) / future_schema / invalid
      files are never interpreted by domain commands;
    - secret-like fields are refused (owned by #138 / C1);
    - unknown non-secret fields are preserved on mutation but never cross the wire.

One atomic writer primitive backs ``config set/unset/init/migrate`` (filelock +
re-read + validate + temp + fsync + os.replace + read-back).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from filelock import FileLock, Timeout

SCHEMA_VERSION = 2
CONFIG_FILE = "paperforge.json"
LOCK_FILE = "paperforge.json.lock"
LOCK_TIMEOUT_SECONDS = 5.0

PAPERFORGE_VAULT_ENV = "PAPERFORGE_VAULT"

_SECRET_KEY_PARTS = ("api_key", "api_token", "token", "password", "secret")

# Single source of truth for the agent-platform vocabulary.  Only the ID
# list is code-owned (CLI choices, canonical config choices).  The skill
# TARGET directory is NOT routed per platform anymore: agents deploy the
# skill themselves with `paperforge skill deploy --to <dir>` (they know
# which harness they run in, e.g. .omp/skills, .agents/skills).  The shared
# cross-agent dir is the default target.
#
# Research (2026-08-19): .agents/skills is the agentskills.io/AAIF open
# standard, natively read by Claude Code (>= v2.1.121), Codex, OpenCode,
# Cursor, Gemini CLI, Kilo, Crush, Kimi-cli, and Oh My Pi/Pi.  Platforms
# with their own dirs (GitHub Copilot, Cline, Windsurf) or harness-native
# dirs (.omp/skills) simply pass --to.
AGENT_SHARED_SKILL_DIR = ".agents/skills"
AGENT_PLATFORM_IDS = (
    "opencode", "claude", "codex", "cursor", "gemini", "kilo",
    "pi", "omp", "crush", "kimi", "github_copilot", "cline",
    "windsurf", "augment", "trae",
)
_VALID_AGENT_PLATFORMS = AGENT_PLATFORM_IDS
_VALID_PROVIDER_TYPES = ("openai_sdk", "requests")

LEGACY_PATH_KEYS = (
    "system_dir", "resources_dir", "literature_dir", "control_dir",
    "base_dir", "skill_dir", "command_dir",
)
_DERIVED_LEGACY_FIELDS = ("paperforge_path", "zotero_link")


# ---------------------------------------------------------------------------
# Field vocabulary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FieldSpec:
    """One canonical user field. Data for loader, validator, CLI, and plugin
    presentation adapter — not an extension registry."""

    key: str
    storage_path: tuple[str, ...]
    value_type: Literal["string", "boolean", "enum", "path"]
    default: str | bool
    env: str | None = None
    choices: tuple[str, ...] = ()
    writable: bool = True
    allow_empty: bool = False
    vault_relative: bool = False


FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec("system_dir", ("vault_config", "system_dir"), "path", "System",
              env="PAPERFORGE_SYSTEM_DIR", vault_relative=True),
    FieldSpec("resources_dir", ("vault_config", "resources_dir"), "path", "Resources",
              env="PAPERFORGE_RESOURCES_DIR", vault_relative=True),
    FieldSpec("literature_dir", ("vault_config", "literature_dir"), "path", "Literature",
              env="PAPERFORGE_LITERATURE_DIR", vault_relative=True),
    FieldSpec("control_dir", ("vault_config", "control_dir"), "path", "LiteratureControl",
              env="PAPERFORGE_CONTROL_DIR", vault_relative=True),
    FieldSpec("base_dir", ("vault_config", "base_dir"), "path", "Bases",
              env="PAPERFORGE_BASE_DIR", vault_relative=True),
    FieldSpec("skill_dir", ("vault_config", "skill_dir"), "path", ".agents/skills",
              env="PAPERFORGE_SKILL_DIR", vault_relative=True),
    FieldSpec("command_dir", ("vault_config", "command_dir"), "path", ".opencode/command",
              env="PAPERFORGE_COMMAND_DIR", vault_relative=True),
    FieldSpec("zotero_data_dir", ("zotero_data_dir",), "path", "",
              env="ZOTERO_DATA_DIR", allow_empty=True),
    FieldSpec("agent_platform", ("agent_platform",), "enum", "opencode",
              env="PAPERFORGE_AGENT_PLATFORM", choices=_VALID_AGENT_PLATFORMS),
    FieldSpec("auto_analyze_after_ocr", ("auto_analyze_after_ocr",), "boolean", False),
    FieldSpec("ocr_profile", ("ocr_profile",), "string", "default",
              env="PAPERFORGE_OCR_PROFILE"),
    FieldSpec("paddleocr_job_url", ("paddleocr_job_url",), "string",
              "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
              env="PADDLEOCR_JOB_URL"),
    FieldSpec("paddleocr_model", ("paddleocr_model",), "string", "PaddleOCR-VL-1.6",
              env="PADDLEOCR_MODEL"),
    FieldSpec("embedding_profile", ("embedding_profile",), "string", "default",
              env="PAPERFORGE_EMBEDDING_PROFILE"),
    FieldSpec("vector_db_provider_type", ("vector_db_provider_type",), "enum", "openai_sdk",
              env="VECTOR_DB_PROVIDER_TYPE", choices=_VALID_PROVIDER_TYPES),
    FieldSpec("vector_db_api_base", ("vector_db_api_base",), "string", "",
              env="VECTOR_DB_API_BASE", allow_empty=True),
    FieldSpec("vector_db_api_model", ("vector_db_api_model",), "string", "text-embedding-3-small",
              env="VECTOR_DB_API_MODEL"),
)

FIELD_BY_KEY: dict[str, FieldSpec] = {spec.key: spec for spec in FIELD_SPECS}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ConfigError(Exception):
    """Stable, code-addressed configuration error (#142 §6)."""

    code: str
    details: Mapping[str, object]

    def __init__(self, code: str, details: Mapping[str, object] | None = None):
        super().__init__(code)
        self.code = code
        self.details: Mapping[str, object] = details or {}


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------

SOURCE_DEFAULT = "default"
SOURCE_FILE = "file"
SOURCE_ENVIRONMENT = "environment"
SOURCE_OVERRIDE = "override"


@dataclass(frozen=True)
class ConfigValue:
    key: str
    value: str | bool
    stored_value: str | bool | None
    source: str
    is_set: bool
    spec: FieldSpec


@dataclass(frozen=True)
class ConfigSnapshot:
    schema_version: int
    revision: str
    values: Mapping[str, ConfigValue]
    unknown_keys: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ConfigValidation:
    state: Literal["valid", "missing", "migration_required", "invalid", "future_schema"]
    revision: str | None
    errors: tuple[dict[str, object], ...]
    warnings: tuple[dict[str, object], ...]
    migration: dict[str, object] | None = None


@dataclass(frozen=True)
class MutationResult:
    changed: bool
    snapshot: ConfigSnapshot
    warnings: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Document I/O (strict reads + the one atomic writer)
# ---------------------------------------------------------------------------

def _read_document(path: Path) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """Strictly read the canonical file.

    Returns ``(data, error_code, revision)``.  error_code is one of
    ``config.not_found`` / ``config.corrupt`` or None; a valid dict is returned
    with its exact-bytes revision stamp.
    """
    if not path.exists():
        return None, "config.not_found", None
    try:
        raw = path.read_bytes()
    except OSError:
        return None, "config.corrupt", None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "config.corrupt", None
    if not isinstance(data, dict):
        return None, "config.corrupt", None
    return data, None, "sha256:" + hashlib.sha256(raw).hexdigest()


def _write_document_atomic(path: Path, data: dict[str, Any]) -> str:
    """Serialize canonical known structure while preserving unknown values,
    then atomically replace via temp + flush + fsync + os.replace."""
    raw = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".paperforge-config-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            shutil.copymode(path, Path(tmp))
        os.replace(tmp, path)
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass  # POSIX best-effort parent fsync
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _schema_version_of(data: dict[str, Any]) -> tuple[int, str | None]:
    """Return ``(version, error_code)``.  String ``"2"`` normalizes; missing or
    non-integer values are legacy (migration_required)."""
    raw = data.get("schema_version", "1")
    if isinstance(raw, bool):
        return 0, "config.migration_required"
    if isinstance(raw, int):
        return raw, None
    if isinstance(raw, str) and raw.strip() == "2":
        return 2, None
    return 0, "config.migration_required"


# ---------------------------------------------------------------------------
# Field validation
# ---------------------------------------------------------------------------

def _is_secret_like(key: str) -> bool:
    low = key.lower()
    return any(part in low for part in _SECRET_KEY_PARTS)


def _parse_bool(value: object, source_label: str) -> tuple[bool | None, str | None]:
    if isinstance(value, bool):
        return value, None
    if isinstance(value, str) and value.strip().lower() in ("true", "1"):
        return True, None
    if isinstance(value, str) and value.strip().lower() in ("false", "0"):
        return False, None
    return None, f"{source_label} must be true|false|1|0"


def _validate_http_url(value: str, source_label: str) -> str | None:
    if not (value.startswith("http://") or value.startswith("https://")):
        return f"{source_label} must be an http(s) URL"
    authority = value.split("://", 1)[1].split("/", 1)[0]
    if not authority:
        return f"{source_label} must include a host"
    if "@" in authority:
        return f"{source_label} must not contain userinfo credentials"
    return None


def _validate_vault_relative(value: str, source_label: str) -> str | None:
    if not value.strip():
        return f"{source_label} must not be empty"
    if value.startswith(("/", "\\")) or (len(value) >= 2 and value[1] == ":"):
        return f"{source_label} must be vault-relative (no absolute path)"
    if "\x00" in value:
        return f"{source_label} must not contain NUL"
    norm = Path(value).as_posix()
    if any(seg == ".." for seg in norm.split("/")):
        return f"{source_label} must not contain '..' segments"
    return None


def validate_field_value(spec: FieldSpec, value: object, source_label: str) -> tuple[str | bool | None, str | None]:
    """Validate one raw value against its FieldSpec; returns ``(parsed, error)``."""
    if spec.value_type == "boolean":
        return _parse_bool(value, source_label)
    if not isinstance(value, str):
        return None, f"{source_label} must be a string"
    if not spec.allow_empty and not value.strip():
        return None, f"{source_label} must not be empty"
    if spec.value_type == "enum":
        if value not in spec.choices:
            return None, f"{source_label} must be one of {', '.join(spec.choices)}"
        return value, None
    if spec.value_type == "path":
        if spec.vault_relative:
            err = _validate_vault_relative(value, source_label)
            if err:
                return None, err
        return value, None
    if spec.key in ("paddleocr_job_url", "vector_db_api_base"):
        if value.strip():
            err = _validate_http_url(value, source_label)
            if err:
                return None, err
        return value, None
    if spec.key in ("ocr_profile", "embedding_profile"):
        if not value or len(value) > 64 or not value[0].islower() or not all(
            c.isalnum() or c == "_" for c in value
        ):
            return None, f"{source_label} must match [a-z][a-z0-9_]{{0,63}}"
        return value, None
    return value, None


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _lookup_stored(data: dict[str, Any], spec: FieldSpec) -> object:
    if spec.storage_path[0] == "vault_config":
        nested = data.get("vault_config")
        if isinstance(nested, dict) and spec.storage_path[1] in nested:
            return nested[spec.storage_path[1]]
        return None
    return data.get(spec.key)


def _store_value(data: dict[str, Any], spec: FieldSpec, value: object) -> None:
    if spec.storage_path[0] == "vault_config":
        nested = data.setdefault("vault_config", {})
        nested[spec.storage_path[1]] = value
    else:
        data[spec.key] = value


def _drop_stored(data: dict[str, Any], spec: FieldSpec) -> None:
    if spec.storage_path[0] == "vault_config":
        nested = data.get("vault_config")
        if isinstance(nested, dict):
            nested.pop(spec.storage_path[1], None)
    else:
        data.pop(spec.key, None)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _classify_document(data: dict[str, Any], path: Path) -> ConfigValidation:
    version, verr = _schema_version_of(data)
    if verr is not None:
        return ConfigValidation("migration_required", None,
                                ({"code": verr, "path": str(path)},), (),
                                migration={"reason": "missing or legacy schema_version"})
    if version > SCHEMA_VERSION:
        return ConfigValidation("future_schema", None,
                                ({"code": "config.future_schema", "path": str(path)},), ())
    if version < SCHEMA_VERSION:
        return ConfigValidation("migration_required", None,
                                ({"code": "config.migration_required", "path": str(path)},), ())

    legacy = [k for k in LEGACY_PATH_KEYS if k in data]
    if legacy or "agent_key" in data or any(k in data for k in _DERIVED_LEGACY_FIELDS):
        return ConfigValidation("migration_required", None,
                                ({"code": "config.migration_required", "path": str(path),
                                  "legacy_keys": legacy},), ())

    errors: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []

    nested = data.get("vault_config")
    if nested is not None and not isinstance(nested, dict):
        return ConfigValidation("invalid", None,
                                ({"code": "config.invalid", "key": "vault_config",
                                  "reason": "must be an object"},), ())

    for spec in FIELD_SPECS:
        stored = _lookup_stored(data, spec)
        if stored is None:
            continue
        parsed, err = validate_field_value(spec, stored, f"field '{spec.key}'")
        if err:
            errors.append({"code": "config.invalid", "key": spec.key, "reason": err})

    top_keys = [k for k in data if k not in ("schema_version", "vault_config")]
    for key in top_keys:
        if _is_secret_like(key):
            return ConfigValidation("invalid", None,
                                    ({"code": "config.secret_field", "key": key},), ())
        if key not in FIELD_BY_KEY:
            warnings.append({"code": "config.unknown_key", "key": key})

    if isinstance(nested, dict):
        for key in nested:
            if _is_secret_like(key):
                return ConfigValidation("invalid", None,
                                        ({"code": "config.secret_field", "key": f"vault_config.{key}"},), ())
            if key not in FIELD_BY_KEY:
                warnings.append({"code": "config.unknown_key", "key": f"vault_config.{key}"})

    if errors:
        return ConfigValidation("invalid", None, tuple(errors), tuple(warnings))
    return ConfigValidation("valid", None, (), tuple(warnings))


def validate_config(vault: Path) -> ConfigValidation:
    """Classify missing/corrupt/legacy/future/current without interpreting
    invalid state.  Command success means the inspection completed."""
    path = vault / CONFIG_FILE
    data, err, revision = _read_document(path)
    if err is not None:
        return ConfigValidation(
            "missing" if err == "config.not_found" else "invalid",
            revision, ({"code": err, "path": str(path)},), ())
    assert data is not None
    result = _classify_document(data, path)
    return ConfigValidation(result.state, revision, result.errors, result.warnings,
                            migration=result.migration)


# ---------------------------------------------------------------------------
# Loading / resolution
# ---------------------------------------------------------------------------

def _snapshot_from(data: dict[str, Any], revision: str, env: Mapping[str, str],
                   overrides: Mapping[str, object]) -> ConfigSnapshot:
    values: dict[str, ConfigValue] = {}
    warnings: list[str] = []
    unknown: list[str] = []

    top_keys = [k for k in data if k not in ("schema_version", "vault_config")]
    for key in top_keys:
        if _is_secret_like(key):
            raise ConfigError("config.secret_field", {"key": key})
        if key not in FIELD_BY_KEY:
            unknown.append(key)
            warnings.append(f"unknown field '{key}' preserved but not interpreted")
    nested = data.get("vault_config")
    if isinstance(nested, dict):
        for key in nested:
            if _is_secret_like(key):
                raise ConfigError("config.secret_field", {"key": f"vault_config.{key}"})
            if key not in FIELD_BY_KEY:
                unknown.append(f"vault_config.{key}")
                warnings.append(f"unknown field 'vault_config.{key}' preserved but not interpreted")

    for spec in FIELD_SPECS:
        source = SOURCE_DEFAULT
        stored_value: str | bool | None = None
        raw: str | bool = spec.default

        stored = _lookup_stored(data, spec)
        if stored is not None:
            parsed, err = validate_field_value(spec, stored, f"field '{spec.key}'")
            if err:
                raise ConfigError("config.invalid", {"key": spec.key, "reason": err})
            assert parsed is not None
            raw = parsed
            stored_value = parsed
            source = SOURCE_FILE

        if spec.env is not None and spec.env in env:
            parsed, err = validate_field_value(spec, env[spec.env], f"environment '{spec.env}'")
            if err:
                raise ConfigError("config.invalid_environment",
                                  {"variable": spec.env, "reason": err})
            assert parsed is not None
            raw = parsed
            source = SOURCE_ENVIRONMENT

        if spec.key in overrides and overrides[spec.key] is not None:
            parsed, err = validate_field_value(spec, overrides[spec.key], f"override '{spec.key}'")
            if err:
                raise ConfigError("config.invalid", {"key": spec.key, "reason": err})
            assert parsed is not None
            raw = parsed
            source = SOURCE_OVERRIDE

        values[spec.key] = ConfigValue(
            key=spec.key, value=raw, stored_value=stored_value,
            source=source, is_set=source != SOURCE_DEFAULT, spec=spec,
        )

    return ConfigSnapshot(
        schema_version=SCHEMA_VERSION,
        revision=revision,
        values=values,
        unknown_keys=tuple(sorted(unknown)),
        warnings=tuple(warnings),
    )


def _raise_invalid_document(validation: ConfigValidation) -> None:
    """Raise the specific first error code (e.g. config.secret_field) so
    clients can route credential migration to #138."""
    if validation.errors:
        code = str(validation.errors[0].get("code", "config.invalid"))
        raise ConfigError(code, {"errors": list(validation.errors)})
    raise ConfigError("config.invalid")


def load_config(vault: Path, *, env: Mapping[str, str] | None = None,
                overrides: Mapping[str, object] | None = None) -> ConfigSnapshot:
    """Strictly load current schema and resolve defaults < file < env < overrides.

    Raises ConfigError (config.not_found / corrupt / migration_required /
    future_schema / invalid / invalid_environment / secret_field) — domain
    commands must never operate on guessed paths.
    """
    path = vault / CONFIG_FILE
    data, err, revision = _read_document(path)
    if err is not None:
        raise ConfigError(err, {"path": str(path)})
    assert data is not None
    validation = _classify_document(data, path)
    if validation.state == "future_schema":
        raise ConfigError("config.future_schema", {"path": str(path)})
    if validation.state == "migration_required":
        raise ConfigError("config.migration_required",
                          {"path": str(path), "hint": "run 'paperforge config migrate'"})
    if validation.state == "invalid":
        _raise_invalid_document(validation)
    return _snapshot_from(data, revision, env if env is not None else os.environ,
                          overrides if overrides is not None else {})


# ---------------------------------------------------------------------------
# Mutation transaction (the single writer — set/unset/init/migrate all route
# through this one primitive)
# ---------------------------------------------------------------------------

def _transaction(vault: Path, mutator, *, allow_missing: bool = False,
                 allow_legacy: bool = False) -> MutationResult:
    """One locked transaction: filelock -> fresh re-read -> strict classify ->
    mutate -> canonicalize -> full candidate validate -> atomic replace ->
    read-back (restoring prior bytes on failure)."""
    path = vault / CONFIG_FILE
    lock_path = vault / LOCK_FILE
    lock = FileLock(str(lock_path), timeout=LOCK_TIMEOUT_SECONDS)
    try:
        with lock:
            data, err, _revision = _read_document(path)
            if err is not None:
                if allow_missing and err == "config.not_found":
                    data = {}
                else:
                    raise ConfigError(err, {"path": str(path)})
            if data:
                validation = _classify_document(data, path)
                if validation.state == "future_schema":
                    raise ConfigError("config.future_schema", {"path": str(path)})
                if validation.state == "migration_required" and not allow_legacy:
                    raise ConfigError("config.migration_required",
                                      {"path": str(path), "hint": "run 'paperforge config migrate'"})
                if validation.state == "invalid":
                    _raise_invalid_document(validation)

            changed, candidate, extras = mutator(data)

            # Canonicalization: schema_version is always written as int 2 on a
            # successful mutation (#142 — string "2" normalizes; legacy docs
            # gain the canonical version).
            if candidate.get("schema_version") != SCHEMA_VERSION:
                candidate["schema_version"] = SCHEMA_VERSION
                changed = True

            # Full candidate validation before any write.
            check = _classify_document(candidate, path)
            if check.state == "invalid":
                raise ConfigError("config.invalid", {"errors": list(check.errors)})
            if check.state == "future_schema":
                raise ConfigError("config.future_schema", {"path": str(path)})

            prior = path.read_bytes() if path.exists() else None
            if changed:
                try:
                    _write_document_atomic(path, candidate)
                except OSError as exc:
                    raise ConfigError("config.write_failed",
                                      {"path": str(path), "detail": str(exc)})

            data2, err2, revision2 = _read_document(path)
            if err2 is not None:
                if prior is not None:
                    try:
                        path.write_bytes(prior)
                    except OSError:
                        pass
                raise ConfigError("config.write_failed",
                                  {"path": str(path), "detail": err2})
            assert data2 is not None
            return MutationResult(
                changed,
                _snapshot_from(data2, revision2, os.environ, {}),
                warnings=tuple(extras),
            )
    except Timeout:
        raise ConfigError("config.locked", {"path": str(lock_path)})


def set_config(vault: Path, key: str, value: object) -> MutationResult:
    """Validate and atomically set one canonical user field."""
    if _is_secret_like(key):
        raise ConfigError("config.secret_field", {"key": key})
    spec = FIELD_BY_KEY.get(key)
    if spec is None:
        raise ConfigError("config.unknown_key", {"key": key})
    if not spec.writable:
        raise ConfigError("config.read_only_key", {"key": key})
    parsed, err = validate_field_value(spec, value, f"value for '{key}'")
    if err:
        raise ConfigError("config.invalid", {"key": key, "reason": err})
    assert parsed is not None

    def _apply(data: dict[str, Any]) -> tuple[bool, dict[str, Any], tuple[str, ...]]:
        current = _lookup_stored(data, spec)
        if current is not None and current == parsed:
            return False, data, ()
        _store_value(data, spec, parsed)
        return True, data, ()

    return _transaction(vault, _apply)


def unset_config(vault: Path, key: str) -> MutationResult:
    """Atomically remove the stored field; effective value falls through to
    env/default."""
    if _is_secret_like(key):
        raise ConfigError("config.secret_field", {"key": key})
    spec = FIELD_BY_KEY.get(key)
    if spec is None:
        raise ConfigError("config.unknown_key", {"key": key})
    if not spec.writable:
        raise ConfigError("config.read_only_key", {"key": key})

    def _apply(data: dict[str, Any]) -> tuple[bool, dict[str, Any], tuple[str, ...]]:
        current = _lookup_stored(data, spec)
        if current is None:
            return False, data, ()
        _drop_stored(data, spec)
        return True, data, ()

    return _transaction(vault, _apply)


def bootstrap_config(vault: Path) -> MutationResult:
    """Create a complete explicit schema-2 file from current defaults when
    absent; idempotent for an existing valid file.  Legacy/corrupt/future
    files are never overwritten."""
    if not vault.exists():
        raise ConfigError("config.not_found",
                          {"path": str(vault / CONFIG_FILE), "reason": "vault does not exist"})

    def _apply(data: dict[str, Any]) -> tuple[bool, dict[str, Any], tuple[str, ...]]:
        if data:
            return False, data, ()
        document: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "vault_config": {}}
        for spec in FIELD_SPECS:
            if spec.storage_path[0] == "vault_config":
                document["vault_config"][spec.storage_path[1]] = spec.default
            else:
                document[spec.key] = spec.default
        return True, document, ()

    return _transaction(vault, _apply, allow_missing=True)


def _migrate_transform(data: dict[str, Any]) -> tuple[bool, dict[str, Any], tuple[str, ...]]:
    """Apply the #142 §9 migration rules. Returns (changed, candidate, warnings)."""
    candidate: dict[str, Any] = dict(data)
    migrated: list[str] = []
    conflicts: list[str] = []

    nested = candidate.get("vault_config")
    if nested is not None and not isinstance(nested, dict):
        raise ConfigError("config.invalid", {"key": "vault_config", "reason": "not an object"})
    vault_config: dict[str, Any] = candidate.setdefault("vault_config", {})

    for key in LEGACY_PATH_KEYS:
        spec = FIELD_BY_KEY[key]
        canonical = vault_config.get(spec.storage_path[1])
        legacy = candidate.get(key)
        if legacy is None:
            continue
        if canonical is not None:
            if str(canonical) != str(legacy):
                conflicts.append(
                    f"conflict.{key}: canonical '{canonical}' vs legacy '{legacy}' — canonical wins")
        else:
            vault_config[spec.storage_path[1]] = legacy
            migrated.append(key)
        del candidate[key]

    agent_key = candidate.pop("agent_key", None)
    if agent_key is not None:
        if "agent_platform" not in candidate:
            candidate["agent_platform"] = agent_key
            migrated.append("agent_key")
        else:
            # RC: legacy writers may have stored a case-mismatched value
            # (e.g. "OpenCode") while agent_key holds the canonical spelling.
            # Normalize rather than letting the invalid value block migration.
            stored = candidate["agent_platform"]
            normalized = (
                str(stored).strip().lower()
                if isinstance(stored, str)
                else stored
            )
            if normalized != stored:
                candidate["agent_platform"] = normalized
                migrated.append("agent_platform.normalize")
            if str(agent_key).strip().lower() != str(normalized).strip().lower():
                candidate["agent_platform"] = agent_key
                migrated.append("agent_platform.from_agent_key")

    for derived in _DERIVED_LEGACY_FIELDS:
        if derived in candidate:
            del candidate[derived]
            migrated.append(derived)

    changed = bool(migrated) or candidate != data
    return changed, candidate, tuple(conflicts)


def migrate_config(vault: Path, *, dry_run: bool = False) -> MutationResult:
    """Explicitly normalize legacy structure through the same writer.

    Dry-run reads without a lock and writes nothing; conflicts are reported in
    ``MutationResult.warnings`` so the CLI/plugin can present them.
    """
    if dry_run:
        data, err, _rev = _read_document(vault / CONFIG_FILE)
        if err is not None:
            raise ConfigError(err, {"path": str(vault / CONFIG_FILE)})
        assert data is not None
        for key in data:
            if key == "vault_config":
                continue
            if _is_secret_like(key):
                raise ConfigError("config.secret_field",
                                  {"key": key, "hint": "credentials migrate via #138 (auth migrate)"})
        nested = data.get("vault_config")
        if isinstance(nested, dict):
            for key in nested:
                if _is_secret_like(key):
                    raise ConfigError("config.secret_field",
                                      {"key": f"vault_config.{key}",
                                       "hint": "credentials migrate via #138 (auth migrate)"})
        changed, candidate, conflicts = _migrate_transform(data)
        if candidate.get("schema_version") != SCHEMA_VERSION:
            candidate["schema_version"] = SCHEMA_VERSION
        stamp = "sha256:" + hashlib.sha256(
            json.dumps(candidate, sort_keys=True).encode("utf-8")).hexdigest()
        return MutationResult(changed, _snapshot_from(candidate, stamp, os.environ, {}),
                              warnings=conflicts)

    return _transaction(vault, _migrate_transform, allow_legacy=True)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def resolve_paths(vault: Path, snapshot: ConfigSnapshot | None = None) -> dict[str, Path]:
    """Return the complete D-Path inventory from resolved configuration."""
    snap = snapshot if snapshot is not None else load_config(vault)
    values = {key: cv.value for key, cv in snap.values.items()}

    vault = Path(vault).expanduser().resolve()
    system = vault / str(values["system_dir"])
    paperforge = system / "PaperForge"
    resources = vault / str(values["resources_dir"])
    literature = resources / str(values["literature_dir"])
    control = resources / str(values["control_dir"])
    bases = vault / str(values["base_dir"])
    skill_path = vault / str(values["skill_dir"])

    zotero_dir_val = str(values["zotero_data_dir"]).strip() if values.get("zotero_data_dir") else ""
    if not zotero_dir_val:
        zotero_dir_val = str(system / "Zotero")
    zotero_dir = Path(zotero_dir_val)
    if not zotero_dir.is_absolute():
        zotero_dir = vault / zotero_dir

    worker_script = Path(__file__).parent / "worker" / "__init__.py"
    pf_deep_script = skill_path / "paperforge" / "scripts" / "pf_deep.py"
    if not pf_deep_script.exists():
        repo_skill = Path(__file__).parent / "skills" / "paperforge" / "scripts" / "pf_deep.py"
        if repo_skill.exists():
            pf_deep_script = repo_skill

    return {
        "vault": vault,
        "system": system,
        "paperforge": paperforge,
        "exports": paperforge / "exports",
        "ocr": paperforge / "ocr",
        "zotero_dir": zotero_dir,
        "resources": resources,
        "literature": literature,
        "control": control,
        "library_records": control / "library-records",
        "bases": bases,
        "worker_script": worker_script,
        "skill_dir": skill_path,
        "pf_deep_script": pf_deep_script,
        "config": paperforge / "config" / "domain-collections.json",
        "index": paperforge / "indexes" / "formal-library.json",
    }


# ---------------------------------------------------------------------------
# Thin wrappers for in-repo callers (delegate to the seam; no fallback, no
# separate defaults).  Removed after every caller migrates.
# ---------------------------------------------------------------------------

def load_vault_config(
    vault: Path,
    env: dict[str, str] | None = None,
    overrides: dict[str, str] | None = None,
    trace_sources: bool = False,
) -> dict[str, str] | tuple[dict[str, str], dict[str, str]]:
    """Thin wrapper over :func:`load_config` — fail-closed (raises ConfigError
    on missing/corrupt/legacy/invalid/future config).  The legacy top-level
    fallback and its warning no longer exist."""
    snapshot = load_config(vault, env=env if env is not None else os.environ,
                           overrides=overrides if overrides is not None else {})
    config: dict[str, str] = {}
    trace: dict[str, str] = {}
    for key, cv in snapshot.values.items():
        config[key] = str(cv.value).lower() if isinstance(cv.value, bool) else str(cv.value)
        trace[key] = cv.source
    if trace_sources:
        return config, trace
    return config


def paperforge_paths(vault: Path, cfg: dict[str, str] | None = None) -> dict[str, Path]:
    """Thin wrapper over :func:`resolve_paths`."""
    if cfg is not None:
        document: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "vault_config": {}}
        for key, value in cfg.items():
            spec = FIELD_BY_KEY.get(key)
            if spec is None:
                continue
            _store_value(document, spec, value)
        snapshot = _snapshot_from(document, "override", {}, {})
        return resolve_paths(vault, snapshot)
    return resolve_paths(vault)


def paths_as_strings(paths: dict[str, Path]) -> dict[str, str]:
    """Convert a paperforge_paths dict to JSON-serializable dict[str, str]."""
    return {name: str(path) for name, path in paths.items()}


def resolve_vault(
    cli_vault: Path | None = None,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
) -> Path:
    """Resolve the vault path: explicit CLI arg → PAPERFORGE_VAULT → nearest
    ancestor containing paperforge.json → cwd."""
    if cli_vault is not None:
        return Path(cli_vault).expanduser().resolve()
    env = env if env is not None else os.environ
    if PAPERFORGE_VAULT_ENV in env and env[PAPERFORGE_VAULT_ENV]:
        return Path(env[PAPERFORGE_VAULT_ENV]).expanduser().resolve()
    search: Path = Path(cwd).expanduser().resolve() if cwd is not None else Path.cwd()
    while search is not None and search != search.parent:
        if (search / CONFIG_FILE).exists():
            return search
        search = search.parent
    return Path(cwd).expanduser().resolve() if cwd is not None else Path.cwd()
