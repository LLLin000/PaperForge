#!/usr/bin/env python3
"""
PaperForge Lite Setup Wizard (Textual Step-by-Step)
====================================================
基于 Textual ContentSwitcher + Tree + ProgressBar 的步骤向导。

Usage:
    python setup_wizard.py --vault /path/to/vault
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import webbrowser
from pathlib import Path

if sys.platform == "win32":
    import winreg
else:
    winreg = None

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    ContentSwitcher,
    Footer,
    Header,
    Markdown,
    ProgressBar,
    Static,
    Tree,
)

# =============================================================================
# Agent Platform Configurations
# =============================================================================

AGENT_CONFIGS = {
    "opencode": {
        "name": "OpenCode",
        "skill_dir": ".opencode/skills",
        "command_dir": ".opencode/command",
        "config_file": None,
    },
    "cursor": {"name": "Cursor", "skill_dir": ".cursor/skills", "config_file": ".cursor/settings.json"},
    "claude": {"name": "Claude Code", "skill_dir": ".claude/skills", "config_file": ".claude/skills.json"},
    "windsurf": {"name": "Windsurf", "skill_dir": ".windsurf/skills", "config_file": None},
    "github_copilot": {
        "name": "GitHub Copilot",
        "skill_dir": ".github/skills",
        "config_file": ".github/copilot-instructions.md",
    },
    "cline": {"name": "Cline", "skill_dir": ".clinerules/skills", "config_file": ".clinerules"},
    "augment": {"name": "Augment", "skill_dir": ".augment/skills", "config_file": None},
    "trae": {"name": "Trae", "skill_dir": ".trae/skills", "config_file": None},
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
        self.system_dir: str = "99_System"  # 可由用户自定义
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
        if v >= (3, 8):
            r.passed = True
            r.detail = f"Python {v.major}.{v.minor}.{v.micro}"
        else:
            r.passed = False
            r.detail = f"Python {v.major}.{v.minor}.{v.micro} (需要 >= 3.8)"
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

    def check_zotero(self) -> CheckResult:
        r = self.results["zotero"]
        path = self._find_zotero()
        if path:
            r.passed = True
            r.detail = str(path)
        else:
            r.passed = False
            r.detail = "未找到 Zotero"
            r.action_required = True
        return r

    def check_bbt(self) -> CheckResult:
        r = self.results["bbt"]
        system = platform.system()
        bbt_found = False
        bbt_path = None

        if system == "Windows":
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


# =============================================================================
# Step Screens
# =============================================================================

STEP_TITLES = [
    "欢迎使用 PaperForge",
    "选择 AI Agent 平台",
    "检查 Python 与依赖",
    "检查 Vault 结构",
    "安装 Zotero 与链接",
    "安装 Better BibTeX",
    "配置 JSON 导出",
    "部署工作流脚本",
    "安装完成",
]

STEP_IDS = [f"step-{i}" for i in range(len(STEP_TITLES))]


class StepScreen(Static):
    """单个步骤页面基类"""

    def __init__(self, step_id: str, checker: EnvChecker, **kwargs):
        kwargs.setdefault("id", step_id)
        super().__init__(**kwargs)
        self.step_id = step_id
        self.checker = checker
        self.step_idx = int(step_id.split("-")[1])

    def compose(self) -> ComposeResult:
        yield Static(f"## {STEP_TITLES[self.step_idx]}", classes="step-title")
        yield Static("", id=f"{self.step_id}-status", classes="status-bar")

    def set_status(self, text: str, success: bool | None = None) -> None:
        status = self.query_one(f"#{self.step_id}-status", Static)
        if success is True:
            status.update(f"[green]✓ {text}[/]")
        elif success is False:
            status.update(f"[red]✗ {text}[/]")
        else:
            status.update(text)


class WelcomeStep(StepScreen):
    """Step 0: 欢迎页"""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static(
            r"""
    ______  ___  ______ _________________ ___________ _____  _____
    | ___ \/ _ \ | ___ \  ___| ___ \  ___|  _  | ___ \  __ \|  ___|
    | |_/ / /_\ \| |_/ / |__ | |_/ / |_  | | | | |_/ / |  \/| |__
    |  __/|  _  ||  __/|  __||    /|  _| | | | |    /| | __ |  __|
    | |   | | | || |   | |___| |\ \| |   \ \_/ / |\ \| |_\ \| |___
    \_|   \_| |_/\_|   \____/\_| \_\_|    \___/\_| \_|\____/\____/

              [+]  Forge Your Knowledge Into Power  [+]
        """,
            classes="logo",
        )
        yield Markdown("""
**PaperForge Lite** 是一个连接 Zotero 与 Obsidian 的文献工作流工具。

安装向导将引导你完成以下配置：

1. 确认 Python 版本 (>= 3.10)
2. 配置 Vault 目录结构
3. 创建 Zotero 数据链接
4. 安装 Better BibTeX 插件
5. 配置 JSON 自动导出
6. 部署工作流文件

点击 **开始安装** 继续。
        """)
        yield Button("▶ 开始安装", id="btn-start", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-start":
            self.app.post_message(StepPassed(self.step_idx))


class AgentPlatformStep(StepScreen):
    """Step 1: 选择 AI Agent 平台"""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Markdown("""
PaperForge 需要知道你使用哪个 **AI Agent** 来执行精读命令。

这将决定 Skill 文件安装到哪里：
- **OpenCode** -> `.opencode/skills/`
- **Cursor** -> `.cursor/skills/`
- **Claude Code** -> `.claude/skills/`
- 其他...

选择你的 Agent 平台：
        """)
        for i, (key, cfg) in enumerate(AGENT_CONFIGS.items()):
            yield Button(
                f"{i+1}. {cfg['name']}",
                id=f"btn-agent-{key}",
                variant="default",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id and btn_id.startswith("btn-agent-"):
            agent_key = btn_id.replace("btn-agent-", "")
            cfg = AGENT_CONFIGS.get(agent_key)
            if cfg:
                # 保存选择到 app
                self.app.agent_config = cfg
                self.app.agent_key = agent_key
                self.set_status(f"已选择: {cfg['name']}", True)
                self.app.post_message(StepPassed(self.step_idx))


class PythonStep(StepScreen):
    """Step 2: Python 版本与依赖"""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Markdown("""
PaperForge 需要 **Python 3.10+** 以及以下 Python 包（pip 安装时会自动解决）：

点击 **一键检测** 检查环境。
        """)
        yield Horizontal(
            Button("🔍 一键检测", id="btn-check-python", variant="primary"),
            Button("📦 安装依赖", id="btn-install-deps", variant="default"),
            Button("⬇ 下载 Python", id="btn-dl-python", variant="default"),
            id="btn-row",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-check-python":
            py_result = self.checker.check_python()
            self.set_status(f"Python: {py_result.detail}", py_result.passed)
            if py_result.passed:
                dep_result = self.checker.check_dependencies()
                self.set_status(f"依赖: {dep_result.detail}", dep_result.passed)
                if dep_result.passed:
                    self.app.post_message(StepPassed(self.step_idx))
        elif event.button.id == "btn-install-deps":
            if self.checker.install_dependencies():
                self.set_status("依赖安装成功", True)
                # 重新检测
                dep_result = self.checker.check_dependencies()
                if dep_result.passed:
                    self.app.post_message(StepPassed(self.step_idx))
            else:
                self.set_status("依赖安装失败，请手动运行: pip install requests pymupdf pillow", False)
        elif event.button.id == "btn-dl-python":
            webbrowser.open("https://www.python.org/downloads/")


class VaultStep(StepScreen):
    """Step 3: Vault 目录结构配置"""

    def __init__(self, step_id: str, checker: EnvChecker, vault: str = "", **kwargs):
        kwargs.setdefault("id", step_id)
        super().__init__(step_id=step_id, checker=checker, **kwargs)
        self.step_id = step_id
        self.checker = checker
        self.step_idx = int(step_id.split("-")[1])
        self._vault = vault

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Markdown("""
PaperForge 需要知道你的 **Obsidian Vault 位置**，以及你想要的目录结构。

你可以保留默认名称，也可以自定义。
        """)
        from textual.widgets import Input

        yield Static("Obsidian Vault 路径 (绝对路径):", classes="step-title")
        yield Input(value=self._vault, placeholder="D:\\Documents\\MyVault", id="input-vault-path")
        yield Static("", id="vault-error", classes="status-bar")
        yield Markdown("""
---

**默认目录结构：**
```
Obsidian Vault/
├── 资源文件夹/               ← 文献笔记和资源
│   ├── 文献子文件夹/           ← 存放正式文献卡片
│   └── 文献索引/               ← 状态跟踪
└── 系统文件夹/               ← 系统文件
    └── PaperForge/             ← 导出和 OCR
```

修改下方名称（留空使用默认值）：
        """)
        yield Static("系统文件夹名称:", classes="step-title")
        yield Input(value="99_System", id="input-system-dir")
        yield Static("资源文件夹名称:", classes="step-title")
        yield Input(value="03_Resources", id="input-resources-dir")
        yield Static("文献子文件夹名称:", classes="step-title")
        yield Input(value="Literature", id="input-literature-dir")
        yield Static("文献索引文件夹名称:", classes="step-title")
        yield Input(value="LiteratureControl", id="input-control-dir")
        yield Static("Obsidian Base 文件夹名称:", classes="step-title")
        yield Input(value="05_Bases", id="input-base-dir")
        yield Horizontal(
            Button("✓ 确认并创建目录", id="btn-setup-vault", variant="primary"),
            id="btn-row",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-setup-vault":
            from textual.widgets import Input

            # 获取 Vault 路径
            vault_input = self.query_one("#input-vault-path", Input).value.strip()
            if not vault_input:
                self.query_one("#vault-error", Static).update("[red]请填写 Obsidian Vault 的绝对路径[/]")
                return

            vault_path = Path(vault_input)
            if not vault_path.exists():
                self.query_one("#vault-error", Static).update(f"[red]该目录不存在: {vault_path}[/]")
                return

            # 更新 app 的 vault 路径
            self.app.vault = vault_path
            self.checker.vault = vault_path

            # 获取目录名称
            system_dir = self.query_one("#input-system-dir", Input).value.strip() or "99_System"
            resources_dir = self.query_one("#input-resources-dir", Input).value.strip() or "03_Resources"
            literature_dir = self.query_one("#input-literature-dir", Input).value.strip() or "Literature"
            control_dir = self.query_one("#input-control-dir", Input).value.strip() or "LiteratureControl"
            base_dir = self.query_one("#input-base-dir", Input).value.strip() or "05_Bases"

            # 解析路径（支持名称、相对路径、绝对路径）
            def resolve_path(base: Path, path_str: str) -> Path:
                p = Path(path_str)
                if p.is_absolute():
                    return p
                else:
                    return base / p

            system_path = resolve_path(vault_path, system_dir)
            resources_path = resolve_path(vault_path, resources_dir)
            base_path = resolve_path(vault_path, base_dir)

            # 保存配置
            self.app.vault_config = {
                "vault_path": str(vault_path),
                "system_dir": system_dir,
                "resources_dir": resources_dir,
                "literature_dir": literature_dir,
                "control_dir": control_dir,
                "base_dir": base_dir,
                "paperforge_path": str(system_path / "PaperForge"),
                "literature_path": str(resources_path / literature_dir),
                "base_path": str(base_path),
            }

            # 创建目录
            dirs_to_create = [
                resources_path / control_dir / "library-records",
                base_path,
                system_path / "PaperForge" / "exports",
                system_path / "PaperForge" / "ocr",
            ]

            created = []
            for d in dirs_to_create:
                d.mkdir(parents=True, exist_ok=True)
                created.append(str(d.relative_to(vault_path)))

            # 同步更新 checker
            self.checker.system_dir = system_dir

            self.query_one("#vault-error", Static).update("")
            self.set_status(f"已创建 {len(created)} 个目录", True)
            self.app.post_message(StepPassed(self.step_idx))


class ZoteroStep(StepScreen):
    """Step 4: Zotero 数据目录链接"""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        # 自动检测 Zotero 数据目录
        detected = self._detect_zotero_data()
        default_value = str(detected) if detected else ""

        yield Markdown("""
**Zotero 数据目录**存放了你的文献数据库和 PDF 附件。

向导将创建目录链接，让 PaperForge 能读取你的 PDF：
```
你的 Vault/
    └── [系统目录]/
        └── Zotero/     ← 链接（自动创建）
            ↓ junction
            你的 Zotero 数据目录/     ← 你填这里
                ├── zotero.sqlite
                └── storage/
```

**请填写你的 Zotero 数据目录路径：**
- 这是 Zotero 存放数据库的地方，不是 Vault 里的路径
- Windows 通常是 `C:/Users/你的用户名/Zotero`
- macOS 通常是 `~/Zotero`

> ⚠️ **不要**填 Vault 里面的路径，也不要在这里创建新文件夹
        """)
        from textual.widgets import Input

        username = os.environ.get("USERNAME", os.environ.get("USER", "YourName"))
        yield Static("Zotero 数据目录:", classes="step-title")
        yield Input(
            value=default_value,
            placeholder=f"C:/Users/{username}/Zotero",
            id="input-zotero-data",
        )
        yield Horizontal(
            Button("🔗 创建目录链接", id="btn-link-zotero", variant="primary"),
            Button("⬇ 下载 Zotero", id="btn-dl-zotero", variant="default"),
            id="btn-row",
        )

    def _detect_zotero_data(self) -> Path | None:
        """Build default Zotero data path from current username."""
        home = Path.home()
        # Default: C:/Users/<username>/Zotero (Windows) or ~/Zotero (Unix)
        default = home / "Zotero"
        if default.exists() and (default / "zotero.sqlite").exists():
            return default
        return default  # Return anyway as default value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-link-zotero":
            from textual.widgets import Input

            path_str = self.query_one("#input-zotero-data", Input).value.strip()
            if not path_str:
                self.set_status("请填写 Zotero 数据目录路径", False)
                return

            zotero_data = Path(path_str)
            if not zotero_data.exists():
                self.set_status("路径不存在，请检查路径是否正确", False)
                return
            if not (zotero_data / "zotero.sqlite").exists():
                self.set_status("未找到 zotero.sqlite，请确认这是 Zotero 数据目录", False)
                return
            if not (zotero_data / "storage").exists():
                self.set_status("未找到 storage 文件夹，请确认这是 Zotero 数据目录", False)
                return

            # 检查是否在 Vault 内部
            vault = self.checker.vault
            is_inside_vault = False
            try:
                zotero_data.resolve().relative_to(vault.resolve())
                is_inside_vault = True
            except ValueError:
                pass

            if is_inside_vault:
                # 在 Vault 内部，直接通过
                self.app.zotero_data_dir = str(zotero_data)
                self.set_status("Zotero 数据目录已确认", True)
                self.app.post_message(StepPassed(self.step_idx))
                return

            # 在 Vault 外部，创建 Junction
            system_dir = getattr(self.app, "vault_config", {}).get("system_dir", "99_System")
            junction_path = vault / system_dir / "Zotero"

            # Remove existing
            if junction_path.exists() or junction_path.is_symlink():
                try:
                    if sys.platform == "win32":
                        subprocess.run(["cmd", "/c", "rmdir", str(junction_path)], check=True, capture_output=True)
                    else:
                        junction_path.unlink()
                except Exception:
                    pass

            try:
                junction_path.parent.mkdir(parents=True, exist_ok=True)
                if sys.platform == "win32":
                    subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(junction_path), str(zotero_data)],
                        check=True,
                        capture_output=True,
                        shell=False,
                    )
                else:
                    junction_path.symlink_to(zotero_data, target_is_directory=True)
                self.app.zotero_data_dir = str(zotero_data)
                self.app.zotero_link = str(junction_path)
                self.set_status("链接已创建", True)
                self.app.post_message(StepPassed(self.step_idx))
            except Exception as e:
                self.set_status(f"创建链接失败: {e}", False)

        elif event.button.id == "btn-dl-zotero":
            webbrowser.open("https://www.zotero.org/download/")


class BBTStep(StepScreen):
    """Step 5: Better BibTeX"""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Markdown("""
**Better BibTeX (BBT)** 是 Zotero 的插件，用于生成 citation key 和自动导出 JSON。

**安装步骤：**
1. 下载 BBT 插件
2. Zotero → 工具 → 插件
3. 齿轮图标 → Install Plugin From File...
4. 选择下载的 `.xpi` 文件 → 重启 Zotero

安装完成后点击 **检测**。
        """)
        yield Horizontal(
            Button("🔍 自动检测", id="btn-check-bbt", variant="primary"),
            Button("⬇ 下载 BBT", id="btn-dl-bbt", variant="default"),
            Button("📷 查看安装截图", id="btn-img-bbt", variant="default"),
            id="btn-row",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-check-bbt":
            result = self.checker.check_bbt()
            self.set_status(result.detail, result.passed)
            if result.passed:
                self.app.post_message(StepPassed(self.step_idx))
        elif event.button.id == "btn-dl-bbt":
            webbrowser.open("https://retorque.re/zotero-better-bibtex/")
        elif event.button.id == "btn-img-bbt":
            self.app.open_screenshot("bbt-install.png")


class JsonStep(StepScreen):
    """Step 5: JSON 导出配置"""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        system_dir = getattr(self.app, "vault_config", {}).get("system_dir", "99_System")
        yield Markdown(f"""
**Better BibTeX 自动导出**是 PaperForge 的数据来源。

**配置步骤：**
1. Zotero → 文件 → 导出库...
2. 格式选择 **Better BibTeX**
3. 保存到：`{system_dir}/PaperForge/exports/`
4. **[必须] 勾选 "保持更新"** — 这是自动同步的关键！

> ⚠️ **重要**：如果不勾选"保持更新"，Zotero 新增文献后 PaperForge 不会自动发现，需要每次手动重新导出。

📁 **子分类与 Base 管理**

你可以根据 Zotero 收藏夹结构，灵活决定如何导出：

**方案 A：分开管理（推荐）**
为每个子分类分别创建 JSON：
```
Zotero 收藏夹结构
├── 骨科
│   ├── 关节外科      → 导出为 orthopedic-joint.json
│   └── 脊柱外科      → 导出为 orthopedic-spine.json
└── 运动医学
    └── 膝盖损伤      → 导出为 sports-knee.json
```
每个 JSON 对应一个独立的 Obsidian Base 视图，可分别配置 OCR 和精读队列。

**方案 B：统一管理**
直接导出整个父级收藏夹：
```
骨科（含所有子分类）  → 导出为 orthopedic.json
```
适合分类较少、希望统一查看的场景。

> 💡 建议：先试用方案 A，分类多了再调整。
        """)
        yield Horizontal(
            Button("🔍 自动检测", id="btn-check-json", variant="primary"),
            id="btn-row",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-check-json":
            result = self.checker.check_json()
            self.set_status(result.detail, result.passed)
            if result.passed:
                self.app.post_message(StepPassed(self.step_idx))


class DeployStep(StepScreen):
    """Step 7: 部署脚本和配置"""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Markdown("""
**最后一步：部署工作流脚本和配置文件。**

向导将自动完成以下操作：
1. **复制脚本** — 将 pipeline worker 脚本部署到你的 Vault
2. **创建 .env** — 配置文件存放 API Key（PaddleOCR 等）
3. **创建 paperforge.json** — 版本和路径配置
4. **安装命令** — 为 Agent 添加快捷命令

这些操作不会覆盖你的数据文件。
        """)
        from textual.widgets import Input

        yield Static("PaddleOCR API Key:", classes="step-title")
        yield Input(placeholder="粘贴你的 PaddleOCR API Key", id="input-api-key")
        yield Static("PaddleOCR API URL:", classes="step-title")
        yield Input(
            value="https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
            placeholder="https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
            id="input-api-url",
        )
        yield Horizontal(
            Button("🚀 一键部署", id="btn-deploy", variant="primary"),
            id="btn-row",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-deploy":
            # 安全检查：前面步骤必须全部通过
            step_states = self.app.step_states
            required_steps = [
                (1, "选择 Agent 平台"),
                (2, "Python 环境检查"),
                (3, "Vault 目录配置"),
                (4, "Zotero 数据目录链接"),
                (5, "Better BibTeX 插件"),
                (6, "JSON 导出配置"),
            ]
            incomplete = []
            for idx, name in required_steps:
                if not step_states[idx]:
                    incomplete.append(f"步骤 {idx}: {name}")

            if incomplete:
                self.set_status(
                    "[无法部署] 以下步骤未完成：\n" + "\n".join(incomplete) + "\n请先返回并完成上述步骤", False
                )
                return

            self.set_status("正在部署...", None)
            success = self._deploy()
            if success:
                self.set_status("部署完成！", True)
                self.app.post_message(StepPassed(self.step_idx))
            else:
                self.set_status("部署过程中出现错误，请检查上方日志", False)

    def _deploy(self) -> bool:
        """Deploy scripts and create config files."""
        vault = self.checker.vault
        vault_config = getattr(self.app, "vault_config", {})
        system_dir = vault_config.get("system_dir", "99_System")
        resources_dir = vault_config.get("resources_dir", "03_Resources")
        literature_dir = vault_config.get("literature_dir", "Literature")
        control_dir = vault_config.get("control_dir", "LiteratureControl")
        base_dir = vault_config.get("base_dir", "05_Bases")

        def apply_user_paths(text: str, skill_dir_value: str = "") -> str:
            agent_config_dir = str(Path(skill_dir_value or ".opencode/skills").parent).replace("\\", "/")
            replacements = {
                "<system_dir>": system_dir,
                "<resources_dir>": resources_dir,
                "<literature_dir>": literature_dir,
                "<control_dir>": control_dir,
                "<base_dir>": base_dir,
                "<skill_dir>": skill_dir_value,
                "<agent_config_dir>": agent_config_dir,
                "99_System/PaperForge": f"{system_dir}/PaperForge",
                "99_System\\PaperForge": f"{system_dir}\\PaperForge",
                "99_System/Zotero": f"{system_dir}/Zotero",
                "99_System\\Zotero": f"{system_dir}\\Zotero",
                "03_Resources/LiteratureControl": f"{resources_dir}/{control_dir}",
                "03_Resources\\LiteratureControl": f"{resources_dir}\\{control_dir}",
                "03_Resources/Literature": f"{resources_dir}/{literature_dir}",
                "03_Resources\\Literature": f"{resources_dir}\\{literature_dir}",
                ".opencode/skills": skill_dir_value or ".opencode/skills",
                ".opencode\\skills": (skill_dir_value or ".opencode/skills").replace("/", "\\"),
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            return text

        # 1. 获取 agent 配置
        agent_config = getattr(self.app, "agent_config", None)
        if not agent_config:
            self.set_status("错误：未选择 Agent 平台", False)
            return False

        skill_dir = agent_config.get("skill_dir", ".opencode/skills")

        # 2. 确定安装包根目录（wizard 所在目录的父目录）
        wizard_dir = Path(__file__).parent.resolve()
        # 如果 wizard 在 github-release/ 下，repo_root 就是 github-release/
        # 如果 wizard 在 scripts/ 下，repo_root 是父目录
        if (wizard_dir / "paperforge").exists():
            repo_root = wizard_dir
        elif (wizard_dir.parent / "paperforge").exists():
            repo_root = wizard_dir.parent
        elif (wizard_dir / "pipeline").exists():
            repo_root = wizard_dir
        elif (wizard_dir.parent / "pipeline").exists():
            repo_root = wizard_dir.parent
        else:
            self.set_status(f"错误：找不到安装包文件。请在 PaperForge 解压目录下运行此向导。当前: {wizard_dir}", False)
            return False

        # 3. 创建目录（使用用户自定义路径）
        pf_path = vault / system_dir / "PaperForge"
        dirs = [
            pf_path / "exports",
            pf_path / "ocr",
            pf_path / "config",
            pf_path / "worker/scripts",
            vault / resources_dir / literature_dir,
            vault / resources_dir / control_dir / "library-records",
            vault / base_dir,
            vault / skill_dir / "literature-qa/scripts",
            vault / skill_dir / "literature-qa/chart-reading",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # 4. 复制脚本（从安装包到 Vault）
        import shutil

        # Copy worker modules to PaperForge/worker/scripts/
        worker_src = repo_root / "paperforge/worker/sync.py"
        worker_dst = pf_path / "worker/scripts/sync.py"
        if worker_src.exists():
            import shutil

            shutil.copy2(worker_src, worker_dst)
            # Also copy other worker modules
            for mod in [
                "ocr.py",
                "repair.py",
                "status.py",
                "deep_reading.py",
                "update.py",
                "base_views.py",
                "__init__.py",
            ]:
                mod_src = repo_root / "paperforge/worker" / mod
                if mod_src.exists():
                    shutil.copy2(mod_src, pf_path / "worker/scripts" / mod)
        else:
            # Fallback to old pipeline location for backward compatibility
            worker_src = repo_root / "pipeline/worker/scripts/literature_pipeline.py"
            worker_dst = pf_path / "worker/scripts/literature_pipeline.py"
            if worker_src.exists():
                shutil.copy2(worker_src, worker_dst)
            else:
                self.set_status(f"错误：找不到 worker 脚本: {worker_src}", False)
                return False

        # Copy ld_deep.py (prefer paperforge/skills, fallback to skills/)
        ld_src = repo_root / "paperforge/skills/literature-qa/scripts/ld_deep.py"
        if not ld_src.exists():
            ld_src = repo_root / "skills/literature-qa/scripts/ld_deep.py"
        ld_dst = vault / skill_dir / "literature-qa/scripts/ld_deep.py"
        if ld_src.exists():
            shutil.copy2(ld_src, ld_dst)
        else:
            self.set_status(f"错误：找不到 ld_deep.py: {ld_src}", False)
            return False

        # Copy subagent prompt (prefer paperforge/skills, fallback to skills/)
        prompt_src = repo_root / "paperforge/skills/literature-qa/prompt_deep_subagent.md"
        if not prompt_src.exists():
            prompt_src = repo_root / "skills/literature-qa/prompt_deep_subagent.md"
        prompt_dst = vault / skill_dir / "literature-qa/prompt_deep_subagent.md"
        if prompt_src.exists():
            shutil.copy2(prompt_src, prompt_dst)
        else:
            self.set_status(f"错误：找不到 prompt_deep_subagent.md: {prompt_src}", False)
            return False

        # Copy chart-reading guides (prefer paperforge/skills, fallback to skills/)
        chart_src = repo_root / "paperforge/skills/literature-qa/chart-reading"
        if not chart_src.exists():
            chart_src = repo_root / "skills/literature-qa/chart-reading"
        chart_dst = vault / skill_dir / "literature-qa/chart-reading"
        if chart_src.exists() and chart_src.is_dir():
            for f in chart_src.glob("*.md"):
                shutil.copy2(f, chart_dst / f.name)

        # Copy OpenCode command files when the target platform supports them.
        if getattr(self.app, "agent_key", "") == "opencode":
            command_src = wizard_dir / "command_files"
            if not command_src.exists() or not command_src.is_dir():
                command_src = repo_root / "command"
            command_dst = vault / agent_config.get("command_dir", ".opencode/command")
            if command_src.exists() and command_src.is_dir():
                command_dst.mkdir(parents=True, exist_ok=True)
                for f in command_src.glob("*.md"):
                    text = apply_user_paths(f.read_text(encoding="utf-8"), skill_dir)
                    (command_dst / f.name).write_text(text, encoding="utf-8")

        # Copy user-facing docs. AGENTS.md is regenerated below with the chosen paths.
        docs_src = repo_root / "docs"
        docs_dst = vault / "docs"
        if docs_src.exists() and docs_src.is_dir():
            shutil.copytree(docs_src, docs_dst, dirs_exist_ok=True)
            for doc in docs_dst.rglob("*.md"):
                doc.write_text(apply_user_paths(doc.read_text(encoding="utf-8"), skill_dir), encoding="utf-8")

        # 5. 创建 .env（放到 PaperForge 目录下）
        from textual.widgets import Input

        api_key = self.query_one("#input-api-key", Input).value.strip()
        api_url = (
            self.query_one("#input-api-url", Input).value.strip()
            or "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
        )

        if not api_key:
            self.set_status("请填写 PaddleOCR API Key", False)
            return False

        # 把 .env 放在 PaperForge 目录下
        env_path = pf_path / ".env"
        env_content = f"""# PaperForge 配置文件
# PaddleOCR API Token（从 https://paddleocr.baidu.com 获取）
PADDLEOCR_API_TOKEN={api_key}

# PaddleOCR API 地址
PADDLEOCR_JOB_URL={api_url}

# PaddleOCR 模型（通常不需要修改）
PADDLEOCR_MODEL=PaddleOCR-VL-1.5

# Zotero data directory selected during setup
ZOTERO_DATA_DIR={getattr(self.app, 'zotero_data_dir', '')}
"""
        env_path.write_text(env_content, encoding="utf-8")

        # Create a minimal domain mapping. The worker will keep this usable even
        # before JSON exports exist, and will infer domains from export filenames.
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

        # 6. 创建 paperforge.json（包含用户自定义路径）
        pf_json = vault / "paperforge.json"
        existing_config = {}
        if pf_json.exists():
            try:
                existing_config = json.loads(pf_json.read_text(encoding="utf-8"))
            except Exception:
                existing_config = {}
        existing_config.update(
            {
                "version": existing_config.get("version", "1.2.0"),
                "agent_platform": agent_config.get("name", "OpenCode"),
                "agent_key": getattr(self.app, "agent_key", "opencode"),
                "skill_dir": skill_dir,
                "command_dir": agent_config.get("command_dir", ""),
                "system_dir": system_dir,
                "resources_dir": resources_dir,
                "literature_dir": literature_dir,
                "control_dir": control_dir,
                "base_dir": base_dir,
                "paperforge_path": f"{system_dir}/PaperForge",
                "zotero_data_dir": getattr(self.app, "zotero_data_dir", ""),
                "zotero_link": getattr(self.app, "zotero_link", f"{system_dir}/Zotero"),
                "vault_config": {
                    "system_dir": system_dir,
                    "resources_dir": resources_dir,
                    "literature_dir": literature_dir,
                    "control_dir": control_dir,
                    "base_dir": base_dir,
                },
            }
        )
        pf_json.write_text(json.dumps(existing_config, indent=2, ensure_ascii=False), encoding="utf-8")

        agents_src = repo_root / "AGENTS.md"
        agents_dst = vault / "AGENTS.md"
        if agents_src.exists():
            agents_text = apply_user_paths(agents_src.read_text(encoding="utf-8"), skill_dir)
            agents_dst.write_text(agents_text, encoding="utf-8")

        # 7. 验证文件完整性
        self.set_status("验证文件完整性...", None)
        checks = {
            "Worker 脚本": worker_dst.exists(),
            "精读脚本": ld_dst.exists(),
            "精读提示词": prompt_dst.exists(),
            "目录结构": (vault / resources_dir / control_dir / "library-records").exists(),
            "Base 目录": (vault / base_dir).exists(),
            "分类配置": domain_config.exists(),
            "导出目录": (pf_path / "exports").exists(),
            "OCR 目录": (pf_path / "ocr").exists(),
        }

        missing = [k for k, v in checks.items() if not v]
        if missing:
            self.set_status(f"验证失败: {', '.join(missing)}", False)
            return False

        self.set_status("文件验证通过，初始化系统...", True)

        # 8. 运行初始化命令（模拟测试）
        try:
            # 测试 selection-sync（会报错因为没 JSON，但测试脚本能否运行）
            result = subprocess.run(
                [sys.executable, str(worker_dst), "--vault", str(vault), "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.set_status("工作流脚本运行正常", True)
            else:
                self.set_status(f"脚本测试警告: {result.stderr[:100]}", None)
        except Exception as e:
            self.set_status(f"脚本测试跳过: {e}", None)

        # 9. 安装 PaperForge 工具包（让 paperforge 命令全局可用）
        self.set_status("安装 PaperForge 工具包...", None)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", str(repo_root)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                self.set_status("PaperForge 工具包安装完成（paperforge 命令已全局注册）", True)
            else:
                stderr = result.stderr[:200] if result.stderr else ""
                self.set_status(f"pip install 警告（paperforge 命令可能需要手动注册）: {stderr}", None)
        except Exception as e:
            self.set_status(f"pip install 跳过: {e}", None)

        return True


class DoneStep(StepScreen):
    """Step 8: 完成页"""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        vault_config = getattr(self.app, "vault_config", {})
        system_dir = vault_config.get("system_dir", "99_System")
        yield Markdown(f"""
## 安装完成！

PaperForge Lite 已完成安装和初始化。以下是立即开始使用的步骤：

### 首次使用步骤：

**1. 同步 Zotero 文献并生成正式笔记**
```bash
paperforge sync
```

如需分阶段执行：
```bash
paperforge sync --selection  # 仅同步 Zotero 到 library-records
paperforge sync --index      # 仅根据现有 library-records 生成正式笔记
```

**2. 标记精读文献**
在 Obsidian 中打开 library-records 文件，设置：
- `do_ocr: true`
- `analyze: true`

**3. 运行 OCR**
```bash
paperforge ocr
```

如需诊断模式（不实际运行）：
```bash
paperforge ocr --diagnose
```

**4. 执行精读**
在 OpenCode Agent 中输入：
```
/pf-deep <zotero_key>
```

### 已安装的 Agent 命令

安装向导已自动将以下命令安装到你的 Agent 中：

**精读命令：**
| 命令 | 作用 |
|------|------|
| `/pf-deep <key>` | 完整三阶段精读 |
| `/pf-paper <key>` | 快速摘要 |

**Worker 快捷命令：**
| 命令 | 作用 |
|------|------|
| `/pf-sync` | 同步 Zotero 文献并生成正式笔记 |
| `/pf-ocr` | 运行 PDF OCR |
| `/pf-status` | 查看工作流状态 |

**paperforge 命令（推荐）：**
```bash
paperforge status            # 查看状态
paperforge sync              # 同步文献并生成笔记
paperforge ocr               # 运行 OCR（自动上传+等待+下载）
paperforge deep-reading      # 查看精读队列
paperforge doctor            # 诊断配置
paperforge update            # 检查更新
```

### 详细文档

- 安装后指南：`docs/setup-guide.md`
- 详细配置说明：`paperforge setup`
- GitHub: https://github.com/LLLin000/PaperForge
        """)
        yield Horizontal(
            Button("📖 打开详细指南", id="btn-open-guide", variant="primary"),
            Button("🔄 重新检测", id="btn-restart", variant="default"),
            Button("✓ 完成退出", id="btn-exit", variant="default"),
            id="btn-row",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-open-guide":
            guide_path = self.checker.vault / "docs" / "setup-guide.md"
            if guide_path.exists():
                if sys.platform == "win32":
                    os.startfile(str(guide_path))
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(guide_path)])
                else:
                    subprocess.run(["xdg-open", str(guide_path)])
            else:
                webbrowser.open("https://github.com/LLLin000/PaperForge/blob/master/docs/setup-guide.md")
        elif event.button.id == "btn-restart":
            self.app.post_message(RestartWizard())
        elif event.button.id == "btn-exit":
            self.app.exit()


# =============================================================================
# Custom Messages
# =============================================================================


class StepPassed(Message):
    """步骤通过消息"""

    def __init__(self, step_idx: int):
        super().__init__()
        self.step_idx = step_idx


class RestartWizard(Message):
    """重新开始消息"""

    def __init__(self):
        super().__init__()


# =============================================================================
# Main App
# =============================================================================


class SetupWizardApp(App):
    """PaperForge 安装向导主应用"""

    CSS = """
    Screen { align: center middle; }

    .wizard-container { width: 95%; height: 95%; border: solid green; }

    .sidebar { width: 25%; height: 100%; border: solid gray; padding: 1; }
    .sidebar-title { text-align: center; text-style: bold; color: cyan; padding: 1; }
    .step-tree { height: 1fr; }

    .main-area { width: 75%; height: 100%; padding: 1; }
    .progress-area { height: auto; padding: 0 1; }
    .content-area { height: 1fr; border: solid blue; padding: 1; overflow-y: auto; }

    .logo { text-align: center; color: ansi_bright_cyan; text-style: bold; height: auto; }
    .step-title { text-style: bold; color: yellow; }
    .status-bar { height: auto; padding: 1; }

    .step-content { padding: 1; }
    .step-content Markdown { padding: 0 1; }

    #btn-row { height: auto; padding: 1; }
    #btn-row Button { margin: 0 1; }

    .done { color: green; }
    .current { color: yellow; text-style: bold; }
    .pending { color: gray; }
    """

    BINDINGS = [
        ("q", "quit", "退出"),
        ("n", "next_step", "下一步"),
        ("p", "prev_step", "上一步"),
    ]

    current_step = reactive(0)
    step_states = reactive([False] * len(STEP_TITLES))

    def __init__(self, vault: Path):
        super().__init__()
        self.vault = vault
        self.checker = EnvChecker(vault)
        self.step_screens: dict[str, StepScreen] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)

        with Container(classes="wizard-container"):
            with Horizontal():
                # 左侧：步骤导航树
                with Vertical(classes="sidebar"):
                    yield Static("安装步骤", classes="sidebar-title")
                    tree = Tree("PaperForge Lite", id="step-tree", classes="step-tree")
                    for i, title in enumerate(STEP_TITLES):
                        tree.root.add_leaf(f"{i}. {title}")
                    yield tree

                # 右侧：主内容区
                with Vertical(classes="main-area"):
                    # 进度条
                    with Container(classes="progress-area"):
                        yield ProgressBar(total=len(STEP_TITLES), show_eta=False, id="progress")
                        yield Static("Step 0 / 6", id="progress-text", classes="progress-text")

                    # 内容切换器
                    with ContentSwitcher(id="content-switcher", classes="content-area"):
                        screens = [
                            WelcomeStep("step-0", self.checker),
                            AgentPlatformStep("step-1", self.checker),
                            PythonStep("step-2", self.checker),
                            VaultStep("step-3", self.checker, vault=str(self.vault)),
                            ZoteroStep("step-4", self.checker),
                            BBTStep("step-5", self.checker),
                            JsonStep("step-6", self.checker),
                            DeployStep("step-7", self.checker),
                            DoneStep("step-8", self.checker),
                        ]
                        for screen in screens:
                            self.step_screens[screen.step_id] = screen
                            yield screen

        yield Footer()

    def on_mount(self) -> None:
        self._update_step_display()

    def watch_current_step(self, step: int) -> None:
        self._update_step_display()

    def watch_step_states(self, states: list[bool]) -> None:
        self._update_step_display()

    def _update_step_display(self) -> None:
        # 更新 ContentSwitcher
        switcher = self.query_one("#content-switcher", ContentSwitcher)
        switcher.current = f"step-{self.current_step}"

        # 更新进度条
        progress = self.query_one("#progress", ProgressBar)
        progress.advance(self.current_step - progress.progress)

        progress_text = self.query_one("#progress-text", Static)
        progress_text.update(f"Step {self.current_step} / {len(STEP_TITLES) - 1}: {STEP_TITLES[self.current_step]}")

        # 更新 Tree 高亮 - 区分已完成、跳过、当前、待处理
        tree = self.query_one("#step-tree", Tree)
        for i, node in enumerate(tree.root.children):
            if self.step_states[i]:
                # 已完成：绿色勾
                node.label = f"[green]✓ {i}. {STEP_TITLES[i]}[/]"
            elif i == self.current_step:
                # 当前：黄色箭头
                node.label = f"[yellow]▶ {i}. {STEP_TITLES[i]}[/]"
            elif i < self.current_step and not self.step_states[i]:
                # 跳过（已访问但未完成）：灰色跳过标记
                node.label = f"[gray]↷ {i}. {STEP_TITLES[i]}[/]"
            else:
                # 待处理：灰色圆圈
                node.label = f"[gray]○ {i}. {STEP_TITLES[i]}[/]"

    def action_next_step(self) -> None:
        if self.current_step < len(STEP_TITLES) - 1:
            self.current_step += 1

    def action_prev_step(self) -> None:
        if self.current_step > 0:
            self.current_step -= 1

    def on_step_passed(self, message: StepPassed) -> None:
        """步骤通过，标记完成并自动前进"""
        self.step_states[message.step_idx] = True
        if message.step_idx < len(STEP_TITLES) - 1:
            self.current_step = message.step_idx + 1

    def on_restart_wizard(self) -> None:
        """重新开始"""
        self.current_step = 0
        self.step_states = [False] * len(STEP_TITLES)
        for screen in self.step_screens.values():
            if hasattr(screen, "set_status"):
                screen.set_status("")

    def open_screenshot(self, filename: str) -> None:
        """打开截图"""
        img_path = self.vault / "docs" / "images" / filename
        if img_path.exists():
            if sys.platform == "win32":
                os.startfile(str(img_path))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(img_path)])
            else:
                subprocess.run(["xdg-open", str(img_path)])
        else:
            # 截图不存在，打开在线文档
            webbrowser.open(f"https://github.com/LLLin000/PaperForge/blob/master/docs/images/{filename}")


# =============================================================================
# Entry
# =============================================================================


def _find_vault() -> Path | None:
    """Find vault by looking for paperforge.json in current or parent dirs."""
    current = Path(".").resolve()
    for path in [current, *current.parents]:
        if (path / "paperforge.json").exists():
            return path
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PaperForge Lite 安装向导")
    parser.add_argument("--vault", type=Path, default=None, help="Vault 路径（可选，默认当前目录）")
    args = parser.parse_args(argv)

    if args.vault:
        vault = args.vault.resolve()
    else:
        # 默认使用当前目录
        vault = Path(".").resolve()

    app = SetupWizardApp(vault)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
