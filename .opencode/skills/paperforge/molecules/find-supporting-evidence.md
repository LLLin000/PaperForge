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

当 scope=paper 时（planner 返回 `paper_key` 且有值）：

```bash
$PYTHON -m paperforge --vault "$VAULT" \
  retrieve "<question>" --paper <KEY> --json
```

- 只查该论文
- `fallback=null`（paper scope 不执行 fallback）
- 无全文 → 报告"本文无可用正文"
- 零结果 → 报告"本文未检索到相关内容"
- 不能再 search 其他论文

单事实问题（"用了多少 Hz"、"样本量多少"）直接用 `retrieve --paper KEY`。
不需要加载整篇 fulltext.md，不需要 StructureTree。

### Step 4: 展示证据

**正文证据区块**（来自 retrieve primary）：

```text
找到 N 条与 "<论点>" 相关的正文证据：

=== Smith 2024 (ABC12345) ===
[1] Introduction · section_title="Background"
    structure_resolved: true
    "…electrical stimulation parameters included 75 Hz frequency…"
```

**object / 图表证据**（来自 retrieve primary）：

打开 `atoms/retrieval-routing.md` §6 的 **Object evidence** 协议。
判断 caption 是否直接回答用户问题。如果需要作者解释或正文论证，执行一次
contextual retrieve，合并展示。

**元数据候选区块**（来自 search --evidence fallback）：

```text
evidence_status: metadata_only
fulltext_verified: false

[1] ABC12345 | Smith 2024 | 论文标题
[2] DEF67890 | Jones 2023 | 论文标题
```

两个区块不混合。metadata candidate 不显示章节位置，不显示正文摘要。
