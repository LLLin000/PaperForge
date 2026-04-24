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

def protected_paths(vault: Path) -> set[str]:
    cfg = load_vault_config(vault)
    pf = f"{cfg['system_dir']}/PaperForge"
    return {
        cfg["resources_dir"],
        cfg["base_dir"],
        f"{pf}/ocr",
        f"{pf}/exports",
        f"{pf}/indexes",
        f"{pf}/candidates",
        ".env",
        "AGENTS.md",
    }


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
    protected = protected_paths(vault)
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
            if any(rel_str.startswith(p) for p in protected):
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

