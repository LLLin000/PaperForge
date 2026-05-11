---
name: literature-qa
description: >
  学术文献精读、问答与检索。Triggered by: /pf-deep /pf-paper /pf-end,
  "精读 <key/title>", "文献问答 <key/title>", "结束讨论", "保存记录",
  "找一下...文献", "查一下...", "库里有没有", "精读队列".
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

### Step B: 获取路径

```
python -m paperforge.worker.paper_resolver paths --vault "$VAULT"
```

如果报 `No module named paperforge`，说明当前 Python 环境没装 paperforge。不要硬闯文件的目录树——**问用户**："你用的是哪个 Python？Vault 里的 `.venv` 路径是什么？"

### Step C: 加载共享知识

加载 [references/vault-knowledge.md](references/vault-knowledge.md) 了解 Vault 结构、Domain/Collection 概念、索引格式。

只有在 Step A+B+C 全部完成之后，才能进入下面的路由表。

---

## 路由表

Agent 根据用户意图路由到对应的 reference 文件：

| 用户意图 | 典型输入 | 加载文件 |
|---------|---------|---------|
| 查看 Vault 概况 | "看一下库里内容", "看一下文献库", "库里有什么", "浏览文献" | [references/vault-knowledge.md](references/vault-knowledge.md) |
| 文献检索 | "找一下骨科...文献", "查一下 TGF-beta", "库里有没有支架材料的", "搜一下 Smith 的文章", "collection 里有没有" | [references/paper-search.md](references/paper-search.md) |
| 三阶段精读（指定论文） | `/pf-deep <query>`, `pf-deep <query>`, "精读 XXX", "深度阅读 XXX", "带我读", "组会讲这篇", "读一下这篇" | [references/deep-reading.md](references/deep-reading.md) |
| 三阶段精读（查看队列） | `/pf-deep`（无参数）, "精读队列", "有哪些该读了" | [references/deep-reading.md](references/deep-reading.md) |
| 论文问答 | `/pf-paper <query>`, `pf-paper <query>`, "做这篇的问答", "帮我看看 XXX", "这篇文章讲了什么", "查一下" | [references/paper-qa.md](references/paper-qa.md) |
| 保存讨论记录 | `/pf-end`, `pf-end`, "保存", "结束讨论", "完成讨论", "保存记录" | [references/save-session.md](references/save-session.md) |

> **重要：** 加载 reference 文件后，**严格按照该文件的流程执行，不要跳过任何步骤。** 如果你不知道下一步干什么，回顾 reference 文件的流程，不要自己发明步骤。

## 论文定位

所有路由共享的论文定位协议：见 [references/paper-resolution.md](references/paper-resolution.md)。

**核心原则：路径从 `paths` 获取，不硬编码。**

| 你要做什么     | 跑这个 Python 命令                                                               |
| -------------- | -------------------------------------------------------------------------------- |
| 获取 vault 路径 | `python -m paperforge.worker.paper_resolver paths --vault .`                      |
| 定位论文（按 key） | `python -m paperforge.worker.paper_resolver resolve-key <KEY> --vault .`          |
| 定位论文（按 DOI） | `python -m paperforge.worker.paper_resolver resolve-doi "<DOI>" --vault .`        |
| 搜索论文       | `python -m paperforge.worker.paper_resolver search --title "..." --domain "..." --vault .` |

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
