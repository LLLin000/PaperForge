# Figure Pipeline VNext Phase 5 — Cutover Evaluation and Default-Switch Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decide, with evidence, whether `build_figure_inventory(...)` can switch from legacy to vnext by default. This phase does **not** assume cutover is already safe. It first closes the comparison and gate-evaluation gaps from spec §8.3 and §9, then performs the wrapper switch only if all gates pass.

**Current assessment (2026-07-03):**
- Production path is still safe: `build_figure_inventory(...)` still calls legacy, so **master has zero behavioral regression today**.
- VNext path is much more auditable and structurally safer, but **not yet proven cutover-ready**.
- Repo-fixture evidence so far:
  - `2HEUD5P9`: parity (`legacy_matched=7`, `vnext_matched=7`, same consumed assets)
  - `YGH7VEX6`: parity on matched count and consumed assets (`12/12`, same consumed assets)
  - `DWQQK2YB`: vnext matches **more** (`legacy=4`, `vnext=6`) while consuming the **same** asset set, which is a plausible improvement but still requires manual adjudication before cutover
- Spec-required comparison corpus is still incomplete: we do not yet have explicit coverage/review for all categories in spec §8.3.

**Architecture:** Treat cutover as a gated release process, not a code flip. The work splits into: (1) comparison harness expansion, (2) representative-corpus curation, (3) diff review + regression triage, (4) default wrapper switch if and only if gates pass.

**Tech Stack:** Python 3, pytest, existing figure/render/rebuild tests, dev scripts under `scripts/dev/`, project records under `project/current/`

## Global Constraints

- Build on branch/worktree `feat/figure-pipeline-vnext`; do not edit the main checkout.
- Preserve the external interface `build_figure_inventory(structured_blocks, page_width=1200) -> FigureInventory`.
- Legacy implementation remains the immutable baseline until the final cutover task.
- No silent scope shrinkage: every spec §8.3 corpus category must be either represented or explicitly waived with written rationale.
- Differences between legacy and vnext must be reviewed paper-by-paper before cutover.
- VNext may differ from legacy only if the difference is explicitly recorded and judged strictly better or equivalent.
- No figure card may consume the same asset twice.
- No owned asset may remain in unresolved clusters.
- Add only the tests and scripts directly needed for cutover evaluation.

---

### Task 1: Expand the comparison harness to cover cutover gates

**Rationale:** The current compare script only reports matched count, unresolved count, unmatched legend count, and consumed asset ids. Spec §8.3 / §9 needs more: completeness totals, conflict counts, pass summaries, and render-facing diff surfaces.

**Files:**
- Modify: `scripts/dev/compare_figure_inventory_legacy_vs_vnext.py`
- Modify: `tests/test_ocr_figure_vnext_compare.py`

**Add to compare output:**
- `legacy_conflict_count`
- `vnext_conflict_count`
- `legacy_completeness`
- `vnext_completeness`
- `legacy_figure_ids`
- `vnext_figure_ids`
- `legacy_render_card_count`
- `vnext_render_card_count`
- `vnext_pass_names`

**Notes:**
- `legacy_conflict_count` can be approximated as `0` if legacy does not expose an ownership-conflict bucket.
- `legacy_completeness` should read `figure_legend_completeness` if present.
- `vnext_completeness` should read `completeness`.
- Render-card diff stays structural in this phase: compare normalized matched-figure card payloads, not screenshots.

- [ ] **Step 1: Add failing compare tests**
- [ ] **Step 2: Expand `compare_inventories(...)` and `compare_blocks_file(...)`**
- [ ] **Step 3: Run compare tests**
- [ ] **Step 4: Commit**

```bash
git add scripts/dev/compare_figure_inventory_legacy_vs_vnext.py tests/test_ocr_figure_vnext_compare.py
git commit -m "feat(ocr): expand legacy-vnext comparison harness for cutover gates"
```

### Task 2: Curate the full spec-required comparison corpus

**Rationale:** Spec §8.3 requires explicit coverage of these categories:
- same-page normal figure
- multi-panel same-row group
- sidecar legend page
- bundle-source page
- locator-bridge page
- dense composite parent page
- classic sequential-only rescue page
- unmatched asset / unresolved cluster page
- duplicated / continued legend page

Current repo fixtures cover only 3 papers and do not document category coverage explicitly.

**Files:**
- Create: `tests/fixtures/ocr_vnext_cutover_manifest.json`
- Create or extend fixture dirs under `tests/fixtures/ocr_vnext_real_papers/`
- Create: `project/current/2026-07-03-vnext-cutover-corpus-map.md`

**Manifest fields per paper:**
```json
{
  "paper": "YGH7VEX6",
  "categories": ["same-page normal figure", "classic sequential-only rescue"],
  "source": "D:/L/OB/Literature-hub/System/PaperForge/ocr/YGH7VEX6/structure/blocks.structured.jsonl",
  "notes": "why this paper represents the category"
}
```

**Requirements:**
- Use the smallest paper that cleanly demonstrates each category where possible.
- One paper may satisfy multiple categories.
- Every category must be mapped.
- Copy needed `blocks.structured.jsonl` files into the repo fixture tree.

- [ ] **Step 1: Select fixture papers from OCR vault**
- [ ] **Step 2: Copy missing fixtures into repo**
- [ ] **Step 3: Write `ocr_vnext_cutover_manifest.json`**
- [ ] **Step 4: Write the human-readable corpus map markdown**
- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/ocr_vnext_cutover_manifest.json tests/fixtures/ocr_vnext_real_papers/ project/current/2026-07-03-vnext-cutover-corpus-map.md
git commit -m "test(ocr): add full cutover comparison corpus manifest"
```

### Task 3: Generate diff reports for the full corpus

**Rationale:** Before switching the wrapper, we need one auditable diff report per paper plus a roll-up summary.

**Files:**
- Create: `project/current/2026-07-03-vnext-cutover-diff-review.md`
- Create: `project/current/vnext-cutover-diffs/<PAPER>.json`
- Optional helper script: `scripts/dev/compare_figure_inventory_corpus.py`

**Per-paper JSON must include at least:**
- legacy matched count
- vnext matched count
- legacy unresolved count
- vnext unresolved count
- legacy/vnext unmatched legends count
- legacy/vnext completeness
- legacy/vnext consumed block ids
- figure-id lists
- pass names triggered in vnext
- reviewer verdict placeholder (`unknown | equivalent | better | regression`)

**Roll-up markdown should summarize:**
- which papers are parity
- which papers are strict improvements
- which papers need manual explanation
- any suspected regressions

- [ ] **Step 1: Build or script corpus-wide compare run**
- [ ] **Step 2: Emit one JSON diff per paper**
- [ ] **Step 3: Write markdown roll-up**
- [ ] **Step 4: Commit**

```bash
git add project/current/2026-07-03-vnext-cutover-diff-review.md project/current/vnext-cutover-diffs/ scripts/dev/compare_figure_inventory_corpus.py
git commit -m "analysis(ocr): generate vnext cutover diff review package"
```

### Task 4: Regression triage and fix wave

**Rationale:** Any unexplained regression blocks cutover. This task is intentionally open-ended but still bounded: only fix issues surfaced by the cutover diff package and required tests.

**Inputs:**
- `project/current/2026-07-03-vnext-cutover-diff-review.md`
- per-paper diff JSONs

**Outputs:**
- code fixes as needed
- updated diff reports after fixes
- written explanation for every remaining difference judged acceptable

**Rules:**
- If a previously confident legacy figure disappears in vnext, fix or explicitly explain it.
- If vnext consumes the same asset twice, fix immediately.
- If an owned asset appears in unresolved clusters, fix immediately.
- If vnext matches more figures than legacy using the same consumed asset set, that is **not automatically a bug**; it needs manual adjudication and written justification.

- [ ] **Step 1: Triage every non-parity paper**
- [ ] **Step 2: Fix real regressions**
- [ ] **Step 3: Re-run targeted paper diffs and affected tests**
- [ ] **Step 4: Update roll-up verdicts (`equivalent | better | regression`)**
- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ tests/ project/current/2026-07-03-vnext-cutover-diff-review.md project/current/vnext-cutover-diffs/
git commit -m "fix(ocr): resolve cutover diff regressions"
```

### Task 5: Gate verification sweep

**Rationale:** Spec §9 cutover gates require contract compatibility, regression suite pass, real-paper diff review, and diagnostics superiority.

**Checks:**

**Gate 1 — contract**
- Explicitly verify `FigureInventory` schema keys expected by downstream code remain present.

**Gate 2 — regression suite**
Run:
```bash
python -m pytest tests/test_ocr_figure_vnext_*.py -q
python -m pytest tests/test_ocr_figures.py tests/test_ocr_render.py -q
```

**Gate 3 — real-paper diff review**
- Every paper in the cutover corpus must be marked `equivalent` or `better`.
- No unexplained regression may remain.

**Gate 4 — diagnostics superiority**
- Confirm vnext exposes:
  - claim journal
  - ownership conflict explanation
  - pass-level invariants
  - completeness accounting trace

**Artifact:**
- Create: `project/current/2026-07-03-vnext-cutover-gate-checklist.md`

- [ ] **Step 1: Run contract + test gates**
- [ ] **Step 2: Complete gate checklist markdown**
- [ ] **Step 3: Commit**

```bash
git add project/current/2026-07-03-vnext-cutover-gate-checklist.md
git commit -m "test(ocr): complete vnext cutover gate verification"
```

### Task 6: Default wrapper switch (only if Tasks 1-5 are all green)

**Rationale:** This is the only behavior-changing production step. It should happen last.

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `tests/test_ocr_figures.py`

**Change:**
```python
def build_figure_inventory(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]:
    return build_figure_inventory_vnext(structured_blocks, page_width)
```

**Tests:**
- Update wrapper tests so the stable public wrapper is now asserted to call vnext.
- Keep `build_figure_inventory_legacy(...)` callable for comparison tooling.

**Verification:**
```bash
python -m pytest tests/test_ocr_figure_vnext_*.py -q
python -m pytest tests/test_ocr_figures.py tests/test_ocr_render.py -q
```

- [ ] **Step 1: Flip wrapper to vnext**
- [ ] **Step 2: Update wrapper contract tests**
- [ ] **Step 3: Re-run final gates**
- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py
git commit -m "feat(ocr): switch build_figure_inventory wrapper to vnext"
```

## Self-Review

- This plan does **not** assume vnext is already safe to switch on; it treats cutover as gated.
- Current evidence suggests vnext is **promising**, not yet fully certified:
  - no production regression today because wrapper still points at legacy
  - parity on 2 repo fixtures
  - one plausible improvement (`DWQQK2YB`) still needs written adjudication
  - comparison corpus required by spec §8.3 is not yet complete
- After Task 6, no architecture work remains — only normal stabilization and future heuristic tuning.

## Execution Handoff

Recommended execution order:
- Task 1
- Task 2
- Task 3
- Task 4
- Task 5
- Task 6 (only if all prior tasks pass)

Tasks 2-4 are analysis/reporting-heavy; they can be partially parallelized once the expanded compare harness exists.
