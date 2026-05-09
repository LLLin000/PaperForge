"""Per-workspace paper-meta.json read/write.

Stores internal pipeline data (OCR jobs, health details, maturity breakdown)
that should NOT appear in formal note frontmatter.  Keeps formal notes lean
while preserving all state for tools and AI context.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

BEIJING = timezone(timedelta(hours=8))

META_FILENAME = "paper-meta.json"
SCHEMA_VERSION = 1


def write_paper_meta(
    workspace_dir: Path,
    entry: dict,
    migrated_from: dict | None = None,
    paperforge_version: str = "",
) -> Path:
    """Write or update paper-meta.json in the paper workspace.

    Idempotent: if the file already exists, updates mutable fields (OCR status,
    health, maturity, lifecycle, next_step) while preserving immutable fields
    (migrated_from, created_at).

    Returns the path to the written file.
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)
    meta_path = workspace_dir / META_FILENAME

    existing = {}
    if meta_path.exists():
        try:
            existing = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    now = datetime.now(BEIJING).isoformat()

    meta = {
        "schema_version": SCHEMA_VERSION,
        "paperforge_version": paperforge_version or existing.get("paperforge_version", ""),
        "zotero_key": entry.get("zotero_key", existing.get("zotero_key", "")),
        "created_at": existing.get("created_at", now),
        "updated_at": now,
        # OCR infrastructure (internal, not in frontmatter)
        "ocr_job_id": entry.get("ocr_job_id", existing.get("ocr_job_id", "")),
        "ocr_md_path": entry.get("ocr_md_path", existing.get("ocr_md_path", "")),
        "ocr_json_path": entry.get("ocr_json_path", existing.get("ocr_json_path", "")),
        "ocr_status": entry.get("ocr_status", existing.get("ocr_status", "pending")),
        # Derived state (full detail, summary already in frontmatter)
        "lifecycle": entry.get("lifecycle", existing.get("lifecycle", "indexed")),
        "next_step": entry.get("next_step", existing.get("next_step", "sync")),
        "health": entry.get("health", existing.get("health", {})),
        "maturity": entry.get("maturity", existing.get("maturity", {})),
        # Debug / internal fields
        "fulltext_path": entry.get("fulltext_path", existing.get("fulltext_path", "")),
        "ai_path": entry.get("ai_path", existing.get("ai_path", "")),
    }

    if migrated_from is not None:
        meta["migrated_from"] = migrated_from
    elif "migrated_from" in existing:
        meta["migrated_from"] = existing["migrated_from"]

    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta_path


def read_paper_meta(workspace_dir: Path) -> dict:
    """Read paper-meta.json from a workspace directory.

    Returns an empty dict if the file does not exist or is unreadable.
    """
    meta_path = workspace_dir / META_FILENAME
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
