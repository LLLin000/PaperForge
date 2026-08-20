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

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from paperforge import __version__

# Backward-compat imports (v2.1 modular setup)

if sys.platform == "win32":
    import winreg
else:
    winreg = None

# [Textual TUI removed — headless-only setup]

# =============================================================================
# Agent Platform Configurations
# =============================================================================

AGENT_NAMES = {
    "opencode":       "OpenCode",
    "claude":         "Claude Code",
    "codex":          "Codex",
    "cursor":         "Cursor",
    "windsurf":       "Windsurf",
    "github_copilot": "GitHub Copilot",
    "gemini":         "Gemini CLI",
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
        if v >= (3, 11):
            r.passed = True
            r.detail = f"Python {v.major}.{v.minor}.{v.micro}"
        else:
            r.passed = False
            r.detail = f"Python {v.major}.{v.minor}.{v.micro} (需要 >= 3.11)"
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
            subprocess.run(
                [sys.executable, "-m", "pip", "install"] + deps,
                check=True, capture_output=True,
                encoding="utf-8", errors="replace",
            )
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
                result = subprocess.run(
                    ["where", "zotero"],
                    capture_output=True, text=True,
                    encoding="utf-8", errors="replace",
                    timeout=5,
                )
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
                result = subprocess.run(
                    ["which", "zotero"],
                    capture_output=True, text=True,
                    encoding="utf-8", errors="replace",
                    timeout=5,
                )
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
                result = subprocess.run(
                    ["which", "zotero"],
                    capture_output=True, text=True,
                    encoding="utf-8", errors="replace",
                    timeout=5,
                )
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
    # Deprecated legacy entry (no product callers): delegate to SetupPlan so
    # paperforge.json is written ONLY through the canonical seam.  The old
    # direct write_text/env/junction body below is dead and must not run.
    import warnings

    warnings.warn(
        "headless_setup is deprecated — use `paperforge setup --modular`",
        DeprecationWarning,
        stacklevel=2,
    )
    from paperforge.setup.plan import SetupPlan

    _cfg = {
        "system_dir": system_dir,
        "resources_dir": resources_dir,
        "literature_dir": literature_dir,
        "base_dir": base_dir,
    }
    if paddleocr_key:
        # #173: secrets NEVER enter .env or config — the credential
        # authority is the only secret store.
        from paperforge.credentials import CredentialKey, store

        try:
            store(CredentialKey("ocr"), paddleocr_key)
        except Exception as exc:  # noqa: BLE001 — report, do not abort setup
            print(f"    [WARN] failed to store OCR credential: {exc}", file=sys.stderr)
    return SetupPlan(
        vault=Path(vault),
        config=_cfg,
        zotero_path=zotero_data,
        agent_type=agent_key,
        skip_checks=skip_checks,
    ).execute()



def main(argv: list[str] | None = None) -> int:
    """Print help message — Textual TUI removed."""
    print("=" * 60)
    print("  PaperForge Setup Wizard")
    print("=" * 60)
    print()
    print("The interactive Textual TUI has been removed.")
    print()
    print("To run setup non-interactively, use:")
    print("  paperforge setup --modular")
    print()
    print("Or configure PaperForge via the Obsidian plugin settings tab:")
    print("  1. Open Obsidian → Settings → Community Plugins → PaperForge")
    print("  2. Fill in your configuration")
    print("  3. Click 'Install'")
    print()
    return 0


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
