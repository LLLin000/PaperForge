# Group-First Cross-Page Figure-Caption Matching — Stage 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Implement the Stage 1 subset of `2026-06-22-group-first-cross-page-figure-caption-matching-design.md` with minimal surgery to the current OCR pipeline. Preserve current asset clustering and most of `build_figure_inventory()` while inserting ledger-aware reservation and primary cross-page settlement ahead of legacy fallback paths.

**Architecture:** Keep the existing group builder (`_build_candidate_figure_groups_from_assets`), strict formal legend gate, and reader/render payload shape. Add raw/residual page ledgers, reserve surplus captions/groups before same-page settlement, skip reserved objects during same-page ownership, then run a primary cross-page settlement phase before existing preproof/group-aware/legacy fallback logic. Do not attempt a full rewrite of `build_figure_inventory()` in Stage 1.

**Tech Stack:** Python 3.10+, pytest, PaperForge OCR workers, fixture-backed regression tests, live-vault rebuild verification.

**Spec:** `docs/superpowers/specs/2026-06-22-group-first-cross-page-figure-caption-matching-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `paperforge/worker/ocr_figures.py` | Primary target. Add ledger helpers, reservation helpers, cross-page settlement phase, and output page semantics. |
| `paperforge/worker/ocr.py` | Keep `caption_group_assignments()` same-page only for render support. No cross-page semantic ownership here. |
| `paperforge/worker/ocr_objects.py` | Verify asset-page-based extraction still works with new `legend_page` / `asset_pages` fields. Modify only if necessary. |
| `tests/test_ocr_figures.py` | Main unit coverage for ledger, reservation, and cross-page settlement. |
| `tests/test_ocr_real_paper_regressions.py` | Observational regression check. Do not tighten broad gold expectations in Stage 1. |
| `tests/test_ocr_figure_reader.py` | Verify downstream reader contract remains compatible with `page`, `legend_page`, and `asset_pages`. |

---

## Non-Negotiable Constraints

- Do not rewrite `build_figure_inventory()` end-to-end in Stage 1.
- Do not change `_build_candidate_figure_groups_from_assets()` clustering behavior in this phase.
- Do not allow reservation logic to run on sidecar/narrow-caption pages in Stage 1.
- Do not let any legacy fallback consume an asset from a multi-asset group.
- Do not let reserved legends/groups re-enter same-page greedy ownership if cross-page settlement fails.
- Do not change `matched_figures.page` away from asset/crop page semantics.
- Do not introduce a heavy page classifier or ML ranking.

---

## Current Flow To Preserve

The current `build_figure_inventory()` roughly does:

```text
collect legends/assets
-> legend dedup
-> build candidate_groups
-> same-page caption-driven matching loop
-> sidecar fallback
-> preproof legend bundle fallback
-> group-aware sequential fallback
-> old asset sequential fallback
```

Stage 1 must only insert new phases into this flow. It must not replace the entire flow.

Target Stage 1 flow:

```text
collect legends/assets
-> legend dedup
-> build candidate_groups
-> build raw ledger
-> build residual ledger seed
-> compute reserved_legend_ids / reserved_group_ids
-> same-page caption-driven matching loop (skip reserved)
-> primary cross-page settlement for reserved/residual objects
-> sidecar fallback (same-page local mode only)
-> preproof legend bundle fallback
-> group-aware sequential fallback
-> old asset sequential fallback (assets not present in any candidate group, or explicitly allowed single-asset compatibility path only)
```

### Stage 1 ownership compatibility note

Current candidate group builders frequently create `single_asset` groups for ordinary figure assets.

Therefore Stage 1 may not enforce a naive rule that old fallback sees no grouped assets at all.

Stage 1 must choose one explicit ownership strategy:

1. **Preferred:** upgrade group-aware fallback / primary cross-page settlement to support `single_asset` groups, then old fallback only sees assets not present in any candidate group.
2. **Compatibility fallback:** old fallback may consume `single_asset` groups through a group-aware compatibility path, but may never split or consume assets from multi-asset groups.

This plan assumes **Option 1 unless proven infeasible**.

Additional hard rule:

```text
Reserved legends skipped by same-page matching must remain cross-page-eligible
even if they were never appended to unmatched_legends.
Cross-page settlement must derive reserved legends from reserved_legend_ids + legends,
not from unmatched_legends alone.
```

---

## Task 1: Lock Same-Page Render Support To Same Page Only

**Files:**
- Modify: `paperforge/worker/ocr.py`
- Test: `tests/test_ocr_figures.py` or `tests/test_ocr_real_paper_regressions.py` if a smaller unit seam is not available

- [ ] **Step 1: Keep `caption_group_assignments()` same-page only**

Requirement:

```text
caption_group_assignments is render support only.
It must never compare page-local coordinates across different pages.
```

Implementation:

1. Keep/confirm the same-page gate in the caption-to-asset loop.
2. Do not add cross-page ownership logic here.
3. Treat this task as guardrail-only. If current code already satisfies same-page-only behavior, do not expand scope in `ocr.py`.

- [ ] **Step 2: Add a targeted test**

Test shape:

1. page 12 has image blocks only
2. page 13 has a formal `Figure 4` caption only
3. `caption_group_assignments()` must not link page 12 image blocks to page 13 caption

- [ ] **Step 3: Run test**

Run the smallest relevant pytest target.

---

## Task 2: Add Eligibility Helpers In `ocr_figures.py`

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Add `strong numbered legend` helper**

Add a helper near the existing legend gate helpers:

```python
def _is_strong_numbered_legend(
    block: dict,
    *,
    caption_score: dict | None = None,
    anchor_supported: bool | None = None,
    caption_text_supported: bool | None = None,
) -> bool:
    ...
```

Contract:

1. figure number exists
2. existing formal legend gate passes
3. not `_is_insufficient_legend_evidence()`
4. `caption_score >= 0.4`
5. validation-first candidate must also have `anchor_supported` or `caption_text_supported`

If `anchor_supported` / `caption_text_supported` are not passed in, the helper must compute them internally.

- [ ] **Step 2: Split group eligibility into structural and ownership-aware helpers**

Add a helper for ledger eligibility:

```python
def _is_structurally_matchable_group(group: dict, *, competing_caption_pages: set[int]) -> bool:
    ...


def _is_unowned_matchable_group(
    group: dict,
    *,
    competing_caption_pages: set[int],
    used_group_ids: set[str],
    used_asset_page_ids: set[tuple],
) -> bool:
    ...
```

Contract:

1. `asset_block_ids` non-empty
2. structural helper does not depend on ownership
3. ownership-aware helper rejects groups already owned or partially consumed
4. group not `_non_body_media`
5. valid `cluster_bbox`
6. `page_assets` group on a competing-caption page is not matchable in Stage 1

- [ ] **Step 3: Unit tests**

Cover:

1. weak truncated legend is not strong
2. strong full `Figure N` legend is strong
3. empty group is not matchable
4. `page_assets` group on competing-caption page is not matchable

---

## Task 3: Add Raw And Residual Ledger Helpers

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Add raw page ledger builder**

Add:

```python
def _build_page_ledger(legends: list[dict], candidate_groups: list[dict]) -> dict[int, dict]:
    ...
```

Fields:

1. `legend_count`
2. `numbered_legend_count`
3. `group_count`
4. `top_legend_count`
5. `bottom_legend_count`
6. `delta`

- [ ] **Step 2: Add residual ledger builder**

Add:

```python
def _build_residual_ledger(
    legends: list[dict],
    candidate_groups: list[dict],
    *,
    competing_caption_pages: set[int],
) -> dict[int, dict]:
    ...
```

Fields:

1. `unmatched_strong_legend_count`
2. `unmatched_matchable_group_count`
3. `residual_delta`

Stage 1 note:

1. This is a seed residual ledger built before ownership.
2. It is used for reservation decisions.
3. It is not authoritative for post-same-page cross-page settlement.

- [ ] **Step 3: Add surplus helpers**

Add exact helpers from the spec:

```python
def _residual_group_surplus(pages: list[int], residual_ledger: dict[int, dict]) -> int:
    ...


def _residual_legend_surplus(pages: list[int], residual_ledger: dict[int, dict]) -> int:
    ...
```

- [ ] **Step 4: Unit tests**

Cover:

1. balanced page -> `delta == 0`
2. caption-surplus page -> positive residual legend surplus
3. group-surplus page -> positive residual group surplus

- [ ] **Step 5: Define post-same-page residual state contract**

Before primary cross-page settlement, recompute or derive post-same-page residual state from live ownership.

Required contract:

```text
reservation uses seed residual ledger
cross-page settlement uses post-same-page unowned groups/legends
```

Implementation options:

1. rebuild a second residual ledger after same-page settlement, or
2. derive residual groups/legends directly from `used_group_ids` and `used_asset_page_ids`

---

## Task 4: Add Reservation Phase Before Same-Page Matching

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Add reservation helper**

Add:

```python
def _reserve_cross_page_objects(
    legends: list[dict],
    candidate_groups: list[dict],
    residual_ledger: dict[int, dict],
    *,
    competing_caption_pages: set[int],
    sidecar_pages: set[int],
) -> tuple[set[str], set[str]]:
    ...
```

Outputs:

1. `reserved_legend_ids`
2. `reserved_group_ids`

Rules:

1. caption-surplus page reserves earliest/topmost `K` strong numbered legends
2. group-surplus page reserves latest/bottommost `K` matchable groups
3. sidecar/narrow-caption pages are excluded from reservation in Stage 1

- [ ] **Step 1a: Define Stage 1 sidecar page detection**

This must be computable before same-page matching. Use a static pre-settlement detector:

```python
sidecar_pages = {
    page for page, legends in legends_by_page.items()
    if len(_same_page_narrow_caption_column(legends, page_width)) >= 2
}
```

- [ ] **Step 2: Integrate reservation before the current caption loop**

In `build_figure_inventory()`:

1. compute `competing_caption_pages`
2. compute `sidecar_pages`
3. build raw ledger
4. build residual ledger seed
5. compute `reserved_legend_ids` / `reserved_group_ids`

- [ ] **Step 3: Make the same-page loop skip reserved objects**

Within `for legend in ordered_legends:`:

1. if `legend_block_id in reserved_legend_ids`, do not attempt same-page ownership
2. same-page matching must also ignore groups whose `group_id` is in `reserved_group_ids`

Important:

Reserved objects are not failures. They are deferred to the primary cross-page settlement stage.

- [ ] **Step 4: Unit test reservation behavior**

Test shape:

1. page 12 has one group
2. page 13 has two strong captions and one group
3. top caption should be reserved backward
4. bottom caption remains eligible for same-page matching

---

## Task 5: Add Primary Cross-Page Settlement Before Legacy Fallback

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Add primary cross-page settlement helper**

Add:

```python
def _settle_cross_page_reserved_objects(
    reserved_legend_ids: set[str],
    reserved_group_ids: set[str],
    legends: list[dict],
    candidate_groups: list[dict],
    structured_blocks: list[dict],
    matched_figures: list[dict],
    ambiguous_figures: list[dict],
    unmatched_legends: list[dict],
    used_group_ids: set[str],
    used_asset_page_ids: set[tuple],
    *,
    residual_ledger: dict[int, dict],
) -> None:
    ...
```

Rules:

1. reserved legends look backward to `P-1`, then `P-2`
2. reserved groups look forward to `P+1`, then `P+2`
3. settlement order uses page distance first, then reading order
4. use lightweight blockers for `P±2`
5. do not use weak same-page score to override reservation
6. forward settlement may use both reserved future legends and strong unmatched future legends left unowned after same-page settlement
7. on every successful cross-page match, update both `used_group_ids` and `used_asset_page_ids` before control returns to any legacy fallback phase

- [ ] **Step 2: Define Stage 1 interruption rules**

Add `INTERRUPTION_ROLES` exactly as in the spec:

```python
INTERRUPTION_ROLES = {
    "section_heading",
    "subsection_heading",
    "sub_subsection_heading",
    "table_caption",
    "table_html",
    "reference_heading",
    "reference_item",
    "backmatter_heading",
    "backmatter_body",
}
```

Optional simple blocker:

```text
intervening page body_paragraph count >= 3 => strong interruption
```

- [ ] **Step 3: Redesign `_allow_previous_page_sequential_match()` or replace it**

Stage 1 contract:

1. input should be a group, not a first asset
2. use group `cluster_bbox`
3. do not require caption-at-page-top heuristic
4. keep the gate conservative, but aligned to reserved settlement semantics

It is acceptable to replace the old helper with a new reserved-settlement-specific check rather than broadening the old helper in place.

- [ ] **Step 3a: Preserve full matched-figure schema in cross-page settlement**

Cross-page matched entries must preserve the current same-page entry shape, then add Stage 1 fields.

Required fields include:

```python
page = group_page
legend_page = legend_page
asset_pages = sorted(unique_asset_pages)
settlement_type = "cross_page_backward" | "cross_page_forward"
cluster_bbox = group["cluster_bbox"]
asset_block_ids = [...]
matched_assets = [{"block_id": ..., "bbox": ...}, ...]
flags += ["cross_page_match"]
```

- [ ] **Step 4: Wire primary cross-page settlement before legacy fallback chain**

Placement:

1. after same-page caption loop completes
2. before sidecar fallback / preproof bundle / group-aware sequential fallback / old sequential fallback

- [ ] **Step 5: Unit tests**

Add focused tests for:

1. backward settlement: extra caption on current page uses prior-page group
2. forward settlement: extra group on current page uses later-page caption
3. `P-2` blocked by strong interruption

---

## Task 6: Prevent Legacy Fallback From Re-Stealing Ownership

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Ensure reserved failures become held/ambiguous**

If reserved settlement fails:

1. reserved legend -> `ambiguous_figures` with `hold_reason="reserved_cross_page_no_valid_group"`
2. reserved group -> existing unresolved surface with `hold_reason="reserved_cross_page_no_valid_legend"`
3. neither may re-enter same-page ownership later

Stage 1 mapping to existing surfaces:

1. multi-asset reserved group failure -> `unresolved_clusters`
2. single-asset reserved group failure -> `unmatched_assets`
3. do not invent a brand-new held-group artifact in Stage 1 unless downstream code already supports it

- [ ] **Step 2: Restrict old single-asset fallback**

Old fallback may only consume assets that satisfy one of these:

1. do not belong to any candidate group, or
2. belong to an explicitly allowed `single_asset` compatibility path if group-aware fallback was not upgraded

In all cases, old fallback may never:

1. consume any asset from a multi-asset group
2. consume any asset already owned via group ownership
3. split a group after reservation

- [ ] **Step 3: Unit tests**

Cover:

1. two captions, one group -> ambiguous/held, not duplicate match
2. grouped asset may not be consumed as bare asset by old fallback

---

## Task 7: Extend Output Schema Without Breaking Crop/Render

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Modify only if needed: `paperforge/worker/ocr_objects.py`
- Test: `tests/test_ocr_figures.py`, `tests/test_ocr_figure_reader.py`

- [ ] **Step 1: Add output fields to matched figure entries**

Required fields:

```python
{
    "page": int,              # primary asset/crop/render page
    "asset_pages": list[int],
    "legend_page": int,
    "settlement_type": str,
}
```

Stage 1 guarantee:

```text
matched_figures.page == primary asset/crop page
```

This requirement applies to all matched figure entries, not just cross-page ones.

For same-page entries:

```text
legend_page = legend page
asset_pages = [entry["page"]]
settlement_type = "same_page"
```

- [ ] **Step 2: Verify object extraction continues to crop from asset page**

If `ocr_objects.py` assumes `page` is the crop page, keep that contract unchanged.

- [ ] **Step 3: Reader/output tests**

Add one test asserting:

1. cross-page match has `page=asset_page`
2. `legend_page=caption_page`
3. `asset_pages=[...]`
4. `settlement_type="cross_page_backward"` or `cross_page_forward`

---

## Task 8: 2HEUD5P9 Verification

**Files:**
- Test/reference: live vault rebuild output

- [ ] **Step 1: Add a focused regression-style test fixture if feasible**

If a small synthetic test can cover the ownership pattern, prefer that first.

- [ ] **Step 2: Rebuild 2HEUD5P9 in the vault and inspect figure inventory**

Verify:

1. Figure 4 uses page 12 assets
2. Figure 5 uses page 13 assets
3. Figure 4 does not consume page 13 Figure 5 panels
4. page 12 Figure 4 panels are no longer orphaned because of page-13 same-page theft

- [ ] **Step 3: Spot-check rendered outputs**

Check:

1. `render/figures/figure_004.md`
2. `render/figures/figure_005.md`
3. `assets/figures/figure_004.jpg`
4. `assets/figures/figure_005.jpg`

---

## Acceptance Test Matrix

- [ ] `page12 group + page13 Fig4 caption + page13 Fig5 group + page13 Fig5 caption` -> Figure 4 backward, Figure 5 same-page
- [ ] same-page one-to-one case remains unchanged
- [ ] caption-surplus reserve works
- [ ] group-surplus forward works
- [ ] two captions cannot claim one group
- [ ] old fallback cannot split grouped assets
- [ ] single-asset cross-page case still works after reservation/fallback refactor
- [ ] cross-page match emits `page`, `asset_pages`, `legend_page`, `settlement_type`

---

## Suggested Verification Commands

```bash
python -m pytest tests/test_ocr_figures.py -v --tb=short
python -m pytest tests/test_ocr_figure_reader.py -v --tb=short
python -m pytest tests/test_ocr_real_paper_regressions.py -v --tb=short
python -m paperforge --vault "D:/L/OB/Literature-hub" ocr rebuild 2HEUD5P9
```

---

## Exit Criteria

Stage 1 is complete only when:

1. current same-page normal figure behavior remains stable
2. reserved captions/groups are excluded from same-page greed
3. primary cross-page settlement runs before legacy fallback
4. legacy fallback cannot break group ownership
5. 2HEUD5P9 Figure 4/5 ownership is corrected
