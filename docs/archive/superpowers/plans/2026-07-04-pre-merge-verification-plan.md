# OCR A/B/C Pre-Merge Verification Plan

**Branch:** `feat/ocr-tail-settlement`

**Current verdict:** not merge-ready yet.

**Why:** fresh regression suite is green, but the current diff still has a few spec / regression blockers that need to be closed before merge.

---

## 1. Fresh evidence already collected

Ran on `feat/ocr-tail-settlement`:

```bash
python -m pytest tests/test_ocr_pipeline_v3.py tests/test_ocr_tail_settlement.py tests/test_ocr_object_writeback.py tests/test_appendix_figure_numbering.py tests/test_ocr_rendering.py -q --tb=line
```

Observed:

- `95 passed`

This proves the current focused suite is green.

It does **not** prove merge readiness by itself, because the remaining blockers are contract gaps and path-coverage gaps.

---

## 2. Merge blockers to clear

### Blocker A — page-qualified object writeback lookup

**Observed code:** `paperforge/worker/ocr_object_writeback.py:111-123`

```python
block_by_id: dict[str, dict] = {}
for b in structured_blocks:
    bid = b.get("block_id")
    if bid is not None:
        block_by_id[str(bid)] = b
...
block = block_by_id.get(asset_bid)
```

**Risk:** if `block_id` is reused on different pages, the later block overwrites the earlier one. That can stamp ownership onto the wrong block and hide the wrong content at render time.

**Required fix:**
- key by `(page, block_id)` instead of `block_id`
- use `(figure.page, asset.block_id)` / `(table.page, asset_block_id)` for lookups
- add a regression test with duplicated `block_id` across pages

**Merge gate:** do not merge before this is fixed and covered.

---

### Blocker B — contained figure text still bypasses the ownership contract

**Observed code:** `paperforge/worker/ocr_figures.py:5677-5680`

```python
block["_figure_contained"] = True
if role in _LEAK_ROLES:
    block["role"] = "figure_inner_text"
```

**Observed gap:** `tests/test_ocr_object_writeback.py` covers side-adjacent text and consumed-block ids, but does **not** cover contained text.

**Spec requirement:** `docs/superpowers/specs/2026-07-04-ocr-pipeline-deepening-design.md:468-476`
- contained figure text
- side-adjacent figure text
- idempotent writeback
- consumed-block contract visible both on block and inventory

**Required fix:**
- route contained-text claims through the same ownership-evidence path as side-adjacent text
- stamp `_object_owner_*`, `_object_association_reason`, `_object_consumed`
- add consumed block ids to the owning figure inventory entry
- add a contained-text regression test to `tests/test_ocr_object_writeback.py`

**Merge gate:** do not merge before contained text is under the same contract as side-adjacent text.

---

### Blocker C — v3 path skips legacy rescue behavior

**Observed flow:**
- `paperforge/worker/ocr_blocks.py` returns early in `normalize_mode="seed_only"`
- `paperforge/worker/ocr.py` then runs `pre_match_normalize(...)` and `post_match_normalize(...)`
- the legacy `rescue_roles_with_document_context(...)` pass is not run on the v3 path

**Risk:** `OCR_PIPELINE_V3=1` can diverge from legacy on papers that rely on rescue-phase body/reference/heading correction.

**Required action:** choose one and prove it:
1. **Preferred:** run `rescue_roles_with_document_context(...)` in the v3 path at the equivalent stage, or
2. prove by regression corpus that v3 no longer needs it

**Merge gate:** because v3 stays default-off, this is a **caveat blocker**, not a release blocker for legacy behavior. It must still be addressed before calling the v3 path merge-ready.

---

### Blocker D — no real-paper parity gate for `OCR_PIPELINE_V3=1`

**Observed coverage:** current v3 tests are unit/synthetic only.

**Missing proof:** no curated old-vs-new corpus diff on real OCR fixtures for:
- frontmatter
- backmatter
- reference boundaries
- figure/table matching parity

**Required fix:** add a small real-paper parity gate, not a giant suite.

Recommended corpus:
- one frontmatter-sensitive paper
- one tail/backmatter-sensitive paper
- one figure-heavy paper
- one table-heavy paper

For each, compare legacy vs v3 on:
- final `role`
- `render_default`
- `index_default`
- figure/table inventory counts

**Merge gate:** v3 is not merge-ready as a completed workstream until this gate exists and is green.

---

## 3. Merge-before-merge execution order

### Step 1 — fix object writeback lookup

Run after the fix:

```bash
python -m pytest tests/test_ocr_object_writeback.py -q --tb=line
```

Expected:
- all current writeback tests pass
- new duplicate-`block_id` cross-page regression test passes

---

### Step 2 — unify contained-text ownership contract

Run after the fix:

```bash
python -m pytest tests/test_ocr_object_writeback.py tests/test_ocr_rendering.py::test_body_renderer_skips_consumed_object_owned_blocks -q --tb=line
```

Expected:
- contained-text regression passes
- side-adjacent regression still passes
- renderer still skips consumed blocks

---

### Step 3 — restore or replace v3 rescue equivalence

Run after the fix:

```bash
python -m pytest tests/test_ocr_pipeline_v3.py tests/test_ocr_rendering.py::test_tail_zone_noise_band_guard tests/test_ocr_rendering.py::test_tail_zone_supplementary_material_not_noise tests/test_ocr_rendering.py::test_tail_candidate_overreach_does_not_absorb_late_body tests/test_ocr_rendering.py::test_cross_page_funding_continuation_preserves_order tests/test_ocr_rendering.py::test_backmatter_boundary_normalizes_child_sections_before_references -q --tb=line
```

Expected:
- v3 suite green
- tail/backmatter parity still green

---

### Step 4 — add real-paper v3 parity gate

Minimum acceptance command after adding it:

```bash
python -m pytest tests/test_ocr_pipeline_v3.py -q --tb=line
```

Expected:
- synthetic tests green
- new real-paper parity tests green

---

### Step 5 — final merge suite

Run this fresh immediately before merge:

```bash
python -m pytest tests/test_ocr_pipeline_v3.py tests/test_ocr_tail_settlement.py tests/test_ocr_object_writeback.py tests/test_appendix_figure_numbering.py tests/test_ocr_rendering.py -q --tb=line
```

Expected:
- `0 failed`

If this is green **and** blockers A-D are closed, the branch is merge-ready.

---

## 4. Merge decision rule

Only merge when all are true:

- cross-page duplicate `block_id` writeback bug is fixed
- contained text uses the same ownership contract as side-adjacent text
- v3 rescue equivalence is restored or explicitly proven unnecessary
- v3 real-paper parity gate exists and is green
- final fresh merge suite is green

Until then: **ready for more work, not ready to merge**.
