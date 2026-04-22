#!/usr/bin/env python3
"""Interactive installer for the Literature Workflow."""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path
from typing import Optional


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


# Agent platform configurations
AGENT_CONFIGS = {
    "opencode": {
        "name": "OpenCode",
        "skill_dir": ".opencode/skills",
        "config_file": None,
    },
    "claude": {
        "name": "Claude Code",
        "skill_dir": ".claude/skills",
        "config_file": ".claude/skills.json",
    },
    "cursor": {
        "name": "Cursor",
        "skill_dir": ".cursor/skills",
        "config_file": ".cursor/settings.json",
    },
    "windsurf": {
        "name": "Windsurf",
        "skill_dir": ".windsurf/skills",
        "config_file": None,
    },
    "github_copilot": {
        "name": "GitHub Copilot",
        "skill_dir": ".github/skills",
        "config_file": ".github/copilot-instructions.md",
    },
    "cline": {
        "name": "Cline",
        "skill_dir": ".clinerules/skills",
        "config_file": ".clinerules",
    },
    "augment": {
        "name": "Augment",
        "skill_dir": ".augment/skills",
        "config_file": None,
    },
    "trae": {
        "name": "Trae",
        "skill_dir": ".trae/skills",
        "config_file": None,
    },
}


def select_agent() -> tuple[str, dict]:
    """Ask user to select their AI agent platform."""
    print_header("Step 0: Agent Platform Selection")
    print("Which AI agent do you use with this vault?")
    print("(This determines where skill files and configurations are placed)\n")
    
    agents = list(AGENT_CONFIGS.items())
    for i, (key, cfg) in enumerate(agents, 1):
        print(f"  {i}. {cfg['name']} ({key})")
    print(f"  {len(agents) + 1}. Other (custom)")
    
    choice = ask("Select agent", default="1")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(agents):
            return agents[idx]
        elif idx == len(agents):
            # Custom agent
            custom_name = ask("Enter agent name")
            custom_dir = ask("Enter skill directory (relative to vault)", default=".custom/skills")
            return "custom", {
                "name": custom_name,
                "skill_dir": custom_dir,
                "config_file": None,
            }
    except ValueError:
        pass
    
    # Default to OpenCode
    print_warning("Invalid choice, defaulting to OpenCode")
    return "opencode", AGENT_CONFIGS["opencode"]


def configure_vault_paths(vault_path: Path) -> dict:
    """Ask user for PaperForge-specific directory structure preferences."""
    print_header("Step 0.5: Vault Directory Configuration")
    print("Configure PaperForge directory structure (press Enter to accept defaults):\n")
    print("Note: 00_Inbox, 04_Archives, 05_Bases, 06_AI_Wiki are your personal PARA folders.")
    print("      PaperForge will NOT create them.\n")
    
    paths = {
        "system_dir": ask("System folder name", default="99_System"),
        "resources_dir": ask("Resources folder name", default="03_Resources"),
        "literature_dir": ask("Literature subfolder (for generated notes)", default="Literature"),
    }
    
    # Build derived paths
    paths["pipeline_path"] = f"{paths['system_dir']}/PaperForge"
        paths["literature_path"] = f"{paths['resources_dir']}/{paths['literature_dir']}"
    
    return paths
    
    return paths


def print_header(text: str) -> None:
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")


def print_success(text: str) -> None:
    print(f"{Colors.OKGREEN}[OK]{Colors.ENDC} {text}")


def print_warning(text: str) -> None:
    print(f"{Colors.WARNING}[WARN]{Colors.ENDC} {text}")


def print_error(text: str) -> None:
    print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {text}")


def ask(question: str, default: Optional[str] = None) -> str:
    """Ask user a question with optional default."""
    if default:
        prompt = f"{question} [{default}]: "
    else:
        prompt = f"{question}: "
    
    answer = input(prompt).strip()
    if not answer and default:
        return default
    return answer


def ask_yes_no(question: str, default: bool = False) -> bool:
    """Ask a yes/no question."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    answer = input(f"{question}{suffix}").strip().lower()
    if not answer:
        return default
    return answer in ('y', 'yes', 'true', '1')


def detect_zotero_path() -> Optional[Path]:
    """Auto-detect Zotero data directory."""
    system = platform.system()
    
    if system == "Windows":
        # Check common locations
        home = Path.home()
        candidates = [
            home / "Zotero",
            home / "AppData" / "Roaming" / "Zotero" / "Zotero",
            Path("C:/Users") / os.environ.get("USERNAME", "") / "Zotero",
        ]
    elif system == "Darwin":  # macOS
        home = Path.home()
        candidates = [
            home / "Zotero",
            home / "Library" / "Application Support" / "Zotero",
        ]
    else:  # Linux
        home = Path.home()
        candidates = [
            home / "Zotero",
            home / ".zotero",
        ]
    
    for candidate in candidates:
        if candidate.exists() and (candidate / "zotero.sqlite").exists():
            return candidate
    
    return None


def create_junction(source: Path, target: Path) -> bool:
    """Create junction/symlink from source to target."""
    system = platform.system()
    
    try:
        if system == "Windows":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(source), str(target)],
                check=True,
                capture_output=True,
                shell=False,
            )
        else:
            source.symlink_to(target, target_is_directory=True)
        return True
    except (subprocess.CalledProcessError, OSError) as e:
        print_error(f"Failed to create junction: {e}")
        return False


def check_python_deps() -> list[str]:
    """Check if required Python packages are installed."""
    required = ["requests", "pymupdf", "PIL", "pytest"]
    missing = []
    
    for package in required:
        try:
            __import__(package.lower().replace("pil", "PIL"))
        except ImportError:
            missing.append(package)
    
    return missing


def install_deps(deps: list[str]) -> bool:
    """Install missing Python dependencies."""
    if not deps:
        return True
    
    print(f"Installing dependencies: {', '.join(deps)}")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install"] + deps,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False


def create_directory_structure(vault_path: Path, paths: dict) -> None:
    """Create PaperForge directory structure with configurable paths."""
    dirs = [
        # Core pipeline directories
        f"{paths['pipeline_path']}/ocr",
        f"{paths['pipeline_path']}/worker/scripts",
        f"{paths['pipeline_path']}/worker/tests",
        f"{paths['pipeline_path']}/indexes",
        f"{paths['pipeline_path']}/exports",
        
        # Zotero junction point
        f"{paths['system_dir']}/Zotero",
        
        # Library records (for selection_sync state)
        f"03_Resources/LiteratureControl/library-records",
    ]
    
    for d in dirs:
        (vault_path / d).mkdir(parents=True, exist_ok=True)
        print_success(f"Created: {d}")
    
    print_success(f"Directory structure created ({len(dirs)} folders)")


def create_env_file(vault_path: Path, config: dict, paths: dict) -> None:
    """Create .env configuration file."""
    env_path = vault_path / ".env"
    
    lines = [
        "# PaperForge Configuration",
        f"ZOTERO_DATA_DIR={config['zotero_path']}",
        f"ZOTERO_STORAGE_DIR={config.get('storage_path', config['zotero_path'])}",
        f"PADDLEOCR_API_TOKEN={config['ocr_api_key']}",
        "PADDLEOCR_JOB_URL=https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
        "",
        "# Agent Configuration",
        f"PAPERFORGE_AGENT={config['agent']}",
        f"PAPERFORGE_AGENT_NAME={config['agent_name']}",
        f"PAPERFORGE_SKILL_DIR={config['skill_dir']}",
        "",
        "# Path Configuration",
        f"PAPERFORGE_SYSTEM_DIR={paths['system_dir']}",
        f"PAPERFORGE_PIPELINE_PATH={paths['pipeline_path']}",
        f"PAPERFORGE_RESOURCES_PATH={paths['literature_path']}",
        f"PAPERFORGE_VAULT_PATH={vault_path}",
    ]
    
    env_path.write_text("\n".join(lines), encoding="utf-8")
    print_success(f"Configuration saved to {env_path}")


def create_agents_md(vault_path: Path, config: dict, paths: dict, agent_config: dict) -> None:
    """Generate AGENTS.md with user-configured paths embedded.
    
    This creates a complete Lite-version workflow guide that is personalized
    to the user's chosen directory structure, not a static template.
    """
    agents_path = vault_path / "AGENTS.md"
    
    if agents_path.exists():
        if not ask_yes_no("AGENTS.md already exists. Overwrite?", default=False):
            print_warning("Skipping AGENTS.md creation")
            return
    
    # Build the personalized AGENTS.md content
    # All paths come from the user's configuration (paths dict)
    content = f"""# PaperForge Lite - Agent Guide

> 本文档面向 **安装完成后的新用户** 和 **AI Agent**。  
> 安装步骤见 [INSTALLATION.md](docs/INSTALLATION.md)。  
> 本 Vault 使用自定义目录结构生成，路径以实际配置为准。

---

## 0. 安装后检查清单（第一次使用前必做）

```
[ ] Zotero 已安装 + Better BibTeX 插件已启用
[ ] Better BibTeX 已配置自动导出 JSON（见下方配置）
[ ] Obsidian 已打开当前 Vault
[ ] Python 依赖已安装 (pip install requests pymupdf pillow)
[ ] PaddleOCR API Key 已配置（在 .env 中）
[ ] 目录结构已创建（setup.py 会自动完成）
[ ] Zotero 数据目录已链接到 {paths['system_dir']}/Zotero
```

### Better BibTeX 自动导出配置

1. Zotero → Edit → Preferences → Better BibTeX
2. 勾选 **"Keep updated"**（自动导出）
3. 选择导出格式：**Better BibLaTeX** 或 **Better BibTeX**
4. 导出路径设置为：`{vault_path}/{paths['pipeline_path']}/exports/library.json`
5. 点击 OK，JSON 文件会自动生成并保持同步

---

## 1. 核心架构（Lite 版）

PaperForge Lite 采用 **两层设计**：

| 层级 | 组件 | 触发方式 | 作用 |
|------|------|----------|------|
| **Worker 层** | `literature_pipeline.py`（4 个 workers） | Python CLI | 后台自动化 |
| **Agent 层** | `/LD-deep`, `/LD-paper` 命令 | 用户手动触发 | 交互式精读 |

**关键区别**：
- **Worker 只做机械劳动**（检测新文献、生成笔记、OCR）
- **Agent 只做深度思考**（精读、分析、写作）
- Worker 不会自动触发 Agent，Agent 不会自动触发 Worker

---

## 2. 完整数据流

```
Zotero 添加文献
    ↓ Better BibTeX 自动导出 JSON
{paths['pipeline_path']}/exports/library.json
    ↓ 运行 selection-sync
{paths['resources_dir']}/LiteratureControl/library-records/<domain>/<key>.md
    ↓ 运行 index-refresh
{paths['literature_path']}/<domain>/<key> - <Title>.md（正式笔记）
    ↓ 用户在 library-record 中设置 do_ocr: true
运行 ocr → {paths['pipeline_path']}/ocr/<key>/
    ↓ 用户在 library-record 中设置 analyze: true
运行 deep-reading（查看队列，确认就绪）
    ↓ 用户执行 Agent 命令
/LD-deep <zotero_key>
    ↓ Agent 生成
正式笔记中新增 ## 🔍 精读 区域
```

---

## 3. 目录结构（本 Vault 配置）

```
{vault_path}/
├── {paths['resources_dir']}/
│   ├── {paths['literature_dir']}/              ← 正式文献笔记（index-refresh 生成）
│   │   ├── 骨科/
│   │   ├── 运动医学/
│   │   └── ...（你的分类）
│   └── LiteratureControl/                      ← 状态跟踪
│       └── library-records/                    ← selection-sync 输出
│           ├── 骨科/
│           │   └── ABCDEFG.md                  ← 单条文献状态记录
│           └── 运动医学/
│               └── HIJKLMN.md
│
├── {paths['system_dir']}/
│   ├── PaperForge/
│   │   ├── exports/                            ← Better BibTeX 自动导出的 JSON
│   │   │   └── library.json
│   │   ├── ocr/                                ← OCR 结果（每个文献一个子目录）
│   │   │   └── ABCDEFG/                        ← Zotero key 作为目录名
│   │   │       ├── fulltext.md                 ← OCR 提取的全文
│   │   │       ├── images/                     ← 图表切割图片
│   │   │       ├── meta.json                   ← OCR 元数据（含 ocr_status）
│   │   │       └── figure-map.json             ← 图表索引（自动创建）
│   │   └── worker/scripts/
│   │       └── literature_pipeline.py          ← 核心脚本
│   └── Zotero/                                 ← Junction/Symlink 到 Zotero 数据目录
│
├── {agent_config['skill_dir']}/                ← {agent_config['name']} Skill 目录
│   └── literature-qa/                          ← 深度阅读 Skill
│       ├── scripts/
│       │   └── ld_deep.py                      ← /LD-deep 核心脚本
│       ├── prompt_deep_subagent.md             ← Agent 精读提示词
│       └── chart-reading/                      ← 14 种图表阅读指南
│
├── .env                                        ← API Key 等敏感配置
└── AGENTS.md                                   ← 本文件
```

### 各目录作用速查

| 目录 | 内容 | 谁生成/修改 |
|------|------|------------|
| `{paths['literature_path']}/` | 正式文献笔记（含 frontmatter + 精读内容） | index-refresh 生成，Agent 写入精读 |
| `{paths['resources_dir']}/LiteratureControl/library-records/` | 文献状态跟踪（analyze, ocr_status 等） | selection-sync 生成，用户修改状态 |
| `{paths['pipeline_path']}/exports/` | Better BibTeX JSON 导出 | Zotero 自动导出 |
| `{paths['pipeline_path']}/ocr/` | OCR 全文 + 图表切割 | ocr worker 生成 |
| `{paths['system_dir']}/Zotero/` | Zotero 数据目录的链接 | 安装时手动创建 junction |

---

## 4. 核心 Workers（Lite 版，4 个）

### selection-sync
- **作用**：检测 Zotero 中的新条目，创建 library-records
- **运行时机**：添加新文献到 Zotero 后
- **输出**：`{paths['resources_dir']}/LiteratureControl/library-records/<domain>/<key>.md`
- **示例**：
  ```bash
  python {paths['pipeline_path']}/worker/scripts/literature_pipeline.py \\
    --vault "{vault_path}" selection-sync
  ```

### index-refresh
- **作用**：基于 library-records 生成正式文献笔记
- **运行时机**：selection-sync 之后，或需要更新笔记格式时
- **输出**：`{paths['literature_path']}/<domain>/<key> - <Title>.md`
- **说明**：会读取 Better BibTeX JSON 提取元数据，生成带 frontmatter 的 Obsidian 笔记

### ocr
- **作用**：将 PDF 上传到 PaddleOCR API，提取全文文本和图表
- **触发条件**：library-record 中 `do_ocr: true`
- **输出**：`{paths['pipeline_path']}/ocr/<key>/` 目录
  - `fulltext.md`：提取的全文（含 `<!-- page N -->` 分页标记）
  - `images/`：自动切割的图表图片
  - `meta.json`：OCR 状态（`ocr_status: done/pending/processing/failed`）
  - `figure-map.json`：图表索引（后续自动生成）
- **注意**：OCR 是异步的，大文件可能需要几分钟

### deep-reading
- **作用**：扫描所有 library-records，列出 `analyze=true` 且 OCR 完成的文献
- **运行时机**：用户想看看哪些文献可以开始精读了
- **输出**：控制台表格，显示队列状态
- **重要**：这只是**查看队列**，不会自动触发 Agent 精读

---

## 5. Agent 命令（用户手动触发）

| 命令 | 用途 | 前置条件 |
|------|------|----------|
| `/LD-deep <zotero_key>` | 完整 Keshav 三阶段精读 | OCR 完成 (`ocr_status: done`) |
| `/LD-paper <zotero_key>` | 快速摘要（无 OCR 要求） | 有正式笔记即可 |

### /LD-deep 执行流程

1. **prepare 阶段**（自动）：
   - 查找 library-record（确认 `analyze: true`）
   - 检查 OCR 状态
   - 读取 formal note
   - 生成 figure-map.json（图表索引）
   - 生成 chart-type-map.json（图表类型识别）
   - 在正式笔记中插入 `## 🔍 精读` 骨架

2. **精读阶段**（Agent 执行）：
   - Pass 1: 概览（5-10 分钟快速扫描）
   - Pass 2: 精读还原（逐图逐表分析）
   - Pass 3: 深度理解（批判性评估 + 迁移思考）

3. **验证阶段**（自动）：
   - 检查 callout 间距
   - 检查必要 section 是否完整
   - 检查 figure/table embed 是否存在

---

## 6. Frontmatter 字段参考

### Library Record（`{paths['resources_dir']}/LiteratureControl/library-records/<domain>/<key>.md`）

这是**用户控制工作流的核心**。每个文献对应一个 record 文件：

```yaml
---
zotero_key: "ABCDEFG"           # Zotero citation key（自动生成）
domain: "骨科"                   # 分类领域（对应 Zotero 收藏夹）
title: "论文标题"
year: 2024
doi: "10.xxxx/xxxxx"
collection_path: "子分类"         # Zotero 子收藏夹路径
has_pdf: true                     # 是否有 PDF 附件（自动生成）
pdf_path: "{paths['system_dir']}/Zotero/..."  # PDF 相对路径（自动生成）
fulltext_md_path: "{paths['pipeline_path']}/ocr/..."
recommend_analyze: true           # 系统推荐精读（有 PDF 时自动设为 true）
analyze: false                    # 【用户控制】是否生成精读？设为 true 触发
do_ocr: true                      # 【用户控制】是否运行 OCR？设为 true 触发
ocr_status: "done"                # OCR 状态（pending/processing/done/failed）
deep_reading_status: "pending"    # 精读状态（pending/done）
analysis_note: ""                 # 预留字段
---
```

**用户操作方式**：
- 在 Obsidian 中打开 library-record 文件
- 修改 `analyze: false` → `analyze: true` 标记要精读的文献
- 修改 `do_ocr: false` → `do_ocr: true` 触发 OCR
- 或使用 Obsidian Base 视图批量操作

### Formal Note（`{paths['literature_path']}/<domain>/<key> - <Title>.md`）

这是最终产出的笔记，包含元数据 + 精读内容：

```yaml
---
title: "论文标题"
year: 2024
type: "journal"
journal: "Journal Name"
impact_factor: 5.2
category: "骨科"
tags:
  - 文献阅读
  - 子分类
keywords: ["keyword1", "keyword2"]
pdf_link: "{paths['system_dir']}/Zotero/..."
---
```

---

## 7. 第一次使用指南（手把手）

### Step 1: 确认 Zotero 有文献

确保 Zotero 中已有至少一篇带 PDF 的文献，且 Better BibTeX 已导出 JSON。

### Step 2: 运行 selection-sync

```bash
# 在 Vault 根目录执行
python {paths['pipeline_path']}/worker/scripts/literature_pipeline.py \\
  --vault "{vault_path}" selection-sync
```

预期输出：
```
[INFO] Found 5 new items
[INFO] Created library-records/骨科/XXXXXXX.md
...
```

### Step 3: 运行 index-refresh

```bash
python {paths['pipeline_path']}/worker/scripts/literature_pipeline.py \\
  --vault "{vault_path}" index-refresh
```

预期输出：
```
[INFO] Generated 5 formal notes
[INFO] Output: {paths['literature_path']}/骨科/XXXXXXX - Title.md
...
```

### Step 4: 标记要精读的文献

在 Obsidian 中：
1. 打开 `{paths['resources_dir']}/LiteratureControl/library-records/骨科/XXXXXXX.md`
2. 将 `do_ocr: false` 改为 `do_ocr: true`
3. 将 `analyze: false` 改为 `analyze: true`
4. 保存文件

### Step 5: 运行 OCR

```bash
python {paths['pipeline_path']}/worker/scripts/literature_pipeline.py \\
  --vault "{vault_path}" ocr
```

等待完成（可能需要几分钟）。

### Step 6: 检查 OCR 状态

```bash
python {paths['pipeline_path']}/worker/scripts/literature_pipeline.py \\
  --vault "{vault_path}" deep-reading
```

预期输出：
```
## 就绪 (1 篇) — OCR 完成
- `XXXXXXX` | 骨科 | 论文标题
```

### Step 7: 执行精读

在 {agent_config['name']} Agent 中输入：
```
/LD-deep XXXXXXX
```

Agent 会自动：
1. 准备精读骨架（prepare）
2. 逐阶段填写精读内容
3. 验证结构完整性

### Step 8: 查看结果

在 Obsidian 中打开正式笔记，找到 `## 🔍 精读` 区域，精读已完成。

---

## 8. 常用命令速查

```bash
# 检测 Zotero 新条目
python {paths['pipeline_path']}/worker/scripts/literature_pipeline.py \\
  --vault "{vault_path}" selection-sync

# 生成/更新正式笔记
python {paths['pipeline_path']}/worker/scripts/literature_pipeline.py \\
  --vault "{vault_path}" index-refresh

# 运行 OCR（处理 do_ocr=true 的文献）
python {paths['pipeline_path']}/worker/scripts/literature_pipeline.py \\
  --vault "{vault_path}" ocr

# 查看精读队列
python {paths['pipeline_path']}/worker/scripts/literature_pipeline.py \\
  --vault "{vault_path}" deep-reading

# 查看整体状态
python {paths['pipeline_path']}/worker/scripts/literature_pipeline.py \\
  --vault "{vault_path}" status
```

### Agent 命令
```
/LD-deep <zotero_key>    # 完整三阶段精读
/LD-paper <zotero_key>   # 快速摘要
```

---

## 9. 常见问题

### Q: 运行 selection-sync 后没有生成 library-records？
- 检查 Better BibTeX JSON 导出路径是否正确：`{paths['pipeline_path']}/exports/library.json`
- 检查 JSON 文件是否包含文献数据
- 确认 Zotero 中该文献有 citation key

### Q: OCR 一直显示 pending？
- 检查 PaddleOCR API Key 是否配置正确（`.env` 文件）
- 检查网络连接
- 查看 `{paths['pipeline_path']}/ocr/<key>/meta.json` 中的错误信息

### Q: /LD-deep 提示 OCR 未完成？
- 确认 library-record 中 `ocr_status: done`
- 如 OCR 失败，可重新设置 `do_ocr: true` 再运行 ocr worker

### Q: Base 视图中 pdf_path 显示为绝对路径？
- 这是 Obsidian 渲染问题，数据本身是相对路径
- 不影响功能，可忽略

### Q: 可以批量操作吗？
- 可以。使用 Obsidian Base 视图批量修改 `do_ocr` 和 `analyze` 字段
- 或使用脚本批量修改 library-records 中的 frontmatter

---

## 10. 升级与维护

### 更新 PaperForge 代码
```bash
cd {vault_path}
# 如果你有 git 跟踪 PaperForge
git pull origin main

# 或手动复制更新文件
cp -r 新下载的scripts/* {paths['pipeline_path']}/worker/scripts/
```

### 备份注意事项
- `{paths['resources_dir']}/` 和 `{paths['pipeline_path']}/ocr/` 包含你的数据，需备份
- `.env` 包含 API Key，不要提交到 git
- `{paths['pipeline_path']}/exports/` 可重新生成（由 Zotero 自动导出）

---

## 配置摘要

| 配置项 | 值 |
|--------|-----|
| Vault 路径 | `{vault_path}` |
| System 目录 | `{paths['system_dir']}` |
| Pipeline 路径 | `{paths['pipeline_path']}` |
| 文献目录 | `{paths['literature_path']}` |
| Agent 平台 | {agent_config['name']} ({config['agent']}) |
| Skill 目录 | `{agent_config['skill_dir']}` |
| Zotero 路径 | {config['zotero_path']} |

---

*PaperForge Lite | 本文件由 setup.py 根据你的自定义配置自动生成*  
*生成时间：{platform.system()} | 请勿手动编辑路径，重装时会被覆盖*
"""
    
    agents_path.write_text(content, encoding="utf-8")
    print_success(f"AGENTS.md created at {agents_path} ({len(content)} chars, fully customized)")


def safe_copy(src: Path, dst: Path, backup: bool = True) -> bool:
    """Safely copy file, never overwrite without consent.
    
    Returns True if copied, False if skipped.
    """
    if dst.exists():
        if backup:
            backup_path = dst.with_suffix(dst.suffix + ".backup")
            shutil.copy2(dst, backup_path)
            print(f"{Colors.YELLOW}[BACKUP]{Colors.ENDC} Existing file saved to {backup_path.name}")
        
        print(f"{Colors.YELLOW}[SKIP]{Colors.ENDC} File exists: {dst}")
        print(f"    To update, manually delete or rename the existing file.")
        return False
    
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def deploy_workflow_scripts(vault_path: Path, agent_key: str, agent_config: dict, paths: dict) -> bool:
    """Deploy workflow scripts from repo to vault.
    
    This copies the core pipeline code from the repository into the user's vault,
    ensuring the latest scripts are available while keeping private data (.env, API keys) separate.
    """
    print_header("Step 4.5: Deploying Workflow Scripts")
    
    # Determine repo root (where this script is located)
    repo_root = Path(__file__).resolve().parent.parent
    
    # Get agent-specific skill directory
    skill_dir = agent_config.get("skill_dir", ".opencode/skills")
    
    # Files to deploy: (source_relative_path, dest_relative_path)
    deployments = [
        # OCR pipeline worker
        (f"pipeline/worker/scripts/literature_pipeline.py",
         f"{paths['pipeline_path']}/worker/scripts/literature_pipeline.py"),
        
        # Deep reading scripts (into agent-specific skill dir)
        (f"skills/literature-qa/scripts/ld_deep.py",
         f"{skill_dir}/literature-qa/scripts/ld_deep.py"),
        
        # Subagent prompt (into agent-specific skill dir)
        (f"skills/literature-qa/prompt_deep_subagent.md",
         f"{skill_dir}/literature-qa/prompt_deep_subagent.md"),
    ]
    
    success_count = 0
    fail_count = 0
    
    for src_rel, dst_rel in deployments:
        src_path = repo_root / src_rel
        dst_path = vault_path / dst_rel
        
        if not src_path.exists():
            print_warning(f"Source file not found (skipping): {src_rel}")
            fail_count += 1
            continue
        
        try:
            if safe_copy(src_path, dst_path):
                print_success(f"Deployed: {dst_rel}")
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print_error(f"Failed to deploy {src_rel}: {e}")
            fail_count += 1
    
    # Deploy chart reading guides (into literature-qa skill as references)
    chart_guide_src = repo_root / "skills/literature-qa/chart-reading"
    chart_guide_dst = vault_path / skill_dir / "literature-qa/chart-reading"
    
    if chart_guide_src.exists() and chart_guide_src.is_dir():
        chart_files = list(chart_guide_src.glob("*.md"))
        if chart_files:
            chart_guide_dst.mkdir(parents=True, exist_ok=True)
            for chart_file in chart_files:
                try:
                    dst_file = chart_guide_dst / chart_file.name
                    if safe_copy(chart_file, dst_file):
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    print_error(f"Failed to deploy chart guide {chart_file.name}: {e}")
                    fail_count += 1
            print_success(f"Deployed {len(chart_files)} chart reading guides")
    
    # Deploy agent commands
    command_src = repo_root / "command"
    command_dst = vault_path / ".opencode/command"
    
    if command_src.exists() and command_src.is_dir():
        command_files = list(command_src.glob("*.md"))
        if command_files:
            command_dst.mkdir(parents=True, exist_ok=True)
            for cmd_file in command_files:
                try:
                    dst_file = command_dst / cmd_file.name
                    if safe_copy(cmd_file, dst_file):
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    print_error(f"Failed to deploy command {cmd_file.name}: {e}")
                    fail_count += 1
            print_success(f"Deployed {len(command_files)} agent commands")
    
    print(f"\nDeployment summary: {success_count} succeeded, {fail_count} failed")
    return fail_count == 0


def validate_setup(vault_path: Path, config: dict, paths: dict) -> list[str]:
    """Validate the setup and return issues."""
    issues = []
    
    # Check Zotero SQLite
    zotero_db = Path(config['zotero_path']) / "zotero.sqlite"
    if not zotero_db.exists():
        issues.append(f"Zotero database not found: {zotero_db}")
    else:
        print_success("Zotero database accessible")
    
    # Check directory structure
    required_dirs = [
        f"{paths['pipeline_path']}/ocr",
        f"{paths['pipeline_path']}/worker/scripts",
        f"{paths['pipeline_path']}/indexes",
        f"03_Resources/LiteratureControl/library-records",
    ]
    for d in required_dirs:
        if not (vault_path / d).exists():
            issues.append(f"Missing directory: {d}")
    
    if not issues:
        print_success("Directory structure correct")
    
    # Check AGENTS.md
    if not (vault_path / "AGENTS.md").exists():
        issues.append("AGENTS.md missing")
    else:
        print_success("AGENTS.md exists")
    
    # Check .env
    if not (vault_path / ".env").exists():
        issues.append(".env configuration missing")
    else:
        print_success("Configuration file exists")
    
    return issues


def main() -> int:
    """Main installer entry point."""
    # Show welcome screen
    try:
        from welcome import show_welcome, show_install_menu
        show_welcome()
        show_install_menu()
    except ImportError:
        print_header("Literature Workflow Installer")
    
    print("This script will help you configure the literature research pipeline.")
    print(f"\n{Colors.BRIGHT_YELLOW}{Colors.BOLD}[SAFETY NOTICE]{Colors.ENDC}")
    print(f"  - This installer will NOT modify your Zotero database or existing notes")
    print(f"  - Existing files will be backed up (.backup) before any change")
    print(f"  - You can safely re-run this script; it will skip existing files\n")
    
    # Step 0: Select agent platform
    agent_key, agent_config = select_agent()
    print_success(f"Selected agent: {agent_config['name']}")
    
    # Step 0.5: Configure vault paths
    print_header("Step 0.5: Vault Configuration")
    vault_path_str = ask(
        "Where is your Obsidian vault located?",
        default=str(Path.cwd()),
    )
    vault_path = Path(vault_path_str).resolve()
    
    if not vault_path.exists():
        print_error(f"Vault path does not exist: {vault_path}")
        return 1
    
    print_success(f"Using vault: {vault_path}")
    
    # Configure directory structure
    paths = configure_vault_paths(vault_path)
    print_success("Directory structure configured")
    
    # Step 1: Check Python deps
    print_header("Step 1: Checking Python Dependencies")
    missing_deps = check_python_deps()
    if missing_deps:
        print_warning(f"Missing packages: {', '.join(missing_deps)}")
        if ask_yes_no("Install now?", default=True):
            if not install_deps(missing_deps):
                return 1
        else:
            print_error("Required packages must be installed to continue")
            return 1
    else:
        print_success("All dependencies installed")
    
    # Step 2: Detect/Ask for Zotero path
    print_header("Step 2: Zotero Configuration")
    detected_zotero = detect_zotero_path()
    
    if detected_zotero:
        print_success(f"Detected Zotero at: {detected_zotero}")
        if ask_yes_no("Use this path?", default=True):
            zotero_path = detected_zotero
        else:
            zotero_path = Path(ask("Enter Zotero data directory:"))
    else:
        print_warning("Could not auto-detect Zotero")
        zotero_path = Path(ask("Enter Zotero data directory (contains zotero.sqlite):"))
    
    if not (zotero_path / "zotero.sqlite").exists():
        print_error(f"zotero.sqlite not found in {zotero_path}")
        print("Please ensure Zotero is installed and the path is correct.")
        return 1
    
    # Step 3: Storage path
    storage_path = zotero_path
    if ask_yes_no("Is your Zotero storage directory in a different location?", default=False):
        storage_path = Path(ask("Enter Zotero storage directory:"))
    
    # Step 4: OCR API Key
    print_header("Step 3: OCR Configuration")
    ocr_api_key = ask("Enter your PaddleOCR API key:")
    if not ocr_api_key:
        print_warning("No API key provided. OCR features will not work.")
    
    # Step 5: Create directories
    print_header("Step 4: Creating Directory Structure")
    create_directory_structure(vault_path, paths)
    
    # Step 6: Deploy workflow scripts
    deploy_workflow_scripts(vault_path, agent_key, agent_config, paths)
    
    # Step 7: Create junction or config
    print_header("Step 5: Configuring Zotero Integration")
    zotero_link = vault_path / paths["system_dir"] / "Zotero"
    
    if zotero_link.exists() or zotero_link.is_symlink():
        print_warning("Zotero link already exists")
    else:
        if create_junction(zotero_link, zotero_path):
            print_success("Zotero junction created")
        else:
            print_warning("Failed to create junction, will use config file instead")
    
    # Step 8: Save configuration
    print_header("Step 6: Saving Configuration")
    config = {
        "zotero_path": str(zotero_path),
        "storage_path": str(storage_path),
        "ocr_api_key": ocr_api_key,
        "agent": agent_key,
        "agent_name": agent_config["name"],
        "skill_dir": agent_config["skill_dir"],
    }
    create_env_file(vault_path, config, paths)
    create_agents_md(vault_path, config, paths, agent_config)
    
    # Step 9: Validation
    print_header("Step 7: Validating Setup")
    issues = validate_setup(vault_path, config, paths)
    
    if issues:
        print_error("\nValidation failed with the following issues:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    
    print_header("Installation Complete!")
    print(f"""
{Colors.OKGREEN}Your literature workflow is ready to use!{Colors.ENDC}

Configuration Summary:
- Agent: {agent_config['name']}
- Skill Directory: {agent_config['skill_dir']}
- System Folder: {paths['system_dir']}
- Literature Path: {paths['literature_path']}

Next steps:
1. Open Obsidian and ensure your vault is loaded
2. Index your library: Run the index-refresh worker
3. Queue papers for analysis in the Base system
4. Run OCR on queued papers
5. Start deep reading with /LD-deep <zotero_key>

For detailed usage, see the documentation in docs/.
""")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
