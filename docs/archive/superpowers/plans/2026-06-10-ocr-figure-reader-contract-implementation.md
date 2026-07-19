# OCR Figure Reader Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a stable reader-facing figure contract that preserves strict matching standards, keeps human-discernible figure information visible, deduplicates caption/body output, persists reader artifacts and health metrics, and avoids exposing debug artifact names in `fulltext.md`.

**Architecture:** Insert a normalization adapter between strict figure inventory outputs and the new reader layer so reader synthesis never depends on unstable raw bucket schemas. Persist the reader layer as a first-class artifact with health metrics before migrating rendering. Only after reader synthesis, artifacts, and render routing are stable should minimal strict-layer sequence promotion be introduced.

**Tech Stack:** Python 3, dataclasses, existing OCR worker modules under `paperforge/worker/`, pytest

---

## File Map

### Existing files to modify

- `paperforge/worker/ocr.py`
  - Current OCR postprocess and page rendering path; must be checked as a real fulltext entrypoint and updated to persist reader payloads and render reader figures.
- `paperforge/worker/ocr_attach.py`
  - Current strict caption/media pairing logic; likely strict-layer seam for sequence-adjacent metadata and may need minor exposure helpers.
- `paperforge/worker/ocr_emit.py`
  - Current page markdown emitter; may or may not be the real production entrypoint. Must only be modified after entrypoint confirmation.
- `paperforge/worker/ocr_orchestrator.py`
  - Current layered ordering helper; may need stable ordering metadata for placement.
- `paperforge/worker/ocr_roles.py`
  - Existing figure/table caption recognition surface; may be reused by adapter backfill helpers when normalized inputs need formal legend signals.
- `tests/test_ocr_attachments.py`
  - Current strict attachment tests; use these for strict-layer input fixtures when possible.
- `tests/test_ocr_rendering.py`
  - Current OCR rendering behavior tests; expand for consumed-caption skips, render-once behavior, and debug leakage.
- `tests/test_ocr_emission_regressions.py`
  - Current emitter regression tests; use for reader-card render hygiene if `ocr_emit.py` remains on the main path.

### New files to create

- `paperforge/worker/ocr_figure_reader.py`
  - Reader-layer module containing:
    - strict inventory normalization adapter
    - eligible input collection
    - reader figure synthesis
    - reader coverage calculation
- `tests/test_ocr_figure_reader.py`
  - Unit tests for normalization, gates, coverage, stable ids, hold semantics, and consumption rules.

### Files likely needed for artifact/health closure

- `paperforge/worker/ocr_health.py`
  - If present on the execution branch, update with reader coverage metrics.
- Reader artifact writer location on the execution branch
  - If no dedicated writer exists, add artifact persistence in `ocr.py` next to existing OCR output files.

## Phase Boundaries

### Phase 1

Normalize strict inventory inputs and build reader synthesis. No render migration yet.

### Phase 2

Persist reader artifacts and health metrics. No user-facing render migration yet.

### Phase 3

Confirm the real fulltext render entrypoint, then migrate render to consume reader figures, skip consumed captions, and hide debug artifact names.

### Phase 4

Add minimal strict-layer sequence promotion. Reader layer only projects the resulting strict status.

### Phase 5

Lock behavior with real-paper audit checks.

## Task 0: Add Strict Inventory Adapter Before Reader Synthesis

**Files:**
- Create: `paperforge/worker/ocr_figure_reader.py`
- Test: `tests/test_ocr_figure_reader.py`

- [ ] **Step 1: Write failing tests for strict inventory normalization**

```python
from __future__ import annotations


def test_normalize_strict_inventory_maps_bucket_variants_to_common_fields() -> None:
    from paperforge.worker.ocr_figure_reader import _normalize_strict_figure_inventory

    strict_inventory = {
        "matched_figures": [
            {
                "figure_number": 6,
                "block_id": 15,
                "text": "Fig. 6 The figure represents...",
                "matched_assets": [{"block_id": 40, "bbox": [1, 2, 3, 4]}],
                "match_score": 0.91,
            }
        ],
        "ambiguous_figures": [
            {
                "figure_number": 3,
                "legend_block_id": 9,
                "text": "FIGURE 3 | Histological evaluation...",
                "candidates": [{"asset_block_id": 10, "match_score": 0.51}, {"asset_block_id": 11, "match_score": 0.49}],
            }
        ],
        "unmatched_legends": [
            {
                "block_id": 21,
                "text": "FIGURE 2 | Treadmill exercise protocols...",
                "figure_number": 2,
            }
        ],
        "unresolved_clusters": [
            {
                "page": 7,
                "media_block_ids": [30, 31],
            }
        ],
    }

    structured_blocks = [
        {"block_id": 21, "marker_signature": {"type": "figure_number"}, "zone": "display_zone", "style_family": "legend_like"}
    ]

    normalized = _normalize_strict_figure_inventory(strict_inventory, structured_blocks)

    assert normalized["matched_figures"][0]["legend_block_id"] == 15
    assert normalized["matched_figures"][0]["caption_text"] == "Fig. 6 The figure represents..."
    assert normalized["matched_figures"][0]["asset_block_ids"] == [40]
    assert normalized["ambiguous_figures"][0]["candidate_asset_ids"] == [10, 11]
    assert normalized["unmatched_legends"][0]["legend_block_id"] == 21
    assert normalized["unresolved_clusters"][0]["asset_block_ids"] == [30, 31]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ocr_figure_reader.py -v`
Expected: FAIL because `ocr_figure_reader.py` and `_normalize_strict_figure_inventory()` do not exist yet

- [ ] **Step 3: Create the reader module with adapter skeleton**

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReaderCoverage:
    total: int
    accounted: int
    gap_count: int

    def as_dict(self) -> dict:
        ratio = 1.0 if self.total == 0 else self.accounted / self.total
        return {
            "total": self.total,
            "accounted": self.accounted,
            "gap_count": self.gap_count,
            "ratio": ratio,
        }


def _index_structured_blocks(structured_blocks: list[dict]) -> dict[int | str, dict]:
    return {block.get("block_id"): block for block in structured_blocks if block.get("block_id") is not None}


def _normalize_strict_figure_inventory(strict_inventory: dict, structured_blocks: list[dict]) -> dict:
    block_index = _index_structured_blocks(structured_blocks)
    return {
        "matched_figures": [],
        "held_figures": [],
        "ambiguous_figures": [],
        "unmatched_legends": [],
        "unresolved_clusters": [],
        "block_index": block_index,
    }
```

- [ ] **Step 4: Run test and observe the next failure**

Run: `pytest tests/test_ocr_figure_reader.py -v`
Expected: FAIL because adapter still returns empty normalized buckets

- [ ] **Step 5: Implement normalization helpers for raw bucket variants**

```python
def _legend_block_id(item: dict) -> int | str | None:
    return item.get("legend_block_id", item.get("block_id"))


def _caption_text(item: dict) -> str:
    return str(item.get("caption_text", item.get("text", "")) or "")


def _asset_ids_from_item(item: dict) -> list[int | str]:
    if "asset_block_ids" in item:
        return list(item.get("asset_block_ids", []))
    if "matched_assets" in item:
        return [asset.get("block_id") for asset in item.get("matched_assets", []) if asset.get("block_id") is not None]
    if "candidates" in item:
        return [asset.get("asset_block_id") for asset in item.get("candidates", []) if asset.get("asset_block_id") is not None]
    if "media_block_ids" in item:
        return list(item.get("media_block_ids", []))
    return []


def _normalize_bucket(items: list[dict], bucket_name: str, block_index: dict[int | str, dict]) -> list[dict]:
    normalized = []
    for item in items:
        legend_block_id = _legend_block_id(item)
        block = block_index.get(legend_block_id, {})
        normalized.append(
            {
                "figure_number": item.get("figure_number"),
                "legend_block_id": legend_block_id,
                "caption_text": _caption_text(item),
                "asset_block_ids": _asset_ids_from_item(item),
                "candidate_asset_ids": _asset_ids_from_item(item) if bucket_name in {"held_figures", "ambiguous_figures"} else [],
                "marker_type": item.get("marker_type") or (block.get("marker_signature") or {}).get("type"),
                "inline_mention": bool(item.get("inline_mention", False)),
                "panel_label": bool(item.get("panel_label", False)),
                "body_prose_likelihood": float(item.get("body_prose_likelihood", 0.0)),
                "zone": item.get("zone") or block.get("zone"),
                "style_family": item.get("style_family") or block.get("style_family"),
                "strict_status": item.get("strict_status", bucket_name.removesuffix("s")),
                "source_item": item,
            }
        )
    return normalized


def _normalize_strict_figure_inventory(strict_inventory: dict, structured_blocks: list[dict]) -> dict:
    block_index = _index_structured_blocks(structured_blocks)
    return {
        "matched_figures": _normalize_bucket(strict_inventory.get("matched_figures", []), "matched_figures", block_index),
        "held_figures": _normalize_bucket(strict_inventory.get("held_figures", []), "held_figures", block_index),
        "ambiguous_figures": _normalize_bucket(strict_inventory.get("ambiguous_figures", []), "ambiguous_figures", block_index),
        "unmatched_legends": _normalize_bucket(strict_inventory.get("unmatched_legends", []), "unmatched_legends", block_index),
        "unresolved_clusters": _normalize_bucket(strict_inventory.get("unresolved_clusters", []), "unresolved_clusters", block_index),
        "block_index": block_index,
    }
```

- [ ] **Step 6: Run tests and commit**

Run: `pytest tests/test_ocr_figure_reader.py -v`
Expected: PASS

```bash
git add paperforge/worker/ocr_figure_reader.py tests/test_ocr_figure_reader.py
git commit -m "feat: normalize strict OCR figure inventory for reader synthesis"
```

## Task 1: Add Reader Schema, Stable IDs, and Status Separation

**Files:**
- Modify: `paperforge/worker/ocr_figure_reader.py`
- Test: `tests/test_ocr_figure_reader.py`

- [ ] **Step 1: Write failing tests for reader status separation and stable IDs**

```python
def test_reader_figure_preserves_separate_reader_and_strict_status() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    normalized_inventory = {
        "matched_figures": [],
        "held_figures": [],
        "ambiguous_figures": [
            {
                "figure_number": 3,
                "legend_block_id": 9,
                "caption_text": "FIGURE 3 | Histological evaluation...",
                "candidate_asset_ids": [10, 11],
                "strict_status": "ambiguous",
                "marker_type": "figure_number",
            }
        ],
        "unmatched_legends": [],
        "unresolved_clusters": [],
    }

    result = synthesize_reader_figures(normalized_inventory, structured_blocks=[])

    rf = result["reader_figures"][0]
    assert rf["reader_status"] == "GROUPED_APPROXIMATE"
    assert rf["strict_status"] == "ambiguous"
    assert rf["strict_source"] == "ambiguous_figures"


def test_reader_figure_id_uses_first_asset_id_for_visual_group_when_figure_number_missing() -> None:
    from paperforge.worker.ocr_figure_reader import _stable_reader_figure_id

    assert _stable_reader_figure_id(None, page=7, first_asset_block_id=31, ordinal=2) == "visual_group_7_31_reader"
```

- [ ] **Step 2: Run tests to verify RED state**

Run: `pytest tests/test_ocr_figure_reader.py -v`
Expected: FAIL because synthesis and id rules are not implemented yet

- [ ] **Step 3: Implement stable ID helper and minimal synthesis shell**

```python
def _stable_reader_figure_id(
    figure_number: int | None,
    *,
    page: int | None = None,
    first_asset_block_id: int | str | None = None,
    ordinal: int | None = None,
    suffix: str = "",
) -> str:
    if figure_number is not None:
        base = f"figure_{int(figure_number):03d}_reader"
    elif first_asset_block_id is not None:
        base = f"visual_group_{int(page or 0)}_{first_asset_block_id}_reader"
    else:
        base = f"visual_group_{int(page or 0)}_{int(ordinal or 0)}_reader"
    return f"{base}{suffix}"


def synthesize_reader_figures(strict_inventory: dict, structured_blocks: list[dict], document_structure: object | None = None) -> dict:
    normalized = _normalize_strict_figure_inventory(strict_inventory, structured_blocks)
    return {
        "normalized_inputs": normalized,
        "reader_figures": [],
        "reader_coverage": ReaderCoverage(total=0, accounted=0, gap_count=0).as_dict(),
        "consumed_caption_block_ids": [],
        "consumed_asset_block_ids": [],
    }
```

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/test_ocr_figure_reader.py -v`
Expected: FAIL only on missing reader figure materialization, while stable id test passes

```bash
git add paperforge/worker/ocr_figure_reader.py tests/test_ocr_figure_reader.py
git commit -m "feat: add OCR reader figure schema and stable ids"
```

## Task 2: Build Eligible Inputs, Gates, and Deduplicated Coverage

**Files:**
- Modify: `paperforge/worker/ocr_figure_reader.py`
- Test: `tests/test_ocr_figure_reader.py`

- [ ] **Step 1: Write failing tests for gate behavior and coverage deduplication**

```python
def test_coverage_total_counts_deduplicated_eligible_inputs() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "ambiguous_figures": [
            {
                "figure_number": 2,
                "legend_block_id": 21,
                "caption_text": "FIGURE 2 | Treadmill exercise protocols...",
                "candidate_asset_ids": [30, 31],
                "marker_type": "figure_number",
            }
        ],
        "unmatched_legends": [
            {
                "figure_number": 2,
                "legend_block_id": 21,
                "caption_text": "FIGURE 2 | Treadmill exercise protocols...",
                "marker_type": "figure_number",
            }
        ],
        "matched_figures": [],
        "held_figures": [],
        "unresolved_clusters": [],
    }

    result = synthesize_reader_figures(strict_inventory, structured_blocks=[])

    assert result["reader_coverage"]["total"] == 1


def test_ambiguous_without_formal_legend_does_not_enter_reader_layer() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "matched_figures": [],
        "held_figures": [],
        "ambiguous_figures": [
            {
                "legend_block_id": 50,
                "caption_text": "Figure 2 shows the progression...",
                "candidate_asset_ids": [70],
                "marker_type": "figure_number",
                "inline_mention": True,
            }
        ],
        "unmatched_legends": [],
        "unresolved_clusters": [],
    }

    result = synthesize_reader_figures(strict_inventory, structured_blocks=[])

    assert result["reader_figures"] == []
    assert result["reader_coverage"]["total"] == 0
```

- [ ] **Step 2: Run tests to verify RED state**

Run: `pytest tests/test_ocr_figure_reader.py -v`
Expected: FAIL because eligible input collection and deduped coverage are not implemented

- [ ] **Step 3: Implement formal legend gate, salient gate, and eligible-input collector**

```python
def _passes_formal_legend_gate(item: dict) -> bool:
    return (
        item.get("marker_type") == "figure_number"
        and not bool(item.get("inline_mention"))
        and not bool(item.get("panel_label"))
        and float(item.get("body_prose_likelihood", 0.0)) < 0.5
        and not bool(item.get("strict_reject"))
    )


def _passes_salient_visual_group_gate(item: dict) -> bool:
    zone = str(item.get("zone") or "")
    if zone == "preproof_cover_zone":
        return False
    area_ratio = float(item.get("cluster_area_ratio", 0.0))
    width_ratio = float(item.get("width_ratio", 0.0))
    height_ratio = float(item.get("height_ratio", 0.0))
    media_count = int(item.get("media_block_count", len(item.get("asset_block_ids", []))))
    if area_ratio >= 0.03:
        return True
    if width_ratio >= 0.30 and height_ratio >= 0.08:
        return True
    if media_count >= 2 and area_ratio >= 0.02:
        return True
    return False


def _collect_reader_eligible_inputs(normalized: dict) -> list[dict]:
    eligible: list[dict] = []
    seen_legends: set[int | str] = set()

    for source_name in ("matched_figures", "held_figures", "ambiguous_figures"):
        for item in normalized.get(source_name, []):
            legend_block_id = item.get("legend_block_id")
            if legend_block_id is None or legend_block_id in seen_legends:
                continue
            if not _passes_formal_legend_gate(item):
                continue
            seen_legends.add(legend_block_id)
            eligible.append({"kind": "legend", "source": source_name, "item": item})

    for item in normalized.get("unmatched_legends", []):
        legend_block_id = item.get("legend_block_id")
        if legend_block_id is None or legend_block_id in seen_legends:
            continue
        if not _passes_formal_legend_gate(item):
            continue
        seen_legends.add(legend_block_id)
        eligible.append({"kind": "legend", "source": "unmatched_legends", "item": item})

    for item in normalized.get("unresolved_clusters", []):
        if item.get("linked_legend_block_id") is not None:
            continue
        if not _passes_salient_visual_group_gate(item):
            continue
        eligible.append({"kind": "visual_group", "source": "unresolved_clusters", "item": item})

    return eligible
```

- [ ] **Step 4: Implement coverage from deduplicated eligible inputs, not bucket sums**

```python
eligible_inputs = _collect_reader_eligible_inputs(normalized)
coverage_total = len(eligible_inputs)
```

Do not compute `coverage_total` by adding raw bucket lengths.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_ocr_figure_reader.py -v`
Expected: PASS

```bash
git add paperforge/worker/ocr_figure_reader.py tests/test_ocr_figure_reader.py
git commit -m "feat: add OCR reader input gating and deduplicated coverage"
```

## Task 3: Materialize Reader Figures and Fix HOLD Semantics

**Files:**
- Modify: `paperforge/worker/ocr_figure_reader.py`
- Test: `tests/test_ocr_figure_reader.py`

- [ ] **Step 1: Write failing tests for `LEGEND_ONLY`, `GROUPED_APPROXIMATE`, and `reader_hold` vs `audit_hold`**

```python
def test_grouped_approximate_requires_visual_candidates() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "matched_figures": [],
        "held_figures": [],
        "ambiguous_figures": [
            {
                "figure_number": 4,
                "legend_block_id": 44,
                "caption_text": "FIGURE 4 | Immunohistochemical staining...",
                "candidate_asset_ids": [],
                "marker_type": "figure_number",
            }
        ],
        "unmatched_legends": [],
        "unresolved_clusters": [],
    }

    result = synthesize_reader_figures(strict_inventory, structured_blocks=[])

    assert result["reader_figures"][0]["reader_status"] != "GROUPED_APPROXIMATE"


def test_reader_hold_does_not_default_to_caption_consumption() -> None:
    from paperforge.worker.ocr_figure_reader import _materialize_hold_outcome

    hold = _materialize_hold_outcome(
        legend_block_id=80,
        caption_text="weak fragment",
        page=10,
        candidate_asset_ids=[],
        hold_visibility="audit_hold",
    )

    assert hold["consumed_caption_block_ids"] == []
    assert hold["debug_refs"]["hold_visibility"] == "audit_hold"


def test_legend_only_consumes_caption_when_rendered() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "matched_figures": [],
        "held_figures": [],
        "ambiguous_figures": [],
        "unmatched_legends": [
            {
                "figure_number": 2,
                "legend_block_id": 21,
                "caption_text": "FIGURE 2 | Treadmill exercise protocols...",
                "marker_type": "figure_number",
            }
        ],
        "unresolved_clusters": [],
    }

    result = synthesize_reader_figures(strict_inventory, structured_blocks=[])

    assert result["consumed_caption_block_ids"] == [21]
    assert result["reader_figures"][0]["reader_status"] == "LEGEND_ONLY"
```

- [ ] **Step 2: Run tests to verify RED state**

Run: `pytest tests/test_ocr_figure_reader.py -v`
Expected: FAIL because hold visibility and reader figure materialization are not implemented

- [ ] **Step 3: Implement reader figure materialization functions**

```python
def _materialize_hold_outcome(
    *,
    legend_block_id,
    caption_text: str,
    page,
    candidate_asset_ids: list[int | str],
    hold_visibility: str,
) -> dict:
    reader_visible = hold_visibility == "reader_hold"
    return {
        "reader_figure_id": _stable_reader_figure_id(None, page=page, ordinal=0, suffix="_hold"),
        "figure_number": None,
        "reader_status": "HOLD",
        "strict_status": "held",
        "strict_source": "held_figures",
        "caption_block_id": legend_block_id,
        "caption_text": caption_text,
        "visual_groups": [],
        "consumed_caption_block_ids": [legend_block_id] if reader_visible and legend_block_id is not None and caption_text else [],
        "consumed_asset_block_ids": [],
        "debug_refs": {"candidate_asset_ids": list(candidate_asset_ids), "hold_visibility": hold_visibility},
    }
```

- [ ] **Step 4: Implement synthesis from eligible inputs**

```python
def _materialize_reader_figure(entry: dict) -> dict | None:
    source = entry["source"]
    item = entry["item"]

    if source == "matched_figures":
        return {
            "reader_figure_id": _stable_reader_figure_id(item.get("figure_number")),
            "figure_number": item.get("figure_number"),
            "reader_status": "EXACT_MATCH",
            "strict_status": item.get("strict_status", "matched"),
            "strict_source": source,
            "caption_block_id": item.get("legend_block_id"),
            "caption_text": item.get("caption_text", ""),
            "visual_groups": [{"page": item.get("page"), "asset_block_ids": list(item.get("asset_block_ids", [])), "group_status": "matched_group", "rendered_as_representative": True}],
            "consumed_caption_block_ids": [item.get("legend_block_id")] if item.get("legend_block_id") is not None else [],
            "consumed_asset_block_ids": list(item.get("asset_block_ids", [])),
            "debug_refs": {},
        }

    if source in {"held_figures", "ambiguous_figures"}:
        candidate_asset_ids = list(item.get("candidate_asset_ids", []))
        if candidate_asset_ids:
            return {
                "reader_figure_id": _stable_reader_figure_id(item.get("figure_number")),
                "figure_number": item.get("figure_number"),
                "reader_status": "GROUPED_APPROXIMATE",
                "strict_status": item.get("strict_status", "ambiguous"),
                "strict_source": source,
                "caption_block_id": item.get("legend_block_id"),
                "caption_text": item.get("caption_text", ""),
                "visual_groups": [{"page": item.get("page"), "asset_block_ids": candidate_asset_ids, "group_status": "candidate_group", "rendered_as_representative": False}],
                "consumed_caption_block_ids": [item.get("legend_block_id")] if item.get("legend_block_id") is not None else [],
                "consumed_asset_block_ids": [],
                "debug_refs": {"candidate_asset_ids": candidate_asset_ids},
            }
        if item.get("caption_text"):
            return {
                "reader_figure_id": _stable_reader_figure_id(item.get("figure_number")),
                "figure_number": item.get("figure_number"),
                "reader_status": "LEGEND_ONLY",
                "strict_status": item.get("strict_status", "held"),
                "strict_source": source,
                "caption_block_id": item.get("legend_block_id"),
                "caption_text": item.get("caption_text", ""),
                "visual_groups": [],
                "consumed_caption_block_ids": [item.get("legend_block_id")] if item.get("legend_block_id") is not None else [],
                "consumed_asset_block_ids": [],
                "debug_refs": {},
            }
        return None

    if source == "unmatched_legends":
        return {
            "reader_figure_id": _stable_reader_figure_id(item.get("figure_number")),
            "figure_number": item.get("figure_number"),
            "reader_status": "LEGEND_ONLY",
            "strict_status": item.get("strict_status", "unmatched"),
            "strict_source": source,
            "caption_block_id": item.get("legend_block_id"),
            "caption_text": item.get("caption_text", ""),
            "visual_groups": [],
            "consumed_caption_block_ids": [item.get("legend_block_id")] if item.get("legend_block_id") is not None else [],
            "consumed_asset_block_ids": [],
            "debug_refs": {},
        }

    if source == "unresolved_clusters":
        asset_ids = list(item.get("asset_block_ids", []))
        return {
            "reader_figure_id": _stable_reader_figure_id(None, page=item.get("page"), first_asset_block_id=asset_ids[0] if asset_ids else None, ordinal=1),
            "figure_number": None,
            "reader_status": "ASSET_GROUP_ONLY",
            "strict_status": item.get("strict_status", "unresolved_cluster"),
            "strict_source": source,
            "caption_block_id": None,
            "caption_text": "",
            "visual_groups": [{"page": item.get("page"), "asset_block_ids": asset_ids, "group_status": "candidate_group", "rendered_as_representative": True}],
            "consumed_caption_block_ids": [],
            "consumed_asset_block_ids": asset_ids,
            "debug_refs": {},
        }

    return None
```

- [ ] **Step 5: Assemble final synthesis payload and commit**

Run: `pytest tests/test_ocr_figure_reader.py -v`
Expected: PASS

```bash
git add paperforge/worker/ocr_figure_reader.py tests/test_ocr_figure_reader.py
git commit -m "feat: materialize OCR reader figures and hold semantics"
```

## Task 4: Persist Reader Payload and Health Metrics

**Files:**
- Modify: `paperforge/worker/ocr.py`
- Modify: `paperforge/worker/ocr_health.py` if it exists on the execution branch
- Test: `tests/test_ocr_rendering.py`
- Test: `tests/test_ocr_figure_reader.py`

- [ ] **Step 1: Write failing tests for persisted reader payload and health coverage metrics**

```python
def test_reader_payload_contains_reader_coverage_and_consumed_ids() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "matched_figures": [],
        "held_figures": [],
        "ambiguous_figures": [],
        "unmatched_legends": [
            {
                "figure_number": 2,
                "legend_block_id": 21,
                "caption_text": "FIGURE 2 | Treadmill exercise protocols...",
                "marker_type": "figure_number",
            }
        ],
        "unresolved_clusters": [],
    }

    result = synthesize_reader_figures(strict_inventory, structured_blocks=[])

    assert result["reader_coverage"]["total"] == 1
    assert result["reader_coverage"]["accounted"] == 1
    assert result["reader_coverage"]["gap_count"] == 0
    assert result["consumed_caption_block_ids"] == [21]
```

- [ ] **Step 2: Run tests to verify RED state where persistence/health hooks are missing**

Run: `pytest tests/test_ocr_figure_reader.py tests/test_ocr_rendering.py -v`
Expected: FAIL on missing persistence integration and/or health fields

- [ ] **Step 3: Add reader payload persistence next to OCR artifacts**

```python
reader_payload = synthesize_reader_figures(strict_inventory, structured_blocks=blocks)
write_json(ocr_root / "structure" / "reader_figures.json", reader_payload)
```

If `structure/` does not already exist on the current branch, create it before writing.

- [ ] **Step 4: Add reader coverage fields into OCR health output**

```python
health["figure_reader_coverage_total"] = reader_payload["reader_coverage"]["total"]
health["figure_reader_coverage_accounted"] = reader_payload["reader_coverage"]["accounted"]
health["figure_reader_coverage_gap_count"] = reader_payload["reader_coverage"]["gap_count"]
health["figure_reader_coverage_ratio"] = reader_payload["reader_coverage"]["ratio"]
if reader_payload["reader_coverage"]["gap_count"] > 0:
    health.setdefault("degraded_reasons", []).append("reader_figure_coverage_gap")
```

If `ocr_health.py` is not present on the execution branch, add these fields to the current health payload builder inside `ocr.py` or the active health writer path instead of inventing a dead module.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_ocr_figure_reader.py tests/test_ocr_rendering.py -v`
Expected: PASS

```bash
git add paperforge/worker/ocr.py paperforge/worker/ocr_figure_reader.py tests/test_ocr_figure_reader.py tests/test_ocr_rendering.py
git commit -m "feat: persist OCR reader figure artifacts and health metrics"
```

## Task 5: Confirm Real Fulltext Render Entrypoint Before Render Migration

**Files:**
- Modify: `paperforge/worker/ocr.py`
- Modify: `paperforge/worker/ocr_emit.py` only if confirmed live
- Test: `tests/test_ocr_rendering.py`

- [ ] **Step 1: Write a failing test against the actual render entrypoint**

```python
def test_actual_fulltext_render_path_can_hide_consumed_caption_from_body_flow(tmp_path) -> None:
    from paperforge.worker.ocr import render_page_blocks

    # Build a minimal page payload with a formal caption and a body paragraph.
    # The expected failure is that the current path cannot yet accept reader payload / consumed ids.
    ...
```

The test must call the production render entrypoint that ultimately feeds `postprocess_ocr_result()`. Do not write a constant-failure test.

- [ ] **Step 2: Run test to verify RED state**

Run: `pytest tests/test_ocr_rendering.py -v`
Expected: FAIL because the live render entrypoint does not yet consume reader payloads

- [ ] **Step 3: Trace and document the actual entrypoint in code before editing**

Confirm in code review notes inside the task implementation:

1. Which function writes page markdown lines
2. Which function writes `fulltext.md`
3. Whether `ocr_emit.emit_page_markdown()` is on the live path or only a helper/legacy test seam

Only modify `ocr_emit.py` if it is confirmed to be on the production path. Otherwise modify the confirmed live renderer in `ocr.py`.

- [ ] **Step 4: Commit the entrypoint confirmation with the first render integration change**

```bash
git add paperforge/worker/ocr.py paperforge/worker/ocr_emit.py tests/test_ocr_rendering.py
git commit -m "refactor: confirm OCR fulltext render entrypoint"
```

## Task 6: Migrate Render to Reader Figures and Enforce Render Hygiene

**Files:**
- Modify: confirmed live renderer in `paperforge/worker/ocr.py`
- Modify: `paperforge/worker/ocr_emit.py` if live
- Test: `tests/test_ocr_rendering.py`
- Test: `tests/test_ocr_emission_regressions.py`

- [ ] **Step 1: Write failing emitter-driven tests for debug leakage, render-once, and caption dedupe**

```python
def test_emitter_driven_render_never_exposes_debug_figure_ids(tmp_path) -> None:
    from paperforge.worker.ocr_emit import emit_page_markdown

    class Node:
        def __init__(self, node_id, node_type, text="", block_id=None):
            self.node_id = node_id
            self.node_type = node_type
            self.text = text
            self.block_id = block_id

    spine = [Node("p1", "paragraph", "Body paragraph.", block_id=1)]
    reader_figures = [
        {
            "reader_figure_id": "figure_003_reader",
            "reader_status": "LEGEND_ONLY",
            "strict_status": "unmatched",
            "caption_text": "FIGURE 3 | Histological evaluation...",
            "placement_page": 7,
            "debug_refs": {"strict_name": "unmatched_legend_003"},
        }
    ]

    rendered = emit_page_markdown(7, spine, [], consumed_caption_block_ids=set(), reader_figures=reader_figures, rendered_reader_figure_ids=set())

    assert "FIGURE 3 | Histological evaluation..." in rendered
    assert "unmatched_legend_" not in rendered
    assert "unresolved_cluster_" not in rendered
    assert "orphan_" not in rendered


def test_emitter_renders_reader_figure_at_most_once() -> None:
    from paperforge.worker.ocr_emit import emit_page_markdown

    class Node:
        def __init__(self, node_id, node_type, text=""):
            self.node_id = node_id
            self.node_type = node_type
            self.text = text

    reader_figures = [
        {
            "reader_figure_id": "figure_002_reader",
            "reader_status": "LEGEND_ONLY",
            "caption_text": "FIGURE 2 | Treadmill exercise protocols...",
            "placement_page": 7,
        }
    ]

    rendered_ids = set()
    first = emit_page_markdown(7, [Node("p1", "paragraph", "Body")], [], consumed_caption_block_ids=set(), reader_figures=reader_figures, rendered_reader_figure_ids=rendered_ids)
    second = emit_page_markdown(7, [Node("p1", "paragraph", "Body")], [], consumed_caption_block_ids=set(), reader_figures=reader_figures, rendered_reader_figure_ids=rendered_ids)

    assert first.count("FIGURE 2 | Treadmill exercise protocols...") == 1
    assert second.count("FIGURE 2 | Treadmill exercise protocols...") == 0
```

- [ ] **Step 2: Run tests to verify RED state**

Run: `pytest tests/test_ocr_emission_regressions.py tests/test_ocr_rendering.py -v`
Expected: FAIL because reader payload and render-once behavior are not yet wired into the live render path

- [ ] **Step 3: Pass reader payload and consumed ids into the live render path**

```python
reader_payload = read_json(ocr_root / "structure" / "reader_figures.json") if (ocr_root / "structure" / "reader_figures.json").exists() else {
    "reader_figures": [],
    "consumed_caption_block_ids": [],
    "consumed_asset_block_ids": [],
}

rendered_reader_figure_ids: set[str] = set()
consumed_caption_ids = set(reader_payload.get("consumed_caption_block_ids", []))
```

- [ ] **Step 4: Implement reader-figure render-once and consumed-caption skip in the live renderer**

```python
if block.get("block_id") in consumed_caption_ids:
    continue

for figure in page_reader_figures:
    rid = figure.get("reader_figure_id")
    if rid in rendered_reader_figure_ids:
        continue
    rendered_reader_figure_ids.add(rid)
    rendered.append(_render_reader_figure_card(figure))
```

The helper `_render_reader_figure_card()` must avoid printing debug bucket names and should only show human-facing statuses.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_ocr_emission_regressions.py tests/test_ocr_rendering.py -v`
Expected: PASS

```bash
git add paperforge/worker/ocr.py paperforge/worker/ocr_emit.py tests/test_ocr_emission_regressions.py tests/test_ocr_rendering.py
git commit -m "feat: render OCR reader figures without debug leakage"
```

## Task 7: Add Minimal Strict-Layer Sequence Match Promotion

**Files:**
- Modify: actual strict figure matching module on the execution branch
- Test: strict-layer figure tests on the execution branch
- Test: `tests/test_ocr_figure_reader.py`

- [ ] **Step 1: Identify the true strict-layer module for figure inventory on the execution branch**

Confirm which file currently owns strict figure inventory and exact/ambiguous/held/unmatched outputs.

Preferred targets:

1. `paperforge/worker/ocr_figures.py` if present on the execution branch
2. Else the active figure-inventory builder inside `paperforge/worker/ocr.py` or `ocr_attach.py`

Do not primarily implement `SEQUENCE_MATCH` inside `ocr_figure_reader.py`.

- [ ] **Step 2: Write a failing strict-layer test for sequence promotion**

```python
def test_strict_layer_promotes_contiguous_legends_and_ordered_visual_groups_to_sequence_match() -> None:
    ...
```

This test must target the strict inventory builder, not just the reader projection.

- [ ] **Step 3: Implement narrow sequence promotion in the strict layer**

Promotion preconditions:

1. contiguous figure numbers
2. compatible cluster count
3. monotonic page/order alignment
4. no contradiction with existing exact matches

Strict output should mark the result explicitly as `strict_status == "sequence_match"` or place it in a dedicated strict bucket.

- [ ] **Step 4: Update reader projection to map strict `sequence_match` -> reader `SEQUENCE_MATCH`**

```python
if item.get("strict_status") == "sequence_match":
    reader_status = "SEQUENCE_MATCH"
```

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_ocr_figure_reader.py <strict-figure-test-file> -v`
Expected: PASS

```bash
git add paperforge/worker/ocr_figure_reader.py paperforge/worker/ocr_attach.py tests/test_ocr_figure_reader.py
git commit -m "feat: add strict OCR sequence match promotion"
```

## Task 8: Add Real-Paper Audit Lock

**Files:**
- Modify: `tests/test_ocr_rendering.py`
- Modify: `tests/test_ocr_emission_regressions.py`
- Modify or create: real-paper audit test file on the execution branch

- [ ] **Step 1: Write failing real-paper audit checks against reader artifacts, not just raw fulltext fragments**

```python
def test_reader_payload_contains_formal_figures_for_a8e7srvs() -> None:
    ...


def test_fulltext_does_not_expose_debug_reader_artifacts() -> None:
    ...


def test_long_legends_do_not_appear_in_body_and_reader_card_twice() -> None:
    ...
```

Use emitted markdown or persisted `reader_figures.json`, not constant-failure sample strings.

- [ ] **Step 2: Run tests to verify RED state**

Run: `pytest <real-paper-audit-tests> -v`
Expected: FAIL until reader payload persistence and render migration are complete

- [ ] **Step 3: Implement final audit assertions**

At minimum, enforce:

1. every formal numbered legend has a strict outcome
2. every formal numbered legend has a reader outcome
3. if caption is consumed, it belongs to exactly one reader figure
4. if a reader figure is rendered, its id exists in `reader_figures`
5. no debug id substrings leak into `fulltext.md`

- [ ] **Step 4: Run focused suite and commit**

Run: `pytest tests/test_ocr_figure_reader.py tests/test_ocr_attachments.py tests/test_ocr_rendering.py tests/test_ocr_emission_regressions.py <real-paper-audit-tests> -v`
Expected: PASS

```bash
git add tests/test_ocr_figure_reader.py tests/test_ocr_attachments.py tests/test_ocr_rendering.py tests/test_ocr_emission_regressions.py
git commit -m "test: lock OCR figure reader contract on real papers"
```

## Self-Review Checklist

Spec coverage:

1. strict inventory adapter before synthesis: Task 0
2. schema, stable ids, status separation: Task 1
3. deduplicated eligible coverage: Task 2
4. HOLD semantics and cautious consumption: Task 3
5. persisted artifacts and health: Task 4
6. render entrypoint confirmation: Task 5
7. render migration and hygiene: Task 6
8. strict-layer sequence promotion: Task 7
9. real-paper audit lock: Task 8

Safety improvements from review:

1. No direct dependence on guessed strict inventory field names after Task 0
2. `coverage_total` derived from deduplicated eligible inputs, not raw bucket counts
3. Formal legend gate applies to held/ambiguous/unmatched legend flows
4. HOLD does not default to caption consumption
5. Sequence match belongs to strict layer, reader only projects it
6. Render plan explicitly confirms the live entrypoint before migration
7. No constant always-fail placeholder tests remain
8. Artifact and health persistence are explicit tasks, not implied follow-ups

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-10-ocr-figure-reader-contract-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
