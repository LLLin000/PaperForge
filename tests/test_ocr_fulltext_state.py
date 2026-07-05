from __future__ import annotations

import datetime as dt
from pathlib import Path

from paperforge.worker.ocr_fulltext_state import (
    compute_disk_fulltext_hash,
    get_fulltext_drift_state,
    create_pre_rebuild_backup,
    prune_pre_rebuild_backups,
)


def _fixed_utc() -> dt.datetime:
    return dt.datetime(2026, 7, 5, 12, 0, 0, tzinfo=dt.timezone.utc)


def test_compute_disk_fulltext_hash_uses_sha256_prefix_and_disk_bytes(tmp_path: Path) -> None:
    path = tmp_path / "fulltext.md"
    path.write_bytes("A\r\nB\n".encode("utf-8"))
    digest = compute_disk_fulltext_hash(path)
    assert digest.startswith("sha256:")


def test_get_fulltext_drift_state_returns_unknown_without_machine_hash(tmp_path: Path) -> None:
    path = tmp_path / "fulltext.md"
    path.write_text("hello\n", encoding="utf-8")
    assert get_fulltext_drift_state(path, None) == "UNKNOWN"


def test_create_pre_rebuild_backup_uses_timestamp_and_sequence(tmp_path: Path) -> None:
    paper_root = tmp_path / "ocr" / "KEY1"
    fulltext = paper_root / "fulltext.md"
    fulltext.parent.mkdir(parents=True)
    fulltext.write_text("v1\n", encoding="utf-8")
    first = create_pre_rebuild_backup(fulltext, _fixed_utc())
    second = create_pre_rebuild_backup(fulltext, _fixed_utc())
    assert first is not None and second is not None
    assert first[1].endswith("20260705T120000Z.md")
    assert second[1].endswith("20260705T120000Z.001.md")


def test_prune_pre_rebuild_backups_only_deletes_matching_files(tmp_path: Path) -> None:
    backups = tmp_path / "backups"
    backups.mkdir()
    for i in range(7):
        (backups / f"fulltext.pre-rebuild.20260705T12000{i}Z.md").write_text(str(i), encoding="utf-8")
    keeper = backups / "notes.keep.md"
    keeper.write_text("do not touch", encoding="utf-8")
    removed = prune_pre_rebuild_backups(backups, keep=5)
    assert len(removed) == 2
    assert keeper.exists()


def test_write_render_outputs_updates_render_artifact_and_meta(tmp_path: Path) -> None:
    import datetime as _dt
    from paperforge.worker.ocr_render import write_render_outputs
    from paperforge.worker.ocr_fulltext_state import compute_disk_fulltext_hash

    paper_root = tmp_path / "ocr" / "KEY1"
    render_root = paper_root / "render"
    user_fulltext = paper_root / "fulltext.md"
    user_fulltext.parent.mkdir(parents=True)
    user_fulltext.write_text("old\n", encoding="utf-8")
    meta = {"ocr_finished_at": "2026-07-05T12:00:00+00:00", "rebuild_count": 0}

    def _fixed_utc() -> _dt.datetime:
        return _dt.datetime(2026, 7, 5, 12, 0, 0, tzinfo=_dt.timezone.utc)

    updated = write_render_outputs(
        render_root=render_root,
        user_fulltext=user_fulltext,
        markdown="new\n",
        meta=meta,
        rebuild_increment=False,
        now_utc=_fixed_utc(),
    )

    assert (render_root / "fulltext.md").read_text(encoding="utf-8") == "new\n"
    assert user_fulltext.read_text(encoding="utf-8") == "new\n"
    assert updated["machine_fulltext_hash"] == compute_disk_fulltext_hash(user_fulltext)
    assert updated["last_backup_path"].startswith("backups/fulltext.pre-rebuild.")
