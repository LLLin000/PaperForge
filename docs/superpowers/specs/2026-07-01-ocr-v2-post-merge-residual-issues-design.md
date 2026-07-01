# OCR-v2 Post-Merge Residual Issues — Design & Triage

**Date:** 2026-07-01
**Status:** Diagnostic — for external review and design recommendation
**Context:** ocr-v2 merged to master. 7/13 previously-audited bugs are fixed. 6 issues remain in various states of mitigation/partial-fix/open.
**Audit evidence:** 69TA9S8W, 2HJSWV3V, XD2BPCMG, UGA8GFAR, JMG23U8Q, AW49IHEX, 4DU8LEH2

---

## Table of Contents

1. [Summary Table](#1-summary-table)
2. [Issue 1: Table N Short Caption — Split-Block + Validation-First Gap](#2-issue-1-table-n-short-caption)
3. [Issue 2: Figure Inner-Text Containment — Demoted-Caption Region Gap](#3-issue-2-figure-inner-text-containment)
4. [Issue 3: Body Text Backfill Bbox Expansion](#4-issue-3-body-text-backfill-bbox-expansion)
5. [Issue 4: Short-Paper Health False Red](#5-issue-4-short-paper-health-false-red)
6. [Issue 5: Multi-Column Page-Assets Group Collapse](#6-issue-5-multi-column-page-assets-group-collapse)
7. [Issue 6: Figure/Table Shared-Consumption Registry](#7-issue-6-figuretable-shared-consumption-registry)
8. [Design Questions for External Review](#8-design-questions-for-external-review)

---

## 1. Summary Table

| # | Issue | Severity | Mechanism | Papers Affected | Fix Complexity |
|---|-------|----------|-----------|-----------------|----------------|
| 1 | Table N short caption split-block | P0 residual | OCR splits "Table N" + description into two blocks; second block misclassified as `figure_caption`; no adjacent-merge logic | 33 papers, 69TA9S8W, 2HJSWV3V | Low — spatial merge heuristic |
| 2 | Figure inner-text containment — demoted-caption region gap | P2 | Caption demoted → no matched_figure → no cluster_bbox; fallback depends on `figure_like` hint which may be absent post-demotion; `_container_bbox` (PyMuPDF) exists but unused | XD2BPCMG, UGA8GFAR, JMG23U8Q, AW49IHEX | Medium — use `_container_bbox` as validated region source |
| 3 | Backfill bbox expansion overflow | P2 (mitigated) | `get_text("words", clip=expanded)` picks up neighbor-block words; render-layer dedup masks root cause | 4DU8LEH2, any backfill paper | Low — clamp to exact bbox |
| 4 | Short-paper health false red | P3 | Health gates treat all papers equally; Letters/Editorials (<3pp) lack headings/abstract by design | All <3-page papers | Low — add page_count guard |
| 5 | Multi-column page_assets collapse | P3 | Spatial clustering (`_cluster_semantic_page_assets`) doesn't respect column boundaries | Multi-column papers with ≥3 assets per page | Medium — column-aware clustering |
| 6 | Shared-consumption registry | P3 | Figure and table pipelines can both consume the same ambiguous asset; a post-hoc conflict audit exists (`ownership_conflicts`), but there is no arbitration/resolution step | Any paper with ambiguous `media_asset` blocks | Low — post-hoc arbitration at pipeline wiring |

---
### 1.1 Recommended Low-Risk Implementation Order

This document now recommends **deterministic local fixes first, audit-model changes second, and cross-module ownership last**. The proposed implementation order is:

```text
3 → 1 → 4 → 2 → 5 → 6
```

Rationale:

- **Issue 3** is the smallest and most deterministic root fix: one local extraction bug in `ocr_pdf_spans.py`
- **Issue 1** is still local to `ocr_tables.py` and affects many papers, but should be split into:
  - 1A: validation-first fallthrough
  - 1B: local continuation materialization in table inventory
- **Issue 4** is a report-layer correction in `ocr_health.py`; it should not be mixed into figure/table ownership work
- **Issue 2** changes containment regions in `ocr_figures.py`; it is still local but needs false-positive guardrails
- **Issue 5** should start with a conservative rejection gate, not a clustering redesign
- **Issue 6** belongs at the pipeline wiring / arbitration layer because it spans both figure and table inventories

Recommended PR grouping:

```text
PR 1: Issue 3 + Issue 1A + Issue 1B + Issue 4
PR 2: Issue 2
PR 3: Issue 5 + Issue 6
```


## 2. Issue 1: Table N Short Caption

### 2.1 Two Variants

**Variant A — Bare "Table N" label (69TA9S8W):** Paper has 12 tables, every caption is literally `"Table 1"`, `"Table 2"`, etc. No descriptive text. Pipeline's `_TRUNCATED_TABLE_ONLY_PATTERN` matches, blocks enter weak-explicit matching. Regular path now has strong-spatial-evidence gating (`_has_strong_spatial_evidence_for_bare_table`), but `validation_first_candidate` path skips matching entirely.

**Variant B — Split caption block (2HJSWV3V):** OCR splits a table caption into two adjacent blocks:

```text
Block 11: "Table 2"                            → role = table_caption
Block 12: "Structural parameters of..."       → role = figure_caption  ← WRONG
Block 13: [table image]                       → role = media_asset
```

Block 12 does not start with `"Table"`, has no table marker, and is therefore invisible to table caption collection. Role assignment sees `body_paragraph + legend_like + figure_title` and promotes it to `figure_caption`. This creates a **caption completeness bug** first, and a **matching bug only conditionally**:

- stable effect: full table caption text is split; table inventory sees only `"Table N"` and loses the descriptive continuation
- conditional effect: if geometry is also weak or the block falls into the validation-first gap, the table can become unmatched

So the root cause is not “split block always causes unmatched”. The exact bug is **continuation text escapes table ownership**.

### 2.2 Current Code Paths

```
ocr_tables.py:16-19   _TRUNCATED_TABLE_ONLY_PATTERN = r"^(?:Table|Supplementary\s+Table|...)\s*\d+(?:\.\d+)?\.?$"
                      Matches bare "Table N" with no trailing body text.

ocr_tables.py:51-53   _is_insufficient_table_caption_evidence → bool
                      → _is_weak_explicit_table_caption → bool

ocr_tables.py:193-214 is_validation_first_candidate + is_weak_truncated:
                      → always continues (skip match attempt)
                      → GAP: doesn't attempt matching even when same-page assets exist

ocr_tables.py:222-269 is_weak_explicit_caption (regular path):
                      → scores candidates, checks _has_strong_spatial_evidence_for_bare_table
                      → proceeds if (strong_spatial + gap≥0.2) OR continuation_match OR tie_break_winner
                      → PARTIALLY FIXED: gate works but depends on score≥0.75 + three spatial markers

ocr_roles.py:758-770  body_paragraph + legend_like + figure_title → figure_caption
                      → second half of split caption gets stolen by figure pipeline
```

### 2.3 Recommended Low-Risk Fix

**Step 1 — Fix validation-first fallthrough (Variant A, deterministic bug):**

In `ocr_tables.py`, change the `is_validation_first_candidate and is_weak_truncated` branch so it only exits early when **no same-page asset exists**. If same-page assets exist, fall through into the existing weak-explicit matching path. Do **not** add a second scoring rule for validation-first candidates.

```python
if is_validation_first_candidate and is_weak_truncated:
    if not same_page_assets:
        held_tables.append(...)
        continue
    # else: fall through into existing weak-explicit matching
```

**Step 2 — Materialize local continuation captions in `build_table_inventory` (Variant B, low blast radius):**

Do **not** merge raw OCR blocks globally. Instead, add a local helper such as:

```python
_find_table_caption_continuation(caption_block, page_blocks)
```

Trigger only when all hold:

```text
- current caption is weak-truncated: "Table N"
- next block is on same page
- y-gap is small (e.g. 0–25 px)
- x-overlap ratio ≥ 0.5 or left-edge delta < 40 px
- continuation role ∈ {figure_caption, body_paragraph, unknown_structural, table_caption_candidate}
- continuation text does NOT start with Fig/Figure/Scheme/Plate
- continuation text is not heading-like
- no media/table asset sits between the two blocks
```

When triggered:

```text
- create a materialized merged caption for matching only
- keep original blocks unchanged
- add continuation block_id to consumed_block_ids so render cannot leak it separately
```

**Rejected here:** raw-block merge before role assignment. It is broader, riskier, and touches unrelated OCR normalization paths.

---

## 3. Issue 2: Figure Inner-Text Containment

### 3.1 Problem

`tag_figure_contained_text` (ocr_figures.py:5245) detects text blocks that leak into body prose by checking spatial containment within figure regions. When it works (matched figure with valid `cluster_bbox`), it correctly reclassifies contained blocks as `figure_inner_text`. The failure mode arises when a **caption is demoted** — then no `matched_figure` entry exists, no `cluster_bbox` is available, and the fallback path depends on `asset_family_hint` which may also be absent.

### 3.2 Root Cause Chain

```
Caption demotion cascade:

Step 1: figure_caption_candidate → body_paragraph
  Reason: "figure mention with narrative prose in body spine"
  → build_figure_inventory has no numbered legend to match
  → no matched_figure entry created

Step 2: tag_figure_contained_text runs
  Source 1 (matched_figures.cluster_bbox):
    → no matched_figure for this page → EMPTY
  Source 2 (fallback_assets):
    → requires asset_family_hint="figure_like" OR raw_label∈{image,chart,figure_title,figure}
    → if the demoted figure's assets also lost their figure_like hint → EMPTY
  → figure_regions = [] → nothing to contain against → all inner-text blocks LEAK

Step 3: _container_bbox exists but unused
  ocr_pdf_spans.py:484-495 — PyMuPDF's visual container bbox
  Represents the actual bounding region of the visual group on the PDF page
  tag_figure_contained_text NEVER references it
```

**This is NOT a "gap between asset bboxes" problem.** For matched figures, `cluster_bbox` already spans the full width of all assets and covers panel gaps. The real failure is the **demoted-caption cascade**: caption demotion → no matched figure → no cluster_bbox → fallback hint-dependent → silent loss of containment region.

### 3.3 Evidence Papers

| Paper | Page | Figure | Failure mode |
|-------|------|--------|-------------|
| XD2BPCMG | 3, 16 | Fig 1, Fig 6 | Caption demoted; 33+ `vision_footnote` blocks inside figure regions → classified as `footnote` in body flow |
| UGA8GFAR | 2 | Fig 1 (31 subfigures) | 11 `vision_footnote` blocks ("Single outlet", "Multiple outlets", etc.) in visual container → `footnote` |
| JMG23U8Q | 4 | Fig 3 | id=5: subfigure label "1" in visual container → `footnote` |
| AW49IHEX | 6 | Fig 3 | id=14: panel title "Scaffold-free techniques" in visual container |

### 3.4 Fix Design

**Add `_container_bbox` as region source, with safety gates — NOT padding, NOT gap-aware merging.**

Region source priority (layered, not additive):

```text
1. matched_figures.cluster_bbox or reader figure bbox  (primary, already works)
2. asset._container_bbox, only if validated             (NEW — catches demoted case)
3. fallback visual cluster bbox                         (existing, hint-dependent)
```

Source 2 safety gates — `_container_bbox` is rejected unless ALL hold:

```text
- container_bbox exists and len ≥ 4
- container_area < page_area × 0.65          (not a full-page container)
- container_width < page_width × 0.98        (not a full-width body span)
  OR container_height < page_height × 0.45  (unless it's a short wide band)
- at least one media_asset / figure_asset / image-like block inside the container
- target block role ∈ _LEAK_ROLES (footnote, body_paragraph, non_body_insert, etc.)
```

Critical constraint — this is a **containment-only pass**, not a matching pass:

```text
- ONLY tags contained text → _figure_contained + role → figure_inner_text
- Does NOT create new matched_figure entries
- Does NOT consume assets or change figure inventory
- Does NOT affect figure ownership or caption matching
```

### 3.5 Rejected Approaches

**Padding cluster_bbox** — risks pulling adjacent body paragraphs into figure region; false positive rate too high for composite figures with tight body-text spacing.

**Gap-aware region merging** — solves a non-problem (panel gaps are already inside cluster_bbox for matched figures); adds complexity without addressing the demoted-caption case.

### 3.6 Verification

```text
test_container_bbox_tags_vision_footnotes_inside_demoted_figure
test_container_bbox_does_not_consume_body_paragraph_next_to_figure
test_huge_container_bbox_is_rejected_by_area_gate
test_full_width_container_bbox_is_rejected_unless_short
test_matched_cluster_bbox_still_takes_precedence_over_container_bbox
test_container_bbox_without_media_asset_is_rejected
```
---

## 4. Issue 3: Body Text Backfill Bbox Expansion

### 4.1 Problem

`backfill_missing_text_from_pdf` expands the search clip region by a margin around the target block's bbox, causing it to pick up words from neighboring blocks. The render layer has a dedup mechanism (5-gram overlap threshold) that suppresses most duplicates, but the root cause remains.

### 4.2 Mechanism

```
ocr_pdf_spans.py:698:
  words = pdf_page.get_text("words", clip=expanded)
  
  orig_bbox  = [100, 200, 500, 220]   (block's OCR bbox)
  expanded   = [90, 190, 510, 230]    (10px margin added)
  
  Neighbor block at [100, 230, 500, 250]:
    → expanded bbox [90, 190, 510, 230] does NOT overlap [100, 230, ...]
    → neighbor is safe in this example
  
  BUT if neighbor is closer (e.g., y=222, tight vertical spacing):
    → expanded bbox overlaps neighbor → get_text returns neighbor's words too
    → backfill text = current block text + neighbor's text
    → render layer sees duplicate → dedup kicks in → backfill text suppressed
    → current block might NEED the backfill but gets false-rejected
```

### 4.3 Mitigation (already in place)

```
ocr_render.py:1590-1595:
  if _backfill_coverage_in_existing(text, existing) >= 0.8:
      continue  # skip this backfill text

ocr_pdf_spans.py:565-590:
  _backfill_coverage_in_existing: 5-gram Jaccard overlap between backfill_text and already-emitted body text
  _BACKFILL_OVERLAP_REJECT_THRESHOLD = 0.8
```

This works for obvious duplicates (same text appears verbatim from OCR + backfill), but fails when:
- The overlap is 60-80% (threshold not met → duplicate leaks through)
- The backfill text is legitimately needed but gets rejected because it overlaps with OCR text that happened to be emitted earlier on the same page

### 4.4 Recommended Low-Risk Fix

Keep expansion for **search**, but filter acceptance at the **word level** against the original bbox. This is the smallest root fix and stays entirely inside `ocr_pdf_spans.py`.

```python
words = pdf_page.get_text("words", clip=expanded)
words = [
    w for w in words
    if _word_belongs_to_block(w[:4], rect)
]
```

Preferred acceptance rule:

```python
def _word_belongs_to_block(word_bbox, block_rect):
    return (
        _center_inside(word_bbox, block_rect)
        or _bbox_overlap_ratio(fitz.Rect(*word_bbox), block_rect) >= 0.30
    )
```

Why this shape is low-risk:

- preserves the reason expansion exists: OCR/PDF alignment drift
- removes neighbor-word pollution before `_words_to_text(...)`
- does not depend on render-layer dedup as correctness logic

**Rejected here:** shrinking the expansion margin. It reduces the symptom but leaves the root cause in place.

---

## 5. Issue 4: Short-Paper Health False Red

### 5.1 Problem

`build_ocr_health` applies the same 7 binary gates to all papers regardless of page count. Letters, Editorials, and Commentaries (1-2 pages) naturally lack formal section headings and abstracts — this is correct journal format, not a pipeline failure.

### 5.2 Mechanism

```
ocr_health.py:172-193  health determination:
  structural_blockers = 0
  if caption_without_media > 0:    structural_blockers += 1
  if media_without_caption > 0:    structural_blockers += 1
  if empty_tables > 0:             structural_blockers += 1
  if not abstract_found:           structural_blockers += 1   ← Letter: no abstract
  if not references_found:         structural_blockers += 1   ← Letter: may lack refs
  if section_heading_count < 2:    structural_blockers += 1   ← Letter: no sections
  if formal_legend_gaps > 0:       structural_blockers += 1
  
  structural_blockers == 0 → GREEN
  structural_blockers == 1 → YELLOW
  structural_blockers >= 2 → RED

Short paper (Letter, 1 page):
  abstract_found = False          → +1
  section_heading_count = 0       → +1
  → structural_blockers = 2       → RED
  → But the paper IS correctly parsed — it just doesn't have these structures
```

`page_count` is already passed to `build_ocr_health` (line 111) and stored in the report (line 265) but **never used in gate logic**.

### 5.3 Recommended Low-Risk Fix

Add a **health profile** instead of hard suppressing gates.

```python
profile = "short_form" if page_count <= 2 else "standard"
```

For `short_form`:

```text
- abstract_found missing: not a structural blocker
- section_heading_count < 2: not a structural blocker
- references_found missing: warning-level only unless other structural failures exist
- figure/table completeness and content-coverage signals remain active
```

Add explicit report fields:

```json
"health_profile": "short_form",
"waived_gates": ["abstract_found", "section_heading_count"],
"degraded_reason": "short_paper_format"
```

This stays entirely in `ocr_health.py` and avoids widening special cases into role assignment or rendering.

---

## 6. Issue 5: Multi-Column Page-Assets Group Collapse

### 6.1 Problem

On multi-column pages, `_cluster_semantic_page_assets` uses pure spatial proximity clustering without column-boundary awareness. Figures in left and right columns can be merged into a single `page_assets` group, causing one figure to consume assets belonging to another.

### 6.2 Mechanism

```
build_figure_inventory candidate group creation (~line 918):
  clusters = _cluster_semantic_page_assets(page_media, page_blocks, ...)
  
  _cluster_semantic_page_assets (line 844):
    → Union-Find on media_blocks by inflated-bbox overlap
    → v_threshold = max(min(page_width, page_height) * 0.08, 40.0)
    → NO column-awareness: treats the page as one flat space
  
  Two-column page, left-col Figure 2, right-col Figure 3:
    Left:  [Asset A (col 0-300)]  [gap ~50px]  Right: [Asset B (col 350-650)]
    
    Inflated bboxes may overlap if gap < v_threshold*2 = ~80px
    → Union-Find merges A and B into one cluster
    → page_assets group contains both figures' assets
    
  _is_safe_page_assets_group (line 254):
    Gate 2: page_numbered_legend_count == 1 → PASS (one caption for Fig 2)
    Gate 6: _cluster_semantic_page_assets check → PASS (already merged)
    → Group marked safe → all assets matched to one figure
    → Figure 3's assets stolen, Figure 3 lost
```

### 6.3 Recommended Low-Risk Fix

Do **not** start with full column-aware clustering. The lowest-risk first step is to tighten the existing `page_assets` acceptance gate.

Add a **column-homogeneity rejection gate** to `_is_safe_page_assets_group`:

```text
- derive a light column band for each media block from x-center
- if one candidate group spans multiple column bands, reject it as safe page_assets
- allow full-width figures to pass when group width > page_width × 0.65 and page has exactly one numbered legend
```

This is the right seam because:

- `_cluster_semantic_page_assets` is candidate generation
- `_is_safe_page_assets_group` is conservative acceptance
- rejecting a dangerous group is lower-risk than redefining clustering topology

Defer full column-aware clustering unless this gate proves insufficient on real papers.

---

## 7. Issue 6: Figure/Table Shared-Consumption Registry

### 7.1 Problem

The figure pipeline (`build_figure_inventory`) and table pipeline (`build_table_inventory`) can both consume the same ambiguous `media_asset`. There **is** a post-hoc conflict audit (`attach_ownership_conflicts` → `figure_inventory["ownership_conflicts"]`), but there is no arbitration step that resolves the winner before writeback/render.

### 7.2 Mechanism

```text
Figure pipeline asset collection:
  ocr_figures.py: role ∈ {"figure_asset", "media_asset"} → candidate
  _filter_figure_assets allows media_asset when raw_label is empty / image-like

Table pipeline asset collection:
  ocr_tables.py:150-171:
    role ∈ {"table_asset", "media_asset", "figure_asset"}
    media_asset: width≥120, height≥60, aspect≥1.5 → candidate
    figure_asset + raw_label="table" → candidate

Ambiguous media_asset (confirmed by harness):
  raw_label = ""
  bbox = [50,100,500,400]
  Figure side: matched to Figure 1
  Table side:  matched to Table 1
  → Same block appears in both matched_figures and tables

Existing handling:
  ocr_tables.py:173              used_asset_indices (internal to table pipeline)
  ocr_figures.py:1275/1521/...   mark_assets_owned (internal to figure pipeline)
  ocr_figures.py:5094-5113       _build_ownership_conflicts / attach_ownership_conflicts
  → Overlap is SURFACED, but not RESOLVED
```

### 7.3 Recommended Low-Risk Fix

Do **not** use figure-first ordering. It bakes a hidden priority into the architecture and can incorrectly steal table-like assets.

Do **not** start with a shared consumed registry either. That couples the two pipelines before they each finish their own local reasoning.

Preferred fix: **post-hoc arbitration after both inventories exist, before writeback/render**.

Add:

```python
resolve_media_asset_conflicts(figure_inventory, table_inventory)
```

Placement:

```text
build_figure_inventory
→ build_table_inventory
→ resolve_media_asset_conflicts   # NEW
→ attach_ownership_conflicts      # keep audit surface
→ writebacks / render
```

Initial arbitration rules should stay conservative:

```text
1. explicit Table N + same-page + strong table geometry → table wins
2. explicit Figure N + same-page + strong figure geometry → figure wins
3. one side explicit, one side fallback/weak → explicit wins
4. both sides weak → keep conflict surfaced; avoid destructive silent resolution
```

This matches the existing pipeline seam in `ocr.py` / `ocr_rebuild.py` and keeps conflict visibility even when resolution remains uncertain.

---

## 8. Design Questions for External Review

These are the key architectural questions where external perspective would be valuable:

### Q1: Adjacent-block merge — before or after role assignment?

For Table N split-caption (Issue 1, Variant B), should the merge happen at the raw-block level (before any role assignment) or at the table-inventory level (after roles are set)? Raw-block merge is architecturally cleaner but has broader impact across all role assignment paths.

### Q2: `_container_bbox` reliability for containment?

Issue 2 fix candidates all involve `_container_bbox` from PyMuPDF. Is this field reliably populated across all PDF types? What's the failure mode? Should it be a primary source or a fallback enhancement?

### Q3: Short-paper threshold — 2 or 3 pages?

Issue 4: what's the right page_count threshold for "short paper" health gate relaxation? Should it also key off detected paper type (Letter vs Research Article vs Review)?

### Q4: Column detection reuse?

Issue 5: the pipeline already has column detection in `ocr_document.py` (zone inference). Should the figure clustering module reuse that, or does it need independent column detection tuned for figure-asset spatial relationships?

### Q5: Ordering dependency for shared-consumption registry?

Issue 6: if we use a unified registry with figure-first ordering, does this create a coupling that will bite us later? Is post-hoc cross-check (Approach 2) more robust despite being slightly more complex?

### Q6: Priority ordering?

Given the severity and fix complexity, what's the recommended implementation order? Candidates:
- 1 → 3 → 4 (low complexity, high paper count) → 2 → 5 → 6
- 3 → 1 → 4 → 2 → 6 → 5 (root-cause fixes first)
- Other ordering?

---

## Appendix: Key File Map

| File | Relevant Section |
|------|-----------------|
| `paperforge/worker/ocr_tables.py:193-269` | Table N weak-explicit matching (Issue 1) |
| `paperforge/worker/ocr_tables.py:16-19` | `_TRUNCATED_TABLE_ONLY_PATTERN` |
| `paperforge/worker/ocr_figures.py:5245-5300` | `tag_figure_contained_text` (Issue 2) |
| `paperforge/worker/ocr_figures.py:5178-5201` | `_is_contained` |
| `paperforge/worker/ocr_figures.py:5130-5135` | `_LEAK_ROLES` |
| `paperforge/worker/ocr_pdf_spans.py:565-590` | `_backfill_coverage_in_existing` (Issue 3) |
| `paperforge/worker/ocr_pdf_spans.py:698` | `get_text("words", clip=expanded)` |
| `paperforge/worker/ocr_health.py:172-193` | Health gates (Issue 4) |
| `paperforge/worker/ocr_health.py:111` | `page_count` parameter (unused in gates) |
| `paperforge/worker/ocr_figures.py:844-920` | `_cluster_semantic_page_assets` (Issue 5) |
| `paperforge/worker/ocr_figures.py:254-331` | `_is_safe_page_assets_group` |
| `paperforge/worker/ocr_tables.py:137-173` | Table asset collection (Issue 6) |
| `paperforge/worker/ocr_figures.py:4227` | `mark_assets_owned` (figure-only) |
| `project/P2-issues-for-gpt.md` | Detailed P2 issue analysis with paper examples |
| `project/current/ocr_rebuild_audit.md` | 452-paper rebuild audit data |
