# Layout Capability Audit — 2026-07-03

## Method

For each complex layout type, evaluated:
- Code logic (does the pipeline have a conceptual model?)
- Actual rendered output (fulltext.md correctness)
- Block role/zone assignment (732 vault papers)
- Known failure patterns

## Findings per Type

### 1. Frontmatter — 🔴 Capability Ceiling

**Current approach**: Hardcoded keyword list (`furniture_signals`, 15 phrases) + position
heuristics (top 20% = title, width < 35% page_width + top half = furniture).
Only pages 1-2.

**Evidence**: CAQNW9Q2 page 1 — `frontmatter_support` (correspondence) leaks into
`body_zone`. Keyword list doesn't match.

**Why ceiling**:
- 15 keywords cannot cover all journal frontmatter styles
- Position thresholds are brittle across layouts
- Only pages 1-2 — multi-page frontmatter automatically mislabeled
- Dependent on seed roles being correct

**Fix requires**: ML model or document grammar. Heuristic patching cannot root-fix.

### 2. Mixed_tail — 🟢 Capable, Working

**Current approach**: `_classify_page_layout` detects `mixed_tail` via role
distribution (one side body + other side tail). `_partition_by_reference_zone`
handles per-page ref zones. `_reconcile_tail_spread` handles body/ref/backmatter
boundary.

**Evidence**: 4 papers checked (A8E7SRVS, KUR9PBJC, 24YKLTHQ, YQIC2RDL):
- All mixed_tail pages correctly classified (conf=0.60)
- Body/ref split reasonable
- KUR9PBJC: clean body_end=12 → ref_start=13

**Gap**: Only 7/73 fixtures have mixed_tail pages. 41 non-fixture papers have
mixed_tail — coverage gap, not capability gap.

### 3. Preproof Frontmatter — 🟢 Capable, Working

**Evidence**: DWQQK2YB renders: title → authors → abstract → highlights →
keywords → Introduction (page 4). Special preproof handling works correctly.

### 4. Figure-heavy / Atlas Pages — 🟡 Data Limitation (Acceptable)

**Evidence**:
- NC66N4Q3 (56p atlas): 52/56 pages `single_column conf=0.35`
- 24YKLTHQ page 7: 8 figure_asset + 1 caption → `single_column conf=0.35`

**Why acceptable**: Pages with few text blocks inherently lack layout signal.
`few_eligible_blocks` fallback to low-confidence `single_column` is correct behavior.
NC66N4Q3 body_end=3 is reasonable (only 3 pages of prose text).

### 5. Two-column Reference Ordering — 🟢 Capable, Fixed

**Evidence**: KUR9PBJC pages 17-18 (60+ refs/page in two_column), A8E7SRVS page 13
(25 refs) all render correctly. `_should_attach_reference_item_to_ref_section`
(commit 9aa228d) handles multi-column continuation.

**History**: Previously buggy, now fixed. No remaining issues.

### 6. Sidecar Caption — 🟢 Capable, Fixed

**Evidence**: 37LK5T97 Figure 1 caption (left column) + image (right column)
correctly paired. `_is_sidecar_candidate` (ocr_document.py:4360) checks vertical
overlap when horizontal overlap is absent.

## Summary

| Layout Type | Verdict | Current State | Real Gap |
|---|---|---|---|
| Frontmatter | 🔴 Ceiling | Heuristics can improve but not fix | Needs ML / grammar |
| Mixed_tail | 🟢 Capable | Classification works | 41 papers not in fixtures |
| Preproof frontmatter | 🟢 Capable | Working | None |
| Figure-heavy / atlas | 🟡 Data limit | Correct fallback | None |
| Two-column ref | 🟢 Capable | Fixed in 9aa228d | None |
| Sidecar caption | 🟢 Capable | Fixed | None |

**Key takeaway**: Only frontmatter is a true capability ceiling. All other layout
types have working pipeline code; prior bug-fix cycles (sidecar, ref ordering,
column-aware prefix recovery, weak cluster rejection) have largely cleared the
implementation gaps. The largest practical gap is mixed_tail fixture coverage
(41 candidate papers not in regression set).
