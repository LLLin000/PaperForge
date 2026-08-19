# read-known-paper

> [!warning] Safety Rules
> - 不要捏造论文未提及的内容
> - 不要把推断写成论文事实——严格区分"文献说了什么"和"我推断什么"
> - 引用原文时标注来源节点/章节
> - 论文未提及的内容明确说明"论文中未提及"

交互式文献问答。分为两个阶段：**A. 定位论文** → **B. 论文内 Q&A**。

> 定位与读文协议由 `molecules/pre-read.md` 决定(线性,命令写死)。
> 检索路由由 `atoms/retrieval-routing.md` 决定。session 状态规则定义在本 molecule。

---

## 阶段 A：定位论文

打开 `molecules/pre-read.md`,按 Step 1(Locate)→ Step 2(Context)执行,
得到 `paper_key`、`data.paper.title`、`data.paper.fulltext_path`、
`data.paper.pdf_path`。不重复调用 paper-context,不调用 query-plan。

### Step A3: 初始化 Q&A Session

只展示已点名的字段,不翻 JSON 找其他字段:

```
已定位: <data.paper.title>
Key: <KEY>
fulltext available: yes / no (fulltext_path 是否有效)
PDF available: yes / no (pdf_path 是否有效)

请问有什么问题？
```

StructureTree 只在真正运行 `paper-context <KEY> --structure` 之后才报告
available/unavailable;初始不展示。若后续章节级问答发现 structure 不可用:
- 不缓存 structure.nodes
- 报告"章节导航暂不可用"
- 仍可继续 fulltext 分析
- 回答中不声称章节位置已确认
## 阶段 B：论文内 Q&A

### 检索策略分类

#### 单事实问题

如"用了多少 Hz"、"样本量是多少"、"用的什么材料"、"随访多久"：

打开 `molecules/pre-read.md` Step 3：先在 `data.paper.fulltext_path`
里词面搜索；无果或句子不完整 → canonical PDF(PyMuPDF,命令写死)；仍无果
且是语义概念 → 一次 `retrieve --paper KEY`。

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
`atoms/retrieval-routing.md` §6 的 Object evidence 协议决定是否
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
