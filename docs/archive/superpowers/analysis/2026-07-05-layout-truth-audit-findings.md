# Layout-Classification Truth Audit — Problem Analysis Report

> **Date:** 2026-07-05
> **Method:** 12 papers sampled by layout class (single/multi/short/figure-dense/no-figures/health-red), `ocr_truth_audit.py --mode high-risk`, then 5 key papers verified via vision subagents on annotated pages.
> **Status:** Ready for GPT solution discussion.

---

## Executive Summary

11/12 papers ran successfully (1 RED paper had no structured blocks). Vision verification found **6 real bug patterns** across the audited papers. The 170 `reference_span_error` findings were confirmed as high-risk-mode false positives (`logical_order_between_reference_members` noise). The actionable bugs cluster into 4 categories.

---

## Bug Pattern A: `_is_obviously_formal_figure_caption` Heuristic Too Aggressive

**Location:** `paperforge/worker/ocr_roles.py:193-204`

```python
def _is_obviously_formal_figure_caption(text: str, block: dict, page_blocks: list[dict]) -> bool:
    if not _has_figure_prefix(text):
        return False
    verb_patterns = ["shows", "illustrates", "depicts", "demonstrates", "presents", "summarizes"]
    has_verb = any(v in text.lower() for v in verb_patterns)
    sentence_markers = [" is ", " are ", " was ", " were "]
    has_sentence = any(m in text.lower() for m in sentence_markers)
    if has_verb and has_sentence:
        return False  # ← Only rejects if BOTH verb AND sentence structure present
    is_short = len(text) <= 80
    near_media = _is_near_figure_media(block, page_blocks)
    return is_short or near_media
```

**Bug:** Body text like "Fig. 9 shows the Mössbauer spectrum of a dehydrated sample..." has the verb "shows" but NOT a sentence marker like " is " — so `has_verb=True, has_sentence=False`, meaning the function returns `True` (it thinks it IS a formal figure caption). This text then enters the pipeline as `figure_caption_candidate` and creates phantom figure matches.

**Confirmed in:** 2HJSWV3V (figure_dense, 12 figures). Figures 8 and 9 both had body-text discussion misclassified as captions. The phantom captions caused cascading ownership errors.

**Indirect consequence in same paper:** 0/4 tables matched because the pipeline was overwhelmed by phantom figure captions.

**Called by:** `assign_block_role()` at `ocr_roles.py:937,964` → `build_structured_blocks()` in `ocr_blocks.py`

---

## Bug Pattern B: Cross-Column Figure Asset Mis-Assignment

**Location:** `paperforge/worker/ocr_figures.py:271-280` (`_column_band_id`), and the pairing framework in `ocr_pairing_framework.py`

```python
def _column_band_id(bbox: list[float], page_width: float) -> int | None:
    """Classify a bbox into left (0), right (1), or center (None) column band."""
    center_x = (bbox[0] + bbox[2]) / 2.0
    if center_x < page_width * 0.45:
        return 0
    if center_x > page_width * 0.55:
        return 1
    return None  # ← center zone: considered "any column"
```

**Bug:** The `None` return for center-column blocks means "ambiguous column." The `_is_safe_page_assets_group()` gate uses this to reject cross-column groups (per Issue 5 fix `4ab227e`). However, during **nearest-neighbor caption-to-asset matching**, the same column-awareness is NOT applied. A left-column asset can be matched to a right-column caption if they are spatially close in y-axis, ignoring column boundaries.

**Confirmed in:** 28JLIHLS (single_column, 6 figures). Figure 5's left-column assets (p4:0, p4:2) were assigned to Figure 6's right-column caption (p4:7) because the nearest-neighbor heuristic didn't check column alignment.

**Root cause:** `_cluster_page_assets()` at `ocr_figures.py:704-769` does spatial clustering without column gating. The legacy nearest-neighbor path in `build_figure_inventory()` also lacks column-awareness.

---

## Bug Pattern C: Render Mapping — Frontmatter Roles Silently Dropped

**Location:** `paperforge/worker/ocr_render.py:1160-1866` (`render_fulltext_markdown`)

```python
CONSUMED_FRONTMATTER_ROLES = frozenset({
    "paper_title", "authors", "doi", "affiliation", "email", "correspondence",
})

# During block iteration:
if role in CONSUMED_FRONTMATTER_ROLES and int(block.get("page", 0) or 0) <= 2:
    continue  # ← Silently drops authors, affiliations, email
```

**Bug:** The renderer intentionally skips frontmatter-role blocks on pages 1-2 because it expects them to be rendered through `resolved_metadata`. The title IS rendered via `resolved_metadata.get("title")`. But authors/affiliations/email are rendered through the metadata info box:

```python
authors_display = resolved_metadata.get("authors_display", "")
if not authors_display:
    authors = resolved_metadata.get("authors", {}).get("value", [])
    if authors:
        authors_display = ", ".join(authors)
```

**Problem:** If `resolved_metadata["authors"]` is empty (which happens when frontmatter extraction fails), the authors are silently lost — the `CONSUMED_FRONTMATTER_ROLES` skip removes them from the block iteration AND the metadata info box is empty.

**Confirmed in:** 29RE4EMX (authors + 7 affiliations missing), CIBQ2KHS (title/authors not rendering), 28JLIHLS (10 content blocks silently dropped including authors, affiliations, table caption, table footnotes).

**Impact:** This is user-visible — the rendered fulltext is missing frontmatter data.

---

## Bug Pattern D: Same-Page Boundary on Two-Column Layout

**Locations:** `paperforge/worker/ocr_document.py:1249-1673` (`infer_zones`) and `_infer_tail_hold_band`, `_page_has_strong_body_continuation`

**Bug:** On two-column pages where body text and references coexist (left column has Conclusions → body, right column has References → backmatter), the zone inference assigns `tail_nonref_hold_zone` / backmatter to left-column body text. This happens because the zone boundary logic scans the page as a whole and finds reference headings in the right column, then back-propagates a "tail zone" label to the entire page bottom.

**Key code flow:** `infer_zones()` → `_is_below_same_page_reference_heading()` at `ocr_document.py` — when ANY block on a page is below a reference heading, adjacent-column body text gets pulled into the tail zone.

**Confirmed in:** 29RE4EMX (left-column body Conclusions pulled to backmatter), CIBQ2KHS (CONCLUSIONS body pulled to backmatter on shared page with REFERENCES).
**False positive confirmed:** 28JLIHLS (single-column with clear spatial separation — zone classification was correct).

---

## Bug Pattern E: Frontmatter Section Headings Misclassified

**Location:** `paperforge/worker/ocr_roles.py` (`assign_block_role`) → routes to `unknown_structural` or `paper_title` instead of `section_heading`

**Confirmed instances:**
- 29RE4EMX: "ARTICLE INFO" → `unknown_structural` (should be `frontmatter_heading` or `section_heading`)
- CIBQ2KHS: "RESULTS AND DISCUSSION" → `paper_title` (should be `section_heading`)
- 8LZUYXMH: "Supplementary Files" → `unknown_structural` (should be `frontmatter_heading`)

**Root cause:** These blocks sit outside the main body flow (sidebar, narrow column, or all-caps formatting), so `assign_block_role()` falls through to conservative defaults. The role resolution doesn't have a "short frontmatter heading" heuristic.

---

## Bug Pattern F: Supplementary-Only PDF — Pipeline Edge Case

**Location:** Entire `ocr_render.py` render path does not handle supplementary-material PDFs that lack standard paper structure (no body paragraphs, no abstract, no references section).

**Confirmed in:** 8LZUYXMH (5-page supplement with Tables S1-S3, no body text). Only 1/10 blocks (the paper title) made it into fulltext. 0/4 tables matched. 90% block-to-fulltext mapping failure.

**Root cause:** The pipeline was designed for standard research papers. Supplementary-only PDFs violate multiple assumptions: no body paragraphs, no abstract, no reference zone. The health check correctly flags this as RED.

---

## Non-Bugs Verified

| Pattern | Papers | Verdict |
|---------|--------|---------|
| `reference_span_error` (170 total) | All papers, ~20/paper | FALSE POSITIVE — high-risk mode conservatism |
| `same_page_boundary` on single-column papers | 28JLIHLS | FALSE POSITIVE — spatial separation clear |
| `frontmatter_error` — empty/logo blocks | 2HJSWV3V | FALSE POSITIVE — genuinely unclassifiable |
| `render_mapping_error` — noise with `render_default:false` | 28JLIHLS | FALSE POSITIVE — correctly excluded per policy |

---

## Code Architecture Observations

### `render_fulltext_markdown()` — 707 lines, complexity=157
This function is a monolith handling ALL render logic: frontmatter metadata, abstract, heading hierarchy, figure/table embedding, body text, backmatter, callouts, page breaks. The 707-line function has 44 loops and a cognitive complexity of 460. The authors/affiliation skip bug (Pattern C) is one symptom of this untestable surface.

### `_is_obviously_formal_figure_caption()` — 12 lines with a fragile heuristic
The sentence marker check (`" is ", " are "`) was designed to catch body text ("Fig. X shows the results...") but fails when the text lacks these specific substrings. Any verb-based figure mention without " is "/" are " passes through.

### Cross-column bug — column data exists but isn't used in asset matching
`_column_band_id()` knows how to classify blocks into left/right/center columns. `_is_safe_page_assets_group()` uses it to reject cross-column groups. But the caption-to-asset matching itself does NOT use column information — a `FigurePipelineState` without column context passes to the matching passes.

---

## Recommended Fix Priority (for GPT)

1. **Pattern C** (render frontmatter skip): Highest user impact — authors/affiliations missing from output
2. **Pattern A** (figure caption heuristic): Causes cascading failures in figure/table matching
3. **Pattern D** (two-column zone boundary): Common layout class (395/734 papers are multi-column)
4. **Pattern B** (cross-column asset assignment): Niche but real — affects multi-column papers
5. **Pattern F** (supplementary-only): Edge case, but health correctly signals RED
6. **Pattern E** (frontmatter headings): Low severity — cosmetic role labels

All fixes must work within the existing architecture seams (vnext passes, post_match_normalize, tail settlement) — no hot-patching, no one-off heuristics.
