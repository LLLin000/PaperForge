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
skill_version: 2026-07-27.1
skill_api_version: 2
---
# PaperForge — Research Memory Runtime

PaperForge 将文献、阅读痕迹、工作过程、方法论和产物
组织成可检索、可复核、可由 agent 调用的研究记忆。

**触发原则：只要用户意图涉及以下任一类，必须调用 paperforge skill：**

- 文献库 / vault 中的论文检索、collection / domain 盘点
- 已知论文的定位、阅读、问答、/pf-paper
- 正文内容、术语、参数、方法、支持证据的查找
- 单篇论文精读、/pf-deep
- PaperForge 阅读笔记、项目日志、方法论卡片保存

---

## 1. 一键状态交接（State-Machine Handoff — 必须最先执行）

不要分三步跑慢速脚本。直接从 PaperForge Rust 状态机一次性领取运行路径、库概览、collection 树、实时后台作业、可用能力与高优先级提醒：

- **首选（MCP 已接入时，0 转义 / `<5ms`）**：直接调用 **`paperforge_brief`**（如已锁定单篇论文，可传 `paper_key`）。
- **回退 A（原生二进制 CLI）**：
  ```bash
  ~/.paperforge/bin/paperforge-daemon agent-brief --vault "$VAULT" --json
  ```
- **回退 B（无二进制时的 Python 兜底）**：按顺序执行 `python $SKILL_DIR/scripts/pf_bootstrap.py --vault "$VAULT"` → `$PYTHON -m paperforge --vault "$VAULT" agent-context --json` → `$PYTHON -m paperforge --vault "$VAULT" runtime-health --json`。

拿到交接结果后记录变量：`$VAULT = data.vault.root`、`$PYTHON = data.runtime.python_exe`、`$LIT_DIR = data.vault.paths.literature`、`$METHODS = data.methodology_index`。

## 1a. Pre-flight Checklist（强制门禁）

**进入任何 molecule 之前，必须核对以下事项：**

- [ ] **handoff completed**：已通过 `paperforge_brief`（或回退链）拿到 `data.capabilities` 与 `data.hints`
- [ ] **respect blocked_actions & hints**：
  - `capabilities.safe_read == false`：禁止路由到 discover-papers、read-known-paper、deep-analyze-paper
  - `capabilities.safe_write == false`：禁止路由到任何日志/记忆/批注写入操作
  - `hints` 中存在 `blocker` 或 `repair_command`（如 `job.ocr.running` / `paper.not_ocr_ready`）：严格遵守提醒，必要时优先把 `repair_command` 返回给用户
- [ ] **intent identified**：用户意图已映射到一个顶层 research intent
- [ ] **molecule selected**：已路由到对应的 `molecules/<intent>.md`

> **检索路由原则**：执行语义和 fallback 规则以 `atoms/retrieval-routing.md` 为准；MCP 可用时优先使用 `paperforge_search` / `paperforge_retrieve` / `paperforge_library_query`，无结果时再按 fallback 梯队降级。

## 4. 意图路由

用户输入按以下顺序判定并路由到 molecule。

### A. 机械命令（不经过 research intent routing）

| 用户说        | 动作                                                       |
| ------------- | ---------------------------------------------------------- |
| `/pf-sync`    | 执行 `paperforge sync`，解释结果                           |
| `/pf-ocr`     | 执行 `paperforge ocr`，解释结果                            |
| `/pf-status`  | 执行 `paperforge status --json` 或 `runtime-health --json` |

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
2. 重新打开**原文/图表/表格**，核实之前的解读
3. 确认的，说明"已回原文复核"
4. 被推翻的，创建 correction note
5. **绝对禁止**仅根据 reading-log 内容回答事实性问题

---

## 6. 全局禁止规则

- **禁止自行拼接文件路径**。所有路径从 bootstrap 或 paper-context 获取。
- **禁止绕过 CLI 直接操作文件**。搜索用 `$PYTHON -m paperforge search`，不用 glob/grep 扫库。
- **禁止在未完成 paper-context 检查前读取原文**（适用于 read-known-paper、deep-analyze-paper）。

---

## 文件结构

```
paperforge/skills/paperforge/
├── SKILL.md              ← 本文件（compound：启动注入 + 路由 + 全局规则）
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
