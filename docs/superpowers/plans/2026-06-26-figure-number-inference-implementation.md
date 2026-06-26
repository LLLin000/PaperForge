# Figure Number Inference — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `subagent-driven-development` or `executing-plans`.

**Goal:** Add `_infer_missing_main_figure_numbers()` to `build_figure_inventory()` that fills `figure_number: None` for matched main-sequence figures when a single leading gap (Figure 1) can be inferred with high confidence. Motivation: N6XCZD25 lost "Figure 1." text in OCR, producing `figure_unknown_005`.

**Primary Spec:** `docs/superpowers/specs/2026-06-26-figure-number-fallback-by-sequence-design.md`

---

## 1. Stage Boundary

This plan:
- Adds one new function: `_infer_missing_main_figure_numbers()`
- Adds one new helper: `_extract_figure_marker()` (structured marker parser)
- Adds one new helper: `_resolve_legend_bbox()` (3-tier lookup)
- Adds one module-level constant: `_FRONTMATTER_VISUAL_VETO`
- Mutates only `matched_figures` and `figure_legends` entries in the inventory dict
- Accepts `inventory` (already assembled) and returns updated `inventory`

This plan does NOT:
- Touch the main matching loop
- Touch `_promote_sequence_matches()`
- Touch renderer or reader
- Touch `compute_figure_legend_completeness()`

---

## 2. Non-Negotiable Constraints

- Do NOT mutate `marker_signature` on any legend entry.
- Do NOT infer supplementary/extended_data namespaces.
- Do NOT infer middle gaps, multiple leading gaps, or end gaps — first release only handles the single leading `[1]` gap.
- Do NOT skip inference silently — always write `inventory["figure_number_inference"]` with reason.
- If `legend_bbox` is not resolvable after 3-tier fallback, do NOT infer.

---

## 3. File Map

| File | Responsibility |
|------|---------------|
| `paperforge/worker/ocr_figures.py` | New function + helpers + constant + integration point in `build_figure_inventory()` |
| `tests/test_ocr_figures.py` | All new tests |

---

## 4. Implementation Tasks

### Task 1: Add `_FRONTMATTER_VISUAL_VETO` constant

**File:** `paperforge/worker/ocr_figures.py`

```python
_FRONTMATTER_VISUAL_VETO = (
    "graphical abstract",
    "toc",
    "table of contents",
    "highlights",
    "available with this article",
    "supplementary data",
    "supporting information",
    "video abstract",
    "visual abstract",
)
```

Module-level, near top of file with other constants.

---

### Task 2: Add `_extract_figure_marker()` helper

**File:** `paperforge/worker/ocr_figures.py`

Returns a structured dict:

```python
def _extract_figure_marker(text: str) -> dict:
    return {
        "namespace": "main" | "supplementary" | "extended_data",
        "number": int | None,
        "raw_prefix": str,
        "has_s_prefix": bool,
        "marker_text": str,
    }
```

Rules:
- Match against existing `_FIGURE_NUMBER_PATTERN` (or equivalent regex)
- If text contains `supplementary`, `supporting`, `additional file`, `appendix` → namespace=supplementary
- If text contains `extended data`, `extended figure` → namespace=extended_data
- If matched prefix has `S` immediately before digit (case-insensitive) → has_s_prefix=True, namespace=supplementary
- Otherwise namespace=main

This REPLACES `_extract_figure_number()` for building the known-number set in the inference pass. The old function can remain for other callers.

---

### Task 3: Add `_resolve_legend_bbox()` helper

**File:** `paperforge/worker/ocr_figures.py`

```python
def _resolve_legend_bbox(
    matched_item: dict,
    structured_blocks: list[dict],
    inventory: dict,
) -> list[float] | None:
```

Lookup order:
1. `matched_item.get("legend_bbox")` — direct field
2. Scan `structured_blocks` for a block whose `block_id == matched_item["legend_block_id"]` and `page == matched_item.get("legend_page")` → return its `bbox`
3. Scan `inventory["figure_legends"]` for entry whose `block_id == matched_item["legend_block_id"]` → return its `bbox`
4. Return `None` (ineligible)

---

### Task 4: Implement `_infer_missing_main_figure_numbers()`

**File:** `paperforge/worker/ocr_figures.py`

```python
def _infer_missing_main_figure_numbers(
    inventory: dict,
    structured_blocks: list[dict],
) -> dict:
```

Algorithm (detailed steps in spec):

1. **Build known set**: `matched_figures` with `isinstance(figure_number, int)`, namespace=main (via `_extract_figure_marker` on their text), not has_s_prefix, unique numbers.

2. **Build eligible unknown set**: `matched_figures` with `figure_number is None`, namespace=main, legend_block_id, asset_block_ids non-empty, settlement_type in accepted set, not vetoed by frontmatter keywords, legend_bbox resolvable.

3. **Early skip if no eligible unknowns** → `reason="no_eligible_unknowns"`

4. **Early skip if known set empty or min != 2** → `reason="known_min_not_2"`

5. **Exactly one eligible unknown required** → else `reason="multiple_eligible_unknowns"`

6. **Order check**: compute `figure_order_key = (min(asset_pages or [page]), legend_page, bbox_y, bbox_x)`. Unknown must be before first_known. Else → `reason="unknown_not_before_first_known"`.

7. **Noise check**: scan `matched_figures`, `held_figures`, `ambiguous_figures` with order_key between unknown and first_known. If any exists → skip (conservative).

8. **Infer**: Update matched item, update corresponding figure_legends entry, write `"accepted"` status.

9. **Write `inventory["figure_number_inference"]`** with full metadata.

---

### Task 5: Wire into `build_figure_inventory()`

**File:** `paperforge/worker/ocr_figures.py`

Find the exact location where `inventory` is assembled and `_promote_sequence_matches()` is called. Insert:

```python
inventory = _promote_sequence_matches(inventory, structured_blocks)

# NEW: infer missing main figure numbers
inventory = _infer_missing_main_figure_numbers(inventory, structured_blocks)

# Existing completeness check follows
inventory["figure_legend_completeness"] = compute_figure_legend_completeness(
    structured_blocks, inventory,
)
```

---

### Task 6: Tests

**File:** `tests/test_ocr_figures.py`

#### 6a. `test_infer_figure1_leading_gap`

Simulate N6XCZD25: matched_figures with known=[2,3,4,5,6], one eligible unknown before Figure 2.

Assert:
- `inference["status"] == "accepted"`
- matched item `figure_number == 1`, `figure_id == "figure_001"`
- corresponding `figure_legends` item has `inferred_figure_number == 1`
- `inventory["figure_number_inference"]["reason"] == "accepted"`

#### 6b. `test_infer_frontmatter_veto`

known=[2,3,4], two unnumbered — one has text "Graphical Abstract".

Assert:
- Only the non-vetoed one gets inferred
- Vetoed item unchanged

#### 6c. `test_infer_main_supplementary_isolation`

known_supplementary=[1], known_main=[2,3], one eligible main unknown before Figure 2.

Assert:
- Unknown gets number 1
- S1 not in known_main set

#### 6d. `test_infer_no_eligible_unknowns`

All matched_figures have numbers. Assert skip, reason `no_eligible_unknowns`.

#### 6e. `test_infer_known_min_not_2`

known=[1,3,4], one unknown before 3. Assert skip, reason `known_min_not_2`.

#### 6f. `test_infer_multiple_eligible_unknowns`

known=[2,3], two unknown before 2. Assert skip, reason `multiple_eligible_unknowns`.

#### 6g. `test_infer_missing_legend_bbox`

Matched item without legend_bbox, structured_blocks empty, figure_legends empty.

Assert skip, reason `missing_legend_bbox`.

#### 6h. `test_infer_unknown_not_before_first_known`

known=[2,3], unknown after 2. Assert skip, reason `unknown_not_before_first_known`.

---

## 5. Test Harness Note

Tests that need `structured_blocks` can use a minimal stub list. Tests that need a realistic inventory structure can construct a small dict inline. Do NOT need to open a real PDF.

Each test must verify:
1. The `inventory["figure_number_inference"]` block (status + reason)
2. The specific mutations on matched_figures and figure_legends
3. That unmatching entries are untouched

---

## 6. Execution Order

```
Task 1: _FRONTMATTER_VISUAL_VETO constant      → 5 min (one PR comment)
Task 2: _extract_figure_marker()                → 15 min
Task 3: _resolve_legend_bbox()                  → 10 min
Task 4: _infer_missing_main_figure_numbers()    → 30 min (core logic)
Task 5: Wire into build_figure_inventory()      → 5 min
Task 6: Tests (8 test cases)                    → 30 min
```

Total: ~95 min. Single commit PR (or squashed into one commit per the pomodoro-log pattern).
