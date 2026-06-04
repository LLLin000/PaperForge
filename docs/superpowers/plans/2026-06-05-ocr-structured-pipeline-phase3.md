# OCR Structured Pipeline Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Phase 3 renderer and quality-health outputs so PaperForge can generate `render/fulltext.md` from structured OCR artifacts and produce `health/ocr_health.json` plus doctor-readable quality diagnostics without changing redo semantics or introducing sync-driven rebuild automation yet.

**Architecture:** Build the new renderer strictly on top of the structured artifacts produced in Phases 1 and 2: `blocks.structured.jsonl`, `resolved_metadata.json`, `figure_inventory.json`, `table_inventory.json`, and object markdown under `render/figures` and `render/tables`. Keep the current top-level `fulltext.md` as a compatibility mirror, but make its content come from the new render pipeline. Add a dedicated OCR health builder that evaluates parse quality separately from `ocr_status`, then surface that report through `ocr doctor` and compatibility metadata snapshots.

**Tech Stack:** Python, pytest, existing PaperForge OCR worker, JSON/JSONL artifacts, Obsidian-flavored Markdown generation, current doctor/status framework

---

## File Structure

Phase 3 should establish these focused units:

- `paperforge/worker/ocr_render.py`
  - New module for rendering `render/fulltext.md` from structured artifacts and mirroring compatibility `fulltext.md`.
- `paperforge/worker/ocr_health.py`
  - New module for building `health/ocr_health.json` and compact quality summaries.
- `paperforge/worker/ocr.py`
  - Keep orchestration entrypoint.
  - Modify only to call render and health builders after Phase 2 artifacts exist.
- `paperforge/worker/status.py`
  - Extend doctor/status integration to surface OCR structured health without redefining `ocr_status`.
- `paperforge/worker/asset_index.py`
  - Only touch if Phase 3 needs to expose the new health summary into existing index payloads.
- `tests/test_ocr_render_v2.py`
  - New unit tests for structured fulltext rendering.
- `tests/test_ocr_health.py`
  - New unit tests for OCR quality metrics and overall verdicts.
- `tests/test_ocr.py`
  - Extend end-to-end OCR postprocess expectations for render and health artifacts.
- `tests/test_ocr_rendering.py`
  - Keep compatibility assertions against old invariants that must survive the renderer swap.
- `tests/test_ocr_doctor.py`
  - Extend OCR doctor coverage for Phase 3 structured health.
- `tests/test_status.py`
  - Extend doctor/status integration expectations if needed.

Rationale:

- Phase 2 already created the object layer; Phase 3 should make the renderer consume it instead of continuing to render directly from raw OCR page blocks.
- Health belongs in its own module so quality scoring does not leak into `ocr_status`.
- Sync/version drift automation still stays out of scope until Phase 4.

### Task 1: Lock The Structured Fulltext Render Contract In Tests

**Files:**
- Create: `tests/test_ocr_render_v2.py`
- Modify: `tests/test_ocr.py`
- Reference: `docs/superpowers/specs/2026-06-04-ocr-structured-pipeline-design.md`

- [ ] **Step 1: Write the failing renderer unit tests**

```python
from __future__ import annotations


def test_render_fulltext_uses_resolved_metadata_and_object_links(tmp_path) -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {"page": 1, "block_id": "p1_b1", "role": "abstract_heading", "text": "Abstract", "render_default": True},
        {"page": 1, "block_id": "p1_b2", "role": "abstract_body", "text": "Background text.", "render_default": True},
        {"page": 2, "block_id": "p2_b1", "role": "section_heading", "text": "1 Introduction", "render_default": True},
        {"page": 2, "block_id": "p2_b2", "role": "body_paragraph", "text": "Intro body.", "render_default": True},
    ]
    resolved_metadata = {
        "title": {"value": "Paper Title"},
        "authors": {"value": ["Alice", "Bob"]},
        "journal": {"value": "Journal A"},
        "year": {"value": 2024},
        "doi": {"value": "10.1000/xyz"},
    }
    figure_inventory = {
        "matched_figures": [{"figure_id": "figure_001", "confidence": 0.91, "flags": []}],
    }
    table_inventory = {
        "tables": [{"table_id": "table_001", "has_asset": True}],
    }

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata=resolved_metadata,
        figure_inventory=figure_inventory,
        table_inventory=table_inventory,
    )

    assert "# Paper Title" in md
    assert "Authors:" in md
    assert "## 1 Introduction" in md or "### 1 Introduction" in md
    assert "![[figures/figure_001.md]]" in md or "![[render/figures/figure_001.md]]" in md
```

- [ ] **Step 2: Add an end-to-end render artifact assertion**

Extend `tests/test_ocr.py`:

```python
assert (ocr_dir / "render" / "fulltext.md").exists()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_render_v2.py tests/test_ocr.py -k "render_fulltext or render/fulltext" -q`
Expected: FAIL because the structured renderer does not exist yet.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ocr_render_v2.py tests/test_ocr.py
git commit -m "test: lock OCR phase3 renderer contract"
```

### Task 2: Implement Structured Fulltext Renderer

**Files:**
- Create: `paperforge/worker/ocr_render.py`
- Modify: `paperforge/worker/ocr.py`
- Test: `tests/test_ocr_render_v2.py`

- [ ] **Step 1: Implement `render_fulltext_markdown()`**

Target shape:

```python
def render_fulltext_markdown(
    *,
    structured_blocks: list[dict],
    resolved_metadata: dict,
    figure_inventory: dict,
    table_inventory: dict,
) -> str:
    ...
```

Rules for Phase 3:

- render title and metadata from `resolved_metadata.json`
- render abstract section from structured blocks when present
- render body headings and paragraphs from `blocks.structured.jsonl`
- render figures and tables via object links/callouts, not raw inline OCR table text
- respect `render_default`
- preserve page markers if practical and stable

- [ ] **Step 2: Implement a small compatibility mirror helper**

Add:

```python
def write_render_outputs(render_root: Path, compat_fulltext: Path, markdown: str) -> None:
    ...
```

This should write:

- `render/fulltext.md`
- top-level compatibility `fulltext.md`

With identical content in Phase 3.

- [ ] **Step 3: Integrate renderer into OCR postprocess**

In `paperforge/worker/ocr.py`, stop treating `merged_parts` from direct page rendering as the primary output.

Phase 3 sequencing should become:

1. raw/source/block artifacts
2. metadata resolution
3. figure/table inventories
4. object markdown/assets
5. structured renderer output
6. health report

If a compatibility fallback is still needed, keep it behind a narrow guard, not as the default path.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_render_v2.py tests/test_ocr.py -k "render_fulltext or render/fulltext" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_render.py paperforge/worker/ocr.py tests/test_ocr_render_v2.py tests/test_ocr.py
git commit -m "feat: render OCR fulltext from structured artifacts"
```

### Task 3: Preserve Critical Rendering Regressions Through The Renderer Swap

**Files:**
- Modify: `tests/test_ocr_rendering.py`
- Modify: `tests/test_ocr_integration_fixtures.py`
- Modify: `paperforge/worker/ocr_render.py`

- [ ] **Step 1: Re-express existing critical invariants against the new render output**

Add tests or adapt existing ones so the new structured renderer still preserves:

- abstract before introduction
- heading retention
- references not mixed with trailing policy sections
- figure/table links appearing in reasonable sequence

- [ ] **Step 2: Add one fixture-backed render regression**

Use an existing real OCR fixture to assert:

- headings present
- body flow intact
- at least one figure or table link rendered when object artifacts exist

- [ ] **Step 3: Run tests to verify the renderer swap does not regress old behavior**

Run: `python -m pytest tests/test_ocr_rendering.py tests/test_ocr_integration_fixtures.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_ocr_rendering.py tests/test_ocr_integration_fixtures.py paperforge/worker/ocr_render.py
git commit -m "test: preserve OCR render regressions through structured renderer"
```

### Task 4: Lock OCR Health Contract In Tests

**Files:**
- Create: `tests/test_ocr_health.py`
- Modify: `tests/test_ocr.py`

- [ ] **Step 1: Write the failing health builder tests**

```python
from __future__ import annotations


def test_health_report_is_independent_from_ocr_status() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    structured_blocks = [
        {"role": "section_heading", "text": "1 Introduction"},
        {"role": "body_paragraph", "text": "Body"},
        {"role": "figure_caption", "text": "Figure 1. Example"},
    ]
    figure_inventory = {
        "matched_figures": [],
        "unmatched_legends": [{"text": "Figure 1. Example"}],
        "unmatched_assets": [],
    }
    table_inventory = {
        "tables": [],
        "unmatched_captions": [],
        "unmatched_assets": [],
    }

    report = build_ocr_health(
        page_count=3,
        raw_blocks_count=20,
        structured_blocks=structured_blocks,
        figure_inventory=figure_inventory,
        table_inventory=table_inventory,
    )

    assert report["page_count"] == 3
    assert report["figure_caption_count"] == 1
    assert report["overall"] in {"yellow", "red"}
```

- [ ] **Step 2: Add an end-to-end health artifact assertion**

Extend `tests/test_ocr.py`:

```python
assert (ocr_dir / "health" / "ocr_health.json").exists()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_health.py tests/test_ocr.py -k ocr_health -q`
Expected: FAIL because the health builder does not exist yet.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ocr_health.py tests/test_ocr.py
git commit -m "test: lock OCR phase3 health contract"
```

### Task 5: Implement OCR Quality Health Report

**Files:**
- Create: `paperforge/worker/ocr_health.py`
- Modify: `paperforge/worker/ocr.py`
- Test: `tests/test_ocr_health.py`

- [ ] **Step 1: Implement `build_ocr_health()`**

Include at least:

- `page_count`
- `blocks_count`
- `section_heading_count`
- `abstract_found`
- `references_found`
- `figure_caption_count`
- `figure_asset_count`
- `table_caption_count`
- `table_asset_count`
- `media_without_caption_count`
- `caption_without_media_count`
- `empty_table_count`
- `frontmatter_quality`
- `overall`

Phase 3 only needs rule-based quality metrics, not ML-based scoring.

- [ ] **Step 2: Implement `write_ocr_health()`**

Write `health/ocr_health.json` and return a compact summary object suitable for `meta.json` mirroring.

- [ ] **Step 3: Integrate health generation into OCR postprocess**

After render output is written:

- build the health report
- write `health/ocr_health.json`
- mirror a compact health snapshot into `meta.json` if useful

Do not change `ocr_status` based on structured quality.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_health.py tests/test_ocr.py -k ocr_health -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_health.py paperforge/worker/ocr.py tests/test_ocr_health.py tests/test_ocr.py
git commit -m "feat: add OCR structured health report"
```

### Task 6: Surface Structured OCR Health Through Doctor And Status

**Files:**
- Modify: `paperforge/worker/status.py`
- Modify: `paperforge/commands/ocr.py`
- Modify: `tests/test_ocr_doctor.py`
- Modify: `tests/test_status.py`

- [ ] **Step 1: Add failing doctor/status tests**

Extend `tests/test_ocr_doctor.py` and `tests/test_status.py` so doctor/status can read and report Phase 3 health signals.

Examples:

```python
def test_doctor_reads_structured_ocr_health(tmp_path):
    ...
    assert "OCR Health" in output
    assert "figure" in output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_doctor.py tests/test_status.py -q`
Expected: FAIL because doctor does not surface the structured health report yet.

- [ ] **Step 3: Implement doctor/status integration**

Keep this narrow:

- if `health/ocr_health.json` exists, read it
- include summary in OCR doctor / status output
- do not replace existing environment/config diagnostics
- do not redefine existing asset-index health semantics yet

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_doctor.py tests/test_status.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/status.py paperforge/commands/ocr.py tests/test_ocr_doctor.py tests/test_status.py
git commit -m "feat: surface OCR structured health in doctor and status"
```

### Task 7: Preserve Compatibility Contracts While Moving To Render V2

**Files:**
- Modify: `tests/test_selection_sync_pdf.py`
- Modify: `tests/e2e/test_ocr_e2e.py`
- Modify: `tests/test_ocr_redo.py`
- Modify: `paperforge/worker/sync.py`

- [ ] **Step 1: Add compatibility guard tests**

Ensure that after Phase 3:

- top-level `fulltext.md` still exists
- `fulltext_md_path` still points to compatibility `fulltext.md`
- `ocr redo` still rebuilds the new render and health artifacts
- sync still consumes `meta.json` without requiring `render/fulltext.md`

- [ ] **Step 2: Run tests to establish the baseline**

Run: `python -m pytest tests/test_selection_sync_pdf.py tests/e2e/test_ocr_e2e.py tests/test_ocr_redo.py -q`
Expected: PASS before and after Phase 3 changes.

- [ ] **Step 3: Keep Phase 3 additive from the perspective of external consumers**

Do not:

- repoint `fulltext_md_path` to `render/fulltext.md`
- introduce sync-triggered render rebuilds
- add raw-version upgrade UI logic

Phase 3 only swaps the producer of the compatibility file.

- [ ] **Step 4: Run compatibility tests to verify they still pass**

Run: `python -m pytest tests/test_selection_sync_pdf.py tests/e2e/test_ocr_e2e.py tests/test_ocr_redo.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/sync.py tests/test_selection_sync_pdf.py tests/e2e/test_ocr_e2e.py tests/test_ocr_redo.py
git commit -m "refactor: preserve OCR compatibility through renderer v2"
```

### Task 8: Final Verification For Phase 3

**Files:**
- Verify only

- [ ] **Step 1: Run Phase 3 focused suite**

Run: `python -m pytest tests/test_ocr_render_v2.py tests/test_ocr_health.py tests/test_ocr.py tests/test_ocr_rendering.py tests/test_ocr_integration_fixtures.py tests/test_ocr_doctor.py tests/test_status.py tests/test_selection_sync_pdf.py tests/e2e/test_ocr_e2e.py tests/test_ocr_redo.py -q`
Expected: PASS

- [ ] **Step 2: Run earlier-phase regression suites**

Run: `python -m pytest tests/test_ocr_artifacts.py tests/test_ocr_blocks.py tests/test_ocr_metadata.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_objects.py tests/test_ocr_roles.py tests/test_ocr_state_machine.py tests/test_sync.py tests/test_context.py -q`
Expected: PASS

- [ ] **Step 3: Inspect diff scope**

Run: `git diff -- paperforge/worker docs/superpowers tests`
Expected: changes are limited to renderer, health, and doctor/status wiring; no sync drift automation or search/evidence work yet.

- [ ] **Step 4: Commit verification-only fixes if needed**

```bash
git add -A
git commit -m "test: finalize OCR structured pipeline phase3 renderer and health"
```

## Risks To Watch During Execution

1. Do not let the renderer fall back into direct raw-block inference.
2. Keep `fulltext.md` compatibility stable even though its producer changes.
3. Keep tables image-first; do not reintroduce raw OCR table text into the main body.
4. Keep `ocr_status` separate from structured quality verdicts.
5. Do not start sync-driven rebuild automation here; that is Phase 4.
6. Treat the current uncommitted `paperforge/worker/ocr_objects.py` change carefully during implementation if it remains in the worktree.

