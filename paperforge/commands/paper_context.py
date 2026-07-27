from __future__ import annotations

import argparse
import json
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.permanent import get_corrections_for_paper, get_reading_notes_for_paper
from paperforge.memory.query import lookup_paper

def _build_compact_tree(vault, zotero_key: str, conn) -> dict | None:
    """Build compact document tree from OCR structure-tree.json.

    Pure projection of existing StructureTree fields — no block-level recalculation.
    Returns None when paper has no OCR structure.
    """
    tree_path = vault / "System" / "PaperForge" / "ocr" / zotero_key / "index" / "structure-tree.json"
    if not tree_path.exists():
        return None

    import json as _json
    tree = _json.loads(tree_path.read_text(encoding="utf-8"))
    raw_nodes = tree.get("nodes", [])
    if not raw_nodes:
        return None

    compact: list[dict] = []

    def _dfs(nodes: list[dict], parent_id: str | None, path: list[str], depth: int) -> None:
        for node in nodes:
            nid = node.get("node_id", "")
            title = node.get("title", "")
            cur_path = path + [title] if title else path
            compact.append({
                "node_id": nid,
                "parent_id": parent_id,
                "title": title,
                "path": cur_path,
                "depth": depth,
                "own_block_count": len(node.get("own_block_ids", [])),
                "subtree_block_count": len(node.get("subtree_block_ids", [])),
                "child_count": len(node.get("children", [])),
                "page_span": node.get("page_span", []),
                "document_order": len(compact) + 1,
            })
            _dfs(node.get("children", []), nid, cur_path, depth + 1)

    _dfs(raw_nodes, None, [], 1)

    # Read structure_version from DB manifest
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (f"manifest:{zotero_key}",)).fetchone()
    version = ""
    if row:
        try:
            manifest = _json.loads(row[0])
            version = str(manifest.get("ocr_result_hash", ""))
        except (TypeError, ValueError, KeyError):
            pass

    return {"version": version, "nodes": compact}
def _build_paper_context(vault, key: str, structure: bool = False) -> dict | None:
    """Build full context for a paper: metadata + reading notes + corrections."""

    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return None

    conn = get_connection(db_path, read_only=True)
    try:
        matches = lookup_paper(conn, key)
        if not matches or len(matches) != 1:
            return None
        resolved_key = matches[0]["zotero_key"]
        row = conn.execute(
            """SELECT zotero_key, citation_key, title, year, doi, journal,
                      first_author, domain, collection_path, has_pdf,
                      ocr_status, analyze, deep_reading_status, lifecycle,
                      next_step, pdf_path, note_path, fulltext_path, paper_root
               FROM papers WHERE zotero_key = ?""",
            (resolved_key,),
        ).fetchone()

        if not row:
            return None

        paper = dict(row)

        prior_notes = get_reading_notes_for_paper(vault, resolved_key)

        corrections = []
        corr_rows = conn.execute(
            """SELECT created_at, payload_json
               FROM paper_events
               WHERE paper_id = ? AND event_type = 'correction_note'
               ORDER BY created_at DESC""",
            (resolved_key,),
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

        jsonl_corrections = get_corrections_for_paper(vault, resolved_key)
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

        try:
            from paperforge.core.io import read_json
            from paperforge.worker._utils import pipeline_paths
            from paperforge.worker.ocr_evidence import build_paper_evidence_summary

            ocr_root = pipeline_paths(vault)["ocr"]
            paper_ocr_dir = ocr_root / paper.get("zotero_key", key)
            role_index_path = paper_ocr_dir / "index" / "role-index.json"
            if role_index_path.exists():
                role_indexes = read_json(role_index_path)
                evidence = build_paper_evidence_summary(
                    paper_id=paper.get("zotero_key", key),
                    role_indexes=role_indexes,
                )
                paper["ocr_evidence"] = evidence
        except Exception:
            pass

        # Add fulltext availability metadata
        try:
            bc = conn.execute(
                "SELECT COUNT(*) FROM body_units WHERE paper_id=? AND indexable=1",
                (resolved_key,),
            ).fetchone()[0]
            paper["body_units_count"] = bc
            paper["fulltext_available"] = bc > 0
        except Exception:
            paper["body_units_count"] = 0
            paper["fulltext_available"] = False

        result = {
            "warning": "Prior reading notes are not verified facts. Re-check source before reuse.",
            "paper": paper,
            "prior_notes": prior_notes,
            "corrections": corrections,
            "recheck_targets": recheck_targets,
        }
        if structure:
            result["structure"] = _build_compact_tree(vault, resolved_key, conn)
        return result
    finally:
        conn.close()


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    key = args.key

    context = _build_paper_context(vault, key, structure=getattr(args, "structure", False))

    if context is None:
        result = PFResult(
            ok=False,
            command="paper-context",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.PATH_NOT_FOUND,
                message=f"No paper found for key: {key}",
            ),
            data={"absence_proof": "multi-path lookup exhausted"},
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
            print(f"  Fulltext: {p.get('fulltext_available', False)} ({p.get('body_units_count', 0)} units)")
            notes_n = len(result.data.get("prior_notes", []))
            print(f"  Reading notes: {notes_n}")
            print(f"  Corrections: {len(result.data.get('corrections', []))}")
            if result.data.get("recheck_targets"):
                print(f"  Recheck targets: {len(result.data['recheck_targets'])}")
            if result.data.get("structure"):
                s = result.data["structure"]
                print(f"  Structure: {len(s.get('nodes', []))} nodes (v={s.get('version', '')[:12]})")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
    return 0 if result.ok else 1
