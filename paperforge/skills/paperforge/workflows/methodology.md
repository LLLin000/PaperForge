# methodology

> **Scope:** Only archive methods reusable across multiple projects/tasks.
> Session-specific progress, decisions, and todos go to project-log.

从 project-log 中提取可复用方法论，按 method-card 模板写入 methodology archive。
不 append 到大文件，每张卡片独立保存。

---

## 前置条件

- bootstrap 已完成
- 有 project-log 记录可读取

---

## 步骤

### Step 1: 确定项目和来源

询问用户从哪个项目提取。如用户未指定，列出有 project-log 的项目。

### Step 2: 读取 project-log

```bash
$PYTHON -m paperforge --vault "$VAULT" project-log --list --project "<project>" --json
```

扫描其中以下信号：

| log 中的信号              | 可提取为                    |
| ------------------------- | --------------------------- |
| `detours` 中的教训        | 方法论规则                   |
| `reusable` 字段里的内容   | 直接采用                    |
| `decisions` 中的重要选择  | 决策原则                    |
| 跨文献审计/比较分析       | 审计方法论                  |
| 写作修正/审阅反馈         | 写作检查清单                |

### Step 3: 识别可提取 pattern

对每个 pattern 分类：
- `review-writing` — 综述框架设计、gap 分析、跨研究审计
- `argument-writing` — 段落写作、论证结构
- `analysis-methods` — 文献审计、跨研究比较、参数提取
- `general` — fallback

### Step 4: 按 method-card 模板生成卡片

打开 `references/method-card-template.md` 确认模板格式。

对每个 pattern 生成一张卡片，展示给用户确认。格式：

```markdown
---
id: <kebab-case-id>
tags: [<tag1>, <tag2>]
source_project: <project-name>
status: active
---

# <标题>

## Use when
<什么时候应该用这个方法>

## Procedure
1. <步骤 1>
2. <步骤 2>
...

## Watch-outs
- <注意事项 1>
- <注意事项 2>

## Example
<来自项目的具体例子>
```

### Step 5: 用户确认后写入

将每张卡片写入：

```
System/PaperForge/methodology/archive/<id>.md
```

用 `write` 工具创建文件。如已存在同名文件，追加到末尾（用 `---` 分隔）。
不自动覆盖已有内容。

---

## 禁止

- 不要提取太泛的"教训"（如"多读文献"）——必须有具体的 Procedure 步骤
- 不要创建超过 4 张卡片/次——优先最可复用的
- 不要在用户确认前写入
