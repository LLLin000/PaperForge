# P0 Implementation Plan: Fix 2 + Fix 4 + Fix 5

> **Based on:** `2026-06-27-ocr-v2-audit-remediation-5-fixes.md`
> **Type:** 3 independent patches, one commit
> **Verification:** YGH7VEX6 + 25K5KZAQ audit papers

---

## Step 1: Fix 4 — Remove `figure_caption` from non-body insert candidates

**File:** `paperforge/worker/ocr_document.py`
**Function:** `_detect_non_body_insert_clusters` (~line 3846)

**Change A — the set:**

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

**Change B — docstring (two locations):**

1. Function docstring: remove `figure_caption, figure_caption_candidate` from role list in detection criteria
2. Inline comment (~line 3805-3806): delete or rephrase "figure_caption is included because PaddleOCR sometimes labels narrow author-bio side-panel blocks as figure_title/figure_caption"

**Verify:** Run YGH7VEX6 audit — Figure 2 caption must be `figure_caption` not `non_body_insert`.

---

## Step 2: Fix 2 — Support bracket format in reference sort

**File:** `paperforge/worker/ocr_render.py`
**Function:** `_ref_number_sort_key` (~line 481)

**Change:**

```python
def _ref_number_sort_key(block: dict) -> tuple:
    text = str(block.get("text") or block.get("block_content") or "")
    m = re.match(r"^\s*(?:\[(\d+)\]|(\d+)[\.\)])\s*", text)
    if m:
        return (0, int(m.group(1) or m.group(2)))
    return (1, text)
```

**Verify:** 25K5KZAQ fulltext — references `[1],[2],...,[10],[11],...` in correct numeric order.

---

## Step 3: Fix 5 — Filter demoted body paragraphs from figure legends

**File:** `paperforge/worker/ocr_figures.py`
**Function:** `build_figure_inventory` — legend collection loop

**Change:** In `for block in structured_blocks:` around line ~2940-2970, before `_is_validation_first_legend_candidate()` call:

```python
# Skip body paragraphs demoted from caption_candidate — narrative mentions, not legends
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

Do NOT touch `render_default` / `index_default` — these blocks stay as normal body text.

**Verify:** YGH7VEX6 Figure 11 — `figure_011` uses real caption (block 13), no `figure_s011`.

---

## Step 3 detail: Insert position for Fix 5

In `build_figure_inventory()`, the legend collection loop order is:

```
1. skip _non_body_media / non_body_insert
2. skip panel label (_PANEL_LABEL_PATTERN)
3. → INSERT Fix 5 FILTER HERE ←
4. is_validation_first_candidate = _is_validation_first_legend_candidate(block)
5. if role in caption_roles or is_validation_first_candidate: → append to legends
```

Do NOT place the filter inside step 5 — by then the block is already in legends.

---

## Test additions

**File:** `tests/test_ocr_render.py`

```python
def test_ref_number_sort_key_supports_bracketed_numbers():
    """[1], [2], [10] → 1, 2, 10"""
    ...

def test_ref_number_sort_key_rejects_plain_year_prefix():
    """'2024 Elsevier...' → lexicographic fallback (not parsed as number)"""
    assert _ref_number_sort_key({"text": "2024 Elsevier Ltd."})[0] == 1
```

**File:** `tests/test_ocr_document.py`

```python
def test_non_body_insert_candidates_exclude_figure_caption_roles():
    """figure_caption escapes non_body_insert even when narrow + font mismatch + cluster exists"""
    # Construct: role=figure_caption, width < 0.9*median, font mismatch, 2 candidates on same page
    # Expected: not in non_body_insert indices
    ...

def test_demoted_body_caption_candidate_excluded_from_legends_but_still_renderable():
    """body_paragraph + seed_role=figure_caption_candidate:
       - excluded from figure_legends / matched_figures / ambiguous_figures / unmatched_legends
       - render_default and index_default NOT mutated
       - appears in rejected_legends with rejection_reason"""
    ...
```

## Acceptance checklist

```text
- pytest targeted tests pass
- YGH7VEX6: Figure 2 caption role = figure_caption, participates in matching
- YGH7VEX6: Figure 11 matched legend = real caption p6:13; p6:7 excluded from legends but remains body text
- 25K5KZAQ: references sort [1], [2], [3], ..., [10], [11] numerically
- No render_default/index_default mutation for demoted body caption candidates
```

## Rollback

Each step is independent. If Fix 4 causes issues, revert the set change alone.
If Fix 5 misses a legitimate caption, the rejected_legends audit trail shows which blocks were excluded.
