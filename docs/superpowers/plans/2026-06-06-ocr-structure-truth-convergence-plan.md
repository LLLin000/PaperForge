# OCR Structure Truth Convergence Plan

Date: 2026-06-06  
Scope: `paperforge/worker/ocr_pdf_spans.py`, `ocr_blocks.py`, `ocr_document.py`, `ocr_roles.py`, `ocr_profiles.py`, `ocr_render.py`, `ocr_rebuild.py`, downstream tests

## Goal

收掉当前 structured OCR pipeline 里最危险的三条分叉，让全文结构、span 样式、最终 `fulltext.md` 使用同一套真相：

1. `span_metadata` 必须基于正确坐标系提取
2. `DocumentStructure` 必须成为唯一的全文结构真相
3. `role/profile` 的构建顺序必须和结构归一化顺序一致

这份计划不重做 pipeline。它从当前代码状态出发，收敛现有实现。

## Current Root Causes

### 1. Span extraction likely uses the wrong coordinate system

Current behavior:

- `ocr_pdf_spans.extract_pdf_spans_for_block()` directly uses OCR block bbox as `page.get_text("rawdict", clip=rect)` PDF coordinates.
- OCR block bbox is derived from rendered page image coordinates, not guaranteed PDF coordinates.
- We already hit the same coordinate mismatch in figure/table cropping earlier.

Impact:

- `span_metadata` may be extracted from the wrong PDF region
- style-based role inference becomes noisy or silently empty
- all later span-profile logic rests on an unstable base

### 2. Document structure is analyzed twice, in two different layers

Current behavior:

- `ocr_blocks.build_structured_blocks()`:
  - seeds roles
  - calls `analyze_document_structure()`
  - calls `rescue_roles_with_document_context()`
- `ocr_render._order_tail_blocks()`:
  - calls `analyze_document_structure()` again
  - does additional `_promote_tail_body_candidates()`
  - does additional `_assign_tail_spread_ownership()`

Impact:

- structure layer and render layer can diverge
- `fulltext.md` may not reflect the same truth used by metadata/index/health/inventory
- debugging remains difficult because render still mutates structural semantics

### 3. Profile construction happens before structural normalization settles

Current behavior:

- `ocr_blocks.build_structured_blocks()`:
  - first-pass roles
  - builds `role_profiles`
  - only then runs `analyze_document_structure()`
- `analyze_document_structure()` currently normalizes some roles in-place:
  - boundary/container backmatter normalization
  - body/frontmatter noise to backmatter body in boundary zone

Impact:

- `role_span_profiles.json` represents pre-normalized roles
- rescue logic compares blocks against profiles that are partially stale
- backmatter families are especially under-modeled

## Non-Goals

- Do not redesign figure/table pipeline here
- Do not add new journal-specific text patches
- Do not introduce absolute page gates or absolute font-size thresholds as primary logic
- Do not rebuild the pipeline from scratch

## Target End State

The final pipeline should be:

1. raw blocks
2. span extraction on correct coordinates
3. seed roles only
4. document structure analysis and structural normalization
5. profile building on normalized structure
6. section-aware rescue
7. downstream consumers render/index/health/inventory consume the same structure without re-inferring it

In other words:

- `ocr_roles.py` owns seed-role assignment only
- `ocr_document.py` owns document segmentation and structural normalization
- `ocr_profiles.py` owns profile construction and profile comparison
- `ocr_render.py` renders; it does not invent structure

## Implementation Plan

### Task 1: Fix span extraction coordinate baseline

Files:

- `paperforge/worker/ocr_pdf_spans.py`
- `paperforge/worker/ocr.py`
- `paperforge/worker/ocr_rebuild.py`
- tests in `tests/test_ocr_pdf_spans.py`

#### 1.1 Add an explicit OCR-to-PDF coordinate mapping path

Update `extract_pdf_spans_for_block()` and/or introduce a helper such as:

- `_map_ocr_bbox_to_pdf_rect(page, bbox, page_width, page_height)`

Use:

- OCR page dimensions from `raw_blocks.page_width/page_height`
- PDF page rect dimensions from `fitz.Page.rect`

Expected mapping:

- if OCR bbox is in rendered image coordinates, convert it back into PDF coordinates using scale ratios
- avoid direct `fitz.Rect(*bbox)` on OCR image coordinates

#### 1.2 Carry the required dimensions through the API

Update call sites so span extraction receives:

- `page_width`
- `page_height`

Likely signature change:

- `extract_pdf_spans_for_block(pdf_doc, page_num, bbox, page_width=None, page_height=None)`

#### 1.3 Preserve graceful degradation

If mapping inputs are absent or invalid:

- return `None`
- do not crash rebuild/ocr

#### 1.4 Add tests for coordinate mapping

Add tests that verify:

- OCR-space bbox is converted before clip extraction
- no-span fallback remains stable when PDF is missing or bbox invalid

Acceptance:

- `span_metadata` extraction no longer relies on raw OCR bbox as PDF clip coords
- tests cover mapped extraction path

### Task 2: Make `ocr_roles.py` a pure seed-role pass

Files:

- `paperforge/worker/ocr_roles.py`
- tests in `tests/test_ocr_roles.py`

#### 2.1 Remove residual structure-owning logic from role assignment

`assign_block_role()` should keep:

- raw label priors
- page-1 frontmatter zone heuristics
- figure/table formal prefix detection
- obvious abstract/reference/backmatter heading seeds
- conservative body fallback

It should stop owning:

- late tail spread ownership
- cross-page tail continuation logic
- render-like backmatter reordering assumptions

#### 2.2 Demote high-risk hard rules

Specifically remove or weaken as primary rules:

- `_is_backmatter_boundary_heading()` relative page gate:
  - `if total_pages > 0 and (page_num / total_pages) < 0.5: return False`
- visual heading shortcuts like:
  - `font_size >= 14`
  - `bold && font_size >= 11`

Replace with:

- heading-like style as one weak signal
- let `ocr_document.py` and later profile matching validate boundary families

#### 2.3 Keep boundary seeds conservative

`backmatter_boundary_heading` should remain seedable, but only when multiple signals agree:

- heading-like shape
- candidate container wording or structure
- not a known backmatter child heading
- not references

No absolute page number or hard half-document gate.

Acceptance:

- `assign_block_role()` becomes easier to reason about as a seed pass
- tests no longer assert page-ratio gating behavior

### Task 3: Move all document-level structural mutation into `ocr_document.py`

Files:

- `paperforge/worker/ocr_document.py`
- `paperforge/worker/ocr_render.py`
- tests in `tests/test_ocr_document.py`, `tests/test_ocr_render_stabilization.py`

#### 3.1 Define `ocr_document.py` as the only owner of structural normalization

`ocr_document.py` should own:

- body/backmatter/references boundary detection
- tail spread reconciliation
- backmatter form classification
- backmatter role normalization after boundary
- tail body candidate promotion
- tail spread ownership assignment

Currently some of this logic still lives in `ocr_render.py`:

- `_promote_tail_body_candidates()`
- `_assign_tail_spread_ownership()`

Move these into `ocr_document.py` or make `ocr_render.py` call normalized results only.

#### 3.2 Make `analyze_document_structure()` return normalized blocks explicitly

Current issue:

- it mutates blocks in-place indirectly and returns only `DocumentStructure`

Refactor to something like:

- `analyze_document_structure(blocks) -> tuple[DocumentStructure, list[dict]]`

or:

- `normalize_document_structure(blocks) -> NormalizedDocument`

where the returned artifact includes:

- `document_structure`
- `normalized_blocks`

This avoids hidden in-place mutation and makes downstream ordering explicit.

#### 3.3 Stop `ocr_render.py` from re-owning structure

`render_fulltext_markdown()` should consume already-normalized blocks and a precomputed `DocumentStructure`.

It should not:

- call `analyze_document_structure()` again
- promote tail bodies
- assign tail ownership

It may still do presentation-only ordering inside already-normalized page groups, but not semantic role mutation.

Acceptance:

- only one module owns structure mutation
- render consumes structure, it does not invent it

### Task 4: Reorder profile construction after structural normalization

Files:

- `paperforge/worker/ocr_blocks.py`
- `paperforge/worker/ocr_profiles.py`
- `paperforge/worker/ocr_document.py`
- tests in `tests/test_ocr_document.py`, `tests/test_ocr_profiles.py` if present

#### 4.1 Change `build_structured_blocks()` order

Current order:

1. seed roles
2. build role profiles
3. analyze document structure
4. rescue

Target order:

1. seed roles
2. analyze document structure + normalize roles
3. build profiles on normalized roles
4. rescue with normalized roles and normalized profiles

This is the most important sequencing fix.

#### 4.2 Expand profile semantics from role-only toward family-aware

Do not throw away `build_role_span_profiles()`.
Extend it so later rescue can reason about:

- body family
- heading family
- backmatter heading family
- reference family
- caption family

Minimal first step:

- keep role profiles for compatibility
- add helper(s) to derive family views from normalized roles

Do not overdesign this phase; the main goal here is correct sequencing, not a full new taxonomy.

Acceptance:

- `role_span_profiles.json` is built from normalized structure, not pre-normalized seeds
- backmatter/reference/body families are less stale

### Task 5: Upgrade rescue to use normalized structure as context

Files:

- `paperforge/worker/ocr_document.py`
- `paperforge/worker/ocr_blocks.py`
- tests in `tests/test_ocr_document.py`

#### 5.1 Keep rescue narrow but make it structurally consistent

Current rescue is acceptable in scope, but must operate on:

- normalized blocks
- normalized profiles
- final section boundaries

It should continue to own:

- frontmatter noise rescued back to body
- body promoted to reference in references zone
- weak heading demoted to body

#### 5.2 Prevent rescue from fighting stale roles

Once Task 4 is done, rescue no longer compares against pre-boundary profiles.

That should especially improve:

- backmatter child stability
- reference consistency
- weak heading/body disambiguation

Acceptance:

- rescue uses normalized context only
- no rescue step depends on pre-normalization role families

### Task 6: Make downstream products consume the same structure truth

Files:

- `paperforge/worker/ocr_rebuild.py`
- `paperforge/worker/ocr.py`
- `paperforge/worker/ocr_render.py`
- possibly `ocr_health.py`, `ocr_index.py`

#### 6.1 Thread document-structure output through downstream calls

Where possible, pass:

- normalized structured blocks
- document structure
- normalized profiles

into downstream stages instead of forcing each layer to reconstruct assumptions.

Minimal requirement:

- render must not recompute structure

Optional but desirable:

- health/index may later write structure summaries for debugging

#### 6.2 Consider persisting document structure artifact

Add a derived artifact such as:

- `structure/document_structure.json`

Contents may include:

- `body_end_page`
- `backmatter_start`
- `references_start`
- `spread_start`
- `spread_end`
- `backmatter_form`

This is useful for:

- debugging
- reproducibility
- making render/index/health easier to compare

Acceptance:

- same structural truth is visible and reusable downstream

## Testing Plan

### Unit / integration targets

1. `tests/test_ocr_pdf_spans.py`
- mapped OCR-to-PDF coordinate extraction
- graceful fallback

2. `tests/test_ocr_roles.py`
- remove expectations that depend on hard page gates or hard font thresholds
- keep seed-role expectations conservative

3. `tests/test_ocr_document.py`
- boundary detection still works
- backmatter normalization still works
- rescue uses normalized roles

4. `tests/test_ocr_render_stabilization.py`
- render no longer depends on its own structural mutation
- tail ordering remains correct when given normalized blocks

5. if needed, add a new test around `build_structured_blocks()` ordering
- asserts profile build happens after document normalization

### Real-paper regression set

Must re-run on:

- `7C8829BD`
  - Frontiers-style mixed tail spread
- `2GN9LMCW`
  - PeerJ-style declarations container + references + unnumbered headings

Verification focus:

- structure layer and rendered markdown agree on backmatter order
- references remain stable
- no reintroduced page marker mismatch
- span metadata is present where expected and not obviously empty/misaligned

## Acceptance Criteria

This plan is complete when all of the following are true:

1. `span_metadata` extraction no longer assumes OCR bbox == PDF coordinates
2. `ocr_render.py` does not recompute or mutate document structure semantics
3. `build_structured_blocks()` builds profiles after structural normalization
4. rescue operates on normalized roles and normalized profiles
5. `7C8829BD` and `2GN9LMCW` remain correct after rebuild
6. tests cover the new sequencing and coordinate-baseline assumptions

## Risks To Watch

1. Over-coupling render to a new structure artifact too early
- keep the first change minimal: pass normalized blocks first, persist structure later if useful

2. Breaking old tests that implicitly relied on hard threshold behavior
- update tests toward seed-role behavior, not old heuristic internals

3. Span extraction still returning sparse data on scan-heavy PDFs
- that is acceptable if graceful degradation remains intact
- the important fix is to stop reading obviously wrong regions

## Recommended Execution Order

1. Task 1 — span coordinate fix
2. Task 3 — make `ocr_document.py` the structure owner
3. Task 4 — reorder profile construction
4. Task 5 — rescue on normalized context
5. Task 6 — downstream truth convergence
6. finalize tests and real-paper rebuild verification

