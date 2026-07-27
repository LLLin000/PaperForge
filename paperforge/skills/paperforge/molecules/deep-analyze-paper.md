# deep-analyze-paper

> [!warning] Safety Rules
> - **禁止主动加 `--force`** — 只有用户明确要求重读时才能用
> - **禁止猜测 `--figures N`** — N 必须来自 Step 1 prepare 输出的实际数字
> - **禁止重复跑 `prepare`** — prepare 只跑一次。跑了两次以上 → 检查 note 结构是否被破坏
> - 不要在 Pass 1 完成前碰 Pass 2/3
> - 不要把推断写成文献事实——区分"作者说了 X"和"我推断 Y"
> - 不要跨 figure 写综合判断（Pass 2 逐图，Pass 3 才做综合）
> - validate 失败超过 3 轮 → 执行自查清单，不要盲目重试

Keshav 三阶段精读。在 formal note 中写入结构化的 `## 精读` 区域。

> 检索决策由 `atoms/retrieval-routing.md` 决定。StructureTree 在本 molecule 中作为导航地图使用。

---

## Pre-flight Checklist

- [ ] SKILL.md Section 1a Pre-flight 全部通过
- [ ] `$VAULT`、`$PYTHON` 已从 bootstrap 获取
- [ ] OCR status 为 `done`（否则无法精读）
- [ ] intent 已确定为 `deep_analyze_paper`

---

## 入口：定位论文（如果需要）

如果尚未有唯一 zotero_key，先定位：

```bash
$PYTHON -m paperforge --vault "$VAULT" \
  query-plan "<identifier>" \
  --intent locate --json
```

执行 `data.primary`（同 `atoms/retrieval-routing.md` §2–§3）。多候选则让用户选择。

获得唯一 KEY 后进入 Step 0。

如果已有唯一 KEY，直接进入 Step 0。

### Step 0: paper-context with StructureTree

```bash
$PYTHON -m paperforge --vault "$VAULT" \
  paper-context <zotero_key> --structure --json
```

检查返回 JSON：

- `ok: false` → 报告 `error.message`，停止
- `data.paper.ocr_status != "done"` → "OCR 未完成，请先运行 paperforge ocr"，停止
- `data.paper.analyze != true` → "analyze 未开启，请在 formal note frontmatter 中设为 true"，停止

**检查 structure：**

```text
data.structure == null → 章节树暂不可用
  → 继续原有 fulltext + pf_deep.py 工作流
  → 不使用 node/path 导航
  → 不终止精读
  → structure_available = false
```

data.structure 非 null 时，读取 StructureTree：

```text
data.structure.version   — 结构版本（与检索结果中的 structure_version 对照）
data.structure.nodes[]   — 章节导航地图

每个 node 包含：
  node_id               — 节点 ID
  parent_id             — 父节点 ID（null = root）
  title                 — 章节标题
  path                  — 章节路径数组
  depth                 — 深度
  own_block_count       — 本节点包含的 block 数
  page_span             — 跨页范围
  document_order        — 文档内顺序
structure_available = true
```

StructureTree 是**导航地图，不是全文内容替代品**。用于确定章节父子关系、document order、判断 evidence 所在章节。

**不要硬编码英文章节标题。** 优先识别 Methods / Results / Discussion 语义角色；
找不到标准标题时，按 `document_order` 和 `path` 判断。很多论文使用 Materials and Methods、Experimental、Findings 等变体。
详细内容仍由 `pf_deep.py prepare`、fulltext、figure/table 素材、chart-reading atom 提供。

**检查 prior_notes：**

- 如果存在 `data.prior_notes`，逐条看 `verified` 字段
- `verified: false` 的条目记入 recheck_targets，精读时必须回原文复核
- `verified: true` → 可作为已核过的历史记录和复查优先级；**仍不能脱离原文直接回答事实问题**（见 SKILL.md §5 Reading-Log Safety Rule）

**记录关键路径：**

- `data.paper.note_path`
- `data.paper.fulltext_path`
- `data.structure.version`（仅当 structure 非 null）
- `data.structure.nodes`（仅当 structure 非 null）
- `structure_available`
- `recheck_targets`

---

## 执行流程

### Step 1: Prepare（跑脚本）

```bash
$PYTHON "$SKILL_DIR/scripts/pf_deep.py" prepare --key <zotero_key> --vault "$VAULT"
```

> [!warning] `--force` 禁止在精读过程中使用。仅在用户明确要求重读时才能用。

解析返回 JSON：

- `status: "ok"` → 记下 `figures`、`tables`、`figure_map`、`chart_type_map`、`formal_note`、`fulltext_md` 路径
- `status: "warn"` + `deep_reading_status: done` → 告知用户"该文献已精读过"，确认是否重读
- `status: "error"` → 报告 `message`，停止

记下 `figures` 数量——Step 4 要用。读 formal note，确认 `## 精读` 骨架已插入。

---

### Step 2: Pass 1 — 概览

只填 `### Pass 1: 概览`。不碰 Pass 2/3。

填写内容必须来自原文，不可推断：

- **一句话总览**：论文类型 + 核心发现
- **5 Cs 快速评估**：Category / Context / Correctness / Contributions / Clarity
- **Figure 导读**基于 fulltext 浏览各图 caption：
  - 关键主图、证据转折点、需展开的 supplementary、关键表格

填完立即保存。

---

### Step 3: Pass 2 — 精读还原

填 `### Pass 2: 精读还原`。按 figure 顺序逐个处理，每处理完一个立即保存。

#### 图表类型定位

读 chart-type-map → Agent 读 caption 做最终判断（打开 `atoms/chart-reading/INDEX.md`）。

#### 每张 Figure 的子标题

```
**图像定位与核心问题**：页码 + 要回答什么问题
**方法与结果**：实验设计 / 核心数据 / 趋势 / 对比
**图表质量审查**：按 chart-reading 指南检查坐标轴、单位、误差棒、统计标注
**作者解释**：作者在正文中对该图的解读
**我的理解**：必须与作者解释做明显区分
**疑点/局限**：用 `> [!warning]` 突出
```

#### 每张 Table 的子标题（简化版）

```
回答什么问题、关键字段/分组、主要结果、我的理解、疑点/局限
```

#### 跨章节定向检索

在每个 Pass 内可用 retrieve 做定向提取：

```
# Pass 2 中需要确认具体参数时
$PYTHON -m paperforge --vault "$VAULT" \
  retrieve "experimental design" --paper <KEY> --deep --json

$PYTHON -m paperforge --vault "$VAULT" \
  retrieve "main findings" --paper <KEY> --deep --json
```

但不能只依赖 top-k retrieve 宣称已经完整分析整篇。

#### 所有 figure/table 处理完后

关键方法补课 + 主要发现与新意（每条标注 Figure/Table 来源）。

---

### Step 4: Postprocess

```bash
$PYTHON "$SKILL_DIR/scripts/pf_deep.py" postprocess-pass2 "<formal_note_path>" --figures <N>
```

- `OK` → 继续 Step 5
- 错误列表 → 按提示修正，修正后重新跑
- 最多 3 轮修正

---

### Step 5: Pass 3 — 深度理解

填 `### Pass 3: 深度理解`。基于 Pass 1/2 已写内容。

- 假设挑战与隐藏缺陷
- 哪些结论扎实，哪些仍存疑（`> [!warning]`）
- Discussion 与 Conclusion 怎么读
- 对自己的启发
- 遗留问题（`> [!question]`）

---

### Step 6: Final Validation

```bash
$PYTHON "$SKILL_DIR/scripts/pf_deep.py" validate-note "<formal_note_path>" --fulltext "<fulltext_path>"
```

- `OK` → 告知用户精读完成
- 错误 → 修正缺失项，直到通过（最多 3 轮）

---

## Callout 格式规则

- `> [!important]` — 每个 main finding
- `> [!warning]` — 疑问、局限、证据边界
- `> [!question]` — 遗留问题
- 相邻 callout 之间必须有空行

### Post-action: 保存/归档

如果用户要求保存精读成果到项目知识库，跳转至 `capture-project-knowledge.md`。
