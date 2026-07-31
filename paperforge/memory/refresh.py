from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.paper_state import upsert_paper_state
from paperforge.memory.schema import ensure_schema
from paperforge.worker.asset_state import (
    compute_lifecycle,
    compute_maturity,
    compute_next_step,
)


def refresh_paper(vault: Path, entry: dict) -> bool:
    """Upsert a single paper into memory DB. Entry is from _build_entry() output.

    Delegates to ``upsert_paper_state()`` which uses ``INSERT … ON CONFLICT DO UPDATE``,
    preserving rowids and letting the built-in FTS triggers fire automatically.

    Takes the cross-process writer lock with a bounded wait (D2b): during an
    active shadow rebuild (maintenance mode) this blocks up to 30s, then
    raises a retryable error rather than silently dropping the write.
    """
    from paperforge.memory.db import WriterLock, get_connection, get_memory_db_path

    zotero_key = entry.get("zotero_key", "")
    if not zotero_key:
        return False

    generated_at = datetime.now(timezone.utc).isoformat()

    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return False

    with WriterLock(vault, timeout=30):
        conn = get_connection(db_path, read_only=False)
        try:
            ensure_schema(conn)

            entry["lifecycle"] = str(compute_lifecycle(entry))
            entry["maturity"] = compute_maturity(entry)
            entry["next_step"] = str(compute_next_step(entry))

            upsert_paper_state(conn, vault=vault, entry=entry, generated_at=generated_at)

            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
