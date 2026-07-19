# PR1: Deterministic Local Fixes — Implementation Plan Draft

**Issues:** 3 (backfill bbox clamp) + 1A (validation-first fallthrough) + 1B (table continuation materialization) + 4 (short-form health profile)

**Implementation order (strict):** 3 → 1A → 1B → 4

**Rationale:** Order minimizes conflict surface. Issue 3 is a pure isolated bug in `ocr_pdf_spans.py`. Issues 1A/1B are both in `ocr_tables.py` and share the same test file, but 1A is the simpler gate change (one `continue` guard), and 1B is the richer continuation helper. Doing 1A first so its passing tests are baseline before 1B's materialization logic. Issue 4 is an independent health-layer change last.

---

## File Map

| File | Role in PR1 |
|------|-------------|
| `paperforge/worker/ocr_pdf_spans.py` | Add `_word_belongs_to_block()` + `_word_center_inside_rect()`; insert word-level filter in `backfill_missing_text_from_pdf()` |
| `paperforge/worker/ocr_tables.py` | Change validation-first `continue` guard (1A); add `_find_table_caption_continuation()` + `_materialize_table_caption()` (1B) |
| `paperforge/worker/ocr_health.py` | Add `_health_profile()`; gate structural_blockers on `short_form`; add report fields `health_profile`, `waived_gates`, `degraded_reason` |
| `tests/test_ocr_pdf_text_fallback.py` | **New file.** Unit tests for backfill word-level filtering |
| `tests/test_ocr_tables.py` | Tests for 1A (validation-first fallthrough) + 1B (split-caption materialization, anti-overreach) |
| `tests/test_ocr_render.py` | Test for render skipping consumed continuation block (1B spillover) |
| `tests/test_ocr_health.py` | Tests for short-form profile behavior |

**No other files modified.** No changes to `ocr_roles.py`, `ocr_figures.py`, pipeline wiring, or any module outside the three listed above.

---

## Issue 3: Backfill Bbox Expansion Overflow

### Validated Root Cause

`backfill_missing_text_from_pdf` at `ocr_pdf_spans.py:687-695` applies a 1%/5% padding margin around the target block's bbox before calling `pdf_page.get_text("words", clip=expanded)`. When a neighbor block is close enough, the expanded clip rectangle overlaps it, and `get_text` returns that neighbor's words as part of the backfill text. The render-layer dedup (5-gram Jaccard ≥0.8) suppresses most duplicates, but:

- 60-80% overlap can leak through the threshold
- A genuinely empty block that needs backfill can be false-rejected if OCR text from the same page is similar enough to the backfill text

### Preferred Low-Risk Approach

**Word-level rejection after expanded extraction.** Keep the expansion for search (it's needed because OCR bboxes can drift from PDF text layer). But filter the returned word list against the original (unexpanded) bbox before reassembling text.

Do NOT change the expansion margin. Do NOT change the overlap dedup threshold. Do NOT change any caller behavior.

**Changes to `ocr_pdf_spans.py`:**

1. Add helper near `_bbox_overlap_ratio` (~line 277):
   - `_word_center_inside_rect(word_bbox, block_rect) -> bool` — word center inside rect
   - `_word_belongs_to_block(word_bbox, block_rect) -> bool` — center-inside OR ≥30% bbox overlap (tolerates partial misalignment)

2. In `backfill_missing_text_from_pdf` (~line 698), change:
   ```python
   words = pdf_page.get_text("words", clip=expanded)
   text = _words_to_text(words)
   ```
   to:
   ```python
   words = pdf_page.get_text("words", clip=expanded)
   words = [
       w for w in words
       if len(w) >= 4 and _word_belongs_to_block(tuple(w[:4]), rect)
   ]
   text = _words_to_text(words)
   ```

### Rejected Approaches

- **Remove expansion entirely** — breaks alignment tolerance for blocks where OCR bbox is slightly misaligned with PDF text layer. 4DU8LEH2 and similar papers would regress.
- **Change the dedup threshold** — fixes the symptom, not the root cause. Could cause genuine duplicate text in render.
- **Per-page pre-clustering of blocks** — architectural churn for a two-helper fix.

### Tests

New file `tests/test_ocr_pdf_text_fallback.py`:
- `test_backfill_expanded_clip_filters_words_to_original_bbox` — Fake PDF page returns words inside and outside the original bbox. After backfill, only the inside word should be recovered.
- `test_backfill_keeps_slightly_misaligned_words_by_center_or_overlap` — Word just outside rect edge but with center inside (or overlap ≥30%) is still accepted.

### Commit Boundary

```bash
# after tests fail → after implementation passes → commit:
git add paperforge/worker/ocr_pdf_spans.py tests/test_ocr_pdf_text_fallback.py
git commit -m "fix: clamp pdf backfill words to original bbox"
```

---

## Issue 1A: Validation-First Bare "Table N" Fallthrough

### Validated Root Cause

`build_table_inventory` at `ocr_tables.py:193-214` has a guard:
```python
if is_validation_first_candidate and is_weak_truncated:
    if not same_page_assets:
        held_tables.append(...)
    continue  # <-- exits unconditionally
```

When same-page assets DO exist (69TA9S8W: 12 bare "Table N" captions on pages with clear table images), the `continue` skips the rest of the matching loop. The weak-explicit path below (lines 215-297) has the spatial gates (`_has_strong_spatial_evidence_for_bare_table`, tie-break) that *could* produce a match, but it never runs.

Key insight: the `continue` was there because without any text evidence, matching seemed pointless. But the weak-explicit path has since been hardened with spatial gating (strong evidence or continuation geometry elevation). The same-page asset may provide enough spatial evidence.

### Preferred Low-Risk Approach

**Add one conditional: only `continue` when there are no same-page assets.** When assets exist, fall through into the existing weak-explicit path. No new scoring, no new gating — just removing the unconditional bypass.

The existing `test_validation_first_table_candidate_with_asset_can_still_match` (test_ocr_tables.py:470-504) already tests the case where the caption has **full text** ("Table 3. Cell counts..."). No test exists for **weak-truncated** + validation-first + same-page asset — that's the exact gap.

**Changes to `ocr_tables.py:193-214`:**

```python
if is_validation_first_candidate and is_weak_truncated:
    same_page_assets = [
        a for i, a in enumerate(assets)
        if i not in used_asset_indices and a.get("page", 0) == caption_page
    ]
    if not same_page_assets:
        held_tables.append({
            "table_id": f"held_table_{len(held_tables) + 1:03d}",
            "caption_block_id": caption.get("block_id", ""),
            "page": caption_page,
            "caption_text": caption_text,
            "table_number": table_num,
            "formal_table_number": formal_table_number,
            "hold_reason": "insufficient_caption_evidence",
            "zone": caption.get("zone", ""),
            "style_family": caption.get("style_family", ""),
            "marker_signature": caption.get("marker_signature", {}),
        })
        continue
    # same-page asset exists → fall through into weak-explicit matching
```

### Rejected Approaches

- **Add a second scoring path for validation-first** — duplicates the scoring logic. The existing weak-explicit path already handles bare "Table N" via `_bare_table_tie_break`, scoring, and spatial evidence.
- **Change validation-first detection** — the candidate detection is correct; the bug is what happens *after* detection.
- **Match in a separate loop** — the match logic depends on `used_asset_indices` tracking across captions; a separate loop would need to replicate that state machine.

### Tests

In `tests/test_ocr_tables.py`:
- `test_validation_first_bare_table_with_same_page_asset_falls_through` — Block with role=body_paragraph, marker_signature.table_number, display_zone, table_caption_like (validation-first), text="Table 1" (weak_truncated), same-page table asset exists. Expects: held_tables empty, 1 table matched with asset.

**Existing relevant tests that must continue passing:**
- `test_validation_first_table_candidate_remains_stable_under_anchor_first_roles` (line 112) — validation-first WITH full text, already matches
- `test_table_matching_can_hold_when_caption_and_asset_conflict` (line 398) — validation-first + weak_truncated + NO same-page asset, should still hold
- `test_validation_first_table_candidate_with_asset_can_still_match` (line 470) — validation-first + full text + asset, already matches

### Commit Boundary

```bash
# after 1A tests pass, before 1B changes:
git add paperforge/worker/ocr_tables.py tests/test_ocr_tables.py
git commit -m "fix: allow validation-first bare tables to fall through"
```

---

## Issue 1B: Table Continuation Materialization

### Validated Root Cause

This is the split-caption case (2HJSWV3V). OCR breaks a table caption into two adjacent text blocks:

| Block | Text | Role Assigned |
|-------|------|---------------|
| Block 11 | "Table 2" | `table_caption` |
| Block 12 | "Structural parameters of..." | `figure_caption` (WRONG) |
| Block 13 | [table image] | `media_asset` |

Block 12 does not start with "Table", has no table marker, so the table caption collector (line 148: `role in {"table_caption", "table_caption_candidate"}`) never sees it. OCR role assignment (`ocr_roles.py:758-770`) promotes it to `figure_caption` via `body_paragraph + legend_like + figure_title` heuristic.

**Two separate effects:**
1. **Stable caption-completeness bug** — Table 2's full caption is "Table 2 Structural parameters of nanocomposites..." but the table inventory records only "Table 2". Complete text is lost from the table caption.
2. **Conditional matching bug** — If geometry is also weak or the block falls into the validation-first gap (already fixed by 1A), the table can become unmatched. But even after 1A, the matching algorithm scores "Table 2" without the continuation text against the asset — the match might be weaker than it should be.

### Preferred Low-Risk Approach

**Add local continuation detection and materialization inside `build_table_inventory`.** Do NOT merge OCR blocks globally. Do NOT change role assignment. Instead, detect the continuation block after caption collection and merge text/metadata for matching purposes only.

**Implementation details:**

1. Add `_find_table_caption_continuation(caption_block, structured_blocks) -> dict | None`:
   - Trigger: current caption is weak-truncated ("Table N")
   - Same page
   - y-gap between blocks ≤ 25px
   - x-overlap ratio ≥ 0.5 OR left-edge delta < 40px
   - Continuation role ∈ {figure_caption, body_paragraph, unknown_structural, table_caption_candidate}
   - Continuation text does NOT start with Fig/Figure/Scheme/Plate
   - No media_asset/table_image sits between the two blocks

2. Add `_materialize_table_caption(caption, continuation) -> (merged_caption, consumed_ids)`:
   - Creates a merged caption dict for matching only
   - Merges text, extends bbox to cover both blocks
   - Tracks continuation's `block_id` in `consumed_block_ids`

3. In the `build_table_inventory` caption loop (~line 183), insert after weak-truncated detection:
   ```python
   materialized_caption = caption
   continuation = None
   continuation_ids: list[str] = []
   if is_weak_truncated:
       continuation = _find_table_caption_continuation(caption, structured_blocks)
       materialized_caption, continuation_ids = _materialize_table_caption(caption, continuation)
       caption_text = materialized_caption.get("text", "")
   ```
   Then pass `materialized_caption` to scoring instead of raw `caption`.

4. Extend `consumed_block_ids` with `continuation_ids` in the final table dict assembly (around lines 448-482).

### Rejected Approaches

- **Merge raw OCR blocks before role assignment** — broader blast radius; affects all downstream consumers (figure pipeline, render, health). Risk of regressions across 33 affected papers.
- **Change role assignment for continuation blocks** — would require `ocr_roles.py` changes and retraining the role-assignment heuristics. Not worth the risk when local detection is precise.
- **Use font/style matching** — unreliable across different OCR outputs; spatial proximity is more robust.
- **Do NOT merge, just improve matching** — leaves caption incomplete in the inventory. Downstream consumers (render, health, export) see truncated text.

### Tests

In `tests/test_ocr_tables.py`:
- `test_split_table_caption_materializes_continuation_stolen_as_figure_caption` — Block1 = "Table 2" (table_caption), Block2 = "Structural parameters..." (figure_caption), same page, small y-gap. Expects: merged caption text starts with "Table 2 Structural", continuation block_id in consumed_block_ids.
- `test_split_table_caption_does_not_steal_real_figure_caption` — Same setup but Block2 starts with "Figure 3." → must NOT be consumed.
- `test_split_table_caption_with_wide_gap_not_materialized` — y-gap = 50px → continuation NOT matched.

In `tests/test_ocr_render.py`:
- `test_materialized_table_caption_continuation_is_skipped_by_render_when_consumed` — Verify that a continuation block in `consumed_block_ids` is excluded from rendered markdown.

### Commit Boundary

```bash
# after 1B tests pass + render test passes:
git add paperforge/worker/ocr_tables.py tests/test_ocr_tables.py tests/test_ocr_render.py
git commit -m "fix: materialize split table caption continuations"
```

---

## Issue 4: Short-Paper Health False Red

### Validated Root Cause

`build_ocr_health` at `ocr_health.py:179-185` unconditionally counts missing abstract, references, and section headings as structural blockers, regardless of paper format. Letters/Editorials/Short Communications ≤2 pages by design lack headings, abstract sections, or reference zones. The health report goes red (structural_blockers ≥ 2 → `overall = "red"`, `needs_rebuild = True`) even when OCR is perfect.

### Preferred Low-Risk Approach

**Add a `page_count`-based health profile selector.** Papers with ≤2 pages enter a `short_form` profile that waives abstract, heading, and references structural-blocker gates. The information is still reported (for transparency), but does not drive the overall color or rebuild decision.

**New fields:**
- `health_profile: "standard" | "short_form"`
- `waived_gates: list[str]` — which gates were waived for this profile
- `degraded_reason: str` — `"short_paper_format"` when profile is short_form

**Changes to `ocr_health.py`:**

1. Add `_health_profile(page_count: int) -> str`.
2. In `build_ocr_health`, compute profile, then conditionally exempt:
   ```python
   profile = _health_profile(page_count)
   waived_gates: list[str] = []
   structural_blockers = 0

   if profile == "short_form":
       waived_gates = ["abstract_found", "section_heading_count"]
       if not references_found:
           waived_gates.append("references_found")
   else:
       if not abstract_found: structural_blockers += 1
       if not references_found: structural_blockers += 1
       if section_heading_count < 2: structural_blockers += 1
   ```
3. Add report fields: `health_profile`, `waived_gates`, `degraded_reason` (when short_form).

**Edge case:** `references_found` is waived too — short papers often have no numbered references, only footnoted URLs or no reference section at all. The data remains in the report for inspection.

### Threshold Selection

`page_count <= 2` is the safe threshold. Letters (1-2pp), Editorials (1-2pp), Short Communications (2pp). Three-page papers with structure issues should still flag — 3pp is enough for a minimal IMRaD structure.

### Rejected Approaches

- **Auto-detect paper type by role patterns** — over-engineered. Page count is the simplest reliable proxy. A 2-page paper *cannot* have a full IMRaD structure by definition.
- **Reduce threshold instead of waiving** — lowering `section_heading_count` threshold would let short papers through but also weaken the signal for regular papers.
- **Make structural_blockers configurable** — adds complexity without narrowing the blast radius. Direct waiver is simpler.

### Tests

In `tests/test_ocr_health.py`:
- `test_short_form_health_does_not_go_red_for_missing_abstract_headings_and_refs` — page_count=2, no headings, no abstract, no refs → `health_profile == "short_form"`, `overall` not "red", `needs_rebuild == False`, `"abstract_found" in waived_gates`.
- `test_standard_profile_still_flags_missing_structure` — page_count=5, same empty structure → `health_profile == "standard"`, `overall == "red"`.

**Existing tests that must continue passing:**
- All tests passing `page_count=1` with headings present (e.g., `test_health_counts_all_heading_tiers_and_requires_stronger_reference_evidence`, line 4) — must still work fine since they include headings.
- `test_health_report_is_independent_from_ocr_status` (line 23) — page_count=3, should get standard profile.
- `test_ocr_health_includes_span_spine_and_layout_signals` (line 148) — page_count=2 but has signals; must not be affected.

### Commit Boundary

```bash
# after tests pass:
git add paperforge/worker/ocr_health.py tests/test_ocr_health.py
git commit -m "fix: add short-form OCR health profile"
```

---

## Integration Safety

### Regression Verification (must run before PR1 merge)

```bash
python -m pytest \
  tests/test_ocr_pdf_text_fallback.py \
  tests/test_ocr_tables.py \
  tests/test_ocr_render.py \
  tests/test_ocr_health.py \
  -q --tb=short
```

**Expected: All pass, 0 failures.**

Then run the full OCR regression suite to catch cross-module effects:
```bash
python -m pytest tests/test_ocr_*.py -q --tb=short -x
```

### Cross-Module Risks

| Change | Could affect | Risk level | Mitigation |
|--------|-------------|------------|------------|
| Issue 3 word filter | All blocks going through `backfill_missing_text_from_pdf` | Medium — could reject words that belong to block but are outside bbox | Center-inside OR overlap ≥30% tolerance; existing tests pass |
| Issue 1A fallthrough | Table matching for validation-first bare tables | Low — only adds a matching attempt for cases that were previously ignored | Identical path as weak-explicit; existing bare-table tests guard regressions |
| Issue 1B continuation | Table inventory, render consumed_block_ids | Low — continuation detection gates are tight; render skip for consumed blocks is already an existing pattern | Anti-overreach test guards real figure captions |
| Issue 4 short form | `needs_rebuild` signal for short papers | Low — only changes behavior for page_count ≤ 2, which already lacks structure | Standard profile logic unchanged; all existing tests pass |

### Non-Goals for PR1

- Do NOT change `ocr_roles.py` — role assignment is intentionally untouched
- Do NOT change figure containment or `_container_bbox` — that's PR2
- Do NOT change page-assets clustering — that's PR3
- Do NOT change ownership arbitration — that's PR3
- Do NOT add new dependencies or configuration files
- Do NOT refactor existing helpers into shared modules
