"""Integration tests for embed status vec0 health probe.

Verifies that embed status --json returns healthy=false when a vec0 table
with meta rows is dropped (simulating corruption).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PYTHON = Path(r"D:\L\OB\Literature-hub\.venv\Scripts\python.exe")
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _build_vault(tmp_path: Path) -> Path:
    """Build a minimal vault with paperforge.json and a seeded memory DB."""
    vault = tmp_path / "vault"
    vault.mkdir(parents=True)
    (vault / "paperforge.json").write_text(
        '{"vault_config":{"system_dir":"System"}}', encoding="utf-8"
    )
    (vault / "System" / "PaperForge").mkdir(parents=True)
    return vault


def _run_embed_status(vault: Path) -> dict:
    """Run embed status --json and return the parsed data dict."""
    result = subprocess.run(
        [
            str(PYTHON),
            "-m",
            "paperforge",
            "--vault",
            str(vault),
            "embed",
            "status",
            "--json",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    assert result.returncode == 0, f"embed status failed:\n{result.stderr}"
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is True
    return parsed["data"]


def _db_path(vault: Path) -> Path:
    """Resolve paperforge.db path using the same logic as get_memory_db_path."""
    from paperforge.memory.db import get_memory_db_path
    return get_memory_db_path(vault)


@pytest.fixture
def vault_with_vec0(tmp_path: Path) -> Path:
    """Create a vault with a seeded paperforge.db containing vec0 tables + meta rows."""
    vault = _build_vault(tmp_path)

    # Create DB schema explicitly (embed status doesn't auto-create)
    from paperforge.memory.db import get_connection, get_memory_db_path, ensure_vec_extension
    from paperforge.memory.schema import ensure_schema

    db_path = get_memory_db_path(vault)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    ensure_schema(conn)
    conn.close()

    # Insert data via a separate connection with vec0 loaded
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    try:
        conn.enable_load_extension(True)
        import sqlite_vec
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception:
        pass

    # Insert meta row into vec_fulltext_meta so total_meta > 0
    conn.execute(
        "INSERT INTO vec_fulltext_meta (rowid, paper_id, chunk_index, text, source) "
        "VALUES (1, 'TESTKEY', 0, 'test', 'fulltext')"
    )

    # Insert a zero vector into vec_fulltext so the k-NN probe works
    zero_vec = [0.0] * 1536
    vec_json = json.dumps(zero_vec)
    conn.execute(
        "INSERT INTO vec_fulltext (rowid, embedding) VALUES (1, ?)",
        (vec_json,),
    )

    conn.commit()
    conn.close()
    return vault


class TestHealthProbe:
    """embed status --json runs vec0 k-NN probe and reports healthy=false when vec0 broken."""

    def test_healthy_when_vec0_ok(self, vault_with_vec0: Path):
        """When vec0 tables are intact, health probe passes."""
        data = _run_embed_status(vault_with_vec0)
        assert data["healthy"] is True, f"Expected healthy=True, got {data}"
        assert data["corrupted"] is False
        assert data["chunk_count"] >= 1

    def test_unhealthy_when_vec0_table_dropped(self, vault_with_vec0: Path):
        """When a vec0 virtual table is dropped but meta rows exist, healthy=false."""
        db_path = _db_path(vault_with_vec0)
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        try:
            conn.enable_load_extension(True)
            import sqlite_vec
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        except Exception:
            pass
        conn.execute("DROP TABLE IF EXISTS vec_fulltext")
        conn.commit()
        conn.close()

        data = _run_embed_status(vault_with_vec0)
        assert data["healthy"] is False, f"Expected healthy=False after dropping vec table, got {data}"
        assert data["corrupted"] is True
        err = data.get("error", "").lower()
        assert "vec0 probe failed" in err or "no such table" in err, f"Unexpected error: {data.get('error')}"
