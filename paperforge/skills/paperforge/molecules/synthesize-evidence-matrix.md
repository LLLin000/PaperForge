# synthesize-evidence-matrix

多文献横向证据对比与结构化矩阵综合工作流。

> [!warning] Evidence Boundary Rules
> - 每个单元格的数值、样本量、实验参数与结论必须来自 `retrieve`、`paper-context` 返回的 `user_annotations` 或原文图表，严禁根据摘要推断或补全缺失字段。
> - 无 OCR 全文的文献（`fulltext_available == false`）只能标注为 `metadata only — 未核验全文`，不得与已核验正文证据混排。
> - 明确区分**文献客观结果**、**作者解释**与**跨文献横向推断**。

---

## Pre-flight Checklist

- [ ] SKILL.md Section 1a Pre-flight 全部通过
- [ ] `$VAULT`、`$PYTHON` 已从 bootstrap 获取
- [ ] 明确至少 2 个待比较维度（如模型/队列、刺激参数、关键结局、样本量、局限性）
- [ ] 遵循 `atoms/retrieval-routing.md` 单次 planner + 至多一次 fallback 协议

---

## 执行流程

### Step 1: 解析候选文献集合

1. 若用户未给出明确的 `<zotero_key>` 列表，通过 `query-plan` + `search --json` / `retrieve --deep --json` / `context --collection` 收集候选文献集合。
2. 展示候选清单与各篇 `fulltext_available` 状态，候选题过多（> 20）时请用户收窄后再做横向精比，不静默丢弃。

### Step 2: 逐篇抽取可核验上下文

对每篇纳入对比的 `<KEY>`：

```bash
$PYTHON -m paperforge --vault "$VAULT" paper-context <KEY> --structure --json
```

1. 检查 `data.user_annotations`：汇总研究者在该文献 PDF 上标记的 `evidence` / `method` / `quote` 高亮及 `questions` 待查项（含物理页码与 `section_path` / `figure_id`）。
2. 若 `data.paper.fulltext_available == true`，按对比维度执行定向混合检索（支持未建向量时自动回退 FTS5 BM25）：
   ```bash
   $PYTHON -m paperforge --vault "$VAULT" \
     retrieve "<dimension keywords>" --paper <KEY> --deep --limit 8 --json
   ```
3. 对返还的 `object` 命中（`figure` / `table`），按需执行 `atoms/retrieval-routing.md` §5 的 Contextual retrieve 补全作者正文解释。

### Step 3: 生成横向对比证据矩阵

按用户关切维度组织 Markdown 矩阵，每条主张附带可追溯出处（`<KEY>`、章节/图表编号、物理页码或 `ann_id`）：

```markdown
| 文献 (Key / Author Year) | 研究对象/模型 | 关键干预/参数 | 主要结果与定量指标 | 证据出处 (Section / Page / Annotation) | 局限与冲突点 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `<KEY>` Smith 2024 | ... | ... | ... | Results Fig.2 (p.5, ann_xxx) | ... |
```

在矩阵下方分两块总结：
1. **跨文献共识与参数边界**（仅基于已核验数据归纳区间与条件差异）
2. **方法学冲突、异质性与待核查缺口**（标注互相矛盾的结果及缺失数据）

### Step 4: Post-action 保存（可选）

若用户要求将矩阵或单条发现归档到项目知识库，跳转至 `molecules/capture-project-knowledge.md`（叙述矩阵走 `write-project-reading-log.md`，逐条引文走 `write-reading-log-jsonl.md` 或 `paperforge annotations promote`）。

---

## 禁止

- 禁止使用 `glob` / `grep` 扫 Vault 或绕过 CLI 自行拼接路径
- 禁止仅凭 stale `prior_notes` 填充证据矩阵单元格
- 禁止将“未报道该指标”写成“结果为阴性/无差异”
