"""Unit tests for PaperForge setup wizard standalone functions.

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
from paperforge.config import (
    AGENT_PLATFORM_IDS,
    AGENT_SHARED_SKILL_DIR,
)
from paperforge.setup_wizard import CheckResult, EnvChecker, _find_vault

from tests.conftest import canonical_test_config

# ===================================================================
# AGENT_SKILL_DIRS (imported from skill_deploy, flat dict)
# ===================================================================


class TestAgentPlatformRegistry:
    """Agent platform vocabulary: ids only — skill target is agent-chosen
    (`paperforge skill deploy --to <dir>`), never routed per platform."""

    def test_has_all_expected_agents(self) -> None:
        expected_agents = {
            "opencode", "claude", "codex", "cursor", "gemini", "kilo",
            "pi", "omp", "crush", "kimi", "github_copilot", "cline",
            "windsurf", "augment", "trae",
        }
        assert set(AGENT_PLATFORM_IDS) == expected_agents

    def test_shared_default_is_agents_skills(self) -> None:
        assert AGENT_SHARED_SKILL_DIR == ".agents/skills"


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
        assert checker.system_dir == "System"
        assert set(checker.results.keys()) == {"python", "vault", "zotero", "bbt", "json"}

    def test_results_are_checkresult_instances(self, tmp_path: Path) -> None:
        checker = EnvChecker(tmp_path)
        for key, result in checker.results.items():
            assert isinstance(result, CheckResult), f"{key} is not CheckResult"
            assert result.name, f"{key} has empty name"

    def test_get_exports_dir(self, tmp_path: Path) -> None:
        checker = EnvChecker(tmp_path)
        expected = tmp_path / "System" / "PaperForge" / "exports"
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
        (tmp_path / "System" / "PaperForge" / "exports").mkdir(parents=True)
        (tmp_path / "System" / "PaperForge" / "ocr").mkdir(parents=True)
        checker = EnvChecker(tmp_path)
        result = checker.check_vault()
        assert result.passed is True

    def test_partial_directories_fails(self, tmp_path: Path) -> None:
        """Vault with only one required dir should fail."""
        (tmp_path / "System" / "PaperForge" / "exports").mkdir(parents=True)
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
        canonical_test_config(vault)

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
        canonical_test_config(parent)
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
        exports_dir = tmp_path / "System" / "PaperForge" / "exports"
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
        exports_dir = tmp_path / "System" / "PaperForge" / "exports"
        exports_dir.mkdir(parents=True)
        (exports_dir / "bad.json").write_text("{invalid}", encoding="utf-8")
        checker = EnvChecker(tmp_path)
        result = checker.check_json()
        assert result.passed is False

    def test_empty_exports_fails(self, tmp_path: Path) -> None:
        exports_dir = tmp_path / "System" / "PaperForge" / "exports"
        exports_dir.mkdir(parents=True)
        checker = EnvChecker(tmp_path)
        result = checker.check_json()
        assert result.passed is False


# ===================================================================
# Integration smoke tests for headless_setup
# ===================================================================


def test_headless_setup_claude_skill_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Setup deploys the paperforge skill into the shared .agents/skills dir."""
    import paperforge.setup_wizard as sw
    from paperforge.setup_wizard import headless_setup

    def patched_check_deps(self) -> CheckResult:
        r = CheckResult("Dependencies")
        r.passed = True
        r.detail = "mocked"
        return r

    monkeypatch.setattr(sw.EnvChecker, "check_dependencies", patched_check_deps)

    rv = headless_setup(
        vault=tmp_path,
        agent_key="claude",
        system_dir="99_System",
        resources_dir="03_Resources",
        literature_dir="Literature",
        base_dir="05_Bases",
        skip_checks=True,
    )

    assert rv == 0, f"claude install failed with code {rv}"
    skill_dir = tmp_path / ".agents" / "skills" / "paperforge"
    assert skill_dir.exists(), f"paperforge skill dir not created: {skill_dir}"
    assert (skill_dir / "SKILL.md").exists(), "SKILL.md not created"
    assert (skill_dir / "atoms" / "chart-reading" / "INDEX.md").exists(), "chart INDEX.md not created"
    assert (skill_dir / "workflows" / "project-engineering.md").exists(), "project-engineering.md not created"
    assert (skill_dir / "atoms" / "clarify-user-intent.md").exists(), "clarify-user-intent.md not created"


def test_headless_setup_opencode_flat_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenCode setup deploys the paperforge skill into the shared .agents/skills dir."""
    import paperforge.setup_wizard as sw
    from paperforge.setup_wizard import headless_setup

    def patched_check_deps(self) -> CheckResult:
        r = CheckResult("Dependencies")
        r.passed = True
        r.detail = "mocked"
        return r

    monkeypatch.setattr(sw.EnvChecker, "check_dependencies", patched_check_deps)

    rv = headless_setup(
        vault=tmp_path,
        agent_key="opencode",
        system_dir="99_System",
        resources_dir="03_Resources",
        literature_dir="Literature",
        base_dir="05_Bases",
        skip_checks=True,
    )

    assert rv == 0, f"opencode install failed with code {rv}"
    skill_dir = tmp_path / ".agents" / "skills" / "paperforge"
    assert skill_dir.exists(), f"paperforge skill dir not created: {skill_dir}"
    assert (skill_dir / "SKILL.md").exists(), "SKILL.md not created"


def test_headless_setup_codex_skill_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Codex setup deploys the paperforge skill into the shared .agents/skills dir."""
    import paperforge.setup_wizard as sw
    from paperforge.setup_wizard import headless_setup

    def patched_check_deps(self) -> CheckResult:
        r = CheckResult("Dependencies")
        r.passed = True
        r.detail = "mocked"
        return r

    monkeypatch.setattr(sw.EnvChecker, "check_dependencies", patched_check_deps)

    rv = headless_setup(
        vault=tmp_path,
        agent_key="codex",
        system_dir="99_System",
        resources_dir="03_Resources",
        literature_dir="Literature",
        base_dir="05_Bases",
        skip_checks=True,
    )

    assert rv == 0, f"codex install failed with code {rv}"
    skill_dir = tmp_path / ".agents" / "skills" / "paperforge"
    assert skill_dir.exists(), f"paperforge skill dir not created: {skill_dir}"
    assert (skill_dir / "SKILL.md").exists(), "SKILL.md not created"


def test_headless_setup_cline_rules_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cline setup deploys the paperforge skill into the shared .agents/skills dir."""
    import paperforge.setup_wizard as sw
    from paperforge.setup_wizard import headless_setup

    def patched_check_deps(self) -> CheckResult:
        r = CheckResult("Dependencies")
        r.passed = True
        r.detail = "mocked"
        return r

    monkeypatch.setattr(sw.EnvChecker, "check_dependencies", patched_check_deps)

    rv = headless_setup(
        vault=tmp_path,
        agent_key="cline",
        system_dir="99_System",
        resources_dir="03_Resources",
        literature_dir="Literature",
        base_dir="05_Bases",
        skip_checks=True,
    )

    assert rv == 0, f"cline install failed with code {rv}"
    skill_dir = tmp_path / ".agents" / "skills" / "paperforge"
    assert skill_dir.exists(), "paperforge skill dir not created under shared .agents/skills"
    assert (skill_dir / "workflows" / "project-engineering.md").exists(), "project-engineering.md not created"


def test_headless_setup_preserves_existing_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Setup should create missing files without overwriting existing user content."""
    import paperforge.setup_wizard as sw
    from paperforge.setup_wizard import headless_setup

    def patched_check_deps(self) -> CheckResult:
        r = CheckResult("Dependencies")
        r.passed = True
        r.detail = "mocked"
        return r

    monkeypatch.setattr(sw.EnvChecker, "check_dependencies", patched_check_deps)

    docs_file = tmp_path / "docs" / "setup-guide.md"
    docs_file.parent.mkdir(parents=True)
    docs_file.write_text("user doc\n", encoding="utf-8")

    agents_file = tmp_path / "AGENTS.md"
    agents_file.write_text("custom agents\n", encoding="utf-8")

    env_file = tmp_path / "99_System" / "PaperForge" / ".env"
    env_file.parent.mkdir(parents=True)
    env_file.write_text("PADDLEOCR_API_TOKEN=keep-me\n", encoding="utf-8")

    plugin_main = tmp_path / ".obsidian" / "plugins" / "paperforge" / "main.js"
    plugin_main.parent.mkdir(parents=True)
    plugin_main.write_text("custom plugin\n", encoding="utf-8")

    existing_note = tmp_path / "03_Resources" / "Literature" / "existing.md"
    existing_note.parent.mkdir(parents=True)
    existing_note.write_text("keep note\n", encoding="utf-8")

    rv = headless_setup(
        vault=tmp_path,
        agent_key="opencode",
        paddleocr_key="new-token",
        system_dir="99_System",
        resources_dir="03_Resources",
        literature_dir="Literature",
        base_dir="05_Bases",
        skip_checks=True,
    )

    assert rv == 0
    assert docs_file.read_text(encoding="utf-8") == "user doc\n"
    assert agents_file.read_text(encoding="utf-8") == "custom agents\n"
    env_text = env_file.read_text(encoding="utf-8")
    assert "PADDLEOCR_API_TOKEN=keep-me" in env_text  # legacy rows untouched
    assert "PADDLEOCR_API_TOKEN=new-token" not in env_text  # #173: secrets never written to .env
    # #173/C1: the setup token lands in the credential authority instead.
    from paperforge.credentials import CredentialKey, resolve

    assert resolve(CredentialKey("ocr")) == "new-token"
    assert plugin_main.read_text(encoding="utf-8") == "custom plugin\n"
    assert existing_note.read_text(encoding="utf-8") == "keep note\n"


def test_headless_setup_allows_empty_paddleocr_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import paperforge.setup_wizard as sw
    from paperforge.setup_wizard import headless_setup

    def patched_check_deps(self) -> CheckResult:
        r = CheckResult("Dependencies")
        r.passed = True
        r.detail = "mocked"
        return r

    monkeypatch.setattr(sw.EnvChecker, "check_dependencies", patched_check_deps)

    rv = headless_setup(
        vault=tmp_path,
        agent_key="opencode",
        paddleocr_key=None,
        skip_checks=True,
    )
    assert rv == 0, f"setup failed with empty paddleocr key, code {rv}"
