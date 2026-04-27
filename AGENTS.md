# PaperForge Lite - Agent Guide

> 本文档面向 **安装完成后的新用户** 和 **AI Agent**。安装步骤见 [INSTALLATION.md](docs/INSTALLATION.md)。

---

## 0. 安装后检查清单（第一次使用前必做）

```
[ ] Zotero 已安装 + Better BibTeX 插件已启用
[ ] Better BibTeX 已配置自动导出 JSON（见下方配置）
[ ] Obsidian 已打开当前 Vault
[ ] Python 依赖已安装 (pip install requests pymupdf pillow)
[ ] PaddleOCR API Key 已配置（在 .env 中）
[ ] 目录结构已创建（setup.py 会自动完成）
[ ] Zotero 数据目录已链接到 <system_dir>/Zotero
```

### Better BibTeX 自动导出配置

1. Zotero → Edit → Preferences → Better BibTeX
2. 勾选 **"Keep updated"**（自动导出）
3. 选择导出格式：**Better BibLaTeX** 或 **Better BibTeX**
4. 导出路径设置为：`{你的Vault路径}/<system_dir>/PaperForge/exports/library.json`
5. 点击 OK，JSON 文件会自动生成并保持同步

---

## 1. 核心架构（Lite 版）

PaperForge Lite 采用 **两层设计**：

| 层级 | 组件 | 触发方式 | 作用 |
|------|------|----------|------|
| **Worker 层** | `literature_pipeline.py`（4 个 workers） | Python CLI | 后台自动化 |
| **Agent 层** | `/pf-deep`, `/pf-paper` 命令 | 用户手动触发 | 交互式精读 |

**关键区别**：
- **Worker 只做机械劳动**（检测新文献、生成笔记、OCR）
- **Agent 只做深度思考**（精读、分析、写作）
- Worker 不会自动触发 Agent，Agent 不会自动触发 Worker

**操作速查**：
| 你要做什么 | 在终端输入 | 在 OpenCode 输入 |
|-----------|-----------|-----------------|
| 同步 Zotero 并生成笔记 | `paperforge sync` | `/pf-sync` |
| 运行 OCR | `paperforge ocr` | `/pf-ocr` |
| 查看精读队列 | `paperforge deep-reading` | `/pf-deep`（精读具体文献） |
| 查看系统状态 | `paperforge status` | `/pf-status` |
| 修复状态分歧 | `paperforge repair` | （终端操作） |
| 验证安装配置 | `paperforge doctor` | （终端操作） |
| 查看帮助 | `paperforge --help` | （终端操作） |

---

## 2. 完整数据流

```
Zotero 添加文献
    ↓ Better BibTeX 自动导出 JSON
<system_dir>/PaperForge/exports/library.json
    ↓ 运行 sync（selection-sync 阶段）
<resources_dir>/<control_dir>/library-records/<domain>/<key>.md
    ↓ 运行 sync（index-refresh 阶段）
<resources_dir>/<literature_dir>/<domain>/<key> - <Title>.md（正式笔记）
    ↓ 用户在 library-record 中设置 do_ocr: true
运行 ocr → <system_dir>/PaperForge/ocr/<key>/
    ↓ 用户在 library-record 中设置 analyze: true
运行 deep-reading（查看队列，确认就绪）
    ↓ 用户执行 Agent 命令
/pf-deep <zotero_key>
    ↓ Agent 生成
正式笔记中新增 ## 🔍 精读 区域
```

---

## 3. 目录结构（Lite 版，5 个核心目录）

```
{你的Vault根目录}/
├── <resources_dir>/
│   ├── <literature_dir>/                    ← 正式文献笔记（index-refresh 生成）
│   │   ├── 骨科/
│   │   ├── 运动医学/
│   │   └── ...（你的分类）
│   └── <control_dir>/             ← 状态跟踪
│       └── library-records/           ← selection-sync 输出
│           ├── 骨科/
│           │   └── ABCDEFG.md         ← 单条文献状态记录
│           └── 运动医学/
│               └── HIJKLMN.md
│
├── <system_dir>/
│   ├── PaperForge/
│   │   ├── exports/                   ← Better BibTeX 自动导出的 JSON
│   │   │   └── library.json
│   │   ├── ocr/                       ← OCR 结果（每个文献一个子目录）
│   │   │   └── ABCDEFG/               ← Zotero key 作为目录名
│   │   │       ├── fulltext.md        ← OCR 提取的全文
│   │   │       ├── images/            ← 图表切割图片
│   │   │       ├── meta.json          ← OCR 元数据（含 ocr_status）
│   │   │       └── figure-map.json    ← 图表索引（自动创建）
│   │   └── worker/scripts/
│   │       └── literature_pipeline.py ← 核心脚本
│   └── Zotero/                        ← Junction/Symlink 到 Zotero 数据目录
│
├── <agent_config_dir>/                         ← OpenCode Agent 配置（自动创建）
│   └── skills/
│       └── literature-qa/             ← 深度阅读 Skill
│           ├── scripts/
│           │   └── ld_deep.py         ← /pf-deep 核心脚本
│           ├── prompt_deep_subagent.md ← Agent 精读提示词
│           └── chart-reading/         ← 14 种图表阅读指南
│
├── .env                               ← API Key 等敏感配置
└── AGENTS.md                          ← 本文件
```

### 各目录作用速查

| 目录 | 内容 | 谁生成/修改 |
|------|------|------------|
| `<resources_dir>/<literature_dir>/` | 正式文献笔记（含 frontmatter + 精读内容） | sync（index-refresh 阶段）生成，Agent 写入精读 |
| `<resources_dir>/<control_dir>/library-records/` | 文献状态跟踪（analyze, ocr_status 等） | sync（selection-sync 阶段）生成，用户修改状态 |
| `<system_dir>/PaperForge/exports/` | Better BibTeX JSON 导出 | Zotero 自动导出 |
| `<system_dir>/PaperForge/ocr/` | OCR 全文 + 图表切割 | ocr worker 生成 |
| `<system_dir>/Zotero/` | Zotero 数据目录的链接 | 安装时手动创建 junction |

---

## 4. 核心 Workers（Lite 版，4 个）

### sync
- **作用**：检测 Zotero 中的新条目并生成正式文献笔记（selection-sync + index-refresh 的统一入口）
- **运行时机**：添加新文献到 Zotero 后，或需要更新笔记格式时
- **输出**：
  - `<resources_dir>/<control_dir>/library-records/<domain>/<key>.md`
  - `<resources_dir>/<literature_dir>/<domain>/<key> - <Title>.md`
- **示例**：
  ```bash
  paperforge sync
  # 仅同步 Zotero 到 library-records
  paperforge sync --selection
  # 仅根据现有 library-records 生成正式笔记
  paperforge sync --index
  # Legacy (备用):
  # python <system_dir>/PaperForge/worker/scripts/literature_pipeline.py \
  #   --vault "{vault路径}" selection-sync
  # python <system_dir>/PaperForge/worker/scripts/literature_pipeline.py \
  #   --vault "{vault路径}" index-refresh
  ```

### ocr
- **作用**：将 PDF 上传到 PaddleOCR API，提取全文文本和图表
- **触发条件**：library-record 中 `do_ocr: true`
- **输出**：`<system_dir>/PaperForge/ocr/<key>/` 目录
  - `fulltext.md`：提取的全文（含 `<!-- page N -->` 分页标记）
  - `images/`：自动切割的图表图片
  - `meta.json`：OCR 状态（`ocr_status: done/pending/processing/failed`）
  - `figure-map.json`：图表索引（后续自动生成）
- **注意**：OCR 是异步的，大文件可能需要几分钟
- **示例**：
  ```bash
  paperforge ocr
  # 诊断模式（不运行，仅检查状态）
  paperforge ocr --diagnose
  # Legacy (备用):
  # python <system_dir>/PaperForge/worker/scripts/literature_pipeline.py \
  #   --vault "{vault路径}" ocr
  ```

### deep-reading
- **作用**：扫描所有 library-records，列出 `analyze=true` 且 OCR 完成的文献
- **运行时机**：用户想看看哪些文献可以开始精读了
- **输出**：控制台表格，显示队列状态
- **重要**：这只是**查看队列**，不会自动触发 Agent 精读
- **示例**：
  ```bash
  paperforge deep-reading
  paperforge deep-reading --verbose  # 显示阻塞条目的修复指令
  # Legacy (备用):
  # python <system_dir>/PaperForge/worker/scripts/literature_pipeline.py \
  #   --vault "{vault路径}" deep-reading
  ```

---

## 5. Agent 命令（用户手动触发）

PaperForge 的命令分为两类：

| 类型 | 命令 | 用途 | 说明 |
|------|------|------|------|
| **深度思考** | `/pf-deep <key>` | 完整 Keshav 三阶段精读 | **必须 Agent 执行** — 需要理解论文、分析图表、生成 callout |
| **深度思考** | `/pf-paper <key>` | 快速摘要 | **必须 Agent 执行** — 需要理解内容并写作 |
| **机械操作** | `/pf-sync` | 同步 Zotero 并生成笔记 | Agent 可帮你检查状态并执行 |
| **机械操作** | `/pf-ocr` | 运行 PDF OCR | Agent 可帮你检查队列并执行 |
| **机械操作** | `/pf-status` | 查看系统状态 | Agent 可帮你解读诊断结果 |

> **双模式调用**：`/pf-sync`、`/pf-ocr`、`/pf-status` 本质上是 CLI 命令的 Agent 包装。你可以在终端直接运行 `paperforge sync/ocr/status`，也可以在 OpenCode 中使用 `/pf-*` 让 Agent 帮你检查前置条件、执行命令、解读输出。

> **v1.4 新增**：所有命令支持全局 `--verbose` / `-v` 参数（如 `paperforge sync --verbose`），输出 DEBUG 级别的诊断信息到 stderr，不影响 stdout 的正常输出。

> **v1.4 新增 — auto_analyze_after_ocr**：如果开启了 `paperforge.json` 中的 `auto_analyze_after_ocr`，OCR 完成后 `analyze` 会自动设为 `true`，无需手动修改 library-record。

### 必须 Agent 执行的命令

#### `/pf-deep <zotero_key>` — 完整精读

**用途**：完整 Keshav 三阶段精读
**前置条件**：OCR 完成 (`ocr_status: done`)

执行流程：
1. **prepare 阶段**（自动）：查找 library-record、检查 OCR、生成 figure-map
2. **精读阶段**（Agent 执行）：Pass 1 概览 → Pass 2 精读还原 → Pass 3 深度理解
3. **验证阶段**（自动）：检查 callout 间距、section 完整性

#### `/pf-paper <zotero_key>` — 快速摘要

**用途**：快速摘要（无 OCR 要求）
**前置条件**：有正式笔记即可

---

## 6. Path Resolution（路径解析）

PaperForge 支持三种 Better BibTeX 导出路径格式，并统一转换为 Obsidian wikilink：

### 支持的 BBT 路径格式

| 格式 | 示例 | 处理方式 |
|------|------|----------|
| **Absolute Windows** | `D:\Zotero\storage\KEY\file.pdf` | 提取 8 位 KEY，转换为 `storage:KEY/file.pdf` |
| **storage: prefix** | `storage:KEY/file.pdf` | 直接透传，仅规范化斜杠 |
| **Bare relative** | `KEY/file.pdf` | 自动添加 `storage:` 前缀 |

### Wikilink 生成规则

- 所有 PDF 路径在 library-record 中存储为 **Obsidian wikilink** 格式：`[[relative/path/to/file.pdf]]`
- 使用正斜杠 `/`（即使 Windows 系统）
- 支持中文文件名，无需转义
- 示例：`[[99_System/Zotero/storage/KEY/中文论文.pdf]]`

### Junction / Symlink 设置

如果 Zotero 数据目录在 Vault 外部，需创建 junction：

```powershell
# 以管理员身份运行 PowerShell
New-Item -ItemType Junction -Path "C:\你的Vault\99_System\Zotero" -Target "C:\Users\用户名\Zotero"
```

或 CMD：

```cmd
mklink /J "C:\你的Vault\99_System\Zotero" "C:\Users\用户名\Zotero"
```

运行 `paperforge doctor` 会自动检测 Zotero 位置并推荐正确的 junction 命令。

### 多附件处理

当一篇文献有多个 PDF 附件时：
- **Main PDF**：title="PDF" 的附件，或最大文件，或第一个 PDF
- **Supplementary**：其他 PDF 附件列表，以 wikilink 数组形式存储

---

## 7. Frontmatter 字段参考

### Library Record（`library-records/<domain>/<key>.md`）

这是**用户控制工作流的核心**。每个文献对应一个 record 文件：

```yaml
---
zotero_key: "ABCDEFG"           # Zotero citation key（自动生成）
domain: "骨科"                   # 分类领域（对应 Zotero 收藏夹）
title: "论文标题"
year: 2024
doi: "10.xxxx/xxxxx"
collection_path: "子分类"        # Zotero 子收藏夹路径
has_pdf: true                    # 是否有 PDF 附件（自动生成）
pdf_path: "[[99_System/Zotero/storage/KEY/文件名.pdf]]"  # Wikilink 格式
bbt_path_raw: "D:\\Zotero\\storage\\KEY\\文件名.pdf"     # 原始 BBT 路径（调试用）
zotero_storage_key: "KEY"        # 8 位 Zotero storage key
attachment_count: 2              # 附件总数
supplementary:                   # 其他 PDF 附件（wikilink 列表）
  - "[[99_System/Zotero/storage/KEY/supp1.pdf]]"
  - "[[99_System/Zotero/storage/KEY/supp2.pdf]]"
fulltext_md_path: "[[99_System/PaperForge/ocr/KEY/fulltext.md]]"
recommend_analyze: true          # 系统推荐精读（有 PDF 时自动设为 true）
analyze: false                   # 【用户控制】是否生成精读？设为 true 触发
do_ocr: true                     # 【用户控制】是否运行 OCR？设为 true 触发
ocr_status: "done"               # OCR 状态（pending/processing/done/failed）
deep_reading_status: "pending"   # 精读状态（pending/done）
path_error: ""                   # 路径错误（not_found/invalid/permission_denied）
analysis_note: ""                # 预留字段
---
```

**用户操作方式**：
- 在 Obsidian 中打开 library-record 文件
- 修改 `analyze: false` → `analyze: true` 标记要精读的文献
- 修改 `do_ocr: false` → `do_ocr: true` 触发 OCR
- 或使用 Obsidian Base 视图批量操作

### Formal Note（`Literature/<domain>/<key> - <Title>.md`）

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
pdf_link: "[[99_System/Zotero/storage/KEY/文件名.pdf]]"
---
```

---

## 7. 第一次使用指南（手把手）

### Step 1: 确认 Zotero 有文献

确保 Zotero 中已有至少一篇带 PDF 的文献，且 Better BibTeX 已导出 JSON。

### Step 2: 运行 sync

```bash
# 在 Vault 根目录执行
paperforge sync
```

预期输出：
```
[INFO] Found 5 new items
[INFO] Created library-records/骨科/XXXXXXX.md
[INFO] Generated 5 formal notes
[INFO] Output: <resources_dir>/<literature_dir>/骨科/XXXXXXX - Title.md
...
```

> 如需分阶段执行：
> - `paperforge sync --selection` — 仅同步 Zotero 到 library-records
> - `paperforge sync --index` — 仅根据现有 library-records 生成正式笔记

### Step 3: 标记要精读的文献

在 Obsidian 中：
1. 打开 `<resources_dir>/<control_dir>/library-records/骨科/XXXXXXX.md`
2. 将 `do_ocr: false` 改为 `do_ocr: true`
3. 将 `analyze: false` 改为 `analyze: true`
4. 保存文件

### Step 4: 运行 OCR

```bash
paperforge ocr
```

等待完成（可能需要几分钟）。

### Step 5: 检查 OCR 状态

```bash
paperforge deep-reading
```

预期输出：
```
## 就绪 (1 篇) — OCR 完成
- `XXXXXXX` | 骨科 | 论文标题
```

### Step 6: 执行精读

在 OpenCode Agent 中输入：
```
/pf-deep XXXXXXX
```

Agent 会自动：
1. 准备精读骨架（prepare）
2. 逐阶段填写精读内容
3. 验证结构完整性

### Step 7: 查看结果

在 Obsidian 中打开正式笔记，找到 `## 🔍 精读` 区域，精读已完成。

---

## 8. 常用命令速查

```bash
# 检测 Zotero 新条目并生成正式笔记
paperforge sync
paperforge sync --verbose      # 显示详细诊断信息

# 仅同步 Zotero 到 library-records
paperforge sync --selection
paperforge sync --selection --verbose

# 仅根据现有 library-records 生成正式笔记
paperforge sync --index
paperforge sync --index --verbose

# 运行 OCR（处理 do_ocr=true 的文献）
paperforge ocr
paperforge ocr --verbose       # 显示 OCR 详细日志
paperforge ocr --diagnose      # 诊断模式，不实际运行
paperforge ocr --no-progress   # 静默模式，不显示进度条

# 查看精读队列
paperforge deep-reading
paperforge deep-reading --verbose  # 显示阻塞条目修复指令

# 修复状态分歧（默认 dry-run）
paperforge repair --verbose        # 查看三向状态分歧详情
paperforge repair --fix           # 实际修复（慎用）

# 查看整体状态
paperforge status

# 验证安装配置
paperforge doctor
```

> 如果 `paperforge` 命令未注册，可使用 fallback：
> ```bash
> python -m paperforge <command>
> ```
> 例如：`python -m paperforge status`

### Agent 命令
```
/pf-deep <zotero_key>    # 完整三阶段精读（必须 Agent 执行）
/pf-paper <zotero_key>   # 快速摘要（必须 Agent 执行）
/pf-sync                 # 同步 Zotero（Agent 包装 CLI）
/pf-ocr                  # 运行 OCR（Agent 包装 CLI）
/pf-status               # 查看状态（Agent 包装 CLI）
```

> 注：`/pf-sync`、`/pf-ocr`、`/pf-status` 与 `paperforge sync/ocr/status` 是同一命令的两种调用方式。在终端直接运行 CLI 即可；在 OpenCode 中使用 `/pf-*` 可以让 Agent 帮你检查前置条件并解读输出。

### Chart-Reading 指南索引

`/pf-deep` 精读时会参考 19 种图表类型的阅读指南，按生物医学文献常见度排序。完整索引参见 `chart-reading/INDEX.md`。

---

## 9. 常见问题

### Q: 运行 sync 后没有生成 library-records？
- 检查 Better BibTeX JSON 导出路径是否正确
- 检查 JSON 文件是否包含文献数据
- 确认 Zotero 中该文献有 citation key

### Q: OCR 一直显示 pending？
- 检查 PaddleOCR API Key 是否配置正确（`.env` 文件）
- 检查网络连接
- 查看 `<system_dir>/PaperForge/ocr/<key>/meta.json` 中的错误信息

### Q: /pf-deep 提示 OCR 未完成？
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

#### 方式 1：自动更新（推荐）

```bash
# 自动检测安装方式并更新
paperforge update
```

系统会自动检测你是通过 pip、git 还是手动安装，并执行对应的更新方式。

#### 方式 2：Windows 一键脚本

双击运行 Vault 根目录下的 `scripts/update-paperforge.ps1`：
- 自动检测安装方式
- 自动执行更新
- 无需手动输入命令

```powershell
# 或在 PowerShell 中执行
.\scripts\update-paperforge.ps1

# 强制更新（跳过确认）
.\scripts\update-paperforge.ps1 -Force

# 只检测不更新
.\scripts\update-paperforge.ps1 -DryRun
```

#### 方式 3：手动更新

**pip 安装用户：**
```bash
pip install --upgrade paperforge
```

**pip editable 安装用户：**
```bash
cd 你的Vault路径
git pull origin master
pip install -e .
```

**git clone 用户：**
```bash
cd 你的Vault路径
git pull origin master
```

#### 方式 4：手动复制（最后手段）

```bash
cp -r 新下载的代码/* <vault_path>/
```

> [!WARNING] 手动复制容易遗漏文件，建议优先使用自动更新。

### 备份注意事项
- `<resources_dir>/` 和 `<system_dir>/PaperForge/ocr/` 包含你的数据，需备份
- `.env` 包含 API Key，不要提交到 git
- `<system_dir>/PaperForge/exports/` 可重新生成（由 Zotero 自动导出）

---

## 11. 命令迁移说明（v1.1 → v1.2）

从 v1.2 开始，PaperForge 采用统一的命令接口：

- **CLI 统一入口**：`paperforge sync`（替代 `selection-sync` + `index-refresh`）、`paperforge ocr`（替代 `ocr run`）
- **Agent 统一前缀**：`/pf-deep`、`/pf-paper`、`/pf-ocr`、`/pf-sync`、`/pf-status`（替代 `/LD-*` 和 `/lp-*`）
- **Python 包重命名**：`paperforge`（替代 `paperforge_lite`）

**旧命令仍兼容**：v1.2 继续支持旧命令名（`selection-sync`、`index-refresh`、`ocr run`），但文档已统一使用新命令。

> **v1.4 新增**：结构化日志（`--verbose`）、自动重试、进度条、代码自动化检查。详细迁移步骤和回滚说明参见 [docs/MIGRATION-v1.2.md](docs/MIGRATION-v1.2.md)（v1.1→v1.2）和 [docs/MIGRATION-v1.4.md](docs/MIGRATION-v1.4.md)（v1.3→v1.4）。

---

*PaperForge Lite | 快速开始指南 | 安装后阅读*
