# OCR Object Rebuild PDF Reuse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make derived rebuild avoid repeated PDF work and repeated intermediate I/O without changing cache-first semantics, markdown output, structured output semantics, or artifact layout.

**Architecture:** Keep the change as a low-risk rebuild de-dup pass. Reuse a lazily-opened shared PDF handle inside `paperforge/worker/ocr_objects.py` without violating cache-first behavior, remove the rebuild-only extra structured-block write/read cycle in `paperforge/worker/ocr_rebuild.py` by adding an in-memory frontmatter-candidate seam in `paperforge/worker/ocr_metadata.py`, and eliminate one safe O(n²) heading-prefix lookup in `paperforge/worker/ocr_render.py`. Lock the behavior down with focused tests and record the fix in `PROJECT-MANAGEMENT.md`.

**Tech Stack:** Python 3.10+, PyMuPDF (`fitz`), Pillow (`PIL`), pytest.

---

## File Structure

- Modify: `paperforge/worker/ocr_objects.py`
  Purpose: add lazy shared-PDF reuse while preserving cache-first crop semantics and current markdown/output behavior.
- Modify: `paperforge/worker/ocr_rebuild.py`
  Purpose: remove unconditional rebuild-only span-adjacent intermediate structured write/read churn by writing structured blocks once at the final state.
- Modify: `paperforge/worker/ocr_metadata.py`
  Purpose: add an in-memory frontmatter-candidate extraction seam so rebuild does not need to write JSONL before metadata resolution.
- Modify: `paperforge/worker/ocr_render.py`
  Purpose: replace one repeated heading-block scan with direct `bid_to_block` lookup.
- Modify: `tests/test_ocr_objects.py`
  Purpose: add regression coverage for PDF-open reuse, same-page render reuse, cache-first no-open behavior, and markdown survival on PDF-open failure.
- Modify: `tests/test_ocr_render.py`
  Purpose: add a focused regression that preserves heading-prefix behavior after the direct lookup simplification.
- Modify: `tests/test_ocr_metadata.py`
  Purpose: add parity coverage for file-based vs in-memory frontmatter candidate extraction.
- Modify: `tests/test_ocr_rebuild.py`
  Purpose: add a rebuild-focused regression that proves structured blocks are written once and metadata candidates come from in-memory blocks.
- Modify: `PROJECT-MANAGEMENT.md`
  Purpose: log the completed performance fix, root cause, result, and test status per repo policy.

## Task 1: Lock Down Cache-First and Shared-PDF Behavior with Tests

**Files:**
- Modify: `tests/test_ocr_objects.py`
- Test: `tests/test_ocr_objects.py`

- [ ] **Step 1: Write the failing cache-first no-open test**

Add this test near the existing `_crop_asset_from_pdf` tests:

```python
def test_crop_asset_uses_cached_page_without_opening_pdf(tmp_path: Path, monkeypatch) -> None:
    from PIL import Image

    from paperforge.worker.ocr_objects import _crop_asset_from_pdf

    page_cache_dir = tmp_path / "pages"
    page_cache_dir.mkdir()
    Image.new("RGB", (600, 800), "white").save(page_cache_dir / "page_001.jpg")

    called = {"count": 0}

    def _boom(*args, **kwargs):
        called["count"] += 1
        raise AssertionError("fitz.open should not be called on cache hit")

    monkeypatch.setattr("fitz.open", _boom)

    dst = tmp_path / "crop.jpg"
    ok = _crop_asset_from_pdf(
        None,
        1,
        [50, 50, 100, 100],
        dst,
        page_cache_dir=page_cache_dir,
    )

    assert ok is True
    assert called["count"] == 0
```

- [ ] **Step 2: Run the cache-first test to verify it fails for the right reason**

Run: `pytest tests/test_ocr_objects.py::test_crop_asset_uses_cached_page_without_opening_pdf -v`

Expected: PASS now and after implementation. This is a guardrail for helper-level cache-first semantics.

- [ ] **Step 3: Write the failing cross-page open-once batch test**

Add this test below the cache-first seam tests:

```python
def test_extract_objects_opens_pdf_once_across_multiple_cache_miss_pages(tmp_path: Path, monkeypatch) -> None:
    import fitz

    from paperforge.worker.ocr_objects import extract_and_write_objects

    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    for _ in range(3):
        page = doc.new_page(width=300, height=400)
        page.draw_rect(fitz.Rect(25, 25, 75, 75), color=(1, 0, 0), fill=(1, 0, 0))
    doc.save(pdf_path)
    doc.close()

    figure_inventory = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "text": "Figure 1.",
                "page": 1,
                "cluster_bbox": [50, 50, 150, 150],
                "matched_assets": [],
            },
            {
                "figure_id": "figure_002",
                "text": "Figure 2.",
                "page": 2,
                "cluster_bbox": [160, 50, 260, 150],
                "matched_assets": [],
            },
            {
                "figure_id": "figure_003",
                "text": "Figure 3.",
                "page": 3,
                "cluster_bbox": [80, 80, 200, 200],
                "matched_assets": [],
            },
        ],
        "unmatched_assets": [],
        "rejected_legends": [],
        "figure_legends": [],
        "figure_assets": [],
        "official_figure_count": 3,
        "unresolved_clusters": [],
    }

    open_count = {"count": 0}
    real_open = fitz.open

    def _counting_open(*args, **kwargs):
        open_count["count"] += 1
        return real_open(*args, **kwargs)

    monkeypatch.setattr("fitz.open", _counting_open)

    extract_and_write_objects(
        pdf_path=pdf_path,
        figure_inventory=figure_inventory,
        table_inventory={"tables": [], "unmatched_assets": []},
        asset_root=tmp_path / "assets",
        render_root=tmp_path / "render",
        page_dimensions_by_page={1: (600, 800), 2: (600, 800), 3: (600, 800)},
    )

    assert open_count["count"] == 1
```

- [ ] **Step 4: Run the cross-page open-once test to verify it fails correctly**

Run: `pytest tests/test_ocr_objects.py::test_extract_objects_opens_pdf_once_across_multiple_cache_miss_pages -v`

Expected: FAIL because the current implementation opens the PDF once per cache-miss page, not once per batch.

- [ ] **Step 5: Write the failing same-page render-once test**

Add this test using a fresh page cache and two same-page crop candidates:

```python
def test_extract_objects_renders_same_page_once_for_multiple_crops(tmp_path: Path, monkeypatch) -> None:
    import fitz

    from paperforge.worker.ocr_objects import extract_and_write_objects

    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page(width=300, height=400)
    page.draw_rect(fitz.Rect(25, 25, 75, 75), color=(1, 0, 0), fill=(1, 0, 0))
    doc.save(pdf_path)
    doc.close()

    figure_inventory = {
        "matched_figures": [
            {"figure_id": "figure_001", "text": "Figure 1.", "page": 1, "cluster_bbox": [50, 50, 150, 150], "matched_assets": []},
            {"figure_id": "figure_002", "text": "Figure 2.", "page": 1, "cluster_bbox": [160, 50, 260, 150], "matched_assets": []},
        ],
        "unmatched_assets": [],
        "rejected_legends": [],
        "figure_legends": [],
        "figure_assets": [],
        "official_figure_count": 2,
        "unresolved_clusters": [],
    }

    render_calls = {"count": 0}

    from paperforge.worker import ocr as ocr_module
    real_render = ocr_module.render_pdf_page_cached

    def _counting_render(*args, **kwargs):
        render_calls["count"] += 1
        return real_render(*args, **kwargs)

    monkeypatch.setattr(ocr_module, "render_pdf_page_cached", _counting_render)

    extract_and_write_objects(
        pdf_path=pdf_path,
        figure_inventory=figure_inventory,
        table_inventory={"tables": [], "unmatched_assets": []},
        asset_root=tmp_path / "assets",
        render_root=tmp_path / "render",
        page_dimensions_by_page={1: (600, 800)},
    )

    assert render_calls["count"] == 1
```

- [ ] **Step 6: Run the render-once test to verify it fails correctly**

Run: `pytest tests/test_ocr_objects.py::test_extract_objects_renders_same_page_once_for_multiple_crops -v`

Expected: PASS before and after implementation. This is a guardrail for existing same-page cache reuse, not the primary failing seam.

- [ ] **Step 7: Write the batch-level cache-hit no-eager-open test**

Add this test to prevent the caller from eagerly opening the shared PDF before the helper's cache-first branch:

```python
def test_extract_objects_cache_hit_does_not_eager_open_shared_pdf(tmp_path: Path, monkeypatch) -> None:
    import fitz
    from PIL import Image

    from paperforge.worker.ocr_objects import extract_and_write_objects

    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page(width=300, height=400)
    page.draw_rect(fitz.Rect(25, 25, 75, 75), color=(1, 0, 0), fill=(1, 0, 0))
    doc.save(pdf_path)
    doc.close()

    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()
    Image.new("RGB", (600, 800), "white").save(pages_dir / "page_001.jpg")

    def _boom(*args, **kwargs):
        raise AssertionError("fitz.open should not be called when page cache already exists")

    monkeypatch.setattr("fitz.open", _boom)

    figure_inventory = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "text": "Figure 1.",
                "page": 1,
                "cluster_bbox": [50, 50, 150, 150],
                "matched_assets": [],
            }
        ],
        "unmatched_assets": [],
        "rejected_legends": [],
        "figure_legends": [],
        "figure_assets": [],
        "official_figure_count": 1,
        "unresolved_clusters": [],
    }

    extract_and_write_objects(
        pdf_path=pdf_path,
        figure_inventory=figure_inventory,
        table_inventory={"tables": [], "unmatched_assets": []},
        asset_root=tmp_path / "assets",
        render_root=tmp_path / "render",
        page_dimensions_by_page={1: (600, 800)},
    )

    assert (tmp_path / "assets" / "figures" / "figure_001.jpg").exists()
```

- [ ] **Step 8: Run the batch-level cache-hit no-eager-open test to verify it fails correctly**

Run: `pytest tests/test_ocr_objects.py::test_extract_objects_cache_hit_does_not_eager_open_shared_pdf -v`

Expected: PASS now; keep it as the guardrail that prevents an eager-open regression in the caller.

- [ ] **Step 9: Write the markdown-survives-open-failure guardrail test**

Add this test to prove markdown emission survives PDF-open failure:

```python
def test_extract_objects_pdf_open_failure_still_writes_markdown(tmp_path: Path, monkeypatch) -> None:
    from paperforge.worker.ocr_objects import extract_and_write_objects

    figure_inventory = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "text": "Figure 1. Example.",
                "page": 1,
                "cluster_bbox": [50, 50, 150, 150],
                "matched_assets": [],
            }
        ],
        "unmatched_assets": [],
        "rejected_legends": [],
        "figure_legends": [],
        "figure_assets": [],
        "official_figure_count": 1,
        "unresolved_clusters": [],
    }

    pdf_path.touch()

    def _boom(*args, **kwargs):
        raise RuntimeError("cannot open pdf")

    monkeypatch.setattr("fitz.open", _boom)

    extract_and_write_objects(
        pdf_path=pdf_path,
        figure_inventory=figure_inventory,
        table_inventory={"tables": [], "unmatched_assets": []},
        asset_root=tmp_path / "assets",
        render_root=tmp_path / "render",
        page_dimensions_by_page={1: (600, 800)},
    )

    note = tmp_path / "render" / "figures" / "figure_001.md"
    assert note.exists()
```

- [ ] **Step 10: Run the markdown-survives-open-failure test to verify behavior**

Run: `pytest tests/test_ocr_objects.py::test_extract_objects_pdf_open_failure_still_writes_markdown -v`

Expected: FAIL only if the test setup is wrong; otherwise it should already pass and prove existing markdown emission is preserved. If it passes immediately, keep it as a guardrail and note that this is expected existing behavior rather than a new failing seam.

- [ ] **Step 11: Run the focused OCR object seam to capture the red/green baseline**

Run: `pytest tests/test_ocr_objects.py -v`

Expected: the new cross-page open-once test fails; the cache-first, same-page render, and markdown-survival tests act as guardrails and should pass.

## Task 2: Implement Lazy Shared-PDF Reuse in `ocr_objects.py`

**Files:**
- Modify: `paperforge/worker/ocr_objects.py`
- Test: `tests/test_ocr_objects.py`

- [ ] **Step 1: Change `_crop_asset_from_pdf()` signature minimally**

Update the function signature to accept nullable `pdf_path` and optional keyword-only `pdf_doc`:

```python
def _crop_asset_from_pdf(
    pdf_path: Path | None,
    page_num: int,
    bbox: list[float],
    dst: Path,
    *,
    page_width: int = 0,
    page_height: int = 0,
    page_cache_dir: Path | None = None,
    pdf_doc: Any | None = None,
) -> bool:
```

- [ ] **Step 2: Preserve stale-destination cleanup and cache-first lookup before any PDF work**

Make sure the first block of the function still behaves like this:

```python
if dst.exists():
    with contextlib.suppress(Exception):
        dst.unlink()

cached_page_image = _find_cached_page_image(page_cache_dir, page_num)
if cached_page_image is not None:
    from paperforge.worker.ocr import crop_block_asset
    return crop_block_asset(cached_page_image, [int(v) for v in bbox], dst)
```

Do not move any PDF open logic above this block.

- [ ] **Step 3: Add local/shared PDF ownership logic inside `_crop_asset_from_pdf()`**

Implement the ownership pattern like this:

```python
created_doc = None
doc = pdf_doc

if doc is None:
    if pdf_path is None or not pdf_path.exists():
        return False
    import fitz
    created_doc = fitz.open(str(pdf_path))
    doc = created_doc

try:
    ...
finally:
    if created_doc is not None:
        doc.close()
```

This is the critical rule that prevents the helper from closing the shared batch document.

- [ ] **Step 4: Reuse `doc` in the OCR-dimension render path**

Replace the current open/close logic in the page-cache render branch with shared-document reuse:

```python
from paperforge.worker.ocr import crop_block_asset, render_pdf_page_cached

page_image_path = page_cache_dir / f"page_{page_num:03d}.jpg"
rendered = render_pdf_page_cached(
    doc,
    page_num,
    target_width=page_width,
    target_height=page_height,
    destination=page_image_path,
)
if not rendered:
    return False
return crop_block_asset(rendered, [int(v) for v in bbox], dst)
```

There should be no `fitz.open()` inside this branch after the change.

- [ ] **Step 5: Reuse `doc` in the fallback direct-PDF-clip path**

Replace the current fallback branch with shared-document reuse:

```python
import fitz

page = doc[page_num - 1]
rect = fitz.Rect(*bbox)
pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
dst.parent.mkdir(parents=True, exist_ok=True)
pix.save(str(dst))
return True
```

This branch must not reopen the PDF when `pdf_doc` is already supplied.

- [ ] **Step 6: Add a lazy shared-document opener with failed-open memoization inside `extract_and_write_objects()`**

Near `_page_dims()`, add a local helper like this:

```python
shared_pdf_doc: Any | None = None
shared_pdf_open_attempted = False

def _get_shared_pdf_doc() -> Any | None:
    nonlocal shared_pdf_doc, shared_pdf_open_attempted
    if shared_pdf_doc is not None:
        return shared_pdf_doc
    if shared_pdf_open_attempted:
        return None
    if pdf_path is None or not pdf_path.exists():
        shared_pdf_open_attempted = True
        return None
    shared_pdf_open_attempted = True
    try:
        import fitz
        shared_pdf_doc = fitz.open(str(pdf_path))
    except Exception:
        return None
    return shared_pdf_doc
```

This helper must not run unless a crop call actually needs the PDF.

- [ ] **Step 7: Add a lazy provider seam to `_crop_asset_from_pdf()` instead of eager caller-side open**

Do not pass `pdf_doc=_get_shared_pdf_doc()` directly from the caller.

That would evaluate the provider before `_crop_asset_from_pdf()` gets a chance to hit the cached-page-image fast path.

Extend the helper signature with a provider seam:

```python
def _crop_asset_from_pdf(
    pdf_path: Path | None,
    page_num: int,
    bbox: list[float],
    dst: Path,
    *,
    page_width: int = 0,
    page_height: int = 0,
    page_cache_dir: Path | None = None,
    pdf_doc: Any | None = None,
    pdf_doc_provider: Callable[[], Any | None] | None = None,
) -> bool:
```

Inside the helper, preserve this order:

1. stale destination cleanup,
2. cached page image lookup,
3. only on cache miss, resolve `doc` from `pdf_doc` or `pdf_doc_provider`.

If `pdf_doc_provider` is supplied and returns `None`, `_crop_asset_from_pdf()` must return `False` instead of falling back to a fresh local `fitz.open()`. Local open fallback remains only for direct helper callers that provided neither `pdf_doc` nor `pdf_doc_provider`.

- [ ] **Step 8: Thread the provider into every crop call site**

For each `_crop_asset_from_pdf(...)` call in `extract_and_write_objects()`, add `pdf_doc_provider=_get_shared_pdf_doc`.

That includes:

- matched figure `cluster_bbox` crops,
- matched figure `matched_assets` fallback crops,
- unresolved cluster crops,
- figure orphan crops,
- table asset crops,
- table orphan crops.

Use the same pattern everywhere:

```python
was_cropped = _crop_asset_from_pdf(
    pdf_path,
    page,
    cluster_bbox,
    asset_path_abs,
    page_width=page_width,
    page_height=page_height,
    page_cache_dir=page_cache_dir,
    pdf_doc_provider=_get_shared_pdf_doc,
)
```

- [ ] **Step 9: Close the shared document exactly once at batch end**

Wrap the crop-emission portion of `extract_and_write_objects()` in a `try/finally` that closes the shared document only if it was opened:

```python
try:
    ... existing object loops ...
finally:
    if shared_pdf_doc is not None:
        with contextlib.suppress(Exception):
            shared_pdf_doc.close()
```

- [ ] **Step 10: Run the targeted OCR object tests**

Run:

`pytest tests/test_ocr_objects.py::test_crop_asset_uses_cached_page_without_opening_pdf -v`

`pytest tests/test_ocr_objects.py::test_extract_objects_opens_pdf_once_across_multiple_cache_miss_pages -v`

`pytest tests/test_ocr_objects.py::test_extract_objects_renders_same_page_once_for_multiple_crops -v`

`pytest tests/test_ocr_objects.py::test_extract_objects_cache_hit_does_not_eager_open_shared_pdf -v`

`pytest tests/test_ocr_objects.py::test_extract_objects_pdf_open_failure_still_writes_markdown -v`

Expected: PASS for all five.

- [ ] **Step 11: Run the whole OCR objects test file**

Run: `pytest tests/test_ocr_objects.py -v`

Expected: PASS with no regressions in existing object markdown/crop behavior.

## Task 3: Record the Fix and Verify End-to-End Expectations

**Files:**
- Modify: `PROJECT-MANAGEMENT.md`
- Test: `tests/test_ocr_objects.py`

- [ ] **Step 1: Add a new project-management entry for the fix**

Append a new section near the current 2026-06-22 entries using this format:

```md
### 12.15 OCR object rebuild PDF reuse (2026-06-22)

**Problem:** Derived rebuild spent most of its time in `extract_and_write_objects()` because `_crop_asset_from_pdf()` reopened the source PDF and repeated page-render setup across many crops.

**Root cause:** PDF ownership lived inside the single-crop helper instead of the batch-level object extraction loop, so matched figures, clusters, orphans, and tables all paid repeated document-open cost.

**Fix:** Reused one lazily-opened shared PDF handle per `extract_and_write_objects()` call, kept cached-page-image-first semantics unchanged, and reused the shared handle in both the OCR-dimension render path and fallback direct-PDF-clip path.

**Result:** Object extraction keeps the same outputs while avoiding repeated `fitz.open()` calls and repeated same-page setup work.

**Test status:** Added focused regression coverage in `tests/test_ocr_objects.py` for open-once, same-page render reuse, cache-first no-open behavior, and markdown survival on PDF-open failure.
```

- [ ] **Step 2: Update remaining-known-issues only if needed**

Check whether this fix resolves any explicitly listed rebuild-performance issue. If not, leave the current remaining-issues lists unchanged.

- [ ] **Step 3: Run the focused verification command one more time**

Run: `pytest tests/test_ocr_objects.py -v`

Expected: PASS.

- [ ] **Step 4: Inspect the final diff before handoff**

Run: `git diff -- paperforge/worker/ocr_objects.py tests/test_ocr_objects.py PROJECT-MANAGEMENT.md docs/superpowers/specs/2026-06-22-ocr-object-rebuild-pdf-reuse-design.md docs/superpowers/plans/2026-06-22-ocr-object-rebuild-pdf-reuse-plan.md`

Expected: diff limited to the planned files, with no accidental behavior changes outside `ocr_objects.py`.

## Task 4: Remove the Extra Structured-Block Write/Read Cycle in Rebuild

**Files:**
- Modify: `paperforge/worker/ocr_metadata.py`
- Modify: `paperforge/worker/ocr_rebuild.py`
- Test: `tests/test_ocr_metadata.py`
- Test: `tests/test_ocr_rebuild.py`

- [ ] **Step 1: Write the failing metadata parity test for in-memory frontmatter extraction**

Add a focused test in `tests/test_ocr_metadata.py`:

```python
def test_extract_frontmatter_candidates_from_blocks_matches_file_based(tmp_path: Path) -> None:
    import json

    from paperforge.worker.ocr_metadata import (
        extract_frontmatter_candidates,
        extract_frontmatter_candidates_from_blocks,
    )

    structured = [
        {"role": "paper_title", "text": "Example Title"},
        {"role": "authors", "text": "Ada Lovelace, Alan Turing"},
        {"role": "doi", "text": "10.1000/example"},
    ]

    path = tmp_path / "blocks.structured.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in structured) + "\n", encoding="utf-8")

    assert extract_frontmatter_candidates_from_blocks(structured) == extract_frontmatter_candidates(path)
```

- [ ] **Step 2: Run the parity test to verify it fails correctly**

Run: `pytest tests/test_ocr_metadata.py::test_extract_frontmatter_candidates_from_blocks_matches_file_based -v`

Expected: FAIL because `extract_frontmatter_candidates_from_blocks` does not exist yet.

- [ ] **Step 3: Write the rebuild orchestration test with a minimal valid fixture**

Add a focused rebuild test in `tests/test_ocr_rebuild.py`:

```python
def test_run_derived_rebuild_writes_structured_blocks_once(tmp_path: Path, monkeypatch) -> None:
    import json

    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    key = "TESTKEY1"
    paper_root = tmp_path / "System" / "PaperForge" / "ocr" / key
    (paper_root / "canonical").mkdir(parents=True)
    (paper_root / "raw").mkdir(parents=True)
    (paper_root / "structure").mkdir(parents=True)

    (paper_root / "canonical" / "blocks.raw.jsonl").write_text(
        json.dumps(
            {
                "paper_id": key,
                "page": 1,
                "block_id": "p1_b1",
                "raw_label": "text",
                "raw_order": 0,
                "text": "Example text",
                "bbox": [10, 10, 100, 40],
                "page_width": 600,
                "page_height": 800,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (paper_root / "raw" / "source_metadata.json").write_text(
        json.dumps({"title": "Example Title"}),
        encoding="utf-8",
    )
    (paper_root / "meta.json").write_text(json.dumps({"source_pdf": ""}), encoding="utf-8")

    writes = {"count": 0}

    def _counting_write(*args, **kwargs):
        writes["count"] += 1

    monkeypatch.setattr("paperforge.worker.ocr_blocks.write_structured_blocks_jsonl", _counting_write)
    monkeypatch.setattr(
        "paperforge.worker.ocr_metadata.extract_frontmatter_candidates_from_blocks",
        lambda structured: {"title": "Example Title", "authors_text": None, "doi_candidates": []},
    )

    result = run_derived_rebuild_for_keys(tmp_path, [key])

    assert result["rebuild_count"] == 1
    assert writes["count"] == 1
```

- [ ] **Step 4: Run the rebuild orchestration test to verify it fails correctly**

Run: `pytest tests/test_ocr_rebuild.py::test_run_derived_rebuild_writes_structured_blocks_once -v`

Expected: FAIL because rebuild currently writes structured blocks twice and still reads frontmatter candidates from the file path seam.

- [ ] **Step 5: Add the in-memory extraction helper in `ocr_metadata.py`**

Implement the new helper by lifting the current per-block logic out of the file-reading wrapper:

```python
def extract_frontmatter_candidates_from_blocks(structured_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: dict[str, Any] = {
        "title": None,
        "authors_text": None,
        "doi_candidates": [],
    }

    for block in structured_blocks:
        role = block.get("role", "")
        text = block.get("text", "").strip()
        ...

    return candidates
```

- [ ] **Step 6: Convert the existing file-based function into a wrapper**

Refactor `extract_frontmatter_candidates()` to keep its public file-path contract while delegating to the in-memory helper:

```python
def extract_frontmatter_candidates(blocks_structured_path: Path) -> dict[str, Any]:
    if not blocks_structured_path.exists():
        return {"title": None, "authors_text": None, "doi_candidates": []}

    structured_blocks: list[dict[str, Any]] = []
    with blocks_structured_path.open("r", encoding="utf-8") as f:
        for line in f:
            ...
            structured_blocks.append(block)

    return extract_frontmatter_candidates_from_blocks(structured_blocks)
```

- [ ] **Step 7: Switch rebuild to use the in-memory frontmatter candidates**

In `paperforge/worker/ocr_rebuild.py`, replace:

```python
write_structured_blocks_jsonl(artifacts.blocks_structured, structured)
...
frontmatter_candidates = extract_frontmatter_candidates(artifacts.blocks_structured)
```

with:

```python
frontmatter_candidates = extract_frontmatter_candidates_from_blocks(structured)
```

and do not write structured blocks yet.

- [ ] **Step 8: Keep only the final structured-block write after figure/table write-backs**

Preserve this final write and delete the earlier intermediate one:

```python
# Re-persist structured blocks with writeback roles (table_html, figure_asset)
write_structured_blocks_jsonl(artifacts.blocks_structured, structured)
```

This must remain the only rebuild-time write of `blocks.structured.jsonl`.

- [ ] **Step 9: Run the focused metadata and rebuild tests**

Run:

`pytest tests/test_ocr_metadata.py::test_extract_frontmatter_candidates_from_blocks_matches_file_based -v`

`pytest tests/test_ocr_rebuild.py::test_run_derived_rebuild_writes_structured_blocks_once -v`

Expected: PASS.

## Task 5: Remove the Heading Prefix O(n²) Lookup

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_render.py`

- [ ] **Step 1: Write the heading-prefix parity test that exercises the size-group branch**

Add a focused render test:

```python
def test_render_fulltext_markdown_preserves_role_heading_prefixes() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured = [
        {
            "page": 1,
            "role": "subsection_heading",
            "text": "Methods",
            "span_metadata": {"size": 12},
            "span_signature": {"bold": True},
            "block_id": "p1_b1",
        },
        {
            "page": 1,
            "role": "body_paragraph",
            "text": "Body text.",
            "block_id": "p1_b2",
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory={"tables": [], "unmatched_assets": []},
        page_count=1,
        document_structure={},
        reader_payload={},
    )

    assert "### Methods" in md
```

- [ ] **Step 2: Run the heading-prefix test to establish the guardrail**

Run: `pytest tests/test_ocr_render.py::test_render_fulltext_markdown_preserves_role_heading_prefixes -v`

Expected: PASS now; keep it as the guardrail before changing the lookup implementation.

- [ ] **Step 3: Replace the repeated scan with direct `bid_to_block` lookup**

In `paperforge/worker/ocr_render.py`, replace:

```python
for bid in block_heading_prefix:
    b = None
    for blk in structured_blocks:
        if id(blk) == bid:
            b = blk
            break
```

with:

```python
for bid in block_heading_prefix:
    b = bid_to_block.get(bid)
```

- [ ] **Step 4: Run the focused heading-prefix test again**

Run: `pytest tests/test_ocr_render.py::test_render_fulltext_markdown_preserves_role_heading_prefixes -v`

Expected: PASS.

## Task 6: Update Project Management Entry for the Full Low-Risk De-dup Pass

**Files:**
- Modify: `PROJECT-MANAGEMENT.md`
- Test: `tests/test_ocr_objects.py`
- Test: `tests/test_ocr_metadata.py`
- Test: `tests/test_ocr_rebuild.py`
- Test: `tests/test_ocr_render.py`

- [ ] **Step 1: Replace the project-management entry text so it covers all four low-risk optimizations**

Use this updated entry text instead of the narrower object-only wording:

```md
### 12.15 OCR rebuild low-risk de-dup pass (2026-06-22)

**Problem:** Derived rebuild spent avoidable time reopening PDFs during object extraction, writing structured blocks twice, reading frontmatter candidates back from a just-written JSONL file, and rescanning structured blocks during heading-prefix override in render.

**Root cause:** Expensive resources and intermediate artifacts were owned below the correct batch boundary, so rebuild paid repeated PDF, render, write, and lookup costs even when the final outputs did not require them.

**Fix:** Reused one lazily-opened shared PDF handle per `extract_and_write_objects()` call, preserved cache-first crop semantics, switched rebuild metadata-candidate extraction to an in-memory helper, removed the intermediate structured JSONL write, and replaced the render heading-prefix rescan with direct `bid_to_block` lookup.

**Result:** Rebuild preserves the same output semantics while removing repeated PDF opens, repeated same-page setup work, one intermediate structured write/read cycle, and one safe O(n²) render lookup.

**Test status:** Added focused regression coverage for cache-first no-open behavior, open-once reuse, same-page render reuse, markdown survival on PDF-open failure, in-memory/file-based frontmatter-candidate parity, single structured-block write in rebuild, and heading-prefix parity in render.
```

- [ ] **Step 2: Run the focused verification commands**

Run:

`pytest tests/test_ocr_objects.py -v`

`pytest tests/test_ocr_metadata.py -v`

`pytest tests/test_ocr_rebuild.py -v`

`pytest tests/test_ocr_render.py -v`

Expected: PASS.

- [ ] **Step 3: Inspect the final diff before handoff**

Run: `git diff -- paperforge/worker/ocr_objects.py paperforge/worker/ocr_rebuild.py paperforge/worker/ocr_metadata.py paperforge/worker/ocr_render.py tests/test_ocr_objects.py tests/test_ocr_metadata.py tests/test_ocr_rebuild.py tests/test_ocr_render.py PROJECT-MANAGEMENT.md docs/superpowers/specs/2026-06-22-ocr-object-rebuild-pdf-reuse-design.md docs/superpowers/plans/2026-06-22-ocr-object-rebuild-pdf-reuse-plan.md`

Expected: diff limited to the planned files, with no accidental behavior changes outside the low-risk rebuild de-dup slice.

## Self-Review

- Spec coverage: the plan implements lazy shared-PDF reuse, cache-first preservation, fallback-path reuse, PDF-open-failure survivability, unchanged markdown behavior, single final structured-block write, in-memory frontmatter candidate extraction, and the direct heading-prefix lookup simplification.
- Placeholder scan: no `TBD`, `TODO`, or “similar to task N” shortcuts remain.
- Type consistency: plan uses `pdf_path: Path | None` and `pdf_doc: Any | None` consistently across test and implementation steps, and it uses `extract_frontmatter_candidates_from_blocks(structured)` as the in-memory rebuild seam.
