# Local Pairing And Fallback Governance — Full Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `subagent-driven-development` or `executing-plans`.

**Purpose:** This is the executable companion to the umbrella roadmap at `docs/superpowers/plans/2026-06-22-local-pairing-and-fallback-governance-implementation.md`. Unlike the roadmap, this document is intended to be actionable end-to-end by another agent in one development run, while still keeping internal stages explicit and test-gated.

**Primary governance spec:** `docs/superpowers/specs/2026-06-22-local-pairing-and-fallback-governance-design.md`

**Upstream specs that must already hold in the branch before continuing:**
- `docs/superpowers/specs/2026-06-22-caption-independent-figure-grouping-design.md`
- `docs/superpowers/specs/2026-06-22-group-first-cross-page-figure-caption-matching-design.md`

**Roadmap this executes:** `docs/superpowers/plans/2026-06-22-local-pairing-and-fallback-governance-implementation.md`

---

## 0. Hard Execution Rules

1. Execute in order. Do not jump ahead.
2. After each stage, run the listed verification before proceeding.
3. If a stage fails its exit criteria, stop and fix that stage before moving on.
4. Update `PROJECT-MANAGEMENT.md` immediately after each landed fix group.
5. Do not invent new broad scoring. Use ownership guards and contract completion first.
6. Do not silently expand scope beyond the stage being executed.

---

## 1. Files In Scope

Primary:
- `paperforge/worker/ocr_figures.py`

Secondary / contract surfaces:
- `paperforge/worker/ocr_figure_reader.py`
- `paperforge/worker/ocr_render.py`
- `paperforge/worker/ocr_tables.py`

Tests:
- `tests/test_ocr_figures.py`
- `tests/test_ocr_figure_reader.py`
- `tests/test_ocr_render.py`
- `tests/test_ocr_real_paper_regressions.py`

Docs / log:
- `PROJECT-MANAGEMENT.md`

Live verification targets:
- `D:/L/OB/Literature-hub`
- `2HEUD5P9`
- `SAN9AYVR`

Additional observational paper families to keep in mind while writing tests / guards:
- `3FDT9652`
- `6FGDBFQN`
- `8VB9ZVQG`
- `24YKLTHQ`

---

## 2. Stage 0 — Preflight / Dependency Gate

### Goal
Confirm the branch already contains the two prerequisite foundations so this plan does not accidentally re-implement them.

### Required checks

- [ ] Confirm semantic grouping is already caption-independent
  - Evidence expected: `_build_semantic_figure_groups_from_assets()` exists and feeds `candidate_groups`
- [ ] Confirm reserve-before-greedy-commit foundations already exist
  - Evidence expected: ledger/residual/reserved helpers exist and same-page loop skips reserved legends/groups
- [ ] Confirm previously repaired cross-page rendering still works

### Verification commands

```bash
python -m pytest tests/test_ocr_figures.py -k "semantic_grouping or reservation or cross_page_backward" -v --tb=short
python -m pytest tests/test_ocr_figure_reader.py tests/test_ocr_render.py -k "cross_page" -v --tb=short
```

### If Stage 0 fails
Produce a short dependency report containing:
1. missing foundation
2. evidence / failing test / missing helper
3. prerequisite plan to run next

Hard rule:

```text
If Stage 0 fails, stop. Do not modify production code in this run.
```

### Exit criteria
- [ ] All prerequisite seams exist and tests are green

---

## 3. Stage A — Ownership Registry Mirror (Behavior-Preserving)

### Goal
Introduce explicit ownership/state surfaces without changing `matched_figures` output yet.

### Required implementation

- [ ] Add a registry/helper API instead of scattered dict/set mutation
- [ ] Keep current `used_group_ids` / `used_asset_page_ids` behavior intact
- [ ] Mirror existing used sets rather than replacing them in this stage

Suggested API surface:

```python
class FigureOwnershipRegistry:
    def reserve_group(self, group_id: str, *, reason: str) -> None: ...
    def match_group(self, group: dict, *, owner_id: str, owner_family: str) -> None: ...
    def mark_assets_owned(self, asset_ids: list[tuple[int, str]], *, owner_id: str, owner_family: str) -> None: ...
    def block_asset(self, asset_id: tuple[int, str], *, reason: str) -> None: ...
    def can_consume_group(self, group: dict) -> bool: ...
    def can_consume_assets(self, asset_ids: list[tuple[int, str]]) -> bool: ...
    def transition_reserved_to_held(self, group_id: str, *, reason: str) -> None: ...
```

### Required state rules

Group-level transitions:

```text
unowned -> reserved
unowned -> matched
unowned -> ambiguous
reserved -> matched
reserved -> ambiguous
reserved -> held
reserved -> unowned only via explicit audited release
matched -> terminal
ambiguous/held -> terminal unless explicit audited release
```

Asset-level transitions:

```text
unowned -> reserved_by_group
unowned -> owned_by_figure
unowned -> owned_by_table
unowned -> blocked(reason)
reserved_by_group -> owned_by_figure
reserved_by_group -> held/blocked(reason)
owned_by_figure / owned_by_table -> terminal
```

### Tests to add

- [ ] blocked asset always carries explicit reason
- [ ] one asset cannot be both figure-owned and table-owned in registry state
- [ ] registry mirror agrees with current used sets on existing green cases

### Verification commands

```bash
python -m pytest tests/test_ocr_figures.py -k "ownership or blocked or grouped" -v --tb=short
python -m pytest tests/test_ocr_figures.py -v --tb=short
```

### `PROJECT-MANAGEMENT.md`
Add a new subsection for Stage A documenting:
- problem
- root cause
- fix
- result
- tests

### Exit criteria
- [ ] behavior-preserving: current figure ownership outputs unchanged on existing green tests
- [ ] ownership/state seams exist and are test-backed

---

## 4. Stage B — Local Pairing Hypothesis Surface (Behavior-Preserving)

### Goal
Represent `caption_below`, `caption_above`, and `caption_sidecar` as explicit local hypotheses without changing ownership output yet.

### Required implementation

- [ ] Add hypothesis helper, for example:

```python
def _make_local_pairing_hypothesis(
    legend: dict,
    group: dict,
    *,
    mode: str,
    local_score: float,
    evidence: list[str] | None = None,
    conflicts: list[str] | None = None,
) -> dict:
    ...
```

- [ ] Generate local hypotheses side-effect free
- [ ] Do not update `used_group_ids` or `used_asset_page_ids` here
- [ ] Do not yet replace commit behavior

### Tests to add

Synthetic-first:
- [ ] `caption_below` case
- [ ] `caption_above` case
- [ ] single-figure sidecar case
- [ ] mixed page with below + sidecar hypotheses

### Verification commands

```bash
python -m pytest tests/test_ocr_figures.py -k "caption_below or caption_above or sidecar" -v --tb=short
python -m pytest tests/test_ocr_figures.py -v --tb=short
```

### `PROJECT-MANAGEMENT.md`
Add a new subsection for Stage B.

### Exit criteria
- [ ] behavior-preserving: no ownership output change yet
- [ ] explicit hypothesis objects exist and are test-backed

---

## 5. Stage C — Reservation-Aware Same-Page Commit Gate

### Goal
Install the minimal commit gate that separates local hypothesis evaluation from ownership mutation.

### Required implementation

- [ ] Keep current same-page candidate scoring order
- [ ] Convert selected candidate into a local hypothesis object
- [ ] Before appending to `matched_figures` / updating used sets, call registry commit gate
- [ ] If legend/group is reserved, defer instead of commit

Deferred reserved objects rule:

```text
Deferred reserved legends/groups remain in reserved/residual flow.
Do not append them to ambiguous_figures merely because same-page commit was withheld.
Only settlement failure may transition them to ambiguous/held.
```

### Tests to add

- [ ] `2HEUD5P9`-style reserve-before-greedy-commit
- [ ] plausible same-page hypothesis withheld by reservation
- [ ] non-reserved same-page pair still commits normally

### Verification commands

```bash
python -m pytest tests/test_ocr_figures.py -k "reservation or cross_page_backward or 2HEUD5P9" -v --tb=short
python -m pytest tests/test_ocr_figures.py tests/test_ocr_figure_reader.py tests/test_ocr_render.py -q
python -m paperforge --vault "D:/L/OB/Literature-hub" ocr rebuild 2HEUD5P9
```

### `PROJECT-MANAGEMENT.md`
Add a new subsection for Stage C.

### Exit criteria
- [ ] reserve outranks same-page commit on imbalanced pages
- [ ] no regression on `2HEUD5P9`

---

## 6. Stage D1 — Shared Fallback Eligibility Helpers

### Goal
Introduce common eligibility helpers before touching any individual fallback behavior.

### Required implementation

- [ ] Add helpers such as:

```python
_fallback_eligible_asset_page_ids(...)
_fallback_eligible_groups(...)
_fallback_can_consume(...)
```

- [ ] No broad scoring changes in this stage

### Tests to add

- [ ] each helper rejects pre-owned objects
- [ ] grouped assets remain unavailable to fallback unless explicitly allowed

### Verification commands

```bash
python -m pytest tests/test_ocr_figures.py -k "fallback and eligible" -v --tb=short
```

### Exit criteria
- [ ] helper layer exists and is green

---

## 7. Stage D2 — Sidecar Fallback Guard

### Goal
Fix the highest-risk ownership-stealing fallback first.

### Required implementation

- [ ] Sidecar consumes only still-unowned local assets/groups
- [ ] Sidecar may not repartition the whole page after ownership exists
- [ ] Use row-coupled local conditions; do not trigger from “two narrow captions” alone

### Tests to add

- [ ] true sidecar case (`6FGDBFQN`-like)
- [ ] non-sidecar multi-column page must not false-trigger (`3FDT9652`-like)
- [ ] mixed page with one sidecar pair and one ordinary below pair
- [ ] pre-owned object test: sidecar cannot consume already matched/reserved assets

### Verification commands

```bash
python -m pytest tests/test_ocr_figures.py -k "6FGDBFQN or sidecar or 3FDT9652" -v --tb=short
python -m pytest tests/test_ocr_real_paper_regressions.py -k "6FGDBFQN or 3FDT9652" -v --tb=short
```

### `PROJECT-MANAGEMENT.md`
Add a new subsection for Stage D2.

### Exit criteria
- [ ] sidecar no longer steals whole-page owned assets
- [ ] true sidecar still works

---

## 8. Stage D3 — `legend_bundle` Fallback Guard

### Goal
Keep preproof / ancient-layout recovery narrow and ownership-safe.

### Required implementation

- [ ] Grouped assets remain unavailable to bundle fallback
- [ ] Interruption rules remain honored
- [ ] Bundle consumes only eligible post-legend unowned asset/group pages

### Tests to add

- [ ] grouped assets are skipped
- [ ] body/table/reference interruption blocks bundle fallback
- [ ] pre-owned object test for bundle path

### Verification commands

```bash
python -m pytest tests/test_ocr_figures.py -k "legend_bundle" -v --tb=short
```

### `PROJECT-MANAGEMENT.md`
Add a new subsection for Stage D3.

### Exit criteria
- [ ] bundle path respects ownership and interruption constraints

---

## 9. Stage D4 — `group_sequential` / old `sequential` Guard

### Goal
Keep both sequential layers from crossing ownership boundaries.

### Required implementation

- [ ] `group_sequential` may consume unowned semantic groups, including `single_asset` groups
- [ ] It may not split multi-asset groups or override stronger ownership
- [ ] Old `sequential` remains restricted to bare assets outside semantic groups, or explicit single-asset compatibility path

### Tests to add

- [ ] `group_sequential` does not split multi-asset groups
- [ ] old sequential cannot consume grouped assets
- [ ] pre-owned object tests for both paths

### Verification commands

```bash
python -m pytest tests/test_ocr_figures.py -k "group_sequential or sequential" -v --tb=short
```

### `PROJECT-MANAGEMENT.md`
Add a new subsection for Stage D4.

### Exit criteria
- [ ] both sequential paths obey ownership boundaries

---

## 10. Stage D5 — `sequence_match` Contract

### Goal
Make `sequence_match` either a real contract or not a match.

### Required implementation

- [ ] Promotion may not invent ownership from caption order alone
- [ ] Promoted entries must include full matched-figure contract:

```text
page
legend_page
asset_pages
matched_assets
asset_block_ids
settlement_type
```

- [ ] If that payload cannot be formed, stay ambiguous/held instead of promoting

### Tests to add

- [ ] no promotion without real asset ownership payload
- [ ] promoted sequence matches carry full fields

### Verification commands

```bash
python -m pytest tests/test_ocr_figures.py tests/test_ocr_figure_reader.py -k "sequence_match" -v --tb=short
```

### `PROJECT-MANAGEMENT.md`
Add a new subsection for Stage D5.

### Exit criteria
- [ ] sequence_match is either a real contract or not a match

---

## 11. Stage E — Figure/Table Ownership Conflict Surface

### Goal
Add global figure/table conflict surfacing, starting conservatively with post-hoc conflict reporting.

### Required implementation

- [ ] collect figure-owned asset IDs
- [ ] collect table-owned asset IDs
- [ ] emit `ownership_conflict` records instead of silent duplication

Suggested helpers:

```python
def _collect_figure_owned_asset_ids(figure_inventory: dict) -> set[tuple[int, str]]: ...
def _collect_table_owned_asset_ids(table_inventory: dict) -> set[tuple[int, str]]: ...
def _build_ownership_conflicts(...) -> list[dict]: ...
```

### Tests to add

- [ ] conflict surface exists when one block is claimed by both figure and table
- [ ] no silent duplicate ownership on mixed pages

### Verification commands

```bash
python -m pytest tests/test_ocr_figures.py -k "ownership_conflict or table" -v --tb=short
```

### `PROJECT-MANAGEMENT.md`
Add a new subsection for Stage E.

### Exit criteria
- [ ] one-owner rule has at least a post-hoc explicit conflict surface

---

## 12. Full Test Strategy

### Synthetic-first

- [ ] local `caption_below` hypothesis
- [ ] local `caption_above` hypothesis
- [ ] local sidecar hypothesis
- [ ] mixed page with sidecar + below hypotheses
- [ ] reserve-before-commit case
- [ ] reserved failure transition to ambiguous/held or audited release
- [ ] each fallback rejects pre-owned objects
- [ ] `sequence_match` requires complete ownership payload
- [ ] figure/table conflict surface emitted

### Real-paper observational second

- [ ] `3FDT9652`
- [ ] `6FGDBFQN`
- [ ] `8VB9ZVQG`
- [ ] `24YKLTHQ`
- [ ] `2HEUD5P9`
- [ ] `SAN9AYVR`

---

## 13. Verification Commands

```bash
python -m pytest tests/test_ocr_figures.py -v --tb=short
python -m pytest tests/test_ocr_figure_reader.py tests/test_ocr_render.py -v --tb=short
python -m pytest tests/test_ocr_real_paper_regressions.py -v --tb=short
python -m paperforge --vault "D:/L/OB/Literature-hub" ocr rebuild 2HEUD5P9
python -m paperforge --vault "D:/L/OB/Literature-hub" ocr rebuild SAN9AYVR
```

---

## 14. Exit Criteria

This execution plan is complete only when:

1. Stage 0 passed and documented its evidence
2. Stage A and B remained behavior-preserving scaffolding stages
3. reservation-aware commit gate exists before major fallback rewiring
4. each fallback class obeys the same ownership guards
5. `sequence_match` is either a real contract or not a match
6. figure/table one-owner rule has at least a post-hoc conflict surface
7. canonical layout families remain stable under verification
