"""Unit tests for Step 4 UX/recovery loop closures (`versions reset-live`, stuck submitting OCR)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from paperforge.cli import main as cli_main
from paperforge.config import load_vault_config, paperforge_paths
from paperforge.worker.ocr_maintenance import collect_maintenance_rows
from tests.conftest import canonical_test_config

pytestmark = pytest.mark.unit


def _seed_restorable_paper(vault: Path, key: str = "RST00001") -> Path:
    canonical_test_config(vault)
    ocr = paperforge_paths(vault, load_vault_config(vault))["ocr"]
    root = ocr / key
    (root / "versions" / "v1").mkdir(parents=True)
    (root / "render").mkdir(parents=True)

    canonical_bytes = b"# Canonical Title\n\nLatest canonical paragraph.\n"
    canonical_file = root / "fulltext.md"
    canonical_file.write_bytes(canonical_bytes)
    (root / "versions" / "v1" / "fulltext.md").write_bytes(b"v1 legacy text\n")
    (root / "render" / "fulltext.md").write_bytes(canonical_bytes)
    (root / "versions" / "manifest.json").write_text(
        json.dumps(
            {
                "versions": [
                    {
                        "label": "v1",
                        "created_at": "2025-01-01T00:00:00Z",
                        "source": "pre-rebuild",
                        "fulltext_size": 15,
                    }
                ],
                "current": {"label": "v1"},
            }
        ),
        encoding="utf-8",
    )
    machine_hash = "sha256:" + hashlib.sha256(canonical_bytes).hexdigest()
    (root / "meta.json").write_text(
        json.dumps(
            {
                "zotero_key": key,
                "ocr_status": "done",
                "ocr_finished_at": "2025-01-03T00:00:00Z",
                "machine_fulltext_hash": machine_hash,
            }
        ),
        encoding="utf-8",
    )
    return root


def test_versions_reset_live_restores_canonical_display_and_clears_provenance(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    key = "RST00001"
    root = _seed_restorable_paper(vault, key=key)

    rc_restore = cli_main(["--vault", str(vault), "versions", "restore", "--key", key, "--label", "v1", "--json"])
    assert rc_restore == 0
    _ = capsys.readouterr()
    assert (root / "render" / "fulltext.md").read_text(encoding="utf-8") == "v1 legacy text\n"
    meta_restored = json.loads((root / "meta.json").read_text(encoding="utf-8"))
    assert "restore_provenance" in meta_restored
    rows_drifted = {r.key: r for r in collect_maintenance_rows(vault)}
    assert rows_drifted[key].fulltext_drift_state == "DRIFTED"

    rc_reset = cli_main(["--vault", str(vault), "versions", "reset-live", "--key", key, "--json"])
    assert rc_reset == 0
    out_reset = json.loads(capsys.readouterr().out)
    assert out_reset["ok"] is True
    assert out_reset["data"]["intent"] == "versions-reset-live"
    assert out_reset["data"]["provenance_cleared"] is True

    canonical_bytes = (root / "fulltext.md").read_bytes()
    assert (root / "render" / "fulltext.md").read_bytes() == canonical_bytes
    meta_reset = json.loads((root / "meta.json").read_text(encoding="utf-8"))
    assert "restore_provenance" not in meta_reset
    assert meta_reset["ocr_finished_at"] == "2025-01-03T00:00:00Z"

    rows_after = {r.key: r for r in collect_maintenance_rows(vault)}
    assert rows_after[key].fulltext_drift_state == "MATCHED"


def test_versions_reset_live_fails_closed_when_canonical_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    key = "NOFULL01"
    root = _seed_restorable_paper(vault, key=key)
    (root / "fulltext.md").unlink()
    before_display = (root / "render" / "fulltext.md").read_bytes()

    rc = cli_main(["--vault", str(vault), "versions", "reset-live", "--key", key, "--json"])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert (root / "render" / "fulltext.md").read_bytes() == before_display


def test_stuck_submitting_unconfirmed_ocr_surfaces_actionable_recovery_row(
    tmp_path: Path,
) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    canonical_test_config(vault)
    ocr_root = paperforge_paths(vault, load_vault_config(vault))["ocr"]
    key = "STUCK001"
    paper_dir = ocr_root / key
    paper_dir.mkdir(parents=True)
    (paper_dir / "meta.json").write_text(
        json.dumps(
            {
                "zotero_key": key,
                "title": "Interrupted OCR Submission",
                "ocr_status": "pending",
                "submission_state": "submitting",
                "ocr_job_id": "",
            }
        ),
        encoding="utf-8",
    )

    rows = {r.key: r for r in collect_maintenance_rows(vault)}
    row = rows[key]
    assert row.visible_in_maintenance is True
    assert row.can_redo is True
    assert row.recommended_action == "redo"
    assert row.display_action == "retry_ocr"
    assert row.display_label == "重新提交"
    assert row.display_reason_key == "submitting_unconfirmed"
    assert row.display_group == "action_needed"
    assert row.display_severity == "warning"
