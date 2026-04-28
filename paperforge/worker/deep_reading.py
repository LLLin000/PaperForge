from __future__ import annotations

import logging
import re
from pathlib import Path

from paperforge.config import paperforge_paths
from paperforge.worker._domain import load_domain_config
from paperforge.worker._utils import (
    read_json,
    scan_library_records,
    write_json,
    yaml_quote,
)
from paperforge.worker.base_views import ensure_base_views
from paperforge.worker.sync import has_deep_reading_content

logger = logging.getLogger(__name__)


def pipeline_paths(vault: Path) -> dict[str, Path]:
    """Build complete PaperForge path inventory — delegates to shared resolver.

    Returns paths from paperforge.config.paperforge_paths() plus
    worker-only keys. Preserves all legacy keys for existing callers.
    """
    shared = paperforge_paths(vault)

    root = shared["paperforge"]
    control_root = shared["control"]

    return {
        **shared,
        # Worker-only keys (added on top of shared resolver output)
        "pipeline": root,
        "candidates": root / "candidates" / "candidates.json",
        "candidate_inbox": root / "candidates" / "inbox",
        "candidate_archive": root / "candidates" / "archive",
        "search_tasks": root / "search" / "tasks",
        "search_archive": root / "search" / "archive",
        "search_results": root / "search" / "results",
        "harvest_root": root / "skill-prototypes" / "zotero-review-manuscript-writer",
        "records": control_root / "candidate-records",
        "review": root / "candidates" / "review-latest.md",
        "config": root / "config" / "domain-collections.json",
        "queue": root / "writeback" / "writeback-queue.jsonl",
        "log": root / "writeback" / "writeback-log.jsonl",
        "bridge_config": root / "zotero-bridge" / "bridge-config.json",
        "bridge_config_sample": root / "zotero-bridge" / "bridge-config.sample.json",
        "index": root / "indexes" / "formal-library.json",
        "ocr_queue": root / "ocr" / "ocr-queue.json",
    }


# Re-exported from _utils.py for backward compatibility


def run_deep_reading(vault: Path, verbose: bool = False) -> int:
    """Sync deep-reading status between formal notes and library records.

    This worker does NOT generate content. It only:
    1. Scans formal literature notes for `## 🔍 精读` content
    2. Updates library-records/*.md frontmatter to match actual state
    3. Reports the queue of papers awaiting deep reading

    Actual content filling is done via /pf-deep (agent-driven).
    """
    paths = pipeline_paths(vault)
    config = load_domain_config(paths)
    ensure_base_views(vault, paths, config)
    {entry["export_file"]: entry["domain"] for entry in config["domains"]}
    synced = 0
    pending_queue: list[dict] = []
    records = scan_library_records(vault)

    for record in records:
        key = record["zotero_key"]
        domain = record["domain"]

        # Status sync: check actual note content vs frontmatter status
        note_path = record["note_path"]
        has_content = False
        if note_path and note_path.exists():
            note_text = note_path.read_text(encoding="utf-8")
            has_content = has_deep_reading_content(note_text)
        correct_status = "done" if has_content else "pending"

        if record["deep_reading_status"] != correct_status:
            record_dir = paths["library_records"] / domain
            record_path = record_dir / f"{key}.md"
            record_text = record_path.read_text(encoding="utf-8")
            new_text = re.sub(
                '^deep_reading_status:\\s*"?.*?"?$',
                f"deep_reading_status: {yaml_quote(correct_status)}",
                record_text,
                flags=re.MULTILINE,
                count=1,
            )
            record_path.write_text(new_text, encoding="utf-8")
            synced += 1

        if correct_status == "pending":
            pending_queue.append(
                {
                    "zotero_key": key,
                    "domain": domain,
                    "title": record["title"],
                    "ocr_status": record["ocr_status"],
                    "is_analyze": True,
                    "is_do_ocr": record["do_ocr"],
                }
            )
    if pending_queue:
        ready = [q for q in pending_queue if q["ocr_status"] == "done"]
        waiting = [q for q in pending_queue if q["is_do_ocr"] and q["ocr_status"] in ("pending", "processing")]
        blocked = [
            q
            for q in pending_queue
            if q["is_analyze"]
            and q["ocr_status"] not in ("done", "")
            and not (q["is_do_ocr"] and q["ocr_status"] in ("pending", "processing"))
        ]
        report_lines = ["# 待精读队列", ""]
        if ready:
            report_lines.extend([f"## 就绪 ({len(ready)} 篇) — OCR 已完成，可直接 /pf-deep", ""])
            for q in ready:
                report_lines.append(f"- `{q['zotero_key']}` | {q['domain']} | {q['title']}")
            report_lines.append("")
        if waiting:
            report_lines.extend([f"## 等待 OCR ({len(waiting)} 篇)", ""])
            for q in waiting:
                report_lines.append(f"- `{q['zotero_key']}` | {q['domain']} | {q['title']} | OCR: {q['ocr_status']}")
            report_lines.append("")
        if blocked:
            report_lines.extend([f"## 阻塞 ({len(blocked)} 篇) — 需要先完成 OCR", ""])
            for q in blocked:
                report_lines.append(
                    f"- `{q['zotero_key']}` | {q['domain']} | {q['title']} | OCR: {q['ocr_status'] or '未启动'}"
                )
            report_lines.append("")
            if verbose:
                report_lines.append("### 修复步骤\n")
                for q in blocked:
                    ocr_s = q["ocr_status"] or ""
                    if not ocr_s or ocr_s == "pending":
                        fix = "paperforge ocr"
                        report_lines.append(f"- `{q['zotero_key']}`: 运行 `{fix}` 启动 OCR")
                    elif ocr_s == "processing":
                        report_lines.append(f"- `{q['zotero_key']}`: OCR 进行中，请等待完成")
                    elif ocr_s == "failed":
                        report_lines.append(
                            f"- `{q['zotero_key']}`: OCR 失败 — 检查 meta.json 错误信息，然后重新运行 `paperforge ocr`"
                        )
                    else:
                        report_lines.append(f"- `{q['zotero_key']}`: 运行 `paperforge ocr` 重试")
                report_lines.append("")
        report_lines.extend(
            [
                "## 操作",
                "",
                "- 对就绪论文，使用 `/pf-deep <zotero_key>` 触发精读",
                "- 批量触发：提供多个 key，用 subagent 并行处理",
                "",
            ]
        )
    else:
        report_lines = ["# 待精读队列", "", "所有 analyze=true 的论文已完成精读。", ""]
    report_path = paths["pipeline"] / "deep-reading-queue.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"deep-reading: synced {synced} records, {len(pending_queue)} pending")
    return 0
