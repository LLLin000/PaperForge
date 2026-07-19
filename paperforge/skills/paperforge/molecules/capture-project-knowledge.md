# capture-project-knowledge

捕获和持久化从阅读中获得的知识到项目记忆。

## Pre-flight Checklist

- [ ] SKILL.md Section 1a Pre-flight 全部通过
- [ ] `$VAULT`、`$PYTHON` 已从 bootstrap 获取
- [ ] 待保存的内容已就绪（证据/讨论/方法论）
- [ ] intent 已确定为 `capture_project_knowledge`

 或作为 post-action（在其他 molecule 输出后用户要求保存）

---

## 触发模式

### 1. 直意模式（Direct intent）

用户直接说"记一下"、"保存"、"记录这条"——不管从哪个上下文来，都路由到这里。

### 2. 后置模式（Post-action）

在其他分子（`read-known-paper`、`find-supporting-evidence`）产出结果后，用户要求保存其中一部分内容。

---

## 捕获类型

| 类型 | 描述 | 对应 Atom |
|------|------|-----------|
| **Lightweight JSONL** | 单条结构化阅读笔记，可搜索、可机器解析 | `atoms/write-reading-log-jsonl.md` |
| **Rich reading-log** | 叙述性段落，直接写入项目 markdown，写作素材 | `atoms/write-project-reading-log.md` |
| **Session/project log** | 会话总结、决策记录、弯路修正、待办事项 | `atoms/write-project-log.md` |
| **Methodology card** | 从项目日志中提取可复用的方法论 | `atoms/extract-methodology-card.md` |

---

## 步骤

### Step 1: 确定用户意图

从对话上下文中判断用户要保存哪类内容：

- 用户提到单条论文片段 / 引用 → **Lightweight JSONL**（最快、最轻量）
- 用户说"写一段总结" / "记录到这个项目" → **Rich reading-log**
- 用户说"记一下今天的进展" / "记录决策" → **Session/project log**
- 用户说"这个方法值得复用" / "提取方法论" → **Methodology card**
- 不确定时：列出四个选项让用户选

### Step 2: 调用对应 Atom

| 意图 | Atom |
|------|------|
| 单条阅读笔记 | `atoms/write-reading-log-jsonl.md` |
| 项目阅读记录 | `atoms/write-project-reading-log.md` |
| 会话/项目日志 | `atoms/write-project-log.md` |
| 方法论提取 | `atoms/extract-methodology-card.md` |

### Step 3: 写入前确认

**必须**在写入前以交互方式展示给用户确认。

格式参考对应 atom（`atoms/write-reading-log-jsonl.md`、`atoms/write-project-reading-log.md`、`atoms/write-project-log.md`）中的确认模板。

### Step 4: 写入后反馈

确认写入成功后，告知用户写入位置和主要内容摘要。

---

## 过渡路由

| 来源 | 路由方式 |
|------|---------|
| `read-known-paper` 保存讨论 | 用户说"保存" → Step 1 |
| `find-supporting-evidence` 保存证据 | 用户选择证据保存 → Step 1 |
| 用户直接说"记一下" | 直意触发 → Step 1 |

---

## 禁止

- 不要在用户未要求时自动保存内容
- 不要绕过确认步骤直接写入
- 不要用 project-reading-log 替代 lightweight JSONL（它们是不同粒度的记录）
