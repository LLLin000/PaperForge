# OCR Reference Detection Fix — Specification v3

> **Status:** Spec complete — all root causes validated via trace evidence
> **Implementation-ready:** Tracks 1, 2a, 3, 5
> **Limitation (no fix):** Track 4 — Wiley heading not in OCR text layer
> **Conditional:** Track 5b (4AG67PBH bio split)
> **Date:** 2026-07-02

---

## Track 1: `(N)` Parenthetical Reference Number Support

**Files:** `ocr_roles.py`, `ocr_render.py`, `ocr_reference_signals.py`
**Status: EXECUTABLE**

### Root Cause

Three regex code paths check reference number prefix formats but none accept `(N)`:

| Code path | File:Line | Accepts | Missing |
|-----------|-----------|---------|---------|
| `_REFERENCE_PATTERN` | `ocr_roles.py:72` | `N. ` / `et al.` / `(Name et al., YYYY)` | `(N) ` |
| `_ref_number_sort_key` | `ocr_render.py:488` | `N.` / `N)` / `[N]` | `(N)` |
| `has_number_lead` in `score_reference_entry()` | `ocr_reference_signals.py:37` | `[N]` / `N.` / `N)` / bare `N` | `(N)` |

**Corpus impact:** 30/500 papers (6%) use `(N)` format. 9ZIJTI6J alone has 506 `(N)` blocks, of which 496 are misclassified as `backmatter_body`.

### Changes

#### 1a. `_REFERENCE_PATTERN` — `ocr_roles.py:72`

Add `\(\d+\)\s` as the **first** alternative (to avoid collision with parenthetical author-year patterns):

```python
_REFERENCE_PATTERN = re.compile(
    r"^\s*(?:\(\d+\)\s|\d+\.\s|[A-Z][A-Za-z'’\-]+\s+et al\.\s*\(\d{4}[a-z]?\)|\([A-Z][A-Za-z'’\-]+\s+et al\.,\s*\d{4}[a-z]?\))",
)
```

**Length guard:** NOT inside `_REFERENCE_PATTERN` itself. Place in `assign_block_role()` around line 1361-1369 where `_looks_like_reference` is consumed:

```python
_PAREN_REF_PREFIX = re.compile(r"^\s*\(\d+\)\s*")

# text with reference-like pattern
if _looks_like_reference(text):
    first_word = text.strip().split(",")[0].strip().lower()
    if first_word not in _BODY_ORDINAL_OPENINGS:
        # Length guard: (N) prefix with very short body → likely a heading, not a ref
        stripped = _PAREN_REF_PREFIX.sub("", text).strip()
        if text.lstrip().startswith("(") and len(stripped) < 25:
            pass  # skip — short (N) text is not a reference item
        else:
            return RoleAssignment(
                role="reference_item",
                confidence=0.6,
                evidence=[f"reference-like pattern: {text[:60]}"],
            )
```

#### 1b. `_ref_number_sort_key` — `ocr_render.py:488`

```python
m = re.match(r"^\s*(?:(\d+)[\.\)]|\[(\d+)\]|\((\d+)\))", text)
```

Return value captures third group:

```python
if m:
    num = m.group(1) or m.group(2) or m.group(3)
    return (0, int(num))
return (1, text)
```

#### 1c. `has_number_lead` — `ocr_reference_signals.py:37`

**⚠️ IMPORTANT: do NOT use `\\d` in raw string — that matches literal `\d`, not digits.**

Current broken spelling is conceptual only — actual code may be fine. Verify in source first. The correct regex:

```python
has_number_lead = bool(
    re.match(r"^\s*(\(\d+\)|\[\d+\]|\d+[\.)]?)(\s+|$)", text)
)
```

### Acceptance

- Among blocks matching `(N)` prefix + author/volume/journal signals and inside detected reference/tail zone, ≥95% become `reference_item`.
- No body-zone short headings like "(1) Introduction" become `reference_item`.
- Sort order: `(1)` before `(2)` before `(3)` in emit.

---

## Track 2a: Reference Heading Variant Expansion

**Files:** `ocr_roles.py` (not `_detect_reference_zones`)
**Status: EXECUTABLE** — location identified, helper contract defined

### Root Cause

Role assignment fails to classify "References and Notes", "Bibliography", "Cited References" as `reference_heading`. These headings end up as `subsection_heading` or other roles, causing `reference_zone.status = HOLD` and blocking reference section assembly.

**KUR9PBJC:** "References and Notes" classified as `subsection_heading` in `body_zone`. The fulltext shows `### References and Notes` at wrong heading level, and 4 refs are missing.

### Changes

**Do NOT modify `_detect_reference_zones()`.** That function consumes existing `reference_heading` roles; it doesn't assign them.

Add a new helper and integrate into `assign_block_role()`:

```python
_REFERENCE_HEADING_PATTERN = re.compile(
    r"^(?:"
    r"references?"
    r"|references?\s+and\s+(?:notes?|further\s+reading)"
    r"|bibliography"
    r"|cited\s+references?"
    r")$",
    re.IGNORECASE,
)

def _normalize_heading_text(text: str) -> str:
    """Strip leader dots, trailing page numbers, and trailing colon.
    
    'References ..... 42' → 'References'
    'References:' → 'References'
    'References and Notes ..... 3054' → 'References and Notes'
    """
    text = text.strip().rstrip(":")
    text = re.sub(r"\.{2,}\s*\d+\s*$", "", text)
    text = re.sub(r"\s+\d+\s*$", "", text)
    return text.strip()


def _is_reference_heading_text(text: str) -> bool:
    """Check if text represents a reference section heading.
    Uses fullmatch to prevent false positives like 'References in this article'.
    """
    return bool(_REFERENCE_HEADING_PATTERN.fullmatch(_normalize_heading_text(text)))
```

Then in `assign_block_role()`, add a check for heading-like blocks (raw_label in `{"paragraph_title", "section_heading", "subsection_heading"}` or short text blocks near zone boundary) before they get assigned a final role:

```python
# Check for reference heading text before heading role assignment
heading_text = text.strip()
if _is_reference_heading_text(heading_text):
    return RoleAssignment(
        role="reference_heading",
        confidence=0.85,
        evidence=[f"reference heading text match: {heading_text[:60]}"],
    )
```

Place this early enough in `assign_block_role()` that it runs before the generic heading → `section_heading` / `subsection_heading` assignment. The exact insertion point depends on the function structure — search for the point where `paragraph_title` raw_label is processed and add the reference_heading check before it.

### Verification

```python
@pytest.mark.parametrize("text", [
    "References",
    "Reference",
    "REFERENCES",
    "References and Notes",
    "References and Notes ..... 42",
    "Bibliography",
    "Cited References",
])
def test_reference_heading_variants(text):
    assert _is_reference_heading_text(text)

@pytest.mark.parametrize("text", [
    "References in this article",
    "Reference values",
    "Further reading",
    "References and results",
])
def test_reference_heading_variants_rejects_non_headings(text):
    assert not _is_reference_heading_text(text)
```

Paper rebuild:
```bash
python scripts/dev/ocr_rebuild_paper.py KUR9PBJC
# Check: "References and Notes" role is reference_heading
# Check: fulltext has proper ## References section
```

---

## Track 3: Cross-Page Reference Partition Consistency (WNDJX4KB)

**Files:** `ocr_document.py` (`_normalize_reference_roles_from_partition`)
**Status: EXECUTABLE** — root cause confirmed via trace evidence

### Root Cause

Trace evidence from WNDJX4KB blocks 1-6 (page 8, heading page) vs 7-26 (page 9+):

| Field | Blocks 1-6 (page 8) | Blocks 7-26 (page 9+) |
|-------|--------------------|----------------------|
| `raw_label` | `reference_content` | `reference_content` |
| `seed_role` | `reference_item` | `reference_item` |
| `style_family` | `reference_like` | `reference_like` |
| `zone` | `reference_zone` | `reference_zone` |
| **Final role** | **`body_paragraph`** | **`reference_item`** |

ALL blocks have evidence `["reference content label: ..."]` — set by `assign_block_role()`. No evidence from `resolve_final_role()`, meaning it returned the same role. The demotion happens in **`_normalize_reference_roles_from_partition()`** which runs after role resolution.

`_normalize_reference_roles_from_partition()` demotes `reference_item` blocks that are NOT in the reference partition. Page 8 blocks (same page as "References" heading) are excluded from the partition because the partition starts tracking from the page AFTER the heading page.

### Fix Contract

In `_normalize_reference_roles_from_partition()`, add a guard that preserves blocks the OCR explicitly identified as reference content, even when the automated partition boundary misses them:

```python
# Before demoting a reference_item block outside the partition:
seed = str(block.get("seed_role") or "")
raw = str(block.get("raw_label") or block.get("block_label") or "")
block_zone = str(block.get("zone") or "")

if (seed == "reference_item" and "reference" in block_zone) or \
   (raw == "reference_content" and "reference" in block_zone):
    continue  # skip demotion, keep as reference_item
```

This is safer than fixing the partition algorithm itself (which may have other edge cases). The guard only triggers when BOTH the OCR label and zone alignment agree it's a reference block.

### Verification

```bash
python scripts/dev/ocr_rebuild_paper.py WNDJX4KB
# Check: blocks 1-6 on page 8 have role=reference_item (not body_paragraph)
```

---

## Track 4: Wiley Heading Missing — OCR Limitation

**Files:** None
**Status: LIMITATION** — no pipeline fix possible

### Root Cause (Confirmed)

Trace evidence from `97M7HFCD` and `2HEUD5P9`:
- `references_start` page has body subsections, publisher watermarks, running headers
- **NO block in the entire paper contains "References", "REFERENCES", or any variant**
- `reference_zone.status=HOLD`, `heading_block_id=None`
- Pipeline set `references_start` based on first `reference_item` block page (not heading)

The "References" heading is not present in the PaddleOCR text output. It's either:
1. Embedded in a graphical element (PDF vector text skipped by OCR)
2. Merged with running header / noise at the header zone
3. Rendered in a font variant that PaddleOCR classifies as `header_image`

**No pipeline fix:** The text simply isn't in the block layer. Synthetic heading is unsafe because `references_start` page still contains body content and the `reference_item` blocks on that page are fake (article tracking numbers like "2409400").

### Design Constraint

If a future investigation determines the heading IS extractable, do NOT add synthetic heading generation unless ALL of:
- Dense `reference_item` block run exists in `reference_zone`
- Block run starts after body end (last `body_paragraph` y-position < first ref y-position)
- No competing `backmatter_heading` before the ref run

---

## Track 5a: Reference Rendering Preservation (U746UJ7G — Already Fixed)

**Files:** `ocr_render.py` (`_reorder_tail_run` emit path)
**Status: DIAGNOSTIC** — U746UJ7G no longer has the issue

### Root Cause (Historical)

Prior trace evidence showed refs 40, 41, 43 missing from fulltext in U746UJ7G.
**Rebuild after P0-P4 + layout robustness commits confirms all 46 refs are
present.** No numbering collision currently exists. The paper was fixed
by earlier pipeline improvements.

### Fix Contract

**Do NOT dedup by ref number.** Different refs sharing a number is an OCR
numbering error, not content duplication. Dropping by number loses valid refs.

Add a **preservation invariant test** that verifies all `reference_item` blocks
in input appear in output, plus **collision logging** for diagnostics only.

=== CRITICAL: Insertion Position ===
The collision/logging code MUST be placed in `_reorder_tail_run()` between
`ref_section["bodies"].sort(key=_ref_number_sort_key)` and
`result.extend(ref_section["bodies"])`. If placed after extend, the
modifications have no effect on output.

Collision logging code (after sort, before extend):

```python
# Collision diagnostic: log duplicate ref numbers.
# Do NOT drop by number — different refs sharing a number is an OCR
# numbering error, not duplicate content. Dropping loses valid refs.
seen_numbers: set[int] = set()
for block in ref_section["bodies"]:
    key = _ref_number_sort_key(block)
    if key[0] == 0:
        num = key[1]
        if num in seen_numbers:
            import logging
            logging.warning(
                f"Duplicate ref number {num}: "
                f"'{str(block.get('text',''))[:60]}'"
            )
        seen_numbers.add(num)
```

**No exact-text dedup either.** Commit 4 is diagnostic only. If exact-text
dedup is ever needed, it must be a separate future change with its own tests.

### Verification

```bash
pytest tests/test_ocr_render.py::test_reorder_tail_run_preserves_all_reference_items \
       tests/test_ocr_render.py::test_reorder_tail_run_preserves_duplicate_numbered_refs -v
python scripts/dev/ocr_rebuild_paper.py U746UJ7G
python -c "import re; t=open(r'D:/L/OB/Literature-hub/System/PaperForge/ocr/U746UJ7G/fulltext.md',encoding='utf-8').read(); print(all(re.search(rf'^{n}\. ',t,re.MULTILINE) for n in [40,41,42,43]))"
```

Expected: True (all refs already present before this change).

## Track 5b: 4AG67PBH Bio Post-Reference Split (Conditional)

**Status: CONDITIONAL** — re-test after Tracks 2a and 3

Track 2a (heading variants) and Track 3 (partition consistency) may fix this. But it is **NOT guaranteed** — even with a reference heading and correct partition, post-reference backmatter boundary still needs to know where refs end and bios begin.

### Post-Track-2a+3 Re-test

```bash
python scripts/dev/ocr_rebuild_paper.py 4AG67PBH
```

Check:
- Are bio blocks still in `reference_zone`?
- Is there a `backmatter_heading` or `backmatter_boundary_heading` separating bios from refs?

If bios remain in `reference_zone`: add a post-reference backmatter split rule that triggers when `backmatter_body` blocks appear in `reference_zone` after a dense `reference_item` run.

---

---

## Execution Plan

### Commit 1: `(N)` reference support

**Files:** `ocr_roles.py`, `ocr_render.py`, `ocr_reference_signals.py`, `ocr_document.py`, `tests/`

1. `_REFERENCE_PATTERN`: add `\(\d+\)\s` alternative
2. `assign_block_role()`: add length guard for `(N)` short text
3. `_ref_number_sort_key`: add `\((\d+)\)` capture
4. `has_number_lead`: add `\(\d+\)` alternative (NOT `\\d+`)
5. `_check_reference_completeness()`: add `\(\d+\)` extraction at line 3237
6. Add `assign_block_role("(1) Introduction") != reference_item` test

### Commit 2: Reference heading variants

**Files:** `ocr_roles.py`, `tests/`
**Rebase on:** Commit 1 (same file `ocr_roles.py`)

1. Add `_is_reference_heading_text()` using `fullmatch()` (not `match()` + `\b`)
2. Add `rstrip(":")` in `_normalize_heading_text()`
3. Integrate into `assign_block_role()` before generic heading assignment
4. Tests: 7 valid variants + 4 false positives; remove unrelated `_PAREN_REF_PREFIX` import

### Commit 3: Cross-page partition demotion guard

**Files:** `ocr_document.py`, `tests/`
**Independent of:** Commits 1, 2 (different file)

1. In `_normalize_reference_roles_from_partition()`, add guard: skip demotion if `seed_role == "reference_item"` + `"reference"` in zone
2. Test must construct a real "outside partition + reference_zone" case — no TODO/pass
3. WNDJX4KB rebuild verification

### Commit 4: Reference rendering preservation + collision logging

**Files:** `ocr_render.py`, `tests/`
**Depends on:** Commit 1 (`_ref_number_sort_key` update)

1. Add preservation invariant test: ALL reference_item blocks in → out (including duplicates)
2. Add collision logging: log duplicate ref numbers, do NOT skip/drop them
3. Allow only exact-duplicate text dedup (same block text)
4. U746UJ7G rebuild verification — if still missing, trace deeper in render pipeline (not `_reorder_tail_run`)

### Conditional: 4AG67PBH bio split (RE-TEST AFTER COMMITS 2+3)

No code yet. Re-test after heading variants + partition fix.

### No fix: Track 4 (Wiley heading)

Heading text not in OCR output. Documented as limitation.

---
## Test Plan

### Track 1 tests (Commit 1)

| Test | File | What |
|------|------|------|
| `test_reference_pattern_matches_short_paren_heading_pattern_only` | `test_ocr_roles.py` | `_looks_like_reference` matches `(N)` pattern |
| `test_assign_block_role_rejects_short_paren_heading` | `test_ocr_roles.py` | `(1) Introduction` → NOT reference_item |
| `test_ref_number_sort_key_paren_format` | `test_ocr_render.py` | `(5)` → sort key (0,5) |
| `test_score_reference_entry_paren_format` | `test_ocr_document.py` | signal detects `(N)` as numbered |

### Track 2a tests (Commit 2)

| Test | File | What |
|------|------|------|
| `test_reference_heading_variants` (parametrized) | `test_ocr_roles.py` | 7 valid variants match |
| `test_reference_heading_variants_rejects_body_phrase` (parametrized) | `test_ocr_roles.py` | 4 false positives rejected |

### Track 3 tests (Commit 3)

| Test | File | What |
|------|------|------|
| `test_normalize_reference_roles_preserves_reference_content_in_zone` | `test_ocr_document.py` | seed_role=reference_item + ref zone → not demoted; _decision_log has partition_fallback |

### Track 5a tests (Commit 4)

| Test | File | What |
|------|------|------|
| `test_reorder_tail_run_preserves_duplicate_numbered_refs` | `test_ocr_render.py` | duplicate ref numbers with different text → both survive, collision logged |
| `test_reorder_tail_run_preserves_all_reference_items` | `test_ocr_render.py` | All ref items in → all ref items out |

### Paper rebuild assertions (manual)

| Paper | After commit | Assertion |
|-------|-------------|-----------|
| 9ZIJTI6J | Commit 1 | ≥95% `(N)` blocks = reference_item |
| KUR9PBJC | Commit 2 | "References and Notes" = reference_heading |
| WNDJX4KB | Commit 3 | blocks 1-6 on page 8 = reference_item |
| U746UJ7G | Commit 4 | refs 40, 41, 43 in fulltext |
| 4AG67PBH | Conditional | post-track-2+3: bios not in reference_zone |

All existing tests must continue to pass after each commit.
