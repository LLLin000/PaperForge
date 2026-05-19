"""Test pf_bootstrap.py capability contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

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

    # Minimal paperforge.json
    pf_json = vault / "paperforge.json"
    pf_json.write_text(
        json.dumps(
            {
                "version": "1.2.0",
                "system_dir": "99_System",
                "resources_dir": "03_Resources",
                "literature_dir": "Literature",
            }
        ),
        encoding="utf-8",
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

    # Skill version
    sv = output.get("skill_version")
    assert sv is not None, "skill_version missing from bootstrap output"
    assert isinstance(sv, str) and sv != "unknown", f"skill_version invalid: {sv}"
