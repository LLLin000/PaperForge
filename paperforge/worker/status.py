from __future__ import annotations

import json
import logging
import os
import re
import sys
from json import JSONDecodeError
from pathlib import Path

from paperforge.config import load_vault_config, paperforge_paths
from paperforge.worker._utils import (
    read_json,
    write_json,
)
from paperforge.worker.base_views import ensure_base_views

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


def load_domain_config(paths: dict[str, Path]) -> dict:
    """Load or create the Lite domain mapping from export JSON files."""
    config_path = paths["config"]
    config = read_json(config_path) if config_path.exists() else {"domains": []}
    domains = config.setdefault("domains", [])
    known_exports = {str(entry.get("export_file", "")) for entry in domains}
    changed = not config_path.exists()
    for export_path in sorted(paths["exports"].glob("*.json")):
        if export_path.name in known_exports:
            continue
        domains.append({"domain": export_path.stem, "export_file": export_path.name, "allowed_collections": []})
        known_exports.add(export_path.name)
        changed = True
    if changed:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(config_path, config)
    return config


def _detect_zotero_data_dir() -> str | None:
    """Try to detect the user's Zotero data directory."""
    if os.name == "nt":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidate = Path(appdata) / "Zotero"
            if candidate.exists() and (candidate / "storage").exists():
                return str(candidate)
    home = Path.home()
    candidates = []
    if os.name == "nt":
        candidates = [
            home / "Zotero",
            home / "AppData" / "Roaming" / "Zotero",
        ]
    else:
        candidates = [
            home / "Zotero",
            home / ".zotero" / "zotero",
            home / "Library" / "Application Support" / "Zotero",
        ]
    for candidate in candidates:
        if candidate.exists() and (candidate / "storage").exists():
            return str(candidate)
    return None


def check_zotero_location(vault: Path, cfg: dict, add_check) -> None:
    """Detect if Zotero data directory is inside vault or linked via junction."""
    system_dir = vault / cfg["system_dir"]
    zotero_link = system_dir / "Zotero"
    if zotero_link.exists():
        if zotero_link.is_symlink() or _is_junction(zotero_link):
            try:
                target = os.path.realpath(zotero_link)
                if Path(target).exists():
                    add_check(
                        "Path Resolution",
                        "pass",
                        f"Zotero junction valid -> {target}",
                    )
                else:
                    add_check(
                        "Path Resolution",
                        "warn",
                        f"Zotero junction target missing: {target}",
                        f'Recreate junction: mklink /J "{zotero_link}" "<Zotero数据目录>"',
                    )
            except Exception:
                add_check(
                    "Path Resolution",
                    "warn",
                    "Zotero junction exists but target could not be resolved",
                )
        else:
            if (zotero_link / "storage").exists():
                add_check(
                    "Path Resolution",
                    "pass",
                    "Zotero inside vault -- direct paths available",
                )
            else:
                add_check(
                    "Path Resolution",
                    "warn",
                    "Zotero directory exists but missing storage/ subdirectory",
                    "Verify this is a valid Zotero data directory",
                )
    else:
        zotero_data_dir = _detect_zotero_data_dir()
        if zotero_data_dir:
            add_check(
                "Path Resolution",
                "warn",
                "Zotero outside vault -- junction recommended",
                f'Run as Administrator: mklink /J "{zotero_link}" "{zotero_data_dir}"',
            )
        else:
            add_check(
                "Path Resolution",
                "fail",
                "Zotero directory not found",
                f'Run as Administrator: mklink /J "{zotero_link}" "<Zotero数据目录>"',
            )


def _summarize_errors(errors: list[str]) -> str:
    """Summarize error types into a human-readable string."""
    counts: dict[str, int] = {}
    for e in errors:
        counts[e] = counts.get(e, 0) + 1
    return ", ".join(f"{count} {err}" for err, count in sorted(counts.items()))


def check_pdf_paths(vault: Path, paths: dict, add_check) -> None:
    """Sample up to 5 library records and validate their pdf_path wikilinks."""
    record_paths = list(paths["library_records"].rglob("*.md"))
    if not record_paths:
        add_check("Path Resolution", "pass", "No library records to check")
        return
    import random

    sample = record_paths if len(record_paths) <= 5 else random.sample(record_paths, 5)
    valid = 0
    errors: list[str] = []
    for record_path in sample:
        try:
            text = record_path.read_text(encoding="utf-8")
        except Exception:
            continue
        pdf_match = re.search(r'^pdf_path:\s*"(.*?)"\s*$', text, re.MULTILINE)
        if not pdf_match:
            continue
        pdf_path = pdf_match.group(1).strip()
        if not pdf_path:
            continue
        raw_path = pdf_path.strip("[]")
        candidate = vault / raw_path.replace("/", os.sep)
        if candidate.exists():
            valid += 1
        else:
            err_match = re.search(r'^path_error:\s*"(.*?)"\s*$', text, re.MULTILINE)
            error_type = err_match.group(1) if err_match else "not_found"
            errors.append(error_type)
    total = len(sample)
    if valid == total:
        add_check("Path Resolution", "pass", f"{valid}/{total} PDF paths valid")
    else:
        error_summary = _summarize_errors(errors) if errors else "unknown"
        add_check(
            "Path Resolution",
            "warn",
            f"{valid}/{total} PDF paths valid, {total - valid} path errors: {error_summary}",
        )


def check_wikilink_format(vault: Path, paths: dict, add_check) -> None:
    """Verify all pdf_path values in library-records use [[...]] format."""
    record_paths = list(paths["library_records"].rglob("*.md"))
    bad_paths: list[str] = []
    for record_path in record_paths:
        try:
            text = record_path.read_text(encoding="utf-8")
        except Exception:
            continue
        pdf_match = re.search(r'^pdf_path:\s*"(.*?)"\s*$', text, re.MULTILINE)
        if not pdf_match:
            continue
        pdf_path = pdf_match.group(1).strip()
        if not pdf_path:
            continue
        if not (pdf_path.startswith("[[") and pdf_path.endswith("]]")):
            bad_paths.append(str(record_path.relative_to(vault)))
    if bad_paths:
        add_check(
            "Path Resolution",
            "warn",
            f"{len(bad_paths)} pdf_path values not in wikilink format",
            "Re-run `paperforge sync` to regenerate wikilinks",
        )
    else:
        add_check(
            "Path Resolution",
            "pass",
            "All pdf_path values use wikilink format",
        )


def run_doctor(vault: Path, verbose: bool = False) -> int:
    """Validate PaperForge setup and report by category.

    Returns:
        0 if all checks pass, 1 otherwise.
    """
    paths = pipeline_paths(vault)
    cfg = load_vault_config(vault)
    checks: list[tuple[str, str, str, str]] = []

    def add_check(category: str, status: str, message: str, fix: str = "") -> None:
        checks.append((category, status, message, fix))

    sys_version = sys.version_info
    if sys_version.major >= 3 and sys_version.minor >= 10:
        add_check("Python 环境", "pass", f"Python {sys_version.major}.{sys_version.minor}.{sys_version.micro}")
    else:
        add_check(
            "Python 环境",
            "fail",
            f"Python {sys_version.major}.{sys_version.minor} (需要 3.10+)",
            "升级 Python 到 3.10 或更高版本",
        )

    required_modules = ["requests", "pymupdf", "PIL", "yaml"]
    missing_modules = []
    for mod in required_modules:
        try:
            __import__(mod)
        except ImportError:
            missing_modules.append(mod)
    if missing_modules:
        add_check(
            "Python 环境",
            "fail",
            f"缺少模块: {', '.join(missing_modules)}",
            f"运行: pip install {' '.join(missing_modules)}",
        )
    elif sys_version.major >= 3 and sys_version.minor >= 10:
        pass

    if (vault / "paperforge.json").exists():
        add_check("Vault 结构", "pass", "paperforge.json 存在")
    else:
        add_check("Vault 结构", "fail", "paperforge.json 不存在", "在 vault 根目录创建 paperforge.json")

    system_dir = vault / cfg["system_dir"]
    if system_dir.exists():
        add_check("Vault 结构", "pass", f"system_dir 存在: {cfg['system_dir']}")
    else:
        add_check("Vault 结构", "fail", f"system_dir 不存在: {cfg['system_dir']}", f"运行: mkdir {cfg['system_dir']}")

    resources_dir = vault / cfg["resources_dir"]
    if resources_dir.exists():
        add_check("Vault 结构", "pass", f"resources_dir 存在: {cfg['resources_dir']}")
    else:
        add_check(
            "Vault 结构", "fail", f"resources_dir 不存在: {cfg['resources_dir']}", f"运行: mkdir {cfg['resources_dir']}"
        )

    control_dir = resources_dir / cfg.get("control_dir", "LiteratureControl")
    if control_dir.exists():
        add_check("Vault 结构", "pass", f"control_dir 存在: {cfg.get('control_dir', 'LiteratureControl')}")
    else:
        add_check(
            "Vault 结构",
            "fail",
            f"control_dir 不存在: {cfg.get('control_dir', 'LiteratureControl')}",
            f"运行: mkdir {cfg['resources_dir']}/{cfg.get('control_dir', 'LiteratureControl')}",
        )

    zotero_link = system_dir / "Zotero"
    if zotero_link.exists():
        if zotero_link.is_symlink() or _is_junction(zotero_link):
            add_check("Zotero 链接", "pass", "Zotero 目录是 junction/symlink")
        else:
            add_check("Zotero 链接", "warn", "Zotero 目录存在但不是 junction，建议使用 junction")
    else:
        add_check(
            "Zotero 链接", "fail", "Zotero 目录不存在", f"创建 junction: mklink /j {zotero_link} <Zotero数据目录>"
        )

    exports_dir = system_dir / "PaperForge" / "exports"
    if exports_dir.exists():
        add_check("BBT 导出", "pass", "exports 目录存在")
    else:
        add_check("BBT 导出", "fail", "exports 目录不存在", "在 Better BibTeX 设置中配置导出路径")

    # Check for any valid JSON export (per-domain or library.json)
    json_files = sorted(exports_dir.glob("*.json")) if exports_dir.exists() else []
    valid_exports = []
    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) > 0:
                has_key = any("key" in item or "citation-key" in item for item in data[:5])
                if has_key:
                    valid_exports.append((jf.name, len(data)))
            elif isinstance(data, dict) and isinstance(data.get("items"), list) and len(data["items"]) > 0:
                has_key = any("key" in item or "citation-key" in item for item in data["items"][:5])
                if has_key:
                    valid_exports.append((jf.name, len(data["items"])))
        except (JSONDecodeError, Exception):
            pass

    if valid_exports:
        for name, count in valid_exports:
            add_check("BBT 导出", "pass", f"{name} 正常 ({count} 条)")
    elif json_files:
        add_check("BBT 导出", "warn", "导出文件存在但无有效 citation key")
    else:
        add_check("BBT 导出", "fail", "未找到 JSON 导出文件", "在 Zotero Better BibTeX 设置中配置导出路径")

    env_api_key = (
        os.environ.get("PADDLEOCR_API_TOKEN") or os.environ.get("PADDLEOCR_API_KEY") or os.environ.get("OCR_TOKEN")
    )
    if env_api_key:
        add_check("OCR 配置", "pass", "API Token 已配置")
    else:
        add_check("OCR 配置", "fail", "缺少 PADDLEOCR_API_TOKEN", "在 .env 文件中设置 PADDLEOCR_API_TOKEN")

    # Worker module check (v1.3+: pipeline/ removed, use paperforge.worker package)
    try:
        from paperforge.worker.base_views import ensure_base_views
        from paperforge.worker.deep_reading import run_deep_reading
        from paperforge.worker.ocr import run_ocr
        from paperforge.worker.sync import run_index_refresh, run_selection_sync

        add_check("Worker 脚本", "pass", "paperforge.worker 包可导入")
    except ImportError as e:
        add_check("Worker 脚本", "fail", f"worker 函数导入失败: {e}", "运行: pip install -e .")

    # Path Resolution checks
    check_zotero_location(vault, cfg, add_check)
    check_pdf_paths(vault, paths, add_check)
    check_wikilink_format(vault, paths, add_check)

    ld_deep_script = paths.get("ld_deep_script")
    skill_dir = None
    if ld_deep_script:
        skill_dir = ld_deep_script.parent.parent
    if skill_dir and skill_dir.exists():
        # Try actual importability check
        ld_deep_import_ok = False
        import_error = ""
        if ld_deep_script and ld_deep_script.exists():
            try:
                import importlib.util

                spec = importlib.util.spec_from_file_location("ld_deep", ld_deep_script)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    ld_deep_import_ok = True
            except Exception as e:
                import_error = str(e)
        if ld_deep_import_ok:
            add_check("Agent 脚本", "pass", "paperforge and ld_deep importable")
        else:
            add_check(
                "Agent 脚本",
                "warn",
                f"literature-qa skill 目录存在但 import 失败: {import_error}",
                "确认 agent_config_dir 配置正确并已运行 pip install -e .",
            )
    else:
        add_check("Agent 脚本", "warn", "literature-qa skill 目录未找到", "确认 agent_config_dir 配置正确")

    print("PaperForge Doctor")
    print("=" * 40)
    current_category = ""
    fix_map: dict[str, list[str]] = {}
    for category, status, message, fix in checks:
        if category != current_category:
            if current_category:
                print()
            current_category = category
        status_tag = {"pass": "[PASS]", "fail": "[FAIL]", "warn": "[WARN]"}[status]
        print(f"{status_tag} {category} — {message}")
        if status == "fail" and fix:
            fix_map.setdefault(category, [])
            fix_map[category].append(fix)

    if fix_map:
        print("\n修复步骤:")
        for cat, fixes in fix_map.items():
            for f in fixes:
                print(f"  - {cat}: {f}")
        print()
        return 1
    print()
    return 0


def _is_junction(path: Path) -> bool:
    """Check if a path is a Windows junction point."""
    try:
        import ctypes
        from ctypes import wintypes

        FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
        GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW
        GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
        GetFileAttributesW.restype = wintypes.DWORD
        attrs = GetFileAttributesW(str(path))
        if attrs == INVALID_FILE_ATTRIBUTES:
            return False
        return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
    except Exception:
        return False


def run_status(vault: Path, verbose: bool = False) -> int:
    """Print a compact Lite install/runtime status."""
    paths = pipeline_paths(vault)
    cfg = load_vault_config(vault)
    config = load_domain_config(paths)
    ensure_base_views(vault, paths, config)
    export_files = sorted(paths["exports"].glob("*.json"))
    record_count = sum(1 for _ in paths["library_records"].rglob("*.md")) if paths["library_records"].exists() else 0
    note_count = sum(1 for _ in paths["literature"].rglob("*.md")) if paths["literature"].exists() else 0
    base_count = sum(1 for _ in paths["bases"].glob("*.base")) if paths["bases"].exists() else 0
    ocr_done = 0
    ocr_total = 0
    if paths["ocr"].exists():
        for meta_path in paths["ocr"].glob("*/meta.json"):
            ocr_total += 1
            try:
                meta = read_json(meta_path)
            except Exception:
                continue
            if str(meta.get("ocr_status", "")).strip().lower() == "done":
                ocr_done += 1
    env_paths = [vault / ".env", paths["pipeline"] / ".env"]
    env_found = [str(path.relative_to(vault)).replace("\\", "/") for path in env_paths if path.exists()]

    # Count path errors
    path_error_count = 0
    if paths["library_records"].exists():
        for record_path in paths["library_records"].rglob("*.md"):
            try:
                text = record_path.read_text(encoding="utf-8")
                if re.search(r'^path_error:\s*"(.+?)"\s*$', text, re.MULTILINE):
                    path_error_count += 1
            except Exception:
                continue

    print("PaperForge status")
    print(f"- vault: {vault}")
    print(f"- system_dir: {cfg['system_dir']}")
    print(f"- resources_dir: {cfg['resources_dir']}")
    print(f"- literature_dir: {cfg['literature_dir']}")
    print(f"- control_dir: {cfg['control_dir']}")
    print(f"- exports: {len(export_files)} JSON file(s)")
    print(f"- domains: {len(config.get('domains', []))}")
    print(f"- library_records: {record_count}")
    print(f"- formal_notes: {note_count}")
    print(f"- bases: {base_count}")
    print(f"- ocr: {ocr_done}/{ocr_total} done")
    print(f"- path_errors: {path_error_count}")
    if path_error_count > 0:
        print("  Tip: Run `paperforge repair --fix-paths` to attempt resolution")
    print(f"- env: {', '.join(env_found) if env_found else 'not configured'}")
    return 0


# =============================================================================
# Update 功能
# =============================================================================

GITHUB_REPO = "LLLin000/PaperForge"
GITHUB_ZIP = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/master.zip"

UPDATEABLE_PATHS = ["skills", "pipeline", "command", "scripts"]
