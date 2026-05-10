---
name: literature-qa
description: >
  学术文献精读与问答。MUST trigger when user types /pf-deep /pf-paper /pf-end
  or says 精读 深度阅读 读一下这篇 读文献 带我读 组会讲这篇 帮我精读 讲讲这篇论文
  查一下这篇论文 帮我看看这篇文章 这篇文章讲了什么 这篇讲了什么 论文问答 做这篇的问答
  保存讨论 结束讨论 保存记录 完成讨论 精读队列 有哪些该读了
  or uses natural language like 那篇关于XX的文章 去年那篇XX 找一下XX的文献
  or any phrase about reading analyzing deep-reading papers in their Zotero library.
  支持 Zotero key DOI 标题 作者 年份 自然语言描述定位论文.
  Routes intent internally via routing table—no separate sub-skills needed.
license: Apache-2.0
compatibility: opencode
---

# Literature QA — 学术文献精读与问答

## 路由表

Agent 读到本文件后，首先根据用户意图路由到对应的 reference 文件：

| 用户意图 | 典型输入 | 加载文件 |
|---------|---------|---------|
| 三阶段精读（指定论文） | `/pf-deep <query>`, `pf-deep <query>`, "精读 XXX", "深度阅读 XXX", "带我读", "组会讲这篇", "读一下这篇" | [references/deep-reading.md](references/deep-reading.md) |
| 三阶段精读（查看队列） | `/pf-deep`（无参数）, "精读队列", "有哪些该读了" | [references/deep-reading.md](references/deep-reading.md) |
| 论文问答 | `/pf-paper <query>`, `pf-paper <query>`, "做这篇的问答", "帮我看看 XXX", "这篇文章讲了什么", "查一下" | [references/paper-qa.md](references/paper-qa.md) |
| 保存讨论记录 | `/pf-end`, `pf-end`, "保存", "结束讨论", "完成讨论", "保存记录" | [references/save-session.md](references/save-session.md) |

> **重要：** 加载 reference 文件后，严格按照该文件的流程执行。不要跳过任何步骤。

## 论文定位（所有路由共用，先执行）

详见 [references/paper-resolution.md](references/paper-resolution.md)。

**核心原则：所有路径操作走 Python，Agent 只管调命令、读输出。零硬编码、零平台依赖。**

### 快速索引

| 你要做什么 | 跑这个 Python 命令 |
|-----------|-------------------|
| 定位论文（按 key） | `python -m paperforge.worker.paper_resolver resolve-key <KEY> --vault .` |
| 定位论文（按 DOI） | `python -m paperforge.worker.paper_resolver resolve-doi "<DOI>" --vault .` |
| 搜索论文（字段匹配） | `python -m paperforge.worker.paper_resolver search --title "..." --author "..." --year ... --vault .` |
| 获取 vault 路径 | `python -m paperforge.worker.paper_resolver paths --vault .` |

### 处理结果

- **Python 返回匹配：** 直接使用返回的 workspace
- **Python 返回空：** Agent 自己搜。用 `paths` 拿到的 `literature_dir` 和 `index_path`，grep frontmatter / 读 formal-library.json
- **自然语言输入：** Agent 自己理解语义，读 formal-library.json（`paths` 里的 `index_path`）搜索
- **命中多篇：** 列出候选清单（key, title, year, domain, ocr_status），让用户选

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
