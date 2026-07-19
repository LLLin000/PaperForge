"""Tests for the paperforge probe CLI command (Issue #76, Issue #69 contract).

Tests cover:
- Envelope structure (all required fields, correct types)
- Reason codes are module-prefixed snake_case
- action.primary has full field set when non-null, null when ready
- Installation probe state mapping (missing/corrupt/invalid-shape/ready/old-python)
- Help probe state mapping (ready/limited)
- Config shape validation (list/primitive/empty dict → config_corrupt)
- CLI subprocess boundary
"""

from __future__ import annotations

import json
import subprocess
import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REQUIRED_ENVELOPE_FIELDS = {
    "schema_version", "module", "capability_state",
    "activity_state", "activity_label", "activity_progress",
    "severity", "reason", "action", "notices", "updated_at", "ttl_seconds",
}

REQUIRED_REASON_FIELDS = {"code", "text"}

REQUIRED_ACTION_PRIMARY_FIELDS = {
    "verb", "label", "destructive", "destructive_scope",
    "destructive_effect", "confirmation_required", "confirmation_prompt",
    "command", "scope", "scope_count",
}

VALID_STATES = {"unknown", "unavailable", "missing_input", "needs_action", "limited", "ready"}
VALID_SEVERITIES = {"ok", "warning", "error", "info"}


def _run_probe(module: str, vault: Path, extra_args: list[str] | None = None, env: dict[str, str] | None = None) -> dict:
    """Run `paperforge probe <module> --json` in a subprocess and return parsed JSON.

    NOTE: --vault must come BEFORE the subcommand (argparse global args rule).
    """
    cmd = [
        sys.executable,
        "-m",
        "paperforge",
        "--vault",
        str(vault),
        "probe",
        module,
        "--json",
    ]
    if extra_args:
        cmd.extend(extra_args)
    run_env = env if env is not None else os.environ.copy()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, env=run_env)
    assert result.returncode == 0, (
        f"CLI exited {result.returncode}\nstdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
    )
    return json.loads(result.stdout)


def _assert_envelope_shape(data: dict) -> None:
    """Assert envelope has all required fields with correct structural types."""
    missing = REQUIRED_ENVELOPE_FIELDS - set(data.keys())
    assert not missing, f"Missing envelope fields: {missing}"

    assert isinstance(data["schema_version"], int), f"schema_version must be int, got {type(data['schema_version']).__name__}"
    assert data["schema_version"] == 1, f"schema_version must be 1, got {data['schema_version']}"
    assert isinstance(data["module"], str), "module must be str"
    assert data["capability_state"] in VALID_STATES, f"invalid capability_state: {data['capability_state']}"
    assert data["activity_state"] in ("idle", "running"), f"invalid activity_state: {data['activity_state']}"
    assert data["activity_label"] is None or isinstance(data["activity_label"], str)
    assert data["activity_progress"] is None or isinstance(data["activity_progress"], (int, float))
    assert data["severity"] in VALID_SEVERITIES, f"invalid severity: {data['severity']}"
    assert isinstance(data["reason"], dict), "reason must be dict"
    reason_missing = REQUIRED_REASON_FIELDS - set(data["reason"].keys())
    assert not reason_missing, f"Missing reason fields: {reason_missing}"
    assert isinstance(data["reason"]["code"], str) and len(data["reason"]["code"]) > 0
    assert isinstance(data["action"], dict), "action must be dict"
    assert isinstance(data["notices"], list), "notices must be list"
    assert isinstance(data["updated_at"], str), "updated_at must be str"
    assert data["updated_at"].endswith("Z"), f"updated_at must be Z-suffixed, got {data['updated_at']}"
    assert isinstance(data["ttl_seconds"], int), "ttl_seconds must be int"
    assert data["ttl_seconds"] > 0, "ttl_seconds must be positive"


def _assert_action_primary_shape(action_primary: dict | None) -> None:
    """Assert action.primary has all required fields when non-null, or is None."""
    if action_primary is None:
        return
    missing = REQUIRED_ACTION_PRIMARY_FIELDS - set(action_primary.keys())
    assert not missing, f"Missing action.primary fields: {missing}"
    assert isinstance(action_primary["verb"], str)
    assert isinstance(action_primary["label"], str)
    assert isinstance(action_primary["destructive"], bool)
    assert action_primary["destructive_scope"] is None or isinstance(action_primary["destructive_scope"], str)
    assert action_primary["destructive_effect"] is None or isinstance(action_primary["destructive_effect"], str)
    assert isinstance(action_primary["confirmation_required"], bool)
    assert isinstance(action_primary["scope"], str), f"scope must be str, got {type(action_primary['scope']).__name__}"
    assert isinstance(action_primary["scope_count"], int), f"scope_count must be int, got {type(action_primary['scope_count']).__name__}"
    assert isinstance(action_primary["command"], str)


# ---------------------------------------------------------------------------
# Envelope contract
# ---------------------------------------------------------------------------

class TestEnvelopeContract:
    """Validate the schema-v1 envelope structure itself."""

    def test_envelope_all_required_fields_present(self, tmp_path: Path) -> None:
        """Installation probe output contains all required envelope fields."""
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        data = _run_probe("installation", tmp_path)
        _assert_envelope_shape(data)

    def test_envelope_is_direct_not_pfresult_wrapped(self, tmp_path: Path) -> None:
        """Output is a direct envelope, not wrapped in PFResult ok/command/data envelope."""
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        data = _run_probe("installation", tmp_path)
        assert "ok" not in data, "Output is PFResult-wrapped, expected bare envelope"
        assert "command" not in data, "Output is PFResult-wrapped, expected bare envelope"
        assert "module" in data
        assert "capability_state" in data

    def test_schema_version_is_integer_1(self, tmp_path: Path) -> None:
        """schema_version must be the integer 1, never a string."""
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        data = _run_probe("installation", tmp_path)
        assert data["schema_version"] == 1
        assert isinstance(data["schema_version"], int)
        assert data["schema_version"] is not True  # not a bool masquerading

    def test_ready_state_action_primary_null(self, tmp_path: Path) -> None:
        """When capability_state is 'ready', action.primary must be null."""
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        data = _run_probe("installation", tmp_path)
        if data["capability_state"] == "ready":
            assert data["action"]["primary"] is None

    def test_envelope_ttl_3600_for_installation(self, tmp_path: Path) -> None:
        """Installation probe has ttl_seconds=3600."""
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        data = _run_probe("installation", tmp_path)
        assert data["ttl_seconds"] == 3600

    def test_envelope_ttl_3600_for_help(self, tmp_path: Path) -> None:
        """Help probe has ttl_seconds=3600."""
        data = _run_probe("help", tmp_path)
        assert data["ttl_seconds"] == 3600

    def test_action_primary_full_fields_non_null(self, tmp_path: Path) -> None:
        """Non-null action.primary has all required fields with correct types."""
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        # Use the worktrees vault which has no paperforge.json → missing_input → has action
        empty_vault = tmp_path / "no_config"
        empty_vault.mkdir()
        data = _run_probe("installation", empty_vault)
        assert data["action"]["primary"] is not None
        _assert_action_primary_shape(data["action"]["primary"])


# ---------------------------------------------------------------------------
# Installation probe states
# ---------------------------------------------------------------------------

class TestInstallationProbe:
    """State mapping for the installation module probe."""

    def test_missing_paperforge_json(self, tmp_path: Path) -> None:
        """No paperforge.json -> missing_input + set_config action."""
        data = _run_probe("installation", tmp_path)
        assert data["module"] == "installation"
        assert data["capability_state"] == "missing_input"
        assert data["severity"] == "warning"
        assert data["reason"]["code"] == "installation.config_missing"
        assert data["action"]["primary"] is not None
        _assert_action_primary_shape(data["action"]["primary"])
        assert data["action"]["primary"]["verb"] == "set_config"
        assert data["action"]["primary"]["label"] == "Set config"

    def test_corrupt_paperforge_json(self, tmp_path: Path) -> None:
        """Invalid JSON in paperforge.json -> unavailable + setup action."""
        (tmp_path / "paperforge.json").write_text("not valid json {{{", encoding="utf-8")
        data = _run_probe("installation", tmp_path)
        assert data["capability_state"] == "unavailable"
        assert data["severity"] == "error"
        assert data["reason"]["code"] == "installation.config_corrupt"
        assert data["action"]["primary"] is not None
        _assert_action_primary_shape(data["action"]["primary"])
        assert data["action"]["primary"]["verb"] == "setup"

    def test_empty_object_config_corrupt(self, tmp_path: Path) -> None:
        """Empty dict {} → config_corrupt/unavailable."""
        (tmp_path / "paperforge.json").write_text("{}", encoding="utf-8")
        data = _run_probe("installation", tmp_path)
        assert data["capability_state"] == "unavailable"
        assert data["severity"] == "error"
        assert data["reason"]["code"] == "installation.config_corrupt"
        assert data["action"]["primary"] is not None
        assert data["action"]["primary"]["verb"] == "setup"

    def test_list_config_corrupt(self, tmp_path: Path) -> None:
        """JSON array → config_corrupt/unavailable."""
        (tmp_path / "paperforge.json").write_text('["a", "b"]', encoding="utf-8")
        data = _run_probe("installation", tmp_path)
        assert data["capability_state"] == "unavailable"
        assert data["reason"]["code"] == "installation.config_corrupt"
        assert data["action"]["primary"]["verb"] == "setup"

    def test_primitive_config_corrupt(self, tmp_path: Path) -> None:
        """JSON string/number/true → config_corrupt/unavailable."""
        for content in ('"just a string"', '42', 'true'):
            (tmp_path / "paperforge.json").write_text(content, encoding="utf-8")
            data = _run_probe("installation", tmp_path)
            assert data["capability_state"] == "unavailable", f"content={content}"
            assert data["reason"]["code"] == "installation.config_corrupt"

    def test_unrecognized_keys_config_corrupt(self, tmp_path: Path) -> None:
        """Dict with keys but no vault_config or legacy path keys → config_corrupt."""
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"name": "Foo", "version": "1.0"}), encoding="utf-8",
        )
        data = _run_probe("installation", tmp_path)
        assert data["capability_state"] == "unavailable"
        assert data["reason"]["code"] == "installation.config_corrupt"
        assert data["action"]["primary"]["verb"] == "setup"

    def test_v2_vault_config_accepted(self, tmp_path: Path) -> None:
        """v2 format with vault_config is accepted as valid config."""
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"vault_config": {"system_dir": "99_System"}}), encoding="utf-8",
        )
        data = _run_probe("installation", tmp_path)
        assert data["capability_state"] == "ready"
        assert data["reason"]["code"] == "installation.ready"

    def test_legacy_path_keys_accepted(self, tmp_path: Path) -> None:
        """Legacy format with at least one legacy path key is accepted."""
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System", "resources_dir": "Resources"}), encoding="utf-8",
        )
        data = _run_probe("installation", tmp_path)
        assert data["capability_state"] == "ready"
        assert data["reason"]["code"] == "installation.ready"

    def test_ready_reason_code(self, tmp_path: Path) -> None:
        """Ready state has correct reason code and null action."""
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        data = _run_probe("installation", tmp_path)
        assert data["capability_state"] == "ready"
        assert data["severity"] == "ok"
        assert data["reason"]["code"] == "installation.ready"
        assert data["action"]["primary"] is None


# ---------------------------------------------------------------------------
# Help probe states
# ---------------------------------------------------------------------------

class TestHelpProbe:
    """State mapping for the help module probe."""

    def test_ready(self, tmp_path: Path) -> None:
        """Help probe returns ready when skill source is available."""
        data = _run_probe("help", tmp_path)
        assert data["module"] == "help"
        assert data["capability_state"] == "ready"
        assert data["severity"] == "ok"
        assert data["action"]["primary"] is None
        assert data["reason"]["code"] == "help.ready"

    def test_limited_when_skill_source_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When SKILL.md is absent, help probe returns limited with setup recovery."""
        from paperforge.commands.probe import probe_help

        orig = Path.exists
        def fake_exists(self) -> bool:
            s = str(self)
            if "SKILL.md" in s and "skills" in s:
                return False
            return orig(self)

        monkeypatch.setattr(Path, "exists", fake_exists)
        envelope = probe_help(tmp_path)
        assert envelope["capability_state"] == "limited"
        assert envelope["severity"] == "warning"
        assert envelope["reason"]["code"] == "help.docs_missing"
        action = envelope["action"]["primary"]
        _assert_action_primary_shape(action)
        assert action["verb"] == "setup"


# ---------------------------------------------------------------------------
# CLI argument validation
# ---------------------------------------------------------------------------

class TestProbeCliArgs:
    """CLI argument validation for the probe command."""

    def test_rejects_unsupported_module(self, tmp_path: Path) -> None:
        """Unknown module name is rejected by argparse."""
        result = subprocess.run(
            [sys.executable, "-m", "paperforge", "--vault", str(tmp_path),
             "probe", "maintenance", "--json"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode != 0

    def test_rejects_help_module(self, tmp_path: Path) -> None:
        """--help/-h on probe subcommand shows usage."""
        result = subprocess.run(
            [sys.executable, "-m", "paperforge", "--vault", str(tmp_path),
             "probe", "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "usage:" in result.stderr.lower()

    def test_module_required(self, tmp_path: Path) -> None:
        """probe without a module argument fails."""
        result = subprocess.run(
            [sys.executable, "-m", "paperforge", "--vault", str(tmp_path),
             "probe", "--json"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode != 0

# ---------------------------------------------------------------------------
# Library probe states (Issue #78)
# ---------------------------------------------------------------------------

class TestLibraryProbe:
    """State mapping for the library module probe."""

    def test_missing_paperforge_json(self, tmp_path: Path) -> None:
        """No paperforge.json -> missing_input + set_config action."""
        data = _run_probe('library', tmp_path)
        assert data['module'] == 'library'
        assert data['capability_state'] == 'missing_input'
        assert data['severity'] == 'warning'
        assert data['reason']['code'] == 'library.config_missing'
        assert data['action']['primary'] is not None
        _assert_action_primary_shape(data['action']['primary'])
        assert data['action']['primary']['verb'] == 'set_config'

    def test_corrupt_config(self, tmp_path: Path) -> None:
        """Corrupt JSON -> unavailable + setup action."""
        (tmp_path / 'paperforge.json').write_text('{{{', encoding='utf-8')
        data = _run_probe('library', tmp_path)
        assert data['capability_state'] == 'unavailable'
        assert data['severity'] == 'error'
        assert data['reason']['code'] == 'library.config_corrupt'

    def test_zotero_not_configured(self, tmp_path: Path) -> None:
        """Config exists but no zotero_data_dir -> missing_input."""
        (tmp_path / 'paperforge.json').write_text(
            json.dumps({'system_dir': '99_System'}), encoding='utf-8',
        )
        data = _run_probe('library', tmp_path)
        assert data['capability_state'] == 'missing_input'
        assert data['reason']['code'] == 'library.zotero_missing'
        assert data['action']['primary']['verb'] == 'set_config'

    def test_envelope_shape(self, tmp_path: Path) -> None:
        """Library envelope has all required fields."""
        (tmp_path / 'paperforge.json').write_text(
            json.dumps({'system_dir': '99_System', 'zotero_data_dir': str(tmp_path)}), encoding='utf-8',
        )
        data = _run_probe('library', tmp_path)
        _assert_envelope_shape(data)
        assert data['ttl_seconds'] == 300

    def test_primitive_config_corrupt(self, tmp_path: Path) -> None:
        """Non-dict config -> unavailable."""
        (tmp_path / 'paperforge.json').write_text('42', encoding='utf-8')
        data = _run_probe('library', tmp_path)
        assert data['capability_state'] == 'unavailable'
        assert data['reason']['code'] == 'library.config_corrupt'

# ---------------------------------------------------------------------------
# OCR probe states (Issue #78)
# ---------------------------------------------------------------------------

    def test_unrecognized_config_corrupt(self, tmp_path: Path) -> None:
        """Parseable dict without recognized keys -> config_corrupt/unavailable."""
        (tmp_path / 'paperforge.json').write_text(
            json.dumps({"name": "Foo", "version": "1.0"}), encoding='utf-8',
        )
        data = _run_probe('library', tmp_path)
        assert data['capability_state'] == 'unavailable'
        assert data['severity'] == 'error'
        assert data['reason']['code'] == 'library.config_corrupt'
        assert data['action']['primary']['verb'] == 'setup'

    def test_sync_failed_nonzero_exit_code(self, tmp_path: Path) -> None:
        """Nonzero last_operation_exit_code -> sync_failed envelope (direct call)."""
        from paperforge.commands import probe as probe_mod
        (tmp_path / 'paperforge.json').write_text(
            json.dumps({"system_dir": "99_System", "zotero_data_dir": str(tmp_path)}), encoding='utf-8',
        )
        data = probe_mod.probe_library(tmp_path, last_operation_exit_code=7)
        assert data['module'] == 'library'
        assert data['capability_state'] == 'needs_action'
        assert data['severity'] == 'error'
        assert data['reason']['code'] == 'library.sync_failed'
        assert 'exit code 7' in data['reason']['text']
        assert data['action']['primary']['verb'] == 'sync'
        assert data['action']['primary']['command'] == 'paperforge sync'

    def test_sync_success_zero_exit_code_normal(self, tmp_path: Path) -> None:
        """Zero last_operation_exit_code -> normal probe, not sync_failed."""
        from paperforge.commands import probe as probe_mod
        (tmp_path / 'paperforge.json').write_text(
            json.dumps({"system_dir": "99_System", "zotero_data_dir": str(tmp_path)}), encoding='utf-8',
        )
        data = probe_mod.probe_library(tmp_path, last_operation_exit_code=0)
        assert data['module'] == 'library'
        assert data['reason']['code'] != 'library.sync_failed'
        # Normal probe falls through to index check (missing in fresh tmp_path)
        assert data['reason']['code'] == 'library.index_missing'


class TestOcrProbe:
    """State mapping for the OCR module probe."""

    def test_missing_paperforge_json(self, tmp_path: Path) -> None:
        """No paperforge.json -> missing_input + set_config action."""
        data = _run_probe('ocr', tmp_path)
        assert data['module'] == 'ocr'
        assert data['capability_state'] == 'missing_input'
        assert data['severity'] == 'warning'
        assert data['reason']['code'] == 'ocr.config_missing'
        assert data['action']['primary']['verb'] == 'set_config'

    def test_corrupt_config(self, tmp_path: Path) -> None:
        """Corrupt JSON -> unavailable."""
        (tmp_path / 'paperforge.json').write_text('{{{', encoding='utf-8')
        data = _run_probe('ocr', tmp_path)
        assert data['capability_state'] == 'unavailable'
        assert data['reason']['code'] == 'ocr.config_corrupt'

    def test_api_key_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Config exists but no API token anywhere -> missing_input."""
        from paperforge.commands import probe as probe_mod
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        # Mock _resolve_paddleocr_token to return empty (no token from any source)
        monkeypatch.setattr("paperforge.worker.ocr._resolve_paddleocr_token", lambda v: "")
        data = probe_mod.probe_ocr(tmp_path)
        assert data["capability_state"] == "missing_input"
        assert data["reason"]["code"] == "ocr.api_key_missing"

    def test_non_dict_config_corrupt(self, tmp_path: Path) -> None:
        """Non-dict config -> unavailable."""
        (tmp_path / 'paperforge.json').write_text('true', encoding='utf-8')
        data = _run_probe('ocr', tmp_path)
        assert data['capability_state'] == 'unavailable'
        assert data['reason']['code'] == 'ocr.config_corrupt'
    def test_unrecognized_config_corrupt(self, tmp_path: Path) -> None:
        """Parseable dict without recognized keys -> config_corrupt/unavailable."""
        (tmp_path / 'paperforge.json').write_text(
            json.dumps({"name": "Foo", "version": "1.0"}), encoding='utf-8',
        )
        data = _run_probe('ocr', tmp_path)
        assert data['capability_state'] == 'unavailable'
        assert data['severity'] == 'error'
        assert data['reason']['code'] == 'ocr.config_corrupt'
        assert data['action']['primary']['verb'] == 'setup'



# ---------------------------------------------------------------------------
# Memory probe states (Issue #78)
# ---------------------------------------------------------------------------

class TestMemoryProbe:
    """State mapping for the memory module probe."""

    def test_db_missing(self, tmp_path: Path) -> None:
        """No paperforge.db -> needs_action + run action."""
        data = _run_probe("memory", tmp_path)
        assert data["module"] == "memory"
        assert data["capability_state"] == "needs_action"
        assert data["reason"]["code"] == "memory.db_missing"
        assert data["action"]["primary"] is not None
        _assert_action_primary_shape(data["action"]["primary"])
        assert data["action"]["primary"]["verb"] == "run"

    def test_envelope_shape(self, tmp_path: Path) -> None:
        """Memory envelope has all required fields."""
        data = _run_probe('memory', tmp_path)
        _assert_envelope_shape(data)
        assert data['ttl_seconds'] == 300

    def test_db_corrupt(self, tmp_path: Path) -> None:
        """Corrupt database -> unavailable + run action."""
        # Create paperforge.json so canonical path resolution works
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        indexes = tmp_path / "99_System" / "PaperForge" / "indexes"
        indexes.mkdir(parents=True, exist_ok=True)
        (indexes / "paperforge.db").write_text("not a database", encoding="utf-8")
        data = _run_probe("memory", tmp_path)
        assert data["capability_state"] == "unavailable"
        assert data["reason"]["code"] == "memory.db_corrupt"
        action = data["action"]["primary"]
        _assert_action_primary_shape(action)
        assert action["verb"] == "run"
        assert action["command"] == "paperforge memory build"


# ---------------------------------------------------------------------------
# Library/OCR/Memory canonical probe tests (Issue #78 repair)
# ---------------------------------------------------------------------------

class TestLibraryProbeCanonical:
    """Library probe with canonical formal-library.json validation."""

    def test_ready_with_canonical_index(self, tmp_path: Path) -> None:
        """Valid formal-library.json + matching export hash -> ready."""
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System", "zotero_data_dir": str(tmp_path)}),
            encoding="utf-8",
        )
        indexes_dir = tmp_path / "99_System" / "PaperForge" / "indexes"
        indexes_dir.mkdir(parents=True, exist_ok=True)
        (indexes_dir / "formal-library.json").write_text(json.dumps({
            "schema_version": "2",
            "items": [{"zotero_key": "ABC123", "title": "Test Paper"}],
            "paper_count": 1,
        }), encoding="utf-8")

        data = _run_probe("library", tmp_path)
        assert data["module"] == "library"
        assert data["capability_state"] != "unavailable"
        assert data["severity"] != "error"
        _assert_envelope_shape(data)

    def test_malformed_index(self, tmp_path: Path) -> None:
        """Non-dict non-list formal-library.json -> needs_action."""
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System", "zotero_data_dir": str(tmp_path)}),
            encoding="utf-8",
        )
        indexes_dir = tmp_path / "99_System" / "PaperForge" / "indexes"
        indexes_dir.mkdir(parents=True, exist_ok=True)
        (indexes_dir / "formal-library.json").write_text('"just a string"', encoding="utf-8")

        data = _run_probe("library", tmp_path)
        assert data["capability_state"] == "needs_action"
        assert data["reason"]["code"] in ("library.index_corrupt", "library.index_legacy")


class TestOcrProbeCanonical:
    """OCR probe with PADDLEOCR_API_TOKEN env credential."""

    def test_credential_from_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """PADDLEOCR_API_TOKEN in env -> passes credential check."""
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        monkeypatch.setenv("PADDLEOCR_API_TOKEN", "test-token-12345")

        data = _run_probe("ocr", tmp_path)
        assert data["reason"]["code"] != "ocr.api_key_missing"
        _assert_envelope_shape(data)

    def test_no_credential_no_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """No PADDLEOCR_API_TOKEN in env + no config -> missing_input."""
        monkeypatch.delenv("PADDLEOCR_API_TOKEN", raising=False)
        monkeypatch.delenv("PADDLEOCR_API_TOKEN_USER", raising=False)
        data = _run_probe("ocr", tmp_path)
        assert data["capability_state"] == "missing_input"
        assert data["reason"]["code"] == "ocr.config_missing"


class TestMemoryProbeCanonical:
    """Memory probe distinguishing corruption from schema mismatch."""

    def test_populated_db_old_schema(self, tmp_path: Path) -> None:
        """DB with papers but old schema -> migration_needed."""
        import sqlite3
        # Create paperforge.json for canonical path resolution
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        indexes = tmp_path / "99_System" / "PaperForge" / "indexes"
        indexes.mkdir(parents=True, exist_ok=True)
        db_path = indexes / "paperforge.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE papers (zotero_key TEXT, title TEXT)")
        conn.execute("CREATE TABLE meta (key TEXT, value TEXT)")
        conn.execute("INSERT INTO meta VALUES ('schema_version', '3')")
        conn.execute("INSERT INTO papers VALUES ('KEY1', 'Test Paper')")
        conn.commit()
        conn.close()

        data = _run_probe("memory", tmp_path)
        _assert_envelope_shape(data)
        assert data["reason"]["code"] == "memory.migration_needed"
        assert data["action"]["primary"]["verb"] == "rebuild_index"


# ---------------------------------------------------------------------------
# All-probe smoke test (Issue #78)
# ---------------------------------------------------------------------------

class TestAllProbes:
    """Verify all five real probes emit valid envelopes."""

    @pytest.mark.parametrize('module', ['installation', 'library', 'ocr', 'memory', 'help'])
    def test_probe_emits_valid_envelope(self, module: str, tmp_path: Path) -> None:
        """Every real probe emits a valid envelope."""
        if module in ('installation', 'library', 'ocr'):
            (tmp_path / 'paperforge.json').write_text(
                json.dumps({'system_dir': '99_System'}), encoding='utf-8',
            )
        data = _run_probe(module, tmp_path)
        _assert_envelope_shape(data)
        assert data['module'] == module
        assert data['severity'] in VALID_SEVERITIES

    def test_cli_accepts_all_modules(self, tmp_path: Path) -> None:
        """CLI accepts all five module names."""
        (tmp_path / 'paperforge.json').write_text(
            json.dumps({'system_dir': '99_System'}), encoding='utf-8',
        )
        for mod in ('installation', 'library', 'ocr', 'memory', 'help'):
            result = subprocess.run(
                [sys.executable, '-m', 'paperforge', '--vault', str(tmp_path),
                 'probe', mod, '--json'],
                capture_output=True, text=True, timeout=15,
            )
            assert result.returncode == 0, f'module={mod}: {result.stderr[:200]}'



# ---------------------------------------------------------------------------
# Issue #78 concrete fix tests
# ---------------------------------------------------------------------------

class TestOcrConcreteFixes:
    """Concrete correctness fixes for Issue #78 OCR probe."""

    def test_healthy_display_action_none_is_ready(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Row with display_action='none', no failures → ready."""
        from paperforge.commands import probe as probe_mod
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        monkeypatch.setenv("PADDLEOCR_API_TOKEN", "test-token")

        class FakeRow:
            status = "ok"
            health = "green"
            display_action = "none"
        monkeypatch.setattr("paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda v: [FakeRow()])
        monkeypatch.setattr("paperforge.ocr_diagnostics.ocr_doctor",
            lambda config=None, live=False: {"passed": True})

        data = probe_mod.probe_ocr(tmp_path)
        assert data["capability_state"] == "ready"
        assert data["severity"] == "ok"
        assert data["reason"]["code"] == "ocr.ready"

    def test_running_rows_independent_from_actionable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Running rows with display_action='retry_ocr' → needs_action with activity overlay."""
        from paperforge.commands import probe as probe_mod
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        monkeypatch.setenv("PADDLEOCR_API_TOKEN", "test-token")

        class FakeRow:
            status = "running"
            health = "green"
            display_action = "retry_ocr"
        monkeypatch.setattr("paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda v: [FakeRow()])
        monkeypatch.setattr("paperforge.ocr_diagnostics.ocr_doctor",
            lambda config=None, live=False: {"passed": True})

        data = probe_mod.probe_ocr(tmp_path)
        # Running status → activity overlay
        assert data["activity_state"] == "running"
        assert data["activity_label"] is not None
        assert data["activity_progress"] is not None
        # Independent actionable state preserved
        assert data["capability_state"] == "needs_action"
        assert data["reason"]["code"] == "ocr.quality_failures"

    def test_collect_maintenance_rows_exception_returns_unknown(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When collect_maintenance_rows raises → unknown/probe, not empty run."""
        from paperforge.commands import probe as probe_mod
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        monkeypatch.setenv("PADDLEOCR_API_TOKEN", "test-token")
        monkeypatch.setattr("paperforge.ocr_diagnostics.ocr_doctor",
            lambda config=None, live=False: {"passed": True})
        def _raise(*args, **kwargs):
            raise RuntimeError("boom")
        monkeypatch.setattr("paperforge.worker.ocr_maintenance.collect_maintenance_rows", _raise)

        data = probe_mod.probe_ocr(tmp_path)
        assert data["capability_state"] == "unknown"
        assert data["severity"] == "unknown"
        assert data["reason"]["code"] == "ocr.probe_failed"
        assert data["action"]["primary"]["verb"] == "probe"


class TestMemoryConcreteFixes:
    """Concrete correctness fixes for Issue #78 Memory probe."""

    def test_get_memory_status_exception_returns_unknown(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When get_memory_status raises → unknown/probe, not unavailable/rebuild."""
        from paperforge.commands import probe as probe_mod
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        def _raise(*args, **kwargs):
            raise RuntimeError("db broken")
        monkeypatch.setattr("paperforge.memory.query.get_memory_status", _raise)

        data = probe_mod.probe_memory(tmp_path)
        assert data["capability_state"] == "unknown"
        assert data["severity"] == "unknown"
        assert data["reason"]["code"] == "memory.probe_failed"
        assert data["action"]["primary"]["verb"] == "probe"


class TestOcrPriorityOrdering:
    """OCR probe priority: redo > run > rebuild > investigate (Issue #78 repair)."""

    def test_pending_overrides_provider_unreachable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Pending + provider unreachable -> needs_action/run, NOT limited/investigate."""
        from paperforge.commands import probe as probe_mod
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        monkeypatch.setenv("PADDLEOCR_API_TOKEN", "test-token")
        monkeypatch.setattr("paperforge.ocr_diagnostics.ocr_doctor",
            lambda config=None, live=False: {"passed": False, "error": "unreachable"})

        class FakePendingRow:
            status = "pending"
            health = "green"
            display_action = "none"
        monkeypatch.setattr("paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda v: [FakePendingRow()])

        data = probe_mod.probe_ocr(tmp_path)
        # Pending (run) beats provider unreachable (investigate)
        assert data["capability_state"] == "needs_action"
        assert data["reason"]["code"] == "ocr.pending"
        assert data["action"]["primary"]["verb"] == "run"

    def test_degraded_overrides_unexpected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Degraded + unexpected action -> needs_action/rebuild, NOT limited/investigate."""
        from paperforge.commands import probe as probe_mod
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        monkeypatch.setenv("PADDLEOCR_API_TOKEN", "test-token")
        monkeypatch.setattr("paperforge.ocr_diagnostics.ocr_doctor",
            lambda config=None, live=False: {"passed": True})

        class FakeDegradedRow:
            status = "done"
            health = "yellow"
            display_action = "rebuild_result"
            display_severity = "actionable"

        class FakeUnexpectedRow:
            status = "done"
            health = "green"
            display_action = "future_action"
            display_severity = "actionable"

        monkeypatch.setattr("paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda v: [FakeDegradedRow(), FakeUnexpectedRow()])

        data = probe_mod.probe_ocr(tmp_path)
        # Degraded (rebuild) beats unexpected (investigate)
        assert data["capability_state"] == "needs_action"
        assert data["reason"]["code"] == "ocr.artifacts_stale"
        assert data["action"]["primary"]["verb"] == "rebuild_derived"

    def test_redo_overrides_pending(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Redo + pending rows -> redo action, NOT run."""
        from paperforge.commands import probe as probe_mod
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        monkeypatch.setenv("PADDLEOCR_API_TOKEN", "test-token")
        monkeypatch.setattr("paperforge.ocr_diagnostics.ocr_doctor",
            lambda config=None, live=False: {"passed": True})

        class FakeRedoPendingRow:
            status = "pending"
            health = "red"
            display_action = "retry_ocr"
        monkeypatch.setattr("paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda v: [FakeRedoPendingRow()])

        data = probe_mod.probe_ocr(tmp_path)
        # Redo (retry_ocr) beats pending (run)
        assert data["capability_state"] == "needs_action"
        assert data["reason"]["code"] == "ocr.quality_failures"
        assert data["action"]["primary"]["verb"] == "redo"



class TestOcrRebuildResultNonDestructive:
    """rebuild_result rows must never become destructive redo (Issue #78 repair)."""

    def test_red_health_rebuild_result_is_rebuild_not_redo(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Red health + display_action='rebuild_result' -> rebuild_derived, NOT redo."""
        from paperforge.commands import probe as probe_mod
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        monkeypatch.setenv("PADDLEOCR_API_TOKEN", "test-token")
        monkeypatch.setattr("paperforge.ocr_diagnostics.ocr_doctor",
            lambda config=None, live=False: {"passed": True})

        class FakeRebuildRedRow:
            status = "done"
            health = "red"
            display_action = "rebuild_result"

        monkeypatch.setattr("paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda v: [FakeRebuildRedRow()])

        data = probe_mod.probe_ocr(tmp_path)
        # rebuild_result must never become redo, even with red health
        assert data["capability_state"] == "needs_action"
        assert data["reason"]["code"] == "ocr.artifacts_stale"
        assert data["action"]["primary"]["verb"] == "rebuild_derived"
        assert data["action"]["primary"]["destructive"] == False


class TestOcrActivityProgress:
    """OCR activity progress current = terminal/completed count, not running/queued."""

    def test_queued_only_batch_progress_zero_of_N(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """All queued -> progress current=0, total=N."""
        from paperforge.commands import probe as probe_mod
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        monkeypatch.setenv("PADDLEOCR_API_TOKEN", "test-token")
        monkeypatch.setattr("paperforge.ocr_diagnostics.ocr_doctor",
            lambda config=None, live=False: {"passed": True})

        rows = []
        for i in range(5):
            class FakeQueuedRow:
                status = "queued"
                health = "green"
                display_action = "none"
            rows.append(FakeQueuedRow())

        monkeypatch.setattr("paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda v: rows)

        data = probe_mod.probe_ocr(tmp_path)
        assert data["activity_state"] == "running"
        assert data["activity_progress"] is not None
        assert data["activity_progress"]["current"] == 0  # no completed rows
        assert data["activity_progress"]["total"] == 5
        assert "0/5" in data["activity_label"]

    def test_mixed_done_queued_progress_completed_count(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """3 done_degraded + 2 queued -> progress current=3, total=5."""
        from paperforge.commands import probe as probe_mod
        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        monkeypatch.setenv("PADDLEOCR_API_TOKEN", "test-token")
        monkeypatch.setattr("paperforge.ocr_diagnostics.ocr_doctor",
            lambda config=None, live=False: {"passed": True})

        rows = []
        for i in range(3):
            class FakeDoneRow:
                status = "done_degraded"
                health = "yellow"
                display_action = "rebuild_result"
            rows.append(FakeDoneRow())
        for i in range(2):
            class FakeQueuedRow:
                status = "queued"
                health = "green"
                display_action = "none"
            rows.append(FakeQueuedRow())

        monkeypatch.setattr("paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda v: rows)

        data = probe_mod.probe_ocr(tmp_path)
        assert data["activity_state"] == "running"
        assert data["activity_progress"] is not None
        assert data["activity_progress"]["current"] == 3  # 3 completed rows
        assert data["activity_progress"]["total"] == 5
        assert "3/5" in data["activity_label"]
