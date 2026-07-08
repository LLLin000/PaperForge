# OCR Object Rebuild PDF Reuse Design

> Date: 2026-06-22
> Status: proposed
> Scope: reduce `paperforge ocr rebuild` time by reusing PDF and rendered page resources inside object extraction only

## Goal

Reduce the hottest part of derived rebuild without changing OCR semantics, inventory logic, or rebuild surface area.

The target is the object-emission path in `paperforge/worker/ocr_objects.py`, which dominates rebuild time on real papers because it repeatedly:

1. opens the source PDF,
2. renders the same page image multiple times,
3. crops multiple objects from the same page through repeated setup work.

This design applies the lowest-risk optimization:

- open the PDF once per `extract_and_write_objects()` call,
- render each page at most once per `extract_and_write_objects()` call,
- reuse those resources for every figure/table/orphan crop on that page.

## Non-Goals

This design does not:

- change figure or table matching logic,
- change span backfill behavior,
- change rebuild command UX,
- introduce concurrency,
- add a new dependency,
- add a new cross-module session abstraction,
- redesign artifact cache layout.

## Measured Motivation

Real-vault profiling on paper `SAN9AYVR` in a temp sandbox showed approximately `12.0s` total derived rebuild time with the following top stages:

- `extract_and_write_objects()`: `7.357s`
- `backfill_span_metadata_from_pdf()`: `2.713s`
- `build_structured_blocks()`: `1.327s`

`extract_and_write_objects()` alone accounted for about `61%` of measured rebuild time.

The sampled paper also had enough object density to make repeated PDF/page work expensive:

- `31` matched figures,
- `16` unmatched figure assets,
- `6` tables,
- `8` unmatched table assets,
- object crops spread across `38` pages.

The optimization target is therefore justified by measured runtime, not guesswork.

## Current Problem

Today `_crop_asset_from_pdf()` performs useful reuse only at the page-image file level.

It does not guarantee reuse of the open PDF document itself.

In the current implementation:

- `extract_and_write_objects()` loops over many objects,
- each object may call `_crop_asset_from_pdf()`,
- `_crop_asset_from_pdf()` may open the PDF internally,
- page rendering setup is repeated through lower-level fallback paths.

This means the expensive resources are managed too low in the stack.

The caller knows the whole crop batch. The helper only sees one crop.

That is the mismatch this design fixes.

## Design Principles

### 1. Reuse resources at the batch boundary

The correct reuse scope is one `extract_and_write_objects()` call, because that call owns the full batch of figure/table/orphan crops.

### 2. Keep the public entrypoint stable

`extract_and_write_objects()` is already called from both rebuild and OCR postprocess paths. The top-level function signature should stay stable so the optimization remains a local implementation detail.

### 3. No speculative architecture

Do not introduce a reusable `PDFSession`, `ObjectExtractionContext`, or similar abstraction. The existing function boundary is enough.

### 4. Preserve output identity

Rendered crops, markdown files, and asset paths must remain identical in meaning to the current implementation. This is a performance fix, not a behavior change.

## Option Review

### Option A: Local reuse inside `ocr_objects.py` (recommended)

Keep the current call graph, but let `extract_and_write_objects()` open one `fitz.Document` and pass it downward for reuse.

Pros:

- smallest diff,
- no command/API changes,
- low regression risk,
- directly attacks the measured hotspot.

Cons:

- does not help span backfill,
- resource reuse remains local to object extraction only.

### Option B: Broader cache-lifecycle cleanup in `ocr_objects.py`

In addition to A, explicitly reorganize cache ownership and cleanup semantics for the page cache directory.

Pros:

- slightly clearer internal structure,
- better future readability.

Cons:

- larger diff,
- more churn than needed for the first performance pass.

### Option C: Cross-module rebuild session context

Push shared PDF/session state upward into rebuild and OCR pipelines.

Pros:

- larger theoretical optimization surface.

Cons:

- over-engineered for the current goal,
- spreads performance plumbing into unrelated call sites,
- violates the requested minimal-risk scope.

## Recommended Design

Use Option A only.

The change should stay entirely inside `paperforge/worker/ocr_objects.py` plus focused tests.

### Surface 1: Reuse one open PDF per object-extraction batch

`extract_and_write_objects()` will:

1. keep cached-page-image crops independent from PDF availability,
2. open the PDF at most once with `fitz.open(str(pdf_path))` when a crop path actually needs the document,
3. keep that document alive for the full crop batch,
4. close it once after all crops finish.

This document handle becomes an internal batch-scoped resource.

No caller API change is required.

Opening the batch PDF is therefore best-effort and lazy enough not to be required for cached-page crops.

### Surface 2: Let `_crop_asset_from_pdf()` accept an already-open document

`_crop_asset_from_pdf()` should accept an optional `pdf_doc` parameter.

Behavior:

- if a cached page image exists, crop from cache first and do not require the PDF,
- if `pdf_doc` is provided, reuse it,
- if not provided, preserve current fallback behavior.

This keeps the helper backward-compatible for tests and any future direct use, while allowing the hot path to stop reopening the file.

Ownership rule:

- if `pdf_doc` is provided, `_crop_asset_from_pdf()` must not close it,
- only `extract_and_write_objects()` owns and closes the batch-scoped shared document,
- if the helper opens its own document for backward compatibility, it must close only that locally-created document.

### Surface 3: Keep page-image reuse at the current cache layer

The current page cache model is directionally correct and must remain cache-first:

- render page image once,
- write `page_NNN.jpg`,
- crop many objects from that image.

The design keeps this behavior, but makes its benefit reliable by pairing it with a reused open PDF handle.

For one `extract_and_write_objects()` call:

- the first crop on page `N` may render `page_NNN.jpg`,
- later crops on page `N` must reuse the cached page image,
- later crops must not reopen the PDF just to reach the same page again,
- if `page_NNN.jpg` already exists, crop must succeed from cache without opening or requiring the PDF.

### Surface 4: Do not move logic into callers

`ocr_rebuild.py` and `ocr.py` should continue to call `extract_and_write_objects()` exactly as they do today.

This optimization belongs in the object extraction module because:

- the module already owns crop execution,
- it already owns page cache usage,
- moving resource management upward would create wider coupling for no immediate gain.

## Detailed Data Flow

### Current flow

```text
extract_and_write_objects
  -> object loop
    -> _crop_asset_from_pdf
      -> maybe open PDF
      -> maybe render page image
      -> crop object
```

### Proposed flow

```text
extract_and_write_objects
  -> prepare lazy shared PDF opener
  -> object loop
    -> _crop_asset_from_pdf(pdf_doc=get_shared_doc_if_needed())
      -> reuse existing page cache image if present without opening PDF
      -> else open/reuse shared_doc and render page image once
      -> crop object
  -> close shared_doc once if opened
```

The control flow stays simple. The only real change is where the expensive resource is owned.

## Implementation Contract

The implementation must preserve the following behavior exactly:

1. `_crop_asset_from_pdf()` gains optional keyword-only `pdf_doc`.
2. Existing destination-crop deletion semantics remain unchanged.
3. Cached page image lookup remains the first crop source after stale destination cleanup.
4. If a cached page image exists, `_crop_asset_from_pdf()` must not open the PDF.
5. If `pdf_doc` is provided, the helper must use it and must not close it.
6. If the helper opens its own document for backward compatibility, it must close only that locally-created document.
7. Both the OCR-page-dimension render path and the fallback direct-PDF-clip path must reuse `pdf_doc` when available.
8. `extract_and_write_objects()` may open the PDF at most once per call and must close it exactly once if opened.
9. PDF open failure must not abort markdown emission or cached-page crop attempts.
10. Existing output filenames, asset relpaths, markdown content, and page-cache layout must remain unchanged.

This contract exists to prevent a performance optimization from accidentally becoming a cache-semantics change.

## Implementation Notes

- The shared PDF handle should be opened lazily, not unconditionally at function entry.
- `_crop_asset_from_pdf()` should accept `pdf_path: Path | None` so cached-page crops remain possible even when no PDF path is available.
- Tests that assert `fitz.open` is called once must use a fresh page cache with no pre-existing `page_NNN` image.
- Tests that assert same-page render reuse must use multiple crop candidates on the same page, valid page dimensions, and no pre-existing cached page image.

## Error Handling

This design must preserve existing fault tolerance.

Rules:

- if a cached page image exists, crop from cache must remain possible even when the PDF is missing, damaged, or cannot be opened,
- if the PDF cannot be opened and no cached page image exists, object extraction should continue to produce markdown notes exactly as today, with crop failure isolated to that asset,
- one failed crop must not abort the full batch,
- PDF close must happen reliably even when an intermediate crop fails,
- cached page-image preference remains unchanged,
- figure/table markdown rendering behavior must remain unchanged, including today's missing-image-link behavior when a crop fails.

The performance change must not reduce rebuild survivability.

## Testing Strategy

This is a behavior-preserving optimization, so tests should prove resource reuse rather than new output semantics.

### Required regression tests

Add focused tests in `tests/test_ocr_objects.py` that prove both document reuse and cache semantics.

Required coverage:

1. `test_extract_objects_opens_pdf_once_for_multiple_crops`
2. `test_extract_objects_renders_same_page_once_for_multiple_crops`
3. `test_crop_asset_uses_cached_page_without_opening_pdf`
4. `test_extract_objects_pdf_open_failure_still_writes_markdown`

Preferred seams:

- monkeypatch `fitz.open` to prove batch-scoped document reuse,
- monkeypatch `paperforge.worker.ocr.render_pdf_page_cached` to prove same-page render reuse,
- assert cached-page crops do not require `fitz.open`,
- assert markdown emission survives document-open failure.

Test preconditions:

- `test_extract_objects_opens_pdf_once_for_multiple_crops` must use a cache miss path with multiple crops in one batch and a fresh page cache directory.
- `test_extract_objects_renders_same_page_once_for_multiple_crops` must use at least two crop candidates on the same page, valid `page_dimensions_by_page`, and no pre-existing cached page image.
- `test_crop_asset_uses_cached_page_without_opening_pdf` must explicitly exercise the cache-hit path, including the case where `pdf_path` is unavailable.

### Existing behavior checks to preserve

Current tests already cover:

- crop with OCR page dimensions,
- preference for cached page images,
- object markdown emission behavior.

These remain the output guardrails after the performance change.

## Expected Impact

This design is expected to reduce the `extract_and_write_objects()` portion of rebuild time substantially, especially on papers with many objects spread across many pages.

This design does not promise a full rebuild-time collapse because:

- span backfill remains untouched,
- structured rebuild remains untouched,
- file writes remain untouched.

Reasonable expectation:

- object extraction becomes materially faster,
- total rebuild time drops noticeably on image-heavy papers,
- correctness risk remains low because no ownership or render logic changes.

## Ponytail Dependency Review

No new package should be added for this optimization.

The repo already has the right tools installed:

- `PyMuPDF` (`pymupdf`, imported as `fitz`) for PDF open, page access, and page rendering,
- `Pillow` (`PIL`) for image crop and save.

That means the lazy path is:

- reuse `fitz.Document` better,
- reuse page renders better,
- avoid writing any custom cache framework,
- avoid introducing concurrency libraries or new PDF/image packages.

### What should not be added

- no `pdf2image`,
- no `opencv`,
- no `joblib`,
- no custom session/cache class unless this local optimization proves insufficient.

### Why existing packages are enough

`fitz` already supports:

- opening one document once,
- reading many pages from the same handle,
- rendering a page pixmap at chosen scale.

`Pillow` already supports:

- reopening one cached page image,
- cropping multiple bounding boxes,
- saving crops to current artifact layout.

The current problem is not missing capability. It is under-reuse of capability already present.

## Implementation Boundary

If this design is later implemented, the intended file touch set is minimal:

- `paperforge/worker/ocr_objects.py`
- `tests/test_ocr_objects.py`
- `PROJECT-MANAGEMENT.md`

Nothing else is required for the first pass.

## Open Questions

There are no unresolved design questions inside the chosen scope.

The remaining larger opportunities are intentionally deferred:

- conditional span backfill,
- split text-only rebuild mode,
- broader rebuild-session reuse across modules.

Those belong to later designs, not this one.
