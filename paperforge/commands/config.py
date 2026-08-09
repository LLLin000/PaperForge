"""paperforge config — canonical configuration CLI (#142 / C0).

Eight verbs, all PFResult-shaped: list / get / set / unset / validate /
paths / init / migrate.  Exit codes: 0 success, 1 operation failure,
2 usage.  Stable error codes (config.*) drive clients, not bespoke exits.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from paperforge import __version__ as PF_VERSION
from paperforge.config import (
    ConfigError,
    ConfigSnapshot,
    ConfigValue,
    bootstrap_config,
    load_config,
    migrate_config,
    paths_as_strings,
    resolve_paths,
    set_config,
    unset_config,
    validate_config,
)
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult

_USAGE_VERBS = ("list", "get", "set", "unset", "validate", "paths", "init", "migrate")


def _config_error_result(command: str, exc: ConfigError) -> PFResult:
    suggestions: list[str] = []
    if exc.code == "config.not_found":
        suggestions.append("run 'paperforge config init' or 'paperforge setup'")
    if exc.code == "config.migration_required":
        suggestions.append("run 'paperforge config migrate --dry-run' to preview")
    return PFResult(
        ok=False,
        command=command,
        version=PF_VERSION,
        error=PFError(
            code=ErrorCode.VALIDATION_ERROR,
            message=exc.code,
            details={"config_code": exc.code, **dict(exc.details)},
            suggestions=suggestions,
        ),
    )


def _print_error(result: PFResult, args: Any) -> None:
    message = result.error.message if result.error else "config error"
    print(result.to_json() if args.json else message, file=__import__("sys").stderr)


def _field_payload(cv: ConfigValue) -> dict[str, Any]:
    return {
        "key": cv.key,
        "value": cv.value,
        "stored_value": cv.stored_value,
        "source": cv.source,
        "is_set": cv.is_set,
        "type": cv.spec.value_type,
        "default": cv.spec.default,
        "environment": cv.spec.env,
        "choices": list(cv.spec.choices),
        "writable": cv.spec.writable,
        "allow_empty": cv.spec.allow_empty,
        "vault_relative": cv.spec.vault_relative,
    }


def _snapshot_meta(snapshot: ConfigSnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version,
        "revision": snapshot.revision,
        "unknown_keys": list(snapshot.unknown_keys),
    }


def _ok(command: str, data: Any, warnings: list[str] | None = None) -> PFResult:
    return PFResult(ok=True, command=command, version=PF_VERSION, data=data,
                    warnings=warnings or [])


def run(args: Any) -> int:
    vault: Path = args.vault_path
    verb: str = args.config_verb

    if verb == "list":
        try:
            snapshot = load_config(vault)
        except ConfigError as exc:
            result = _config_error_result("config.list", exc)
            _print_error(result, args)
            return 1
        data = {**_snapshot_meta(snapshot),
                "fields": [_field_payload(cv) for cv in snapshot.values.values()]}
        result = _ok("config.list", data, warnings=list(snapshot.warnings))

    elif verb == "get":
        key = getattr(args, "key", None)
        if not key:
            result = PFResult(ok=False, command="config.get", version=PF_VERSION,
                              error=PFError(code=ErrorCode.VALIDATION_ERROR,
                                            message="config.usage", details={"verb": "get"}))
            _print_error(result, args)
            return 2
        try:
            snapshot = load_config(vault)
            cv = snapshot.values.get(key)
            if cv is None:
                raise ConfigError("config.unknown_key", {"key": key})
        except ConfigError as exc:
            result = _config_error_result("config.get", exc)
            _print_error(result, args)
            return 2 if exc.code == "config.unknown_key" else 1
        data = {**_snapshot_meta(snapshot), "field": _field_payload(cv)}
        result = _ok("config.get", data)

    elif verb == "set":
        key = getattr(args, "key", None)
        value = getattr(args, "value", None)
        if not key or value is None:
            result = PFResult(ok=False, command="config.set", version=PF_VERSION,
                              error=PFError(code=ErrorCode.VALIDATION_ERROR,
                                            message="config.usage", details={"verb": "set"}))
            _print_error(result, args)
            return 2
        try:
            mutation = set_config(vault, key, value)
        except ConfigError as exc:
            result = _config_error_result("config.set", exc)
            _print_error(result, args)
            return 2 if exc.code in ("config.unknown_key", "config.read_only_key", "config.secret_field") else 1
        cv = mutation.snapshot.values[key]
        data = {**_snapshot_meta(mutation.snapshot), "changed": mutation.changed,
                "field": _field_payload(cv)}
        result = _ok("config.set", data)

    elif verb == "unset":
        key = getattr(args, "key", None)
        if not key:
            result = PFResult(ok=False, command="config.unset", version=PF_VERSION,
                              error=PFError(code=ErrorCode.VALIDATION_ERROR,
                                            message="config.usage", details={"verb": "unset"}))
            _print_error(result, args)
            return 2
        try:
            mutation = unset_config(vault, key)
        except ConfigError as exc:
            result = _config_error_result("config.unset", exc)
            _print_error(result, args)
            return 2 if exc.code == "config.unknown_key" else 1
        cv = mutation.snapshot.values[key]
        data = {**_snapshot_meta(mutation.snapshot), "changed": mutation.changed,
                "field": _field_payload(cv)}
        result = _ok("config.unset", data)

    elif verb == "validate":
        validation = validate_config(vault)
        data = {
            "state": validation.state,
            "revision": validation.revision,
            "errors": list(validation.errors),
            "warnings": list(validation.warnings),
            "migration": validation.migration,
        }
        result = _ok("config.validate", data)

    elif verb == "paths":
        try:
            snapshot = load_config(vault)
            paths = resolve_paths(vault, snapshot)
        except ConfigError as exc:
            result = _config_error_result("config.paths", exc)
            _print_error(result, args)
            return 1
        data = {"revision": snapshot.revision, "paths": paths_as_strings(paths)}
        result = _ok("config.paths", data)

    elif verb == "init":
        try:
            mutation = bootstrap_config(vault)
        except ConfigError as exc:
            result = _config_error_result("config.init", exc)
            _print_error(result, args)
            return 1
        data = {**_snapshot_meta(mutation.snapshot), "created": mutation.changed}
        result = _ok("config.init", data)

    elif verb == "migrate":
        try:
            mutation = migrate_config(vault, dry_run=bool(getattr(args, "dry_run", False)))
        except ConfigError as exc:
            result = _config_error_result("config.migrate", exc)
            _print_error(result, args)
            return 1
        data = {**_snapshot_meta(mutation.snapshot), "changed": mutation.changed,
                "dry_run": bool(getattr(args, "dry_run", False))}
        result = _ok("config.migrate", data)

    else:  # pragma: no cover - argparse prevents this
        result = PFResult(ok=False, command=f"config.{verb}", version=PF_VERSION,
                          error=PFError(code=ErrorCode.VALIDATION_ERROR,
                                        message="config.usage", details={"verb": verb}))
        _print_error(result, args)
        return 2

    print(result.to_json() if args.json else (result.error.message if result.error else "ok"))
    return 0
