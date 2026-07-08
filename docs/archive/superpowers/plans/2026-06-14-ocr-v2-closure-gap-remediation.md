# OCR-v2 Closure Gap Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining verified OCR-v2 layout-analysis gaps without adding paper-specific patches, so regenerated real-paper `block_trace.csv` moves closer to `expectations.json` while preserving broad academic-document behavior.

**Architecture:** Fix seed-role classification and document-level normalization at their actual decision points instead of patching render output or weakening expectations. Constrain changes with targeted regression tests on both synthetic fixtures and regenerated real-paper traces so every improvement is tied to a general rule and checked against likely regression surfaces.

**Tech Stack:** Python 3.14, pytest, PaperForge OCR worker modules (`ocr_roles.py`, `ocr_document.py`, `ocr_structural_gate.py`, `ocr_render.py`, `sync_service.py`), fixture-based regression tests.

---

## File Map

- Modify: `paperforge/worker/ocr_roles.py`
  Purpose: seed-role classification for page-1 article-type labels, frontmatter author/support routing, and safe sidebar heading handling.
- Modify: `paperforge/worker/ocr_document.py`
  Purpose: zone inference and backmatter/body boundary handling, especially same-page reference/body conflicts.
- Modify: `paperforge/worker/ocr_structural_gate.py`
  Purpose: promotion from candidate roles to accepted structural roles when document evidence is sufficient.
- Modify: `paperforge/worker/ocr_render.py`
  Purpose: abstract-body fallback rendering without `document_structure`, and reader-status visibility contract.
- Modify: `paperforge/services/sync_service.py`
  Purpose: initialize `ocr_runtime_summary` on all dispatch paths.
- Modify: `tests/test_ocr_roles.py`
  Purpose: page-1 article-type label, author byline, and highlights-safe handling regressions.
- Modify: `tests/test_ocr_document.py`
  Purpose: same-page ref/body conflict, gratitude tail handling, biography normalization, and backmatter candidate promotion regressions.
- Modify: `tests/test_ocr_structural_gate.py`
  Purpose: candidate-to-accepted promotion tests for backmatter headings and support-zone handling.
- Modify: `tests/test_ocr_rendering.py`
  Purpose: abstract-body fallback and reader-status visibility regressions.
- Modify: `tests/test_cli_worker_dispatch.py`
  Purpose: selection-sync dispatch regression for `ocr_runtime_summary`.
- Modify: `tests/test_ocr_trace_vs_expectations.py`
  Purpose: keep fixture comparison stable if helper assumptions need to reflect improved roles.
- Use/Regenerate: `tests/fixtures/ocr_real_papers/{CAQNW9Q2,DWQQK2YB}/block_trace.csv`
  Purpose: real-paper truth trace after each accepted fix.

---

### Task 1: Lock Current Gap Surface In Tests

**Files:**
- Modify: `tests/test_ocr_roles.py`
- Modify: `tests/test_ocr_document.py`
- Modify: `tests/test_ocr_rendering.py`
- Modify: `tests/test_cli_worker_dispatch.py`

- [ ] **Step 1: Add focused failing role tests for CAQ page-1 article type and author/support routing**

```python
def test_page1_review_article_label_stays_frontmatter_noise() -> None:
    block = {
        "page": 1,
        "raw_label": "paragraph_title",
        "text": "REVIEW",
        "bbox": [120, 120, 420, 180],
        "page_width": 1200,
        "page_height": 1700,
    }
    role = assign_block_role(block, page_blocks=[block])
    assert role.role == "frontmatter_noise"


def test_page1_author_byline_with_initial_lastname_order_is_authors() -> None:
    block = {
        "page": 1,
        "raw_label": "text",
        "text": "J C Buckland-Wright",
        "bbox": [120, 300, 640, 350],
        "page_width": 1200,
        "page_height": 1700,
    }
    role = assign_block_role(block, page_blocks=[block])
    assert role.role == "authors"


def test_page1_correspondence_footnote_routes_to_frontmatter_support() -> None:
    block = {
        "page": 1,
        "raw_label": "footnote",
        "text": "Correspondence to: Dr J C Buckland-Wright",
        "bbox": [80, 1320, 640, 1420],
        "page_width": 1200,
        "page_height": 1700,
    }
    role = assign_block_role(block, page_blocks=[block])
    assert role.role == "frontmatter_support"
```

- [ ] **Step 2: Add focused failing document tests for same-page ref/body and backmatter promotion**

```python
def test_same_page_conclusion_stays_in_body_zone_before_reference_tail() -> None:
    blocks = [
        {"block_id": "c", "page": 7, "seed_role": "section_heading", "text": "Conclusion", "bbox": [80, 120, 420, 180]},
        {"block_id": "g", "page": 7, "seed_role": "body_paragraph", "text": "I wish to express my gratitude", "bbox": [80, 220, 920, 320]},
        {"block_id": "refs", "page": 7, "seed_role": "reference_heading", "text": "References", "bbox": [80, 1080, 360, 1140]},
        {"block_id": "r1", "page": 7, "seed_role": "reference_item", "text": "1 Buckland-Wright JC...", "bbox": [80, 1180, 960, 1260]},
    ]
    doc, normalized = normalize_document_structure(blocks)
    by_id = {b["block_id"]: b for b in normalized}
    assert by_id["c"]["zone"] == "body_zone"
    assert by_id["g"]["role"] == "backmatter_body"


def test_backmatter_heading_candidate_promotes_when_post_reference_tail_is_confirmed() -> None:
    blocks = [
        {"block_id": "refs", "page": 25, "seed_role": "reference_heading", "text": "References"},
        {"block_id": "r1", "page": 25, "seed_role": "reference_item", "text": "[1] ref"},
        {"block_id": "coi", "page": 25, "seed_role": "backmatter_heading_candidate", "text": "Conflict of Interest"},
        {"block_id": "coi_body", "page": 25, "seed_role": "body_paragraph", "text": "All authors declare no conflict."},
    ]
    doc, normalized = normalize_document_structure(blocks)
    by_id = {b["block_id"]: b for b in normalized}
    assert by_id["coi"]["role"] == "backmatter_heading"
    assert by_id["coi_body"]["role"] == "backmatter_body"
```

- [ ] **Step 3: Add focused failing render tests for abstract fallback and reader-status visibility**

```python
def test_render_fulltext_renders_abstract_body_without_document_structure() -> None:
    markdown = render_fulltext_markdown(
        structured_blocks=[
            {"role": "abstract_heading", "text": "", "render_default": True, "page": 1},
            {"role": "abstract_body", "text": "This is the abstract body text.", "render_default": True, "page": 1},
            {"role": "section_heading", "text": "1 Introduction", "render_default": True, "page": 1},
        ],
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )
    assert "## Abstract" in markdown
    assert "This is the abstract body text." in markdown


def test_reader_visible_statuses_are_emitted_in_markdown_contract() -> None:
    markdown = render_fulltext_markdown(
        structured_blocks=[{"block_id": "a", "page": 1, "role": "body_paragraph", "text": "Some body text.", "render_default": True}],
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=1,
        reader_payload={
            "reader_figures": [
                {"reader_figure_id": "fig_reader_0", "figure_number": 0, "block_id": "fig_0", "page": 1, "page_coords": {"x": 0, "y": 0, "width": 10, "height": 10}, "reader_status": "EXACT_MATCH", "consumed_caption_block_ids": []},
            ]
        },
    )
    assert "EXACT_MATCH" in markdown
```

- [ ] **Step 4: Add focused failing sync dispatch test for unbound `ocr_runtime_summary`**

```python
def test_selection_sync_dispatch_initializes_ocr_runtime_summary(...) -> None:
    result = run_selection_sync(...)
    assert "ocr_runtime" in result
```

- [ ] **Step 5: Run the targeted tests to verify they fail for the expected reasons**

Run:
`python -m pytest tests/test_ocr_roles.py tests/test_ocr_document.py tests/test_ocr_rendering.py tests/test_cli_worker_dispatch.py -k "review or buckland or correspondence or conclusion or gratitude or backmatter_heading_candidate or abstract_body_without_document_structure or reader_visible_statuses or selection_sync_dispatch" -v --tb=short`

Expected:
- FAIL on `REVIEW -> paper_title`
- FAIL on `Buckland-Wright -> unknown_structural`
- FAIL on `Correspondence -> frontmatter_noise`
- FAIL on Conclusion/gratitude zone assertions
- FAIL on backmatter candidate promotion assertions
- FAIL on abstract-body fallback render
- FAIL on reader-status visibility
- FAIL on `ocr_runtime_summary` unbound error

---

### Task 2: Fix Page-1 Article-Type Labels And Narrow The Guard

**Files:**
- Modify: `paperforge/worker/ocr_roles.py`
- Test: `tests/test_ocr_roles.py`

- [ ] **Step 1: Add a narrow article-type label set and exact-match guard**

```python
_PAGE1_ARTICLE_TYPE_LABELS = frozenset(
    {
        "review",
        "review article",
        "research article",
        "original article",
        "case report",
        "brief communication",
        "rapid communication",
    }
)
```

- [ ] **Step 2: Route exact article-type labels to frontmatter noise only in the safe position**

```python
if (
    raw_label == "paragraph_title"
    and lower in _PAGE1_ARTICLE_TYPE_LABELS
    and (block.get("page") or 1) == 1
):
    return RoleAssignment(
        role="frontmatter_noise",
        confidence=0.8,
        evidence=[f"page-1 article-type label: {lower}"],
    )
```

- [ ] **Step 3: Keep the guard exact-match only — do not use substring checks**

```python
# Good: lower in {"review"}
# Bad: "review" in lower
```

- [ ] **Step 4: Run the page-1 article-type tests**

Run:
`python -m pytest tests/test_ocr_roles.py -k "review_article_label" -v --tb=short`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_roles.py tests/test_ocr_roles.py
git commit -m "fix: narrow page-1 article-type label handling"
```

---

### Task 3: Fix Page-1 Author Byline And Correspondence Support Routing

**Files:**
- Modify: `paperforge/worker/ocr_roles.py`
- Modify: `paperforge/worker/ocr_metadata.py`
- Test: `tests/test_ocr_roles.py`

- [ ] **Step 1: Extend author-byline detection for initial-lastname order**

```python
_INITIAL_LASTNAME_PATTERN = re.compile(
    r"^(?:[A-Z]\s*){1,3}[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+)?$"
)

def _looks_like_initial_lastname_byline(text: str) -> bool:
    compact = " ".join(text.split())
    return bool(_INITIAL_LASTNAME_PATTERN.fullmatch(compact))
```

- [ ] **Step 2: Use the new helper inside the page-1 author-byline branch**

```python
_is_author_byline = (
    (
        re.search(r"&|,.*,", text)
        or _seems_like_authors(text)
        or _looks_like_initial_lastname_byline(text)
    )
    and len(text.split()) <= 15
    and not _has_heading_numbering(text)
    ...
)
```

- [ ] **Step 3: Route page-1 correspondence footnotes to `frontmatter_support` instead of noise**

```python
if raw_label == "footnote" and page_num == 1:
    lower_txt = text.lower()
    if lower_txt.startswith(("correspondence", "corresponding author", "address for correspondence")):
        return RoleAssignment(
            role="frontmatter_support",
            confidence=0.75,
            evidence=[f"page-1 correspondence footnote: {text[:60]}"],
        )
```

- [ ] **Step 4: Keep DOI / received / accepted / published footnotes as noise**

```python
if raw_label == "footnote" and page_num == 1:
    if lower_txt.startswith(("doi", "received", "accepted", "published", "copyright")):
        return RoleAssignment(... role="frontmatter_noise" ...)
```

- [ ] **Step 5: Run targeted CAQ role tests**

Run:
`python -m pytest tests/test_ocr_roles.py -k "buckland or correspondence" -v --tb=short`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_roles.py paperforge/worker/ocr_metadata.py tests/test_ocr_roles.py
git commit -m "fix: improve page-1 author and correspondence routing"
```

---

### Task 4: Keep Sidebar Labels Safe Without Letting Them Corrupt Nearby Blocks

**Files:**
- Modify: `paperforge/worker/ocr_roles.py`
- Test: `tests/test_ocr_roles.py`
- Test: `tests/test_ocr_rendering.py`

- [ ] **Step 1: Use only narrow, exact sidebar heading matches**

```python
if lower in {"highlights", "key points"} and page_num > 1:
    return RoleAssignment(
        role="structured_insert_candidate",
        confidence=0.7,
        evidence=[f"structured insert label: {lower}"],
    )
```

- [ ] **Step 2: Explicitly do not add generic tokens like `box` or `summary`**

```python
# Intentionally excluded: "box", "summary"
# Reason: too ambiguous, risks swallowing normal subsection headings.
```

- [ ] **Step 3: Add a regression test that the label does not disturb surrounding body order even if promotion never happens**

```python
def test_highlights_label_does_not_swallow_following_body_paragraphs() -> None:
    blocks = [
        {"block_id": "h", "page": 2, "raw_label": "paragraph_title", "text": "Highlights"},
        {"block_id": "b1", "page": 2, "raw_label": "text", "text": "Important point one."},
        {"block_id": "b2", "page": 2, "raw_label": "text", "text": "Important point two."},
    ]
    # Assert b1/b2 still render in-order and are not reclassified as headings.
```

- [ ] **Step 4: Run the sidebar safety tests**

Run:
`python -m pytest tests/test_ocr_roles.py tests/test_ocr_rendering.py -k "highlights" -v --tb=short`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_roles.py tests/test_ocr_roles.py tests/test_ocr_rendering.py
git commit -m "fix: narrow sidebar heading routing"
```

---

### Task 5: Fix Same-Page Reference/Body Zone Conflict For CAQ Page 7

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_document.py`

- [ ] **Step 1: Write the failing same-page zone regression**

```python
def test_same_page_reference_start_does_not_blank_preceding_conclusion_heading() -> None:
    ...
    assert by_id["c"]["zone"] == "body_zone"
```

- [ ] **Step 2: Change reference-zone assignment to split by vertical boundary, not whole-page ownership**

```python
if page == references_start_page:
    ref_heading_top = _block_y_top(reference_heading_block)
    if _block_y_bottom(block) <= ref_heading_top:
        keep_in_body_zone(block)
    else:
        assign_reference_zone(block)
```

- [ ] **Step 3: Make gratitude-like non-reference tail text after the reference heading enter `tail_nonref_hold_zone`**

```python
if page == references_start_page and _block_y_top(block) > ref_heading_top:
    if role in {"body_paragraph", "section_heading", "subsection_heading"} and not _is_reference_item_candidate(block):
        block["zone"] = "tail_nonref_hold_zone"
```

- [ ] **Step 4: Let tail non-reference body in that zone normalize to `backmatter_body`**

```python
if block.get("zone") == "tail_nonref_hold_zone" and block.get("role") == "body_paragraph":
    block["role"] = "backmatter_body"
```

- [ ] **Step 5: Run targeted document tests**

Run:
`python -m pytest tests/test_ocr_document.py -k "same_page_reference_start or gratitude" -v --tb=short`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_document.py tests/test_ocr_document.py
git commit -m "fix: split same-page body and reference tail zones"
```

---

### Task 6: Promote Confirmed Backmatter Candidates Without Paper-Specific Patches

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_structural_gate.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_structural_gate.py`

- [ ] **Step 1: Add a document-level promotion rule for candidate headings followed by backmatter-like body**

```python
if block.get("role") == "backmatter_heading_candidate":
    next_body = _next_nonempty_block_same_page(blocks, idx)
    if next_body and next_body.get("role") in {"body_paragraph", "backmatter_body"}:
        if _looks_like_tail_body(next_body):
            block["role"] = "backmatter_heading"
```

- [ ] **Step 2: Normalize following body paragraphs in the same local cluster to `backmatter_body`**

```python
if current_heading_role == "backmatter_heading":
    for follower in follower_blocks:
        if follower.get("role") == "body_paragraph":
            follower["role"] = "backmatter_body"
```

- [ ] **Step 3: Keep the rule generic — text evidence + local follower evidence only**

```python
# No paper-key checks
# No literal page-number checks
# Promotion must depend on candidate heading role + nearby tail-like body.
```

- [ ] **Step 4: Run the backmatter promotion tests**

Run:
`python -m pytest tests/test_ocr_document.py tests/test_ocr_structural_gate.py -k "backmatter_heading_candidate or conflict of interest or acknowledgments or table and figure captions" -v --tb=short`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_document.py paperforge/worker/ocr_structural_gate.py tests/test_ocr_document.py tests/test_ocr_structural_gate.py
git commit -m "fix: promote confirmed backmatter heading candidates"
```

---

### Task 7: Normalize Biography Sections As Tail Backmatter, Not References

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_document.py`

- [ ] **Step 1: Add a failing biography regression using the DW pattern**

```python
def test_biography_section_after_references_is_backmatter_not_reference_items() -> None:
    ...
    assert by_id["bio_heading"]["role"] == "backmatter_heading"
    assert by_id["bio_1"]["role"] == "backmatter_body"
```

- [ ] **Step 2: Detect biography container headings after references**

```python
_BIOGRAPHY_HEADINGS = {"biographies", "author biographies", "authors' biographies"}
if lower_txt in _BIOGRAPHY_HEADINGS and page_num >= references_start_page:
    block["role"] = "backmatter_heading"
```

- [ ] **Step 3: Convert `reference_item` to `backmatter_body` when the text looks like a biography sentence cluster**

```python
if block.get("role") == "reference_item" and _looks_like_biography_text(block.get("text", "")):
    if block.get("zone") == "post_reference_backmatter_zone":
        block["role"] = "backmatter_body"
```

- [ ] **Step 4: Add a page-mapping helper test for the missing Ami Yoo / Eunpyo Choi anchors**

```python
def test_biography_page_mapping_uses_actual_block_page_not_expectation_shortcut() -> None:
    ...
```

- [ ] **Step 5: Run the biography tests**

Run:
`python -m pytest tests/test_ocr_document.py -k "biograph" -v --tb=short`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_document.py tests/test_ocr_document.py
git commit -m "fix: normalize biography tail blocks as backmatter"
```

---

### Task 8: Fix The Two Pre-Existing Render Contract Failures

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_rendering.py`

- [ ] **Step 1: Render abstract body blocks even when `document_structure` is absent**

```python
if role == "abstract_body":
    abstract_lines.append(text)
    continue
```

- [ ] **Step 2: Add a small fallback abstract-span builder inside render when no document structure exists**

```python
if document_structure is None:
    abstract_block_ids = [
        b.get("block_id")
        for b in structured_blocks
        if b.get("role") in {"abstract_heading", "abstract_body"}
    ]
```

- [ ] **Step 3: Make reader-visible status part of the markdown contract, not just embedded child files**

```python
lines.append(f"> **{reader_status}**")
lines.append(f"![[render/figures/{figure_id}.md]]")
```

- [ ] **Step 4: Keep current embed behavior; add status text above embed instead of replacing embed**

```python
# Preserve existing embed consumer behavior.
# Add status label as visible markdown line before the embed.
```

- [ ] **Step 5: Run the render regression tests**

Run:
`python -m pytest tests/test_ocr_rendering.py -k "abstract_before_introduction or reader_visible_statuses" -v --tb=short`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_render.py tests/test_ocr_rendering.py
git commit -m "fix: restore abstract fallback and reader status visibility"
```

---

### Task 9: Fix `ocr_runtime_summary` Initialization In Selection Sync Dispatch

**Files:**
- Modify: `paperforge/services/sync_service.py`
- Test: `tests/test_cli_worker_dispatch.py`

- [ ] **Step 1: Find the branch where `ocr_runtime_summary` is conditionally assigned**

```python
ocr_runtime_summary = {"status": "unknown", "dirty": False, "warnings": []}
```

- [ ] **Step 2: Initialize the variable before branch-specific assignments**

```python
ocr_runtime_summary = {"status": "unknown", "dirty": False, "warnings": []}
if enable_ocr_runtime:
    ocr_runtime_summary = compute_ocr_runtime_summary(...)
```

- [ ] **Step 3: Keep output shape stable for all dispatch callers**

```python
return {
    ...,
    "ocr_runtime": ocr_runtime_summary,
}
```

- [ ] **Step 4: Run the dispatch regression**

Run:
`python -m pytest tests/test_cli_worker_dispatch.py -k "selection_sync_dispatch" -v --tb=short`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/services/sync_service.py tests/test_cli_worker_dispatch.py
git commit -m "fix: initialize sync ocr runtime summary"
```

---

### Task 10: Regenerate Real-Paper Traces And Measure Closure

**Files:**
- Modify: `tests/fixtures/ocr_real_papers/{CAQNW9Q2,DWQQK2YB}/block_trace.csv`
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Regenerate traces from live raw blocks using the canonical script**

Run:
`python tests/fixtures/ocr_real_papers/regenerate_traces.py`

Expected:
- `block_trace.csv` rewritten for `DWQQK2YB`
- `block_trace.csv` rewritten for `CAQNW9Q2`

- [ ] **Step 2: Re-run trace-vs-expectations comparison**

Run:
`python -m pytest tests/test_ocr_trace_vs_expectations.py -v --tb=short -s --timeout=60`

Expected:
- CAQ pass count increases from 19/23
- DW pass count increases from 34/63
- Remaining failures map exactly to documented, still-open categories

- [ ] **Step 3: Update `PROJECT-MANAGEMENT.md` with new pass/fail counts and remaining gaps**

```markdown
### Phase 13: Final gap closure round
- CAQNW9Q2: X/23 PASS
- DWQQK2YB: Y/63 PASS
- Remaining open buckets: ...
```

- [ ] **Step 4: Run the consolidated verification suite**

Run:
`python -m pytest tests/test_ocr_roles.py tests/test_ocr_document.py tests/test_ocr_structural_gate.py tests/test_ocr_figures.py tests/test_ocr_rendering.py tests/test_ocr_v2_structural_regressions.py tests/test_cli_worker_dispatch.py tests/test_ocr_trace_vs_expectations.py -v --tb=short`

Expected:
- All targeted synthetic tests PASS
- Trace-vs-expectations failure set only contains still-open documented gaps (if any)

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/ocr_real_papers/CAQNW9Q2/block_trace.csv tests/fixtures/ocr_real_papers/DWQQK2YB/block_trace.csv PROJECT-MANAGEMENT.md
git commit -m "docs: update OCR closure verification status"
```

---

## Spec Coverage Check

- Covered: CAQ article-type label, CAQ authors, CAQ correspondence support, CAQ same-page conclusion/ref split, CAQ gratitude tail routing.
- Covered: DW Highlights safety, DW backmatter heading promotion, DW biography normalization, DW page-25/page-35 tail handling.
- Covered: pre-existing render failures and sync dispatch failure.
- Covered: regenerate `block_trace.csv` and compare against `expectations.json` after each accepted fix.
- Not covered: TSCKAVIS fixture import into `ocr-v2` (explicitly out of scope for this closure plan).

## Self-Review

- Placeholder scan: no `TODO` / `TBD` placeholders remain.
- Type consistency: all proposed roles match existing code (`frontmatter_noise`, `frontmatter_support`, `structured_insert_candidate`, `backmatter_heading_candidate`, `backmatter_heading`, `backmatter_body`).
- Scope check: plan stays inside one subsystem (OCR-v2 closure + a small sync dispatch regression) and remains merge-focused.

---

Plan complete and saved to `docs/superpowers/plans/2026-06-14-ocr-v2-closure-gap-remediation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
