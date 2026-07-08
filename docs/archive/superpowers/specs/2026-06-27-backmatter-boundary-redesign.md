# Backmatter Boundary Redesign

**Date:** 2026-06-27
**Status:** Spec — for implementation
**Audit evidence:** 25K5KZAQ, NC66N4Q3
**Previous attempt:** `2026-06-27-figure-containment-and-backmatter-boundary-design.md` §4 (superseded)

---

## 0. Core contracts — READ BEFORE IMPLEMENTING

### Contract A — reference_zone is the ONLY hard boundary

Pre-ref backmatter headings (CRediT, Ethics, Declaration, etc.) may only normalize
**local same-column runs**. They must NEVER determine:

- `reference_zone.start` / `reference_zone.end`
- `body_end_page`
- `spread_start` / `spread_end`
- Body spine anchor page selection
- Whether the global tail region has begun

Only a **verified reference_zone** (status ACCEPT or HOLD with block_ids) may define
the global partition into pre-ref / reference / post-ref.

### Contract B — Pre-ref disclosure runs are local only

When a known disclosure heading is found before `reference_zone.start`, its role
normalization scope is limited to:

- The heading block itself
- Same-column blocks between it and the NEXT heading (any heading)
- Blocks up to `reference_zone.start` (whichever comes first)

It must NOT consume across:
- A numbered body section heading
- A canonical unnumbered body heading (Discussion, Conclusion, Results, Methods, Limitations, Future perspectives, Materials and methods)
- A column boundary
- `reference_zone.start`

### Contract C — New path skips old tail promotion

When the ref-partitioned path is active (`ref_partition_active = True`):
- `_promote_tail_body_candidates()` must be SKIPPED
- `_assign_tail_spread_ownership()` must be SKIPPED (or limited to only post-ref blocks)
- Only the partition's own role normalization may assign pre-ref tail roles

### Contract D — Derive body_end_page from actual body blocks

`body_end_page` must be the max page of blocks classified as pre-ref body_flow,
NOT a mechanical `ref_start_page - 1`. Same-page body+ref is valid.

### Implementation placement — CRITICAL: replace the LATER `_reconcile_tail_spread()` call

Do NOT insert the ref-partition path at the first `infer_zones()` call near the
top of `normalize_document_structure()`. The current pipeline computes `region_bus`
early, then resolves roles, recomputes `page_layouts`, and only THEN calls
`_reconcile_tail_spread()`.

The new ref-partition path must replace that **later** `_reconcile_tail_spread()`
decision point. At that point, recompute or refresh `region_bus`, compute `ref_zones`
from the recomputed `page_layouts`, and then choose:

- Verified `reference_zone` → ref-partition path
- No verified `reference_zone` → old `_reconcile_tail_spread()` fallback

---

## 1. Problem

### 1.1 Evidence (25K5KZAQ, NC66N4Q3)

**25K5KZAQ (Bioactive Materials, 11p):**
- Pages 9-10: CRediT/Ethics headings at font 7.97pt bold → `subsection_heading` (not `backmatter_heading`)
- "Declaration of competing interest" at y=829 → correctly `backmatter_heading` (contains "DECLARATION")
- Result: CRediT text renders as body prose above Discussion, not as backmatter

**NC66N4Q3 (Radiographic Atlas, 56p):**
- Page 56: two-column layout, left=Discussion, right=References
- `body_end_page=None`, `ref_start=None` — boundary detection fails because body+ref share final page
- `is_clean_separated = False` → tail spread logic enters degraded mode

### 1.2 Root cause

`normalize_document_structure()` computes `region_bus.reference_zone` early (first
`infer_zones()` call), but LATER recomputes `tail_spread` through `_reconcile_tail_spread()`
after role resolution and page-layout recomputation. The actual order is:

1. First `infer_zones()` → `region_bus.reference_zone` is set ✓
2. Role resolution / family partition / page_layouts recomputation
3. `_reconcile_tail_spread()` LATER OVERWRITES the boundary using old heuristic

The later heuristic becomes the authoritative `DocumentStructure` boundary and can
contradict the already-known `reference_zone`, especially on same-page body+ref layouts.

On column-mixed pages (body+ref same page), the forward scan also fails because
the left column has body without tail → `any_body_without_tail=True` → scan continues.

**Result:** `reference_zone` is already computed but never used to set the tail boundary.
The heuristic (forward/backward) wins over data-driven reference_zone.

### 1.3 Scope of impact

| Paper | Effect | Frequency |
|-------|--------|-----------|
| 25K5KZAQ | CRediT/Ethics in body flow, not backmatter | ~30-50% of papers with CRediT |
| Any with small-font disclosure headings | Disclosure → subsection_heading | Likely >10% |
| Same-page body+ref | tail_spread degraded, ref_start=None | ≤5% |

---

## 2. What reference_zone data is already available

The current pipeline already computes reference_zone extent in `region_bus`:

| Data | Source | Current issue |
|------|--------|---------------|
| `reference_zone.block_ids` | `infer_zones()` | Trimmed list — blocks that belong to reference zone. Already excludes post-ref backmatter blocks. |
| `reference_zone.boundary_band.start_page` | `infer_zones()` | First reference heading/item page. Reliable. |
| `reference_zone.boundary_band.end_page` | `infer_zones()` | Uses raw `reference_item_blocks` max page — **NOT trimmed** if post-ref backmatter exists. Overstates. |
| `region_bus` status (ACCEPT/HOLD) | `infer_zones()` | Whether reference zone is verified |
| `ReferenceZone` per-page, per-column | `_detect_reference_zones()` | Column-scoped vertical bands. Stored in `doc.reference_zones` AFTER `infer_zones()`. |
| `ref_heading_pages` dict | `_apply_content_zone_fallback()` | y_top of reference heading per page — used for same-page vertical split |

**Key insight:** `region_bus.reference_zone` is computed by `infer_zones()`, which
runs INSIDE `normalize_document_structure()`. But `_reconcile_tail_spread()` runs
BEFORE `infer_zones()` — so tail spread operates without the reference anchor,
then `infer_zones()` re-derives reference zone independently but its output is
never used to correct the tail boundary.

---

## 3. Algorithm

### 3.1 Overall flow

The new partition replaces the **later** `_reconcile_tail_spread()` call point,
AFTER role resolution and page_layouts recomputation. Current approximate position
in `normalize_document_structure()`:

```python
    # ... early: first infer_zones(), role resolution, page_layouts recomputation ...

    # --- REPLACE THIS POINT ---
    # OLD:
    #   tail_spread = _reconcile_tail_spread(blocks, page_layouts)
    #   _normalize_backmatter_roles_after_boundary(tail_spread, backmatter_form, blocks)

    # NEW:
    region_bus = infer_zones(blocks, ..., tail_spread=None)   # refresh region_bus
    ref_zones = _detect_reference_zones(blocks, page_layouts)

    if _has_verified_reference_zone(region_bus):
        partition = _partition_by_reference_zone(blocks, region_bus, ref_zones=ref_zones)
        _normalize_pre_ref_disclosure_runs(partition, region_bus)
        tail_spread = _build_tail_boundary_from_ref_partition(partition, region_bus)
        ref_partition_active = True
    else:
        tail_spread = _reconcile_tail_spread(blocks, page_layouts)
        _normalize_backmatter_roles_after_boundary(tail_spread, backmatter_form, blocks)
        ref_partition_active = False

    # --- existing: zone labels (unchanged) ---
    _apply_zone_labels(blocks, region_bus)     # includes _apply_content_zone_fallback internally
    _sanitize_reference_zone_boundary(blocks)  # signature: only blocks

    # --- CONDITIONAL (Contract C) ---
    if not ref_partition_active:
        blocks = _promote_tail_body_candidates(blocks, doc_structure, ...)
        blocks = _assign_tail_spread_ownership(blocks, doc_structure)
    # else: SKIP — old promotion would re-classify body_paragraph as tail_candidate_body
    # using spread_start/spread_end heuristics. The ref-anchored partition
    # has already assigned correct roles.
```

### 3.2 Phase A — Determine reference_zone extent

```python
def _resolve_reference_zone_extent(
    blocks: list[dict],
    region_bus: dict[str, dict],
) -> tuple[int | None, int | None]:
    """Return (ref_start_page, ref_end_page) from region_bus data.

    Uses block_ids (which are already trimmed for post-ref backmatter).
    NEVER uses untrimmed boundary_band.end_page for the end.
    """
    ref_zone = region_bus.get("reference_zone", {}) or {}
    block_ids: list[str] = ref_zone.get("block_ids") or []
    band = ref_zone.get("boundary_band") or {}
    ref_start = band.get("start_page")

    if not block_ids or ref_start is None:
        return None, None

    # Use effective_end_page stored during infer_zones (see §3.2a).
    # Do NOT fallback to band.get("end_page") — that is the untrimmed raw max.
    effective_end = ref_zone.get("effective_end_page")
    if effective_end is None:
        effective_end = _derive_effective_end_from_block_ids(blocks, block_ids)

    return ref_start, effective_end


def _derive_effective_end_from_block_ids(
    blocks: list[dict], block_ids: list[str]
) -> int | None:
    """Scan blocks for max page among reference_zone.block_ids.

    block_ids may be bare block_id strings or `p{page}:{block_id}` artifact keys.
    """
    id_set = set(block_ids)
    max_page = None
    for b in blocks:
        bid = str(b.get("block_id") or "")
        key = _zone_block_key(b)
        if bid in id_set or key in id_set:
            p = int(b.get("page", 0) or 0)
            if p > 0:
                max_page = max(max_page, p) if max_page is not None else p
    return max_page
```

**§3.2a — Store effective_end_page in infer_zones()**

In `infer_zones()`, compute `effective_reference_end_page` from the **trimmed**
`reference_blocks` list (NOT the raw `reference_item_blocks`). Store it inside
`_make_zone()` for the `reference_zone` entry:

```python
# Current: reference_end_page = max(page of ALL reference_item_blocks)  ← overstates
# Replace with:
if post_ref_backmatter_start is not None:
    trimmed_pages = [
        int(b.get("page", 0) or 0) for b in reference_blocks
        if int(b.get("page", 0) or 0) > 0
    ]
    effective_reference_end_page = max(trimmed_pages) if trimmed_pages else first_reference_page
else:
    effective_reference_end_page = reference_end_page  # same as current

# Then in _make_zone(): pass effective_end_page alongside boundary_band
"reference_zone": _make_zone(
    status,
    block_ids,
    composite_block_ids=reference_composite_ids,
    anchor_family=...,
    boundary_band=_page_band(first_reference_page, reference_end_page),
    effective_end_page=effective_reference_end_page,     # NEW
),
```

### 3.3 Phase B — Partition blocks by reference_zone

```python
def _partition_by_reference_zone(
    blocks: list[dict],
    region_bus: dict[str, dict],
    ref_zones: list[ReferenceZone] | None = None,
) -> dict[str, list[dict]]:
    """Partition all blocks into pre-ref / reference / post-ref zones.

    reference_zone is the ONLY boundary. Pre-ref backmatter headings
    do not participate in partition (they are normalized later in §3.4).

    Returns:
        "pre_ref": blocks strictly before reference_zone start
        "reference": blocks within reference_zone extent
        "post_ref": blocks strictly after reference_zone end
    """
    ref_start, ref_end = _resolve_reference_zone_extent(blocks, region_bus)
    if ref_start is None:
        return _fallback_tail_spread_partition(blocks, region_bus)  # old path

    pre_ref, reference, post_ref = [], [], []

    for block in blocks:
        page = int(block.get("page", 0) or 0)
        role = str(block.get("role") or "")

        if page < ref_start:
            pre_ref.append(block)
        elif page > ref_end:
            post_ref.append(block)
        else:
            # page is within [ref_start, ref_end] — same-page split needed
            zone = _classify_same_page_block(block, region_bus, page, ref_zones=ref_zones)
            if zone == "pre_ref":
                pre_ref.append(block)
            elif zone == "reference":
                reference.append(block)
            else:
                post_ref.append(block)

    return {"pre_ref": pre_ref, "reference": reference, "post_ref": post_ref}
```

### 3.4 Phase C — Normalize pre-ref disclosure runs (LOCAL ONLY)

Contract A+B: this function must NEVER change global boundaries.

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

# NOT in the list: "funding", "supplementary", "appendix" — too generic,
# risk of false positive on unnumbered body headings.

_STRONG_BODY_HEADINGS: frozenset[str] = frozenset({
    "discussion", "conclusion", "conclusions", "results", "summary",
    "limitations", "future perspectives", "materials and methods",
    "methods", "introduction",
})


_HEADING_ROLES = frozenset({
    "section_heading", "subsection_heading", "sub_subsection_heading",
    "backmatter_heading", "backmatter_boundary_heading", "backmatter_heading_candidate",
})

_MARKER_HEADING_TYPES = frozenset({
    "heading_numbered", "heading_arabic", "heading_decimal",
})


def _normalize_pre_ref_disclosure_runs(
    blocks: list[dict],
    partition: dict[str, list[dict]],
    ref_start_page: int | None,
    total_pages: int,
    page_layouts: dict[int, PageLayoutProfile] | None = None,
    page_width: int = 0,
) -> None:
    """Local role normalization for known disclosure sections before ref.

    Hard rules:
    1. Only modifies roles in the pre_ref partition.
    2. Does not change ref_start_page, body_end_page, spread_start, or any boundary field.
    3. Each disclosure heading only owns blocks from itself to the next heading
       (any heading, including another disclosure heading).
    4. Does not cross a STRONG_BODY_HEADING.
    5. Does not cross reference_zone.start.
    6. Does NOT cross a column boundary.
    7. Does not affect numbered body section headings.
    """
    pre_ref_blocks = partition.get("pre_ref", [])
    if ref_start_page is None:
        return

    for i, block in enumerate(pre_ref_blocks):
        text = str(block.get("text", "") or "").strip().lower()
        text_norm = re.sub(r"\s+", " ", text)

        # Check exact match against known disclosure headings
        matched_key = None
        for key, aliases in _KNOWN_PRE_REFERENCE_DISCLOSURE_HEADINGS.items():
            if text_norm == key or text_norm in aliases:
                matched_key = key
                break
        if matched_key is None:
            continue

        # Gate: heading must be heading-like
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
            # Not heading-like — could be a body paragraph matching disclosure text.
            # Only promote if bold + short.
            span = block.get("span_signature") or {}
            if not span.get("bold") and not span.get("font_size", 0) > 10:
                continue
            if len(text.split()) > 20:
                continue

        # Gate: proximity to ref_start (not total_pages ratio)
        block_page = int(block.get("page", 0) or 0)
        if ref_start_page is not None:
            max_before_ref = max(2, int(total_pages * 0.25))
            if block_page > ref_start_page or block_page < max(1, ref_start_page - max_before_ref):
                continue

        # Determine block's column once (for same-column guard below)
        block_col = _get_column_index(block, page_width) if page_width > 0 else None

        # Normalize the local run: same column only, to next heading or ref_start
        block["role"] = "backmatter_heading"
        heading_like_count = 1  # track subsequent headings in the run
        for j in range(i + 1, len(pre_ref_blocks)):
            next_block = pre_ref_blocks[j]
            next_page = int(next_block.get("page", 0) or 0)
            if next_page > ref_start_page:
                break

            # Column guard: do not cross column boundary
            if block_col is not None and page_width > 0:
                next_col = _get_column_index(next_block, page_width)
                if next_col is not None and next_col != block_col:
                    break

            next_text = str(next_block.get("text", "") or "").strip().lower()
            next_role = str(next_block.get("role") or "")
            next_raw_label = str(next_block.get("raw_label") or "")
            next_marker_type = str((next_block.get("marker_signature") or {}).get("type") or "")
            next_heading_like = (
                next_role in _HEADING_ROLES
                or next_raw_label == "paragraph_title"
                or next_marker_type in _MARKER_HEADING_TYPES
            )

            if next_heading_like:
                # Another disclosure heading in sequence (e.g. CRediT → Ethics)
                if _is_known_disclosure(next_text):
                    continue  # will be handled by its own loop iteration
                else:
                    break  # non-disclosure heading → stop run

            # Stop at strong body section start
            if any(next_text.startswith(h) for h in _STRONG_BODY_HEADINGS):
                break
            # Stop at numbered heading
            if re.match(r"^\d+(?:\.\d+)*\.?\s", next_text):
                break

            # Normalize this block
            if next_role.endswith("_heading"):
                next_block["role"] = "backmatter_heading"
            elif next_role == "body_paragraph":
                next_block["role"] = "backmatter_body"
            elif next_role == "frontmatter_noise":
                next_block["role"] = "backmatter_body"


def _is_known_disclosure(text: str) -> bool:
    text_norm = re.sub(r"\s+", " ", text).strip().lower()
    for key, aliases in _KNOWN_PRE_REFERENCE_DISCLOSURE_HEADINGS.items():
        if text_norm == key or text_norm in aliases:
            return True
    return False
```

### 3.5 Phase D — Same-page body+ref column-aware split

```python
def _classify_same_page_block(
    block: dict,
    region_bus: dict,
    page: int,
    ref_zones: list[ReferenceZone] | None = None,
    page_layouts: dict[int, PageLayoutProfile] | None = None,
) -> str:
    """Classify a block on a shared body/ref page.

    A block is "reference" only if it explicitly belongs to the reference zone.
    Same column as a reference heading is NOT sufficient.

    Priority:
    1. Block key in reference_zone.block_ids/composite_block_ids → "reference"
    2. role/seed_role is reference_heading/reference_item → "reference"
    3. Column-aware: below reference heading in ref column WITH reference evidence
    4. Vertical split by y (fallback)
    5. "pre_ref" (conservative — keeps body in body)
    """
    role = str(block.get("role") or "")
    seed_role = str(block.get("seed_role") or "")
    if role in {"reference_heading", "reference_item"}:
        return "reference"
    if seed_role in {"reference_heading", "reference_item"}:
        return "reference"

    # Check if block is explicitly in reference_zone block_ids
    ref_zone = region_bus.get("reference_zone", {}) or {}
    ref_block_ids = set(ref_zone.get("block_ids") or [])
    ref_composite_ids = set(ref_zone.get("composite_block_ids") or [])
    block_key = str(block.get("block_id") or "")
    if block_key in ref_block_ids or block_key in ref_composite_ids:
        return "reference"
    art_key = _zone_block_key(block)
    if art_key in ref_block_ids or art_key in ref_composite_ids:
        return "reference"

    # Column-aware split: below ref heading in a ref column
    if ref_zones and page_layouts:
        block_x = _block_x_center(block)
        page_zones = [rz for rz in ref_zones if rz.page == page]
        layout = page_layouts.get(page)
        if layout:
            col_boundaries = layout.column_boundaries
        for rz in page_zones:
            col_x_range = _column_x_range(rz.column_index, col_boundaries, page_width)
            if col_x_range and col_x_range[0] <= block_x <= col_x_range[1]:
                # Same reference column — check y and evidence
                if _block_y_top(block) >= rz.y_start:
                    # Below ref heading in ref column — check for reference evidence
                    marker = (block.get("marker_signature") or {}).get("type")
                    if marker in {"reference_bracket", "reference_sup", "reference_numeric"}:
                        return "reference"
                    return "post_ref"  # in ref column but not a ref → post-ref backmatter
                return "pre_ref"  # above ref heading in same column → body flow
        return "pre_ref"  # in a different column → body flow

    # Fallback: vertical split using ref_heading_pages
    ref_heading_pages = _compute_ref_heading_pages(region_bus)
    if page in ref_heading_pages:
        ref_top = ref_heading_pages[page]
        if _block_y_bottom(block) <= ref_top:
            return "pre_ref"
        return "reference"

    return "pre_ref"
```

### 3.6 Phase E — Build tail boundary from partition (Contract D)

```python
def _build_tail_boundary_from_ref_partition(
    partition: dict[str, list[dict]],
    region_bus: dict[str, dict],
) -> TailBoundary:
    """Derive TailBoundary from the ref-anchored partition.

    body_end_page = max page of pre_ref blocks that are body_flow.
    spread_start = references_start (NOT body_end_page — body_end is body metadata,
    not tail-spread start).
    """
    pre_ref = partition.get("pre_ref", [])
    reference = partition.get("reference", [])
    post_ref = partition.get("post_ref", [])

    # body_end_page: max page of body-like blocks in pre_ref
    body_like_pages = [
        int(b.get("page", 0) or 0) for b in pre_ref
        if b.get("role") in {"body_paragraph", "section_heading",
                             "subsection_heading", "sub_subsection_heading"}
    ]
    body_end_page = max(body_like_pages) if body_like_pages else None

    # ref_start_page from region_bus
    ref_zone = region_bus.get("reference_zone", {}) or {}
    band = ref_zone.get("boundary_band") or {}
    ref_start_page = band.get("start_page")

    ref_pages = [int(b.get("page", 0) or 0) for b in reference if b.get("page")]
    references_start = min(ref_pages) if ref_pages else ref_start_page
    references_end = max(ref_pages) if ref_pages else references_start

    post_ref_pages = [int(b.get("page", 0) or 0) for b in post_ref if b.get("page")]

    # spread_start = references_start (NOT body_end_page)
    # spread_end = max of reference + post-ref pages
    all_tail_pages = ref_pages + post_ref_pages
    spread_start = min(all_tail_pages) if all_tail_pages else references_start
    spread_end = max(all_tail_pages) if all_tail_pages else references_start

    return TailBoundary(
        body_end_page=body_end_page,
        backmatter_start=references_start,
        references_start=references_start,
        spread_start=spread_start,
        spread_end=spread_end,
        is_clean_separated=True,
        reason="ref_zone_partition",
    )
```

---

## 4. Call site and affected code

### 4.1 normalize_document_structure() changes

```python
def normalize_document_structure(blocks, ...):
    # ... existing preamble (role assignment, family partition, etc.) ...

    # --- existing ---
    page_layouts = _build_page_layout_profiles(blocks)

    # --- existing: region bus (infer_zones) ---
    region_bus = infer_zones(blocks, ..., tail_spread=tail_spread, ...)

    # --- NEW: detect per-column reference zones (for column-aware same-page split) ---
    ref_zones = _detect_reference_zones(blocks, page_layouts)

    # --- NEW: ref-anchored partition (replaces tail_spread when ref zone verified) ---
    ref_partition_active = False
    if _has_verified_reference_zone(region_bus):
        partition = _partition_by_reference_zone(blocks, region_bus, ref_zones=ref_zones)
        _normalize_reference_roles_from_partition(partition)
        _normalize_pre_ref_disclosure_runs(partition, region_bus, ref_start_page, total_pages)
        tail_spread = _build_tail_boundary_from_ref_partition(partition, region_bus)
        ref_partition_active = True
    else:
        # --- existing fallback ---
        tail_spread = _reconcile_tail_spread(blocks, page_layouts)
        _normalize_backmatter_roles_after_boundary(tail_spread, backmatter_form, blocks)
        ref_partition_active = False

    # --- existing: zone labels (unchanged) ---
    _apply_zone_labels(blocks, region_bus)  # includes _apply_content_zone_fallback internally
    _sanitize_reference_zone_boundary(blocks)  # signature: blocks only

    # --- CONDITIONAL: skip old promotion in ref-partitioned path (Contract C) ---
    if not ref_partition_active:
        blocks = _promote_tail_body_candidates(blocks, doc_structure, ...)
        blocks = _assign_tail_spread_ownership(blocks, doc_structure)

    # ... rest of normalize_document_structure ...
```

### 4.2 infer_zones() additions

Store `effective_end_page` after trimming (lines 1067–1081):
```python
if post_ref_backmatter_start is not None:
    trimmed_pages = [int(b.get("page", 0) or 0) for b in reference_blocks]
    effective_end_page = max(trimmed_pages) if trimmed_pages else None
else:
    effective_end_page = reference_end_page
ref_zone["effective_end_page"] = effective_end_page
```

### 4.3 Affected files

| File | Change | Scope |
|------|--------|-------|
| `ocr_document.py` | New `_partition_by_reference_zone()` + helpers | ~80 lines |
| `ocr_document.py` | New `_normalize_pre_ref_disclosure_runs()` | ~70 lines |
| `ocr_document.py` | New `_classify_same_page_block()` | ~40 lines |
| `ocr_document.py` | New `_build_tail_boundary_from_ref_partition()` | ~40 lines |
| `ocr_document.py` | New `_has_verified_reference_zone()` | ~10 lines |
| `ocr_document.py` | Modify `infer_zones()` to store `effective_end_page` | ~5 lines |
| `ocr_document.py` | Modify `normalize_document_structure()` | ~30 lines |
| `ocr_document.py` | `_detect_reference_zones()` — move before partition call | import only |
| `ocr_document.py` | `_normalize_backmatter_roles_after_boundary()` — unchanged, kept as fallback | 0 |
| `ocr_document.py` | `_promote_tail_body_candidates()` — SKIPPED in ref-partitioned path | 0 |

---

## 5. Test strategy

### 5.1 Test papers

| Paper | Pages | Layout | Issue | Expected after fix |
|-------|-------|--------|-------|-------------------|
| 25K5KZAQ | 11 | two-col | CRediT/Ethics/Declaration → body_paragraph | CRediT → backmatter_heading, text → backmatter_body. Discussion/Conclusion unchanged. |
| NC66N4Q3 | 56 | two-col | body_end_page=None, ref_start=None | ref items → reference_zone, Discussion → body_flow, no degraded mode |
| 9TW98JH8 | 5 | mixed-tail | 20/20 correct | No change (regression) |
| Standard paper | any | single-col | Clean body/ref separation | No change |

### 5.2 Unit tests

| Test | Verifies |
|------|----------|
| `test_ref_zone_partition_simple` | Single-col body p1-8, ref p9-10, post-ref p11 → correct 3-way split |
| `test_ref_zone_partition_credit` | 25K5KZAQ: CRediT before ref → backmatter_heading, body → backmatter_body; Discussion after CRediT → unchanged |
| `test_pre_ref_disclosure_does_not_change_ref_start` | CRediT heading found → ref_start_page unchanged (Contract A) |
| `test_pre_ref_disclosure_does_not_span_strong_body_heading` | "CRediT ... Conclusion ... References" → Conclusion NOT consumed (Contract B) |
| `test_pre_ref_disclosure_does_not_span_numbered_heading` | "CRediT ... 5. Conclusion ... References" → 5. Conclusion NOT consumed |
| `test_pre_ref_disclosure_stops_at_ref_start` | Blocks after candidate, before ref_start, past another heading → NOT consumed |
| `test_ref_zone_partition_same_page_body_ref` | NC66N4Q3: column-aware split, left-col body stays body_flow |
| `test_ref_zone_partition_no_ref` | No reference_zone → fallback to old algorithm, no crash |
| `test_known_disclosure_exact_match` | Exact match triggers, substring "funding" in body heading doesn't |
| `test_disclosure_proximity_gate` | Candidate at page 2 of 15, ref at page 12 → NOT triggered (too far from ref) |
| `test_body_end_page_from_actual_blocks` | Same-page body+ref → body_end_page == ref_start_page, not ref_start - 1 |
| `test_tail_boundary_derived_from_partition` | body_end_page = max pre-ref body_flow page |
| `test_promote_tail_body_skipped_on_ref_path` | ref_partition_active=True → _promote_tail_body_candidates not called |
| `test_reference_end_page_trimming` | Post-ref backmatter on page 12 doesn't extend reference_zone |
| `test_infer_zones_stores_effective_end_page` | After trim, effective_end_page < raw end_page |

### 5.3 Regression tests

All existing tests pass unchanged:
- `test_ocr_layout_zones.py` — single-col, two-col, column-major ordering, region_bus output
- `test_pipeline_keeps_reference_zone_and_legend_family_out_of_default_body`
- `test_reference_zone_adapter_accepts_without_tail_end_boundary`
- Full suite: `python -m pytest tests/unit/ tests/cli/ -v --tb=short`

---

## 6. Risks and unknowns

### 6.1 `_detect_reference_zones()` availability

Currently `_detect_reference_zones()` is called inside `infer_zones()` (for `references_start` detection) but the result (`ReferenceZone` list) is stored in `DocumentStructure.reference_zones` AFTER `infer_zones()` returns. The partition runs inside `normalize_document_structure()`, which has access to `doc_structure` mid-construction. Verify that `doc_structure.reference_zones` is populated before the partition call.

**Mitigation:** Move the `_detect_reference_zones()` call to just before the partition, not relying on `infer_zones()` to have stored it.

### 6.2 Verified reference_zone ≠ perfect reference_zone

`_has_verified_reference_zone()` must check for actual block_ids, not just ACCEPT status. A zone can be ACCEPT with zero block_ids (if the anchor family is accepted but no items are in range). In that case, fall back to old tail_spread logic.

```python
def _has_verified_reference_zone(region_bus):
    ref_zone = region_bus.get("reference_zone", {}) or {}
    if ref_zone.get("status") in ("ACCEPT", "HOLD"):
        block_ids = ref_zone.get("block_ids") or []
        if block_ids:
            return True
    return False
```

### 6.3 Downstream zone assignment

`_apply_zone_labels()` and `_apply_content_zone_fallback()` run AFTER the partition and role normalization. Since zone labels depend on roles, and roles have been updated by the partition, zones should be assigned correctly on first pass. No stale behavior expected — but verify on 25K5KZAQ that CRediT blocks get `tail_nonref_hold_zone` or `body_zone` consistently with their new `backmatter_body` role.

### 6.4 Renderer compatibility

`_reorder_tail_run()` in `ocr_render.py` reads `tail_spread` from document structure. Since the new `_build_tail_boundary_from_ref_partition()` produces a compatible `TailBoundary`, the renderer should work unchanged. Verify with 25K5KZAQ that CRediT text renders as backmatter, not between Discussion paragraphs.

### 6.5 Body spine contamination

`_build_page_layout_profiles()` excludes pages with >50% media from body spine sampling. This is unchanged. The new path does not modify body spine selection.

### 6.6 Papers with post-ref backmatter only (no pre-ref)

Papers where all backmatter (Acknowledgements, Funding, etc.) appears after the reference section are handled by the existing `post_reference_backmatter_zone` in `infer_zones()`. No change needed for these — they are not affected by the new partition.

---

## 7. Implementation order

```
Step 1: Modify infer_zones() — store effective_end_page in reference_zone entry
Step 2: Add _has_verified_reference_zone() helper
Step 3: Add _KNOWN_PRE_REFERENCE_DISCLOSURE_HEADINGS and _STRONG_BODY_HEADINGS constants
Step 4: Add _resolve_reference_zone_extent()
Step 5: Add _classify_same_page_block() using ref_zones column data
Step 6: Add _normalize_pre_ref_disclosure_runs() with local-only scope
Step 7: Add _partition_by_reference_zone()
Step 8: Add _build_tail_boundary_from_ref_partition()
Step 9: Wire into normalize_document_structure() with ref_partition_active gate
Step 10: Ensure _promote_tail_body_candidates is skipped in ref-partitioned path
Step 11: Tests — 15 unit tests + 25K5KZAQ/NC66N4Q3/9TW98JH8 regression
```

**Estimated scope:** ~280 lines new code, all in `ocr_document.py`
**Dependencies:** None on P0/P1
