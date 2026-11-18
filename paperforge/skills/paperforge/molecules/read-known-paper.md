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

按 **Safe Executor**（§3）渲染 CLI。

#### 如果 primary 是 paper-context

direct_context_placeholder:
直接复用 primary 的 response，**不再调用第二次 paper-context**。从 response 中记录：
```
paper_key              — session 生命周期复用
title, first_author, year, journal, domain — 不重复调用
fulltext_path          — 有全文时记录
note_path              — formal note 路径
living_memory          — 已沉淀的分面认知记忆（idea_logic/methods_params/research_craft/critique_limits/my_connection）
user_annotations       — 内置 PDF 阅读器上的高亮与疑问
prior_notes            — 存在时记录 recheck_targets
```

> [!important] **Read-Before-Speak 原则**：若 `data.living_memory.facets` 非空，务必先结合既有分面理解承接讨论并验证新问题，避免从零重复泛读；若 `user_annotations.questions` 非空，优先关注用户划出的疑点。

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

#### 图表相关问题

如"Figure 3 表明什么"、"这张图在哪个章节讨论"：

先做初始检索：

```bash
$PYTHON -m paperforge --vault "$VAULT" \
  retrieve "<用户原问题，包含 Figure 3>" --paper <KEY> --json
```

拿到 object hit 后，按 `atoms/retrieval-routing.md` §5 **Object Context Resolution Protocol** 处理：

- Caption 已直接回答问题 → 直接使用，标注"图表 caption 信息"
- 需要作者解释/正文论证 → 执行一次 contextual retrieve:
  ```bash
  $PYTHON -m paperforge --vault "$VAULT" \
    retrieve "Figure 3 <caption 关键词>" --paper <KEY> --deep --json
  ```
  只取 `source_kind=body` 的结果作为正文讨论
- 同一 session 同一图不重复补查
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

## 保存与演进单篇记忆

1. **动态单篇认知沉淀（`atoms/update-paper-memory.md`）**
   若讨论中针对论文的实验技术参数、研究逻辑、巧思设计、审稿硬伤或课题启发产生了新的已核实洞见（或用户明确说"记住这个理解/记进这张文献卡片"）：
   - 按 `atoms/update-paper-memory.md` 读取现有分面，融合后执行 `memory-card refine <KEY> --facet <...> --content "..." --json`；
   - **禁止**把逐字问答对话直接贴进记忆卡片，始终提炼为紧凑的多维度认知演变摘要。
   - 若用户明确希望顺手在 PDF 原页高亮关键句段或图表，可路由至 `molecules/annotate-paper-pdf.md`。

2. **保存问答对 / 项目知识库**
   用户明确说"保存讨论"、"结束"、"归档项目"时：
   1. 收集 Q&A 对，序列化为 JSON 数组
   2. 调用 `paperforge.worker.discussion record` 或对应的保存 atom
   3. 返回 ok → 告知用户已保存
   4. 返回 error → 重试一次，仍失败则告知用户

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
