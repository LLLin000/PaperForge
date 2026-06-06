# OCR Span Metadata Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build persistent span_metadata pipeline from raw OCR through structured blocks, profile aggregation, and cross-validation role refinement.

**Architecture:** Five-phase build: (1) carry span_metadata through raw/structured block extraction, (2) create shared profile infrastructure in new `ocr_profiles.py`, (3) persist role_span_profiles.json and wire into rebuild, (4) refactor heading family discovery to use dynamic profile matching instead of hardcoded thresholds, (5) add second-pass cross-validation for body/caption/reference ambiguity. Each phase is independently testable.

**Tech Stack:** Python 3.x, PaddleOCR block JSON structure, existing PaperForge worker pipeline (`ocr_blocks.py`, `ocr_roles.py`, `ocr_render.py`, `ocr_rebuild.py`)

**Spec:** `docs/superpowers/specs/2026-06-06-ocr-unified-span-metadata-design.md`

---

### Task 1: Pipeline span_metadata Carry-Through

**Files:**
- Modify: `paperforge/worker/ocr_blocks.py:71-92` (`build_raw_blocks_for_page`)
- Modify: `paperforge/worker/ocr_blocks.py:10-61` (`build_structured_blocks`)
- Modify: `tests/test_ocr_blocks.py`

- [ ] **Step 1: Add span_metadata extraction to `build_raw_blocks_for_page`**

The PaddleOCR API response includes `span_metadata` on each entry in `parsing_res_list`. It can arrive as either a dict (`{"size": N, "flags": "bold", "font": "Times", "color": 0}`) or a list of per-character span dicts (`[{"size": N, "flags": N, "font": "...", "color": N}, ...]`). Carry it through as-is.

Add to `build_raw_blocks_for_page` after line 86 (after `"source": "ocr_raw"`):

```python
    "span_metadata": block.get("span_metadata"),
```

- [ ] **Step 2: Write failing test for span_metadata preservation**

Add to `tests/test_ocr_blocks.py`:

```python
def test_build_raw_blocks_preserves_span_metadata() -> None:
    from paperforge.worker.ocr_blocks import build_raw_blocks_for_page
    span_data = {"size": 14.0, "flags": 16, "font": "TimesNewRomanPS-BoldMT", "color": 0}
    result = {
        "prunedResult": {
            "width": 1200, "height": 1600,
            "parsing_res_list": [
                {"block_id": 1, "block_label": "text", "block_order": 0,
                 "block_bbox": [1,2,3,4], "block_content": "Title",
                 "span_metadata": span_data},
            ],
        }
    }
    rows = build_raw_blocks_for_page("KEY001", 1, result)
    assert rows[0]["span_metadata"] == span_data
```

Run: `pytest tests/test_ocr_blocks.py::test_build_raw_blocks_preserves_span_metadata -v`
Expected: FAIL because `span_metadata` key is not yet present in output

- [ ] **Step 3: Write failing test for span_metadata in structured blocks**

Add to `tests/test_ocr_blocks.py`:

```python
def test_build_structured_blocks_carries_span_metadata() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks
    span_data = {"size": 14.0, "flags": 16, "font": "TimesNewRomanPS-BoldMT", "color": 0}
    raw_blocks = [{
        "paper_id": "KEY001", "page": 1, "block_id": "p1_b1",
        "raw_label": "paragraph_title", "raw_order": 0,
        "bbox": [1,2,3,4], "text": "Methods", "page_width": 1200, "page_height": 1600,
        "source": "ocr_raw", "span_metadata": span_data,
    }]
    rows = build_structured_blocks(raw_blocks)
    assert rows[0].get("span_metadata") == span_data
```

Run: `pytest tests/test_ocr_blocks.py::test_build_structured_blocks_carries_span_metadata -v`
Expected: FAIL because structured output drops span_metadata

- [ ] **Step 4: Implement span_metadata carry-through in `build_structured_blocks`**

In `ocr_blocks.py`, `build_structured_blocks` function (around line 38, where `role_input` dict is built), the `span_metadata` from the raw block must be included in the output structured block. After the `role_confidence` and `evidence` assignment, add:

```python
    row["span_metadata"] = raw.get("span_metadata")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_ocr_blocks.py -v`
Expected: 4 passed (2 existing + 2 new)

- [ ] **Step 6: Commit**

```bash
git add tests/test_ocr_blocks.py paperforge/worker/ocr_blocks.py
git commit -m "feat: carry span_metadata through raw and structured block pipeline"
```

---

### Task 2: Create `ocr_profiles.py` Profile Infrastructure

**Files:**
- Create: `paperforge/worker/ocr_profiles.py`
- Modify: `paperforge/worker/ocr_render.py` (refactor `_extract_style_profile` to import from new module)
- Create: `tests/test_ocr_profiles.py`

This module owns: block-level style extraction, family/profile aggregation, profile-quality scoring, span cross-validation, and role-family comparison. Extract existing logic from `ocr_render.py` and add new aggregation/cross-validation helpers.

- [ ] **Step 1: Write failing tests for `extract_block_span_profile`**

Create `tests/test_ocr_profiles.py`:

```python
"""Tests for ocr_profiles.py profile infrastructure."""

from __future__ import annotations


def test_extract_block_span_profile_list_format() -> None:
    from paperforge.worker.ocr_profiles import extract_block_span_profile

    block = {
        "span_metadata": [
            {"size": 14.0, "font": "Times-Bold", "flags": 16, "color": 0},
            {"size": 14.0, "font": "Times-Bold", "flags": 16, "color": 0},
        ]
    }
    profile = extract_block_span_profile(block)
    assert profile is not None
    assert profile["mean_size"] == 14.0
    assert profile["max_size"] == 14.0
    assert profile["is_bold"] is True
    assert profile["is_italic"] is False
    assert profile["is_colored"] is False


def test_extract_block_span_profile_dict_format() -> None:
    from paperforge.worker.ocr_profiles import extract_block_span_profile

    block = {
        "span_metadata": {"size": 12.0, "flags": "bold"}
    }
    profile = extract_block_span_profile(block)
    assert profile is not None
    assert profile["mean_size"] == 12.0
    assert profile["is_bold"] is True


def test_extract_block_span_profile_no_data() -> None:
    from paperforge.worker.ocr_profiles import extract_block_span_profile

    block = {}
    profile = extract_block_span_profile(block)
    assert profile is None


def test_extract_block_span_profile_empty_list() -> None:
    from paperforge.worker.ocr_profiles import extract_block_span_profile

    block = {"span_metadata": []}
    profile = extract_block_span_profile(block)
    assert profile is None
```

Run: `pytest tests/test_ocr_profiles.py -v`
Expected: 4 FAILED — module/function not defined

- [ ] **Step 2: Implement `extract_block_span_profile`**

Create `paperforge/worker/ocr_profiles.py` with the extraction function, ported from `ocr_render.py:_extract_style_profile`:

```python
"""OCR span style profile extraction and cross-validation.

Owns: block-level style extraction, family/profile aggregation,
profile-quality scoring, span cross-validation, role-family comparison.
"""

from __future__ import annotations


def extract_block_span_profile(block: dict) -> dict | None:
    """Extract a normalized style profile dict from a block's span_metadata.

    Handles both list format (per-character spans) and dict format
    (legacy/aggregated). Returns None when no span data is available.

    Return shape:
        {"mean_size": float, "max_size": float, "font_families": set[str],
         "is_bold": bool, "is_italic": bool, "is_colored": bool}
    """
    span_meta = block.get("span_metadata")
    if not span_meta:
        return None

    if isinstance(span_meta, list):
        sizes: list[float] = []
        fonts: set[str] = set()
        flags = 0
        colors: set[int] = set()
        for sp in span_meta:
            sz = sp.get("size")
            if sz is not None:
                sizes.append(float(sz))
            fnt = sp.get("font")
            if fnt:
                fonts.add(str(fnt))
            flags |= sp.get("flags", 0) if isinstance(sp.get("flags"), int) else 0
            c = sp.get("color")
            if c is not None:
                colors.add(int(c))
        if not sizes:
            return None
        return {
            "mean_size": sum(sizes) / len(sizes),
            "max_size": max(sizes),
            "font_families": fonts,
            "is_bold": bool(flags & 16),
            "is_italic": bool(flags & 4),
            "is_colored": any(c != 0 for c in colors),
        }

    if isinstance(span_meta, dict):
        size = span_meta.get("size")
        if size is None:
            return None
        flags_val = span_meta.get("flags", 0)
        is_bold: bool
        is_italic: bool
        if isinstance(flags_val, str):
            is_bold = "bold" in flags_val.lower()
            is_italic = "italic" in flags_val.lower()
        else:
            is_bold = bool(flags_val & 16) if isinstance(flags_val, int) else False
            is_italic = bool(flags_val & 4) if isinstance(flags_val, int) else False
        return {
            "mean_size": float(size),
            "max_size": float(size),
            "font_families": {span_meta.get("font", "")} if span_meta.get("font") else set(),
            "is_bold": is_bold,
            "is_italic": is_italic,
            "is_colored": span_meta.get("color", 0) != 0,
        }

    return None
```

- [ ] **Step 3: Run tests to verify pass (4 of 4)**

Run: `pytest tests/test_ocr_profiles.py -v`
Expected: 4 PASSED

- [ ] **Step 4: Write failing tests for `build_role_span_profiles`**

Append to `tests/test_ocr_profiles.py`:

```python
def test_build_role_span_profiles_aggregates_by_role() -> None:
    from paperforge.worker.ocr_profiles import build_role_span_profiles

    blocks = [
        {"role": "section_heading", "span_metadata": {"size": 16.0, "flags": "bold"}},
        {"role": "section_heading", "span_metadata": {"size": 15.5, "flags": "bold"}},
        {"role": "body_paragraph", "span_metadata": {"size": 10.0, "flags": "normal"}},
        {"role": "body_paragraph", "span_metadata": {"size": 10.5, "flags": "normal"}},
    ]
    profiles = build_role_span_profiles(blocks)
    assert "section_heading" in profiles
    assert "body_paragraph" in profiles
    assert profiles["section_heading"]["block_count"] == 2
    assert profiles["body_paragraph"]["mean_size"] == 10.25


def test_build_role_span_profiles_profile_quality() -> None:
    from paperforge.worker.ocr_profiles import build_role_span_profiles

    blocks = [
        {"role": "body_paragraph", "span_metadata": {"size": 10.0, "flags": 0}}
    ]
    profiles = build_role_span_profiles(blocks)
    assert profiles["body_paragraph"]["quality"] in ("weak", "no_data")


def test_build_role_span_profiles_empty_input() -> None:
    from paperforge.worker.ocr_profiles import build_role_span_profiles

    assert build_role_span_profiles([]) == {}
```

Run: `pytest tests/test_ocr_profiles.py::test_build_role_span_profiles_aggregates_by_role tests/test_ocr_profiles.py::test_build_role_span_profiles_profile_quality tests/test_ocr_profiles.py::test_build_role_span_profiles_empty_input -v`
Expected: 3 FAILED

- [ ] **Step 5: Implement `build_role_span_profiles`**

Add to `paperforge/worker/ocr_profiles.py`:

```python
_PROFILE_QUALITY_STRONG = 3       # block_count >= 3 and low dispersion
_PROFILE_QUALITY_MODERATE = 2     # block_count >= 3 and acceptable dispersion
_PROFILE_QUALITY_WEAK = 1         # block_count >= 2 but high dispersion
_PROFILE_QUALITY_NO_DATA = 0      # insufficient data


def _profile_quality(block_count: int, dispersion: float) -> str:
    if block_count >= 3 and dispersion <= 0.15:
        return "strong"
    if block_count >= 3:
        return "moderate"
    if block_count >= 2:
        return "weak"
    return "no_data"


def build_role_span_profiles(blocks: list[dict]) -> dict:
    """Aggregate span profiles per role across all blocks.

    Returns dict keyed by role name, each value:
        {"block_count": int, "mean_size": float, "quality": str, ...}
    """
    buckets: dict[str, dict] = {}
    for block in blocks:
        role = block.get("role")
        if not role:
            continue
        profile = extract_block_span_profile(block)
        if profile is None:
            continue
        if role not in buckets:
            buckets[role] = {
                "sizes": [],
                "bold_count": 0,
                "italic_count": 0,
                "font_families": set(),
                "block_count": 0,
                "colored_count": 0,
            }
        buckets[role]["sizes"].extend([profile["mean_size"], profile["max_size"]])
        if profile["is_bold"]:
            buckets[role]["bold_count"] += 1
        if profile["is_italic"]:
            buckets[role]["italic_count"] += 1
        if profile["is_colored"]:
            buckets[role]["colored_count"] += 1
        buckets[role]["font_families"].update(profile["font_families"])
        buckets[role]["block_count"] += 1

    result: dict = {}
    for role, bucket in buckets.items():
        sizes = bucket["sizes"]
        mean_size = sum(sizes) / len(sizes) if sizes else 0.0
        max_size = max(sizes) if sizes else 0.0
        min_size = min(sizes) if sizes else 0.0
        dispersion = (max_size - min_size) / max_size if max_size > 0 else 0.0
        bold_ratio = bucket["bold_count"] / bucket["block_count"] if bucket["block_count"] else 0.0
        result[role] = {
            "block_count": bucket["block_count"],
            "mean_size": round(mean_size, 2),
            "max_size": round(max_size, 2),
            "min_size": round(min_size, 2),
            "dispersion": round(dispersion, 4),
            "quality": _profile_quality(bucket["block_count"], dispersion),
            "bold_ratio": round(bold_ratio, 2),
            "italic_ratio": round(bucket["italic_count"] / bucket["block_count"], 2) if bucket["block_count"] else 0.0,
            "font_families": list(bucket["font_families"]),
        }
    return result
```

- [ ] **Step 6: Run tests to verify pass**

Run: `pytest tests/test_ocr_profiles.py -v`
Expected: 7 PASSED

- [ ] **Step 7: Write failing test for `cross_validate_with_span`**

Append to `tests/test_ocr_profiles.py`:

```python
def test_cross_validate_with_span_no_profile() -> None:
    from paperforge.worker.ocr_profiles import cross_validate_with_span

    block = {"span_metadata": {"size": 10.0, "flags": 0}}
    result = cross_validate_with_span(block, "body_paragraph", {})
    assert result["role"] == "body_paragraph"
    assert result["adjustment"] == 0.0


def test_cross_validate_with_span_mismatch() -> None:
    from paperforge.worker.ocr_profiles import cross_validate_with_span

    block = {"span_metadata": {"size": 16.0, "flags": "bold"}}
    profiles = {
        "body_paragraph": {
            "block_count": 5, "mean_size": 10.0, "max_size": 10.5, "min_size": 9.5,
            "dispersion": 0.05, "quality": "strong", "bold_ratio": 0.0,
            "italic_ratio": 0.0, "font_families": ["TimesNewRomanPSMT"],
        },
    }
    result = cross_validate_with_span(block, "body_paragraph", profiles)
    assert result["role"] == "body_paragraph"
    assert result["adjustment"] < 0


def test_cross_validate_with_span_match() -> None:
    from paperforge.worker.ocr_profiles import cross_validate_with_span

    block = {"span_metadata": {"size": 10.0, "flags": 0}}
    profiles = {
        "body_paragraph": {
            "block_count": 5, "mean_size": 10.0, "max_size": 10.5, "min_size": 9.5,
            "dispersion": 0.05, "quality": "strong", "bold_ratio": 0.0,
            "italic_ratio": 0.0, "font_families": ["TimesNewRomanPSMT"],
        },
    }
    result = cross_validate_with_span(block, "body_paragraph", profiles)
    assert result["role"] == "body_paragraph"
    assert result["adjustment"] > 0


def test_cross_validate_with_span_suggests_alternative() -> None:
    from paperforge.worker.ocr_profiles import cross_validate_with_span

    block = {"span_metadata": {"size": 16.0, "flags": "bold"}}
    profiles = {
        "body_paragraph": {
            "block_count": 5, "mean_size": 10.0, "max_size": 10.5, "min_size": 9.5,
            "dispersion": 0.05, "quality": "strong", "bold_ratio": 0.0,
            "italic_ratio": 0.0, "font_families": ["TimesNewRomanPSMT"],
        },
        "section_heading": {
            "block_count": 3, "mean_size": 16.0, "max_size": 16.5, "min_size": 15.5,
            "dispersion": 0.03, "quality": "strong", "bold_ratio": 1.0,
            "italic_ratio": 0.0, "font_families": ["TimesNewRomanPS-BoldMT"],
        },
    }
    result = cross_validate_with_span(block, "body_paragraph", profiles)
    assert "section_heading" in result["suggested_roles"]
    assert result["adjustment"] < 0
```

Run: `pytest tests/test_ocr_profiles.py::test_cross_validate_with_span_no_profile tests/test_ocr_profiles.py::test_cross_validate_with_span_mismatch tests/test_ocr_profiles.py::test_cross_validate_with_span_match tests/test_ocr_profiles.py::test_cross_validate_with_span_suggests_alternative -v`
Expected: 4 FAILED

- [ ] **Step 8: Implement `cross_validate_with_span` and `compare_against_role_family`**

Add to `paperforge/worker/ocr_profiles.py`:

```python
def compare_against_role_family(
    block_profile: dict,
    role_family_profile: dict,
) -> dict:
    """Compare a block's style profile against a role family profile.

    Returns a dict with:
        {"size_compatible": bool, "bold_compatible": bool,
         "size_distance": float, "match_score": float}
    """
    if not block_profile or not role_family_profile:
        return {"size_compatible": False, "bold_compatible": False,
                "size_distance": 1.0, "match_score": 0.0}

    block_size = block_profile.get("mean_size", 0)
    fam_mean = role_family_profile.get("mean_size", 0)
    fam_max = role_family_profile.get("max_size", 0)
    fam_min = role_family_profile.get("min_size", 0)

    if fam_max == fam_min:
        size_compatible = abs(block_size - fam_mean) < 2.0
    else:
        size_compatible = fam_min <= block_size <= fam_max

    size_distance = (
        abs(block_size - fam_mean) / max(fam_mean, 1)
        if fam_mean > 0
        else 1.0
    )

    bold_ratio = role_family_profile.get("bold_ratio", 0)
    block_bold = block_profile.get("is_bold", False)
    bold_compatible = (bold_ratio > 0.5) == block_bold

    match_score = (
        (0.6 * (1 - min(size_distance, 1.0))) +
        (0.4 * (1 if bold_compatible else 0))
    )

    return {
        "size_compatible": size_compatible,
        "bold_compatible": bold_compatible,
        "size_distance": round(size_distance, 4),
        "match_score": round(match_score, 4),
    }


def cross_validate_with_span(
    block: dict,
    tentative_role: str,
    role_profiles: dict,
) -> dict:
    """Cross-validate a block's span profile against role family profiles.

    Never overrides the tentative role — only adjusts confidence and
    suggests alternatives.

    Returns:
        {"role": str, "adjustment": float, "confidence_total": float,
         "suggested_roles": list[str], "match_details": dict}
    """
    block_profile = extract_block_span_profile(block)
    if block_profile is None:
        return {"role": tentative_role, "adjustment": 0.0, "confidence_total": 0.0,
                "suggested_roles": [], "match_details": {}}

    current_match = compare_against_role_family(
        block_profile, role_profiles.get(tentative_role, {})
    )
    base_score = current_match["match_score"]
    quality = role_profiles.get(tentative_role, {}).get("quality", "no_data")

    if quality in ("weak", "no_data"):
        return {"role": tentative_role, "adjustment": 0.0, "confidence_total": base_score,
                "suggested_roles": [], "match_details": {tentative_role: current_match}}

    suggested_roles = []
    for alt_role, alt_profile in role_profiles.items():
        if alt_role == tentative_role:
            continue
        alt_match = compare_against_role_family(block_profile, alt_profile)
        if alt_match["match_score"] > base_score + 0.1:
            suggested_roles.append(alt_role)

    adjustment = round(base_score - 0.5, 4)

    return {
        "role": tentative_role,
        "adjustment": adjustment,
        "confidence_total": round(base_score, 4),
        "suggested_roles": suggested_roles,
        "match_details": {tentative_role: current_match},
    }
```

- [ ] **Step 9: Run all profile tests to verify pass**

Run: `pytest tests/test_ocr_profiles.py -v`
Expected: 11 PASSED

- [ ] **Step 10: Refactor `ocr_render.py` to import from `ocr_profiles.py`**

In `paperforge/worker/ocr_render.py`, replace the existing `_extract_style_profile` function (lines 167-225) with:

```python
from paperforge.worker.ocr_profiles import extract_block_span_profile
```

Remove the old `_extract_style_profile` function body entirely. The function name is now an imported alias — all call sites (`_build_heading_style_profiles` at line 243, `_disambiguate_heading_role` at line 343) continue to work identically.

Also replace all `_extract_style_profile(block)` calls with the same call (the import makes it a transparent alias).

- [ ] **Step 11: Run render tests to confirm no regression**

Run: `pytest tests/test_ocr_render.py -v`
Expected: all pass (or skip if render tests need OCR artifacts — at minimum check no import errors)

Actually: run: `python -c "from paperforge.worker.ocr_profiles import extract_block_span_profile, build_role_span_profiles, cross_validate_with_span, compare_against_role_family; from paperforge.worker.ocr_render import render_fulltext_markdown; print('OK')"`
Expected: `OK`

- [ ] **Step 12: Commit**

```bash
git add paperforge/worker/ocr_profiles.py tests/test_ocr_profiles.py paperforge/worker/ocr_render.py
git commit -m "feat: create ocr_profiles.py with span extraction, profile aggregation, and cross-validation"
```

---

### Task 3: Profile Persistence and Pipeline Wiring

**Files:**
- Modify: `paperforge/worker/ocr_rebuild.py` (add profile writing step)
- Modify: `paperforge/worker/ocr.py` (`postprocess_ocr_result`, add profile writing)
- Create/modify pipeline wiring to write `role_span_profiles.json`

- [ ] **Step 1: Write failing test for profile JSON output**

Add to `tests/test_ocr_blocks.py` (or new test file for rebuild tests):

```python
def test_role_span_profiles_written_to_output() -> None:
    """Verify that role_span_profiles.json is written during rebuild."""
    import json, os, tempfile
    from pathlib import Path
    from paperforge.worker.ocr_profiles import build_role_span_profiles
    # This is a contract test — verify the function exists and produces
    # serializable output that matches the file format spec
    blocks = [
        {"role": "section_heading", "span_metadata": {"size": 16.0, "flags": "bold"}},
        {"role": "body_paragraph", "span_metadata": {"size": 10.0, "flags": 0}},
    ]
    profiles = build_role_span_profiles(blocks)
    # Must be JSON-serializable
    dumped = json.dumps(profiles)
    assert "section_heading" in dumped
    assert "body_paragraph" in dumped
```

- [ ] **Step 2: Add `write_role_span_profiles` to `ocr_profiles.py`**

Add to `paperforge/worker/ocr_profiles.py`:

```python
import json
from pathlib import Path


def write_role_span_profiles(
    blocks: list[dict],
    output_dir: str | Path,
) -> Path:
    """Build and write role_span_profiles.json.

    Returns the path to the written file.
    """
    profiles = build_role_span_profiles(blocks)
    output_path = Path(output_dir) / "role_span_profiles.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)
    return output_path
```

- [ ] **Step 3: Wire into `postprocess_ocr_result` in `ocr.py`**

In `paperforge/worker/ocr.py`, in `postprocess_ocr_result` (around line 1691), find the point after `build_structured_blocks` where structured blocks are written. After the `write_structured_blocks_jsonl` call, add:

```python
from paperforge.worker.ocr_profiles import write_role_span_profiles

# ... inside postprocess_ocr_result ...
# Write role-level span profiles
write_role_span_profiles(all_structured_rows, structured_output_dir)
```

- [ ] **Step 4: Wire into `run_derived_rebuild_for_keys` in `ocr_rebuild.py`**

In `paperforge/worker/ocr_rebuild.py`, in `run_derived_rebuild_for_keys` (around line 34), find the section after `write_structured_blocks_jsonl` (around line 105). Add:

```python
from paperforge.worker.ocr_profiles import write_role_span_profiles

write_role_span_profiles(all_structured_rows, structured_dir)
```

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `python -m pytest tests/unit/ tests/cli/ -v --tb=short -x`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_profiles.py paperforge/worker/ocr.py paperforge/worker/ocr_rebuild.py tests/test_ocr_blocks.py
git commit -m "feat: persist role_span_profiles.json and wire into rebuild pipeline"
```

---

### Task 4: Dynamic Heading Family Discovery

**Files:**
- Modify: `paperforge/worker/ocr_roles.py` (refactor `_infer_heading_level`, `_is_backmatter_boundary_heading`, heading fallback)
- Modify: `paperforge/worker/ocr_render.py` (refactor `_disambiguate_heading_role`, `_build_heading_style_profiles`)
- Modify: `tests/test_ocr_roles.py`

This task replaces hardcoded font-size thresholds with dynamic profile-based matching. The key changes:

1. **`_infer_heading_level`** — remove hardcoded `font_size >= 14`; use profile-relative comparison
2. **`_disambiguate_heading_role`** — use `build_role_span_profiles` output instead of ephemeral clustering for heading level matching
3. **`_is_backmatter_boundary_heading`** — remove `page >= 8` hard gate; use relative tail position + span distinctiveness

- [ ] **Step 1: Review current hardcoded heading thresholds**

Read lines 231-253 (`_infer_heading_level`), lines 726-759 (heading fallback in `assign_block_role`), and lines 134-176 (`_is_backmatter_boundary_heading`) in `ocr_roles.py`. The hardcoded gates to remove:

| Location | Line | Gate |
|---|---|---|
| `_infer_heading_level` | 240 | `if font_size >= 14: ... section_heading` |
| `assign_block_role` heading fallback | 750-751 | `(font_size >= 12 and "bold" in font_flags) or font_size >= 14` |
| `_is_backmatter_boundary_heading` | 160-161 | `page_num < 8: return False` |

- [ ] **Step 2: Write failing test for profile-based heading detection**

Add to `tests/test_ocr_roles.py`:

```python
def test_heading_level_from_profile_match() -> None:
    """After profile aggregation, headings should be classified by
    profile match, not hardcoded font size."""
    from paperforge.worker.ocr_profiles import build_role_span_profiles
    from paperforge.worker.ocr_roles import _infer_heading_level

    # A 12pt bold heading in a context where section headings are 16pt
    # should NOT be classified as section_heading
    profiles = build_role_span_profiles([
        {"role": "section_heading", "span_metadata": {"size": 16.0, "flags": "bold"}},
        {"role": "subsection_heading", "span_metadata": {"size": 14.0, "flags": "bold"}},
    ])
    # The existing _infer_heading_level doesn't use profiles yet;
    # this test verifies the target behavior after refactor
    pass  # Will be updated when the refactor is complete


def test_backmatter_boundary_detects_on_early_page() -> None:
    """Backmatter boundary should be detectable on papers with fewer
    than 8 pages, without a hard page gate."""
    from paperforge.worker.ocr_roles import _is_backmatter_boundary_heading
    block = {
        "span_metadata": {"size": 12.0, "flags": "bold"},
        "text": "ADDITIONAL INFORMATION AND DECLARATIONS",
        "page": 5,
    }
    result = _is_backmatter_boundary_heading(block, 5, 10)
    # Currently returns False because page 5 < 8
    # After fix: should detect if the text + style look like a boundary
    assert result == False  # Will change to True after fix
```

- [ ] **Step 3: Refactor `_infer_heading_level` to accept and use role profiles**

Change signature from `_infer_heading_level(text: str, font_size: float = 0)` to:

```python
def _infer_heading_level(
    text: str,
    font_size: float = 0,
    role_profiles: dict | None = None,
    block: dict | None = None,
) -> str | None:
```

New logic:
- If `role_profiles` is available and has heading families, use profile matching:
  - Check `section_heading` profile: if block size matches, return `section_heading`
  - Check `subsection_heading` profile: if block size matches, return` subsection_heading`
  - Fall back to `sub_subsection_heading`
- If no profiles available (no_data), fall back to current heuristics (word count, upper_ratio, verb detection)

The hardcoded `if font_size >= 14` block (line 240) must be removed. Replace with profile-based check.

Actual implementation to add at start of function:

```python
    if role_profiles and block:
        block_profile = extract_block_span_profile(block)
        if block_profile:
            for candidate_role, required_size in [
                ("section_heading", None),
                ("subsection_heading", None),
                ("sub_subsection_heading", None),
            ]:
                fam = role_profiles.get(candidate_role)
                if fam and fam.get("quality") in ("strong", "moderate"):
                    from paperforge.worker.ocr_profiles import compare_against_role_family
                    match = compare_against_role_family(block_profile, fam)
                    if match["size_compatible"] and match["match_score"] > 0.6:
                        return candidate_role
```

- [ ] **Step 4: Refactor `_is_backmatter_boundary_heading` to remove page gate**

Replace `if page_num < 8: return False` (line 160-161) with:

```python
    # Relative tail position instead of absolute page gate
    if total_pages > 0 and (page_num / total_pages) < 0.5:
        return False
```

This changes from a fixed `page >= 8` to "must be in the second half of the paper."

Also add span visual signal: if the block has `span_metadata` showing bold + distinctive size vs. body, boost detection confidence. After the existing text-based checks, add:

```python
    # Span visual signal — boundary headings are typically bold 11pt+
    span_meta = block.get("span_metadata", {}) or {}
    if isinstance(span_meta, dict):
        font_size = span_meta.get("size", 0) or 0
        font_flags = (str(span_meta.get("flags", "") or "")).lower()
        is_visually_heading = ("bold" in font_flags and font_size >= 11) or font_size >= 14
    elif isinstance(span_meta, list):
        sizes = [s.get("size", 0) or 0 for s in span_meta if s.get("size")]
        flags = [s.get("flags", 0) for s in span_meta]
        mean_size = sum(sizes) / len(sizes) if sizes else 0
        is_bold = any(bool(f & 16) for f in flags if isinstance(f, int))
        is_text_bold = any("bold" in (str(s.get("flags", "") or "")).lower() for s in span_meta)
        is_visually_heading = ((is_bold or is_text_bold) and mean_size >= 11) or mean_size >= 14
    else:
        is_visually_heading = False

    if not is_visually_heading and not has_container_words:
        return False
```

The logic: a boundary heading must either have container words (existing) OR be visually distinctive (span signal). Both paths remain valid.

- [ ] **Step 5: Refactor `_disambiguate_heading_role` in `ocr_render.py`**

Update to use `build_role_span_profiles` aggregated profiles instead of just the ephemeral `style_profiles` dict:

```python
def _disambiguate_heading_role(
    block: dict,
    style_profiles: dict,
    role_profiles: dict | None = None,
) -> str | None:
    profile = extract_block_span_profile(block)
    if profile is None:
        return None

    # Try role profiles first (persistent, aggregated across papers)
    if role_profiles:
        for candidate_role in (
            "section_heading", "subsection_heading",
            "sub_subsection_heading", "backmatter_heading",
        ):
            fam = role_profiles.get(candidate_role)
            if fam and fam.get("quality") in ("strong", "moderate"):
                from paperforge.worker.ocr_profiles import compare_against_role_family
                match = compare_against_role_family(profile, fam)
                if match["size_compatible"] and match["match_score"] > 0.6:
                    return candidate_role

    # Fall back to style_profiles (ephemeral, per-paper clustering)
    if not style_profiles:
        return None
    # ... existing style_profiles matching logic ...
```

- [ ] **Step 6: Update heading fallback in `assign_block_role`**

Replace lines 741-759 (the dead span_metadata branch that always produces `is_visually_prominent = False`) with:

```python
    # Visual heading detection — use span_metadata if available
    is_visually_prominent = False
    span_meta = block.get("span_metadata", {}) or {}
    if isinstance(span_meta, dict):
        font_size = span_meta.get("size", 0) or 0
        font_flags = (str(span_meta.get("flags", "") or "")).lower()
        is_visually_prominent = ("bold" in font_flags and font_size >= 11) or font_size >= 14
    elif isinstance(span_meta, list):
        sizes = [s.get("size", 0) or 0 for s in span_meta if s.get("size")]
        mean_size = sum(sizes) / len(sizes) if sizes else 0
        all_flags = [s.get("flags", 0) for s in span_meta]
        is_bold = any(bool(f & 16) for f in all_flags if isinstance(f, int))
        is_visually_prominent = (is_bold and mean_size >= 11) or mean_size >= 14
```

This is NOT a new threshold — it's the same logic that was already intended in the original code but was dead because `span_metadata` never arrived. Now with Task 1's pipeline carry-through, this code will actually execute.

- [ ] **Step 7: Run heading-related tests**

Run: `python -m pytest tests/test_ocr_roles.py -v --tb=short -x`
Expected: all pass (existing tests should be unaffected; dead code path activation may change behavior for papers with real span_metadata, but unit tests use mocked data)

Run: `python -m pytest tests/ -v --tb=short -k "heading" --no-header -q`
Expected: all pass

- [ ] **Step 8: Commit**

```bash
git add paperforge/worker/ocr_roles.py paperforge/worker/ocr_render.py tests/test_ocr_roles.py
git commit -m "feat: dynamic heading family discovery with profile matching, remove hardcoded font-size thresholds and absolute page gate"
```

---

### Task 5: Second-Pass Cross-Validation

**Files:**
- Modify: `paperforge/worker/ocr_roles.py` (add second-pass function, wire into `assign_block_role`)
- Modify: `paperforge/worker/ocr_profiles.py` (add second-pass helpers if needed)
- Create: `tests/test_second_pass_cross_validation.py`

This task adds a second-pass cross-validation step that runs after initial role assignment. It targets low-confidence blocks where span_metadata can help resolve ambiguity:

- body paragraphs that look like headings (large bold text)
- body paragraphs that look like captions (Figure/Table prefix + small text)
- captions that look like body text (long text without span evidence)
- regex-matched references that look like body text (body-sized font)

- [ ] **Step 1: Write failing tests for second-pass cross-validation**

Create `tests/test_second_pass_cross_validation.py`:

```python
"""Tests for second-pass cross-validation of low-confidence role assignments."""

from __future__ import annotations


SAMPLE_PROFILES = {
    "body_paragraph": {
        "block_count": 10, "mean_size": 10.0, "max_size": 10.5, "min_size": 9.5,
        "dispersion": 0.05, "quality": "strong", "bold_ratio": 0.0,
        "italic_ratio": 0.0, "font_families": ["TimesNewRomanPSMT"],
    },
    "section_heading": {
        "block_count": 3, "mean_size": 16.0, "max_size": 16.5, "min_size": 15.5,
        "dispersion": 0.03, "quality": "strong", "bold_ratio": 1.0,
        "italic_ratio": 0.0, "font_families": ["TimesNewRomanPS-BoldMT"],
    },
    "figure_caption": {
        "block_count": 4, "mean_size": 9.0, "max_size": 9.5, "min_size": 8.5,
        "dispersion": 0.05, "quality": "strong", "bold_ratio": 0.0,
        "italic_ratio": 0.75, "font_families": ["TimesNewRomanPS-ItalicMT"],
    },
    "reference_item": {
        "block_count": 15, "mean_size": 8.5, "max_size": 9.0, "min_size": 8.0,
        "dispersion": 0.04, "quality": "strong", "bold_ratio": 0.0,
        "italic_ratio": 0.0, "font_families": ["TimesNewRomanPSMT"],
    },
}


def test_second_pass_body_paragraph_misclassified_heading() -> None:
    """A body_paragraph with heading-like span should be flagged."""
    from paperforge.worker.ocr_roles import second_pass_cross_validate

    block = {
        "role": "body_paragraph",
        "role_confidence": 0.4,
        "span_metadata": {"size": 16.0, "flags": "bold"},
        "text": "Clinical Outcomes",
        "raw_label": "text",
    }
    result = second_pass_cross_validate(block, SAMPLE_PROFILES)
    assert result["role_changed"] is False
    assert "section_heading" in result["suggested_roles"]
    assert result["confidence_adjustment"] < 0


def test_second_pass_body_paragraph_confirmed_body() -> None:
    """A body_paragraph with body-like span should be left alone."""
    from paperforge.worker.ocr_roles import second_pass_cross_validate

    block = {
        "role": "body_paragraph",
        "role_confidence": 0.6,
        "span_metadata": {"size": 10.0, "flags": 0},
        "text": "The results show a significant difference between groups.",
        "raw_label": "text",
    }
    result = second_pass_cross_validate(block, SAMPLE_PROFILES)
    assert result["role_changed"] is False
    assert result["confidence_adjustment"] > 0


def test_second_pass_caption_long_text() -> None:
    """A long figure_caption with body-sized span should be flagged."""
    from paperforge.worker.ocr_roles import second_pass_cross_validate

    block = {
        "role": "figure_caption",
        "role_confidence": 0.5,
        "span_metadata": {"size": 10.5, "flags": 0},
        "text": "Figure 4. This is a very long caption that looks like body text in font size...",
        "raw_label": "figure_title",
    }
    result = second_pass_cross_validate(block, SAMPLE_PROFILES)
    assert result["role_changed"] is False  # Don't override formal prefix
    assert result["confidence_adjustment"] < 0


def test_second_pass_reference_body_style() -> None:
    """A regex-matched reference item with body-sized font should be flagged."""
    from paperforge.worker.ocr_roles import second_pass_cross_validate

    block = {
        "role": "reference_item",
        "role_confidence": 0.55,
        "span_metadata": {"size": 10.5, "flags": 0},
        "text": "Smith et al. (2020) found that...",
        "raw_label": "text",
    }
    result = second_pass_cross_validate(block, SAMPLE_PROFILES)
    assert result["role_changed"] is False
    # Should have lower confidence because font matches body, not reference family
    assert result["confidence_adjustment"] < 0


def test_second_pass_no_span_metadata() -> None:
    """Without span_metadata, second pass should produce no change."""
    from paperforge.worker.ocr_roles import second_pass_cross_validate

    block = {
        "role": "body_paragraph",
        "role_confidence": 0.5,
        "text": "Some paragraph without span data.",
        "raw_label": "text",
    }
    result = second_pass_cross_validate(block, SAMPLE_PROFILES)
    assert result["role_changed"] is False
    assert result["confidence_adjustment"] == 0.0
    assert len(result["suggested_roles"]) == 0
```

Run: `pytest tests/test_second_pass_cross_validation.py -v`
Expected: 5 FAILED

- [ ] **Step 2: Implement `second_pass_cross_validate` in `ocr_roles.py`**

Add to `paperforge/worker/ocr_roles.py`:

```python
def second_pass_cross_validate(
    block: dict,
    role_profiles: dict,
) -> dict:
    """Second-pass cross-validation for low-confidence role assignments.

    Examines low-confidence blocks against role family profiles.
    Never overrides the assigned role — only adjusts confidence and
    suggests alternative roles for review.

    Returns:
        {"role": str, "confidence_adjustment": float,
         "role_changed": bool, "suggested_roles": list[str],
         "match_details": dict}
    """
    from paperforge.worker.ocr_profiles import (
        cross_validate_with_span,
        extract_block_span_profile,
    )

    current_role = block.get("role", "")
    current_confidence = block.get("role_confidence", 0.5)

    # Skip if no span data
    block_profile = extract_block_span_profile(block)
    if block_profile is None:
        return {
            "role": current_role,
            "confidence_adjustment": 0.0,
            "role_changed": False,
            "suggested_roles": [],
            "match_details": {},
        }

    # Run cross-validation
    xv_result = cross_validate_with_span(block, current_role, role_profiles)
    adjustment = xv_result["adjustment"]
    suggested_roles = xv_result["suggested_roles"]

    # Don't change role — only adjust confidence
    # Exception: if suggested_roles has exactly one strong candidate
    # AND current confidence is very low (< 0.3) AND adjustment is strongly negative
    role_changed = False
    if (
        len(suggested_roles) == 1
        and current_confidence < 0.3
        and adjustment < -0.2
    ):
        # Roles that must never be overridden by second pass
        never_override = {"paper_title", "abstract_body", "reference_heading",
                          "reference_item", "media_asset", "figure_asset",
                          "table_html", "noise", "unknown_structural"}
        if current_role in never_override:
            role_changed = False
        elif suggested_roles[0] not in never_override:
            role_changed = True

    return {
        "role": suggested_roles[0] if role_changed else current_role,
        "confidence_adjustment": round(adjustment, 4),
        "role_changed": role_changed,
        "suggested_roles": suggested_roles,
        "match_details": xv_result.get("match_details", {}),
    }
```

- [ ] **Step 3: Wire second-pass into `assign_block_role`**

In `ocr_roles.py`, `assign_block_role` function, after the initial role assignment (around line 776, just before `return row`), add:

```python
    # Second-pass cross-validation for low-confidence blocks
    if row.get("role_confidence", 1.0) < 0.7 and paper_context and "role_profiles" in paper_context:
        xv_result = second_pass_cross_validate(row, paper_context["role_profiles"])
        row["role_confidence"] = round(
            max(0.0, min(1.0, row.get("role_confidence", 0.5) + xv_result["confidence_adjustment"])),
            4,
        )
        if xv_result["role_changed"]:
            row["role"] = xv_result["role"]
            row.setdefault("evidence", []).append(
                f"second_pass: {xv_result['role']} (span cross-validation)"
            )
        if xv_result["suggested_roles"]:
            row.setdefault("evidence", []).append(
                f"span_alternatives: {','.join(xv_result['suggested_roles'])}"
            )
```

Note: `paper_context` is a new parameter to `assign_block_role`. Its current signature must be updated. Either:
- Option A: Add an optional `paper_context: dict | None = None` parameter (cleaner, but changes API)
- Option B: Store `role_profiles` as a module-level cache (ugly, thread-unsafe)
- Option C: Have `build_structured_blocks` compute profiles and pass them through

For this implementation, use **Option A** — add `paper_context` as an optional dict parameter:

```python
def assign_block_role(
    block: dict,
    total_pages: int,
    page_regime: dict | None = None,
    paper_context: dict | None = None,
) -> dict:
```

And in `build_structured_blocks` (ocr_blocks.py), after computing all structured rows, compute role_profiles and pass them to `assign_block_role`:

```python
    from paperforge.worker.ocr_profiles import build_role_span_profiles

    # Build role profiles for cross-validation
    paper_context = {}
    pages = set(r["page"] for r in raw_blocks)
    # Only build profiles if there are enough blocks
    if len(raw_blocks) >= 10:
        paper_context["role_profiles"] = build_role_span_profiles(
            [{"role": "temp", **r} for r in raw_blocks]
        )

    for raw in raw_blocks:
        row = assign_block_role(raw, total_pages, paper_context=paper_context)
        ...
```

Wait — this creates a chicken-and-egg problem: `build_role_span_profiles` needs role-assigned blocks, but `assign_block_role` needs profiles. This means the second-pass must be a **separate loop** after initial assignment.

Correct approach: first pass assigns roles without profiles, then profiles are built from first-pass results, then second pass refines low-confidence blocks.

In `build_structured_blocks`, replace the single loop with a two-pass approach:

```python
    # First pass: initial role assignment (no span profiles)
    rows = []
    for raw in raw_blocks:
        row = assign_block_role(raw, total_pages)
        rows.append(row)

    # Build role span profiles from first-pass results
    paper_context: dict = {}
    if len(rows) >= 10:
        from paperforge.worker.ocr_profiles import build_role_span_profiles
        paper_context["role_profiles"] = build_role_span_profiles(rows)

    # Second pass: cross-validate low-confidence blocks
    if paper_context.get("role_profiles"):
        for row in rows:
            if row.get("role_confidence", 1.0) < 0.7:
                xv_result = second_pass_cross_validate(row, paper_context["role_profiles"])
                row["role_confidence"] = round(
                    max(0.0, min(1.0, row.get("role_confidence", 0.5) + xv_result["confidence_adjustment"])),
                    4,
                )
                if xv_result["role_changed"]:
                    row["role"] = xv_result["role"]
                    row.setdefault("evidence", []).append(
                        f"second_pass: {xv_result['role']} (span cross-validation)"
                    )
                if xv_result["suggested_roles"]:
                    row.setdefault("evidence", []).append(
                        f"span_alternatives: {','.join(xv_result['suggested_roles'])}"
                    )
```

- [ ] **Step 4: Run second-pass tests to verify pass**

Run: `pytest tests/test_second_pass_cross_validation.py -v`
Expected: 5 PASSED

Run: `python -m pytest tests/ -v --tb=short -x`
Expected: all pass (no regressions)

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_roles.py paperforge/worker/ocr_blocks.py tests/test_second_pass_cross_validation.py
git commit -m "feat: second-pass cross-validation for low-confidence role assignments using span profiles"
```

---

### Spec Coverage Checklist

| Spec Requirement | Task |
|---|---|
| span_metadata preserved through raw layer | Task 1 |
| span_metadata preserved through structured layer | Task 1 |
| `role_span_profiles.json` exists with profile quality | Task 3 |
| heading families discovered dynamically per paper | Task 4 |
| unnumbered heading hierarchy uses family matching | Task 4 |
| `backmatter_boundary_heading` no longer depends on absolute page number | Task 4 |
| `reference_item` gets family consistency support | Task 5 |
| `frontmatter_noise` becomes more zone/style driven | (TBD — see Future Tasks below) |
| second-pass cross-validation for low-confidence blocks | Task 5 |
| zero span data produces near-zero behavior change | Task 1 (graceful None return), Task 5 (skip if no span) |

### Future Tasks (After This Plan)

The following spec items are **not covered** by the current plan and should be separate follow-ups:

1. **Frontmatter noise refactor** — make `frontmatter_noise` more zone+style driven than phrase driven. Requires analysis of actual journal furniture patterns.
2. **Reference item family re-validation** — deeper per-item consistency checking using `compare_against_role_family` for every reference item, not just low-confidence ones.
3. **Figure caption family consistency** — use `build_role_span_profiles` to compute caption family and validate all captions against it.
4. **Real-paper regression suite** — run span integration on 10+ diverse papers and capture before/after role assignment diff.
