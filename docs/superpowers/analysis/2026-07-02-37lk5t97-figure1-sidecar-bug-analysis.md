# 37LK5T97 Figure 1 Sidecar Bug Analysis

## Paper Context

- **Paper:** 37LK5T97 — "Both IM and EC ossification occurs during the bone-healing process"
- **Page 2:** Two-column layout
- **Caption:** `p2:2` (block_id=2), bbox=[118, 135, 364, 640], text="FIG. 1. Both IM and EC ossification..."
- **Image:** `p2:9` (block_id=9), bbox=[398, 306, 1091, 645], raw_label=image, role=media_asset

## Symptom

Figure 1 caption was classified as `body_paragraph` instead of `figure_caption`. The image was detected as `media_asset` but left unmatched. Result: Figure 1 completely missing from figure inventory (Figures 2 and 3 matched correctly).

## Root Cause Chain

### Step 1: Seed role correct ✅

`assign_block_role()` assigned `figure_caption_candidate` — correctly identified from `FIG. 1` prefix. Confidence: 0.9.

### Step 2: `_is_near_figure_media()` returns False ❌

The function checks `h_overlap = bx1 < ox2 and ox1 < bx2`:

```python
caption bbox: [118, 135, 364, 640]    # left column (246px wide)
image bbox:   [398, 306, 1091, 645]    # right column (693px wide)

h_overlap = 118 < 1091 and 398 < 364
          = True        and False
          = False
```

Because the caption and image are in **different columns** of a two-column layout, there is zero horizontal overlap. The function skips this image candidate entirely.

### Step 3: `_looks_like_figure_narrative_prose()` returns True ✅

```python
sentence_count = text.count(". ") + text.count(".\n")
# "FIG. 1. Both IM and EC ossification occurs during the bone-healing process
#  in the... The results demonstrate..." → sentence_count >= 2
```

A long descriptive caption meets the "narrative prose" threshold (≥2 sentences). This is correct — the caption IS long prose. But in a sidecar layout, that's expected.

### Step 4: Demotion triggered 🔴

```python
if (
    in_body_spine        # True — page 2 is before body_end_page
    and is_prose         # True — ≥2 sentences
    and not (...)        # not display_zone + legend_like + figure_title
    and not (...)        # not vision_footnote rescue
):
    block["role"] = "body_paragraph"
```

All three conditions met → caption demoted to `body_paragraph`.

### Step 5: Sidecar fallback never reachable

The figure-inventory sidecar fallback (`_apply_bbox_only_synthetic_vector_fallback`, narrow-caption matching) operates downstream of `candidate_resolution`. Since the caption was already `body_paragraph` before reaching `build_figure_inventory()`, the sidecar fallback never sees it.

## Why This Case Fails vs Other Cases That Work

| Scenario | Layout | x_overlap | near_media | is_prose | Result |
|----------|--------|-----------|------------|----------|--------|
| Normal Figure (Fig 2 of same paper) | Caption above image, same column | ✅ Yes | ✅ True | ✅ True | **Caption kept** (excepted by different branch: `display_zone + legend_like + figure_title`) |
| U746UJ7G rotated caption | Caption rotated 90°, beside chart | ❌ No (no h_overlap, but v_overlap) | ❌ False | ✅ True | Was demoted; rescued post-fix by vision_footnote Figure Description rescue path |
| 37LK5T97 Fig 1 (THIS BUG) | Caption left col, image right col (sidecar) | ❌ No (no h_overlap, but v_overlap) | ❌ False | ✅ True | **Demoted** — no exception applies |

The critical pattern: both the rotated caption (U746UJ7G) and the sidecar caption (37LK5T97) have **vertical overlap but no horizontal overlap** with their media asset. The current `_is_near_figure_media()` only checks horizontal overlap, missing both cases.

## The Real Issue

`_is_near_figure_media()` uses `h_overlap` as its sole geometric gate. This is correct for standard layouts (caption above/below image), but fails for:

1. **Sidecar layout**: caption in one column, image in adjacent column — vertical overlap, zero horizontal overlap
2. **Rotated caption**: vertical text beside the figure — vertical overlap, zero horizontal overlap (if the rotated caption's narrow bbox doesn't overlap horizontally)

Both share the same pattern: **caption and media_asset share the same vertical band but occupy different horizontal bands**.

## Fix: Add v_overlap Check to `_is_near_figure_media()`

### Location
`paperforge/worker/ocr_roles.py:197-202`

### Current code
```python
h_overlap = bx1 < ox2 and ox1 < bx2
if not h_overlap:
    continue
gap = by1 - oy2
if -max_gap * 0.3 <= gap <= max_gap:
    return True
```

### Proposed fix
```python
h_overlap = bx1 < ox2 and ox1 < bx2
if h_overlap:
    gap = by1 - oy2
    if -max_gap * 0.3 <= gap <= max_gap:
        return True
else:
    # Sidecar layout check: caption and image in different columns
    # but share vertical overlap → sidecar relationship
    v_overlap = by1 < oy2 and oy1 < by2
    if v_overlap:
        return True
```

### What this changes

For the 37LK5T97 case:
- `h_overlap = False` → enters the `else` branch
- `v_overlap = 135 < 645 and 306 < 640 = True` → returns True
- `near_media = True`
- Demotion condition: `if in_body_spine and is_prose and not near_media`... wait, `near_media` is NOT in the demotion condition directly.

Looking at the demotion code again:
```python
if (
    in_body_spine
    and is_prose
    and not (zone == "display_zone" and style_family == "legend_like" and raw_label == "figure_title")
    and not (raw_label == "vision_footnote" and _looks_like_figure_description_opening(text))
):
```

`near_media` is computed but NOT used in the demotion condition! It appears to be unused in this code path (it's used in the `ocr_roles.py` `assign_block_role` for `vision_footnote` routing).

So the fix to `_is_near_figure_media` alone won't prevent the demotion. We also need to use `near_media` in the demotion condition.

### Revised Fix

Two changes needed:

**1. `ocr_roles.py` — `_is_near_figure_media()`**: Add v_overlap check for sidecar layouts.

**2. `ocr_document.py` — `candidate_resolution` demotion gate**: Add `near_media` as a guard:

```python
if (
    in_body_spine
    and is_prose
    and not near_media      # ← NEW: if near media, don't demote
    and not (zone == "display_zone" and style_family == "legend_like" and raw_label == "figure_title")
    and not (raw_label == "vision_footnote" and _looks_like_figure_description_opening(text))
):
```

This prevents caption demotion when a `figure_caption_candidate` is near a `media_asset` on the same page. If both `h_overlap` and `v_overlap` checks are used, this correctly catches:
- Standard captions (above/below image) → `h_overlap` True → near_media True → kept
- Sidecar captions (adjacent column) → `h_overlap` False, `v_overlap` True → near_media True → kept
- True narrative prose (no media asset nearby) → both False → near_media False → demoted

### Risk Assessment

- **False negatives** (caption NOT demoted when it should be): Low risk. A `figure_caption_candidate` that is near `media_asset` is almost certainly a real caption. The figure inventory pipeline will resolve it correctly.
- **False positives** (narrative prose kept as caption): Possible if a figure-mention body paragraph happens to be vertically near an unrelated media_asset. However, the figure inventory's matching scores should reject bad pairings.
- **Regression**: `_is_near_figure_media` is also called from `ocr_roles.py:assign_block_role()` for `vision_footnote` routing. Adding v_overlap there could increase false positives for that path (classifying vision_footnote as figure_caption_candidate). Review needed.

### Verification

Rebuild 37LK5T97 after fix and verify:
- Figure 1 has `figure_number=1`, `figure_id=figure_001`
- Caption `p2:2` is `figure_caption` not `body_paragraph`
- Image `p2:9` is matched as Figure 1 asset
- No regression on Figures 2/3 or other papers
