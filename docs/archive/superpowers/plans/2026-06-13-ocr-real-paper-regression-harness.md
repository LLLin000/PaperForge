# OCR Real-Paper Regression Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-path regression harness with real-paper fixtures that fails against current known-bad behavior, then repair the OCR-v2 production chain in order: seed roles, document structure, figure/table ownership, final rendering.

**Architecture:** Two-phase execution. Phase 1 creates repo-local deterministic fixtures + production-path replay harness + failing contract tests — zero production code changes. Phase 2 repairs `ocr_roles.py`, `ocr_document.py`, `ocr_figures.py`/`ocr_figure_reader.py`, `ocr_tables.py`, `ocr_render.py` in dependency order, stopping when the Phase 1 gate passes.

**Tech Stack:** Python 3, pytest, existing OCR-v2 modules under `paperforge/worker/`

**Spec reference:** `docs/superpowers/specs/2026-06-13-ocr-real-paper-production-path-spec-realignment-design.md`

---

## Phase 1: Build The Gate (no production code changes)

### Task 1: Create fixture directory structure and expectations files

**Files:**
- Create: `tests/fixtures/ocr_real_papers/CAQNW9Q2/expectations.json`
- Create: `tests/fixtures/ocr_real_papers/DWQQK2YB/expectations.json`
- Create: `tests/fixtures/ocr_real_papers/A8E7SRVS/expectations.json`

- [ ] **Step 1: Create fixture root and expectations skeletons**

```bash
mkdir -p tests/fixtures/ocr_real_papers/CAQNW9Q2/annotated_pages
mkdir -p tests/fixtures/ocr_real_papers/DWQQK2YB/annotated_pages
mkdir -p tests/fixtures/ocr_real_papers/A8E7SRVS/annotated_pages
```

- [ ] **Step 2: Write CAQNW9Q2 expectations**

Write `tests/fixtures/ocr_real_papers/CAQNW9Q2/expectations.json`:

```json
{
  "document": {
    "expected_reader_figure_count_min": 2,
    "expected_reference_zone": true,
    "expected_abstract_span": true
  },
  "pages": {
    "1": {
      "expected_roles": [
        {"block_pattern": "Quantitative radiography", "role": "title_or_doc_title", "confidence": "medium"}
      ],
      "expected_non_body": [0, 1, 4, 5],
      "expected_reference_rules": [
        {"block_id_comment": "no block on page 1 should be reference_item"}
      ]
    },
    "7": {
      "expected_order_relations": [
        {"before_text": "Conclusion", "after_text": "References", "layer": "render_order_markdown"}
      ],
      "expected_reference_rules": [
        {"must_not_render_references_as_body": true}
      ]
    }
  }
}
```

- [ ] **Step 3: Write DWQQK2YB expectations**

Write `tests/fixtures/ocr_real_papers/DWQQK2YB/expectations.json`:

```json
{
  "document": {
    "expected_reader_figure_count_min": 3,
    "expected_reference_zone": true,
    "expected_abstract_span": true
  },
  "pages": {
    "35": {
      "expected_object_ownership": [
        {
          "object_type": "figure",
          "figure_number": 1,
          "must_render_as_object": true,
          "must_not_render_caption_blocks_as_body": true,
          "comment": "figure-summary page caption must not duplicate formal figure-page caption"
        }
      ]
    }
  },
  "expected_render_invariants": [
    {"type": "no_duplicate_caption", "caption_regex": "Fig\\.\\s*1"}
  ]
}
```

- [ ] **Step 4: Write A8E7SRVS page-level expectations**

Write `tests/fixtures/ocr_real_papers/A8E7SRVS/expectations.json`:

```json
{
  "pages": {
    "5": {
      "expected_object_ownership": [
        {"object_type": "figure", "figure_number": 1, "must_render_as_object": true, "comment": "must be reader-visible"},
        {"object_type": "figure", "figure_number": 2, "must_render_as_object": true, "comment": "must be reader-visible"},
        {"object_type": "figure", "figure_number": 3, "must_render_as_object": true, "comment": "must be reader-visible"},
        {"object_type": "figure", "figure_number": 4, "must_render_as_object": true, "comment": "must be reader-visible"}
      ],
      "expected_render_invariants": [
        {"type": "not_in_body", "text_contains": "Fig. 1", "comment": "no raw image/caption block as loose body output after ownership"}
      ]
    },
    "6": {
      "expected_consumption": [
        {"block_id_comment": "Fig.5 continuation sentence", "consumed_by_kind": "figure", "consumed_by_number": 5, "must_not_render_as_body": true}
      ]
    },
    "7": {
      "expected_object_ownership": [
        {"object_type": "table", "table_number": 3, "must_render_as_object": true, "must_not_split_by_body_blocks": true}
      ]
    },
    "12": {
      "expected_render_invariants": [
        {"type": "before_text", "before": "Conclusion", "after": "References", "layer": "render_order_markdown"}
      ]
    }
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/ocr_real_papers/
git commit -m "feat: add structured expectation fixtures for three audited papers"
```

---

### Task 2: Write production-path replay harness

**Files:**
- Create: `tests/test_ocr_real_paper_regressions.py` (replace or extend existing env-driven version)

- [ ] **Step 1: Write the replay harness helper**

```python
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "ocr_real_papers"


def _fixture_path(key: str, filename: str) -> Path:
    return FIXTURE_ROOT / key / filename


def _load_ocr_payload(key: str) -> list[dict]:
    """Load replayable PaddleOCR all_results payload from fixture."""
    path = _fixture_path(key, "ocr_payload.json")
    if not path.exists():
        pytest.skip(f"ocr_payload.json not found for {key}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_source_metadata(key: str) -> dict:
    path = _fixture_path(key, "source_metadata.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_expectations(key: str) -> dict:
    path = _fixture_path(key, "expectations.json")
    if not path.exists():
        pytest.skip(f"expectations.json not found for {key}")
    return json.loads(path.read_text(encoding="utf-8"))


def replay_production_pipeline(key: str, tmp_path: Path) -> dict:
    """Run the full OCR-v2 production path against a fixture paper.

    Returns a dict with keys:
    - structured_blocks
    - document_structure
    - figure_inventory
    - reader_payload
    - table_inventory
    - rendered_markdown
    """
    from paperforge.worker.ocr_blocks import build_raw_blocks_for_result_lines, build_structured_blocks
    from paperforge.worker.ocr_figures import build_figure_inventory
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures
    from paperforge.worker.ocr_tables import build_table_inventory
    from paperforge.worker.ocr_render import render_fulltext_markdown

    all_results = _load_ocr_payload(key)
    source_metadata = _load_source_metadata(key)

    raw_blocks = build_raw_blocks_for_result_lines(key, all_results)

    # Skip PDF backfill in CI — fixtures may not have source PDF
    # If span_metadata is needed, it should be precomputed in the payload

    structured, doc_structure = build_structured_blocks(
        raw_blocks,
        source_metadata=source_metadata,
    )

    figure_inventory = build_figure_inventory(structured)
    reader_payload = synthesize_reader_figures(figure_inventory, structured_blocks=structured)
    table_inventory = build_table_inventory(structured)

    markdown = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory=figure_inventory,
        table_inventory=table_inventory,
        page_count=max(int(b.get("page", 0) or 1) for b in structured) if structured else 1,
        document_structure=doc_structure,
        reader_payload=reader_payload,
    )

    return {
        "structured_blocks": structured,
        "document_structure": doc_structure,
        "figure_inventory": figure_inventory,
        "reader_payload": reader_payload,
        "table_inventory": table_inventory,
        "rendered_markdown": markdown,
    }


def _dump_debug_bundle(key: str, result: dict, tmp_path: Path) -> Path:
    """Write debug artifacts on assertion failure."""
    bundle = tmp_path / "debug_bundle"
    bundle.mkdir(exist_ok=True)
    (bundle / "structured_blocks.failed.jsonl").write_text(
        "\n".join(json.dumps(b, default=str) for b in result["structured_blocks"]), encoding="utf-8"
    )
    (bundle / "document_structure.failed.json").write_text(
        json.dumps(result.get("document_structure", {}), default=str, indent=2), encoding="utf-8"
    )
    (bundle / "figure_inventory.failed.json").write_text(
        json.dumps(result.get("figure_inventory", {}), default=str, indent=2), encoding="utf-8"
    )
    (bundle / "reader_figures.failed.json").write_text(
        json.dumps(result.get("reader_payload", {}), default=str, indent=2), encoding="utf-8"
    )
    (bundle / "table_inventory.failed.json").write_text(
        json.dumps(result.get("table_inventory", {}), default=str, indent=2), encoding="utf-8"
    )
    (bundle / "rendered.failed.md").write_text(result["rendered_markdown"], encoding="utf-8")
    return bundle
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_ocr_real_paper_regressions.py
git commit -m "feat: add production-path replay harness with debug bundle support"
```

---

### Task 3: Add spec-contract tests

**Files:**
- Create: `tests/test_ocr_spec_contracts.py`

- [ ] **Step 1: Write contract tests**

```python
from __future__ import annotations

import pytest


def test_contract_zone_is_not_role() -> None:
    """Being in the body_zone does not make a block body_paragraph by itself.
    A block must have accepted structural evidence, not just zone membership.
    """
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "text",
        "block_content": "Check for updates",
        "block_bbox": [900, 50, 1100, 72],
    }

    role = assign_block_role(block, page_blocks=[block], page_width=1200, page_height=1600)

    assert role.role not in ("section_heading", "subsection_heading"), (
        f"zone-only text must not become heading: {role.role}"
    )


def test_contract_reference_tail_first() -> None:
    """Reference-like text without reference_zone or numbering support
    must not be promoted to reference_item.
    """
    from paperforge.worker.ocr_roles import assign_block_role

    for ordinal_word in ("First,", "Fourth,", "Sixth,", "Additionally,", "Historically,", "Metabolically,"):
        block = {
            "block_label": "text",
            "block_content": f"{ordinal_word} some body prose that looks like a reference but is not one.",
            "block_bbox": [100, 200, 800, 260],
        }
        role = assign_block_role(block, page_blocks=[block], page_width=1200, page_height=1600)
        assert role.role != "reference_item", (
            f"Ordinal body opening '{ordinal_word}' must not become reference_item, got {role.role}"
        )


def test_contract_renderer_is_not_semantic_rescue() -> None:
    """render_fulltext_markdown must not promote blocks to figure/table/reference
    based on raw text alone when structured role does not support it.
    """
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {
            "block_id": "p1_b1",
            "page": 1,
            "role": "body_paragraph",
            "raw_label": "text",
            "text": "Fig. 1 This looks like a figure caption but has no accepted figure role.",
            "bbox": [100, 100, 800, 160],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    markdown = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={"matched_figures": []},
        table_inventory={"tables": []},
        page_count=1,
        document_structure=None,
        reader_payload={"reader_figures": [], "consumed_caption_block_ids": []},
    )

    assert "Fig. 1" in markdown, "readable text must not be silently dropped"
    assert "![[assets/figures/" not in markdown, "renderer must not invent figure embedding from raw text"


def test_contract_object_ownership_is_exclusive() -> None:
    """A block consumed by a figure object must not also appear as loose body text."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {
            "block_id": "p1_b1",
            "page": 1,
            "role": "figure_caption",
            "raw_label": "figure_title",
            "text": "Figure 1. A sample figure.",
            "bbox": [100, 100, 800, 160],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    reader_payload = {
        "reader_figures": [
            {
                "reader_figure_id": "figure_001_reader",
                "reader_status": "EXACT_MATCH",
                "caption_block_id": "p1_b1",
                "consumed_caption_block_ids": ["p1_b1"],
            }
        ],
        "consumed_caption_block_ids": ["p1_b1"],
    }

    markdown = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={"matched_figures": [{"figure_id": "figure_001", "text": "Figure 1. A sample figure.", "page": 1}]},
        table_inventory={"tables": []},
        page_count=1,
        document_structure=None,
        reader_payload=reader_payload,
    )

    occurrences = markdown.count("Figure 1.")
    assert occurrences == 1, (
        f"Consumed caption must appear exactly once in markdown, found {occurrences} occurrences"
    )


def test_contract_reading_segments_are_authoritative() -> None:
    """When page-local geometry would put body after references,
    document-level reading segments must override to keep body before references.
    """
    from paperforge.worker.ocr_render import render_fulltext_markdown

    # Conclusion block appears after References in page geometry (y=800 vs y=600),
    # but reading segments dictate Conclusion before References.
    blocks = [
        {
            "block_id": "p1_b2",
            "page": 1,
            "role": "reference_heading",
            "raw_label": "paragraph_title",
            "text": "References",
            "bbox": [100, 600, 400, 640],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "block_id": "p1_b3",
            "page": 1,
            "role": "reference_item",
            "raw_label": "text",
            "text": "[1] Example reference.",
            "bbox": [100, 660, 800, 700],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "block_id": "p1_b1",
            "page": 1,
            "role": "subsection_heading",
            "raw_label": "paragraph_title",
            "text": "Conclusion",
            "bbox": [100, 800, 400, 840],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    markdown = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={"matched_figures": []},
        table_inventory={"tables": []},
        page_count=1,
        document_structure=None,
        reader_payload={"reader_figures": [], "consumed_caption_block_ids": []},
    )

    conclusion_pos = markdown.find("Conclusion")
    references_pos = markdown.find("References")
    assert conclusion_pos < references_pos, (
        f"Conclusion must appear before References (conclusion at {conclusion_pos}, refs at {references_pos})"
    )
```

- [ ] **Step 2: Run tests to verify they reflect current behavior**

```bash
pytest tests/test_ocr_spec_contracts.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_ocr_spec_contracts.py
git commit -m "test: add spec-contract tests for zone, reference, renderer, ownership, segments"
```

---

### Task 4: Mark existing env-driven tests as audit-only

**Files:**
- Modify: `tests/test_ocr_real_paper_contract.py` — add module-level docstring
- Modify: `tests/test_ocr_real_paper_reader_audit.py` — add module-level docstring

- [ ] **Step 1: Classify existing tests**

Add to top of `tests/test_ocr_real_paper_contract.py`:

```python
"""Production-path contract audit for real OCR papers.

Classification: secondary audit coverage.
Primary regression gate is tests/test_ocr_real_paper_regressions.py
(spec-contract + fixture-backed production-path replay).

These tests validate broader real-paper drift but require
PAPERFORGE_REAL_OCR_VAULT env; they are not the deterministic
first-line gate.
"""
```

Add to top of `tests/test_ocr_real_paper_reader_audit.py`:

```python
"""Reader-figure audit for real OCR papers.

Classification: secondary audit coverage.
Primary regression gate is tests/test_ocr_real_paper_regressions.py.
"""
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_ocr_real_paper_contract.py tests/test_ocr_real_paper_reader_audit.py
git commit -m "docs: classify env-driven audit tests as secondary coverage"
```

---

## Phase 2: Repair Production Path (in dependency order)

### Task 5: Repair ocr_roles.py — seed role normalization

**Files:**
- Modify: `paperforge/worker/ocr_roles.py`

Direction per spec Section 9.1:
1. Deny ordinal body openings from becoming `reference_item`
2. Stop dangerous fallback paths that silently convert weak candidates into `body_paragraph`
3. Explicitly handle `footnote`, `vision_footnote`, `aside_text`

- [ ] **Step 1: Write failing test for ordinal prose**

In `tests/test_ocr_spec_contracts.py`, add a parametrized version of `test_contract_reference_tail_first` that includes all known false-positive ordinal words from the five audited samples.

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_ocr_spec_contracts.py::test_contract_reference_tail_first -v
```

Expected: FAIL — ordinal words like "First," are still becoming `reference_item`.

- [ ] **Step 3: Fix reference heuristic in ocr_roles.py**

In `assign_block_role()`, after the `_REFERENCE_PATTERN` check, add a denylist for known body-ordinal openings before promoting to `reference_item`:

```python
_BODY_ORDINAL_OPENINGS = frozenset({
    "first,", "second,", "third,", "fourth,", "fifth,", "sixth,", "seventh,", "eighth,", "ninth,", "tenth,",
    "additionally,", "historically,", "metabolically,", "clinically,", "conversely,", "however,",
    "interestingly,", "surprisingly,", "importantly,", "notably,", "moreover,", "furthermore,",
    "nevertheless,", "nonetheless,", "therefore,", "thus,", "hence,", "accordingly,", "consequently,",
})
```

In the `_looks_like_reference` path (around line 176), check the lowercased first word against this set before returning `reference_item`.

- [ ] **Step 4: Run spec-contract tests**

```bash
pytest tests/test_ocr_spec_contracts.py -v
```

Expected: `test_contract_reference_tail_first` now PASSES.

- [ ] **Step 5: Verify no existing test regressions**

```bash
pytest tests/test_ocr_roles.py tests/test_ocr_rendering.py -v
```

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_roles.py tests/test_ocr_spec_contracts.py
git commit -m "fix: deny body ordinal openings from becoming reference_item"
```

---

### Task 6: Repair ocr_document.py — reading segments and reference zone protection

**Files:**
- Modify: `paperforge/worker/ocr_document.py`

Direction per spec Section 9.2:
1. Mixed body/reference pages must not interleave references with unfinished body columns
2. Reference zone ownership must be stronger than generic tail/body fallback

- [ ] **Step 1: Run existing document tests as baseline**

```bash
pytest tests/test_ocr_document.py -v -k "reference"
```

- [ ] **Step 2: Identify and fix mixed page interleaving**

In `normalize_document_structure()`, after `_build_tail_reading_order()` and `_assign_tail_spread_ownership()`, add a check: when a page contains both body-continuation blocks and reference-zone blocks in left/right columns, the body continuation must complete before references begin. If the current tail segment ordering would place references before unfinished body columns, enforce column-major completion within that page's tail segment before switching to reference output.

- [ ] **Step 3: Run full document test suite**

```bash
pytest tests/test_ocr_document.py -v
```

- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/ocr_document.py
git commit -m "fix: enforce body-column completion before reference zone on mixed tail pages"
```

---

### Task 7: Repair ocr_figures.py + ocr_figure_reader.py — figure ownership

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `paperforge/worker/ocr_figure_reader.py`

Direction per spec Section 9.3:
1. Prevent summary-page and formal figure-page caption duplication
2. Attach continuation legends to correct reader-visible figure contract
3. Ensure consumed caption/asset ids are complete enough for duplicate suppression

- [ ] **Step 1: Fix summary-page vs formal-page duplication**

In `build_figure_inventory()`, the dedup logic at `_dedup_map` (around line 517) currently prefers pages with assets. When both a summary page and a body-page copy of the same caption exist, and the summary page has no assets, the dedup must prefer the page that has assets AND must not allow the other copy to appear independently in `unmatched_legends`.

Add an explicit check: if a deduped legend's copy exists on a page without assets and the dedup winner is on a page with assets, mark the copy page's legend as consumed (not unmatched).

- [ ] **Step 2: Verify with figure tests**

```bash
pytest tests/test_ocr_figures.py tests/test_ocr_figure_reader.py -v
```

- [ ] **Step 3: Commit**

```bash
git add paperforge/worker/ocr_figures.py
git commit -m "fix: prevent summary-page caption from duplicating formal figure-page caption"
```

---

### Task 8: Repair ocr_tables.py — table ownership

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`

Direction per spec Section 9.4:
1. Bind table caption, table asset, and table note under one table ownership contract
2. Prevent table fragments from bypassing inventory authority

- [ ] **Step 1: Bind table note to table object**

In `build_table_inventory()`, after a caption-asset match, scan for `vision_footnote` or `footnote` blocks on the same page that are geometrically adjacent to the matched asset (within 80px below). If found, attach them as `note_block_ids` to the table entry.

- [ ] **Step 2: Commit**

```bash
git add paperforge/worker/ocr_tables.py
git commit -m "fix: bind table notes to table ownership contract"
```

---

### Task 9: Repair ocr_render.py — final structured rendering

**Files:**
- Modify: `paperforge/worker/ocr_render.py`

Direction per spec Section 9.5:
1. Render only accepted artifacts and accepted body blocks
2. Consume figure/table/reference/abstract blocks exactly once
3. Do not use renderer text heuristics as semantic rescue

- [ ] **Step 1: Enforce single consumption in renderer**

In `render_fulltext_markdown()`, after building the initial output, add a pass that scans for any block whose id appears in `reader_payload["consumed_caption_block_ids"]` or `reader_payload["consumed_asset_block_ids"]` and removes duplicate appearances as loose body/caption text.

- [ ] **Step 2: Verify spec-contract tests pass**

```bash
pytest tests/test_ocr_spec_contracts.py -v
```

Expected: `test_contract_object_ownership_is_exclusive` and `test_contract_renderer_is_not_semantic_rescue` PASS.

- [ ] **Step 3: Commit**

```bash
git add paperforge/worker/ocr_render.py
git commit -m "fix: enforce single-consumption in final structured renderer"
```

---

### Task 10: Mark legacy render_page_blocks tests as diagnostic-only

**Files:**
- Modify: `tests/test_ocr_rendering.py` — add module docstring

- [ ] **Step 1: Classify**

Add to top of `tests/test_ocr_rendering.py`:

```python
"""Legacy page-local renderer tests.

Classification: diagnostic only.
render_page_blocks() is not the final fulltext truth for OCR-v2.
Primary production path is render_fulltext_markdown() in ocr_render.py.
These tests exist for backward compatibility and legacy trace interpretation.
"""
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_ocr_rendering.py
git commit -m "docs: mark legacy renderer tests as diagnostic-only"
```

---

### Task 11: Optional legacy side-effect cleanup in ocr.py

**Files:**
- Modify: `paperforge/worker/ocr.py`

Scope limited to:
- Reduce confusion between legacy `render_page_blocks()` and production `render_fulltext_markdown()` paths
- Do not make this file the main semantic repair surface

- [ ] **Step 1: Commit (if changes made)**

```bash
git add paperforge/worker/ocr.py
git commit -m "chore: reduce legacy renderer side effects in ocr.py"
```

---

## Execution Strategy

Phase 1 (Tasks 1-4) builds the gate with zero production code changes. Tests are expected to fail against current known-bad behavior per spec Section 11 requirement: "The new real-paper regression tests must fail against the current known-bad behavior before repair."

Phase 2 (Tasks 5-11) repairs production modules in the dependency order defined by the spec.

After each repair task, run:
```bash
pytest tests/test_ocr_spec_contracts.py tests/test_ocr_roles.py tests/test_ocr_document.py tests/test_ocr_figures.py tests/test_ocr_figure_reader.py tests/test_ocr_tables.py tests/test_ocr_rendering.py -v
```

to verify no regressions.
