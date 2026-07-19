# Figure Number Inference — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `subagent-driven-development` or `executing-plans`.

**Goal:** Add `_infer_missing_main_figure_numbers()` to `build_figure_inventory()` that fills `figure_number: None` for matched main-sequence figures when a single leading gap (Figure 1) can be inferred with high confidence. Motivation: N6XCZD25 lost "Figure 1." text in OCR, producing `figure_unknown_005`.

**Primary Spec:** `docs/superpowers/specs/2026-06-26-figure-number-fallback-by-sequence-design.md`

> **Implementation note:** This plan supersedes the integration-point wording in the primary spec. The primary spec was written before the code structure was fully audited; it describes a different insertion point. The correct insertion point (defined here in Task 5) is after `inventory` assembly and after `_promote_sequence_matches()`, NOT before the main matching loop.

---

## 1. Stage Boundary

This plan:
- Adds one new function: `_infer_missing_main_figure_numbers()`
- Adds one new helper: `_extract_figure_marker()` (structured marker parser)
- Adds one new helper: `_resolve_legend_bbox()` (3-tier lookup)
- Adds one new helper: `_has_frontmatter_visual_veto()` (keyword check)
- Adds one new helper: `_coerce_int_figure_number()` (type-safe number coercion)
- Adds one module-level constant: `_FRONTMATTER_VISUAL_VETO`
- Adds one module-level regex: `_FIGURE_MARKER_PATTERN`
- Mutates `matched_figures`, `figure_legends`, and `inventory["figure_number_inference"]` only
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
- If duplicate known numbers exist (same integer appearing >1 in matched_figures), skip with `reason="duplicate_known_main_numbers"`.

---

## 3. File Map

| File | Responsibility |
|------|---------------|
| `paperforge/worker/ocr_figures.py` | New function + helpers + constant + regex + integration point in `build_figure_inventory()` |
| `tests/test_ocr_figures.py` | All new tests |

---

## 4. Implementation Tasks

### Task 1: Add `_FRONTMATTER_VISUAL_VETO` constant

**File:** `paperforge/worker/ocr_figures.py`

```python
_FRONTMATTER_VISUAL_VETO = (
    "graphical abstract",
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

Add a matching helper:

```python
def _has_frontmatter_visual_veto(text: str) -> bool:
    lower = " ".join(text.lower().split())
    if re.search(r"\btoc\b", lower):
        return True
    return any(
        phrase in lower
        for phrase in _FRONTMATTER_VISUAL_VETO
    )
```

Single-word tokens like `"toc"` are matched via `\b...\b` regex, not raw substring, to avoid false positives.

---

### Task 2: Add `_FIGURE_MARKER_PATTERN` regex and `_extract_figure_marker()` helper

**File:** `paperforge/worker/ocr_figures.py`

**Do NOT reuse the old `_FIGURE_NUMBER_PATTERN`.** It was designed to capture bare digits only, discarding the `S` prefix. Build a new capture-group regex:

```python
_FIGURE_MARKER_PATTERN = re.compile(
    r"(?P<prefix>Supplementary\s+Figure|Supplementary\s+Fig\.?|"
    r"Extended\s+Data\s+Figure|Extended\s+Data\s+Fig\.?|"
    r"Figure|Fig\.?)\s*"
    r"(?P<s_prefix>S\.?\s*)?"
    r"(?P<number>\d+(?:\.\d+)?)",
    re.I,
)
```

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
- Match against `_FIGURE_MARKER_PATTERN` (not old pattern)
- `has_s_prefix = bool(m.group("s_prefix"))`
- If text contains `supplementary`, `supporting`, `additional file`, `appendix` → namespace=supplementary
- If text contains `extended data`, `extended figure` → namespace=extended_data
- If `has_s_prefix` is True → namespace=supplementary (overrides keyword-based main)
- Otherwise namespace=main

This REPLACES `_extract_figure_number()` for building the known-number set in the inference pass. The old function can remain for other callers.

---

### Task 3: Add `_coerce_int_figure_number()` helper

**File:** `paperforge/worker/ocr_figures.py`

Inventory data can carry numbers as ints, floats, or strings from JSON. Accept any usable form:

```python
def _coerce_int_figure_number(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None
```

---

### Task 4: Add `_resolve_legend_bbox()` helper

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

### Task 5: Implement `_infer_missing_main_figure_numbers()`

**File:** `paperforge/worker/ocr_figures.py`

```python
def _infer_missing_main_figure_numbers(
    inventory: dict,
    structured_blocks: list[dict],
) -> dict:
```

Algorithm:

1. **Build known set**: iterate `matched_figures`, for each:
   - `num = _coerce_int_figure_number(item.get("figure_number"))`
   - if num is None → skip
   - parse text via `_extract_figure_marker()` → skip if namespace != main or has_s_prefix
   - collect `num` in known set
   - **Duplicate check**: if any `num` appears >1 → write `reason="duplicate_known_main_numbers"`, return early

2. **Build eligible unknown set**: iterate `matched_figures`, for each:
   - `num = _coerce_int_figure_number(item.get("figure_number"))` → must be None
   - parse text → namespace must be main
   - `legend_block_id` must be truthy
   - `asset_block_ids` must be non-empty
   - `settlement_type` in `{"same_page", "group_sequential", "cross_page_forward", "cross_page_backward", "composite_parent"}`
   - `_has_frontmatter_visual_veto(item.get("text", "") + legend_block_text)` must be False
   - `_resolve_legend_bbox(...)` must return non-None
   - Collect `(item, legend_bbox)` in eligible list

3. **Early skip if no eligible unknowns** → `reason="no_eligible_unknowns"`, return

4. **Early skip if known set empty or min != 2** → `reason="known_min_not_2"`, return

5. **Exactly one eligible unknown required** → else `reason="multiple_eligible_unknowns"`, return

6. **Order check** — compute `figure_order_key` for eligible unknown and first_known:
   ```python
   figure_order_key = (
       min(item.get("asset_pages") or [item.get("page", 1)]),
       item.get("legend_page") or item.get("page", 1),
       legend_bbox_y,
       legend_bbox_x,
   )
   ```
   Unknown must be before first_known. Else → `reason="unknown_not_before_first_known"`, return.

7. **Noise check**: scan `matched_figures`, `held_figures`, `ambiguous_figures` for items whose `figure_order_key` falls between unknown and first_known. For each noise item:
   - Resolve bbox (same 3-tier lookup)
   - If bbox not resolvable → skip inference with `reason="intervening_unknown_unorderable"`
   - If any resolvable item's order key is between unknown and first_known → skip with `reason="intervening_items_between"`

8. **Infer**:
   - Update matched item: `figure_number=1`, `figure_id=_format_figure_id("main", 1)`, `figure_namespace="main"`, `number_inference={...}`
   - Update corresponding `figure_legends` entry: `inferred_figure_number=1`, `figure_number_source="sequence_gap_inference"`
   - Write `inventory["figure_number_inference"]` with `status="accepted"`, `reason="accepted"`, and full metadata

---

### Task 6: Wire into `build_figure_inventory()`

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

### Task 7: Tests

**File:** `tests/test_ocr_figures.py`

#### 7a. `test_infer_figure1_leading_gap`

Simulate N6XCZD25: matched_figures with known=[2,3,4,5,6], one eligible unknown before Figure 2.

Assert:
- `inference["status"] == "accepted"`
- `inference["reason"] == "accepted"`
- matched item `figure_number == 1`, `figure_id == "figure_001"`
- corresponding `figure_legends` item has `inferred_figure_number == 1`

#### 7b. `test_infer_frontmatter_veto`

known=[2,3,4], two unnumbered. One has text "Graphical Abstract" and otherwise satisfies ALL eligibility (legend_block_id, asset_block_ids non-empty, accepted settlement_type, resolvable bbox). The other has no veto keyword.

Assert:
- Only the non-vetoed one gets inferred (`reason="accepted"`)
- Vetoed item unchanged (`figure_number` still None)
- Vetoed item not in `number_inference` mutation list

#### 7c. `test_infer_main_supplementary_isolation`

known_supplementary=[1], known_main=[2,3], one eligible main unknown before Figure 2.

Assert:
- Unknown gets number 1
- S1 not in known_main set
- `reason="accepted"`

#### 7d. `test_infer_no_eligible_unknowns`

All matched_figures have numbers. Assert skip, reason `no_eligible_unknowns`.

#### 7e. `test_infer_known_min_not_2`

known=[1,3,4], one unknown before 3. Assert skip, reason `known_min_not_2`.

#### 7f. `test_infer_multiple_eligible_unknowns`

known=[2,3], two unknown before 2. Assert skip, reason `multiple_eligible_unknowns`.

#### 7g. `test_infer_missing_legend_bbox`

Matched item without legend_bbox, structured_blocks empty, figure_legends empty.

Assert skip, reason `missing_legend_bbox`.

#### 7h. `test_infer_unknown_not_before_first_known`

known=[2,3], unknown after 2. Assert skip, reason `unknown_not_before_first_known`.

#### 7i. `test_infer_duplicate_known_numbers_skips`

known=[2,2,3], one eligible unknown before first Figure 2.

Assert skip, reason `duplicate_known_main_numbers`.

---

## 5. Test Harness Note

Tests that need `structured_blocks` can use a minimal stub list. Tests that need a realistic inventory structure can construct a small dict inline. Do NOT need to open a real PDF.

Each test must verify:
1. The `inventory["figure_number_inference"]` block (status + reason)
2. The specific mutations on matched_figures and figure_legends (where applicable)
3. That unmatching entries are untouched

For frontmatter veto test (7b), the veto-target item must satisfy ALL other eligibility criteria to prove the veto keyword is what excludes it.

---

## 6. Execution Order

```
Task 1: _FRONTMATTER_VISUAL_VETO + _has_frontmatter_visual_veto     → 5 min
Task 2: _FIGURE_MARKER_PATTERN regex + _extract_figure_marker()      → 15 min
Task 3: _coerce_int_figure_number()                                  → 5 min
Task 4: _resolve_legend_bbox()                                       → 10 min
Task 5: _infer_missing_main_figure_numbers()                          → 35 min (core logic + skip reasons)
Task 6: Wire into build_figure_inventory()                           → 5 min
Task 7: Tests (9 test cases)                                         → 35 min
```

Total: ~110 min. Single commit PR.
