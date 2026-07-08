# OCR-v2 Unified Close-Out Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the current OCR-v2 close-out pass by removing useless preproof cover page 1 at the structured-block layer, conservatively tightening tail/post-reference cleanup, verifying the branch on the 8 gold papers plus up to 10 targeted vault papers, then rewriting the residual picture and deciding whether figure-group work is truly next.

**Architecture:** Keep the existing OCR-v2 anchor-first pipeline. Make one early filtering change in the structured-block build path so true preproof cover pages never enter document normalization, then make conservative no-damage changes in `ocr_document.py` so tail/post-reference handling preserves valid structure instead of trying to perfect `backmatter_heading` taxonomy. After code changes, run a bounded rebuild/audit pass on the 8 gold fixtures plus a deliberately chosen 10-paper vault sample and use that evidence to update the project trackers and decide whether to reopen figure-group work.

**Tech Stack:** Python 3.14, existing `paperforge.worker` OCR pipeline, pytest, existing rebuild scripts, repo-local audit helpers under `.opencode/skills/paperforge-development/`, vault OCR artifacts.

---

## File Structure

- Modify: `paperforge/worker/ocr_blocks.py`
  - Owns structured-block build flow; add the preproof page-1 drop before document normalization.
- Modify: `paperforge/worker/ocr_document.py`
  - Owns conservative tail/post-reference cleanup behavior.
- Modify: `tests/test_ocr_document.py`
  - Owns document-pipeline and post-reference regression coverage.
- Modify: `tests/test_ocr_real_paper_regressions.py`
  - Owns production-path replay checks on known papers.
- Modify: `tests/fixtures/ocr_real_papers/DWQQK2YB/expectations.json`
  - Update only if post-fix visual truth proves the current expectations are stale.
- Modify: `tests/fixtures/ocr_real_papers/coverage_manifest.json`
  - Record any extra verification-sample metadata only if the existing manifest is the cleanest place to note layout coverage.
- Modify: `project/current/ocr-error-root-cause-fix-queue.md`
  - Write back the final measured residual summary.
- Modify: `PROJECT-MANAGEMENT.md`
  - Record what the unified close-out pass fixed and what remains.

---

### Task 1: Lock Preproof-Drop And Conservative Tail Cleanup With Red Tests

**Files:**
- Modify: `tests/test_ocr_document.py`
- Modify: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Add a unit test for preproof page-1 removal**

Add this test to `tests/test_ocr_document.py` or the nearest structured/document pipeline test section:

```python
def test_preproof_cover_page_one_is_dropped_before_document_normalization() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "DWTEST",
            "block_id": "p1_preproof",
            "page": 1,
            "text": "Journal Pre-proof",
            "block_content": "Journal Pre-proof",
            "raw_label": "text",
            "block_label": "text",
            "marker_signature": {"type": "preproof_marker"},
            "bbox": [80, 100, 600, 180],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "DWTEST",
            "block_id": "p1_pii",
            "page": 1,
            "text": "PII: S1234-5678(26)00001-2",
            "block_content": "PII: S1234-5678(26)00001-2",
            "raw_label": "text",
            "block_label": "text",
            "marker_signature": {"type": "none"},
            "bbox": [80, 240, 700, 300],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "DWTEST",
            "block_id": "p2_title",
            "page": 2,
            "text": "Real Article Title",
            "block_content": "Real Article Title",
            "raw_label": "paragraph_title",
            "block_label": "paragraph_title",
            "marker_signature": {"type": "none"},
            "bbox": [80, 120, 800, 190],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    structured, _doc = build_structured_blocks(raw_blocks, source_metadata={"title": "Real Article Title"})
    pages = {int(b.get("page", 0) or 0) for b in structured}
    assert 1 not in pages
    assert 2 in pages
```

- [ ] **Step 2: Add a non-preproof guard test**

Still in `tests/test_ocr_document.py`, add:

```python
def test_non_preproof_page_one_is_not_dropped() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "OKTEST",
            "block_id": "p1_title",
            "page": 1,
            "text": "A normal paper title",
            "block_content": "A normal paper title",
            "raw_label": "paragraph_title",
            "block_label": "paragraph_title",
            "marker_signature": {"type": "none"},
            "bbox": [80, 120, 900, 200],
            "page_width": 1200,
            "page_height": 1600,
        }
    ]

    structured, _doc = build_structured_blocks(raw_blocks, source_metadata={"title": "A normal paper title"})
    pages = {int(b.get("page", 0) or 0) for b in structured}
    assert 1 in pages
```

- [ ] **Step 3: Add a conservative tail cleanup regression**

Add this test to `tests/test_ocr_document.py`:

```python
def test_post_reference_plain_heading_stays_heading_not_backmatter_taxonomy_upgrade() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {"block_id": "refs", "page": 12, "seed_role": "reference_heading", "text": "References", "bbox": [80, 900, 340, 960]},
        {"block_id": "r1", "page": 12, "seed_role": "reference_item", "text": "[1] First ref", "bbox": [80, 1000, 960, 1080]},
        {"block_id": "bio_h", "page": 13, "seed_role": "subsection_heading", "text": "Biographies", "bbox": [80, 120, 380, 180]},
        {"block_id": "bio_b", "page": 13, "seed_role": "body_paragraph", "text": "Author A received the PhD degree in 2015.", "bbox": [80, 220, 980, 320]},
    ]

    _doc, normalized = normalize_document_structure(blocks)
    by_id = {b["block_id"]: b for b in normalized}
    assert by_id["bio_h"]["role"] in {"subsection_heading", "backmatter_heading"}
    assert by_id["bio_b"]["role"] != "unknown_structural"
```

- [ ] **Step 4: Add a production-path DW regression that expects page 1 to disappear**

In `tests/test_ocr_real_paper_regressions.py`, replace the old preproof-frontmatter expectation with:

```python
def test_dwqqk2yb_preproof_page_one_is_absent_from_structured_blocks(tmp_path: Path) -> None:
    result = replay_production_pipeline("DWQQK2YB", tmp_path)
    blocks = result["structured_blocks"]
    assert not any(int(b.get("page", 0) or 0) == 1 for b in blocks)
```

- [ ] **Step 5: Run the focused red tests**

Run: `python -m pytest tests/test_ocr_document.py -k "preproof or post_reference_plain_heading" -v --tb=short`

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "dwqqk2yb_preproof_page_one" -v --tb=short`

Expected: FAIL until the implementation lands.

- [ ] **Step 6: Commit the failing tests only**

```bash
git add tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "test: lock unified OCR close-out regressions"
```

---

### Task 2: Drop Confident Preproof Cover Page 1 At The Structured-Block Layer

**Files:**
- Modify: `paperforge/worker/ocr_blocks.py`
- Test: `tests/test_ocr_document.py`

- [ ] **Step 1: Add a narrow helper for preproof cover-page detection**

Near `build_structured_blocks()` helpers in `paperforge/worker/ocr_blocks.py`, add:

```python
def _is_confident_preproof_cover_page(blocks: list[dict], page: int) -> bool:
    if page != 1:
        return False
    page_blocks = [b for b in blocks if int(b.get("page", 0) or 0) == page]
    if not page_blocks:
        return False

    marker_hits = 0
    noisy_cover_hits = 0
    useful_heading_hits = 0

    for block in page_blocks:
        marker_type = str((block.get("marker_signature") or {}).get("type") or "")
        text = str(block.get("text") or block.get("block_content") or "").strip().lower()
        raw_label = str(block.get("raw_label") or block.get("block_label") or "")
        if marker_type == "preproof_marker":
            marker_hits += 1
        if any(token in text for token in ("journal pre-proof", "pre-proof", "pii:", "accepted date", "published by elsevier")):
            noisy_cover_hits += 1
        if raw_label == "paragraph_title" and len(text.split()) >= 4 and "pre-proof" not in text:
            useful_heading_hits += 1

    return marker_hits >= 1 and noisy_cover_hits >= 2 and useful_heading_hits == 0
```

- [ ] **Step 2: Filter page 1 before document normalization**

In `build_structured_blocks()`, after the initial structured row shaping and before `normalize_document_structure()` runs, add:

```python
    if _is_confident_preproof_cover_page(structured_blocks, 1):
        structured_blocks = [
            block for block in structured_blocks
            if int(block.get("page", 0) or 0) != 1
        ]
```

- [ ] **Step 3: Make the filter self-documenting in evidence/debug metadata**

Add a small debug note so dropped-page behavior is traceable during local debugging:

```python
        for block in structured_blocks:
            if int(block.get("page", 0) or 0) == 2:
                block.setdefault("evidence", []).append("page_1_preproof_cover_dropped_upstream")
                break
```

- [ ] **Step 4: Run focused tests until green**

Run: `python -m pytest tests/test_ocr_document.py -k "preproof_cover_page_one or non_preproof_page_one" -v --tb=short`

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "dwqqk2yb_preproof_page_one" -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_blocks.py tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: drop preproof cover page one before OCR normalization"
```

---

### Task 3: Tighten Tail/Post-Reference Cleanup Conservatively

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_document.py`

- [ ] **Step 1: Add a helper that recognizes explicit backmatter-body evidence only**

Near `_exclude_tail_nonref_from_body_flow()` in `paperforge/worker/ocr_document.py`, keep the helper deliberately small:

```python
def _looks_like_backmatter_body_text(text: str) -> bool:
    lower = text.lower()
    markers = (
        "conflict of interest",
        "declaration",
        "publisher",
        "author contributions",
        "funding",
        "acknowledg",
        "data availability",
        "ethics",
        "supplement",
    )
    return any(marker in lower for marker in markers)
```

- [ ] **Step 2: Make `_exclude_tail_nonref_from_body_flow()` preserve ordinary prose by default**

Replace the broad conversion logic with:

```python
        if not _looks_like_backmatter_body_text(text):
            continue
```

and keep the role rewrite only for blocks that pass the helper.

- [ ] **Step 3: Keep post-reference normalization from damaging object-adjacent structure**

Inside `_normalize_backmatter_roles_after_boundary()`, add a preserve set and skip conversion for those roles:

```python
_POST_REF_PRESERVE_ROLES = {
    "figure_inner_text",
    "figure_caption",
    "figure_caption_candidate",
    "table_caption",
    "table_caption_candidate",
    "media_asset",
    "table_html",
}
```

and use:

```python
if block.get("role") in _POST_REF_PRESERVE_ROLES:
    continue
```

- [ ] **Step 4: Avoid aggressive heading taxonomy expansion**

Do not add a large phrase list for `backmatter_heading`. Instead, keep valid `section_heading` / `subsection_heading` / `sub_subsection_heading` intact when the current evidence already supports them.

Use this conservative guard in the normalization branch:

```python
if block.get("role") in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
    continue
```

- [ ] **Step 5: Run focused tests until green**

Run: `python -m pytest tests/test_ocr_document.py -k "tail_nonref or backmatter or post_reference_plain_heading" -v --tb=short`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_document.py tests/test_ocr_document.py
git commit -m "fix: conservatively tighten OCR tail and post-reference cleanup"
```

---

### Task 4: Run The Bounded Rebuild And Choose The 10-Paper Expansion Sample

**Files:**
- Modify if needed: `tests/fixtures/ocr_real_papers/coverage_manifest.json`
- Reference: vault OCR store under `D:/L/OB/Literature-hub/System/PaperForge/ocr/`

- [ ] **Step 1: Rebuild the 8 gold papers first**

Run:

```bash
python scripts/dev/ocr_rebuild_paper.py CAQNW9Q2 DWQQK2YB TSCKAVIS A8E7SRVS K7R8PEKW 6FGDBFQN SAN9AYVR 2GN9LMCW
```

Expected: refreshed structured blocks, document structure, render output, and trace artifacts for the gold set.

- [ ] **Step 2: Pick up to 10 extra vault papers by layout class**

Use the vault OCR inventory plus existing audit knowledge to choose up to 10 papers that cover these classes:

```text
1. preproof cover page
2. same-page body/reference split
3. biography/backmatter tail
4. multi-panel figure
5. narrow-caption or side-caption figure
6. table-heavy layout
7. publisher margin-noise layout
```

Write the chosen keys into your working notes or `coverage_manifest.json` only if that file is already the cleanest coverage ledger.

- [ ] **Step 3: Rebuild the 10 selected vault papers**

Run:

```bash
python scripts/dev/ocr_rebuild_paper.py <KEY1> <KEY2> <KEY3> <KEY4> <KEY5> <KEY6> <KEY7> <KEY8> <KEY9> <KEY10>
```

Expected: the bounded sample is rebuilt from current code, without opening a full-vault rebuild loop.

- [ ] **Step 4: Refresh audit artifacts for the selected papers**

For each selected key, run:

```bash
python .opencode/skills/paperforge-development/scripts/ocr_truth_audit.py <KEY> --source-root D:/L/OB/Literature-hub/System/PaperForge/ocr --mode high-risk --refresh-artifacts
```

Expected: refreshed high-risk audit helper outputs without manual truth loss.

- [ ] **Step 5: Commit only if coverage metadata changed**

If you updated `tests/fixtures/ocr_real_papers/coverage_manifest.json`, commit it:

```bash
git add tests/fixtures/ocr_real_papers/coverage_manifest.json
git commit -m "docs: record bounded OCR close-out verification sample"
```

If no tracked metadata changed, skip this commit.

---

### Task 5: Regressions, Truth Updates, And Residual Rewrite

**Files:**
- Modify: `tests/fixtures/ocr_real_papers/DWQQK2YB/expectations.json`
- Modify: `project/current/ocr-error-root-cause-fix-queue.md`
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Run the deterministic regression suite**

Run:

```bash
python -m pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py tests/test_ocr_roles.py tests/test_ocr_layout_first_regressions.py -v --tb=short
```

Expected: green or improved close-out gates for the touched areas.

- [ ] **Step 2: Update expectations only where visual truth proves the old truth is stale**

If DW expectations still mention page-1 preproof content after the drop, update the relevant `tests/fixtures/ocr_real_papers/DWQQK2YB/expectations.json` entries so they stop asserting the removed cover page.

Use this pattern only when justified:

```json
{
  "text_contains": "Real article title",
  "expected_role": "paper_title",
  "expected_zone": "frontmatter_main_zone",
  "notes": "Updated after structured-layer preproof page-1 drop; visual audit confirms page 1 is disposable cover content."
}
```

- [ ] **Step 3: Re-run the high-risk diff audit on touched papers**

Run for the gold papers most affected by this pass and for the newly selected sample papers:

```bash
python .opencode/skills/paperforge-development/scripts/diff_audit.py DWQQK2YB --source-root D:/L/OB/Literature-hub/System/PaperForge/ocr --audit-root D:/L/Med/Research/99_System/LiteraturePipeline/github-release/audit
```

Repeat for CAQ and any newly selected papers where the current pass changed outputs materially.

- [ ] **Step 4: Rewrite the residual summary from evidence**

Update `project/current/ocr-error-root-cause-fix-queue.md` and `PROJECT-MANAGEMENT.md` with:

```md
### Unified Close-Out Pass Result (2026-06-17)

- What changed: preproof cover page 1 is dropped before normalization; tail/post-reference cleanup is more conservative
- Verification scope: 8 gold papers + up to 10 targeted vault papers
- Result: [fill with measured residual delta after rerun]
- Remaining document-structure residuals: [measured list]
- Remaining figure-ownership residuals: [measured list]
- Decision: [state whether figure-group is now the dominant blocker]
```

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/ocr_real_papers/DWQQK2YB/expectations.json project/current/ocr-error-root-cause-fix-queue.md PROJECT-MANAGEMENT.md
git commit -m "docs: record unified OCR close-out pass results"
```

---

### Task 6: Figure-Group Decision Gate

**Files:**
- Modify if needed: `project/current/ocr-v2-closeout-priority.md`
- Modify if needed: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Compare residual category totals after the bounded audit pass**

Build a simple decision table from the refreshed audit results:

```text
document_structure_residuals = ?
truth_or_expectation_residuals = ?
figure_ownership_residuals = ?
```

Only use measured post-pass counts.

- [ ] **Step 2: Decide whether figure-group work is now dominant**

Use this rule:

```text
Reopen group-first figure inventory only if figure ownership is the largest stable remaining class
and it appears across more than one paper/layout family in the bounded sample.
```

- [ ] **Step 3: Write the decision back to the active priority file if it changes**

If figure-group becomes the next dominant blocker, update `project/current/ocr-v2-closeout-priority.md` and `PROJECT-MANAGEMENT.md` to say so explicitly. If it does not, update them to keep the branch on the current close-out/verification path.

- [ ] **Step 4: Commit only if a tracked priority file changed**

```bash
git add project/current/ocr-v2-closeout-priority.md PROJECT-MANAGEMENT.md
git commit -m "docs: update OCR close-out next-step decision"
```

Skip the commit if no tracked priority files changed.

---

## Self-Review

- Spec coverage: this plan covers every section of the approved unified spec: preproof page-1 drop, conservative tail cleanup, bounded 8+10 verification, residual write-back, and figure-group decision gate.
- Placeholder scan: no `TODO`, `TBD`, or unresolved implementation placeholders remain in the task steps.
- Type consistency: the plan uses existing seams only (`build_structured_blocks`, `normalize_document_structure`, `_exclude_tail_nonref_from_body_flow`, `_normalize_backmatter_roles_after_boundary`, `replay_production_pipeline`, `ocr_rebuild_paper.py`, `ocr_truth_audit.py`, `diff_audit.py`) and does not invent a second implementation track.

Plan complete and saved to `docs/superpowers/plans/2026-06-17-ocr-v2-closeout-single-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
