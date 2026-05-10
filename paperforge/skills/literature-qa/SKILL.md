---
name: literature-qa
description: >
  学术文献精读与问答。MUST trigger when user types /pf-deep, /pf-paper, /pf-end,
  or says "精读", "深度阅读", "读一下", "查一下这篇论文", "帮我看看这篇文章",
  "这篇文章讲了什么", "保存讨论", "结束讨论", "做这篇文献的问答",
  or any phrase about reading/analyzing papers in their Zotero library.
  支持 Zotero key, DOI, 标题, 作者/年份, 自然语言描述定位论文.
license: Apache-2.0
compatibility: opencode
---

# Literature QA — 学术文献精读与问答

## 路由表

Agent 读到本文件后，首先根据用户意图路由到对应的 reference 文件：

| 用户意图 | 典型输入 | 加载文件 |
|---------|---------|---------|
| 三阶段精读（指定论文） | `/pf-deep <query>`, `pf-deep <query>`, "精读 XXX", "深度阅读 XXX" | [references/deep-reading.md](references/deep-reading.md) |
| 三阶段精读（查看队列） | `/pf-deep`（无参数）, "精读队列", "有哪些该读了" | [references/deep-reading.md](references/deep-reading.md) |
| 论文问答 | `/pf-paper <query>`, `pf-paper <query>`, "做这篇的问答", "帮我看看 XXX" | [references/paper-qa.md](references/paper-qa.md) |
| 保存讨论记录 | `/pf-end`, `pf-end`, "保存", "结束讨论", "完成讨论" | [references/save-session.md](references/save-session.md) |

> **重要：** 加载 reference 文件后，严格按照该文件的流程执行。不要跳过任何步骤。

## 论文定位（所有路由共用，先执行）

详见 [references/paper-resolution.md](references/paper-resolution.md)。

**核心原则：二路定位。Python 干确定的活，Agent 干理解的活。路径全在环境变量里，零硬编码。**

### 第零步：加载环境变量（每条路由启动时跑一次）

```pwsh
python -m paperforge.worker.paper_resolver env --vault . --shell pwsh | Invoke-Expression
```

此后所有路径用环境变量引用，不再拼接：

| 变量               | 含义                        |
| ------------------ | --------------------------- |
| `$env:PF_VAULT`      | vault 根目录                  |
| `$env:PF_INDEX_PATH` | formal-library.json 路径     |
| `$env:PF_LITERATURE_DIR` | formal notes 目录        |
| `$env:PF_OCR_DIR`    | OCR 结果目录                 |

### 第一步：判断输入类型，选择路径

| 输入特征 | 执行命令 |
|---------|---------|
| 8位 key | `python -m paperforge.worker.paper_resolver resolve-key <KEY> --vault "$env:PF_VAULT"` |
| DOI | `python -m paperforge.worker.paper_resolver resolve-doi "<DOI>" --vault "$env:PF_VAULT"` |
| 标题片段 | `python -m paperforge.worker.paper_resolver search --title "..." --vault "$env:PF_VAULT"` |
| 作者+年份 | `python -m paperforge.worker.paper_resolver search --author "Smith" --year 2024 --vault "$env:PF_VAULT"` |
| 自然语言 | Agent 读 `$env:PF_INDEX_PATH` 指向的 formal-library.json |

### 第二步：处理结果

- **Python 返回匹配：** 直接使用返回的 workspace（`formal_note_path` 等由 config 动态计算）
- **Python 搜不到：** Agent grep fallback：`rg -l "zotero_key:.*ABC" "$env:PF_LITERATURE_DIR/"`
- **自然语言搜不到：** 告知用户 "未找到，请确认或先运行 `paperforge sync`"
- **命中多篇：** 列出候选清单让用户选

## 文件结构

```
literature-qa/
├── SKILL.md                       ← 本文件（路由入口）
├── references/
│   ├── deep-reading.md            ← 精读工作流
│   ├── paper-qa.md                ← 问答工作流
│   ├── save-session.md            ← 保存记录工作流
│   ├── paper-resolution.md        ← 论文定位详细协议
│   ├── deep-subagent.md           ← 子代理提示词模板
│   └── chart-reading/             ← 19 个图表类型阅读指南
└── scripts/
    └── ld_deep.py                 ← 精读引擎（Python）
```
