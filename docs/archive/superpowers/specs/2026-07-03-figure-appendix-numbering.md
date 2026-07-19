## Problem

The figure caption regex `_FIGURE_NUMBER_PATTERN` only extracts digits (`\d+`) from figure numbers, with `S` as the sole alphabetic prefix:

```
Figure 1  → number=1   → figure_001  ✅
Figure S1 → has_s=True → figure_s001 ✅
Figure A1 → NONE       → UNMATCHED   ❌
Figure A2 → NONE       → UNMATCHED   ❌
```

This leaves appendix-style figures (`Figure A1`, `Figure B2`) entirely unmatched, even when their caption and image are on the same page.

## Scope

Only `_extract_figure_number`, `_extract_figure_marker`, `_extract_figure_namespace`, and `_format_figure_id`. No zone boundary changes, no layout changes, no pass changes.

## Design

### Principle

The pipeline already detects "numbering system switches" via namespace detection:
- No prefix → `main`
- `S` prefix → `supplementary`

Extend this: any non-S alphabetic prefix → `appendix`.

Vault analysis shows **zero papers with multiple letter prefixes** (no paper has both Figure A1 and Figure B1). However, the ID format still preserves the real letter prefix so future papers with B1 don't collide.

### Regex Change — Named Groups

Current `_FIGURE_NUMBER_PATTERN`:

```python
r"(?:Figure|Fig\.?|...)\s*(?:S\.?\s*)?(\\d+(?:\\.\\d+)?)"
```

Problems:
1. Only one capture group (digit) — `group(1)` = figure number
2. `S` prefix is a hardcoded non-capturing group, not extensible
3. Adding prefix groups shifts group indices, breaking `_extract_figure_number`

New pattern — named groups:

```python
_FIGURE_NUMBER_PATTERN = re.compile(
    r"(?:Figure|Fig\\.?|Supplementary\\s+Figure|Supplementary\\s+Fig\\.?|"
    r"Extended\\s+Data\\s+Figure|Extended\\s+Data\\s+Fig\\.?|"
    r"TABLE|Table|图|圖|ͼ)"
    r"\\s*(?:(?P<prefix>[A-Z])\\.?\\s*)?(?P<number>\\d+(?:\\.\\d+)?)",
    re.IGNORECASE,
)
```

- `prefix`: optional single letter (A-Z), normalized to uppercase
- `number`: the digit sequence (unchanged)
- No hardcoded `S` check in the regex — prefix logic moves to namespace code

### `_extract_figure_number` — MUST Update

**Cannot be left unchanged.** Old implementation reads `match.group(1)` (digit). After named groups, reads `match.group("number")`:

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

Return type remains `int | None` — callers unchanged.

### `_extract_figure_marker` — Extended contract

```python
{
    "number": 1,
    "number_text": "1",
    "prefix": "A",              # raw prefix letter from regex (A-Z), or None
    "alpha_prefix": "A",        # prefix if non-S, else None
    "has_s": False,              # prefix == "S"
    "has_alpha_prefix": True,    # prefix is A-Z and not S
    "namespace": "appendix",     # resolved namespace
}
```

Note: `Supplementary Figure 1` has no alphabetic prefix (`prefix=None`), so its namespace comes from the keyword path (`"supplementary"`), not from prefix detection.

### `_extract_figure_namespace` — Priority: keyword > S prefix > non-S prefix

```python
def _extract_figure_namespace(text: str, prefix: str | None = None) -> str:
    lower = text.lower()

    # Explicit descriptor has highest priority.
    if "extended data" in lower or "extended figure" in lower:
        return "extended_data"

    # S-prefix remains supplementary even without keyword.
    if prefix == "S":
        return "supplementary"

    if "supplementary" in lower or "supporting" in lower or "additional file" in lower:
        return "supplementary"

    # Non-S alphabetic prefix without explicit descriptor → appendix.
    if prefix and prefix != "S":
        return "appendix"

    return "main"
```

This prevents `Supplementary Figure A1` from being misclassified as appendix — the keyword `Supplementary` takes priority.

### `_format_figure_id` — Preserve Real Prefix Letter

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

```
Figure A1 → figure_a001
Figure B1 → figure_b001   (no collision with A1)
```

### Table A1 — Explicitly Out of Scope

`_extract_figure_number` and `_extract_figure_marker` are shared utilities (used by both figure and table code). However:

- **This spec is figure-only.** The regex already includes `TABLE|Table`, which is pre-existing. This change must NOT expand table-caption matching behavior — the regex already matched `Table 1` before.
- Figure inventory must not newly start consuming table captions as figure records. If `Table A1` is matched by the regex, it is consumed by `_extract_figure_marker` for utility purposes only, but `build_figure_inventory` must not emit a `figure_a001` for it.
- Table-side appendix support (`table_a001`) is deferred to a separate change.

### Functions to Touch

| Function | File | Change |
|----------|------|--------|
| `_FIGURE_NUMBER_PATTERN` | ocr_figures.py | Replace with named-group regex |
| `_extract_figure_number` | ocr_figures.py | Read `group("number")` instead of `group(1)` |
| `_extract_figure_marker` | ocr_figures.py | Add `prefix`, `alpha_prefix`, `has_alpha_prefix`, `namespace` fields |
| `_extract_figure_namespace` | ocr_figures.py | Accept `prefix` param; keyword-first priority; non-S → appendix |
| `_format_figure_id` | ocr_figures.py | Accept `alpha_prefix` param; appendix → `figure_{letter}XXX` |

### Not Touched

- Zone detection — no change
- Layout passes — no change
- `LegendBundlePass` — unchanged (calls `_extract_figure_number` which still returns `int | None`)
- Cross-page / same-page passes — unchanged
- Table inventory — out of scope
- `Scheme 1` / Roman numerals / `Figure 1A` — out of scope

## Edge Cases

| Case | number | prefix | alpha_prefix | namespace | ID | Correct? |
|------|--------|--------|-------------|-----------|-----|----------|
| `Figure 1` | 1 | None | None | main | `figure_001` | ✅ |
| `Figure S1` | 1 | S | None | supplementary | `figure_s001` | ✅ |
| `Fig. S.1` | 1 | S | None | supplementary | `figure_s001` | ✅ |
| `Fig. S 1` | 1 | S | None | supplementary | `figure_s001` | ✅ |
| `Supplementary Figure 1` | 1 | None | None | supplementary | `figure_s001` | ✅ keyword path |
| `Supplementary Figure A1` | 1 | A | A | supplementary | `figure_s001` | ✅ keyword > prefix |
| `Extended Data Figure A1` | 1 | A | A | extended_data | `figure_ed001` | ✅ keyword > prefix |
| `Figure A1` | 1 | A | A | appendix | `figure_a001` | ✅ |
| `Figure A.1` | 1 | A | A | appendix | `figure_a001` | ✅ |
| `Fig. A 1` | 1 | A | A | appendix | `figure_a001` | ✅ |
| `Figure B2` | 2 | B | B | appendix | `figure_b002` | ✅ |
| `TABLE A1` | 1 | A | A | appendix | N/A | ⚠️ extractor-level only; table inventory deferred |
| `Figure 1A` | 1 | None | None | main | `figure_001` | ⚠️ pre-existing (suffix ignored) |
| `Figure A` (no digit) | None | A | — | — | — | ✅ no number → no match |
| `Scheme 1` | None | None | — | — | — | ⚠️ out of scope |
| `Figure I` (Roman) | None | I | — | — | — | ⚠️ out of scope |

## Verification

### Unit tests (add to `test_ocr_figures.py`)

```python
# Core contract: _extract_figure_number still works after regex change
def test_extract_figure_number_main_after_regex_change():
    assert _extract_figure_number("Figure 1. Caption") == 1

def test_extract_figure_number_supplementary_after_regex_change():
    assert _extract_figure_number("Figure S1. Caption") == 1

def test_extract_figure_number_appendix_after_regex_change():
    assert _extract_figure_number("Figure A1. Caption") == 1

# Supplementary keyword has no prefix
def test_supplementary_figure_keyword_has_no_prefix():
    marker = _extract_figure_marker("Supplementary Figure 1")
    assert marker["prefix"] is None
    assert marker["alpha_prefix"] is None
    assert marker["namespace"] == "supplementary"
    assert _format_figure_id(marker["namespace"], marker["number"], marker["alpha_prefix"]) == "figure_s001"

# Keyword overrides appendix prefix
def test_supplementary_keyword_overrides_appendix_prefix():
    marker = _extract_figure_marker("Supplementary Figure A1")
    assert marker["prefix"] == "A"
    assert marker["namespace"] == "supplementary"

def test_extended_data_keyword_overrides_appendix_prefix():
    marker = _extract_figure_marker("Extended Data Figure A1")
    assert marker["prefix"] == "A"
    assert marker["namespace"] == "extended_data"

# Prefix forms
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
def test_figure_marker_prefix(text, exp_prefix):
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
def test_figure_namespace(text, exp_ns):
    marker = _extract_figure_marker(text)
    assert marker["namespace"] == exp_ns

# ID format preserves real prefix letter
def test_appendix_letter_is_preserved_in_id():
    marker = _extract_figure_marker("Figure B2. Caption")
    assert marker["alpha_prefix"] == "B"
    fid = _format_figure_id("appendix", 2, alpha_prefix="B")
    assert fid == "figure_b002"

def test_figure_a1_and_figure_b1_do_not_collide():
    id_a = _format_figure_id("appendix", 1, alpha_prefix="A")
    id_b = _format_figure_id("appendix", 1, alpha_prefix="B")
    assert id_a != id_b

# Existing behavior unchanged
def test_s_prefix_stays_supplementary_number():
    assert _extract_figure_number("Figure S1. text") == 1

# Vault spot-check: M84CTEM9
def test_appendix_figure_integration():
    blocks = load_blocks_for("M84CTEM9")
    inv = build_figure_inventory_vnext(blocks)
    ids = [f["figure_id"] for f in inv["matched_figures"]]
    assert "figure_a001" in ids
    assert "figure_a002" in ids
    assert "figure_a003" in ids
    assert all(f.get("matched_assets") for f in inv["matched_figures"] if "figure_a00" in f["figure_id"])
```

### Regression safety

- `pytest tests/test_ocr_figures.py` — all existing tests pass
- `ruff check paperforge/worker/ocr_figures.py` — clean
- Figure inventory must not gain new `figure_aXXX` entries for table captions (compare against baseline)

### Vault verification

- Run `build_figure_inventory_vnext` on M84CTEM9: confirm `figure_a001`, `figure_a002`, `figure_a003` appear with assets
- Run full batch comparison against vault: total figure match count should increase by ~7 (the 7 post-ref appendix figure captions). Zero regressions on existing `Figure 1` / `Figure S1` matches.

## Open Decisions

- Table A1: separate PR, not here
- `Scheme 1` / Roman numerals: separate issue
- Cross-page continuation (NC66N4Q3): separate issue
