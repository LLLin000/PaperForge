from __future__ import annotations

import json
import logging
import re
import shutil
from json import JSONDecodeError
from pathlib import Path

from paperforge.config import paperforge_paths

logger = logging.getLogger(__name__)

# --- Constants ---

STANDARD_VIEW_NAMES = frozenset(
    ["控制面板", "推荐分析", "待 OCR", "OCR 完成", "待深度阅读", "深度阅读完成", "正式卡片", "全记录"]
)

# --- Journal Database ---


from paperforge.core.io import read_json, write_json


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
# write_json re-exported from paperforge.core.io


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
    cleaned = cleaned[:120].rstrip(" .")
    return cleaned or "untitled"


from paperforge.core.date_utils import extract_year as _extract_year


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


def get_analyze_queue(vault: Path) -> list[dict]:
    """Scan formal literature notes for analyze=true entries.

    Reads frontmatter directly from formal notes — no intermediary index.
    This eliminates the stale-index problem: when a user ticks analyze in
    the Base view (which updates formal note frontmatter), the queue picks
    it up immediately without requiring a sync.

    Return value fields:
      - zotero_key: str
      - domain: str
      - title: str
      - analyze: bool (always True in results)
      - do_ocr: bool
      - deep_reading_status: str
      - ocr_status: str
      - note_path: Path | None
    """
    from paperforge.config import paperforge_paths

    paths = paperforge_paths(vault)
    lit_root = paths.get("literature")

    if not lit_root or not lit_root.exists():
        return []

    results = []
    for note_file in lit_root.rglob("*.md"):
        if note_file.name in ("fulltext.md", "deep-reading.md", "discussion.md"):
            continue
        try:
            text = note_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # Quick exit: check analyze before extracting other fields
        analyze_match = re.search(
            r"^analyze:\s*(?:[\"'])?(true|false)(?:[\"'])?\s*$", text, re.MULTILINE | re.IGNORECASE
        )
        if not analyze_match or analyze_match.group(1).lower() != "true":
            continue

        zotero_key = ""
        key_match = re.search(r'^zotero_key:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        if key_match:
            zotero_key = key_match.group(1).strip()

        domain = ""
        domain_match = re.search(r'^domain:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        if domain_match:
            domain = domain_match.group(1).strip()

        title = ""
        title_match = re.search(r'^title:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()

        do_ocr = False
        do_ocr_match = re.search(r"^do_ocr:\s*(?:[\"'])?(true|false)(?:[\"'])?\s*$", text, re.MULTILINE | re.IGNORECASE)
        if do_ocr_match:
            do_ocr = do_ocr_match.group(1).lower() == "true"

        ocr_status = "pending"
        ocr_match = re.search(r'^ocr_status:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        if ocr_match:
            ocr_status = ocr_match.group(1).strip()

        dr_status = "pending"
        dr_match = re.search(r'^deep_reading_status:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        if dr_match:
            dr_status = dr_match.group(1).strip()

        results.append(
            {
                "zotero_key": zotero_key,
                "domain": domain,
                "title": title,
                "analyze": True,
                "do_ocr": do_ocr,
                "ocr_status": ocr_status,
                "deep_reading_status": dr_status,
                "note_path": note_file,
            }
        )

    results.sort(key=lambda r: (r["domain"], r["zotero_key"]))
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


def install_obsidian_plugin(vault: Path) -> bool:
    """Copy Obsidian plugin files into .obsidian/plugins/paperforge/.

    Source priority: vault copy (git/zip) -> Python package (pip).
    Lives in _utils.py so it can be reloaded after update.
    """
    try:
        plugin_dst = vault / ".obsidian" / "plugins" / "paperforge"
        plugin_src = vault / "paperforge" / "plugin"
        if not plugin_src.is_dir():
            import paperforge

            plugin_src = Path(paperforge.__file__).parent.resolve() / "plugin"
        if not plugin_src.is_dir():
            logger.warning("Plugin source not found: %s", plugin_src)
            return False
        plugin_dst.mkdir(parents=True, exist_ok=True)
        count = 0
        for f in plugin_src.glob("*"):
            if f.is_file():
                shutil.copy2(f, plugin_dst / f.name)
                count += 1
        if count:
            logger.info("Obsidian plugin installed: %d files -> %s", count, plugin_dst)
        return True
    except Exception as e:
        logger.warning("Failed to install Obsidian plugin: %s", e)
        return False
