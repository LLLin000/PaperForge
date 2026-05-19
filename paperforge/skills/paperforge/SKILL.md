---
name: paperforge
description: >
  Research Memory Runtime — 文献搜索、精读、问答、阅读笔记、
  工作记录、方法论提取。Triggered by:
  pf-deep pf-paper pf-sync pf-ocr pf-status,
  "精读" "找文献" "搜文献" "文献问答" "读一下" "看看这篇"
  "讨论" "记录阅读" "记录工作" "总结会话" "提取方法论"
  "记一下" "保存这次" "找证据" "找75 Hz" "找支持" "collection" "库里".
source: paperforge
---

# PaperForge — Research Memory Runtime

PaperForge 将文献、阅读痕迹、工作过程、方法论和产物
组织成可检索、可复核、可由 agent 调用的研究记忆。

---

## 1. Bootstrap — 必须先执行

```bash
python $SKILL_DIR/scripts/pf_bootstrap.py --vault "$VAULT"
```

返回 JSON。记录以下变量（所有 molecule 文件继承，不再重复声明）：

| 变量          | JSON 字段               | 用途                           |
| ------------- | ----------------------- | ------------------------------ |
| `$VAULT`      | `vault_root`            | 所有 `--vault` 参数            |
| `$PYTHON`     | `python_candidate`      | 所有 `python -m paperforge` 调用 |
| `$LIT_DIR`    | `paths.literature_dir`  | 文献笔记根目录                 |
| `$SKILL_DIR`  | 平台注入                | 脚本路径                       |
| `$METHODS`    | `methodology_index`     | 可用方法论索引                 |

如果 `ok: false`，报告 `error` 给用户，**停止。禁止自己拼路径。**

如果 `python_verified` 为 `false` 或 `python_candidate` 为 `null`：
依次尝试 `python` 再 `python3`。全部失败则停止，提示用户在 `paperforge.json` 中设置 `python_path`。

bootstrap 现在也返回一个 `capabilities` 块（rg, semantic, metadata 等）。

## 1a. Pre-flight Checklist

**进入任何 molecule 之前，必须完成以下检查。标记为 `[x]` 后才可前进。**

- [ ] **bootstrap completed**：`$VAULT`、`$PYTHON`、`$LIT_DIR`、`$SKILL_DIR` 已定义
- [ ] **capabilities**：已读取 `capabilities` 块中的 `rg`、`metadata_search`、`paper_context`、`semantic_enabled`、`semantic_ready`
- [ ] **runtime-health passed**：`safe_read`、`safe_write` 已知，vector 状态已知
- [ ] **intent identified**：用户意图已映射到一个顶层 research intent
- [ ] **molecule selected**：已路由到对应的 `molecules/<intent>.md`

如果任一检查未通过，先执行对应的步骤，**不跳过**。

---

## 2. Agent Context — bootstrap 成功后执行

```bash
$PYTHON -m paperforge --vault "$VAULT" agent-context --json
```

返回 library overview、collection tree、可用命令和规则。Agent 注入为会话上下文。

---

## 3. Runtime Health — compound 启动原子

在 compound 启动链中，只执行一次：

```text
bootstrap -> agent-context -> runtime-health -> route -> molecule
```

执行命令：

```bash
$PYTHON -m paperforge --vault "$VAULT" runtime-health --json
```

检查返回 JSON：

- `data.summary.safe_read == false`：禁止路由到 discover-papers、read-known-paper、deep-analyze-paper
- `data.summary.safe_write == false`：禁止路由到 write-reading-log-jsonl、write-project-reading-log、write-project-log
- `data.layers.vector.status != "ok"`：禁止把 semantic retrieve 当主路径，必要时退回 FTS / paper-context / fulltext
- `data.layers.*.repair_command` 存在时，优先把该命令作为修复建议返回给用户

一旦 runtime-health 通过，后续 molecule 继承该状态，**不要在每个 molecule 里重复跑 preflight**。

Dashboard 的 `System Status` 只是这个 contract 的薄展示，不是第二套真相源。

---

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
2. **`read_known_paper`** — 用户给定了明确的 paper（key/DOI/标题）
3. **`discover_papers`** — 用户要找一批论文（"找XX的文章"、"collection里有什么"）
4. **`find_supporting_evidence`** — 用户要找具体证据/参数/术语（"找75 Hz"、"找支持这句话的依据"）
5. **`deep_analyze_paper`** — 用户明确要精读（"/pf-deep"）

**判定顺序（必须严格按此顺序执行）：**

```text
0. 处理机械命令（A 节）
1. 处理别名（B 节）→ deep_analyze_paper / read_known_paper
2. 如果用户要求保存/归档/从上下文提取 → capture_project_knowledge
3. 如果用户已指向单一论文 → read_known_paper
4. 如果用户想要论文列表 → discover_papers
5. 如果用户想要证据/支持 → find_supporting_evidence
6. 如果意图无法判定 → 打开 atoms/clarify-user-intent.md
   注意：如果多个 intent 同时匹配（如"找这篇的证据然后保存"），**除非某个 intent 明显主导**，否则也走 clarify；不要硬猜。
7. post-action：molecule 输出后，如果用户要求保存 → capture_project_knowledge
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
│   ├── discover-papers.md
│   ├── find-supporting-evidence.md
│   ├── deep-analyze-paper.md
│   └── capture-project-knowledge.md
├── atoms/                ← 可复用子步骤
│   ├── clarify-user-intent.md
│   ├── retrieval-routing.md
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
