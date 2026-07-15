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


def _run_probe(module: str, vault: Path, extra_args: list[str] | None = None) -> dict:
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
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
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
             "probe", "ocr", "--json"],
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
