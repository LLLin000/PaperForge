# OCR Structured Pipeline Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce the Phase 1 OCR structured pipeline foundation so PaperForge can preserve raw OCR truth, emit canonical and structured block artifacts, and record raw/derived versions without breaking existing `paperforge ocr` and `paperforge ocr redo` behavior.

**Architecture:** Keep the current `paperforge ocr` and `paperforge ocr redo` entrypoints intact while extracting the first durable intermediate layers out of `paperforge.worker.ocr`. Phase 1 does not replace the renderer yet; it adds a deterministic artifact pipeline beside the existing compatibility outputs so later phases can switch metadata, figure/table objects, and renderer behavior onto stable structured inputs.

**Tech Stack:** Python, pytest, existing PaperForge OCR worker, JSON/JSONL artifacts, Pillow/PyMuPDF-compatible current OCR pipeline

---

## File Structure

Phase 1 should establish these focused units:

- `paperforge/worker/ocr_artifacts.py`
  - New module for OCR artifact paths, raw/derived version payload builders, and artifact write/read helpers.
- `paperforge/worker/ocr_blocks.py`
  - New module for deterministic rebuild from `json/result.json` into `canonical/blocks.raw.jsonl` and `structure/blocks.structured.jsonl`.
- `paperforge/worker/ocr.py`
  - Keep as orchestration entrypoint.
  - Modify only to call the new artifact/block builders during `postprocess_ocr_result()` and to preserve compatibility outputs.
- `paperforge/worker/sync.py`
  - Keep backward compatibility with enriched `meta.json`; do not add derived-drift behavior yet.
- `tests/test_ocr_artifacts.py`
  - New unit tests for artifact paths and version payloads.
- `tests/test_ocr_blocks.py`
  - New unit tests for raw and structured block emission.
- `tests/test_ocr.py`
  - Extend end-to-end OCR postprocess expectations for new artifact files.
- `tests/test_selection_sync_pdf.py`
  - Guard sync compatibility against enriched `meta.json`.
- `tests/e2e/test_ocr_e2e.py`
  - Extend fixture-level OCR artifact expectations if needed.

Rationale:

- `ocr.py` is already too broad; Phase 1 should add new focused modules instead of deepening that file.
- The plan intentionally does not introduce metadata resolver, figure inventory, table inventory, or renderer v2 yet.
- The fastest safe milestone is: raw truth preserved, stable block artifacts emitted, versions recorded, old outputs still usable.

### Task 1: Lock Phase 1 Artifact Contract In Tests

**Files:**
- Create: `tests/test_ocr_artifacts.py`
- Modify: `tests/test_ocr.py`
- Reference: `docs/superpowers/specs/2026-06-04-ocr-structured-pipeline-design.md`

- [ ] **Step 1: Write the failing artifact contract tests**

```python
from __future__ import annotations

from pathlib import Path


def test_phase1_artifact_layout_is_paper_local(tmp_path: Path) -> None:
    from paperforge.worker.ocr_artifacts import artifact_paths_for_key

    vault = tmp_path / "vault"
    vault.mkdir()

    paths = artifact_paths_for_key(vault, "ABCD1234")

    assert paths.paper_root.as_posix().endswith("/ocr/ABCD1234")
    assert paths.raw_meta.as_posix().endswith("/ocr/ABCD1234/raw/raw_meta.json")
    assert paths.source_metadata.as_posix().endswith("/ocr/ABCD1234/raw/source_metadata.json")
    assert paths.blocks_raw.as_posix().endswith("/ocr/ABCD1234/canonical/blocks.raw.jsonl")
    assert paths.blocks_structured.as_posix().endswith("/ocr/ABCD1234/structure/blocks.structured.jsonl")


def test_raw_and_derived_version_payloads_have_separate_namespaces() -> None:
    from paperforge.worker.ocr_artifacts import build_version_payload

    payload = build_version_payload(
        pdf_fingerprint="sha256:abc",
        result_json_hash="sha256:def",
        ocr_model="PaddleOCR-VL-1.6",
    )

    assert "raw_version" in payload
    assert "derived_version" in payload
    assert payload["raw_version"]["ocr_model"] == "PaddleOCR-VL-1.6"
    assert "renderer_version" in payload["derived_version"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_artifacts.py -q`
Expected: FAIL because `paperforge.worker.ocr_artifacts` does not exist yet.

- [ ] **Step 3: Add a failing postprocess expectation to existing OCR tests**

Add one targeted test to `tests/test_ocr.py` asserting that a successful OCR postprocess creates:

- `raw/raw_meta.json`
- `raw/source_metadata.json`
- `canonical/blocks.raw.jsonl`
- `structure/blocks.structured.jsonl`

Minimal shape:

```python
def test_postprocess_writes_phase1_artifacts(tmp_path: Path) -> None:
    ...
    assert (ocr_dir / "raw" / "raw_meta.json").exists()
    assert (ocr_dir / "raw" / "source_metadata.json").exists()
    assert (ocr_dir / "canonical" / "blocks.raw.jsonl").exists()
    assert (ocr_dir / "structure" / "blocks.structured.jsonl").exists()
```

- [ ] **Step 4: Run the targeted test to verify it fails**

Run: `python -m pytest tests/test_ocr.py -k phase1_artifacts -q`
Expected: FAIL because the artifacts are not written yet.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ocr_artifacts.py tests/test_ocr.py
git commit -m "test: lock OCR phase1 artifact contract"
```

### Task 2: Add Artifact Path And Version Helpers

**Files:**
- Create: `paperforge/worker/ocr_artifacts.py`
- Modify: `paperforge/worker/ocr.py`
- Test: `tests/test_ocr_artifacts.py`

- [ ] **Step 1: Implement `ocr_artifacts.py` with a small typed path container**

Include:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OCRArtifactPaths:
    paper_root: Path
    meta_json: Path
    result_json: Path
    compat_fulltext: Path
    raw_meta: Path
    source_metadata: Path
    blocks_raw: Path
    blocks_structured: Path


def artifact_paths_for_key(vault: Path, zotero_key: str) -> OCRArtifactPaths:
    ...
```
```

- [ ] **Step 2: Add version payload helpers**

Implement in the same module:

```python
def build_version_payload(
    *,
    pdf_fingerprint: str,
    result_json_hash: str,
    ocr_model: str,
) -> dict:
    return {
        "raw_version": {
            "ocr_provider": "PaddleOCR",
            "ocr_model": ocr_model,
            "ocr_raw_schema_version": "1.0.0",
            "pdf_fingerprint": pdf_fingerprint,
            "result_json_hash": result_json_hash,
        },
        "derived_version": {
            "canonical_block_version": "1.0.0",
            "structure_version": "1.0.0",
            "metadata_resolver_version": "0.0.0-phase1",
            "asset_extractor_version": "0.0.0-phase1",
            "renderer_version": "1.0.0-compat",
            "doctor_version": "0.0.0-phase1",
        },
    }
```

- [ ] **Step 3: Add hashing helpers only for what Phase 1 needs**

Add minimal helpers for:

- PDF fingerprint from `source_pdf` if readable
- `result.json` hash after write

Keep this narrow. Do not add generic artifact digests for every future layer yet.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_artifacts.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_artifacts.py paperforge/worker/ocr.py tests/test_ocr_artifacts.py
git commit -m "feat: add OCR artifact path and version helpers"
```

### Task 3: Emit Raw Metadata And Source Metadata During OCR Postprocess

**Files:**
- Modify: `paperforge/worker/ocr.py`
- Modify: `tests/test_ocr.py`
- Modify: `tests/e2e/test_ocr_e2e.py`

- [ ] **Step 1: Write or extend the failing metadata artifact test**

Add assertions that `postprocess_ocr_result()` writes:

- `raw/raw_meta.json`
- `raw/source_metadata.json`

And that `meta.json` gains:

- `raw_version`
- `derived_version`

Example:

```python
assert meta["raw_version"]["ocr_model"] == "PaddleOCR-VL-1.6"
assert "renderer_version" in meta["derived_version"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr.py tests/e2e/test_ocr_e2e.py -k "raw_meta or source_metadata or raw_version" -q`
Expected: FAIL because those files/fields do not exist yet.

- [ ] **Step 3: Implement minimal raw metadata emission in `postprocess_ocr_result()`**

Update `paperforge/worker/ocr.py` so that after writing `json/result.json` it also writes:

- `raw/raw_meta.json`
  - provider/model
  - created/updated timestamps
  - PDF fingerprint
  - result hash
- `raw/source_metadata.json`
  - `zotero_key`
  - `source_pdf`
  - fields copied from current row/meta when available

Also mirror `raw_version` and `derived_version` into compatibility `meta.json`.

Do not attempt full Zotero metadata resolver logic yet. Phase 1 only preserves source-side fields when already available.

- [ ] **Step 4: Keep old fields intact**

When updating `meta.json`, preserve current compatibility fields:

- `ocr_status`
- `ocr_provider`
- `page_count`
- `markdown_path`
- `json_path`
- `fulltext_md_path`

Do not rename or delete them in Phase 1.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr.py tests/e2e/test_ocr_e2e.py -k "raw_meta or source_metadata or raw_version" -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr.py tests/test_ocr.py tests/e2e/test_ocr_e2e.py
git commit -m "feat: persist OCR raw metadata and version payloads"
```

### Task 4: Build And Persist Canonical Raw Blocks

**Files:**
- Create: `paperforge/worker/ocr_blocks.py`
- Modify: `paperforge/worker/ocr.py`
- Create: `tests/test_ocr_blocks.py`
- Modify: `tests/test_ocr_integration_fixtures.py`

- [ ] **Step 1: Write the failing raw block emission tests**

Add unit tests for flattening `result.json` into canonical block records:

```python
from __future__ import annotations


def test_build_raw_blocks_preserves_every_block() -> None:
    from paperforge.worker.ocr_blocks import build_raw_blocks_for_page

    result = {
        "prunedResult": {
            "width": 1200,
            "height": 1600,
            "parsing_res_list": [
                {"block_id": 1, "block_label": "text", "block_order": 0, "block_bbox": [1, 2, 3, 4], "block_content": "A"},
                {"block_id": 2, "block_label": "header", "block_order": 1, "block_bbox": [5, 6, 7, 8], "block_content": "B"},
            ],
        }
    }

    rows = build_raw_blocks_for_page("KEY001", 1, result)

    assert len(rows) == 2
    assert rows[0]["paper_id"] == "KEY001"
    assert rows[1]["raw_label"] == "header"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_blocks.py -q`
Expected: FAIL because `ocr_blocks.py` does not exist yet.

- [ ] **Step 3: Implement raw block builders**

In `paperforge/worker/ocr_blocks.py`, add:

- `build_raw_blocks_for_page()`
- `build_raw_blocks_for_result_lines()`
- `write_raw_blocks_jsonl()`

Design rules:

- preserve all blocks
- preserve raw order and raw label
- preserve page width/height
- normalize missing text to `""`
- generate stable Phase 1 fallback `block_id` values when OCR block id is missing

- [ ] **Step 4: Wire raw block emission into `postprocess_ocr_result()`**

After writing `json/result.json`, generate and write `canonical/blocks.raw.jsonl`.

Do not change existing `render_page_blocks()` behavior yet.

- [ ] **Step 5: Extend integration fixture tests**

Add a fixture-backed test in `tests/test_ocr_integration_fixtures.py` that:

- loads a real `result.json`
- writes `blocks.raw.jsonl`
- verifies the output row count is non-zero

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_blocks.py tests/test_ocr_integration_fixtures.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add paperforge/worker/ocr_blocks.py paperforge/worker/ocr.py tests/test_ocr_blocks.py tests/test_ocr_integration_fixtures.py
git commit -m "feat: emit canonical OCR raw blocks"
```

### Task 5: Build And Persist Structured Blocks

**Files:**
- Modify: `paperforge/worker/ocr_blocks.py`
- Modify: `paperforge/worker/ocr_roles.py`
- Modify: `paperforge/worker/ocr.py`
- Modify: `tests/test_ocr_blocks.py`
- Modify: `tests/test_ocr_roles.py`

- [ ] **Step 1: Write the failing structured block tests**

Extend block tests with structured emission expectations:

```python
def test_build_structured_blocks_preserves_noise_and_confidence() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "p1_b1",
            "raw_label": "header",
            "raw_order": 0,
            "bbox": [1, 2, 3, 4],
            "text": "Header",
            "page_width": 1200,
            "page_height": 1600,
        }
    ]

    rows = build_structured_blocks(raw_blocks)

    assert rows[0]["role"] in {"noise", "page_header"}
    assert "role_confidence" in rows[0]
    assert "evidence" in rows[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_blocks.py tests/test_ocr_roles.py -q`
Expected: FAIL because structured builders do not exist yet.

- [ ] **Step 3: Implement Phase 1 structured block builder**

Add to `paperforge/worker/ocr_blocks.py`:

- `build_structured_blocks(raw_blocks: list[dict]) -> list[dict]`
- `write_structured_blocks_jsonl()`

Use `assign_block_role()` from `ocr_roles.py` as the initial classifier, but emit a richer record:

```python
{
    "paper_id": "...",
    "page": 1,
    "block_id": "p1_b1",
    "raw_label": "text",
    "raw_order": 0,
    "bbox": [..],
    "text": "...",
    "role": "body_paragraph",
    "role_confidence": 0.6,
    "evidence": ["default body_paragraph for text label"],
    "render_default": True,
    "index_default": True,
}
```

Phase 1 only needs basic `render_default` / `index_default` rules, for example:

- noise-like roles -> both false
- body/reference/caption/heading -> both true
- unknown -> render false, index true

- [ ] **Step 4: Write structured artifacts during postprocess**

After `blocks.raw.jsonl`, generate `structure/blocks.structured.jsonl`.

- [ ] **Step 5: Tighten role tests only where Phase 1 requires it**

Do not attempt the full future taxonomy yet. Update tests only for roles that Phase 1 really emits consistently:

- heading
- body paragraph
- figure caption
- table caption
- media asset
- reference item
- noise / unknown

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_blocks.py tests/test_ocr_roles.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add paperforge/worker/ocr_blocks.py paperforge/worker/ocr_roles.py paperforge/worker/ocr.py tests/test_ocr_blocks.py tests/test_ocr_roles.py
git commit -m "feat: emit OCR structured block artifacts"
```

### Task 6: Preserve Compatibility Outputs While Wiring Phase 1 Artifacts

**Files:**
- Modify: `paperforge/worker/ocr.py`
- Modify: `tests/test_ocr_rendering.py`
- Modify: `tests/test_selection_sync_pdf.py`
- Modify: `tests/test_context.py`

- [ ] **Step 1: Write failing compatibility assertions**

Add or extend tests ensuring that after Phase 1:

- top-level `fulltext.md` still exists
- `json/result.json` still exists
- `meta.json` old fields still exist
- sync can still read `ocr_status` and `fulltext_md_path`

Add a narrow test to `tests/test_selection_sync_pdf.py`:

```python
def test_sync_reads_enriched_meta_without_breaking_ocr_status(...):
    ...
    assert entry["ocr_status"] == "done"
```

- [ ] **Step 2: Run tests to verify they fail if compatibility breaks**

Run: `python -m pytest tests/test_selection_sync_pdf.py tests/test_context.py tests/test_ocr_rendering.py -q`
Expected: PASS before code changes, then stay PASS after code changes.

- [ ] **Step 3: Make `postprocess_ocr_result()` write both compatibility and Phase 1 artifacts**

Compatibility behavior must remain:

- `json/result.json`
- top-level `fulltext.md`
- current return tuple `(page_num, markdown_path, json_path, fulltext_md_path)`

Do not redirect current consumers to `render/fulltext.md` in Phase 1.
If desired, `render/` may be created later in another phase, but Phase 1 should keep the existing output path stable.

- [ ] **Step 4: Keep `sync.py` tolerant of enriched `meta.json`**

Do not add version-drift behavior yet. Only ensure that enriched `meta.json` does not affect:

- `validate_ocr_meta()`
- sync index generation
- frontmatter note generation

- [ ] **Step 5: Run compatibility tests**

Run: `python -m pytest tests/test_selection_sync_pdf.py tests/test_context.py tests/test_ocr_rendering.py tests/test_ocr.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr.py paperforge/worker/sync.py tests/test_selection_sync_pdf.py tests/test_context.py tests/test_ocr_rendering.py tests/test_ocr.py
git commit -m "refactor: preserve OCR compatibility while adding phase1 artifacts"
```

### Task 7: Verify Redo Rebuilds The New Phase 1 Artifacts End-To-End

**Files:**
- Modify: `tests/test_ocr_redo.py`
- Modify: `tests/test_ocr.py`
- Modify: `paperforge/worker/ocr.py`

- [ ] **Step 1: Write the failing redo artifact test**

Add a redo-specific test asserting that a successful `ocr redo` run leaves the paper with:

- fresh `json/result.json`
- fresh `raw/raw_meta.json`
- fresh `canonical/blocks.raw.jsonl`
- fresh `structure/blocks.structured.jsonl`
- `ocr_redo: false` only after success

Example:

```python
def test_ocr_redo_rebuilds_phase1_artifacts(tmp_path):
    ...
    assert (ocr_dir / "canonical" / "blocks.raw.jsonl").exists()
    assert (ocr_dir / "structure" / "blocks.structured.jsonl").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_redo.py tests/test_ocr.py -k phase1 -q`
Expected: FAIL until redo writes the new artifacts as part of the rerun path.

- [ ] **Step 3: Ensure redo path uses the same postprocess pipeline**

Do not add redo-specific artifact writers.
The fix should be that `ocr_redo_papers()` continues to rerun normal OCR, and normal OCR now emits the new Phase 1 artifacts automatically.

- [ ] **Step 4: Run redo tests to verify they pass**

Run: `python -m pytest tests/test_ocr_redo.py tests/test_ocr.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr.py tests/test_ocr_redo.py tests/test_ocr.py
git commit -m "test: cover OCR redo rebuilding phase1 artifacts"
```

### Task 8: Final Verification For Phase 1

**Files:**
- Verify only

- [ ] **Step 1: Run focused OCR suite**

Run: `python -m pytest tests/test_ocr_artifacts.py tests/test_ocr_blocks.py tests/test_ocr.py tests/test_ocr_redo.py tests/test_ocr_roles.py tests/test_ocr_rendering.py tests/test_ocr_integration_fixtures.py tests/test_selection_sync_pdf.py tests/e2e/test_ocr_e2e.py -q`
Expected: PASS

- [ ] **Step 2: Run state-machine regression coverage**

Run: `python -m pytest tests/test_ocr_state_machine.py -q`
Expected: PASS

- [ ] **Step 3: Run sync compatibility coverage**

Run: `python -m pytest tests/test_sync.py tests/test_context.py tests/test_status.py -q`
Expected: PASS

- [ ] **Step 4: Inspect generated diff scope**

Run: `git diff -- paperforge/worker docs/superpowers tests`
Expected: changes are limited to Phase 1 artifact foundation, tests, and no premature metadata/figure/table/render-v2 work.

- [ ] **Step 5: Commit verification-only fixes if needed**

```bash
git add -A
git commit -m "test: finalize OCR structured pipeline phase1 foundation"
```

## Risks To Watch During Execution

1. Do not let Phase 1 drift into metadata resolver or figure/table object work.
2. Do not make `fulltext.md` consumers depend on `blocks.structured.jsonl` yet.
3. Do not redefine redo semantics; it must remain full-paper rerun.
4. Keep `meta.json` additive in Phase 1.
5. Preserve every OCR block in raw and structured artifacts, including noise.
6. Avoid premature sync-triggered rebuild logic; that belongs to Phase 4.

