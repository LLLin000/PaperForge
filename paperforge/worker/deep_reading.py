from __future__ import annotations
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

from paperforge.worker.sync import has_deep_reading_content, load_export_rows
from paperforge.worker.base_views import ensure_base_views
from paperforge.worker.ocr import validate_ocr_meta

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

def _resolve_formal_note_path(vault: Path, zotero_key: str, domain: str) -> Path | None:
    """Resolve formal literature note by zotero_key."""
    lit_root = pipeline_paths(vault)['literature']
    domain_dir = lit_root / domain
    if not domain_dir.exists():
        return None
    frontmatter_pattern = re.compile(f'^\\s*zotero_key:\\s*"?{re.escape(zotero_key)}"?\\s*$', re.MULTILINE)
    for note_path in domain_dir.rglob('*.md'):
        try:
            text = note_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            text = note_path.read_text(encoding='utf-8', errors='ignore')
        if frontmatter_pattern.search(text):
            return note_path
    return None

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
    domain_lookup = {entry['export_file']: entry['domain'] for entry in config['domains']}
    synced = 0
    pending_queue: list[dict] = []
    for export_path in sorted(paths['exports'].glob('*.json')):
        domain = domain_lookup.get(export_path.name, export_path.stem)
        for item in load_export_rows(export_path):
            key = item['key']
            record_dir = paths['library_records'] / domain
            record_path = record_dir / f'{key}.md'
            if not record_path.exists():
                continue
            record_text = record_path.read_text(encoding='utf-8')
            analyze_match = re.search('^analyze:\\s*(true|false)$', record_text, re.MULTILINE)
            is_analyze = analyze_match and analyze_match.group(1) == 'true'
            do_ocr_match = re.search('^do_ocr:\\s*(true|false)$', record_text, re.MULTILINE)
            is_do_ocr = do_ocr_match and do_ocr_match.group(1) == 'true'
            note_path = _resolve_formal_note_path(vault, key, domain)
            has_content = False
            if note_path and note_path.exists():
                note_text = note_path.read_text(encoding='utf-8')
                has_content = has_deep_reading_content(note_text)
            correct_status = 'done' if has_content else 'pending'
            status_match = re.search('^deep_reading_status:\\s*"??"?$', record_text, re.MULTILINE)
            current_status = status_match.group(1) if status_match else 'pending'
            if current_status != correct_status:
                new_text = re.sub('^deep_reading_status:\\s*"?.*?"?$', f'deep_reading_status: {yaml_quote(correct_status)}', record_text, flags=re.MULTILINE, count=1)
                record_path.write_text(new_text, encoding='utf-8')
                synced += 1
            if is_analyze and correct_status == 'pending':
                meta_path = paths['ocr'] / key / 'meta.json'
                ocr_status = 'pending'
                if meta_path.exists():
                    try:
                        meta = read_json(meta_path)
                        validated_status, error_msg = validate_ocr_meta(paths, meta)
                        ocr_status = validated_status
                    except Exception:
                        pass
                pending_queue.append({
                    'zotero_key': key,
                    'domain': domain,
                    'title': item.get('title', ''),
                    'ocr_status': ocr_status,
                    'is_analyze': is_analyze,
                    'is_do_ocr': is_do_ocr,
                })
    if pending_queue:
        ready = [q for q in pending_queue if q['ocr_status'] == 'done']
        waiting = [q for q in pending_queue if q['is_do_ocr'] and q['ocr_status'] in ('pending', 'processing')]
        blocked = [q for q in pending_queue if q['is_analyze'] and q['ocr_status'] not in ('done', '') and not (q['is_do_ocr'] and q['ocr_status'] in ('pending', 'processing'))]
        report_lines = ['# 待精读队列', '']
        if ready:
            report_lines.extend([f'## 就绪 ({len(ready)} 篇) — OCR 已完成，可直接 /pf-deep', ''])
            for q in ready:
                report_lines.append(f"- `{q['zotero_key']}` | {q['domain']} | {q['title']}")
            report_lines.append('')
        if waiting:
            report_lines.extend([f'## 等待 OCR ({len(waiting)} 篇)', ''])
            for q in waiting:
                report_lines.append(f"- `{q['zotero_key']}` | {q['domain']} | {q['title']} | OCR: {q['ocr_status']}")
            report_lines.append('')
        if blocked:
            report_lines.extend([f'## 阻塞 ({len(blocked)} 篇) — 需要先完成 OCR', ''])
            for q in blocked:
                report_lines.append(f"- `{q['zotero_key']}` | {q['domain']} | {q['title']} | OCR: {q['ocr_status'] or '未启动'}")
            report_lines.append('')
            if verbose:
                report_lines.append('### 修复步骤\n')
                for q in blocked:
                    ocr_s = q['ocr_status'] or ''
                    if not ocr_s or ocr_s == 'pending':
                        fix = f"paperforge ocr"
                        report_lines.append(f"- `{q['zotero_key']}`: 运行 `{fix}` 启动 OCR")
                    elif ocr_s == 'processing':
                        report_lines.append(f"- `{q['zotero_key']}`: OCR 进行中，请等待完成")
                    elif ocr_s == 'failed':
                        report_lines.append(f"- `{q['zotero_key']}`: OCR 失败 — 检查 meta.json 错误信息，然后重新运行 `paperforge ocr`")
                    else:
                        report_lines.append(f"- `{q['zotero_key']}`: 运行 `paperforge ocr` 重试")
                report_lines.append('')
        report_lines.extend(['## 操作', '', '- 对就绪论文，使用 `/pf-deep <zotero_key>` 触发精读', '- 批量触发：提供多个 key，用 subagent 并行处理', ''])
    else:
        report_lines = ['# 待精读队列', '', '所有 analyze=true 的论文已完成精读。', '']
    report_path = paths['pipeline'] / 'deep-reading-queue.md'
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')
    print(f'deep-reading: synced {synced} records, {len(pending_queue)} pending')
    return 0

