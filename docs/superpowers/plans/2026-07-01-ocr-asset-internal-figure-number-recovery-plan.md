# Asset-Internal Figure Number Recovery Plan

> **来源:** U746UJ7G rotated figure — "Figure 2. Plot of Criteria Time..." 被吞进 chart asset bbox 内部，未成为独立 block。
> **目标:** 在 synthetic vector fallback 之后，对已存在但缺编号的 figure，从 asset bbox 内恢复 figure number。
> **原则:** 只写 metadata，不拆 OCR block，不污染正文。

---

## 问题

```
PDF rawdict line (dir=(0,-1)):
  [52,348→60,718] ← "Figure 2. Plot of Criteria Time..."

这个 line 的 bbox 完全在 chart asset bbox [105,134,967,1443] 内部
→ OCR assembly 把它归入 chart block，未产生独立 text block
→ 当前 prematch + synthetic fallback 产出 figure_unknown_000
→ 没有 figure_number，没有 Figure 2
```

---

## Implementation Amendments（开工前必读）

以下 9 个补丁来自 GPT 二审。不修则引入坐标不一致、duplicate gate 跳过、bare label 遗漏等 bug。

| # | 问题 | 修法 |
|---|------|------|
| 1 | 坐标系不写死 → line bbox 和 asset bbox 跨坐标系比较全部出错 | `page_pdf_lines_by_page` 传进来之前必须归一化到 OCR 坐标；line 格式写死含 `bbox` (OCR坐标) + `source_bbox_pdf` (仅debug) |
| 2 | `_INTERNAL_FIGURE_LABEL_PATTERN` 要求 `.+` → 拒掉裸 `Figure 2.` | 改为 `(?:\S.*)?`；长度门从 8→6 |
| 3 | 插入位置没说清 promotion/infer/collision 顺序 | recovery 放在 `promote` + `infer` **之后**，dedup/completeness/collision **之前** |
| 4 | 验收条件硬编码 `fig_2` → 和 `_format_figure_id` 真实输出不一致 | 改为 `_format_figure_id("figure", 2)` |
| 5 | duplicate gate 把当前 figure 自己也挡了 | 用 `enumerate` + `j != i` 排除当前索引 |
| 6 | recovery 需要 matched_assets bbox 才能工作 | 没有 `matched_assets` 或 `bbox` 就跳过，不用 `asset_block_ids` |
| 7 | 缺少 line inside/overlap gate 和大面积文本 rejection | 加 `_line_inside_or_overlaps_asset` + 面积占比 >0.15 时 reject |
| 8 | 没写要同步更新 `figure_namespace` | recovery 后同步 `namespace` + `figure_id` + `recovered_*` + flags 去重 |
| 9 | `_needs_...` 对 description 判断过宽（`"this figure" in text`） | 改为 `text.startswith("this figure ")` 或 `_FIGURE_DESCRIPTION_OPENING` |

---

## 解决方案

在 synthetic fallback 之后，加一个窄 pass：

> **只对 matched_figures 中缺 figure_number 且命中 weak/description 型 caption 的条目，扫描 matched asset 内部 PDF line，补 figure_number / recovered_label_text / figure_id。**

### 触发条件（必须全部满足）

**Amendment 9:**
```python
def _needs_asset_internal_figure_number_recovery(fig: dict) -> bool:
    if fig.get("figure_number") is not None:
        return False
    figure_id = str(fig.get("figure_id") or "")
    if not figure_id.startswith("figure_unknown") and not figure_id.startswith("synthetic_figure"):
        return False
    flags = set(fig.get("flags") or [])
    if not ("bbox_only_asset" in flags or "synthetic_vector_asset" in flags):
        return False
    text = str(fig.get("text") or "").strip()
    if not text:
        return False
    lower = text.lower()
    return (
        bool(_FIGURE_DESCRIPTION_OPENING.match(text))
        or lower.startswith("this figure ")
        or lower.startswith("the figure ")
    )
```

### 候选 line gate（被接受的概率极低）

**Amendment 2:** 接受裸 `Figure 2.` / `Fig. 2.` 标签。
```python
_INTERNAL_FIGURE_LABEL_PATTERN = re.compile(
    r"^(?:Figure|Fig\.?)\s+(\d+(?:\.\d+)?)(?:[A-Za-z])?"
    r"(?:[\.:]\s*)?(?:\S.*)?$",
    flags=re.IGNORECASE,
)

def _looks_like_internal_figure_label(text: str) -> bool:
    stripped = " ".join(text.split())
    if len(stripped) < 6 or len(stripped) > 200:
        return False
    if not _INTERNAL_FIGURE_LABEL_PATTERN.match(stripped):
        return False
    lower = stripped.lower()
    if re.match(r"^(?:figure|fig\.?)\s+\d+\s+(?:shows|showed|demonstrates|illustrates|indicates)\b", lower):
        return False
    return True
```

### 坐标系 contract（Amendment 1 — 最重要）

`page_pdf_lines_by_page` 里的 `bbox` **必须**已经归一化到和 `structured_blocks[*].bbox` 一致的坐标体系（OCR/render 坐标系）。PDF rawdict 坐标不可直接比较。

```python
line_record = {
    "page": 8,
    "text": "Figure 2. Plot of Criteria Time...",
    "bbox": [104, 696, 120, 1436],             # OCR / render 坐标
    "source_bbox_pdf": [52, 348, 60, 718],     # 仅 debug
    "dir": (0.0, -1.0),
    "source": "pdf_rawdict_line",
}
```

**在 helper 内强约束：**
```python
# line["bbox"] 和 asset bbox 处于同一坐标体系。
# 永远不要拿 source_bbox_pdf 和 OCR block bbox 做比较。
```

### 几何 gate

**Amendment 7:** 加 inside/overlap + 大面积文本 rejection。

```python
def _line_inside_or_overlaps_asset(line_bbox, asset_bbox) -> bool:
    lx1, ly1, lx2, ly2 = line_bbox
    ax1, ay1, ax2, ay2 = asset_bbox
    line_area = max(1.0, (lx2 - lx1) * (ly2 - ly1))
    ix1, iy1 = max(lx1, ax1), max(ly1, ay1)
    ix2, iy2 = min(lx2, ax2), min(ly2, ay2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    cx = (lx1 + lx2) / 2
    cy = (ly1 + ly2) / 2
    center_inside = ax1 <= cx <= ax2 and ay1 <= cy <= ay2
    return center_inside or (inter / line_area) >= 0.7


def _asset_edge_band_score(line_bbox, asset_bbox) -> float:
    lx1, ly1, lx2, ly2 = line_bbox
    ax1, ay1, ax2, ay2 = asset_bbox
    asset_w = max(1.0, ax2 - ax1)
    asset_h = max(1.0, ay2 - ay1)
    # 大面积文本 rejection：line 覆盖超过 15% asset → 不是 label
    line_w = lx2 - lx1
    line_h = ly2 - ly1
    if (line_w * line_h) / (asset_w * asset_h) > 0.15:
        return 0.0
    cx = (lx1 + lx2) / 2
    cy = (ly1 + ly2) / 2
    left_dist = abs(cx - ax1)
    right_dist = abs(cx - ax2)
    top_dist = abs(cy - ay1)
    bottom_dist = abs(cy - ay2)
    edge_dist = min(left_dist / asset_w, right_dist / asset_w,
                    top_dist / asset_h, bottom_dist / asset_h)
    if edge_dist <= 0.08:
        return 1.0
    if edge_dist <= 0.15:
        return 0.7
    if edge_dist <= 0.25:
        return 0.4
    return 0.0
```

`edge_score > 0` 作为硬要求。

### 去重 gate（Amendment 5）

当前索引排除自己，避免把自己挡掉：
```python
for idx, fig in enumerate(matched_figures):
    existing_numbers = {
        (other.get("figure_namespace") or "figure", other.get("figure_number"))
        for j, other in enumerate(matched_figures)
        if j != idx and other.get("figure_number") is not None
    }
```

### 多候选 gate + 匹配 asset 条件（Amendment 6）

```python
def _iter_matched_figure_assets(fig: dict) -> list[dict]:
    assets = fig.get("matched_assets") or []
    return [a for a in assets if a.get("bbox") and len(a.get("bbox", [])) >= 4]
```

只有 `matched_assets` 有 valid bbox 时才 recovery。不靠 `asset_block_ids` 全局查找。

同一 asset 内扫到多个不同 `Figure N` → 不补：
```python
numbers = {(c["figure_namespace"], c["figure_number"]) for c in recovered_candidates}
if len(numbers) > 1:
    continue
```

---

## 插入位置（Amendment 3）

最稳的位置是：**所有可能新增/修改 matched_figures 的步骤之后；final dedup / completeness / id collision 之前。**

```python
inventory = { ... }

inventory = _promote_sequence_matches(inventory, structured_blocks)
inventory = _infer_missing_main_figure_numbers(inventory, structured_blocks)

# Recovery pass: 对已有但缺编号的 figure 从 asset 内恢复编号
_recover_missing_figure_numbers_from_assets(
    inventory=inventory,
    page_pdf_lines_by_page=page_pdf_lines_by_page,
)

_dedup_unmatched_assets_against_matched_figures(inventory)
_dedup_unresolved_clusters_against_matched_figures(inventory)

inventory["figure_legend_completeness"] = compute_figure_legend_completeness(...)
_resolve_figure_id_collisions(inventory)
```

不要只放在 pre-inventory list 层面做。否则后面的 promotion/infer 又产生 unknown/synthetic figure 就覆盖不到。

---

## 需要什么输入

`build_figure_inventory` 当前签名：

```python
def build_figure_inventory(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]:
```

需要透传 `page_pdf_lines_by_page: dict[int, list[dict]] | None = None`。
由调用方（`ocr_rebuild.py`）构建，不在 `ocr_figures.py` 里打开 PDF。

---

## 输出 modification

**Amendment 8:** 同时更新 `figure_namespace` + `recovered_*` + 去重 flags。

```json
{
  "figure_id": "fig_2",
  "figure_number": 2,
  "figure_namespace": "figure",
  "text": "This figure demonstrates...",
  "recovered_label_text": "Figure 2. Plot of Criteria Time",
  "recovered_label_bbox": [104, 696, 120, 1436],
  "figure_number_source": "asset_internal_pdf_line",
  "flags": [
    "synthetic_vector_asset",
    "bbox_only_asset",
    "figure_number_recovered_from_asset_text"
  ]
}
```

修改：

- `figure_id` → 用 `_format_figure_id(ns, number)` 生成
- `figure_number` → 补上数字
- `figure_namespace` → 同步更新（Amendment 8）
- 新增 `recovered_label_text` / `recovered_label_bbox` / `figure_number_source`
- flags 去重追加 `figure_number_recovered_from_asset_text`

```python
fig["figure_namespace"] = recovered["figure_namespace"]
fig["figure_number"] = number
fig["figure_id"] = _format_figure_id(ns, number)
fig["recovered_label_text"] = recovered["text"]
fig["recovered_label_bbox"] = recovered["bbox"]
fig["figure_number_source"] = "asset_internal_pdf_line"
fig["flags"] = list(dict.fromkeys((fig.get("flags") or []) + [
    "figure_number_recovered_from_asset_text"
]))
```

---

## 验收标准（Amendment 4 — 用 _format_figure_id）

| 场景 | 条件 |
|------|------|
| U746UJ7G Figure 2 | `figure_number == 2`, `figure_id == _format_figure_id("figure", 2)`, `recovered_label_text` 包含 "Plot of Criteria Time", flags 含 `figure_number_recovered_from_asset_text` |
| 正常 figure（已编号） | 不被此 pass 影响，no-op |
| 无候选 line 的 synthetic figure | 保持 `figure_unknown_NNN`，无副作用 |
| 已有 Figure 2 在 inventory 中 | 不再给第二个 `number=2` |

---

## 测试要求

| # | 场景 | 验证点 |
|---|------|--------|
| 1 | synthetic unknown + asset-internal Figure 2 line | recovery 成功，`figure_number == 2` |
| 2 | 已有 Figure 2 在 matched_figures | 当前 unknown 不补 2 |
| 3 | 正常已编号 figure | 不受影响 |
| 4 | asset 内多个不同 Figure N | 不补 |
| 5 | line 在 asset 中央不在 edge band | 不补 |
| 6 | line bbox 坐标归一化（PDF vs OCR） | 测试明确预期坐标转换后的行为 |

测试文件：`tests/test_ocr_figures.py`（recovery helper）+ `tests/test_ocr_pdf_spans.py`（若 page_pdf_lines 构建有独立逻辑）。

---

## 文件变更

| 文件 | 变更 |
|------|------|
| `paperforge/worker/ocr_figures.py` | 新增 helper + pattern + recovery pass；`build_figure_inventory` 签名增加可选 `page_pdf_lines_by_page` |
| `paperforge/worker/ocr_rebuild.py` | 构建 `page_pdf_lines_by_page` 并传入 `build_figure_inventory` |
| `tests/test_ocr_figures.py` | 6 条 recovery pass 测试 |
| `tests/test_ocr_pdf_spans.py`（推荐） | page_pdf_lines 构建独立测试 |

---

## Commit 消息

```
feat: recover figure number from asset-internal PDF lines

When a synthetic/weak figure entry lacks a figure_number,
scan the matched asset bbox for formal "Figure N." PDF lines.
Only triggers for caption-description figures with bbox_only
or synthetic_vector flags. Writes metadata only
(recovered_label_text, figure_number_source) — no block splitting.
```

---

## 分步实现

1. 在 `ocr_figures.py` 加 pattern + gate 函数
2. 加 `_recover_asset_internal_figure_number` 主函数
3. 加 `_recover_missing_figure_numbers_from_assets` 作为 inventory pass
4. 加 `build_figure_inventory` 可选参数
5. `ocr_rebuild.py` 构建 page_pdf_lines 并传入
6. 测试（6 条 + 坐标归一化）
7. 重建 U746UJ7G 验证
