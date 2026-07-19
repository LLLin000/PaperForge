# PR-2 & PR-3 Implementation Plan (修正版 v2)

> 基于审计反馈修正。核心问题：当前 `build_figure_inventory()` 已走 vnext pipeline，plan 不能写 legacy 思路。

---

## 全局前置：补 vnext completeness normalization

**改 `ocr_health.py`**，在 PR-2/PR-3 之前修好兼容层，否则后续验证口径都是错的。

当前 health 读的是：
```python
figure_inventory.get("figure_legend_completeness", {}).get("total", 0)
```
但 vnext 输出的是：
```python
figure_inventory["completeness"]["total_numbered_legends"]
```

加兼容函数：
```python
def _figure_completeness(figure_inventory: dict) -> dict:
    c = (
        figure_inventory.get("figure_legend_completeness")
        or figure_inventory.get("completeness")
        or {}
    )
    return {
        "total": int(c.get("total", c.get("total_numbered_legends", 0)) or 0),
        "accounted_for": int(c.get("accounted_for", 0) or 0),
        "gap_count": int(c.get("gap_count", 0) or 0),
    }
```

**验证：** `test_figure_completeness_backward_compat()`、`test_figure_completeness_vnext_format()`

---

## PR-2b：Continued Caption（先做，风险低）

### 改动点

| 不要做的 | 要做的 |
|---------|-------|
| 改 legacy dedup loop | 改 vnext pipeline |
| 在 `(ns, fn)` 去重阶段插入 | 在 `FigureCandidateIndex` 或新 pass 中处理 |
| 复用原 `figure_id` | 生成唯一 continuation_id，用 `continuation_of` 指向主图 |

### 具体步骤

**1. helpers（`ocr_figures.py`）**

```python
_FIGURE_CONTINUATION_PATTERN = re.compile(
    r"\(\s*cont(?:inued)?\.?\s*\)|\bcontinued\b", re.I,
)

def _is_figure_continuation_caption(text: str) -> bool:
    return bool(_FIGURE_CONTINUATION_PATTERN.search(text or ""))

def _extract_base_figure_number(text: str) -> int | None:
    cleaned = _FIGURE_CONTINUATION_PATTERN.sub("", text or "").strip()
    return _extract_figure_number(cleaned)
```

**2. 标记 continuation legends（`FigureCandidateIndex.from_corpus()`）**

在构建 `formal_legends` 时，对每个 legend 检查是否 continuation。如果是，设置：
```python
legend["_figure_continuation"] = True
legend["_continuation_base_number"] = _extract_base_figure_number(text)
```

**3. 新增 ContinuationCaptionPass**

放在 `PrimarySamePagePass` **之前**。原因：如果 continuation caption 先被 PrimarySamePagePass 处理，它会被当成普通 "Figure 1" 产出一个新 figure_id。

- Same-page continuation：同页找 group，几何匹配，claim assets
- Cross-page continuation：只允许 page±1，无 strong interruption
- 匹配记录：
```python
{
    "figure_id": "figure_001_continued_p005_b012",   # 唯一
    "figure_number": 1,
    "continuation_of": "figure_001",
    "is_continuation": True,
    "settlement_type": "continuation_same_page" | "continuation_cross_page",
}
```

**4. vnext 注册 pass**

在 `build_figure_inventory_vnext()` 的 pass 序列中插入 `ContinuationCaptionPass`。

### 测试

```python
def test_cont_caption_detected_and_marked_in_candidate_index():
def test_cont_caption_matches_same_page_visual_group():
def test_cont_caption_cross_page_links_correctly():
def test_cont_caption_has_unique_id_not_base_figure_id():
```

### 验证 paper

9DM6MCIF（3 unmatched legends 含 "(Continued)"）、XGT9Z257

---

## PR-2a：Short Caption Geometry（后做，风险中）

### 改动点

| 不要做的 | 要做的 |
|---------|-------|
| 改 `ocr_scores.score_figure_match()` | 改 `_score_legend_to_group()` 或新增 ShortCaptionGeometryPass |
| 新增 `_FIGURE_SHORT_CAPTION_PATTERN` | **复用已有 `_TRUNCATED_LEGEND_ONLY_PATTERN`** |
| 全局降低阈值 | 窄门：zone/style/raw_label 三重验证 |

### 具体步骤

**1. helper（`ocr_figures.py`）**

复用现有的 `_TRUNCATED_LEGEND_ONLY_PATTERN`（匹配 "Figure N" 或 "Fig. N" 无描述文字），加 zone/style/raw_label gate：

```python
def _is_short_numbered_figure_caption(block: dict) -> bool:
    text = str(block.get("text") or "").strip()
    if not _TRUNCATED_LEGEND_ONLY_PATTERN.fullmatch(text):
        return False
    return (
        str(block.get("zone") or "") == "display_zone"
        or str(block.get("style_family") or "") == "legend_like"
        or str(block.get("raw_label") or "") == "figure_title"
    )
```

**2. 匹配逻辑（`_score_legend_to_group()` 或新 pass）**

不在 `score_figure_match()` 中修改（它没有 group-level 上下文）。

在 `_score_legend_to_group()` 或 `PrimarySamePagePass` 中加 short-caption branch：

```python
if _is_short_numbered_figure_caption(legend):
    # 必须同页
    # group 与 legend 同 column 或 x-overlap
    # vertical gap <= 220 px
    # 若当前页有多个 numbered legends，仅当 column-local 唯一时生效
    # 返回 score 0.62-0.70
    # evidence 标记 "short_caption_geometry"
```

**3. 约束条件**

- 不跨页
- 不用文本相似度
- 当前页有多个竞争 numbered legends 时不生效

### 测试

```python
def test_short_numbered_caption_matches_nearest_same_column_group():
def test_short_caption_does_not_cross_match_two_column_neighbor():
def test_short_caption_with_multiple_groups_without_column_evidence_is_held():
```

### 验证 paper

6QNRHRKX（0/7 matched → 预期改善）

---

## PR-3：Status Split

### 改动点

| 不要做的 | 要做的 |
|---------|-------|
| `overall_status` 新字段 | 保持 `overall` 不变，加新维度字段 |
| `figure_caption_count` 作分母 | 用 vnext `completeness.total_numbered_legends`（就是前置 step 的归一化结果） |

### 产出字段

```python
report["overall"] = overall                               # 不变
report["structure_status"] = structure_status
report["figure_status"] = figure_status
report["table_status"] = table_status
report["dimension_statuses"] = {
    "structure": structure_status,
    "figure": figure_status,
    "table": table_status,
}
report["status_reasons"] = [
    {"scope": "structure", "reason": "..."},
    {"scope": "figure", "reason": "..."},
]
```

### figure_status 计算

```python
def _compute_figure_status(figure_inventory: dict) -> tuple[str, list[str]]:
    c = _figure_completeness(figure_inventory)
    total = c["total"]
    accounted = c["accounted_for"]
    gaps = c["gap_count"]

    if total == 0:
        return "green", ["no_numbered_figures"]

    ratio = accounted / total
    if gaps == 0 and ratio >= 0.9:
        return "green", [f"figure_accounting_ok:{accounted}/{total}"]
    if ratio >= 0.6:
        return "yellow", [f"partial_figure_accounting:{accounted}/{total}"]
    return "red", [f"poor_figure_accounting:{accounted}/{total}"]
```

### 验证 paper

SWDN9RHF（structure=red, figure=green）、V4UTP5X7（structure=red, figure=green）

---

## 执行顺序（修正版）

| Step | 内容 | 文件 | 风险 |
|------|------|------|------|
| **0** | vnext completeness normalization | `ocr_health.py` | 低（兼容层） |
| **1** | Continued caption 处理 | `ocr_figures.py` + vnext pass | 低 |
| **2** | Short caption geometry | `ocr_figures.py` + `_score_legend_to_group()` | 中 |
| **3** | Status split | `ocr_health.py` | 低 |

Step 0 必须在 1/2 之前，否则验证口径不对。
Step 1 在 2 之前（风险低，先验证 vnext pass 注册机制）。
