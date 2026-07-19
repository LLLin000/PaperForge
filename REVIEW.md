---
phase: code-review
reviewed: 2026-06-18T12:00:00Z
depth: deep
files_reviewed: 10
files_reviewed_list:
  - PROJECT-MANAGEMENT.md
  - audit/coverage_ledger.json
  - paperforge/worker/ocr_blocks.py
  - paperforge/worker/ocr_document.py
  - paperforge/worker/ocr_health.py
  - project/current/ocr-v2-closeout-priority.md
  - project/current/ocr-v2-generalization-boundary.md
  - project/current/ocr-v2-remaining-issues-2026-06-18.md
  - tests/test_ocr_document.py
  - tests/test_ocr_real_paper_regressions.py
findings:
  critical: 2
  warning: 8
  info: 3
  total: 13
status: issues_found
---

# Code Review Report: OCR-v2 Readiness-Gates Implementation

**Reviewed:** 2026-06-18
**Depth:** deep (cross-file analysis with call-chain tracing)
**Files Changed in Range:** 10 files, 619 insertions, 54 deletions
**Status:** issues_found

## Summary

Review of commits `9329843..8fac15e` (6 commits spanning `77b727b` → `8fac15e`).
Claimed status: **Gates 1, 3, 4 done; Gate 2 xfail; Gate 5 docs only.**

**Verdict on status accuracy: PARTIALLY MISLEADING.**

- **Gate 1 claim "DONE" is overstated.** The completeness-signal functions exist as source code AND are unit-tested, but none are wired into the production pipeline. `_summarize_page_text_coverage()` and `_classify_region_text_completeness()` in `ocr_blocks.py` and `audit_rendered_text_coverage()` in `ocr_health.py` are never called from `build_ocr_health()`, `build_structured_blocks()`, or any other production entry point. They are dead code at runtime. A claim of "DONE" implies the pipeline can now detect silent text loss — it cannot, because the detection functions don't run.

- **Gate 3 claim "DONE" is supportable but thinly verified.** The core function `_enforce_reference_boundary_from_structure` is implemented and integrated. However, its single unit test only checks role preservation, not zone assignment or correct boundary stripping. There is also a stale-role state inconsistency in the stripping path.

- **Gate 4 claim "DONE" overstates formalization.** Two of eight audit papers (K7R8PEKW, SAN9AYVR) have `"layout_tags": []` — removed from all tracked layout classes. The contract tests only verify that each tag has at least one representative, not that ALL papers are classified. 25% of the corpus is effectively untracked.

- **Gate 2 xfail:** Claimed accurately. The test exists as `xfail(strict=True)` and documents the known gap.

- **Gate 5 docs only:** Claimed accurately.

---

## Critical Issues

### CR-01: Completeness-signal functions unreachable from pipeline (Gate 1 not production-integrated)

**Files:** `paperforge/worker/ocr_blocks.py:21`, `paperforge/worker/ocr_blocks.py:33`, `paperforge/worker/ocr_health.py:7`
**Evidence:** Cross-file grep for call-sites shows:
- `_summarize_page_text_coverage` — defined in `ocr_blocks.py:21`, called **only** from `tests/test_ocr_document.py`. Zero calls from any `.py` file under `paperforge/`.
- `_classify_region_text_completeness` — defined in `ocr_blocks.py:33`, called **only** from `tests/test_ocr_document.py`. Zero calls from any `.py` file under `paperforge/`.
- `audit_rendered_text_coverage` — defined in `ocr_health.py:7`, called **only** from `tests/test_ocr_document.py`. Not invoked by `build_ocr_health()` (lines 60-323 of `ocr_health.py`). Zero production call-sites.

**Issue:** PROJECT-MANAGEMENT.md section 10.2 states "Added `_summarize_page_text_coverage()` and `_classify_region_text_completeness()` to `ocr_blocks.py`" and "Added `audit_rendered_text_coverage()` to `ocr_health.py`" — and claims Gate 1 "DONE". These functions cannot detect silent text loss because nothing calls them during pipeline execution. The "completeness signals" are unit-testable artifacts, not operational monitors.

**Impact:** A claim of `state healthy` based on Gate 1 completeness signals is false. Silent text loss in OCR output will not be detected.

**Fix:** Wire these functions into the production pipeline, e.g.:
- Call `_summarize_page_text_coverage` and `_classify_region_text_completeness` from `build_ocr_health()` in `ocr_health.py` or from the `build_structured_blocks()` flow in `ocr_blocks.py`.
- Call `audit_rendered_text_coverage` from the render step or from `build_ocr_health()` with rendered markdown and PDF segments.
- Update `build_ocr_health` return dict to include the coverage signals.
- Update PROJECT-MANAGEMENT.md Gate 1 status to "PARTIAL — functions implemented but not integrated" until wiring is complete.

---

### CR-02: `_summarize_page_text_coverage` returns ratio=1.0 when PDF text is missing

**File:** `paperforge/worker/ocr_blocks.py:24-25`
**Issue:** When `pdf_chars == 0` (no PDF text available for comparison), the function returns `"page_text_coverage_ratio_chars": 1.0` — indicating perfect 100% coverage. This is semantically wrong: when there is no baseline to compare against, a downstream consumer reading this field would interpret 1.0 as "all text is covered," masking the absence of PDF text.

```python
if pdf_chars == 0:
    return {"page_text_coverage_status": "missing_pdf_text", "page_text_coverage_ratio_chars": 1.0}
```

**Impact:** If this function is ever wired into the pipeline (see CR-01), silent text loss on pages without a PDF text layer would be invisible — the health report would show 1.0 coverage ratio, not flagging the issue.

**Fix:** Return `None` or `-1.0` for the ratio when `pdf_chars == 0`, or remove the ratio field entirely from this branch. Downstream consumers should check `page_text_coverage_status` first:
```python
if pdf_chars == 0:
    return {"page_text_coverage_status": "missing_pdf_text", "page_text_coverage_ratio_chars": None}
```

---

## Warnings

### WR-01: `_classify_region_text_completeness` has false-positive gap (no content comparison)

**File:** `paperforge/worker/ocr_blocks.py:33-44`
**Issue:** The function compares character counts but never checks content similarity. If OCR text has `>= 45%` of PDF character length but contains completely different text (wrong page recognized, garbage OCR), the function returns `"complete"` with `0.7` confidence. The `pdf.startswith(ocr)` check only catches truncated tails — not semantic mismatch.

**Example:**
- OCR: `"The quick brown fox jumps over the lazy dog."` (44 chars)
- PDF: `"We report a novel method for synthesizing nanoparticles."` (54 chars)
- Ratio: 44/54 = 0.81 → `"page_text_coverage_status": "ok"` in the page function, and `"complete"` in the region function. Both signals say everything is fine. Ground truth: completely different text.

**Impact:** Cannot detect wrong-page or hallucinated OCR content.

**Fix:** Add a content overlap check (character-level n-gram Jaccard similarity or edit distance ratio) before declaring `"complete"`:
```python
# After the length checks, add content overlap
overlap = sum(1 for c in set(ocr) if c in set(pdf))
overlap_ratio = overlap / max(len(set(ocr)), 1)
if overlap_ratio < 0.5:
    return {"text_completeness_status": "content_mismatch", "text_completeness_confidence": 0.6}
```

---

### WR-02: `audit_rendered_text_coverage` uses fragile substring matching

**File:** `paperforge/worker/ocr_health.py:8`
**Issue:** The function checks `segment not in rendered_markdown` using Python's `in` operator — literal substring match, case-sensitive and formatting-sensitive.

```python
missing = [segment for segment in pdf_segments if segment and segment not in rendered_markdown]
```

Rendered markdown often differs from raw PDF segments in:
- Whitespace normalization (extra spaces, line breaks)
- Case changes (markdown formatting may lowercase)
- HTML escaping or unicode normalization

**Example:** PDF segment `"in vivo"` will not match rendered markdown `"in  vivo"` (double space) or `"In Vivo"` (title case).

**Impact:** High false-positive gap rate when wired into production, causing alert fatigue or distrust of the coverage signal.

**Fix:** Normalize both inputs before comparison:
```python
import re
def _normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip().lower()
missing = [s for s in pdf_segments if s and _normalize(s) not in _normalize(rendered_markdown)]
```

---

### WR-03: `_enforce_reference_boundary_from_structure` can leave stale role assignments

**File:** `paperforge/worker/ocr_document.py:2558-2566`
**Issue:** When stripping `zone` from blocks above the reference heading boundary, the function zeroes only the `zone` field but does NOT revert the `role` field. If a block had `role = "reference_item"` from a previous pass but is positioned above the heading, after this function its state is: `zone=""` + `role="reference_item"`. The `record_decision` call also passes `old_role == new_role` (same value), so the decision log won't record any role mutation even though a meaningful structural change (zone strip) occurred.

```python
elif block_bottom < boundary_y and b.get("zone") == "reference_zone":
    b["zone"] = ""
    record_decision(
        b,
        stage="reference_boundary_enforcement",
        old_role=b.get("role", ""),
        new_role=b.get("role", ""),  # same as old_role — no mutation logged
        reason="block above reference heading boundary stripped from reference_zone",
    )
```

**Impact:** Downstream consumers checking `role` will see "reference_item" on a block that should be body content. The decision log records a no-op.

**Fix:** Either revert the role (e.g., set to the seed_role if different) or at minimum log the zone change accurately:
```python
elif block_bottom < boundary_y and b.get("zone") in ("reference_zone", ""):
    old_zone = b.get("zone", "")
    b["zone"] = ""
    # Only log if zone actually changed
    if old_zone != "":
        record_decision(
            b, stage="reference_boundary_enforcement",
            old_role=b.get("role", ""), new_role=b.get("role", ""),
            reason=f"block above reference heading: zone {old_zone} → empty",
        )
```

---

### WR-04: Two audit papers have empty layout tags (Gate 4 corpus incomplete)

**File:** `audit/coverage_ledger.json:9-10`
**Issue:** After the taxonomy migration, K7R8PEKW and SAN9AYVR have empty `layout_tags: []`. Previously they had `["single_column"]` and `["multi_column"]` respectively. Removing these tags means 2 of 8 audit papers (25%) are not tracked against any readiness layout class.

```json
{"paper_key": "K7R8PEKW", "layout_tags": [], "risk_tags": ["frontmatter_sensitive"]},
{"paper_key": "SAN9AYVR", "layout_tags": [], "risk_tags": ["special_structure"]}
```

The contract tests (`test_gold_set_covers_readiness_layout_classes` and `test_layout_class_manifest_has_named_representatives`) only verify that each tag has at least one paper — they do not enforce that every paper has meaningful tags. So these untagged papers pass all contract checks.

**Impact:** Layout-coverage formalization claims are based on a 6-of-8 corpus. K7R8PEKW (frontmatter-sensitive `single_column`) and SAN9AYVR (`special_structure`) are invisible to the coverage model.

**Fix:** Tag these papers with the appropriate readiness-class tags. At minimum:
- K7R8PEKW: was `single_column` previously — if no readiness-class equivalent exists, retain `special_structure` if applicable.
- SAN9AYVR: was `multi_column` previously — consider `side_caption`, `multi_panel`, or `special_structure` as appropriate.

---

### WR-05: `_is_page1_body_start` is dead code

**File:** `paperforge/worker/ocr_document.py:510-525`
**Issue:** The function `_is_page1_body_start` is defined but never called. `infer_zones()` (line 951 of the modified file) now calls `_is_first_page_body_start` instead. The old function remains in the module with no callers.

**Impact:** Dead code adds maintenance burden and confuses readers (which body-start detection is active?). The import-only references in `docs/superpowers/specs/` and `docs/superpowers/plans/` reference the concept, not the function.

**Fix:** Remove `_is_page1_body_start` and its docstring. Update any doc references to point to `_is_first_page_body_start`.

---

### WR-06: Gate 3 boundary test is too weak

**File:** `tests/test_ocr_document.py:4792-4804`
**Issue:** `test_same_page_reference_boundary_is_resolved_upstream_not_in_renderer` only checks that roles are preserved (`body_1` stays `body_paragraph`, `ref_1` stays `reference_item`). It does NOT verify:
- That `ref_1["zone"]` is set to `"reference_zone"` after the enforcement
- That `body_1["zone"]` is NOT `"reference_zone"` (correct boundary)
- That a block above the heading with a pre-existing reference_zone assignment gets stripped

```python
assert by_id["body_1"]["role"] == "body_paragraph"
assert by_id["ref_1"]["role"] == "reference_item"
# Missing zone assertions!
```

**Impact:** The enforcement function could silently assign wrong zones and this test would still pass.

**Fix:** Add zone assertions:
```python
assert by_id["body_1"].get("zone") != "reference_zone"
assert by_id["ref_1"].get("zone") == "reference_zone"
```

---

### WR-07: `_enforce_reference_boundary_from_structure` misses detected but un-assigned reference headings

**File:** `paperforge/worker/ocr_document.py:2533-2537, 2540-2566`
**Issue:** `_same_page_reference_boundary_y` matches only blocks where `seed_role == "reference_heading"`. But reference headings can be detected by `_is_reference_heading_candidate` (which checks marker_signature type and canonical section text) without having `seed_role` set to `"reference_heading"` yet (role resolution happens later in the pipeline). If a heading's seed_role is still `"section_heading"` or `"unassigned"`, this function won't see it, and the boundary enforcement is skipped for that page.

**Impact:** Pages where the reference heading hasn't been assigned seed_role="reference_heading" by the time `_enforce_reference_boundary_from_structure` runs will have no boundary enforcement.

**Fix:** Either broaden the match to include `_is_reference_heading_candidate`, or run the enforcement after role resolution is more complete.

---

### WR-08: `_detect_frontmatter_zone` lost its page guard

**File:** `paperforge/worker/ocr_document.py:1877-1882` (in diff)
**Issue:** The old function had an early guard: `if page_num > 1: return None`. The new version removed this check. The docstring still says "Detect frontmatter zone for a block on the first surviving page" but there is no enforcement — the function accepts blocks from any page. If called with a block from page 7 with `raw_label = "doc_title"` and positioned in the top 20% of the page, it could incorrectly return `"title_zone"`.

**Impact:** Off-by-one pages with title-like text could be misclassified as frontmatter zones.

**Fix:** Either restore the page guard against the `first_surviving_page` anchor, or document that the caller must pre-filter.

---

## Info

### IN-01: `_is_page1_body_start` vs `_is_first_page_body_start` are nearly identical copies

**File:** `paperforge/worker/ocr_document.py:510-525 vs 528-545`
**Issue:** The two functions share ~80% of their logic. The newer version adds `structured_insert`, `structured_insert_candidate` role handling and `preproof_marker` filtering. Since the old version is dead code (WR-05), this is a one-time cleanup after deletion, but worth noting that the duplication was introduced rather than inlined.

---

### IN-02: Type annotation mismatch in `_body_started_excluded_ids`

**File:** `paperforge/worker/ocr_document.py:974`
**Issue:** The type annotation says `set[str]` but `_artifact_block_id` returns `str | int | None`. The set actually stores `str | int | None` values:
```python
_body_started_excluded_ids: set[str] = set()
```
Later: `_body_started_excluded_ids.add(_artifact_block_id(block, duplicate_block_ids))` which is `str | int | None`.

---

### IN-03: `record_decision` call in `_enforce_reference_boundary_from_structure` logs identical old/new role

**File:** `paperforge/worker/ocr_document.py:2560-2564`
**Issue:** The `record_decision` call passes `old_role=b.get("role", "")` and `new_role=b.get("role", "")` — identical values. The decision summary's `role_mutation_count` will not increment for this event, even though the zone change is a meaningful structural event.

---

## Detailed Gate Status Assessment

| Gate | Claimed | Actual | Evidence |
|------|---------|--------|----------|
| **Gate 1** | DONE | **PARTIAL** (implemented but not integrated) | 3 completeness functions exist + 3 unit tests, but **none are called from production code** (CR-01). Functions cannot detect silent text loss at runtime. |
| **Gate 2** | PARTIAL (xfail) | **ACCURATE** | `test_dwqqk2yb_figure3_is_fully_owned_not_merely_captured` exists as `xfail(strict=True)`. No production changes. |
| **Gate 3** | DONE | **DONE** (thinly verified) | `_enforce_reference_boundary_from_structure` implemented and integrated. However: test doesn't check zone assignment (WR-06), stale-role issue (WR-03), seed_role-only matching gap (WR-07). |
| **Gate 4** | DONE | **MOSTLY DONE** (corpus 75% tagged) | Taxonomy migrated. But 2 of 8 papers have empty `layout_tags` (WR-04). Contract tests don't enforce per-paper classification. |
| **Gate 5** | Entry criteria defined | **ACCURATE** | `ocr-v2-remaining-issues-2026-06-18.md` updated with checklist. No execution. |

---

## Test Count Verification

All test counts in PROJECT-MANAGEMENT.md §10.7 are **accurate**:

| Suite | Collected | Claimed | Match |
|-------|-----------|---------|-------|
| `test_ocr_document.py` | 131 | 131/131 PASS | Yes |
| `test_ocr_figures.py` | 88 | 82/88 (6 pre-existing) | Yes |
| `test_ocr_real_paper_regressions.py` | 52 | 5P/46S/1X (collected: 5+46+1=52) | Yes |
| `test_ocr_real_paper_audit_contracts.py` | 2 | 2/2 PASS | Yes |
| `tests/cli/` + `tests/unit/` | 283 | 283/283 PASS | Yes |

---

## Verdict

**The implementation status report in PROJECT-MANAGEMENT.md §10 overstates completion for Gates 1 and 4.**

- **Gate 1: "DONE"** is inaccurate. The code exists but is dead from the pipeline's perspective. Correct status: **PARTIAL — functions implemented but not production-wired**.
- **Gate 4: "DONE"** is overstated. 25% of the corpus has empty layout tags. Correct status: **MOSTLY DONE — corpus 75% tagged, contract tests incomplete**.
- **Gates 2, 3, 5:** Status claims are accurate (Gate 2 xfail, Gate 3 DONE with thin verification, Gate 5 docs-only).

The reported test counts are verified correct. The primary risk is that the `state healthy` definition depends on Gates 1-4 being complete, but Gate 1 cannot operationalize its signals and Gate 4 has untracked papers.

---

_Reviewed: 2026-06-18_
_Reviewer: gsd-code-review agent_
_Depth: deep (cross-file call-chain tracing)_
