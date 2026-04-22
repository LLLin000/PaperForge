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
[ ] Zotero 数据目录已链接到 99_System/Zotero
```

### Better BibTeX 自动导出配置

1. Zotero → Edit → Preferences → Better BibTeX
2. 勾选 **"Keep updated"**（自动导出）
3. 选择导出格式：**Better BibLaTeX** 或 **Better BibTeX**
4. 导出路径设置为：`{你的Vault路径}/99_System/PaperForge/exports/library.json`
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
99_System/PaperForge/exports/library.json
    ↓ 运行 selection-sync
03_Resources/LiteratureControl/library-records/<domain>/<key>.md
    ↓ 运行 index-refresh
03_Resources/Literature/<domain>/<key> - <Title>.md（正式笔记）
    ↓ 用户在 library-record 中设置 do_ocr: true
运行 ocr → 99_System/PaperForge/ocr/<key>/
    ↓ 用户在 library-record 中设置 analyze: true
运行 deep-reading（查看队列，确认就绪）
    ↓ 用户执行 Agent 命令
/LD-deep <zotero_key>
    ↓ Agent 生成
正式笔记中新增 ## 🔍 精读 区域
```

---

## 3. 目录结构（Lite 版，5 个核心目录）

```
{你的Vault根目录}/
├── 03_Resources/
│   ├── Literature/                    ← 正式文献笔记（index-refresh 生成）
│   │   ├── 骨科/
│   │   ├── 运动医学/
│   │   └── ...（你的分类）
│   └── LiteratureControl/             ← 状态跟踪
│       └── library-records/           ← selection-sync 输出
│           ├── 骨科/
│           │   └── ABCDEFG.md         ← 单条文献状态记录
│           └── 运动医学/
│               └── HIJKLMN.md
│
├── 99_System/
│   ├── LiteraturePipeline/
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
│   ├── Template/
│   │   └── 科研读图指南.md            ← 图表阅读参考
│   └── Zotero/                        ← Junction/Symlink 到 Zotero 数据目录
│
├── .opencode/                         ← OpenCode Agent 配置（自动创建）
│   └── skills/
│       └── literature-qa/             ← 深度阅读 Skill
│           ├── scripts/
│           │   └── ld_deep.py         ← /LD-deep 核心脚本
│           ├── prompt_deep_subagent.md ← Agent 精读提示词
│           └── chart-reading/         ← 14 种图表阅读指南
│
├── .env                               ← API Key 等敏感配置
└── AGENTS.md                          ← 本文件
```

### 各目录作用速查

| 目录 | 内容 | 谁生成/修改 |
|------|------|------------|
| `03_Resources/Literature/` | 正式文献笔记（含 frontmatter + 精读内容） | index-refresh 生成，Agent 写入精读 |
| `03_Resources/LiteratureControl/library-records/` | 文献状态跟踪（analyze, ocr_status 等） | selection-sync 生成，用户修改状态 |
| `99_System/PaperForge/exports/` | Better BibTeX JSON 导出 | Zotero 自动导出 |
| `99_System/PaperForge/ocr/` | OCR 全文 + 图表切割 | ocr worker 生成 |
| `99_System/Zotero/` | Zotero 数据目录的链接 | 安装时手动创建 junction |

---

## 4. 核心 Workers（Lite 版，4 个）

### selection-sync
- **作用**：检测 Zotero 中的新条目，创建 library-records
- **运行时机**：添加新文献到 Zotero 后
- **输出**：`03_Resources/LiteratureControl/library-records/<domain>/<key>.md`
- **示例**：
  ```bash
  python 99_System/PaperForge/worker/scripts/literature_pipeline.py \
    --vault "{vault路径}" selection-sync
  ```

### index-refresh
- **作用**：基于 library-records 生成正式文献笔记
- **运行时机**：selection-sync 之后，或需要更新笔记格式时
- **输出**：`03_Resources/Literature/<domain>/<key> - <Title>.md`
- **说明**：会读取 Better BibTeX JSON 提取元数据，生成带 frontmatter 的 Obsidian 笔记

### ocr
- **作用**：将 PDF 上传到 PaddleOCR API，提取全文文本和图表
- **触发条件**：library-record 中 `do_ocr: true`
- **输出**：`99_System/PaperForge/ocr/<key>/` 目录
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
pdf_path: "99_System/Zotero/..." # PDF 相对路径（自动生成）
fulltext_md_path: "99_System/PaperForge/ocr/..."
recommend_analyze: true          # 系统推荐精读（有 PDF 时自动设为 true）
analyze: false                   # 【用户控制】是否生成精读？设为 true 触发
do_ocr: true                     # 【用户控制】是否运行 OCR？设为 true 触发
ocr_status: "done"               # OCR 状态（pending/processing/done/failed）
deep_reading_status: "pending"   # 精读状态（pending/done）
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
pdf_link: "99_System/Zotero/..."
---
```

---

## 7. 第一次使用指南（手把手）

### Step 1: 确认 Zotero 有文献

确保 Zotero 中已有至少一篇带 PDF 的文献，且 Better BibTeX 已导出 JSON。

### Step 2: 运行 selection-sync

```bash
# 在 Vault 根目录执行
python 99_System/PaperForge/worker/scripts/literature_pipeline.py \
  --vault "你的Vault路径" selection-sync
```

预期输出：
```
[INFO] Found 5 new items
[INFO] Created library-records/骨科/XXXXXXX.md
...
```

### Step 3: 运行 index-refresh

```bash
python 99_System/PaperForge/worker/scripts/literature_pipeline.py \
  --vault "你的Vault路径" index-refresh
```

预期输出：
```
[INFO] Generated 5 formal notes
[INFO] Output: 03_Resources/Literature/骨科/XXXXXXX - Title.md
...
```

### Step 4: 标记要精读的文献

在 Obsidian 中：
1. 打开 `03_Resources/LiteratureControl/library-records/骨科/XXXXXXX.md`
2. 将 `do_ocr: false` 改为 `do_ocr: true`
3. 将 `analyze: false` 改为 `analyze: true`
4. 保存文件

### Step 5: 运行 OCR

```bash
python 99_System/PaperForge/worker/scripts/literature_pipeline.py \
  --vault "你的Vault路径" ocr
```

等待完成（可能需要几分钟）。

### Step 6: 检查 OCR 状态

```bash
python 99_System/PaperForge/worker/scripts/literature_pipeline.py \
  --vault "你的Vault路径" deep-reading
```

预期输出：
```
## 就绪 (1 篇) — OCR 完成
- `XXXXXXX` | 骨科 | 论文标题
```

### Step 7: 执行精读

在 OpenCode Agent 中输入：
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
python 99_System/PaperForge/worker/scripts/literature_pipeline.py \
  --vault "你的Vault路径" selection-sync

# 生成/更新正式笔记
python 99_System/PaperForge/worker/scripts/literature_pipeline.py \
  --vault "你的Vault路径" index-refresh

# 运行 OCR（处理 do_ocr=true 的文献）
python 99_System/PaperForge/worker/scripts/literature_pipeline.py \
  --vault "你的Vault路径" ocr

# 查看精读队列
python 99_System/PaperForge/worker/scripts/literature_pipeline.py \
  --vault "你的Vault路径" deep-reading

# 查看整体状态
python 99_System/PaperForge/worker/scripts/literature_pipeline.py \
  --vault "你的Vault路径" status
```

### Agent 命令
```
/LD-deep <zotero_key>    # 完整三阶段精读
/LD-paper <zotero_key>   # 快速摘要
```

---

## 9. 常见问题

### Q: 运行 selection-sync 后没有生成 library-records？
- 检查 Better BibTeX JSON 导出路径是否正确
- 检查 JSON 文件是否包含文献数据
- 确认 Zotero 中该文献有 citation key

### Q: OCR 一直显示 pending？
- 检查 PaddleOCR API Key 是否配置正确（`.env` 文件）
- 检查网络连接
- 查看 `99_System/PaperForge/ocr/<key>/meta.json` 中的错误信息

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
cd 你的Vault路径
# 如果你有 git 跟踪 PaperForge
git pull origin main

# 或手动复制更新文件
cp -r 新下载的scripts/* 99_System/PaperForge/worker/scripts/
```

### 备份注意事项
- `03_Resources/` 和 `99_System/PaperForge/ocr/` 包含你的数据，需备份
- `.env` 包含 API Key，不要提交到 git
- `99_System/PaperForge/exports/` 可重新生成（由 Zotero 自动导出）

---

*PaperForge Lite | 快速开始指南 | 安装后阅读*
