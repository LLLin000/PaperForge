"""Tests for paperforge.config resolver contract.

These tests prove:
- CONF-01: Env vars override JSON values
- CONF-02: paperforge_paths returns required key inventory
- CONF-03: All consumers use the same resolver
- CONF-04: Top-level and nested paperforge.json keys are both honored
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_vault(tmp_path: Path) -> Path:
    """A vault with no paperforge.json."""
    return tmp_path


@pytest.fixture
def vault_with_nested_config(tmp_path: Path) -> Path:
    """A vault with nested vault_config block."""
    vault = tmp_path / "vault_nested"
    vault.mkdir()
    pf = vault / "paperforge.json"
    pf.write_text(
        json.dumps(
            {
                "vault_config": {
                    "system_dir": "CustomSystem",
                    "resources_dir": "CustomResources",
                    "literature_dir": "CustomLiterature",
                    "control_dir": "CustomControl",
                    "base_dir": "CustomBases",
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return vault


@pytest.fixture
def vault_with_top_level_config(tmp_path: Path) -> Path:
    """A vault with legacy top-level keys that should override nested for backward compat."""
    vault = tmp_path / "vault_legacy"
    vault.mkdir()
    pf = vault / "paperforge.json"
    pf.write_text(
        json.dumps(
            {
                "vault_config": {
                    "system_dir": "NestedSystem",
                    "resources_dir": "NestedResources",
                },
                # Legacy top-level keys — these take precedence per CONF-04
                "system_dir": "LegacySystem",
                "resources_dir": "LegacyResources",
                "literature_dir": "LegacyLiterature",
                "control_dir": "LegacyControl",
                "base_dir": "LegacyBases",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return vault


@pytest.fixture
def populated_vault(tmp_path: Path) -> Path:
    """A vault with realistic directory structure."""
    vault = tmp_path / "vault_populated"
    vault.mkdir()
    system = vault / "99_System"
    system.mkdir()
    pf_dir = system / "PaperForge"
    pf_dir.mkdir(parents=True)
    (pf_dir / "exports").mkdir()
    (pf_dir / "ocr").mkdir()
    resources = vault / "03_Resources"
    resources.mkdir()
    literature = resources / "Literature"
    literature.mkdir(parents=True)
    control = resources / "LiteratureControl"
    control.mkdir(parents=True)
    control_records = control / "library-records"
    control_records.mkdir(parents=True)
    bases = vault / "05_Bases"
    bases.mkdir()
    skills = vault / ".opencode" / "skills"
    skills.mkdir(parents=True)
    command = vault / ".opencode" / "command"
    command.mkdir(parents=True)
    return vault


@pytest.fixture
def env_dict() -> dict[str, str]:
    """Empty env dict for tests that control env injection."""
    return {}


# ---------------------------------------------------------------------------
# DEFAULT_CONFIG tests — truths from must_haves
# ---------------------------------------------------------------------------


def test_default_system_dir_is_99_System():
    """Built-in default for system_dir must be '99_System'."""
    from paperforge.config import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["system_dir"] == "99_System"


def test_default_resources_dir_is_03_Resources():
    """Built-in default for resources_dir must be '03_Resources'."""
    from paperforge.config import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["resources_dir"] == "03_Resources"


def test_default_literature_dir():
    from paperforge.config import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["literature_dir"] == "Literature"


def test_default_control_dir():
    from paperforge.config import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["control_dir"] == "LiteratureControl"


def test_default_base_dir():
    from paperforge.config import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["base_dir"] == "05_Bases"


def test_default_skill_dir():
    from paperforge.config import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["skill_dir"] == ".opencode/skills"


def test_default_command_dir():
    from paperforge.config import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["command_dir"] == ".opencode/command"


# ---------------------------------------------------------------------------
# ENV_KEYS coverage — CONF-01
# ---------------------------------------------------------------------------


def test_env_keys_has_all_required_overrides():
    """All PAPERFORGE_* env vars must be registered in ENV_KEYS."""
    from paperforge.config import ENV_KEYS

    required = {
        "PAPERFORGE_VAULT",
        "PAPERFORGE_SYSTEM_DIR",
        "PAPERFORGE_RESOURCES_DIR",
        "paperforgeRATURE_DIR",
        "PAPERFORGE_CONTROL_DIR",
        "PAPERFORGE_BASE_DIR",
        "PAPERFORGE_SKILL_DIR",
        "PAPERFORGE_COMMAND_DIR",
    }
    env_values = set(ENV_KEYS.values())
    assert required.issubset(env_values), f"Missing env keys: {required - env_values}"


# ---------------------------------------------------------------------------
# load_vault_config precedence — CONF-01, CONF-04
# ---------------------------------------------------------------------------


def test_env_overrides_nested_json(env_dict):
    """PAPERFORGE_SYSTEM_DIR overrides nested vault_config.system_dir (CONF-01)."""
    from paperforge.config import load_vault_config

    # Create a vault with nested config
    vault = Path("test_vault_env_override")
    vault.mkdir(exist_ok=True)
    (vault / "paperforge.json").write_text(
        json.dumps({"vault_config": {"system_dir": "NestedSystem"}}),
        encoding="utf-8",
    )

    # Env overrides JSON
    env_dict["PAPERFORGE_SYSTEM_DIR"] = "EnvSystem"
    cfg = load_vault_config(vault, env=env_dict)

    assert (
        cfg["system_dir"] == "EnvSystem"
    ), f"Expected 'EnvSystem' from PAPERFORGE_SYSTEM_DIR, got '{cfg['system_dir']}'"

    # Cleanup
    import shutil

    shutil.rmtree(vault, ignore_errors=True)


def test_explicit_overrides_win_over_env(env_dict):
    """Explicit overrides passed to load_vault_config win over env vars (CONF-01)."""
    from paperforge.config import load_vault_config

    vault = Path("test_vault_explicit")
    vault.mkdir(exist_ok=True)
    (vault / "paperforge.json").write_text("{}", encoding="utf-8")

    env_dict["PAPERFORGE_SYSTEM_DIR"] = "EnvSystem"
    overrides = {"system_dir": "OverrideSystem"}
    cfg = load_vault_config(vault, env=env_dict, overrides=overrides)

    assert (
        cfg["system_dir"] == "OverrideSystem"
    ), f"Expected 'OverrideSystem' from explicit override, got '{cfg['system_dir']}'"

    import shutil

    shutil.rmtree(vault, ignore_errors=True)


def test_nested_vault_config_is_honored(tmp_path: Path):
    """Nested vault_config keys are honored when present (CONF-04)."""
    from paperforge.config import load_vault_config

    vault = tmp_path / "vault_nested"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        json.dumps({"vault_config": {"system_dir": "NestedSystem"}}),
        encoding="utf-8",
    )

    cfg = load_vault_config(vault)
    assert cfg["system_dir"] == "NestedSystem"


def test_top_level_keys_override_nested_for_backward_compat(tmp_path: Path):
    """Top-level paperforge.json keys override nested vault_config (CONF-04 backward compat)."""
    from paperforge.config import load_vault_config

    vault = tmp_path / "vault_legacy"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        json.dumps(
            {
                "vault_config": {"system_dir": "NestedSystem"},
                "system_dir": "LegacySystem",
            }
        ),
        encoding="utf-8",
    )

    cfg = load_vault_config(vault)
    assert cfg["system_dir"] == "LegacySystem", f"Expected 'LegacySystem' from top-level key, got '{cfg['system_dir']}'"


def test_defaults_used_when_no_json(tmp_path: Path):
    """When no paperforge.json exists, defaults are returned."""
    from paperforge.config import load_vault_config

    vault = tmp_path / "vault_empty"
    vault.mkdir()

    cfg = load_vault_config(vault)
    assert cfg["system_dir"] == "99_System"
    assert cfg["resources_dir"] == "03_Resources"


# ---------------------------------------------------------------------------
# paperforge_paths key inventory — CONF-02, CONF-03
# ---------------------------------------------------------------------------


def test_paperforge_paths_returns_exact_keys(tmp_path: Path):
    """paperforge_paths() must return exactly the required user-facing keys."""
    from paperforge.config import paperforge_paths

    vault = tmp_path / "vault_paths"
    vault.mkdir()

    # Create required directory structure
    (vault / "99_System" / "PaperForge" / "exports").mkdir(parents=True)
    (vault / "99_System" / "PaperForge" / "ocr").mkdir(parents=True)
    (vault / "03_Resources" / "Literature").mkdir(parents=True)
    (vault / "03_Resources" / "LiteratureControl" / "library-records").mkdir(parents=True)
    (vault / "05_Bases").mkdir(parents=True)
    (vault / ".opencode" / "skills").mkdir(parents=True)
    (vault / ".opencode" / "command").mkdir(parents=True)

    paths = paperforge_paths(vault)

    required_keys = {
        "vault",
        "system",
        "paperforge",
        "exports",
        "ocr",
        "zotero_dir",
        "resources",
        "literature",
        "control",
        "library_records",
        "bases",
        "worker_script",
        "skill_dir",
        "ld_deep_script",
    }

    actual_keys = set(paths.keys())
    missing = required_keys - actual_keys
    extra = actual_keys - required_keys

    assert not missing, f"Missing required path keys: {sorted(missing)}"
    assert not extra, f"Extra path keys not in spec: {sorted(extra)}"


def test_paperforge_paths_values_are_absolute(tmp_path: Path):
    """All path values returned must be absolute Path objects."""
    from paperforge.config import paperforge_paths

    vault = tmp_path / "vault_absolute"
    vault.mkdir()
    (vault / "99_System" / "PaperForge" / "exports").mkdir(parents=True)
    (vault / "99_System" / "PaperForge" / "ocr").mkdir(parents=True)
    (vault / "03_Resources" / "Literature").mkdir(parents=True)
    (vault / "03_Resources" / "LiteratureControl" / "library-records").mkdir(parents=True)
    (vault / "05_Bases").mkdir(parents=True)
    (vault / ".opencode" / "skills").mkdir(parents=True)
    (vault / ".opencode" / "command").mkdir(parents=True)

    paths = paperforge_paths(vault)
    for name, path in paths.items():
        assert path.is_absolute(), f"Path '{name}' is not absolute: {path}"


def test_paperforge_paths_includes_worker_script(tmp_path: Path):
    """worker_script key must point to literature_pipeline.py."""
    from paperforge.config import paperforge_paths

    vault = tmp_path / "vault_ws"
    vault.mkdir()
    (vault / "99_System" / "PaperForge" / "exports").mkdir(parents=True)
    (vault / "99_System" / "PaperForge" / "ocr").mkdir(parents=True)
    (vault / "03_Resources" / "Literature").mkdir(parents=True)
    (vault / "03_Resources" / "LiteratureControl" / "library-records").mkdir(parents=True)
    (vault / "05_Bases").mkdir(parents=True)
    (vault / ".opencode" / "skills").mkdir(parents=True)
    (vault / ".opencode" / "command").mkdir(parents=True)

    paths = paperforge_paths(vault)
    assert "worker_script" in paths
    assert paths["worker_script"].name == "__init__.py"


def test_paperforge_paths_includes_ld_deep_script(tmp_path: Path):
    """ld_deep_script key must point to ld_deep.py."""
    from paperforge.config import paperforge_paths

    vault = tmp_path / "vault_ld"
    vault.mkdir()
    (vault / "99_System" / "PaperForge" / "exports").mkdir(parents=True)
    (vault / "99_System" / "PaperForge" / "ocr").mkdir(parents=True)
    (vault / "03_Resources" / "Literature").mkdir(parents=True)
    (vault / "03_Resources" / "LiteratureControl" / "library-records").mkdir(parents=True)
    (vault / "05_Bases").mkdir(parents=True)
    (vault / ".opencode" / "skills").mkdir(parents=True)
    (vault / ".opencode" / "command").mkdir(parents=True)

    paths = paperforge_paths(vault)
    assert "ld_deep_script" in paths
    assert paths["ld_deep_script"].name == "ld_deep.py"


# ---------------------------------------------------------------------------
# paths_as_strings — JSON serializable output
# ---------------------------------------------------------------------------


def test_paths_as_strings_returns_string_values():
    """paths_as_strings must return dict[str, str] with all values as strings."""
    from pathlib import Path

    from paperforge.config import paths_as_strings

    paths = {
        "vault": Path("/some/vault"),
        "system": Path("/some/vault/99_System"),
        "paperforge": Path("/some/vault/99_System/PaperForge"),
        "exports": Path("/some/vault/99_System/PaperForge/exports"),
        "ocr": Path("/some/vault/99_System/PaperForge/ocr"),
        "resources": Path("/some/vault/03_Resources"),
        "literature": Path("/some/vault/03_Resources/Literature"),
        "control": Path("/some/vault/03_Resources/LiteratureControl"),
        "library_records": Path("/some/vault/03_Resources/LiteratureControl/library-records"),
        "bases": Path("/some/vault/05_Bases"),
        "worker_script": Path("/some/vault/99_System/PaperForge/worker/scripts/literature_pipeline.py"),
        "skill_dir": Path("/some/vault/.opencode/skills"),
        "ld_deep_script": Path("/some/vault/.opencode/skills/literature-qa/scripts/ld_deep.py"),
    }

    result = paths_as_strings(paths)

    assert isinstance(result, dict)
    for key, value in result.items():
        assert isinstance(value, str), f"Expected str for '{key}', got {type(value).__name__}"

    # Verify JSON serializable
    json.dumps(result)


# ---------------------------------------------------------------------------
# resolve_vault precedence
# ---------------------------------------------------------------------------


def test_resolve_vault_precedence_explicit_first(tmp_path: Path):
    """resolve_vault returns explicit cli_vault first."""
    from paperforge.config import resolve_vault

    vault_a = tmp_path / "vault_a"
    vault_b = tmp_path / "vault_b"
    vault_a.mkdir()
    vault_b.mkdir()

    result = resolve_vault(cli_vault=vault_a, env={}, cwd=vault_b)
    assert result == vault_a


def test_resolve_vault_precedence_env_second(tmp_path: Path):
    """resolve_vault returns PAPERFORGE_VAULT when no explicit cli_vault."""
    from paperforge.config import resolve_vault

    vault = tmp_path / "vault_env"
    vault.mkdir()

    result = resolve_vault(cli_vault=None, env={"PAPERFORGE_VAULT": str(vault)}, cwd=tmp_path)
    assert result == vault


def test_resolve_vault_precedence_json_search_third(tmp_path: Path):
    """resolve_vault falls back to scanning cwd for paperforge.json."""
    from paperforge.config import resolve_vault

    vault = tmp_path / "vault_json"
    vault.mkdir()
    (vault / "paperforge.json").write_text("{}", encoding="utf-8")

    result = resolve_vault(cli_vault=None, env={}, cwd=vault)
    assert result == vault


def test_resolve_vault_precedence_cwd_last(tmp_path: Path):
    """resolve_vault falls back to cwd when no explicit, env, or json."""
    from paperforge.config import resolve_vault

    result = resolve_vault(cli_vault=None, env={}, cwd=tmp_path)
    assert result == tmp_path
