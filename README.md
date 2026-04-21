# PaperForge

基于 Obsidian + Zotero 的文献精读工作流，将粗糙的 PDF 文献锻造成精炼的知识晶体。

**支持多 Agent 平台**: OpenCode / Claude Code / Cursor / Windsurf / GitHub Copilot / Cline / Augment / Trae

```
   +======================+
   |    PaperForge v1.0   |
   +======================+
          |        |
    Zotero |        | Obsidian
    (Better|        | (Notes)
    BibTeX)|        |
          v        v
   +======================+
   |  Literature Pipeline |
   +======================+
   OCR -> Index -> Deep Reading
```

## 快速开始

### 方式一：让 Agent 帮你配置（推荐）

复制以下内容，粘贴给你的 AI Agent，它会自动完成全部配置：

```
Install and configure the literature workflow by following the instructions here:
https://raw.githubusercontent.com/LLLin000/PaperForge/main/docs/INSTALLATION.md
```

Agent 会问你几个问题，然后自动完成安装、配置和验证。

### 方式二：手动安装

需要：
- Python 3.10+
- Zotero（安装 Better BibTeX 插件）
- Obsidian
- PaddleOCR API Key

```bash
# 1. 克隆仓库
git clone https://github.com/LLLin000/PaperForge.git
cd PaperForge

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 运行安装脚本
python scripts/setup.py
```

安装脚本会引导你：
1. **选择 Agent 平台**（决定 skill 文件存放位置）
2. **配置 Vault 目录结构**（可自定义系统文件夹、文献目录等名称）
3. **配置 Zotero 路径**（Better BibTeX JSON 导出目录）
4. **部署工作流脚本**

---

## 功能特性

- **文献索引** — 自动从 Better BibTeX JSON 导出生成 Obsidian 笔记
- **深度精读** — Keshav 三阶段阅读法（概览 → 精读还原 → 深度理解）
- **自动 OCR** — PaddleOCR-VL API 提取 PDF 全文和图片
- **图表解析** — 14 种科研图表的读图指南
- **多 Agent 支持** — 支持 OpenCode、Claude Code、Cursor 等 8+ 平台

---

## 工作流程

### 第 1 阶段：索引（Zotero → Obsidian）

```
Zotero + Better BibTeX
    |
    v (自动导出 JSON)
99_System/LiteraturePipeline/exports/骨科.json
    |
    v (run_index_refresh)
03_Resources/Literature/骨科/*.md  (生成文献笔记)
```

### 第 2 阶段：标记（选择需要深入阅读的论文）

```
literature_pipeline.py selection-sync
    |
    v (标记 analyze=true)
03_Resources/LiteratureControl/library-records/*.md
```

### 第 3 阶段：OCR（提取 PDF 内容）

```
 literature_pipeline.py ocr
    |
    v (PaddleOCR-VL API)
99_System/LiteraturePipeline/ocr/<zotero_key>/
    ├── fulltext.md          (完整文本)
    ├── images/              (提取的图片)
    └── meta.json            (元数据)
```

### 第 4 阶段：深度阅读（生成精读笔记）

```
 literature_pipeline.py deep-reading
    |
    v (AI Agent 填充)
03_Resources/Literature/骨科/*.md
    └── ## 🔍 精读           (追加三阶段精读)
```

### 三阶段精读结构

```markdown
## 🔍 精读

### Pass 1: 概览
- 一句话总览
- 5 Cs 快速评估
- Figure 导读

### Pass 2: 精读还原
- Figure-by-Figure 解析（含图表嵌入）
- Table-by-Table 解析
- 关键方法补课
- 主要发现与新意

### Pass 3: 深度理解
- 假设挑战与隐藏缺陷
- 哪些结论扎实，哪些仍存疑
- Discussion 解读
- 对我的启发
- 遗留问题
```

---

## 目录结构

PaperForge 只管理以下目录。你的 PARA 文件夹（00_Inbox, 04_Archives 等）由你自己维护。

```
<vault>/
├── 99_System/                          # [PaperForge 管理]
│   ├── LiteraturePipeline/             #   核心管道
│   │   ├── candidates/                 #     候选文献管理
│   │   │   ├── inbox/                  #       搜索结果临时存储
│   │   │   └── archive/                #       归档事件
│   │   ├── exports/                    #     Better BibTeX JSON 导出
│   │   ├── indexes/                    #     生成的索引文件
│   │   ├── ocr/                        #     OCR 输出
│   │   │   └── <zotero_key>/           #       fulltext.md + images/
│   │   ├── search/                     #     搜索任务
│   │   │   ├── tasks/                  #       搜索配置
│   │   │   └── results/                #       结果缓存
│   │   ├── writeback/                  #     回写队列和日志
│   │   └── worker/                     #     Worker 脚本
│   │       ├── scripts/                #       literature_pipeline.py
│   │       └── tests/                  #       测试文件
│   ├── Template/                       #   模板
│   │   ├── 文献阅读.md                 #     文献笔记模板
│   │   ├── 科研读图指南.md             #     主读图指南
│   │   └── 读图指南/                   #     14 种图表类型指南
│   └── Zotero/                         #   Zotero 软链接 (junction)
│
├── 03_Resources/
│   ├── Literature/                     # [你的文献库]
│   │   ├── 骨科/                       #   index_refresh 生成
│   │   └── 运动医学/                   #   index_refresh 生成
│   └── LiteratureControl/              # [PaperForge 管理]
│       ├── candidate-records/          #   candidate_sync 生成
│       └── library-records/            #   selection_sync 生成
│
├── AGENTS.md                           # [PaperForge 生成] Agent 指南
└── .env                                # [PaperForge 生成] 配置文件
```

---

## 核心 Worker

| Worker | 功能 |
|--------|------|
| `index-refresh` | 读取 Better BibTeX JSON，生成文献笔记 |
| `selection-sync` | 标记需要深入阅读的论文（analyze/ocr/deep） |
| `ocr` | PaddleOCR-VL API 提取 PDF 全文和图片 |
| `deep-reading` | AI 生成三阶段精读笔记 |
| `search-sources` | PubMed/OpenAlex/arXiv 搜索 |
| `candidate-sync` | 候选文献管理和筛选 |

---

## 文档

- [安装指南](docs/INSTALLATION.md)
- [审计报告](docs/AUDIT_REPORT.md) - 工作流架构详解
- [读图指南](99_System/Template/科研读图指南.md)

---

## 技术栈

- **Obsidian** - 知识管理
- **Zotero** + Better BibTeX - 文献管理
- **PaddleOCR-VL** - PDF 识别
- **Python 3.10+** - 管道脚本

---

## License

MIT License — 允许商业使用，需保留版权声明。
