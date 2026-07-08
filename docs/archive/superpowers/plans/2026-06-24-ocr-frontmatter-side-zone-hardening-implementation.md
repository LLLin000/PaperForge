# OCR Frontmatter Side Zone Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop real early-body-page headings and body continuations from being swallowed into `frontmatter_side_zone`, while preserving legitimate frontmatter/support furniture and keeping the existing structural gate architecture unchanged.

**Architecture:** Keep the current two-layer OCR-v2 structure intact: zone inference produces cleaner zone assignments, and the existing structural gate continues to consume those assignments without new policy. The only behavioral changes are in `paperforge/worker/ocr_document.py`: narrow `_is_frontmatter_side_candidate()` with first-surviving-page and local same-column context, narrow `_demote_early_frontmatter_body_leaks()` to the first surviving page before body start, and normalize accepted heading membership ids so page-local `block_id` collisions do not contaminate heading verification.

**Tech Stack:** Python 3.14, pytest, existing `paperforge.worker` OCR pipeline, fixture-backed real-paper replay tests, repo regression fixtures under `tests/` and live replay targets such as `49PY5UCJ` and `DWQQK2YB`.

---

## File Structure

- Modify: `paperforge/worker/ocr_document.py`
  - Owns `_is_frontmatter_side_candidate()`, `infer_zones()`, `_demote_early_frontmatter_body_leaks()`, and `_build_accepted_heading_block_ids()`.
- Modify: `tests/test_ocr_document.py`
  - Owns focused unit tests for zone inference, helper behavior, demotion boundaries, and heading-id normalization.
- Modify: `tests/test_ocr_real_paper_regressions.py`
  - Owns production-path replay checks for `DWQQK2YB` and control papers, plus fixture-conditional notes for the motivating live-paper case.
- Modify: `PROJECT-MANAGEMENT.md`
  - Record the completed fix immediately after verification, including problem, root cause, repair, and remaining known risks.

No new files in `paperforge/worker/`. No new document artifacts. No new structural gate implementation file.

---

### Task 1: Lock The Regression With Red Tests

**Files:**
- Modify: `tests/test_ocr_document.py`
- Modify: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Add a unit test that page-2 body headings are not treated as frontmatter-side just because they are narrow and early**

Add this near the existing `infer_zones()` tests in `tests/test_ocr_document.py`:

```python
def test_infer_zones_does_not_route_page2_heading_with_body_continuation_to_frontmatter_side() -> None:
    from paperforge.worker.ocr_document import infer_zones

    blocks = [
        {
            "block_id": "p1_title",
            "page": 1,
            "role": "paper_title",
            "seed_role": "paper_title",
            "text": "Real Paper Title",
            "bbox": [80, 120, 900, 180],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "none"},
        },
        {
            "block_id": "p2_body_1",
            "page": 2,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "text": "Lead body paragraph that establishes the left-column body family on the first surviving page for this synthetic case.",
            "bbox": [80, 120, 585, 260],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_family_norm": "MinionPro-Regular", "font_size_median": 9.5},
        },
        {
            "block_id": "p2_h1",
            "page": 2,
            "role": "section_heading",
            "seed_role": "section_heading",
            "text": "THE MOLECULAR IDENTITY AND REGULATION OF THE MCU COMPLEX",
            "bbox": [80, 560, 535, 630],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_family_norm": "HelveticaNeueLTStd-Bd", "font_size_median": 12.0},
        },
        {
            "block_id": "p2_b2",
            "page": 2,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "text": "To date, three different mitochondrial membrane proteins have been characterized as components of the uniporter.",
            "bbox": [80, 678, 586, 748],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_family_norm": "MinionPro-Regular", "font_size_median": 9.5},
        },
    ]

    zones = infer_zones(
        blocks,
        {"body_family_anchor": {"status": "ACCEPT", "sample_pages": [2], "width_bucket": 500, "font_family_norm": "MinionPro-Regular"},
         "reference_family_anchor": {"status": "HOLD"}},
    )

    assert "p2_h1" in zones["body_zone"]["block_ids"]
    assert "p2_h1" not in zones["frontmatter_side_zone"]["block_ids"]
    assert "p2_b2" in zones["body_zone"]["block_ids"]
```

- [ ] **Step 2: Add a unit test that heading-like furniture can still enter `frontmatter_side_zone` after the first surviving page**

Add this immediately after the previous test in `tests/test_ocr_document.py`:

```python
def test_infer_zones_keeps_page2_highlights_in_frontmatter_side_when_support_geometry_matches() -> None:
    from paperforge.worker.ocr_document import infer_zones

    blocks = [
        {
            "block_id": "p1_title",
            "page": 1,
            "role": "paper_title",
            "seed_role": "paper_title",
            "text": "Paper Title",
            "bbox": [80, 120, 900, 180],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "none"},
        },
        {
            "block_id": "p2_highlights",
            "page": 2,
            "role": "section_heading",
            "seed_role": "section_heading",
            "text": "Highlights",
            "bbox": [930, 170, 1110, 220],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_family_norm": "HelveticaNeueLTStd-Bd", "font_size_median": 10.0},
        },
    ]

    zones = infer_zones(
        blocks,
        {"body_family_anchor": {"status": "ACCEPT", "sample_pages": [2], "width_bucket": 500, "font_family_norm": "MinionPro-Regular"},
         "reference_family_anchor": {"status": "HOLD"}},
    )

    assert "p2_highlights" in zones["frontmatter_side_zone"]["block_ids"]
    assert "p2_highlights" not in zones["body_zone"]["block_ids"]
```

- [ ] **Step 3: Add a unit test that accepted heading ids are page-safe when local `block_id`s collide**

Add this near `test_gate_context_adapters_do_not_accept_from_seed_roles_only` in `tests/test_ocr_document.py`:

```python
def test_build_accepted_heading_block_ids_uses_page_safe_ids_for_duplicates() -> None:
    from paperforge.worker.ocr_document import _build_accepted_heading_block_ids

    blocks = [
        {"page": 2, "block_id": 4, "seed_role": "section_heading", "role": "section_heading", "zone": "body_zone"},
        {"page": 7, "block_id": 4, "seed_role": "section_heading", "role": "section_heading", "zone": "body_zone"},
    ]

    accepted = _build_accepted_heading_block_ids(blocks, None)

    assert accepted == {"p2:4", "p7:4"}
    assert 4 not in accepted
```

- [ ] **Step 4: Add a fixture-conditional target regression placeholder and keep the mandatory gate on synthetic plus existing replay fixtures**

Do not add a mandatory `49PY5UCJ` replay test until a real fixture exists under `tests/fixtures/ocr_real_papers/49PY5UCJ/`.

Instead, add this comment block near the other OCR replay regressions in `tests/test_ocr_real_paper_regressions.py` so the missing fixture is explicit and future work has an anchor:

```python
# NOTE:
# `49PY5UCJ` is the motivating live-paper failure, but it is not currently
# fixture-backed under `tests/fixtures/ocr_real_papers/49PY5UCJ/`.
# Keep merge-gate coverage on synthetic tests plus existing replay fixtures.
# Once the fixture lands, add a replay test that asserts:
# - page-2 main heading reaches `body_zone`
# - final role is `section_heading`
# - rendered markdown contains:
#   "## THE MOLECULAR IDENTITY AND REGULATION OF THE MCU COMPLEX"
```

- [ ] **Step 5: Run the focused tests to verify red**

Run: `python -m pytest tests/test_ocr_document.py -k "frontmatter_side or accepted_heading_block_ids" -v --tb=short`

Expected: FAIL because `_is_frontmatter_side_candidate()` still over-trusts `page <= 2` geometry and `_build_accepted_heading_block_ids()` still emits bare duplicate ids.

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "dwqqk2yb_first_surviving_page" -v --tb=short`

Expected: PASS or remain green; this control confirms the synthetic red tests are not just breaking first-surviving-page frontmatter handling.

- [ ] **Step 6: Commit the failing tests only**

```bash
git add tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "test: lock frontmatter side OCR regressions"
```

---

### Task 2: Narrow `_is_frontmatter_side_candidate()` Instead Of Adding New State

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Add a helper for explicit frontmatter/support furniture text**

In `paperforge/worker/ocr_document.py`, above `_is_frontmatter_side_candidate()`, add:

```python
def _is_explicit_frontmatter_support_furniture(text: str) -> bool:
    lower = text.strip().lower()
    if not lower:
        return False
    if lower in {"highlights", "key points"} or lower.startswith(("highlights", "key points")):
        return True
    phrases = (
        "correspondence",
        "corresponding author",
        "highlights",
        "key points",
        "received:",
        "accepted:",
        "published online",
        "copyright",
        "edited by",
        "reviewed by",
        "specialty section",
        "citation:",
        "how to cite",
        "to cite this article",
        "conflict of interest",
        "equal contribution",
        "these authors contributed equally",
        "orcid",
    )
    return any(phrase in lower for phrase in phrases)
```

- [ ] **Step 2: Add helpers for heading-like veto and nearest same-column meaningful block**

Still above `_is_frontmatter_side_candidate()`, add:

```python
def _is_heading_like_block(block: dict) -> bool:
    role = str(block.get("role") or "")
    seed_role = str(block.get("seed_role") or "")
    if role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
        return True
    if seed_role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
        return True
    marker_type = str(((block.get("marker_signature") or {}).get("type")) or "")
    return marker_type in {"canonical_section_name", "heading_arabic", "heading_decimal"}


def _nearest_meaningful_same_column_block(block: dict, page_blocks: list[dict]) -> dict | None:
    bbox = _block_bbox(block)
    if bbox is None:
        return None
    page = int(block.get("page", 0) or 0)
    right_of = bbox[3]
    current_col = _get_column(block, float(block.get("page_width") or 1200))
    best: tuple[float, dict] | None = None
    boundary_roles = {"structured_insert", "non_body_insert", "reference_heading", "reference_item", "table_html", "table_caption", "figure_caption"}
    for other in page_blocks:
        if other is block or int(other.get("page", 0) or 0) != page:
            continue
        other_text = str(other.get("text") or other.get("block_content") or "").strip()
        if not other_text:
            continue
        other_role = str(other.get("role") or "")
        if other_role in {"noise", "page_header", "page_footer", "number", "frontmatter_noise"}:
            continue
        obox = _block_bbox(other)
        if obox is None or obox[1] < right_of:
            continue
        if _get_column(other, float(other.get("page_width") or 1200)) != current_col:
            continue
        gap = float(obox[1]) - float(right_of)
        if best is None or gap < best[0]:
            best = (gap, other)
    if best is None:
        return None
    candidate = best[1]
    if str(candidate.get("role") or "") in boundary_roles:
        return candidate
    return candidate
```

- [ ] **Step 3: Extend `_is_frontmatter_side_candidate()` with local context and replace the broad early-page rule**

Change the signature and body in `paperforge/worker/ocr_document.py` to:

```python
def _is_frontmatter_side_candidate(
    block: dict,
    body_anchor: dict | None = None,
    *,
    first_surviving_page: int | None = None,
    page_blocks: list[dict] | None = None,
) -> bool:
    page = int(block.get("page", 0) or 0)
    if page <= 0:
        return False

    marker_type = (block.get("marker_signature") or {}).get("type") or "none"
    if marker_type == "preproof_marker" or _is_reference_item_candidate(block):
        return False

    text = str(block.get("text") or block.get("block_content") or "").strip()
    if not text:
        return False

    lower = text.lower()
    explicit_furniture = _is_explicit_frontmatter_support_furniture(text)
    bbox = _block_bbox(block)
    page_width = float(block.get("page_width") or 0)
    page_height = float(block.get("page_height") or 0)
    block_width = (bbox[2] - bbox[0]) if bbox else 0.0
    x_center = ((bbox[0] + bbox[2]) / 2.0) if bbox else 0.0
    narrow = page_width > 0 and block_width > 0 and block_width <= page_width * 0.38
    side_column = page_width > 0 and bbox is not None and (x_center <= page_width * 0.28 or x_center >= page_width * 0.72)
    top_half = page_height > 0 and bbox is not None and bbox[1] <= page_height * 0.55

    if explicit_furniture:
        if first_surviving_page is None or page == first_surviving_page:
            return top_half or narrow or side_column
        if "highlights" in lower or "key points" in lower:
            return top_half and (narrow or side_column)
        return top_half and (narrow or side_column)

    if page != first_surviving_page:
        return False

    if _is_heading_like_block(block):
        return False

    nearest = _nearest_meaningful_same_column_block(block, page_blocks or [])
    if nearest is not None:
        nearest_role = str(nearest.get("role") or nearest.get("seed_role") or "")
        nearest_bbox = _block_bbox(nearest)
        gap = None if bbox is None or nearest_bbox is None else float(nearest_bbox[1]) - float(bbox[3])
        if nearest_role == "body_paragraph" and gap is not None and gap <= page_height * 0.12:
            return False
        if nearest_role in {
            "structured_insert",
            "structured_insert_candidate",
            "non_body_insert",
            "reference_heading",
            "reference_item",
            "table_html",
            "table_html_candidate",
            "table_caption",
            "table_caption_candidate",
            "figure_caption",
            "figure_caption_candidate",
            "figure_asset",
            "media_asset",
        }:
            return False

    body_anchor = body_anchor or {}
    body_width = body_anchor.get("width_bucket")
    body_font_family = body_anchor.get("font_family_norm")
    span_signature = block.get("span_signature") or {}
    block_font_family = span_signature.get("font_family_norm")
    if page == first_surviving_page and top_half and (narrow or side_column):
        if body_width is not None and block_width and block_width <= float(body_width) - 100:
            return True
        if body_font_family and block_font_family and block_font_family != body_font_family:
            return True

    return False
```

- [ ] **Step 4: Pass `first_surviving_page` and per-page blocks from `infer_zones()`**

In `infer_zones()` inside `paperforge/worker/ocr_document.py`, replace the current `frontmatter_side_blocks` comprehension with a page-aware version like:

```python
    blocks_by_page: dict[int, list[dict]] = {}
    for block in blocks:
        p = int(block.get("page", 0) or 0)
        if p > 0:
            blocks_by_page.setdefault(p, []).append(block)

    frontmatter_side_blocks = [
        block
        for block in blocks
        if _is_frontmatter_side_candidate(
            block,
            body_anchor=body_anchor,
            first_surviving_page=first_surviving_page,
            page_blocks=blocks_by_page.get(int(block.get("page", 0) or 0), []),
        )
        and _artifact_block_id(block, duplicate_block_ids) not in frontmatter_main_id_set
        and block.get("block_id") is not None
        and not (
            body_started
            and first_surviving_page is not None
            and int(block.get("page", 0) or 0) == first_surviving_page
        )
    ]
```

- [ ] **Step 5: Run the focused tests to verify green for zone narrowing**

Run: `python -m pytest tests/test_ocr_document.py -k "frontmatter_side or first_surviving_page" -v --tb=short`

Expected: PASS for the new unit tests.

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "dwqqk2yb_first_surviving_page" -v --tb=short`

Expected: `DWQQK2YB` stays green; this confirms the zone-narrowing change did not regress first-surviving-page frontmatter handling.

- [ ] **Step 6: Commit the zone narrowing change**

```bash
git add paperforge/worker/ocr_document.py tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: narrow frontmatter side zone capture"
```

---

### Task 3: Narrow Early Demotion And Normalize Accepted Heading Identity

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `tests/test_ocr_document.py`

- [ ] **Step 1: Add a unit test that early frontmatter demotion stops after body-start on the first surviving page**

Add this in `tests/test_ocr_document.py` near the other demotion/helper tests:

```python
def test_demote_early_frontmatter_body_leaks_stops_after_heading_on_first_surviving_page() -> None:
    from paperforge.worker.ocr_document import _demote_early_frontmatter_body_leaks

    blocks = [
        {"page": 2, "role": "section_heading", "seed_role": "section_heading", "text": "REAL SECTION"},
        {"page": 2, "role": "body_paragraph", "seed_role": "body_paragraph", "text": "Real body paragraph after heading should stay body."},
        {"page": 3, "role": "body_paragraph", "seed_role": "body_paragraph", "text": "Later page body stays untouched too."},
    ]

    _demote_early_frontmatter_body_leaks(blocks)

    assert blocks[1]["role"] == "body_paragraph"
    assert blocks[2]["role"] == "body_paragraph"
```

- [ ] **Step 2: Narrow `_demote_early_frontmatter_body_leaks()` to the first surviving page and allow `seed_role` body-start evidence without deleting existing demotion categories**

Refactor the helper in `paperforge/worker/ocr_document.py` so that only the scope changes. Preserve the current demotion categories (`author list`, `affiliation`, `received/accepted`, `journal badge/article type`, and related branches) inside the narrowed scope.

The top of the function should become:

```python
def _demote_early_frontmatter_body_leaks(blocks: list[dict]) -> None:
    pages = sorted({int(block.get("page", 0) or 0) for block in blocks if int(block.get("page", 0) or 0) > 0})
    if not pages:
        return
    first_surviving_page = pages[0]
    body_started = False
    for block in blocks:
        page = int(block.get("page", 0) or 0)
        if page != first_surviving_page:
            continue
        role = str(block.get("role") or "")
        seed_role = str(block.get("seed_role") or "")
        if role in {"section_heading", "subsection_heading", "sub_subsection_heading"} or seed_role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
            body_started = True
            continue
        if role == "body_paragraph":
            text = _block_text(block).strip()
            if len(text.split()) >= 20:
                body_started = True
        if body_started:
            continue
        if role != "body_paragraph":
            continue
        if seed_role == "abstract_body":
            continue
```

After that prologue, keep the existing body of the helper intact so the current frontmatter-noise/support classification branches still run within the narrowed scope.

- [ ] **Step 3: Make `_build_accepted_heading_block_ids()` return artifact-safe ids when local ids collide and avoid leaking pre-existing bare ids**

Change `_build_accepted_heading_block_ids()` in `paperforge/worker/ocr_document.py` to:

```python
def _build_accepted_heading_block_ids(blocks: list[dict], doc_structure) -> set:
    heading_artifact = _doc_get(doc_structure, "accepted_heading_block_ids", set()) or set()
    duplicate_block_ids = _duplicate_block_ids_from_blocks(blocks)
    result = set()
    for item in heading_artifact:
        if isinstance(item, str) and item.startswith("p") and ":" in item:
            result.add(item)
        elif isinstance(item, int) and str(item) not in duplicate_block_ids:
            result.add(item)
    heading_seed_roles = {"section_heading", "subsection_heading", "sub_subsection_heading"}
    for block in blocks:
        if block.get("seed_role") in heading_seed_roles and block.get("zone") in {"body_zone", "tail_body_zone"}:
            bid = _artifact_block_id(block, duplicate_block_ids)
            if bid is not None:
                result.add(bid)
    return result
```

- [ ] **Step 4: Run the focused tests to verify green**

Run: `python -m pytest tests/test_ocr_document.py -k "demote_early_frontmatter_body_leaks or accepted_heading_block_ids" -v --tb=short`

Expected: PASS.

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "dwqqk2yb_first_surviving_page" -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit the demotion and identity normalization change**

```bash
git add paperforge/worker/ocr_document.py tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: harden early OCR frontmatter zoning"
```

---

### Task 4: Full Verification, Real-Paper Check, And Session Documentation

**Files:**
- Modify: `PROJECT-MANAGEMENT.md`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Run the full focused OCR verification set**

Run: `python -m pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py tests/test_ocr_render.py -k "frontmatter_side or first_surviving_page or dwqqk2yb" -v --tb=short`

Expected: PASS.

- [ ] **Step 2: Run the narrow rebuild-oriented control tests**

Run: `python -m pytest tests/test_ocr_rebuild.py tests/test_ocr_v2_structural_regressions.py -k "heading or zone or frontmatter" -v --tb=short`

Expected: PASS or no collected tests for the narrow `-k`; no new failures introduced.

- [ ] **Step 3: Manually validate the motivating live-paper outside the merge gate**

Do not make `49PY5UCJ` a required replay gate until a fixture exists.

Instead, after the synthetic and existing replay tests pass, run a manual rebuild against the real vault paper and inspect the output:

```bash
$env:PAPERFORGE_VAULT = "D:\L\OB\Literature-hub"
python -m paperforge ocr rebuild 49PY5UCJ
```

Then inspect:

- `D:\L\OB\Literature-hub\System\PaperForge\ocr\49PY5UCJ\structure\blocks.structured.jsonl`
- `D:\L\OB\Literature-hub\System\PaperForge\ocr\49PY5UCJ\fulltext.md`

Expected live-paper result:

```text
## THE MOLECULAR IDENTITY AND REGULATION OF THE MCU COMPLEX
### The Pore Forming Subunits
```

- [ ] **Step 4: Record the fix in `PROJECT-MANAGEMENT.md`**

Append a new entry using the repo format:

```markdown
### 1.X OCR frontmatter-side zone hardening (2026-06-24)

**Problem:** Real page-2 body headings and body continuations could be swallowed into `frontmatter_side_zone`, then suppressed by the structural gate.

**Root cause:** `_is_frontmatter_side_candidate()` over-trusted early-page narrow/side-column geometry, `_demote_early_frontmatter_body_leaks()` still used broad `page <= 2` assumptions, and accepted heading membership used page-local ids that could collide across pages.

**Fix:** Narrowed frontmatter-side entry to explicit furniture plus supporting geometry, added heading/body-continuation vetoes, restricted early demotion to the first surviving page before body-start, and normalized accepted heading membership ids to artifact-safe identities.

**Result:** `49PY5UCJ` page-2 section heading survives as body heading; preproof-drop frontmatter behavior remains intact; heading verification no longer varies because of cross-page id reuse.

**Tests:** `python -m pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py tests/test_ocr_render.py -k "frontmatter_side or first_surviving_page or dwqqk2yb" -v --tb=short`
```

- [ ] **Step 5: Commit verification and project management update**

```bash
git add PROJECT-MANAGEMENT.md
git commit -m "docs: record OCR frontmatter side hardening"
```
