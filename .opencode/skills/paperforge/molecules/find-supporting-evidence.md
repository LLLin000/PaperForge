# find-supporting-evidence

为特定论点或问题查找文献中的证据支持。

> 检索决策由 `atoms/retrieval-routing.md` 决定。这个 molecule 只编排工作流和解释证据。

---


## 步骤

### Step 1: 解析证据需求 + 选择路由

提取：
- **论点/问题**：需要支持的具体主张
- **范围**：是否限定特定论文、domain、作者
- **证据类型**：统计结果、方法引用、临床发现、机制解释

打开 `atoms/retrieval-routing.md` 按三分支选路由：

- 范围限定已知论文 → Route B(`pre-read.md` Step 3:fulltext 词面优先)
- 范围是模糊/跨库 → Route C(search → 无果 → retrieve 一次)
- 不调用 query-plan

### Step 2: Execute and assess

执行所选路由的命令(命令在 `atoms/retrieval-routing.md` 中写死)。
Keep `scope=paper` isolated; report zero results or no direct answer without
expanding to other papers.

### Step 3: Paper scope

当问题限定单篇论文时,打开 `molecules/pre-read.md` Step 3:

- fulltext 词面搜索优先(`data.paper.fulltext_path` + grep)
- fulltext 命中但截断 / 不可读 → canonical PDF 一次(PyMuPDF,命令写死)
- fulltext 词面零命中且是语义概念 → `retrieve --paper KEY` 一次
- 不再 search 其他论文;不重复 fallback

### Step 4: 展示证据

**正文证据区块**(来自 fulltext 词面命中 / retrieve 命中):

```text
找到 N 条与 "<论点>" 相关的正文证据：

=== Smith 2024 (ABC12345) ===
[1] Introduction · section_title="Background"
    structure_resolved: true
    "…electrical stimulation parameters included 75 Hz frequency…"
```

**object / 图表证据**:

打开 `atoms/retrieval-routing.md` §6 的 **Object evidence** 协议。
判断 caption 是否直接回答用户问题。如果需要作者解释或正文论证，执行一次
contextual retrieve，合并展示。

**元数据候选区块**(来自 Route C 的 search,仅跨库场景):

```text
evidence_status: metadata_only
fulltext_verified: false

[1] ABC12345 | Smith 2024 | 论文标题
[2] DEF67890 | Jones 2023 | 论文标题
```

两个区块不混合。metadata candidate 不显示章节位置，不显示正文摘要。
retrieve 命中必须标记 "semantic match",非精确词面。
