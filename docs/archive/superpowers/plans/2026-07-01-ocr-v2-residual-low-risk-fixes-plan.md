# OCR-v2 Residual Low-Risk Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the six residual OCR fixes in the safest possible order, using local root fixes first, audit-model changes second, and cross-module ownership arbitration last.

**Architecture:** Keep each fix at the narrowest seam that already owns the behavior: PDF-text backfill in `ocr_pdf_spans.py`, table caption ownership in `ocr_tables.py`, health policy in `ocr_health.py`, figure contained-text cleanup in `ocr_figures.py`, and cross-pipeline resolution only at the final figure/table wiring point in `ocr.py` and `ocr_rebuild.py`. Do not do a global OCR block merge, do not move logic into unrelated modules, and do not add a new top-level gate that tries to solve everything at once.

**Tech Stack:** Python 3.x, pytest, PyMuPDF (`fitz`), existing OCR worker modules under `paperforge/worker/`

## Global Constraints

- Keep implementation order strict: `3 → 1 → 4 → 2 → 5 → 6`.
- Every task must start with a failing test at the real seam.
- Do **not** globally merge raw OCR blocks.
- Do **not** use figure-first ordering for figure/table conflicts.
- Do **not** use padding to fix Issue 2.
- Issue 2 is containment-only: it may tag `figure_inner_text`, but must not create new figure matches or consume assets.
- Preserve existing `ownership_conflicts` audit surface; add arbitration before it, not instead of it.
- Prefer tiny helpers inside the owning module over new shared utilities.
- Commit after each task with a narrow message.

---

## File Map

- `paperforge/worker/ocr_pdf_spans.py` — PDF text-layer backfill; word extraction and overlap filtering
- `tests/test_ocr_pdf_text_fallback.py` — backfill unit tests
- `paperforge/worker/ocr_tables.py` — table caption collection, weak-explicit matching, consumed block ownership
- `tests/test_ocr_tables.py` — table inventory tests
- `tests/test_ocr_render.py` — render skip behavior for consumed table continuation blocks
- `paperforge/worker/ocr_health.py` — health scoring and rebuild policy
- `tests/test_ocr_health.py` — health report tests
- `paperforge/worker/ocr_figures.py` — figure containment, page-assets gate, ownership conflict audit, future arbitration helper
- `tests/unit/worker/test_figure_containment.py` — containment unit tests
- `tests/test_ocr_figures.py` — page-assets and ownership-conflict/arbitration tests
- `paperforge/worker/ocr.py` — main OCR pipeline wiring
- `paperforge/worker/ocr_rebuild.py` — rebuild pipeline wiring

---

### Task 1: Fix word-level backfill overflow in `ocr_pdf_spans.py`

**Files:**
- Modify: `paperforge/worker/ocr_pdf_spans.py`
- Test: `tests/test_ocr_pdf_text_fallback.py`

**Interfaces:**
- Consumes: existing `backfill_missing_text_from_pdf(raw_blocks, pdf_path) -> list[dict]`
- Produces:
  - `_word_center_inside_rect(word_bbox: tuple[float, float, float, float], block_rect: fitz.Rect) -> bool`
  - `_word_belongs_to_block(word_bbox: tuple[float, float, float, float], block_rect: fitz.Rect) -> bool`
  - Updated `backfill_missing_text_from_pdf(...)` that filters words after `get_text("words", clip=expanded)` and before `_words_to_text(words)`

- [ ] **Step 1: Write the failing tests**

Add these tests to `tests/test_ocr_pdf_text_fallback.py`:

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

Expected: FAIL because neighbor word is currently included in recovered text, and `_word_belongs_to_block` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

In `paperforge/worker/ocr_pdf_spans.py`, add these helpers near `_bbox_overlap_ratio`:

```python
def _word_center_inside_rect(word_bbox: tuple[float, float, float, float], block_rect: fitz.Rect) -> bool:
    x0, y0, x1, y1 = word_bbox
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    return block_rect.x0 <= cx <= block_rect.x1 and block_rect.y0 <= cy <= block_rect.y1


def _word_belongs_to_block(word_bbox: tuple[float, float, float, float], block_rect: fitz.Rect) -> bool:
    word_rect = fitz.Rect(*word_bbox)
    return (
        _word_center_inside_rect(word_bbox, block_rect)
        or _bbox_overlap_ratio(word_rect, block_rect) >= 0.30
    )
```

Then change the extraction block in `backfill_missing_text_from_pdf(...)` from:

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

### Task 2: Fix validation-first bare `Table N` fallthrough

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`
- Test: `tests/test_ocr_tables.py`

**Interfaces:**
- Consumes: existing `_is_validation_first_table_candidate(block) -> bool`, `_is_insufficient_table_caption_evidence(block) -> bool`, weak-explicit path in `build_table_inventory(structured_blocks) -> dict`
- Produces: updated validation-first handling that falls through to existing weak-explicit scoring when same-page assets exist

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

Expected: FAIL with `official_table_count == 0` or unmatched caption.

- [ ] **Step 3: Write minimal implementation**

In `paperforge/worker/ocr_tables.py`, replace:

```python
if is_validation_first_candidate and is_weak_truncated:
    same_page_assets = [...]
    if not same_page_assets:
        held_tables.append(...)
    continue
```

with:

```python
if is_validation_first_candidate and is_weak_truncated:
    same_page_assets = [
        a for i, a in enumerate(assets)
        if i not in used_asset_indices and a.get("page", 0) == caption_page
    ]
    if not same_page_assets:
        held_tables.append(
            {
                "table_id": f"held_table_{len(held_tables) + 1:03d}",
                "caption_block_id": caption.get("block_id", ""),
                "page": caption_page,
                "caption_text": caption_text,
                "table_number": table_num,
                "formal_table_number": formal_table_number,
                "hold_reason": "insufficient_caption_evidence",
                "zone": caption.get("zone", ""),
                "style_family": caption.get("style_family", ""),
                "marker_signature": caption.get("marker_signature", {}),
            }
        )
        continue
    # same-page asset exists → fall through into weak-explicit matching
```

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

### Task 3: Materialize split table caption continuations inside `build_table_inventory`

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`
- Test: `tests/test_ocr_tables.py`
- Test: `tests/test_ocr_render.py`

**Interfaces:**
- Consumes: `build_table_inventory(structured_blocks) -> dict`
- Produces:
  - `_find_table_caption_continuation(caption: dict, structured_blocks: list[dict]) -> dict | None`
  - `_materialize_table_caption(caption: dict, continuation: dict | None) -> tuple[dict, list[str]]`
  - table entries whose `caption_text`, `caption_block_id`, `consumed_block_ids`, and matching bbox can reflect a local continuation block without mutating the original OCR blocks

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ocr_tables.py`:

```python
def test_split_table_caption_materializes_continuation_stolen_as_figure_caption():
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "block_id": "cap1",
            "page": 1,
            "role": "table_caption",
            "text": "Table 2",
            "bbox": [100, 100, 220, 120],
            "raw_label": "text",
        },
        {
            "block_id": "cap2",
            "page": 1,
            "role": "figure_caption",
            "text": "Structural parameters of nanocomposites obtained from the d",
            "bbox": [100, 121, 500, 145],
            "raw_label": "text",
        },
        {
            "block_id": "asset",
            "page": 1,
            "role": "media_asset",
            "raw_label": "table_image",
            "text": "",
            "bbox": [100, 150, 500, 400],
        },
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

Expected: FAIL because continuation is currently not merged, not consumed, and render may still emit the second block.

- [ ] **Step 3: Write minimal implementation**

Add to `paperforge/worker/ocr_tables.py`:

```python
def _find_table_caption_continuation(caption: dict, structured_blocks: list[dict]) -> dict | None:
    page = int(caption.get("page", 0) or 0)
    bbox = caption.get("bbox") or [0, 0, 0, 0]
    if len(bbox) < 4:
        return None

    candidates = []
    for block in structured_blocks:
        if block is caption or int(block.get("page", 0) or 0) != page:
            continue
        role = str(block.get("role") or "")
        if role not in {"figure_caption", "body_paragraph", "unknown_structural", "table_caption_candidate"}:
            continue
        text = str(block.get("text") or "").strip()
        if not text:
            continue
        lower = text.lower()
        if lower.startswith(("fig", "figure", "scheme", "plate")):
            continue
        bb = block.get("bbox") or [0, 0, 0, 0]
        if len(bb) < 4:
            continue
        y_gap = bb[1] - bbox[3]
        x_overlap = max(0.0, min(bbox[2], bb[2]) - max(bbox[0], bb[0]))
        overlap_ratio = x_overlap / max(1.0, min(bbox[2] - bbox[0], bb[2] - bb[0]))
        left_delta = abs(bb[0] - bbox[0])
        if not (0 <= y_gap <= 25):
            continue
        if not (overlap_ratio >= 0.5 or left_delta < 40):
            continue
        candidates.append((y_gap, left_delta, block))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2]


def _materialize_table_caption(caption: dict, continuation: dict | None) -> tuple[dict, list[str]]:
    merged = dict(caption)
    consumed = [str(caption.get("block_id") or "")]
    if continuation is None:
        return merged, [bid for bid in consumed if bid]

    merged_text = " ".join(
        part.strip()
        for part in [str(caption.get("text") or ""), str(continuation.get("text") or "")]
        if part.strip()
    )
    merged["text"] = merged_text
    cb = caption.get("bbox") or [0, 0, 0, 0]
    nb = continuation.get("bbox") or [0, 0, 0, 0]
    if len(cb) >= 4 and len(nb) >= 4:
        merged["bbox"] = [
            min(cb[0], nb[0]), min(cb[1], nb[1]),
            max(cb[2], nb[2]), max(cb[3], nb[3]),
        ]
    if continuation.get("block_id") is not None:
        consumed.append(str(continuation.get("block_id")))
    return merged, [bid for bid in consumed if bid]
```

Then inside the caption loop in `build_table_inventory(...)`, before score extraction, add:

```python
materialized_caption = caption
continuation = None
continuation_ids: list[str] = []
if is_weak_truncated:
    continuation = _find_table_caption_continuation(caption, structured_blocks)
    materialized_caption, continuation_ids = _materialize_table_caption(caption, continuation)
    caption_text = materialized_caption.get("text", "")
```

And when building `consumed_block_ids`, extend with `continuation_ids`.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest \
  tests/test_ocr_tables.py::test_split_table_caption_materializes_continuation_stolen_as_figure_caption \
  tests/test_ocr_tables.py::test_split_table_caption_does_not_steal_real_figure_caption \
  tests/test_ocr_render.py::test_materialized_table_caption_continuation_is_skipped_by_render_when_consumed -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_tables.py tests/test_ocr_tables.py tests/test_ocr_render.py
git commit -m "fix: materialize split table caption continuations"
```

---

### Task 4: Add `short_form` health profile in `ocr_health.py`

**Files:**
- Modify: `paperforge/worker/ocr_health.py`
- Test: `tests/test_ocr_health.py`

**Interfaces:**
- Consumes: `build_ocr_health(...) -> dict`
- Produces:
  - `_health_profile(page_count: int) -> str`
  - report fields: `health_profile`, `waived_gates`, `degraded_reason`
  - updated `overall` / `needs_rebuild` behavior for `page_count <= 2`

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

Expected: FAIL because `health_profile` fields do not exist and short forms still go red.

- [ ] **Step 3: Write minimal implementation**

In `paperforge/worker/ocr_health.py`, add:

```python
def _health_profile(page_count: int) -> str:
    return "short_form" if int(page_count or 0) <= 2 else "standard"
```

Then in `build_ocr_health(...)`:

```python
profile = _health_profile(page_count)
waived_gates: list[str] = []
structural_blockers = 0

if profile == "short_form":
    waived_gates.extend(["abstract_found", "section_heading_count"])
    if not references_found:
        # keep visible in report, but not a structural blocker by itself
        pass
else:
    if not abstract_found:
        structural_blockers += 1
    if not references_found:
        structural_blockers += 1
    if section_heading_count < 2:
        structural_blockers += 1
```

And add report fields:

```python
report["health_profile"] = profile
report["waived_gates"] = waived_gates
if profile == "short_form":
    report["degraded_reason"] = "short_paper_format"
```

Make `needs_rebuild` respect the short-form profile.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_ocr_health.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_health.py tests/test_ocr_health.py
git commit -m "fix: add short-form OCR health profile"
```

---

### Task 5: Use validated `_container_bbox` regions for contained text in demoted-caption cases

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/unit/worker/test_figure_containment.py`

**Interfaces:**
- Consumes: `tag_figure_contained_text(blocks, matched_figures) -> None`, existing `_container_bbox` fields already produced upstream
- Produces:
  - `_validated_container_regions(page_blocks: list[dict], page_width: float, page_height: float) -> list[list[float]]`
  - updated `tag_figure_contained_text(...)` region priority:
    1. matched figure bbox
    2. validated `_container_bbox`
    3. fallback asset cluster bbox

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/worker/test_figure_containment.py`:

```python
def test_container_bbox_tags_vision_footnote_inside_demoted_figure(self):
    blocks = [
        self._block("inner", 1, 120, 120, 180, 140, role="footnote", text="Single outlet", _container_bbox=[90, 90, 320, 220]),
        self._block("asset1", 1, 100, 100, 200, 200, role="media_asset", raw_label="table", asset_family_hint="ambiguous"),
        self._block("asset2", 1, 210, 100, 310, 200, role="media_asset", raw_label="table", asset_family_hint="ambiguous"),
    ]
    tag_figure_contained_text(blocks, [])
    assert blocks[0]["role"] == "figure_inner_text"


def test_huge_container_bbox_is_rejected_by_area_gate(self):
    blocks = [
        self._block("body", 1, 100, 100, 500, 130, role="body_paragraph", text="Nearby body text", _container_bbox=[0, 0, 1200, 1600]),
        self._block("asset", 1, 100, 500, 300, 700, role="media_asset", raw_label="image", asset_family_hint="figure_like"),
    ]
    tag_figure_contained_text(blocks, [])
    assert blocks[0]["role"] == "body_paragraph"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/worker/test_figure_containment.py -q
```

Expected: FAIL because `_container_bbox` is currently ignored.

- [ ] **Step 3: Write minimal implementation**

In `paperforge/worker/ocr_figures.py`, add:

```python
def _validated_container_regions(page_blocks: list[dict], page_width: float, page_height: float) -> list[list[float]]:
    page_area = max(1.0, page_width * page_height)
    regions: list[list[float]] = []
    for block in page_blocks:
        bbox = block.get("_container_bbox")
        if not bbox or len(bbox) < 4:
            continue
        cw = bbox[2] - bbox[0]
        ch = bbox[3] - bbox[1]
        area = max(1.0, cw * ch)
        if area >= page_area * 0.65:
            continue
        if cw >= page_width * 0.98 and ch >= page_height * 0.45:
            continue
        has_media = any(
            (other.get("role") in {"figure_asset", "media_asset"})
            and _is_contained(other.get("bbox") or [0, 0, 0, 0], bbox)
            for other in page_blocks
            if len(other.get("bbox") or []) >= 4
        )
        if not has_media:
            continue
        regions.append(list(bbox))
    return regions
```

Then in `tag_figure_contained_text(...)`, after matched figure regions and before fallback asset regions, add:

```python
page_width = max((float((b.get("page_width") or 0)) for b in page_blocks), default=0.0)
page_height = max((float((b.get("page_height") or 0)) for b in page_blocks), default=0.0)
for cr in _validated_container_regions(page_blocks, page_width, page_height):
    if not _highly_overlaps_any_matched_region(cr, figure_regions):
        figure_regions.append(("container", cr))
```

Do **not** create figure inventory entries. Do **not** mutate assets. Only containment tagging may change.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/worker/test_figure_containment.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/unit/worker/test_figure_containment.py
git commit -m "fix: use validated container bboxes for contained figure text"
```

---

### Task 6: Reject cross-column `page_assets` groups at the safe-group gate

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

**Interfaces:**
- Consumes: `_is_safe_page_assets_group(group, legend, page_blocks, page_numbered_legend_count, page_width, page_height) -> tuple[bool, list[str]]`
- Produces:
  - `_column_band_id(bbox: list[float], page_width: float) -> int | None`
  - updated `_is_safe_page_assets_group(...)` with cross-column rejection for non-full-width page-assets groups

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ocr_figures.py`:

```python
def test_page_assets_group_rejects_cross_column_media_assets():
    from paperforge.worker.ocr_figures import _is_safe_page_assets_group

    media_blocks = [
        {"block_id": "L1", "page": 1, "bbox": [0, 0, 280, 200], "raw_label": "image", "text": ""},
        {"block_id": "L2", "page": 1, "bbox": [0, 220, 280, 420], "raw_label": "image", "text": ""},
        {"block_id": "R1", "page": 1, "bbox": [310, 0, 590, 200], "raw_label": "image", "text": ""},
    ]
    group = {"media_blocks": media_blocks, "cluster_bbox": [0, 0, 590, 420]}
    legend = {"text": "Figure 1. Example.", "page": 1}

    safe, evidence = _is_safe_page_assets_group(
        group,
        legend,
        page_blocks=list(media_blocks),
        page_numbered_legend_count=1,
        page_width=600,
        page_height=1000,
    )

    assert safe is False
    assert "cross_column_media" in evidence


def test_full_width_group_can_still_pass_single_caption_gate():
    from paperforge.worker.ocr_figures import _is_safe_page_assets_group

    media_blocks = [
        {"block_id": "A", "page": 1, "bbox": [20, 100, 580, 280], "raw_label": "image", "text": ""},
        {"block_id": "B", "page": 1, "bbox": [20, 300, 580, 480], "raw_label": "image", "text": ""},
        {"block_id": "C", "page": 1, "bbox": [20, 500, 580, 680], "raw_label": "image", "text": ""},
    ]
    group = {"media_blocks": media_blocks, "cluster_bbox": [20, 100, 580, 680]}
    legend = {"text": "Figure 1. Full-width figure.", "page": 1}

    safe, evidence = _is_safe_page_assets_group(
        group,
        legend,
        page_blocks=list(media_blocks),
        page_numbered_legend_count=1,
        page_width=600,
        page_height=1000,
    )

    assert safe is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_ocr_figures.py::test_page_assets_group_rejects_cross_column_media_assets tests/test_ocr_figures.py::test_full_width_group_can_still_pass_single_caption_gate -q
```

Expected: FAIL because the current safe-group gate is column-agnostic.

- [ ] **Step 3: Write minimal implementation**

In `paperforge/worker/ocr_figures.py`, add:

```python
def _column_band_id(bbox: list[float], page_width: float) -> int | None:
    if not bbox or len(bbox) < 4 or page_width <= 0:
        return None
    center_x = (bbox[0] + bbox[2]) / 2.0
    if center_x < page_width * 0.45:
        return 0
    if center_x > page_width * 0.55:
        return 1
    return None
```

Then in `_is_safe_page_assets_group(...)`, before returning `True`, add:

```python
full_width_group = cw >= page_width * 0.65 and page_numbered_legend_count == 1
if not full_width_group:
    bands = {
        _column_band_id(mb.get("bbox") or [0, 0, 0, 0], page_width)
        for mb in media_blocks
    }
    bands.discard(None)
    if len(bands) > 1:
        return False, ["cross_column_media"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_ocr_figures.py::test_page_assets_group_rejects_cross_column_media_assets tests/test_ocr_figures.py::test_full_width_group_can_still_pass_single_caption_gate -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py
git commit -m "fix: reject cross-column safe page-assets groups"
```

---

### Task 7: Add conservative post-hoc figure/table ownership arbitration

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `paperforge/worker/ocr.py`
- Modify: `paperforge/worker/ocr_rebuild.py`
- Test: `tests/test_ocr_figures.py`

**Interfaces:**
- Consumes:
  - `figure_inventory: dict`
  - `table_inventory: dict`
  - existing `attach_ownership_conflicts(figure_inventory, table_inventory) -> None`
- Produces:
  - `resolve_media_asset_conflicts(figure_inventory: dict, table_inventory: dict) -> list[dict]`
  - optional `figure_inventory["ownership_resolutions"]`
  - pipeline wiring calls that resolve first, then attach remaining conflicts

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ocr_figures.py`:

```python
def test_resolve_media_asset_conflicts_prefers_explicit_table_over_weak_figure():
    from paperforge.worker.ocr_figures import resolve_media_asset_conflicts, _build_ownership_conflicts

    figure_inventory = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "legend_block_id": "figcap",
                "text": "Figure 1. Example.",
                "match_score": {"score": 0.51, "decision": "matched", "evidence": ["fallback"]},
                "asset_block_ids": ["asset"],
                "page": 1,
            }
        ]
    }
    table_inventory = {
        "tables": [
            {
                "table_id": "table_001",
                "caption_block_id": "tabcap",
                "caption_text": "Table 1. Example.",
                "match_status": "matched",
                "has_asset": True,
                "asset_block_id": "asset",
                "page": 1,
            }
        ]
    }

    resolutions = resolve_media_asset_conflicts(figure_inventory, table_inventory)
    conflicts = _build_ownership_conflicts(figure_inventory, table_inventory)

    assert resolutions[0]["winner"] == "table"
    assert figure_inventory["matched_figures"] == []
    assert conflicts == []


def test_resolve_media_asset_conflicts_leaves_weak_weak_case_unresolved():
    from paperforge.worker.ocr_figures import resolve_media_asset_conflicts, _build_ownership_conflicts

    figure_inventory = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "legend_block_id": "figcap",
                "text": "Figure 1.",
                "match_score": {"score": 0.52, "decision": "matched_low_confidence", "evidence": ["fallback"]},
                "asset_block_ids": ["asset"],
                "page": 1,
            }
        ]
    }
    table_inventory = {
        "tables": [
            {
                "table_id": "table_001",
                "caption_block_id": "tabcap",
                "caption_text": "Table 1",
                "match_status": "matched_low_confidence",
                "has_asset": True,
                "asset_block_id": "asset",
                "page": 1,
            }
        ]
    }

    resolutions = resolve_media_asset_conflicts(figure_inventory, table_inventory)
    conflicts = _build_ownership_conflicts(figure_inventory, table_inventory)

    assert resolutions == []
    assert len(conflicts) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_ocr_figures.py::test_resolve_media_asset_conflicts_prefers_explicit_table_over_weak_figure tests/test_ocr_figures.py::test_resolve_media_asset_conflicts_leaves_weak_weak_case_unresolved -q
```

Expected: FAIL because `resolve_media_asset_conflicts` does not exist.

- [ ] **Step 3: Write minimal implementation**

In `paperforge/worker/ocr_figures.py`, add:

```python
def _table_ownership_strength(table: dict) -> tuple[int, int]:
    explicit = 1 if str(table.get("caption_text") or "").lower().startswith("table") else 0
    strong = 1 if str(table.get("match_status") or "") == "matched" else 0
    return (explicit, strong)


def _figure_ownership_strength(fig: dict) -> tuple[int, float]:
    text = str(fig.get("text") or "")
    explicit = 1 if text.lower().startswith(("figure", "fig.")) else 0
    score = float((fig.get("match_score") or {}).get("score", 0.0) or 0.0)
    return (explicit, score)


def resolve_media_asset_conflicts(figure_inventory: dict, table_inventory: dict) -> list[dict]:
    resolutions: list[dict] = []
    tables_by_asset = {
        (int(t.get("page", 0) or 0), str(t.get("asset_block_id", ""))): t
        for t in table_inventory.get("tables", [])
        if t.get("has_asset") and t.get("asset_block_id")
    }

    kept_figures = []
    for fig in figure_inventory.get("matched_figures", []):
        asset_ids = [
            (int(fig.get("page", 0) or 0), str(bid))
            for bid in fig.get("asset_block_ids", [])
            if bid is not None
        ]
        conflict = next((aid for aid in asset_ids if aid in tables_by_asset), None)
        if conflict is None:
            kept_figures.append(fig)
            continue

        table = tables_by_asset[conflict]
        fig_strength = _figure_ownership_strength(fig)
        table_strength = _table_ownership_strength(table)

        if table_strength > (fig_strength[0], 1 if fig_strength[1] >= 0.70 else 0):
            resolutions.append({"page": conflict[0], "block_id": conflict[1], "winner": "table"})
            continue

        if (fig_strength[0], 1 if fig_strength[1] >= 0.70 else 0) > table_strength:
            resolutions.append({"page": conflict[0], "block_id": conflict[1], "winner": "figure"})
            table["has_asset"] = False
            table["asset_block_id"] = None
            kept_figures.append(fig)
            continue

        kept_figures.append(fig)

    figure_inventory["matched_figures"] = kept_figures
    figure_inventory["ownership_resolutions"] = resolutions
    return resolutions
```

Then update `paperforge/worker/ocr.py` and `paperforge/worker/ocr_rebuild.py`:

```python
from paperforge.worker.ocr_figures import attach_ownership_conflicts, resolve_media_asset_conflicts

resolve_media_asset_conflicts(figure_inventory, table_inventory)
attach_ownership_conflicts(figure_inventory, table_inventory)
```

Place `resolve_media_asset_conflicts(...)` **before** writebacks.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_ocr_figures.py::test_resolve_media_asset_conflicts_prefers_explicit_table_over_weak_figure tests/test_ocr_figures.py::test_resolve_media_asset_conflicts_leaves_weak_weak_case_unresolved -q
```

Expected: PASS.

- [ ] **Step 5: Run focused regression sweep**

Run:

```bash
python -m pytest tests/test_ocr_figures.py tests/test_ocr_tables.py tests/unit/worker/test_figure_containment.py tests/test_ocr_health.py tests/test_ocr_pdf_text_fallback.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_figures.py paperforge/worker/ocr.py paperforge/worker/ocr_rebuild.py tests/test_ocr_figures.py
git commit -m "fix: add conservative figure-table asset arbitration"
```

---

## Self-Review

### 1. Spec coverage

- Issue 3 backfill overflow → Task 1
- Issue 1A validation-first gap → Task 2
- Issue 1B split caption continuation → Task 3
- Issue 4 short-form health red → Task 4
- Issue 2 demoted-caption containment gap → Task 5
- Issue 5 page-assets cross-column collapse → Task 6
- Issue 6 shared-consumption arbitration → Task 7

No spec gaps remain.

### 2. Placeholder scan

- No `TODO`, `TBD`, or “implement later” steps remain
- Every task includes explicit file paths, test names, commands, and code snippets
- All rejected approaches are called out explicitly where they are dangerous

### 3. Type consistency

- `backfill_missing_text_from_pdf(...)` stays list-in/list-out
- `build_table_inventory(...)` remains dict-returning, with only internal helper additions
- `build_ocr_health(...)` remains dict-returning with additive report keys
- `tag_figure_contained_text(...)` stays in-place mutation only
- `resolve_media_asset_conflicts(...)` is new and returns `list[dict]`, while mutating inventories before existing writeback calls

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-01-ocr-v2-residual-low-risk-fixes-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
