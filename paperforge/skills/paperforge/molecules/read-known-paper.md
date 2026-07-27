# read-known-paper

> [!warning] Safety Rules
> - 不要捏造论文未提及的内容
> - 不要把推断写成论文事实——严格区分"文献说了什么"和"我推断什么"
> - 引用原文时标注来源节点/章节
> - 论文未提及的内容明确说明"论文中未提及"

交互式文献问答。分为两个阶段：**A. 定位论文** → **B. 论文内 Q&A**。

> 检索决策由 `atoms/retrieval-routing.md` 决定。session 状态规则也定义在该 atom 中。

---

## Pre-flight Checklist

- [ ] SKILL.md Section 1a Pre-flight 全部通过
- [ ] `$VAULT`、`$PYTHON` 已从 bootstrap 获取
- [ ] intent 已确定为 `read_known_paper`

---

## 阶段 A：定位论文

用户可能给 zotero_key、DOI、标题关键词、作者+年份。

### Step A1: 调用 planner

```bash
$PYTHON -m paperforge --vault "$VAULT" \
  query-plan "<identifier>" \
  --intent locate --json
```

打开 `atoms/retrieval-routing.md`，按 **Planner Protocol**（§2）执行 `data.primary`。

### Step A2: 安全执行 primary

按 **Safe Executor**（§3）渲染 CLI：

- `paper-context` → 定位成功，取 `zotero_key`
- `search` → 多候选时列出让用户选，无结果时告知

### Step A3: 检查 paper-context 返回

```bash
$PYTHON -m paperforge --vault "$VAULT" paper-context <KEY> --json
```

从返回中记录 session 状态：
```
paper_key              — session 生命周期复用
title, first_author, year, journal, domain — 不重复调用
fulltext_path          — 有全文时记录
note_path              — formal note 路径
prior_notes            — 存在时记录 recheck_targets
```

### Step A4: 加载结构（仅首次）

首次进入 Q&A 时不加载整篇 fulltext.md。只展示论文信息：

```
已定位: <title> (<year>, <journal>)
作者: <authors> | Key: <KEY> | 领域: <domain>
正文可用: yes / no

请问有什么问题？
```

---

## 阶段 B：论文内 Q&A

### 检索策略分类

#### 单事实问题

如"用了多少 Hz"、"样本量是多少"、"用的什么材料"、"随访多久"：

```bash
$PYTHON -m paperforge --vault "$VAULT" \
  retrieve "<question>" --paper <KEY> --json
```

- 不重新调用 query-plan
- 不加载整篇 fulltext.md
- 不加载 StructureTree
- session 内的 `paper_key` 直接复用

#### 章节级 / 关系型问题

如"实验设计是什么"、"结果如何支持结论"、"Methods 和 Results 是否一致"：

第一次调用加载 StructureTree：

```bash
$PYTHON -m paperforge --vault "$VAULT" \
  paper-context <KEY> --structure --json
```

缓存 `structure.nodes`（session 内不清除）。然后：

```bash
$PYTHON -m paperforge --vault "$VAULT" \
  retrieve "<question>" --paper <KEY> --deep --json
```

`--deep` 启用 BM25 + 向量混合检索，适用于跨章节关联查询。

#### 总结型/整篇问题

如"总结这篇文章的逻辑链"：

需要完整全文：

```bash
$PYTHON -m paperforge --vault "$VAULT" \
  paper-context <KEY> --structure --json
```

读取完整 fulltext（使用 paper-context 返回的 `fulltext_path`），做全文分析。

---

### 回答原则

- 严格基于正文内容
- 引用原文时标注来源（node、章节）
- 论文未提及的内容明确说明"论文中未提及"
- 区分"文献说了什么"和"我推断什么"
- 不要整段逐字复制——用自己的话总结

---

## 保存讨论

用户说"保存"、"结束"、"完成"时执行。

1. 收集 Q&A 对，序列化为 JSON 数组
2. 调用 `paperforge.worker.discussion record` 或对应的保存 atom
3. 返回 ok → 告知用户已保存
4. 返回 error → 重试一次，仍失败则告知用户

> [!important] 不要自动保存。仅用户明确要求时执行。

如果用户要求保存到项目知识库，跳转至 `capture-project-knowledge.md`。

---

## Session 缓存规则

```
paper_key：    整个 Q&A session 复用
structure：    第一次章节/总结问题后缓存，不清除
metadata：     不重复调用 paper-context
重置条件：     用户明确切换论文时重置全部
```

---

## 过渡路由

| 用户动作 | 路由目标 |
|---------|---------|
| 结束 Q&A | 提示保存后结束 |
| 保存讨论到项目知识库 | `capture-project-knowledge.md` |
| 切换论文 | 重置 session 状态 → 阶段 A |
