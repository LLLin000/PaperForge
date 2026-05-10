#!/usr/bin/env python3
"""
PaperForge Setup Wizard (Headless-Only)
=============================================
Headless-only setup wizard. Textual TUI removed.
Use `--headless` flag for non-interactive setup.

Usage:
    python setup_wizard.py --vault /path/to/vault
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from paperforge import __version__

# Backward-compat imports (v2.1 modular setup)
from paperforge.setup.checker import SetupChecker
from paperforge.setup.config_writer import ConfigWriter

if sys.platform == "win32":
    import winreg
else:
    winreg = None

# [Textual TUI removed — headless-only setup]

# =============================================================================
# Agent Platform Configurations
# =============================================================================

from paperforge.services.skill_deploy import AGENT_SKILL_DIRS

AGENT_NAMES = {
    "opencode":       "OpenCode",
    "claude":         "Claude Code",
    "codex":          "Codex",
    "cursor":         "Cursor",
    "windsurf":       "Windsurf",
    "github_copilot": "GitHub Copilot",
    "cline":          "Cline",
    "augment":        "Augment",
    "trae":           "Trae",
}


# =============================================================================
# Detection Logic (unchanged from previous version)
# =============================================================================


class CheckResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.detail = ""
        self.action_required = False


class EnvChecker:
    """环境检测器"""

    def __init__(self, vault: Path):
        self.vault = vault
        self.manual_zotero_path: Path | None = None
        self.system_dir: str = "System"  # 可由用户自定义
        self.results: dict[str, CheckResult] = {
            "python": CheckResult("Python 版本"),
            "vault": CheckResult("Vault 结构"),
            "zotero": CheckResult("Zotero 安装"),
            "bbt": CheckResult("Better BibTeX"),
            "json": CheckResult("JSON 导出"),
        }

    def get_exports_dir(self) -> Path:
        """Get exports directory based on user config."""
        return self.vault / self.system_dir / "PaperForge" / "exports"

    def check_python(self) -> CheckResult:
        r = self.results["python"]
        v = sys.version_info
        if v >= (3, 10):
            r.passed = True
            r.detail = f"Python {v.major}.{v.minor}.{v.micro}"
        else:
            r.passed = False
            r.detail = f"Python {v.major}.{v.minor}.{v.micro} (需要 >= 3.10)"
            r.action_required = True
        return r

    def check_dependencies(self) -> CheckResult:
        r = CheckResult("Python 依赖")
        required = {"requests": "requests", "pymupdf": "fitz", "PIL": "PIL"}
        missing = []
        for pkg, import_name in required.items():
            try:
                __import__(import_name)
            except ImportError:
                missing.append(pkg)
        if not missing:
            r.passed = True
            r.detail = "所有依赖已安装 (requests, pymupdf, pillow)"
        else:
            r.passed = False
            r.detail = f"缺少依赖: {', '.join(missing)}"
            r.action_required = True
        return r

    def install_dependencies(self) -> bool:
        deps = ["requests", "pymupdf", "pillow"]
        try:
            subprocess.run([sys.executable, "-m", "pip", "install"] + deps, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def check_vault(self) -> CheckResult:
        r = self.results["vault"]
        required = [
            f"{self.system_dir}/PaperForge/exports",
            f"{self.system_dir}/PaperForge/ocr",
        ]
        missing = [rel for rel in required if not (self.vault / rel).exists()]
        if not missing:
            r.passed = True
            r.detail = "所有必要目录已就绪"
        else:
            r.passed = False
            r.detail = f"缺少: {', '.join(missing)}"
            r.action_required = True
        return r

    def _find_zotero(self, manual_path: Path | None = None) -> Path | None:
        # 如果提供了手动路径，优先使用
        if manual_path and manual_path.exists():
            return manual_path

        system = platform.system()
        if system == "Windows":
            # ...existing detection code...
            # 1. 注册表检测 (HKEY_LOCAL_MACHINE)
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Zotero") as key:
                    install_dir, _ = winreg.QueryValueEx(key, "InstallDir")
                    path = Path(install_dir) / "zotero.exe"
                    if path.exists():
                        return path
            except (FileNotFoundError, OSError):
                pass
            # 2. 注册表检测 (HKEY_CURRENT_USER - 用户级安装)
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Zotero") as key:
                    install_dir, _ = winreg.QueryValueEx(key, "InstallDir")
                    path = Path(install_dir) / "zotero.exe"
                    if path.exists():
                        return path
            except (FileNotFoundError, OSError):
                pass
            # 3. 常见安装路径检测
            search_paths = [
                Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Zotero" / "zotero.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Zotero" / "zotero.exe",
                Path(os.environ.get("LOCALAPPDATA", r"C:\Users\%USERNAME%\AppData\Local")) / "Zotero" / "zotero.exe",
                Path.home() / "AppData" / "Local" / "Zotero" / "zotero.exe",
                Path.home() / "scoop" / "apps" / "zotero" / "current" / "zotero.exe",  # Scoop安装
            ]
            for p in search_paths:
                if p.exists():
                    return p
            # 4. 通过 where 命令检测
            try:
                result = subprocess.run(["where", "zotero"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        p = Path(line.strip())
                        if p.exists():
                            return p
            except Exception:
                pass
        elif system == "Darwin":
            search_paths = [
                Path("/Applications/Zotero.app/Contents/MacOS/zotero"),
                Path.home() / "Applications" / "Zotero.app" / "Contents" / "MacOS" / "zotero",
            ]
            for p in search_paths:
                if p.exists():
                    return p
            # 通过 which 检测
            try:
                result = subprocess.run(["which", "zotero"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return Path(result.stdout.strip())
            except Exception:
                pass
        else:
            # Linux
            search_paths = [
                Path.home() / ".local" / "share" / "zotero" / "zotero",
                Path("/usr/bin/zotero"),
                Path("/usr/local/bin/zotero"),
                Path("/snap/bin/zotero"),
            ]
            for p in search_paths:
                if p.exists():
                    return p
            try:
                result = subprocess.run(["which", "zotero"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return Path(result.stdout.strip())
            except Exception:
                pass
        return None

    def check_zotero(self, manual_path: Path | None = None) -> CheckResult:
        r = self.results["zotero"]
        path = self._find_zotero(manual_path)
        if path:
            r.passed = True
            r.detail = str(path)
        else:
            r.passed = False
            r.detail = "未找到 Zotero"
            r.action_required = True
        return r

    def _looks_like_bbt(self, name: str) -> bool:
        """Match Better BibTeX by normalizing extension name.

        Works for both Zotero 7 (.xpi files) and Zotero 6 (unpacked directories).
        """
        normalized = "".join(c for c in name.lower() if c.isalnum())
        return "betterbibtex" in normalized

    def _scan_extensions_dir(self, ext_dir: Path) -> tuple[bool, str | None]:
        """Scan an extensions/ directory (or profile root) for Better BibTeX."""
        if not ext_dir.is_dir():
            return False, None
        try:
            for entry in ext_dir.iterdir():
                if self._looks_like_bbt(entry.name):
                    return True, entry.name
        except OSError:
            pass
        return False, None

    def check_bbt(self, manual_path: Path | None = None) -> CheckResult:
        r = self.results["bbt"]
        system = platform.system()

        # 1) Platform-specific profiles paths (most reliable — scan first)
        profile_roots: list[Path] = []
        if system == "Windows":
            appdata = os.environ.get("APPDATA", "")
            if appdata:
                profile_roots.append(Path(appdata) / "Zotero" / "Zotero" / "Profiles")
        elif system == "Darwin":
            profile_roots.append(Path.home() / "Library" / "Application Support" / "Zotero" / "Profiles")
        else:  # Linux
            profile_roots.append(Path.home() / ".zotero" / "zotero")

        # 2) User-configured zotero_data_dir (may also have a Profiles/ subtree)
        if manual_path and manual_path.exists():
            manual_profiles = manual_path / "Profiles"
            if manual_profiles.is_dir():
                profile_roots.append(manual_profiles)

        for profiles in profile_roots:
            if not profiles.is_dir():
                continue
            try:
                for profile in profiles.iterdir():
                    if not profile.is_dir():
                        continue
                    # Zotero 7 / standard: extensions/ folder with .xpi files
                    ext_dir = profile / "extensions"
                    found, name = self._scan_extensions_dir(ext_dir)
                    if found:
                        r.passed = True
                        r.detail = name
                        return r
                    # Zotero 6 fallback: extensions unpacked directly in profile
                    found, name = self._scan_extensions_dir(profile)
                    if found:
                        r.passed = True
                        r.detail = name
                        return r
            except OSError:
                continue

        r.passed = False
        r.detail = "未找到 Better BibTeX 插件"
        r.action_required = True
        return r

    def check_json(self) -> CheckResult:
        r = self.results["json"]
        exports_dir = self.get_exports_dir()
        if not exports_dir.exists():
            r.passed = False
            r.detail = f"导出目录不存在: {exports_dir}"
            r.action_required = True
            return r

        json_files = list(exports_dir.glob("*.json"))
        if not json_files:
            r.passed = False
            r.detail = "未找到 JSON 导出文件"
            r.action_required = True
            return r

        valid = []
        for jf in json_files:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                # Better BibTeX JSON 是 dict 格式（含 items），也兼容 list 格式
                if isinstance(data, dict) and data.get("items") or isinstance(data, list) and len(data) > 0:
                    valid.append(jf.name)
            except Exception:
                pass

        if valid:
            r.passed = True
            r.detail = f"找到 {len(valid)} 个有效 JSON"
        else:
            r.passed = False
            r.detail = "JSON 文件格式无效"
            r.action_required = True
        return r


# [TUI step classes removed]


def _find_vault() -> Path | None:
    """Find vault by looking for paperforge.json in current or parent dirs."""
    current = Path(".").resolve()
    for path in [current, *current.parents]:
        if (path / "paperforge.json").exists():
            return path
    return None


def _copy_file_incremental(src: Path, dst: Path) -> bool:
    """Copy a file only when the destination is missing."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return False
    shutil.copy2(src, dst)
    return True


def _copy_tree_incremental(src_dir: Path, dst_dir: Path) -> tuple[int, int]:
    """Copy an entire tree without overwriting existing files."""
    created = 0
    skipped = 0
    for src in src_dir.rglob("*"):
        rel = src.relative_to(src_dir)
        dst = dst_dir / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        if _copy_file_incremental(src, dst):
            created += 1
        else:
            skipped += 1
    return created, skipped


def _merge_env_incremental(env_path: Path, values: dict[str, str]) -> str:
    """Create .env if missing, otherwise append only missing keys."""
    lines = [
        "# PaperForge configuration",
        f"PADDLEOCR_API_TOKEN={values['PADDLEOCR_API_TOKEN']}",
        f"PADDLEOCR_JOB_URL={values['PADDLEOCR_JOB_URL']}",
        f"PADDLEOCR_MODEL={values['PADDLEOCR_MODEL']}",
    ]
    if "ZOTERO_DATA_DIR" in values:
        lines.append(f"ZOTERO_DATA_DIR={values['ZOTERO_DATA_DIR']}")

    if not env_path.exists():
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return "created"

    existing_text = env_path.read_text(encoding="utf-8")
    existing_keys = {
        line.split("=", 1)[0].strip()
        for line in existing_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#") and "=" in line
    }
    missing_lines = [f"{key}={value}" for key, value in values.items() if key not in existing_keys]
    if not missing_lines:
        return "preserved"

    suffix = "\n".join(missing_lines) + "\n"
    if existing_text and not existing_text.endswith("\n"):
        existing_text += "\n"
    if existing_text.strip():
        existing_text += "\n"
    env_path.write_text(existing_text + suffix, encoding="utf-8")
    return "extended"


def headless_setup(
    vault: Path,
    agent_key: str = "opencode",
    paddleocr_key: str | None = None,
    paddleocr_url: str = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
    system_dir: str = "System",
    resources_dir: str = "Resources",
    literature_dir: str = "Literature",
    base_dir: str = "Bases",
    zotero_data: str | None = None,
    skip_checks: bool = False,
    repo_root: Path | None = None,
) -> int:
    """Run PaperForge setup non-interactively (no Textual TUI).

    Designed for AI agents and automated scripts. Returns 0 on success,
    non-zero on failure with error messages on stderr.

    Args:
        vault: Path to Obsidian vault root.
        agent_key: AI agent platform key (opencode, cursor, claude, etc.)
        paddleocr_key: PaddleOCR API token.
        paddleocr_url: PaddleOCR API URL.
        system_dir: System directory name.
        resources_dir: Resources directory name.
        literature_dir: Literature subdirectory name.
        base_dir: Base directory name.
        zotero_data: Zotero data directory (auto-detect if None).
        skip_checks: Skip environment validation.
        repo_root: Path to PaperForge package root (auto-detect if None).

    Returns:
        int: 0 on success, non-zero on failure.
    """
    vault = Path(vault).expanduser().resolve()

    # Determine repo_root (where paperforge package sources live)
    if repo_root is None:
        wizard_dir = Path(__file__).parent.resolve()
        if wizard_dir / "paperforge" if wizard_dir.name != "paperforge" else False:
            _repo = wizard_dir
        elif (wizard_dir.parent / "paperforge").exists():
            _repo = wizard_dir.parent
        elif wizard_dir.name == "paperforge" and (wizard_dir / "__init__.py").exists():
            _repo = wizard_dir.parent
        else:
            _repo = wizard_dir.parent
        repo_root = _repo

    if not (repo_root / "paperforge").exists():
        print(f"Error: cannot find PaperForge package root (tried: {repo_root})", file=sys.stderr)
        return 1

    # Agent config
    skill_dir = AGENT_SKILL_DIRS.get(agent_key)
    if not skill_dir:
        print(f"Error: unknown agent platform '{agent_key}'", file=sys.stderr)
        return 1
    agent_name = AGENT_NAMES.get(agent_key, agent_key)

    print(f"[*] PaperForge headless setup")
    print(f"    Vault:    {vault}")
    print(f"    Agent:    {agent_name}")
    print(f"    System:   {system_dir}")
    print(f"    Resources: {resources_dir}")

    # =========================================================================
    # Phase 1: Pre-flight checks (BLOCKING — must pass to continue)
    # =========================================================================
    checker = EnvChecker(vault)
    checker.system_dir = system_dir

    if not skip_checks:
        print("[*] Phase 1: Pre-flight checks...")

        py = checker.check_python()
        if not py.passed:
            print(f"[FAIL] {py.detail}", file=sys.stderr)
            return 2
        print(f"    [OK] {py.detail}")

        deps = checker.check_dependencies()
        if not deps.passed:
            print(f"[FAIL] {deps.detail}", file=sys.stderr)
            print(f"[FIX] pip install requests pymupdf pillow", file=sys.stderr)
            return 3
        print(f"    [OK] {deps.detail}")

    # =========================================================================
    # Phase 2: Create directories
    # =========================================================================
    print("[*] Phase 2: Creating directories...")
    pf_path = vault / system_dir / "PaperForge"
    dirs = [
        pf_path / "exports",
        pf_path / "ocr",
        pf_path / "config",
        pf_path / "worker/scripts",
        vault / resources_dir / literature_dir,
        vault / base_dir,
        vault / ".obsidian" / "plugins" / "paperforge",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print(f"    [OK] {len(dirs)} directories ready")

    # Zotero junction (creates <system_dir>/Zotero -> actual Zotero data dir)
    if zotero_data and zotero_data.strip():
        zotero_link_path = vault / system_dir / "Zotero"
        if not zotero_link_path.exists():
            try:
                zotero_link_path.parent.mkdir(parents=True, exist_ok=True)
                if sys.platform == "win32":
                    result = subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(zotero_link_path), str(zotero_data)],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.returncode != 0:
                        print(f"    [WARN] Zotero junction failed: {result.stderr.strip()}")
                        print(f"    手动创建: mklink /J {zotero_link_path} {zotero_data}")
                    else:
                        print(f"    [OK] Zotero junction created")
                        print(f"        {zotero_data} -> {zotero_link_path}")
                else:
                    zotero_link_path.symlink_to(zotero_data, target_is_directory=True)
                    print(f"    [OK] Zotero symlink created")
            except Exception as e:
                print(f"    [WARN] Zotero junction failed: {e}")

    # =========================================================================
    # Phase 3: Informational checks (NON-BLOCKING — warnings only)
    # =========================================================================
    built_vault_config = {
        "system_dir": system_dir,
        "resources_dir": resources_dir,
        "literature_dir": literature_dir,
        "base_dir": base_dir,
    }

    if not skip_checks:
        print("[*] Phase 3: Environment checks (non-blocking)...")

        manual_zotero_path = Path(zotero_data).expanduser() if zotero_data else None

        zot = checker.check_zotero(manual_zotero_path)
        if zot.passed:
            print(f"    [OK] Zotero: {zot.detail}")
        else:
            print(f"    [WARN] Zotero not found — install from https://zotero.org")
            print(f"    {zot.detail}")

        bbt = checker.check_bbt(manual_zotero_path)
        if bbt.passed:
            print(f"    [OK] Better BibTeX: {bbt.detail}")
        else:
            print(f"    [WARN] Better BibTeX not found")
            print(f"    Install from: https://retorque.re/zotero-better-bibtex/")

        # JSON export check — only after exports/ dir exists
        json_check = checker.check_json()
        if json_check.passed:
            print(f"    [OK] JSON exports: {json_check.detail}")
        else:
            print(f"    [WARN] {json_check.detail}")
            zotero_data_hint = zotero_data or "<你的Zotero数据目录>"
            if sys.platform == "win32":
                print(f"    首次安装需要配置 BBT 自动导出：")
                print(f"    1. 在 Zotero 中右键要同步的文献库或分类 → 导出")
                print(f"    2. 格式选择 Better BibTeX JSON")
                print(f"    3. 保存到 vault 的 {system_dir}/PaperForge/exports/")
                print(f'    4. 勾选 "保持更新"')
            else:
                print(f"    Configure BBT auto-export to: {system_dir}/PaperForge/exports/")
            print(f"    完成后运行: paperforge sync")

    # Zotero data directory detection
    if zotero_data is None and not skip_checks:
        detected = checker._find_zotero()
        if detected:
            # _find_zotero returns the .exe path; we need the data directory
            zotero_home = detected.parent.parent if detected.parent.name == "Zotero" else detected.parent
            data_candidate = Path(str(zotero_home)).parent if "Zotero" in str(zotero_home) else zotero_home
            # Common Zotero data dir: ~/Zotero on all platforms
            home_zotero = Path.home() / "Zotero"
            if home_zotero.exists() and (home_zotero / "zotero.sqlite").exists():
                zotero_data = str(home_zotero)
                print(f"    [OK] Zotero data detected: {zotero_data}")

    # =========================================================================
    # Phase 4: Deploy files
    # =========================================================================
    print("[*] Phase 4: Deploying files...")
    import shutil

    # Worker scripts
    worker_src = repo_root / "paperforge/worker/sync.py"
    worker_dst = pf_path / "worker/scripts/sync.py"
    if not worker_src.exists():
        print(f"Error: worker script not found: {worker_src}", file=sys.stderr)
        return 4

    _copy_file_incremental(worker_src, worker_dst)
    for mod in [
        "ocr.py",
        "repair.py",
        "status.py",
        "deep_reading.py",
        "update.py",
        "base_views.py",
        "__init__.py",
        "_utils.py",
        "_progress.py",
        "_retry.py",
    ]:
        mod_src = repo_root / "paperforge/worker" / mod
        if mod_src.exists():
            _copy_file_incremental(mod_src, pf_path / "worker/scripts" / mod)
    print(f"    [OK] worker scripts")

    # Deploy skills via shared service (single source of truth)
    from paperforge.services.skill_deploy import deploy_skills as _deploy_skills_service

    skill_result = _deploy_skills_service(
        vault=vault,
        agent_key=agent_key,
        overwrite=False,
    )
    if skill_result["skill_deployed"]:
        print(f"    [OK] literature-qa skill deployed")
    for err in skill_result.get("errors", []):
        print(f"    [WARN] {err}")

    # AGENTS.md
    if skill_result["agents_md"]:
        print(f"    [OK] AGENTS.md")
    else:
        print(f"    [WARN] AGENTS.md source not found; skipping")

    # Create agent config file if defined (e.g., Claude skills.json)
    # Only a few platforms need stub configs; most auto-discover skills via directory
    AGENT_CONFIG_FILES = {
        "claude": ".claude/skills.json",
        "cursor": ".cursor/settings.json",
    }
    config_file = AGENT_CONFIG_FILES.get(agent_key)
    if config_file:
        config_dst = vault / config_file
        if not config_dst.exists():
            try:
                config_dst.parent.mkdir(parents=True, exist_ok=True)
                if config_file.endswith(".json"):
                    config_dst.write_text("{}\n", encoding="utf-8")
                else:
                    config_dst.write_text("", encoding="utf-8")
                print(f"    [OK] {config_file}")
            except OSError:
                pass

    # Docs are developer-facing and not installed to user vaults

    # Obsidian plugin
    plugin_src = repo_root / "paperforge/plugin"
    plugin_dst = vault / ".obsidian" / "plugins" / "paperforge"
    PLUGIN_FILES = {"main.js", "styles.css", "manifest.json", "versions.json", "i18n.js"}
    if plugin_src.exists() and plugin_src.is_dir():
        created = 0
        skipped = 0
        for name in PLUGIN_FILES:
            f = plugin_src / name
            if not f.exists():
                skipped += 1
                continue
            if _copy_file_incremental(f, plugin_dst / f.name):
                created += 1
            else:
                skipped += 1
        print(f"    [OK] Obsidian plugin (created {created}, preserved {skipped})")
    else:
        print(f"    [WARN] Plugin source not found: {plugin_src}")

    # =========================================================================
    # Phase 5: Create config files
    # =========================================================================
    print("[*] Phase 5: Creating config files...")

    # .env
    raw_key = paddleocr_key or os.environ.get("PADDLEOCR_API_TOKEN", "").strip()
    env_status = _merge_env_incremental(
        vault / ".env",
        {
            "PADDLEOCR_API_TOKEN": raw_key,
            "PADDLEOCR_JOB_URL": paddleocr_url,
            "PADDLEOCR_MODEL": "PaddleOCR-VL-1.5",
            "ZOTERO_DATA_DIR": zotero_data or "",
        },
    )
    print(f"    [OK] .env ({env_status})")

    # Domain config (populated from whatever JSONs already exist in exports/)
    domain_config = pf_path / "config" / "domain-collections.json"
    if not domain_config.exists():
        export_domains = [
            {"domain": f.stem, "export_file": f.name, "allowed_collections": []}
            for f in sorted((pf_path / "exports").glob("*.json"))
        ]
        domain_config.write_text(
            json.dumps({"domains": export_domains}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    print(f"    [OK] domain-collections.json")

    # paperforge.json -- canonical format: path keys only in vault_config block
    pf_json = vault / "paperforge.json"
    existing_config = {}
    if pf_json.exists():
        try:
            existing_config = json.loads(pf_json.read_text(encoding="utf-8"))
        except Exception:
            existing_config = {}
    config = {
        "version": existing_config.get("version", __version__),
        "schema_version": "2",
        "agent_platform": agent_name,
        "agent_key": agent_key,
        "skill_dir": skill_dir,
        "paperforge_path": f"{system_dir}/PaperForge",
        "zotero_data_dir": zotero_data or "",
        "zotero_link": f"{system_dir}/Zotero",
        "vault_config": built_vault_config,
    }
    pf_json.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"    [OK] paperforge.json")

    # Phase 6: pip install — always upgrade
    print("[*] Phase 6: Installing/upgrading paperforge CLI...")
    try:
        try:
            import paperforge as _pf

            current_ver = getattr(_pf, "__version__", "?")
        except ImportError:
            current_ver = "not installed"
        # If repo_root is the source repository (has pyproject.toml), install from it.
        # Otherwise (site-packages copy) install from GitHub tagged release.
        if (repo_root / "pyproject.toml").exists():
            install_target = [str(repo_root)]
        else:
            from paperforge import __version__ as _pv

            install_target = [f"git+https://github.com/LLLin000/PaperForge.git@{_pv}"]
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade"] + install_target,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            _new = subprocess.run(
                [sys.executable, "-c", "import paperforge; print(getattr(paperforge, '__version__', '?'))"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            new_ver = _new.stdout.strip() or "?"
            print(f"    [OK] paperforge {current_ver} -> {new_ver}")
        else:
            stderr_short = result.stderr[:200] if result.stderr else ""
            print(f"    [WARN] pip install failed: {stderr_short}", file=sys.stderr)
    except Exception as e:
        print(f"    [WARN] pip install skipped: {e}")

    # =========================================================================
    # Phase 7: Verify
    # =========================================================================
    print("[*] Phase 7: Verifying installation...")
    checks = {
        "Worker scripts": worker_dst.exists(),
        "Skill files": len(imported_skills) > 0,
        "Base dir": (vault / base_dir).exists(),
        "Exports dir": (pf_path / "exports").exists(),
        "OCR dir": (pf_path / "ocr").exists(),
        "paperforge.json": pf_json.exists(),
        "Obsidian plugin": (vault / ".obsidian" / "plugins" / "paperforge" / "main.js").exists(),
        "AGENTS.md": (vault / "AGENTS.md").exists(),
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"[FAIL] Missing: {', '.join(failed)}", file=sys.stderr)
        return 6

    print(f"    [OK] All {len(checks)} checks passed")

    # =========================================================================
    # Done
    # =========================================================================
    print()
    print("=" * 60)
    print(f"  PaperForge v{__version__} installation complete!")
    print("=" * 60)
    print()
    print("Safety note:")
    print("  Existing files in the target vault were preserved; setup only created missing files and folders.")
    print()
    print("Next steps:")
    print(
        f"  1. In Zotero, export the library or a collection as Better BibTeX JSON into: {vault / system_dir / 'PaperForge' / 'exports'}"
    )
    print("     Enable 'Keep updated' so Zotero keeps the JSON in sync.")
    print("  2. Open Obsidian → Settings → Community Plugins → Enable 'PaperForge'")
    print("  3. Press Ctrl+P and type 'PaperForge' to open the dashboard")
    print()
    print("First-run workflow:")
    print("  4. Add papers to Zotero, then run: paperforge sync")
    print("  5. In Obsidian Base view, mark do_ocr:true, then run: paperforge ocr")
    print("  6. After OCR done, mark analyze:true in Base view")
    print("  7. Use /pf-deep <key> in your AI agent for deep reading")
    print()

    return 0


def main(argv: list[str] | None = None) -> int:
    """Print help message — Textual TUI removed."""
    print("=" * 60)
    print("  PaperForge Setup Wizard")
    print("=" * 60)
    print()
    print("The interactive Textual TUI has been removed.")
    print()
    print("To run setup non-interactively, use:")
    print("  paperforge setup --headless")
    print()
    print("Or configure PaperForge via the Obsidian plugin settings tab:")
    print("  1. Open Obsidian → Settings → Community Plugins → PaperForge")
    print("  2. Fill in your configuration")
    print("  3. Click 'Install'")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
