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
    zoterostyle_path = vault / '99_System' / 'Zotero' / 'zoterostyle.json'
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

def pipeline_paths(vault: Path) -> dict[str, Path]:
    root = vault / '99_System' / 'LiteraturePipeline'
    control_root = vault / '03_Resources' / 'LiteratureControl'
    return {'pipeline': root, 'candidates': root / 'candidates' / 'candidates.json', 'candidate_inbox': root / 'candidates' / 'inbox', 'candidate_archive': root / 'candidates' / 'archive', 'search_tasks': root / 'search' / 'tasks', 'search_archive': root / 'search' / 'archive', 'search_results': root / 'search' / 'results', 'harvest_root': root / 'skill-prototypes' / 'zotero-review-manuscript-writer', 'records': control_root / 'candidate-records', 'review': root / 'candidates' / 'review-latest.md', 'config': root / 'config' / 'domain-collections.json', 'exports': root / 'exports', 'library_records': control_root / 'library-records', 'queue': root / 'writeback' / 'writeback-queue.jsonl', 'log': root / 'writeback' / 'writeback-log.jsonl', 'bridge_config': root / 'zotero-bridge' / 'bridge-config.json', 'bridge_config_sample': root / 'zotero-bridge' / 'bridge-config.sample.json', 'index': root / 'indexes' / 'formal-library.json', 'ocr': root / 'ocr', 'ocr_queue': root / 'ocr' / 'ocr-queue.json', 'resources': vault / '03_Resources'}

def build_collection_lookup(collections: dict) -> dict:
    path_cache = {}
    item_paths = {}

    def path_for(key: str) -> str:
        if key in path_cache:
            return path_cache[key]
        node = collections.get(key, {})
        parent = node.get('parent') or ''
        name = node.get('name', '')
        parent_path = path_for(parent) if parent else ''
        full_path = f'{parent_path}/{name}' if parent_path else name
        path_cache[key] = full_path
        return full_path
    for key, node in collections.items():
        full_path = path_for(key)
        for item_id in node.get('items', []):
            item_paths.setdefault(item_id, []).append(full_path)
    return {'path_by_key': path_cache, 'paths_by_item_id': item_paths}

def export_collection_paths(export_path: Path) -> list[str]:
    data = read_json(export_path)
    if not isinstance(data, dict):
        return []
    collections = data.get('collections', {})
    if not isinstance(collections, dict):
        return []
    lookup = build_collection_lookup(collections)
    paths = sorted({path for path in lookup.get('path_by_key', {}).values() if str(path or '').strip()}, key=lambda value: (value.count('/'), value))
    return paths

def load_domain_collection_catalog(paths: dict[str, Path]) -> dict[str, list[str]]:
    config_path = paths['config']
    config = read_json(config_path) if config_path.exists() else {'domains': []}
    domain_entries = list(config.get('domains', []))
    entry_by_export = {entry.get('export_file', ''): dict(entry) for entry in domain_entries if entry.get('export_file')}
    export_files = sorted(paths['exports'].glob('*.json'))
    changed = False
    for export_path in export_files:
        entry = entry_by_export.get(export_path.name)
        if not entry:
            entry = {'domain': export_path.stem, 'export_file': export_path.name, 'allowed_collections': []}
            entry_by_export[export_path.name] = entry
            changed = True
        derived = export_collection_paths(export_path)
        if entry.get('allowed_collections', []) != derived:
            entry['allowed_collections'] = derived
            changed = True
    domains = sorted(entry_by_export.values(), key=lambda entry: entry.get('domain', ''))
    if changed or config.get('domains', []) != domains:
        write_json(config_path, {'domains': domains})
    return {entry.get('domain', ''): entry.get('allowed_collections', []) for entry in domains if entry.get('domain')}

def load_export_inventory(paths: dict[str, Path]) -> dict[str, dict]:
    inventory = {'doi': {}, 'pmid': {}, 'title': {}}
    for export_path in sorted(paths['exports'].glob('*.json')):
        domain = export_path.stem
        for item in load_export_rows(export_path):
            record = {'zotero_key': item.get('key', ''), 'domain': domain, 'title': item.get('title', ''), 'doi': item.get('doi', ''), 'pmid': item.get('pmid', ''), 'collections': item.get('collections', [])}
            doi = str(record.get('doi', '') or '').strip().lower()
            pmid = str(record.get('pmid', '') or '').strip()
            title = normalize_candidate_title(record.get('title', ''))
            if doi and doi not in inventory['doi']:
                inventory['doi'][doi] = record
            if pmid and pmid not in inventory['pmid']:
                inventory['pmid'][pmid] = record
            if title and title not in inventory['title']:
                inventory['title'][title] = record
    return inventory

def find_existing_library_match(row: dict, inventory: dict[str, dict]) -> dict | None:
    doi = str(row.get('doi', '') or '').strip().lower()
    if doi and doi in inventory['doi']:
        return inventory['doi'][doi]
    pmid = str(row.get('pmid', '') or '').strip()
    if pmid and pmid in inventory['pmid']:
        return inventory['pmid'][pmid]
    title = normalize_candidate_title(row.get('title', ''))
    if title and title in inventory['title']:
        return inventory['title'][title]
    return None

def resolve_collection_choice(domain: str, raw_value: str, catalog: dict[str, list[str]]) -> dict[str, str]:
    text = str(raw_value or '').strip()
    if not text:
        return {'resolved': '', 'match': '', 'input': ''}
    allowed = [path for path in catalog.get(domain, []) if path]
    if not allowed:
        return {'resolved': '', 'match': 'no_catalog', 'input': text}
    lower_text = text.lower()
    if '/' not in text:
        leaf_matches = [path for path in allowed if path.split('/')[-1].strip().lower() == lower_text]
        leaf_matches = sorted(set(leaf_matches))
        if len(leaf_matches) > 1:
            return {'resolved': '', 'match': 'ambiguous_leaf', 'input': text}
    exact_map = {path: path for path in allowed}
    if text in exact_map:
        return {'resolved': text, 'match': 'exact', 'input': text}
    lower_exact = {path.lower(): path for path in allowed}
    if lower_text in lower_exact:
        return {'resolved': lower_exact[lower_text], 'match': 'exact_ci', 'input': text}
    leaf_matches = [path for path in allowed if path.split('/')[-1].strip().lower() == lower_text]
    if len(leaf_matches) == 1:
        return {'resolved': leaf_matches[0], 'match': 'leaf', 'input': text}
    suffix_matches = [path for path in allowed if path.lower().endswith('/' + lower_text) or path.lower() == lower_text]
    suffix_matches = sorted(set(suffix_matches))
    if len(suffix_matches) == 1:
        return {'resolved': suffix_matches[0], 'match': 'suffix', 'input': text}
    compact = re.sub('\\s+', '', lower_text)
    compact_matches = []
    for path in allowed:
        path_compact = re.sub('\\s+', '', path.lower())
        if path_compact.endswith('/' + compact) or path_compact == compact:
            compact_matches.append(path)
    compact_matches = sorted(set(compact_matches))
    if len(compact_matches) == 1:
        return {'resolved': compact_matches[0], 'match': 'compact_suffix', 'input': text}
    match = 'ambiguous' if leaf_matches or suffix_matches or compact_matches else 'unresolved'
    return {'resolved': '', 'match': match, 'input': text}

def apply_candidate_collection_resolution(row: dict, catalog: dict[str, list[str]]) -> dict:
    resolved = dict(row)
    domain = str(resolved.get('domain', '') or '').strip()
    recommended = resolve_collection_choice(domain, resolved.get('recommended_collection', ''), catalog)
    user = resolve_collection_choice(domain, resolved.get('user_collection', ''), catalog)
    resolved['recommended_collection'] = recommended.get('resolved', '')
    resolved['user_collection_resolved'] = user.get('resolved', '')
    if str(resolved.get('user_collection', '') or '').strip():
        resolved['final_collection'] = user.get('resolved', '')
        resolved['collection_resolution'] = f"user_{user.get('match', 'unresolved')}" if user.get('match') else 'user_unresolved'
    else:
        resolved['final_collection'] = recommended.get('resolved', '')
        resolved['collection_resolution'] = f"recommended_{recommended.get('match', 'unresolved')}" if recommended.get('match') else 'recommended_unresolved'
    return resolved

def apply_existing_library_match(row: dict, inventory: dict[str, dict]) -> dict:
    resolved = dict(row)
    match = find_existing_library_match(resolved, inventory)
    if not match:
        resolved['existing_zotero_key'] = ''
        resolved['existing_collections'] = []
        resolved['duplicate_hint'] = ''
        return resolved
    resolved['existing_zotero_key'] = str(match.get('zotero_key', '') or '').strip()
    resolved['existing_collections'] = list(match.get('collections', []) or [])
    collections_text = ' | '.join(resolved['existing_collections'])
    if collections_text:
        resolved['duplicate_hint'] = f"已存在于 Zotero: {resolved['existing_zotero_key']} ({collections_text})"
    else:
        resolved['duplicate_hint'] = f"已存在于 Zotero: {resolved['existing_zotero_key']}"
    return resolved

def resolve_item_collection_paths(item: dict, collection_lookup: dict) -> list[str]:
    paths = []
    collection_keys = item.get('collections') or []
    if collection_keys:
        for key in collection_keys:
            paths.append(collection_lookup.get('path_by_key', {}).get(key, key))
    item_id = item.get('itemID')
    if item_id is not None:
        paths.extend(collection_lookup.get('paths_by_item_id', {}).get(item_id, []))
    return sorted({path for path in paths if path}, key=lambda value: (-value.count('/'), value))

def obsidian_wikilink_for_pdf(vault: Path, path: str) -> str:
    text = str(path or '').strip()
    if not text:
        return ''
    return obsidian_wikilink_for_path(vault, text)

def absolutize_vault_path(vault: Path, path: str) -> str:
    text = str(path or '').strip()
    if not text:
        return ''
    candidate = Path(text)
    if candidate.is_absolute():
        return str(candidate)
    return str((vault / text.replace('/', os.sep)).resolve())

def obsidian_wikilink_for_path(vault: Path, path: str) -> str:
    absolute = absolutize_vault_path(vault, path)
    if not absolute:
        return ''
    absolute_path = Path(absolute)
    try:
        relative = absolute_path.relative_to(vault)
    except ValueError:
        return f'[[{absolute_path.as_posix()}]]'
    return f'[[{relative.as_posix()}]]'

def collection_fields(collection_paths: list[str]) -> dict[str, str | list[str]]:
    paths = [path for path in collection_paths if path]
    primary = paths[0] if paths else ''
    if paths:
        primary = sorted(paths, key=lambda value: (value.count('/'), len(value), value), reverse=True)[0]
    tags = []
    seen = set()
    for path in paths:
        for part in [segment.strip() for segment in path.split('/') if segment.strip()]:
            if part not in seen:
                seen.add(part)
                tags.append(part)
    group = primary
    return {'collections': paths, 'collection_tags': tags, 'collection_group': [group] if group else []}

def extract_authors(item: dict) -> list[str]:
    authors = []
    for creator in item.get('creators', []):
        if creator.get('creatorType') != 'author':
            continue
        full_name = ' '.join((part for part in [creator.get('firstName', ''), creator.get('lastName', '')] if part)).strip()
        if full_name:
            authors.append(full_name)
        elif creator.get('name'):
            authors.append(creator['name'])
    return authors

def load_export_rows(path: Path) -> list[dict]:
    data = read_json(path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get('items'), list):
        collection_lookup = build_collection_lookup(data.get('collections', {}))
        rows = []
        for item in data['items']:
            if item.get('itemType') in {'attachment', 'note', 'annotation'}:
                continue
            attachments = []
            for attachment in item.get('attachments', []):
                if not isinstance(attachment, dict):
                    continue
                attachment_path = attachment.get('path', '')
                content_type = 'application/pdf' if str(attachment_path).lower().endswith('.pdf') else ''
                attachments.append({'path': attachment_path, 'contentType': content_type})
            rows.append({'key': item.get('key') or item.get('itemKey', ''), 'title': item.get('title', ''), 'authors': extract_authors(item), 'abstract': item.get('abstractNote', ''), 'journal': item.get('publicationTitle', ''), 'year': _extract_year(item.get('date', '')), 'date': item.get('date', ''), 'doi': item.get('DOI', ''), 'pmid': item.get('PMID', ''), 'collections': resolve_item_collection_paths(item, collection_lookup), 'attachments': attachments})
        return rows
    raise ValueError(f'Unsupported export format: {path}')

def compute_final_collection(row: dict) -> str:
    user_raw = str(row.get('user_collection', '') or '').strip()
    user_resolved = str(row.get('user_collection_resolved', '') or '').strip()
    recommended = str(row.get('recommended_collection', '') or '').strip()
    if user_raw:
        return user_resolved
    return recommended

def canonicalize_decision(value: str) -> str:
    text = str(value or '').strip()
    if text in {'', '待查'}:
        return '待定'
    if text in {'排除', '不纳入'}:
        return '不纳入'
    if text == '纳入':
        return '纳入'
    return '待定'

def candidate_markdown(row: dict) -> str:
    row = dict(row)
    row['final_collection'] = compute_final_collection(row)
    row['decision'] = canonicalize_decision(row.get('decision', ''))
    lines = ['---']
    ordered_keys = ['candidate_id', 'domain', 'title', 'authors', 'year', 'journal', 'doi', 'pmid', 'source', 'requester_skill', 'request_context', 'abstract_short', 'decision', 'recommended_collection', 'recommend_confidence', 'recommend_reason', 'user_collection', 'user_collection_resolved', 'final_collection', 'collection_resolution', 'duplicate_hint', 'existing_zotero_key', 'existing_collections', 'import_status', 'note', 'candidate_source_type', 'source_zotero_key', 'cited_ref_number', 'trigger_sentence', 'source_context', 'task_relevance_reason', 'harvest_priority', 'raw_reference', 'status']
    row.setdefault('status', 'candidate')
    for key in ordered_keys:
        value = row.get(key, '')
        if isinstance(value, list):
            lines.append(f'{key}:')
            for item in value:
                lines.append(f'  - {yaml_quote(item)}')
        elif value == '':
            lines.append(f'{key}:')
        elif '\n' in str(value):
            lines.extend(yaml_block(str(value)).copy() if key == 'abstract' else [f'{key}: |-'] + [f'  {line}' for line in str(value).splitlines()])
        else:
            lines.append(f'{key}: {yaml_quote(value)}')
    lines.extend(['---', '', f"# {row['candidate_id']}", '', '候选文献轻量记录，仅用于 Base 决策和 write-back 触发，不是正式文献卡片。', ''])
    return '\n'.join(lines)

def generate_review(candidates: list[dict]) -> str:
    normalized = []
    for row in candidates:
        copy = dict(row)
        copy['decision'] = canonicalize_decision(copy.get('decision', ''))
        normalized.append(copy)
    include = [c for c in normalized if c.get('decision') == '纳入']
    exclude = [c for c in normalized if c.get('decision') == '不纳入']
    lines = ['# 本轮候选总览', '', '## 检索背景', '', f'- 候选数量：{len(normalized)}', f'- 建议纳入：{len(include)}', f'- 不纳入：{len(exclude)}', '', '## 总体判断', '', '- 当前候选池已经按决策状态分层，可直接进入 Base 处理。', '', '## 推荐优先纳入', '']
    if include:
        for row in include:
            lines.extend([f"### {row['candidate_id']}", '', f"- 标题：{row['title']}", f'- 推荐分类：`{compute_final_collection(row)}`', f"- 理由：{row.get('recommend_reason', '')}", ''])
    else:
        lines.extend(['- 暂无', ''])
    lines.extend(['## 不纳入', ''])
    if exclude:
        for row in exclude:
            lines.extend([f"### {row['candidate_id']}", '', f"- 标题：{row['title']}", f"- 理由：{row.get('recommend_reason', '')}", ''])
    else:
        lines.extend(['- 暂无', ''])
    lines.extend(['## 下一步', '', '1. 在 Base 中确认决策。', '2. 对纳入项执行 write-back。', '3. 刷新正式索引。', ''])
    return '\n'.join(lines)
DEEP_READING_HEADER = '## 🔍 精读'

def extract_preserved_deep_reading(text: str) -> str:
    """Extract the `## 🔍 精读` section by matching it as a real markdown header.

    Uses regex to ensure we match `## 🔍 精读` at the start of a line,
    avoiding false positives from prose text that merely mentions the string.
    """
    if not text:
        return ''
    match = re.search('^## 🔍 精读\\s*$', text, re.MULTILINE)
    if not match:
        return ''
    start = match.start()
    preserved = text[start:].strip()
    return preserved

def has_deep_reading_content(text: str) -> bool:
    """Return True only if the deep-reading section contains *substantive* content.

    A scaffold alone (filled with placeholders like '（待补充）') does NOT count.
    We strip out structural lines (section headers, callout headers, empty lists)
    and placeholder text, then require at least one prose sentence or 20 chars
    of actual content.
    """
    preserved = extract_preserved_deep_reading(text)
    if not preserved:
        return False
    body = preserved.replace(DEEP_READING_HEADER, '').strip()
    if not body:
        return False
    lines = body.splitlines()
    non_placeholder_chars = 0
    has_prose_sentence = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('### '):
            continue
        if re.match('^>\\s*\\[!', stripped):
            continue
        if '（待补充）' in stripped:
            continue
        if re.match('^[-*]\\s*$', stripped):
            continue
        non_placeholder_chars += len(stripped)
        if re.search('[\\u4e00-\\u9fff]', stripped) and re.search('[。！？\\.\\!\\?]$', stripped):
            has_prose_sentence = True
    return has_prose_sentence or non_placeholder_chars >= 20

def library_record_markdown(row: dict) -> str:
    lines = ['---', f"zotero_key: {row.get('zotero_key', '')}", f"domain: {row.get('domain', '')}", f"title: {yaml_quote(row.get('title', ''))}", f"year: {row.get('year', '')}", f"doi: {yaml_quote(row.get('doi', ''))}", f"date: {yaml_quote(row.get('date', ''))}", f"collection_path: {yaml_quote(row.get('collection_path', ''))}", f"has_pdf: {('true' if row.get('has_pdf') else 'false')}", f"pdf_path: {yaml_quote(row.get('pdf_path', ''))}", f"fulltext_md_path: {yaml_quote(row.get('fulltext_md_path', ''))}", f"recommend_analyze: {('true' if row.get('recommend_analyze') else 'false')}", f"analyze: {('true' if row.get('analyze') else 'false')}", f"do_ocr: {('true' if row.get('do_ocr') else 'false')}", f"ocr_status: {yaml_quote(row.get('ocr_status', 'pending'))}", f"deep_reading_status: {yaml_quote(row.get('deep_reading_status', 'pending'))}", f"analysis_note: {yaml_quote(row.get('analysis_note', ''))}"]
    lines.extend(yaml_list('collection_group', row.get('collection_group', [])))
    lines.extend(yaml_list('collections', row.get('collections', [])))
    lines.extend(yaml_list('collection_tags', row.get('collection_tags', [])))
    lines.append(f"first_author: {yaml_quote(row.get('first_author', ''))}")
    lines.append(f"journal: {yaml_quote(row.get('journal', ''))}")
    lines.append(f"impact_factor: {yaml_quote(row.get('impact_factor', ''))}")
    lines.extend(['---', '', f"# {row.get('title', '')}", '', '正式库控制记录。', '', '- `recommend_analyze` 仅由 `has_pdf=true` 推导。', '- `analyze` 控制是否生成正式文献卡片。', '- `do_ocr` 控制 OCR 任务。', '- `deep_reading_status` 仅两级：`pending`（未精读）/ `done`（已精读）。', ''])
    return '\n'.join(lines)

def _add_missing_frontmatter_fields(existing_content: str, new_fields: dict[str, str]) -> str:
    """Surgically append missing fields to existing frontmatter without overwriting anything."""
    if not existing_content.startswith('---'):
        return existing_content
    parts = existing_content.split('---', 2)
    if len(parts) < 3:
        return existing_content
    frontmatter = parts[1]
    body = parts[2]
    lines_to_add = []
    for key, value in new_fields.items():
        pattern = '^' + re.escape(key) + '\\s*:'
        if not re.search(pattern, frontmatter, re.MULTILINE):
            lines_to_add.append(f'{key}: {yaml_quote(value)}')
    if not lines_to_add:
        return existing_content
    new_frontmatter = frontmatter.rstrip('\n') + '\n' + '\n'.join(lines_to_add) + '\n'
    return f'---{new_frontmatter}---{body}'

def update_frontmatter_field(content: str, key: str, value: str) -> str:
    """Update an existing frontmatter field value, or add if missing."""
    if not content.startswith('---'):
        return content
    pattern = '^' + re.escape(key) + '\\s*:.*$'
    replacement = f'{key}: {yaml_quote(value)}'
    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE, count=1)
    if count == 0:
        new_content = _add_missing_frontmatter_fields(content, {key: value})
    return new_content

def parse_existing_library_record(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding='utf-8')
    result = {}
    for key in ('analyze', 'recommend_analyze', 'do_ocr'):
        match = re.search(f'^{key}:\\s*(true|false)$', text, re.MULTILINE)
        if match:
            result[key] = match.group(1) == 'true'
    for key in ('ocr_status', 'analysis_note'):
        match = re.search(f'^{key}:\\s*"?(.*?)"?$', text, re.MULTILINE)
        if match:
            result[key] = match.group(1)
    for key in ('deep_reading_status',):
        match = re.search(f'^{key}:\\s*"?(.*?)"?$', text, re.MULTILINE)
        if match:
            result[key] = match.group(1)
    return result

def load_control_actions(paths: dict[str, Path]) -> dict[str, dict]:
    actions = {}
    if not paths['library_records'].exists():
        return actions
    for record in paths['library_records'].rglob('*.md'):
        text = record.read_text(encoding='utf-8')
        key_match = re.search('^zotero_key:\\s*(.+)$', text, re.MULTILINE)
        if not key_match:
            continue
        zotero_key = key_match.group(1).strip()
        row = parse_existing_library_record(record)
        actions[zotero_key] = {'analyze': row.get('analyze', False), 'do_ocr': row.get('do_ocr', False)}
    return actions

def run_selection_sync(vault: Path) -> int:
    paths = pipeline_paths(vault)
    config = read_json(paths['config'])
    domain_lookup = {entry['export_file']: entry['domain'] for entry in config['domains']}
    written = 0
    updated = 0
    for export_path in sorted(paths['exports'].glob('*.json')):
        domain = domain_lookup.get(export_path.name, export_path.stem)
        for item in load_export_rows(export_path):
            pdf_attachments = [a for a in item.get('attachments', []) if a.get('contentType') == 'application/pdf']
            collection_meta = collection_fields(item.get('collections', []))
            record_dir = paths['library_records'] / domain
            record_dir.mkdir(parents=True, exist_ok=True)
            record_path = record_dir / f"{item['key']}.md"
            existing = parse_existing_library_record(record_path)
            meta_path = paths['ocr'] / item['key'] / 'meta.json'
            meta = read_json(meta_path) if meta_path.exists() else {}
            validated_ocr_status, validated_error = validate_ocr_meta(paths, meta) if meta else ('pending', '')
            if meta:
                meta['ocr_status'] = validated_ocr_status
                if validated_error:
                    meta['error'] = validated_error
                    write_json(meta_path, meta)
            note_path = paths['resources'] / 'Literature' / domain / f"{item['key']} - {slugify_filename(item['title'])}.md"
            note_text = note_path.read_text(encoding='utf-8') if note_path.exists() else ''
            fulltext_md_path = obsidian_wikilink_for_path(vault, meta.get('fulltext_md_path', '') or meta.get('markdown_path', ''))
            ocr_status = meta.get('ocr_status', 'pending')
            creators = item.get('creators', [])
            first_author = ''
            for c in creators:
                if c.get('creatorType') == 'author':
                    first_author = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
                    break
            journal = item.get('publicationTitle', '')
            extra = item.get('extra', '')
            impact_factor = lookup_impact_factor(journal, extra, vault)
            content = library_record_markdown({'zotero_key': item['key'], 'domain': domain, 'title': item.get('title', ''), 'year': item.get('year', ''), 'doi': item.get('doi', ''), 'date': item.get('date', ''), 'collection_path': ' | '.join(item.get('collections', [])), 'collections': collection_meta.get('collections', []), 'collection_tags': collection_meta.get('collection_tags', []), 'collection_group': collection_meta.get('collection_group', []), 'has_pdf': bool(pdf_attachments), 'pdf_path': obsidian_wikilink_for_pdf(vault, pdf_attachments[0]['path']) if pdf_attachments else '', 'recommend_analyze': bool(pdf_attachments), 'analyze': existing.get('analyze', False), 'do_ocr': existing.get('do_ocr', False), 'ocr_status': ocr_status, 'fulltext_md_path': fulltext_md_path, 'deep_reading_status': 'done' if note_text and has_deep_reading_content(note_text) else 'pending', 'analysis_note': existing.get('analysis_note', ''), 'first_author': first_author, 'journal': journal, 'impact_factor': impact_factor})
            if record_path.exists():
                existing_content = record_path.read_text(encoding='utf-8')
                updated_content = _add_missing_frontmatter_fields(existing_content, {'first_author': first_author, 'journal': journal, 'impact_factor': impact_factor})
                updated_content = update_frontmatter_field(updated_content, 'ocr_status', ocr_status)
                updated_content = update_frontmatter_field(updated_content, 'deep_reading_status', 'done' if note_text and has_deep_reading_content(note_text) else 'pending')
                updated_content = update_frontmatter_field(updated_content, 'fulltext_md_path', fulltext_md_path or '')
                if updated_content != existing_content:
                    record_path.write_text(updated_content, encoding='utf-8')
                    updated += 1
            else:
                written += 1
                record_path.write_text(content, encoding='utf-8')
    print(f'selection-sync: wrote {written} records, updated {updated} records')
    return 0

def load_candidates_by_id(paths: dict[str, Path]) -> dict[str, dict]:
    candidates = read_json(paths['candidates'])
    return {row['candidate_id']: row for row in candidates}

def save_candidates(paths: dict[str, Path], candidate_map: dict[str, dict]) -> None:
    collection_catalog = load_domain_collection_catalog(paths)
    export_inventory = load_export_inventory(paths)
    rows = []
    for row in candidate_map.values():
        copy = dict(row)
        copy['decision'] = canonicalize_decision(copy.get('decision', ''))
        copy = apply_candidate_collection_resolution(copy, collection_catalog)
        copy = apply_existing_library_match(copy, export_inventory)
        copy['final_collection'] = compute_final_collection(copy)
        rows.append(copy)
    write_json(paths['candidates'], rows)

def writeback_command_for_candidate(row: dict) -> dict | None:
    final_collection = str(row.get('final_collection', '') or '').strip()
    if not final_collection:
        return None
    candidate_id = str(row.get('candidate_id', '') or '').strip()
    if not candidate_id:
        return None
    command = {'command_id': f'wb-native-{candidate_id}', 'status': 'queued', 'source_candidate_id': candidate_id, 'target_domain': str(row.get('domain', '') or '').strip(), 'target_collection': final_collection, 'requested_at': datetime.now(timezone.utc).isoformat()}
    existing_zotero_key = str(row.get('existing_zotero_key', '') or '').strip()
    if existing_zotero_key:
        command.update({'action': 'attach_existing_item_to_collection', 'existing_zotero_key': existing_zotero_key})
        return command
    doi = str(row.get('doi', '') or '').strip()
    pmid = str(row.get('pmid', '') or '').strip()
    if doi:
        command.update({'action': 'create_item_from_identifier', 'identifier_type': 'doi', 'identifier': doi, 'metadata_fallback': {'title': row.get('title', ''), 'authors': row.get('authors', []), 'year': str(row.get('year', '') or ''), 'journal': row.get('journal', ''), 'doi': doi, 'pmid': pmid, 'abstractNote': row.get('abstract_short', '')}})
        return command
    if pmid:
        command.update({'action': 'create_item_from_identifier', 'identifier_type': 'pmid', 'identifier': pmid, 'metadata_fallback': {'title': row.get('title', ''), 'authors': row.get('authors', []), 'year': str(row.get('year', '') or ''), 'journal': row.get('journal', ''), 'doi': doi, 'pmid': pmid, 'abstractNote': row.get('abstract_short', '')}})
        return command
    command.update({'action': 'create_item_from_metadata', 'metadata': {'title': row.get('title', ''), 'authors': row.get('authors', []), 'year': str(row.get('year', '') or ''), 'journal': row.get('journal', ''), 'doi': doi, 'pmid': pmid, 'abstractNote': row.get('abstract_short', '')}})
    return command

def sync_writeback_queue(paths: dict[str, Path], candidate_map: dict[str, dict]) -> tuple[list[dict], int]:
    existing_rows = read_jsonl(paths['queue'])
    existing_by_candidate = {str(row.get('source_candidate_id', '') or '').strip(): dict(row) for row in existing_rows if str(row.get('source_candidate_id', '') or '').strip()}
    queue_rows: list[dict] = []
    queued_candidates: set[str] = set()
    created = 0
    for candidate_id, row in candidate_map.items():
        decision = canonicalize_decision(row.get('decision', ''))
        if decision != '纳入':
            continue
        if str(row.get('import_status', '') or '').strip() == 'imported':
            continue
        candidate_copy = dict(row)
        candidate_copy['final_collection'] = compute_final_collection(candidate_copy)
        final_collection = str(candidate_copy.get('final_collection', '') or '').strip()
        if not final_collection:
            candidate_copy['import_status'] = 'needs_collection_resolution'
            candidate_map[candidate_id] = candidate_copy
            continue
        command = writeback_command_for_candidate(candidate_copy)
        if not command:
            candidate_copy['import_status'] = 'blocked'
            candidate_map[candidate_id] = candidate_copy
            continue
        existing = existing_by_candidate.get(candidate_id)
        if existing and str(existing.get('status', '') or '').strip() in {'queued', 'running', 'processed'}:
            merged = dict(existing)
            merged['target_collection'] = command['target_collection']
            merged['target_domain'] = command.get('target_domain', merged.get('target_domain', ''))
            if merged.get('status') != 'processed':
                merged['requested_at'] = command['requested_at']
            queue_rows.append(merged)
        else:
            queue_rows.append(command)
            created += 1
        candidate_copy['import_status'] = 'queued_for_writeback'
        candidate_map[candidate_id] = candidate_copy
        queued_candidates.add(candidate_id)
    for row in existing_rows:
        candidate_id = str(row.get('source_candidate_id', '') or '').strip()
        status = str(row.get('status', '') or '').strip()
        if candidate_id in queued_candidates:
            continue
        if status == 'processed':
            queue_rows.append(row)
    write_jsonl(paths['queue'], queue_rows)
    return (queue_rows, created)

def load_bridge_config(paths: dict[str, Path]) -> dict:
    config_path = paths['bridge_config']
    if not config_path.exists():
        sample = read_json(paths['bridge_config_sample'])
        write_json(config_path, sample)
    return read_json(config_path)

def apply_writeback_log(paths: dict[str, Path], candidate_map: dict[str, dict]) -> int:
    log_rows = read_jsonl(paths['log'])
    changed = 0
    latest_by_candidate: dict[str, dict] = {}
    for row in log_rows:
        candidate_id = str(row.get('source_candidate_id', '') or '').strip()
        if candidate_id:
            latest_by_candidate[candidate_id] = row
    for candidate_id, log_row in latest_by_candidate.items():
        candidate = dict(candidate_map.get(candidate_id, {}))
        if not candidate:
            continue
        status = str(log_row.get('status', '') or '').strip()
        if status == 'success':
            candidate['import_status'] = 'imported'
            candidate['zotero_key'] = str(log_row.get('zotero_key', '') or '').strip()
            changed += 1
        elif status == 'error':
            candidate['import_status'] = 'writeback_error'
            changed += 1
        candidate_map[candidate_id] = candidate
    return changed

def invoke_native_bridge(paths: dict[str, Path], max_commands: int=5) -> dict:
    config = load_bridge_config(paths)
    base_url = str(config.get('server_base_url', 'http://127.0.0.1:23119')).rstrip('/')
    endpoint = str(config.get('process_endpoint', '/literaturePipeline/processQueue'))
    payload = {'queuePath': str(paths['queue']).replace('\\', '/'), 'logPath': str(paths['log']).replace('\\', '/'), 'configPath': str(paths['bridge_config']).replace('\\', '/'), 'maxCommands': max_commands}
    response = requests.post(f'{base_url}{endpoint}', json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()
    if not result.get('ok', False):
        raise RuntimeError(result.get('error', 'Native bridge returned non-ok result'))
    return result

def normalize_candidate_title(text: str) -> str:
    return re.sub('\\s+', ' ', str(text or '').strip().lower())

def candidate_identity_keys(row: dict) -> dict[str, str]:
    doi = str(row.get('doi', '') or '').strip().lower()
    pmid = str(row.get('pmid', '') or '').strip()
    title = normalize_candidate_title(row.get('title', ''))
    return {'doi': doi, 'pmid': pmid, 'title': title}

def candidate_id_from_payload(row: dict) -> str:
    source = str(row.get('source', '') or 'candidate').strip().lower()
    doi = re.sub('[^a-z0-9]+', '-', str(row.get('doi', '') or '').strip().lower()).strip('-')
    pmid = re.sub('[^0-9]+', '', str(row.get('pmid', '') or '').strip())
    fallback = re.sub('[^a-z0-9]+', '-', normalize_candidate_title(row.get('title', ''))).strip('-')[:80]
    suffix = doi or pmid or fallback or datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    return f'{source}-{suffix}'

def _normalize_candidate_value(value):
    if value is None:
        return ''
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return str(value).strip()

def _authors_from_pubmed(value) -> list[str] | str:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return str(value or '').strip()

def _authors_from_openalex(value) -> list[str]:
    authors = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                author = item.get('author') or {}
                name = author.get('display_name') or item.get('display_name') or ''
                if name:
                    authors.append(str(name).strip())
            elif str(item).strip():
                authors.append(str(item).strip())
    return authors

def _abstract_from_openalex(inverted_index) -> str:
    if not isinstance(inverted_index, dict):
        return ''
    tokens: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            try:
                tokens.append((int(pos), str(word)))
            except Exception:
                continue
    if not tokens:
        return ''
    tokens.sort(key=lambda item: item[0])
    return ' '.join((word for _, word in tokens))

def _authors_from_arxiv(value) -> list[str]:
    authors = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                name = item.get('name', '') or item.get('author', '')
                if name:
                    authors.append(str(name).strip())
            elif str(item).strip():
                authors.append(str(item).strip())
    return authors

def _authors_from_scholar(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split('\\s*,\\s*|\\s+and\\s+', value)
        return [part.strip() for part in parts if part.strip()]
    return []

def adapt_pubmed_candidate(row: dict) -> dict:
    payload = dict(row.get('payload') or {})
    adapted = {'candidate_id': row.get('candidate_id') or f"pubmed-{payload.get('pmid') or payload.get('PMID') or ''}", 'domain': row.get('domain', ''), 'title': payload.get('title', ''), 'authors': _authors_from_pubmed(payload.get('authors', [])), 'year': payload.get('year', ''), 'journal': payload.get('journal', ''), 'doi': payload.get('doi', ''), 'pmid': payload.get('pmid') or payload.get('PMID', ''), 'source': row.get('source', '') or 'pubmed_search', 'requester_skill': row.get('requester_skill', ''), 'request_context': row.get('request_context', ''), 'abstract_short': payload.get('abstract', '') or payload.get('abstract_short', ''), 'decision': row.get('decision', ''), 'recommended_collection': row.get('recommended_collection', ''), 'recommend_confidence': row.get('recommend_confidence', ''), 'recommend_reason': row.get('recommend_reason', ''), 'user_collection': row.get('user_collection', ''), 'final_collection': row.get('final_collection', ''), 'duplicate_hint': row.get('duplicate_hint', ''), 'import_status': row.get('import_status', ''), 'note': row.get('note', ''), 'candidate_source_type': row.get('candidate_source_type', '') or 'external_search', 'source_context': row.get('source_context', ''), 'task_relevance_reason': row.get('task_relevance_reason', '')}
    return adapted

def adapt_openalex_candidate(row: dict) -> dict:
    payload = dict(row.get('payload') or {})
    primary_location = payload.get('primary_location') or {}
    source_info = primary_location.get('source') or {}
    openalex_id = str(payload.get('id', '') or '').rstrip('/').split('/')[-1]
    adapted = {'candidate_id': row.get('candidate_id') or f'openalex-{openalex_id}', 'domain': row.get('domain', ''), 'title': payload.get('display_name', '') or payload.get('title', ''), 'authors': _authors_from_openalex(payload.get('authorships', [])), 'year': payload.get('publication_year', '') or payload.get('year', ''), 'journal': source_info.get('display_name', '') or payload.get('journal', ''), 'doi': str(payload.get('doi', '') or '').replace('https://doi.org/', ''), 'pmid': '', 'source': row.get('source', '') or 'openalex_search', 'requester_skill': row.get('requester_skill', ''), 'request_context': row.get('request_context', ''), 'abstract_short': _abstract_from_openalex(payload.get('abstract_inverted_index')), 'decision': row.get('decision', ''), 'recommended_collection': row.get('recommended_collection', ''), 'recommend_confidence': row.get('recommend_confidence', ''), 'recommend_reason': row.get('recommend_reason', ''), 'user_collection': row.get('user_collection', ''), 'final_collection': row.get('final_collection', ''), 'duplicate_hint': row.get('duplicate_hint', ''), 'import_status': row.get('import_status', ''), 'note': row.get('note', ''), 'candidate_source_type': row.get('candidate_source_type', '') or 'external_search', 'source_context': row.get('source_context', ''), 'task_relevance_reason': row.get('task_relevance_reason', '')}
    return adapted

def adapt_arxiv_candidate(row: dict) -> dict:
    payload = dict(row.get('payload') or {})
    arxiv_id = str(payload.get('id', '') or payload.get('entry_id', '')).rstrip('/').split('/')[-1]
    adapted = {'candidate_id': row.get('candidate_id') or f'arxiv-{arxiv_id}', 'domain': row.get('domain', ''), 'title': payload.get('title', ''), 'authors': _authors_from_arxiv(payload.get('authors', [])), 'year': str(payload.get('published', '') or '')[:4], 'journal': payload.get('journal_ref', '') or 'arXiv', 'doi': payload.get('doi', ''), 'pmid': '', 'source': row.get('source', '') or 'arxiv_search', 'requester_skill': row.get('requester_skill', ''), 'request_context': row.get('request_context', ''), 'abstract_short': payload.get('summary', '') or payload.get('abstract', ''), 'decision': row.get('decision', ''), 'recommended_collection': row.get('recommended_collection', ''), 'recommend_confidence': row.get('recommend_confidence', ''), 'recommend_reason': row.get('recommend_reason', ''), 'user_collection': row.get('user_collection', ''), 'final_collection': row.get('final_collection', ''), 'duplicate_hint': row.get('duplicate_hint', ''), 'import_status': row.get('import_status', ''), 'note': row.get('note', ''), 'candidate_source_type': row.get('candidate_source_type', '') or 'external_search', 'source_context': row.get('source_context', ''), 'task_relevance_reason': row.get('task_relevance_reason', '')}
    return adapted

def adapt_google_scholar_candidate(row: dict) -> dict:
    payload = dict(row.get('payload') or {})
    adapted = {'candidate_id': row.get('candidate_id') or f"google-scholar-{re.sub('[^a-z0-9]+', '-', normalize_candidate_title(payload.get('title', ''))).strip('-')[:80]}", 'domain': row.get('domain', ''), 'title': payload.get('title', ''), 'authors': _authors_from_scholar(payload.get('authors', [])), 'year': str(payload.get('year', '') or ''), 'journal': payload.get('journal', '') or payload.get('venue', ''), 'doi': payload.get('doi', ''), 'pmid': '', 'source': row.get('source', '') or 'google_scholar_search', 'requester_skill': row.get('requester_skill', ''), 'request_context': row.get('request_context', ''), 'abstract_short': payload.get('abstract', '') or payload.get('snippet', ''), 'decision': row.get('decision', ''), 'recommended_collection': row.get('recommended_collection', ''), 'recommend_confidence': row.get('recommend_confidence', ''), 'recommend_reason': row.get('recommend_reason', ''), 'user_collection': row.get('user_collection', ''), 'final_collection': row.get('final_collection', ''), 'duplicate_hint': row.get('duplicate_hint', ''), 'import_status': row.get('import_status', ''), 'note': row.get('note', ''), 'candidate_source_type': row.get('candidate_source_type', '') or 'external_search', 'source_context': row.get('source_context', ''), 'task_relevance_reason': row.get('task_relevance_reason', '')}
    return adapted

def adapt_candidate_event(row: dict) -> dict:
    adapter = str(row.get('adapter', '') or '').strip()
    if adapter == 'pubmed_search':
        return adapt_pubmed_candidate(row)
    if adapter == 'openalex_search':
        return adapt_openalex_candidate(row)
    if adapter == 'arxiv_search':
        return adapt_arxiv_candidate(row)
    if adapter == 'google_scholar_search':
        return adapt_google_scholar_candidate(row)
    return dict(row)

def default_user_agent() -> str:
    return 'ResearchLiteraturePipeline/1.0 (+local-vault)'

def build_search_event(base_task: dict, source: str, payload: dict) -> dict:
    return {'adapter': source, 'payload': payload, 'source': source, 'requester_skill': base_task.get('requester_skill', ''), 'request_context': base_task.get('request_context', ''), 'domain': base_task.get('domain', ''), 'recommended_collection': base_task.get('recommended_collection', ''), 'recommend_confidence': base_task.get('recommend_confidence', ''), 'recommend_reason': base_task.get('recommend_reason', '') or f'{source} 检索命中', 'candidate_source_type': base_task.get('candidate_source_type', '') or 'external_search', 'task_relevance_reason': base_task.get('task_relevance_reason', ''), 'note': base_task.get('note', '')}

def _pubmed_abstract_and_doi_map(xml_text: str) -> dict[str, dict]:
    root = ET.fromstring(xml_text)
    result = {}
    for article in root.findall('.//PubmedArticle'):
        pmid = (article.findtext('.//MedlineCitation/PMID') or '').strip()
        if not pmid:
            continue
        abstract_parts = []
        for node in article.findall('.//Abstract/AbstractText'):
            label = (node.attrib.get('Label') or '').strip()
            text = ' '.join(''.join(node.itertext()).split())
            if not text:
                continue
            abstract_parts.append(f'{label}: {text}' if label else text)
        doi = ''
        for id_node in article.findall('.//PubmedData/ArticleIdList/ArticleId'):
            if (id_node.attrib.get('IdType') or '').lower() == 'doi':
                doi = ''.join(id_node.itertext()).strip()
                if doi:
                    break
        if not doi:
            for id_node in article.findall('.//ELocationID'):
                if (id_node.attrib.get('EIdType') or '').lower() == 'doi':
                    doi = ''.join(id_node.itertext()).strip()
                    if doi:
                        break
        result[pmid] = {'abstract': '\n'.join(abstract_parts).strip(), 'doi': doi}
    return result

def search_pubmed(task: dict, limit: int) -> tuple[list[dict], dict]:
    query = str(task.get('query', '') or '').strip()
    if not query:
        return ([], {'count': 0, 'ids': []})
    base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'
    headers = {'User-Agent': os.environ.get('LIT_PIPELINE_USER_AGENT', default_user_agent())}
    common_params = {}
    email = os.environ.get('NCBI_EMAIL', '').strip()
    api_key = os.environ.get('NCBI_API_KEY', '').strip()
    if email:
        common_params['email'] = email
    if api_key:
        common_params['api_key'] = api_key
    esearch = requests.get(f'{base_url}/esearch.fcgi', params={'db': 'pubmed', 'retmode': 'json', 'sort': 'relevance', 'term': query, 'retmax': limit, **common_params}, headers=headers, timeout=60)
    esearch.raise_for_status()
    search_payload = esearch.json().get('esearchresult', {})
    ids = [str(item).strip() for item in search_payload.get('idlist', []) if str(item).strip()]
    if not ids:
        return ([], {'count': 0, 'ids': []})
    id_text = ','.join(ids)
    esummary = requests.get(f'{base_url}/esummary.fcgi', params={'db': 'pubmed', 'retmode': 'json', 'id': id_text, **common_params}, headers=headers, timeout=60)
    esummary.raise_for_status()
    summary_payload = esummary.json().get('result', {})
    efetch = requests.get(f'{base_url}/efetch.fcgi', params={'db': 'pubmed', 'retmode': 'xml', 'id': id_text, **common_params}, headers=headers, timeout=90)
    efetch.raise_for_status()
    abstract_map = _pubmed_abstract_and_doi_map(efetch.text)
    rows = []
    for pmid in ids:
        item = summary_payload.get(pmid, {}) or {}
        title = html.unescape(str(item.get('title', '') or '')).strip()
        if not title:
            continue
        article_ids = item.get('articleids', []) or []
        doi = ''
        for article_id in article_ids:
            if str(article_id.get('idtype', '')).lower() == 'doi':
                doi = str(article_id.get('value', '')).strip()
                if doi:
                    break
        if not doi:
            doi = abstract_map.get(pmid, {}).get('doi', '')
        rows.append({'pmid': pmid, 'title': title, 'authors': [author.get('name', '') for author in item.get('authors') or [] if author.get('name')], 'year': _extract_year(str(item.get('pubdate', '') or '')), 'journal': item.get('fulljournalname', '') or item.get('source', ''), 'doi': doi, 'abstract': abstract_map.get(pmid, {}).get('abstract', '')})
    return (rows, {'count': len(rows), 'ids': ids})

def search_openalex(task: dict, limit: int) -> tuple[list[dict], dict]:
    query = str(task.get('query', '') or '').strip()
    if not query:
        return ([], {'count': 0})
    headers = {'User-Agent': os.environ.get('LIT_PIPELINE_USER_AGENT', default_user_agent())}
    params = {'search': query, 'per-page': limit}
    api_key = os.environ.get('OPENALEX_API_KEY', '').strip()
    if api_key:
        params['api_key'] = api_key
    mailto = os.environ.get('OPENALEX_MAILTO', '').strip()
    if mailto:
        params['mailto'] = mailto
    response = requests.get('https://api.openalex.org/works', params=params, headers=headers, timeout=60)
    response.raise_for_status()
    payload = response.json()
    results = payload.get('results', []) or []
    return (results, {'count': len(results), 'meta': payload.get('meta', {})})

def search_arxiv(task: dict, limit: int) -> tuple[list[dict], dict]:
    query = str(task.get('query', '') or '').strip()
    if not query:
        return ([], {'count': 0})
    encoded_query = urllib.parse.quote(f'all:{query}')
    url = f'https://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results={limit}&sortBy=relevance&sortOrder=descending'
    headers = {'User-Agent': os.environ.get('LIT_PIPELINE_USER_AGENT', default_user_agent())}
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
    root = ET.fromstring(response.text)
    entries = []
    for entry in root.findall('atom:entry', ns):
        entries.append({'id': (entry.findtext('atom:id', default='', namespaces=ns) or '').strip(), 'title': ' '.join((entry.findtext('atom:title', default='', namespaces=ns) or '').split()), 'summary': ' '.join((entry.findtext('atom:summary', default='', namespaces=ns) or '').split()), 'published': (entry.findtext('atom:published', default='', namespaces=ns) or '').strip(), 'authors': [{'name': (node.findtext('atom:name', default='', namespaces=ns) or '').strip()} for node in entry.findall('atom:author', ns)], 'doi': (entry.findtext('arxiv:doi', default='', namespaces=ns) or '').strip(), 'journal_ref': (entry.findtext('arxiv:journal_ref', default='', namespaces=ns) or '').strip()})
    return (entries, {'count': len(entries)})

def _coerce_source_name(value: str) -> str:
    text = str(value or '').strip().lower()
    aliases = {'pubmed': 'pubmed_search', 'pubmed_search': 'pubmed_search', 'openalex': 'openalex_search', 'openalex_search': 'openalex_search', 'arxiv': 'arxiv_search', 'arxiv_search': 'arxiv_search'}
    return aliases.get(text, text)

def run_search_command(vault: Path, args) -> int:
    paths = pipeline_paths(vault)
    paths['search_tasks'].mkdir(parents=True, exist_ok=True)
    task_id = f"search-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    sources = args.sources or ['pubmed_search', 'openalex_search', 'arxiv_search']
    task = {'task_id': task_id, 'query': args.query, 'domain': args.domain, 'recommended_collection': args.recommended_collection or '', 'requester_skill': args.requester_skill or '', 'request_context': args.request_context or '', 'sources': sources, 'limit': args.limit, 'recommend_reason': args.recommend_reason or '围绕检索主题补充候选文献', 'candidate_source_type': 'external_search'}
    task_path = paths['search_tasks'] / f'{task_id}.json'
    write_json(task_path, task)
    print(f'search: task written -> {task_path}')
    code = run_search_sources(vault)
    if code:
        return code
    if not args.skip_ingest:
        return run_ingest_candidates(vault)
    return 0

def normalize_candidate_payload(row: dict) -> dict:
    normalized = {key: _normalize_candidate_value(value) for key, value in adapt_candidate_event(row).items()}
    normalized['candidate_id'] = str(normalized.get('candidate_id', '') or '').strip() or candidate_id_from_payload(normalized)
    normalized['title'] = str(normalized.get('title', '') or '').strip()
    normalized['domain'] = str(normalized.get('domain', '') or '').strip()
    normalized['source'] = str(normalized.get('source', '') or '').strip() or 'candidate_ingest'
    normalized['candidate_source_type'] = str(normalized.get('candidate_source_type', '') or '').strip() or normalized['source']
    normalized['decision'] = canonicalize_decision(normalized.get('decision', ''))
    normalized['import_status'] = str(normalized.get('import_status', '') or '').strip() or 'pending'
    normalized['recommend_confidence'] = str(normalized.get('recommend_confidence', '') or '').strip() or '0'
    normalized['status'] = 'candidate'
    return normalized

def merge_candidate_record(existing: dict | None, incoming: dict) -> dict:
    merged = dict(existing or {})
    preserve_if_existing = {'decision', 'user_collection', 'note', 'import_status'}
    for key, value in incoming.items():
        if existing and key in preserve_if_existing:
            current = merged.get(key, '')
            if str(current).strip():
                continue
        merged[key] = value
    merged['decision'] = canonicalize_decision(merged.get('decision', ''))
    merged['final_collection'] = compute_final_collection(merged)
    return merged

def resolve_existing_candidate(candidate_map: dict[str, dict], incoming: dict) -> tuple[str | None, dict | None]:
    candidate_id = incoming.get('candidate_id', '')
    if candidate_id and candidate_id in candidate_map:
        return (candidate_id, candidate_map[candidate_id])
    incoming_keys = candidate_identity_keys(incoming)
    for existing_id, existing in candidate_map.items():
        existing_keys = candidate_identity_keys(existing)
        if incoming_keys['doi'] and incoming_keys['doi'] == existing_keys['doi']:
            return (existing_id, existing)
        if incoming_keys['pmid'] and incoming_keys['pmid'] == existing_keys['pmid']:
            return (existing_id, existing)
        if incoming_keys['title'] and incoming_keys['title'] == existing_keys['title']:
            return (existing_id, existing)
    return (None, None)

def _harvest_csv_paths(paths: dict[str, Path]) -> list[Path]:
    root = paths['harvest_root']
    if not root.exists():
        return []
    return sorted(root.rglob('*-05-reference-harvest-candidates.csv'))

def _normalize_harvest_value(value: str) -> str:
    text = str(value or '').strip()
    if text == '<inherit-from-task-context>':
        return ''
    return text

def _normalize_harvest_row(row: dict[str, str]) -> dict:
    normalized = normalize_candidate_payload({key: _normalize_harvest_value(value) for key, value in row.items()})
    normalized['source'] = normalized.get('source', '') or 'reference_harvest'
    normalized['candidate_source_type'] = normalized.get('candidate_source_type', '') or 'reference_harvest'
    return normalized

def _merge_harvest_candidate(existing: dict | None, incoming: dict) -> dict:
    return merge_candidate_record(existing, incoming)

def next_key(domain: str, export_rows: list[dict]) -> str:
    prefix = 'ORTHO' if domain == '骨科' else 'SPORT'
    existing = [row.get('key', '') for row in export_rows]
    max_num = 0
    for key in existing:
        if key.startswith(prefix):
            suffix = key[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return f'{prefix}{max_num + 1:03d}'

def frontmatter_note(entry: dict, existing_text: str='') -> str:
    deep_reading_path = entry.get('deep_reading_md_path', '')
    preserved_deep = extract_preserved_deep_reading(existing_text)
    lines = ['---', f"title: {yaml_quote(entry['title'])}", f"year: {entry.get('year', '')}", 'type: article', f"journal: {yaml_quote(entry.get('journal', ''))}", 'authors:']
    for author in entry.get('authors', []):
        lines.append(f'  - {yaml_quote(author)}')
    lines.extend([f"collection_path: {yaml_quote(entry.get('collection_path', ''))}", f"domain: {yaml_quote(entry.get('domain', ''))}", f"zotero_key: {yaml_quote(entry.get('zotero_key', ''))}", f"doi: {yaml_quote(entry.get('doi', ''))}", f"pmid: {yaml_quote(entry.get('pmid', ''))}"])
    lines.extend(yaml_list('collection_group', entry.get('collection_group', [])))
    lines.extend(yaml_list('collections', entry.get('collections', [])))
    lines.extend(yaml_list('collection_tags', entry.get('collection_tags', [])))
    lines.extend(yaml_block(entry.get('abstract', '')))
    lines.extend([f"has_pdf: {('true' if entry.get('has_pdf') else 'false')}", f"ocr_status: {yaml_quote(entry.get('ocr_status', 'pending'))}", f"ocr_job_id: {yaml_quote(entry.get('ocr_job_id', ''))}", f"ocr_md_path: {yaml_quote(entry.get('ocr_md_path', ''))}", f"ocr_json_path: {yaml_quote(entry.get('ocr_json_path', ''))}", f"deep_reading_status: {yaml_quote(entry.get('deep_reading_status', 'pending'))}", f'deep_reading_md_path: {yaml_quote(deep_reading_path)}', f"pdf_path: {yaml_quote(entry.get('pdf_path', ''))}", 'tags:', '  - 文献阅读', f"  - {entry.get('domain', '')}", '---', '', f"# {entry['title']}", '', '## 📄 文献基本信息', '', f"- Zotero Key: `{entry.get('zotero_key', '')}`", f"- Collection: `{entry.get('collection_path', '')}`", f"- 作者：{', '.join(entry.get('authors', []))}", f"- PDF: {('已检测' if entry.get('has_pdf') else '未检测到')}", f"- OCR: {entry.get('ocr_status', 'pending')}", f"- 精读: {entry.get('deep_reading_status', 'pending')}", '', '## 摘要', '', entry.get('abstract', '') or '暂无摘要', '', '## 💡 文献内容总结', '', '- 由 index-refresh worker 自动生成的正式文献卡片。', '- 精读笔记（Deep Reading）仅由 /LD-deep 命令维护；index-refresh 只保留已有内容，不自动生成。', '- 如需精读，请在 Base 中勾选 analyze，OCR 完成后运行 /LD-deep <zotero_key>。', ''])
    if preserved_deep:
        lines.extend(['', preserved_deep, ''])
    return '\n'.join(lines)

def analyze_selected_keys(paths: dict[str, Path]) -> set[str]:
    return {key for key, row in load_control_actions(paths).items() if row.get('analyze')}

def run_index_refresh(vault: Path) -> int:
    paths = pipeline_paths(vault)
    config = read_json(paths['config'])
    domain_lookup = {entry['export_file']: entry['domain'] for entry in config['domains']}
    exports = {}
    for export_path in sorted(paths['exports'].glob('*.json')):
        domain = domain_lookup.get(export_path.name, export_path.stem)
        export_rows = load_export_rows(export_path)
        exports[domain] = {row['key']: row for row in export_rows}
    selected_keys = None
    index_rows = []
    lit_root = paths['resources'] / 'Literature'
    for export_path in sorted(paths['exports'].glob('*.json')):
        domain = domain_lookup.get(export_path.name, export_path.stem)
        export_rows = load_export_rows(export_path)
        for item in export_rows:
            key = item['key']
            if selected_keys is not None and key not in selected_keys:
                continue
            collection_meta = collection_fields(item.get('collections', []))
            pdf_attachments = [a for a in item.get('attachments', []) if a.get('contentType') == 'application/pdf']
            meta_path = paths['ocr'] / key / 'meta.json'
            meta = read_json(meta_path) if meta_path.exists() else {}
            if meta:
                validated_ocr_status, validated_error = validate_ocr_meta(paths, meta)
                meta['ocr_status'] = validated_ocr_status
                if validated_error:
                    meta['error'] = validated_error
                    write_json(meta_path, meta)
            title_slug = slugify_filename(item['title'])
            note_path = lit_root / domain / f'{key} - {title_slug}.md'
            if note_path.parent.exists():
                for stale_note in note_path.parent.glob(f'{key} - *.md'):
                    if stale_note != note_path:
                        stale_note.unlink()
            entry = {'zotero_key': key, 'domain': domain, 'title': item['title'], 'authors': item.get('authors', []), 'abstract': item.get('abstract', ''), 'journal': item.get('journal', ''), 'year': item.get('year', ''), 'doi': item.get('doi', ''), 'pmid': item.get('pmid', ''), 'collection_path': ' | '.join(item.get('collections', [])), 'collections': collection_meta.get('collections', []), 'collection_tags': collection_meta.get('collection_tags', []), 'collection_group': collection_meta.get('collection_group', []), 'has_pdf': bool(pdf_attachments), 'pdf_path': obsidian_wikilink_for_pdf(vault, pdf_attachments[0]['path']) if pdf_attachments else '', 'ocr_status': meta.get('ocr_status', 'pending'), 'ocr_job_id': meta.get('ocr_job_id', ''), 'ocr_md_path': obsidian_wikilink_for_path(vault, meta.get('markdown_path', '')), 'ocr_json_path': meta.get('json_path', ''), 'deep_reading_status': 'done' if note_path.exists() and has_deep_reading_content(note_path.read_text(encoding='utf-8')) else 'pending', 'note_path': str(note_path.relative_to(vault)).replace('\\', '/'), 'deep_reading_md_path': str(note_path.relative_to(vault)).replace('\\', '/') if note_path.exists() and has_deep_reading_content(note_path.read_text(encoding='utf-8')) else ''}
            note_path.parent.mkdir(parents=True, exist_ok=True)
            existing_text = note_path.read_text(encoding='utf-8') if note_path.exists() else ''
            note_path.write_text(frontmatter_note(entry, existing_text), encoding='utf-8')
            index_rows.append(entry)
    write_json(paths['index'], index_rows)
    print(f'index-refresh: wrote {len(index_rows)} index rows')
    control_records_dir = paths['resources'] / 'LiteratureControl' / 'library-records'
    if control_records_dir.exists():
        for domain_dir in control_records_dir.iterdir():
            if not domain_dir.is_dir():
                continue
            domain = domain_dir.name
            domain_export_keys = set(exports.get(domain, {}).keys())
            records_by_title = {}
            records_info = {}
            for record_file in domain_dir.glob('*.md'):
                try:
                    content = record_file.read_text(encoding='utf-8')
                    title_match = re.search('^title:\\s*["\\\']?(.+)["\\\']?\\s*$', content, re.MULTILINE)
                    title = title_match.group(1) if title_match else ''
                    has_pdf = 'has_pdf: true' in content
                    normalized = re.sub('[^a-z0-9]', '', title.lower())[:20]
                    key = record_file.stem
                    records_info[key] = {'file': record_file, 'title': title, 'has_pdf': has_pdf, 'normalized': normalized}
                    if normalized not in records_by_title:
                        records_by_title[normalized] = []
                    records_by_title[normalized].append(key)
                except Exception:
                    continue
            to_delete = []
            for normalized, keys in records_by_title.items():
                keys_in_export = [k for k in keys if k in domain_export_keys]
                keys_not_in_export = [k for k in keys if k not in domain_export_keys]
                if keys_in_export and keys_not_in_export:
                    for k in keys_not_in_export:
                        if not records_info[k]['has_pdf']:
                            to_delete.append(k)
            deleted_count = 0
            for key in to_delete:
                try:
                    records_info[key]['file'].unlink()
                    deleted_count += 1
                except Exception:
                    pass
            if deleted_count > 0:
                print(f'index-refresh: cleaned {deleted_count} orphaned records in {domain}')
    return 0

def ensure_ocr_meta(vault: Path, row: dict) -> dict:
    paths = pipeline_paths(vault)
    key = row['zotero_key']
    meta_path = paths['ocr'] / key / 'meta.json'
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta = read_json(meta_path) if meta_path.exists() else {}
    meta.setdefault('zotero_key', key)
    meta.setdefault('source_pdf', row.get('pdf_path', ''))
    meta.setdefault('ocr_provider', 'PaddleOCR-VL-1.5')
    meta.setdefault('mode', 'async')
    meta.setdefault('ocr_status', 'pending')
    meta.setdefault('ocr_job_id', '')
    meta.setdefault('ocr_started_at', '')
    meta.setdefault('ocr_finished_at', '')
    meta.setdefault('page_count', 0)
    meta.setdefault('markdown_path', '')
    meta.setdefault('json_path', '')
    meta.setdefault('assets_path', f'99_System/LiteraturePipeline/ocr/{key}/images')
    meta.setdefault('fulltext_md_path', '')
    meta.setdefault('error', '')
    return meta

def validate_ocr_meta(paths: dict[str, Path], meta: dict) -> tuple[str, str]:
    status = str(meta.get('ocr_status', 'pending') or 'pending').strip().lower()
    if status != 'done':
        return (status, str(meta.get('error', '') or ''))
    key = str(meta.get('zotero_key', '') or '').strip()
    if not key:
        return ('done_incomplete', 'Missing zotero_key in OCR meta')
    ocr_root = paths['ocr'] / key
    fulltext_path = ocr_root / 'fulltext.md'
    json_path = ocr_root / 'json' / 'result.json'
    page_count = int(meta.get('page_count', 0) or 0)
    if not fulltext_path.exists():
        return ('done_incomplete', 'OCR fulltext.md missing')
    if not json_path.exists():
        return ('done_incomplete', 'OCR result.json missing')
    fulltext_size = fulltext_path.stat().st_size
    json_size = json_path.stat().st_size
    if page_count < 1:
        return ('done_incomplete', 'OCR page_count invalid')
    if fulltext_size < 500:
        return ('done_incomplete', 'OCR fulltext.md too small')
    if json_size < 1000:
        return ('done_incomplete', 'OCR result.json too small')
    try:
        rendered_pages = fulltext_path.read_text(encoding='utf-8').count('<!-- page ')
    except Exception:
        rendered_pages = 0
    if rendered_pages < 1:
        return ('done_incomplete', 'OCR fulltext has no rendered pages')
    if rendered_pages != page_count:
        return ('done_incomplete', f'OCR page marker mismatch: meta={page_count}, rendered={rendered_pages}')
    return ('done', '')

def read_ocr_queue(paths: dict[str, Path]) -> list[dict]:
    queue_path = paths['ocr_queue']
    if not queue_path.exists():
        return []
    try:
        data = read_json(queue_path)
        return data if isinstance(data, list) else []
    except JSONDecodeError:
        text = queue_path.read_text(encoding='utf-8')
        recovered = []
        decoder = json.JSONDecoder()
        index = 0
        while True:
            match = re.search('\\{', text[index:])
            if not match:
                break
            start = index + match.start()
            try:
                obj, end = decoder.raw_decode(text, start)
            except JSONDecodeError:
                index = start + 1
                continue
            if isinstance(obj, dict) and obj.get('zotero_key'):
                recovered.append(obj)
            index = end
        deduped = []
        seen = set()
        for row in recovered:
            key = row.get('zotero_key')
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        write_json(queue_path, deduped)
        return deduped

def write_ocr_queue(paths: dict[str, Path], queue_rows: list[dict]) -> None:
    deduped = []
    seen = set()
    for row in queue_rows:
        key = row.get('zotero_key')
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    write_json(paths['ocr_queue'], deduped)

def sync_ocr_queue(paths: dict[str, Path], target_rows: list[dict]) -> list[dict]:
    existing_queue = read_ocr_queue(paths)
    target_map = {row['zotero_key']: row for row in target_rows}
    synced_queue: list[dict] = []
    queued_keys: set[str] = set()
    for row in existing_queue:
        key = row.get('zotero_key')
        if not key or key not in target_map:
            continue
        target = target_map[key]
        if not target.get('has_pdf'):
            continue
        meta_path = paths['ocr'] / key / 'meta.json'
        meta = read_json(meta_path) if meta_path.exists() else {}
        status = str(meta.get('ocr_status', 'pending') or 'pending').strip().lower()
        if status in {'done', 'blocked'}:
            continue
        synced = dict(row)
        synced['has_pdf'] = bool(target.get('has_pdf'))
        synced['pdf_path'] = target.get('pdf_path', '')
        synced['queue_status'] = status
        if not synced.get('queued_at'):
            synced['queued_at'] = datetime.now(timezone.utc).isoformat()
        synced_queue.append(synced)
        queued_keys.add(key)
    now = datetime.now(timezone.utc).isoformat()
    for row in target_rows:
        key = row['zotero_key']
        if key in queued_keys:
            continue
        if not row.get('has_pdf'):
            continue
        meta_path = paths['ocr'] / key / 'meta.json'
        meta = read_json(meta_path) if meta_path.exists() else {}
        status = str(meta.get('ocr_status', 'pending') or 'pending').strip().lower()
        if status in {'done', 'blocked'}:
            continue
        synced_queue.append({'zotero_key': key, 'has_pdf': bool(row.get('has_pdf')), 'pdf_path': row.get('pdf_path', ''), 'queued_at': now, 'queue_status': status})
    write_ocr_queue(paths, synced_queue)
    return synced_queue

def cleanup_blocked_ocr_dirs(paths: dict[str, Path]) -> None:
    for meta_path in paths['ocr'].glob('*/meta.json'):
        try:
            meta = read_json(meta_path)
        except Exception:
            continue
        status = str(meta.get('ocr_status', '') or '').strip().lower()
        key = str(meta.get('zotero_key', '') or '').strip()
        ocr_dir = meta_path.parent
        if status != 'blocked':
            continue
        has_payload = any((candidate.exists() for candidate in [ocr_dir / 'fulltext.md', ocr_dir / 'json' / 'result.json']))
        if has_payload:
            continue
        shutil.rmtree(ocr_dir, ignore_errors=True)

def normalize_obsidian_markdown(text: str) -> str:
    normalized = text.replace('\r\n', '\n')
    normalized = re.sub('[ \\t]+\\$', '$', normalized)
    normalized = re.sub('\\$[ \\t]+', '$', normalized)
    normalized = re.sub('\\$\\s+\\^', '$^', normalized)
    normalized = re.sub('\\^\\{\\s+', '^{', normalized)
    normalized = re.sub('\\s+\\}', '}', normalized)
    normalized = normalized.replace('$^{ID}$', '')
    normalized = re.sub('[ \\t]{2,}', ' ', normalized)
    normalized = re.sub('\\$\\^\\{([^}]*)\\\\dagger\\}\\$', lambda m: _superscript_to_equal_footnote(m.group(1)), normalized)
    normalized = re.sub('\\$\\^\\{([^}]*)†\\}\\$', lambda m: _superscript_to_equal_footnote(m.group(1)), normalized)
    normalized = re.sub('\\$\\^\\{([^}]*)\\*\\}\\$', lambda m: _superscript_to_correspondence_footnote(m.group(1)), normalized)
    normalized = re.sub('(?m)^\\*\\s*Correspondence:\\s*(.+)$', lambda match: f'[^correspondence]: {match.group(1).strip()}', normalized)
    normalized = re.sub('(?m)^Correspondence:\\s*(.+)$', lambda match: f'[^correspondence]: {match.group(1).strip()}', normalized)
    normalized = re.sub('(?m)^†\\s*(.+)$', lambda match: f'[^equal]: {match.group(1).strip()}', normalized)
    normalized = re.sub('([A-Za-z])(\\$[^$\\n]+\\$)', '\\1 \\2', normalized)
    normalized = re.sub('(\\$[^$\\n]+\\$)([A-Za-z])', '\\1 \\2', normalized)
    normalized = re.sub('\\n{3,}', '\n\n', normalized)
    return normalized.strip()

def _image_embed_for_obsidian(vault_rel: Path) -> str:
    return f"![[{str(vault_rel).replace(chr(92), '/')}]]"

def _superscript_to_equal_footnote(content: str) -> str:
    cleaned = re.sub('(,)?\\\\dagger', '', content).replace('†', '').strip(', ')
    if cleaned:
        return f'$^{{{cleaned}}}$[^equal]'
    return '[^equal]'

def _superscript_to_correspondence_footnote(content: str) -> str:
    cleaned = content.replace('*', '').strip(', ')
    if cleaned:
        return f'$^{{{cleaned}}}$[^correspondence]'
    return '[^correspondence]'

def ensure_page_image_cached(url: str, destination: Path) -> Path | None:
    if destination.exists():
        return destination
    if not url:
        return None
    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
    except requests.RequestException:
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return destination

def render_pdf_page_cached(pdf_doc, page_index: int, target_width: int, target_height: int, destination: Path) -> Path | None:
    if destination.exists():
        return destination
    if not pdf_doc or page_index < 1 or page_index > len(pdf_doc):
        return None
    try:
        page = pdf_doc[page_index - 1]
        rect = page.rect
        zoom_x = target_width / rect.width if target_width and rect.width else 2.0
        zoom_y = target_height / rect.height if target_height and rect.height else 2.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom_x, zoom_y), alpha=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(destination))
        return destination
    except Exception:
        return None

def crop_block_asset(page_image_path: Path, bbox: list[int], destination: Path) -> bool:
    if destination.exists():
        return True
    try:
        with Image.open(page_image_path) as img:
            x1, y1, x2, y2 = [max(0, int(v)) for v in bbox]
            if x2 <= x1 or y2 <= y1:
                return False
            crop = img.crop((x1, y1, x2, y2))
            destination.parent.mkdir(parents=True, exist_ok=True)
            crop.save(destination)
            return True
    except Exception:
        return False

def block_sort_key(block: dict) -> tuple[int, int, int, int]:
    bbox = block.get('block_bbox', [0, 0, 0, 0])
    return (int(bbox[1]), int(bbox[0]), int(bbox[3]), int(bbox[2]))

def clean_block_text(text: str) -> str:
    text = html.unescape(normalize_obsidian_markdown(text)).strip()
    text = re.sub('([a-z])and ([A-Z])', '\\1 and \\2', text)
    return text

def is_subfigure_label(text: str) -> bool:
    compact = re.sub('\\s+', ' ', text.strip().lower())
    return bool(re.fullmatch('(?:\\([a-z]\\)\\s*)+', compact) or re.fullmatch('[a-z]', compact) or re.fullmatch('[a-z]\\)', compact))

def is_affiliation_line(text: str) -> bool:
    compact = ' '.join(text.split())
    if re.match('^(?:\\$\\^\\{)?\\d+(?:[,\\d-]*)?(?:\\})?', compact):
        return True
    keywords = ('university', 'department', 'college', 'school', 'institute', 'hospital', 'center', 'centre', 'laboratory', 'lab', 'program', 'research')
    lower = compact.lower()
    return any((word in lower for word in keywords)) and len(compact) > 30

def is_frontmatter_noise_line(text: str) -> bool:
    compact = ' '.join(text.split())
    lower = compact.lower()
    if compact in {'Article', 'Review'}:
        return True
    prefixes = ('academic editor:', 'copyright:', 'licensee', 'this article is an open access article', "publisher's note:", 'check for updates')
    if lower.startswith(prefixes):
        return True
    if re.fullmatch('\\d+\\s+\\w{1,6}', compact):
        return True
    if len(compact) < 18 and re.search('\\d', compact):
        return True
    return False

def is_reference_tail_noise_line(text: str) -> bool:
    compact = clean_block_text(text)
    lower = compact.lower()
    if 'submit your next manuscript' in lower:
        return True
    patterns = ('^doi:\\s*10\\.', '^Cite this article as:', '^Submit your next manuscript', '^BioMed Central\\b', '^Convenient online submission$', '^Thorough peer review$', '^No space constraints', '^Immediate publication on acceptance$', '^Inclusion in PubMed, CAS, Scopus and Google Scholar$', '^Research which is freely available for redistribution$', '^[•\\-]\\s*(Convenient online submission|Thorough peer review|No space constraints|Immediate publication on acceptance|Inclusion in PubMed|Research which is freely available)')
    return any((re.match(pattern, compact, flags=re.IGNORECASE) for pattern in patterns))

def parse_reference_number(text: str) -> int | None:
    text = clean_block_text(text)
    m = re.match('^\\s*(\\d+)[\\.\\)]\\s*', text)
    if m:
        return int(m.group(1))
    m = re.match('^\\s*\\[(\\d+)\\][\\]\\.\\)\\s]*', text)
    if m:
        return int(m.group(1))
    return None

def sort_reference_blocks(blocks: list[dict]) -> list[dict]:
    numbered_count = sum((parse_reference_number(block.get('block_content', '')) is not None for block in blocks))
    if numbered_count >= max(3, len(blocks) // 2):
        return sorted(blocks, key=lambda block: (parse_reference_number(block.get('block_content', '')) is None, parse_reference_number(block.get('block_content', '')) or 10 ** 9, block_sort_key(block)))
    return sorted(blocks, key=lambda block: (block.get('block_bbox', [0, 0, 0, 0])[0], block.get('block_bbox', [0, 0, 0, 0])[1]))

def assign_reference_continuation(continuation_block: dict, reference_blocks: list[dict]) -> int | None:
    bbox = continuation_block.get('block_bbox', [0, 0, 0, 0])
    x1, y1, x2, _ = bbox
    candidates = []
    for index, ref_block in enumerate(reference_blocks):
        rb = ref_block.get('block_bbox', [0, 0, 0, 0])
        rx1, ry1, rx2, ry2 = rb
        horizontal_overlap = min(x2, rx2) - max(x1, rx1)
        same_column = horizontal_overlap > 0 or abs((x1 + x2) / 2 - (rx1 + rx2) / 2) < 180
        if not same_column or ry1 > y1:
            continue
        candidates.append((index, ry2, abs((x1 + x2) / 2 - (rx1 + rx2) / 2)))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[1], item[2]))
    return candidates[0][0]

def clean_author_line(text: str) -> str:
    text = clean_block_text(text)
    text = text.replace('$^{ID}$', '')
    text = re.sub('\\s*,\\s*', ', ', text)
    text = re.sub('\\s+and\\s+', ' and ', text)
    text = re.sub('([a-z])and ([A-Z])', '\\1 and \\2', text)
    return text

def handle_first_page_metadata_lines(text: str, rendered: list[str], affiliation_buffer: list[str], deferred_meta: list[str], footnotes: list[str]) -> bool:
    handled = False
    lines = [part.strip() for part in text.splitlines() if part.strip()]
    if not lines:
        return True
    for line in lines:
        if is_frontmatter_noise_line(line):
            handled = True
            continue
        if line.startswith('Citation:'):
            deferred_meta.append(line)
            handled = True
            continue
        if line.startswith('Received:') or line.startswith('Revised:') or line.startswith('Accepted:') or line.startswith('Published:'):
            deferred_meta.append(line)
            handled = True
            continue
        if line.startswith('Correspondence:') or line.startswith('* Correspondence:'):
            footnotes[:] = [fn for fn in footnotes if not fn.startswith('[^correspondence]:')]
            footnotes.append(f"[^correspondence]: {line.split(':', 1)[1].strip()}")
            handled = True
            continue
        if line.startswith('† '):
            footnotes[:] = [fn for fn in footnotes if not fn.startswith('[^equal]:')]
            footnotes.append(f'[^equal]: {line[2:].strip()}')
            handled = True
            continue
        if is_affiliation_line(line):
            affiliation_buffer.append(line)
            handled = True
            continue
        if '$^{' in line and ',' in line and (' and ' in line):
            rendered.append(clean_author_line(line))
            handled = True
            continue
        if len(line) < 22 or re.fullmatch('\\d+\\s+\\w+', line):
            handled = True
            continue
    return handled

def footnote_marker_and_body(content: str) -> tuple[str, str]:
    cleaned = clean_block_text(content)
    match = re.match('^\\$?\\^?\\{?([^\\}\\s]+)\\}?\\$?\\s*(.+)$', cleaned)
    if match:
        return (match.group(1).strip(), match.group(2).strip())
    return ('', cleaned)

def attach_footnote_reference(text: str, marker: str, footnote_id: str) -> str:
    if not marker:
        return text
    candidates = [f'$^{{{marker}}}$', f'$^{{{marker},*}}$', f'$^{{*,{marker}}}$']
    for token in candidates:
        if token in text and f'{token}[^{footnote_id}]' not in text:
            return text.replace(token, f'{token}[^{footnote_id}]', 1)
    return text

def parse_vision_footnote_entries(content: str) -> list[tuple[str, str]]:
    cleaned = clean_block_text(content)
    if not cleaned:
        return []
    matches = re.findall('\\$?\\^\\{?([A-Za-z*]+)\\}?\\$?\\s*([^;]+)', cleaned)
    if matches:
        return [(marker.strip(), body.strip()) for marker, body in matches if body.strip()]
    marker, body = footnote_marker_and_body(content)
    return [(marker, body)] if body else []

def _parse_asset_bbox_from_line(line: str) -> tuple[int, int, int, int] | None:
    match = re.search('page_(\\d+)_(?:figure|table)_(\\d+)_(\\d+)_(\\d+)_(\\d+)\\.jpg', line)
    if not match:
        return None
    return tuple((int(match.group(i)) for i in range(2, 6)))

def _bbox_area(bbox: tuple[int, int, int, int]) -> int:
    x1, y1, x2, y2 = bbox
    return max(0, x2 - x1) * max(0, y2 - y1)

def _bbox_contains(outer: tuple[int, int, int, int], inner: tuple[int, int, int, int], margin: int=12) -> bool:
    ox1, oy1, ox2, oy2 = outer
    ix1, iy1, ix2, iy2 = inner
    return ox1 - margin <= ix1 and oy1 - margin <= iy1 and (ox2 + margin >= ix2) and (oy2 + margin >= iy2)

def dedupe_page_media_lines(lines: list[str]) -> list[str]:
    media_indexes: list[tuple[int, tuple[int, int, int, int]]] = []
    for idx, line in enumerate(lines):
        if not line.startswith('![['):
            continue
        bbox = _parse_asset_bbox_from_line(line)
        if bbox:
            media_indexes.append((idx, bbox))
    drop_indexes: set[int] = set()
    for idx, bbox in media_indexes:
        for other_idx, other_bbox in media_indexes:
            if idx == other_idx:
                continue
            if _bbox_contains(other_bbox, bbox) and _bbox_area(other_bbox) > _bbox_area(bbox) * 1.15:
                drop_indexes.add(idx)
                break
    return [line for i, line in enumerate(lines) if i not in drop_indexes]

def attach_table_footnotes(table_html: str, marker_to_id: dict[str, str]) -> str:

    def replacer(match):
        markers = [part.strip() for part in match.group(1).split(',')]
        refs = []
        for marker in markers:
            ref_id = marker_to_id.get(marker)
            refs.append(f'{marker}[^{ref_id}]' if ref_id else marker)
        return ', '.join(refs) + '</td>'
    return re.sub('([a-z](?:\\s*,\\s*[a-z])*)</td>', replacer, table_html)

def media_clusters(blocks: list[dict]) -> tuple[dict[int, int], list[list[dict]]]:
    media = [b for b in blocks if b.get('block_label') in {'image', 'chart'}]
    clusters: list[list[dict]] = []
    block_to_cluster: dict[int, int] = {}
    for block in media:
        x1, y1, x2, y2 = block.get('block_bbox', [0, 0, 0, 0])
        assigned = None
        for idx, cluster in enumerate(clusters):
            cx1 = min((item['block_bbox'][0] for item in cluster)) - 40
            cy1 = min((item['block_bbox'][1] for item in cluster)) - 40
            cx2 = max((item['block_bbox'][2] for item in cluster)) + 40
            cy2 = max((item['block_bbox'][3] for item in cluster)) + 40
            if not (x2 < cx1 or x1 > cx2 or y2 < cy1 or (y1 > cy2)):
                assigned = idx
                break
        if assigned is None:
            assigned = len(clusters)
            clusters.append([])
        clusters[assigned].append(block)
        block_to_cluster[block.get('block_id', -1)] = assigned
    return (block_to_cluster, clusters)

def _bbox_width(bbox: list[int]) -> int:
    return max(0, int(bbox[2]) - int(bbox[0]))

def _bbox_height(bbox: list[int]) -> int:
    return max(0, int(bbox[3]) - int(bbox[1]))

def _bbox_horizontal_overlap(a: list[int], b: list[int]) -> int:
    return max(0, min(int(a[2]), int(b[2])) - max(int(a[0]), int(b[0])))

def _bbox_vertical_overlap(a: list[int], b: list[int]) -> int:
    return max(0, min(int(a[3]), int(b[3])) - max(int(a[1]), int(b[1])))

def _bbox_horizontal_overlap_ratio(a: list[int], b: list[int]) -> float:
    width = min(_bbox_width(a), _bbox_width(b))
    if width <= 0:
        return 0.0
    return _bbox_horizontal_overlap(a, b) / width

def _bbox_center_x(bbox: list[int]) -> float:
    return (int(bbox[0]) + int(bbox[2])) / 2

def _bbox_center_y(bbox: list[int]) -> float:
    return (int(bbox[1]) + int(bbox[3])) / 2

def _cluster_bbox(cluster: list[dict]) -> list[int]:
    return [min((int(item['block_bbox'][0]) for item in cluster)), min((int(item['block_bbox'][1]) for item in cluster)), max((int(item['block_bbox'][2]) for item in cluster)), max((int(item['block_bbox'][3]) for item in cluster))]

def is_formal_figure_legend(text: str) -> bool:
    cleaned = clean_block_text(text)
    if not cleaned:
        return False
    return bool(re.match('^(?:Extended\\s+Data\\s+Fig\\.?\\s+\\w+|Extended\\s+Data\\s+Figure\\s+\\w+|Extended\\s+Data\\s+Table\\s+\\w+|Supplementary\\s+Fig\\.?\\s+\\w+|Supplementary\\s+Figure\\s+\\w+|Supplementary\\s+Table\\s+\\w+|Supplementary\\s+Video\\s+\\w+|Figure\\s+\\d+|Fig\\.?\\s+\\d+|Table\\s+\\d+|Scheme\\s+\\w+|Graphical\\s+Abstract(?:\\s*[:|.\\-].*)?)', cleaned, flags=re.IGNORECASE))

def _figure_caption_blocks(blocks: list[dict]) -> list[dict]:
    captions = []
    for block in blocks:
        if block.get('block_label') not in {'figure_title', 'paragraph_title', 'text'}:
            continue
        text = clean_block_text(block.get('block_content', ''))
        if is_formal_figure_legend(text):
            captions.append(block)
    return captions

def estimate_body_column_width(blocks: list[dict], page_width: int=0) -> int:
    widths: list[int] = []
    for block in blocks:
        if block.get('block_label') not in {'text', 'paragraph_title', 'abstract'}:
            continue
        text = clean_block_text(block.get('block_content', ''))
        if not text or is_subfigure_label(text) or re.match('^(?:Figure|Fig\\.?|Table)\\s+\\w+', text, flags=re.IGNORECASE):
            continue
        bbox = [int(value) for value in block.get('block_bbox', [0, 0, 0, 0])]
        width = _bbox_width(bbox)
        height = _bbox_height(bbox)
        if width <= 0 or height <= 0:
            continue
        if page_width and width >= int(page_width * 0.82):
            widths.append(width)
            continue
        if width >= 430:
            widths.append(width)
    if not widths:
        return int(page_width * 0.45) if page_width else 520
    widths.sort()
    return widths[len(widths) // 2]

def _precaption_media_region(caption_bbox: list[int], cluster_bboxes: list[list[int]]) -> list[int] | None:
    relevant = [bbox for bbox in cluster_bboxes if int(bbox[3]) <= int(caption_bbox[1]) + 24]
    if len(relevant) < 1:
        return None
    return [min((int(bbox[0]) for bbox in relevant)), min((int(bbox[1]) for bbox in relevant)), max((int(bbox[2]) for bbox in relevant)), max((int(bbox[3]) for bbox in relevant))]

def compute_precaption_composite_regions(blocks: list[dict], page_width: int=0, page_height: int=0) -> list[dict]:
    caption_blocks = _figure_caption_blocks(blocks)
    _, clusters = media_clusters(blocks)
    cluster_bboxes = [_cluster_bbox(cluster) for cluster in clusters]
    body_column_width = estimate_body_column_width(blocks, page_width=page_width)
    regions: list[dict] = []
    for caption in caption_blocks:
        caption_bbox = [int(value) for value in caption.get('block_bbox', [0, 0, 0, 0])]
        precaption_region = _precaption_media_region(caption_bbox, cluster_bboxes)
        if not precaption_region:
            continue
        region_blocks = []
        for block in blocks:
            label = block.get('block_label', '')
            bbox = [int(value) for value in block.get('block_bbox', [0, 0, 0, 0])]
            if bbox[3] > caption_bbox[1] + 24:
                continue
            vertical_overlap_with_region = _bbox_vertical_overlap(bbox, precaption_region)
            near_region_side = vertical_overlap_with_region > 0 and (0 <= precaption_region[0] - bbox[2] <= 80 or 0 <= bbox[0] - precaption_region[2] <= 80)
            intersects_region = _bbox_horizontal_overlap(bbox, precaption_region) > 0 or precaption_region[0] - 24 <= _bbox_center_x(bbox) <= precaption_region[2] + 24 or near_region_side
            if not intersects_region:
                continue
            if label in {'image', 'chart'}:
                region_blocks.append(block)
                continue
            if label in {'text', 'paragraph_title'}:
                width = _bbox_width(bbox)
                text = clean_block_text(block.get('block_content', ''))
                if text and (not re.match('^(?:Extended\\s+Data\\s+Fig\\.?|Extended\\s+Data\\s+Figure|Figure|Fig\\.?|Table)\\s+\\w+', text, flags=re.IGNORECASE)) and (width <= int(max(body_column_width, 1) * 0.78) or is_embedded_figure_text_block(block, blocks, page_width=page_width, page_height=page_height)):
                    region_blocks.append(block)
        media_ids = {block.get('block_id') for block in region_blocks if block.get('block_label') in {'image', 'chart'}}
        text_ids = {block.get('block_id') for block in region_blocks if block.get('block_label') in {'text', 'paragraph_title'}}
        if len(media_ids) < 1 or not text_ids or len(region_blocks) < 3:
            continue
        region_bbox = [min((int(block['block_bbox'][0]) for block in region_blocks)), min((int(block['block_bbox'][1]) for block in region_blocks)), max((int(block['block_bbox'][2]) for block in region_blocks)), max((int(block['block_bbox'][3]) for block in region_blocks))]
        regions.append({'bbox': region_bbox, 'block_ids': {block.get('block_id') for block in region_blocks}, 'caption_block_id': caption.get('block_id')})
    return regions

def is_embedded_figure_text_block(block: dict, blocks: list[dict], page_width: int=0, page_height: int=0) -> bool:
    label = block.get('block_label', '')
    if label not in {'text', 'paragraph_title'}:
        return False
    text = clean_block_text(block.get('block_content', ''))
    if not text:
        return False
    if is_formal_figure_legend(text):
        return False
    bbox = [int(value) for value in block.get('block_bbox', [0, 0, 0, 0])]
    width = _bbox_width(bbox)
    height = _bbox_height(bbox)
    if width <= 0 or height <= 0:
        return False
    if label == 'paragraph_title' and is_subfigure_label(text):
        return True
    caption_blocks = _figure_caption_blocks(blocks)
    cluster_index, clusters = media_clusters(blocks)
    cluster_bboxes = [_cluster_bbox(cluster) for cluster in clusters]
    body_column_width = estimate_body_column_width(blocks, page_width=page_width)
    del cluster_index
    nearest_media = None
    nearest_media_distance = None
    close_media_count = 0
    stacked_media_above = False
    stacked_media_below = False
    side_media = False
    for cluster_bbox in cluster_bboxes:
        horizontal_ratio = _bbox_horizontal_overlap_ratio(bbox, cluster_bbox)
        vertical_overlap = _bbox_vertical_overlap(bbox, cluster_bbox)
        top_gap = int(bbox[1]) - int(cluster_bbox[3])
        bottom_gap = int(cluster_bbox[1]) - int(bbox[3])
        center_inside_x = int(cluster_bbox[0]) <= _bbox_center_x(bbox) <= int(cluster_bbox[2])
        center_inside_y = int(cluster_bbox[1]) <= _bbox_center_y(bbox) <= int(cluster_bbox[3])
        if horizontal_ratio >= 0.45 and (0 <= top_gap <= 48 or 0 <= bottom_gap <= 48 or vertical_overlap > 0) or (center_inside_x and abs(_bbox_center_y(bbox) - _bbox_center_y(cluster_bbox)) <= max(80, height * 4)):
            close_media_count += 1
        if horizontal_ratio >= 0.5 and 0 <= top_gap <= 90:
            stacked_media_above = True
        if horizontal_ratio >= 0.5 and 0 <= bottom_gap <= 90:
            stacked_media_below = True
        if vertical_overlap > 0 and (0 <= int(bbox[0]) - int(cluster_bbox[2]) <= 60 or 0 <= int(cluster_bbox[0]) - int(bbox[2]) <= 60):
            side_media = True
        dx = 0
        if int(bbox[2]) < int(cluster_bbox[0]):
            dx = int(cluster_bbox[0]) - int(bbox[2])
        elif int(cluster_bbox[2]) < int(bbox[0]):
            dx = int(bbox[0]) - int(cluster_bbox[2])
        dy = 0
        if int(bbox[3]) < int(cluster_bbox[1]):
            dy = int(cluster_bbox[1]) - int(bbox[3])
        elif int(cluster_bbox[3]) < int(bbox[1]):
            dy = int(bbox[1]) - int(cluster_bbox[3])
        distance = dx + dy
        if nearest_media_distance is None or distance < nearest_media_distance:
            nearest_media_distance = distance
            nearest_media = cluster_bbox
            del center_inside_y
    nearest_caption_above = None
    nearest_caption_below = None
    for caption in caption_blocks:
        cb = [int(value) for value in caption.get('block_bbox', [0, 0, 0, 0])]
        if cb[3] <= bbox[1]:
            if nearest_caption_above is None or cb[3] > nearest_caption_above[3]:
                nearest_caption_above = cb
        if cb[1] >= bbox[3]:
            if nearest_caption_below is None or cb[1] < nearest_caption_below[1]:
                nearest_caption_below = cb
    media_between_block_and_caption = 0
    media_x_covering_block = 0
    precaption_region = None
    if nearest_caption_below:
        precaption_region = _precaption_media_region(nearest_caption_below, cluster_bboxes)
        for cluster_bbox in cluster_bboxes:
            if cluster_bbox[1] >= nearest_caption_below[1] + 24:
                continue
            if cluster_bbox[3] <= bbox[1] - 24:
                continue
            media_between_block_and_caption += 1
            if cluster_bbox[0] - 24 <= _bbox_center_x(bbox) <= cluster_bbox[2] + 24 or _bbox_horizontal_overlap_ratio(bbox, cluster_bbox) >= 0.35:
                media_x_covering_block += 1
    if nearest_caption_above:
        caption_gap = bbox[1] - nearest_caption_above[3]
        left_align_gap = abs(bbox[0] - nearest_caption_above[0])
        effective_page_width = max(page_width, width)
        if 0 <= caption_gap <= 72 and left_align_gap <= 80 and (width >= int(effective_page_width * 0.45)) and (not stacked_media_above):
            return False
    score = 0.0
    if is_subfigure_label(text):
        score += 4.0
    if width <= int(max(body_column_width, 1) * 0.78):
        score += 1.4
    elif width <= int(max(body_column_width, 1) * 0.9):
        score += 0.5
    if label == 'paragraph_title' and len(text) <= 24:
        score += 0.8
    if height <= 26:
        score += 0.8
    elif height <= 34:
        score += 0.4
    if page_width and width <= int(page_width * 0.22):
        score += 0.5
    if close_media_count >= 2:
        score += 2.0
    elif close_media_count == 1:
        score += 1.1
    if stacked_media_above and stacked_media_below:
        score += 2.2
    elif stacked_media_above or stacked_media_below:
        score += 0.9
    if side_media:
        score += 1.0
    if nearest_caption_below and nearest_media:
        caption_gap = nearest_caption_below[1] - bbox[3]
        media_gap = min(abs(bbox[1] - nearest_media[3]), abs(nearest_media[1] - bbox[3]), abs(_bbox_center_y(bbox) - _bbox_center_y(nearest_media)))
        if 0 <= caption_gap <= 120 and media_gap <= 80:
            score += 0.8
    if nearest_caption_below:
        caption_gap = nearest_caption_below[1] - bbox[3]
        if 0 <= caption_gap <= 520 and media_between_block_and_caption >= 3:
            score += 0.9
        if 0 <= caption_gap <= 520 and media_x_covering_block >= 2:
            score += 1.3
        if 0 <= caption_gap <= 520 and media_x_covering_block >= 1 and (width <= int(max(page_width, width) * 0.82)) and (height <= 96):
            score += 0.8
        if precaption_region:
            region_overlap = _bbox_horizontal_overlap_ratio(bbox, precaption_region)
            within_region_y = int(precaption_region[1]) - 24 <= int(bbox[1]) <= int(precaption_region[3]) + 24 and int(bbox[3]) <= int(nearest_caption_below[1]) + 24
            if region_overlap >= 0.55 and within_region_y:
                score += 1.5
            if int(precaption_region[0]) - 24 <= _bbox_center_x(bbox) <= int(precaption_region[2]) + 24 and within_region_y and (media_between_block_and_caption >= 2):
                score += 1.1
    if len(text) <= 22:
        score += 0.15
    return score >= 2.6

def is_embedded_vision_footnote_block(block: dict, blocks: list[dict], page_width: int=0, page_height: int=0) -> bool:
    if block.get('block_label') != 'vision_footnote':
        return False
    if is_formal_figure_legend(block.get('block_content', '')):
        return False
    bbox = [int(value) for value in block.get('block_bbox', [0, 0, 0, 0])]
    if _bbox_width(bbox) <= 0 or _bbox_height(bbox) <= 0:
        return False
    composite_regions = compute_precaption_composite_regions(blocks, page_width=page_width, page_height=page_height)
    for region in composite_regions:
        region_bbox = region.get('bbox', [0, 0, 0, 0])
        if _bbox_contains(tuple(region_bbox), tuple(bbox), margin=36):
            return True
    _, clusters = media_clusters(blocks)
    for cluster in clusters:
        cluster_bbox = _cluster_bbox(cluster)
        if _bbox_contains(tuple(cluster_bbox), tuple(bbox), margin=24):
            return True
        if _bbox_horizontal_overlap(bbox, cluster_bbox) > 0 and _bbox_vertical_overlap(bbox, cluster_bbox) > 0:
            return True
        vertical_overlap = _bbox_vertical_overlap(bbox, cluster_bbox)
        near_side = vertical_overlap > 0 and _bbox_width(bbox) <= 180 and (0 <= int(cluster_bbox[0]) - int(bbox[2]) <= 60 or 0 <= int(bbox[0]) - int(cluster_bbox[2]) <= 60)
        if near_side:
            return True
    return False

def caption_group_assignments(blocks: list[dict]) -> tuple[dict[int, list[dict]], dict[int, list[dict]]]:
    figure_captions = []
    table_captions = []
    for block in blocks:
        if block.get('block_label') not in {'figure_title', 'paragraph_title', 'text'}:
            continue
        text = clean_block_text(block.get('block_content', ''))
        if re.match('^(?:Figure|Fig\\.?)\\s+\\d+', text, flags=re.IGNORECASE):
            figure_captions.append(block)
        elif re.match('^(?:Table|Extended\\s+Data\\s+Table|Supplementary\\s+Table)\\s+\\d+', text, flags=re.IGNORECASE):
            table_captions.append(block)
    figure_map: dict[int, list[dict]] = {}
    table_map: dict[int, list[dict]] = {}
    for block in blocks:
        label = block.get('block_label')
        bbox = block.get('block_bbox', [0, 0, 0, 0])
        if label in {'image', 'chart'}:
            best_caption = None
            best_distance = None
            for caption in figure_captions:
                cb = caption.get('block_bbox', [0, 0, 0, 0])
                if bbox[1] < cb[1]:
                    distance = cb[1] - bbox[1]
                    if best_distance is None or distance < best_distance:
                        best_caption = caption
                        best_distance = distance
            if best_caption:
                figure_map.setdefault(best_caption['block_id'], []).append(block)
        elif label == 'table':
            best_caption = None
            best_distance = None
            for caption in table_captions:
                cb = caption.get('block_bbox', [0, 0, 0, 0])
                distance = min(abs(bbox[1] - cb[3]), abs(cb[1] - bbox[3]))
                if distance < 260 and (best_distance is None or distance < best_distance):
                    best_caption = caption
                    best_distance = distance
            if best_caption:
                table_map.setdefault(best_caption['block_id'], []).append(block)
    return (figure_map, table_map)

def render_page_blocks(vault: Path, page_index: int, result: dict, images_dir: Path, page_cache_dir: Path, pdf_doc=None) -> list[str]:
    pruned = result.get('prunedResult', {})
    blocks = sorted(pruned.get('parsing_res_list', []), key=block_sort_key)
    raw_reference_blocks = [block for block in blocks if block.get('block_label') == 'reference_content']
    first_reference_y = min((block.get('block_bbox', [0, 10 ** 9, 0, 0])[1] for block in raw_reference_blocks), default=10 ** 9)
    ocr_width = int(pruned.get('width', 0) or 0)
    ocr_height = int(pruned.get('height', 0) or 0)
    page_image = render_pdf_page_cached(pdf_doc, page_index, ocr_width, ocr_height, page_cache_dir / f'page_{page_index:03d}.png')
    if not page_image:
        page_image = ensure_page_image_cached(result.get('inputImage', ''), page_cache_dir / f'page_{page_index:03d}.jpg')
    cluster_index, clusters = media_clusters(blocks)
    figure_caption_map, table_caption_map = caption_group_assignments(blocks)
    composite_regions = compute_precaption_composite_regions(blocks, page_width=ocr_width, page_height=ocr_height)
    composite_by_block_id: dict[int, dict] = {}
    for region in composite_regions:
        region['rendered'] = False
        for block_id in region.get('block_ids', set()):
            composite_by_block_id[block_id] = region
    caption_linked_media_ids = {item.get('block_id') for media_list in list(figure_caption_map.values()) + list(table_caption_map.values()) for item in media_list}
    rendered: list[str] = [f'<!-- page {page_index} -->']
    reference_blocks: list[dict] = []
    reference_continuations: list[dict] = []
    footnotes: list[str] = []
    footnote_counter = 0
    rendered_cluster_ids: set[int] = set()
    rendered_caption_media_ids: set[int] = set()
    first_page_meta_done = page_index != 1
    affiliation_buffer: list[str] = []
    deferred_meta: list[str] = []
    for block in blocks:
        label = block.get('block_label', '')
        content = block.get('block_content', '')
        bbox = block.get('block_bbox', [0, 0, 0, 0])
        composite_region = composite_by_block_id.get(block.get('block_id'))
        if composite_region:
            if not composite_region.get('rendered'):
                composite_region['rendered'] = True
                region_bbox = composite_region['bbox']
                asset_path = images_dir / 'blocks' / f'page_{page_index:03d}_figure_{region_bbox[0]}_{region_bbox[1]}_{region_bbox[2]}_{region_bbox[3]}.jpg'
                if page_image and crop_block_asset(page_image, region_bbox, asset_path):
                    rendered.append(_image_embed_for_obsidian(asset_path.relative_to(vault)))
            continue
        if label in {'header', 'header_image', 'footer', 'footer_image', 'number'}:
            continue
        if label == 'doc_title':
            rendered.append(f'# {clean_block_text(content)}')
            continue
        if label == 'paragraph_title':
            title = clean_block_text(content)
            if title.lower() == 'check for updates' or is_subfigure_label(title) or is_reference_tail_noise_line(title) or is_embedded_figure_text_block(block, blocks, page_width=ocr_width, page_height=ocr_height):
                continue
            if page_index == 1 and affiliation_buffer:
                rendered.extend(affiliation_buffer)
                affiliation_buffer.clear()
            if page_index == 1 and deferred_meta:
                rendered.extend(deferred_meta)
                deferred_meta.clear()
                first_page_meta_done = True
            rendered.append(f'### {title}')
            continue
        if label == 'abstract':
            if page_index == 1 and affiliation_buffer:
                rendered.extend(affiliation_buffer)
                affiliation_buffer.clear()
            rendered.append(clean_block_text(content))
            if page_index == 1 and deferred_meta:
                rendered.extend(deferred_meta)
                deferred_meta.clear()
                first_page_meta_done = True
            continue
        if label == 'reference_content':
            text = clean_block_text(content)
            if text and (not is_reference_tail_noise_line(text)):
                if parse_reference_number(text) is None:
                    reference_continuations.append(block)
                else:
                    reference_blocks.append(block)
            continue
        if label == 'text':
            text = clean_block_text(content)
            if not text or is_subfigure_label(text) or is_frontmatter_noise_line(text) or is_reference_tail_noise_line(text) or is_embedded_figure_text_block(block, blocks, page_width=ocr_width, page_height=ocr_height):
                continue
            if raw_reference_blocks and bbox[1] >= first_reference_y - 10:
                reference_continuations.append(block)
                continue
            if page_index == 1 and (not first_page_meta_done):
                if handle_first_page_metadata_lines(text, rendered, affiliation_buffer, deferred_meta, footnotes):
                    continue
            rendered.append(text)
            continue
        if label == 'display_formula':
            formula = clean_block_text(content)
            formula = formula.strip()
            if formula.startswith('$$') and formula.endswith('$$') and (len(formula) >= 4):
                formula = formula[2:-2].strip()
            rendered.append(f'$$\n{formula}\n$$')
            continue
        if label == 'formula_number':
            rendered.append(clean_block_text(content))
            continue
        if label in {'table', 'image', 'chart'}:
            if block.get('block_id') in caption_linked_media_ids:
                continue
            if block.get('block_id') in rendered_caption_media_ids:
                continue
            if label in {'image', 'chart'}:
                cluster_id = cluster_index.get(block.get('block_id', -1))
                if cluster_id is None or cluster_id in rendered_cluster_ids:
                    continue
                rendered_cluster_ids.add(cluster_id)
                cluster_blocks = clusters[cluster_id]
                bbox = [min((item['block_bbox'][0] for item in cluster_blocks)), min((item['block_bbox'][1] for item in cluster_blocks)), max((item['block_bbox'][2] for item in cluster_blocks)), max((item['block_bbox'][3] for item in cluster_blocks))]
                asset_name = f'page_{page_index:03d}_figure_{bbox[0]}_{bbox[1]}_{bbox[2]}_{bbox[3]}.jpg'
            else:
                asset_name = f'page_{page_index:03d}_{label}_{bbox[0]}_{bbox[1]}_{bbox[2]}_{bbox[3]}.jpg'
            asset_path = images_dir / 'blocks' / asset_name
            if page_image and crop_block_asset(page_image, bbox, asset_path):
                rendered.append(_image_embed_for_obsidian(asset_path.relative_to(vault)))
            if label == 'table' and content:
                rendered.append(clean_block_text(content))
            continue
        if label == 'figure_title':
            caption_text = clean_block_text(content)
            if is_subfigure_label(caption_text):
                continue
            if not is_formal_figure_legend(caption_text):
                continue
            linked_media = figure_caption_map.get(block.get('block_id'), []) or table_caption_map.get(block.get('block_id'), [])
            if linked_media and page_image:
                rendered_caption_media_ids.update((item.get('block_id') for item in linked_media))
                union_bbox = [min((item['block_bbox'][0] for item in linked_media)), min((item['block_bbox'][1] for item in linked_media)), max((item['block_bbox'][2] for item in linked_media)), max((item['block_bbox'][3] for item in linked_media))]
                asset_kind = 'figure' if block.get('block_id') in figure_caption_map else 'table'
                asset_path = images_dir / 'blocks' / f'page_{page_index:03d}_{asset_kind}_{union_bbox[0]}_{union_bbox[1]}_{union_bbox[2]}_{union_bbox[3]}.jpg'
                if crop_block_asset(page_image, union_bbox, asset_path):
                    rendered.append(_image_embed_for_obsidian(asset_path.relative_to(vault)))
                if asset_kind == 'table':
                    for item in linked_media:
                        if item.get('block_label') == 'table' and item.get('block_content'):
                            rendered.append(clean_block_text(item.get('block_content', '')))
                            break
            rendered.append(caption_text)
            continue
        if label == 'vision_footnote':
            if is_formal_figure_legend(content):
                rendered.append(clean_block_text(content))
                continue
            if is_embedded_vision_footnote_block(block, blocks, page_width=ocr_width, page_height=ocr_height):
                continue
            entries = parse_vision_footnote_entries(content)
            marker_to_id = {}
            for marker, body in entries:
                footnote_counter += 1
                footnote_id = f'p{page_index}-fn{footnote_counter}'
                marker_to_id[marker] = footnote_id
                footnotes.append(f'[^{footnote_id}]: {body or clean_block_text(content)}')
            if rendered and marker_to_id:
                last = rendered[-1]
                if last.startswith('<table>'):
                    rendered[-1] = attach_table_footnotes(last, marker_to_id)
                else:
                    for marker, footnote_id in marker_to_id.items():
                        rendered[-1] = attach_footnote_reference(rendered[-1], marker, footnote_id)
            continue
    if footnotes:
        rendered.append('')
        rendered.extend(footnotes)
    rendered = dedupe_page_media_lines(rendered)
    if reference_blocks:
        rendered.append('')
        ordered_reference_blocks = sort_reference_blocks(reference_blocks)
        continuation_map: dict[int, list[str]] = {}
        sorted_continuations = sorted(reference_continuations, key=block_sort_key)
        assigned_continuation_indexes: set[int] = set()
        incomplete_reference_indexes = [index for index, block in enumerate(ordered_reference_blocks) if clean_block_text(block.get('block_content', '')).rstrip().endswith(':')]
        for index, continuation in zip(incomplete_reference_indexes, sorted_continuations):
            continuation_text = clean_block_text(continuation.get('block_content', ''))
            if continuation_text:
                continuation_map.setdefault(index, []).append(continuation_text)
                assigned_continuation_indexes.add(id(continuation))
        for continuation in sorted_continuations:
            if id(continuation) in assigned_continuation_indexes:
                continue
            target_index = assign_reference_continuation(continuation, ordered_reference_blocks)
            if target_index is None:
                continue
            continuation_map.setdefault(target_index, []).append(clean_block_text(continuation.get('block_content', '')))
            assigned_continuation_indexes.add(id(continuation))
        unassigned_continuations = [clean_block_text(continuation.get('block_content', '')) for continuation in sorted_continuations if id(continuation) not in assigned_continuation_indexes]
        for index, block in enumerate(ordered_reference_blocks):
            text = clean_block_text(block.get('block_content', ''))
            if text:
                rendered.append(text)
            for continuation_text in continuation_map.get(index, []):
                if continuation_text:
                    rendered.append(continuation_text)
            if text.rstrip().endswith(':') and unassigned_continuations:
                rendered.append(unassigned_continuations.pop(0))
    return [part for part in rendered if part]

def postprocess_ocr_result(vault: Path, key: str, all_results: list[dict]) -> tuple[int, str, str, str]:
    paths = pipeline_paths(vault)
    ocr_root = paths['ocr'] / key
    json_dir = ocr_root / 'json'
    images_dir = ocr_root / 'images'
    page_cache_dir = ocr_root / 'pages'
    meta_path = ocr_root / 'meta.json'
    json_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    page_cache_dir.mkdir(parents=True, exist_ok=True)
    page_num = 0
    merged_parts = []
    meta = read_json(meta_path) if meta_path.exists() else {}
    source_pdf = Path(meta.get('source_pdf', '')) if meta.get('source_pdf') else None
    pdf_doc = None
    try:
        if source_pdf and source_pdf.exists():
            pdf_doc = fitz.open(str(source_pdf))
        for page_payload in all_results:
            for res in page_payload.get('layoutParsingResults', []):
                page_num += 1
                merged_parts.append('\n\n'.join(render_page_blocks(vault, page_num, res, images_dir, page_cache_dir, pdf_doc=pdf_doc)))
    finally:
        if pdf_doc is not None:
            pdf_doc.close()
    write_json(json_dir / 'result.json', all_results)
    fulltext_path = ocr_root / 'fulltext.md'
    fulltext_path.write_text('\n\n'.join(merged_parts).strip() + '\n', encoding='utf-8')
    markdown_dir = ocr_root / 'markdown'
    if markdown_dir.exists():
        shutil.rmtree(markdown_dir)
    markdown_path = str(fulltext_path.relative_to(vault)).replace('\\', '/') if page_num else ''
    json_path = str((json_dir / 'result.json').relative_to(vault)).replace('\\', '/')
    fulltext_md_path = str(fulltext_path.resolve())
    return (page_num, markdown_path, json_path, fulltext_md_path)

def run_ocr(vault: Path) -> int:
    paths = pipeline_paths(vault)
    cleanup_blocked_ocr_dirs(paths)
    control_actions = load_control_actions(paths)
    target_keys = {key for key, action in control_actions.items() if action.get('do_ocr', False)}
    target_rows = []
    for export_path in sorted(paths['exports'].glob('*.json')):
        for item in load_export_rows(export_path):
            if item['key'] not in target_keys:
                continue
            pdf_attachments = [a for a in item.get('attachments', []) if a.get('contentType') == 'application/pdf']
            target_rows.append({'zotero_key': item['key'], 'has_pdf': bool(pdf_attachments), 'pdf_path': pdf_attachments[0]['path'] if pdf_attachments else ''})
    ocr_queue = sync_ocr_queue(paths, target_rows)
    max_items_raw = os.environ.get('PADDLEOCR_MAX_ITEMS', '').strip()
    max_items = 3
    if max_items_raw:
        try:
            max_items = max(1, int(max_items_raw))
        except ValueError:
            max_items = 3
    token = os.environ.get('PADDLEOCR_API_TOKEN', '').strip()
    if not token:
        token = os.environ.get('PADDLEOCR_API_TOKEN_USER', '').strip()
    if not token:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as env_key:
                token = str(winreg.QueryValueEx(env_key, 'PADDLEOCR_API_TOKEN')[0]).strip()
        except Exception:
            token = ''
    job_url = os.environ.get('PADDLEOCR_JOB_URL', 'https://paddleocr.aistudio-app.com/api/v2/ocr/jobs').strip()
    model = os.environ.get('PADDLEOCR_MODEL', 'PaddleOCR-VL-1.5').strip()
    optional_payload = {'useDocOrientationClassify': False, 'useDocUnwarping': False, 'useChartRecognition': False}
    changed = 0
    active_submitted = 0
    queue_changed = False
    for queue_row in ocr_queue:
        key = queue_row['zotero_key']
        meta = ensure_ocr_meta(vault, queue_row)
        status = str(meta.get('ocr_status', 'pending') or 'pending').strip().lower()
        queue_row['queue_status'] = status
        if status == 'done':
            queue_changed = True
            continue
        if status in {'queued', 'running'} and meta.get('ocr_job_id'):
            active_submitted += 1
            if not token:
                continue
            response = requests.get(f"{job_url}/{meta['ocr_job_id']}", headers={'Authorization': f'bearer {token}'}, timeout=60)
            response.raise_for_status()
            payload = response.json()['data']
            state = payload['state']
            if state in {'pending', 'running'}:
                meta['ocr_status'] = state
                queue_row['queue_status'] = state
                meta['error'] = ''
            elif state == 'done':
                result_url = payload['resultUrl']['jsonUrl']
                result_response = requests.get(result_url, timeout=120)
                result_response.raise_for_status()
                lines = [line.strip() for line in result_response.text.splitlines() if line.strip()]
                all_results = []
                for line in lines:
                    page_payload = json.loads(line)['result']
                    all_results.append(page_payload)
                page_num, markdown_path, json_path, fulltext_md_path = postprocess_ocr_result(vault, key, all_results)
                meta['ocr_status'] = 'done'
                meta['ocr_finished_at'] = datetime.now(timezone.utc).isoformat()
                meta['page_count'] = page_num
                meta['markdown_path'] = markdown_path
                meta['json_path'] = json_path
                meta['fulltext_md_path'] = fulltext_md_path
                meta['error'] = ''
                queue_row['queue_status'] = 'done'
                queue_changed = True
                active_submitted = max(0, active_submitted - 1)
            else:
                meta['ocr_status'] = 'error'
                meta['error'] = payload.get('errorMsg', 'Unknown OCR failure')
                queue_row['queue_status'] = 'error'
                active_submitted = max(0, active_submitted - 1)
            write_json(paths['ocr'] / key / 'meta.json', meta)
            changed += 1
    available_slots = max(0, max_items - active_submitted)
    if available_slots > 0:
        for queue_row in ocr_queue:
            if available_slots <= 0:
                break
            key = queue_row['zotero_key']
            meta = ensure_ocr_meta(vault, queue_row)
            status = str(meta.get('ocr_status', 'pending') or 'pending').strip().lower()
            if status == 'done':
                queue_changed = True
                continue
            if status in {'queued', 'running'} and meta.get('ocr_job_id'):
                continue
            if not queue_row.get('has_pdf'):
                meta['ocr_status'] = 'blocked'
                meta['error'] = 'PDF not found in Zotero attachments'
                queue_row['queue_status'] = 'blocked'
                write_json(paths['ocr'] / key / 'meta.json', meta)
                changed += 1
                continue
            if not token:
                meta['ocr_status'] = 'blocked'
                meta['error'] = 'PaddleOCR not configured'
                queue_row['queue_status'] = 'blocked'
                write_json(paths['ocr'] / key / 'meta.json', meta)
                changed += 1
                continue
            with open(queue_row['pdf_path'], 'rb') as file_handle:
                response = requests.post(job_url, headers={'Authorization': f'bearer {token}'}, data={'model': model, 'optionalPayload': json.dumps(optional_payload)}, files={'file': file_handle}, timeout=120)
            response.raise_for_status()
            meta['ocr_job_id'] = response.json()['data']['jobId']
            meta['ocr_status'] = 'queued'
            meta['ocr_started_at'] = datetime.now(timezone.utc).isoformat()
            meta['error'] = ''
            queue_row['queue_status'] = 'queued'
            write_json(paths['ocr'] / key / 'meta.json', meta)
            changed += 1
            available_slots -= 1
    if queue_changed:
        ocr_queue = [row for row in ocr_queue if str(row.get('queue_status', '')).lower() != 'done']
    write_ocr_queue(paths, ocr_queue)
    run_selection_sync(vault)
    run_index_refresh(vault)
    print(f'ocr: updated {changed} records')
    return 0

def _resolve_formal_note_path(vault: Path, zotero_key: str, domain: str) -> Path | None:
    """Resolve formal literature note from 03_Resources/Literature by zotero_key."""
    lit_root = vault / '03_Resources' / 'Literature'
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

def run_deep_reading(vault: Path) -> int:
    """Sync deep-reading status between formal notes and library records.

    This worker does NOT generate content. It only:
    1. Scans formal literature notes for `## 🔍 精读` content
    2. Updates library-records/*.md frontmatter to match actual state
    3. Reports the queue of papers awaiting deep reading

    Actual content filling is done via /LD-deep (agent-driven).
    """
    paths = pipeline_paths(vault)
    config = read_json(paths['config'])
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
            note_path = _resolve_formal_note_path(vault, key, domain)
            has_content = False
            if note_path and note_path.exists():
                note_text = note_path.read_text(encoding='utf-8')
                has_content = has_deep_reading_content(note_text)
            correct_status = 'done' if has_content else 'pending'
            status_match = re.search('^deep_reading_status:\\s*"?(.*?)"?$', record_text, re.MULTILINE)
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
                        ocr_status = str(meta.get('ocr_status', 'pending')).strip().lower()
                    except Exception:
                        pass
                pending_queue.append({'zotero_key': key, 'domain': domain, 'title': item.get('title', ''), 'ocr_status': ocr_status})
    if pending_queue:
        report_lines = ['# 待精读队列', '']
        ready = [q for q in pending_queue if q['ocr_status'] == 'done']
        blocked = [q for q in pending_queue if q['ocr_status'] != 'done']
        if ready:
            report_lines.extend([f'## 就绪 ({len(ready)} 篇) — OCR 已完成，可直接 /LD-deep', ''])
            for q in ready:
                report_lines.append(f"- `{q['zotero_key']}` | {q['domain']} | {q['title']}")
            report_lines.append('')
        if blocked:
            report_lines.extend([f'## 阻塞 ({len(blocked)} 篇) — 等待 OCR', ''])
            for q in blocked:
                report_lines.append(f"- `{q['zotero_key']}` | {q['domain']} | {q['title']} | OCR: {q['ocr_status']}")
            report_lines.append('')
        report_lines.extend(['## 操作', '', '- 对就绪论文，使用 `/LD-deep <zotero_key>` 触发精读', '- 批量触发：提供多个 key，用 subagent 并行处理', ''])
    else:
        report_lines = ['# 待精读队列', '', '所有 analyze=true 的论文已完成精读。', '']
    report_path = paths['pipeline'] / 'deep-reading-queue.md'
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')
    print(f'deep-reading: synced {synced} records, {len(pending_queue)} pending')
    return 0

# =============================================================================
# Update 功能
# =============================================================================

GITHUB_REPO = "LLLin000/PaperForge"
GITHUB_ZIP = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/master.zip"

PROTECTED_PATHS = {
    "03_Resources", "05_Bases",
    "99_System/LiteraturePipeline/ocr",
    "99_System/LiteraturePipeline/exports",
    "99_System/LiteraturePipeline/indexes",
    "99_System/LiteraturePipeline/candidates",
    ".env", "AGENTS.md",
}
UPDATEABLE_PATHS = ["skills", "pipeline", "templates", "command", "scripts"]


def _color(text: str, c: str = "") -> str:
    colors = {"r": "\033[91m", "g": "\033[92m", "y": "\033[93m", "b": "\033[94m", "c": "\033[96m", "x": "\033[0m"}
    if sys.platform == "win32" and not os.environ.get("FORCE_COLOR"):
        return text
    return f"{colors.get(c, '')}{text}{colors['x']}"


def _log(msg: str, c: str = "") -> None:
    print(_color(msg, c))


def _remote_version() -> str | None:
    try:
        api = f"https://api.github.com/repos/{GITHUB_REPO}/contents/paperforge.json"
        req = urllib.request.Request(api, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PaperForge"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            req2 = urllib.request.Request(data["download_url"], headers={"User-Agent": "PaperForge"})
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                return json.loads(resp2.read()).get("version")
    except Exception:
        return None


def _scan_updates(vault: Path, source: Path) -> list[tuple[Path, Path, str]]:
    updates = []
    for name in UPDATEABLE_PATHS:
        src_dir = source / name
        if not src_dir.exists():
            continue
        for src in src_dir.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(source)
            dst = vault / rel
            rel_str = str(rel).replace("\\", "/")
            if any(rel_str.startswith(p) for p in PROTECTED_PATHS):
                continue
            if dst.exists():
                if hashlib.sha256(src.read_bytes()).hexdigest() != hashlib.sha256(dst.read_bytes()).hexdigest():
                    updates.append((src, dst, "UPDATE"))
            else:
                updates.append((src, dst, "NEW"))
    return updates


def _do_backup(vault: Path, updates: list) -> Path | None:
    backup_dir = vault / f".backup_{datetime.now():%Y%m%d_%H%M%S}"
    backup_dir.mkdir(exist_ok=True)
    count = 0
    for src, dst, action in updates:
        if action == "UPDATE" and dst.exists():
            bp = backup_dir / dst.relative_to(vault)
            bp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, bp)
            count += 1
    if count:
        _log(f"[INFO] 已备份 {count} 个文件到 {backup_dir.name}", "c")
    return backup_dir if count else None


def _apply_updates(vault: Path, updates: list) -> bool:
    try:
        for src, dst, action in updates:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return True
    except Exception as e:
        _log(f"[ERR] 更新失败: {e}", "r")
        return False


def _rollback(vault: Path, backup_dir: Path) -> None:
    _log("[INFO] 正在回滚...", "b")
    for bp in backup_dir.rglob("*"):
        if bp.is_file():
            orig = vault / bp.relative_to(backup_dir)
            orig.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bp, orig)
    _log("[OK] 回滚完成", "g")


def update_via_git(vault: Path) -> bool:
    if not (vault / ".git").is_dir():
        _log("[ERR] 不是 git 仓库", "r")
        return False
    r = subprocess.run(["git", "status", "--short"], cwd=vault, capture_output=True, text=True, encoding="utf-8")
    if r.stdout.strip():
        _log("[WARN] 有未提交的更改，请先提交或储藏", "y")
        return False
    _log("[INFO] 执行 git pull...", "b")
    r = subprocess.run(["git", "pull", "origin", "master"], cwd=vault, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        _log(f"[ERR] git pull 失败: {r.stderr}", "r")
        return False
    _log("[OK] git pull 成功", "g")
    if r.stdout.strip():
        print(r.stdout)
    return True


def update_via_zip(vault: Path) -> bool:
    _log("[INFO] 下载更新包...", "b")
    tmp = Path(tempfile.mkdtemp(prefix="pf_update_"))
    zip_path = tmp / "update.zip"
    try:
        req = urllib.request.Request(GITHUB_ZIP, headers={"User-Agent": "PaperForge"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            zip_path.write_bytes(resp.read())
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp / "extracted")
        dirs = [d for d in (tmp / "extracted").iterdir() if d.is_dir()]
        source = dirs[0] if dirs else None
        if not source:
            _log("[ERR] 解压失败", "r")
            return False
        updates = _scan_updates(vault, source)
        if not updates:
            _log("[OK] 所有文件已是最新", "g")
            return True
        _log(f"\n[INFO] 发现 {len(updates)} 个文件需要更新:", "b")
        for src, dst, action in updates:
            _log(f"  [{action}] {dst.relative_to(vault)}", "g" if action == "NEW" else "y")
        backup = _do_backup(vault, updates)
        if _apply_updates(vault, updates):
            _log(f"\n[OK] 更新完成！共 {len(updates)} 个文件", "g")
            return True
        if backup:
            _rollback(vault, backup)
        return False
    except Exception as e:
        _log(f"[ERR] 下载失败: {e}", "r")
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_update(vault: Path) -> int:
    """运行更新检查与安装"""
    local_cfg = vault / "paperforge.json"
    if not local_cfg.exists():
        _log("[ERR] 未找到 paperforge.json", "r")
        return 1
    local = json.loads(local_cfg.read_text(encoding="utf-8")).get("version", "unknown")
    remote = _remote_version()
    _log("=" * 50, "b")
    _log("PaperForge Lite 更新", "b")
    _log("=" * 50, "b")
    _log(f"本地版本: {local}", "c")
    _log(f"远程版本: {remote or 'unknown'}", "c")
    if not remote:
        _log("[ERR] 无法获取远程版本", "r")
        return 1
    try:
        needs = tuple(int(x) for x in remote.split(".") if x.isdigit()) > tuple(int(x) for x in local.split(".") if x.isdigit())
    except ValueError:
        needs = remote != local
    if not needs:
        _log("[OK] 当前已是最新版本", "g")
        return 0
    _log(f"\n[INFO] 发现新版本: {local} -> {remote}", "y")
    _log("[WARN] 更新前建议备份 Vault", "y")
    ans = input(_color("确认更新? [y/N]: ", "y")).strip().lower()
    if ans not in ("y", "yes"):
        _log("[INFO] 已取消", "c")
        return 0
    if (vault / ".git").is_dir():
        success = update_via_git(vault)
    else:
        success = update_via_zip(vault)
    if success:
        _log("\n[OK] 更新完成！请重启 Obsidian", "g")
    return 0 if success else 1


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--vault', required=True, type=Path)
    parser.add_argument('--query')
    parser.add_argument('--domain')
    parser.add_argument('--recommended-collection', default='')
    parser.add_argument('--requester-skill', default='')
    parser.add_argument('--request-context', default='')
    parser.add_argument('--recommend-reason', default='')
    parser.add_argument('--limit', type=int, default=8)
    parser.add_argument('--sources', nargs='+')
    parser.add_argument('--skip-ingest', action='store_true')
    parser.add_argument('worker', choices=['selection-sync', 'index-refresh', 'ocr', 'deep-reading', 'update', 'wizard', 'all'])
    args = parser.parse_args()
    load_simple_env(args.vault / '.env')
    if args.worker == 'selection-sync':
        return run_selection_sync(args.vault)
    if args.worker == 'index-refresh':
        return run_index_refresh(args.vault)
    if args.worker == 'ocr':
        return run_ocr(args.vault)
    if args.worker == 'deep-reading':
        return run_deep_reading(args.vault)
    if args.worker == 'update':
        return run_update(args.vault)
    if args.worker == 'wizard':
        wizard_script = args.vault / 'setup_wizard.py'
        if not wizard_script.exists():
            print(f"[ERR] 未找到 {wizard_script}")
            return 1
        return subprocess.run([sys.executable, str(wizard_script), '--vault', str(args.vault)]).returncode
    # 'all' - 依次运行所有 Lite 版 workers
    code = run_selection_sync(args.vault)
    if code:
        return code
    code = run_index_refresh(args.vault)
    if code:
        return code
    code = run_ocr(args.vault)
    if code:
        return code
    return run_deep_reading(args.vault)
if __name__ == '__main__':
    raise SystemExit(main())