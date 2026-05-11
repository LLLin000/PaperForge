---
name: literature-qa
description: >
  学术文献库操作：精读、问答、检索、浏览。Triggered by:
  /pf-deep /pf-paper /pf-end,
  "精读", "文献问答", "结束讨论", "保存记录",
  "找文献", "搜文献", "文献库", "文献检索", "精读队列", "库里有什么",
  "搜一下库里", "看一下文献库", "浏览文献库".
  Uses Zotero key, DOI, title, or domain keywords to locate papers.
license: Apache-2.0
compatibility: all
---

# Literature QA — 学术文献精读、问答与检索

---

## MANDATORY FIRST STEP — 必须先执行，不可跳过

在任何文献操作之前，你必须完成以下三步。跑不完不要进入后续路由。

### Step A: 识别 Vault

检查当前目录及其父目录是否存在 `paperforge.json`：

```
Test-Path paperforge.json
```

如果不存在，逐级往上找（`..`、`..\..`），直到找到。如果找不到，**问用户**："你的 PaperForge Vault 根目录路径是什么？"

记下 vault 根目录为 `$VAULT`，后续所有 `--vault` 参数都用这个路径。

### Step B: 找到正确的 Python 并获取路径

PaperForge 的 Python 环境不一定是当前终端的 `python`。按以下顺序尝试：

```
1. 读 $VAULT/paperforge.json → 找 "python_path" 字段 → 用这个路径
2. $VAULT/.venv/Scripts/python.exe
3. $VAULT/.paperforge-test-venv/Scripts/python.exe
4. 当前终端的 python
```

找到可用的 Python 后，用它跑：
```
$PYTHON -m paperforge.worker.paper_resolver paths --vault "$VAULT"
```

如果所有 Python 都报 `No module named paperforge`：
- **不要继续。** 不要硬闯文件的目录树。
- **问用户**："你的 Vault 里哪个 Python 装了 paperforge？在终端试试 `python -m paperforge --version` 看哪个能跑。"

### Step C: 加载共享知识

加载 [references/vault-knowledge.md](references/vault-knowledge.md) 了解 Vault 结构、Domain/Collection 概念、索引格式。

只有在 Step A+B+C 全部完成之后，才能进入下面的路由表。

---

## 路由表

加载本 Skill 后，根据用户的 **具体意图** 选择一条路由，加载对应的 reference 文件：

| 用户意图 | 典型输入 | 加载文件 | 说明 |
|---------|---------|---------|------|
| 了解库概况 | "看一下库里有什么", "库里内容" | [vault-knowledge.md](references/vault-knowledge.md) | 展示 domain 分布和统计 |
| 文献检索 | "找文献", "搜文献", "库里有没有XX", "文献检索", "搜一下库里" | [paper-search.md](references/paper-search.md) | 在库里搜索论文 |
| 精读 | `/pf-deep <key>`, "精读 <key>" | [deep-reading.md](references/deep-reading.md) | Keshav 三阶段精读 |
| 精读队列 | `/pf-deep` 无参数, "精读队列" | [deep-reading.md](references/deep-reading.md) | 查看待精读列表 |
| 论文问答 | `/pf-paper <key>`, "文献问答 <key>" | [paper-qa.md](references/paper-qa.md) | 交互式 Q&A |
| 保存记录 | `/pf-end`, "结束讨论", "保存记录" | [save-session.md](references/save-session.md) | 存档问答记录 |

> **重要：** 加载 reference 文件后，**严格按照该文件的流程执行，不要跳过任何步骤。** 如果你不知道下一步干什么，回顾 reference 文件的流程，不要自己发明步骤。

## 论文定位

所有路由共享的论文定位协议：见 [references/paper-resolution.md](references/paper-resolution.md)。

**核心原则：路径从 `paths` 获取，不硬编码。Python 从 Step B 找到的 `$PYTHON` 用，不用系统的 `python`。**

| 你要做什么     | 跑这个命令                                                                         |
| -------------- | ---------------------------------------------------------------------------------- |
| 获取 vault 路径 | `$PYTHON -m paperforge.worker.paper_resolver paths --vault "$VAULT"`                 |
| 定位论文（按 key） | `$PYTHON -m paperforge.worker.paper_resolver resolve-key <KEY> --vault "$VAULT"`      |
| 定位论文（按 DOI） | `$PYTHON -m paperforge.worker.paper_resolver resolve-doi "<DOI>" --vault "$VAULT"`    |
| 搜索论文       | `$PYTHON -m paperforge.worker.paper_resolver search --title "..." --domain "..." --vault "$VAULT"` |

## 文件结构

```
literature-qa/
├── SKILL.md                       ← 本文件（路由入口）
├── references/
│   ├── vault-knowledge.md         ← Vault 结构共享知识
│   ├── paper-resolution.md        ← 论文定位详细协议
│   ├── paper-search.md            ← 文献检索工作流
│   ├── deep-reading.md            ← 精读工作流
│   ├── paper-qa.md                ← 问答工作流
│   ├── save-session.md            ← 保存记录工作流
│   ├── deep-subagent.md           ← 子代理提示词模板
│   └── chart-reading/             ← 19 个图表类型阅读指南
└── scripts/
    └── ld_deep.py                 ← 精读引擎（Python）
```
