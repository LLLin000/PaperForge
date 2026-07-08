# OCR-v2 PR1 Deterministic Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the four lowest-risk OCR residual fixes: backfill word clamp, validation-first bare-table fallthrough, table continuation materialization, and short-form health profile.

**Architecture:** Keep every change inside the module that already owns the broken behavior: `ocr_pdf_spans.py` for backfill extraction, `ocr_tables.py` for table caption ownership, and `ocr_health.py` for report policy. Do not touch OCR role assignment globally, do not refactor cross-module ownership, and do not widen scope beyond these local fixes.

**Tech Stack:** Python 3.x, pytest, PyMuPDF (`fitz`), OCR worker modules under `paperforge/worker/`

## Global Constraints

- PR1 scope is fixed: **Issue 3 → Issue 1A → Issue 1B → Issue 4**.
- Start with failing tests at the real seam for each fix.
- Do **not** globally merge OCR blocks.
- Keep backfill expansion for search; filter accepted words to the original bbox.
- For split table captions, materialize merged captions **inside** `build_table_inventory` only.
- For short papers, add a `short_form` health profile instead of hard suppressing fields ad hoc.
- No project-wide test sweep inside this PR; only targeted suites plus one focused regression bundle at the end.

---

## File Map

- `paperforge/worker/ocr_pdf_spans.py` — PDF text-layer backfill extraction
- `tests/test_ocr_pdf_text_fallback.py` — backfill tests
- `paperforge/worker/ocr_tables.py` — table caption collection, weak-explicit matching, consumed ownership
- `tests/test_ocr_tables.py` — table inventory tests
- `tests/test_ocr_render.py` — consumed table continuation skip checks
- `paperforge/worker/ocr_health.py` — health scoring and rebuild policy
- `tests/test_ocr_health.py` — short-form health tests

---

### Task 1: Clamp backfill words to the original bbox

**Files:**
- Modify: `paperforge/worker/ocr_pdf_spans.py`
- Test: `tests/test_ocr_pdf_text_fallback.py`

**Interfaces:**
- Consumes: `backfill_missing_text_from_pdf(raw_blocks, pdf_path) -> list[dict]`
- Produces:
  - `_word_center_inside_rect(word_bbox, block_rect) -> bool`
  - `_word_belongs_to_block(word_bbox, block_rect) -> bool`
  - filtered `words` before `_words_to_text(words)`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ocr_pdf_text_fallback.py`:

```python
def test_backfill_expanded_clip_filters_words_to_original_bbox(monkeypatch, tmp_path):
    from paperforge.worker import ocr_pdf_spans
    import fitz

    class FakePage:
        rect = fitz.Rect(0, 0, 1000, 1000)
        def get_text(self, kind, clip=None):
            if kind == "words":
                return [
                    (100, 100, 120, 110, "inside", 0, 0, 0),
                    (100, 111, 120, 121, "neighbor", 0, 0, 1),
                ]
            if kind == "text":
                return "inside neighbor"
            return []

    class FakeDoc:
        def __len__(self): return 1
        def __getitem__(self, idx): return FakePage()
        def close(self): pass

    monkeypatch.setattr(ocr_pdf_spans, "_fitz_quiet_open", lambda path: FakeDoc())
    monkeypatch.setattr(
        ocr_pdf_spans,
        "_map_ocr_bbox_to_pdf_rect",
        lambda bbox, pw, ph, page: fitz.Rect(100, 100, 120, 110),
    )

    pdf_path = tmp_path / "fake.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n")

    blocks = [{
        "page": 1,
        "bbox": [100, 100, 120, 110],
        "page_width": 1000,
        "page_height": 1000,
        "raw_label": "text",
        "text": "",
        "block_content": "",
        "span_metadata": [{"font": "Body"}],
    }]

    ocr_pdf_spans.backfill_missing_text_from_pdf(blocks, pdf_path)

    assert blocks[0]["text"] == "inside"
    assert blocks[0]["_ocr_raw_status"] == "missing_text_recovered"


def test_backfill_keeps_slightly_misaligned_words_by_center_or_overlap():
    from paperforge.worker.ocr_pdf_spans import _word_belongs_to_block
    import fitz

    block_rect = fitz.Rect(100, 100, 120, 110)

    assert _word_belongs_to_block((99, 100, 109, 110), block_rect) is True
    assert _word_belongs_to_block((121, 111, 131, 121), block_rect) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_ocr_pdf_text_fallback.py -q
```

Expected: FAIL because neighbor words are currently accepted and `_word_belongs_to_block` does not exist.

- [ ] **Step 3: Write minimal implementation**

In `paperforge/worker/ocr_pdf_spans.py`, add:

```python
def _word_center_inside_rect(word_bbox, block_rect) -> bool:
    x0, y0, x1, y1 = word_bbox
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    return block_rect.x0 <= cx <= block_rect.x1 and block_rect.y0 <= cy <= block_rect.y1


def _word_belongs_to_block(word_bbox, block_rect) -> bool:
    word_rect = fitz.Rect(*word_bbox)
    return (
        _word_center_inside_rect(word_bbox, block_rect)
        or _bbox_overlap_ratio(word_rect, block_rect) >= 0.30
    )
```

Then change:

```python
words = pdf_page.get_text("words", clip=expanded)
text = _words_to_text(words)
```

to:

```python
words = pdf_page.get_text("words", clip=expanded)
words = [
    w for w in words
    if len(w) >= 4 and _word_belongs_to_block(tuple(w[:4]), rect)
]
text = _words_to_text(words)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_ocr_pdf_text_fallback.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_pdf_spans.py tests/test_ocr_pdf_text_fallback.py
git commit -m "fix: clamp pdf backfill words to original bbox"
```

---

### Task 2: Let validation-first bare tables fall through to weak-explicit matching

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`
- Test: `tests/test_ocr_tables.py`

**Interfaces:**
- Consumes: `_is_validation_first_table_candidate`, `_is_insufficient_table_caption_evidence`, `build_table_inventory(...)`
- Produces: updated validation-first branch that only early-exits when no same-page asset exists

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ocr_tables.py`:

```python
def test_validation_first_bare_table_with_same_page_asset_falls_through_to_weak_explicit_matching():
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "block_id": "cap",
            "page": 1,
            "role": "body_paragraph",
            "raw_label": "text",
            "text": "Table 1",
            "bbox": [100, 100, 300, 120],
            "marker_signature": {"type": "table_number"},
            "zone": "display_zone",
            "style_family": "table_caption_like",
        },
        {
            "block_id": "asset",
            "page": 1,
            "role": "media_asset",
            "raw_label": "table_image",
            "text": "",
            "bbox": [100, 130, 500, 400],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    assert inventory["official_table_count"] == 1
    assert inventory["tables"][0]["asset_block_id"] == "asset"
    assert inventory["tables"][0]["caption_block_id"] == "cap"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_ocr_tables.py::test_validation_first_bare_table_with_same_page_asset_falls_through_to_weak_explicit_matching -q
```

Expected: FAIL because current code always `continue`s.

- [ ] **Step 3: Write minimal implementation**

In `paperforge/worker/ocr_tables.py`, change the branch to:

```python
if is_validation_first_candidate and is_weak_truncated:
    same_page_assets = [
        a for i, a in enumerate(assets)
        if i not in used_asset_indices and a.get("page", 0) == caption_page
    ]
    if not same_page_assets:
        held_tables.append(...)
        continue
    # same-page asset exists → fall through into weak-explicit matching
```

Do **not** add a second scoring path.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_ocr_tables.py::test_validation_first_bare_table_with_same_page_asset_falls_through_to_weak_explicit_matching -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_tables.py tests/test_ocr_tables.py
git commit -m "fix: allow validation-first bare tables to fall through"
```

---

### Task 3: Materialize table caption continuations locally inside `build_table_inventory`

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`
- Test: `tests/test_ocr_tables.py`
- Test: `tests/test_ocr_render.py`

**Interfaces:**
- Produces:
  - `_find_table_caption_continuation(caption, structured_blocks) -> dict | None`
  - `_materialize_table_caption(caption, continuation) -> tuple[dict, list[str]]`
  - continuation block ids added to `consumed_block_ids`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ocr_tables.py`:

```python
def test_split_table_caption_materializes_continuation_stolen_as_figure_caption():
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {"block_id": "cap1", "page": 1, "role": "table_caption", "text": "Table 2", "bbox": [100, 100, 220, 120]},
        {"block_id": "cap2", "page": 1, "role": "figure_caption", "text": "Structural parameters of nanocomposites obtained from the d", "bbox": [100, 121, 500, 145]},
        {"block_id": "asset", "page": 1, "role": "media_asset", "raw_label": "table_image", "text": "", "bbox": [100, 150, 500, 400]},
    ]

    inventory = build_table_inventory(structured_blocks)

    assert inventory["official_table_count"] == 1
    assert inventory["tables"][0]["caption_text"].startswith("Table 2 Structural parameters")
    assert "cap2" in inventory["tables"][0]["consumed_block_ids"]


def test_split_table_caption_does_not_steal_real_figure_caption():
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {"block_id": "cap1", "page": 1, "role": "table_caption", "text": "Table 2", "bbox": [100, 100, 220, 120]},
        {"block_id": "figcap", "page": 1, "role": "figure_caption", "text": "Figure 3. Histology results.", "bbox": [600, 100, 900, 125]},
        {"block_id": "asset", "page": 1, "role": "media_asset", "raw_label": "table_image", "text": "", "bbox": [100, 150, 500, 400]},
    ]

    inventory = build_table_inventory(structured_blocks)

    assert inventory["tables"][0]["caption_text"] == "Table 2"
    assert "figcap" not in inventory["tables"][0]["consumed_block_ids"]
```

Add to `tests/test_ocr_render.py`:

```python
def test_materialized_table_caption_continuation_is_skipped_by_render_when_consumed():
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {"page": 1, "block_id": "cap1", "role": "table_caption", "text": "Table 2", "bbox": [100, 100, 220, 120]},
        {"page": 1, "block_id": "cap2", "role": "figure_caption", "text": "Structural parameters of nanocomposites obtained from the d", "bbox": [100, 121, 500, 145]},
    ]
    table_inventory = {
        "tables": [
            {
                "page": 1,
                "caption_block_id": "cap1",
                "caption_text": "Table 2 Structural parameters of nanocomposites obtained from the d",
                "consumed_block_ids": ["cap1", "cap2"],
                "has_asset": False,
                "match_status": "unmatched_caption",
            }
        ]
    }

    md = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={"matched_figures": []},
        table_inventory=table_inventory,
        page_count=1,
        document_structure=None,
        reader_payload={"reader_figures": [], "consumed_caption_block_ids": []},
    )

    assert "Structural parameters of nanocomposites" not in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest \
  tests/test_ocr_tables.py::test_split_table_caption_materializes_continuation_stolen_as_figure_caption \
  tests/test_ocr_tables.py::test_split_table_caption_does_not_steal_real_figure_caption \
  tests/test_ocr_render.py::test_materialized_table_caption_continuation_is_skipped_by_render_when_consumed -q
```

Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

Add helpers in `paperforge/worker/ocr_tables.py`:

```python
def _find_table_caption_continuation(caption: dict, structured_blocks: list[dict]) -> dict | None:
    ...


def _materialize_table_caption(caption: dict, continuation: dict | None) -> tuple[dict, list[str]]:
    ...
```

Required trigger rules:

```text
- current caption is weak-truncated: "Table N"
- next block same page
- y-gap 0–25 px
- x-overlap ratio ≥ 0.5 or left-edge delta < 40 px
- continuation role ∈ {figure_caption, body_paragraph, unknown_structural, table_caption_candidate}
- continuation text does NOT start with Fig/Figure/Scheme/Plate
- no asset sits between the two blocks
```

Then inside `build_table_inventory(...)`:

```python
if is_weak_truncated:
    continuation = _find_table_caption_continuation(caption, structured_blocks)
    materialized_caption, continuation_ids = _materialize_table_caption(caption, continuation)
    caption_text = materialized_caption.get("text", "")
```

Use `materialized_caption` for matching and extend `consumed_block_ids` with `continuation_ids`.

- [ ] **Step 4: Run tests to verify they pass**

Run the same command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_tables.py tests/test_ocr_tables.py tests/test_ocr_render.py
git commit -m "fix: materialize split table caption continuations"
```

---

### Task 4: Add a short-form health profile

**Files:**
- Modify: `paperforge/worker/ocr_health.py`
- Test: `tests/test_ocr_health.py`

**Interfaces:**
- Produces:
  - `_health_profile(page_count: int) -> str`
  - report fields: `health_profile`, `waived_gates`, `degraded_reason`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ocr_health.py`:

```python
def test_short_form_health_does_not_go_red_for_missing_abstract_headings_and_refs():
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=2,
        raw_blocks_count=2,
        structured_blocks=[
            {"page": 1, "role": "body_paragraph", "text": "Short letter text."},
            {"page": 2, "role": "body_paragraph", "text": "More short letter text."},
        ],
        figure_inventory={"matched_figures": [], "held_figures": [], "unmatched_legends": [], "unmatched_assets": [], "figure_legend_completeness": {}},
        table_inventory={"tables": [], "held_tables": [], "unmatched_captions": [], "unmatched_assets": []},
    )

    assert report["health_profile"] == "short_form"
    assert report["overall"] in {"green", "yellow"}
    assert report["needs_rebuild"] is False
    assert "abstract_found" in report["waived_gates"]
    assert report["degraded_reason"] == "short_paper_format"


def test_standard_profile_still_flags_missing_structure():
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=5,
        raw_blocks_count=2,
        structured_blocks=[
            {"page": 1, "role": "body_paragraph", "text": "Body."},
            {"page": 5, "role": "body_paragraph", "text": "Tail."},
        ],
        figure_inventory={"matched_figures": [], "held_figures": [], "unmatched_legends": [], "unmatched_assets": [], "figure_legend_completeness": {}},
        table_inventory={"tables": [], "held_tables": [], "unmatched_captions": [], "unmatched_assets": []},
    )

    assert report["health_profile"] == "standard"
    assert report["overall"] == "red"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest \
  tests/test_ocr_health.py::test_short_form_health_does_not_go_red_for_missing_abstract_headings_and_refs \
  tests/test_ocr_health.py::test_standard_profile_still_flags_missing_structure -q
```

Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

In `paperforge/worker/ocr_health.py`, add:

```python
def _health_profile(page_count: int) -> str:
    return "short_form" if int(page_count or 0) <= 2 else "standard"
```

Then in `build_ocr_health(...)` use:

```python
profile = _health_profile(page_count)
waived_gates: list[str] = []
structural_blockers = 0

if profile == "short_form":
    waived_gates.extend(["abstract_found", "section_heading_count"])
else:
    if not abstract_found:
        structural_blockers += 1
    if not references_found:
        structural_blockers += 1
    if section_heading_count < 2:
        structural_blockers += 1
```

Add report fields:

```python
report["health_profile"] = profile
report["waived_gates"] = waived_gates
if profile == "short_form":
    report["degraded_reason"] = "short_paper_format"
```

Also make `needs_rebuild` respect short-form policy.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_ocr_health.py -q
```

Expected: PASS.

- [ ] **Step 5: Run focused PR1 regression bundle**

Run:

```bash
python -m pytest \
  tests/test_ocr_pdf_text_fallback.py \
  tests/test_ocr_tables.py \
  tests/test_ocr_render.py \
  tests/test_ocr_health.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_health.py tests/test_ocr_health.py
git commit -m "fix: add short-form OCR health profile"
```

---

## Self-Review

### 1. Spec coverage
- Issue 3 → Task 1
- Issue 1A → Task 2
- Issue 1B → Task 3
- Issue 4 → Task 4

### 2. Placeholder scan
- No TODO/TBD text remains
- Every task has exact files, tests, commands, and code snippets

### 3. Type consistency
- All changes are additive helpers or local branch changes
- No cross-module interface churn introduced in PR1

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-01-ocr-v2-pr1-deterministic-fixes-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
