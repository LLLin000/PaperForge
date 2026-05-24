# extract-methodology-card

从项目日志中提取可复用的方法论，生成方法论卡片。

---

## 前置条件

- bootstrap 已完成（有 `$VAULT`、`$PYTHON`）
- 已知 project 名称
- 目标项目有至少一条 `type: "session_summary"` 或 `type: "note"` 的日志

---

## 步骤

### Step 1: 读取项目日志

```bash
$PYTHON -m paperforge --vault "$VAULT" project-log --list --project "<project>" --json
```

从返回的日志条目中筛选包含可复用方法论的内容（`reusable` 字段非空的条目）。

### Step 2: 识别可复用模式

逐条分析日志，找出：
- 重复出现的解决策略
- 用户纠正的常见错误
- 被多次验证有效的流程

### Step 3: 读取方法论卡片模板

从 `references/method-card-template.md` 读取模板：

```bash
cat "$VAULT/System/PaperForge/references/method-card-template.md"
```

### Step 4: 填充模板生成卡片

按模板格式填充：

```markdown
---
id: <kebab-case-id>
tags: [<tag1>, <tag2>]
source_project: <project-name>
status: active
---

# <卡片标题（简短可搜索）>

## Use when
<!-- 什么时候应该用 -->

## Procedure
1. <步骤 1>
2. <步骤 2>
3. <步骤 3>

## Watch-outs
- <常见陷阱>
- <注意事项>

## Example
来自 `<project>` 项目的具体例子（附 project-log 来源）
---
```

### Step 5: 确认写入

```
即将创建方法论卡片到 System/PaperForge/methodology/archive/<id>.md:

标题: dc-parameter-audit
来源: 综述写作
步骤:
  1. 列出所有参数窗断言
  2. 逐句追溯文献来源
  3. 区分"文献说了什么"和"我推断什么"

确认写入？(y/n)
```

### Step 6: 写入

```bash
cat > "$VAULT/System/PaperForge/methodology/archive/<id>.md" << 'EOF'
<卡片内容>
EOF
```

写入后确认文件已创建。

---

## 禁止

- 不要在没有 project-log 的情况下凭空创建卡片
- 不要创建单次使用的方法——必须是可跨项目复用的模式
- 不要使用与已有卡片重复的 id

---

## 参考

模板文件：`references/method-card-template.md`
