# Figure Appendix Numbering — Execution Plan

## Strategy

Single PR. Small continuous patch, not parallel agents:

```
regex/marker/namespace → ID/callsites → tests → vault spot-check
```

## Tasks (not parallel — sequential)

### Step 1 — Regex + `_extract_figure_number` + `_extract_figure_marker` + `_extract_figure_namespace`

**File:** `paperforge/worker/ocr_figures.py`

This is one atomic change. Cannot split because:

- `_extract_figure_marker` reads the regex — if regex changes to named groups but marker still reads `group(1)`, it breaks
- `_extract_figure_marker` calls `_extract_figure_namespace(text, prefix)` — requires the new signature

**Changes:**

1. **`_FIGURE_NUMBER_PATTERN`** (line ~14): Replace with named-group regex:

```python
_FIGURE_NUMBER_PATTERN = re.compile(
    r"(?:Figure|Fig\\.?|Supplementary\\s+Figure|Supplementary\\s+Fig\\.?|"
    r"Extended\\s+Data\\s+Figure|Extended\\s+Data\\s+Fig\\.?|"
    r"TABLE|Table|图|圖|ͼ)"
    r"\\s*(?:(?P<prefix>[A-Z])\\.?\\s*)?(?P<number>\\d+(?:\\.\\d+)?)",
    re.IGNORECASE,
)
```

2. **`_extract_figure_number`** (line ~109): Read `m.group("number")` instead of `m.group(1)`:

```python
def _extract_figure_number(text: str) -> int | None:
    m = _FIGURE_NUMBER_PATTERN.search(text)
    if m:
        try:
            num_str = m.group("number")
            if num_str is not None:
                return int(float(num_str))
        except (ValueError, TypeError):
            pass
    return None
```

3. **`_extract_figure_marker`** (line ~128): Add prefix fields. **Normalize prefix to uppercase:**

```python
prefix_raw = m.group("prefix")  # may be None or lowercase due to IGNORECASE
prefix = (prefix_raw or "").upper() or None
```

Return dict:

```python
{
    "number": int(float(m.group("number"))),
    "number_text": m.group("number"),
    "prefix": prefix,
    "alpha_prefix": prefix if prefix and prefix != "S" else None,
    "has_s": prefix == "S",
    "has_alpha_prefix": prefix is not None and prefix != "S",
    "namespace": _extract_figure_namespace(text, prefix),
}
```

4. **`_extract_figure_namespace`** (line ~119): Add `prefix` param. Keyword-first priority:

```python
def _extract_figure_namespace(text: str, prefix: str | None = None) -> str:
    lower = text.lower()
    if "extended data" in lower or "extended figure" in lower:
        return "extended_data"
    if prefix == "S":
        return "supplementary"
    if "supplementary" in lower or "supporting" in lower or "additional file" in lower:
        return "supplementary"
    if prefix and prefix != "S":
        return "appendix"
    return "main"
```

**Test (before commit):** `pytest tests/test_ocr_figures.py` passes.

---

### Step 2 — `_format_figure_id` + writeback to all callsites

**File:** `paperforge/worker/ocr_figures.py`

1. **`_format_figure_id`** (line ~240): Add `alpha_prefix` param:

```python
def _format_figure_id(namespace: str, number: int, alpha_prefix: str | None = None) -> str:
    if namespace == "supplementary":
        return f"figure_s{number:03d}"
    if namespace == "extended_data":
        return f"figure_ed{number:03d}"
    if namespace == "appendix":
        letter = (alpha_prefix or "x").lower()
        return f"figure_{letter}{number:03d}"
    return f"figure_{number:03d}"
```

2. **Find every callsite**: `rg "_format_figure_id" paperforge/worker/ocr_figures.py` and update each.

   Every path that passes `namespace` and `number` from marker data must also pass `alpha_prefix`. The callsites include:
   - `ClassicSequentialPass` / `UnresolvedClusterConsolidation`
   - `GroupSequentialPass` / `CompositeParentPass`
   - `CrossPageSettlementPass` / `LegendBundlePass`
   - `SidecarPass` / `FinalAccountingPass`
   - Any synthetic/fallback figure_id construction (where namespace is `"figure"`)
   - `_postprocess_inventory_figures` / `_synthesize_unnumbered_figures`
   - `_recover_unnumbered_figure_assets`

   Rule: if the callsite has marker data available (has `prefix`/`alpha_prefix`), pass it. If not, the new default `None` keeps existing behavior. Add a guard:

```python
if namespace == "appendix" and not alpha_prefix:
    alpha_prefix = "x"  # fallback — should not happen in practice
```

**Test (before commit):** `pytest tests/test_ocr_figures.py` passes.

---

### Step 3 — Tests

**File:** `tests/test_appendix_figure_numbering.py` (new)

Use synthetic block construction (not vault fixtures) for automated tests:

```python
"""Tests for appendix figure numbering (Figure A1 → figure_a001)."""

import pytest
from paperforge.worker.ocr_figures import (
    _extract_figure_number,
    _extract_figure_marker,
    _extract_figure_namespace,
    _format_figure_id,
    build_figure_inventory_vnext,
)

# ---- _extract_figure_number ----

class TestExtractFigureNumber:
    def test_main_after_regex_change(self):
        assert _extract_figure_number("Figure 1. Caption") == 1

    def test_supplementary_after_regex_change(self):
        assert _extract_figure_number("Figure S1. Caption") == 1

    def test_appendix_after_regex_change(self):
        assert _extract_figure_number("Figure A1. Caption") == 1

# ---- _extract_figure_marker ----

class TestExtractFigureMarker:
    def test_supplementary_keyword_has_no_prefix(self):
        marker = _extract_figure_marker("Supplementary Figure 1")
        assert marker["prefix"] is None
        assert marker["alpha_prefix"] is None
        assert marker["namespace"] == "supplementary"
        assert _format_figure_id(marker["namespace"], marker["number"], marker["alpha_prefix"]) == "figure_s001"

    def test_supplementary_keyword_overrides_appendix_prefix(self):
        marker = _extract_figure_marker("Supplementary Figure A1")
        assert marker["prefix"] == "A"
        assert marker["namespace"] == "supplementary"

    def test_extended_data_keyword_overrides_appendix_prefix(self):
        marker = _extract_figure_marker("Extended Data Figure A1")
        assert marker["prefix"] == "A"
        assert marker["namespace"] == "extended_data"

    def test_lowercase_appendix_prefix_normalized(self):
        marker = _extract_figure_marker("Figure a1")
        assert marker["prefix"] == "A"
        assert marker["alpha_prefix"] == "A"
        assert marker["namespace"] == "appendix"

    @pytest.mark.parametrize("text,exp_prefix", [
        ("Figure S1", "S"),
        ("Figure S.1", "S"),
        ("Fig. S 1", "S"),
        ("Figure A1", "A"),
        ("Figure A.1", "A"),
        ("Fig. A 1", "A"),
        ("Figure B2", "B"),
        ("Figure 1", None),
    ])
    def test_prefix_extraction(self, text, exp_prefix):
        marker = _extract_figure_marker(text)
        assert marker["prefix"] == exp_prefix

    @pytest.mark.parametrize("text,exp_ns", [
        ("Figure S1", "supplementary"),
        ("Supplementary Figure 1", "supplementary"),
        ("Figure A1", "appendix"),
        ("Figure A.1", "appendix"),
        ("Figure B2", "appendix"),
        ("Figure 1", "main"),
    ])
    def test_namespace_resolution(self, text, exp_ns):
        marker = _extract_figure_marker(text)
        assert marker["namespace"] == exp_ns

# ---- _format_figure_id ----

class TestFormatFigureId:
    def test_appendix_letter_is_preserved(self):
        assert _format_figure_id("appendix", 2, alpha_prefix="B") == "figure_b002"

    def test_figure_a1_and_figure_b1_do_not_collide(self):
        id_a = _format_figure_id("appendix", 1, alpha_prefix="A")
        id_b = _format_figure_id("appendix", 1, alpha_prefix="B")
        assert id_a == "figure_a001"
        assert id_b == "figure_b001"
        assert id_a != id_b

    def test_main_number_unchanged(self):
        assert _format_figure_id("main", 1) == "figure_001"
        assert _format_figure_id("main", 12, alpha_prefix=None) == "figure_012"

    def test_supplementary_unchanged(self):
        assert _format_figure_id("supplementary", 1) == "figure_s001"

# ---- Inventory-level: Table A1 must NOT leak ----

class TestTableA1Leak:
    def test_table_a1_caption_not_consumed_by_figure_inventory(self):
        """Table A1 is out of scope. Figure inventory must not emit it."""
        blocks = [
            {
                "block_id": 1,
                "page": 1,
                "role": "table_caption",
                "raw_label": "table",
                "text": "Table A1. Baseline characteristics",
                "bbox": [100, 100, 500, 130],
            },
            {
                "block_id": 2,
                "page": 1,
                "role": "media_asset",
                "raw_label": "table",
                "text": "",
                "bbox": [100, 140, 500, 400],
            },
        ]
        inv = build_figure_inventory_vnext(blocks)
        for f in inv.get("matched_figures", []):
            assert "Table A1" not in str(f.get("text", "")), f"Table A1 leaked as {f['figure_id']}"
        assert "figure_a001" not in [f["figure_id"] for f in inv.get("matched_figures", [])]
```

---

### Step 4 — Vault verification (manual / CI)

Not a unit test. Run once before opening PR:

```bash
# M84CTEM9 spot-check
python -c "
from pathlib import Path
from paperforge.worker.ocr_figures import build_figure_inventory_vnext
import json
blocks = [json.loads(l) for l in
    Path('D:/L/OB/Literature-hub/System/PaperForge/ocr/M84CTEM9/structure/blocks.structured.jsonl')
    .read_text('utf-8', errors='replace').splitlines() if l.strip()]
inv = build_figure_inventory_vnext(blocks)
ids = [f['figure_id'] for f in inv['matched_figures']]
assert 'figure_a001' in ids, f'Missing appendix figures. Got: {ids}'
assert 'figure_a002' in ids
assert 'figure_a003' in ids
for f in inv['matched_figures']:
    if 'figure_a00' in f['figure_id']:
        assert f.get('matched_assets'), f'{f[\"figure_id\"]} has no assets'
print(f'OK: {len(ids)} figures, including appendix a001-a003')
"
```

---

## Commits

| # | Scope | Atomic? | Message |
|---|-------|---------|---------|
| 1 | regex + number + namespace + marker | ✅ `pytest tests/test_ocr_figures.py` passes | `feat: recognize appendix figure prefixes` |
| 2 | format ID + all callsites | ✅ `pytest tests/test_ocr_figures.py` passes | `feat: preserve appendix figure prefix in IDs` |
| 3 | tests | ✅ new tests pass | `test: cover appendix figure numbering` |

---

## Pre-implementation checklist

- [ ] `_format_figure_id("appendix", 1, "B")` expected value is `"figure_b001"` (not `b002`) — **FIXED in plan**
- [ ] Task A/B/C treated as one atomic implementation unit (regex + marker + namespace together)
- [ ] Prefix normalized to uppercase in `_extract_figure_marker`
- [ ] `rg "_format_figure_id"` finds ALL callsites; appendix namespace receives `alpha_prefix`
- [ ] Negative test: Table A1 caption NOT consumed by figure inventory
- [ ] Synthetic blocks for automated tests; M84CTEM9 is manual vault verification only

## Risks

| Risk | Mitigation |
|------|-----------|
| `_extract_figure_number` callers break silently | Return type unchanged (`int \| None`). Step 1 commit passes existing test suite. |
| Keyword priority breaks `Supplementary Figure 1` | Existing path has `prefix=None`, falls through to keyword check → same result. Explicit test. |
| Table caption leaks as `figure_a001` | Explicit negative test in Step 3. Guard in `_format_figure_id` for appendix without alpha_prefix. |
| M84CTEM9 Figure A3 collides with main Figure 3 | Different namespaces (`appendix` vs `main`) produce different IDs (`figure_a003` vs `figure_003`). No collision. |
| Lowercase input `Figure a1` not handled | Normalized to uppercase in marker. Explicit test. |
