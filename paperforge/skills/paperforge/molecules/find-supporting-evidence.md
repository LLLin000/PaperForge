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

### Step 2: 评估结果

按 `atoms/retrieval-routing.md` §4（Exactly-One-Fallback Protocol）评估结果。
可能的 fallback trigger 为 `zero_results` 或 `no_direct_answer`。
本 molecule 不重新定义 trigger 规则。

### 有正文证据时（scope=library, primary=retrieve）
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

**object / 图表证据**（来自 retrieve primary）：

打开 `atoms/retrieval-routing.md` §5 的 **Object Context Resolution Protocol**。

判断 caption 是否直接回答用户问题。如果需要作者解释或正文论证，执行一次
contextual retrieve，合并展示。
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
