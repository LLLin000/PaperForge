# DWQ Repair And Completeness Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean stale OCR tracking files first, then repair the remaining real DWQQK2YB support-routing and figure-ownership issues, rebuild affected derived artifacts, and leave the completeness-check layer fully planned as the next slice.

**Architecture:** This phase has one hard rule: fix the repo's current truth files before touching behavior, so later work stops inheriting stale issue narratives. After the cleanup, make two narrow production repairs in the existing OCR-v2 pipeline: one in frontmatter support routing and one in figure ownership partition/claim logic, then rebuild the affected paper artifacts and update the docs again from measured results. The completeness-check feature remains planning-only in this phase and is carried forward as the next explicit implementation topic.

**Tech Stack:** Python 3.14, pytest, existing `paperforge.worker` OCR pipeline, `scripts/dev/ocr_rebuild_paper.py`, audit artifacts under `audit/`, real-paper replay regressions.

---

## File Structure

- Modify: `project/current/ocr-v2-closeout-priority.md`
  - Active next-step truth source; must stop claiming already-fixed P0-P2 issues are open.
- Modify: `project/current/ocr-v2-remaining-issues-2026-06-18.md`
  - Residual issue snapshot; must be rewritten from actual post-9.7 state.
- Modify: `PROJECT-MANAGEMENT.md`
  - Session log and current truth surface; must record file cleanup, DWQ repairs, rebuild results, and next planned completeness topic.
- Modify: `paperforge/worker/ocr_roles.py`
  - Frontmatter support routing seam for first-surviving-page support-like blocks.
- Modify: `paperforge/worker/ocr_figures.py`
  - Figure candidate-group partition and local asset claiming seam for DWQQK2YB ownership repair.
- Modify: `tests/test_ocr_roles.py`
  - Unit-level frontmatter support regression coverage.
- Modify: `tests/test_ocr_figures.py`
  - Unit-level ownership/partition regression coverage.
- Modify: `tests/test_ocr_real_paper_regressions.py`
  - Real-paper DWQQK2YB ownership and support-routing checks.
- Use: `scripts/dev/ocr_rebuild_paper.py`
  - Canonical derived-artifact rebuild entry point after the code fixes land.
- Preserve reference spec: `docs/superpowers/specs/2026-06-18-ocr-completeness-check-design.md`
  - Carry forward into the end-of-phase planning/doc update; no production-code changes in this phase.

---

### Task 1: Clean Stale Truth Files First

**Files:**
- Modify: `project/current/ocr-v2-closeout-priority.md`
- Modify: `project/current/ocr-v2-remaining-issues-2026-06-18.md`
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Write the failing doc-truth regression note as a checklist in the current files**

At the top of your work buffer, use this checklist to drive the edits:

```text
- remove already-fixed DW post-drop frontmatter item as an active open bug
- remove or downgrade stale `media_asset -> body_paragraph` as a live blocker when latest analysis says it was stale audit truth
- stop treating DW biography mismatch as active if the current replay/audit state already moved
- keep DW frontmatter support routing open
- keep DW figure ownership open
- keep completeness check as next planned work
```

- [ ] **Step 2: Rewrite `project/current/ocr-v2-closeout-priority.md` so it no longer inherits stale blockers**

Make the following concrete edits:

```md
## Remaining blockers before merge:
- DWQQK2YB frontmatter support/equal-contribution routing on the first surviving page
- DWQQK2YB figure ownership on mixed post-reference figure pages
- derived artifact rebuild after ownership/support repairs
- completeness-check layer implementation (next slice)
```

Remove these stale or downgraded claims from that block unless fresh evidence re-proves them during this phase:

```md
- `media_asset → body_paragraph` (42 blocks) — zone/attribution work
- DW biography page mismatch
```

- [ ] **Step 3: Rewrite `project/current/ocr-v2-remaining-issues-2026-06-18.md` to reflect post-9.7 truth**

Replace the stale issue sections with a compact residual list shaped like this:

```md
## Active Residuals After 9.7

1. DWQQK2YB first-surviving-page support blocks still route inconsistently (`frontmatter_support` vs `frontmatter_noise` / body fallback)
2. DWQQK2YB figure ownership still over-claims or stays ambiguous on mixed post-reference figure pages
3. Backmatter heading taxonomy remains partially conservative by design; only fix if verified zone semantics require it
4. Completeness-check layer is specified and pending implementation
```

Delete or archive the old sections for:

- Issue 1: DW post-drop frontmatter not recognized
- Issue 3: figure inner label issue as a main active blocker
- Issue 4: publisher noise as a main active blocker
- Issue 6: DW biography mismatch as an active bug

- [ ] **Step 4: Add a new `PROJECT-MANAGEMENT.md` entry recording the truth-file cleanup before code changes**

Append a new entry skeleton using this exact shape:

```md
### 9.8 Task 1 — Active OCR Truth-File Cleanup (2026-06-18)

**Problem:** Active current-priority files still inherited stale pre-9.7 issue narratives, causing the next phase to start from wrong blockers.

**Root cause:** `project/current/` and `PROJECT-MANAGEMENT.md` were not fully reconciled after the P0-P2 close-out session.

**Fix:** Rewrote the active close-out priority and remaining-issues files so only real unresolved DWQQK2YB support-routing and ownership issues remain active; completeness-check stays as the next planned slice.

**Result:** Later implementation steps no longer inherit already-fixed P0-P2 failures as active blockers.
```

- [ ] **Step 5: Run a quick grep-based verification that the stale phrases are gone from active current files**

Run: `rg -n "DW Post-Drop Frontmatter Not Recognized|media_asset -> body_paragraph|DW Biography Page Mismatch" project/current PROJECT-MANAGEMENT.md`

Expected: only historical/project-log references remain; active current sections no longer present those as top open blockers.

- [ ] **Step 6: Commit the truth-file cleanup first**

```bash
git add project/current/ocr-v2-closeout-priority.md project/current/ocr-v2-remaining-issues-2026-06-18.md PROJECT-MANAGEMENT.md
git commit -m "docs: align OCR active issues after 9.7 close-out"
```

---

### Task 2: Lock DWQQK2YB Frontmatter Support Routing With Red Tests

**Files:**
- Modify: `tests/test_ocr_roles.py`
- Modify: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write the failing unit test for first-surviving-page equal-contribution support**

Add this to `tests/test_ocr_roles.py` near the page-1 frontmatter support tests:

```python
def test_first_surviving_page_equal_contribution_text_routes_to_frontmatter_support() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    title = {
        "page": 2,
        "block_label": "text",
        "raw_label": "text",
        "block_content": "Real Article Title",
        "text": "Real Article Title",
        "block_bbox": [80, 140, 900, 190],
        "page_width": 1200,
        "page_height": 1600,
    }
    support = {
        "page": 2,
        "block_label": "text",
        "raw_label": "text",
        "block_content": "These authors contributed equally to this work.",
        "text": "These authors contributed equally to this work.",
        "block_bbox": [90, 760, 560, 805],
        "page_width": 1200,
        "page_height": 1600,
    }

    result = assign_block_role(support, page_blocks=[title, support], page_width=1200, page_height=1600)

    assert result.role == "frontmatter_support"
```

- [ ] **Step 2: Write the failing unit test for first-surviving-page correspondence support**

Add this immediately after the previous test in `tests/test_ocr_roles.py`:

```python
def test_first_surviving_page_correspondence_text_routes_to_frontmatter_support() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    title = {
        "page": 2,
        "block_label": "text",
        "raw_label": "text",
        "block_content": "Real Article Title",
        "text": "Real Article Title",
        "block_bbox": [80, 140, 900, 190],
        "page_width": 1200,
        "page_height": 1600,
    }
    support = {
        "page": 2,
        "block_label": "text",
        "raw_label": "text",
        "block_content": "Corresponding author: person@example.edu",
        "text": "Corresponding author: person@example.edu",
        "block_bbox": [90, 820, 980, 900],
        "page_width": 1200,
        "page_height": 1600,
    }

    result = assign_block_role(support, page_blocks=[title, support], page_width=1200, page_height=1600)

    assert result.role == "frontmatter_support"
```

- [ ] **Step 3: Write the failing real-paper regression for DW support lines**

Add this to `tests/test_ocr_real_paper_regressions.py` near the other DW tests:

```python
def test_dwqqk2yb_first_surviving_page_support_blocks_stay_frontmatter_support(tmp_path: Path) -> None:
    result = replay_production_pipeline("DWQQK2YB", tmp_path)
    page2_blocks = [b for b in result["structured_blocks"] if int(b.get("page", 0) or 0) == 2]

    equal_block = next(b for b in page2_blocks if "contributed equally" in str(b.get("text") or "").lower())
    corr_block = next(b for b in page2_blocks if "corresponding author" in str(b.get("text") or "").lower())

    assert equal_block.get("role") == "frontmatter_support"
    assert corr_block.get("role") == "frontmatter_support"
```

- [ ] **Step 4: Run the focused tests to verify red**

Run: `python -m pytest tests/test_ocr_roles.py -k "first_surviving_page and frontmatter_support" -v --tb=short`

Expected: FAIL because the current routing still leans on page-1 and text-prefix specials.

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "dwqqk2yb_first_surviving_page_support" -v --tb=short`

Expected: FAIL because DW support-like blocks still route inconsistently.

- [ ] **Step 5: Commit the failing tests only**

```bash
git add tests/test_ocr_roles.py tests/test_ocr_real_paper_regressions.py
git commit -m "test: lock DW frontmatter support regressions"
```

---

### Task 3: Implement DWQQK2YB Frontmatter Support Repair

**Files:**
- Modify: `paperforge/worker/ocr_roles.py`
- Test: `tests/test_ocr_roles.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Add a helper for frontmatter-support-like text confirmation**

In `paperforge/worker/ocr_roles.py`, near the other frontmatter helpers, add:

```python
def _looks_like_frontmatter_support_text(text: str) -> bool:
    lower = text.lower().strip()
    return (
        "corresponding author" in lower
        or lower.startswith("correspondence")
        or "contributed equally" in lower
        or "share first authorship" in lower
    )
```

- [ ] **Step 2: Route first-surviving-page support-like text before generic frontmatter noise/body fallback**

In the `raw_label == "text"` branch of `assign_block_role()` in `paperforge/worker/ocr_roles.py`, insert this block before the generic body fallback:

```python
        bbox = block.get("block_bbox") or block.get("bbox") or [0, 0, 0, 0]
        topish = len(bbox) >= 4 and bbox[1] <= page_height * 0.65
        support_zone = zone in {"author_zone", "affiliation_zone", "journal_furniture_zone"}
        if page_num in (1, 2) and topish and _looks_like_frontmatter_support_text(text):
            return RoleAssignment(
                role="frontmatter_support",
                confidence=0.78,
                evidence=[f"first-surviving-page support text: {text[:60]}"],
            )
```

Keep the helper text-confirmatory only; this remains bounded to early-page support routing and should not become a generic full-document string rule.

- [ ] **Step 3: Run the focused tests to verify green**

Run: `python -m pytest tests/test_ocr_roles.py -k "first_surviving_page and frontmatter_support" -v --tb=short`

Expected: PASS.

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "dwqqk2yb_first_surviving_page_support" -v --tb=short`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/ocr_roles.py tests/test_ocr_roles.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: preserve DW frontmatter support on surviving page"
```

---

### Task 4: Lock DWQQK2YB Figure Ownership With Red Tests

**Files:**
- Modify: `tests/test_ocr_figures.py`
- Modify: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write the failing unit test for caption-band-local asset partition**

Add this to `tests/test_ocr_figures.py` near the candidate-group tests:

```python
def test_partition_assets_by_caption_bands_keeps_assets_local_to_caption_band() -> None:
    from paperforge.worker.ocr_figures import _partition_assets_by_caption_bands

    captions = [
        {"block_id": 101, "bbox": [700, 900, 1050, 960]},
        {"block_id": 102, "bbox": [700, 1250, 1050, 1310]},
    ]
    assets = [
        {"block_id": 1, "bbox": [650, 200, 1050, 520]},
        {"block_id": 2, "bbox": [650, 560, 1050, 820]},
        {"block_id": 3, "bbox": [650, 980, 1050, 1180]},
    ]

    parts = _partition_assets_by_caption_bands(captions, assets, page_height=1600)

    assert [a["block_id"] for a in parts["101"]] == [1, 2]
    assert [a["block_id"] for a in parts["102"]] == [3]
```

- [ ] **Step 2: Write the failing real-paper ownership regression for DW**

Add this to `tests/test_ocr_real_paper_regressions.py` next to `test_gold_figure_merge_ownership_contracts`:

```python
def test_dwqqk2yb_ownership_no_longer_mega_merges_same_page_assets(tmp_path: Path) -> None:
    result = replay_production_pipeline("DWQQK2YB", tmp_path)
    reader_payload = result["reader_payload"]
    matched, ambiguous = _reader_figure_index(reader_payload)

    fig2 = matched.get(2)
    fig4 = matched.get(4)

    assert fig2 is not None
    assert len(fig2.get("asset_block_ids", [])) <= 3
    assert fig4 is not None
    assert len(fig4.get("asset_block_ids", [])) <= 3
    assert 3 in matched or 3 in ambiguous
```

- [ ] **Step 3: Run the focused tests to verify red**

Run: `python -m pytest tests/test_ocr_figures.py -k "caption_bands" -v --tb=short`

Expected: FAIL if current partitioning does not keep same-page assets local enough.

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "dwqqk2yb_ownership_no_longer_mega_merges" -v --tb=short`

Expected: FAIL because Figure 2 / 4 currently over-claim and Figure 3 stays unresolved.

- [ ] **Step 4: Commit the failing tests only**

```bash
git add tests/test_ocr_figures.py tests/test_ocr_real_paper_regressions.py
git commit -m "test: lock DW figure ownership regressions"
```

---

### Task 5: Implement DWQQK2YB Figure Ownership Repair

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Use caption-band partitioning before broad same-page claiming**

In `build_figure_inventory()` in `paperforge/worker/ocr_figures.py`, after `page_caption_index` is built and before broad candidate scoring claims the whole page cluster, compute per-page partition maps:

```python
    page_assets_index: dict[int, list[dict]] = {}
    for asset in assets:
        page_assets_index.setdefault(int(asset.get("page", 0) or 0), []).append(asset)

    partitioned_assets_by_caption: dict[tuple[int, str], list[dict]] = {}
    for page, captions in page_caption_index.items():
        partitions = _partition_assets_by_caption_bands(captions, page_assets_index.get(page, []), page_height=1700)
        for caption_id, caption_assets in partitions.items():
            partitioned_assets_by_caption[(page, caption_id)] = caption_assets
```

- [ ] **Step 2: Restrict candidate groups to caption-local assets when partition evidence exists**

In the legend loop inside `build_figure_inventory()`, before appending a candidate group, insert this guard:

```python
            local_assets = partitioned_assets_by_caption.get((legend_page, str(legend.get("block_id", ""))))
            if local_assets:
                local_ids = {a.get("block_id") for a in local_assets}
                group_ids = set(group.get("asset_block_ids", []))
                if not (group_ids & local_ids):
                    continue
```

This keeps same-page narrow-caption ownership local when partition evidence exists, without inventing a paper-specific branch.

- [ ] **Step 3: Keep unresolved over false mega-merge**

When no caption-local candidate remains after the partition guard, preserve ambiguity instead of claiming the highest broad page group. Use this shape where the weak/ambiguous path is built:

```python
                ambiguous_figures.append(
                    {
                        "figure_number": fig_num,
                        "legend_block_id": legend.get("block_id", ""),
                        "asset_block_ids": [],
                        "candidate_asset_ids": [],
                        "page": legend_page,
                    }
                )
                continue
```

Only use this path when local partition evidence existed and no local group survived; do not broadly weaken all papers.

- [ ] **Step 4: Run the focused tests to verify green**

Run: `python -m pytest tests/test_ocr_figures.py -k "caption_bands" -v --tb=short`

Expected: PASS.

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "dwqqk2yb_ownership_no_longer_mega_merges or gold_figure_merge_ownership_contracts" -v --tb=short`

Expected: PASS, or the only remaining ambiguity is explicitly the guarded unresolved path and no false mega-merge remains.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: constrain DW figure ownership to local caption bands"
```

---

### Task 6: Rebuild Derived Artifacts And Update Docs From Measured Results

**Files:**
- Run: `scripts/dev/ocr_rebuild_paper.py`
- Modify: `PROJECT-MANAGEMENT.md`
- Modify: `project/current/ocr-v2-closeout-priority.md`
- Modify: `project/current/ocr-v2-remaining-issues-2026-06-18.md`

- [ ] **Step 1: Rebuild the affected paper artifacts after the code repairs**

Run: `python scripts/dev/ocr_rebuild_paper.py --trace DWQQK2YB`

Expected: derived artifacts rebuilt, `block_trace.csv` regenerated, role/zone distributions printed.

- [ ] **Step 2: Run the targeted DW verification slice after rebuild**

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "DWQQK2YB" -v --tb=short`

Expected: support-routing and ownership checks now reflect rebuilt artifacts.

- [ ] **Step 3: Record the rebuild and measured repair outcome in `PROJECT-MANAGEMENT.md`**

Append a new entry using this shape:

```md
### 9.9 Task 2 — DWQQK2YB Support + Ownership Repair And Rebuild (2026-06-18)

**Problem:** After 9.7, DWQQK2YB still had one real frontmatter-support routing gap and one real same-page figure ownership gap; derived assets also lagged behind the repaired code path.

**Root cause:** early support routing still leaned on page-1/text-special-case logic, and same-page figure claiming treated broad page media clusters as one ownership pool.

**Fix:** promoted first-surviving-page frontmatter support lines using bounded support-text confirmation; constrained figure claiming to caption-local partition bands before broad same-page asset adoption; rebuilt DWQQK2YB derived artifacts with `scripts/dev/ocr_rebuild_paper.py`.

**Result:** DW support blocks remain in frontmatter support flow; figure ownership no longer mega-merges same-page assets; rebuilt artifacts now reflect the repaired logic.

**Test status:** [insert exact pytest and rebuild commands/results from this run].
```

- [ ] **Step 4: Rewrite the active current files again from the measured post-rebuild result**

Update:

- `project/current/ocr-v2-closeout-priority.md`
- `project/current/ocr-v2-remaining-issues-2026-06-18.md`

so they reflect only what remained true after the rebuild. If the DW support issue or the DW ownership issue is fully gone, remove it from active blockers. If one remains partial, rewrite it precisely rather than keeping the older broad wording.

- [ ] **Step 5: Commit**

```bash
git add PROJECT-MANAGEMENT.md project/current/ocr-v2-closeout-priority.md project/current/ocr-v2-remaining-issues-2026-06-18.md
git commit -m "docs: record DW repair and OCR rebuild results"
```

---

### Task 7: Carry Completeness Check Forward As The Next Explicit Slice

**Files:**
- Preserve: `docs/superpowers/specs/2026-06-18-ocr-completeness-check-design.md`
- Preserve: `docs/superpowers/specs/2026-06-18-dwq-repair-and-completeness-phase-design.md`
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Add a next-topic note pointing at the completeness-check spec**

In the latest active session block in `PROJECT-MANAGEMENT.md`, add a final line like:

```md
- Next topic: implement the fuzzy OCR completeness-check layer described in `docs/superpowers/specs/2026-06-18-ocr-completeness-check-design.md` after the DW repairs settle.
```

- [ ] **Step 2: Run one final sanity slice across the touched areas**

Run: `python -m pytest tests/test_ocr_roles.py tests/test_ocr_figures.py tests/test_ocr_real_paper_regressions.py -k "DWQQK2YB or frontmatter_support or ownership" -v --tb=short`

Expected: PASS, with no new regressions in the touched seams.

- [ ] **Step 3: Commit the final planning-state sync**

```bash
git add PROJECT-MANAGEMENT.md
git commit -m "docs: point OCR next slice at completeness checks"
```
