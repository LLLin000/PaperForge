from __future__ import annotations

import argparse
import json
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.permanent import get_corrections_for_paper, get_reading_notes_for_paper


def _build_paper_context(vault, key: str) -> dict | None:
    """Build full context for a paper: metadata + reading notes + corrections."""

    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return None

    conn = get_connection(db_path, read_only=True)
    try:
        row = conn.execute(
            """SELECT zotero_key, citation_key, title, year, doi, journal,
                      first_author, domain, collection_path, has_pdf,
                      ocr_status, analyze, deep_reading_status, lifecycle,
                      next_step, pdf_path, note_path, fulltext_path, paper_root
               FROM papers WHERE zotero_key = ?""",
            (key,),
        ).fetchone()

        if not row:
            return None

        paper = dict(row)

        prior_notes = get_reading_notes_for_paper(vault, key)

        corrections = []
        corr_rows = conn.execute(
            """SELECT created_at, payload_json
               FROM paper_events
               WHERE paper_id = ? AND event_type = 'correction_note'
               ORDER BY created_at DESC""",
            (key,),
        ).fetchall()
        seen_ids: set[str] = set()
        for cr in corr_rows:
            payload = json.loads(cr["payload_json"])
            orig_id = payload.get("original_id", "")
            corrections.append({
                "created_at": cr["created_at"],
                "previous_note_id": orig_id,
                "correction": payload.get("correction", ""),
                "reason": payload.get("reason", ""),
            })
            if orig_id:
                seen_ids.add(orig_id)

        jsonl_corrections = get_corrections_for_paper(vault, key)
        for c in jsonl_corrections:
            cid = c.get("original_id", "")
            if cid and cid in seen_ids:
                continue
            corrections.append({
                "created_at": c.get("created_at", ""),
                "previous_note_id": cid,
                "correction": c.get("correction", ""),
                "reason": c.get("reason", ""),
            })
            if cid:
                seen_ids.add(cid)

        recheck_targets = []
        for n in prior_notes:
            if not n.get("verified", False):
                recheck_targets.append(
                    f"{n.get('section', 'unknown')}: {n.get('excerpt', '')[:80]}..."
                )

        return {
            "warning": "Prior reading notes are not verified facts. Re-check source before reuse.",
            "paper": paper,
            "prior_notes": prior_notes,
            "corrections": corrections,
            "recheck_targets": recheck_targets,
        }
    finally:
        conn.close()


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    key = args.key

    context = _build_paper_context(vault, key)

    if context is None:
        result = PFResult(
            ok=False,
            command="paper-context",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.PATH_NOT_FOUND,
                message=f"No paper found for key: {key}",
            ),
        )
    else:
        result = PFResult(
            ok=True,
            command="paper-context",
            version=PF_VERSION,
            data=context,
        )

    if args.json:
        print(result.to_json())
    else:
        if result.ok:
            p = result.data["paper"]
            print(f"Paper: {p.get('title', key)}")
            print(f"  Key: {p.get('zotero_key', '')}")
            print(f"  OCR: {p.get('ocr_status', 'unknown')}")
            print(f"  Lifecycle: {p.get('lifecycle', '')}")
            notes = result.data.get("prior_notes", [])
            print(f"  Reading notes: {len(notes)}")
            print(f"  Corrections: {len(result.data.get('corrections', []))}")
            if result.data.get("recheck_targets"):
                print(f"  Recheck targets: {len(result.data['recheck_targets'])}")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)

    return 0 if result.ok else 1
