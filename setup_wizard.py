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
import winreg
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    ContentSwitcher,
    Footer,
    Header,
    Label,
    Markdown,
    ProgressBar,
    Static,
    Tree,
)


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
        self.manual_zotero_path: Optional[Path] = None
        self.results: dict[str, CheckResult] = {
            "python": CheckResult("Python 版本"),
            "vault": CheckResult("Vault 结构"),
            "zotero": CheckResult("Zotero 安装"),
            "bbt": CheckResult("Better BibTeX"),
            "json": CheckResult("JSON 导出"),
        }

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

    def check_vault(self) -> CheckResult:
        r = self.results["vault"]
        required = [
            "03_Resources/LiteratureControl/library-records",
            "99_System/LiteraturePipeline/exports",
            "99_System/LiteraturePipeline/ocr",
            "99_System/Template",
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

    def _find_zotero(self, manual_path: Optional[Path] = None) -> Optional[Path]:
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
        exports_dir = self.vault / "99_System" / "LiteraturePipeline" / "exports"
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
                if isinstance(data, list) and len(data) > 0:
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
    "检查 Python 版本",
    "检查 Vault 结构",
    "安装 Zotero",
    "安装 Better BibTeX",
    "配置 JSON 导出",
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
        yield Markdown("""
**PaperForge Lite** 是一个连接 Zotero 与 Obsidian 的文献工作流工具。

安装向导将引导你完成以下配置：

1. 确认 Python 版本 (>= 3.8)
2. 检查 Vault 目录结构
3. 确认 Zotero 已安装
4. 确认 Better BibTeX 插件已安装
5. 确认 JSON 自动导出已配置

点击 **开始安装** 继续。
        """)
        yield Button("▶ 开始安装", id="btn-start", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-start":
            self.app.post_message(StepPassed(self.step_idx))


class PythonStep(StepScreen):
    """Step 1: Python 版本"""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Markdown("""
PaperForge 需要 **Python 3.8 或更高版本**。

当前环境将自动检测，无需手动操作。
        """)
        yield Horizontal(
            Button("🔍 自动检测", id="btn-check-python", variant="primary"),
            Button("⬇ 下载 Python", id="btn-dl-python", variant="default"),
            id="btn-row",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-check-python":
            result = self.checker.check_python()
            self.set_status(result.detail, result.passed)
            if result.passed:
                self.app.post_message(StepPassed(self.step_idx))
        elif event.button.id == "btn-dl-python":
            webbrowser.open("https://www.python.org/downloads/")


class VaultStep(StepScreen):
    """Step 2: Vault 结构"""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        vault_path = self.checker.vault.resolve()
        yield Markdown(f"""
PaperForge 需要特定的目录结构来存放文献数据。

当前 Vault 路径：`{vault_path}`

必要目录：
- `03_Resources/LiteratureControl/library-records/` — 文献状态跟踪
- `99_System/LiteraturePipeline/exports/` — Zotero JSON 导出
- `99_System/LiteraturePipeline/ocr/` — OCR 结果
- `99_System/Template/` — 模板文件
        """)
        yield Horizontal(
            Button("🔍 自动检测", id="btn-check-vault", variant="primary"),
            Button("📁 一键创建目录", id="btn-create-vault", variant="default"),
            id="btn-row",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-check-vault":
            result = self.checker.check_vault()
            self.set_status(result.detail, result.passed)
            if result.passed:
                self.app.post_message(StepPassed(self.step_idx))
        elif event.button.id == "btn-create-vault":
            dirs = [
                "03_Resources/LiteratureControl/library-records",
                "99_System/LiteraturePipeline/exports",
                "99_System/LiteraturePipeline/ocr",
                "99_System/Template",
            ]
            for d in dirs:
                (self.checker.vault / d).mkdir(parents=True, exist_ok=True)
            self.set_status("目录已创建，请重新检测", None)


class ZoteroStep(StepScreen):
    """Step 3: Zotero"""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Markdown("""
**Zotero** 是必需的文献管理软件。

如果自动检测不到，你可以手动输入 Zotero 安装路径（如 `C:\\Program Files\\Zotero\\zotero.exe`）。
        """)
        yield Horizontal(
            Button("🔍 自动检测", id="btn-check-zotero", variant="primary"),
            Button("⬇ 下载 Zotero", id="btn-dl-zotero", variant="default"),
            Button("📷 查看安装截图", id="btn-img-zotero", variant="default"),
            id="btn-row",
        )
        yield Static("或手动指定路径：", classes="step-title")
        from textual.widgets import Input
        yield Horizontal(
            Input(placeholder="C:\\Program Files\\Zotero\\zotero.exe", id="input-zotero-path"),
            Button("✓ 使用此路径", id="btn-manual-zotero", variant="primary"),
            id="manual-row",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-check-zotero":
            result = self.checker.check_zotero()
            self.set_status(result.detail, result.passed)
            if result.passed:
                self.app.post_message(StepPassed(self.step_idx))
        elif event.button.id == "btn-dl-zotero":
            webbrowser.open("https://www.zotero.org/download/")
        elif event.button.id == "btn-img-zotero":
            self.app.open_screenshot("zotero-install.png")
        elif event.button.id == "btn-manual-zotero":
            from textual.widgets import Input
            input_widget = self.query_one("#input-zotero-path", Input)
            path_str = input_widget.value.strip()
            if path_str:
                manual_path = Path(path_str)
                self.checker.manual_zotero_path = manual_path
                result = self.checker.check_zotero()
                self.set_status(result.detail, result.passed)
                if result.passed:
                    self.app.post_message(StepPassed(self.step_idx))


class BBTStep(StepScreen):
    """Step 4: Better BibTeX"""

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
    """Step 5: JSON Export"""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        exports_dir = self.checker.vault / "99_System" / "LiteraturePipeline" / "exports"
        yield Markdown(f"""
**Better BibTeX 自动导出**是 PaperForge 的数据来源。

**配置步骤：**
1. Zotero → 文件 → 导出库...
2. 格式选择 **Better BibLaTeX**
3. 保存到：`{exports_dir}/library.json`
4. 勾选 **Keep updated**（自动保持更新）

**📁 子分类与 Base 管理**

你可以根据 Zotero 收藏夹结构，灵活决定如何导出：

**方案 A：分开管理（推荐）**
为每个子分类分别创建 JSON：
```
Zotero 收藏夹结构
├── 骨科
│   ├── 关节外科      → 导出为 orthopedic-joint.json
│   └── 脊柱外科      → 导出为 orthopedic-spine.json
└── 运动医学
    └── 膝关节        → 导出为 sports-knee.json
```
每个 JSON 会生成一个独立的 Obsidian Base，便于分类查看。

**方案 B：统一管理**
为父分类创建单个 JSON：
```
医学文献（父分类）    → 导出为 medical-library.json
├── 骨科
│   ├── 关节外科
│   └── 脊柱外科
└── 运动医学
    └── 膝关节
```
所有文献放在同一个 Base 中，通过 `collection_path` 字段区分子分类。

**建议**：如果子分类文献量较大（>100篇），建议使用方案 A 分开管理。
        """)
        yield Horizontal(
            Button("🔍 自动检测", id="btn-check-json", variant="primary"),
            Button("📷 查看配置截图", id="btn-img-json", variant="default"),
            id="btn-row",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-check-json":
            result = self.checker.check_json()
            self.set_status(result.detail, result.passed)
            if result.passed:
                self.app.post_message(StepPassed(self.step_idx))
        elif event.button.id == "btn-img-json":
            self.app.open_screenshot("json-export.png")


class DoneStep(StepScreen):
    """Step 6: 完成页"""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Markdown("""
## 安装完成！

所有前置条件已满足，你现在可以开始使用 PaperForge Lite。

### 首次使用步骤：

**1. 同步 Zotero 文献**
```bash
python pipeline/worker/scripts/literature_pipeline.py --vault . selection-sync
```

**2. 生成正式笔记**
```bash
python pipeline/worker/scripts/literature_pipeline.py --vault . index-refresh
```

**3. 标记精读文献**
在 Obsidian 中打开 library-records 文件，设置：
- `do_ocr: true`
- `analyze: true`

**4. 运行 OCR**
```bash
python pipeline/worker/scripts/literature_pipeline.py --vault . ocr
```

**5. 执行精读**
在 OpenCode Agent 中输入：
```
/LD-deep <zotero_key>
```

### 已安装的 Agent 命令

安装向导已自动将以下命令安装到你的 Agent 中：

**精读命令：**
| 命令 | 作用 |
|------|------|
| `/LD-deep <key>` | 完整三阶段精读 |
| `/LD-paper <key>` | 快速摘要 |

**Worker 快捷命令：**
| 命令 | 作用 |
|------|------|
| `/lp-selection-sync` | 同步 Zotero 新文献 |
| `/lp-index-refresh` | 生成正式笔记 |
| `/lp-ocr` | 运行 PDF OCR |
| `/lp-status` | 查看工作流状态 |

**Python 脚本命令（备用）：**
```bash
python pipeline/worker/scripts/literature_pipeline.py --vault . <command>
```
| 命令 | 作用 |
|------|------|
| `selection-sync` | 检测新文献 |
| `index-refresh` | 生成正式笔记 |
| `ocr` | PDF OCR |
| `deep-reading` | 查看精读队列 |
| `update` | 检查更新 |

### 详细文档

- 安装后指南：`AGENTS.md`
- 图表阅读指南：`99_System/Template/科研读图指南.md`
- GitHub: https://github.com/LLLin000/PaperForge
        """)
        yield Horizontal(
            Button("📖 打开详细指南", id="btn-open-guide", variant="primary"),
            Button("🔄 重新检测", id="btn-restart", variant="default"),
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
                            PythonStep("step-1", self.checker),
                            VaultStep("step-2", self.checker),
                            ZoteroStep("step-3", self.checker),
                            BBTStep("step-4", self.checker),
                            JsonStep("step-5", self.checker),
                            DoneStep("step-6", self.checker),
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
            if hasattr(screen, 'set_status'):
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

def main() -> int:
    parser = argparse.ArgumentParser(description="PaperForge Lite 安装向导")
    parser.add_argument("--vault", type=Path, default=Path("."), help="Vault 路径")
    args = parser.parse_args()

    vault = args.vault.resolve()
    if not (vault / "paperforge.json").exists():
        print(f"[ERR] 未找到 paperforge.json: {vault}")
        print("请先在 Vault 根目录运行 setup.py 完成初始安装")
        return 1

    app = SetupWizardApp(vault)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
