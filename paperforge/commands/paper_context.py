from __future__ import annotations

import argparse
import json
import sys

import sqlite3
from pathlib import Path
from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.permanent import load_record_authority, order_records, project_record, record_time
from paperforge.memory.query import lookup_paper

def _build_compact_tree(vault: Path, zotero_key: str, conn: sqlite3.Connection) -> dict | None:
    """Build compact document tree from OCR structure-tree.json.

    Pure projection of existing StructureTree fields — no block-level recalculation.
    Returns None when paper has no OCR structure.
    """
    from paperforge.config import paperforge_paths

    tree_path = paperforge_paths(vault)["ocr"] / zotero_key / "index" / "structure-tree.json"
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

def _build_paper_context(vault: Path, key: str, structure: bool = False) -> dict | None:

    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return None

    from paperforge.memory.db import open_live_reader
    reader = open_live_reader(vault, db_path)
    conn = reader.__enter__()
    try:
        matches = lookup_paper(conn, key)
        if not matches or len(matches) != 1:
            return None
        resolved_key = matches[0]["zotero_key"]
        row = conn.execute(
            """SELECT zotero_key, citation_key, title, year, doi, journal,
                      first_author, domain, collection_path, has_pdf,
                      ocr_status, analyze, deep_reading_status, lifecycle,
                      next_step, pdf_path, note_path, main_note_path, fulltext_path, paper_root
               FROM papers WHERE zotero_key = ?""",
            (resolved_key,),
        ).fetchone()

        if not row:
            return None

        paper = dict(row)
        from paperforge.memory.paper_state import resolve_effective_note_relpath

        effective_note = resolve_effective_note_relpath(vault, paper)
        if effective_note:
            paper["note_path"] = effective_note

        notes, related = load_record_authority(vault)
        prior_notes = [project_record(vault, n, related.get(n["id"], []))
                       for n in notes if n["paper_id"] == resolved_key]
        order_records(prior_notes)

        corrections = [
            {**c, "previous_note_id": c.get("original_id", "")} for c in
            sorted((c for paper_notes in [related.get(n["id"], []) for n in prior_notes]
                    for c in paper_notes),
                   key=lambda c: (record_time(c), c.get("id", "")), reverse=True)
        ]

        recheck_targets = [
            f"{n.get('section', 'unknown')}: {n.get('excerpt', '')[:80]}..."
            for n in prior_notes if n.get("provenance", {}).get("status") not in ("matched", "confirmed")
        ]

        try:
            from paperforge.config import paperforge_paths
            from paperforge.core.io import read_json
            from paperforge.worker.ocr_evidence import build_paper_evidence_summary

            ocr_root = paperforge_paths(vault)["ocr"]
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
            "living_memory": _load_living_memory(vault, resolved_key, conn),
            "prior_notes": prior_notes,
            "corrections": corrections,
            "recheck_targets": recheck_targets,
            "user_annotations": _load_user_annotations(vault, resolved_key, conn),
        }
        if structure:
            result["structure"] = _build_compact_tree(vault, resolved_key, conn)
        return result
    finally:
        conn.close()
        reader.__exit__(None, None, None)


def _project_annotation(ann: dict) -> dict:
    """Project a sidecar or DB annotation record into a compact agent-facing dict."""
    return {
        "ann_id": str(ann.get("ann_id") or ""),
        "page": ann.get("page"),
        "kind": str(ann.get("kind") or "highlight"),
        "intent": str(ann.get("intent") or "general"),
        "color": str(ann.get("color") or "yellow"),
        "section_path": str(ann.get("section_path") or ""),
        "figure_id": str(ann.get("figure_id") or ""),
        "exact_text": str(ann.get("exact_text") or ""),
        "comment": str(ann.get("comment") or ""),
        "embed_wikilink": str(ann.get("embed_wikilink") or ""),
        "provenance_status": str(ann.get("provenance_status") or "verified"),
    }


def _load_living_memory(vault: Path, zotero_key: str, conn: sqlite3.Connection) -> dict:
    """Load the faceted Living Paper Memory Card for *zotero_key*."""
    try:
        from paperforge.services.memory_card_service import get_memory_card

        card = get_memory_card(vault, zotero_key)
        if card.get("facets"):
            return card
    except Exception:
        pass

    facets: list[dict] = []
    try:
        from paperforge.services.memory_card_service import facet_label

        has_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='paper_memory_cards'"
        ).fetchone()
        if has_table is not None:
            for r in conn.execute(
                "SELECT facet, content, revision, updated_at "
                "FROM paper_memory_cards WHERE zotero_key = ?",
                (zotero_key,),
            ).fetchall():
                slug = str(r["facet"])
                facets.append(
                    {
                        "facet": slug,
                        "label": facet_label(slug),
                        "content": str(r["content"] or ""),
                        "revision": int(r["revision"] or 1),
                        "updated_at": str(r["updated_at"] or ""),
                    }
                )
    except Exception:
        facets = []
    latest = max((f["updated_at"] for f in facets if f.get("updated_at")), default="")
    return {
        "paper_id": zotero_key,
        "updated_at": latest,
        "facet_count": len(facets),
        "facets": facets,
    }


def _load_user_annotations(vault: Path, zotero_key: str, conn: sqlite3.Connection) -> dict:
    """Load non-destructive user PDF annotations from sidecar JSONL with SQLite fallback."""
    rows: list[dict] = []
    try:
        from paperforge.services.annotations_service import list_annotations

        rows = list_annotations(vault, zotero_key)
    except Exception:
        rows = []

    if not rows:
        try:
            has_table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='paper_annotations'"
            ).fetchone()
            if has_table is not None:
                db_rows = conn.execute(
                    "SELECT ann_id, kind, color, intent, page, exact_text, comment, "
                    "section_path, figure_id, crop_asset_rel, embed_wikilink, pdf_sha256 "
                    "FROM paper_annotations WHERE paper_id = ? "
                    "ORDER BY page ASC, created_at ASC",
                    (zotero_key,),
                ).fetchall()
                rows = [
                    {
                        **dict(r),
                        "provenance_status": "verified" if r["pdf_sha256"] else "unknown",
                    }
                    for r in db_rows
                ]
        except Exception:
            rows = []

    projected = [_project_annotation(r) for r in rows]
    return {
        "total": len(projected),
        "questions": [a for a in projected if a.get("intent") == "question"],
        "highlights": [a for a in projected if a.get("intent") != "question"],
    }


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    key = args.key

    try:
        context = _build_paper_context(vault, key, structure=getattr(args, "structure", False))
    except (ValueError, OSError, UnicodeError) as exc:
        result = PFResult(
            ok=False, command="paper-context", version=PF_VERSION,
            error=PFError(code=ErrorCode.VALIDATION_ERROR, message=str(exc)),
        )
        print(result.to_json() if args.json else f"Error: {exc}", file=sys.stderr)
        return 1

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
            lm = result.data.get("living_memory") or {}
            if lm.get("facet_count", 0) > 0:
                print(f"  Living memory: {lm['facet_count']} facets (updated {lm.get('updated_at', '')})")
            ua = result.data.get("user_annotations") or {}
            if ua.get("total", 0) > 0:
                print(f"  Annotations: {ua['total']} ({len(ua.get('questions', []))} questions)")
            if result.data.get("structure"):
                s = result.data["structure"]
                print(f"  Structure: {len(s.get('nodes', []))} nodes (v={s.get('version', '')[:12]})")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
    return 0 if result.ok else 1
