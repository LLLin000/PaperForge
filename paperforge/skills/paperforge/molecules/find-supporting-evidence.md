# find-supporting-evidence

为特定论点或问题查找文献中的证据支持。

> 检索决策由 `atoms/retrieval-routing.md` 决定。这个 molecule 只编排工作流和解释证据。

---

## Pre-flight Checklist

- [ ] SKILL.md Section 1a Pre-flight 全部通过
- [ ] `$VAULT`、`$PYTHON` 已从 bootstrap 获取
- [ ] intent 已确定为 `find_supporting_evidence`
- [ ] `atoms/retrieval-routing.md` §5（Evidence Interpretation）已熟知

---

## 步骤

### Step 1: 解析证据需求 + 调用 planner

提取：
- **论点/问题**：需要支持的具体主张
- **范围**：是否限定特定论文、domain、作者
- **证据类型**：统计结果、方法引用、临床发现、机制解释

```bash
$PYTHON -m paperforge --vault "$VAULT" \
  query-plan "<user_query>" \
  --intent content --json
```

打开 `atoms/retrieval-routing.md`，按 **Planner Protocol**（§2）和 **Safe Executor**（§3）执行 `data.primary`。

### Step 2: Library scope

当 scope=library 时，primary 通常是 `retrieve`（跨论文正文检索）。

#### 如果有结果

按 `atoms/retrieval-routing.md` §5 解释每条 evidence：

```yaml
source_kind: body + structure_resolved: true
  → 章节归属已解析
  → Agent 仍须阅读 text 判断是否直接支持用户问题
  → 区分作者陈述与 Agent 推断
  → section_title / section_level / part_ordinal 可用

source_kind: body + structure_resolved: false
  → 内容存在但章节位置未确认
  → 慎用，标注"章节未确认"

source_kind: object
  → 图表证据，标注 object_kind
  structure_resolved 默认为 false（大部分 object 未关联章节）
```

#### 如果 zero_results 且 fallback 非 null

执行一次 fallback（通常为 `search`）。fallback 结果必须标为：

```
metadata candidate
fulltext_verified=false
```

不能与 retrieve evidence 混为同级。

#### 如果 zero_results 且 fallback 为 null

告知用户"未检索到相关内容"。

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

```
找到 N 条与 "<论点>" 相关的正文证据：

=== Smith 2024 (ABC12345) ===
[1] Introduction · section_title="Background"
    structure_resolved: true
    "…electrical stimulation parameters included 75 Hz frequency…"
```

**元数据候选区块**（来自 search --evidence fallback）：

```
元数据候选（fulltext_verified=false，不显示正文引文）：

[1] ABC12345 | Smith 2024 | 论文标题
    evidence_status: metadata_only
[2] DEF67890 | Jones 2023 | 论文标题
    evidence_status: metadata_only
```

两个区块不混合。metadata candidate 不显示章节位置，不显示正文摘要。

---

## 禁止

- 不要在没有 OCR/全文的情况下虚构引用位置或片段
- 不要把 metadata candidate 与正文证据混为同级
- 不要在用户未要求时自动保存证据
- 不要绕过 CLI 使用 `rg`/`grep` 搜索——所有检索通过 CLI 完成
- 不要把 structure_resolved=true 等同于"该证据支持用户主张"——仅表示章节归属已解析
