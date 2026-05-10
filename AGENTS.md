# PaperForge - Agent Guide

> 本文档面向 **安装完成后的新用户** 和 **AI Agent**。如果还没有安装 PaperForge，请通过 Obsidian 插件市场安装，或查看 [README.md](README.md) 中的安装说明。Docs 版本与 v1.4.18 对应。

---

## 0. 安装后检查清单（第一次使用前必做）

```
[ ] Zotero 已安装 + Better BibTeX 插件已启用
[ ] Obsidian 已打开当前 Vault
[ ] PaperForge 已安装 (pip install git+https://github.com/LLLin000/PaperForge.git)
[ ] PaddleOCR API Key 已配置（在 .env 中）
[ ] 目录结构已创建（安装向导会自动完成）
[ ] Zotero 数据目录已链接到 <system_dir>/Zotero
[ ] Better BibTeX 已按下方步骤导出 JSON 到 <system_dir>/PaperForge/exports/
```

> 安装向导是增量式的：如果你选择的 Vault 或目录里已经有文件，PaperForge 只会补充缺失的目录和文件，不会删除已有内容。

### Better BibTeX 自动导出配置

这一步应在安装向导完成之后再做，因为 `exports/` 目录需要先由安装流程创建。

1. 打开 Zotero
2. 对你要同步的文献库或分类右键 → `导出...`
3. 选择格式：**Better BibTeX JSON**
4. 勾选 **"Keep updated"**（自动导出）
5. 保存到：`{你的Vault路径}/<system_dir>/PaperForge/exports/`
6. JSON 文件名会作为 Base 名称，例如 `library.json`、`骨科.json`

---

## 1. 核心架构（v2.1 契约驱动）

PaperForge 在 v2.1（1.4.17rc4）重构为 **契约驱动架构**，分 5 层：

```
CLI/Plugin 调用
    ↓ PFResult 契约 {ok, command, version, data, error}
┌─────────────────────────────────────────────┐
│  commands/    CLI 分发层                      │
├─────────────────────────────────────────────┤
│  adapter/bbt, zotero_paths, frontmatter    │  ← 独立可测
│  services/sync_service       ← 编排适配器   │
├─────────────────────────────────────────────┤
│  core/result, errors, state   ← 共享数据契约 │
├─────────────────────────────────────────────┤
│  worker/sync, ocr, status     ← 机械劳动     │
│  setup/6个类                  ← 安装流程     │
├─────────────────────────────────────────────┤
│  schema/field_registry.yaml   ← 字段注册表   │
│  doctor/field_validator.py    ← 字段校验     │
└─────────────────────────────────────────────┘
```

| 层级 | 组件 | 触发方式 | 作用 |
|------|------|----------|------|
| **契约层** | `core/`（PFResult, ErrorCode, 状态机） | 被所有模块引用 | 定义 CLI/Plugin/Worker 之间的数据交换格式 |
| **适配器层** | `adapters/`（bbt, zotero_paths, frontmatter） | 被服务层调用 | 封装外部数据格式与 I/O 操作 |
| **服务层** | `services/sync_service` | 被 worker 调度 | 编排适配器，实现业务逻辑 |
| **Worker 层** | `worker/`（sync, ocr, status, repair 等） | Python CLI | 后台自动化（机械劳动） |
| **Agent 层** | `/pf-deep`, `/pf-paper` | 用户手动触发 | 交互式精读（深度思考） |

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
    ↓ 运行 sync
<resources_dir>/<literature_dir>/<domain>/<key> - <Title>.md（正式笔记，含 frontmatter）
    ↓ 用户在正式笔记 frontmatter 中设置 do_ocr: true
运行 ocr → <system_dir>/PaperForge/ocr/<key>/
    ↓ 用户在正式笔记 frontmatter 中设置 analyze: true
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
│   ├── <literature_dir>/                    ← 正式文献笔记（sync 生成，含 frontmatter 状态跟踪）
│   │   ├── 骨科/
│   │   ├── 运动医学/
│   │   └── ...（你的分类）
│
├── <system_dir>/
│   ├── PaperForge/
│   │       ├── exports/                   ← Better BibTeX 自动导出的 JSON
│   │       │   └── library.json
│   │       ├── ocr/                       ← OCR 结果（每个文献一个子目录）
│   │       │   └── ABCDEFG/               ← Zotero key 作为目录名
│   │       │       ├── fulltext.md        ← OCR 提取的全文
│   │       │       ├── images/            ← 图表切割图片
│   │       │       ├── meta.json          ← OCR 元数据（含 ocr_status）
│   │       │       └── figure-map.json    ← 图表索引（自动创建）
│   │       ├── indexes/                   ← 索引缓存（formal-library.json 等）
│   │       └── config/                    ← 领域-收藏夹映射等配置
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
| `<resources_dir>/<literature_dir>/` | 正式文献笔记（含 frontmatter + 精读内容） | sync 生成，Agent 写入精读 |
| `<system_dir>/PaperForge/exports/` | Better BibTeX JSON 导出 | Zotero 自动导出 |
| `<system_dir>/PaperForge/ocr/` | OCR 全文 + 图表切割 | ocr worker 生成 |
| `<system_dir>/PaperForge/indexes/` | 索引缓存（formal-library.json） | sync 生成 |
| `<system_dir>/PaperForge/config/` | 领域-收藏夹映射等 | 用户/安装向导配置 |
| `<system_dir>/Zotero/` | Zotero 数据目录的链接 | 安装时手动创建 junction |

---

## 4. 核心 Workers（Lite 版，4 个）

### sync
- **作用**：检测 Zotero 中的新条目并生成正式文献笔记
- **运行时机**：添加新文献到 Zotero 后，或需要更新笔记格式时
- **输出**：
  - `<resources_dir>/<literature_dir>/<domain>/<key> - <Title>.md`
- **示例**：
  ```bash
  paperforge sync
  # Legacy (备用):
  # python -m paperforge sync --vault "{vault路径}"
  ```

### ocr
- **作用**：将 PDF 上传到 PaddleOCR API，提取全文文本和图表
- **触发条件**：正式笔记 frontmatter 中 `do_ocr: true`
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
  # python -m paperforge ocr --vault "{vault路径}"
  ```

### deep-reading
- **作用**：扫描所有正式笔记，列出 `analyze=true` 且 OCR 完成的文献
- **运行时机**：用户想看看哪些文献可以开始精读了
- **输出**：控制台表格，显示队列状态
- **重要**：这只是**查看队列**，不会自动触发 Agent 精读
- **示例**：
  ```bash
  paperforge deep-reading
  paperforge deep-reading --verbose  # 显示阻塞条目的修复指令
  # Legacy (备用):
  # python -m paperforge deep-reading --vault "{vault路径}"
  ```

---

## 5. Agent 命令（用户手动触发）

PaperForge 的命令分为两类：

| 类型 | 命令 | 用途 | 说明 |
|------|------|------|------|
| **深度思考** | `/pf-deep <key>` | 完整 Keshav 三阶段精读 | **必须 Agent 执行** — 需要理解论文、分析图表、生成 callout |
| **深度思考** | `/pf-paper <key>` | 文献问答 | **必须 Agent 执行** — 需要理解内容并写作 |
| **机械操作** | `/pf-sync` | 同步 Zotero 并生成笔记 | Agent 可帮你检查状态并执行 |
| **机械操作** | `/pf-ocr` | 运行 PDF OCR | Agent 可帮你检查队列并执行 |
| **机械操作** | `/pf-status` | 查看系统状态 | Agent 可帮你解读诊断结果 |

> **双模式调用**：`/pf-sync`、`/pf-ocr`、`/pf-status` 本质上是 CLI 命令的 Agent 包装。你可以在终端直接运行 `paperforge sync/ocr/status`，也可以在 OpenCode 中使用 `/pf-*` 让 Agent 帮你检查前置条件、执行命令、解读输出。

> **v1.4 新增**：所有命令支持全局 `--verbose` / `-v` 参数（如 `paperforge sync --verbose`），输出 DEBUG 级别的诊断信息到 stderr，不影响 stdout 的正常输出。

> **v1.4 新增 — auto_analyze_after_ocr**：如果开启了 `paperforge.json` 中的 `auto_analyze_after_ocr`，OCR 完成后 `analyze` 会自动设为 `true`，无需手动修改 formal note frontmatter。

### 必须 Agent 执行的命令

#### `/pf-deep <zotero_key>` — 完整精读

**用途**：完整 Keshav 三阶段精读
**前置条件**：OCR 完成 (`ocr_status: done`)

执行流程：
1. **prepare 阶段**（自动）：查找正式笔记、检查 OCR、生成 figure-map
2. **精读阶段**（Agent 执行）：Pass 1 概览 → Pass 2 精读还原 → Pass 3 深度理解
3. **验证阶段**（自动）：检查 callout 间距、section 完整性

#### `/pf-paper <zotero_key>` — 文献问答

**用途**：文献问答（无 OCR 要求）
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

- 所有 PDF 路径在正式笔记中存储为 **Obsidian wikilink** 格式：`[[relative/path/to/file.pdf]]`
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

### Formal Note（`Literature/<domain>/<key> - <Title>.md`）

这是**用户控制工作流的核心**。每个文献对应一个 formal note 文件，frontmatter 包含元数据 + 工作流控制字段：

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
- 在 Obsidian 中打开 formal note 文件
- 修改 `analyze: false` → `analyze: true` 标记要精读的文献
- 修改 `do_ocr: false` → `do_ocr: true` 触发 OCR
- 或使用 Obsidian Base 视图批量操作

---

## 8. 第一次使用指南（手把手）

### Step 1: 完成 Better BibTeX 自动导出

先按上面的步骤把 JSON 导出到 `<system_dir>/PaperForge/exports/`。这一步没完成前，`sync` 不会读到文献。

### Step 2: 确认 Zotero 有文献

确保 Zotero 中已有至少一篇带 PDF 的文献，且 Better BibTeX 已导出 JSON。

### Step 3: 运行 sync

```bash
# 在 Vault 根目录执行
paperforge sync
```

预期输出：
```
[INFO] Found 5 new items
[INFO] Created 骨科/XXXXXXX.md
[INFO] Generated 5 formal notes
[INFO] Output: <resources_dir>/<literature_dir>/骨科/XXXXXXX - Title.md
...
```

### Step 4: 在 Base 视图中标记 OCR

打开 Obsidian Base 视图，找到该文献，将 `do_ocr` 设为 `true`。

### Step 5: 运行 OCR

```bash
paperforge ocr
```

等待完成（可能需要几分钟）。

### Step 6: 在 Base 视图中标记精读

OCR 完成后，在 Base 视图中找到该文献，将 `analyze` 设为 `true`。

### Step 7: 执行精读

先确认队列就绪：
```bash
paperforge deep-reading
```

然后在 OpenCode Agent 中输入：
```
/pf-deep XXXXXXX
```

Agent 会自动：
1. 准备精读骨架（prepare）
2. 逐阶段填写精读内容
3. 验证结构完整性

### Step 8: 查看结果

在 Obsidian 中打开正式笔记，找到 `## 🔍 精读` 区域，精读已完成。

---

## 9. 常用命令速查

```bash
# 检测 Zotero 新条目并生成正式笔记
paperforge sync
paperforge sync --verbose      # 显示详细诊断信息



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
/pf-paper <zotero_key>   # 文献问答（必须 Agent 执行）
/pf-sync                 # 同步 Zotero（Agent 包装 CLI）
/pf-ocr                  # 运行 OCR（Agent 包装 CLI）
/pf-status               # 查看状态（Agent 包装 CLI）
```

> 注：`/pf-sync`、`/pf-ocr`、`/pf-status` 与 `paperforge sync/ocr/status` 是同一命令的两种调用方式。在终端直接运行 CLI 即可；在 OpenCode 中使用 `/pf-*` 可以让 Agent 帮你检查前置条件并解读输出。

### Chart-Reading 指南索引

`/pf-deep` 精读时会参考 19 种图表类型的阅读指南，按生物医学文献常见度排序。完整索引参见 `chart-reading/INDEX.md`。

---

## 10. 常见问题

### Q: 运行 sync 后没有生成正式笔记？
- 检查 Better BibTeX JSON 导出路径是否正确
- 检查 JSON 文件是否包含文献数据
- 确认 Zotero 中该文献有 citation key

### Q: OCR 一直显示 pending？
- 检查 PaddleOCR API Key 是否配置正确（`.env` 文件）
- 检查网络连接
- 查看 `<system_dir>/PaperForge/ocr/<key>/meta.json` 中的错误信息

### Q: /pf-deep 提示 OCR 未完成？
- 确认正式笔记 frontmatter 中 `ocr_status: done`
- 如 OCR 失败，可重新设置 `do_ocr: true` 再运行 ocr worker

### Q: Base 视图中 pdf_path 显示为绝对路径？
- 这是 Obsidian 渲染问题，数据本身是相对路径
- 不影响功能，可忽略

### Q: 可以批量操作吗？
- 可以。使用 Obsidian Base 视图批量修改 `do_ocr` 和 `analyze` 字段
- 或使用脚本批量修改 formal note frontmatter

---

## 11. 升级与维护

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

**推荐：自动更新**
```bash
paperforge update
```
系统会自动检测安装方式并执行对应的更新命令。

**pip 安装用户：**
```bash
pip install --upgrade git+https://github.com/LLLin000/PaperForge.git
```

**pip editable / git clone 用户：**
```bash
cd 你的仓库目录
git pull origin master
pip install -e .
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

## 12. 命令迁移说明（v1.1 → v1.2）

从 v1.2 开始，PaperForge 采用统一的命令接口：

- **CLI 统一入口**：`paperforge sync`（替代 `selection-sync` + `index-refresh`）、`paperforge ocr`（替代 `ocr run`）
- **Agent 统一前缀**：`/pf-deep`、`/pf-paper`、`/pf-ocr`、`/pf-sync`、`/pf-status`（替代 `/LD-*` 和 `/lp-*`）
- **Python 包重命名**：`paperforge`（替代 `paperforge_lite`）

**旧命令仍兼容**：v1.2 继续支持旧命令名（`selection-sync`、`index-refresh`、`ocr run`），但文档已统一使用新命令。

> **v1.4 新增**：结构化日志（`--verbose`）、自动重试、进度条、代码自动化检查。详细迁移步骤和回滚说明参见 [docs/MIGRATION-v1.2.md](docs/MIGRATION-v1.2.md)（v1.1→v1.2）和 [docs/MIGRATION-v1.4.md](docs/MIGRATION-v1.4.md)（v1.3→v1.4）。

---

## 13. 开发者指南（AI Agent 必读）

### v2.1 新增模块

v2.1（1.4.17rc4）引入了以下新增模块，开发时请注意：

| 路径 | 内容 | 注意事项 |
|------|------|---------|
| `paperforge/core/` | 契约层 — PFResult, ErrorCode, 状态机 | 所有模块都可引用，不循环依赖 |
| `paperforge/adapters/` | 适配器 — bbt, zotero_paths, frontmatter | 独立可测，从 `sync.py` 提取 |
| `paperforge/services/` | 服务层 — SyncService | 编排适配器，`sync.py` 变调度壳 |
| `paperforge/setup/` | 安装层 — 6 个类 | 从 `setup_wizard.py` 拆出 |
| `paperforge/schema/` | 字段注册表 — `field_registry.yaml` | 44 字段定义 |
| `paperforge/doctor/` | 校验 — `field_validator.py` | `doctor` 命令使用 |

所有 `--json` 输出统一为 PFResult 格式 `{ok, command, version, data, error}`。修改输出结构时需同时更新 `core/result.py` 和下游 consumer（plugin）。

### 版本号管理

PaperForge 版本只在 `paperforge/__init__.py` 一处定义。升版本时不要手动改多个文件，使用自动化脚本：

```bash
# 升 patch 版本（1.4.11 → 1.4.12），自动 git commit + tag
python scripts/bump.py patch

# 升 minor 版本（1.4.11 → 1.5.0）
python scripts/bump.py minor

# 指定版本号
python scripts/bump.py 2.0.0

# 预览（不实际修改）
python scripts/bump.py patch --dry-run

# 只改文件不 commit
python scripts/bump.py patch --no-git
```

 脚本会自动更新：
| 文件 | 字段 |
|------|------|
| `paperforge/__init__.py` | `__version__` |
| `paperforge/plugin/manifest.json` | `version` |
| `manifest.json` | `version` |
| `paperforge/plugin/versions.json` | 追加 `"version": "minAppVersion"` |

### 发布 Release 流程

```bash
# 1. 升版本（自动 commit + tag）
python scripts/bump.py patch

# 2. 推送代码和 tag
git push && git push --tags

# 3. 创建 GitHub Release 并上传插件文件
gh release create v1.4.12 \
    --title "v1.4.12" \
    --notes "简短说明" \
    paperforge/plugin/main.js \
    paperforge/plugin/styles.css \
    paperforge/plugin/manifest.json \
    paperforge/plugin/versions.json
```

> Obsidian 社区插件要求 Release 附带 `main.js`、`manifest.json`、`styles.css`、`versions.json` 四个单独文件（非 zip）。

### 插件 i18n

插件界面通过 `paperforge/plugin/i18n.js` 做中英文适配：
- 语言自动检测：读取 Obsidian 语言设置，`zh*` 用中文，其他用英文
- 新增文本时，需同时在 `i18n.js` 的 `zh` 和 `en` 两块加 key
- 代码中使用 `t('key_name')` 读取翻译
- Dashboard 的 `ACTIONS` 标题保持英文（Obsidian 命令面板统一使用英文 ID）

### pre-commit 检查

```bash
# 提交前运行 ruff lint + format + 一致性审计
ruff check --fix paperforge/ && ruff format paperforge/

# 运行测试（173 tests）
python -m pytest tests/unit/ -q --tb=short
```

---

*PaperForge | 快速开始指南 | 安装后阅读*
