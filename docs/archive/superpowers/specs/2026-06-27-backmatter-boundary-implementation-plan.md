# Implementation Plan: Backmatter Boundary Redesign

> **Based on:** `2026-06-27-backmatter-boundary-redesign.md`
> **Type:** Ref-anchored partition replaces `_reconcile_tail_spread()`, all in `ocr_document.py`
> **Verification:** 25K5KZAQ (CRediT fix), NC66N4Q3 (same-page body+ref), 9TW98JH8 (regression)

---

## Overview

Replace the later `_reconcile_tail_spread()` call in `normalize_document_structure()`
with a ref-anchored 3-way partition (pre-ref / reference / post-ref) when a verified
`reference_zone` exists. Pre-ref disclosure headings (CRediT, Ethics, Declaration)
are normalized as local same-column runs only — they NEVER set global boundaries.

**Does NOT affect:**
- First `infer_zones()` call near the top (unchanged)
- `_reconcile_tail_spread()` — kept as fallback for papers without reference zone
- `_normalize_backmatter_roles_after_boundary()` — kept as fallback
- `_promote_tail_body_candidates()` — SKIPPED in ref-partitioned path (Contract C)

---

## Implementation guardrails (read before coding)

```
- Do NOT redefine existing helpers: _zone_block_key, _block_y_top, _block_y_bottom already exist.
- Do NOT use boundary_band.end_page as reference end in ref-partition path.
- Do NOT classify same-column blocks as reference only by x-column membership.
- Do NOT let a disclosure heading consume across ANY next heading, including another disclosure heading — each heading must be handled by its own outer-loop iteration.
- Do NOT run _promote_tail_body_candidates() or _assign_tail_spread_ownership() after ref_partition_active=True.
- After refreshing region_bus, clear stale body/reference/tail zones and re-apply zone labels.
- Normalize reference partition roles BEFORE _sanitize_reference_zone_boundary().
```

---

## Step 1: `_has_verified_reference_zone()`

```python
def _has_verified_reference_zone(region_bus: dict[str, dict]) -> bool:
    """Check if region_bus contains a verified reference zone with block IDs."""
    ref_zone = region_bus.get("reference_zone", {}) or {}
    if ref_zone.get("status") not in ("ACCEPT", "HOLD"):
        return False
    block_ids = ref_zone.get("block_ids") or []
    return len(block_ids) > 0
```

---

## Step 2: Constants

```python
_KNOWN_PRE_REFERENCE_DISCLOSURE_HEADINGS: dict[str, list[str]] = {
    "credit authorship contribution statement": [],
    "ethics approval and consent to participate": ["ethics statement", "ethical approval"],
    "declaration of competing interest": [],
    "competing interests": ["conflict of interest"],
    "data availability": ["data availability statement"],
    "acknowledgements": ["acknowledgments", "acknowledgement", "acknowledgment"],
    "author contributions": [],
}

_STRONG_BODY_HEADINGS: frozenset[str] = frozenset({
    "discussion", "conclusion", "conclusions", "results", "summary",
    "limitations", "future perspectives", "materials and methods",
    "methods", "introduction",
})

_HEADING_ROLES: frozenset[str] = frozenset({
    "section_heading", "subsection_heading", "sub_subsection_heading",
    "backmatter_heading", "backmatter_boundary_heading", "backmatter_heading_candidate",
})

_MARKER_HEADING_TYPES: frozenset[str] = frozenset({
    "heading_numbered", "heading_arabic", "heading_decimal",
})
```

---

## Step 3: `_resolve_reference_zone_extent()`

**P0-2 fix: Do NOT redefine `_zone_block_key` — reuse existing one.**

```python
def _derive_effective_end_from_block_ids(
    blocks: list[dict], block_ids: list[str]
) -> int | None:
    """Scan blocks for max page among reference_zone.block_ids.
    block_ids may be bare block_id or `p{page}:{block_id}` artifact keys.
    """
    id_set = {str(x) for x in block_ids}  # P0-6b: str conversion
    max_page = None
    for b in blocks:
        bid = str(b.get("block_id") or "")
        key = _zone_block_key(b)  # reuse existing helper
        if bid in id_set or key in id_set:
            p = int(b.get("page", 0) or 0)
            if p > 0:
                max_page = max(max_page, p) if max_page is not None else p
    return max_page


def _resolve_reference_zone_extent(
    blocks: list[dict],
    region_bus: dict[str, dict],
) -> tuple[int | None, int | None]:
    """Return (ref_start_page, ref_end_page) from region_bus.
    Uses effective_end_page or derives from trimmed block_ids.
    NEVER falls back to untrimmed boundary_band.end_page.
    """
    ref_zone = region_bus.get("reference_zone", {}) or {}
    block_ids: list[str] = ref_zone.get("block_ids") or []
    band = ref_zone.get("boundary_band") or {}
    ref_start = band.get("start_page")
    if not block_ids or ref_start is None:
        return None, None

    effective_end = ref_zone.get("effective_end_page")
    if effective_end is None:
        effective_end = _derive_effective_end_from_block_ids(blocks, block_ids)
    if effective_end is None:
        return None, None  # P0-6a: handle both-None case
    return ref_start, effective_end
```

---

## Step 4: `_classify_same_page_block()`

**P0-2: Reuse existing `_block_y_top()` / `_block_y_bottom()`. Do NOT redefine.**
**P0-3: Use correct marker type set, not invented names.**
**P0-4: Remove `_compute_ref_heading_pages()` — fallback conservatively returns `pre_ref`.**

Reference marker types from existing code:
```python
_REFERENCE_ZONE_MARKER_TYPES = {
    "reference_numeric_bracket", "reference_numeric_dot",
    "reference_numeric_parenthesis", "reference_pattern", "citation_line",
}
```

```python
def _block_x_center(block: dict) -> float:
    bbox = block.get("bbox") or [0, 0, 0, 0]
    return (bbox[0] + bbox[2]) / 2.0 if len(bbox) >= 4 else 0.0


def _classify_same_page_block(  # P0-4: no _compute_ref_heading_pages
    block: dict,
    region_bus: dict,
    page: int,
    ref_zones: list[ReferenceZone] | None = None,
    page_layouts: dict[int, PageLayoutProfile] | None = None,
) -> str:
    """Classify a block on a shared body/ref page.

    A block is "reference" only if it explicitly belongs to the reference zone.
    Conservative: when uncertain, return "pre_ref" (keeps body in body).
    """
    role = str(block.get("role") or "")
    seed_role = str(block.get("seed_role") or "")
    if role in {"reference_heading", "reference_item"}:
        return "reference"
    if seed_role in {"reference_heading", "reference_item"}:
        return "reference"

    # Check block_ids / composite_block_ids membership
    ref_zone = region_bus.get("reference_zone", {}) or {}
    ref_ids = {str(x) for x in (ref_zone.get("block_ids") or [])}
    ref_comp_ids = {str(x) for x in (ref_zone.get("composite_block_ids") or [])}
    block_key = str(block.get("block_id") or "")
    art_key = _zone_block_key(block)
    if block_key in ref_ids or art_key in ref_ids:
        return "reference"
    if block_key in ref_comp_ids or art_key in ref_comp_ids:
        return "reference"

    # Column-aware: below ref heading, same column, with reference marker
    if ref_zones and page_layouts:
        block_x = _block_x_center(block)
        layout = page_layouts.get(page)
        col_boundaries = layout.column_boundaries if layout else []
        for rz in ref_zones:
            if rz.page != page:
                continue
            if not col_boundaries or rz.column_index >= len(col_boundaries):
                continue
            col_range = _column_x_range(rz.column_index, col_boundaries)
            if col_range[0] <= block_x <= col_range[1]:
                if _block_y_top(block) >= rz.y_start:
                    marker = str((block.get("marker_signature") or {}).get("type") or "")
                    if marker in _REFERENCE_ZONE_MARKER_TYPES:
                        return "reference"
                    # In ref column but not a reference item — still body flow
                    # (conservative: don't force into ref zone without marker)
                    return "pre_ref"
                return "pre_ref"  # above ref heading in ref column
        return "pre_ref"  # different column

    # Fallback: no column data — return pre_ref conservatively
    return "pre_ref"
```

Helper for column x-range:
```python
def _column_x_range(
    column_index: int,
    col_boundaries: list[float],
    page_width: float = 1200.0,
) -> tuple[float, float]:
    """Return (x_start, x_end) for a column index."""
    if not col_boundaries:
        return (0.0, page_width)
    if column_index == 0:
        right = (col_boundaries[0] + col_boundaries[1]) / 2 if len(col_boundaries) > 1 else col_boundaries[0]
        return (0.0, right)
    if column_index < len(col_boundaries):
        left = (col_boundaries[column_index - 1] + col_boundaries[column_index]) / 2 if column_index > 0 else 0.0
        right = (col_boundaries[column_index] + col_boundaries[column_index + 1]) / 2 if column_index + 1 < len(col_boundaries) else page_width
        return (left, right)
    mid = (col_boundaries[-1] + page_width) / 2
    return (mid, page_width)
```

---

## Step 5: `_partition_by_reference_zone()`

```python
def _partition_by_reference_zone(
    blocks: list[dict],
    region_bus: dict[str, dict],
    ref_zones: list[ReferenceZone] | None = None,
    page_layouts: dict[int, PageLayoutProfile] | None = None,
) -> dict[str, list[dict]]:
    """Partition blocks into pre-ref / reference / post-ref.
    reference_zone is the ONLY boundary. Pre-ref disclosure headings do not
    participate in partition (normalized later).
    """
    ref_start, ref_end = _resolve_reference_zone_extent(blocks, region_bus)
    if ref_start is None or ref_end is None:  # P0-6a: both required
        return {"fallback": True}

    pre_ref, reference, post_ref = [], [], []
    for block in blocks:
        page = int(block.get("page", 0) or 0)
        if page < ref_start:
            pre_ref.append(block)
        elif page > ref_end:
            post_ref.append(block)
        else:
            zone = _classify_same_page_block(
                block, region_bus, page,
                ref_zones=ref_zones, page_layouts=page_layouts,
            )
            if zone == "pre_ref":
                pre_ref.append(block)
            elif zone == "reference":
                reference.append(block)
            else:
                post_ref.append(block)

    return {"pre_ref": pre_ref, "reference": reference, "post_ref": post_ref}
```

---

## Step 6a: `_normalize_reference_roles_from_partition()` **P0-1 — CRITICAL ADDITION**

**Must run BEFORE `_sanitize_reference_zone_boundary()` or the sanitizer will strip
untyped blocks from the reference zone.**

```python
def _normalize_reference_roles_from_partition(
    blocks: list[dict],
    partition: dict[str, list[dict]],
) -> None:
    """Ensure blocks in the reference partition have reference roles.

    Without this, _sanitize_reference_zone_boundary() strips any block in
    reference_zone whose role isn't reference_heading/reference_item.
    """
    for block in partition.get("reference", []):
        role = str(block.get("role") or "")
        seed = str(block.get("seed_role") or "")
        if role in {"reference_heading", "reference_item"}:
            continue
        if seed in {"reference_heading", "reference_item"}:
            block["role"] = seed
            continue
        # Fallback: check marker
        marker = str((block.get("marker_signature") or {}).get("type") or "")
        if marker in _REFERENCE_ZONE_MARKER_TYPES:
            block["role"] = "reference_item"
```

---

## Step 6b: `_normalize_pre_ref_disclosure_runs()`

**P0-5 fix: Disclosure run must break at ANY next heading, including another disclosure heading.**
Each disclosure heading is handled by its own outer-loop iteration.

```python
def _is_known_disclosure(text: str) -> bool:
    text_norm = re.sub(r"\s+", " ", text).strip().lower()
    for key, aliases in _KNOWN_PRE_REFERENCE_DISCLOSURE_HEADINGS.items():
        if text_norm == key or text_norm in aliases:
            return True
    return False


def _get_column_index(block: dict, col_boundaries: list[float]) -> int | None:
    """Return column index (0=L, 1=R) or None if undetermined."""
    if not col_boundaries:
        return None
    bbox = block.get("bbox") or [0, 0, 0, 0]
    if len(bbox) < 4:
        return None
    cx = (bbox[0] + bbox[2]) / 2.0
    for i in range(len(col_boundaries) - 1):
        mid = (col_boundaries[i] + col_boundaries[i + 1]) / 2
        if cx <= mid:
            return i
    return len(col_boundaries) - 1


def _normalize_pre_ref_disclosure_runs(
    partition: dict[str, list[dict]],
    ref_start_page: int | None,
    total_pages: int,
    page_layouts: dict[int, PageLayoutProfile] | None = None,
) -> None:
    """Local role normalization for known disclosure sections before ref.

    Contract B rules enforced:
    - Local same-column runs only
    - Does NOT cross ANY next heading (including another disclosure heading) — P0-5
    - Does NOT cross STRONG_BODY_HEADING
    - Does NOT cross numbered heading
    - Does NOT cross column boundary
    - Does NOT cross ref_start_page
    """
    pre_ref = partition.get("pre_ref", [])
    if ref_start_page is None or not pre_ref:
        return

    for i, block in enumerate(pre_ref):
        text = str(block.get("text", "") or "").strip().lower()
        text_norm = re.sub(r"\s+", " ", text)

        matched_key = None
        for key, aliases in _KNOWN_PRE_REFERENCE_DISCLOSURE_HEADINGS.items():
            if text_norm == key or text_norm in aliases:
                matched_key = key
                break
        if matched_key is None:
            continue

        # Heading-like gate
        role = str(block.get("role") or "")
        seed_role = str(block.get("seed_role") or "")
        raw_label = str(block.get("raw_label") or "")
        marker_type = str((block.get("marker_signature") or {}).get("type") or "")
        heading_like = (
            role in _HEADING_ROLES
            or seed_role in _HEADING_ROLES
            or raw_label == "paragraph_title"
            or marker_type in _MARKER_HEADING_TYPES
        )
        if not heading_like:
            span = block.get("span_signature") or {}
            if not span.get("bold") and not span.get("font_size", 0) > 10:
                continue
            if len(text.split()) > 20:
                continue

        # Proximity gate (relative to ref_start, not total_pages ratio)
        block_page = int(block.get("page", 0) or 0)
        if ref_start_page is not None:
            max_before_ref = max(2, int(total_pages * 0.25))
            if block_page > ref_start_page or block_page < max(1, ref_start_page - max_before_ref):
                continue

        # Determine column for run — use page_layouts if available
        block_col = None
        if page_layouts is not None:
            layout = page_layouts.get(block_page)
            if layout is not None:
                block_col = _get_column_index(block, layout.column_boundaries)

        # Normalize run
        block["role"] = "backmatter_heading"
        block["_pre_ref_disclosure_run"] = True

        for j in range(i + 1, len(pre_ref)):
            nb = pre_ref[j]
            np_ = int(nb.get("page", 0) or 0)
            if np_ > ref_start_page:
                break

            # Column guard — P0-5: if column data available, enforce same column
            if block_col is not None and page_layouts is not None:
                nlayout = page_layouts.get(np_)
                if nlayout is not None:
                    nc = _get_column_index(nb, nlayout.column_boundaries)
                    if nc is not None and nc != block_col:
                        break

            nt = str(nb.get("text", "") or "").strip().lower()
            nr = str(nb.get("role") or "")
            nrw = str(nb.get("raw_label") or "")
            nmt = str((nb.get("marker_signature") or {}).get("type") or "")
            next_heading = (
                nr in _HEADING_ROLES
                or nrw == "paragraph_title"
                or nmt in _MARKER_HEADING_TYPES
            )

            # P0-5: Stop at ANY next heading (including another disclosure).
            # Each disclosure heading gets its own outer-loop iteration.
            if next_heading:
                break

            # Body heading guards
            if any(nt.startswith(h) for h in _STRONG_BODY_HEADINGS):
                break
            if re.match(r"^\d+(?:\.\d+)*\.?\s", nt):
                break

            nr_final = str(nb.get("role") or "")
            if nr_final.endswith("_heading"):
                nb["role"] = "backmatter_heading"
            elif nr_final == "body_paragraph":
                nb["role"] = "backmatter_body"
            elif nr_final == "frontmatter_noise":
                nb["role"] = "backmatter_body"
            nb["_pre_ref_disclosure_run"] = True
```

---

## Step 7: `_build_tail_boundary_from_ref_partition()`

```python
def _build_tail_boundary_from_ref_partition(
    partition: dict[str, list[dict]],
    region_bus: dict[str, dict],
) -> TailBoundary | None:
    """Derive TailBoundary from the ref-anchored partition.
    body_end_page from actual body blocks. spread_start = references_start.
    """
    pre_ref = partition.get("pre_ref", [])
    reference = partition.get("reference", [])
    post_ref = partition.get("post_ref", [])

    body_like_pages = [
        int(b.get("page", 0) or 0) for b in pre_ref
        if b.get("role") in {"body_paragraph", "section_heading",
                             "subsection_heading", "sub_subsection_heading"}
    ]
    body_end_page = max(body_like_pages) if body_like_pages else None

    ref_pages = [int(b.get("page", 0) or 0) for b in reference if b.get("page")]
    post_ref_pages = [int(b.get("page", 0) or 0) for b in post_ref if b.get("page")]

    if not ref_pages:
        return None

    references_start = min(ref_pages)
    all_tail = ref_pages + post_ref_pages

    return TailBoundary(
        body_end_page=body_end_page,
        backmatter_start=references_start,
        references_start=references_start,
        spread_start=references_start,  # NOT body_end_page — Contract D
        spread_end=max(all_tail),
        is_clean_separated=True,
        reason="ref_zone_partition",
    )
```

---

## Step 8: Wire call site

**P0-6: After refreshing region_bus, clear stale zones and re-apply.**
**P0-1: Call `_normalize_reference_roles_from_partition()` before sanitizer.**

Find the second `page_layouts` recomputation block in `normalize_document_structure()`.

```python
# --- Ref-anchored partition (replaces second _reconcile_tail_spread) ---
page_layouts = _build_page_layout_profiles(blocks)

region_bus = infer_zones(blocks, ..., tail_spread=None)  # refresh for current roles
ref_zones = _detect_reference_zones(blocks, page_layouts)

ref_partition_active = False
if _has_verified_reference_zone(region_bus):
    partition = _partition_by_reference_zone(
        blocks, region_bus, ref_zones=ref_zones, page_layouts=page_layouts,
    )
    if "fallback" not in partition:
        _normalize_reference_roles_from_partition(blocks, partition)  # P0-1
        _normalize_pre_ref_disclosure_runs(
            partition,
            ref_start_page=_resolve_reference_zone_extent(blocks, region_bus)[0],
            total_pages=len({b.get("page") for b in blocks if b.get("page")}),
            page_layouts=page_layouts,
        )
        tail_spread = _build_tail_boundary_from_ref_partition(partition, region_bus)
        ref_partition_active = tail_spread is not None

        if ref_partition_active:
            # P0-6: clear stale zones and re-apply with new roles
            _clear_partition_zones(blocks)
            _apply_zone_labels(blocks, region_bus)
            _apply_content_zone_fallback(blocks, region_bus)
            _sanitize_reference_zone_boundary(blocks, region_bus)

if not ref_partition_active:
    tail_spread = _reconcile_tail_spread(blocks, page_layouts)
    if tail_spread is not None:
        backmatter_form = ...
        _normalize_backmatter_roles_after_boundary(tail_spread, backmatter_form, blocks)
```

The stale-zone clearing helper:
```python
def _clear_partition_zones(blocks: list[dict]) -> None:
    """Clear zones that will be reassigned after ref-partition role normalization."""
    _STALE_ZONES = frozenset({
        "body_zone", "reference_zone", "tail_nonref_hold_zone",
        "post_reference_backmatter_zone", "display_zone",
    })
    for b in blocks:
        if b.get("zone") in _STALE_ZONES:
            b["zone"] = ""
```

Then the Contract C skip further down:
```python
# --- CONDITIONAL: skip old promotion in ref-partitioned path ---
if not ref_partition_active:
    blocks = _promote_tail_body_candidates(blocks, doc_structure, ...)
    blocks = _assign_tail_spread_ownership(blocks, doc_structure)
```

---

## Step 9: Modify `infer_zones()` — store `effective_end_page`

Inside `infer_zones()`, after the reference_blocks trimming step (~lines 1067–1081):

```python
# After trimming reference_blocks for post-ref backmatter:
if post_ref_backmatter_start is not None:
    trimmed_pages = [
        int(b.get("page", 0) or 0) for b in reference_blocks
        if int(b.get("page", 0) or 0) > 0
    ]
    effective_reference_end_page = max(trimmed_pages) if trimmed_pages else first_reference_page
else:
    effective_reference_end_page = reference_end_page  # same as current behavior

# Pass into _make_zone() — NOT as ref_zone["..."] direct assignment:
"reference_zone": _make_zone(  # or simpler: pass as kwargs if _make_zone supports it
    ...,
    boundary_band=_page_band(first_reference_page, reference_end_page),
    effective_end_page=effective_reference_end_page,
),
```

If `_make_zone()` does not accept arbitrary kwargs, set it after the call:
```python
ref_zone_entry = _make_zone(...)  # existing call
ref_zone_entry["effective_end_page"] = effective_reference_end_page  # add after
```

---

## Step 10: Tests

**File:** `tests/unit/worker/test_backmatter_boundary.py`

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_ref_zone_partition_simple` | Single-col body p1-8, ref p9-10, post-ref p11 → correct 3-way split |
| 2 | `test_ref_zone_partition_corrects_credit` | 25K5KZAQ: CRediT before ref → backmatter_heading; Discussion after → unchanged |
| 3 | `test_pre_ref_disclosure_does_not_change_ref_start` | CRediT found → ref_start_page unchanged (Contract A) |
| 4 | `test_disclosure_does_not_span_strong_body_heading` | "CRediT ... Conclusion ... References" → Conclusion NOT consumed |
| 5 | `test_disclosure_does_not_span_numbered_heading` | "CRediT ... 5. Conclusion ... References" → section NOT consumed |
| 6 | `test_disclosure_stops_at_another_disclosure` | **P0-5**: "CRediT ... Ethics ... References" → CRediT does NOT consume Ethics body |
| 7 | `test_disclosure_stops_at_ref_start` | Blocks after CRediT but before ref, past another heading → NOT consumed |
| 8 | `test_same_page_body_ref_column_aware` | Left-col body stays body_flow, right-col ref starts correctly |
| 9 | `test_no_ref_zone_falls_back` | No reference_zone → old path, no crash |
| 10 | `test_known_disclosure_exact_match` | Exact match triggers; substring "funding" in body heading doesn't |
| 11 | `test_disclosure_proximity_gate` | page 2 of 15, ref at page 12 → NOT triggered (too far) |
| 12 | `test_disclosure_same_column_only` | Two-column: right-col CRediT does NOT consume left-col text |
| 13 | `test_reference_partition_normalizes_reference_roles` | **P0-1**: partition reference block with role body_paragraph → reference_item before sanitizer |
| 14 | `test_ref_partition_clears_stale_tail_zone` | **P0-6**: initial zone=tail_nonref_hold_zone, after partition → re-assigned correctly |
| 15 | `test_same_page_ref_column_non_reference_not_forced` | Block in ref column, below ref heading, no marker → NOT forced to "reference" |
| 16 | `test_body_end_page_from_actual_blocks` | Pre-ref body max page determines body_end_page, not mechanical `ref_start - 1` |
| 17 | `test_spread_start_is_references_start` | spread_start == references_start, not body_end_page |
| 18 | `test_promote_tail_body_skipped_on_ref_path` | ref_partition_active → _promote_tail_body_candidates not called |
| 19 | `test_reference_end_page_trimming` | Post-ref backmatter page excluded from effective_end_page |
| 20 | `test_infer_zones_stores_effective_end_page` | After trimming, effective_end_page < raw end_page |

---

## Step 11: Verify

**Audit papers:**
- **25K5KZAQ:** CRediT/Ethics → `backmatter_heading`/`backmatter_body`. Discussion/Conclusion unchanged. Fulltext renders correctly.
- **NC66N4Q3:** page 56 left-col Discussion → body_flow, right-col refs → reference_zone. No degraded tail mode.
- **9TW98JH8 (regression):** 20/20 blocks correct, unchanged.

**Test run:**
```bash
python -m pytest tests/unit/ tests/cli/ -v --tb=short
ruff check --fix paperforge/ && ruff format paperforge/
```

---

## Summary of P0 fixes vs original plan

| P0 | Issue | Fix |
|----|-------|-----|
| P0-1 | Missing `_normalize_reference_roles_from_partition()` | Added Step 6a — runs before sanitizer |
| P0-2 | Redefined existing helpers | Plan now says "reuse existing `_zone_block_key`, `_block_y_top`, `_block_y_bottom`" |
| P0-3 | Wrong marker type names | Uses existing `_REFERENCE_ZONE_MARKER_TYPES` set |
| P0-4 | `_compute_ref_heading_pages()` doesn't exist | Removed this fallback; `_classify_same_page_block` conservatively returns `pre_ref` without column data |
| P0-5 | Disclosure run continues past another disclosure | Loop now `break`s at ANY next heading (P0-5 §6b) |
| P0-6 | Stale zones after region_bus refresh | Added `_clear_partition_zones()` + zone re-apply (Step 8) |

**Total diff:** ~320 lines new code + ~100 lines tests, all in `ocr_document.py` + new test file
