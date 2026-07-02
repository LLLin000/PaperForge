# Reference Detection Fix — Implementation Plan

> **For agentic workers:** Four commits (sequential: 1 → 2/3/4 parallel or interleaved).
>
> **Prerequisite:** Spec at `docs/superpowers/specs/2026-07-02-reference-detection-fix-spec.md`

**Goal:** Fix 5 reference-detection problems discovered in corpus audit (500 papers):
1. `(N)` parenthetical ref format not recognized (6% corpus) — **Commit 1**
2. Reference heading variants not detected ("References and Notes") — **Commit 2**
3. Cross-page ref role inconsistency (WNDJX4KB) — **Commit 3**
4. Wiley "References" heading absent from OCR — **No fix (OCR limitation)**
5. Rendering preservation — **Commit 4 (diagnostic, U746UJ7G already fixed by prior work)**

**Architecture:** Commit 1 modifies 4 core files + tests. Commits 2/3/4 each modify one source file + its test; they can run in parallel after Commit 1.

**Tech Stack:** Python 3.x, PaperForge OCR worker modules, pytest, no new runtime dependencies.

---

## Commit 1: `(N)` Parenthetical Reference Support

**Files:**
- Modify: `paperforge/worker/ocr_roles.py`
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `paperforge/worker/ocr_reference_signals.py`
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `tests/test_ocr_roles.py`
- Modify: `tests/test_ocr_render.py`
- Modify: `tests/test_ocr_document.py`
### Step 1: Read the current regex patterns

Read these lines to confirm exact current code:
- `paperforge/worker/ocr_roles.py` line 72 (`_REFERENCE_PATTERN`)
- `paperforge/worker/ocr_roles.py` lines 1361-1369 (`_looks_like_reference` usage + `_BODY_ORDINAL_OPENINGS` guard)
- `paperforge/worker/ocr_render.py` line 488 (`_ref_number_sort_key`)
- `paperforge/worker/ocr_reference_signals.py` line 37 (`has_number_lead`)

### Step 2: Write failing tests first

Add to `tests/test_ocr_roles.py`:

_PAREN_REF_TEXT = "(1) Li, T.; Shi, C.; Jin, F.; Yang, F.; Gu, L.; Wang, T.; Dong, W.; Feng, Z.-Q. Cell Activity Modulation and Its Specific Function in Load Bearing."
_SHORT_PAREN_HEADING = "(1) Introduction"

def test_reference_pattern_accepts_long_paren_reference() -> None:
    from paperforge.worker.ocr_roles import _looks_like_reference
    assert _looks_like_reference(_PAREN_REF_TEXT) is True

def test_reference_pattern_matches_short_paren_heading_pattern_only() -> None:
    from paperforge.worker.ocr_roles import _looks_like_reference
    # _looks_like_reference uses _REFERENCE_PATTERN which matches (N)
    # regardless of length. Length guard is in assign_block_role, not here.
    assert _looks_like_reference(_SHORT_PAREN_HEADING) is True


def test_assign_block_role_rejects_short_paren_heading() -> None:
    from paperforge.worker.ocr_roles import assign_block_role
    block = {
        "raw_label": "text",
        "text": "(1) Introduction",
        "page": 3,
        "bbox": [100, 100, 300, 130],
        "page_width": 1200,
        "page_height": 1600,
    }
    role = assign_block_role(block, page_blocks=[block]).role
    assert role != "reference_item", f"Expected not reference_item, got {role}"
```

Add to `tests/test_ocr_document.py`:

```python
def test_score_reference_entry_has_number_lead_paren() -> None:
    from paperforge.worker.ocr_reference_signals import score_reference_entry

    result = score_reference_entry(
        "(1) Smith AB, Jones CD. Journal Name. 2020;10(3):100-10."
    )

    assert result["signals"].get("number_lead") is True
    assert result["family"] == "vancouver_structured_numbered"


def test_reference_completeness_accepts_parenthetical_numbers() -> None:
    from paperforge.worker.ocr_document import _check_reference_completeness

    blocks = [
        {"role": "reference_item", "zone": "reference_zone", "text": "(1) A."},
        {"role": "reference_item", "zone": "reference_zone", "text": "(2) B."},
        {"role": "reference_item", "zone": "reference_zone", "text": "(3) C."},
    ]

    result = _check_reference_completeness(blocks)

    assert result["status"] == "OK"
    assert result["expected_count"] == 3
    assert result["missing_numbers"] == []
```

Add to `tests/test_ocr_render.py`:

```python
def test_ref_number_sort_key_paren_format() -> None:
    from paperforge.worker.ocr_render import _ref_number_sort_key
    block = {"text": "(5) Smith J. Journal Name. 2020."}
    key = _ref_number_sort_key(block)
    assert key == (0, 5), f"Expected (0, 5), got {key}"

def test_ref_number_sort_key_paren_handles_mixed_formats() -> None:
    from paperforge.worker.ocr_render import _ref_number_sort_key
    assert _ref_number_sort_key({"text": "(5) ..."}) == (0, 5)
    assert _ref_number_sort_key({"text": "5. ..."}) == (0, 5)
    assert _ref_number_sort_key({"text": "[5] ..."}) == (0, 5)
```
### Step 3: Run the tests — expect failures

```bash
pytest tests/test_ocr_roles.py::test_reference_pattern_accepts_long_paren_reference \
       tests/test_ocr_roles.py::test_reference_pattern_matches_short_paren_heading_pattern_only \
       tests/test_ocr_roles.py::test_assign_block_role_rejects_short_paren_heading \
       tests/test_ocr_render.py::test_ref_number_sort_key_paren_format \
       tests/test_ocr_render.py::test_ref_number_sort_key_paren_handles_mixed_formats \
       tests/test_ocr_document.py::test_score_reference_entry_has_number_lead_paren \
       tests/test_ocr_document.py::test_reference_completeness_accepts_parenthetical_numbers -v
```

### Step 4: Implement `_REFERENCE_PATTERN` fix

In `paperforge/worker/ocr_roles.py`, find `_REFERENCE_PATTERN` (around line 72). Add `\(\d+\)\s` as the first alternative:

```python
_REFERENCE_PATTERN = re.compile(
    r"^\s*(?:\(\d+\)\s|\d+\.\s|[A-Z][A-Za-z'’\-]+\s+et al\.\s*\(\d{4}[a-z]?\)|\([A-Z][A-Za-z'’\-]+\s+et al\.,\s*\d{4}[a-z]?\))",
)
```

### Step 5: Add length guard in `assign_block_role()`

Find the `_looks_like_reference` usage around line 1361-1369. Insert the `_PAREN_REF_PREFIX` compile before the function (top of file or local) and add the length guard:

Add at module level (with other pattern compiles):
```python
_PAREN_REF_PREFIX = re.compile(r"^\s*\(\d+\)\s*")
```

Modify the guard block (around line 1362-1368):
```python
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

### Step 6: Implement `_ref_number_sort_key` fix

In `paperforge/worker/ocr_render.py`, find `_ref_number_sort_key` (around line 488). Change the regex and return:

```python
def _ref_number_sort_key(block: dict) -> tuple:
    text = str(block.get("text") or block.get("block_content") or "")
    m = re.match(r"^\s*(?:(\d+)[\.\)]|\[(\d+)\]|\((\d+)\))", text)
    if m:
        num = m.group(1) or m.group(2) or m.group(3)
        return (0, int(num))
    return (1, text)
```

### Step 7: Implement `has_number_lead` fix

In `paperforge/worker/ocr_reference_signals.py`, find `has_number_lead` (around line 37). Change:

```python
has_number_lead = bool(
    re.match(r"^\s*(\(\d+\)|\[\d+\]|\d+[\.)]?)(\s+|$)", text)
)
```

Also expose it in the return dict so the test can check it directly. Look for the return dict and add if absent:

```python
return {
    "family": family,
    "confidence": confidence,
    "signals": {
        "author_signature": has_author_signature,
        "year_signature": has_year,
        "volume_issue_pages_signature": has_vol_pages,
        "online_marker_signature": has_online,
        "journal_lexicon_match": journal_match,
        "number_lead": has_number_lead,
    },
}
```

### Step 7.5: Implement `_check_reference_completeness` fix

Find `_check_reference_completeness()` in `paperforge/worker/ocr_document.py` at line 3221.
Add parenthetical pattern BEFORE the bracket pattern at line 3237:

```python
text = (block.get("text") or "").strip()
# Try parenthetical pattern: (1)
m = _re.match(r"^\s*\((\d+)\)", text)
if m:
    numbers.append(int(m.group(1)))
    continue
# Try bracket pattern: [1]
m = _re.match(r"^\s*\[(\d+)\]", text)  # existing, unchanged
...
```

This prevents completeness false positives for `(N)` format papers.


### Step 8: Run tests — expect pass

```bash
pytest tests/test_ocr_roles.py::test_reference_pattern_accepts_long_paren_reference \
       tests/test_ocr_roles.py::test_reference_pattern_matches_short_paren_heading_pattern_only \
       tests/test_ocr_roles.py::test_assign_block_role_rejects_short_paren_heading \
       tests/test_ocr_render.py::test_ref_number_sort_key_paren_format \
       tests/test_ocr_render.py::test_ref_number_sort_key_paren_handles_mixed_formats \
       tests/test_ocr_document.py::test_score_reference_entry_has_number_lead_paren -v
```

Expected: 6 passed.

### Step 9: Run full existing test suite

```bash
pytest tests/test_ocr_roles.py tests/test_ocr_render.py tests/test_ocr_document.py tests/test_ocr_families.py -q
```

Expected: all existing tests still pass (count unchanged for unrelated files).
### Step 10: Commit

```bash
git add paperforge/worker/ocr_roles.py paperforge/worker/ocr_render.py paperforge/worker/ocr_reference_signals.py paperforge/worker/ocr_document.py tests/test_ocr_roles.py tests/test_ocr_render.py tests/test_ocr_document.py
git commit -m "fix: support parenthetical (N) reference number format

Add (N) prefix to 4 regex locations:
- _REFERENCE_PATTERN: recognize (1) as reference start
- _ref_number_sort_key: extract number from (N) for sort
- has_number_lead in score_reference_entry: detect (N) as numbered ref
- _check_reference_completeness: count (N) refs in completeness check

Add length guard in assign_block_role: (N) prefix + text < 25 chars
is rejected (prevents '(1) Introduction' false positive).
Corpus: 30/500 papers use (N) format, previously all misclassified."
```

---

## Commit 2: Reference Heading Variant Expansion

**Files:**
- Modify: `paperforge/worker/ocr_roles.py`
- Modify: `tests/test_ocr_roles.py`

### Step 1: Read the current heading assignment code

Read `paperforge/worker/ocr_roles.py` and find:
- Where `paragraph_title` raw_label is processed and assigned to `section_heading` / `subsection_heading`
- The entry point for `assign_block_role` (the function that reads `raw_label` and returns a `RoleAssignment`)

### Step 2: Add the heading detection helper

Add to `paperforge/worker/ocr_roles.py` (near the top with other pattern compiles, or just before `assign_block_role`):

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

### Step 3: Integrate into `assign_block_role()`

Find the point in `assign_block_role()` where heading-like blocks (`raw_label == "paragraph_title"` or similar) are about to be assigned a generic heading role. Insert BEFORE that assignment:

```python
    # Reference heading detection — must run before generic heading assignment
    heading_text = text.strip()
    if _is_reference_heading_text(heading_text):
        return RoleAssignment(
            role="reference_heading",
            confidence=0.85,
            evidence=[f"reference heading text match: {heading_text[:60]}"],
        )
```

The exact insertion point depends on the function structure. Search for where `paragraph_title` raw_label is handled and add the check before the standard heading role assignment.

### Step 4: Write tests

Add to `tests/test_ocr_roles.py`:

```python
import pytest


@pytest.mark.parametrize("text", [
    "References",
    "Reference",
    "REFERENCES",
    "References and Notes",
    "References and Notes ..... 42",
    "Bibliography",
    "Cited References",
])
def test_reference_heading_variants(text: str) -> None:
    from paperforge.worker.ocr_roles import _is_reference_heading_text
    assert _is_reference_heading_text(text), f"Expected match: {text!r}"


@pytest.mark.parametrize("text", [
    "References in this article",
    "Reference values",
    "Further reading",
    "References and results",
])
## Commit 3: Preserve heading-page reference_content after partition fallback (WNDJX4KB)

**Files:**
- Modify: `paperforge/worker/ocr_document.py` (post-partition guard in `normalize_document_structure`)
- Modify: `tests/test_ocr_document.py`

**Status: EXECUTABLE** — root cause confirmed. Test must verify _decision_log.

### Root Cause (Trace-Confirmed)

1. `_partition_by_reference_zone` excludes heading-page refs from the partition.
2. `_clear_partition_zones` + `_apply_zone_labels` then strip their `reference_zone` label.
3. Final role falls to `body_paragraph` because no partition override applies.

The fix is NOT in `_normalize_reference_roles_from_partition` (that only promotes IN-partition blocks). It's a post-partition fallback in `normalize_document_structure`.

### Step 1: Read the partition boundary logic

Read `_partition_by_reference_zone` in `ocr_document.py` to understand how heading-page blocks get excluded. Read `normalize_document_structure` to find the right insertion point: after `_normalize_reference_roles_from_partition` returns, before `_clear_partition_zones`.

### Step 2: Write integration test that would fail without the fix

The test must prove the fix actually fires — not just assert correct roles on hand-crafted blocks.

Add to `tests/test_ocr_document.py`:

```python
def test_normalize_document_structure_preserves_heading_page_reference_items() -> None:
    """Heading-page reference_item blocks excluded from partition must be
    restored by fallback guard. Verifies _decision_log for partition_fallback."""
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {"page": 1, "role": "reference_heading", "raw_label": "paragraph_title",
         "text": "References", "bbox": [100, 100, 200, 120],
         "page_width": 1200, "page_height": 1600, "block_id": "h1"},
        {"page": 1, "role": "reference_item", "seed_role": "reference_item",
         "raw_label": "reference_content",
         "text": "1. Author A. Journal. 2020.",
         "bbox": [100, 130, 500, 150],
         "page_width": 1200, "page_height": 1600, "block_id": "r1"},
        {"page": 2, "role": "reference_item", "seed_role": "reference_item",
         "raw_label": "reference_content",
         "text": "2. Author B. Journal. 2021.",
         "bbox": [100, 130, 500, 150],
         "page_width": 1200, "page_height": 1600, "block_id": "r2"},
    ]

    doc, normalized = normalize_document_structure(blocks)

    for b in normalized:
        if b.get("block_id") in ("r1", "r2"):
            assert b.get("role") == "reference_item", \
                f"Block {b['block_id']} demoted to {b.get('role')}"
            dl = b.get("_decision_log", [])
            fallback_entries = [
                d for d in (dl if isinstance(dl, list) else [])
                if isinstance(d, dict) and d.get("stage") == "partition_fallback"
            ]
            assert any(
                d.get("stage") == "partition_fallback"
                for d in (dl if isinstance(dl, list) else [])
                if isinstance(d, dict)
            ), f"Block {b['block_id']} did not trigger partition_fallback — test would pass without fix"
```

### Step 3: Add post-partition fallback guard in `normalize_document_structure()`

Insert AFTER `_normalize_reference_roles_from_partition(temp_blocks, all_blocks)` returns and BEFORE `_clear_partition_zones(temp_blocks)`:

```python
# Post-partition fallback: restore reference_item for blocks that OCR
# explicitly identified as reference content but were excluded from the
# reference partition boundary (WNDJX4KB pattern — heading-page refs).
for block in temp_blocks:
    zone = str(block.get("zone") or "")
    seed = str(block.get("seed_role") or "")
    raw = str(block.get("raw_label") or block.get("block_label") or "")
    if block.get("role") == "body_paragraph" and "reference" in zone:
        if seed == "reference_item" or raw == "reference_content":
            block["role"] = "reference_item"
            _record_decision(
                block,
                stage="partition_fallback",
                old_role="body_paragraph",
                new_role="reference_item",
                reason="reference_content block outside partition, restored from seed_role",
            )
```

Search for `_record_decision` or `record_decision` in the file to get the exact function name.

### Step 4: Verify

```bash
pytest tests/test_ocr_document.py::test_normalize_document_structure_preserves_heading_page_reference_items -v
python scripts/dev/ocr_rebuild_paper.py WNDJX4KB
# Check blocks 1-6 have role=reference_item AND partition_fallback log
python -c "
import json, re
with open('D:/L/OB/Literature-hub/System/PaperForge/ocr/WNDJX4KB/structure/blocks.structured.jsonl', encoding='utf-8') as f:
    blocks = [json.loads(l) for l in f if l.strip()]
for b in blocks:
    t = str(b.get('text','') or b.get('block_content',''))
    m = re.match(r'^\s*([1-6])[.\)]\s', t)
    if m:
        dl = b.get('_decision_log', [])
        has_fb = any(d.get('stage') == 'partition_fallback' for d in (dl if isinstance(dl, list) else []) if isinstance(d, dict))
        print(f'Ref {m.group(1)}: role={b.get(\"role\")} fallback={has_fb}')
"
```

### Step 5: Run full suite

```bash
pytest tests/test_ocr_document.py tests/test_ocr_render.py tests/test_ocr_families.py -q
```

### Step 6: Commit

```bash
git add paperforge/worker/ocr_document.py tests/test_ocr_document.py
git commit -m "fix: preserve heading-page reference_content after partition fallback

Reference partition can exclude reference_content blocks on the same page
as the reference heading. After partition normalization, restore blocks
whose seed_role/raw_label and zone still identify them as reference items.
Fixes WNDJX4KB refs 1-6 demoted to body_paragraph."
```

## Commit 4: Reference Rendering Preservation + Collision Logging (Diagnostic)

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `tests/test_ocr_render.py`

**Type: DIAGNOSTIC** — does not fix U746UJ7G (refs already rendered correctly since P0-P4 layout work).
Just add safety net: preservation invariant + duplicate-number collision logging.

**Depends on:** Commit 1 (`_ref_number_sort_key` update)

### Root Cause

U746UJ7G **no longer has a problem** — rebuild after P0-P4 + layout robustness commits shows
all 46 refs (40, 41, 43 included) are present in both structured blocks and fulltext.
No numbering collision found.

Commit 4 exists only as a diagnostic safety net: if future papers have duplicate-numbered refs,
we log the collision and check preservation invariants.

=== CRITICAL: Insertion Position ===
The dedup/collision code MUST go between sort and extend:

```python
if ref_section.get("bodies"):
    ref_section["bodies"].sort(key=_ref_number_sort_key)
    # ← COLLISION LOGGING GOES HERE (after sort, before extend)
    result.extend(ref_section["bodies"])
```

If placed after `result.extend(ref_section["bodies"])`, the modification to `ref_section["bodies"]`
does NOT affect the output — it's already been emitted.

### Step 1: Add preservation invariant tests

Add to `tests/test_ocr_render.py`:

```python
def test_reorder_tail_run_preserves_all_reference_items() -> None:
    from paperforge.worker.ocr_render import _reorder_tail_run

    ref_heading = {"role": "reference_heading", "text": "References", "bbox": [100, 100, 200, 120]}
    refs = [
        {"role": "reference_item", "text": f"{i}. Entry {i}.", "bbox": [100, 120 + i * 20, 500, 140 + i * 20]}
        for i in range(1, 6)
    ]
    tail_blocks = [ref_heading, *refs]

    ordered, _, _ = _reorder_tail_run(tail_blocks, None, None, page_width=1200)

    before = {id(b) for b in tail_blocks if b.get("role") == "reference_item"}
    after = {id(b) for b in ordered if b.get("role") == "reference_item"}
    assert before == after, f"Lost refs: {before - after}"


def test_reorder_tail_run_preserves_duplicate_numbered_refs() -> None:
    """Two different refs with the same number must BOTH survive (no dedup by number)."""
    from paperforge.worker.ocr_render import _reorder_tail_run

    heading = {"role": "reference_heading", "text": "References", "bbox": [100, 100, 200, 120]}
    ref42a = {"role": "reference_item", "text": "42. Rhee C, Wang R...", "bbox": [100, 200, 500, 220]}
    ref42b = {"role": "reference_item", "text": "42. Baghdadi JD, Brook RH...", "bbox": [100, 220, 500, 240]}
    ref43 = {"role": "reference_item", "text": "43. Baghdadi JD, Wong MD...", "bbox": [100, 240, 500, 260]}

    ordered, _, _ = _reorder_tail_run([heading, ref42a, ref42b, ref43], None, None, page_width=1200)

    before = {id(b) for b in [ref42a, ref42b, ref43]}
    after = {id(b) for b in ordered if b.get("role") == "reference_item"}
    assert before == after, f"Lost refs: {before - after}"
```

### Step 2: Add collision logging only (NO exact-text dedup)

In `_reorder_tail_run()`, locate the sort-then-extend block and insert logging between them:

```python
if ref_section.get("bodies"):
    ref_section["bodies"].sort(key=_ref_number_sort_key)

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
                logging.warning(f"Duplicate ref number {num}: '{str(block.get('text',''))[:60]}'")
            seen_numbers.add(num)

    result.extend(ref_section["bodies"])
```

### Step 3: Verify

```bash
pytest tests/test_ocr_render.py::test_reorder_tail_run_preserves_all_reference_items \
       tests/test_ocr_render.py::test_reorder_tail_run_preserves_duplicate_numbered_refs -v
python scripts/dev/ocr_rebuild_paper.py U746UJ7G
python -c "
import re
t = open('D:/L/OB/Literature-hub/System/PaperForge/ocr/U746UJ7G/fulltext.md', encoding='utf-8').read()
for n in [40, 41, 42, 43]:
    found = bool(re.search(rf'^{n}\. ', t, re.MULTILINE))
    print(f'Ref {n}: {\"OK\" if found else \"MISSING\"}')
"
```

### Step 4: Run full suite

```bash
pytest tests/test_ocr_document.py tests/test_ocr_render.py tests/test_ocr_families.py -q
```

### Step 5: Commit

```bash
git add paperforge/worker/ocr_render.py tests/test_ocr_render.py
git commit -m "fix: add reference rendering preservation invariant + collision logging

Add preservation invariant: all reference_item blocks survive rendering
(including duplicate-numbered refs — do NOT dedup by number).
Add collision logging for duplicate ref numbers only (no exact-text dedup).
Diagnostic only: U746UJ7G already fixed by earlier P0-P4 layout work."
```
## No Fix: Track 4 Wiley Heading

**Status: LIMITATION** — 97M7HFCD and 2HEUD5P9 confirmed "References" heading text not in PaddleOCR output. No pipeline code fix.

---

## Conditional: 4AG67PBH Bio Split (Post-Commit-2+3)

Re-test after Commits 2 and 3:

```bash
python scripts/dev/ocr_rebuild_paper.py 4AG67PBH
python -c "
from pathlib import Path
import json
with open(Path('D:/L/OB/Literature-hub/System/PaperForge/ocr/4AG67PBH/structure/blocks.structured.jsonl'), encoding='utf-8') as f:
    blocks = [json.loads(l) for l in f if l.strip()]
bio_in_ref = [
    b for b in blocks
    if 'reference' in str(b.get('zone',''))
    and 'Ph.D.' in str(b.get('text','') or b.get('block_content',''))
]
print(f'Bios still in reference_zone: {len(bio_in_ref)}')
"
```

If > 0: add post-reference backmatter split rule.
If == 0: no further action.

---
## Summary

| # | Type | Description | Depends on |
|---|------|-------------|-----------|
| 1 | **Commit** | `(N)` reference format (4 regex + length guard) | — |
| 2 | **Commit** | Reference heading variants (fullmatch regex) | After 1 (same file) |
| 3 | **Commit** | Preserve heading-page reference_content after partition | After 1 (same file) |
| 4 | **Commit** | Reference rendering preservation + collision logging (Diagnostic) | After 1 (uses _ref_number_sort_key) |
| — | **No fix** | Wiley heading — OCR limitation (Track 4) | — |
| 5 | **Conditional** | 4AG67PBH bio split (re-test after 2+3) | After 2+3 |

**Execution order:** 1 → 2/3/4 can run in parallel after 1 (different files, all depend on 1) → 5.
