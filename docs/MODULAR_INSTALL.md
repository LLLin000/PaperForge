# PaperForge 模块化安装架构设计

## 1. 设计目标

- **按需安装**: 用户只安装需要的功能模块
- **依赖自动解析**: 安装模块 A 时自动安装其依赖
- **增量扩展**: 后续可随时添加新模块
- **一键完整安装**: 保留当前的完整安装选项
- **配置隔离**: 每个模块独立配置，互不影响

---

## 2. 模块划分

### 2.1 模块依赖图

```
┌─────────────────────────────────────────────────────────────┐
│                      Core Infrastructure                     │
│  (目录结构, .env, AGENTS.md, Zotero junction)               │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│    Indexing      │ │ Lit. Control    │ │   Candidate     │
│   (文献索引)      │ │  (文献控制)      │ │   Management    │
│                  │ │                 │ │  (候选管理)      │
│ - index-refresh  │ │ - selection-sync│ │ - search-sources│
│ - formal-library │ │ - library-records│ │ - candidates    │
│   .json          │ │                 │ │ - writeback     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│     OCR          │ │   Deep Reading  │ │  (Optional      │
│  (OCR处理)       │ │   (深度阅读)     │ │   Extensions)   │
│                  │ │                 │ │                 │
│ - ocr worker     │ │ - ld_deep.py    │ │ - Chart Guides  │
│ - PaddleOCR API  │ │ - /LD-deep      │ │ - Export Plugins│
│                  │ │ - 精读笔记       │ │ - Sync Plugins  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 2.2 模块定义

#### Core Infrastructure (核心基础设施)
**必需**: 是 (所有模块的基础)

**功能**:
- 创建 PaperForge 目录结构
- 配置 .env 文件
- 生成 AGENTS.md
- 创建 Zotero junction
- 安装 Python 依赖

**文件**:
- `scripts/setup.py` (核心安装器)
- `scripts/validate_setup.py` (验证脚本)
- `scripts/welcome.py` (欢迎界面)

**目录**:
- `99_System/LiteraturePipeline/` (框架)
- `99_System/Template/` (框架)
- `99_System/Zotero/` (junction)

**配置**:
- Zotero 路径
- Vault 路径
- Agent 平台选择

---

#### Module 1: Indexing (文献索引)
**必需**: 否 (但推荐)
**依赖**: Core

**功能**:
- 读取 Better BibTeX JSON 导出
- 生成 formal-library.json 索引
- 自动创建/更新 Obsidian 文献笔记

**Worker**:
- `run_index_refresh` (line 1954)

**文件**:
- `literature_pipeline.py` (index-refresh 部分)

**目录**:
- `99_System/LiteraturePipeline/exports/` (Better BibTeX JSON)
- `99_System/LiteraturePipeline/indexes/` (生成的索引)
- `03_Resources/Literature/<domain>/` (生成的笔记)

**前置条件**:
- Zotero 安装 Better BibTeX 插件
- 配置自动导出 JSON

**适合用户**:
- 已有 Zotero 文献库
- 想自动同步到 Obsidian
- 不需要候选文献管理

---

#### Module 2: Literature Control (文献控制)
**必需**: 否
**依赖**: Core

**功能**:
- 扫描文献库，标记处理状态
- 创建 library-records 跟踪文件
- 标记哪些论文需要 analyze/ocr/deep_reading

**Worker**:
- `run_selection_sync` (line 790)

**文件**:
- `literature_pipeline.py` (selection-sync 部分)

**目录**:
- `03_Resources/LiteratureControl/library-records/`

**适合用户**:
- 想选择性深入阅读部分论文
- 需要跟踪论文处理状态
- 作为 OCR 和 Deep Reading 的前置模块

---

#### Module 3: Candidate Management (候选文献管理)
**必需**: 否
**依赖**: Core

**功能**:
- 外部文献搜索 (PubMed/OpenAlex/arXiv)
- 候选文献收集和去重
- 人工筛选工作流 (candidate-records)
- 回写到 Zotero (分配 ORTHO001/SPORT001 键)

**Worker**:
- `run_search_sources` (line 1549)
- `run_ingest_candidates` (line 1691)
- `run_harvest_sync` (line 1759)
- `run_candidate_sync` (line 620)
- `run_prepare_writeback` (line 1061)
- `run_writeback` (line 1804)
- `run_writeback_native` (line 1093)

**文件**:
- `literature_pipeline.py` (candidate 相关 workers)
- Zotero Bridge 插件 (可选)

**目录**:
- `99_System/LiteraturePipeline/candidates/`
- `99_System/LiteraturePipeline/search/`
- `99_System/LiteraturePipeline/writeback/`
- `03_Resources/LiteratureControl/candidate-records/`

**配置**:
- PubMed API (可选)
- OpenAlex API (可选)
- Zotero Bridge HTTP 端口

**适合用户**:
- 需要做系统性文献综述
- 想管理候选文献筛选流程
- 需要回写自定义键到 Zotero

---

#### Module 4: OCR Processing (OCR 处理)
**必需**: 否
**依赖**: Core, Literature Control (推荐)

**功能**:
- 上传 PDF 到 PaddleOCR-VL API
- 下载识别结果 (fulltext.md + images/)
- 提取图表和表格

**Worker**:
- `run_ocr` (line 2250)

**文件**:
- `literature_pipeline.py` (ocr worker)

**目录**:
- `99_System/LiteraturePipeline/ocr/<zotero_key>/`
  - `fulltext.md`
  - `images/`
  - `meta.json`

**配置**:
- PaddleOCR API Key
- PaddleOCR API URL

**前置条件**:
- 文献有 PDF 附件
- (推荐) Literature Control 标记 ocr=true

**适合用户**:
- 需要提取 PDF 全文
- 想做图表分析
- 是 Deep Reading 的前置步骤

---

#### Module 5: Deep Reading (深度阅读)
**必需**: 否
**依赖**: Core, OCR Processing (强烈推荐)

**功能**:
- AI 生成三阶段精读笔记
- 图表解析和嵌入
- 结构化输出 (Pass 1/2/3)

**命令**:
- `figure-map`
- `ensure-scaffold`
- `validate-note`
- `queue`

**文件**:
- `ld_deep.py`
- `prompt_deep_subagent.md`
- 读图指南 (14 个)

**目录**:
- `{skill_dir}/literature-qa/`
- `99_System/Template/读图指南/`

**配置**:
- Agent 平台特定配置

**前置条件**:
- (强烈推荐) OCR 完成，有 fulltext.md
- (推荐) Literature Control 标记 analyze=true

**适合用户**:
- 想深度理解论文
- 需要做文献精读笔记
- 是 PaperForge 的核心价值功能

---

#### Module 6: Chart Guides (读图指南)
**必需**: 否
**依赖**: Deep Reading (可选增强)

**功能**:
- 14 种科研图表的读图指南
- 辅助 Deep Reading 的图表分析

**文件**:
- `99_System/Template/科研读图指南.md`
- `99_System/Template/读图指南/*.md` (14 个)

**适合用户**:
- 想提升图表分析质量
- 使用 Deep Reading 模块

---

## 3. 典型安装场景

### 场景 A: 纯索引用户
> "我只想将 Zotero 文献自动同步到 Obsidian"

**安装模块**: Core + Indexing

**工作流程**:
1. Zotero Better BibTeX 自动导出 JSON
2. PaperForge 读取 JSON，生成 Obsidian 笔记
3. 在 Obsidian 中阅读和标注

**不安装**: Candidate, OCR, Deep Reading

---

### 场景 B: 深度阅读用户
> "我想对关键论文做 AI 精读"

**安装模块**: Core + Literature Control + OCR + Deep Reading

**工作流程**:
1. 手动导入或索引文献到 Obsidian
2. Literature Control 标记需要深入阅读的论文
3. OCR 提取 PDF 内容
4. Deep Reading 生成三阶段精读笔记

**不安装**: Candidate Management

---

### 场景 C: 系统综述用户
> "我要做系统性文献综述，需要搜索、筛选、管理候选文献"

**安装模块**: Core + Candidate Management + Indexing

**工作流程**:
1. 配置搜索任务 (PubMed/OpenAlex)
2. 收集候选文献到 inbox
3. 人工筛选 (candidate-records)
4. 回写到 Zotero (分配自定义键)
5. 索引生成 Obsidian 笔记

**可选安装**: OCR + Deep Reading (对纳入的论文做深入分析)

---

### 场景 D: 完整工作流用户
> "我要使用 PaperForge 的所有功能"

**安装模块**: All (Core + Indexing + Literature Control + Candidate + OCR + Deep Reading + Chart Guides)

**工作流程**: 完整 4 阶段工作流

---

## 4. 配置存储设计

### 4.1 模块配置格式 (.env)

```ini
# Core
PAPERFORGE_AGENT=opencode
PAPERFORGE_AGENT_NAME=OpenCode
PAPERFORGE_SKILL_DIR=.opencode/skills
PAPERFORGE_SYSTEM_DIR=99_System
PAPERFORGE_PIPELINE_PATH=99_System/LiteraturePipeline
PAPERFORGE_TEMPLATE_PATH=99_System/Template

# Module: Indexing
PAPERFORGE_MODULE_INDEXING=true
ZOTERO_DATA_DIR=C:\Users\XXX\Zotero

# Module: Literature Control
PAPERFORGE_MODULE_LIT_CONTROL=true

# Module: Candidate Management
PAPERFORGE_MODULE_CANDIDATE=true

# Module: OCR
PAPERFORGE_MODULE_OCR=true
PADDLEOCR_API_KEY=xxx
PADDLEOCR_API_URL=https://paddleocr.baidu.com/api/v1/ocr

# Module: Deep Reading
PAPERFORGE_MODULE_DEEP_READING=true

# Module: Chart Guides
PAPERFORGE_MODULE_CHART_GUIDES=true
```

### 4.2 模块状态文件

```json
// .paperforge/modules.json
{
  "version": "1.0",
  "installed": [
    "core",
    "indexing",
    "literature-control",
    "ocr",
    "deep-reading"
  ],
  "config": {
    "core": {
      "agent": "opencode",
      "system_dir": "99_System"
    },
    "indexing": {
      "enabled": true,
      "auto_refresh": true
    }
  }
}
```

---

## 5. 安装器设计

### 5.1 交互式模块选择

```
========================================
PaperForge Modular Installer
========================================

Select installation mode:

  1. Quick Setup - Full installation (all modules)
  2. Custom Setup - Choose modules individually
  3. Minimal Setup - Core + Indexing only

> 2

--- Module Selection ---

[✓] Core Infrastructure (required)
    Creates directory structure, .env, AGENTS.md

[ ] Module 1: Indexing
    Auto-sync Zotero to Obsidian notes

[ ] Module 2: Literature Control
    Track paper processing status

[ ] Module 3: Candidate Management
    Search, collect, and filter candidates

[ ] Module 4: OCR Processing
    Extract PDF text and images via PaddleOCR

[ ] Module 5: Deep Reading
    AI-powered three-pass reading notes

[ ] Module 6: Chart Guides
    14 chart reading guide templates

Select modules (e.g., 1,4,5): 1,4,5

Dependencies check:
  - Indexing: requires Core ✓
  - OCR: requires Core ✓
  - Deep Reading: requires Core, OCR (recommended) ✓

Continue with installation? [Y/n]: Y
```

### 5.2 命令行接口

```bash
# 完整安装
python scripts/setup.py --full

# 只安装特定模块
python scripts/setup.py --modules indexing,ocr,deep-reading

# 添加模块到现有安装
python scripts/setup.py --add chart-guides

# 查看已安装模块
python scripts/setup.py --status

# 模块帮助
python scripts/setup.py --help-modules
```

---

## 6. 实现计划

### Phase 1: 重构 setup.py (本周)
- [ ] 创建 `ModuleRegistry` 类
- [ ] 定义所有模块的元数据
- [ ] 实现依赖解析算法
- [ ] 添加 `--modules` 命令行参数

### Phase 2: 模块部署函数 (下周)
- [ ] 为每个模块创建独立的 `deploy_*()` 函数
- [ ] 模块配置验证
- [ ] 增量安装支持

### Phase 3: 状态管理 (下周)
- [ ] 创建 `.paperforge/modules.json`
- [ ] 实现 `--status` 和 `--add` 命令
- [ ] 模块卸载支持

### Phase 4: 文档更新 (下周)
- [ ] 更新 INSTALLATION.md
- [ ] 添加模块选择流程图
- [ ] 典型场景示例

---

## 7. 代码结构

```
github-release/
├── scripts/
│   ├── setup.py              # 主安装器 (模块化)
│   ├── modules/              # 模块定义
│   │   ├── __init__.py
│   │   ├── core.py           # 核心基础设施
│   │   ├── indexing.py       # 文献索引
│   │   ├── lit_control.py    # 文献控制
│   │   ├── candidate.py      # 候选管理
│   │   ├── ocr.py            # OCR 处理
│   │   ├── deep_reading.py   # 深度阅读
│   │   └── chart_guides.py   # 读图指南
│   ├── welcome.py            # 欢迎界面
│   └── validate_setup.py     # 验证脚本
├── docs/
│   ├── INSTALLATION.md
│   └── MODULAR_INSTALL.md    # 本文档
└── 99_System/
    └── LiteraturePipeline/
        └── worker/
            └── scripts/
                └── literature_pipeline.py
```

---

## 8. 向后兼容

- 保留当前的 `python scripts/setup.py` 完整安装行为
- 新增命令行参数是可选的
- 现有用户不受影响
- 通过 `.paperforge/modules.json` 检测旧版本并提示升级
