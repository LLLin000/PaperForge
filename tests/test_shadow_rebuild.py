"""Integration tests for atomic shadow vector rebuild (#117).

Covers the BuildTarget/ShadowBuild lifecycle, writer-lock re-entrancy,
publication swap, verification checklist, abort semantics, and crash
recovery. Uses real sqlite3 files — no mocks of the swap itself.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "System" / "PaperForge" / "indexes").mkdir(parents=True)
    return vault


def _seed_live_db(vault: Path, *, vec_rows: int = 5) -> Path:
    """Create a live paperforge.db with schema + vec tables + rows."""
    import sqlite_vec

    from paperforge.memory.db import get_memory_db_path

    db_path = get_memory_db_path(vault)
    conn = sqlite3.connect(str(db_path))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("CREATE TABLE papers (zotero_key TEXT PRIMARY KEY, title TEXT)")
    conn.execute("INSERT INTO papers VALUES ('A', 'Paper A')")
    conn.execute("CREATE VIRTUAL TABLE vec_body USING vec0(embedding float[3])")
    conn.execute("CREATE TABLE vec_body_meta (rowid INTEGER PRIMARY KEY, paper_id TEXT, unit_id TEXT)")
    for i in range(vec_rows):
        cur = conn.execute("INSERT INTO vec_body(embedding) VALUES (?)",
                           [json.dumps([0.1, 0.2, 0.3])])
        conn.execute("INSERT INTO vec_body_meta(rowid, paper_id, unit_id) VALUES (?, 'A', ?)",
                     (cur.lastrowid, f"u{i}"))
    conn.commit()
    conn.close()
    return db_path


def _vec_available(conn) -> bool:
    try:
        conn.execute("SELECT * FROM vec_body LIMIT 0")
        return True
    except Exception:
        return False


# ── 1. Successful build: reader through build, publish, new reader ────────


def test_shadow_publish_reader_contract(tmp_path: Path) -> None:
    """Reader open through build phase reads old data; after publish reads new."""
    from paperforge.embedding.build_target import BuildTarget, ShadowBuild

    vault = _make_vault(tmp_path)
    live = _seed_live_db(vault)
    target = BuildTarget(source_path=live, vector_path=live.with_suffix(".db.build"))

    with ShadowBuild(target) as shadow:
        shadow.prepare()
        # snapshot into candidate (load vec0 on both connections)
        import sqlite_vec

        src = sqlite3.connect(str(live))
        src.enable_load_extension(True)
        sqlite_vec.load(src)
        dst = sqlite3.connect(str(target.vector_path))
        dst.enable_load_extension(True)
        sqlite_vec.load(dst)
        src.backup(dst)
        src.close()
        dst.close()
        shadow.building()

        # Reader on live during build phase sees old rows
        reader = sqlite3.connect(str(live))
        reader.enable_load_extension(True)
        sqlite_vec.load(reader)
        assert reader.execute("SELECT COUNT(*) FROM vec_body_meta").fetchone()[0] == 5

        # Candidate gets new data
        cand = sqlite3.connect(str(target.vector_path))
        cand.enable_load_extension(True)
        sqlite_vec.load(cand)
        cur = cand.execute("INSERT INTO vec_body(embedding) VALUES (?)",
                           [json.dumps([0.9, 0.9, 0.9])])
        cand.execute("INSERT INTO vec_body_meta(rowid, paper_id, unit_id) VALUES (?, 'B', 'u9')",
                     (cur.lastrowid,))
        cand.commit()
        cand.close()
        shadow.seal()
        shadow.verified()
        # Publication barrier (D1): readers close before the swap on Windows
        reader.close()
        shadow.publish()

        # New reader on live path sees published data
        new_reader = sqlite3.connect(str(live))
        assert new_reader.execute("SELECT COUNT(*) FROM vec_body_meta").fetchone()[0] == 6
        new_reader.close()

    # No candidate files left after publish
    assert not target.vector_path.exists()
    assert not Path(str(target.vector_path) + "-wal").exists()


# ── 2. Worker failure → shadow deleted, live untouched ────────────────────


def test_abort_preserves_live(tmp_path: Path) -> None:
    from paperforge.embedding.build_target import BuildTarget, ShadowBuild

    vault = _make_vault(tmp_path)
    live = _seed_live_db(vault)
    before = live.read_bytes()
    target = BuildTarget(source_path=live, vector_path=live.with_suffix(".db.build"))

    with ShadowBuild(target) as shadow:
        shadow.prepare()
        shadow.building()
        shadow.abort()  # simulates worker failure mid-build

    assert live.read_bytes() == before, "live DB untouched on abort"
    assert not target.vector_path.exists(), "candidate deleted"


# ── 3. Cancellation == abort ──────────────────────────────────────────────


def test_exit_without_publish_aborts(tmp_path: Path) -> None:
    from paperforge.embedding.build_target import BuildTarget, ShadowBuild

    vault = _make_vault(tmp_path)
    live = _seed_live_db(vault)
    target = BuildTarget(source_path=live, vector_path=live.with_suffix(".db.build"))

    with pytest.raises(RuntimeError, match="cancelled"):
        with ShadowBuild(target) as shadow:
            shadow.prepare()
            shadow.building()
            # __exit__ with exception → abort
            raise RuntimeError("cancelled")

    # context manager exited abnormally → candidate cleaned
    assert not target.vector_path.exists()


# ── 4. Lifecycle transitions ──────────────────────────────────────────────


def test_publish_only_from_verified(tmp_path: Path) -> None:
    from paperforge.embedding.build_target import (
        BuildTarget,
        BuildTargetError,
        ShadowBuild,
    )

    vault = _make_vault(tmp_path)
    live = _seed_live_db(vault)
    target = BuildTarget(source_path=live, vector_path=live.with_suffix(".db.build"))

    shadow = ShadowBuild(target)
    with pytest.raises(BuildTargetError):
        shadow.publish()  # NEW → publish invalid
    shadow.prepare()
    with pytest.raises(BuildTargetError):
        shadow.publish()  # PREPARED → publish invalid
    shadow.abort()
    assert shadow.state == shadow.ABORTED
    shadow.abort()  # idempotent


# ── 5. Crash recovery: stale candidate cleaned unconditionally ────────────


def test_stale_candidate_cleaned_on_next_start(tmp_path: Path) -> None:
    from paperforge.embedding.build_target import BuildTarget, ShadowBuild

    vault = _make_vault(tmp_path)
    live = _seed_live_db(vault)
    target = BuildTarget(source_path=live, vector_path=live.with_suffix(".db.build"))
    target.vector_path.write_bytes(b"stale candidate from crashed build")
    Path(str(target.vector_path) + "-wal").write_bytes(b"stale wal")

    shadow = ShadowBuild(target)
    shadow.abort()  # D6: unconditional cleanup — no build_state consulted
    assert not target.vector_path.exists()
    assert not Path(str(target.vector_path) + "-wal").exists()
    assert live.exists(), "live never touched"


# ── 6. Verification checklist ─────────────────────────────────────────────


def test_verify_candidate_mismatch_rejected(tmp_path: Path) -> None:
    from paperforge.embedding.build_target import verify_candidate

    vault = _make_vault(tmp_path)
    live = _seed_live_db(vault)
    build = live.with_suffix(".db.build")

    src = sqlite3.connect(str(live))
    dst = sqlite3.connect(str(build))
    src.backup(dst)
    src.close()
    dst.close()

    # Expected count mismatch → rejected
    report = verify_candidate(build, dimension=3, expected_count=999)
    assert not report["ok"]
    assert "expected" in report["reason"]

    # Correct count → ok
    report2 = verify_candidate(build, dimension=3, expected_count=5)
    assert report2["ok"], report2


def test_verify_zero_count_valid(tmp_path: Path) -> None:
    """Zero-vector candidate publishes legitimately (D4)."""
    from paperforge.embedding.build_target import verify_candidate

    vault = _make_vault(tmp_path)
    live = vault / "System" / "PaperForge" / "indexes" / "paperforge.db"
    conn = sqlite3.connect(str(live))
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

    build = live.with_suffix(".db.build")
    src = sqlite3.connect(str(live))
    dst = sqlite3.connect(str(build))
    src.backup(dst)
    src.close()
    dst.close()

    report = verify_candidate(build, dimension=3, expected_count=0)
    assert report["ok"], report  # empty DB + expected 0 → valid


# ── 7. Writer lock re-entrancy + cross-process exclusion ──────────────────


def test_writer_lock_reentrant_same_thread(tmp_path: Path) -> None:
    from paperforge.memory.db import WriterLock

    vault = _make_vault(tmp_path)
    _seed_live_db(vault)

    with WriterLock(vault):
        with WriterLock(vault):  # nested in same thread — must not deadlock
            assert True


def test_writer_lock_excludes_second_process(tmp_path: Path) -> None:
    """Second process writer blocks while first holds the lock."""
    import subprocess
    import sys
    import time

    from paperforge.memory.db import WriterLock

    vault = _make_vault(tmp_path)
    _seed_live_db(vault)

    lock = WriterLock(vault, timeout=1)
    lock.__enter__()
    try:
        # Child process tries to acquire with short timeout → must fail fast
        code = (
            "import sys; sys.path.insert(0, r'{}'); "
            "from paperforge.memory.db import WriterLock; "
            "from pathlib import Path; "
            "v = Path(r'{}'); "
            "l = WriterLock(v, timeout=0.5); l.__enter__(); print('ACQUIRED'); l.__exit__(None,None,None)"
        ).format(str(Path.cwd()), str(vault))
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=10,
        )
        assert "ACQUIRED" not in result.stdout, "second writer must block while lock held"
    finally:
        lock.__exit__(None, None, None)


# ── 8. Direct-connect read sites open read-only ───────────────────────────


def test_dashboard_connection_read_only(tmp_path: Path) -> None:
    """Dashboard/probe connect read-only; writer transaction doesn't block them."""
    vault = _make_vault(tmp_path)
    live = _seed_live_db(vault)
    live.parent.mkdir(parents=True, exist_ok=True)

    # Simulate an open writer transaction
    writer = sqlite3.connect(str(live))
    writer.execute("BEGIN IMMEDIATE")
    try:
        # Read-only URI connect works concurrently (WAL)
        ro = sqlite3.connect(f"file:{live.as_posix()}?mode=ro", uri=True)
        ro.close()
    finally:
        writer.rollback()
        writer.close()


# ── Regression tests from code review ─────────────────────────────────────


def test_cleanup_stale_does_not_break_state_machine(tmp_path: Path) -> None:
    """D6: cleanup_stale before prepare must not transition NEW → ABORTED."""
    from paperforge.embedding.build_target import BuildTarget, ShadowBuild

    vault = _make_vault(tmp_path)
    live = _seed_live_db(vault)
    target = BuildTarget(source_path=live, vector_path=live.with_suffix(".db.build"))

    shadow = ShadowBuild(target)
    shadow.cleanup_stale()   # stale candidate from crashed build
    shadow.prepare()         # must still be valid (NEW → PREPARED)
    shadow.building()
    shadow.abort()


def test_publish_uses_reader_barrier(tmp_path: Path) -> None:
    """D1: publish takes the reader lock; sidecar cleanup inside barrier."""
    from paperforge.embedding.build_target import BuildTarget, ShadowBuild

    vault = _make_vault(tmp_path)
    live = _seed_live_db(vault)
    target = BuildTarget(source_path=live, vector_path=live.with_suffix(".db.build"))

    with ShadowBuild(target) as shadow:
        shadow.prepare()
        import sqlite_vec

        src = sqlite3.connect(str(live))
        src.enable_load_extension(True)
        sqlite_vec.load(src)
        dst = sqlite3.connect(str(target.vector_path))
        dst.enable_load_extension(True)
        sqlite_vec.load(dst)
        src.backup(dst)
        src.close()
        dst.close()
        shadow.building()
        shadow.seal()
        shadow.verified()
        shadow.publish()

    # .read.lock file may linger (filelock) but publish succeeded and
    # candidate is gone
    assert not target.vector_path.exists()
    assert live.exists()


# ── Remaining PRD test cases ──────────────────────────────────────────────


def test_dimension_change_rebuild_publishes(tmp_path: Path) -> None:
    """D4/D5: candidate rebuilt at NEW dimension publishes; verify uses
    candidate dimension, not live (regression: live reports old dim)."""
    from paperforge.embedding.build_target import (
        BuildTarget,
        ShadowBuild,
        verify_candidate,
    )

    vault = _make_vault(tmp_path)
    live = _seed_live_db(vault)  # live vec0 at dim 3

    import sqlite_vec

    # Build candidate at a DIFFERENT dimension (simulated model migration)
    build = live.with_suffix(".db.build")
    conn = sqlite3.connect(str(build))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("CREATE VIRTUAL TABLE vec_body USING vec0(embedding float[5])")
    conn.execute("CREATE TABLE vec_body_meta (rowid INTEGER PRIMARY KEY, paper_id TEXT, unit_id TEXT)")
    cur = conn.execute("INSERT INTO vec_body(embedding) VALUES (?)",
                       [json.dumps([0.1] * 5)])
    conn.execute("INSERT INTO vec_body_meta(rowid, paper_id, unit_id) VALUES (?, 'A', 'u1')",
                 (cur.lastrowid,))
    conn.commit()
    conn.close()

    # Verify with the CANDIDATE dimension (5), not live (3)
    report = verify_candidate(build, dimension=5, expected_count=1)
    assert report["ok"], report

def test_integrity_failure_blocks_publish(tmp_path: Path) -> None:
    """D4: corrupt candidate fails integrity_check → verify rejects."""
    from paperforge.embedding.build_target import verify_candidate

    vault = _make_vault(tmp_path)
    live = _seed_live_db(vault)
    build = live.with_suffix(".db.build")
    build.write_bytes(b"not a database at all")

    report = verify_candidate(build, dimension=3, expected_count=5)
    assert not report["ok"]
    assert any(k in report["reason"] for k in ("integrity", "missing", "not a database"))


def test_memory_build_blocked_during_shadow(tmp_path: Path) -> None:
    """D2: concurrent memory writer blocks on writer lock during shadow build."""
    import subprocess
    import sys

    from paperforge.memory.db import WriterLock

    vault = _make_vault(tmp_path)
    _seed_live_db(vault)

    # Helper script: try to acquire the writer lock with a short timeout
    script = tmp_path / "try_lock.py"
    script.write_text(
        "import sys\n"
        "sys.path.insert(0, r'{}')\n"
        "from pathlib import Path\n"
        "from paperforge.memory.db import WriterLock\n"
        "v = Path(r'{}')\n"
        "try:\n"
        "    l = WriterLock(v, timeout=0.5)\n"
        "    l.__enter__()\n"
        "    print('ACQUIRED')\n"
        "    l.__exit__(None, None, None)\n"
        "except Exception as e:\n"
        "    print('BLOCKED', type(e).__name__)\n"
        .format(str(Path.cwd()), str(vault)),
        encoding="utf-8",
    )

    lock = WriterLock(vault, timeout=1)
    lock.__enter__()
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=10,
        )
        assert "ACQUIRED" not in result.stdout, "memory writer must block during shadow build"
        assert "BLOCKED" in result.stdout, f"bounded wait then retryable error, got: {result.stdout!r}"
    finally:
        lock.__exit__(None, None, None)


def test_refresh_paper_bounded_wait_during_shadow(tmp_path: Path) -> None:
    """D2b: refresh_paper blocks up to 30s while writer lock held, then raises."""
    from paperforge.memory.db import WriterLock
    from paperforge.memory.refresh import refresh_paper

    vault = _make_vault(tmp_path)
    _seed_live_db(vault)

    lock = WriterLock(vault, timeout=0.5)
    lock.__enter__()
    try:
        with pytest.raises(Exception):  # filelock.Timeout after bounded wait
            refresh_paper(vault, {"zotero_key": "A", "title": "Paper A"})
    finally:
        lock.__exit__(None, None, None)


# ── P0-2: real mutators take the writer lock ──────────────────────────────


def test_build_from_index_acquires_writer_lock(tmp_path: Path) -> None:
    """build_from_index() takes the writer lock — verified by holding it."""
    from paperforge.memory.builder import build_from_index
    from paperforge.memory.db import WriterLock, get_memory_db_path
    from paperforge.worker.asset_index import atomic_write_index, get_index_path
    import threading
    import time

    vault = _make_vault(tmp_path)
    idx = get_index_path(vault)
    idx.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_index(idx, {"items": [{"zotero_key": "A", "title": "Paper A"}], "generated_at": ""})
    # Hold the writer lock; build_from_index must block (cross-owner).
    lock = WriterLock(vault, timeout=0.5)
    lock.__enter__()
    result = {}

    def _build():
        try:
            build_from_index(vault)
            result["ok"] = True
        except Exception as exc:
            result["err"] = str(exc)

    t = threading.Thread(target=_build)
    t.start()
    time.sleep(1.0)
    # While we hold the lock, the build must not have completed
    assert "ok" not in result, "build_from_index must block while writer lock held"
    lock.__exit__(None, None, None)
    t.join(timeout=15)
    assert not t.is_alive(), "build_from_index should finish after lock release"
    assert result.get("ok"), result


# ── Re-review P0-2: barrier timeout propagates, reentrancy ──────────────


def test_reader_barrier_timeout_propagates_not_degrade(tmp_path: Path) -> None:
    """Holding .read.lock must make a reader Timeout — never read unlocked."""
    from filelock import FileLock, Timeout

    from paperforge.memory.db import get_memory_db_path, open_live_reader

    vault = _make_vault(tmp_path)
    db_path = get_memory_db_path(vault)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

    blocker = FileLock(str(db_path) + ".read.lock", timeout=0.2)
    blocker.acquire()
    try:
        with pytest.raises(Timeout):
            with open_live_reader(vault, db_path) as c:
                c.execute("SELECT 1")
    finally:
        blocker.release()


def test_reader_barrier_reentrant_nested(tmp_path: Path) -> None:
    """Nested open_live_reader must not self-deadlock (same thread)."""
    from paperforge.memory.db import get_memory_db_path, open_live_reader

    vault = _make_vault(tmp_path)
    db_path = get_memory_db_path(vault)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

    with open_live_reader(vault, db_path) as c1:
        with open_live_reader(vault, db_path) as c2:
            assert c1 is not c2
            assert c2.execute("SELECT 1") is not None


def test_publish_checkpoints_live_before_replace(tmp_path: Path) -> None:
    """P0-3: _publish_files checkpoints the OLD live WAL BEFORE os.replace —
    a failed swap must leave the old live self-contained (no data loss)."""
    from unittest.mock import patch

    from paperforge.embedding import build_target
    from paperforge.embedding.build_target import BuildTarget, ShadowBuild
    from paperforge.memory.db import get_memory_db_path

    vault = _make_vault(tmp_path)
    live = _seed_live_db(vault, vec_rows=3)
    # Keep the live in WAL mode WITH uncheckpointed data: hold a connection
    # open so the WAL survives (sqlite auto-checkpoints on close).
    c = sqlite3.connect(str(live))
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("INSERT INTO papers VALUES ('B', 'Paper B')")
    c.commit()
    wal_path = Path(str(live) + "-wal")
    assert wal_path.exists(), "WAL with uncheckpointed commit must exist"

    target = BuildTarget(source_path=live, vector_path=Path(str(live) + ".build"))
    shadow = ShadowBuild(target)
    shadow.prepare()
    shadow.building()
    cand = sqlite3.connect(str(target.vector_path))
    cand.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    cand.commit()
    cand.close()
    shadow.seal()
    shadow.verified()

    # Simulate a FAILED swap: os.replace raises → publish must abort and the
    # old live (with its WAL) must still be fully readable.
    with patch.object(build_target.os, "replace", side_effect=OSError("simulated replace failure")):
        with pytest.raises(OSError):
            shadow.publish()
    c.execute("SELECT COUNT(*) FROM papers").fetchone()
    assert c.execute("SELECT COUNT(*) FROM papers").fetchone()[0] == 2, (
        "old live must retain its uncheckpointed commit after failed publish"
    )
    assert wal_path.exists(), "old live WAL must survive a failed swap"
    c.close()


def test_plain_build_model_change_routes_to_shadow(tmp_path: Path) -> None:
    """P1: a plain `embed build` (no --force, no --resume) with a recorded
    model different from the current config must route through shadow."""
    from unittest.mock import patch

    from paperforge.commands import embed

    vault = _make_vault(tmp_path)
    from paperforge.memory.db import get_memory_db_path
    live = get_memory_db_path(vault)
    # Full schema (papers with doi etc.) + vec0 at dim 3 + a DIFFERENT model
    import sqlite_vec
    c = sqlite3.connect(str(live))
    c.enable_load_extension(True)
    sqlite_vec.load(c)
    from paperforge.memory.schema import ensure_schema
    ensure_schema(c)
    c.execute(
        "INSERT OR REPLACE INTO build_state (key, value) VALUES "
        "('model', '\"old-model\"'), ('status', '\"completed\"'), ('mode', '\"api\"')"
    )
    c.commit()
    c.close()

    args = argparse.Namespace(
        vault_path=vault,
        embed_subcommand="build",
        json=True,
        force=False,
        resume=False,
    )
    # Current model differs from recorded — shadow must trigger.  Mock only
    # the API path so the run reaches the shadow decision without encoding.
    fake_status = {
        "mode": "api", "model": "new-model", "db_exists": True, "healthy": True,
        "chunk_count": 0, "body_chunk_count": 0, "object_chunk_count": 0, "total_chunks": 0,
        "dimension": 3, "corrupted": False, "error": "", "vector_state": "ready",
    }
    with patch("paperforge.embedding._config.get_api_model", return_value="new-model"), \
         patch.object(embed, "get_embed_status", return_value=fake_status), \
         patch.object(embed, "read_index", return_value={"items": []}), \
         patch.object(embed, "_preflight_check", return_value={"ok": True}), \
         patch.object(embed, "ensure_vec_tables", return_value=None):
        rc = embed.run(args)
    # Empty index: build completes trivially; the point is no crash and the
    # requires_shadow decision is exercised (force path with shadow prepare
    # runs against the live DB even with zero papers).
    assert rc == 0
    # Shadow must have been triggered: candidate was created AND published
    # (live replaced — no .build leftover, build_state now records new-model)
    from paperforge.embedding.build_state import read_vector_build_state
    assert not Path(str(live) + ".build").exists()
    assert read_vector_build_state(vault).get("model") == "new-model"


# ── Final hardening: P0-3 publish commit-point, P0-4 events, P1-2 busy ──


def test_publish_state_set_before_sidecar_cleanup(tmp_path: Path) -> None:
    """P0-3: after os.replace the build is PUBLISHED even if post-swap
    sidecar cleanup fails — bookkeeping must not flip a successful publish."""
    from unittest.mock import patch

    from paperforge.embedding import build_target
    from paperforge.embedding.build_target import BuildTarget, ShadowBuild
    from paperforge.memory.db import get_memory_db_path

    vault = _make_vault(tmp_path)
    live = _seed_live_db(vault, vec_rows=3)
    target = BuildTarget(source_path=live, vector_path=Path(str(live) + ".build"))
    shadow = ShadowBuild(target)
    shadow.prepare()
    shadow.building()
    cand = sqlite3.connect(str(target.vector_path))
    cand.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    cand.commit()
    cand.close()
    shadow.seal()
    shadow.verified()

    # os.replace succeeds; the post-swap sidecar cleanup (unlink) raises an
    # OSError.  Real cleanup is best-effort (wrapped), so publish must still
    # complete with state PUBLISHED — the swap is the commit point and a
    # leftover old-live sidecar must not flip the outcome.
    real_replace = build_target.os.replace
    real_unlink = Path.unlink

    def unlink_fails(self, *a, **k):
        if str(self).endswith(("-wal", "-shm")):
            raise OSError("simulated cleanup failure")
        return real_unlink(self, *a, **k)

    with patch.object(build_target.os, "replace", side_effect=real_replace), \
         patch.object(Path, "unlink", unlink_fails):
        shadow.publish()  # must NOT raise — cleanup is best-effort
    assert shadow.state == shadow.PUBLISHED, (
        "publish must be marked PUBLISHED at the os.replace commit point"
    )
    # New live is in place
    assert Path(str(live)).exists()
    shadow.abort()  # must be a no-op, must NOT delete the new live
    assert Path(str(live)).exists()


def test_export_reading_log_no_nameerror(tmp_path: Path) -> None:
    """P0-4: export_reading_log uses open_live_reader and must not NameError."""
    from paperforge.memory.db import get_memory_db_path
    from paperforge.memory.events import export_reading_log

    vault = _make_vault(tmp_path)
    db_path = get_memory_db_path(vault)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(db_path))
    c.execute("CREATE TABLE papers (zotero_key TEXT PRIMARY KEY, citation_key TEXT, title TEXT, year TEXT, first_author TEXT)")
    c.commit()
    c.close()
    result = export_reading_log(vault)
    assert result == []


def test_write_correction_note_blocks_during_shadow(tmp_path: Path) -> None:
    """P0-4: write_correction_note takes the writer lock — a shadow build
    holding it blocks the correction write, then succeeds after release."""
    import threading
    import time

    from paperforge.memory.db import WriterLock, get_memory_db_path
    from paperforge.memory.events import write_correction_note

    vault = _make_vault(tmp_path)
    db_path = get_memory_db_path(vault)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(db_path))
    c.execute("CREATE TABLE paper_events (paper_id TEXT, event_type TEXT, payload_json TEXT)")
    c.commit()
    c.close()

    lock = WriterLock(vault, timeout=1.0)
    lock.__enter__()
    result = {}

    def _write():
        try:
            ok = write_correction_note(vault, "P1", "orig", "correction")
            result["ok"] = ok
        except Exception as exc:
            result["err"] = str(exc)

    t = threading.Thread(target=_write)
    t.start()
    time.sleep(0.5)
    assert "ok" not in result and "err" not in result, (
        "correction write must block while writer lock held"
    )
    lock.__exit__(None, None, None)
    t.join(timeout=10)
    assert not t.is_alive()
    assert result.get("ok") is True, result


def test_checkpoint_busy_rejects_publish(tmp_path: Path) -> None:
    """P1-2: a busy/incomplete checkpoint must fail, not proceed."""
    from unittest.mock import patch

    from paperforge.embedding.build_target import (
        BuildTargetError,
        _checkpoint_truncate,
    )

    db_path = _seed_live_db(_make_vault(tmp_path), vec_rows=2)
    conn = sqlite3.connect(str(db_path))
    # Normal checkpoint on an empty/clean DB succeeds (busy=0).
    _checkpoint_truncate(conn, "candidate")

    # Simulate a busy checkpoint with a fake connection whose wal_checkpoint
    # returns (1, 10, 5) — busy != 0 must fail the seal/publish.
    class _FakeCur:
        def fetchone(self):
            return (1, 10, 5)

    class _FakeConn:
        def execute(self, _sql):
            return _FakeCur()

    with pytest.raises(BuildTargetError, match="checkpoint incomplete"):
        _checkpoint_truncate(_FakeConn(), "candidate")
    conn.close()


# ── Round 5 hardening: commit semantics, layout routing, lock scoping ──


def test_post_publish_bookkeeping_failure_returns_success(tmp_path: Path) -> None:
    """P0-2: once PUBLISHED, a bookkeeping failure must return rc=0 with
    published=true — never abort/mark-failed a live new DB."""
    from unittest.mock import patch

    from paperforge.commands import embed

    vault = _make_vault(tmp_path)
    from paperforge.memory.db import get_memory_db_path
    live = get_memory_db_path(vault)
    import sqlite_vec
    c = sqlite3.connect(str(live))
    c.enable_load_extension(True)
    sqlite_vec.load(c)
    from paperforge.memory.schema import ensure_schema
    ensure_schema(c)
    c.commit()
    c.close()

    args = argparse.Namespace(
        vault_path=vault, embed_subcommand="build", json=True, force=True, resume=False,
    )
    fake_status = {
        "mode": "api", "model": "m", "db_exists": True, "healthy": True,
        "chunk_count": 0, "body_chunk_count": 0, "object_chunk_count": 0, "total_chunks": 0,
        "dimension": 3, "corrupted": False, "error": "", "vector_state": "ready",
    }
    # make mark_vector_build_state fail AFTER publish
    with patch("paperforge.embedding._config.get_api_model", return_value="m"), \
         patch.object(embed, "get_embed_status", return_value=fake_status), \
         patch.object(embed, "read_index", return_value={"items": []}), \
         patch.object(embed, "_preflight_check", return_value={"ok": True}), \
         patch.object(embed, "ensure_vec_tables", return_value=None), \
         patch.object(embed, "write_vector_runtime", side_effect=RuntimeError("bookkeeping boom")):
        rc = embed.run(args)
    assert rc == 0, f"published build must not report failure, rc={rc}"
    # new live is in place
    assert not Path(str(live) + ".build").exists()
    assert Path(str(live)).exists()


def test_incremental_write_rejects_dimension_recreate(tmp_path: Path) -> None:
    """P0-3: live incremental write path must raise VectorRebuildRequired
    instead of silently dropping live vec0 tables on dimension mismatch."""
    from paperforge.embedding.dim_detect import VectorRebuildRequired
    from paperforge.memory.db import get_memory_db_path

    vault = _make_vault(tmp_path)
    live = get_memory_db_path(vault)
    import sqlite_vec
    c = sqlite3.connect(str(live))
    c.enable_load_extension(True)
    sqlite_vec.load(c)
    c.execute("CREATE VIRTUAL TABLE vec_body USING vec0(embedding float[3])")
    c.commit()
    c.close()

    from unittest.mock import patch

    from paperforge.embedding import dim_detect
    with patch.object(dim_detect, "detect_embedding_dim", return_value=1536):
        conn = sqlite3.connect(str(live))
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        try:
            with pytest.raises(VectorRebuildRequired):
                dim_detect.ensure_vec_tables(conn, vault, allow_recreate=False)
        finally:
            conn.close()
    # live table untouched
    c = sqlite3.connect(f"file:{live.as_posix()}?mode=ro", uri=True)
    row = c.execute("SELECT sql FROM sqlite_master WHERE name='vec_body'").fetchone()
    assert row and "float[3]" in row[0], "live vec_body must not be recreated"
    c.close()


def test_writer_lock_per_path_no_false_reentry(tmp_path: Path) -> None:
    """P1-2: WriterLock depth is keyed per DB path — nesting two vaults in
    one thread takes BOTH file locks."""
    import threading

    from paperforge.memory.db import WriterLock

    v1 = tmp_path / "a"
    v2 = tmp_path / "b"
    (v1 / "System" / "PaperForge" / "indexes").mkdir(parents=True, exist_ok=True)
    (v2 / "System" / "PaperForge" / "indexes").mkdir(parents=True, exist_ok=True)

    l1 = WriterLock(v1)
    l2 = WriterLock(v2)
    l1.__enter__()
    try:
        # P1-2: v2's file lock is INDEPENDENT of v1's — it must be
        # acquirable while v1 is held (a shared depth counter would have
        # treated v2 as re-entry and skipped its lock, allowing a second
        # writer into vault B).
        l2.__enter__()
        assert l2._acquired, "v2 must take its own file lock"
        l2.__exit__(None, None, None)
        # Same-vault nesting still re-enters without a second file lock.
        l1.__enter__()  # re-entry on SAME key
        assert not l1._acquired, "same-vault nesting must not re-acquire"
        l1.__exit__(None, None, None)
        print("per-path writer lock: OK")
    finally:
        l1.__exit__(None, None, None)
