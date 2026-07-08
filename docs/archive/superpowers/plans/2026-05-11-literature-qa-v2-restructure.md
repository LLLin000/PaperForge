# Literature-QA Skill v2 Restructuring Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure literature-qa skill so that SKILL.md is the single hub containing bootstrap, decision tree, and tool usage guidelines. Reference files become pure workflow instructions. Add multi-reading workflow. Remove unused routes.

**Architecture:** SKILL.md = bootstrap + overview + decision tree + tool rules + routing table. Each reference file = one workflow (no path discovery, no Python discovery). All `$PYTHON`/`$VAULT` context inherited from SKILL.md.

**Tech Stack:** Markdown, Python (pf_bootstrap.py, ld_deep.py)

---

## File Changes

| File | Action | Responsibility |
|------|--------|---------------|
| `SKILL.md` | **Rewrite** | Bootstrap, vault overview, decision tree, tool guidelines, routing table |
| `references/vault-knowledge.md` | **Delete** | Merged into SKILL.md |
| `references/multi-reading.md` | **Create** | Batch reading workflow with reading log |
| `references/paper-search.md` | **Simplify** | Remove `$PYTHON`/`$VAULT` preamble (inherited) |
| `references/paper-qa.md` | **Simplify** | Remove `$PYTHON`/`$VAULT` preamble |
| `references/deep-reading.md` | **Simplify** | Remove `$PYTHON`/`$VAULT` preamble; remove "精读队列" variant |
| `references/save-session.md` | **Simplify** | Remove `$PYTHON`/`$VAULT` preamble |
| `references/paper-resolution.md` | **Simplify** | Remove `$PYTHON`/`$VAULT` preamble, just the protocol |

---

## Task Breakdown

### Task 1: Rewrite SKILL.md

**Files:**
- Rewrite: `paperforge/skills/literature-qa/SKILL.md`

**New structure:**

```markdown
---
name: literature-qa
description: >
  学术文献库操作。Triggered by: /pf-deep /pf-paper /pf-end,
  "精读", "文献问答", "结束讨论", "找文献", "搜文献",
  "文献库", "文献检索", "精读队列", "库里有什么",
  "搜一下库里", "看一下文献库".
---

# Literature QA

---

## 1. Bootstrap — 进入本 Skill 后必须先执行

跑这个脚本，拿到所有你需要的信息：

```
python <skill_dir>/scripts/pf_bootstrap.py
```

返回 JSON 记住以下变量：

| 变量       | 来源                  | 示例值                                                    |
| ---------- | --------------------- | --------------------------------------------------------- |
| `$VAULT`     | `vault_root`            | `D:\L\OB\Literature-hub`                                    |
| `$PYTHON`    | `python_candidate`      | `D:\L\OB\Literature-hub\.venv\Scripts\python.exe`           |
| `$LIT_DIR`   | `paths.literature_dir`  | `D:\L\OB\Literature-hub\Resources\Literature`               |
| `$IDX_PATH`  | `paths.index_path`      | `D:\L\OB\Literature-hub\System\PaperForge\indexes\formal-library.json` |
| `$OCR_DIR`   | `paths.ocr_dir`         | `D:\L\OB\Literature-hub\System\PaperForge\ocr`              |
| `$DOMAINS`   | `domains`               | `["骨科", "运动医学"]`                                      |
| `$SUMMARY`   | `index_summary`         | `{"骨科": 550, "运动医学": 263}`                             |

如果 `ok: false`，报告 `error` 给用户，**停止。不要自己猜任何路径。**

---

## 2. Vault 概览 — 直接展示

```
当前 Vault: $VAULT
文献库概况:
  骨科 — 550 篇
  运动医学 — 263 篇
共 813 篇
```

---

## 3. 决策树 — Agent 如何判断用户要干什么

```
用户输入
  │
  ├─ "看一下库"/"浏览文献"/"库里有什么"
  │   └─ 上面已经展示了。等用户下一步。
  │
  ├─ 给出文献标识 (key/DOI/标题/作者年份) + 想精读
  │   └─ 路由 → deep-reading.md
  │
  ├─ 给出文献标识 (key/DOI/标题/作者年份) + 想问答/讨论
  │   └─ 路由 → paper-qa.md
  │
  ├─ 搜索文献 ("找文献"/"搜文献"/"库里有没有XXX"/"文献检索")
  │   └─ 路由 → paper-search.md
  │
  ├─ 批量阅读/综述整理
  │   触发词: "读一下这个collection", "帮我看一下这方向的文章",
  │           "总结一下库里关于XXX的文献", "写一段文献综述",
  │           用户给了多篇文献要求一起读
  │   └─ 路由 → multi-reading.md
  │
  ├─ "结束"/"保存"/"/pf-end"
  │   └─ 路由 → save-session.md
  │       (仅 paper-qa 或 deep-reading 会话中有效)
  │
  └─ 不确定 → 问用户："你是想精读一篇、搜索文献、还是批量阅读？"
```

---

## 4. 工具使用指南

**什么时候用命令（paper_resolver / ld_deep 等）：**

| 场景                  | 命令                                                         | 原因                        |
| --------------------- | ------------------------------------------------------------ | --------------------------- |
| 定位论文（按 key）    | `$PYTHON -m paperforge.worker.paper_resolver resolve-key <KEY> --vault "$VAULT"` | 确定性匹配，返回 workspace 路径 |
| 定位论文（按 DOI）    | `$PYTHON -m paperforge.worker.paper_resolver resolve-doi "<DOI>" --vault "$VAULT"` | 同上                        |
| 搜索论文（结构化）    | `$PYTHON -m paperforge.worker.paper_resolver search --title "..." --domain "..." --vault "$VAULT"` | 返回结构化 JSON，含相关性打分 |
| 精读 prepare/校验     | `$PYTHON "$SKILL_DIR/scripts/ld_deep.py" prepare --key <KEY> --vault "$VAULT"` | 机械操作，Agent 不做         |
| 保存讨论              | `$PYTHON -m paperforge.worker.discussion record <KEY> --vault "$VAULT" --agent pf-paper --model "<MODEL>" --qa-pairs '...'` | 写入 discussion.md/json      |

**什么时候自己 grep/glob/read：**

| 场景                    | 操作                                                    | 原因                       |
| ----------------------- | ------------------------------------------------------- | -------------------------- |
| 按关键词在全部文献里搜 | `grep <关键词> $IDX_PATH` 或读 JSON 筛 `title`/`abstract` | 模糊搜索，paper_resolver 不够 |
| 读论文全文/精读笔记    | 直接 read `$LIT_DIR/<domain>/<key> - <title>/fulltext.md` | 收到 resolve-key 返回的路径后直接读 |
| 按 collection 筛选       | 读 `$IDX_PATH`，筛 `collection_path` 字段                 | paper_resolver 不支持 collection |
| 遍历所有笔记做统计      | `rg <pattern> $LIT_DIR/ --include '*.md'`               | 批量操作                   |

---

## 5. 路由表

| 路由         | 触发词                                     | 加载文件                                 |
| ------------ | ------------------------------------------ | ---------------------------------------- |
| 精读         | `/pf-deep <key>`, "精读 <key>"              | [deep-reading.md](references/deep-reading.md) |
| 问答         | `/pf-paper <key>`, "文献问答 <key>"         | [paper-qa.md](references/paper-qa.md)       |
| 文献检索     | "找文献", "搜文献", "文献检索", "搜一下库里"  | [paper-search.md](references/paper-search.md) |
| 批量阅读     | "读一下collection", "这篇方向", "总结文献"   | [multi-reading.md](references/multi-reading.md) |
| 保存记录     | `/pf-end`, "结束讨论", "保存"               | [save-session.md](references/save-session.md) |
| 论文定位协议 | 共享                                       | [paper-resolution.md](references/paper-resolution.md) |

---

## 文件结构

```
literature-qa/
├── SKILL.md
├── references/
│   ├── deep-reading.md
│   ├── paper-qa.md
│   ├── paper-search.md
│   ├── multi-reading.md       ← NEW
│   ├── save-session.md
│   ├── paper-resolution.md
│   └── chart-reading/
└── scripts/
    ├── pf_bootstrap.py
    └── ld_deep.py
```
```

- [ ] **Step 1: Write the new SKILL.md**
- [ ] **Step 2: Run a syntax check (it's markdown, read it back for typos)**
- [ ] **Step 3: Commit**

```bash
git add paperforge/skills/literature-qa/SKILL.md
git commit -m "feat: restructure SKILL.md as central hub with decision tree and tool guidelines"
```

---

### Task 2: Delete vault-knowledge.md

**Files:**
- Delete: `paperforge/skills/literature-qa/references/vault-knowledge.md`

Content merged into SKILL.md sections 1+2+3+4.

- [ ] **Step 1: Delete the file**
- [ ] **Step 2: Commit**

```bash
git rm paperforge/skills/literature-qa/references/vault-knowledge.md
git commit -m "refactor: remove vault-knowledge.md (merged into SKILL.md)"
```

---

### Task 3: Create multi-reading.md

**Files:**
- Create: `paperforge/skills/literature-qa/references/multi-reading.md`

**Content:**

```markdown
# 批量文献阅读

用户需要阅读多篇文献并总结——综述写作、找引用、研究方向调研等。

---

## 触发条件

- 用户给了一个 collection 名（Zotero 收藏夹）
- 用户给了模糊方向（"帮我看一下骨科里关于支架材料的文章"）
- 用户给了一个多篇文献阅读任务（"读一下这几篇写一段综述"）
- 用户说"总结库里XXX方向的文献"

---

## 执行流程

### Step 1: 确定文献范围

先和用户确认要读哪些文献：
- 如果用户给了 collection 名 → 读 `$IDX_PATH`，筛 `collection_path` 包含该名称的条目
- 如果用户给了关键词 → 用 paper_resolver search 或直接 grep `$IDX_PATH`
- 如果用户给了多篇 key → 直接确认 key 列表

列出候选文献清单让用户确认：

```
找到 N 篇匹配：collection = "自发电"

[1] ABC12345 — Piezoelectric Scaffolds for Cartilage (2024)
[2] DEF67890 — Triboelectric Nanogenerators (2023)
...

要全部读，还是选几篇？(输入编号如 "1,3,5" 或 "all")
```

### Step 2: 逐篇阅读

对每篇选定的文献：
1. 运行 `$PYTHON -m paperforge.worker.paper_resolver resolve-key <KEY> --vault "$VAULT"` 获取 workspace 路径
2. 读 formal note 的 frontmatter 了解元数据
3. 如果有 fulltext.md → 读关键段落（Abstract、Results、Discussion）
4. 如果没有 fulltext → 只能基于已知信息

### Step 3: 生成 Reading Log

每篇读完后立即在 `$VAULT/Bases/` 下生成 `reading-log-<timestamp>.md` 文件（追加模式，不要覆盖之前的记录）：

```markdown
# Reading Log — <timestamp>

## [KEY] <title> (作者, 年份, 期刊)

- **核心发现**: <一句话>
- **方法**: <实验设计简述>
- **关键数据**: <主要结果>
- **与主题相关性**: <为什么对当前任务有用>
- **引用值**: <适合引什么→什么结论>
```

### Step 4: 整合输出

全部读完，根据用户原始意图输出：

**如果是综述写作**：
```
从 N 篇文献中总结：
- 主题A 的共识: ...
- 主题A 的争议: ...
- 方法论趋势: ...
- 可引用的关键结论及其文献来源:
  1. "...[结论]" — [KEY] (作者, 年份)
  2. ...
```

**如果是找引用**：
```
以下文献适合引用：
- 支撑"XXX"观点 → [KEY] (作者, 年份), Fig.3
- 支撑"YYY"方法 → [KEY] (作者, 年份), Methods section
```

### Step 5: 问用户

问用户：
- "Reading log 已保存到 `Bases/reading-log-<ts>.md`。需要我把总结写到哪里？"
- 用户可以指定目标文件路径

---

## 注意事项

- Reading log **追加**写入同一个文件（同一次多篇阅读任务），不要每篇新建一个
- 暂时不支持多篇阅读后运行 /pf-end
- 如果某篇文献没有 fulltext，如实告知用户
```

- [ ] **Step 1: Write the file**
- [ ] **Step 2: Commit**

```bash
git add paperforge/skills/literature-qa/references/multi-reading.md
git commit -m "feat: add multi-reading workflow with reading log"
```

---

### Task 4: Simplify reference files (remove $PYTHON/$VAULT preamble)

**Files:**
- Modify: `references/deep-reading.md` — remove preamble, remove "精读队列" variant
- Modify: `references/paper-qa.md` — remove preamble
- Modify: `references/paper-search.md` — remove preamble
- Modify: `references/save-session.md` — remove preamble
- Modify: `references/paper-resolution.md` — remove preamble

Each file's preamble like:
```markdown
**所有 Python 命令用 `$PYTHON`（来自 pf_bootstrap 的 `python_candidate`），vault 路径用 `$VAULT`。**
```
→ **Delete**. The variables are now inherited from SKILL.md.

- [ ] **Step 1: Strip preamble from all 5 files**
- [ ] **Step 2: In deep-reading.md, remove the "精读队列" variant (line references to `/pf-deep` without args)**
- [ ] **Step 3: Commit**

```bash
git add paperforge/skills/literature-qa/references/
git commit -m "refactor: simplify reference files — remove $PYTHON/$VAULT preamble (inherited), drop unused route"
```

---

### Task 5: Integration Check

- [ ] **Step 1: Read all files end-to-end, verify no broken references**
- [ ] **Step 2: Verify SKILL.md routing table links are all valid**
- [ ] **Step 3: Run bootstrap script to verify it still works**

```bash
python paperforge/skills/literature-qa/scripts/pf_bootstrap.py --vault "D:\L\OB\Literature-hub"
```

Expected: `"ok": true` with domains and index summary.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: integration check — all routes verified"
```

---

## Rollback Plan

1. Restore `vault-knowledge.md` from git history
2. Revert `SKILL.md` to pre-restructure version
3. Revert reference file preambles

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|-----------|
| Agent confused by missing vault-knowledge.md | Low | All info now in SKILL.md sections 1-4 |
| multi-reading generates too large reading logs | Low | Append mode; user asked before saving final output |
| "精读队列" still in ld_deep.py code | Low | Skill just removes the routing trigger; code stays |
