from __future__ import annotations

import json
import logging
import re
from json import JSONDecodeError
from pathlib import Path

from paperforge.config import paperforge_paths

logger = logging.getLogger(__name__)

# --- Constants ---

STANDARD_VIEW_NAMES = frozenset(
    ["控制面板", "推荐分析", "待 OCR", "OCR 完成", "待深度阅读", "深度阅读完成", "正式卡片", "全记录"]
)

# --- Journal Database ---


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


_JOURNAL_DB: dict[str, dict] | None = None


def load_journal_db(vault: Path) -> dict[str, dict]:
    """Load zoterostyle.json journal database."""
    global _JOURNAL_DB
    if _JOURNAL_DB is not None:
        return _JOURNAL_DB
    from paperforge.config import load_vault_config

    zoterostyle_path = vault / load_vault_config(vault)["system_dir"] / "Zotero" / "zoterostyle.json"
    if zoterostyle_path.exists():
        try:
            _JOURNAL_DB = read_json(zoterostyle_path)
        except (JSONDecodeError, Exception):
            _JOURNAL_DB = {}
    else:
        _JOURNAL_DB = {}
    return _JOURNAL_DB


def lookup_impact_factor(journal_name: str, extra: str, vault: Path) -> str:
    """Lookup impact factor: prefer zoterostyle.json, fallback to extra field."""
    if not journal_name:
        return ""
    journal_db = load_journal_db(vault)
    if journal_name in journal_db:
        rank_data = journal_db[journal_name].get("rank", {})
        if isinstance(rank_data, dict):
            sciif = rank_data.get("sciif", "")
            if sciif:
                return str(sciif)
    if extra:
        if_match = re.search("影响因子[:：]\\s*([0-9.]+)", extra)
        if if_match:
            return if_match.group(1)
    return ""


# --- JSON I/O ---


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    if text:
        text += "\n"
    path.write_text(text, encoding="utf-8")


# --- YAML Helpers ---


def yaml_quote(value: str) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return '"' + str(value or "").replace("\\", "\\\\").replace('"', '\\"') + '"'


def yaml_block(value: str) -> list[str]:
    value = (value or "").strip()
    if not value:
        return ["abstract: |-", "  "]
    lines = ["abstract: |-"]
    for line in value.splitlines():
        lines.append(f"  {line}")
    return lines


def yaml_list(key: str, values) -> list[str]:
    cleaned = [str(value).strip() for value in values or [] if value is not None and str(value).strip()]
    if not cleaned:
        return [f"{key}: []"]
    lines = [f"{key}:"]
    for value in cleaned:
        lines.append(f"  - {yaml_quote(value)}")
    return lines


# --- String / Path Utils ---


def slugify_filename(text: str) -> str:
    cleaned = re.sub('[<>:"/\\\\|?*]+', "", text).strip()
    return cleaned[:120] or "untitled"


def _extract_year(value: str) -> str:
    match = re.search("(19|20)\\d{2}", value or "")
    return match.group(0) if match else ""


# --- Deep-Reading Queue ---


def _resolve_formal_note_path(vault: Path, zotero_key: str, domain: str) -> Path | None:
    """Resolve formal literature note by zotero_key."""
    from paperforge.config import paperforge_paths

    lit_root = paperforge_paths(vault)["literature"]
    domain_dir = lit_root / domain
    if not domain_dir.exists():
        return None
    frontmatter_pattern = re.compile(rf'^\s*zotero_key:\s*"?{re.escape(zotero_key)}"?\s*$', re.MULTILINE)
    for note_path in domain_dir.rglob("*.md"):
        try:
            text = note_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = note_path.read_text(encoding="utf-8", errors="ignore")
        if frontmatter_pattern.search(text):
            return note_path
    return None


def scan_library_records(vault: Path) -> list[dict]:
    """Scan library-records for analyze=true entries.

    Pure data acquisition -- no side effects, no categorization.
    Returns all library records with analyze=true regardless of deep_reading_status.
    Caller filters and categorizes as needed.

    Return value fields (per D-03):
      - zotero_key: str
      - domain: str
      - title: str
      - analyze: bool (always True in results, included for symmetrical interface)
      - do_ocr: bool
      - deep_reading_status: str ("pending" | "done" -- from frontmatter, not validated)
      - ocr_status: str ("pending" | "processing" | "done" | "failed" -- from meta.json)
      - note_path: Path | None (resolved via _resolve_formal_note_path)
    """
    from paperforge.config import paperforge_paths

    paths = paperforge_paths(vault)
    records_root = paths.get("library_records")
    ocr_root = paths.get("ocr")

    if not records_root or not records_root.exists():
        return []

    results: list[dict] = []
    for domain_dir in sorted(records_root.iterdir()):
        if not domain_dir.is_dir():
            continue
        domain = domain_dir.name
        for record_path in sorted(domain_dir.glob("*.md")):
            try:
                text = record_path.read_text(encoding="utf-8")
            except Exception:
                continue

            # Extract frontmatter fields
            zotero_key_match = re.search(r"^zotero_key:\s*(.+)$", text, re.MULTILINE)
            analyze_match = re.search(r"^analyze:\s*(true|false)$", text, re.MULTILINE)
            title_match = re.search(r'^title:\s*"?(.+?)"?$', text, re.MULTILINE)
            do_ocr_match = re.search(r"^do_ocr:\s*(true|false)$", text, re.MULTILINE)
            status_match = re.search(r'^deep_reading_status:\s*"?(.*?)"?$', text, re.MULTILINE)

            zotero_key = (
                zotero_key_match.group(1).strip().strip('"').strip("'") if zotero_key_match else record_path.stem
            )
            is_analyze = analyze_match is not None and analyze_match.group(1) == "true"
            title = title_match.group(1).strip().strip('"') if title_match else ""
            do_ocr = do_ocr_match is not None and do_ocr_match.group(1) == "true"
            dr_status = status_match.group(1).strip() if status_match else "pending"

            if not is_analyze:
                continue

            # Check OCR status from meta.json
            meta_path = ocr_root / zotero_key / "meta.json"
            ocr_status = "pending"
            if meta_path.exists():
                try:
                    meta = read_json(meta_path)
                    ocr_status = str(meta.get("ocr_status", "pending")).strip().lower()
                except Exception:
                    pass

            # Resolve formal note path
            note_path = _resolve_formal_note_path(vault, zotero_key, domain)

            results.append(
                {
                    "zotero_key": zotero_key,
                    "domain": domain,
                    "title": title,
                    "analyze": True,
                    "do_ocr": do_ocr,
                    "deep_reading_status": dr_status,
                    "ocr_status": ocr_status,
                    "note_path": note_path,
                }
            )

    return results


def pipeline_paths(vault: Path) -> dict[str, Path]:
    """Build complete PaperForge path inventory — delegates to shared resolver."""
    shared = paperforge_paths(vault)
    root = shared["paperforge"]
    control_root = shared["control"]
    return {
        **shared,
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
