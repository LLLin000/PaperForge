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

if sys.platform == "win32":
    import winreg
else:
    winreg = None

# [Textual TUI removed — headless-only setup]

# =============================================================================
# Agent Platform Configurations
# =============================================================================

AGENT_CONFIGS = {
    "opencode": {
        "name": "OpenCode",
        "skill_dir": ".opencode/skills",
        "command_dir": ".opencode/command",
        "format": "flat_command",
        "prefix": "/",
        "config_file": None,
    },
    "claude": {
        "name": "Claude Code",
        "skill_dir": ".claude/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": ".claude/skills.json",
    },
    "codex": {
        "name": "Codex",
        "skill_dir": ".codex/skills",
        "format": "skill_directory",
        "prefix": "$",
        "config_file": None,
    },
    "cursor": {
        "name": "Cursor",
        "skill_dir": ".cursor/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": ".cursor/settings.json",
    },
    "windsurf": {
        "name": "Windsurf",
        "skill_dir": ".windsurf/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": None,
    },
    "github_copilot": {
        "name": "GitHub Copilot",
        "skill_dir": ".github/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": ".github/copilot-instructions.md",
    },
    "cline": {
        "name": "Cline",
        "skill_dir": ".clinerules",
        "format": "rules_file",
        "prefix": "/",
        "config_file": ".clinerules",
    },
    "augment": {
        "name": "Augment",
        "skill_dir": ".augment/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": None,
    },
    "trae": {
        "name": "Trae",
        "skill_dir": ".trae/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": None,
    },
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

    def check_bbt(self, manual_path: Path | None = None) -> CheckResult:
        r = self.results["bbt"]
        system = platform.system()
        bbt_found = False
        bbt_path = None

        if manual_path and manual_path.exists():
            direct_candidates = [
                manual_path / "better-bibtex",
                manual_path / "extensions",
                manual_path / "Profiles",
            ]
            for candidate in direct_candidates:
                if not candidate.exists():
                    continue
                if candidate.name == "better-bibtex":
                    bbt_found = True
                    bbt_path = candidate
                    break
                if candidate.name == "extensions":
                    for entry in candidate.iterdir():
                        if entry.name.startswith("better-bibtex"):
                            bbt_found = True
                            bbt_path = entry
                            break
                if candidate.name == "Profiles":
                    for profile in candidate.iterdir():
                        ext_dir = profile / "extensions"
                        if ext_dir.exists():
                            for entry in ext_dir.iterdir():
                                if entry.name.startswith("better-bibtex"):
                                    bbt_found = True
                                    bbt_path = entry
                                    break
                        if bbt_found:
                            break
                if bbt_found:
                    break

        if system == "Windows" and not bbt_found:
            appdata = os.environ.get("APPDATA", "")
            if appdata:
                profiles = Path(appdata) / "Zotero" / "Zotero" / "Profiles"
                if profiles.exists():
                    for profile in profiles.iterdir():
                        if profile.is_dir():
                            ext_dir = profile / "extensions"
                            if ext_dir.exists():
                                for ext in ext_dir.iterdir():
                                    if "better-bibtex" in ext.name.lower() or "betterbibtex" in ext.name.lower():
                                        bbt_found = True
                                        bbt_path = ext
                                        break
        elif system == "Darwin":
            profiles = Path.home() / "Library" / "Application Support" / "Zotero" / "Profiles"
            if profiles.exists():
                for profile in profiles.iterdir():
                    ext_dir = profile / "extensions"
                    if ext_dir.exists():
                        for ext in ext_dir.iterdir():
                            if "better-bibtex" in ext.name.lower():
                                bbt_found = True
                                bbt_path = ext
                                break
        else:
            profiles = Path.home() / ".zotero" / "zotero" / "Profiles"
            if profiles.exists():
                for profile in profiles.iterdir():
                    ext_dir = profile / "extensions"
                    if ext_dir.exists():
                        for ext in ext_dir.iterdir():
                            if "better-bibtex" in ext.name.lower():
                                bbt_found = True
                                bbt_path = ext
                                break

        if bbt_found:
            r.passed = True
            r.detail = bbt_path.name if bbt_path else "Better BibTeX"
        else:
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


def _substitute_vars(
    text: str,
    system_dir: str,
    resources_dir: str,
    literature_dir: str,
    control_dir: str,
    base_dir: str,
    skill_dir: str,
    prefix: str = "/",
) -> str:
    """Substitute path variables and command prefix in skill content."""
    for old, new in [
        ("<system_dir>", system_dir),
        ("<resources_dir>", resources_dir),
        ("<literature_dir>", literature_dir),
        ("<control_dir>", control_dir),
        ("<base_dir>", base_dir),
        ("<skill_dir>", skill_dir),
        ("<prefix>", prefix),
    ]:
        text = text.replace(old, new)
    return text


def _copy_file_incremental(src: Path, dst: Path) -> bool:
    """Copy a file only when the destination is missing."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return False
    shutil.copy2(src, dst)
    return True


def _write_text_incremental(dst: Path, text: str) -> bool:
    """Write a text file only when the destination is missing."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return False
    dst.write_text(text, encoding="utf-8")
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
    missing_lines = [
        f"{key}={value}"
        for key, value in values.items()
        if key not in existing_keys
    ]
    if not missing_lines:
        return "preserved"

    suffix = "\n".join(missing_lines) + "\n"
    if existing_text and not existing_text.endswith("\n"):
        existing_text += "\n"
    if existing_text.strip():
        existing_text += "\n"
    env_path.write_text(existing_text + suffix, encoding="utf-8")
    return "extended"


def _deploy_skill_directory(
    vault: Path,
    skill_dir: str,
    repo_root: Path,
    system_dir: str,
    resources_dir: str,
    literature_dir: str,
    control_dir: str,
    base_dir: str,
    prefix: str = "/",
) -> list[str]:
    """Deploy AI-deep skills as independent SKILL.md directories (Claude Code, Codex, etc.).

    pf-deep and pf-paper are two separate skills (not one skill with two modules).
    pf-deep bundles scripts, chart-reading, and subagent prompt.
    pf-paper is a lightweight SKILL.md only.
    """
    imported = []
    src_scripts = repo_root / "paperforge" / "skills" / "literature-qa" / "scripts"
    src_charts = repo_root / "paperforge" / "skills" / "literature-qa" / "chart-reading"
    src_prompt = repo_root / "paperforge" / "skills" / "literature-qa" / "prompt_deep_subagent.md"

    # --- Deploy all pf-*.md scripts as independent skill directories ---
    # Each .md file in scripts/ becomes a skill dir with SKILL.md.
    # Special bundles (pf-deep with scripts/charts, pf-paper) handle extras below.
    for skill_file in sorted(src_scripts.glob("pf-*.md")):
        skill_name = skill_file.stem  # e.g. "pf-end"
        skill_dst = vault / skill_dir / skill_name
        skill_dst.mkdir(parents=True, exist_ok=True)
        text = skill_file.read_text(encoding="utf-8")
        text = _substitute_vars(text, system_dir, resources_dir, literature_dir, control_dir, base_dir, skill_dir, prefix)
        _write_text_incremental(skill_dst / "SKILL.md", text)
        imported.append(skill_name)

    # pf-deep extras: scripts, chart-reading, subagent prompt
    pf_deep_dst = vault / skill_dir / "pf-deep"
    pf_deep_dst.mkdir(parents=True, exist_ok=True)
    ld_src = src_scripts / "ld_deep.py"
    ld_dst = pf_deep_dst / "scripts" / "ld_deep.py"
    if ld_src.exists():
        _copy_file_incremental(ld_src, ld_dst)
    if src_prompt.exists():
        _copy_file_incremental(src_prompt, pf_deep_dst / "prompt_deep_subagent.md")
    if src_charts.exists() and src_charts.is_dir():
        chart_dst = pf_deep_dst / "chart-reading"
        chart_dst.mkdir(parents=True, exist_ok=True)
        for f in src_charts.glob("*.md"):
            _copy_file_incremental(f, chart_dst / f.name)

    return imported


def _deploy_flat_command(
    vault: Path,
    command_dir: str,
    repo_root: Path,
    system_dir: str,
    resources_dir: str,
    literature_dir: str,
    control_dir: str,
    base_dir: str,
    skill_dir: str,
) -> list[str]:
    """Deploy skills in flat .md command format (OpenCode)."""
    imported = []
    command_src = repo_root / "command"
    if not (command_src.exists() and command_src.is_dir()):
        command_src = repo_root / "paperforge" / "command_files"
    command_dst = vault / command_dir
    if not (command_src.exists() and command_src.is_dir()):
        return imported

    command_dst.mkdir(parents=True, exist_ok=True)
    for f in command_src.glob("pf-*.md"):
        text = f.read_text(encoding="utf-8")
        text = _substitute_vars(text, system_dir, resources_dir, literature_dir, control_dir, base_dir, skill_dir)
        _write_text_incremental(command_dst / f.name, text)
        imported.append(f.stem)

    return imported


def _deploy_rules_file(
    vault: Path,
    skill_dir: str,
    repo_root: Path,
    system_dir: str,
    resources_dir: str,
    literature_dir: str,
    control_dir: str,
    base_dir: str,
    skill_dir_path: str,
) -> list[str]:
    """Deploy skills as .clinerules directory with pf-deep/pf-paper subdirectories (Cline)."""
    imported = []
    src_scripts = repo_root / "paperforge" / "skills" / "literature-qa" / "scripts"
    src_charts = repo_root / "paperforge" / "skills" / "literature-qa" / "chart-reading"
    src_prompt = repo_root / "paperforge" / "skills" / "literature-qa" / "prompt_deep_subagent.md"

    # pf-deep
    pf_deep_dst = vault / skill_dir / "pf-deep"
    pf_deep_dst.mkdir(parents=True, exist_ok=True)
    ld_src = src_scripts / "ld_deep.py"
    if ld_src.exists():
        _copy_file_incremental(ld_src, pf_deep_dst / "scripts" / "ld_deep.py")
    if src_prompt.exists():
        _copy_file_incremental(src_prompt, pf_deep_dst / "prompt_deep_subagent.md")
    if src_charts.exists() and src_charts.is_dir():
        (pf_deep_dst / "chart-reading").mkdir(parents=True, exist_ok=True)
        for f in src_charts.glob("*.md"):
            _copy_file_incremental(f, pf_deep_dst / "chart-reading" / f.name)

    imported.append("clinerules")
    return imported


def headless_setup(
    vault: Path,
    agent_key: str = "opencode",
    paddleocr_key: str | None = None,
    paddleocr_url: str = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
    system_dir: str = "System",
    resources_dir: str = "Resources",
    literature_dir: str = "Literature",
    control_dir: str = "LiteratureControl",
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
        control_dir: Control subdirectory name.
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
        if (wizard_dir / "paperforge" if wizard_dir.name != "paperforge" else False):
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
    agent_config = AGENT_CONFIGS.get(agent_key)
    if not agent_config:
        print(f"Error: unknown agent platform '{agent_key}'", file=sys.stderr)
        return 1
    skill_dir = agent_config.get("skill_dir", ".opencode/skills")

    print(f"[*] PaperForge headless setup")
    print(f"    Vault:    {vault}")
    print(f"    Agent:    {agent_config['name']}")
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
                        capture_output=True, text=True, timeout=30,
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
        "control_dir": control_dir,
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
    for mod in ["ocr.py", "repair.py", "status.py", "deep_reading.py",
                "update.py", "base_views.py", "__init__.py",
                "_utils.py", "_progress.py", "_retry.py"]:
        mod_src = repo_root / "paperforge/worker" / mod
        if mod_src.exists():
            _copy_file_incremental(mod_src, pf_path / "worker/scripts" / mod)
    print(f"    [OK] worker scripts")

    # Deploy skills based on agent format
    fmt = agent_config.get("format", "skill_directory")
    prefix = agent_config.get("prefix", "/")
    imported_skills = []

    if fmt == "flat_command":
        imported_skills = _deploy_flat_command(
            vault, agent_config["command_dir"], repo_root,
            system_dir, resources_dir, literature_dir, control_dir, base_dir, skill_dir,
        )
        # OpenCode also needs the skill directory (ld_deep.py, prompt, chart-reading)
        imported_skills += _deploy_skill_directory(
            vault, skill_dir, repo_root,
            system_dir, resources_dir, literature_dir, control_dir, base_dir, prefix,
        )
    elif fmt == "rules_file":
        imported_skills = _deploy_rules_file(
            vault, agent_config["skill_dir"], repo_root,
            system_dir, resources_dir, literature_dir, control_dir, base_dir, skill_dir,
        )
    else:
        # skill_directory (default)
        imported_skills = _deploy_skill_directory(
            vault, skill_dir, repo_root,
            system_dir, resources_dir, literature_dir, control_dir, base_dir, prefix,
        )

    if imported_skills:
        print(f"    [OK] {len(imported_skills)} skill(s): {', '.join(imported_skills)}")

    # Create agent config file if defined (e.g., Claude skills.json)
    config_file = agent_config.get("config_file")
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

    # Docs
    docs_src = repo_root / "docs"
    docs_dst = vault / "docs"
    if docs_src.exists() and docs_src.is_dir():
        created, skipped = _copy_tree_incremental(docs_src, docs_dst)
        print(f"    [OK] docs (created {created}, preserved {skipped})")
    else:
        print(f"    [WARN] docs source not found: {docs_src}")

    # Obsidian plugin
    plugin_src = repo_root / "paperforge/plugin"
    plugin_dst = vault / ".obsidian" / "plugins" / "paperforge"
    if plugin_src.exists() and plugin_src.is_dir():
        created = 0
        skipped = 0
        for f in plugin_src.glob("*"):
            if _copy_file_incremental(f, plugin_dst / f.name):
                created += 1
            else:
                skipped += 1
        print(f"    [OK] Obsidian plugin (created {created}, preserved {skipped})")
    else:
        print(f"    [WARN] Plugin source not found: {plugin_src}")

    # AGENTS.md
    agents_src = repo_root / "AGENTS.md"
    agents_dst = vault / "AGENTS.md"
    if agents_src.exists():
        text = agents_src.read_text(encoding="utf-8")
        for old, new in [
            ("<system_dir>", system_dir),
            ("<resources_dir>", resources_dir),
            ("<literature_dir>", literature_dir),
            ("<control_dir>", control_dir),
            ("<base_dir>", base_dir),
            ("<skill_dir>", skill_dir),
        ]:
            text = text.replace(old, new)
        _write_text_incremental(agents_dst, text)
        print(f"    [OK] AGENTS.md")
    else:
        print(f"    [WARN] AGENTS.md source not found; skipping")

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
        "agent_platform": agent_config.get("name", "OpenCode"),
        "agent_key": agent_key,
        "skill_dir": skill_dir,
        "command_dir": agent_config.get("command_dir") or "",
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
            current_ver = getattr(_pf, '__version__', '?')
        except ImportError:
            current_ver = 'not installed'
        # If repo_root is the source repository (has pyproject.toml), install from it.
        # Otherwise (site-packages copy) install from GitHub tagged release.
        if (repo_root / "pyproject.toml").exists():
            install_target = [str(repo_root)]
        else:
            from paperforge import __version__ as _pv
            install_target = [f"git+https://github.com/LLLin000/PaperForge.git@{_pv}"]
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade"] + install_target,
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            _new = subprocess.run(
                [sys.executable, "-c", "import paperforge; print(getattr(paperforge, '__version__', '?'))"],
                capture_output=True, text=True, timeout=15,
            )
            new_ver = _new.stdout.strip() or '?'
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
        "AGENTS.md": True if not agents_src.exists() else agents_dst.exists(),
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
    print(f"  1. In Zotero, export the library or a collection as Better BibTeX JSON into: {vault / system_dir / 'PaperForge' / 'exports'}")
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
