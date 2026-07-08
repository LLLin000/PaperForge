# Group-First Figure Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor strict figure inventory so media assets are normalized into deterministic candidate groups before legend matching. The first implementation does not attempt journal-specific layout recovery; it only changes the matching unit from individual assets to candidate groups while preserving current single-asset behavior as the default-compatible path.

**Architecture:** Keep the existing formal-legend gate, reader-figure synthesis, and rendering layers intact. Refactor `build_figure_inventory()` so it builds deterministic candidate figure groups (`single`, `same_row_pair`, `same_row_triple`) before matching legends, then matches formal legends against those groups instead of individual assets. Restrict all fallback logic so it only runs after group-first matching fails, prevent sequence-promotion from conflicting with claimed groups, and make grouped outcomes explicit in inventory metadata without changing the external reader/render schema.

**Tech Stack:** Python 3.14, pytest, PaperForge OCR workers, fixture-backed regression tests, live-vault OCR audit contracts.

---

## File Map

- Modify: `paperforge/worker/ocr_figures.py`
  - Owns strict figure inventory construction.
  - Current problem seam: legend loop scores individual assets before any generic grouping is applied.
  - Planned changes: add candidate group builder, group scoring, group consumption, guarded fallback behavior.

- Modify: `paperforge/worker/ocr_health.py`
  - Owns health metrics derived from figure inventory.
  - Planned changes: report grouped-match counts and grouped-vs-single inventory composition for audit visibility.

- Modify: `tests/test_ocr_figures.py`
  - Owns unit and contract behavior for `build_figure_inventory()`.
  - Planned changes: add red-green coverage for group-first matching, no-regression safety for single-panel papers, and fallback constraints.

- Modify: `tests/test_ocr_figure_reader.py`
  - Owns strict-inventory to reader-payload normalization tests.
  - Planned changes: verify grouped strict matches materialize into a single reader figure with multi-asset visual group.

- Reference only: `tests/test_ocr_real_paper_regressions.py`
  - Owns fixture-backed production-path regression gates.
  - Planned use in this phase: verify no deterministic gold regressions after the inventory refactor.

- Modify: `tests/test_ocr_real_paper_audit_contracts.py`
  - Owns fixture quality contract, not runtime behavior.
  - Planned changes: only if needed to reflect new stronger grouped-ownership coverage requirements.

- Reference only: `tests/fixtures/ocr_real_papers/6FGDBFQN/expectations.json`
  - Gold AJR expectations.
  - Do not strengthen these expectations in this phase; use real-paper runs as observational shadow-checks only.

- Reference only: `paperforge/worker/ocr_figure_reader.py`
  - Consumes `matched_assets` and already supports multi-asset `visual_groups`.
  - Do not redesign unless grouped strict inventory exposes an incompatibility.

- Reference only: `paperforge/worker/ocr_render.py`
  - Renders reader figures and figure embeds.
  - Do not redesign unless grouped reader figures render incorrectly.

## Non-Negotiable Constraints

- Do not introduce journal-specific, AJR-specific, profile, or template logic in phase 1.
- Do not use image semantics, OCR panel text, or vision inference as required evidence.
- Do not override strong existing exact single-panel matches unless the new grouped match is strictly higher-confidence under deterministic rules.
- Do not let sequential fallback consume assets that belong to a valid grouped candidate.
- Do not let `_promote_sequence_matches()` create matches that conflict with already claimed grouped assets.
- Do not change reader/render public payload shape unless a test proves it is necessary.
- Do not support cross-page grouping in phase 1.
- Do not support arbitrary grids in phase 1; only `single`, `same_row_pair`, `same_row_triple`.

## Risks To Avoid

1. **Breaking ordinary single-image papers**
   - Current majority path works because a caption often truly maps to one image.
   - Guardrail: `single_asset` remains a valid candidate group and must compete in the same scoring system.

2. **Over-grouping unrelated nearby media**
   - Adjacent images, headshots, icon strips, or author bios can be geometrically close.
   - Guardrail: group builder must filter to figure-like media only and enforce same-page, same-row, size-similarity, and spacing thresholds.

3. **Double consumption across figures**
   - Existing code consumes asset indices early.
   - Guardrail: switch consumption unit from asset index to group asset-set ownership; once a grouped match wins, all member assets are reserved together.

4. **Sequential fallback undoing correct grouping**
   - Current fallback greedily assigns one caption to one remaining asset.
   - Guardrail: fallback only sees truly unclaimed assets after grouped matching has finalized ownership.

5. **Reader/render incompatibility**
   - Downstream code assumes `matched_assets` list exists and reader figures build `visual_groups` from it.
   - Guardrail: preserve `matched_assets` shape; add metadata fields instead of replacing existing ones.

6. **False confidence on truncated legends**
   - Weak captions should still HOLD/AMBIGUOUS rather than force-group.
   - Guardrail: keep `_is_insufficient_legend_evidence()` gate in front of grouped matching.

## Implementation Strategy

### Phase 1: Promote Generic Grouping Into Primary Inventory Path

Refactor the strict inventory path so candidate groups are built before legend matching. Reuse existing `_media_clusters()` concepts where possible, but tighten them into deterministic group candidates instead of late unresolved-only clusters.

Candidate group model should include:

```python
{
    "group_id": "group_001",
    "page": 4,
    "group_type": "same_row_pair",  # single_asset | same_row_pair | same_row_triple
    "asset_block_ids": [7, 8],
    "media_blocks": [...],
    "cluster_bbox": [x1, y1, x2, y2],
    "row_band": {"y_center": 546.0, "height_mean": 336.5},
    "group_confidence": 0.82,
    "group_evidence": ["same_page", "same_row_band", "size_similar", "tight_horizontal_gap"],
}
```

Legend matching should then evaluate candidate groups, not raw assets, with `single_asset` represented as a group of size 1.

### Phase 2: Keep Current Fallbacks, But De-power Them

`sequential_fallback` and `unresolved_clusters` stay, but only after group-first exact matching has run. They should never outrank deterministic grouped exact matches.

### Phase 3: Shadow-Check Real Papers Without Tightening Gold Expectations

After the generic path is stable, run observational real-paper compare checks on known multi-panel papers. Do not tighten AJR or other gold ownership expectations in this phase.

## Task 1: Add Red Test For Group-First Matching In AJR-Like Layout

**Files:**
- Modify: `tests/test_ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Write the failing test**

Add a focused unit test near the existing figure matching tests:

```python
def test_group_first_matching_prefers_same_row_pair_over_single_asset() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {
            "block_id": 1,
            "role": "figure_caption",
            "text": "Fig. 2 A and B, MRI and gross anatomic correlation.",
            "page": 3,
            "bbox": [80, 120, 420, 210],
            "marker_signature": {"type": "figure_number", "number": 2},
            "zone": "display_zone",
            "style_family": "legend_like",
        },
        {"block_id": 2, "role": "media_asset", "raw_label": "image", "page": 3, "bbox": [450, 120, 780, 520]},
        {"block_id": 3, "role": "media_asset", "raw_label": "image", "page": 3, "bbox": [805, 120, 1130, 520]},
    ]

    inventory = build_figure_inventory(blocks, page_width=1200)
    matched = inventory["matched_figures"]

    assert len(matched) == 1
    assert matched[0]["figure_number"] == 2
    assert [a["block_id"] for a in matched[0]["matched_assets"]] == [2, 3]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ocr_figures.py -k group_first_matching_prefers_same_row_pair_over_single_asset -v`

Expected: FAIL because current inventory will match only one asset or produce ambiguous/no-asset behavior.

- [ ] **Step 3: Commit the failing test only**

```bash
git add tests/test_ocr_figures.py
git commit -m "test: add failing pair-group figure inventory case"
```

## Task 2: Add Candidate Figure Group Builder In `ocr_figures.py`

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Add helper skeletons for group-first inventory**

Insert helpers near `_media_clusters()`:

```python
def _bbox_width(bbox: list[float]) -> float:
    return float(bbox[2] - bbox[0])


def _bbox_height(bbox: list[float]) -> float:
    return float(bbox[3] - bbox[1])


def _bbox_center_y(bbox: list[float]) -> float:
    return float(bbox[1] + bbox[3]) / 2.0


def _candidate_group_entry(group_id: str, page: int, media_blocks: list[dict], group_type: str, evidence: list[str]) -> dict:
    return {
        "group_id": group_id,
        "page": page,
        "group_type": group_type,
        "asset_block_ids": [b.get("block_id") for b in media_blocks if b.get("block_id") is not None],
        "media_blocks": media_blocks,
        "cluster_bbox": _cluster_bbox([b.get("bbox", [0, 0, 0, 0]) for b in media_blocks]),
        "group_evidence": evidence,
    }
```

- [ ] **Step 2: Add deterministic same-row grouping helper**

Add a helper that derives `single_asset`, `same_row_pair`, and `same_row_triple` candidates from same-page media:

```python
def _build_candidate_figure_groups_from_assets(assets: list[dict], page_width: float = 1200) -> list[dict]:
    media = [
        b for b in assets
        if not b.get("_non_body_media")
        and (b.get("role") == "figure_asset" or (b.get("role") == "media_asset" and b.get("raw_label", "") in {"image", "chart", "figure"}))
    ]
    media.sort(key=lambda b: (b.get("page", 0), (b.get("bbox") or [0, 0, 0, 0])[1], (b.get("bbox") or [0, 0, 0, 0])[0]))

    groups: list[dict] = []
    next_id = 1
    by_page: dict[int, list[dict]] = {}
    for block in media:
        by_page.setdefault(int(block.get("page", 0) or 0), []).append(block)

    for page, page_media in by_page.items():
        for block in page_media:
            groups.append(_candidate_group_entry(f"group_{next_id:03d}", page, [block], "single_asset", ["single_asset"]))
            next_id += 1

        for start in range(len(page_media)):
            for size in (2, 3):
                chunk = page_media[start:start + size]
                if len(chunk) != size:
                    continue
                bboxes = [b.get("bbox", [0, 0, 0, 0]) for b in chunk]
                heights = [_bbox_height(bb) for bb in bboxes]
                centers_y = [_bbox_center_y(bb) for bb in bboxes]
                if max(centers_y) - min(centers_y) > max(40.0, min(heights) * 0.35):
                    continue
                if max(heights) - min(heights) > max(40.0, min(heights) * 0.4):
                    continue
                gaps = []
                ordered = sorted(chunk, key=lambda b: (b.get("bbox") or [0, 0, 0, 0])[0])
                for left, right in zip(ordered, ordered[1:]):
                    lb = left.get("bbox", [0, 0, 0, 0])
                    rb = right.get("bbox", [0, 0, 0, 0])
                    gaps.append(max(0.0, rb[0] - lb[2]))
                if any(gap > page_width * 0.08 for gap in gaps):
                    continue
                group_type = "same_row_pair" if size == 2 else "same_row_triple"
                evidence = ["same_page", "same_row_band", "size_similar", "tight_horizontal_gap"]
                groups.append(_candidate_group_entry(f"group_{next_id:03d}", page, ordered, group_type, evidence))
                next_id += 1

    return groups
```

- [ ] **Step 3: Run the targeted test to verify it still fails for the right reason**

Run: `python -m pytest tests/test_ocr_figures.py -k group_first_matching_prefers_same_row_pair_over_single_asset -v`

Expected: still FAIL until the legend matching loop actually consumes candidate groups.

- [ ] **Step 4: Commit helper-only scaffolding**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py
git commit -m "refactor: add candidate figure group scaffolding"
```

## Task 3: Change Strict Matching From Asset-First To Group-First

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Replace raw asset candidate loop with candidate group loop**

In `build_figure_inventory()`, after collecting `assets`, build candidate groups:

```python
candidate_groups = _build_candidate_figure_groups_from_assets(assets, page_width=page_width)
used_asset_indices: set[int] = set()
used_asset_block_ids: set[int | str] = set()
```

Then replace the legend-scoring loop so it evaluates groups on the same page whose assets are all unconsumed.

- [ ] **Step 2: Keep group scoring generic and single-asset compatible**

Do not make `A and B` / `A–C` parsing a required condition in this phase. Instead, keep `single_asset` groups behavior as close as possible to the old `score_figure_match()` path, and let multi-asset groups compete only when their geometry is highly coherent.

Add a helper:

```python
def _score_legend_to_group(legend: dict, group: dict, *, caption_score: dict, page_width: float = 1200) -> dict:
    if group.get("group_type") == "single_asset":
        asset = group["media_blocks"][0]
        return score_figure_match(
            legend,
            asset,
            caption_score=caption_score,
            anchor_supported=_has_anchor_supported_legend_context(legend),
            caption_text_supported=_has_strong_explicit_caption_text(legend),
            family_supported=False,
            zone_supported=False,
        )

    # Multi-asset groups: score the group bbox and add a small coherence bonus.
    # Keep this generic and geometry-only in phase 1.
```

- [ ] **Step 3: Materialize grouped strict matches without changing external shape**

When a candidate group wins, emit:

```python
entry = {
    "figure_id": fig_id,
    "legend_block_id": legend.get("block_id", ""),
    "page": legend_page,
    "text": legend_text,
    "figure_number": fig_num,
    "matched_assets": [
        {"block_id": a.get("block_id", ""), "bbox": a.get("bbox", [0, 0, 0, 0])}
        for a in winning_group["media_blocks"]
    ],
    "cluster_bbox": winning_group["cluster_bbox"],
    "group_type": winning_group["group_type"],
    "group_evidence": winning_group["group_evidence"],
    "confidence": match_score["score"],
    "match_score": match_score,
    "flags": ["group_first_match"] if len(winning_group["media_blocks"]) > 1 else [],
    "caption_score": caption_score,
}
```

- [ ] **Step 4: Reserve all assets in a winning group together**

Update the consumption logic so all member `block_id`s are added to `used_asset_block_ids`. Filter all future candidate groups against this set.

- [ ] **Step 5: Run focused tests to verify the new grouped behavior**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "group_first_matching_prefers_same_row_pair_over_single_asset or sequence_match_requires_at_least_one_asset_block_id" -v
```

Expected: PASS for the new group-first test and PASS for the existing safety tests.

- [ ] **Step 6: Commit group-first strict matching**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py
git commit -m "feat: match figure legends against candidate media groups"
```

## Task 4: Constrain Fallback Behavior So It Cannot Undo Grouped Matches

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Write a failing regression test for fallback stealing grouped assets**

Add:

```python
def test_sequential_fallback_does_not_split_grouped_assets() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": 1, "role": "figure_caption", "text": "Fig. 2 A and B, paired figure.", "page": 3, "bbox": [80, 120, 420, 210], "marker_signature": {"type": "figure_number"}, "zone": "display_zone", "style_family": "legend_like"},
        {"block_id": 2, "role": "media_asset", "raw_label": "image", "page": 3, "bbox": [450, 120, 780, 520]},
        {"block_id": 3, "role": "media_asset", "raw_label": "image", "page": 3, "bbox": [805, 120, 1130, 520]},
        {"block_id": 4, "role": "figure_caption", "text": "Fig. 3 Single figure.", "page": 4, "bbox": [80, 120, 420, 210], "marker_signature": {"type": "figure_number"}, "zone": "display_zone", "style_family": "legend_like"},
    ]

    inventory = build_figure_inventory(blocks, page_width=1200)
    matched = {item["figure_number"]: item for item in inventory["matched_figures"]}
    assert [a["block_id"] for a in matched[2]["matched_assets"]] == [2, 3]
    assert 3 not in matched
```

- [ ] **Step 2: Run test to verify it fails if fallback still steals assets**

Run: `python -m pytest tests/test_ocr_figures.py -k sequential_fallback_does_not_split_grouped_assets -v`

Expected: FAIL before the fallback guard is added.

- [ ] **Step 3: Guard sequential fallback against grouped ownership**

Adjust fallback setup so `sorted_asts` excludes every asset whose `block_id` is already present in any grouped or single strict match.

- [ ] **Step 4: Restrict unresolved cluster creation to truly unclaimed assets**

Ensure `_media_clusters(unmatched_assets, ...)` sees only assets not already claimed by any grouped match.

- [ ] **Step 5: Guard `_promote_sequence_matches()` against grouped ownership conflicts**

Also ensure `_promote_sequence_matches()` does not create promoted matches that conflict with already claimed group assets, and does not promote empty-asset entries unless the existing contract explicitly allows sequence-style outcomes without assets.

- [ ] **Step 6: Run focused fallback tests**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "sequential_fallback_does_not_split_grouped_assets or strict_layer_promotes_contiguous_legends_with_ordered_assets" -v
```

Expected: PASS.

- [ ] **Step 7: Commit fallback hardening**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py
git commit -m "fix: prevent fallback from splitting grouped figure assets"
```

## Task 5: Verify Reader Layer Accepts Grouped Strict Matches

**Files:**
- Modify: `tests/test_ocr_figure_reader.py`
- Test: `tests/test_ocr_figure_reader.py`

- [ ] **Step 1: Write a failing reader test for grouped strict inventory**

Add:

```python
def test_reader_materializes_grouped_strict_match_as_single_visual_group() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "figure_legends": [],
        "matched_figures": [
            {
                "figure_number": 2,
                "legend_block_id": 10,
                "page": 3,
                "text": "Fig. 2 A and B, paired figure.",
                "matched_assets": [
                    {"block_id": 20, "bbox": [100, 100, 300, 300]},
                    {"block_id": 21, "bbox": [320, 100, 520, 300]},
                ],
                "match_score": {"score": 0.82, "decision": "matched", "evidence": ["same_row_pair"]},
                "caption_score": {"score": 0.9},
            }
        ],
        "held_figures": [],
        "ambiguous_figures": [],
        "unmatched_legends": [],
        "unresolved_clusters": [],
    }

    payload = synthesize_reader_figures(strict_inventory, structured_blocks=[])
    rf = payload["reader_figures"][0]
    assert rf["figure_number"] == 2
    assert rf["visual_groups"][0]["asset_block_ids"] == [20, 21]
```

- [ ] **Step 2: Run test to verify current reader behavior**

Run: `python -m pytest tests/test_ocr_figure_reader.py -k grouped_strict_match_as_single_visual_group -v`

Expected: PASS or targeted FAIL only if grouped metadata reveals a normalization incompatibility.

- [ ] **Step 3: If needed, apply the minimal normalization fix**

Only if the test fails, adjust `_asset_ids_from_item()` or `_materialize_reader_figure()` so multi-asset strict matches remain one reader figure with one visual group.

- [ ] **Step 4: Run reader tests**

Run: `python -m pytest tests/test_ocr_figure_reader.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit reader compatibility work**

```bash
git add tests/test_ocr_figure_reader.py paperforge/worker/ocr_figure_reader.py
git commit -m "test: verify reader figures preserve grouped strict matches"
```

## Task 6: Add Health Visibility For Grouped Matches

**Files:**
- Modify: `paperforge/worker/ocr_health.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Add grouped-match counters in health report**

Add derived metrics:

```python
grouped_figure_match_count = sum(
    1 for mf in figure_inventory.get("matched_figures", []) if len(mf.get("matched_assets", [])) > 1
)
single_asset_figure_match_count = sum(
    1 for mf in figure_inventory.get("matched_figures", []) if len(mf.get("matched_assets", [])) == 1
)
```

Add to report:

```python
"grouped_figure_match_count": grouped_figure_match_count,
"single_asset_figure_match_count": single_asset_figure_match_count,
```

- [ ] **Step 2: Add a small health test**

Add a unit test that feeds a fake inventory with one grouped match and one single match into `build_ocr_health()` and verifies both counters.

- [ ] **Step 3: Run targeted health test**

Run: `python -m pytest tests/test_ocr_figures.py -k grouped_figure_match_count -v`

Expected: PASS.

- [ ] **Step 4: Commit health visibility**

```bash
git add paperforge/worker/ocr_health.py tests/test_ocr_figures.py
git commit -m "feat: report grouped figure match health metrics"
```

## Task 7: Shadow-Check Real Papers Without Changing Gold Expectations

**Files:**
- Modify: none
- Test: `tests/test_ocr_real_paper_regressions.py`
- Test: `tests/test_ocr_real_paper_contract.py`

- [ ] **Step 1: Run deterministic regression suite without changing gold expectations**

Run:

```bash
python -m pytest tests/test_ocr_real_paper_regressions.py -v --tb=short
```

Expected: PASS with no deterministic gold regressions.

- [ ] **Step 2: Run observational live-paper compare on one known multi-panel paper and one clean control**

Run:

```bash
$env:PAPERFORGE_REAL_OCR_VAULT='D:\L\OB\Literature-hub'; $env:PAPERFORGE_REAL_OCR_KEYS='6FGDBFQN,2GN9LMCW'; python -m pytest tests/test_ocr_real_paper_contract.py -v --tb=short
```

Expected: observational only. Do not tighten AJR ownership expectations in this phase.

- [ ] **Step 3: Record grouped-match observations, but do not edit expectations**

If grouped figure counts or reader outputs improve on live artifacts, note that in the implementation summary only. Do not modify `6FGDBFQN` gold ownership gates.

## Task 8: Full Verification Across Unit, Fixture, and Gold Gates

**Files:**
- Modify: none unless failures require targeted fixes
- Test: `tests/test_ocr_figures.py`
- Test: `tests/test_ocr_figure_reader.py`
- Test: `tests/test_ocr_real_paper_audit_contracts.py`
- Test: `tests/test_ocr_trace_vs_expectations.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Run focused unit tests for figure inventory**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -v --tb=short
```

Expected: PASS.

- [ ] **Step 2: Run reader tests**

Run:

```bash
python -m pytest tests/test_ocr_figure_reader.py -v --tb=short
```

Expected: PASS.

- [ ] **Step 3: Run fixture-backed OCR gold verification**

Run:

```bash
python -m pytest tests/test_ocr_real_paper_audit_contracts.py tests/test_ocr_trace_vs_expectations.py tests/test_ocr_real_paper_regressions.py -v --tb=short
```

Expected: all deterministic gold tests PASS; existing env-dependent live-vault tests may remain skipped.

- [ ] **Step 4: Spot-check live compare for AJR and one control paper**

Run:

```bash
$env:PAPERFORGE_REAL_OCR_VAULT='D:\L\OB\Literature-hub'; $env:PAPERFORGE_REAL_OCR_KEYS='6FGDBFQN,2GN9LMCW'; python -m pytest tests/test_ocr_real_paper_contract.py -v --tb=short
```

Expected: PASS or actionable flagged output only if the live vault has stale derived artifacts that need rebuild.

- [ ] **Step 5: Commit final verification-safe fixes**

```bash
git add .
git commit -m "feat: promote group-first figure inventory matching"
```

## Spec Coverage Check

- Fix the structural problem where grouped media exists in code but not as the default match unit: covered by Tasks 2-4.
- Preserve generic behavior for most papers and avoid AJR-only hacks: covered by candidate-group design and constraints in Tasks 2-4.
- Keep reader/render contracts stable: covered by Task 5.
- Improve observability and auditability: covered by Task 6.
- Prove the result on the deterministic gold suite and shadow-check live papers without widening scope: covered by Tasks 7-8.

## Placeholder Scan

- No `TODO`, `TBD`, or “appropriate handling” placeholders remain.
- Every code-changing task includes target file paths, test commands, and concrete code sketches.

## Type/Name Consistency Check

- Group builder terminology is consistent: `candidate group`, `group_type`, `asset_block_ids`, `matched_assets`.
- Downstream compatibility is preserved by keeping `matched_assets` as the externally consumed shape.

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-15-group-first-figure-inventory-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
