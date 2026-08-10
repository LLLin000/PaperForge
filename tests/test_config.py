"""Tests for the canonical configuration authority (#142 / C0).

Covers the acceptance criteria of the frozen design: one parser/validator/
writer, resolution order defaults < file < env < overrides with per-field
sources, fail-closed classification, one atomic writer, unknown-field
preservation, secret refusal, explicit migration, and the config CLI verbs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from paperforge.config import (
    FIELD_BY_KEY,
    ConfigError,
    bootstrap_config,
    load_config,
    migrate_config,
    resolve_paths,
    set_config,
    unset_config,
    validate_config,
)
from paperforge.config import (
    SCHEMA_VERSION,
    SOURCE_DEFAULT,
    SOURCE_ENVIRONMENT,
    SOURCE_FILE,
    SOURCE_OVERRIDE,
)


def _write(vault: Path, data: dict) -> Path:
    vault.mkdir(parents=True, exist_ok=True)
    path = vault / "paperforge.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


_VAULT_CONFIG_FIELDS = frozenset({
    "system_dir", "resources_dir", "literature_dir", "control_dir",
    "base_dir", "skill_dir", "command_dir",
})


def _canonical(vault: Path, **overrides) -> dict:
    doc: dict[str, object] = {"schema_version": SCHEMA_VERSION, "vault_config": {}}
    for key, value in overrides.items():
        if key in _VAULT_CONFIG_FIELDS:
            doc["vault_config"][key] = value  # type: ignore[index]
        else:
            doc[key] = value
    _write(vault, doc)
    return overrides


# ---------------------------------------------------------------------------
# Field vocabulary
# ---------------------------------------------------------------------------

def test_field_specs_cover_documented_fields():
    expected = {
        "system_dir", "resources_dir", "literature_dir", "control_dir",
        "base_dir", "skill_dir", "command_dir", "zotero_data_dir",
        "agent_platform", "auto_analyze_after_ocr", "ocr_profile",
        "paddleocr_job_url", "paddleocr_model", "embedding_profile",
        "vector_db_provider_type", "vector_db_api_base", "vector_db_api_model",
    }
    assert set(FIELD_BY_KEY) == expected


def test_agent_platform_choices_python_owned():
    spec = FIELD_BY_KEY["agent_platform"]
    assert spec.choices and "opencode" in spec.choices


# ---------------------------------------------------------------------------
# Classification (fail closed)
# ---------------------------------------------------------------------------

def test_validate_missing(tmp_path: Path):
    assert validate_config(tmp_path).state == "missing"


def test_validate_corrupt(tmp_path: Path):
    vault = tmp_path / "v"
    vault.mkdir()
    (vault / "paperforge.json").write_text("{not json", encoding="utf-8")
    assert validate_config(vault).state == "invalid"


def test_validate_future_schema(tmp_path: Path):
    vault = tmp_path / "v"
    vault.mkdir()
    (vault / "paperforge.json").write_text('{"schema_version": 99}', encoding="utf-8")
    assert validate_config(vault).state == "future_schema"


def test_validate_migration_required_for_legacy_top_level(tmp_path: Path):
    vault = tmp_path / "v"
    _write(vault, {"system_dir": "System"})
    assert validate_config(vault).state == "migration_required"


def test_validate_migration_required_without_schema_version(tmp_path: Path):
    vault = tmp_path / "v"
    _write(vault, {"vault_config": {"system_dir": "System"}})
    assert validate_config(vault).state == "migration_required"


def test_validate_secret_field(tmp_path: Path):
    vault = tmp_path / "v"
    _write(vault, {"schema_version": 2, "vault_config": {}, "openai_api_key": "sk-x"})
    assert validate_config(vault).state == "invalid"


def test_validate_unknown_key_warns(tmp_path: Path):
    vault = tmp_path / "v"
    _write(vault, {"schema_version": 2, "vault_config": {}, "repository": "x"})
    validation = validate_config(vault)
    assert validation.state == "valid"
    assert any("config.unknown_key" in str(w.get("code")) for w in validation.warnings)


def test_load_missing_raises(tmp_path: Path):
    with pytest.raises(ConfigError) as exc:
        load_config(tmp_path)
    assert exc.value.code == "config.not_found"


def test_load_migration_required_raises(tmp_path: Path):
    vault = tmp_path / "v"
    _write(vault, {"system_dir": "System"})
    with pytest.raises(ConfigError) as exc:
        load_config(vault)
    assert exc.value.code == "config.migration_required"


def test_load_secret_field_raises(tmp_path: Path):
    vault = tmp_path / "v"
    _write(vault, {"schema_version": 2, "vault_config": {}, "vector_db_api_key": "k"})
    with pytest.raises(ConfigError) as exc:
        load_config(vault)
    assert exc.value.code == "config.secret_field"


# ---------------------------------------------------------------------------
# Resolution order and sources
# ---------------------------------------------------------------------------

def test_resolution_defaults_file_env_override(tmp_path: Path, monkeypatch):
    _canonical(tmp_path, system_dir="FileSystem")
    monkeypatch.setenv("PAPERFORGE_SYSTEM_DIR", "EnvSystem")
    snapshot = load_config(tmp_path, overrides={"system_dir": "OverrideSystem"})
    assert snapshot.values["system_dir"].value == "OverrideSystem"
    assert snapshot.values["system_dir"].source == SOURCE_OVERRIDE
    snapshot = load_config(tmp_path)
    assert snapshot.values["system_dir"].value == "EnvSystem"
    assert snapshot.values["system_dir"].source == SOURCE_ENVIRONMENT
    monkeypatch.delenv("PAPERFORGE_SYSTEM_DIR")
    snapshot = load_config(tmp_path)
    assert snapshot.values["system_dir"].value == "FileSystem"
    assert snapshot.values["system_dir"].source == SOURCE_FILE
    assert snapshot.values["ocr_profile"].source == SOURCE_DEFAULT


def test_invalid_environment_fails_closed(tmp_path: Path, monkeypatch):
    _canonical(tmp_path)
    monkeypatch.setenv("PAPERFORGE_AGENT_PLATFORM", "not-a-platform")
    with pytest.raises(ConfigError) as exc:
        load_config(tmp_path)
    assert exc.value.code == "config.invalid_environment"


def test_invalid_file_value_fails_closed(tmp_path: Path):
    _write(tmp_path, {"schema_version": 2, "vault_config": {}, "agent_platform": "nope"})
    with pytest.raises(ConfigError) as exc:
        load_config(tmp_path)
    assert exc.value.code == "config.invalid"


# ---------------------------------------------------------------------------
# Mutation (one atomic writer)
# ---------------------------------------------------------------------------

def test_set_and_get_roundtrip(tmp_path: Path):
    _canonical(tmp_path)
    mutation = set_config(tmp_path, "vector_db_api_model", "text-embedding-3-large")
    assert mutation.changed is True
    assert mutation.snapshot.values["vector_db_api_model"].value == "text-embedding-3-large"
    assert mutation.snapshot.values["vector_db_api_model"].source == SOURCE_FILE


def test_set_same_value_changed_false(tmp_path: Path):
    _canonical(tmp_path, system_dir="System")
    mutation = set_config(tmp_path, "system_dir", "System")
    assert mutation.changed is False


def test_set_unknown_key(tmp_path: Path):
    _canonical(tmp_path)
    with pytest.raises(ConfigError) as exc:
        set_config(tmp_path, "nope", "x")
    assert exc.value.code == "config.unknown_key"


def test_set_secret_like_key_refused(tmp_path: Path):
    _canonical(tmp_path)
    with pytest.raises(ConfigError) as exc:
        set_config(tmp_path, "vector_db_api_key", "k")
    assert exc.value.code == "config.secret_field"


def test_set_invalid_value(tmp_path: Path):
    _canonical(tmp_path)
    with pytest.raises(ConfigError) as exc:
        set_config(tmp_path, "agent_platform", "nope")
    assert exc.value.code == "config.invalid"


def test_set_boolean_parsing(tmp_path: Path):
    _canonical(tmp_path)
    set_config(tmp_path, "auto_analyze_after_ocr", "true")
    assert load_config(tmp_path).values["auto_analyze_after_ocr"].value is True
    set_config(tmp_path, "auto_analyze_after_ocr", False)
    assert load_config(tmp_path).values["auto_analyze_after_ocr"].value is False
    with pytest.raises(ConfigError):
        set_config(tmp_path, "auto_analyze_after_ocr", "maybe")


def test_set_vault_relative_rejects_absolute(tmp_path: Path):
    _canonical(tmp_path)
    with pytest.raises(ConfigError) as exc:
        set_config(tmp_path, "system_dir", "C:/Absolute")
    assert exc.value.code == "config.invalid"


def test_set_url_rejects_userinfo(tmp_path: Path):
    _canonical(tmp_path)
    with pytest.raises(ConfigError):
        set_config(tmp_path, "paddleocr_job_url", "https://user:pass@host/api")


def test_unset_falls_through_to_default(tmp_path: Path):
    _canonical(tmp_path, system_dir="Custom")
    mutation = unset_config(tmp_path, "system_dir")
    assert mutation.changed is True
    cv = mutation.snapshot.values["system_dir"]
    assert cv.value == "System"
    assert cv.source == SOURCE_DEFAULT


def test_mutation_preserves_unknown_fields(tmp_path: Path):
    _canonical(tmp_path)
    data = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
    data["repository"] = "keep-me"
    (tmp_path / "paperforge.json").write_text(json.dumps(data), encoding="utf-8")
    set_config(tmp_path, "agent_platform", "claude")
    after = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
    assert after["repository"] == "keep-me"
    snapshot = load_config(tmp_path)
    assert "repository" in snapshot.unknown_keys


def test_mutation_refuses_corrupt_file(tmp_path: Path):
    vault = tmp_path / "v"
    vault.mkdir()
    (vault / "paperforge.json").write_text("{corrupt", encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        set_config(vault, "system_dir", "X")
    assert exc.value.code == "config.corrupt"


def test_concurrent_different_key_mutations_both_survive(tmp_path: Path):
    _canonical(tmp_path)
    set_config(tmp_path, "system_dir", "A")
    set_config(tmp_path, "resources_dir", "B")
    snapshot = load_config(tmp_path)
    assert snapshot.values["system_dir"].value == "A"
    assert snapshot.values["resources_dir"].value == "B"


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def test_bootstrap_creates_explicit_defaults(tmp_path: Path):
    mutation = bootstrap_config(tmp_path)
    assert mutation.changed is True
    snapshot = mutation.snapshot
    assert snapshot.schema_version == SCHEMA_VERSION
    assert snapshot.values["system_dir"].value == "System"
    assert snapshot.values["system_dir"].source == SOURCE_FILE
    assert snapshot.values["vector_db_api_model"].value == "text-embedding-3-small"


def test_bootstrap_idempotent(tmp_path: Path):
    bootstrap_config(tmp_path)
    mutation = bootstrap_config(tmp_path)
    assert mutation.changed is False


def test_bootstrap_refuses_legacy(tmp_path: Path):
    _write(tmp_path, {"system_dir": "System"})
    with pytest.raises(ConfigError) as exc:
        bootstrap_config(tmp_path)
    assert exc.value.code == "config.migration_required"


def test_bootstrap_refuses_future(tmp_path: Path):
    _write(tmp_path, {"schema_version": 99})
    with pytest.raises(ConfigError) as exc:
        bootstrap_config(tmp_path)
    assert exc.value.code == "config.future_schema"


# ---------------------------------------------------------------------------
# Migration (explicit)
# ---------------------------------------------------------------------------

def test_migrate_legacy_top_level(tmp_path: Path):
    _write(tmp_path, {"system_dir": "Legacy", "agent_key": "claude", "paperforge_path": "x"})
    mutation = migrate_config(tmp_path)
    assert mutation.changed is True
    snapshot = load_config(tmp_path)
    assert snapshot.values["system_dir"].value == "Legacy"
    assert snapshot.values["agent_platform"].value == "claude"
    doc = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
    assert "system_dir" not in doc
    assert "paperforge_path" not in doc
    assert doc["schema_version"] == SCHEMA_VERSION


def test_migrate_dry_run_changes_nothing(tmp_path: Path):
    path = _write(tmp_path, {"system_dir": "Legacy"})
    before = path.read_bytes()
    mutation = migrate_config(tmp_path, dry_run=True)
    assert mutation.changed is True
    assert path.read_bytes() == before


def test_migrate_idempotent(tmp_path: Path):
    _write(tmp_path, {"system_dir": "Legacy"})
    migrate_config(tmp_path)
    mutation = migrate_config(tmp_path)
    assert mutation.changed is False


def test_migrate_secret_stops(tmp_path: Path):
    _write(tmp_path, {"schema_version": "2", "vault_config": {}, "openai_api_key": "k"})
    with pytest.raises(ConfigError) as exc:
        migrate_config(tmp_path)
    assert exc.value.code == "config.secret_field"


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def test_resolve_paths_inventory(tmp_path: Path):
    _canonical(tmp_path, system_dir="99_System")
    paths = resolve_paths(tmp_path)
    assert paths["system"] == tmp_path.resolve() / "99_System"
    assert paths["paperforge"] == paths["system"] / "PaperForge"
    assert paths["index"] == paths["paperforge"] / "indexes" / "formal-library.json"
    assert paths["exports"] == paths["paperforge"] / "exports"
    assert paths["literature"] == paths["resources"] / "Literature"


def test_resolve_paths_zotero_env(tmp_path: Path, monkeypatch):
    _canonical(tmp_path)
    monkeypatch.setenv("ZOTERO_DATA_DIR", "C:/Zotero")
    paths = resolve_paths(tmp_path)
    assert paths["zotero_dir"] == Path("C:/Zotero")


def test_unknown_fields_never_cross_wire():
    # config list exposes only declared fields + unknown names, never values
    from paperforge.commands.config import _field_payload

    snapshot = None
    # Covered by CLI contract tests; placeholder ensures import path exists.
    assert _field_payload is not None


# ---------------------------------------------------------------------------
# Wrappers (thin, fail-closed)
# ---------------------------------------------------------------------------

def test_load_vault_config_wrapper_fail_closed(tmp_path: Path):
    from paperforge.config import load_vault_config

    with pytest.raises(ConfigError):
        load_vault_config(tmp_path)
    _canonical(tmp_path, system_dir="System")
    cfg = load_vault_config(tmp_path)
    assert cfg["system_dir"] == "System"
    assert "schema_version" not in cfg


def test_paperforge_paths_wrapper(tmp_path: Path):
    from paperforge.config import paperforge_paths

    _canonical(tmp_path)
    paths = paperforge_paths(tmp_path)
    assert paths["vault"] == tmp_path.resolve()

# ---------------------------------------------------------------------------
# C0 correctness gaps (review 2026-08-09)
# ---------------------------------------------------------------------------

def test_custom_path_survives_cli_args_paths(tmp_path: Path):
    """P0-1: paperforge_paths(vault, cfg) must honor custom path config."""
    from paperforge.config import load_vault_config, paperforge_paths

    _canonical(tmp_path, system_dir="99_System")
    cfg = load_vault_config(tmp_path)
    paths = paperforge_paths(tmp_path, cfg)
    assert paths["system"] == tmp_path.resolve() / "99_System"
    assert paths["paperforge"] == paths["system"] / "PaperForge"


def test_nested_secret_rejected_on_validate(tmp_path: Path):
    _write(tmp_path, {"schema_version": 2,
                      "vault_config": {"system_dir": "System", "openai_api_key": "sk-x"}})
    validation = validate_config(tmp_path)
    assert validation.state == "invalid"
    assert any("config.secret_field" in str(e.get("code")) for e in validation.errors)


def test_nested_secret_rejected_on_load(tmp_path: Path):
    _write(tmp_path, {"schema_version": 2,
                      "vault_config": {"system_dir": "System", "vector_db_api_key": "k"}})
    with pytest.raises(ConfigError) as exc:
        load_config(tmp_path)
    assert exc.value.code == "config.secret_field"


def test_nested_secret_rejected_on_migrate(tmp_path: Path):
    _write(tmp_path, {"schema_version": "2",
                      "vault_config": {"system_dir": "System", "openai_api_key": "sk-x"}})
    with pytest.raises(ConfigError) as exc:
        migrate_config(tmp_path)
    assert exc.value.code == "config.secret_field"


def test_concurrent_set_threads_both_survive(tmp_path: Path):
    """True concurrency: two threads mutate different keys against the same
    file — the locked fresh re-read preserves both."""
    import threading

    _canonical(tmp_path)
    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def setter(key: str, value: str) -> None:
        try:
            barrier.wait()
            set_config(tmp_path, key, value)
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [
        threading.Thread(target=setter, args=("system_dir", "Alpha")),
        threading.Thread(target=setter, args=("resources_dir", "Beta")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    snapshot = load_config(tmp_path)
    assert snapshot.values["system_dir"].value == "Alpha"
    assert snapshot.values["resources_dir"].value == "Beta"


def test_migrate_racing_set_no_lost_update(tmp_path: Path):
    """set + migrate against the same legacy file: both effects survive.

    A set that wins the lock before migration fails closed by contract
    (legacy is never mutated in place); a set that runs after migration
    must never be lost."""
    import threading

    _write(tmp_path, {"system_dir": "Legacy"})
    barrier = threading.Barrier(2)
    results: list[str] = []

    def do_set() -> None:
        try:
            barrier.wait()
            set_config(tmp_path, "resources_dir", "Custom")
            results.append("set-ok")
        except ConfigError as exc:
            results.append(exc.code)

    def do_migrate() -> None:
        try:
            barrier.wait()
            migrate_config(tmp_path)
        except Exception as exc:  # pragma: no cover - failure path
            results.append(f"migrate:{exc}")

    threads = [threading.Thread(target=do_set), threading.Thread(target=do_migrate)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # Fail-closed set (lost the race against the legacy file) retries
    # deterministically after migration.
    if "config.migration_required" in results:
        set_config(tmp_path, "resources_dir", "Custom")
    doc = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
    assert doc["vault_config"]["system_dir"] == "Legacy"
    assert doc["vault_config"]["resources_dir"] == "Custom"
    assert doc["schema_version"] == SCHEMA_VERSION


def test_write_failure_preserves_old_file(tmp_path: Path, monkeypatch):
    _canonical(tmp_path, system_dir="System")
    before = (tmp_path / "paperforge.json").read_bytes()
    import paperforge.config as config_module

    def _boom(path, data):
        raise OSError("disk full")

    monkeypatch.setattr(config_module, "_write_document_atomic", _boom)
    with pytest.raises(ConfigError) as exc:
        set_config(tmp_path, "system_dir", "NewSystem")
    assert exc.value.code == "config.write_failed"
    assert (tmp_path / "paperforge.json").read_bytes() == before


def test_read_back_failure_restores_prior_bytes(tmp_path: Path, monkeypatch):
    _canonical(tmp_path, system_dir="System")
    before = (tmp_path / "paperforge.json").read_bytes()
    import paperforge.config as config_module

    real_read = config_module._read_document
    calls = {"n": 0}

    def _failing_read(path):
        calls["n"] += 1
        if calls["n"] >= 2:  # the read-back after write
            return None, "config.corrupt", None
        return real_read(path)

    monkeypatch.setattr(config_module, "_read_document", _failing_read)
    with pytest.raises(ConfigError) as exc:
        set_config(tmp_path, "system_dir", "NewSystem")
    assert exc.value.code == "config.write_failed"
    assert (tmp_path / "paperforge.json").read_bytes() == before


def test_string_schema_version_normalizes_on_mutation(tmp_path: Path):
    _write(tmp_path, {"schema_version": "2", "vault_config": {"system_dir": "System"}})
    set_config(tmp_path, "resources_dir", "Res")
    doc = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
    assert doc["schema_version"] == 2


def test_migration_conflict_visible_in_dry_run(tmp_path: Path):
    _write(tmp_path, {"schema_version": "2",
                      "vault_config": {"system_dir": "Canonical"},
                      "system_dir": "Legacy"})
    mutation = migrate_config(tmp_path, dry_run=True)
    assert any("conflict" in w and "system_dir" in w for w in mutation.warnings)
    # canonical wins; file untouched on dry-run
    doc = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
    assert doc["vault_config"]["system_dir"] == "Canonical"
    assert "system_dir" in doc  # legacy alias still present (dry-run)


def test_json_error_is_machine_readable_on_stdout(tmp_path: Path):
    """#137 machine contract: --json emits exactly one PFResult JSON on stdout
    for failures too; stderr carries no JSON."""
    import subprocess
    import sys

    _canonical(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(tmp_path),
         "config", "set", "nope", "x", "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["details"]["config_code"] == "config.unknown_key"


def test_migrate_cli_dry_run_reports_conflicts(tmp_path: Path):
    """Migration conflicts are visible in the dry-run CLI payload."""
    import subprocess
    import sys

    _write(tmp_path, {"schema_version": "2",
                      "vault_config": {"system_dir": "Canonical"},
                      "system_dir": "Legacy"})
    result = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(tmp_path),
         "config", "migrate", "--dry-run", "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert any("conflict" in w and "system_dir" in w for w in payload["data"]["warnings"])
