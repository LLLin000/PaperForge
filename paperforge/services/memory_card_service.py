"""Service for faceted evolving Living Paper Memory Cards & Base table snapshots."""
from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paperforge.lineage import workspace_dir_for_key
from paperforge.memory.db import WriterLock, get_connection, get_memory_db_path, open_live_reader
from paperforge.memory.schema import ensure_schema
from paperforge.services.state_signal import bump_state_seq, read_state_seq
from paperforge.worker.asset_index import read_index

FACET_LABELS: OrderedDict[str, str] = OrderedDict(
    [
        ("idea_logic", "研究思路与逻辑链"),
        ("methods_params", "实验技术与关键参数"),
        ("research_craft", "研究技巧与巧思"),
        ("critique_limits", "硬伤、边界与存疑"),
        ("my_connection", "课题迁移与灵感"),
    ]
)

CUSTOM_FACET_RE = re.compile(r"^[a-z0-9_]{2,32}$")
MAX_FACET_CHARS = 4000


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_facet_slug(raw: str) -> str:
    slug = str(raw or "").strip().lower().replace("-", "_")
    if slug in FACET_LABELS or CUSTOM_FACET_RE.match(slug):
        return slug
    raise ValueError(
        f"Invalid facet {raw!r}; expected one of {list(FACET_LABELS)} or ^[a-z0-9_]{{2,32}}$"
    )


def facet_label(slug: str) -> str:
    return FACET_LABELS.get(slug, slug)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".mc-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _resolve_workspace_optional(vault: Path, paper_key: str) -> tuple[dict[str, Any], Path | None]:
    vault_root = Path(vault).expanduser().resolve()
    idx = read_index(vault_root)
    items = idx.get("items", []) if isinstance(idx, dict) else (idx or [])
    matched = [it for it in items if isinstance(it, dict) and it.get("zotero_key") == paper_key]
    item = matched[0] if matched else {}
    if item.get("paper_root"):
        return item, (vault_root / str(item["paper_root"]).rstrip("/")).resolve()
    return item, workspace_dir_for_key(vault_root, paper_key)


def _card_file_for_workspace(ws_dir: Path) -> Path:
    return ws_dir / "ai" / "memory-card.json"


def _read_card_file(card_path: Path) -> dict[str, dict[str, Any]]:
    if not card_path.exists():
        return {}
    try:
        data = json.loads(card_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    facets_raw = data.get("facets", {})
    if isinstance(facets_raw, list):
        return {
            str(entry["facet"]): dict(entry)
            for entry in facets_raw
            if isinstance(entry, dict) and entry.get("facet")
        }
    if isinstance(facets_raw, dict):
        return {
            str(k): dict(v)
            for k, v in facets_raw.items()
            if isinstance(v, dict)
        }
    return {}


def _sort_facets(raw_facets: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    known_order = list(FACET_LABELS.keys())
    ordered_keys = [k for k in known_order if k in raw_facets]
    extra_keys = sorted(k for k in raw_facets if k not in FACET_LABELS)
    out: list[dict[str, Any]] = []
    for k in ordered_keys + extra_keys:
        entry = raw_facets[k]
        content = str(entry.get("content") or "").strip()
        if not content:
            continue
        out.append(
            {
                "facet": k,
                "label": str(entry.get("label") or facet_label(k)),
                "content": content,
                "revision": int(entry.get("revision") or 1),
                "updated_at": str(entry.get("updated_at") or ""),
            }
        )
    return out


def get_memory_card(vault: Path, paper_key: str) -> dict[str, Any]:
    """Return the active faceted Living Paper Memory Card for *paper_key*."""
    vault_root = Path(vault).expanduser().resolve()
    _item, ws_dir = _resolve_workspace_optional(vault_root, paper_key)
    raw_facets: dict[str, dict[str, Any]] = {}
    if ws_dir is not None:
        raw_facets = _read_card_file(_card_file_for_workspace(ws_dir))

    if not raw_facets:
        with contextlib.suppress(Exception):
            db_path = get_memory_db_path(vault_root)
            if db_path.exists():
                with open_live_reader(vault_root, db_path) as conn:
                    rows = conn.execute(
                        "SELECT facet, content, revision, updated_at "
                        "FROM paper_memory_cards WHERE zotero_key = ?",
                        (paper_key,),
                    ).fetchall()
                    for r in rows:
                        raw_facets[str(r["facet"])] = {
                            "facet": str(r["facet"]),
                            "label": facet_label(str(r["facet"])),
                            "content": str(r["content"] or ""),
                            "revision": int(r["revision"] or 1),
                            "updated_at": str(r["updated_at"] or ""),
                        }

    facets = _sort_facets(raw_facets)
    latest = max((f["updated_at"] for f in facets if f.get("updated_at")), default="")
    return {
        "paper_id": paper_key,
        "updated_at": latest,
        "facet_count": len(facets),
        "facets": facets,
    }


def refine_memory_facet(
    vault: Path,
    paper_key: str,
    *,
    facet: str,
    content: str,
) -> dict[str, Any]:
    """Upsert & refine one cognitive facet of a paper's Living Memory Card."""
    slug = normalize_facet_slug(facet)
    cleaned = str(content or "").strip()
    if not cleaned:
        raise ValueError("content must be non-empty")
    if len(cleaned) > MAX_FACET_CHARS:
        raise ValueError(f"content exceeds {MAX_FACET_CHARS} chars; keep memory facets concise")

    vault_root = Path(vault).expanduser().resolve()
    item, ws_dir = _resolve_workspace_optional(vault_root, paper_key)
    now = _utcnow_iso()

    # Check DB presence too in case index/workspace isn't populated for paper_key
    in_db = False
    db_path: Path | None = None
    with contextlib.suppress(FileNotFoundError):
        cand = get_memory_db_path(vault_root)
        if cand.exists():
            db_path = cand
            with open_live_reader(vault_root, cand) as conn:
                row = conn.execute(
                    "SELECT 1 FROM papers WHERE zotero_key = ?",
                    (paper_key,),
                ).fetchone()
                in_db = row is not None

    if ws_dir is None and not item and not in_db:
        raise ValueError(f"Unknown paper key: {paper_key}")

    current_map: dict[str, dict[str, Any]] = {}
    if ws_dir is not None:
        current_map = _read_card_file(_card_file_for_workspace(ws_dir))
    elif in_db and db_path is not None:
        with open_live_reader(vault_root, db_path) as conn:
            for r in conn.execute(
                "SELECT facet, content, revision, updated_at FROM paper_memory_cards WHERE zotero_key = ?",
                (paper_key,),
            ).fetchall():
                current_map[str(r["facet"])] = dict(r)

    prev = current_map.get(slug)
    revision = int(prev.get("revision") or 0) + 1 if prev else 1
    record = {
        "facet": slug,
        "label": facet_label(slug),
        "content": cleaned,
        "revision": revision,
        "updated_at": now,
    }
    current_map[slug] = record

    if ws_dir is not None:
        card_payload = {
            "paper_id": paper_key,
            "updated_at": now,
            "facets": {f["facet"]: f for f in _sort_facets(current_map)},
        }
        _atomic_write_json(_card_file_for_workspace(ws_dir), card_payload)

    if db_path is not None and db_path.exists():
        with WriterLock(vault_root):
            conn = get_connection(db_path)
            try:
                ensure_schema(conn)
                paper_row = conn.execute(
                    "SELECT 1 FROM papers WHERE zotero_key = ?",
                    (paper_key,),
                ).fetchone()
                if paper_row is not None:
                    conn.execute(
                        """INSERT OR REPLACE INTO paper_memory_cards
                           (zotero_key, facet, content, revision, updated_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (paper_key, slug, cleaned, revision, now),
                    )
                    conn.execute(
                        """INSERT INTO paper_memory_history
                           (zotero_key, facet, content, revision, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (paper_key, slug, cleaned, revision, now),
                    )
                    conn.commit()
            finally:
                conn.close()

    with contextlib.suppress(Exception):
        bump_state_seq(vault_root, reason="memory_card.refine", changed_keys=[paper_key])

    return {
        "paper_id": paper_key,
        "updated": record,
        "card": get_memory_card(vault_root, paper_key),
    }


def get_memory_history(vault: Path, paper_key: str, *, facet: str = "") -> dict[str, Any]:
    """Return chronological revision snapshots from ``paper_memory_history``."""
    vault_root = Path(vault).expanduser().resolve()
    slug = normalize_facet_slug(facet) if facet else ""
    history: list[dict[str, Any]] = []
    with contextlib.suppress(FileNotFoundError):
        db_path = get_memory_db_path(vault_root)
        if db_path.exists():
            with open_live_reader(vault_root, db_path) as conn:
                if slug:
                    rows = conn.execute(
                        "SELECT facet, content, revision, created_at FROM paper_memory_history "
                        "WHERE zotero_key = ? AND facet = ? ORDER BY id DESC LIMIT 50",
                        (paper_key, slug),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT facet, content, revision, created_at FROM paper_memory_history "
                        "WHERE zotero_key = ? ORDER BY id DESC LIMIT 50",
                        (paper_key,),
                    ).fetchall()
                for r in rows:
                    history.append(
                        {
                            "facet": str(r["facet"]),
                            "label": facet_label(str(r["facet"])),
                            "content": str(r["content"]),
                            "revision": int(r["revision"]),
                            "created_at": str(r["created_at"]),
                        }
                    )
    return {"paper_id": paper_key, "facet": slug, "history": history}


def clear_memory_facet(vault: Path, paper_key: str, *, facet: str = "") -> dict[str, Any]:
    """Remove a single facet or all facets for *paper_key*."""
    vault_root = Path(vault).expanduser().resolve()
    slug = normalize_facet_slug(facet) if facet else ""
    _item, ws_dir = _resolve_workspace_optional(vault_root, paper_key)
    removed = 0

    if ws_dir is not None:
        card_path = _card_file_for_workspace(ws_dir)
        current_map = _read_card_file(card_path)
        if slug:
            if slug in current_map:
                del current_map[slug]
                removed += 1
        else:
            removed += len(current_map)
            current_map = {}
        _atomic_write_json(
            card_path,
            {
                "paper_id": paper_key,
                "updated_at": _utcnow_iso(),
                "facets": {f["facet"]: f for f in _sort_facets(current_map)},
            },
        )

    with contextlib.suppress(FileNotFoundError):
        db_path = get_memory_db_path(vault_root)
        if db_path.exists():
            with WriterLock(vault_root):
                conn = get_connection(db_path)
                try:
                    ensure_schema(conn)
                    if slug:
                        cur = conn.execute(
                            "DELETE FROM paper_memory_cards WHERE zotero_key = ? AND facet = ?",
                            (paper_key, slug),
                        )
                    else:
                        cur = conn.execute(
                            "DELETE FROM paper_memory_cards WHERE zotero_key = ?",
                            (paper_key,),
                        )
                    removed = max(removed, cur.rowcount)
                    conn.commit()
                finally:
                    conn.close()

    with contextlib.suppress(Exception):
        bump_state_seq(vault_root, reason="memory_card.clear", changed_keys=[paper_key])

    return {"paper_id": paper_key, "facet": slug, "removed": removed}


def get_base_table_snapshot(vault: Path) -> dict[str, Any]:
    """Return lightweight read-only status/cognitive counts keyed by ``zotero_key``.

    Designed for Obsidian ``PaperForgeBasesView`` (`paperforge-table`): keeps all
    mutable workflow status and cognitive summaries out of Markdown YAML.
    """
    vault_root = Path(vault).expanduser().resolve()
    seq_info = read_state_seq(vault_root)
    idx = read_index(vault_root)
    items = idx.get("items", []) if isinstance(idx, dict) else (idx or [])

    ann_counts: dict[str, tuple[int, int]] = {}
    mem_counts: dict[str, tuple[int, str]] = {}
    db_papers: dict[str, dict[str, Any]] = {}

    with contextlib.suppress(Exception):
        db_path = get_memory_db_path(vault_root)
        if db_path.exists():
            with open_live_reader(vault_root, db_path) as conn:
                for r in conn.execute(
                    "SELECT zotero_key, ocr_status, deep_reading_status FROM papers"
                ).fetchall():
                    db_papers[str(r["zotero_key"])] = {
                        "ocr_status": str(r["ocr_status"] or "pending"),
                        "deep_reading_status": str(r["deep_reading_status"] or "pending"),
                    }
                has_ann = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='paper_annotations'"
                ).fetchone()
                if has_ann is not None:
                    cols = {
                        str(c["name"])
                        for c in conn.execute("PRAGMA table_info(paper_annotations)").fetchall()
                    }
                    if "author" in cols:
                        sql = (
                            "SELECT paper_id, "
                            "SUM(CASE WHEN COALESCE(author, 'user') = 'agent' THEN 0 ELSE 1 END) AS u_cnt, "
                            "SUM(CASE WHEN COALESCE(author, 'user') = 'agent' THEN 1 ELSE 0 END) AS a_cnt "
                            "FROM paper_annotations GROUP BY paper_id"
                        )
                    else:
                        sql = "SELECT paper_id, COUNT(*) AS u_cnt, 0 AS a_cnt FROM paper_annotations GROUP BY paper_id"
                    for r in conn.execute(sql).fetchall():
                        ann_counts[str(r["paper_id"])] = (int(r["u_cnt"] or 0), int(r["a_cnt"] or 0))
                has_mem = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='paper_memory_cards'"
                ).fetchone()
                if has_mem is not None:
                    for r in conn.execute(
                        "SELECT zotero_key, COUNT(*) AS f_cnt, MAX(updated_at) AS last_upd "
                        "FROM paper_memory_cards GROUP BY zotero_key"
                    ).fetchall():
                        mem_counts[str(r["zotero_key"])] = (int(r["f_cnt"] or 0), str(r["last_upd"] or ""))

    rows: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("zotero_key") or "").strip()
        if not key:
            continue
        db_p = db_papers.get(key, {})
        ocr_status = str(item.get("ocr_status") or db_p.get("ocr_status") or "pending")
        dr_status = str(item.get("deep_reading_status") or db_p.get("deep_reading_status") or "pending")
        health = item.get("health") if isinstance(item.get("health"), dict) else {}
        ocr_health = str(health.get("ocr_health") or "")
        u_cnt, a_cnt = ann_counts.get(key, (0, 0))
        m_cnt, m_upd = mem_counts.get(key, (0, ""))

        # Workspace file fallback when DB hasn't been rebuilt yet
        if key not in mem_counts and item.get("paper_root"):
            ws_dir = vault_root / str(item["paper_root"]).rstrip("/")
            c_map = _read_card_file(_card_file_for_workspace(ws_dir))
            if c_map:
                sorted_f = _sort_facets(c_map)
                m_cnt = len(sorted_f)
                m_upd = max((f["updated_at"] for f in sorted_f if f.get("updated_at")), default="")

        rows[key] = {
            "zotero_key": key,
            "title": str(item.get("title") or key),
            "first_author": str(item.get("first_author") or ""),
            "year": str(item.get("year") or ""),
            "journal": str(item.get("journal") or ""),
            "impact_factor": str(item.get("impact_factor") or ""),
            "domain": str(item.get("domain") or ""),
            "has_pdf": bool(item.get("has_pdf")),
            "do_ocr": bool(item.get("do_ocr")),
            "analyze": bool(item.get("analyze")),
            "ocr_status": ocr_status,
            "deep_reading_status": dr_status,
            "main_note_path": str(item.get("main_note_path") or item.get("note_path") or ""),
            "user_ann_count": u_cnt,
            "agent_ann_count": a_cnt,
            "memory_facet_count": m_cnt,
            "memory_updated_at": m_upd,
            "needs_diagnostic": ocr_status in ("failed", "done_incomplete", "unknown")
            or (ocr_status == "done" and ocr_health not in ("", "healthy")),
        }

    return {
        "seq": seq_info["seq"],
        "updated_at": seq_info["updated_at"],
        "rows": rows,
    }
