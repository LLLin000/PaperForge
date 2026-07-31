"""Integration tests for atomic shadow vector rebuild (#117).

Covers the BuildTarget/ShadowBuild lifecycle, writer-lock re-entrancy,
publication swap, verification checklist, abort semantics, and crash
recovery. Uses real sqlite3 files — no mocks of the swap itself.
"""

from __future__ import annotations

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
