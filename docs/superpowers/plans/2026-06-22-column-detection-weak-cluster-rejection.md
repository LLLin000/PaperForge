# Weak Cluster Rejection for Column Detection — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix false two_column classification when a single short offset body line creates a spurious second x-center cluster. Add cluster metadata with weak-cluster rejection before layout type decision.

**Architecture:** Add `_cluster_page_column_groups()` returning cluster metadata dicts (center, count, y_coverage, word_count, blocks, etc.). Keep `_cluster_page_columns()` as a compatibility wrapper (body replaced with `return [c["center"] for c in _cluster_page_column_groups(...)]`). Add `_is_weak_isolated_column_cluster()` that rejects clusters with count<3 AND y_coverage<10% page height AND word_count<25. Modify `_classify_page_layout()` to filter weak clusters BEFORE deciding `column_count`, and use cluster `blocks` for role distribution instead of `page_width/2` midpoint.

**Tech Stack:** Python, no new dependencies.

---

### Task 1: Add `_cluster_page_column_groups()` function

**Files:**
- Modify: `paperforge/worker/ocr_document.py` — insert `_cluster_page_column_groups()` before `_cluster_page_columns()`, then replace `_cluster_page_columns()` body with wrapper

- [ ] **Step 1: Insert `_cluster_page_column_groups()` before `_cluster_page_columns()`, then replace `_cluster_page_columns()` body with wrapper**

Open `paperforge/worker/ocr_document.py`. Insert the new function before `_cluster_page_columns()` (currently at line 278), then replace the body of `_cluster_page_columns()` with a one-line wrapper:

```python
def _cluster_page_column_groups(page_blocks: list[dict], page_width: float) -> list[dict]:
    """Cluster block x-centers by column and return per-cluster metadata.

    Returns list of cluster dicts sorted by center ascending. Each dict:
        center, count, center_min, center_max, y_min, y_max, y_coverage,
        word_count, width_median, block_ids, blocks
    """
    items: list[tuple[float, dict]] = []
    for block in page_blocks:
        bbox = block.get("bbox") or block.get("block_bbox")
        if not bbox or len(bbox) < 4:
            continue
        block_width = bbox[2] - bbox[0]
        if block_width <= 50:
            continue
        x_center = (bbox[0] + bbox[2]) / 2
        items.append((x_center, block))

    if not items:
        return [{
            "center": page_width / 2,
            "count": 0,
            "center_min": page_width / 2,
            "center_max": page_width / 2,
            "y_min": 0.0,
            "y_max": 0.0,
            "y_coverage": 0.0,
            "word_count": 0,
            "width_median": 0.0,
            "block_ids": [],
            "blocks": [],
        }]

    items.sort(key=lambda x: x[0])
    gap_threshold = page_width * 0.15
    raw_clusters: list[list[dict]] = [[items[0][1]]]
    last_center = items[0][0]

    for center, block in items[1:]:
        if center - last_center > gap_threshold:
            raw_clusters.append([block])
        else:
            raw_clusters[-1].append(block)
        last_center = center

    result: list[dict] = []
    for cluster_blocks in raw_clusters:
        valid_bboxes = [
            bb for b in cluster_blocks
            for bb in [b.get("bbox") or b.get("block_bbox")]
            if bb and len(bb) >= 4
        ]
        centers_for_compute = [(bb[0] + bb[2]) / 2 for bb in valid_bboxes]

        widths = sorted(bb[2] - bb[0] for bb in valid_bboxes)

        y_vals = [(bb[1], bb[3]) for bb in valid_bboxes]

        center_val = sum(centers_for_compute) / len(centers_for_compute) if centers_for_compute else page_width / 2
        y_min_val = min(yv[0] for yv in y_vals) if y_vals else 0.0
        y_max_val = max(yv[1] for yv in y_vals) if y_vals else 0.0

        result.append({
            "center": center_val,
            "count": len(cluster_blocks),
            "center_min": min(centers_for_compute) if centers_for_compute else page_width / 2,
            "center_max": max(centers_for_compute) if centers_for_compute else page_width / 2,
            "y_min": y_min_val,
            "y_max": y_max_val,
            "y_coverage": y_max_val - y_min_val,
            "word_count": sum(len(_block_text(b).split()) for b in cluster_blocks),
            "width_median": widths[len(widths) // 2] if widths else 0.0,
            "block_ids": [b.get("block_id", "") for b in cluster_blocks],
            "blocks": cluster_blocks,
        })

    result.sort(key=lambda c: c["center"])
    return result


# ponytail: Replace _cluster_page_columns() body with wrapper delegating to _cluster_page_column_groups()
def _cluster_page_columns(page_blocks: list[dict], page_width: float) -> list[float]:
    return [c["center"] for c in _cluster_page_column_groups(page_blocks, page_width)]
```

- [ ] **Step 2: Verify wrapper — run existing layout tests**

```bash
python -m pytest tests/test_ocr_document.py::test_layout_profile_single_column tests/test_ocr_document.py::test_layout_profile_two_column tests/test_ocr_document.py::test_layout_profile_mixed_tail -v --tb=short
```

Expected: All 3 tests PASS; wrapper preserves old observable behavior.

- [ ] **Step 3: Commit**

```bash
git add paperforge/worker/ocr_document.py
git commit -m "feat: add _cluster_page_column_groups() returning cluster metadata"
```

---

### Task 2: Add `_is_weak_isolated_column_cluster()` and modify `_classify_page_layout()`

**Files:**
- Modify: `paperforge/worker/ocr_document.py` — insert helper before `_classify_page_layout()`, replace `_classify_page_layout()` body

- [ ] **Step 1: Read current functions to confirm boundaries**

Read `paperforge/worker/ocr_document.py` from `_cluster_page_columns` through `_classify_page_layout` to confirm no conflicting changes since this plan was written.

- [ ] **Step 2: Insert `_is_weak_isolated_column_cluster()` before `_classify_page_layout()`**

After `_cluster_page_column_groups()` (just inserted), add:

```python
def _is_weak_isolated_column_cluster(cluster: dict, page_height: float) -> bool:
    """Return True if this cluster has insufficient evidence to be a real column."""
    if cluster["count"] >= 3:
        return False
    if cluster["y_coverage"] >= page_height * 0.10:
        return False
    if cluster["word_count"] >= 25:
        return False
    return True
```

- [ ] **Step 3: Replace `_classify_page_layout()` body**

Replace the entire function with:

```python
def _classify_page_layout(page_blocks: list[dict], page_width: float, page_height: float) -> PageLayoutProfile:
    """Classify a page's layout based on column clusters and role distribution."""
    clusters = _cluster_page_column_groups(page_blocks, page_width)

    real_clusters = [
        c for c in clusters
        if not _is_weak_isolated_column_cluster(c, page_height)
    ]

    if not real_clusters:
        return PageLayoutProfile(
            column_count=1,
            column_boundaries=[page_width / 2],
            layout_type="single_column",
            confidence=0.35,
            evidence=["eligible_body_blocks", "all_column_clusters_weak"],
        )

    evidence_extra: list[str] = []
    if len(real_clusters) < len(clusters):
        evidence_extra.append("weak_isolated_column_cluster_ignored")

    centers = [c["center"] for c in real_clusters]
    column_count = len(real_clusters)

    if column_count == 1:
        return PageLayoutProfile(
            column_count=1,
            column_boundaries=[real_clusters[0]["center"]],
            layout_type="single_column",
            confidence=0.55 if evidence_extra else 0.7,
            evidence=["eligible_body_blocks"] + evidence_extra,
        )

    if column_count == 2:
        col_blocks: dict[int, list[str]] = {0: [], 1: []}
        for i in (0, 1):
            for block in real_clusters[i]["blocks"]:
                col_blocks[i].append(block.get("role", ""))

        body_roles = {
            "body_paragraph",
            "section_heading",
            "subsection_heading",
            "sub_subsection_heading",
        }

        col_has_body: dict[int, bool] = {}
        col_has_tail: dict[int, bool] = {}
        for col_idx, roles in col_blocks.items():
            col_has_body[col_idx] = bool(set(roles) & body_roles)
            col_has_tail[col_idx] = bool(set(roles) & _TAIL_ROLES)

        one_side_body = col_has_body[0] and not col_has_tail[0]
        other_side_tail = not col_has_body[1] and col_has_tail[1]
        swapped = col_has_body[1] and not col_has_tail[1]
        swapped_tail = not col_has_body[0] and col_has_tail[0]

        if (one_side_body and other_side_tail) or (swapped and swapped_tail):
            return PageLayoutProfile(
                column_count=2,
                column_boundaries=centers,
                layout_type="mixed_tail",
                confidence=0.6,
                evidence=["eligible_body_blocks", "two_center_clusters"] + evidence_extra,
            )

        return PageLayoutProfile(
            column_count=2,
            column_boundaries=centers,
            layout_type="two_column",
            confidence=0.7,
            evidence=["eligible_body_blocks"] + evidence_extra,
        )

    return PageLayoutProfile(
        column_count=column_count,
        column_boundaries=centers,
        layout_type="two_column",
        confidence=0.5,
        evidence=["eligible_body_blocks", "wide_dispersion"] + evidence_extra,
    )
```

- [ ] **Step 4: Run existing layout tests to verify no regression**

```bash
python -m pytest tests/test_ocr_document.py::test_layout_profile_single_column tests/test_ocr_document.py::test_layout_profile_two_column tests/test_ocr_document.py::test_layout_profile_mixed_tail tests/test_ocr_document.py::test_layout_profile_build_profiles -v --tb=short
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_document.py
git commit -m "feat: add weak isolated cluster rejection to column detection"
```

---

### Task 3: Add test — short isolated line does NOT create two_column

**Files:**
- Modify: `tests/test_ocr_document.py` — append at end of file

- [ ] **Step 1: Add `test_short_isolated_body_line_does_not_create_two_column_layout`**

Append to `tests/test_ocr_document.py`:

```python
def test_short_isolated_body_line_does_not_create_two_column_layout() -> None:
    """Replicates page 12 of paper 2E4EPHN2: 6 full-width body blocks +
    1 short offset line should NOT be classified as two_column."""
    from paperforge.worker.ocr_document import _classify_page_layout

    page_width = 1191.0
    page_height = 1684.0
    blocks = [
        {"role": "body_paragraph", "bbox": [325, 224, 1123, 298], "text": "Long paragraph " * 40, "page_width": page_width},
        {"role": "body_paragraph", "bbox": [325, 299, 1124, 377], "text": "Long paragraph " * 40, "page_width": page_width},
        {"role": "body_paragraph", "bbox": [325, 398, 1125, 633], "text": "Long paragraph " * 40, "page_width": page_width},
        {"role": "body_paragraph", "bbox": [326, 643, 1125, 762], "text": "Long paragraph " * 40, "page_width": page_width},
        {"role": "body_paragraph", "bbox": [325, 772, 1124, 820], "text": "Long paragraph " * 40, "page_width": page_width},
        {"role": "body_paragraph", "bbox": [328, 832, 704, 854], "text": "Informed Consent Statement: Not applicable.", "page_width": page_width},
        {"role": "body_paragraph", "bbox": [327, 867, 1122, 914], "text": "Long paragraph " * 40, "page_width": page_width},
    ]

    profile = _classify_page_layout(blocks, page_width, page_height)

    assert profile.layout_type == "single_column", f"Expected single_column, got {profile.layout_type}"
    assert profile.column_count == 1, f"Expected column_count=1, got {profile.column_count}"
    assert "weak_isolated_column_cluster_ignored" in profile.evidence, (
        f"Expected weak_isolated_column_cluster_ignored in evidence, got {profile.evidence}"
    )
```

- [ ] **Step 2: Run test — expect PASS**

```bash
python -m pytest tests/test_ocr_document.py::test_short_isolated_body_line_does_not_create_two_column_layout -v --tb=short
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ocr_document.py
git commit -m "test: short isolated line does not create two_column layout"
```

---

### Task 4: Add test — balanced two_column still detected

**Files:**
- Modify: `tests/test_ocr_document.py` — append

- [ ] **Step 1: Add `test_balanced_two_column_layout_still_detected`**

Append to `tests/test_ocr_document.py`:

```python
def test_balanced_two_column_layout_still_detected() -> None:
    """True two-column page with multiple blocks per column must remain two_column."""
    from paperforge.worker.ocr_document import _classify_page_layout

    page_width = 800.0
    page_height = 1000.0
    blocks = [
        {"role": "body_paragraph", "bbox": [50, 100, 380, 250], "text": "Left body " * 30, "page_width": page_width},
        {"role": "body_paragraph", "bbox": [50, 270, 380, 420], "text": "Left body " * 30, "page_width": page_width},
        {"role": "body_paragraph", "bbox": [420, 100, 750, 250], "text": "Right body " * 30, "page_width": page_width},
        {"role": "body_paragraph", "bbox": [420, 270, 750, 420], "text": "Right body " * 30, "page_width": page_width},
    ]

    profile = _classify_page_layout(blocks, page_width, page_height)
    assert profile.layout_type == "two_column", f"Expected two_column, got {profile.layout_type}"
    assert profile.column_count == 2, f"Expected column_count=2, got {profile.column_count}"
```

- [ ] **Step 2: Run test — expect PASS**

```bash
python -m pytest tests/test_ocr_document.py::test_balanced_two_column_layout_still_detected -v --tb=short
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ocr_document.py
git commit -m "test: balanced two_column layout still detected"
```

---

### Task 5: Add test — one large block per column still two_column

**Files:**
- Modify: `tests/test_ocr_document.py` — append

- [ ] **Step 1: Add `test_single_large_block_per_column_still_two_column`**

Append to `tests/test_ocr_document.py`:

```python
def test_single_large_block_per_column_still_two_column() -> None:
    """Each column has only 1 block, but large y_coverage and word_count
    must still classify as two_column (not killed by count=1 guard)."""
    from paperforge.worker.ocr_document import _classify_page_layout

    page_width = 800.0
    page_height = 1000.0
    blocks = [
        {"role": "body_paragraph", "bbox": [50, 100, 380, 800], "text": "Left body " * 100, "page_width": page_width},
        {"role": "body_paragraph", "bbox": [420, 100, 750, 800], "text": "Right body " * 100, "page_width": page_width},
    ]

    profile = _classify_page_layout(blocks, page_width, page_height)
    assert profile.layout_type == "two_column", f"Expected two_column, got {profile.layout_type}"
    assert profile.column_count == 2, f"Expected column_count=2, got {profile.column_count}"
```

- [ ] **Step 2: Run test — expect PASS**

```bash
python -m pytest tests/test_ocr_document.py::test_single_large_block_per_column_still_two_column -v --tb=short
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ocr_document.py
git commit -m "test: single large block per column still two_column"
```

---

### Task 6: Add test — multiple weak offset lines do not trigger wide_dispersion

**Files:**
- Modify: `tests/test_ocr_document.py` — append

- [ ] **Step 1: Add `test_multiple_weak_offset_lines_do_not_create_wide_dispersion`**

Append to `tests/test_ocr_document.py`:

```python
def test_multiple_weak_offset_lines_do_not_create_wide_dispersion() -> None:
    """3 raw clusters (2 weak, 1 real) must produce single_column, not two_column/wide_dispersion."""
    from paperforge.worker.ocr_document import _classify_page_layout

    page_width = 1191.0
    page_height = 1684.0
    blocks = [
        {"role": "body_paragraph", "bbox": [325, 224, 1123, 298], "text": "Long paragraph " * 40, "page_width": page_width},
        {"role": "body_paragraph", "bbox": [325, 299, 1124, 377], "text": "Long paragraph " * 40, "page_width": page_width},
        {"role": "body_paragraph", "bbox": [328, 832, 704, 854], "text": "IC Statement: Not applicable.", "page_width": page_width},
        {"role": "body_paragraph", "bbox": [328, 870, 550, 890], "text": "Short note.", "page_width": page_width},
        {"role": "body_paragraph", "bbox": [327, 900, 1122, 950], "text": "Long paragraph " * 40, "page_width": page_width},
    ]

    profile = _classify_page_layout(blocks, page_width, page_height)

    assert profile.layout_type == "single_column", f"Expected single_column, got {profile.layout_type}"
    assert profile.column_count == 1, f"Expected column_count=1, got {profile.column_count}"
    assert "weak_isolated_column_cluster_ignored" in profile.evidence, (
        f"Expected weak_isolated_column_cluster_ignored in evidence, got {profile.evidence}"
    )
```

- [ ] **Step 2: Run test — expect PASS**

```bash
python -m pytest tests/test_ocr_document.py::test_multiple_weak_offset_lines_do_not_create_wide_dispersion -v --tb=short
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ocr_document.py
git commit -m "test: multiple weak offset lines do not trigger wide_dispersion"
```

---

### Task 7: Add optional test — all clusters weak fallback to single_column

**Files:**
- Modify: `tests/test_ocr_document.py` — append

- [ ] **Step 1: Add `test_all_clusters_weak_fallback_to_single_column`**

Append to `tests/test_ocr_document.py`:

```python
def test_all_clusters_weak_fallback_to_single_column() -> None:
    """When all clusters are weak (e.g. only short offset lines), fallback to low-confidence single_column."""
    from paperforge.worker.ocr_document import _classify_page_layout

    page_width = 1191.0
    page_height = 1684.0
    blocks = [
        {"role": "body_paragraph", "bbox": [328, 832, 704, 854], "text": "IC Statement: Not applicable.", "page_width": page_width},
        {"role": "body_paragraph", "bbox": [60, 870, 300, 890], "text": "Footnote text.", "page_width": page_width},
    ]

    profile = _classify_page_layout(blocks, page_width, page_height)

    assert profile.layout_type == "single_column", f"Expected single_column, got {profile.layout_type}"
    assert profile.confidence <= 0.35, f"Expected confidence <= 0.35, got {profile.confidence}"
    assert "all_column_clusters_weak" in profile.evidence, (
        f"Expected all_column_clusters_weak in evidence, got {profile.evidence}"
    )
```

- [ ] **Step 2: Run test — expect PASS**

```bash
python -m pytest tests/test_ocr_document.py::test_all_clusters_weak_fallback_to_single_column -v --tb=short
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ocr_document.py
git commit -m "test: all clusters weak fallback to single_column"
```

---

### Task 8: Run full test suites — verify no regression

**Files:** None (verification only)

- [ ] **Step 1: Run focused new tests**

```bash
python -m pytest tests/test_ocr_document.py -v --tb=short -k "weak or two_column or wide_dispersion or isolated"
```

Expected: At least 5 tests PASS (the 5 new tests + any existing matching keywords).

- [ ] **Step 2: Run full test_ocr_document.py**

```bash
python -m pytest tests/test_ocr_document.py -v --tb=short
```

Expected: All tests PASS. Note: existing tests that assert exact confidence (e.g. 0.7) for sparse one-block pages may now show confidence <= 0.35 if the sole cluster is weak. Use `<=` comparison instead of exact equality.

- [ ] **Step 3: Run all OCR-related tests**

```bash
python -m pytest tests/test_ocr_rendering.py tests/test_ocr_layout_zones.py tests/test_ocr_layout_first_regressions.py tests/test_ocr_render_stabilization.py -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 4: Verify build_profile tests (mixed_tail role distribution uses cluster blocks)**

```bash
python -m pytest tests/test_ocr_document.py::test_layout_profile_mixed_tail tests/test_ocr_document.py::test_layout_profile_build_profiles -v --tb=short
```

Expected: PASS. This confirms mixed_tail detection still works with cluster-based role distribution.

---

### Task 9: Rebuild affected paper and verify fix

**Files:** None (verification only)

- [ ] **Step 1: Rebuild page layout profiles for paper 2E4EPHN2**

```bash
$PYTHON -m paperforge ocr rebuild 2E4EPHN2 --keys derived
```

Expected: Page 12 now shows `single_column` layout_type.

- [ ] **Step 2: Verify `document_structure.json` for page 12**

Read `D:\L\OB\Literature-hub\System\PaperForge\ocr\2E4EPHN2\structure\document_structure.json` and check page 12 profile:
```json
"12": {
  "column_count": 1,
  "layout_type": "single_column",
  ...
}
```

Expected: `layout_type` is `"single_column"`.

- [ ] **Step 3: Observe `fulltext.md` reading order (optional, NOT guaranteed by this fix)**

Check that "Informed Consent Statement: Not applicable." appears in the rendered `fulltext.md`. Note: this fix addresses the layout profile misclassification. The renderer's `_sort_blocks_by_column()` still uses `page_width/2` midpoint and is NOT changed by this plan. The reading order in `fulltext.md` may or may not be correct depending on downstream tail reordering logic. Full reading order fix requires a separate renderer change (tracked separately).
