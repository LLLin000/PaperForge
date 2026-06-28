# 5 OCR Fixes from Vision Audit Remediation

> **Date:** 2026-06-27
> **Source:** 5-paper vision truth audit (NC66N4Q3, 25K5KZAQ, 9TW98JH8, YGH7VEX6, XD2BPCMG)
> **Status:** v2 after review

---

## 实施拆分

| 包 | Fixes | 类型 |
|----|-------|------|
| **P0 quick fixes** | Fix 2 + Fix 4 + Fix 5 | bug patches, 可单独落地 |
| **P1 layout cleanup** | Fix 1 + Fix 3 (separate spec) | 结构性变更, 分开做 |

**P0 三件套可以同时 commit，但每条改动是独立的。** Fix 3 拆成单独 spec。

---

# P0 QUICK FIXES

---

## Fix 2: Reference Number Sort — Support Bracket Format `[N]`

### Problem
`_ref_number_sort_key` (`ocr_render.py:481`) regex `r"^\s*(\d+)[\.\)]"` 不匹配 `[N]`。`[10]` 排在 `[2]` 前面。

### Implementation

```python
# ocr_render.py:481
def _ref_number_sort_key(block: dict) -> tuple:
    text = str(block.get("text") or block.get("block_content") or "")
    m = re.match(r"^\s*(?:\[(\d+)\]|(\d+)[\.\)])\s*", text)
    if m:
        return (0, int(m.group(1) or m.group(2)))
    return (1, text)
```

只接受：
- `[1] Author...` → 1
- `1. Author...` → 1  
- `1) Author...` → 1

不接受 `2024 something`（没有 bracket 或 dot/paren 的数字不匹配）。

### Risk
None.

---

## Fix 4: Remove `figure_caption` from Non-Body Insert Candidate Set

### Problem
`_detect_non_body_insert_clusters` (`ocr_document.py:3846`) 的 `_INSERT_CANDIDATE_ROLES` 包含 `figure_caption` 和 `figure_caption_candidate`。当 caption 宽度略窄于 body median + 字体不同时（caption 常用小字/斜体），被误杀为 `non_body_insert`。

YGH7VEX6 Figure 2: 宽度 442px vs median 507px (threshold 456)。差 14px 导致 Figure 2 在整个 pipeline 中不可见。

### Implementation

```python
# BEFORE
_INSERT_CANDIDATE_ROLES = {
    "body_paragraph",
    "figure_caption",
    "figure_caption_candidate",
    "unknown_structural",
}

# AFTER
_INSERT_CANDIDATE_ROLES = {
    "body_paragraph",
    "unknown_structural",
}
```

同时更新 docstring：删除"figure_caption is included because PaddleOCR sometimes labels narrow author-bio side-panel blocks as figure_title/figure_caption"这一段，避免后续维护误导。

### Risk
Minimal。原假设（PaddleOCR 误标）无证据。如果真的误标，会从 `body_paragraph` 或 `unknown_structural` 通道走，family-profile rescue 仍然能兜底。

---

## Fix 5: Caption Matching — Filter Demoted Body Paragraphs from Legends

### Problem
被 `candidate_resolution` 降级为 `body_paragraph` 的块（原 `figure_caption_candidate`）仍然在 `figure_legends` 中，通过 `is_validation_first_candidate` 参与匹配，可抢占真 caption 的主 slot。

YGH7VEX6 Figure 11: 正文 p6:7（"Figure 11 shows..."）通过 `adjacent_x` 绑定左栏 assets，抢了 `figure_011`。真 caption p6:13 被踢到 `figure_s011`。

### Design — legend collection 入口过滤，不改 renderer

在 `build_figure_inventory()` 的 legend collection 循环中，`is_validation_first_candidate` 之前加：

```python
if block.get("role") == "body_paragraph" and block.get("seed_role") == "figure_caption_candidate":
    rejected_legends.append({
        "page": block.get("page"),
        "block_id": block.get("block_id", ""),
        "text": block.get("text", ""),
        "role": block.get("role", ""),
        "seed_role": block.get("seed_role", ""),
        "rejection_reason": "demoted_body_caption_candidate",
    })
    continue
```

位置：在 `build_figure_inventory()` 的 `for block in structured_blocks` 循环中，
1. 跳过 `_non_body_media` / `non_body_insert` 后
2. 跳过 panel label 后
3. **计算 `is_validation_first_candidate` 之前**

**不设置 `render_default=false` / `index_default=false`。** 这些块仍然是正常正文内容（"Figure 11 shows..."），应该在 fulltext 中保留。

---

# P1 LAYOUT CLEANUP

---

## Fix 1: Figure-Internal Text Containment Detection

### Problem
文本块在空间上位于复合多图 bbox 内（panel labels、composition data、function labels），但未被识别为图内文字。泄漏到 fulltext 中成为 `##` 标题。

Page 3 of XD2BPCMG: 21 个文字块在 Figure 1 的 composite bbox 内，全部误标。

### Design

新增 `_bind_inner_text_to_matched_figures()`，在 `build_figure_inventory()` 之后调用。

**复用基础：**
- `is_embedded_figure_text()` 已有初步逻辑（检查 block centroid 是否落在 figure/media asset 内，或窄文本与 asset 横向重叠）
- `matched_figures[].cluster_bbox` 已有
- `_bbox_contains` (`ocr.py:833`) 已有

**实现：**

```
function _bind_inner_text_to_matched_figures(blocks, matched_figures):
    for mf in matched_figures where mf.status == "matched":
        fig_bbox = mf.get("cluster_bbox")  # 优先使用
        if not fig_bbox:
            assets = [b for b in blocks if b.id in mf.asset_block_ids]
            fig_bbox = _cluster_bbox(assets)
        
        # guard: 跳过 page_area_ratio > 0.80 AND asset_fill_ratio very low 的假大框
        page_area = page_width * page_height
        bbox_area = (fig_bbox.x2 - fig_bbox.x1) * (fig_bbox.y2 - fig_bbox.y1)
        if page_area > 0 and bbox_area / page_area > 0.80:
            asset_bboxes = [b.bbox for b in assets]
            asset_area_sum = sum((b.x2-b.x1)*(b.y2-b.y1) for b in asset_bboxes)
            if asset_area_sum / bbox_area < 0.3:
                continue  # 大框里没填满，可能是跨页合并
        
        for block in same_page_blocks:
            if block.role in PROTECTED_ROLES: skip
            if _bbox_contains(fig_bbox, block.bbox, margin=10):
                block["role"] = "figure_inner_text"
                block["render_default"] = False
                block["index_default"] = False
```

**PROTECTED_ROLES**（不覆盖）：
- `figure_caption`, `figure_caption_candidate`, `table_caption`
- `paper_title`, `authors`, `abstract_heading`, `abstract_body`
- `reference_heading`, `reference_item`, `backmatter_heading`, `backmatter_body`
- `noise`, `page_header`, `page_footer`

**注意：** 这是 render-hygiene pass，不是匹配防护。`build_figure_inventory()` 内部的 panel-title suppression 仍然是 legend 匹配的首道防线。本函数只解决 fulltext 泄漏问题。

### Placement

在 `build_figure_inventory()` 返回后、`render_fulltext_markdown()` 之前。**不放在 `normalize_document_structure` 内**——此时 `matched_figures` 还不存在。

```text
orchestration:
    structured_blocks = build_document_structure(raw_blocks)
    figure_inventory = build_figure_inventory(structured_blocks)
    _bind_inner_text_to_matched_figures(structured_blocks, figure_inventory)  # ← 在这里
    render_fulltext_markdown(structured_blocks, figure_inventory, ...)
```

Helper 定义在 `ocr_figures.py` 或专用 postprocess 模块。

---

## Fix 3: Reference-Boundary Backmatter Redesign

**不在此 spec 中实施。** 拆为独立 spec，需覆盖：

1. 找 verified `reference_heading` / `reference_zone`
2. `reference_heading` 之前：禁止 backmatter role promotion
3. `reference_zone` 内：保留 `reference_heading` / `reference_item`
4. `reference_zone` 之后：
   - same-page below reference zone end：可进入 `post_ref_backmatter`
   - later pages：可进入 `post_ref_backmatter`
5. renderer `_reorder_tail_run()` 同步改，不再按旧 `backmatter_boundary_heading` 分组
6. 不能简单"reference_heading 后全是 backmatter"——reference list 本身在 heading 后面，`reference_zone` / `reference_item` 优先

当前代码的 tail/backmatter 逻辑分布在 `_promote_tail_body_candidates`、`_assign_tail_spread_ownership`、`_reorder_tail_run` 等，不是按几个函数名删能搞定的。需要单独设计和测试。

---

## Verification Plan

| Fix | Verification |
|-----|-------------|
| Fix 2 | 25K5KZAQ fulltext references: `[1],[2],[3],...,[10],[11],...` 正确数字顺序 |
| Fix 4 | YGH7VEX6 Figure 2 caption role = `figure_caption`，matched figure 有正确 legend |
| Fix 5 | YGH7VEX6 Figure 11: `figure_011` 用 p6:13（真 caption），无 `figure_s011` 条目。p6:7 仍在 fulltext 正文中 |
| Fix 1 | XD2BPCMG page 3: `(b) Type of cartilage` role = `figure_inner_text`，不在 fulltext 中作为 heading |
| Fix 3 | 单独 spec，单独验证 |

### Test commands

```bash
python -m pytest tests/ -v --tb=short -k "non_body_insert or reference_sort or caption_matching"
python .opencode/skills/paperforge-development/scripts/ocr_truth_audit.py YGH7VEX6 --refresh-artifacts --source-root D:/L/OB/Literature-hub/System/PaperForge/ocr
# verify figure_inventory.json for Figure 2 (matched) and Figure 11 (legend=block 13)
```
