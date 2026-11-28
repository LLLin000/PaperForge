---
name: paperforge
description: >
  Research Memory Runtime — 文献搜索、精读、PDF 批注、问答、阅读笔记、
  工作记录、方法论提取。Triggered by:
  pf-deep pf-paper pf-sync pf-ocr pf-status,
  "精读" "批注" "标注 PDF" "找文献" "搜文献" "文献问答" "读一下" "看看这篇"
  "讨论" "记录阅读" "记录工作" "总结会话" "提取方法论"
  "记一下" "保存这次" "找证据" "找75 Hz" "找支持" "collection" "库里".
source: paperforge
skill_version: 2026-11-28.1
skill_api_version: 3
---
# PaperForge — Research Memory Runtime

PaperForge 将文献、阅读痕迹、工作过程、方法论和产物
组织成可检索、可复核、可由 agent 调用的研究记忆。

**触发原则：只要用户意图涉及以下任一类，必须调用 paperforge skill：**

- 文献库 / vault 中的论文检索、collection / domain 盘点
- 已知论文的定位、阅读、问答、/pf-paper
- 正文内容、术语、参数、方法、支持证据的查找
- 单篇论文精读、/pf-deep
- PaperForge 阅读笔记、项目日志、方法论卡片保存、PDF 批注

---

## 1. MCP-First 工作流（首选入口 — 零引号转义问题）

**第一步始终直接调用 `paperforge_brief`**（如已锁定单篇论文，传入 `paper_key`），一次性获取库路径、能力状态、活跃作业与高优先级提示。

核心 MCP 工具全集（11 个）：

| 类别 | MCP 工具 | 用途 |
|---|---|---|
| 交接与盘点 | `paperforge_brief` / `paperforge_library_query` | 会话交接、按 domain/collection/status 分页盘点 |
| 检索与定位 | `paperforge_search` / `paperforge_retrieve` | 元数据 FTS5 检索与全库正文/向量检索（`deep=true` 强制 BM25） |
| 读论文 | `paperforge_paper_context` / `paperforge_read_paper` | 单篇上下文/批注/记忆卡片；**无论是否完成 OCR** 均可分页读取原文（`pages="1-3"`） |
| 批注读写 | `paperforge_annotate_batch` / `paperforge_annotations` | 原子提交 AI 批注（支持 OCR 与无 OCR 原生 PDF）；`list` / `adopt` / `clear_agent` / `delete` |
| 记忆与日志 | `paperforge_memory_refine` / `paperforge_log_write` | 演化 Living Paper Memory Card；写入 `reading_log` / `project_log` / `methodology` |
| 流水线作业 | `paperforge_job` | 查询或触发 `status` / `ocr`（按 keys/collection/domain/dry_run）/ `embed` / `sync` / `reconcile` |

> **CLI 回退（仅在无 MCP 的纯终端环境使用）**：`paperforge-daemon agent-brief --vault "$VAULT" --json` 或 `python -m paperforge --vault "$VAULT" <command> --json`；在 Windows PowerShell 传中文/多行 JSON 时优先使用 `--input <file>` 或 stdin `--input -`，避免引号转义损坏。

## 1a. Pre-flight Checklist（强制门禁）

**进入任何 molecule 之前，必须核对以下事项：**

- [ ] **handoff completed**：已通过 `paperforge_brief` 拿到 `data.capabilities` 与 `data.hints`
- [ ] **respect blocked_actions & hints**：
  - `capabilities.safe_read == false`：禁止路由到 discover-papers、read-known-paper、deep-analyze-paper
  - `capabilities.safe_write == false`：禁止路由到任何日志/记忆/批注写入操作
  - 有 `has_pdf == true` 的论文**无需等待 OCR**：可直接调用 `paperforge_read_paper` 分页读取原生 PDF 文本，并用 `paperforge_annotate_batch` 完成定位批注；仅当 `has_pdf == false` 时才禁止 PDF 批注
  - 若 `hints` 中存在正在执行的作业（如 `job.ocr.running` / `job.sync.running`），避免重复触发同类作业
- [ ] **intent identified**：用户意图已映射到一个顶层 research intent
- [ ] **molecule selected**：已路由到对应的 `molecules/<intent>.md`

> **检索路由原则**：执行语义和 fallback 规则以 `atoms/retrieval-routing.md` 为准；MCP 优先使用 `paperforge_search` / `paperforge_retrieve` / `paperforge_library_query`；若使用 CLI `query-plan`，统一使用 `--intent <locate|discover|content>`（`known-paper` 为 `locate` 的别名）。

## 4. 意图路由

用户输入按以下顺序判定并路由到 molecule。

### A. 机械命令（不经过 research intent routing）

| 用户说        | 动作                                                       |
| ------------- | ---------------------------------------------------------- |
| `/pf-sync`    | 调用 `paperforge_job(action="sync")`（CLI 回退 `paperforge sync --json`），解释结果 |
| `/pf-ocr`     | 调用 `paperforge_job(action="ocr", ...)`（CLI 回退 `paperforge ocr --json`），解释结果 |
| `/pf-status`  | 调用 `paperforge_job(action="status")` 或 `paperforge_brief`（CLI 回退 `paperforge status --json` / `runtime-health --json`） |

### B. 研究命令别名

| 用户说      | 路由到的 intent              |
| ----------- | ---------------------------- |
| `/pf-deep`  | `deep_analyze_paper`         |
| `/pf-paper` | `read_known_paper`           |

### C. 顶层研究意图（按判定顺序）

1. **`capture_project_knowledge`** — 直接保存/归档/提取（用户说"记一下"、"保存这次"、"提取方法论"）
2. **`annotate_paper_pdf`** — 用户明确要求给某篇论文做 PDF 批注 / 领读标注（"批注这篇"、"在 PDF 上标出逻辑链/实验参数/硬伤"、`molecules/annotate-paper-pdf.md`）
3. **`deep_analyze_paper`** — 用户明确要求精读（出现"精读"、"深度分析"、"完整分析"、"Keshav"等动作词时，优先于普通问答）
4. **`synthesize_evidence_matrix`** — 用户要求横向对比多篇文献、归纳参数窗或生成证据矩阵（"横向对比"、"证据矩阵"、"compare papers"）
5. **`read_known_paper`** — 用户给定了明确的 paper（key/DOI/标题），但未要求精读
6. **`discover_papers`** — 用户要找一批论文（"找XX的文章"、"collection里有什么"）
7. **`find_supporting_evidence`** — 用户要找具体证据/参数/术语（"找75 Hz"、"找支持这句话的依据"）

**判定顺序（必须严格按此顺序执行）：**

```text
0. 处理机械命令（A 节）
1. 处理别名（B 节）→ deep_analyze_paper / read_known_paper
2. 如果用户要求保存/归档/从上下文提取 → capture_project_knowledge
3. 如果用户明确要求对论文 PDF 划线/打批注 → annotate_paper_pdf
4. 如果用户明确要求精读（含"精读"、"深度分析"、"Keshav"等词）→ deep_analyze_paper
5. 如果用户已指向单一论文但未要求精读 → read_known_paper
6. 如果用户想要论文列表 → discover_papers
7. 如果用户想要证据/支持 → find_supporting_evidence
8. 如果意图无法判定 → 打开 atoms/clarify-user-intent.md
   注意：如果多个 intent 同时匹配（如"找这篇的证据然后保存"），**除非某个 intent 明显主导**，否则也走 clarify；不要硬猜。
9. post-action：molecule 输出后，如果用户要求保存 → capture_project_knowledge
```

### D. Clarify 回退

- 不能稳定判定 intent 时，打开 `atoms/clarify-user-intent.md`
- 最多两轮

未知或拼错的 `/pf-*` 命令不要静默掉进 `project-engineering`，必须明确提示用户命令不存在或请澄清意图。

---

## 5. Reading-Log Safety Rule — 全局规则，所有 workflow 必须遵守

Reading-log 不是事实源。它记录的是**之前的关注点、解读和预期用途**。

当存在 prior reading-log 时：
1. 用它决定**优先复查什么**，不是用它回答用户问题
2. 重新打开**原文/图表/表格**（通过 `paperforge_read_paper` 或 `paperforge_retrieve`），核实之前的解读
3. 确认的，说明"已回原文复核"
4. 被推翻的，创建 correction note
5. **绝对禁止**仅根据 reading-log 内容回答事实性问题

---

## 6. 全局禁止规则

- **禁止自行拼接文件路径**。所有读取、批注与写入通过 MCP 工具或 PaperForge CLI 完成。
- **禁止绕过工具直接扫描库文件**。检索用 `paperforge_search` / `paperforge_retrieve`，不用 glob/grep 扫库。
- **禁止在未查看 `paperforge_paper_context`（或 `paperforge_brief(paper_key=...)`）前对已知论文下结论**。

---

## 文件结构

```
paperforge/skills/paperforge/
├── SKILL.md              ← 本文件（compound：MCP-First 路由 + 全局规则）
├── molecules/            ← 1 molecule = 1 intent 的完整执行流程
│   ├── read-known-paper.md
│   ├── annotate-paper-pdf.md
│   ├── discover-papers.md
│   ├── find-supporting-evidence.md
│   ├── deep-analyze-paper.md
│   ├── synthesize-evidence-matrix.md
│   └── capture-project-knowledge.md
├── atoms/                ← 可复用子步骤
│   ├── clarify-user-intent.md
│   ├── retrieval-routing.md
│   ├── update-paper-memory.md
│   ├── write-reading-log-jsonl.md
│   ├── write-project-reading-log.md
│   ├── write-project-log.md
│   ├── extract-methodology-card.md
│   └── chart-reading/
├── scripts/
│   ├── pf_bootstrap.py
│   └── pf_deep.py
└── workflows/
    └── project-engineering.md
```
