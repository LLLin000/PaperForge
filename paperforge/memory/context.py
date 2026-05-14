from __future__ import annotations

from pathlib import Path

from paperforge.memory.db import get_connection, get_memory_db_path


def _build_collection_tree(conn) -> list[dict]:
    """Build collection hierarchy from papers.collection_path.
    
    Each collection_path is pipe-separated, e.g. "骨科 | 骨折".
    Returns flat list of top-level collections with sub-collections.
    """
    rows = conn.execute(
        "SELECT collection_path, COUNT(*) as cnt FROM papers "
        "WHERE collection_path != '' "
        "GROUP BY collection_path ORDER BY cnt DESC"
    ).fetchall()
    top: dict[str, dict] = {}
    for row in rows:
        parts = [p.strip() for p in row["collection_path"].split("|") if p.strip()]
        if not parts:
            continue
        root = parts[0]
        if root not in top:
            top[root] = {"name": root, "count": 0, "sub": []}
        top[root]["count"] += row["cnt"]
        if len(parts) > 1:
            sub_name = parts[-1]
            if sub_name not in top[root]["sub"]:
                top[root]["sub"].append(sub_name)
    for c in top.values():
        c["sub"] = sorted(c["sub"])
    return sorted(top.values(), key=lambda x: -x["count"])


def get_agent_context(vault: Path) -> dict | None:
    """Build agent context from paperforge.db — library stats + collection tree.
    
    Returns None if DB is missing or query fails.
    """
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return None

    conn = get_connection(db_path, read_only=True)
    try:
        total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]

        domains = {
            r["domain"]: r["cnt"]
            for r in conn.execute(
                "SELECT domain, COUNT(*) as cnt FROM papers GROUP BY domain ORDER BY cnt DESC"
            ).fetchall()
        }

        lifecycle_counts = {
            r["lifecycle"]: r["cnt"]
            for r in conn.execute(
                "SELECT lifecycle, COUNT(*) as cnt FROM papers GROUP BY lifecycle"
            ).fetchall()
        }

        ocr_counts = {
            r["ocr_status"]: r["cnt"]
            for r in conn.execute(
                "SELECT ocr_status, COUNT(*) as cnt FROM papers GROUP BY ocr_status"
            ).fetchall()
        }

        deep_counts = {
            r["deep_reading_status"]: r["cnt"]
            for r in conn.execute(
                "SELECT deep_reading_status, COUNT(*) as cnt FROM papers GROUP BY deep_reading_status"
            ).fetchall()
        }

        collections = _build_collection_tree(conn)

        return {
            "library": {
                "paper_count": total,
                "domain_counts": domains,
                "lifecycle_counts": lifecycle_counts,
                "ocr_counts": ocr_counts,
                "deep_reading_counts": deep_counts,
            },
            "collections": collections,
        }
    except Exception:
        return None
    finally:
        conn.close()
