"""Test pf_bootstrap.py capability contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.conftest import canonical_test_config

BOOTSTRAP = (
    Path(__file__).resolve().parent.parent
    / "paperforge"
    / "skills"
    / "paperforge"
    / "scripts"
    / "pf_bootstrap.py"
)


def test_bootstrap_capabilities_contract(tmp_path: Path) -> None:
    """Verify bootstrap JSON output includes capabilities block."""
    vault = tmp_path / "TestVault"
    vault.mkdir()

    # Minimal canonical paperforge.json
    canonical_test_config(
        vault,
        system_dir="99_System",
        resources_dir="03_Resources",
        literature_dir="Literature",
    )

    # Create minimal directory structure
    (vault / "99_System" / "PaperForge" / "indexes").mkdir(parents=True)
    (vault / "99_System" / "PaperForge" / "ocr").mkdir(parents=True)
    (vault / "99_System" / "PaperForge" / "exports").mkdir(parents=True)
    (vault / "03_Resources" / "Literature").mkdir(parents=True)

    # Run bootstrap
    result = subprocess.run(
        [sys.executable, str(BOOTSTRAP), "--vault", str(vault)],
        capture_output=True,
        text=True,
        timeout=15,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, f"bootstrap failed:\n{result.stderr}"

    output = json.loads(result.stdout)
    assert output.get("ok") is True, f"bootstrap ok=False: {output.get('error', '')}"

    # Capabilities block
    caps = output.get("capabilities")
    assert caps is not None, "capabilities block missing from bootstrap output"
    assert isinstance(caps, dict), "capabilities must be a dict"

    assert "rg" in caps, "capabilities.rg missing"
    assert isinstance(caps["rg"], bool), "capabilities.rg must be bool"

    assert "metadata_search" in caps, "capabilities.metadata_search missing"
    assert caps["metadata_search"] is True, "capabilities.metadata_search should be True"

    assert "paper_context" in caps, "capabilities.paper_context missing"
    assert caps["paper_context"] is True, "capabilities.paper_context should be True"

    assert "semantic_enabled" in caps, "capabilities.semantic_enabled missing"
    assert isinstance(caps["semantic_enabled"], bool), "capabilities.semantic_enabled must be bool"

    assert "semantic_ready" in caps, "capabilities.semantic_ready missing"
    assert isinstance(caps["semantic_ready"], bool), "capabilities.semantic_ready must be bool"

    pv = output.get("plugin_version")
    assert pv is not None, "plugin_version missing from bootstrap output"
    assert isinstance(pv, str) and pv, f"plugin_version invalid: {pv}"

    sv = output.get("skill_version")
    assert sv is not None, "skill_version missing from bootstrap output"
    assert isinstance(sv, str) and sv, f"skill_version invalid: {sv}"

    sav = output.get("skill_api_version")
    assert sav is None or isinstance(sav, int), f"skill_api_version invalid: {sav}"


def test_semantic_ready_reflects_backend_not_switch(
    tmp_path: Path, monkeypatch
) -> None:
    """RC UX Seam: semantic_ready must mirror the backend embed status, not
    the plugin settings toggle. A vault with no vector index reports
    semantic_ready=false even when data.json says vector_db enabled."""
    import paperforge.skills.paperforge.scripts.pf_bootstrap as boot

    vault = tmp_path / "SemVault"
    vault.mkdir()
    canonical_test_config(
        vault,
        system_dir="99_System",
        resources_dir="03_Resources",
        literature_dir="Literature",
    )
    (vault / "99_System" / "PaperForge" / "indexes").mkdir(parents=True)
    (vault / "99_System" / "PaperForge" / "ocr").mkdir(parents=True)
    (vault / "99_System" / "PaperForge" / "exports").mkdir(parents=True)
    (vault / "03_Resources" / "Literature").mkdir(parents=True)
    # Plugin settings toggle says enabled — the old false-green source.
    data_dir = vault / ".obsidian" / "plugins" / "paperforge"
    data_dir.mkdir(parents=True)
    (data_dir / "data.json").write_text(
        json.dumps({"features": {"vector_db": True}}), encoding="utf-8"
    )

    # The subprocess embed-status call must observe an empty index. In this
    # hermetic vault there is no paperforge.db at all, so the real command
    # reports not_built — semantic_ready stays false.
    result = subprocess.run(
        [sys.executable, str(BOOTSTRAP), "--vault", str(vault)],
        capture_output=True,
        text=True,
        timeout=30,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["capabilities"]["semantic_enabled"] is True
    assert output["capabilities"]["semantic_ready"] is False
    assert output["memory_layer"]["vector_search"] is False
