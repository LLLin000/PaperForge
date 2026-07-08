# OCR P0-P2 Layout Close-Out Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the current OCR-v2 P0-P2 close-out issues by making first-surviving-page zone inference authoritative, tightening publisher edge-band noise handling, recovering residual figure inner text with layout evidence, and updating only the verified stale expectations.

**Architecture:** Keep the existing OCR-v2 anchor-first pipeline and patch the two narrow seams that are actually failing: `infer_zones()` in `ocr_document.py` and layout-first fallback classification in `ocr_roles.py`. Use TDD with focused unit tests first, then confirm the behavior against `DWQQK2YB`, `K7R8PEKW`/`A8E7SRVS`, and one control paper so the close-out fixes do not reopen the broader figure-group or page-state-machine work.

**Tech Stack:** Python 3.14, pytest, existing `paperforge.worker` OCR pipeline, fixture-backed real-paper replay tests, repo audit artifacts under `audit/`.

---

## File Structure

- Modify: `paperforge/worker/ocr_document.py`
  - Owns `infer_zones()` and the first-page/frontmatter/body split logic.
- Modify: `paperforge/worker/ocr_roles.py`
  - Owns layout-first fallback role assignment, margin-band noise detection, and figure-inner-text heuristics.
- Modify: `tests/test_ocr_document.py`
  - Owns unit tests for zone inference and body-start behavior.
- Modify: `tests/test_ocr_real_paper_regressions.py`
  - Owns production-path replay checks on DW, K7/A8, and a control paper.
- Modify: `tests/fixtures/ocr_real_papers/DWQQK2YB/expectations.json`
  - Update only if the first-surviving-page behavior is visually verified and the old expectations are now stale.
- Modify: `PROJECT-MANAGEMENT.md`
  - Record the completed fix and remaining residuals immediately after verification.
- Modify: `project/current/ocr-v2-remaining-issues-2026-06-18.md`
  - Rewrite the residual picture after the measured rerun.

---

### Task 1: Lock First-Surviving-Page Behavior With Red Tests

**Files:**
- Modify: `tests/test_ocr_document.py`
- Modify: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write the failing unit test for first-surviving-page frontmatter retention**

Add this test near the other zone/document normalization tests in `tests/test_ocr_document.py`:

```python
def test_infer_zones_treats_first_surviving_page_as_frontmatter_origin() -> None:
    from paperforge.worker.ocr_document import infer_zones

    blocks = [
        {
            "block_id": "p2_title",
            "page": 2,
            "text": "Real Article Title",
            "seed_role": "paper_title",
            "role": "paper_title",
            "bbox": [80, 120, 900, 180],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "none"},
        },
        {
            "block_id": "p2_authors",
            "page": 2,
            "text": "A. Author, B. Author",
            "seed_role": "authors",
            "role": "authors",
            "bbox": [80, 220, 920, 280],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "none"},
        },
        {
            "block_id": "p2_body",
            "page": 2,
            "text": "This is the first real body paragraph with enough words to trigger body flow on the first surviving page.",
            "seed_role": "body_paragraph",
            "role": "body_paragraph",
            "bbox": [80, 520, 1030, 650],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "none"},
        },
    ]

    zones = infer_zones(blocks, body_anchor={"status": "ACCEPT"}, reference_anchor={"status": "HOLD"})

    assert "p2_title" in zones["frontmatter_main_zone"]["block_ids"]
    assert "p2_authors" in zones["frontmatter_main_zone"]["block_ids"]
    assert "p2_body" in zones["body_zone"]["block_ids"]
```

- [ ] **Step 2: Write the failing unit test that body can start on the first surviving page**

Add this immediately after the previous test in `tests/test_ocr_document.py`:

```python
def test_infer_zones_allows_body_blocks_on_first_surviving_page() -> None:
    from paperforge.worker.ocr_document import infer_zones

    blocks = [
        {
            "block_id": "p2_title",
            "page": 2,
            "text": "Real Article Title",
            "seed_role": "paper_title",
            "role": "paper_title",
            "bbox": [80, 120, 900, 180],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "none"},
        },
        {
            "block_id": "p2_heading",
            "page": 2,
            "text": "Highlights",
            "seed_role": "structured_insert",
            "role": "structured_insert",
            "bbox": [80, 980, 260, 1020],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "short_fragment"},
        },
        {
            "block_id": "p2_b1",
            "page": 2,
            "text": "Body continuation should remain eligible for body_zone when it begins on the first surviving page rather than literal page one.",
            "seed_role": "body_paragraph",
            "role": "body_paragraph",
            "bbox": [100, 1060, 1020, 1180],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "none"},
        },
    ]

    zones = infer_zones(blocks, body_anchor={"status": "ACCEPT"}, reference_anchor={"status": "HOLD"})

    assert "p2_b1" in zones["body_zone"]["block_ids"]
    assert "p2_b1" not in zones["frontmatter_main_zone"]["block_ids"]
```

- [ ] **Step 3: Write the failing real-paper regression for DWQQK2YB first-surviving-page recovery**

Add this in `tests/test_ocr_real_paper_regressions.py` near the other DW regression tests:

```python
def test_dwqqk2yb_first_surviving_page_keeps_title_and_authors(tmp_path: Path) -> None:
    result = replay_production_pipeline("DWQQK2YB", tmp_path)
    page2_blocks = [b for b in result["structured_blocks"] if int(b.get("page", 0) or 0) == 2]

    title_block = next(
        b for b in page2_blocks if "Magnetoresponsive Stem Cell Spheroid" in str(b.get("text") or "")
    )
    authors_block = next(
        b for b in page2_blocks if "Ami Yoo" in str(b.get("text") or "") or "Ami Yoo" in str(b.get("block_content") or "")
    )

    assert title_block.get("role") == "paper_title"
    assert authors_block.get("role") in {"authors", "frontmatter_support"}
    assert title_block.get("zone") == "frontmatter_main_zone"
    assert authors_block.get("zone") == "frontmatter_main_zone"
```

- [ ] **Step 4: Run the focused tests to verify red**

Run: `python -m pytest tests/test_ocr_document.py -k "first_surviving_page" -v --tb=short`

Expected: FAIL because `infer_zones()` still hardcodes literal page 1 and excludes first-surviving-page body blocks.

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "dwqqk2yb_first_surviving_page" -v --tb=short`

Expected: FAIL because DW page 2 title/authors currently fall into `unknown_structural` / `body_zone` fallback.

- [ ] **Step 5: Commit the failing tests only**

```bash
git add tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "test: lock first surviving page OCR regressions"
```

---

### Task 2: Implement First-Surviving-Page Zone Inference

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Add a helper that returns the first surviving page**

In `paperforge/worker/ocr_document.py`, near the other zone helpers above `infer_zones()`, add:

```python
def _first_surviving_page(blocks: list[dict]) -> int | None:
    pages = sorted({int(block.get("page", 0) or 0) for block in blocks if int(block.get("page", 0) or 0) > 0})
    return pages[0] if pages else None
```

- [ ] **Step 2: Generalize `_is_page1_body_start()` without broadening it**

Replace the existing helper with a first-surviving-page-aware version in `paperforge/worker/ocr_document.py`:

```python
def _is_first_page_body_start(block: dict, *, seen_title_or_author: bool) -> bool:
    if not seen_title_or_author:
        return False
    role = block.get("role") or block.get("seed_role")
    if role == "unassigned":
        role = block.get("seed_role")
    text = str(block.get("text") or "").strip()
    words = text.split()
    marker_type = ((block.get("marker_signature") or {}).get("type") or "none")
    if marker_type == "preproof_marker":
        return False
    if role in {"section_heading", "subsection_heading", "structured_insert", "structured_insert_candidate"}:
        return True
    if role == "body_paragraph" and len(words) >= 20:
        lower = text.lower()
        if not lower.startswith(("correspondence", "received", "accepted", "published", "doi")):
            return True
    return False
```

- [ ] **Step 3: Make `infer_zones()` use the first surviving page instead of literal page 1**

In `infer_zones()` update the frontmatter/body-start block collection from:

```python
page1_candidates = [
    b for b in blocks
    if int(b.get("page", 0) or 0) == 1
    ...
]
```

to:

```python
first_surviving_page = _first_surviving_page(blocks)

page1_candidates = [
    b for b in blocks
    if first_surviving_page is not None
    and int(b.get("page", 0) or 0) == first_surviving_page
    and ((b.get("marker_signature") or {}).get("type") or "none") != "preproof_marker"
    and not _is_reference_item_candidate(b)
    and b.get("block_id") is not None
]
```

Also update the body-start call site from `_is_page1_body_start(...)` to `_is_first_page_body_start(...)`.

- [ ] **Step 4: Allow body eligibility on the first surviving page**

In `infer_zones()` replace the body-page gate:

```python
and int(block.get("page", 0) or 0) > 1
```

with:

```python
and first_surviving_page is not None
and (
    int(block.get("page", 0) or 0) > first_surviving_page
    or (
        int(block.get("page", 0) or 0) == first_surviving_page
        and _artifact_block_id(block, duplicate_block_ids) not in frontmatter_main_id_set
        and _artifact_block_id(block, duplicate_block_ids) not in frontmatter_side_id_set
    )
)
```

Keep the existing reference-heading split, reference exclusion, and side-zone exclusion intact.

- [ ] **Step 5: Update the page-band metadata to reflect the surviving first page**

In the returned zone payload, replace:

```python
boundary_band=_page_band(1, 1) if frontmatter_main_ids else None,
```

with:

```python
boundary_band=_page_band(first_surviving_page, first_surviving_page) if frontmatter_main_ids else None,
```

- [ ] **Step 6: Run the focused tests to verify green**

Run: `python -m pytest tests/test_ocr_document.py -k "first_surviving_page" -v --tb=short`

Expected: PASS.

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "dwqqk2yb_first_surviving_page" -v --tb=short`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add paperforge/worker/ocr_document.py tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: infer OCR zones from first surviving page"
```

---

### Task 3: Lock And Implement Layout-First Margin-Band Noise And Figure-Inner-Text Recovery

**Files:**
- Modify: `tests/test_ocr_document.py`
- Modify: `paperforge/worker/ocr_roles.py`
- Modify: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write the failing unit test for edge-band watermark noise**

Add this test to `tests/test_ocr_document.py`:

```python
def test_assign_block_role_marks_margin_band_as_noise() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "page": 4,
        "block_id": "wm",
        "raw_label": "aside_text",
        "block_label": "aside_text",
        "text": "Downloaded from https://advanced.onlinelibrary.wiley.com by Example Library. For personal use only.",
        "bbox": [1155, 30, 1171, 1535],
        "block_bbox": [1155, 30, 1171, 1535],
        "page_width": 1224,
        "page_height": 1584,
    }

    assignment = assign_block_role(block, page_blocks=[block])

    assert assignment.role == "noise"
    assert assignment.confidence >= 0.95
```

- [ ] **Step 2: Write the failing unit test for figure-inner-text recovery**

Add this next to the previous test in `tests/test_ocr_document.py`:

```python
def test_assign_block_role_marks_short_figure_adjacent_label_as_inner_text() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    image_block = {
        "page": 1,
        "block_id": "img1",
        "raw_label": "image",
        "block_label": "image",
        "bbox": [300, 300, 800, 900],
        "block_bbox": [300, 300, 800, 900],
        "page_width": 1200,
        "page_height": 1600,
    }
    label_block = {
        "page": 1,
        "block_id": "lab1",
        "raw_label": "text",
        "block_label": "text",
        "text": "Day 7",
        "bbox": [320, 320, 410, 360],
        "block_bbox": [320, 320, 410, 360],
        "page_width": 1200,
        "page_height": 1600,
    }

    assignment = assign_block_role(label_block, page_blocks=[image_block, label_block])

    assert assignment.role == "figure_inner_text"
```

- [ ] **Step 3: Write the failing real-paper regression for publisher strips**

Add this to `tests/test_ocr_real_paper_regressions.py`:

```python
def test_k7r8pekw_margin_band_publishers_stay_noise(tmp_path: Path) -> None:
    result = replay_production_pipeline("K7R8PEKW", tmp_path)
    watermark_blocks = [
        b for b in result["structured_blocks"]
        if "Downloaded from" in str(b.get("text") or "")
    ]

    assert watermark_blocks, "Expected at least one publisher watermark block"
    assert all(b.get("role") == "noise" for b in watermark_blocks)
```

- [ ] **Step 4: Run the focused tests to verify red**

Run: `python -m pytest tests/test_ocr_document.py -k "margin_band or inner_text" -v --tb=short`

Expected: FAIL until the geometry helpers are tightened.

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "k7r8pekw_margin_band" -v --tb=short`

Expected: FAIL because the watermark strips still survive as `unknown_structural` in the replay path.

- [ ] **Step 5: Tighten the geometry-first watermark rule**

In `paperforge/worker/ocr_roles.py`, keep the existing helpers but make the edge-band path slightly stricter and optionally text-confirmed:

```python
def _has_confirmatory_watermark_text(text: str) -> bool:
    lower = text.lower()
    return "downloaded from" in lower or "for personal use only" in lower
```

Then update `_looks_like_margin_band_noise()` so it still accepts the current extreme geometry but tolerates the real K7/A8 right-edge strips:

```python
very_tall = height >= page_height * 0.30
very_narrow = width <= page_width * 0.12
edge_band = at_left_edge or at_right_edge
text = str(block.get("text") or block.get("block_content") or "")
return edge_band and very_tall and (very_narrow or _has_confirmatory_watermark_text(text))
```

Do not call the helper outside the geometry gate.

- [ ] **Step 6: Broaden figure-inner-text recovery by geometry, not caption text**

In `paperforge/worker/ocr_roles.py`, update `_looks_like_figure_inner_label()` from the current alpha-only filter to allow compact mixed alnum labels while staying short and figure-adjacent:

```python
if not t or len(t) > 12:
    return False
if _has_figure_prefix(t):
    return False
token_count = len(t.split())
if token_count > 2:
    return False
has_alnum = any(ch.isalnum() for ch in t)
if not has_alnum:
    return False
```

Keep the existing media adjacency check intact.

- [ ] **Step 7: Run the focused tests to verify green**

Run: `python -m pytest tests/test_ocr_document.py -k "margin_band or inner_text" -v --tb=short`

Expected: PASS.

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "k7r8pekw_margin_band" -v --tb=short`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add paperforge/worker/ocr_roles.py tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: tighten OCR margin-band noise and figure inner text"
```

---

### Task 4: Reconcile Verified Expectations And Project Trackers

**Files:**
- Modify: `tests/fixtures/ocr_real_papers/DWQQK2YB/expectations.json`
- Modify: `PROJECT-MANAGEMENT.md`
- Modify: `project/current/ocr-v2-remaining-issues-2026-06-18.md`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Re-run the targeted real-paper replay checks**

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "DWQQK2YB or K7R8PEKW or CAQNW9Q2" -v --tb=short`

Expected: PASS for the newly added DW/K7 checks, and no regression on the existing CAQ production-path checks.

- [ ] **Step 2: Update DW expectations only if the behavior is now visually correct**

In `tests/fixtures/ocr_real_papers/DWQQK2YB/expectations.json`, change the stale page-2 assertions from the current bug notes:

```json
{"text_contains": "Magnetoresponsive Stem Cell Spheroid", "expected_role": "paper_title", "expected_zone": "frontmatter_main_zone"}
```

and:

```json
{"text_contains": "Ami Yoo", "expected_role": "authors", "expected_zone": "frontmatter_main_zone"}
```

If the replay still produces `frontmatter_support` for the author block but the zone is correct, update the expected role to `frontmatter_support` instead of forcing `authors`.

- [ ] **Step 3: Run the paper-specific regression to verify expectations**

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "DWQQK2YB" -v --tb=short`

Expected: PASS.

- [ ] **Step 4: Update the project tracker immediately after the verified fix**

In `PROJECT-MANAGEMENT.md`, append a new session entry in the existing format:

```md
### 10.x First-surviving-page and edge-band close-out (2026-06-18)
- Problem: preproof-drop papers still used literal page 1 assumptions; repeated publisher strips survived as unknown_structural.
- Root cause: `infer_zones()` anchored frontmatter/body split to `page == 1`; margin-band noise helpers were geometry-correct for only the narrowest cases.
- Fix: switched zone inference to the first surviving page, allowed body flow on that page after the local body-start anchor, and tightened geometry-first margin-band noise detection with optional confirmatory text.
- Result: DW first surviving page frontmatter recovered; K7 watermark strips demoted to noise without broad text-first routing.
- Test status: [insert exact focused pytest commands and result counts from this run].
```

- [ ] **Step 5: Rewrite the remaining-issues note from measured results**

In `project/current/ocr-v2-remaining-issues-2026-06-18.md`, update only the sections that changed:

- mark Issue 1 resolved if DW replay now passes,
- reduce or remove the publisher-noise bucket if the K7/A8 geometry fix closes it,
- leave figure-group and CLI rebuild items deferred,
- do not claim success for any bucket that was not re-measured.

- [ ] **Step 6: Run the final close-out test slice**

Run: `python -m pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py -k "first_surviving_page or margin_band or inner_text or DWQQK2YB or K7R8PEKW or CAQNW9Q2" -v --tb=short`

Expected: all selected tests PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/ocr_real_papers/DWQQK2YB/expectations.json PROJECT-MANAGEMENT.md project/current/ocr-v2-remaining-issues-2026-06-18.md tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "docs: record OCR layout close-out progress"
```
