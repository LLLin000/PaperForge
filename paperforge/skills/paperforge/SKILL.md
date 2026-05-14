---
name: paperforge
description: >
  Research Memory Runtime — 文献搜索、精读、问答、阅读笔记、
  工作记录、方法论提取。Triggered by:
  pf-deep pf-paper pf-sync pf-ocr pf-status,
  "精读" "找文献" "搜文献" "文献问答" "读一下" "看看这篇"
  "讨论" "记录阅读" "记录工作" "总结会话" "提取方法论".
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

返回 JSON。记录以下变量（所有 workflow 文件继承，不再重复声明）：

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

---

## 2. Agent Context — bootstrap 成功后执行

```bash
$PYTHON -m paperforge agent-context --json --vault "$VAULT"
```

返回 library overview、collection tree、可用命令和规则。Agent 注入为会话上下文。

---

## 3. Methodology Index — bootstrap 自动提供

bootstrap 已返回 `methodology_index`（从 `System/PaperForge/methodology/archive/` 扫描）。
Agent 在需要时自行读取对应卡片（`read System/PaperForge/methodology/archive/<id>.md`）。

---

## 4. Reading-Log Safety Rule — 全局规则，所有 workflow 必须遵守

Reading-log 不是事实源。它记录的是**之前的关注点、解读和预期用途**。

当存在 prior reading-log 时：
1. 用它决定**优先复查什么**，不是用它回答用户问题
2. 重新打开**原文/图表/表格**，核实之前的解读
3. 确认的，说明"已回原文复核"
4. 被推翻的，创建 correction note
5. **绝对禁止**仅根据 reading-log 内容回答事实性问题

---

## 5. 意图路由

用户输入对应唯一一个 workflow 文件（打开并执行其完整流程）：

| 用户说                                                   | 打开                             |
| -------------------------------------------------------- | -------------------------------- |
| "找文献" "搜" "库里有没有XX" "collection 里关于YY"       | `workflows/paper-search.md`      |
| "精读 <key>" "/pf-deep" "三阶段阅读"                     | `workflows/deep-reading.md`      |
| "读一下" "看看" "讨论" "/pf-paper" "<key> 这篇讲了什么"  | `workflows/paper-qa.md`          |
| "记一下" "记录阅读" "reading log" "读完这段记一下"       | `workflows/reading-log.md`       |
| "总结会话" "工作记录" "项目记录" "project log" "记决策"   | `workflows/project-log.md`       |
| "提取方法论" "总结规律" "存档写作规律"                    | `workflows/methodology.md`       |
| "branch" "代码审查" "feature" "dashboard" "memory layer" "用户反馈" "报错" "安装失败" "Git" "Zotero" "BetterBibTeX" "OCR" "插件" | `workflows/project-engineering.md` |
| 不确定 / 空输入                                          | 问用户：搜文献、精读、问答、记笔记、记工作、提方法论？ |

路由后如用户切换意图，重新判断并打开对应 workflow。

---

## 6. 全局禁止规则

- **禁止自行拼接文件路径**。所有路径从 bootstrap 或 paper-context 获取。
- **禁止绕过 CLI 直接操作文件**。搜索用 `$PYTHON -m paperforge search`，不用 glob/grep 扫库。
- **禁止在未完成 paper-context 检查前读取原文**（适用于 deep-reading、paper-qa）。

---

## 文件结构

```
paperforge/
├── SKILL.md              ← 本文件（compound：启动注入 + 路由 + 全局规则）
├── workflows/            ← molecules：原子序列 + 分支条件
│   ├── paper-search.md
│   ├── deep-reading.md
│   ├── paper-qa.md
│   ├── reading-log.md
│   ├── project-log.md
│   ├── methodology.md
│   └── project-engineering.md
├── references/           ← 共享参考
│   ├── chart-reading/    ← 19 种图表阅读指南
│   └── method-card-template.md
└── scripts/              ← 脚本 atoms
    ├── pf_bootstrap.py
    └── pf_deep.py
```
