"""#99-B — redo crash-orphan recovery from transaction snapshots."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from paperforge.worker.ocr import recover_redo_orphans


@pytest.fixture(autouse=True)
def _clean_global_snapshots():
    """Isolate tests: previous runs may leave paperforge-redo-* dirs in the
    shared system temp directory."""
    tmp = Path(tempfile.gettempdir())
    leftovers = list(tmp.glob("paperforge-redo-*"))
    for item in leftovers:
        shutil.rmtree(item, ignore_errors=True)
    yield
    leftovers = list(tmp.glob("paperforge-redo-*"))
    for item in leftovers:
        shutil.rmtree(item, ignore_errors=True)


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        json.dumps({"system_dir": "System"}), encoding="utf-8"
    )
    (vault / "System" / "PaperForge" / "ocr").mkdir(parents=True)
    return vault


def _make_snapshot(tmp_path: Path, key: str, meta_status: str = "done") -> Path:
    snap = Path(tempfile.gettempdir()) / f"paperforge-redo-{key}-abc123"
    snap_ocr = snap / "ocr"
    (snap_ocr / "structure").mkdir(parents=True)
    (snap_ocr / "structure" / "blocks.structured.jsonl").write_text(
        json.dumps({"blocks": [1, 2, 3]}), encoding="utf-8"
    )
    (snap_ocr / "meta.json").write_text(
        json.dumps({"zotero_key": key, "ocr_status": meta_status}),
        encoding="utf-8",
    )
    return snap


class TestRedoOrphanRecovery:
    def test_restores_deleted_ocr_dir_from_snapshot(self, tmp_path):
        vault = _make_vault(tmp_path)
        _make_snapshot(tmp_path, "KEY00001")
        ocr_dir = vault / "System" / "PaperForge" / "ocr" / "KEY00001"
        assert not ocr_dir.exists()

        restored = recover_redo_orphans(vault)

        assert restored == 1
        assert (ocr_dir / "structure" / "blocks.structured.jsonl").exists()
        # snapshot consumed
        assert not list(Path(tempfile.gettempdir()).glob("paperforge-redo-*"))

    def test_restores_half_written_pending_ocr_dir(self, tmp_path):
        vault = _make_vault(tmp_path)
        _make_snapshot(tmp_path, "KEY00002")
        ocr_dir = vault / "System" / "PaperForge" / "ocr" / "KEY00002"
        ocr_dir.mkdir(parents=True)
        (ocr_dir / "meta.json").write_text(
            json.dumps({"zotero_key": "KEY00002", "ocr_status": "pending"}),
            encoding="utf-8",
        )
        (ocr_dir / "partial.txt").write_text("half", encoding="utf-8")

        restored = recover_redo_orphans(vault)

        assert restored == 1
        # half-written artifacts replaced by the snapshot
        assert not (ocr_dir / "partial.txt").exists()
        assert (ocr_dir / "structure" / "blocks.structured.jsonl").exists()

    def test_completed_transaction_orphan_is_cleaned_not_restored(self, tmp_path):
        vault = _make_vault(tmp_path)
        snap = _make_snapshot(tmp_path, "KEY00003")
        ocr_dir = vault / "System" / "PaperForge" / "ocr" / "KEY00003"
        ocr_dir.mkdir(parents=True)
        (ocr_dir / "meta.json").write_text(
            json.dumps({"zotero_key": "KEY00003", "ocr_status": "done"}),
            encoding="utf-8",
        )

        restored = recover_redo_orphans(vault)

        assert restored == 0
        assert ocr_dir.exists()
        assert not snap.exists()

    def test_unrelated_tempdirs_untouched(self, tmp_path):
        vault = _make_vault(tmp_path)
        other = Path(tempfile.gettempdir()) / "unrelated-temp-xyz"
        other.mkdir(exist_ok=True)
        try:
            assert recover_redo_orphans(vault) == 0
            assert other.exists()
        finally:
            shutil.rmtree(other, ignore_errors=True)
