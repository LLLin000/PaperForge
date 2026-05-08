from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from json import JSONDecodeError
from pathlib import Path

from paperforge.config import (
    load_vault_config,
    paperforge_paths,
    read_paperforge_json,
    CONFIG_PATH_KEYS,
    get_paperforge_schema_version,
)
from paperforge.worker._domain import load_domain_config
from paperforge.worker._utils import (
    pipeline_paths,
    read_json,
    write_json,
)
from paperforge.worker.base_views import ensure_base_views

logger = logging.getLogger(__name__)


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
    """Sample up to 5 formal notes and validate their pdf_path wikilinks."""
    record_paths = list(paths["literature"].rglob("*.md"))
    if not record_paths:
        add_check("Path Resolution", "pass", "No formal notes to check")
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
    """Verify all pdf_path values in formal notes use [[...]] format."""
    record_paths = list(paths["literature"].rglob("*.md"))
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


# ---------------------------------------------------------------------------
# Module-level manifest for dependency checks
# ---------------------------------------------------------------------------

_MODULE_MANIFEST = [
    {"import": "requests", "pip": "requests", "label": "requests"},
    {"import": "pymupdf", "pip": "pymupdf", "label": "pymupdf"},
    {"import": "PIL", "pip": "Pillow", "label": "Pillow"},
    {"import": "yaml", "pip": "pyyaml>=6.0", "label": "PyYAML"},
]


# ---------------------------------------------------------------------------
# Plugin interpreter resolution helpers (Phase 53)
# ---------------------------------------------------------------------------


def _read_plugin_data(vault: Path) -> dict:
    """Read Obsidian plugin's data.json to get the user's python_path override.
    
    Returns empty dict if file not found, invalid, or not a dict.
    """
    plugin_data_path = vault / ".obsidian" / "plugins" / "paperforge" / "data.json"
    if not plugin_data_path.exists():
        return {}
    try:
        data = json.loads(plugin_data_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, OSError, Exception):
        return {}


def _resolve_plugin_interpreter(vault: Path, plugin_data: dict) -> tuple[str, str, list[str]]:
    """Replicate the plugin's resolvePythonExecutable() logic in pure Python.
    
    Detection order:
    1. Manual override: plugin_data["python_path"] if set and on disk
    2. Venv candidates: .paperforge-test-venv, .venv, venv (Scripts/ on Windows, bin/ on POSIX)
    3. System candidates: py -3, python, python3 (tested via --version)
    4. Fallback: python
    
    Returns (interpreter_path, source, extra_args).
    """
    # 1. Manual override
    manual_path = (plugin_data.get("python_path") or "").strip()
    if manual_path and os.path.exists(manual_path):
        return (manual_path, "manual", [])

    # 2. Venv candidates
    if os.name == "nt":
        venv_candidates = [
            vault / ".paperforge-test-venv" / "Scripts" / "python.exe",
            vault / ".venv" / "Scripts" / "python.exe",
            vault / "venv" / "Scripts" / "python.exe",
        ]
    else:
        venv_candidates = [
            vault / ".paperforge-test-venv" / "bin" / "python",
            vault / ".venv" / "bin" / "python",
            vault / "venv" / "bin" / "python",
        ]

    for candidate in venv_candidates:
        try:
            if candidate.exists():
                return (str(candidate), "auto-detected", [])
        except (PermissionError, OSError):
            continue

    # 3. System candidates — find first that runs --version successfully
    system_candidates = [
        ("py", ["-3"]),
        ("python", []),
        ("python3", []),
    ]

    for path, extra in system_candidates:
        try:
            cmd = [path] + extra + ["--version"]
            result = subprocess.run(cmd, capture_output=True, timeout=5, text=True)
            if result.returncode == 0 and "Python" in (result.stdout or ""):
                return (path, "auto-detected", extra)
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError, OSError):
            continue

    # 4. Fallback
    return ("python", "auto-detected", [])


def _query_resolved_version(
    interp: str, extra_args: list[str]
) -> tuple[str | None, tuple[int, int, int] | None]:
    """Run interpreter --version, parse and return version info.
    
    Returns (version_string, (major, minor, micro)) or (None, None) on failure.
    """
    try:
        cmd = [interp] + extra_args + ["--version"]
        result = subprocess.run(cmd, capture_output=True, timeout=10, text=True)
        if result.returncode != 0:
            return (None, None)
        output = (result.stdout or "").strip() or (result.stderr or "").strip()
        match = re.search(r"Python (\d+)\.(\d+)(?:\.(\d+))?", output)
        if match:
            major = int(match.group(1))
            minor = int(match.group(2))
            micro = int(match.group(3) or "0")
            return (output, (major, minor, micro))
        return (output, None)
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError, OSError):
        return (None, None)


def _query_resolved_package(
    interp: str, extra_args: list[str], package_name: str
) -> dict | None:
    """Run pip show for a package under the resolved interpreter.
    
    Returns dict with keys Name, Version, Location, etc., or None if not found.
    """
    try:
        cmd = [interp] + extra_args + ["-m", "pip", "show", package_name]
        result = subprocess.run(cmd, capture_output=True, timeout=15, text=True)
        if result.returncode != 0:
            return None
        output = (result.stdout or "").strip()
        if not output:
            return None
        info: dict[str, str] = {}
        for line in output.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip()] = value.strip()
        return info if info else None
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError, OSError):
        return None


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

    # --- Plugin-resolved interpreter (Phase 53: DOCTOR-01, DOCTOR-02) ---
    plugin_data = _read_plugin_data(vault)
    interp, source, extra_args = _resolve_plugin_interpreter(vault, plugin_data)
    version_str, version_tuple = _query_resolved_version(interp, extra_args)
    pf_pkg_info = _query_resolved_package(interp, extra_args, "paperforge")

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

    # --- Plugin-resolved interpreter checks ---
    add_check("Python 环境 (插件)", "pass",
        f"已解析解释器: {interp} (来源: {source})")

    if version_tuple is not None and version_tuple >= (3, 10, 0):
        add_check("Python 环境 (插件)", "pass",
            f"Python {version_str}")
    elif version_tuple is not None:
        add_check("Python 环境 (插件)", "fail",
            f"Python {version_str} (需要 3.10+)",
            f"升级解释器 {interp} 到 Python 3.10 或更高版本")
    else:
        add_check("Python 环境 (插件)", "fail",
            f"无法获取 {interp} 的 Python 版本",
            f"验证 {interp} 是一个有效的 Python 解释器")

    if pf_pkg_info is not None:
        pkg_version = pf_pkg_info.get("Version", "?")
        pkg_location = pf_pkg_info.get("Location", "?")
        expected_version = __import__("paperforge").__version__
        if pkg_version == expected_version:
            add_check("PaperForge 包", "pass",
                f"v{pkg_version} 已安装 -> {pkg_location}")
        else:
            add_check("PaperForge 包", "warn",
                f"v{pkg_version} 已安装 (插件版本 v{expected_version}) - 版本不匹配",
                f"运行: {interp} -m pip install --upgrade git+https://github.com/LLLin000/PaperForge.git")
    else:
        add_check("PaperForge 包", "fail",
            f"PaperForge 未安装在 {interp} 中",
            f"运行: {interp} -m pip install -e .")

    # Wrong-environment detection
    current_package_path = os.path.dirname(__import__("paperforge").__file__)
    if pf_pkg_info is not None and pf_pkg_info.get("Location"):
        loc = pf_pkg_info["Location"]
        if loc and loc != current_package_path:
            add_check("PaperForge 包", "warn",
                f"包路径不一致: 已解析解释器 -> {loc} | 当前诊断进程 -> {current_package_path}",
                "建议: 使用已解析解释器运行 doctor，或统一 Python 环境")

    # --- Per-module dependency checks (Phase 53: DOCTOR-03) ---
    for mod_info in _MODULE_MANIFEST:
        mod_name = mod_info["import"]
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", None)
            ver_str = f" ({ver})" if ver else ""

            # PyYAML specific: warn if version < 6.0
            if mod_name == "yaml" and ver:
                try:
                    ver_parts = str(ver).split(".")
                    if int(ver_parts[0]) < 6:
                        add_check("Python 环境", "warn",
                            f"{mod_info['label']} {ver} (需要 >=6.0)",
                            f"运行: pip install {mod_info['pip']}")
                        continue
                except (ValueError, IndexError):
                    pass

            add_check("Python 环境", "pass",
                f"{mod_info['label']} 已安装{ver_str}")
        except ImportError:
            add_check("Python 环境", "fail",
                f"{mod_info['label']} 缺失",
                f"运行: pip install {mod_info['pip']}")

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

    # Config Migration check
    pf_data = read_paperforge_json(vault)
    if pf_data:
        has_stale_top_level = any(k in pf_data for k in CONFIG_PATH_KEYS)
        if has_stale_top_level:
            backup_path = vault / "paperforge.json.bak"
            backup_hint = f" (backup: {backup_path})" if backup_path.exists() else ""
            add_check(
                "Config Migration",
                "warn",
                f"paperforge.json has stale top-level path keys -- run `paperforge sync` to auto-migrate{backup_hint}",
                "Run `paperforge sync` to auto-migrate to vault_config canonical format",
            )
        else:
            add_check(
                "Config Migration",
                "pass",
                "paperforge.json uses canonical vault_config format",
            )

        # Schema version check
        sv = get_paperforge_schema_version(vault)
        if sv >= 2:
            add_check("Config Migration", "pass", f"schema_version: {sv}")
        else:
            add_check(
                "Config Migration",
                "info",
                f"schema_version: {sv} (migration available via `paperforge sync`)",
            )
    else:
        add_check("Config Migration", "info", "paperforge.json not found -- new install?")

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

    # --- Index Health section (Phase 25: derived from canonical index) ---
    try:
        from paperforge.worker.asset_index import read_index as _read_idx, summarize_index as _summarize_idx

        _summary = _summarize_idx(vault)
    except Exception:
        _summary = None

    if _summary and _summary.get("paper_count", 0) > 0:
        _health = _summary.get("health_aggregate", {})

        def _health_status(dim: dict) -> tuple[str, str]:
            healthy = dim.get("healthy", 0)
            unhealthy = dim.get("unhealthy", 0)
            total = healthy + unhealthy
            if total == 0:
                return ("pass", "0 papers")
            if unhealthy == 0:
                return ("pass", f"{healthy}/{total} healthy")
            if healthy == 0:
                return ("fail", f"0/{total} healthy -- run doctor/repair")
            return ("warn", f"{healthy}/{total} healthy, {unhealthy} issues")

        for _dim_name, _dim_key in [
            ("PDF Health", "pdf_health"),
            ("OCR Health", "ocr_health"),
            ("Note Health", "note_health"),
            ("Asset Health", "asset_health"),
        ]:
            _dim = _health.get(_dim_key, {})
            if not isinstance(_dim, dict):
                _dim = {"healthy": 0, "unhealthy": 0}
            _st, _msg = _health_status(_dim)
            add_check("Index Health", _st, f"{_dim_name}: {_msg}")

        # Brownfield migration detection (MIG-01, MIG-03)
        _idx_data = _read_idx(vault)
        if isinstance(_idx_data, dict):
            _sv = _idx_data.get("schema_version", "0")
            try:
                if int(_sv) < 2:
                    add_check(
                        "Index Health", "warn",
                        f"Legacy index schema v{_sv} -- consider rebuild to v2",
                        "Run `paperforge sync --rebuild-index`",
                    )
            except (ValueError, TypeError):
                pass

        # Legacy Base templates (pre-lifecycle format)
        _bases_dir = paths.get("bases")
        if _bases_dir and _bases_dir.exists():
            _legacy = 0
            for _bp in _bases_dir.glob("*.base"):
                try:
                    _content = _bp.read_text(encoding="utf-8")
                    if "has_pdf" in _content and "lifecycle" not in _content:
                        _legacy += 1
                except Exception:
                    continue
            if _legacy > 0:
                add_check(
                    "Index Health", "warn",
                    f"{_legacy} Base file(s) use legacy columns (has_pdf, do_ocr) instead of lifecycle",
                    "Run `paperforge sync` to regenerate Base views",
                )

        # Partial OCR assets
        _ocr_dir = paths.get("ocr")
        if _ocr_dir and _ocr_dir.exists():
            _partial = 0
            for _mp in _ocr_dir.glob("*/meta.json"):
                try:
                    _meta = json.loads(_mp.read_text(encoding="utf-8"))
                    _os = str(_meta.get("ocr_status", "")).strip().lower()
                    if _os == "done_incomplete":
                        _partial += 1
                except Exception:
                    continue
            if _partial > 0:
                add_check(
                    "Index Health", "warn",
                    f"{_partial} partial OCR asset(s) found",
                    "Re-run `paperforge ocr` on affected items",
                )

        # WS-05: Workspace integrity checks
        try:
            from paperforge.worker.asset_index import read_index as _ws_read_idx
            _idx_content = _ws_read_idx(vault)
            _items = _idx_content.get("items", []) if isinstance(_idx_content, dict) else []
            _missing_workspace = 0
            _missing_fulltext = 0
            _ws_literature = paths.get("literature")
            for _e in _items:
                _key = _e.get("zotero_key", "")
                _dom = _e.get("domain", "")
                _title = _e.get("title", "")
                if not _key or not _dom:
                    continue
                from paperforge.worker._utils import slugify_filename
                _slug = slugify_filename(_title or _key)
                _ws_dir = _ws_literature / _dom / f"{_key} - {_slug}"
                if not _ws_dir.exists():
                    _missing_workspace += 1
                    continue
                if _e.get("ocr_status") == "done":
                    _ft = _ws_dir / "fulltext.md"
                    if not _ft.exists():
                        _missing_fulltext += 1
            if _missing_workspace > 0:
                add_check(
                    "Index Health", "warn",
                    f"{_missing_workspace} paper(s) missing workspace directories",
                    "Run `paperforge sync` to create workspace folders",
                )
            if _missing_fulltext > 0:
                add_check(
                    "Index Health", "warn",
                    f"{_missing_fulltext} paper(s) missing fulltext.md in workspace",
                    "Re-run OCR or run `paperforge sync` to bridge fulltext",
                )
            if _missing_workspace == 0 and _missing_fulltext == 0 and _items:
                add_check("Index Health", "pass", "Workspace integrity: all papers valid")
        except Exception:
            pass

        # LRD-05: Stale record detection in control directory
        _lr_dir = paths.get("control")
        if _lr_dir and _lr_dir.exists():
            _stale_count = sum(1 for _ in _lr_dir.rglob("*.md"))
            if _stale_count > 0:
                add_check(
                    "Index Health", "warn",
                    f"{_stale_count} stale record(s) found in control directory",
                    "Review and remove stale files from the control directory",
                )
    else:
        add_check("Index Health", "info", "No canonical index -- run `paperforge sync` to generate")

    print("PaperForge Doctor")
    print("=" * 40)
    current_category = ""
    fix_map: dict[str, list[str]] = {}
    for category, status, message, fix in checks:
        if category != current_category:
            if current_category:
                print()
            current_category = category
        status_tag = {"pass": "[PASS]", "fail": "[FAIL]", "warn": "[WARN]", "info": "[INFO]"}.get(status, "[INFO]")
        print(f"{status_tag} {category} — {message}")
        if status == "fail" and fix:
            fix_map.setdefault(category, [])
            fix_map[category].append(fix)

    # --- Verdict (Phase 53: DOCTOR-04) ---
    has_fail = any(status == "fail" for _, status, _, _ in checks)
    has_warn = any(status == "warn" for _, status, _, _ in checks)

    if has_fail:
        verdict = "FAIL"
    elif has_warn:
        verdict = "WARN"
    else:
        verdict = "OK"

    # Disable color when output is piped
    if sys.stdout.isatty():
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        RED = "\033[91m"
        RESET = "\033[0m"
    else:
        GREEN = YELLOW = RED = RESET = ""

    # Determine recommended next action
    fail_categories = set()
    for cat, status, _, fix in checks:
        if status == "fail" and fix:
            fail_categories.add(cat)

    if "PaperForge 包" in fail_categories and not bool(fail_categories - {"PaperForge 包"}):
        next_action = "Recommended: run pip install via the resolved interpreter"
    elif "Python 环境" in fail_categories or "Python 环境 (插件)" in fail_categories:
        next_action = "Recommended: install/upgrade Python to 3.10+"
    elif "Vault 结构" in fail_categories or "Config Migration" in fail_categories:
        next_action = "Recommended: run `paperforge sync`"
    elif "OCR 配置" in fail_categories:
        next_action = "Recommended: configure PADDLEOCR_API_TOKEN in .env"
    elif "BBT 导出" in fail_categories:
        next_action = "Recommended: configure Better BibTeX auto-export"
    elif "Zotero 链接" in fail_categories or "Path Resolution" in fail_categories:
        next_action = "Recommended: create Zotero junction"
    elif has_warn:
        next_action = "Recommended: `paperforge doctor` indicates warnings - review above"
    else:
        next_action = "Recommended: `paperforge sync` to ensure index is current"

    separator = "=" * 40
    print(f"\n{separator}")

    if verdict == "OK":
        tag = f"{GREEN}[OK]{RESET}"
    elif verdict == "WARN":
        tag = f"{YELLOW}[WARN]{RESET}"
    else:
        tag = f"{RED}[FAIL]{RESET}"

    print(f"{tag} 诊断结论")
    print(f"{next_action}")
    print(f"{separator}\n")

    if fix_map:
        print("修复步骤:")
        for cat, fixes in fix_map.items():
            for f in fixes:
                print(f"  - {cat}: {f}")
        print()

    return 1 if has_fail else 0


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


def run_status(vault: Path, verbose: bool = False, json_output: bool = False) -> int:
    """Print a compact Lite install/runtime status."""
    import json as _json

    paths = pipeline_paths(vault)
    cfg = load_vault_config(vault)
    config = load_domain_config(paths)

    # Phase 25: read canonical index summary (falls back gracefully)
    try:
        from paperforge.worker.asset_index import summarize_index

        summary = summarize_index(vault)
    except Exception:
        summary = None
    ensure_base_views(vault, paths, config)
    export_files = sorted(paths["exports"].glob("*.json"))
    record_count = (
        sum(1 for p in paths["literature"].rglob("*.md") if p.name not in ("fulltext.md", "deep-reading.md", "discussion.md"))
        if paths["literature"].exists()
        else 0
    )
    note_count = sum(1 for _ in paths["literature"].rglob("*.md")) if paths["literature"].exists() else 0
    base_count = sum(1 for _ in paths["bases"].glob("*.base")) if paths["bases"].exists() else 0
    ocr_done = 0
    ocr_total = 0
    ocr_pending = 0
    ocr_processing = 0
    ocr_failed = 0
    # Count from formal notes — picks up do_ocr:true items before meta.json exists
    do_ocr_keys: set[str] = set()
    if paths["literature"].exists():
        for note_path in paths["literature"].rglob("*.md"):
            if note_path.name in ("fulltext.md", "deep-reading.md", "discussion.md"):
                continue
            try:
                text = note_path.read_text(encoding="utf-8")
                if re.search(r"^do_ocr:\s*true\s*$", text, re.MULTILINE):
                    m = re.search(r"^zotero_key:\s*(\S+)", text, re.MULTILINE)
                    if m:
                        do_ocr_keys.add(m.group(1))
            except Exception:
                continue
    ocr_total += len(do_ocr_keys)
    # Check meta.json for each do_ocr key
    for key in do_ocr_keys:
        meta_path = paths["ocr"] / key / "meta.json"
        if not meta_path.exists():
            ocr_pending += 1
            continue
        try:
            meta = read_json(meta_path)
        except Exception:
            ocr_failed += 1
            continue
        status = str(meta.get("ocr_status", "")).strip().lower()
        if status == "done":
            ocr_done += 1
        elif status in ("queued", "running", "processing"):
            ocr_processing += 1
        elif status == "pending":
            ocr_pending += 1
        else:
            ocr_failed += 1
    # Also count any extra meta.jsons that aren't in do_ocr keys (e.g. legacy items)
    if paths["ocr"].exists():
        for meta_path in paths["ocr"].glob("*/meta.json"):
            try:
                meta = read_json(meta_path)
            except Exception:
                ocr_failed += 1
                continue
            if str(meta.get("zotero_key", "")).strip() in do_ocr_keys:
                continue
            ocr_total += 1
            status = str(meta.get("ocr_status", "")).strip().lower()
            if status == "done":
                ocr_done += 1
            elif status in ("queued", "running", "processing"):
                ocr_processing += 1
            elif status == "pending":
                ocr_pending += 1
            else:
                ocr_failed += 1
    env_paths = [vault / ".env", paths["pipeline"] / ".env"]
    env_found = [str(path.relative_to(vault)).replace("\\", "/") for path in env_paths if path.exists()]

    # Count path errors from formal notes
    path_error_count = 0
    if paths["literature"].exists():
        for note_path in paths["literature"].rglob("*.md"):
            if note_path.name in ("fulltext.md", "deep-reading.md", "discussion.md"):
                continue
            try:
                text = note_path.read_text(encoding="utf-8")
                if re.search(r'^path_error:\s*"(.+?)"\s*$', text, re.MULTILINE):
                    path_error_count += 1
            except Exception:
                continue

    # Phase 25: index-derived aggregates (empty dict when index unavailable)
    lifecycle_level_counts = {}
    health_aggregate = {}
    maturity_distribution = {}
    if summary is not None:
        lifecycle_level_counts = summary["lifecycle_level_counts"]
        health_aggregate = summary["health_aggregate"]
        maturity_distribution = summary["maturity_distribution"]

    if json_output:
        data = {
            "version": __import__("paperforge").__version__,
            "vault": str(vault),
            "system_dir": cfg["system_dir"],
            "resources_dir": cfg["resources_dir"],
            "exports": len(export_files),
            "domains": len(config.get("domains", [])),
            "total_papers": record_count,
            "formal_notes": note_count,
            "bases": base_count,
            "ocr": {
                "total": ocr_total,
                "pending": ocr_pending,
                "processing": ocr_processing,
                "done": ocr_done,
                "failed": ocr_failed,
            },
            "path_errors": path_error_count,
            "env_configured": len(env_found) > 0,
            # Phase 25: lifecycle/health/maturity from canonical index ({} when unavailable)
            "lifecycle_level_counts": lifecycle_level_counts,
            "health_aggregate": health_aggregate,
            "maturity_distribution": maturity_distribution,
        }
        print(_json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    print("PaperForge status")
    print(f"- vault: {vault}")
    print(f"- system_dir: {cfg['system_dir']}")
    print(f"- resources_dir: {cfg['resources_dir']}")
    print(f"- literature_dir: {cfg['literature_dir']}")
    print(f"- control_dir: {cfg['control_dir']}")
    print(f"- exports: {len(export_files)} JSON file(s)")
    print(f"- domains: {len(config.get('domains', []))}")
    print(f"- formal_notes: {record_count}")
    print(f"- formal_notes: {note_count}")
    print(f"- bases: {base_count}")
    # Phase 25: index section (only when canonical index available)
    if summary is not None:
        lc = lifecycle_level_counts
        print(f"- index: {summary['paper_count']} papers")
        print(f"  lifecycle: indexed={lc['indexed']} pdf_ready={lc['pdf_ready']} "
              f"fulltext_ready={lc['fulltext_ready']} deep_read={lc['deep_read_done']} "
              f"ai_ready={lc['ai_context_ready']}")
        ha = health_aggregate
        print(f"  health: pdf={ha['pdf_health']['healthy']}/{ha['pdf_health']['unhealthy']} "
              f"ocr={ha['ocr_health']['healthy']}/{ha['ocr_health']['unhealthy']} "
              f"note={ha['note_health']['healthy']}/{ha['note_health']['unhealthy']} "
              f"asset={ha['asset_health']['healthy']}/{ha['asset_health']['unhealthy']}")
    print(f"- ocr: {ocr_done}/{ocr_total} done (pending: {ocr_pending}, processing: {ocr_processing}, failed: {ocr_failed})")
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

UPDATEABLE_PATHS = ["command", "scripts", "paperforge/skills", "paperforge/plugin"]
