"""Test compatibility: literature_pipeline uses shared resolver."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from importlib.util import spec_from_file_location, module_from_spec


def _load_module(name: str, path: Path):
    """Load a Python script as an importable module."""
    spec = spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_REPO_ROOT = Path(__file__).parent.parent

# Pre-load literature_pipeline so its functions are available
_lp_spec = spec_from_file_location(
    "literature_pipeline",
    _REPO_ROOT / "pipeline" / "worker" / "scripts" / "literature_pipeline.py",
)
_lp_mod = module_from_spec(_lp_spec)
sys.modules["literature_pipeline"] = _lp_mod
_lp_spec.loader.exec_module(_lp_mod)


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Create a minimal PaperForge vault for testing."""
    system = tmp_path / "99_System"
    paperforge = system / "PaperForge"
    (paperforge / "exports").mkdir(parents=True)
    (paperforge / "ocr").mkdir(parents=True)
    (paperforge / "candidates").mkdir(parents=True)

    resources = tmp_path / "03_Resources"
    literature = resources / "Literature"
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


class TestWorkerLoadVaultConfig:
    """Test literature_pipeline.load_vault_config matches paperforge_lite.config."""

    def test_defaults_match_shared_resolver(self, tmp_vault: Path) -> None:
        """load_vault_config returns same top-level keys as shared resolver."""
        from paperforge_lite.config import load_vault_config as shared_load
        import literature_pipeline as lp

        shared_cfg = shared_load(tmp_vault)
        worker_cfg = lp.load_vault_config(tmp_vault)

        assert set(worker_cfg.keys()) == set(shared_cfg.keys()), (
            f"Key mismatch: worker={set(worker_cfg.keys())} vs shared={set(shared_cfg.keys())}"
        )
        for key in shared_cfg:
            assert worker_cfg.get(key) == shared_cfg.get(key), (
                f"Key '{key}' differs: worker={worker_cfg.get(key)!r} vs shared={shared_cfg.get(key)!r}"
            )

    def test_nested_vault_config_respected(self, tmp_vault: Path) -> None:
        """Nested vault_config block takes precedence over top-level keys."""
        import literature_pipeline as lp

        cfg = lp.load_vault_config(tmp_vault)
        assert cfg["system_dir"] == "99_System"
        assert cfg["resources_dir"] == "03_Resources"

    def test_env_override_system_dir(self, tmp_vault: Path, monkeypatch) -> None:
        """PAPERFORGE_SYSTEM_DIR env var overrides vault_config."""
        import literature_pipeline as lp

        monkeypatch.setenv("PAPERFORGE_SYSTEM_DIR", "EnvSystem")
        cfg = lp.load_vault_config(tmp_vault)
        assert cfg["system_dir"] == "EnvSystem"


class TestWorkerPipelinePaths:
    """Test literature_pipeline.pipeline_paths includes all expected keys."""

    def test_pipeline_paths_keys(self, tmp_vault: Path) -> None:
        """pipeline_paths returns expected worker keys from shared resolver."""
        import literature_pipeline as lp

        paths = lp.pipeline_paths(tmp_vault)

        expected_keys = [
            # Shared resolver keys
            "vault",
            "system",
            "paperforge",
            "exports",
            "ocr",
            "resources",
            "literature",
            "control",
            "library_records",
            "bases",
            # Worker-only keys
            "pipeline",
            "candidates",
            "candidate_inbox",
            "candidate_archive",
            "search_tasks",
            "search_archive",
            "search_results",
            "harvest_root",
            "records",
            "review",
            "config",
            "queue",
            "log",
            "bridge_config",
            "bridge_config_sample",
            "index",
            "ocr_queue",
        ]
        for key in expected_keys:
            assert key in paths, f"Missing key: {key}"

    def test_pipeline_paths_values_from_shared_resolver(
        self, tmp_vault: Path
    ) -> None:
        """Verify shared resolver keys have correct values."""
        from paperforge_lite.config import paperforge_paths as shared_paths
        import literature_pipeline as lp

        shared = shared_paths(tmp_vault)
        worker = lp.pipeline_paths(tmp_vault)

        for key in ["exports", "ocr", "library_records", "literature", "control", "bases"]:
            assert worker[key] == shared[key], (
                f"Key '{key}' differs: worker={worker[key]} vs shared={shared[key]}"
            )


class TestLegacyStatusSubprocess:
    """Test direct worker invocation via subprocess (CMD-02 smoke test)."""

    def test_status_exits_zero(self, tmp_vault: Path) -> None:
        """`python literature_pipeline.py --vault <vault> status` exits 0."""
        worker_script = _REPO_ROOT / "pipeline" / "worker" / "scripts" / "literature_pipeline.py"
        if not worker_script.exists():
            pytest.skip("Worker script not found at expected path")

        result = subprocess.run(
            [sys.executable, str(worker_script), "--vault", str(tmp_vault), "status"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Should exit 0, no import errors
        assert result.returncode == 0, (
            f"status command failed with code {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "ImportError" not in result.stderr, (
            f"Import error in stderr: {result.stderr}"
        )