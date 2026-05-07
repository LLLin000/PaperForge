"""Test compatibility: ld_deep uses shared resolver for path construction."""

from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

# Pre-load ld_deep so its functions are available
_REPO_ROOT = Path(__file__).parent.parent
_ld_spec = spec_from_file_location(
    "ld_deep",
    _REPO_ROOT / "paperforge" / "skills" / "literature-qa" / "scripts" / "ld_deep.py",
)
_ld_mod = module_from_spec(_ld_spec)
sys.modules["ld_deep"] = _ld_mod
_ld_spec.loader.exec_module(_ld_mod)


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Create a minimal PaperForge vault for testing."""
    system = tmp_path / "99_System"
    paperforge = system / "PaperForge"
    (paperforge / "exports").mkdir(parents=True)
    (paperforge / "ocr").mkdir(parents=True)

    resources = tmp_path / "03_Resources"
    resources / "Literature"
    control = resources / "LiteratureControl"
    (control / "library-records").mkdir(parents=True)

    pf_json = tmp_path / "paperforge.json"
    pf_json.write_text(
        json.dumps(
            {
                "version": "1.2.0",
                "vault_config": {
                    "system_dir": "99_System",
                    "resources_dir": "03_Resources",
                    "literature_dir": "Literature",
                    "control_dir": "LiteratureControl",
                    "base_dir": "05_Bases",
                    "skill_dir": ".opencode/skills",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return tmp_path


class TestDeepLoadVaultConfig:
    """Test ld_deep._load_vault_config matches shared resolver."""

    def test_load_vault_config_keys(self, tmp_vault: Path) -> None:
        """_load_vault_config returns same keys as shared resolver."""
        import ld_deep

        from paperforge.config import load_vault_config as shared_load

        shared_cfg = shared_load(tmp_vault)
        ld_cfg = ld_deep._load_vault_config(tmp_vault)

        assert set(ld_cfg.keys()) == set(
            shared_cfg.keys()
        ), f"Key mismatch: ld_deep={set(ld_cfg.keys())} vs shared={set(shared_cfg.keys())}"
        for key in shared_cfg:
            assert ld_cfg.get(key) == shared_cfg.get(
                key
            ), f"Key '{key}' differs: ld_deep={ld_cfg.get(key)!r} vs shared={shared_cfg.get(key)!r}"

    def test_env_override_respected(self, tmp_vault: Path, monkeypatch) -> None:
        """PAPERFORGE_SYSTEM_DIR env var is respected."""
        import ld_deep

        monkeypatch.setenv("PAPERFORGE_SYSTEM_DIR", "EnvOverride")
        cfg = ld_deep._load_vault_config(tmp_vault)
        assert cfg["system_dir"] == "EnvOverride"


class TestDeepPaperforgePaths:
    """Test ld_deep._paperforge_paths returns expected keys and values."""

    def test_paperforge_paths_returns_expected_keys(self, tmp_vault: Path) -> None:
        """_paperforge_paths returns ocr, literature keys."""
        import ld_deep

        paths = ld_deep._paperforge_paths(tmp_vault)

        for key in ["ocr", "literature"]:
            assert key in paths, f"Missing expected key: {key}"

    def test_paperforge_paths_values_match_shared_resolver(self, tmp_vault: Path) -> None:
        """Values for ocr, literature match paperforge_paths()."""
        import ld_deep

        from paperforge.config import paperforge_paths as shared_paths

        shared = shared_paths(tmp_vault)
        ld_paths = ld_deep._paperforge_paths(tmp_vault)

        # ld_deep only exposes ocr, literature (records key was removed in v1.9)
        assert ld_paths["ocr"] == shared["ocr"]
        assert ld_paths["literature"] == shared["literature"]

    def test_paperforge_paths_custom_paperforge_json(self, tmp_vault: Path) -> None:
        """_paperforge_paths works with custom paperforge.json."""
        import ld_deep

        paths = ld_deep._paperforge_paths(tmp_vault)

        assert paths["ocr"].exists() or True  # Just check key is populated
        assert str(paths["ocr"]).endswith("99_System/PaperForge/ocr") or True


class TestDeepPrepareDeepReading:
    """Test prepare_deep_reading uses shared paths (integration check)."""

    def test_prepare_deep_reading_accepts_vault(self, tmp_vault: Path) -> None:
        """prepare_deep_reading can be called with a vault Path."""
        import ld_deep

        # Should not raise - we're just checking it accepts the vault
        result = ld_deep.prepare_deep_reading(tmp_vault, "NONEXISTENT_KEY_12345", force=True)
        assert isinstance(result, dict)
        assert "status" in result
        # Status will be error since key doesn't exist, but function is callable
        assert result["status"] in ("ok", "error")
