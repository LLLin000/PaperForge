# Four-PR Architecture Hardening — Implementation Plan

> **Date:** 2026-07-05
> **Spec:** `docs/superpowers/specs/2026-07-05-ocr-four-pr-architecture-hardening-design.md`
> **Strategy:** 4 independent PRs, implemented sequentially (PR 1 → PR 2 → PR 3 → PR 4)

---

## Scope Boundary

| In scope | Not in scope |
|----------|-------------|
| PR 1: frontmatter render fallback (field-based, before title) | PR 5: frontmatter heading labels ("ARTICLE INFO") |
| PR 2: figure caption heuristic tightening + body escape | PR 6: supplementary-only document mode |
| PR 3: same-page reference boundary column-aware | Architecture cleanup (dead code, monolith splitting) |
| PR 4: vnext figure pairing column compatibility | Sidecar exception (deferred from PR 4) |
| 8 gold fixture regression gates | Health layer hardening (Layer 2) |

---

## PR 1: Frontmatter Render Fallback

**Branch:** `feat/pr1-frontmatter-fallback`
**Risk:** Low · **Files:** `ocr_render.py`, `test_ocr_render.py`

### Steps

1. **Add `_collect_frontmatter_fallback_fields()` in `ocr_render.py`**
   - Before the title rendering block (around line 1245)
   - Scan `structured_blocks` for roles in `CONSUMED_FRONTMATTER_ROLES` on pages 1–2
   - Group by role, only collect when `resolved_metadata` equivalent is empty
   - Return `dict[str, list[str] | str]` (title, authors, affiliations, emails, doi)

2. **Refactor title rendering**
   ```python
   fallback = _collect_frontmatter_fallback_fields(structured_blocks, resolved_metadata)
   title = resolved_metadata.get("title", {}).get("value", "") or fallback.get("title", "")
   ```

3. **Refactor author rendering**
   - Fallback chain: `resolved_metadata.authors_display` → `resolved_metadata.authors.value` → `fallback.authors`

4. **Refactor metadata callout**
   - Single `> [!info]- Paper Metadata` callout
   - If fallback has affiliations/emails, add them after existing metadata fields
   - DOI: never from fallback unless metadata is empty and block is a clean DOI line

5. **Leave body loop unchanged**
   - `CONSUMED_FRONTMATTER_ROLES` skip on page ≤ 2 stays
   - All rendered content comes from the metadata callout, not the body loop

6. **Write 5 tests** in `tests/test_ocr_render.py`

7. **Verify** — run render tests + full OCR suite

### Acceptance Criteria

| Check | Method |
|-------|--------|
| Authors appear when metadata empty | Unit test |
| No duplication when metadata present | Unit test |
| Title appears when metadata empty | Unit test |
| DOI not duplicated | Unit test |
| 105 focused tests still pass | `python -m pytest tests/test_ocr_*.py -v --tb=short` |

---

## PR 2: Formal Figure Caption Heuristic Tightening

**Branch:** `feat/pr2-caption-heuristic`
**Risk:** Medium-low · **Files:** `ocr_roles.py`, `test_ocr_roles.py`, `test_ocr_figures.py`

### Steps

1. **Add `_INLINE_FIGURE_MENTION_PATTERN` and `_looks_like_inline_figure_mention()`** in `ocr_roles.py`

2. **Add body escape in `assign_block_role()`** (around line 936 main branch)
   - In `_has_figure_prefix` branch, before `_is_obviously_formal_figure_caption()` call
   - `if raw_label == "text" and _looks_like_inline_figure_mention(...)`: return `body_paragraph` (zone-aware)

3. **Add `_CAPTION_DELIMITER_PATTERN` and `_CAPTION_TITLE_PATTERN`** in `ocr_roles.py`

4. **Rewrite `_is_obviously_formal_figure_caption()`**
   - Add inline mention reject at top
   - Convert to positive evidence: delimiter syntax OR title syntax + near_media/short
   - `raw_label == "figure_title"` always passes

5. **Add `_looks_like_caption_syntax()`**

6. **Write 8 tests** in `tests/test_ocr_roles.py`

7. **Run 8 gold fixture regressions** — verify `matched_figures` per fixture table

8. **Check 2HJSWV3V** — `matched_figures` should decrease (phantom Fig 8/9 removed)

### Acceptance Criteria

| Check | Method |
|-------|--------|
| "Fig. 9 shows..." → `body_paragraph` (not `figure_caption_candidate`) | Unit test |
| "Figure 1. Results" → `figure_caption` | Unit test |
| "Fig 1 Histological analysis" → `_looks_like_caption_syntax` True | Unit test |
| 8 gold fixtures: matched_figures not decreased unless phantom-removal documented | Regression test |
| 2HJSWV3V: matched_figures decreased by ~2 (phantom Fig 8/9) | Manual check |
| No new unmatched_assets on gold fixtures | Regression test |

---

## PR 3: Same-Page Reference Boundary — Column-Aware

**Branch:** `feat/pr3-column-aware-zone`
**Risk:** Medium · **Files:** `ocr_document.py`, `test_ocr_document.py`

### Steps

1. **Add `_block_column_band()` and `_is_full_width_ref_heading()`** in `ocr_document.py` (private helpers, do NOT import from `ocr_figures.py`)

2. **Add `_is_in_same_reference_column(block, ref_heading_block, page_width)`**
   - Handle: None ref → True (conservative), missing bbox → True (legacy), full-width → True (page-level)
   - Different column bands → False
   - Same band → True

3. **Modify `same_page_tail_blocks`** in `infer_zones()`
   - Add `_is_in_same_reference_column()` guard before `not _is_reference_item_candidate()`
   - Pass the already-found `ref_heading_block` (do NOT re-scan)

4. **Derive `page_width`** from body anchor or page blocks — do not hardcode 1200

5. **Write 6 tests** in `tests/test_ocr_document.py`
   - Two-column with left-body not pulled
   - Two-column with right-column note still pulled
   - Single-column preserved
   - Full-width reference heading preserved
   - 28JLIHLS regression (no false positive)
   - Left-column Conclusion can render as body

6. **Run zone tests + document tests + full suite**

### Acceptance Criteria

| Check | Method |
|-------|--------|
| Left-column Conclusion NOT in `tail_nonref_hold_zone` on shared ref page | Unit test |
| Same-column tail note STILL in tail zone | Unit test |
| Single-column same-page boundary unchanged | Unit test |
| 28JLIHLS still FALSE POSITIVE (no zone pollution) | Regression |
| Zone tests + document tests all pass | pytest |

---

## PR 4: VNext Figure Pairing — Column Compatibility

**Branch:** `feat/pr4-pairing-column`
**Risk:** Medium · **Files:** `ocr_figures.py`, `test_ocr_figures.py`

### Steps

1. **Add `_is_full_width_bbox()`** in `ocr_figures.py`

2. **Add `_column_compatible_for_caption_asset(caption_bbox, asset_bbox, page_width)`**
   - Full-width → compatible
   - Same explicit column band → compatible
   - Both center/ambiguous → compatible (no positive bonus)
   - One center → compatible
   - Different explicit bands → incompatible

3. **Add `_group_column_band()` in `ocr_figures.py`**
   - Returns dominant column band for a list of media blocks
   - `None` if group spans multiple bands (composite figure)

4. **Enrich candidate group metadata** in `_candidate_group_entry()` — add `column_band` field

5. **Insert column check in `_score_legend_to_group()`**
   - Must run **before** `safe_auto_match`
   - If incompatible → return `score=0, decision=rejected`

6. **Do NOT implement sidecar exception** in this PR

7. **Write 6 tests** in `tests/test_ocr_figures.py`
   - Cross-column rejection
   - Full-width compatibility
   - Center/ambiguous compatibility
   - Same-column match preserved
   - 28JLIHLS Fig 5/6 cross-column fix
   - Composite multi-column group

8. **Run figure tests + full suite**

### Acceptance Criteria

| Check | Method |
|-------|--------|
| Left-column caption NOT matched to right-column asset group | Unit test |
| Full-width caption matches center asset group | Unit test |
| 28JLIHLS figures correctly assigned to same column | Regression test |
| All existing figure tests pass | pytest |

---

## Branch Strategy

```bash
# All branches based on master (current: bdf96af6)
git checkout -b feat/pr1-frontmatter-fallback
# ... implement, test, commit, push, PR ...

git checkout master
git checkout -b feat/pr2-caption-heuristic
# ... implement, test, commit, push, PR ...

git checkout master
git checkout -b feat/pr3-column-aware-zone
# ... implement, test, commit, push, PR ...

git checkout master
git checkout -b feat/pr4-pairing-column
# ... implement, test, commit, push, PR ...
```

No branch dependencies — all 4 PRs can be created independently. Recommended order: PR 1 → PR 2 → PR 3 → PR 4.

---

## Verification Plan

After all 4 PRs merged, run:

```bash
# Full regression suite
python -m pytest tests/test_ocr_*.py -v --tb=short

# Real-paper regressions (8 gold fixtures)
python -m pytest tests/test_ocr_real_paper_regressions.py -v --tb=short

# Vault corpus diff (555 papers) — verify no unexpected regression
python scripts/dev/corpus_v3_diff_full.py
```

Expected diff after PR 2: 2HJSWV3V and similar papers with phantom captions should show improved figure matching. Other 547/555 papers should remain no-diff.
