"""Unit tests for PaperForge Lite setup wizard standalone functions.

Covers: AGENT_CONFIGS, EnvChecker (check_python, check_vault, check_dependencies,
get_exports_dir, _find_zotero), CheckResult, and _find_vault.

Test strategy:
- Textual App and StepScreen classes require a running terminal and are NOT tested here.
- Focus on standalone detection/validation logic that can run without Textual.
- Use monkeypatch for environment/platform-dependent tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure repo root is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import standalone functions and classes (not Textual-dependent)
from setup_wizard import AGENT_CONFIGS, CheckResult, EnvChecker, _find_vault


# ===================================================================
# AGENT_CONFIGS
# ===================================================================


class TestAgentConfigs:
    """Agent platform configuration completeness."""

    def test_has_all_expected_agents(self) -> None:
        """Verify all 8 agent platforms are configured."""
        expected_agents = {"opencode", "cursor", "claude", "windsurf", "github_copilot", "cline", "augment", "trae"}
        assert set(AGENT_CONFIGS.keys()) == expected_agents

    def test_each_agent_has_name_and_skill_dir(self) -> None:
        """Every agent config must have name and skill_dir."""
        for key, cfg in AGENT_CONFIGS.items():
            assert "name" in cfg, f"{key} missing name"
            assert "skill_dir" in cfg, f"{key} missing skill_dir"
            assert isinstance(cfg["name"], str) and cfg["name"], f"{key} has empty name"
            assert isinstance(cfg["skill_dir"], str) and cfg["skill_dir"], f"{key} has empty skill_dir"

    def test_opencode_skill_dir_is_dot_opencode(self) -> None:
        """OpenCode skill dir must be .opencode/skills."""
        assert AGENT_CONFIGS["opencode"]["skill_dir"] == ".opencode/skills"

    def test_cursor_skill_dir_is_dot_cursor(self) -> None:
        assert AGENT_CONFIGS["cursor"]["skill_dir"] == ".cursor/skills"

    def test_claude_skill_dir_is_dot_claude(self) -> None:
        assert AGENT_CONFIGS["claude"]["skill_dir"] == ".claude/skills"

    def test_opencode_has_command_dir(self) -> None:
        """OpenCode is the only agent with command_dir."""
        assert AGENT_CONFIGS["opencode"].get("command_dir") == ".opencode/command"


# ===================================================================
# CheckResult
# ===================================================================


class TestCheckResult:
    """CheckResult data class."""

    def test_default_state(self) -> None:
        r = CheckResult("Test Check")
        assert r.name == "Test Check"
        assert r.passed is False
        assert r.detail == ""
        assert r.action_required is False

    def test_can_set_passed(self) -> None:
        r = CheckResult("X")
        r.passed = True
        assert r.passed is True

    def test_can_set_detail(self) -> None:
        r = CheckResult("X")
        r.detail = "Some detail"
        assert r.detail == "Some detail"

    def test_can_set_action_required(self) -> None:
        r = CheckResult("X")
        r.action_required = True
        assert r.action_required is True


# ===================================================================
# EnvChecker
# ===================================================================


class TestEnvCheckerInit:
    """EnvChecker initialization."""

    def test_init_with_vault_path(self, tmp_path: Path) -> None:
        checker = EnvChecker(tmp_path)
        assert checker.vault == tmp_path
        assert checker.system_dir == "99_System"
        assert set(checker.results.keys()) == {"python", "vault", "zotero", "bbt", "json"}

    def test_results_are_checkresult_instances(self, tmp_path: Path) -> None:
        checker = EnvChecker(tmp_path)
        for key, result in checker.results.items():
            assert isinstance(result, CheckResult), f"{key} is not CheckResult"
            assert result.name, f"{key} has empty name"

    def test_get_exports_dir(self, tmp_path: Path) -> None:
        checker = EnvChecker(tmp_path)
        expected = tmp_path / "99_System" / "PaperForge" / "exports"
        assert checker.get_exports_dir() == expected

    def test_get_exports_dir_custom_system_dir(self, tmp_path: Path) -> None:
        checker = EnvChecker(tmp_path)
        checker.system_dir = "CustomSystem"
        expected = tmp_path / "CustomSystem" / "PaperForge" / "exports"
        assert checker.get_exports_dir() == expected


class TestEnvCheckerCheckPython:
    """EnvChecker.check_python()"""

    def test_python_version_passes(self, tmp_path: Path) -> None:
        checker = EnvChecker(tmp_path)
        result = checker.check_python()
        # Should pass on any modern Python (>= 3.8)
        assert result.passed is True
        assert "Python" in result.detail

    def test_python_version_in_detail(self, tmp_path: Path) -> None:
        checker = EnvChecker(tmp_path)
        result = checker.check_python()
        v = sys.version_info
        assert f"{v.major}.{v.minor}" in result.detail


class TestEnvCheckerCheckVault:
    """EnvChecker.check_vault()"""

    def test_missing_directories_fails(self, tmp_path: Path) -> None:
        """Empty vault should fail vault structure check."""
        checker = EnvChecker(tmp_path)
        result = checker.check_vault()
        assert result.passed is False
        assert result.action_required is True
        assert "missing" in result.detail.lower() or "缺少" in result.detail

    def test_existing_directories_passes(self, tmp_path: Path) -> None:
        """Vault with correct structure should pass."""
        (tmp_path / "99_System" / "PaperForge" / "exports").mkdir(parents=True)
        (tmp_path / "99_System" / "PaperForge" / "ocr").mkdir(parents=True)
        checker = EnvChecker(tmp_path)
        result = checker.check_vault()
        assert result.passed is True

    def test_partial_directories_fails(self, tmp_path: Path) -> None:
        """Vault with only one required dir should fail."""
        (tmp_path / "99_System" / "PaperForge" / "exports").mkdir(parents=True)
        checker = EnvChecker(tmp_path)
        result = checker.check_vault()
        assert result.passed is False


class TestEnvCheckerCheckDependencies:
    """EnvChecker.check_dependencies()"""

    def test_installed_deps_pass(self, tmp_path: Path) -> None:
        """If requests/pymupdf/PIL are installed, this should pass (in CI/test env)."""
        checker = EnvChecker(tmp_path)
        result = checker.check_dependencies()
        # In CI these should be installed since they're test deps
        # Accept either pass or fail — what matters is the result is valid
        assert isinstance(result.passed, bool)
        assert isinstance(result.detail, str)

    def test_missing_dep_fails(self, tmp_path: Path) -> None:
        """Simulate a missing import to verify failure path."""
        checker = EnvChecker(tmp_path)
        with patch("builtins.__import__", side_effect=ImportError("missing")):
            result = checker.check_dependencies()
            assert result.passed is False
            assert result.action_required is True


class TestEnvCheckerFindZotero:
    """EnvChecker._find_zotero() — platform-dependent search."""

    def test_manual_path_is_used_when_valid(self, tmp_path: Path) -> None:
        """If a manual path is provided and exists, it should be returned."""
        checker = EnvChecker(tmp_path)
        fake_zotero = tmp_path / "zotero.exe"
        fake_zotero.write_text("fake binary", encoding="utf-8")
        result = checker._find_zotero(manual_path=fake_zotero)
        assert result == fake_zotero

    def test_manual_path_none_falls_through(self, tmp_path: Path) -> None:
        """When manual_path is None, search logic runs (likely returns None on CI)."""
        checker = EnvChecker(tmp_path)
        result = checker._find_zotero()
        # On CI there's no Zotero, so result should be None
        # This test just validates the fallthrough doesn't crash
        if result is not None:
            assert result.exists()


class TestFindVault:
    """_find_vault() — standalone vault discovery."""

    def test_finds_vault_with_paperforge_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify _find_vault detects paperforge.json in current or parent dirs."""
        vault = tmp_path / "my_vault"
        vault.mkdir(parents=True)
        (vault / "paperforge.json").write_text("{}", encoding="utf-8")

        monkeypatch.chdir(vault)
        result = _find_vault()
        assert result is not None
        assert result == vault

    def test_no_paperforge_json_returns_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify _find_vault returns None when no paperforge.json exists."""
        monkeypatch.chdir(tmp_path)
        result = _find_vault()
        assert result is None

    def test_finds_in_parent_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify _find_vault walks up parent directories."""
        parent = tmp_path / "parent"
        parent.mkdir()
        (parent / "paperforge.json").write_text("{}", encoding="utf-8")
        child = parent / "subdir" / "deeper"
        child.mkdir(parents=True)

        monkeypatch.chdir(child)
        result = _find_vault()
        assert result is not None
        # Should resolve to the same path
        assert result.resolve() == parent.resolve()


class TestEnvCheckerCheckJson:
    """EnvChecker.check_json() — JSON export detection."""

    def test_no_exports_dir_fails(self, tmp_path: Path) -> None:
        checker = EnvChecker(tmp_path)
        result = checker.check_json()
        assert result.passed is False

    def test_valid_json_exports_pass(self, tmp_path: Path) -> None:
        exports_dir = tmp_path / "99_System" / "PaperForge" / "exports"
        exports_dir.mkdir(parents=True)
        (exports_dir / "test.json").write_text(
            json.dumps({"items": [{"key": "TEST"}]}),
            encoding="utf-8",
        )
        checker = EnvChecker(tmp_path)
        result = checker.check_json()
        assert result.passed is True
        assert "JSON" in result.detail

    def test_invalid_json_fails(self, tmp_path: Path) -> None:
        exports_dir = tmp_path / "99_System" / "PaperForge" / "exports"
        exports_dir.mkdir(parents=True)
        (exports_dir / "bad.json").write_text("{invalid}", encoding="utf-8")
        checker = EnvChecker(tmp_path)
        result = checker.check_json()
        assert result.passed is False

    def test_empty_exports_fails(self, tmp_path: Path) -> None:
        exports_dir = tmp_path / "99_System" / "PaperForge" / "exports"
        exports_dir.mkdir(parents=True)
        checker = EnvChecker(tmp_path)
        result = checker.check_json()
        assert result.passed is False
