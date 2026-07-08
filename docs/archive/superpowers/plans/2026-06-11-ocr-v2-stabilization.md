# OCR V2 Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move `ocr-v2` from a partially landed transition branch to a merge-ready OCR v2 branch by restoring hard test feedback loops, closing the reader contract, reasserting anchor-first pipeline authority, and converging the named real-paper failures on a verified path.

**Architecture:** Execute stabilization in three rings. Ring 1 restores contract-level correctness at the fastest seams (`ocr_figure_reader.py`, `ocr_render.py`, `ocr_health.py`, and audit tests). Ring 2 finishes the branch's anchor-first pipeline order (`signatures -> anchors -> zones -> families -> final role -> figure/table validation -> render`) so the reader layer sits on top of reliable structure instead of compensating for unstable upstream semantics. Ring 3 closes the remaining real-paper failures on the named problem keys and then enforces merge gates, so the branch stops drifting between partial fixes and skipped audits.

**Tech Stack:** Python 3, pytest, existing OCR worker modules under `paperforge/worker/`, existing real-paper audit tests, real OCR vault via `PAPERFORGE_REAL_OCR_VAULT` and `PAPERFORGE_REAL_OCR_KEYS`

---

## Scope Notes

- This plan supersedes the execution order of:
  - `docs/superpowers/plans/2026-06-10-ocr-figure-reader-contract-implementation.md`
  - `docs/superpowers/plans/2026-06-10-ocr-real-paper-recovery-plan.md`
  - `docs/superpowers/plans/2026-06-10-ocr-real-paper-full-closure-plan.md`
- Those documents remain useful as background, but this file is the single execution path.
- Do not broaden scope into new OCR features, plugin work, or release chores until the stabilization gates in this plan are green.
- Do not treat skipped real-paper audits as success. A green branch requires both fast local seams and real-paper seams.

## Stabilization Gates

### Gate A: Fast local seam

- `python -m pytest tests/test_ocr_figure_reader.py tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py tests/test_ocr_health.py -q`
- Purpose: prove reader synthesis, render dedupe, and health metrics are locally correct before touching broader pipeline order.

### Gate B: Branch integration seam

- `python -m pytest tests/test_ocr_roles.py tests/test_ocr_document.py tests/test_ocr_families.py tests/test_ocr_figures.py tests/test_ocr_objects.py tests/test_ocr_tables.py tests/test_ocr_integration_fixtures.py -q`
- Purpose: prove anchor-first authority is coherent before depending on it in real papers.

### Gate C: Real-paper seam

- `python -m pytest tests/test_ocr_real_paper_reader_audit.py tests/test_ocr_real_paper_regressions.py -v`
- Requires:
  - `PAPERFORGE_REAL_OCR_VAULT`
  - `PAPERFORGE_REAL_OCR_KEYS`
- Purpose: prove the branch is not only internally consistent, but also stable on named real OCR artifacts.

### Gate D: Merge seam

- All Gates A-C green.
- No OCR debug artifacts leak into `fulltext.md`.
- No required OCR tests are skipped except tests explicitly marked environment-dependent.
- Branch worktree contains no stray debug scripts or scratch files that are not intentionally tracked.

---

## File Map

### Primary implementation files

- `paperforge/worker/ocr_figure_reader.py`
  - Reader normalization, admission gates, reader synthesis, reader coverage accounting.
- `paperforge/worker/ocr_render.py`
  - Reader-primary figure rendering, consumed-caption dedupe, debug leakage prevention.
- `paperforge/worker/ocr_figures.py`
  - Strict figure inventory, unresolved cluster geometry, sequence-match promotion safety.
- `paperforge/worker/ocr_health.py`
  - Reader coverage metrics and degraded reasons.
- `paperforge/worker/ocr.py`
  - Main OCR postprocess entrypoint for reader artifact persistence.
- `paperforge/worker/ocr_rebuild.py`
  - Rebuild path for reader artifact persistence and render/health regeneration.
- `paperforge/worker/ocr_blocks.py`
  - Main structured-block orchestration and pipeline order.
- `paperforge/worker/ocr_roles.py`
  - `seed_role` vs final `role` authority split.
- `paperforge/worker/ocr_metadata.py`
  - Early source-backed frontmatter anchors.
- `paperforge/worker/ocr_document.py`
  - Zones, boundary authority, body/reference split, tail exclusion.
- `paperforge/worker/ocr_families.py`
  - Body/reference/display/support family partition authority.
- `paperforge/worker/ocr_signatures.py`
  - Low-level signature typing, especially old-style numeric references.
- `paperforge/worker/ocr_objects.py`
  - Figure/table object completeness behavior.
- `paperforge/worker/ocr_tables.py`
  - Table validation aligned to the final authority order.

### Primary test files

- `tests/test_ocr_figure_reader.py`
- `tests/test_ocr_rendering.py`
- `tests/test_ocr_render_stabilization.py`
- `tests/test_ocr_health.py`
- `tests/test_ocr_roles.py`
- `tests/test_ocr_document.py`
- `tests/test_ocr_families.py`
- `tests/test_ocr_figures.py`
- `tests/test_ocr_objects.py`
- `tests/test_ocr_tables.py`
- `tests/test_ocr_integration_fixtures.py`
- `tests/test_ocr_real_paper_reader_audit.py`
- `tests/test_ocr_real_paper_regressions.py`

---

## Task 1: Restore the reader normalization contract

**Files:**
- Modify: `paperforge/worker/ocr_figure_reader.py`
- Test: `tests/test_ocr_figure_reader.py`

- [ ] **Step 1: Run the current red seam and record the exact failures**

Run:
`python -m pytest tests/test_ocr_figure_reader.py -q`

Expected:
- FAIL on the currently red reader tests, especially coverage and reader-figure emission.

- [ ] **Step 2: Tighten the failing tests so they lock the actual missing normalization fields**

Add or preserve assertions like:

```python
def test_normalize_strict_inventory_preserves_reader_gate_inputs() -> None:
    from paperforge.worker.ocr_figure_reader import _normalize_strict_figure_inventory

    strict_inventory = {
        "ambiguous_figures": [{
            "figure_number": 3,
            "legend_block_id": 9,
            "caption_text": "FIGURE 3 | Histological evaluation...",
            "candidate_asset_ids": [10, 11],
            "marker_type": "figure_number",
            "strict_reject": False,
        }],
        "unresolved_clusters": [{
            "page": 7,
            "media_block_ids": [30, 31],
            "cluster_area_ratio": 0.031,
            "width_ratio": 0.42,
            "height_ratio": 0.15,
            "media_block_count": 2,
            "linked_legend_block_id": None,
        }],
    }

    normalized = _normalize_strict_figure_inventory(strict_inventory, structured_blocks=[])

    item = normalized["ambiguous_figures"][0]
    assert item["marker_type"] == "figure_number"
    assert item["candidate_asset_ids"] == [10, 11]
    assert item["strict_reject"] is False

    cluster = normalized["unresolved_clusters"][0]
    assert cluster["cluster_area_ratio"] == 0.031
    assert cluster["linked_legend_block_id"] is None
```

- [ ] **Step 3: Implement the minimal normalization repair**

In `paperforge/worker/ocr_figure_reader.py`, extend `_normalize_bucket()` so it preserves gate-critical fields from `source_item`, `legend_data`, and fallback blocks:

```python
normalized.append(
    {
        "figure_number": source_item.get("figure_number") or source_marker.get("number"),
        "legend_block_id": legend_block_id,
        "caption_text": source_text,
        "asset_block_ids": _asset_ids_from_item(source_item),
        "candidate_asset_ids": _candidate_asset_ids_from_item(source_item) if bucket_name in candidate_buckets else [],
        "marker_type": source_item.get("marker_type") or source_marker.get("type"),
        "inline_mention": bool(source_item.get("inline_mention", False)),
        "panel_label": bool(source_item.get("panel_label", False)),
        "body_prose_likelihood": float(source_item.get("body_prose_likelihood", 0.0)),
        "strict_reject": bool(source_item.get("strict_reject", False)),
        "linked_legend_block_id": source_item.get("linked_legend_block_id"),
        "cluster_area_ratio": float(source_item.get("cluster_area_ratio", 0.0)),
        "width_ratio": float(source_item.get("width_ratio", 0.0)),
        "height_ratio": float(source_item.get("height_ratio", 0.0)),
        "media_block_count": int(source_item.get("media_block_count", len(_asset_ids_from_item(source_item)))),
        "page": source_item.get("page", block.get("page")),
        "zone": legend_data.get("zone") or source_item.get("zone") or block.get("zone"),
        "style_family": legend_data.get("style_family") or source_item.get("style_family") or block.get("style_family"),
        "strict_status": source_item.get("strict_status", bucket_name.removesuffix("s")),
        "source_item": source_item,
    }
)
```

- [ ] **Step 4: Re-run the fast reader seam**

Run:
`python -m pytest tests/test_ocr_figure_reader.py -q`

Expected:
- the current six reader failures collapse or reduce to the next real contract issue.

- [ ] **Step 5: Expand coverage assertions to lock the restored contract**

Keep concrete checks like:

```python
assert result["reader_coverage"]["total"] == 2
assert result["reader_coverage"]["accounted"] == len(result["reader_figures"])
assert set(result["consumed_caption_block_ids"]) == {5, 21}
```

- [ ] **Step 6: Suggested checkpoint commit**

```bash
git add paperforge/worker/ocr_figure_reader.py tests/test_ocr_figure_reader.py
git commit -m "fix: restore OCR reader normalization contract"
```

---

## Task 2: Make rendering reader-primary and dedupe captions globally

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_rendering.py`
- Test: `tests/test_ocr_render_stabilization.py`

- [ ] **Step 1: Write the failing render tests at the real seam**

Add tests like:

```python
def test_render_fulltext_skips_consumed_caption_block_even_when_role_is_body_paragraph() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {"block_id": 21, "role": "body_paragraph", "text": "FIGURE 2 | Treadmill exercise protocols...", "page": 1, "bbox": [0, 0, 100, 20]},
        {"block_id": 22, "role": "body_paragraph", "text": "The treadmill protocol was well tolerated.", "page": 1, "bbox": [0, 30, 500, 50]},
    ]
    reader_payload = {
        "reader_figures": [{
            "reader_figure_id": "figure_002_reader",
            "reader_status": "LEGEND_ONLY",
            "strict_status": "unmatched",
            "figure_number": 2,
            "caption_text": "FIGURE 2 | Treadmill exercise protocols...",
            "caption_block_id": 21,
            "visual_groups": [],
            "consumed_caption_block_ids": [21],
            "consumed_asset_block_ids": [],
            "debug_refs": {},
        }],
        "consumed_caption_block_ids": [21],
        "consumed_asset_block_ids": [],
    }

    markdown = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={"matched_figures": []},
        table_inventory={"tables": []},
        page_count=1,
        reader_payload=reader_payload,
    )

    assert markdown.count("FIGURE 2 | Treadmill exercise protocols...") == 1
```

```python
def test_render_fulltext_prefers_reader_figures_over_legacy_matched_figures() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [{"block_id": 22, "role": "body_paragraph", "text": "Results body.", "page": 1, "bbox": [0, 30, 500, 50]}]
    markdown = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={"matched_figures": [{"figure_id": "figure_002", "page": 1, "text": "Figure 2 legacy caption"}]},
        table_inventory={"tables": []},
        page_count=1,
        reader_payload={
            "reader_figures": [{
                "reader_figure_id": "figure_002_reader",
                "reader_status": "LEGEND_ONLY",
                "strict_status": "unmatched",
                "strict_source": "unmatched_legends",
                "figure_number": 2,
                "caption_text": "FIGURE 2 | Reader caption",
                "caption_block_id": 21,
                "visual_groups": [],
                "consumed_caption_block_ids": [21],
                "consumed_asset_block_ids": [],
                "debug_refs": {},
            }],
            "consumed_caption_block_ids": [21],
            "consumed_asset_block_ids": [],
        },
    )

    assert "![[render/figures/figure_002.md]]" not in markdown
    assert "> **Figure 2**" in markdown
```

- [ ] **Step 2: Run the focused render seam to verify failure**

Run:
`python -m pytest tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py -k "consumed_caption or prefers_reader_figures" -q`

Expected:
- FAIL because consumed-caption skipping is role-local and legacy matched-figure emission is still active beside reader rendering.

- [ ] **Step 3: Add a single page-object emission helper and move the consumed-caption check earlier**

Refactor `render_fulltext_markdown()` around two concrete rules:

```python
block_id = block.get("block_id")
if block_id is not None and block_id in consumed_caption_block_ids:
    continue
```

and

```text
def _emit_page_objects(page: int) -> None:
    if reader_figures_by_page.get(page):
        for rf in reader_figures_by_page.get(page, []):
            rfid = rf.get("reader_figure_id")
            if rfid and rfid not in rendered_reader_figure_ids:
                rendered_reader_figure_ids.add(rfid)
                lines.extend(_render_reader_figure_card(rf))
                lines.append("")
    else:
        for fig in figures_by_page.get(page, []):
            lines.append(f"![[render/figures/{fig['figure_id']}.md]]")
            lines.append("")
        for cluster_id in unresolved_clusters_by_page.get(page, []):
            lines.append(f"![[render/figures/{cluster_id}.md]]")
            lines.append("")
```

Do not leave four duplicated page-emission loops with divergent behavior.

- [ ] **Step 4: Re-run the render seam**

Run:
`python -m pytest tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py -q`

Expected:
- PASS on the new dedupe tests.
- No regression in existing render stabilization checks.

- [ ] **Step 5: Suggested checkpoint commit**

```bash
git add paperforge/worker/ocr_render.py tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py
git commit -m "fix: make OCR figure rendering reader-primary"
```

---

## Task 3: Tighten strict figure safety and health reporting

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `paperforge/worker/ocr_figure_reader.py`
- Modify: `paperforge/worker/ocr_health.py`
- Test: `tests/test_ocr_figures.py`
- Test: `tests/test_ocr_figure_reader.py`
- Test: `tests/test_ocr_health.py`

- [ ] **Step 1: Write failing tests for sequence-match promotion and salient visual groups**

```python
def test_sequence_match_requires_non_empty_assets() -> None:
    from paperforge.worker.ocr_figures import _promote_sequence_matches

    inventory = _promote_sequence_matches(
        {
            "matched_figures": [{"figure_number": 2, "matched_assets": [{"block_id": 10}]}],
            "ambiguous_figures": [{"figure_number": 3, "legend_block_id": 31, "text": "Figure 3", "candidate_asset_ids": []}],
        },
        blocks=[],
    )
    assert all(fig.get("matched_assets") for fig in inventory["matched_figures"] if fig.get("strict_status") == "sequence_match")


def test_unresolved_cluster_enters_reader_only_when_salience_fields_are_present() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    result = synthesize_reader_figures(
        {
            "matched_figures": [],
            "held_figures": [],
            "ambiguous_figures": [],
            "unmatched_legends": [],
            "unresolved_clusters": [{
                "page": 7,
                "media_block_ids": [30, 31],
                "cluster_area_ratio": 0.031,
                "width_ratio": 0.42,
                "height_ratio": 0.15,
                "media_block_count": 2,
                "linked_legend_block_id": None,
                "zone": "display_zone",
            }],
        },
        structured_blocks=[],
    )
    assert result["reader_figures"][0]["reader_status"] == "ASSET_GROUP_ONLY"
```

- [ ] **Step 2: Run the focused strict seam**

Run:
`python -m pytest tests/test_ocr_figures.py tests/test_ocr_figure_reader.py tests/test_ocr_health.py -k "sequence_match or ASSET_GROUP_ONLY or reader_coverage" -q`

Expected:
- FAIL because sequence promotion is adjacency-only and unresolved-cluster gates depend on fields that are currently missing or weak.

- [ ] **Step 3: Tighten `_promote_sequence_matches()` to require evidence, not only adjacency**

Implement a conservative promotion rule such as:

```python
candidate_assets = af.get("candidates") or af.get("candidate_asset_ids") or []
if not candidate_assets:
    remaining_ambiguous.append(af)
    continue
if not ((fn - 1 in matched_fig_nums) or (fn + 1 in matched_fig_nums)):
    remaining_ambiguous.append(af)
    continue
```

Promoted entries must not be emitted as `SEQUENCE_MATCH` with `matched_assets=[]` and `confidence=0.0` unless an explicit asset representative is carried through.

- [ ] **Step 4: Carry unresolved-cluster salience geometry through strict inventory and reader normalization**

In `ocr_figures.py`, ensure unresolved clusters preserve geometry fields needed by the reader gate:

```python
unresolved_clusters.append(
    {
        "cluster_id": cluster_id,
        "media_block_ids": cluster_ids,
        "cluster_bbox": cluster_bbox,
        "page": cluster_page,
        "cluster_area_ratio": cluster_area_ratio,
        "width_ratio": width_ratio,
        "height_ratio": height_ratio,
        "media_block_count": len(cluster_ids),
        "linked_legend_block_id": linked_legend_block_id,
    }
)
```

- [ ] **Step 5: Keep health aligned with the stricter reader contract**

Lock `ocr_health.py` to concrete expectations:

```python
assert report["figure_reader_coverage_total"] >= report["figure_reader_coverage_accounted"]
assert "reader_figure_coverage_gap" in report["degraded_reasons"]
```

- [ ] **Step 6: Re-run Gate A**

Run:
`python -m pytest tests/test_ocr_figure_reader.py tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py tests/test_ocr_health.py tests/test_ocr_figures.py -q`

Expected:
- PASS.

- [ ] **Step 7: Suggested checkpoint commit**

```bash
git add paperforge/worker/ocr_figures.py paperforge/worker/ocr_figure_reader.py paperforge/worker/ocr_health.py tests/test_ocr_figures.py tests/test_ocr_figure_reader.py tests/test_ocr_health.py
git commit -m "fix: harden OCR figure matching safety"
```

---

## Task 4: Repair the real-paper reader audit harness

**Files:**
- Modify: `tests/test_ocr_real_paper_reader_audit.py`
- Test: `tests/test_ocr_real_paper_reader_audit.py`

- [ ] **Step 1: Replace the overbroad formal-legend helper with a contract-aware source**

The current helper is too broad because it treats `table_caption` and `table_caption_like` as formal figure legends. Replace it with figure-aware input derived from either `figure_inventory.json` or `reader_payload["normalized_inputs"]`.

Concrete direction:

```python
def _eligible_reader_legend_block_ids(reader_payload: dict) -> set[int | str]:
    ids: set[int | str] = set()
    normalized = reader_payload.get("normalized_inputs", {})
    for source_name in ("matched_figures", "held_figures", "ambiguous_figures", "unmatched_legends"):
        for item in normalized.get(source_name, []):
            if item.get("marker_type") == "figure_number" and not item.get("inline_mention") and not item.get("panel_label"):
                bid = item.get("legend_block_id")
                if bid is not None:
                    ids.add(bid)
    return ids
```

- [ ] **Step 2: Run the audit file without the real env to verify skip behavior is explicit**

Run:
`python -m pytest tests/test_ocr_real_paper_reader_audit.py -q`

Expected:
- SKIP only because `PAPERFORGE_REAL_OCR_VAULT` / `PAPERFORGE_REAL_OCR_KEYS` are not set.
- No false impression that the contract passed.

- [ ] **Step 3: When real-paper env is available, run the audit directly**

Run:
`python -m pytest tests/test_ocr_real_paper_reader_audit.py -v`

Expected:
- FAIL only on real reader gaps, not on table-caption false positives.

- [ ] **Step 4: Suggested checkpoint commit**

```bash
git add tests/test_ocr_real_paper_reader_audit.py
git commit -m "test: align OCR real-paper reader audit with reader contract"
```

---

## Task 5: Re-establish the anchor-first pipeline order

**Files:**
- Modify: `paperforge/worker/ocr_blocks.py`
- Modify: `paperforge/worker/ocr_roles.py`
- Modify: `paperforge/worker/ocr_metadata.py`
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_roles.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_integration_fixtures.py`

- [ ] **Step 1: Write failing tests that freeze the intended authority order**

```python
def test_build_structured_blocks_preserves_seed_role_and_delays_final_role() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [{
        "paper_id": "P1",
        "page": 1,
        "block_id": 1,
        "raw_label": "text",
        "raw_order": 1,
        "bbox": [80, 220, 520, 260],
        "text": "Results body text.",
        "page_width": 1200,
        "page_height": 1700,
    }]

    rows, _ = build_structured_blocks(raw_blocks, source_metadata={})
    assert "seed_role" in rows[0]
    assert rows[0]["role"] != "text"


def test_frontmatter_anchors_exist_before_zone_inference() -> None:
    from paperforge.worker.ocr_metadata import build_source_backed_frontmatter_anchors

    page_blocks = [
        {"block_id": 1, "page": 1, "text": "Anchor First OCR Pipeline", "role": "title"},
        {"block_id": 2, "page": 1, "text": "Ami Yoo, William Marks", "role": "authors"},
    ]
    anchors = build_source_backed_frontmatter_anchors(
        {"title": "Anchor First OCR Pipeline", "authors": ["Ami Yoo", "William Marks"], "doi": "10.1000/example"},
        page_blocks,
    )
    assert anchors["title_source_anchor"]["status"] == "ACCEPT"


def test_zone_and_family_partition_complete_before_final_role_resolution() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [{
        "paper_id": "P1",
        "page": 2,
        "block_id": 5,
        "raw_label": "text",
        "raw_order": 1,
        "bbox": [80, 1200, 520, 1260],
        "text": "1. Old-style numbered reference entry.",
        "page_width": 1200,
        "page_height": 1700,
    }]

    rows, doc_structure = build_structured_blocks(raw_blocks, source_metadata={})
    assert rows
    assert doc_structure is not None
```

- [ ] **Step 2: Run the branch integration seam for order-specific failures**

Run:
`python -m pytest tests/test_ocr_roles.py tests/test_ocr_document.py tests/test_ocr_integration_fixtures.py -k "seed_role or frontmatter_anchors or before_final_role" -q`

Expected:
- FAIL because the branch still partially commits semantic role too early.

- [ ] **Step 3: Split eager role assignment into `seed_role` and final `role`**

In `ocr_roles.py` / `ocr_blocks.py`, apply the explicit boundary:

```python
row["seed_role"] = role.role
row["seed_confidence"] = role.confidence
row["seed_evidence"] = role.evidence
row["role"] = "unassigned"
```

Then in orchestration, drive the final order as:

```text
raw observations
-> build_structural_signatures
-> source-backed frontmatter anchors
-> discover_body_family_anchor
-> discover_reference_family_anchor
-> infer_zones
-> partition_zone_families
-> resolve_final_role
```

Do not reintroduce a compensating second refresh pass that makes zones or families post hoc.

- [ ] **Step 4: Re-run the order seam**

Run:
`python -m pytest tests/test_ocr_roles.py tests/test_ocr_document.py tests/test_ocr_integration_fixtures.py -q`

Expected:
- PASS on the order-specific tests.

- [ ] **Step 5: Suggested checkpoint commit**

```bash
git add paperforge/worker/ocr_blocks.py paperforge/worker/ocr_roles.py paperforge/worker/ocr_metadata.py paperforge/worker/ocr_document.py tests/test_ocr_roles.py tests/test_ocr_document.py tests/test_ocr_integration_fixtures.py
git commit -m "refactor: restore OCR anchor-first authority order"
```

---

## Task 6: Close upstream semantic gaps that still poison real papers

**Files:**
- Modify: `paperforge/worker/ocr_signatures.py`
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_families.py`
- Modify: `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_signatures.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_families.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Lock the named upstream failure classes in tests**

Add or tighten cases for:

```python
def test_caqnw9q2_old_style_references_gain_reference_like_family(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    lines = _fulltext_lines(_ocr_root, "CAQNW9Q2")
    assert not any(line.strip().startswith("1.") and "body" in line.lower() for line in lines)


def test_m36wa39n_same_page_tail_nonref_and_references_split_correctly(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    blocks = _read_jsonl(_structured_path(_ocr_root, "M36WA39N"))
    assert any(block.get("role") == "reference_item" for block in blocks)
    assert any(block.get("role") in {"backmatter_body", "tail_candidate_body"} for block in blocks)


def test_tsckavis_table_display_does_not_render_as_body_heading(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    fulltext = _fulltext_path(_ocr_root, "TSCKAVIS").read_text(encoding="utf-8", errors="replace")
    assert "### Table 1" not in fulltext


def test_frontmatter_side_candidates_do_not_remain_body_paragraph(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    blocks = _read_jsonl(_structured_path(_ocr_root, "A8E7SRVS"))
    assert not any(block.get("zone") == "frontmatter_side_zone" and block.get("role") == "body_paragraph" for block in blocks)
```

- [ ] **Step 2: Run the targeted integration seam**

Run:
`python -m pytest tests/test_ocr_signatures.py tests/test_ocr_document.py tests/test_ocr_families.py tests/test_ocr_real_paper_regressions.py -k "CAQNW9Q2 or M36WA39N or TSCKAVIS or frontmatter_side" -q`

Expected:
- FAIL on the currently weak family/signature/zone cases.

- [ ] **Step 3: Fix old-style numbered references at the signature layer**

Implement concrete typing similar to:

```python
if reference_numeric_dot_pattern.match(text):
    return Signature(kind="reference_numeric_dot", confidence=0.95, evidence=["numeric_dot_reference_marker"])
```

This should feed `ocr_document.py` and `ocr_families.py` so old-style references are not left as body candidates.

- [ ] **Step 4: Make frontmatter-side, reference-zone, and tail support authority explicit**

Apply minimal but authoritative fixes in `ocr_document.py` / `ocr_families.py`:

```python
if zone == "frontmatter_side_zone":
    block["family"] = "frontmatter_support"
    block["render_default"] = False

if is_reference_like and reference_anchor_present:
    block["family"] = "reference_like"
    block["zone"] = "reference_zone"

if tail_nonref_support:
    block["family"] = "tail_support"
    block["render_default"] = False
```

- [ ] **Step 5: Re-run Gate B**

Run:
`python -m pytest tests/test_ocr_roles.py tests/test_ocr_document.py tests/test_ocr_families.py tests/test_ocr_figures.py tests/test_ocr_objects.py tests/test_ocr_tables.py tests/test_ocr_integration_fixtures.py -q`

Expected:
- PASS.

- [ ] **Step 6: Suggested checkpoint commit**

```bash
git add paperforge/worker/ocr_signatures.py paperforge/worker/ocr_document.py paperforge/worker/ocr_families.py paperforge/worker/ocr_render.py tests/test_ocr_signatures.py tests/test_ocr_document.py tests/test_ocr_families.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: close OCR semantic authority gaps on real papers"
```

---

## Task 7: Converge reader and object behavior on the named real papers

**Files:**
- Modify: `paperforge/worker/ocr.py`
- Modify: `paperforge/worker/ocr_rebuild.py`
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `paperforge/worker/ocr_objects.py`
- Modify: `paperforge/worker/ocr_tables.py`
- Modify: `paperforge/worker/ocr_health.py`
- Test: `tests/test_ocr_real_paper_reader_audit.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Run the real-paper suite on the named keys after Gates A and B are green**

Use:

```powershell
$env:PAPERFORGE_REAL_OCR_VAULT="D:\L\OB\Literature-hub"
$env:PAPERFORGE_REAL_OCR_KEYS="TSCKAVIS,CAQNW9Q2,A8E7SRVS,K7R8PEKW,DWQQK2YB,M36WA39N,SAN9AYVR,2GN9LMCW,7C8829BD"
python -m pytest tests/test_ocr_real_paper_reader_audit.py tests/test_ocr_real_paper_regressions.py -v
```

Expected:
- Any remaining failures now represent actual branch gaps, not local red seams or false-positive audit logic.

- [ ] **Step 2: Close remaining figure/object completeness failures, not just render hygiene**

Lock or fix behaviors such as:

```python
def test_real_paper_legends_do_not_silently_disappear_from_object_inventory(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    figure_inventory = _read_json(_figure_inventory_path(_ocr_root, "DWQQK2YB"))
    reader_payload = _read_json(_reader_figures_path(_ocr_root, "DWQQK2YB"))
    assert figure_inventory.get("figure_legends")
    assert reader_payload.get("reader_figures")


def test_reader_figures_persist_after_rebuild(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    payload = _read_json(_reader_figures_path(_ocr_root, "TSCKAVIS"))
    assert payload["reader_figures"]
    assert "reader_coverage" in payload
```

If `ocr_objects.py` is omitting expected objects, make the omission explicit and traceable in health or object metadata rather than silently dropping output.

- [ ] **Step 3: Rebuild and re-run after each targeted fix, not after a large batch**

Use a tight loop:

```powershell
python -m pytest tests/test_ocr_real_paper_reader_audit.py -v
python -m pytest tests/test_ocr_real_paper_regressions.py -v
```

and only widen back to both files once the targeted failure class is closed.

- [ ] **Step 4: Update health expectations to expose any residual reader/object gap explicitly**

Concrete expectation:

```python
assert health["figure_reader_coverage_gap_count"] == 0
assert "reader_figure_coverage_gap" not in health.get("degraded_reasons", [])
```

- [ ] **Step 5: Suggested checkpoint commit**

```bash
git add paperforge/worker/ocr.py paperforge/worker/ocr_rebuild.py paperforge/worker/ocr_figures.py paperforge/worker/ocr_objects.py paperforge/worker/ocr_tables.py paperforge/worker/ocr_health.py tests/test_ocr_real_paper_reader_audit.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: converge OCR v2 on real-paper figure and object outputs"
```

---

## Task 8: Merge-readiness closure

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-ocr-v2-stabilization.md`
- Modify: `docs/superpowers/specs/2026-06-10-ocr-figure-reader-contract-design.md` only if the implemented behavior changed materially
- Modify: `docs/superpowers/specs/2026-06-10-ocr-real-paper-regression-ledger.md` if it is the active evidence ledger

- [ ] **Step 1: Run the four stabilization gates in order and record the outputs**

Run:

```bash
python -m pytest tests/test_ocr_figure_reader.py tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py tests/test_ocr_health.py -q
python -m pytest tests/test_ocr_roles.py tests/test_ocr_document.py tests/test_ocr_families.py tests/test_ocr_figures.py tests/test_ocr_objects.py tests/test_ocr_tables.py tests/test_ocr_integration_fixtures.py -q
python -m pytest tests/test_ocr_real_paper_reader_audit.py tests/test_ocr_real_paper_regressions.py -v
git status --short
```

Expected:
- all required tests PASS
- only intentional tracked files remain changed

- [ ] **Step 2: Remove or quarantine scratch artifacts**

Examples to audit before merge:

```text
_check_effect.py
_check_rebuild.py
_extract_master_figs.py
_render_full.py
_master_funcs.txt
```

If a file is still needed, move it into a clearly named tracked debug or maintainer location. Do not leave branch-root scratch utilities unexplained.

- [ ] **Step 3: Update the plan/spec ledger with final status**

Record:
- which problem keys are now green
- whether any keys remain intentionally deferred
- exact commands used for the final verification pass

- [ ] **Step 4: Suggested checkpoint commit**

```bash
git add docs/superpowers/plans/2026-06-11-ocr-v2-stabilization.md docs/superpowers/specs/2026-06-10-ocr-figure-reader-contract-design.md docs/superpowers/specs/2026-06-10-ocr-real-paper-regression-ledger.md
git commit -m "docs: record OCR v2 stabilization closure"
```

---

## Execution Order Summary

1. Task 1: restore reader normalization contract.
2. Task 2: make render reader-primary and dedupe globally.
3. Task 3: tighten strict figure safety and health reporting.
4. Task 4: repair the real-paper reader audit harness.
5. Task 5: restore anchor-first pipeline order.
6. Task 6: close upstream semantic authority gaps.
7. Task 7: converge reader/object outputs on named real papers.
8. Task 8: enforce merge-readiness closure.

## Stop Conditions

- Stop if Gate A is still red after Task 3. Do not move upstream while the reader contract itself is unstable.
- Stop if Gate B is red after Task 6. Do not trust real-paper outcomes built on an unstable authority order.
- Stop if Gate C is green only because it skipped. Set the env and run it for real.
- Stop if new fixes cause debug token leakage into `fulltext.md`; restore hygiene before continuing.

## Recommended First Execution Slice

If execution starts immediately, do only this slice first:

1. Task 1 through Task 3.
2. Run Gate A.
3. Reassess before touching pipeline-order refactors.

That is the smallest slice that proves the branch is moving forward instead of churning locally.
