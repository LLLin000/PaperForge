# OCR Visual Grammar Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining OCR-v2 figure/table residuals by implementing the approved `P0 -> P1A -> P1B -> P2 -> P3A/B/C` visual-grammar hardening sequence without destabilizing the existing grouping and ownership foundations.

**Architecture:** Preserve the current atomic caption-independent semantic grouping as the base visual truth, then layer higher-order composite parent candidates, page-local grammar validation, and figure/table early separation on top. Each stage is intentionally isolated so behavior changes are measurable and reversible, with diagnostic-only phases before ownership-bearing phases.

**Tech Stack:** Python, `pytest`, PaperForge OCR pipeline (`ocr_figures.py`, `ocr.py`, `ocr_rebuild.py`, `ocr_tables.py`), audit corpus under `audit/`, real-paper regressions in `tests/test_ocr_real_paper_regressions.py`.

---

## 1. Scope And Execution Rules

This plan implements the approved design at:

- `docs/superpowers/specs/2026-06-23-ocr-visual-grammar-hardening-design.md`

It must be executed as **staged capability passes**, not as one all-at-once refactor.

Hard rules:

1. Do not widen atomic semantic grouping thresholds in `_cluster_semantic_page_assets()`.
2. Do not combine P1A and P1B in one unchecked diff.
3. Do not let `composite_parent` candidates flow into legacy fallback paths before explicit parent-aware arbitration exists.
4. Do not introduce a second ownership matcher in P2; P2 is validator-only at first.
5. Do not rewrite the figure/table pipelines together in one step; P3A/B/C must remain staged.
6. After each stage, run the listed verification before starting the next stage.
7. Update `PROJECT-MANAGEMENT.md` after each landed stage.
8. Execute this roadmap as separate tickets: `Stage 0 + P0-A + P0-B`, then `P1A`, then `P1B`, then `P2`, then `P3A/B/C`.

---

## 2. Files Expected To Change

Primary implementation files:

- `paperforge/worker/ocr_figures.py`
- `paperforge/worker/ocr.py`
- `paperforge/worker/ocr_rebuild.py`
- `paperforge/worker/ocr_tables.py`

Primary test files:

- `tests/test_ocr_figures.py`
- `tests/test_ocr_figure_reader.py`
- `tests/test_ocr_render.py`
- `tests/test_ocr_real_paper_regressions.py`

Docs / logging:

- `PROJECT-MANAGEMENT.md`

Reference context only:

- `audit/`
- `project/current/ocr-v2-active-queue.md`
- `project/current/ocr-v2-generalization-boundary.md`

---

## 3. Stage 0 - Preflight / Safety Gate

**Purpose:** Confirm the current branch still contains the already-landed governance foundations and that the new plan starts from the expected state.

**Files:**
- Modify: none
- Verify: `paperforge/worker/ocr_figures.py`, `paperforge/worker/ocr.py`, `paperforge/worker/ocr_rebuild.py`
- Test: `tests/test_ocr_figures.py`, `tests/test_ocr_figure_reader.py`, `tests/test_ocr_render.py`

- [ ] **Step 1: Verify foundation seams exist**

Check for these functions/helpers in `paperforge/worker/ocr_figures.py`:

```python
_build_semantic_figure_groups_from_assets
_make_local_pairing_hypothesis
_infer_local_pairing_mode
_reserve_cross_page_objects
_settle_cross_page_reserved_objects
_promote_sequence_matches
_build_ownership_conflicts
attach_ownership_conflicts
```

- [ ] **Step 2: Run foundation verification**

Run:

```bash
python -m pytest tests/test_ocr_figures.py tests/test_ocr_figure_reader.py tests/test_ocr_render.py -q
```

Expected:

```text
all figure/reader/render tests pass except any separately documented pre-existing non-plan failures
```

- [ ] **Step 2.5: Record exact baseline failures if any exist**

If the baseline is not green, record the exact failing test node ids before any code change.

Rule:

```text
Only those exact node ids count as pre-existing later.
Any new failing node id introduced after a stage blocks progression.
```

- [ ] **Step 3: Stop if the baseline is missing required seams**

If any required seam is absent, do **not** start P0.
Write a dependency note instead.

---

## 4. Stage P0-A - Conflict Persistence Order

**Purpose:** Ensure `ownership_conflicts` is persisted into `figure_inventory.json` after `table_inventory` exists.

**Files:**
- Modify: `paperforge/worker/ocr.py`, `paperforge/worker/ocr_rebuild.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Write a failing persistence-order test**

Add a focused test that exercises the persisted artifact, not just the in-memory helper.

Hard requirement:

```text
P0-A must assert the written `figure_inventory.json`, not only `_build_ownership_conflicts()`.
```

Minimal target contract:

```python
_attach_conflicts_and_write_inventories(...)
written = read_json(tmp_path / "figure_inventory.json")
assert "ownership_conflicts" in written
assert isinstance(written["ownership_conflicts"], list)
```

- [ ] **Step 2: Run the focused test to confirm failure**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "ownership_conflict" -v --tb=short
```

Expected:

```text
failure if persistence order is still stale
```

- [ ] **Step 3: Reorder write path minimally**

Required code shape in both entry points:

```python
figure_inventory = build_figure_inventory(structured)
reader_payload = synthesize_reader_figures(...)
table_inventory = build_table_inventory(structured)
attach_ownership_conflicts(figure_inventory, table_inventory)
write_figure_inventory(..., figure_inventory)
write_table_inventory(..., table_inventory)
```

Do not broaden this task into figure/table matcher changes.

- [ ] **Step 4: Re-run the focused verification**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "ownership_conflict" -v --tb=short
```

Expected:

```text
PASS
```

---

## 5. Stage P0-B - Bundle-Source Duplicate Legend Canonicalization

**Purpose:** Canonicalize caption-list / bundle-source legend duplicates without turning dedup losers into silent gaps and without disabling bundle-only fallback.

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`, `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write the failing duplicate-legend tests**

Add synthetic regressions covering:

```python
test_bundle_source_duplicate_loser_is_accounted_not_gap()
test_dwqq_style_duplicate_legend_prefers_real_cross_page_instance()
test_same_page_real_legend_outranks_bundle_duplicate()
test_bundle_only_source_legends_remain_eligible_for_legend_bundle_fallback()
```

Required assertions:

```python
assert dedup_entry["dedup_reason"] == "bundle_source_duplicate_loser"
assert completeness["gap_count"] == 0
assert matched_fig["legend_page"] == expected_real_page
```

- [ ] **Step 2: Run only the duplicate-legend slice**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "bundle_source_duplicate or bundle_only_source or deduped_duplicate or same_page_real_legend" -v --tb=short
```

- [ ] **Step 3: Implement bundle-source legend identification and dedup priority**

Required helper direction:

```python
_identify_bundle_source_legend_ids(...)
_legend_has_same_page_asset(...)
_legend_has_adjacent_page_asset(...)
_legend_dedup_priority(...)
```

Required invariants:

```text
bundle-source lowers canonical priority only when a stronger duplicate exists
bundle-only legends remain eligible for legend_bundle fallback
dedup losers are recorded as accounted outcomes, not gaps
```

- [ ] **Step 4: Re-run targeted and real-paper verification**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "bundle_source_duplicate or bundle_only_source or deduped_duplicate or same_page_real_legend" -v --tb=short
python -m pytest tests/test_ocr_real_paper_regressions.py::test_dwqqk2yb_figure3_is_fully_owned_not_merely_captured -v --tb=short
```

Expected:

```text
both PASS
```

---

## 6. Stage P1A - Composite Parent Detector (Diagnostic-Only)

**Purpose:** Build same-page composite parent candidates and expose them for audit/debugging without changing ownership behavior.

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`, `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write the failing P1A diagnostic tests**

Add synthetic tests that assert parent candidates are emitted but ownership remains unchanged.

Required candidate expectations:

```python
before = build_figure_inventory(blocks, enable_composite_parent_detection=False)
after = build_figure_inventory(blocks, enable_composite_parent_detection=True)

assert after["matched_figures"] == before["matched_figures"]
assert after["unmatched_assets"] == before["unmatched_assets"]
assert after["unresolved_clusters"] == before["unresolved_clusters"]
assert after["official_figure_count"] == before["official_figure_count"]
assert after["composite_parent_candidates"]
```

If no clean test seam exists for an `enable_composite_parent_detection` flag, use fixed fixture-level expected outputs instead and prove that `matched_figures`, `unmatched_assets`, and `unresolved_clusters` remain unchanged while diagnostic candidates appear.

Recommended paper-shaped fixtures:

```text
VFS8CBW2-like dense composite page
24YKLTHQ-like under-grouped composite page
ordinary multi-figure page that must NOT form one mega-parent
```

Additional boundary:

```text
P1A diagnostics must be audit-visible but behavior-preserving.
```

- [ ] **Step 2: Run the detector-only test slice**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "composite_parent and diagnostic" -v --tb=short
```

- [ ] **Step 3: Implement visual-only parent candidate construction**

Suggested helper:

```python
_build_composite_parent_figure_groups_visual_only(
    atomic_groups,
    assets,
    structured_blocks,
    page_width,
)
```

Hard requirement:

```text
P1A visual parent construction must not accept `legends` as topology input.
Caption evidence belongs only to P1B eligibility/scoring.
```

Required constraints:

```text
same-page only
visual-only construction
no caption identity in topology construction
confidence bands apply
0.50-0.75 stays diagnostic-only
```

Required diagnostic artifact shape:

```python
{
    "group_id": str,
    "group_type": "composite_parent",
    "child_group_ids": list[str],
    "asset_block_ids": list[str],
    "cluster_bbox": list[float],
    "parent_evidence": list[str],
    "parent_confidence": float,
    "ownership_enabled": False,
}
```

- [ ] **Step 4: Verify behavior-preserving diagnostics**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "composite_parent and diagnostic" -v --tb=short
python -m pytest tests/test_ocr_real_paper_regressions.py -k "VFS8CBW2 or 24YKLTHQ or 2UIPV93M" -v --tb=short
```

Expected:

```text
diagnostic candidate visibility improves
ownership counts do not worsen on verified cases
```

---

## 7. Stage P1B - Composite Parent Ownership Arbitration

**Purpose:** Allow only strong parent candidates to enter ownership, with explicit parent-over-child arbitration.

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`, `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write the failing arbitration tests**

Add tests covering:

```python
test_composite_parent_acceptance_consumes_children()
test_weak_parent_candidate_does_not_consume_children()
test_competing_caption_veto_blocks_parent_promotion()
test_parent_candidate_never_enters_legacy_fallback_directly()
```

- [ ] **Step 2: Run the P1B focused failures**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "composite_parent and (consume or veto or weak or legacy)" -v --tb=short
```

- [ ] **Step 3: Implement parent-over-child arbitration path**

Required behavior:

```text
parent and child are not peer ownership candidates
if parent accepted -> child groups/assets reserved or consumed by parent
if parent weak/rejected -> child groups remain available
legacy fallback paths must not consume composite_parent directly
```

Do not let `composite_parent` flow into old fallback branches as if it were a normal `distance_cluster` or `single_asset` group.

Required integration shape:

```text
keep atomic `candidate_groups` as the ordinary ownership input
keep `composite_parent_candidates` in a separate collection
run parent arbitration before normal same-page candidate selection for a legend
only if a parent wins, synthesize a parent-backed region_match and consume child groups/assets
otherwise continue the existing atomic path unchanged
```

Forbidden approach:

```python
candidate_groups = atomic_groups + composite_parent_candidates
```

- [ ] **Step 4: Re-run paper-level validations**

Run:

```bash
python -m pytest tests/test_ocr_real_paper_regressions.py -k "VFS8CBW2 or 24YKLTHQ or 2UIPV93M or RKSLQRIM" -v --tb=short
```

Expected:

```text
lower unresolved/unmatched composite residuals without mega-group regressions
```

---

## 8. Stage P2 - Mixed Caption Grammar Validator

**Purpose:** Annotate and validate local grammar consistency without replacing the existing matcher.

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`, `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write failing validator tests**

Add tests covering:

```python
test_page_local_grammar_annotations_include_status_reason_evidence()
test_stronger_ordinary_below_pair_is_protected_from_sidecar_takeover()
test_mixed_page_can_be_self_consistent_without_one_global_mode()
test_incompatible_local_grammar_marks_conflict()
```

### Required output fields

```python
assert hypothesis["grammar_status"] in {"accepted", "deferred", "rejected", "conflict"}
assert isinstance(hypothesis["grammar_reason"], str)
assert isinstance(hypothesis["grammar_evidence"], list)
```

- [ ] **Step 2: Run the focused P2 slice**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "grammar_status or sidecar_takeover or mixed_page" -v --tb=short
```

- [ ] **Step 3: Implement annotation-first validator**

Suggested helper:

```python
_validate_page_local_caption_grammar(
    local_pairing_hypotheses,
    candidate_groups,
    legends,
    ownership,
    page_width,
)
```

Hard boundary:

```text
annotate first
protect obvious stronger ordinary pairs
do not globally replace same-page scoring order in this pass
```

- [ ] **Step 4: Re-run mixed-grammar papers**

Run:

```bash
python -m pytest tests/test_ocr_real_paper_regressions.py -k "6FGDBFQN or 3FDT9652 or RKSLQRIM" -v --tb=short
```

Expected:

```text
less sidecar overreach
fewer absurd caption/asset bindings on mixed-grammar pages
```

---

## 9. Stage P3A - Asset Family Hint

**Purpose:** Compute `asset_family_hint` without changing figure/table behavior yet.

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`, `paperforge/worker/ocr_tables.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Write failing hint-only tests**

Required hint shape:

```python
assert asset["asset_family_hint"] in {"figure_like", "table_like", "ambiguous"}
assert isinstance(asset["asset_family_confidence"], float)
assert isinstance(asset["asset_family_evidence"], list)
```

Persistence rule:

```text
P3A must define a persisted audit-visible surface for `asset_family_hint`.
At minimum, structured asset blocks and copied inventory asset records should expose the hint fields.
```

- [ ] **Step 2: Run hint-only tests**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "asset_family_hint" -v --tb=short
```

- [ ] **Step 3: Implement hint computation only**

Do **not** alter matching behavior in P3A.
Only emit the hint/evidence surface for later use.

Minimum persisted surface:

```text
structured block fields:
  asset_family_hint
  asset_family_confidence
  asset_family_evidence

figure inventory asset records copy these fields where applicable
table inventory asset/candidate records copy these fields where applicable
```

---

## 10. Stage P3B / P3C - Figure/Table Separator Veto

**Purpose:** Use strong `table_like` / `figure_like` signals to reduce obvious co-page ownership collisions.

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`, `paperforge/worker/ocr_tables.py`
- Test: `tests/test_ocr_figures.py`, `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write failing veto tests**

Add tests for:

```python
test_figure_matcher_skips_strong_table_like_region()
test_table_matcher_skips_strong_figure_like_region()
test_ambiguous_region_is_not_hard_forced()
```

- [ ] **Step 2: Run the co-page separator slice**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "table_like or figure_like or ownership_conflict" -v --tb=short
```

- [ ] **Step 3: Apply strong veto / down-rank only**

Required posture:

```text
strong table_like -> figure path veto/down-rank
strong figure_like -> table path veto/down-rank
ambiguous -> no hard assignment
```

Do not rewrite the whole figure/table pipelines.

- [ ] **Step 4: Re-run mixed co-page papers**

Run:

```bash
python -m pytest tests/test_ocr_real_paper_regressions.py -k "RKSLQRIM or 24YKLTHQ or 2UIPV93M" -v --tb=short
```

If all selected real-paper tests skip:

```text
record the skip count explicitly
add or run a synthetic equivalent
note fixture absence in PROJECT-MANAGEMENT.md
```

---

## 11. Final Verification

**Files:**
- Verify: all touched OCR figure/table files
- Test: all primary OCR figure suites plus live rebuild targets

- [ ] **Step 1: Run the core suite**

Run:

```bash
python -m pytest tests/test_ocr_figures.py tests/test_ocr_figure_reader.py tests/test_ocr_render.py -q
```

- [ ] **Step 2: Run real-paper regression sweep**

Run:

```bash
python -m pytest tests/test_ocr_real_paper_regressions.py -v --tb=short
```

- [ ] **Step 3: Run live rebuild validation**

Run:

```bash
python -m paperforge --vault "D:/L/OB/Literature-hub" ocr rebuild 2HEUD5P9
python -m paperforge --vault "D:/L/OB/Literature-hub" ocr rebuild SAN9AYVR
python -m paperforge --vault "D:/L/OB/Literature-hub" ocr rebuild DWQQK2YB
```

- [ ] **Step 4: Confirm final acceptance metrics**

Track explicitly:

```text
unmatched_fig_assets
unresolved_clusters
composite panel coverage quality
deduped_duplicate accounting
ownership_conflicts
rendered figure loss/duplication
```

---

## 12. `PROJECT-MANAGEMENT.md` Updates

After each stage, add one subsection using the established format:

```text
Problem
Root cause
Fix
Result
Tests
```

Required entries:

1. P0-A conflict persistence
2. P0-B duplicate legend canonicalization
3. P1A diagnostic-only parent detection
4. P1B parent arbitration
5. P2 grammar validator
6. P3A asset-family hint
7. P3B/P3C separator veto

---

## 13. Exit Criteria

This plan is complete only when all of the following are true:

1. `ownership_conflicts` is persisted in written figure inventory artifacts
2. bundle-source duplicate legends are accounted outcomes, not silent gaps
3. P1A diagnostic parent candidates are visible and behavior-preserving
4. P1B can improve composite coverage without manufacturing mega-groups
5. P2 validates mixed local grammar without becoming a second matcher
6. P3A/B/C reduces obvious figure/table co-page collisions without broad pipeline rewrite
7. core OCR figure suites and relevant real-paper regressions pass or only show separately documented pre-existing failures

---

## 14. Ticketization Guidance

This roadmap should be executed as separate tickets, not one uninterrupted implementation pass.

Recommended execution tickets:

1. `Stage 0 + P0-A + P0-B`
2. `P1A` only
3. `P1B` only
4. `P2` only
5. `P3A/B/C`

Each ticket should be independently reviewed and re-verified before the next one starts.
