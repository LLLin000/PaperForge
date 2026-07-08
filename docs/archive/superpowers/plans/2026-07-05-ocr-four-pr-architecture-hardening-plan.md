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

1. **Move `CONSUMED_FRONTMATTER_ROLES` to module-level constant `_CONSUMED_FRONTMATTER_ROLES`** in `ocr_render.py`
   - Both `_collect_frontmatter_fallback_fields()` and the body loop skip use the same constant
   - Prevents scope issue (body loop defines it AFTER title rendering) and avoids two copies drifting apart

2. **Add `_collect_frontmatter_fallback_fields()`** in `ocr_render.py`
   - Call BEFORE the title rendering block (around line 1240)
   - Read `text` or `block_content` from blocks, normalize via `normalize_ocr_math_text()`
   - Deduplicate: track `seen` set of normalized text to avoid duplicate entries
   - Do NOT check `render_default` — these blocks will be consumed by skip anyway
   - Return `dict[str, list[str] | str]` (title, authors, affiliations, emails, doi)

3. **Refactor title rendering**
   ```python
   fallback = _collect_frontmatter_fallback_fields(structured_blocks, resolved_metadata)
   title = resolved_metadata.get("title", {}).get("value", "") or fallback.get("title", "")
   ```

4. **Refactor author rendering**
   - Fallback chain: resolved_metadata.authors_display → resolved_metadata.authors.value → fallback.authors

5. **Refactor metadata callout**
   - Single `> [!info]- Paper Metadata` callout
   - If fallback has affiliations/emails, add them after existing metadata fields
   - DOI: only from fallback when metadata is empty AND block text is a clean DOI line
   - Dedupe affiliation/email text via normalized `seen` set

6. **Leave body loop unchanged**
   - `_CONSUMED_FRONTMATTER_ROLES` skip on page ≤ 2 stays
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
   - `if raw_label == "text" and _looks_like_inline_figure_mention(...)`: **default to body_paragraph**
   - Only bypass when both conditions hold: `zone == "display_zone"` AND `style_family == "legend_like"`
   - This ensures early-stage blocks (no zone yet) also get the body escape, not just post-zone blocks
3. **Add `_CAPTION_DELIMITER_PATTERN` and `_CAPTION_TITLE_PATTERN`** in `ocr_roles.py`

4. **Rewrite `_is_obviously_formal_figure_caption()`**
   - Add inline mention reject at top
   - Convert to positive evidence: delimiter syntax OR title syntax + near_media/short
   - `raw_label == "figure_title"` always passes

5. **Add `_looks_like_caption_syntax()`**

### Acceptance Criteria

| Check | Method |
|-------|--------|
| "Fig. 9 shows..." → `body_paragraph` (not `figure_caption_candidate`) | Unit test |
| "Figure 1. Results" → `figure_caption` | Unit test |
| "Fig 1 Histological analysis" → `_looks_like_caption_syntax` True | Unit test |
| 8 gold fixtures: matched_figures not decreased unless phantom-removal documented | Regression test |
| 2HJSWV3V: phantom Fig 8/9 body mentions no longer enter formal legend pool; matched_figures may decrease only for phantom matches; real captions must not increase | Manual check |
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
| DOI not duplicated (fallback only when metadata empty AND block is clean DOI) | Unit test |
3. **Modify `same_page_tail_blocks`** in `infer_zones()`
   - Add `_is_in_same_reference_column()` guard before `not _is_reference_item_candidate()`
   - Pass the already-found `ref_heading_block` (do NOT re-scan)

4. **Derive `page_width`** — use a helper `_page_width_for_zone_block()`:
   - Check `block.get("page_width")` first
   - Then scan `page_blocks` for any block with `page_width`, take the max
   - Then try `body_anchor.get("page_width")`
   - Finally fallback to 1200 (needed for test fixtures without page_width)
   - Do NOT hardcode 1200 directly in the column comparison logic
5. **Write 6 tests** in `tests/test_ocr_document.py`
   - Two-column with left-body not pulled
   - Two-column with right-column note still pulled
   - Single-column preserved
   - Full-width reference heading preserved
   - 28JLIHLS single-column same-page boundary remains correctly classified; no new zone pollution

6. **Run zone tests + document tests + full suite**

### Acceptance Criteria

| Check | Method |
|-------|--------|
| Left-column Conclusion NOT in `tail_nonref_hold_zone` on shared ref page | Unit test |
| Same-column tail note STILL in tail zone | Unit test |
| 28JLIHLS single-column same-page boundary remains correctly classified; no new zone pollution | Regression |
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

4. **Enrich candidate group metadata** — add `column_band` after `_candidate_group_entry()` call
   - Use **Scheme B** (smaller diff): do NOT change `_candidate_group_entry()` signature
   - Instead, in the caller (`_build_semantic_figure_groups_from_assets()` or equivalent):
     ```python
     entry = _candidate_group_entry(...)
     entry["column_band"] = _group_column_band(cluster, page_width)
     entry["column_evidence"] = "..."
     ```
   - `page_width` is already available in the calling context
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
