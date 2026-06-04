# OCR Structured Pipeline Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Phase 2 OCR structured pipeline outputs for resolved metadata, formal figure inventory, formal table inventory, and first-class figure/table objects while preserving PaperForge compatibility and keeping table images as the truth source.

**Architecture:** Build Phase 2 on top of the Phase 1 raw and structured block artifacts rather than directly on `render_page_blocks()`. Start by fixing the remaining Phase 1 path-truth-source gap, then add auditable multi-source metadata resolution plus caption-first figure/table inventories, asset crops, and object markdown files. Do not switch the main paper `fulltext.md` renderer yet; Phase 2 only creates the structured object layer that Phase 3 will consume.

**Tech Stack:** Python, pytest, existing PaperForge OCR worker, JSON/JSONL artifacts, Pillow/PyMuPDF-compatible page crops, current `paperforge_paths()` / `pipeline_paths()` path contracts

---

## File Structure

Phase 2 should establish these focused units:

- `paperforge/worker/ocr_artifacts.py`
  - Fix Phase 1 path handling so artifact roots come from the configured OCR root, not hardcoded `System/PaperForge/ocr`.
- `paperforge/worker/ocr_metadata.py`
  - New module for source candidate capture and resolved metadata generation.
- `paperforge/worker/ocr_figures.py`
  - New module for figure legend detection, figure asset candidates, caption-first matching, and figure inventory writing.
- `paperforge/worker/ocr_tables.py`
  - New module for table detection, table asset handling, and table inventory writing.
- `paperforge/worker/ocr_objects.py`
  - New module for object markdown emission for figures and tables.
- `paperforge/worker/ocr.py`
  - Keep orchestration entrypoint.
  - Modify only to invoke new Phase 2 builders after Phase 1 block artifacts exist.
- `tests/test_ocr_metadata.py`
  - New unit tests for multi-source metadata candidate preservation and resolution.
- `tests/test_ocr_figures.py`
  - New unit tests for legend detection, matching, and inventory generation.
- `tests/test_ocr_tables.py`
  - New unit tests for table truth-source policy and inventory generation.
- `tests/test_ocr_objects.py`
  - New unit tests for figure/table object markdown generation.
- `tests/test_ocr.py`
  - Extend end-to-end OCR postprocess expectations for Phase 2 artifacts.
- `tests/test_selection_sync_pdf.py`
  - Keep compatibility guardrails for enriched `meta.json`.
- `tests/test_ocr_integration_fixtures.py`
  - Extend real-result fixture coverage for figure/table inventories.

Rationale:

- Phase 2 should consume the new stable block artifacts rather than deepen renderer-side heuristics.
- The remaining Phase 1 gap around path truth source is best fixed immediately at the start of Phase 2.
- The renderer still stays compatibility-first until Phase 3; object generation comes first.

### Task 1: Fix The Phase 1 Path Truth Source Gap

**Files:**
- Modify: `paperforge/worker/ocr_artifacts.py`
- Modify: `paperforge/worker/ocr.py`
- Create: `tests/test_ocr_artifact_paths_config.py`

- [ ] **Step 1: Write the failing path-source tests**

```python
from __future__ import annotations

from pathlib import Path


def test_artifact_paths_follow_pipeline_ocr_root(tmp_path: Path) -> None:
    from paperforge.worker.ocr_artifacts import artifact_paths_for_root

    ocr_root = tmp_path / "CustomSystem" / "PaperForge" / "ocr"
    paths = artifact_paths_for_root(ocr_root, "KEY001")

    assert paths.paper_root == ocr_root / "KEY001"
    assert paths.meta_json == ocr_root / "KEY001" / "meta.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ocr_artifact_paths_config.py -q`
Expected: FAIL because the current helper hardcodes `System/PaperForge/ocr`.

- [ ] **Step 3: Refactor artifact path helpers**

Implement:

```python
def artifact_paths_for_root(ocr_root: Path, zotero_key: str) -> OCRArtifactPaths:
    ...
```

Then keep a small compatibility wrapper if useful:

```python
def artifact_paths_for_key(vault: Path, zotero_key: str) -> OCRArtifactPaths:
    paths = pipeline_paths(vault)
    return artifact_paths_for_root(paths["ocr"], zotero_key)
```

Use the configured path source everywhere in `paperforge/worker/ocr.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_artifact_paths_config.py tests/test_ocr_artifacts.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_artifacts.py paperforge/worker/ocr.py tests/test_ocr_artifact_paths_config.py tests/test_ocr_artifacts.py
git commit -m "fix: route OCR artifact paths through configured OCR root"
```

### Task 2: Lock Metadata Resolver Contract In Tests

**Files:**
- Create: `tests/test_ocr_metadata.py`
- Modify: `tests/test_ocr.py`
- Reference: `docs/superpowers/specs/2026-06-04-ocr-structured-pipeline-design.md`

- [ ] **Step 1: Write the failing metadata resolver tests**

```python
from __future__ import annotations


def test_resolved_metadata_prefers_zotero_but_preserves_ocr_candidates() -> None:
    from paperforge.worker.ocr_metadata import resolve_metadata

    source_metadata = {
        "zotero_key": "KEY001",
        "title": "Canonical Zotero Title",
        "authors": ["Alice", "Bob"],
        "year": 2024,
        "journal": "Journal A",
        "doi": "10.1000/xyz",
        "source": "zotero_bbt",
    }
    frontmatter_candidates = {
        "title": "Canonical Zotero Title",
        "authors_text": "Alice, Bob, Carol",
        "doi_candidates": ["10.1000/xyz"],
    }

    resolved = resolve_metadata(source_metadata, frontmatter_candidates)

    assert resolved["title"]["value"] == "Canonical Zotero Title"
    assert resolved["title"]["source"] == "zotero"
    assert resolved["authors"]["value"] == ["Alice", "Bob"]
    assert "raw_frontmatter" in resolved
```

- [ ] **Step 2: Add a failing end-to-end metadata artifact assertion**

Extend `tests/test_ocr.py`:

```python
assert (ocr_dir / "metadata" / "resolved_metadata.json").exists()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_metadata.py tests/test_ocr.py -k resolved_metadata -q`
Expected: FAIL because metadata resolver does not exist yet.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ocr_metadata.py tests/test_ocr.py
git commit -m "test: lock OCR phase2 metadata resolver contract"
```

### Task 3: Implement Multi-Source Metadata Resolution

**Files:**
- Create: `paperforge/worker/ocr_metadata.py`
- Modify: `paperforge/worker/ocr.py`
- Test: `tests/test_ocr_metadata.py`

- [ ] **Step 1: Implement metadata candidate extraction helpers**

Add narrow Phase 2 helpers for:

- frontmatter block candidate extraction from `blocks.structured.jsonl`
- DOI candidate extraction from early-page blocks
- raw preservation of author/affiliation/correspondence text

Do not attempt external API lookups in Phase 2.

- [ ] **Step 2: Implement `resolve_metadata()`**

Minimal target:

```python
def resolve_metadata(source_metadata: dict, frontmatter_candidates: dict) -> dict:
    ...
```

Rules:

- Zotero/BBT title, authors, year, journal, DOI stay primary when present
- OCR candidates are preserved in `alternatives` and `raw_frontmatter`
- include confidence scores for all resolved top-level fields

- [ ] **Step 3: Write `metadata/resolved_metadata.json` during OCR postprocess**

Phase 2 write order should become:

1. Phase 1 raw/source/block artifacts
2. metadata resolution
3. figure/table inventories
4. object markdown

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_metadata.py tests/test_ocr.py -k resolved_metadata -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_metadata.py paperforge/worker/ocr.py tests/test_ocr_metadata.py tests/test_ocr.py
git commit -m "feat: add OCR resolved metadata artifact"
```

### Task 4: Lock Figure Inventory Contract In Tests

**Files:**
- Create: `tests/test_ocr_figures.py`
- Modify: `tests/test_ocr_integration_fixtures.py`
- Modify: `tests/test_ocr.py`

- [ ] **Step 1: Write the failing figure legend and inventory tests**

```python
from __future__ import annotations


def test_formal_figure_count_is_based_on_legends_not_raw_images() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {"paper_id": "KEY001", "page": 3, "block_id": "p3_b21", "role": "figure_caption", "text": "Figure 1. Left column figure.", "bbox": [66, 446, 559, 628]},
        {"paper_id": "KEY001", "page": 3, "block_id": "p3_b22", "role": "figure_asset", "text": "", "bbox": [80, 116, 546, 434]},
        {"paper_id": "KEY001", "page": 3, "block_id": "p3_b23", "role": "figure_asset", "text": "", "bbox": [598, 114, 1063, 493]},
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert inventory["official_figure_count"] == 1
    assert len(inventory["figure_legends"]) == 1
```

- [ ] **Step 2: Add a failing end-to-end figure artifact assertion**

In `tests/test_ocr.py`:

```python
assert (ocr_dir / "structure" / "figure_inventory.json").exists()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_figures.py tests/test_ocr.py -k figure_inventory -q`
Expected: FAIL because figure inventory is not implemented yet.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ocr_figures.py tests/test_ocr_integration_fixtures.py tests/test_ocr.py
git commit -m "test: lock OCR phase2 figure inventory contract"
```

### Task 5: Implement Caption-First Figure Inventory

**Files:**
- Create: `paperforge/worker/ocr_figures.py`
- Modify: `paperforge/worker/ocr_roles.py`
- Modify: `paperforge/worker/ocr.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Strengthen figure caption detection only where needed for Phase 2**

Extend role logic conservatively so more formal legends are recognized:

- `Figure 1`
- `Fig. 1`
- `Supplementary Fig. S1`
- `Extended Data Fig. 1`

Keep this role work scoped to formal legend improvement, not general layout redesign.

- [ ] **Step 2: Implement `build_figure_inventory()`**

Required outputs:

- `figure_legends`
- `figure_assets`
- `matched_figures`
- `unmatched_legends`
- `unmatched_assets`
- `official_figure_count`

Phase 2 matching rules:

- caption-first
- same-page first
- adjacent-page fallback allowed
- preserve low-confidence matches with flags
- allow `legend-only` figures

- [ ] **Step 3: Persist `structure/figure_inventory.json`**

Emit the inventory during OCR postprocess from structured blocks.

- [ ] **Step 4: Add fixture-backed regression expectations**

Extend `tests/test_ocr_integration_fixtures.py` with at least one real OCR fixture that:

- produces one or more figure legends
- produces a non-empty `matched_figures` or `unmatched_legends`

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_figures.py tests/test_ocr_integration_fixtures.py tests/test_ocr.py -k figure_inventory -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_figures.py paperforge/worker/ocr_roles.py paperforge/worker/ocr.py tests/test_ocr_figures.py tests/test_ocr_integration_fixtures.py tests/test_ocr.py
git commit -m "feat: add OCR figure inventory"
```

### Task 6: Lock Table Inventory Contract In Tests

**Files:**
- Create: `tests/test_ocr_tables.py`
- Modify: `tests/test_ocr.py`

- [ ] **Step 1: Write the failing table truth-source tests**

```python
from __future__ import annotations


def test_table_image_is_truth_source_and_text_is_assistive() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {"paper_id": "KEY001", "page": 5, "block_id": "p5_b10", "role": "table_asset", "text": "raw parsed cells", "bbox": [100, 100, 600, 500]},
        {"paper_id": "KEY001", "page": 5, "block_id": "p5_b11", "role": "table_caption", "text": "Table 1. Results", "bbox": [100, 520, 600, 560]},
    ]

    inventory = build_table_inventory(structured_blocks)

    assert inventory["official_table_count"] == 1
    assert inventory["tables"][0]["truth_source"] == "image"
```

- [ ] **Step 2: Add a failing end-to-end table artifact assertion**

In `tests/test_ocr.py`:

```python
assert (ocr_dir / "structure" / "table_inventory.json").exists()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_tables.py tests/test_ocr.py -k table_inventory -q`
Expected: FAIL because table inventory is not implemented yet.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ocr_tables.py tests/test_ocr.py
git commit -m "test: lock OCR phase2 table inventory contract"
```

### Task 7: Implement Table Inventory With Image-First Policy

**Files:**
- Create: `paperforge/worker/ocr_tables.py`
- Modify: `paperforge/worker/ocr.py`
- Test: `tests/test_ocr_tables.py`

- [ ] **Step 1: Implement `build_table_inventory()`**

Required outputs:

- `tables`
- `unmatched_captions`
- `unmatched_assets`
- `official_table_count`

Rules:

- image is truth source
- parsed OCR text is attached as assistive payload only
- low-confidence table text must not upgrade text into truth

- [ ] **Step 2: Persist `structure/table_inventory.json`**

Write inventory during OCR postprocess from structured blocks.

- [ ] **Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_tables.py tests/test_ocr.py -k table_inventory -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/ocr_tables.py paperforge/worker/ocr.py tests/test_ocr_tables.py tests/test_ocr.py
git commit -m "feat: add OCR table inventory"
```

### Task 8: Generate Figure And Table Object Markdown Plus Asset Crops

**Files:**
- Create: `paperforge/worker/ocr_objects.py`
- Modify: `paperforge/worker/ocr.py`
- Create: `tests/test_ocr_objects.py`
- Modify: `tests/test_ocr_redo.py`

- [ ] **Step 1: Write the failing object markdown tests**

```python
from __future__ import annotations


def test_figure_object_markdown_links_image_and_legend(tmp_path) -> None:
    from paperforge.worker.ocr_objects import render_figure_object_markdown

    md = render_figure_object_markdown(
        {
            "figure_id": "figure_001",
            "page": 4,
            "caption": "Figure 1. Example.",
            "image_relpath": "assets/figures/figure_001.jpg",
            "confidence": 0.91,
        }
    )

    assert "# Figure 1" in md
    assert "![[../assets/figures/figure_001.jpg]]" in md
    assert "Figure 1. Example." in md
```

- [ ] **Step 2: Add end-to-end file existence assertions**

In `tests/test_ocr.py` and/or `tests/test_ocr_redo.py` assert that successful OCR creates:

- `assets/figures/*.jpg` or `assets/tables/*.jpg` when candidates exist
- `render/figures/*.md`
- `render/tables/*.md`

Use minimal fixture conditions so the tests stay deterministic.

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_objects.py tests/test_ocr.py tests/test_ocr_redo.py -k "figure_object or table_object or render/figures or render/tables" -q`
Expected: FAIL because object markdown and assets are not created yet.

- [ ] **Step 4: Implement object emitters and crop writers**

`ocr_objects.py` should provide:

- `render_figure_object_markdown()`
- `render_table_object_markdown()`
- narrow file-write helpers for object markdown

`paperforge/worker/ocr.py` should:

- crop figure/table assets into `assets/figures/` and `assets/tables/`
- write object markdown into `render/figures/` and `render/tables/`

Phase 2 rules:

- orphan media goes to `assets/orphans/`
- do not rewrite main `fulltext.md` yet
- do not expand parsed tables into body render

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_objects.py tests/test_ocr.py tests/test_ocr_redo.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_objects.py paperforge/worker/ocr.py tests/test_ocr_objects.py tests/test_ocr.py tests/test_ocr_redo.py
git commit -m "feat: emit OCR figure and table objects"
```

### Task 9: Preserve Compatibility While Adding Phase 2 Artifacts

**Files:**
- Modify: `paperforge/worker/ocr.py`
- Modify: `paperforge/worker/sync.py`
- Modify: `tests/test_selection_sync_pdf.py`
- Modify: `tests/e2e/test_ocr_e2e.py`

- [ ] **Step 1: Add compatibility guard tests**

Add or extend tests to ensure:

- old `meta.json` fields still exist
- old top-level `fulltext.md` still exists
- sync still reads `ocr_status`
- `ocr redo` still means full rerun, not partial rebuild

- [ ] **Step 2: Run tests to establish the baseline**

Run: `python -m pytest tests/test_selection_sync_pdf.py tests/e2e/test_ocr_e2e.py tests/test_ocr_redo.py -q`
Expected: PASS before and after Phase 2 work.

- [ ] **Step 3: Keep Phase 2 additive**

Do not:

- redirect consumers to `render/fulltext.md`
- modify redo semantics
- introduce derived-drift automation

Phase 2 adds new artifacts only.

- [ ] **Step 4: Run compatibility tests to verify they still pass**

Run: `python -m pytest tests/test_selection_sync_pdf.py tests/e2e/test_ocr_e2e.py tests/test_ocr_redo.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr.py paperforge/worker/sync.py tests/test_selection_sync_pdf.py tests/e2e/test_ocr_e2e.py tests/test_ocr_redo.py
git commit -m "refactor: preserve OCR compatibility while adding phase2 artifacts"
```

### Task 10: Final Verification For Phase 2

**Files:**
- Verify only

- [ ] **Step 1: Run Phase 2 focused suite**

Run: `python -m pytest tests/test_ocr_artifact_paths_config.py tests/test_ocr_metadata.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_objects.py tests/test_ocr.py tests/test_ocr_redo.py tests/test_ocr_integration_fixtures.py tests/test_selection_sync_pdf.py tests/e2e/test_ocr_e2e.py -q`
Expected: PASS

- [ ] **Step 2: Run Phase 1 regression suite again**

Run: `python -m pytest tests/test_ocr_artifacts.py tests/test_ocr_blocks.py tests/test_ocr_roles.py tests/test_ocr_rendering.py tests/test_ocr_state_machine.py tests/test_sync.py tests/test_context.py tests/test_status.py -q`
Expected: PASS

- [ ] **Step 3: Inspect diff scope**

Run: `git diff -- paperforge/worker docs/superpowers tests`
Expected: changes are limited to metadata, inventories, object artifacts, and the path-truth-source fix; no premature renderer-v2 or doctor work.

- [ ] **Step 4: Commit verification-only fixes if needed**

```bash
git add -A
git commit -m "test: finalize OCR structured pipeline phase2 object layer"
```

## Risks To Watch During Execution

1. Fix the path-truth-source issue first; do not build more artifacts on the hardcoded root.
2. Do not let metadata resolution call remote services in Phase 2.
3. Keep figure detection conservative and auditable; preserve low-confidence outputs instead of inventing certainty.
4. Keep table image primary even when OCR text looks good.
5. Do not rewrite the main renderer yet.
6. Do not let redo semantics drift away from “full-paper rerun”.

