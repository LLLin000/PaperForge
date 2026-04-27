from __future__ import annotations
import logging
import argparse
import csv
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from json import JSONDecodeError
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
import requests
import fitz
from PIL import Image

from paperforge.worker.sync import (
    load_export_rows,
    obsidian_wikilink_for_pdf,
    update_frontmatter_field,
)
from paperforge.worker.deep_reading import _resolve_formal_note_path
from paperforge.worker.ocr import validate_ocr_meta

logger = logging.getLogger(__name__)

STANDARD_VIEW_NAMES = frozenset([
    "控制面板", "推荐分析", "待 OCR", "OCR 完成",
    "待深度阅读", "深度阅读完成", "正式卡片", "全记录"
])

def load_simple_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and (value[0] in {'"', "'"}):
            value = value[1:-1]
        os.environ[key] = value

def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))
_JOURNAL_DB: dict[str, dict] | None = None

def load_journal_db(vault: Path) -> dict[str, dict]:
    """Load zoterostyle.json journal database."""
    global _JOURNAL_DB
    if _JOURNAL_DB is not None:
        return _JOURNAL_DB
    zoterostyle_path = vault / load_vault_config(vault)['system_dir'] / 'Zotero' / 'zoterostyle.json'
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
        return ''
    journal_db = load_journal_db(vault)
    if journal_name in journal_db:
        rank_data = journal_db[journal_name].get('rank', {})
        if isinstance(rank_data, dict):
            sciif = rank_data.get('sciif', '')
            if sciif:
                return str(sciif)
    if extra:
        if_match = re.search('影响因子[:：]\\s*([0-9.]+)', extra)
        if if_match:
            return if_match.group(1)
    return ''

def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def read_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows

def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = '\n'.join((json.dumps(row, ensure_ascii=False) for row in rows))
    if text:
        text += '\n'
    path.write_text(text, encoding='utf-8')

def yaml_quote(value: str) -> str:
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return '"' + str(value or '').replace('\\', '\\\\').replace('"', '\\"') + '"'

def yaml_block(value: str) -> list[str]:
    value = (value or '').strip()
    if not value:
        return ['abstract: |-', '  ']
    lines = ['abstract: |-']
    for line in value.splitlines():
        lines.append(f'  {line}')
    return lines

def yaml_list(key: str, values) -> list[str]:
    cleaned = [str(value).strip() for value in values or [] if str(value).strip()]
    if not cleaned:
        return [f'{key}: []']
    lines = [f'{key}:']
    for value in cleaned:
        lines.append(f'  - {yaml_quote(value)}')
    return lines

def slugify_filename(text: str) -> str:
    cleaned = re.sub('[<>:"/\\\\|?*]+', '', text).strip()
    return cleaned[:120] or 'untitled'

def _extract_year(value: str) -> str:
    match = re.search('(19|20)\\d{2}', value or '')
    return match.group(0) if match else ''


def load_vault_config(vault: Path) -> dict:
    """Read vault configuration — delegates to shared resolver.

    Preserves the public name for legacy callers. Configuration precedence:
    1. paperforge.config.load_vault_config (overrides > env > JSON > defaults)
    """
    from paperforge.config import load_vault_config as _shared_load_vault_config
    return _shared_load_vault_config(vault)


def pipeline_paths(vault: Path) -> dict[str, Path]:
    """Build complete PaperForge path inventory — delegates to shared resolver.

    Returns paths from paperforge.config.paperforge_paths() plus
    worker-only keys. Preserves all legacy keys for existing callers.
    """
    from paperforge.config import paperforge_paths as _shared_paperforge_paths

    shared = _shared_paperforge_paths(vault)

    cfg = load_vault_config(vault)
    system_dir = cfg["system_dir"]
    resources_dir = cfg["resources_dir"]
    control_dir = cfg["control_dir"]

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

def load_domain_config(paths: dict[str, Path]) -> dict:
    """Load or create the Lite domain mapping from export JSON files."""
    config_path = paths['config']
    if config_path.exists():
        config = read_json(config_path)
    else:
        config = {"domains": []}
    domains = config.setdefault("domains", [])
    known_exports = {str(entry.get("export_file", "")) for entry in domains}
    changed = not config_path.exists()
    for export_path in sorted(paths['exports'].glob('*.json')):
        if export_path.name in known_exports:
            continue
        domains.append({"domain": export_path.stem, "export_file": export_path.name, "allowed_collections": []})
        known_exports.add(export_path.name)
        changed = True
    if changed:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(config_path, config)
    return config

def _find_export_for_domain(paths: dict[str, Path], domain: str) -> Path | None:
    """Find the BBT export JSON file for a given domain."""
    for export_path in sorted(paths["exports"].glob("*.json")):
        if export_path.stem == domain:
            return export_path
    return None


def _detect_path_errors(paths: dict[str, Path], verbose: bool = False) -> dict:
    """Scan library-records for path_error fields.

    Returns dict with:
        - total: total count of records with path_error
        - by_type: dict mapping error type -> count
        - records: list of record dicts with keys: path, zotero_key, domain, path_error, bbt_path_raw
    """
    result: dict = {"total": 0, "by_type": {}, "records": []}
    if not paths["library_records"].exists():
        return result
    for record_path in paths["library_records"].rglob("*.md"):
        try:
            text = record_path.read_text(encoding="utf-8")
        except Exception as e:
            if verbose:
                logger.error("error reading %s: %s", record_path, e)
            continue
        err_match = re.search(r'^path_error:\s*"(.*?)"\s*$', text, re.MULTILINE)
        if not err_match:
            continue
        path_error = err_match.group(1).strip()
        if not path_error:
            continue
        key_match = re.search(r'^zotero_key:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        if not key_match:
            continue
        zotero_key = key_match.group(1).strip()
        domain = record_path.parent.name
        bbt_match = re.search(r'^bbt_path_raw:\s*"(.*?)"\s*$', text, re.MULTILINE)
        bbt_path_raw = bbt_match.group(1) if bbt_match else ""
        result["total"] += 1
        result["by_type"][path_error] = result["by_type"].get(path_error, 0) + 1
        result["records"].append(
            {
                "path": record_path,
                "zotero_key": zotero_key,
                "domain": domain,
                "path_error": path_error,
                "bbt_path_raw": bbt_path_raw,
                "text": text,
            }
        )
    return result


def repair_pdf_paths(
    vault: Path,
    paths: dict[str, Path],
    error_records: list[dict],
    verbose: bool = False,
) -> int:
    """Re-resolve PDF paths for items with path_error.

    Returns number of paths successfully fixed.
    """
    fixed = 0
    from paperforge.pdf_resolver import resolve_pdf_path

    cfg = load_vault_config(vault)
    zotero_dir = vault / cfg.get("system_dir", "99_System") / "Zotero"

    # Cache export rows by domain to avoid reloading
    domain_exports: dict[str, list[dict]] = {}

    for record in error_records:
        record_path = record["path"]
        zotero_key = record["zotero_key"]
        domain = record["domain"]
        path_error = record["path_error"]
        text = record["text"]

        # For not_found errors, try to find the item in BBT export and re-process
        if path_error == "not_found":
            export_rows = domain_exports.get(domain)
            if export_rows is None:
                export_path = _find_export_for_domain(paths, domain)
                if export_path and export_path.exists():
                    try:
                        export_rows = load_export_rows(export_path)
                        domain_exports[domain] = export_rows
                    except Exception as e:
                        if verbose:
                            logger.error("error loading export for %s: %s", domain, e)
                        export_rows = []
                else:
                    export_rows = []
                    domain_exports[domain] = export_rows

            item = next((r for r in export_rows if r["key"] == zotero_key), None)
            if item:
                pdf_path = item.get("pdf_path", "")
                if pdf_path:
                    new_wikilink = obsidian_wikilink_for_pdf(
                        pdf_path, vault, zotero_dir
                    )
                    if new_wikilink:
                        new_text = update_frontmatter_field(
                            text, "pdf_path", new_wikilink
                        )
                        new_text = update_frontmatter_field(
                            new_text, "path_error", ""
                        )
                        new_text = update_frontmatter_field(
                            new_text,
                            "bbt_path_raw",
                            item.get("bbt_path_raw", ""),
                        )
                        new_text = update_frontmatter_field(
                            new_text,
                            "zotero_storage_key",
                            item.get("zotero_storage_key", ""),
                        )
                        if new_text != text:
                            record_path.write_text(new_text, encoding="utf-8")
                            fixed += 1
                            if verbose:
                                logger.info("fixed path for %s: %s", zotero_key, new_wikilink)
                        continue

        # For all errors, try resolving the current pdf_path
        pdf_match = re.search(r'^pdf_path:\s*"(.*?)"\s*$', text, re.MULTILINE)
        if pdf_match:
            current_pdf = pdf_match.group(1).strip()
            if current_pdf:
                raw_path = current_pdf.strip("[]")
                resolved = resolve_pdf_path(raw_path, True, vault, zotero_dir)
                if resolved:
                    new_text = update_frontmatter_field(text, "path_error", "")
                    if new_text != text:
                        record_path.write_text(new_text, encoding="utf-8")
                        fixed += 1
                        if verbose:
                            logger.info("cleared path_error for %s", zotero_key)
                else:
                    if verbose:
                        logger.warning("%s path still unresolved", zotero_key)
            else:
                if verbose:
                    logger.warning("%s has empty pdf_path (not_found)", zotero_key)
        else:
            if verbose:
                logger.warning("%s has no pdf_path field", zotero_key)

    return fixed


def run_repair(vault: Path, paths: dict, verbose: bool = False, fix: bool = False, fix_paths: bool = False) -> dict:
    """Scan all domains for three-way state divergence and optionally repair.

    Compares three sources of ocr_status:
    1. library_record.md frontmatter ocr_status
    2. formal_note.md frontmatter ocr_status
    3. meta.json ocr_status (post-validate_ocr_meta())

    Returns:
        dict with scanned, divergent, fixed, errors counts
    """
    result = {"scanned": 0, "divergent": [], "fixed": 0, "errors": []}
    config = load_domain_config(paths)
    domain_lookup = {entry['export_file']: entry['domain'] for entry in config['domains']}
    record_paths = list(paths['library_records'].rglob('*.md'))
    for record_path in record_paths:
        try:
            record_text = record_path.read_text(encoding='utf-8')
        except Exception as e:
            result['errors'].append({"file": str(record_path), "error": str(e)})
            continue
        key_match = re.search('^zotero_key:\\s*"?(.+?)"?\\s*$', record_text, re.MULTILINE)
        if not key_match:
            continue
        zotero_key = key_match.group(1).strip()
        domain = record_path.parent.name
        record_dir = record_path.parent
        result['scanned'] += 1
        lib_ocr_match = re.search('^ocr_status:\\s*"?(.+?)"?\\s*$', record_text, re.MULTILINE)
        lib_ocr_status = lib_ocr_match.group(1).strip() if lib_ocr_match else 'pending'
        note_path = _resolve_formal_note_path(vault, zotero_key, domain)
        note_ocr_status = None
        if note_path and note_path.exists():
            try:
                note_text = note_path.read_text(encoding='utf-8')
                note_status_match = re.search('^ocr_status:\\s*"?(.+?)"?\\s*$', note_text, re.MULTILINE)
                note_ocr_status = note_status_match.group(1).strip() if note_status_match else None
            except Exception:
                pass
        meta_path = paths['ocr'] / zotero_key / 'meta.json'
        meta_ocr_status = None
        meta_validated_status = None
        validated_status = None
        validated_error = ""
        if meta_path.exists():
            try:
                meta = read_json(meta_path)
                validated_status, validated_error = validate_ocr_meta(paths, meta)
                meta_validated_status = validated_status
                if validated_error and verbose:
                    logger.warning("%s meta validation error: %s", zotero_key, validated_error)
                raw_status = str(meta.get('ocr_status', '') or '').strip().lower()
                meta_ocr_status = raw_status if raw_status else None
                if meta_validated_status == 'done_incomplete':
                    meta_ocr_status = 'done_incomplete'
            except Exception as e:
                result['errors'].append({"file": str(meta_path), "error": str(e)})
                meta_ocr_status = None
        is_divergent = False
        div_reason = ""
        if meta_validated_status == 'done_incomplete':
            is_divergent = True
            div_reason = f"meta validation: done_incomplete ({validated_error})"
        elif lib_ocr_status == 'done' and meta_ocr_status in ('pending', 'processing', None):
            is_divergent = True
            div_reason = f"library_record done but meta {meta_ocr_status or 'missing'}"
        elif note_ocr_status == 'done' and (meta_ocr_status is None or meta_validated_status == 'done_incomplete'):
            is_divergent = True
            div_reason = "formal_note done but meta.json missing/invalid"
        elif lib_ocr_status != 'pending' and meta_ocr_status is not None and meta_validated_status is not None and lib_ocr_status != meta_validated_status:
            is_divergent = True
            div_reason = f"library_record={lib_ocr_status} vs meta post-validation={meta_validated_status}"
        if is_divergent:
            item = {
                "zotero_key": zotero_key,
                "domain": domain,
                "library_record_ocr_status": lib_ocr_status,
                "formal_note_ocr_status": note_ocr_status,
                "meta_ocr_status": meta_validated_status or meta_ocr_status,
                "reason": div_reason,
            }
            result['divergent'].append(item)
            if verbose:
                logger.info("divergent: %s | %s", zotero_key, div_reason)
            if fix:
                fixed_library_record = False
                fixed_formal_note = False
                fixed_meta = False
                new_status = 'pending'
                if meta_ocr_status is None or meta_validated_status == 'done_incomplete':
                    new_status = 'pending'
                    new_record_text = update_frontmatter_field(record_text, 'ocr_status', new_status)
                    if new_record_text != record_text:
                        record_path.write_text(new_record_text, encoding='utf-8')
                        fixed_library_record = True
                    if note_path and note_path.exists():
                        try:
                            note_text = note_path.read_text(encoding='utf-8')
                            new_note_text = update_frontmatter_field(note_text, 'ocr_status', new_status)
                            if new_note_text != note_text:
                                note_path.write_text(new_note_text, encoding='utf-8')
                                fixed_formal_note = True
                        except Exception:
                            pass
                    if meta_validated_status is not None and meta_validated_status != 'done':
                        if meta_path.exists():
                            try:
                                meta = read_json(meta_path)
                                meta['ocr_status'] = 'pending'
                                write_json(meta_path, meta)
                                fixed_meta = True
                            except Exception:
                                pass
                    record_do_ocr_match = re.search(r'^do_ocr:\s*(true|false)$', new_record_text, re.MULTILINE)
                    is_do_ocr = record_do_ocr_match and record_do_ocr_match.group(1) == 'true'
                    if not is_do_ocr:
                        final_record_text = update_frontmatter_field(new_record_text, 'do_ocr', 'true')
                        if final_record_text != new_record_text:
                            record_path.write_text(final_record_text, encoding='utf-8')
                            fixed_library_record = True
                elif lib_ocr_status == 'done' and meta_ocr_status in ('pending', 'processing'):
                    new_status = 'pending'
                    new_record_text = update_frontmatter_field(record_text, 'ocr_status', new_status)
                    if new_record_text != record_text:
                        record_path.write_text(new_record_text, encoding='utf-8')
                        fixed_library_record = True
                    if note_path and note_path.exists():
                        try:
                            note_text = note_path.read_text(encoding='utf-8')
                            new_note_text = update_frontmatter_field(note_text, 'ocr_status', new_status)
                            if new_note_text != note_text:
                                note_path.write_text(new_note_text, encoding='utf-8')
                                fixed_formal_note = True
                        except Exception:
                            pass
                    if meta_path.exists():
                        try:
                            meta = read_json(meta_path)
                            meta['ocr_status'] = 'pending'
                            write_json(meta_path, meta)
                            fixed_meta = True
                        except Exception:
                            pass
                    record_do_ocr_match = re.search(r'^do_ocr:\s*(true|false)$', new_record_text, re.MULTILINE)
                    is_do_ocr = record_do_ocr_match and record_do_ocr_match.group(1) == 'true'
                    if not is_do_ocr:
                        final_record_text = update_frontmatter_field(new_record_text, 'do_ocr', 'true')
                        if final_record_text != new_record_text:
                            record_path.write_text(final_record_text, encoding='utf-8')
                            fixed_library_record = True
                fixed_count = sum([fixed_library_record, fixed_formal_note, fixed_meta])
                result['fixed'] += fixed_count
                if verbose and fixed_count > 0:
                    logger.info("fixed %d files for %s", fixed_count, zotero_key)
    # Path error detection and repair
    path_errors = _detect_path_errors(paths, verbose)
    if path_errors["total"] > 0:
        error_summary = ", ".join(
            f"{count} {err}" for err, count in sorted(path_errors["by_type"].items())
        )
        print(
            f"[repair] Found {path_errors['total']} items with path errors: {error_summary}"
        )
        if fix_paths:
            fixed_count = repair_pdf_paths(
                vault, paths, path_errors["records"], verbose
            )
            print(f"[repair] Fixed {fixed_count} PDF paths")
        else:
            print("[repair] Tip: run with --fix-paths to attempt auto-resolution")
    elif verbose:
        print("[repair] No path errors found")

    result["path_errors"] = path_errors
    return result

