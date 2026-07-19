# Cover Page Detection & Block 9 Callout Strategy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) Drop known cover-only page 1 (ACS "Just Accepted", accepted-manuscript covers) from the pipeline using positive cover markers, same path as preproof. (2) Convert footnotes in body zone with distinct font to inline callouts.

**Architecture:** Two independent changes in separate commits. Task 1: extend preproof cover detection in `ocr_blocks.py` to also detect non-preproof covers via positive markers + no body guard. Task 2: add footnote-to-callout conversion in `ocr_render.py` before tail reorder, with proper body zone overlap, font_size helper, and content guards.

**Tech Stack:** Python, existing OCR pipeline

---

## 修订日志 (from plan review)

| ID | 问题 | 修复方式 |
|----|------|---------|
| P0.1 | `_has_cover_page_one` 用"无 body"判定，误删正常 abstract page 1 | 改成 positive cover marker + no body guard |
| P0.2 | abstract_body 测试预期写反了 | 测试改为：有 abstract 的 page 1 不应 drop |
| P0.3 | 函数只改 evidence 不改名 | 完整改名为 `_annotate_cover_page_drop` |
| P0.4 | 未验证 wiring / page renumber | 加 `build_structured_blocks` wiring 测试 |
| P0.5 | body zone overlap 算反了，fn_y1(520) > body_y2(500) 不重叠 | 改 `_is_near_body_flow`，用 column-aligned + vertical proximity |
| P0.6 | `_block_font_size` 没有 fallback 到 `span_metadata` | 加 `_block_font_size` helper |
| P0.7 | 插入点写成不存在的 `reorder_and_render` | 改为 `render_fulltext_markdown()` 内的正确位置 |
| P0.8 | 缺少 full render 测试 | 加 `render_fulltext_markdown` 调用，验证 `> [!NOTE]` |
| P1.2 | 缺少内容 guard | 加 copyright/boilerplate 排除 + affiliation content 正向允许 |
| P1.3 | 两变更应分开 commit | 两个独立 commit |
| v2-P0.1 | `available online` marker 过宽 | 只保留强 marker，删除弱 marker |
| v2-P0.4 | full render test 签名错误 | 改为 keyword-only 签名 |
| v2-P0.5 | positive allow 代码未实现 | 加 `_POSITIVE_CALLOUT_MARKERS` 并在循环中检查 |
| v2-P1.1 | body blocks 跨页误判 | 按同页过滤 body blocks + font median |

---

### Task 1: Non-preproof cover page detection (positive marker)

**Files:**
- Modify: `paperforge/worker/ocr_blocks.py:114-244`
- Test: `tests/test_ocr_blocks.py`

**Contract:**
1. Keep `_has_preproof_cover_page_one` unchanged.
2. Add `_has_nonpreproof_cover_page_one(rows)` — requires **positive cover markers** (text like "just accepted", "manuscript has been accepted" on page 1) AND no substantial article content on page 1.
3. Page 1 with `abstract_body` / title / authors / keywords but no Introduction → **preserved** (NOT a cover page).
4. Drop only when BOTH: page 1 has cover-marker text AND page 1 has no section heading nor ≥20-word body_paragraph.
5. Rename `_annotate_preproof_cover_drop` to `_annotate_cover_page_drop(rows, *, reason)` with evidence `"page_1_cover_dropped_upstream:{reason}"`.
6. Add wiring test through `build_structured_blocks`.

- [ ] **Step 1: Write helper tests**

```python
# In tests/test_ocr_blocks.py

from paperforge.worker.ocr_blocks import _has_nonpreproof_cover_page_one


def test_nonpreproof_cover_false_when_page1_has_abstract():
    """page 1 with abstract but no cover marker → NOT cover."""
    rows = [
        {"page": 1, "seed_role": "paper_title", "text": "Some Title"},
        {"page": 1, "seed_role": "authors", "text": "John Doe"},
        {"page": 1, "seed_role": "abstract_body",
         "text": "This abstract describes the study purpose, methods, results, and conclusions."},
        {"page": 1, "seed_role": "frontmatter_noise", "text": "Keywords: something"},
        {"page": 2, "seed_role": "section_heading", "text": "1. Introduction"},
        {"page": 2, "seed_role": "body_paragraph",
         "text": "Real body text starts here with many words. It has enough length to pass the threshold."},
    ]
    assert _has_nonpreproof_cover_page_one(rows) is False


def test_nonpreproof_cover_false_when_page1_has_section_heading():
    """page 1 with section heading → NOT cover even with marker."""
    rows = [
        {"page": 1, "seed_role": "frontmatter_noise", "text": "Just Accepted"},
        {"page": 1, "seed_role": "paper_title", "text": "Some Title"},
        {"page": 1, "seed_role": "section_heading", "text": "1. Introduction"},
    ]
    assert _has_nonpreproof_cover_page_one(rows) is False


def test_nonpreproof_cover_true_with_just_accepted_marker():
    """ACS 'Just Accepted' marker + no body → cover page."""
    rows = [
        {"page": 1, "seed_role": "frontmatter_noise", "text": "Just Accepted"},
        {"page": 1, "seed_role": "frontmatter_noise",
         "text": "This is a PDF file of an unedited manuscript that has been accepted for publication."},
        {"page": 1, "seed_role": "frontmatter_noise",
         "text": "American Chemical Society"},
        {"page": 2, "seed_role": "paper_title", "text": "Some Title"},
        {"page": 2, "seed_role": "body_paragraph",
         "text": "Real body text starts here with many words to pass the threshold requirement. More words here."},
    ]
    assert _has_nonpreproof_cover_page_one(rows) is True


def test_nonpreproof_cover_false_when_no_cover_marker():
    """page 1 with no cover marker text but no body → NOT cover (too risky)."""
    rows = [
        {"page": 1, "seed_role": "frontmatter_noise", "text": "Copyright © 2023 Publisher"},
        {"page": 2, "seed_role": "section_heading", "text": "Introduction"},
    ]
    assert _has_nonpreproof_cover_page_one(rows) is False


def test_nonpreproof_cover_false_for_available_online_only():
    """'Available online' alone must NOT trigger cover drop."""
    rows = [
        {"page": 1, "seed_role": "frontmatter_noise", "text": "Available online 12 March 2024"},
        {"page": 1, "seed_role": "abstract_body",
         "text": "This abstract describes the study purpose, methods, and results."},
        {"page": 2, "seed_role": "section_heading", "text": "1. Introduction"},
    ]
    assert _has_nonpreproof_cover_page_one(rows) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_blocks.py -v -k "nonpreproof_cover" --tb=short 2>&1 | tail -10`
Expected: 5 failures (ImportError / NameError)

- [ ] **Step 3: Add `_has_nonpreproof_cover_page_one` in `ocr_blocks.py`**

After `_has_preproof_cover_page_one` (around line 124):

```python
_COVER_PAGE_MARKERS = {
    "just accepted",
    "accepted manuscript",
    "this is a pdf file of an unedited manuscript",
    "this is a pdf file of a manuscript that has been accepted",
    "manuscript has been accepted",
}


def _has_nonpreproof_cover_page_one(rows: list[dict]) -> bool:
    """Return True if page 1 is a cover page (non-preproof).

    Uses positive cover markers + negative body-content guard.
    Both must hold: page 1 contains cover-marker text AND no article body.
    Page 1 with abstract_body / section heading is always preserved.
    """
    page1_blocks = [r for r in rows if (int(r.get("page", 0) or 0)) == 1]
    if not page1_blocks:
        return False

    texts_lower = " ".join(
        str(r.get("text", "") or "").lower()
        for r in page1_blocks
    )
    has_marker = any(m in texts_lower for m in _COVER_PAGE_MARKERS)
    if not has_marker:
        return False

    for r in page1_blocks:
        role = r.get("seed_role", "")
        # Strong article content guards — cover pages don't have these
        if role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
            return False
        if role in {"abstract_body", "abstract_heading", "authors"}:
            return False
        if role == "body_paragraph":
            words = str(r.get("text", "") or "").strip().split()
            if len(words) >= 20:
                return False

    return True
```

- [ ] **Step 4: Rename `_annotate_preproof_cover_drop` to `_annotate_cover_page_drop`**

Replace:

```python
def _annotate_preproof_cover_drop(rows: list[dict]) -> None:
    for row in rows:
        if int(row.get("page", 0) or 0) <= 1:
            continue
        evidence = row.setdefault("evidence", [])
        if "page_1_preproof_cover_dropped_upstream" not in evidence:
            evidence.append("page_1_preproof_cover_dropped_upstream")
        return
```

With:

```python
def _annotate_cover_page_drop(rows: list[dict], *, reason: str) -> None:
    """Mark remaining rows that page 1 was dropped.

    Only annotates the first surviving row (intentional: single evidence marker).
    """
    for row in rows:
        if int(row.get("page", 0) or 0) <= 1:
            continue
        evidence = row.setdefault("evidence", [])
        label = f"page_1_cover_dropped_upstream:{reason}"
        if label not in evidence:
            evidence.append(label)
        return
```

- [ ] **Step 5: Wire into `build_structured_blocks`**

Replace lines 242-244:

```python
    if _has_preproof_cover_page_one(rows):
        rows = [row for row in rows if (row.get("page", 0) or 0) != 1]
        _annotate_preproof_cover_drop(rows)
```

With:

```python
    if _has_preproof_cover_page_one(rows):
        rows = [row for row in rows if (row.get("page", 0) or 0) != 1]
        _annotate_cover_page_drop(rows, reason="preproof_marker")
    elif _has_nonpreproof_cover_page_one(rows):
        rows = [row for row in rows if (row.get("page", 0) or 0) != 1]
        _annotate_cover_page_drop(rows, reason="cover_marker_no_body")
```

- [ ] **Step 6: Update all callers of old function name**

Find and update any reference to `_annotate_preproof_cover_drop`:

```bash
rg "_annotate_preproof_cover_drop" --files-with-matches
```

Update any evidence string reference `"page_1_preproof_cover_dropped_upstream"` → `"page_1_cover_dropped_upstream:preproof_marker"`.

- [ ] **Step 7: Add wiring test**

```python
# At end of test file

def test_nonpreproof_cover_wired_through_build_structured_blocks(tmp_path):
    """build_structured_blocks drops page 1 for non-preproof cover."""
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {"paper_id": "TEST", "page": 1, "block_id": 0, "raw_label": "text",
         "text": "Just Accepted", "bbox": [0, 0, 100, 20], "page_width": 1200, "page_height": 1600,
         "raw_order": 0},
        {"paper_id": "TEST", "page": 1, "block_id": 1, "raw_label": "text",
         "text": "This is a PDF file of an unedited manuscript that has been accepted for publication.",
         "bbox": [0, 30, 500, 60], "page_width": 1200, "page_height": 1600, "raw_order": 1},
        {"paper_id": "TEST", "page": 2, "block_id": 2, "raw_label": "doc_title",
         "text": "Real Title", "bbox": [0, 100, 500, 150], "page_width": 1200, "page_height": 1600,
         "raw_order": 2},
        {"paper_id": "TEST", "page": 2, "block_id": 3, "raw_label": "text",
         "text": "Real body text starts here with enough words in this paragraph to pass the threshold check correctly.",
         "bbox": [0, 200, 500, 250], "page_width": 1200, "page_height": 1600, "raw_order": 3},
    ]

    rows, doc = build_structured_blocks(raw_blocks, structure_output_dir=tmp_path)
    assert all(r["page"] != 1 for r in rows), "page 1 should be dropped"
    assert any("page_1_cover_dropped_upstream:cover_marker_no_body" in (r.get("evidence") or [])
               for r in rows), "evidence should mark cover drop"
```

- [ ] **Step 8: Run helper tests + wiring test**

Run: `python -m pytest tests/test_ocr_blocks.py -v -k "cover" --tb=short 2>&1 | tail -15`
Expected: 6 passes (5 helper + 1 wiring)

- [ ] **Step 9: Run full regression to check no collateral**

Run: `python -m pytest tests/test_ocr_blocks.py tests/test_ocr_document.py tests/test_ocr_roles.py -v --tb=short 2>&1 | tail -10`
Expected: All tests pass (check for any test referencing old evidence string)

- [ ] **Step 10: Commit (Task 1 only)**

```bash
git add -A && git commit -m "feat: drop non-preproof cover page 1 via positive cover markers"
```

---

### Task 2: Footnote → callout conversion (block 9 fix)

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_render_stabilization.py`

**Contract:**
1. Add `_block_font_size(block)` helper that reads `span_signature.font_size` first, then `span_metadata` (dict or list).
2. Add `_is_near_body_flow(fn_bbox, body_blocks, page_height)` — uses:
   - Not page-bottom zone: `fn_y1 < page_height * 0.82`
   - Column-aligned with body: `horizontal_overlap / fn_width >= 0.5`
   - Near or overlapping vertically: `overlaps_y` OR `0 <= fn_y1 - body_y2 <= page_height * 0.08`
3. Add `_convert_footnotes_to_callouts(blocks)` — converts "footnote" → "structured_insert" when all conditions met.
4. Insert in `render_fulltext_markdown()` before `style_profiles` and before `_order_tail_blocks`.
5. Add full render test: `render_fulltext_markdown(...)` output contains `> [!NOTE]`.
6. Content guard: exclude copyright/boilerplate text. Positive allow for affiliation/author content.

- [ ] **Step 1: Write helper tests**

```python
# In tests/test_ocr_render_stabilization.py

from paperforge.worker.ocr_render import _block_font_size, _is_near_body_flow


def test_block_font_size_from_span_signature():
    block = {"span_signature": {"font_size": 8.0}}
    assert _block_font_size(block) == 8.0


def test_block_font_size_fallback_to_span_metadata_dict():
    block = {"span_metadata": {"size": 7.5}}
    assert _block_font_size(block) == 7.5


def test_block_font_size_fallback_to_span_metadata_list():
    block = {"span_metadata": [{"size": 9.0}, {"size": 9.0}, {"size": 9.0}]}
    assert _block_font_size(block) == 9.0


def test_block_font_size_none():
    assert _block_font_size({}) is None


def test_is_near_body_flow_overlaps_y():
    """Footnote whose y-range overlaps body y-range → near body flow."""
    fn_bbox = [100, 460, 800, 540]
    body_blocks = [
        {"bbox": [100, 300, 800, 500]},
    ]
    assert _is_near_body_flow(fn_bbox, body_blocks, page_height=1500) is True


def test_is_near_body_flow_just_below():
    """Footnote 40px below body (within 8% of page) and x-aligned → near body flow."""
    fn_bbox = [100, 520, 800, 600]
    body_blocks = [
        {"bbox": [100, 300, 800, 500]},
    ]
    # gap = 520 - 500 = 20
    # 20 <= 1500 * 0.08 = 120 → True
    assert _is_near_body_flow(fn_bbox, body_blocks, page_height=1500) is True


def test_is_near_body_flow_too_far_down():
    """Footnote at page bottom (y1 > 0.82 * page_height) → not near body flow."""
    fn_bbox = [100, 1300, 800, 1400]
    body_blocks = [
        {"bbox": [100, 300, 800, 500]},
    ]
    # y1=1300 > 1500*0.82=1230 → False
    assert _is_near_body_flow(fn_bbox, body_blocks, page_height=1500) is False


def test_is_near_body_flow_wrong_column():
    """Footnote not x-aligned with body → not near body flow."""
    fn_bbox = [50, 400, 200, 500]  # left sidebar
    body_blocks = [
        {"bbox": [400, 300, 800, 500]},  # right column
    ]
    # horizontal_overlap = 0, fn_width = 150, ratio = 0 < 0.5 → False
    assert _is_near_body_flow(fn_bbox, body_blocks, page_height=1500) is False
```

- [ ] **Step 2: Run helper tests**

Run: `python -m pytest tests/test_ocr_render_stabilization.py -v -k "block_font_size or near_body_flow" --tb=short 2>&1 | tail -10`
Expected: 8 failures (4 block_font_size + 4 is_near_body_flow tests)

- [ ] **Step 3: Add `_block_font_size` and `_is_near_body_flow` in `ocr_render.py`**

Near top of file (after imports):

```python
def _block_font_size(block: dict) -> float | None:
    sig = block.get("span_signature") or {}
    fs = sig.get("font_size")
    if fs is not None:
        return float(fs)
    meta = block.get("span_metadata")
    if isinstance(meta, dict) and meta.get("size") is not None:
        return float(meta["size"])
    if isinstance(meta, list):
        sizes = [
            float(s["size"]) for s in meta
            if isinstance(s, dict) and s.get("size") is not None
        ]
        if sizes:
            return sorted(sizes)[len(sizes) // 2]
    return None


def _is_near_body_flow(
    fn_bbox: list[float],
    body_blocks: list[dict],
    page_height: float,
) -> bool:
    fn_x1, fn_y1, fn_x2, fn_y2 = fn_bbox[0], fn_bbox[1], fn_bbox[2], fn_bbox[3]
    fn_width = max(1.0, fn_x2 - fn_x1)
    # Page-bottom footnote zone exclusion
    if fn_y1 > page_height * 0.82:
        return False
    for body in body_blocks:
        bb = body.get("bbox") or body.get("block_bbox") or []
        if len(bb) < 4:
            continue
        bx1, by1, bx2, by2 = bb[0], bb[1], bb[2], bb[3]
        h_overlap = max(0.0, min(fn_x2, bx2) - max(fn_x1, bx1))
        x_aligned = h_overlap / fn_width >= 0.5
        if not x_aligned:
            continue
        overlaps_y = fn_y1 < by2 and fn_y2 > by1
        gap = fn_y1 - by2
        near_below = 0 <= gap <= page_height * 0.08
        if overlaps_y or near_below:
            return True
    return False
```

- [ ] **Step 4: Write `_convert_footnotes_to_callouts` tests**

```python

def test_footnote_in_body_zone_smaller_font_converts():
    """Footnote near body with smaller font → converts to structured_insert."""
    from paperforge.worker.ocr_render import _convert_footnotes_to_callouts
    blocks = [
        {"page": 1, "block_id": 0, "role": "paper_title", "text": "Title",
         "bbox": [100, 50, 800, 100], "page_height": 1500},
        {"page": 1, "block_id": 1, "role": "body_paragraph",
         "text": "Real body text that has at least twenty words in it to make the count threshold trigger correctly here.",
         "bbox": [100, 300, 800, 500], "page_height": 1500,
         "span_signature": {"font_size": 9.0}},
        {"page": 1, "block_id": 2, "role": "footnote",
         "text": "Y. Bai, Z. Wang, X. He — affiliation footnote with author details and addresses.",
         "bbox": [100, 520, 800, 600], "page_height": 1500,
         "span_signature": {"font_size": 7.5}},
    ]
    result = _convert_footnotes_to_callouts(blocks)
    fn = next(b for b in result if b["block_id"] == 2)
    assert fn["role"] == "structured_insert", f"Expected structured_insert, got {fn['role']}"


def test_footnote_same_font_stays_footnote():
    from paperforge.worker.ocr_render import _convert_footnotes_to_callouts
    blocks = [
        {"page": 1, "block_id": 1, "role": "body_paragraph",
         "text": "Body text with at least twenty words here for testing detection logic accordingly.",
         "bbox": [100, 300, 800, 500], "page_height": 1500,
         "span_signature": {"font_size": 9.0}},
        {"page": 1, "block_id": 2, "role": "footnote",
         "text": "Same font size footnote.",
         "bbox": [100, 520, 800, 600], "page_height": 1500,
         "span_signature": {"font_size": 9.0}},
    ]
    result = _convert_footnotes_to_callouts(blocks)
    fn = next(b for b in result if b["block_id"] == 2)
    assert fn["role"] == "footnote"


def test_footnote_page_bottom_stays_footnote():
    from paperforge.worker.ocr_render import _convert_footnotes_to_callouts
    blocks = [
        {"page": 1, "block_id": 1, "role": "body_paragraph",
         "text": "Body text with at least twenty words here for testing purpose only thank you.",
         "bbox": [100, 300, 800, 500], "page_height": 1500,
         "span_signature": {"font_size": 9.0}},
        {"page": 1, "block_id": 2, "role": "footnote",
         "text": "Way at bottom of page.",
         "bbox": [100, 1300, 800, 1400], "page_height": 1500,
         "span_signature": {"font_size": 8.0}},
    ]
    result = _convert_footnotes_to_callouts(blocks)
    fn = next(b for b in result if b["block_id"] == 2)
    assert fn["role"] == "footnote"


def test_footnote_wrong_column_stays_footnote():
    from paperforge.worker.ocr_render import _convert_footnotes_to_callouts
    blocks = [
        {"page": 1, "block_id": 1, "role": "body_paragraph",
         "text": "Body text with at least twenty words here for testing purpose only.",
         "bbox": [400, 300, 800, 500], "page_height": 1500,
         "span_signature": {"font_size": 9.0}},
        {"page": 1, "block_id": 2, "role": "footnote",
         "text": "Left column footnote not aligned with body column.",
         "bbox": [50, 400, 200, 500], "page_height": 1500,
         "span_signature": {"font_size": 8.0}},
    ]
    result = _convert_footnotes_to_callouts(blocks)
    fn = next(b for b in result if b["block_id"] == 2)
    assert fn["role"] == "footnote"


def test_footnote_copyright_boilerplate_not_converted():
    """Copyright/boilerplate footnote → keep as footnote."""
    from paperforge.worker.ocr_render import _convert_footnotes_to_callouts
    blocks = [
        {"page": 1, "block_id": 1, "role": "body_paragraph",
         "text": "Body text with at least twenty words in this test scenario that must pass correctly.",
         "bbox": [100, 300, 800, 500], "page_height": 1500,
         "span_signature": {"font_size": 9.0}},
        {"page": 1, "block_id": 2, "role": "footnote",
         "text": "Copyright © 2023 Publisher. All rights reserved.",
         "bbox": [100, 520, 800, 560], "page_height": 1500,
         "span_signature": {"font_size": 8.0}},
    ]
    result = _convert_footnotes_to_callouts(blocks)
    fn = next(b for b in result if b["block_id"] == 2)
    assert fn["role"] == "footnote"


def test_footnote_without_positive_marker_stays_footnote():
    """Footnote near body flow but no affiliation/author content → not converted."""
    from paperforge.worker.ocr_render import _convert_footnotes_to_callouts
    blocks = [
        {"page": 1, "block_id": 1, "role": "body_paragraph",
         "text": "Body text with at least twenty words in this test scenario that must pass correctly.",
         "bbox": [100, 300, 800, 500], "page_height": 1500,
         "span_signature": {"font_size": 9.0}},
        {"page": 1, "block_id": 2, "role": "footnote",
         "text": "Some generic note in small font with no identifying author metadata.",
         "bbox": [100, 520, 800, 560], "page_height": 1500,
         "span_signature": {"font_size": 8.0}},
    ]
    result = _convert_footnotes_to_callouts(blocks)
    fn = next(b for b in result if b["block_id"] == 2)
    assert fn["role"] == "footnote"
```

- [ ] **Step 5: Run conversion tests**

Run: `python -m pytest tests/test_ocr_render_stabilization.py -v -k "footnote" --tb=short 2>&1 | tail -15`
Expected: 6 failures (5 conversion tests + 1 positive_marker test)

- [ ] **Step 6: Implement `_convert_footnotes_to_callouts`**

After the two helpers added in Step 3:

```python
_BOILERPLATE_MARKERS = frozenset({
    "copyright", "©", "all rights reserved", "downloaded from",
    "published by", "received:", "accepted:",
})

_POSITIVE_CALLOUT_MARKERS = frozenset({
    "correspondence",
    "corresponding author",
    "e-mail",
    "email",
    "department",
    "university",
    "institute",
    "affiliation",
    "address",
    "these authors contributed",
    "contributed equally",
})


def _convert_footnotes_to_callouts(blocks: list[dict]) -> list[dict]:
    """Convert qualifying footnotes to structured_insert (callout).

    Conditions: role==footnote, near body flow, font < 0.9*body_font,
    not boilerplate, has positive affiliation/author content or symbol.
    """
    # Group body blocks and font sizes by page
    body_blocks = [b for b in blocks if b.get("role") == "body_paragraph"]
    body_fonts_by_page: dict[int, list[float]] = {}
    for body in body_blocks:
        p = int(body.get("page", 0) or 0)
        fs = _block_font_size(body)
        if fs is not None:
            body_fonts_by_page.setdefault(p, []).append(fs)
    all_body_fonts = [fs for sizes in body_fonts_by_page.values() for fs in sizes]
    if not all_body_fonts:
        return blocks

    result = list(blocks)
    for i, b in enumerate(result):
        if b.get("role") != "footnote":
            continue
        bbox = b.get("bbox") or b.get("block_bbox") or []
        if len(bbox) < 4:
            continue

        raw_text = str(b.get("text", "") or "")
        text_lower = raw_text.lower()

        # Exclude boilerplate
        if any(m in text_lower for m in _BOILERPLATE_MARKERS):
            continue

        # Positive allow: affiliation/author content or superscript symbol
        has_positive = any(m in text_lower for m in _POSITIVE_CALLOUT_MARKERS)
        has_symbol = any(sym in raw_text for sym in ("†", "*", "‡", "§"))
        if not (has_positive or has_symbol):
            continue

        # Font check — use same-page body font median
        fn_page = int(b.get("page", 0) or 0)
        page_body_fonts = body_fonts_by_page.get(fn_page) or all_body_fonts
        body_font_median = sorted(page_body_fonts)[len(page_body_fonts) // 2]
        fn_fs = _block_font_size(b)
        if fn_fs is None or fn_fs >= body_font_median * 0.9:
            continue

        # Body zone check — use same-page body blocks
        page_body_blocks = [bb for bb in body_blocks if int(bb.get("page", 0) or 0) == fn_page]
        page_height = max(
            (
                float(bb.get("page_height") or 0)
                for bb in blocks
                if int(bb.get("page", 0) or 0) == fn_page
            ),
            default=0.0,
        ) or 1500.0

        if not _is_near_body_flow(bbox, page_body_blocks, page_height):
            continue

        result[i] = dict(b)
        result[i]["role"] = "structured_insert"
        from paperforge.worker.ocr_decisions import record_decision
        record_decision(
            result[i],
            stage="footnote_to_callout",
            old_role="footnote",
            new_role="structured_insert",
            reason=f"footnote near body flow font={fn_fs:.1f} < body={body_font_median:.1f}",
        )

    return result
```

- [ ] **Step 7: Find and insert at correct location in `render_fulltext_markdown`**

Search for `_build_heading_style_profiles` in `ocr_render.py`:

```bash
rg "_build_heading_style_profiles" paperforge/worker/ocr_render.py -n
```

The exact location. Insert right before that call:

```python
    # -- block 9 callout conversion: footnotes in body zone with smaller font --
    structured_blocks = _convert_footnotes_to_callouts(structured_blocks)

    style_profiles = _build_heading_style_profiles(structured_blocks)
```

This ensures the conversion happens AFTER all document normalization (roles are final) and BEFORE tail reorder (so converted blocks stay in main flow).

- [ ] **Step 8: Run conversion tests**

Run: `python -m pytest tests/test_ocr_render_stabilization.py -v -k "footnote" --tb=short 2>&1 | tail -10`
Expected: 6 passes

- [ ] **Step 9: Add full render callout test**

```python

def test_footnote_to_callout_full_render(tmp_path):
    """Full render output shows [!NOTE] for qualifying footnote."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {"page": 1, "block_id": 0, "role": "paper_title", "text": "Test Title",
         "bbox": [100, 50, 800, 100], "page_height": 1500, "render_default": True,
         "span_signature": {"font_size": 12.0}},
        {"page": 1, "block_id": 1, "role": "body_paragraph",
         "text": "Body text that has at least twenty words in the paragraph for the threshold test to pass correctly.",
         "bbox": [100, 300, 800, 500], "page_height": 1500, "render_default": True,
         "span_signature": {"font_size": 9.0}},
        {"page": 1, "block_id": 2, "role": "footnote",
         "text": "Correspondence to: John Doe, Department of Orthopaedic Surgery.",
         "bbox": [100, 520, 800, 560], "page_height": 1500, "render_default": True,
         "span_signature": {"font_size": 8.0}},
    ]
    doc_structure = type("_", (), {
        "body_family_anchor": {},
        "spread_start": None,
        "source_frontmatter_anchors": {},
        "tail_reading_order": None,
        "reference_zones": None,
        "reference_zone": None,
    })()

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unresolved_clusters": []},
        table_inventory={"tables": []},
        page_count=1,
        document_structure=doc_structure,
        reader_payload={"reader_figures": [], "consumed_caption_block_ids": []},
    )
    assert "[!NOTE]" in md, f"Expected [!NOTE] callout in output:\n{md}"
    assert "Correspondence to: John Doe" in md
```

- [ ] **Step 10: Run all tests including full render**

Run: `python -m pytest tests/test_ocr_render_stabilization.py -v --tb=short 2>&1 | tail -10`
Expected: All pass (including new full render test)

- [ ] **Step 11: Run full regression suite**

Run: `python -m pytest tests/ -v --tb=short 2>&1 | tail -10`
Expected: All tests pass (or only pre-existing unrelated failures)

- [ ] **Step 12: Commit (Task 2 only)**

```bash
git add -A && git commit -m "feat: convert body-zone footnotes with distinct font to callout"
```
