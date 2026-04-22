#!/usr/bin/env python3
"""
PaperForge Lite 安装向导 (Textual TUI)

Usage:
    python setup_wizard.py --vault /path/to/vault

功能：
    1. 检测前置条件（Zotero, Better BibTeX, JSON导出, Vault结构）
    2. 逐项检查，通过后自动打勾
    3. 全部通过解锁操作指南
    4. 操作指南说明工作流和首次使用步骤
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import winreg
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    RichLog,
    Static,
)


# =============================================================================
# 检测逻辑
# =============================================================================

class CheckItem:
    """单个检查项"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = "pending"  # pending, checking, pass, fail
        self.detail = ""  # 详细说明或错误信息

    @property
    def icon(self) -> str:
        return {
            "pending": "[gray]○[/]",
            "checking": "[yellow]⟳[/]",
            "pass": "[green]✓[/]",
            "fail": "[red]✗[/]",
        }.get(self.status, "○")


class Checker:
    """检测器"""
    def __init__(self, vault: Path):
        self.vault = vault
        self.items: list[CheckItem] = [
            CheckItem("Python版本", "需要 Python >= 3.8"),
            CheckItem("Vault目录结构", "必要的文件夹是否存在"),
            CheckItem("Zotero安装", "Zotero 文献管理软件"),
            CheckItem("Better BibTeX插件", "Zotero 的 Better BibTeX 插件"),
            CheckItem("JSON导出文件", "Better BibTeX 自动导出的 JSON"),
        ]

    def check_python(self) -> None:
        item = self.items[0]
        item.status = "checking"
        v = sys.version_info
        if v >= (3, 8):
            item.status = "pass"
            item.detail = f"Python {v.major}.{v.minor}.{v.micro} ✓"
        else:
            item.status = "fail"
            item.detail = f"当前 Python {v.major}.{v.minor}.{v.micro}，需要 >= 3.8"

    def check_vault_structure(self) -> None:
        item = self.items[1]
        item.status = "checking"
        required = [
            "03_Resources/LiteratureControl/library-records",
            "99_System/LiteraturePipeline/exports",
            "99_System/LiteraturePipeline/ocr",
            "99_System/Template",
        ]
        missing = []
        for rel in required:
            if not (self.vault / rel).exists():
                missing.append(rel)
        if not missing:
            item.status = "pass"
            item.detail = "所有必要目录已就绪"
        else:
            item.status = "fail"
            item.detail = f"缺少: {', '.join(missing)}\n请运行 setup.py 创建目录结构"

    def check_zotero(self) -> None:
        item = self.items[2]
        item.status = "checking"
        zotero_path = self._find_zotero()
        if zotero_path:
            item.status = "pass"
            item.detail = f"找到: {zotero_path}"
        else:
            item.status = "fail"
            item.detail = "未找到 Zotero\n请访问 https://www.zotero.org/download/ 下载安装"

    def _find_zotero(self) -> Optional[Path]:
        system = platform.system()
        if system == "Windows":
            # 检查注册表
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Zotero") as key:
                    install_dir, _ = winreg.QueryValueEx(key, "InstallDir")
                    path = Path(install_dir) / "zotero.exe"
                    if path.exists():
                        return path
            except (FileNotFoundError, OSError):
                pass
            # 检查常见路径
            for p in [
                Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Zotero" / "zotero.exe",
                Path(os.environ.get("LOCALAPPDATA", r"C:\Users\%USERNAME%\AppData\Local")) / "Zotero" / "zotero.exe",
            ]:
                if p.exists():
                    return p
        elif system == "Darwin":
            p = Path("/Applications/Zotero.app/Contents/MacOS/zotero")
            if p.exists():
                return p
        else:  # Linux
            for p in [Path.home() / ".local" / "share" / "zotero" / "zotero"]:
                if p.exists():
                    return p
            try:
                result = subprocess.run(["which", "zotero"], capture_output=True, text=True)
                if result.returncode == 0:
                    return Path(result.stdout.strip())
            except Exception:
                pass
        return None

    def check_better_bibtex(self) -> None:
        item = self.items[3]
        item.status = "checking"
        system = platform.system()
        bbt_found = False
        bbt_path = None

        if system == "Windows":
            # Zotero profile 目录
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
        else:  # Linux
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
            item.status = "pass"
            item.detail = f"已安装: {bbt_path.name if bbt_path else 'Better BibTeX'}"
        else:
            item.status = "fail"
            item.detail = (
                "未找到 Better BibTeX 插件\n"
                "安装步骤:\n"
                "  1. 下载插件: https://retorque.re/zotero-better-bibtex/\n"
                "  2. Zotero → 工具(Tools) → 插件(Plugins)\n"
                "  3. 齿轮图标 → Install Plugin From File...\n"
                "  4. 选择下载的 .xpi 文件 → 重启 Zotero"
            )

    def check_json_exports(self) -> None:
        item = self.items[4]
        item.status = "checking"
        exports_dir = self.vault / "99_System" / "LiteraturePipeline" / "exports"
        if not exports_dir.exists():
            item.status = "fail"
            item.detail = (
                f"导出目录不存在: {exports_dir}\n"
                "配置步骤:\n"
                "  1. Zotero → 编辑(Edit) → 首选项(Preferences)\n"
                "  2. 左侧选择 Better BibTeX\n"
                "  3. 找到 'Automatic export' 勾选 'On Change'\n"
                "  4. 文件 → 导出库(Export Library)...\n"
                "  5. 格式: Better BibLaTeX\n"
                f"  6. 保存到: {exports_dir}/library.json\n"
                "  7. 勾选 'Keep updated' → 确定"
            )
            return

        json_files = list(exports_dir.glob("*.json"))
        if not json_files:
            item.status = "fail"
            item.detail = (
                f"未找到 JSON 文件\n"
                "配置步骤:\n"
                "  1. Zotero → 文件 → 导出库(Export Library)...\n"
                "  2. 格式: Better BibLaTeX\n"
                f"  3. 保存到: {exports_dir}/library.json\n"
                "  4. 勾选 'Keep updated'\n"
                "每个 JSON 对应一个 Base 视图"
            )
            return

        # 验证 JSON 格式
        valid_files = []
        for jf in json_files:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                if isinstance(data, list) and len(data) > 0:
                    valid_files.append(jf.name)
            except (json.JSONDecodeError, Exception):
                pass

        if valid_files:
            item.status = "pass"
            item.detail = f"找到 {len(valid_files)} 个有效的 JSON 导出:\n" + "\n".join(f"  • {f}" for f in valid_files)
        else:
            item.status = "fail"
            item.detail = (
                f"找到 {len(json_files)} 个 JSON 但格式无效\n"
                "请确认导出格式为 'Better BibLaTeX' 而非 'BibTeX'"
            )

    def check_all(self) -> None:
        self.check_python()
        self.check_vault_structure()
        self.check_zotero()
        self.check_better_bibtex()
        self.check_json_exports()

    @property
    def all_passed(self) -> bool:
        return all(item.status == "pass" for item in self.items)


# =============================================================================
# Textual 界面
# =============================================================================

class CheckListItem(Static):
    """单个检查项的 UI 组件"""
    def __init__(self, item: CheckItem):
        super().__init__()
        self.item = item

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(self.item.icon, id=f"icon-{id(self.item)}")
            with Vertical():
                yield Label(f"[b]{self.item.name}[/b]", id=f"name-{id(self.item)}")
                yield Label(self.item.description, classes="description")
                yield Label(self.item.detail, id=f"detail-{id(self.item)}", classes="detail")

    def update_status(self) -> None:
        icon = self.query_one(f"#icon-{id(self.item)}", Label)
        icon.update(self.item.icon)
        detail = self.query_one(f"#detail-{id(self.item)}", Label)
        detail.update(self.item.detail)
        detail.classes = f"detail {self.item.status}"


class SetupWizard(App):
    """安装向导主应用"""
    CSS = """
    Screen { align: center middle; }
    .title { text-align: center; content-align: center; padding: 1; }
    .check-panel { width: 50%; height: 100%; border: solid green; padding: 1; }
    .guide-panel { width: 50%; height: 100%; border: solid blue; padding: 1; }
    .check-item { padding: 0 1; margin: 1 0; }
    .check-item .description { color: gray; text-style: italic; }
    .check-item .detail { margin-top: 0; }
    .check-item .detail.pass { color: green; }
    .check-item .detail.fail { color: red; }
    .check-item .detail.pending { color: gray; }
    .locked { color: gray; text-align: center; content-align: center; }
    .guide-content { color: white; padding: 1; }
    .step { margin: 1 0; padding: 1; border: solid gray; }
    .step-header { text-style: bold; color: yellow; }
    .command { background: black; color: cyan; padding: 0 1; }
    .info { color: cyan; }
    .warning { color: yellow; }
    #log { height: 5; border: solid gray; }
    """

    BINDINGS = [
        ("q", "quit", "退出"),
        ("r", "refresh_checks", "重新检测"),
    ]

    def __init__(self, vault: Path):
        super().__init__()
        self.vault = vault
        self.checker = Checker(vault)
        self.check_widgets: list[CheckListItem] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("[b]PaperForge Lite 安装向导[/b]\n配置检查与首次使用指南", classes="title")
        
        with Horizontal():
            # 左侧：检查清单
            with Vertical(classes="check-panel"):
                yield Static("[b]前置检查[/b]", classes="title")
                
                for item in self.checker.items:
                    widget = CheckListItem(item)
                    self.check_widgets.append(widget)
                    yield widget
                
                yield Button("检测全部", id="check-all", variant="primary")
                
            # 右侧：操作指南
            with Vertical(classes="guide-panel"):
                yield Static("[b]操作指南[/b]", classes="title")
                self.guide_container = Vertical(id="guide-content")
                yield self.guide_container
                yield Button("📖 打开图文指南", id="open-guide", variant="primary")
        
        yield RichLog(id="log", highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#log", RichLog).write("[green]欢迎使用 PaperForge Lite 安装向导[/]")
        self.query_one("#log", RichLog).write("点击 [b]检测全部[/b] 开始检查前置条件...")
        self._update_guide()

    def _update_guide(self) -> None:
        """更新操作指南显示"""
        guide = self.guide_container
        guide.remove_children()
        
        if not self.checker.all_passed:
            guide.mount(Static(
                "\n\n[yellow]🔒 操作指南已锁定[/]\n\n"
                "请先完成左侧所有检查项，\n"
                "全部通过后将解锁详细操作指南。\n\n"
                "每个 JSON 导出文件将对应一个 Obsidian Base 视图，\n"
                "用于管理不同领域的文献。",
                classes="locked"
            ))
            return
        
        # 解锁后的详细指南
        guide_content = """
## 🎉 恭喜！所有检查通过

现在你可以开始使用 PaperForge Lite 了。

### 📚 核心概念

**Base 与 JSON 的关系：**
每个 Better BibTeX 导出的 JSON 文件对应一个 **Obsidian Base** 视图。
- 如果你有 `骨科.json` → 生成 `骨科.base`
- 如果你有 `运动医学.json` → 生成 `运动医学.base`

**完整工作流：**
```
Zotero 添加文献
    ↓ Better BibTeX 自动导出 JSON
exports/*.json
    ↓ 运行 selection-sync
library-records/*.md（状态跟踪）
    ↓ 运行 index-refresh
Literature/*.md（正式笔记）
    ↓ 标记 do_ocr + analyze
运行 ocr → OCR 提取全文
    ↓ 用户运行 /LD-deep
Agent 精读 → 笔记追加精读内容
```

### 🚀 首次使用步骤

[step-1]
**Step 1: 同步 Zotero 文献**

运行以下命令检测新文献并创建状态记录：
```
python pipeline/worker/scripts/literature_pipeline.py --vault . selection-sync
```

预期输出：`Found X new items, created library-records/...`
[/step-1]

[step-2]
**Step 2: 生成正式笔记**

将状态记录转换为正式的 Obsidian 笔记：
```
python pipeline/worker/scripts/literature_pipeline.py --vault . index-refresh
```

预期输出：`Generated X formal notes`
[/step-2]

[step-3]
**Step 3: 标记要精读的文献**

在 Obsidian 中打开任意 `library-records/*.md` 文件：
- 将 `do_ocr: false` → `do_ocr: true`（触发 OCR）
- 将 `analyze: false` → `analyze: true`（标记精读）

或使用 Obsidian Base 视图批量操作。
[/step-3]

[step-4]
**Step 4: 运行 OCR**
```
python pipeline/worker/scripts/literature_pipeline.py --vault . ocr
```

等待 OCR 完成（需要配置 PaddleOCR API Key）。
[/step-4]

[step-5]
**Step 5: 执行深度精读**

在 OpenCode Agent 中执行：
```
/LD-deep <zotero_key>
```

Agent 将自动生成 `## 🔍 精读` 区域。
[/step-5]

### ⚡ 快捷命令

| 命令 | 作用 |
|------|------|
| `selection-sync` | 检测 Zotero 新条目 |
| `index-refresh` | 生成/更新正式笔记 |
| `ocr` | 运行 PDF OCR |
| `deep-reading` | 查看精读队列 |
| `update` | 检查并安装更新 |

### 📖 详细文档

- 安装后指南：`AGENTS.md`
- 图表阅读指南：`99_System/Template/科研读图指南.md`
- GitHub: https://github.com/LLLin000/PaperForge
"""
        guide.mount(Static(guide_content, classes="guide-content"))
        self.query_one("#log", RichLog).write("[green]✓ 操作指南已解锁！请查看右侧[/]")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "check-all":
            log = self.query_one("#log", RichLog)
            log.write("[yellow]开始检测...[/]")
            
            for item in self.checker.items:
                item.status = "checking"
            self._refresh_checks()
            
            # 执行检测
            self.checker.check_all()
            
            # 更新 UI
            self._refresh_checks()
            
            passed = sum(1 for i in self.checker.items if i.status == "pass")
            total = len(self.checker.items)
            
            if self.checker.all_passed:
                log.write(f"[green]✓ 全部通过 ({passed}/{total})[/]")
                self._update_guide()
            else:
                failed = [i.name for i in self.checker.items if i.status == "fail"]
                log.write(f"[red]✗ 未通过项: {', '.join(failed)}[/]")
                log.write("[yellow]请修复上述问题后重新检测[/]")
        
        elif event.button.id == "open-guide":
            guide_path = self.vault / "docs" / "setup-guide.md"
            if guide_path.exists():
                if sys.platform == "win32":
                    os.startfile(str(guide_path))
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(guide_path)])
                else:
                    subprocess.run(["xdg-open", str(guide_path)])
                self.query_one("#log", RichLog).write(f"[green]已打开: {guide_path}[/]")
            else:
                self.query_one("#log", RichLog).write("[yellow]未找到本地指南，尝试打开在线文档...[/]")
                import webbrowser
                webbrowser.open("https://github.com/LLLin000/PaperForge/blob/master/docs/setup-guide.md")

    def _refresh_checks(self) -> None:
        """刷新检查项显示"""
        for widget in self.check_widgets:
            widget.update_status()

    def action_refresh_checks(self) -> None:
        """快捷键重新检测"""
        button = self.query_one("#check-all", Button)
        button.press()


# =============================================================================
# 入口
# =============================================================================

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="PaperForge Lite 安装向导")
    parser.add_argument("--vault", type=Path, default=Path("."), help="Vault 路径")
    args = parser.parse_args()
    
    vault = args.vault.resolve()
    if not (vault / "paperforge.json").exists():
        print(f"[ERR] 未找到 paperforge.json: {vault}")
        print("请先在 Vault 根目录运行 setup.py 完成初始安装")
        return 1
    
    app = SetupWizard(vault)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
