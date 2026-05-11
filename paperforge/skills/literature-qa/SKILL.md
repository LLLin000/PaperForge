---
name: literature-qa
description: >
  学术文献库操作：精读、问答、检索、批量阅读。Triggered by:
  pf-deep pf-paper pf-end,
  "精读", "文献问答", "结束讨论", "找文献", "搜文献",
  "文献库", "文献检索", "库里有什么", "搜一下库里", "看一下文献库",
  "读一下collection", "总结文献", "批量阅读", "读一下这个方向".
---

# Literature QA

---

## 1. Bootstrap — 必须先执行

跑这个脚本：

```
python $SKILL_DIR/scripts/pf_bootstrap.py
```

返回 JSON。记住以下变量：

| 变量        | 来自 JSON 的         | 用于                                    |
| ----------- | -------------------- | --------------------------------------- |
| `$SKILL_DIR`  | skill 安装路径（平台注入） | 运行 `scripts/ld_deep.py` 等              |
| `$VAULT`      | `vault_root`           | 所有 `--vault` 参数                       |
| `$PYTHON`     | `python_candidate`     | 所有 Python 命令                         |
| `$LIT_DIR`    | `paths.literature_dir` | 文献笔记根目录                          |
| `$IDX_PATH`   | `paths.index_path`     | 索引文件                                |
| `$OCR_DIR`    | `paths.ocr_dir`        | OCR 目录                                |
| `$DOMAINS`    | `domains`              | 领域列表                                |
| `$SUMMARY`    | `index_summary`        | 每领域论文数                            |

如果 `ok: false` → 报告 `error` 给用户，**停止。不许自己拼路径。**

---

## 2. Vault 概览

展示：

```
Vault: $VAULT
文献库:
  <domain1> — N1 篇
  <domain2> — N2 篇
共 M 篇
```

**如果用户是空输入触发的 skill**（没给任何具体指令），展示概览后加一句交互：

```
你可以：
  [1] 精读一篇论文   → "精读 <key/标题>"
  [2] 文献问答       → "文献问答 <key/标题>"
  [3] 搜索文献       → "找文献 <关键词>" / "库里有没有 <关键词>"
  [4] 批量阅读       → "读一下 <collection名>" / "总结 <方向> 文献"
  [5] 返回
```

**如果用户给了具体指令**，直接进入决策树。

---

## 3. 决策树

```
用户输入
  │
  ├─ 文献标识 (key/DOI/标题/作者年份) + 精读意图
  │   └─ 路由 → deep-reading.md
  │
  ├─ 文献标识 (key/DOI/标题/作者年份) + 问答/讨论意图
  │   └─ 路由 → paper-qa.md
  │
  ├─ 搜索意图 ("找文献"/"搜文献"/"库里有没有"/"文献检索")
  │   └─ 路由 → paper-search.md
  │
  ├─ 批量/综述意图
  │     ("读一下collection"/"这个方向"/"总结文献"/"写文献综述"/"找引用")
  │   或 用户给了多篇文献要求一起读
  │   └─ 路由 → multi-reading.md
  │
  ├─ 结束/保存 ("结束讨论"/"保存"/"pf-end")
  │   └─ 路由 → save-session.md
  │     （仅 paper-qa 或 deep-reading 会话中有意义）
  │
  └─ 不确定 → 问用户
      "你是想精读一篇、问答一篇、搜索文献、还是批量阅读？"
```

---

## 4. 工具使用指南

本 Skill 提供两类工具：**确定性命令** 和 **Agent 自查**。必须根据场景选择正确的方式。

### 确定性命令 — 优先使用

| 场景                   | 命令                                                                                       | 原因 |
| ---------------------- | ------------------------------------------------------------------------------------------ | ---- |
| 按 key 快速找文件       | `glob("$LIT_DIR/**/<KEY>.md")` 或用 `Get-ChildItem "$LIT_DIR" -Recurse -Filter "<KEY>.md"` | 不需要 $PYTHON，最快 |
| 按 key 查完整信息       | `$PYTHON -m paperforge.worker.paper_resolver resolve-key <KEY> --vault "$VAULT"`             | 返回 frontmatter 字段 (analyze, ocr_status 等) |
| 按 DOI 定位论文        | `$PYTHON -m paperforge.worker.paper_resolver resolve-doi "<DOI>" --vault "$VAULT"`           | DOI 无法用文件系统快速匹配 |
| 按字段搜索论文         | `$PYTHON -m paperforge.worker.paper_resolver search --title "..." --author "..." --year ... --domain "..." --vault "$VAULT"` | 结构化搜索，含相关性打分 |
| 精读 prepare           | `$PYTHON "$SKILL_DIR/scripts/ld_deep.py" prepare --key <KEY> --vault "$VAULT"`               |
| 精读 postprocess       | `$PYTHON "$SKILL_DIR/scripts/ld_deep.py" postprocess-pass2 <FORMAL_NOTE_PATH> --figures <N> --vault "$VAULT"` |
| 精读 validate          | `$PYTHON "$SKILL_DIR/scripts/ld_deep.py" validate-note <FORMAL_NOTE_PATH> --fulltext <FULLTEXT_PATH>` |
| 保存讨论               | `$PYTHON -m paperforge.worker.discussion record <KEY> --vault "$VAULT" --agent pf-paper --model "<MODEL>" --qa-pairs '<JSON>'` |

### Agent 自查 — 当命令覆盖不到时用

| 场景                     | 操作                                                        |
| ------------------------ | ----------------------------------------------------------- |
| 按关键词模糊搜索全部文献 | 读 `$IDX_PATH` 的 JSON，筛 `title` / `abstract` / `journal`   |
| 按 collection 筛选       | 读 `$IDX_PATH`，筛 `collection_path` 字段                     |
| 读论文全文               | 已找到 `fulltext.md` 路径（glob 或 resolve-key） → 直接 read                               |
| 读精读笔记               | 已找到 formal note 路径 → read 的 `## 🔍 精读` 区域                                          |
| 遍历笔记做批量统计       | `Get-ChildItem "$LIT_DIR" -Recurse -Filter "*.md"` + 读 frontmatter 或 `find "$LIT_DIR" -name "*.md"` |
| **禁止的操作**           | **根据 vault-knowledge 示例拼接路径、把目录名写死在文件路径里** |

---

## 5. 路由表

| 路由          | 触发词                                                     | 加载文件                                 |
| ------------- | ---------------------------------------------------------- | ---------------------------------------- |
| 精读          | `pf-deep <key>`, "精读 <key>"                               | [deep-reading.md](references/deep-reading.md) |
| 问答          | `pf-paper <key>`, "文献问答 <key>"                          | [paper-qa.md](references/paper-qa.md)       |
| 文献检索      | "找文献", "搜文献", "文献检索", "搜一下库里", "库里有没有"   | [paper-search.md](references/paper-search.md) |
| 批量阅读      | "读一下collection", "这个方向", "总结文献", "批量阅读"       | [multi-reading.md](references/multi-reading.md) |
| 保存记录      | `pf-end`, "结束讨论", "保存"                                | [save-session.md](references/save-session.md) |
| 论文定位协议  | 所有路由共享                                               | [paper-resolution.md](references/paper-resolution.md) |

> 所有路由继承 Skill 级别的 `$PYTHON` / `$VAULT` / `$LIT_DIR` 等变量。reference 文件不再重复声明。

---

## 文件结构

```
literature-qa/
├── SKILL.md                         ← 本文件
├── references/
│   ├── deep-reading.md              ← 精读工作流
│   ├── paper-qa.md                  ← 问答工作流
│   ├── paper-search.md              ← 文献检索工作流
│   ├── multi-reading.md             ← 批量阅读工作流
│   ├── save-session.md              ← 保存记录工作流
│   ├── paper-resolution.md          ← 论文定位协议
│   ├── deep-subagent.md
│   └── chart-reading/
└── scripts/
    ├── pf_bootstrap.py              ← Bootstrap 入口
    └── ld_deep.py                   ← 精读引擎
```
