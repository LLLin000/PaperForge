"""OCR maintenance row model — single source of truth for the maintenance tab.

Every row is assembled here. The plugin/CLI only consume this model.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path

from paperforge.core.io import read_json


@dataclass
class OCRMaintenanceRow:
    key: str
    title: str
    title_full: str
    status: str
    health: str
    version: str
    finished_at: str
    rebuild_finished_at: str
    pages: int
    blocks: int
    figures: int
    tables: int
    model: str
    degraded_reasons: list[str] = field(default_factory=list)
    error_summary: str = ""
    error_stage: str = ""
    can_redo: bool = False
    can_rebuild: bool = False
    recommended_action: str = ""

    def to_dict(self) -> dict:
        return {
            "key": _safe_str(self.key),
            "title": _safe_str(self.title),
            "title_full": _safe_str(self.title_full),
            "status": _safe_str(self.status),
            "health": _safe_str(self.health),
            "version": _safe_str(self.version),
            "finished_at": _safe_str(self.finished_at),
            "rebuild_finished_at": _safe_str(self.rebuild_finished_at),
            "pages": int(self.pages),
            "blocks": int(self.blocks),
            "figures": int(self.figures),
            "tables": int(self.tables),
            "model": _safe_str(self.model),
            "degraded_reasons": [_safe_str(r) for r in self.degraded_reasons],
            "error_summary": _safe_str(self.error_summary),
            "error_stage": _safe_str(self.error_stage),
            "can_redo": bool(self.can_redo),
            "can_rebuild": bool(self.can_rebuild),
            "recommended_action": _safe_str(self.recommended_action),
        }


def _fmt_iso(iso_str: str | None) -> str:
    if not iso_str:
        return "-"
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime("%m-%d %H:%M")
    except (ValueError, TypeError):
        return "-"


def _safe_str(val) -> str:
    if val is None:
        return ""
    try:
        s = str(val)
        s.encode("utf-8", errors="replace")
        return s
    except Exception:
        return repr(val)


def _short_title(title, max_len: int = 40) -> str:
    t = _safe_str(title).strip()
    if not t:
        return "-"
    t = t.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    return t[:max_len] + ("..." if len(t) > max_len else "")


def _detect_version(meta: dict, has_structured: bool, has_raw: bool) -> str:
    if meta.get("raw_version") or meta.get("derived_version"):
        return "v2"
    if meta.get("is_backfilled"):
        return "backfill"
    if has_raw and has_structured:
        return "v2"
    if meta.get("ocr_status") == "done":
        return "v1"
    return "-"


def _error_summary(meta: dict) -> str:
    error_type = str(meta.get("error_type", "") or "")
    error_msg = str(meta.get("error", "") or "")
    last_error = str(meta.get("last_error", "") or "")
    msg = last_error or error_msg
    if error_type and msg:
        return f"{error_type}: {msg[:80]}"
    if msg:
        return msg[:80]
    return ""


def _error_stage(meta: dict) -> str:
    return str(meta.get("error_stage", "") or "")


def _can_rebuild(meta: dict, has_raw: bool, has_source_meta: bool) -> bool:
    status = str(meta.get("ocr_status", "") or "").lower()
    if status in ("running", "pending", "nopdf", "blocked"):
        return False
    if status == "failed":
        stage = _error_stage(meta)
        if stage in ("submit", "poll", "upload", "ocr_parse"):
            return False
    return has_raw and has_source_meta


def _can_redo(meta: dict) -> bool:
    status = str(meta.get("ocr_status", "") or "").lower()
    if status in ("running", "blocked", "nopdf"):
        return False
    return True


def _recommended_action(meta: dict, has_raw: bool, has_source_meta: bool) -> str:
    """Decide what the UI should recommend for this paper."""
    version = _detect_version(meta, has_raw, has_source_meta)
    status = str(meta.get("ocr_status", "") or "").lower()

    if status == "failed":
        stage = _error_stage(meta)
        if stage in ("submit", "poll", "upload", "ocr_parse"):
            return "redo"
        elif _can_rebuild(meta, has_raw, has_source_meta):
            return "rebuild"
        return "redo"

    if version == "v1":
        return "redo"

    if meta.get("derived_stale") and _can_rebuild(meta, has_raw, has_source_meta):
        return "rebuild"

    if status == "done_degraded" and _can_rebuild(meta, has_raw, has_source_meta):
        return "rebuild"

    return ""


def collect_maintenance_rows(vault: Path) -> list[OCRMaintenanceRow]:
    """Scan all OCR paper directories and return normalized maintenance rows."""
    from paperforge.worker._utils import pipeline_paths
    from paperforge.worker.ocr_artifacts import artifact_paths_for_root

    paths = pipeline_paths(vault)
    ocr_root = paths.get("ocr")
    if not ocr_root or not ocr_root.exists():
        return []

    rows: list[OCRMaintenanceRow] = []
    for paper_dir in sorted(ocr_root.iterdir()):
        if not paper_dir.is_dir():
            continue
        key = paper_dir.name
        artifacts = artifact_paths_for_root(ocr_root, key)
        meta_path = artifacts.meta_json
        health_path = artifacts.paper_root / "health" / "ocr_health.json"

        meta: dict = {}
        if meta_path.exists():
            meta = read_json(meta_path)

        health: dict = {}
        if health_path.exists():
            health = read_json(health_path)

        has_raw = artifacts.blocks_raw.exists()
        has_source_meta = artifacts.source_metadata.exists()
        has_structured = artifacts.blocks_structured.exists()

        status = str(meta.get("ocr_status", "") or "").lower() or "-"
        health_overall = str(health.get("overall", "") or "")
        version = _detect_version(meta, has_structured, has_raw)
        model = str(
            meta.get("raw_version", {}).get("ocr_model", "")
            or meta.get("ocr_provider", "")
            or ""
        )
        degraded_reasons = (
            health.get("degraded_reasons", [])
            or [meta.get("degraded_reason", "")]
            if meta.get("degraded_reason")
            else []
        )
        degraded_reasons = [r for r in degraded_reasons if r]

        rebuild_ts = meta.get("rebuild_finished_at") or meta.get("ocr_health_rebuild_time") or ""
        row = OCRMaintenanceRow(
            key=key,
            title=_short_title(meta.get("title") or key),
            title_full=_safe_str(meta.get("title") or key),
            status=status if status != "-" else "pending",
            health=health_overall or "-",
            version=version,
            finished_at=_fmt_iso(meta.get("ocr_finished_at")),
            rebuild_finished_at=_fmt_iso(rebuild_ts),
            pages=int(meta.get("page_count") or health.get("page_count") or 0),
            blocks=int(health.get("blocks_count") or 0),
            figures=int(health.get("figure_caption_count") or 0),
            tables=int(health.get("table_caption_count") or 0),
            model=model or "-",
            degraded_reasons=degraded_reasons,
            error_summary=_error_summary(meta),
            error_stage=_error_stage(meta),
            can_redo=_can_redo(meta),
            can_rebuild=_can_rebuild(meta, has_raw, has_source_meta),
            recommended_action=_recommended_action(meta, has_raw, has_source_meta),
        )
        rows.append(row)

    return rows
