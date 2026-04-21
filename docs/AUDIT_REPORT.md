# PaperForge 工作流审计报告

> 生成时间: 2026-04-22
> 审计范围: `literature_pipeline.py` (11 workers) + `ld_deep.py` (6 commands) + `setup.py` 配置

---

## 1. 用户实际工作流全貌

### 1.1 数据流架构

```
┌─────────────┐     Better BibTeX     ┌─────────────────────────────┐
│   Zotero    │ ────auto-export────>  │ 99_System/LiteraturePipeline/│
│  (source)   │        JSON           │    exports/骨科.json          │
└─────────────┘                       └─────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PaperForge Pipeline Workers                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Phase 1: 候选文献管理 (External → Candidates)                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│  │search_sources│ -> │ingest_cand.  │ -> │ candidate.   │         │
│  │ (PubMed/     │    │ (dedup/      │    │ json         │         │
│  │  OpenAlex)   │    │  normalize)  │    │              │         │
│  └──────────────┘    └──────────────┘    └──────────────┘         │
│         ▲                                         │                 │
│         │                                         ▼                 │
│  ┌──────────────┐                       ┌──────────────┐           │
│  │ harvest_sync │ <──────────────────── │prepare_writeb│           │
│  │ (CSV import) │                       │ ack          │           │
│  └──────────────┘                       └──────────────┘           │
│                                                │                    │
│  Phase 2: 回写与同步 (Candidates → Zotero)                          │
│                                                ▼                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│  │   writeback  │ -> │writeback_    │ -> │   Zotero     │         │
│  │(assign keys) │    │ native       │    │ (Bridge API) │         │
│  └──────────────┘    └──────────────┘    └──────────────┘         │
│         │                                                           │
│  Phase 3: 索引与笔记 (Zotero → Obsidian)                             │
│         ▼                                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│  │selection_sync│ -> │ index_refresh│ -> │ 03_Resources/│         │
│  │(flags: analyze│    │ (generate    │    │ Literature/  │         │
│  │  ocr, deep)  │    │  formal-lib) │    │ 骨科/运动医学│         │
│  └──────────────┘    └──────────────┘    └──────────────┘         │
│                                                │                    │
│  Phase 4: 深度处理 (Notes → Enhanced Notes)                          │
│                                                ▼                    │
│  ┌──────────────┐    ┌──────────────┐                              │
│  │     ocr      │ -> │deep_reading  │                              │
│  │(PaddleOCR-VL│    │ (/LD-deep)   │                              │
│  │  API)        │    │              │                              │
│  └──────────────┘    └──────────────┘                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 关键目录（来自 `pipeline_paths()`）

| 路径变量 | 实际路径 | 用途 |
|----------|----------|------|
| `candidates` | `99_System/LiteraturePipeline/candidates/` | 候选文献 JSON 存储 |
| `candidate_inbox` | `99_System/LiteraturePipeline/candidates/inbox/` | 搜索结果的临时收件箱 |
| `candidate_archive` | `99_System/LiteraturePipeline/candidates/archive/` | 归档的候选事件 |
| `search_tasks` | `99_System/LiteraturePipeline/search/tasks/` | 搜索任务配置 JSON |
| `search_results` | `99_System/LiteraturePipeline/search/results/` | 搜索结果缓存 |
| `exports` | `99_System/LiteraturePipeline/exports/` | **Better BibTeX JSON 导出** |
| `index` | `99_System/LiteraturePipeline/indexes/` | 生成的索引文件 |
| `ocr` | `99_System/LiteraturePipeline/ocr/` | OCR 输出（fulltext.md + images/） |
| `writeback` | `99_System/LiteraturePipeline/writeback/` | 回写队列和日志 |
| `library_records` | `03_Resources/LiteratureControl/library-records/` | 库记录管理（带处理标志） |
| `records` | `03_Resources/LiteratureControl/candidate-records/` | 候选记录 Markdown |

### 1.3 11 个 Worker 详解

| Worker | 行号 | 输入 | 输出 | 关键动作 |
|--------|------|------|------|----------|
| `run_candidate_sync` | 620 | `candidates.json` | `candidate-records/*.md`, `review-latest.md` | 生成供人工筛选的候选文献卡片 |
| `run_search_sources` | 1549 | `search/tasks/*.json` | `candidates/inbox/*.jsonl` | PubMed/OpenAlex/arXiv 搜索 |
| `run_ingest_candidates` | 1691 | `candidates/inbox/*.jsonl` | `candidates.json` | 归一化、合并、去重 |
| `run_harvest_sync` | 1759 | CSV 文件 | `candidates.json` | 外部搜索结果导入 |
| `run_selection_sync` | 790 | `exports/*.json` | `library-records/*.md` | 标记需要 analyze/ocr/deep_reading 的条目 |
| `run_prepare_writeback` | 1061 | `candidates.json` | `writeback/queue.jsonl` | 生成回写命令 |
| `run_writeback` | 1804 | `writeback/queue.jsonl` | `exports/*.json` | 分配 ORTHO001/SPORT001 键 |
| `run_writeback_native` | 1093 | `writeback/queue.jsonl` | Zotero (HTTP API) | 调用 Zotero Bridge 插件 |
| `run_index_refresh` | 1954 | `exports/*.json` | `indexes/formal-library.json`, `03_Resources/Literature/<domain>/*.md` | **生成正式文献笔记** |
| `run_ocr` | 2250 | PDF 文件 (来自 exports) | `ocr/<key>/fulltext.md` | PaddleOCR-VL 识别 |
| `run_deep_reading` | 2350 | `library-records/*.md` (analyze=true) | 笔记追加 `## 🔍 精读` | LD-deep 三阶段精读 |

### 1.4 LD-deep 子系统（6 个命令）

| 命令 | 功能 |
|------|------|
| `figure-index` | 从 OCR fulltext 提取 Figure 信息 |
| `ensure-scaffold` | 在笔记末尾追加 `## 🔍 精读` 骨架（Pass 1/2/3） |
| `validate-selected` | 检查选定的 figure/table embeds 是否存在 |
| `validate-note` | 完整结构验证（12 sections, callout spacing, 占位符） |
| `queue` | 列出等待深度阅读的论文 |
| `figure-map` | 从 OCR 构建 caption-driven 图表映射 |

---

## 2. Setup.py 审计发现

### 2.1 ❌ 问题 1：创建了不应由 PaperForge 管理的目录

**当前行为**：
```python
dirs = [
    f"{paths['pipeline_path']}/ocr",
    f"{paths['pipeline_path']}/worker/scripts",
    f"{paths['system_dir']}/Zotero",
    f"{paths['template_path']}",
    f"{paths['literature_path']}",  # ❌ 03_Resources/Literature 是用户文献库，不应由安装程序创建
    f"{paths['inbox_dir']}",        # ❌ 00_Inbox 是用户 PARA 系统的一部分
    f"{paths['bases_dir']}",        # ❌ 05_Bases 是用户 PARA 系统的一部分
    f"{paths['archives_dir']}",     # ❌ 04_Archives 是用户 PARA 系统的一部分
    f"{paths['wiki_dir']}",         # ❌ 06_AI_Wiki 是用户 PARA 系统的一部分
]
```

**正确行为**：PaperForge 只应创建它自己管理的目录：
```python
dirs = [
    # 核心管道目录
    f"{paths['pipeline_path']}/ocr",
    f"{paths['pipeline_path']}/worker/scripts",
    f"{paths['pipeline_path']}/candidates/inbox",
    f"{paths['pipeline_path']}/candidates/archive",
    f"{paths['pipeline_path']}/search/tasks",
    f"{paths['pipeline_path']}/search/results",
    f"{paths['pipeline_path']}/indexes",
    f"{paths['pipeline_path']}/writeback",
    
    # 模板目录
    f"{paths['template_path']}",
    f"{paths['template_path']}/读图指南",
    
    # Zotero 连接点
    f"{paths['system_dir']}/Zotero",
    
    # 文献控制目录（PaperForge 管理）
    "03_Resources/LiteratureControl/library-records",
    "03_Resources/LiteratureControl/candidate-records",
]
```

### 2.2 ❌ 问题 2：AGENTS.md 重复写入

**位置**：`setup.py` 第 401-405 行
```python
agents_path.write_text(content, encoding="utf-8")  # line 401
print_success(f"AGENTS.md created at {agents_path}")

agents_path.write_text(content, encoding="utf-8")  # line 404 - ❌ 重复！
print_success(f"AGENTS.md created at {agents_path}")
```

**影响**：无功能影响，但会打印两次成功消息，显得不专业。

### 2.3 ⚠️ 问题 3：AGENTS.md 包含 OpenCode 特定命令

**当前内容**：
```markdown
- `/LD <query>` - Quick literature lookup
- `/LD-deep <query>` - Deep reading (Keshav three-pass)
- `/LD-deep queue` - Process queued papers
```

**问题**：`/LD` 和 `/LD-deep` 是 OpenCode 的 slash command 语法。其他 Agent（如 Claude Code、Cursor）不使用这种语法。

**建议**：改为描述功能而非命令语法：
```markdown
- **Quick Lookup** - 文献速览（单篇或批量）
- **Deep Reading** - 深度精读（Keshav 三阶段阅读法）
- **Queue Processing** - 批量处理等待队列中的论文
```

### 2.4 ⚠️ 问题 4：部署路径未包含所有必要脚本

**当前部署**：
- `literature_pipeline.py` → `99_System/LiteraturePipeline/worker/scripts/`
- `ld_deep.py` → `{skill_dir}/literature-qa/scripts/`
- `prompt_deep_subagent.md` → `{skill_dir}/literature-qa/`
- 读图指南 → `99_System/Template/读图指南/`

**缺失**：
- `99_System/LiteraturePipeline/worker/tests/` - 测试文件
- `99_System/Template/文献阅读.md` - 文献笔记模板
- `99_System/Template/科研读图指南.md` - 主读图指南

### 2.5 ❌ 问题 5：配置变量未保存路径配置

**当前 `.env` 生成**：
```python
config = {
    "zotero_path": str(zotero_path),
    "storage_path": str(storage_path),
    "ocr_api_key": ocr_api_key,
    "agent": agent_key,
    "agent_name": agent_config["name"],
    "skill_dir": agent_config["skill_dir"],
}
```

**缺失**：没有保存用户自定义的路径配置（system_dir, literature_path 等）。如果用户更改了默认文件夹名，worker 无法知道。

**建议添加**：
```python
config["system_dir"] = paths["system_dir"]
config["pipeline_path"] = paths["pipeline_path"]
config["template_path"] = paths["template_path"]
```

---

## 3. 修复建议（优先级排序）

### 🔴 P0：修复目录创建
- [ ] 移除 00_Inbox, 04_Archives, 05_Bases, 06_AI_Wiki 的创建
- [ ] 添加缺失的管道目录：candidates/inbox, candidates/archive, search/tasks, search/results, indexes, writeback
- [ ] 添加 LiteratureControl 目录：library-records, candidate-records

### 🔴 P0：修复 AGENTS.md 重复写入
- [ ] 删除 line 404-405 的重复 write_text

### 🟡 P1：修复 AGENTS.md 命令引用
- [ ] 将 `/LD` 和 `/LD-deep` 改为功能描述
- [ ] 添加注释说明这些命令的 Agent 特定语法

### 🟡 P1：完善 .env 配置
- [ ] 保存用户自定义路径到 .env
- [ ] 更新 worker 读取 .env 中的路径配置

### 🟢 P2：完善部署文件
- [ ] 部署测试文件
- [ ] 部署文献阅读模板
- [ ] 部署科研读图指南主文件

---

## 4. 附：用户实际目录结构（预期）

```
<vault>/
├── 00_Inbox/                    # [用户 PARA，PaperForge 不创建]
├── 01_Projects/                 # [用户 PARA，PaperForge 不创建]
├── 02_Areas/                    # [用户 PARA，PaperForge 不创建]
├── 03_Resources/
│   ├── Literature/              # [用户文献库，PaperForge 不创建]
│   │   ├── 骨科/                #   index_refresh 生成
│   │   └── 运动医学/            #   index_refresh 生成
│   └── LiteratureControl/       # [PaperForge 创建]
│       ├── candidate-records/   #   candidate_sync 生成
│       └── library-records/     #   selection_sync 生成
├── 04_Archives/                 # [用户 PARA，PaperForge 不创建]
├── 05_Bases/                    # [用户 PARA，PaperForge 不创建]
├── 06_AI_Wiki/                  # [用户 PARA，PaperForge 不创建]
├── 99_System/                   # [PaperForge 创建]
│   ├── LiteraturePipeline/      #   核心管道
│   │   ├── candidates/          #     候选文献存储
│   │   │   ├── inbox/           #       搜索结果收件箱
│   │   │   └── archive/         #       归档事件
│   │   ├── config/              #     配置文件
│   │   ├── exports/             #     Better BibTeX JSON
│   │   ├── indexes/             #     生成的索引
│   │   ├── ocr/                 #     OCR 输出
│   │   │   └── <zotero_key>/    #       fulltext.md + images/
│   │   ├── search/              #     搜索任务
│   │   │   ├── tasks/           #       搜索配置
│   │   │   └── results/         #       结果缓存
│   │   ├── skill-prototypes/    #     技能原型
│   │   ├── writeback/           #     回写队列和日志
│   │   └── worker/              #     Worker 脚本
│   │       ├── scripts/         #       literature_pipeline.py
│   │       └── tests/           #       测试文件
│   ├── Template/                #   模板
│   │   ├── 文献阅读.md          #     文献笔记模板
│   │   ├── 科研读图指南.md      #     主读图指南
│   │   └── 读图指南/            #     14 个子指南
│   └── Zotero/                  #   Zotero 软链接
│       └── zotero.sqlite        #     通过 junction 链接
├── AGENTS.md                    # [PaperForge 生成]
└── .env                         # [PaperForge 生成]
```

---

## 5. 总结

PaperForge 的 setup.py 有多项与实际工作流不符的配置：

1. **最严重**：创建了用户的 PARA 文件夹（00_Inbox 等），这会导致：
   - 如果用户已有这些文件夹，可能引起困惑
   - 如果用户使用不同的 PARA 命名，会造成不匹配
   - 违反了"PaperForge 只管理自己的目录"原则

2. **关键缺失**：没有创建管道运行必需的目录（candidates/, search/, indexes/, writeback/, LiteratureControl/），这会导致 worker 运行时因目录不存在而失败。

3. **小问题**：AGENTS.md 重复写入、命令引用过于特定、配置保存不完整。

**建议立即修复 P0 和 P1 级别的问题。**
