# read-known-paper

> [!warning] Safety Rules
> - 不要捏造论文未提及的内容
> - 不要把推断写成论文事实——严格区分"文献说了什么"和"我推断什么"
> - 引用原文时标注来源页码/章节
> - 论文未提及的内容明确说明"论文中未提及"

交互式文献问答。不强制要求 OCR，但 OCR 完成后回答更准确。

---

## 前置条件

- bootstrap 已完成（有 `$VAULT`、`$PYTHON`）

---

## 步骤

### Step 1: 定位论文

用户可能给 zotero_key、DOI、标题片段、作者+年份。按以下方式查找：

**如果用户给的是 zotero_key：**

```bash
$PYTHON -m paperforge --vault "$VAULT" paper-context <zotero_key> --json
```

返回 JSON 包含 paper 元数据、OCR 状态、prior_notes 等。

**如果用户给的是 DOI、标题片段、作者+年份，先解析成候选：**

```bash
$PYTHON -m paperforge --vault "$VAULT" paper-status "<query>" --json
```

如果 `paper-status` 直接唯一命中，取返回的 `zotero_key` 再调 `paper-context`。

**paper-status 无法唯一定位时的备选：**

```bash
$PYTHON -m paperforge --vault "$VAULT" search "<query>" --json --limit 5
```

如果多候选，列出让用户选；用户选定后，再用选中的 `zotero_key` 调 `paper-context`。
如果无结果，告知用户并停止。

### Step 2: 加载文献内容

1. 从 paper-context 或 formal note frontmatter 获取：标题、作者、期刊、年份、domain
2. 读 `fulltext.md`（如果 OCR done）作为主要回答依据
3. 如果 fulltext 不存在："OCR 文本不可用，回答将基于元数据和公开信息"

### Step 3: 展示论文信息 + 进入 Q&A

```
已加载: <title> (<year>, <journal>)
作者: <authors> | Key: <zotero_key> | 领域: <domain>
OCR: done / 不可用
结束对话时说"保存"即可保存讨论。
请问有什么问题？
```

### Step 4: Q&A 循环

- 等待用户提问
- 每次回答后等待下一个问题
- 持续到用户说"保存"、"结束"、"完成"

**回答原则：**
- 严格基于 fulltext.md 中的文本内容
- 引用原文时标注来源页码/章节
- 论文未提及的内容明确说明"论文中未提及"
- 区分"文献说了什么"和"我推断什么"

### Step 5: 保存讨论

用户说"保存"、"结束"、"完成"时执行。

**收集 Q&A 对**，序列化为 JSON 数组：

```json
[
  {
    "question": "用户的问题",
    "answer": "Agent 的回答",
    "source": "user_question",
    "timestamp": "2026-05-14T12:00:00+08:00"
  }
]
```

`source`: `"user_question"`（用户提问）或 `"agent_analysis"`（Agent 主动分析）。

**调 discussion 模块：**

```bash
$PYTHON -m paperforge.worker.discussion record <zotero_key> \
    --vault "$VAULT" \
    --agent pf-paper \
    --model "<current_model>" \
    --qa-pairs '<JSON_ARRAY>'
```

- 返回 `ok` → 告知用户已保存
- 返回 `error` → 重试一次，仍失败则告知用户

> [!important] 不要自动保存。仅用户明确要求时执行。

### Post-action: 保存/归档

如果用户要求保存讨论内容到项目知识库，跳转至 `capture-project-knowledge.md`。
