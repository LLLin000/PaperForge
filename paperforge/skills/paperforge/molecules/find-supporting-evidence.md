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
  → 正文证据，可直接使用
  → 标注章节位置

source_kind: object
  → 图表证据，标注 object_kind

structure_resolved: false
  → 内容存在但章节未确认，慎用
```

不要求额外的 `rg`/`grep` 验证——结构坐标即为验证。

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

```
找到 N 条与 "<论点>" 相关的证据：

=== Smith 2024 (ABC12345) ===
[1] Introduction · section_title="Background"
    structure_resolved: true
    "…electrical stimulation parameters included 75 Hz frequency…"

=== Jones 2023 (DEF67890) ===
[2] Methods
    structure_resolved: true
    metadata candidate — fulltext not yet available
    "study of PTOA patients using biophysical stimulation…"
```

### Step 5: 等待用户选择

- "看 [1] 的详情" → `read-known-paper.md`
- "保存这条证据" → `capture-project-knowledge.md`
- "换个关键词" → 回到 Step 1
- "够了" → 结束

---

## 过渡路由

| 用户动作 | 路由目标 |
|---------|---------|
| 查看论文详情 | `read-known-paper.md` |
| 保存证据到项目知识 | `capture-project-knowledge.md` |
| 重新搜索 | 回到 Step 1 |

---

## 元数据降级

当 runtime-health 显示没有任何论文有 OCR 或全文可用时：

> 精确证据验证受限——降级到元数据级支持

输出候选项时标注 `fulltext_available=false`，不虚构引用位置或片段。

---

## 禁止

- 不要在没有 OCR/全文的情况下虚构引用位置或片段
- 不要把 metadata candidate 与正文证据混为同级
- 不要在用户未要求时自动保存证据
- 不要绕过 CLI 使用 `rg`/`grep` 验证——结构坐标即为验证
