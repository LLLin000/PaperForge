"""vec0 vector-row lifecycle (pure sqlite-vec).

Ownership, transaction, WriterLock, and rollback semantics are unchanged
from the previous home (``paperforge.embedding._chroma``): the caller owns
the transaction boundary.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from paperforge.memory.db import ensure_vec_extension, get_memory_db_path, get_connection
from paperforge.memory.schema import ensure_schema

logger = logging.getLogger(__name__)

_VEC_TABLE_MAP = {
    "paperforge_fulltext": ("vec_fulltext", "vec_fulltext_meta"),
    "paperforge_body": ("vec_body", "vec_body_meta"),
    "paperforge_objects": ("vec_objects", "vec_objects_meta"),
}


def delete_paper_vectors_in_conn(conn: sqlite3.Connection, key: str) -> int:
    """Delete vec0 rows and meta rows for *key*. No commit/rollback/close.

    Safe to call from within an outer transaction — the caller owns the
    transaction boundary.  Returns count of vector rows deleted.
    """
    total = 0
    for vec_table, meta_table in _VEC_TABLE_MAP.values():
        rows = conn.execute(
            f"SELECT rowid FROM {meta_table} WHERE paper_id = ?", (key,)
        ).fetchall()
        rowids = [r["rowid"] for r in rows]
        if rowids:
            placeholders = ",".join("?" for _ in rowids)
            conn.execute(
                f"DELETE FROM {vec_table} WHERE rowid IN ({placeholders})", rowids
            )
            conn.execute(f"DELETE FROM {meta_table} WHERE paper_id = ?", (key,))
        total += len(rowids)
    return total


def delete_paper_vectors(vault: Path, zotero_key: str) -> int:
    """Delete a paper's vectors under the global writer lock (P0-4).

    A shadow publish swaps the whole live DB — an unlocked delete could be
    overwritten by the publish or race the snapshot.
    """
    from paperforge.memory.db import WriterLock

    with WriterLock(vault):
        return _delete_paper_vectors_locked(vault, zotero_key)


def _delete_paper_vectors_locked(vault: Path, zotero_key: str) -> int:
    """Locked body: caller owns the WriterLock.

    Multi-verification before deleting a vector row — never delete a row
    that is not provably owned by *zotero_key*:
    1. rowids come from ``meta WHERE paper_id = ?`` (ownership by
       construction);
    2. each rowid is re-verified against its meta row owner immediately
       before the vec0 DELETE (guards a corrupted/misaligned meta rowid
       that could otherwise delete another paper's vector);
    3. the vec0 DELETE rowcount must equal the expected rowid count, else
       the whole delete is rolled back (partial deletion never commits).
    """
    db_path = get_memory_db_path(vault)
    # A vault without a vector substrate is a valid absent carrier.  Do not
    # create a database merely because orphan cleanup was requested.
    if not db_path.exists():
        return 0

    conn = get_connection(db_path)
    try:
        names = tuple(
            table
            for vec_table, meta_table in _VEC_TABLE_MAP.values()
            for table in (vec_table, meta_table)
        )
        placeholders = ",".join("?" for _ in names)
        existing = conn.execute(
            f"SELECT 1 FROM sqlite_master WHERE name IN ({placeholders}) LIMIT 1",
            names,
        ).fetchone()
        if existing is None:
            return 0

        ensure_vec_extension(conn)
        ensure_schema(conn)
        total = 0
        for vec_table, meta_table in _VEC_TABLE_MAP.values():
            rows = conn.execute(
                f"SELECT rowid FROM {meta_table} WHERE paper_id = ?", (zotero_key,)
            ).fetchall()
            rowids = [r["rowid"] for r in rows]
            if not rowids:
                continue
            # Verification 2: every rowid must still be owned by this paper.
            verified: list[int] = []
            for rowid in rowids:
                owner = conn.execute(
                    f"SELECT paper_id FROM {meta_table} WHERE rowid = ?", (rowid,)
                ).fetchone()
                if owner is not None and owner["paper_id"] == zotero_key:
                    verified.append(rowid)
                else:
                    logger.warning(
                        "vec delete: rowid %s in %s not owned by %s — skipped",
                        rowid, meta_table, zotero_key,
                    )
            if not verified:
                continue
            placeholders = ",".join("?" for _ in verified)
            cur = conn.execute(
                f"DELETE FROM {vec_table} WHERE rowid IN ({placeholders})", verified
            )
            # Verification 3: full deletion or rollback — a partial delete
            # (e.g. missing vec0 row) must never commit silently.
            if cur.rowcount != len(verified):
                raise RuntimeError(
                    f"vec delete partial: {cur.rowcount}/{len(verified)} rows "
                    f"removed from {vec_table} for {zotero_key}"
                )
            conn.execute(
                f"DELETE FROM {meta_table} WHERE paper_id = ?", (zotero_key,)
            )
            total += len(verified)
        conn.commit()
        return total
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
