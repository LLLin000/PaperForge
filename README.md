# PaperForge

基于 Obsidian + Zotero 的文献精读工作流，将粗糙的 PDF 文献锻造成精炼的知识晶体。

目前支持 OpenCode Agent，未来计划支持更多 AI Agent。

```
    ______  ___  ______ _________________ ___________ _____  _____
    | ___ \/ _ \ | ___ \  ___| ___ \  ___|  _  | ___ \  __ \|  ___|
    | |_/ / /_\ \| |_/ / |__ | |_/ / |_  | | | | |_/ / |  \/| |__
    |  __/|  _  ||  __/|  __||    /|  _| | | | |    /| | __ |  __|
    | |   | | | || |   | |___| |\ \| |   \ \_/ / |\ \| |_\ \| |___
    \_|   \_| |_/\_|   \____/\_| \_\_|    \___/\_| \_|\____/\____/

              [+]  Forge Your Knowledge Into Power  [+]
```

## 核心架构

PaperForge 是一个三层文献处理管道：

### 第一层：索引生成
- **Better BibTeX** 自动导出 Zotero 库为 JSON
- `selection_sync` 检测新条目并标记状态
- `index_refresh` 生成 Obsidian 文献笔记（含 Frontmatter）

### 第二层：OCR 处理
- `ocr` 自动上传 PDF 到 PaddleOCR API
- 提取全文文本 + 图表切割
- 保存到 `ocr/<key>/` 目录供精读使用

### 第三层：深度精读（Agent 驱动）
- 用户执行 `/LD-deep <key>` 命令
- Agent 调用 `ld_deep.py` 生成 Keshav 三阶段精读骨架
- 填充 Pass 1/2/3 内容，输出 `## 🔍 精读` 笔记

> **注意**：深度精读由 Agent 命令触发，非自动执行。

## 快速开始

### 让 Agent 帮你安装（推荐）

复制以下内容，粘贴给你的 OpenCode Agent：

```
Install and configure the literature workflow by following the instructions here:
https://raw.githubusercontent.com/LLLin000/PaperForge/main/docs/INSTALLATION.md
```

Agent 会自动完成：
1. 检测 Zotero 路径
2. 安装 Python 依赖
3. 创建目录结构
4. 配置 PaddleOCR API
5. 部署工作流脚本

### 手动安装

```bash
git clone https://github.com/LLLin000/PaperForge.git
cd PaperForge
python scripts/setup.py
```

## 安装要求

- **Zotero** + Better BibTeX 插件（自动导出 JSON）
- **Obsidian**（笔记存储）
- **Python 3.8+**
- **PaddleOCR API Key**（PDF 识别）

## 目录结构

安装后在你的 Vault 中创建：

```
99_System/
├── LiteraturePipeline/
│   ├── exports/          # Better BibTeX JSON 导出
│   ├── indexes/          # 文献索引 formal-library.json
│   ├── ocr/              # OCR 结果（全文 + 图表）
│   └── worker/scripts/   # 工作流脚本
├── Template/
│   └── 科研读图指南.md     # 图表阅读参考
└── Zotero/               # Zotero 数据链接

03_Resources/
└── Literature/
    └── <domain>/         # 生成的文献笔记

.opencode/skills/
├── literature-qa/        # 深度阅读 Skill
│   ├── scripts/ld_deep.py
│   └── prompt_deep_subagent.md
└── chart-reading/        # 14 种图表阅读指南
```

## 工作流命令

### 后台 Worker（Python）

```bash
# 检测新条目并更新状态
python pipeline/worker/scripts/literature_pipeline.py selection-sync

# 生成/更新 Obsidian 笔记
python pipeline/worker/scripts/literature_pipeline.py index-refresh

# OCR 处理待处理 PDF
python pipeline/worker/scripts/literature_pipeline.py ocr

# 生成待精读队列
python pipeline/worker/scripts/literature_pipeline.py deep-reading
```

### Agent 命令（OpenCode）

```
/LD-deep <citation_key>    # 对指定文献执行深度精读
```

## 工作流程

```
1. Zotero 中添加文献（Better BibTeX 自动导出 JSON）
   ↓
2. 运行 selection-sync（检测新条目）
   ↓
3. 运行 index-refresh（生成 Obsidian 笔记）
   ↓
4. 运行 ocr（处理 PDF，提取全文+图表）
   ↓
5. 在 Obsidian 中查看笔记，执行 /LD-deep <key>
   ↓
6. Agent 生成 ## 🔍 精读 笔记
```

## 核心特性

- **全自动索引**：Zotero 变动自动同步到 Obsidian
- **OCR 全文提取**：PDF 转可搜索文本 + 图表切割
- **Keshav 三阶段精读**：概览 → 精读还原 → 深度理解
- **14 种图表阅读指南**：箱式图、热图、ROC、火山图等
- **结构化输出**：标准化 frontmatter + 三阶段精读模板

## 隐私保护

- `.env` 文件（含 API Key）已加入 `.gitignore`
- 所有个人数据（笔记、PDF、OCR 结果）不会被提交
- 仓库仅包含工作流代码和模板

## License

MIT License with commercial use permitted.

---

**PaperForge** — *Preparing for the Future, One Paper at a Time.*
