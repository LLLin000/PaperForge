"""OCR maintenance row model — single source of truth for the maintenance tab.

Every row is assembled here. The plugin/CLI only consume this model.
"""

from __future__ import annotations

import datetime
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from paperforge.core.io import read_json
from paperforge.worker.ocr_fulltext_state import get_fulltext_drift_state


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
    display_action: str = "none"
    display_label: str = "已完成"
    display_label_key: str = ""
    display_reason: str = ""
    display_reason_key: str = ""
    display_group: str = "hidden"
    display_severity: str = "normal"
    visible_in_maintenance: bool = False
    fulltext_drift_state: str = "UNKNOWN"
    fulltext_drift_reason: str = ""
    show_in_base: bool = True
    def __post_init__(self) -> None:
        df = self.compute_display_fields(
            status=self.status, health_overall=self.health,
            version=self.version, can_redo=self.can_redo,
            can_rebuild=self.can_rebuild, error_stage=self.error_stage,
            error_summary=self.error_summary,
            degraded_reasons=self.degraded_reasons,
        )
        for k, v in df.items():
            setattr(self, k, v)

    @staticmethod
    def compute_display_fields(
        status: str,
        health_overall: str,
        version: str,
        can_redo: bool,
        can_rebuild: bool,
        error_stage: str = "",
        error_summary: str = "",
        degraded_reasons: list[str] | None = None,
    ) -> dict:
        """Map raw OCR state to display fields for the maintenance tab."""
        is_degraded = health_overall in ("yellow", "red") or status == "done_degraded"

        if status in ("pending",):
            return dict(display_action="none", display_label="等待处理", display_label_key="",
                        display_reason="", display_reason_key="",
                        display_group="hidden", display_severity="normal",
                        visible_in_maintenance=False, show_in_base=True)
        if status in ("running", "queued", "processing"):
            return dict(display_action="none", display_label="处理中", display_label_key="",
                        display_reason="", display_reason_key="",
                        display_group="hidden", display_severity="normal",
                        visible_in_maintenance=False, show_in_base=True)
        if status in ("failed", "error", "fatal_error", "done_incomplete", "retryable_error") and can_redo:
            return dict(display_action="retry_ocr", display_label="重试 OCR",
                        display_label_key="maintenance_action_retry_ocr",
                        display_reason="上次处理未完成，可以重新尝试",
                        display_reason_key="maintenance_reason_retry",
                        display_group="retry", display_severity="actionable",
                        visible_in_maintenance=True, show_in_base=True)
        if version == "v1" and can_redo:
            return dict(display_action="upgrade_legacy", display_label="升级旧结果",
                        display_label_key="maintenance_action_upgrade_legacy",
                        display_reason="旧版本结果仍然可用，升级后可获得更好的章节、图表和问答效果",
                        display_reason_key="maintenance_reason_legacy",
                        display_group="legacy_optional", display_severity="optional",
                        visible_in_maintenance=True, show_in_base=True)
        if is_degraded and can_rebuild:
            return dict(display_action="rebuild_result", display_label="重建结果",
                        display_label_key="",
                        display_reason="已有OCR数据，可重建获得更稳定的结果",
                        display_reason_key="",
                        display_group="rebuild", display_severity="actionable",
                        visible_in_maintenance=True, show_in_base=True)
        if is_degraded and not can_rebuild and can_redo:
            return dict(display_action="retry_ocr", display_label="重试 OCR",
                        display_label_key="",
                        display_reason="降级结果无法重建，可重新OCR",
                        display_reason_key="",
                        display_group="retry", display_severity="actionable",
                        visible_in_maintenance=True, show_in_base=True)
        if status == "nopdf":
            return dict(display_action="add_pdf", display_label="补充 PDF",
                        display_label_key="",
                        display_reason="请去 Zotero 添加 PDF 文件",
                        display_reason_key="",
                        display_group="external_action", display_severity="external",
                        visible_in_maintenance=False, show_in_base=True)
        if status == "blocked":
            return dict(display_action="configure_ocr", display_label="配置 OCR",
                        display_label_key="",
                        display_reason="请配置 PaddleOCR API Token",
                        display_reason_key="",
                        display_group="external_action", display_severity="external",
                        visible_in_maintenance=False, show_in_base=True)
        if status == "done" and not is_degraded:
            return dict(display_action="none", display_label="已完成", display_label_key="",
                        display_reason="", display_reason_key="",
                        display_group="hidden", display_severity="normal",
                        visible_in_maintenance=False, show_in_base=True)
        if not can_redo and not can_rebuild:
            return dict(display_action="none", display_label="已完成", display_label_key="",
                        display_reason="", display_reason_key="",
                        display_group="hidden", display_severity="normal",
                        visible_in_maintenance=False, show_in_base=False)
        return dict(display_action="none", display_label="已完成", display_label_key="",
                    display_reason="", display_reason_key="",
                    display_group="hidden", display_severity="normal",
                    visible_in_maintenance=False, show_in_base=True)

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
            "display_action": self.display_action,
            "display_label": self.display_label,
            "display_label_key": self.display_label_key,
            "display_reason": self.display_reason,
            "display_reason_key": self.display_reason_key,
            "display_group": self.display_group,
            "display_severity": self.display_severity,
            "visible_in_maintenance": self.visible_in_maintenance,
            "show_in_base": self.show_in_base,
            "fulltext_drift_state": self.fulltext_drift_state,
            "fulltext_drift_reason": self.fulltext_drift_reason,
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

_compute_display_fields = OCRMaintenanceRow.compute_display_fields


def compute_maintenance_manifest(vault: Path) -> dict[str, str]:
    """Return {key: sha256} for all OCR papers.
    Only reads meta.json + health/ocr_health.json.
    Does NOT read source_metadata, raw blocks, or formal-library index.
    """
    from paperforge.worker._utils import pipeline_paths
    from paperforge.worker.ocr_artifacts import artifact_paths_for_root
    import hashlib

    paths = pipeline_paths(vault)
    ocr_root = paths.get("ocr")
    if not ocr_root or not ocr_root.exists():
        return {}

    manifest = {}
    for paper_dir in sorted(ocr_root.iterdir()):
        if not paper_dir.is_dir():
            continue
        key = paper_dir.name
        artifacts = artifact_paths_for_root(ocr_root, key)
        meta = read_json(artifacts.meta_json) if artifacts.meta_json.exists() else {}
        health = read_json(artifacts.paper_root / "health" / "ocr_health.json") if (artifacts.paper_root / "health" / "ocr_health.json").exists() else {}
        status = str(meta.get("ocr_status", "") or "").lower()
        health_overall = str(health.get("overall", "") or "")

        # Also compute can_redo, can_rebuild, version to include in hash
        has_raw = artifacts.blocks_raw.exists()
        has_source_meta = artifacts.source_metadata.exists()
        has_structured = artifacts.blocks_structured.exists()
        version = _detect_version(meta, has_structured, has_raw)
        can_redo = _can_redo(meta)
        can_rebuild = _can_rebuild(meta, has_raw, has_source_meta)
        rec_action = _recommended_action(meta, has_raw, has_source_meta)

        # Compute display fields for hash
        df = OCRMaintenanceRow.compute_display_fields(
            status=status, health_overall=health_overall,
            version=version, can_redo=can_redo, can_rebuild=can_rebuild,
            error_stage=_error_stage(meta),
            error_summary=_error_summary(meta),
            degraded_reasons=health.get("degraded_reasons", []) or [],
        )

        err_summary = _error_summary(meta)
        drift_state = get_fulltext_drift_state(artifacts.compat_fulltext, meta.get("machine_fulltext_hash"))
        err_summary_hash = hashlib.sha256(err_summary.encode("utf-8")).hexdigest() if err_summary else ""
        raw = "|".join([
            key, status, health_overall, version, rec_action,
            df["display_action"], df["display_group"], df["display_severity"],
            drift_state, meta.get("machine_fulltext_hash", ""),
            err_summary, err_summary_hash,
            str(can_redo), str(can_rebuild),
            _error_stage(meta),
            str(health.get("degraded_reasons", [])),
        ])
        manifest[key] = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    return manifest


def collect_maintenance_rows(vault: Path) -> list[OCRMaintenanceRow]:
    """Scan all OCR paper directories and return normalized maintenance rows."""
    from paperforge.worker._utils import pipeline_paths
    from paperforge.worker.ocr_artifacts import artifact_paths_for_root

    paths = pipeline_paths(vault)
    ocr_root = paths.get("ocr")
    if not ocr_root or not ocr_root.exists():
        return []

    rows: list[OCRMaintenanceRow] = []

    # Preload canonical index for title fallback
    lib_index = paths.get("index", ocr_root.parent / "indexes") / "formal-library.json"
    title_by_key: dict[str, str] = {}
    if lib_index.exists():
        lib_data = read_json(lib_index)
        lib_items = lib_data.get("items", lib_data) if isinstance(lib_data, dict) else lib_data
        title_by_key = {i.get("zotero_key", ""): str(i.get("title", "") or "") for i in lib_items if i.get("zotero_key")}

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

        # Resolve title: meta.json -> source_metadata -> canonical index -> key
        title = meta.get("title")
        if not title and has_source_meta:
            sm = read_json(artifacts.source_metadata) if artifacts.source_metadata.exists() else {}
            title = sm.get("title", "")
        if not title:
            title = title_by_key.get(key, key)
        row = OCRMaintenanceRow(
            key=key,
            title=_short_title(title),
            title_full=_safe_str(title),
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
        row_status = status if status != "-" else "pending"
        df = _compute_display_fields(
            status=row_status, health_overall=health_overall,
            version=version, can_redo=row.can_redo, can_rebuild=row.can_rebuild,
            error_stage=meta.get("error_stage", ""),
            error_summary=_error_summary(meta),
            degraded_reasons=degraded_reasons,
        )
        row.display_action = df["display_action"]
        row.display_label = df["display_label"]
        row.display_label_key = df.get("display_label_key", "")
        row.display_reason = df["display_reason"]
        row.display_reason_key = df.get("display_reason_key", "")
        row.display_group = df["display_group"]
        row.display_severity = df["display_severity"]
        row.visible_in_maintenance = df["visible_in_maintenance"]
        drift_state = get_fulltext_drift_state(artifacts.compat_fulltext, meta.get("machine_fulltext_hash"))
        row.fulltext_drift_state = drift_state
        row.fulltext_drift_reason = {
            "MATCHED": "fulltext.md matches the latest machine write.",
            "DRIFTED": "fulltext.md has changed since the last machine write.",
            "UNKNOWN": "No machine baseline is available.",
        }[drift_state]
        rows.append(row)

    return rows
