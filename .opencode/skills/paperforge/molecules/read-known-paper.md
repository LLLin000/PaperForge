# read-known-paper

> [!warning] Safety Rules
> - 不要捏造论文未提及的内容
> - 不要把推断写成论文事实——严格区分"文献说了什么"和"我推断什么"
> - 引用原文时标注来源节点/章节
> - 论文未提及的内容明确说明"论文中未提及"

交互式文献问答。分为两个阶段：**A. 定位论文** → **B. 论文内 Q&A**。

> 检索决策由 `atoms/retrieval-routing.md` 决定。session 状态规则也定义在该 atom 中。

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

按 **Safe Executor**（§3）渲染 CLI。

#### 如果 primary 是 paper-context

直接复用 primary 的 response，**不再调用第二次 paper-context**。从 response 中记录：
```
paper_key              — session 生命周期复用
title, first_author, year, journal, domain — 不重复调用
fulltext_path          — 有全文时记录
note_path              — formal note 路径
prior_notes            — 存在时记录 recheck_targets
```

#### 如果 primary 是 search

用户从候选中选择后，再调用一次 paper-context 获取完整信息：
```bash
$PYTHON -m paperforge --vault "$VAULT" paper-context <KEY> --json
```

#### 无结果时

告知用户"未找到匹配论文"。

### Step A3: 初始化 Q&A Session

展示论文信息，不加载全文：

```
已定位: <title> (<year>, <journal>)
作者: <authors> | Key: <KEY> | 领域: <domain>
正文可用: yes / no
StructureTree: available / unavailable

请问有什么问题？
```

如果 StructureTree 不可用，在后续章节级问答中：
- 不缓存 structure.nodes
- 报告"章节导航暂不可用"
- 仍可继续 scoped retrieve / fulltext 分析
- 回答中不声称章节位置已确认
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

#### 图表相关问题

先用同一条 paper-scoped `retrieve`。收到 `source_kind=object` 后，按
`atoms/retrieval-routing.md` 的 Object Context Resolution Protocol 决定是否
补一次 contextual retrieve；caption 已回答时不补查。
#### 总结型 / 整篇问题

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
