# Local Pairing And Fallback Governance — Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: use `subagent-driven-development` or `executing-plans`.

**Goal:** Implement the governance model from `2026-06-22-local-pairing-and-fallback-governance-design.md` in small, reversible stages. This document is an umbrella roadmap, not a single all-at-once execution plan.

**Primary Spec:** `docs/superpowers/specs/2026-06-22-local-pairing-and-fallback-governance-design.md`

**Depends on:**
- `docs/superpowers/specs/2026-06-22-caption-independent-figure-grouping-design.md`
- `docs/superpowers/specs/2026-06-22-group-first-cross-page-figure-caption-matching-design.md`

---

## 1. Roadmap Positioning

This document must not be treated as:

```text
one execution task for one agent in one pass
```

It should be treated as:

```text
umbrella implementation roadmap
```

Execution should happen as multiple smaller plans / PR-sized stages.

The key reason is blast radius:

```text
ownership registry
+ local pairing hypotheses
+ reservation-aware commit
+ sidecar / bundle / sequential rewiring
+ table conflict handling
```

is too much for one direct execution pass.

---

## 2. Stage Structure

The roadmap is intentionally split into:

```text
Stage 0: Preflight / dependency gate
Stage A: Ownership registry mirror (behavior-preserving)
Stage B: Local pairing hypothesis surface (behavior-preserving)
Stage C: Reservation-aware same-page commit gate
Stage D1: Shared fallback eligibility helpers
Stage D2: Sidecar fallback guard
Stage D3: legend_bundle fallback guard
Stage D4: group_sequential / old sequential guard
Stage D5: sequence_match contract
Stage E: figure/table ownership conflict surface
```

Stages A and B are scaffolding stages.
They must not materially change matched ownership output.

---

## 3. Stage 0 — Preflight / Dependency Gate

**Purpose:** make sure this roadmap is not being applied on a branch that still lacks the prerequisite foundations.

Before any implementation from this roadmap:

- [ ] verify semantic grouping is already caption-independent
- [ ] verify ledger / reservation / cross-page settlement helpers already exist in the current branch
- [ ] run current regression checks for `2HEUD5P9` and `SAN9AYVR`
- [ ] if either foundation is missing, stop and execute the prerequisite plan first

If Stage 0 fails, produce a short dependency report containing:

1. the missing foundation
2. the evidence / failing test / missing helper
3. the prerequisite plan that should run next

Hard rule:

```text
if Stage 0 fails, do not modify production code in this roadmap run
```

Required checks:

```text
semantic_groups exist and feed candidate_groups
reserve-before-greedy-commit behavior already exists
cross-page figure render dedup still passes
```

If this gate fails, do not continue with later stages.

---

## 4. Stage A — Ownership Registry Mirror (Behavior-Preserving)

**Purpose:** introduce explicit ownership/state surfaces without yet changing ownership decisions.

**Files likely touched:**
- `paperforge/worker/ocr_figures.py`
- maybe helper files if extraction is needed
- `tests/test_ocr_figures.py`

### Requirements

- [ ] add ownership registry/helper API rather than scattered dict mutation
- [ ] state changes must go through helper calls, not direct branch-local mutation
- [ ] preserve current output behavior

Mirror rule:

```text
In Stage A, the registry mirrors existing used_group_ids / used_asset_page_ids.
Those existing sets remain source-compatible for behavior.
Registry assertions may compare against them, but Stage A must not require replacing them yet.
```

Suggested surface:

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

### State transition table to enforce

Group-level:

```text
unowned -> reserved
unowned -> matched
unowned -> ambiguous
reserved -> matched
reserved -> ambiguous
reserved -> held
reserved -> unowned only through explicit audited_release
matched -> terminal
ambiguous/held -> terminal unless explicitly audited_release
```

Asset-level:

```text
unowned -> reserved_by_group
unowned -> owned_by_figure
unowned -> owned_by_table
unowned -> blocked(reason)
reserved_by_group -> owned_by_figure
reserved_by_group -> held/blocked(reason)
owned_by_figure / owned_by_table -> terminal
```

### Tests

- [ ] blocked assets always carry explicit reasons
- [ ] one asset cannot be both figure-owned and table-owned in registry state
- [ ] behavior-preserving: matched ownership output is unchanged vs current branch

---

## 5. Stage B — Local Pairing Hypothesis Surface (Behavior-Preserving)

**Purpose:** introduce explicit hypothesis objects without changing ownership commit behavior yet.

**Files likely touched:**
- `paperforge/worker/ocr_figures.py`
- `tests/test_ocr_figures.py`

### Requirements

- [ ] local pairing modes produce explicit hypothesis objects
- [ ] hypothesis generation is side-effect free
- [ ] no ownership output change yet

Minimum helper:

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

Hard rule:

```text
Stage B only introduces hypothesis objects and tests.
It must not change ownership commit behavior except through a later explicit Stage C commit gate.
```

### Tests

- [ ] synthetic `caption_below` case
- [ ] synthetic `caption_above` case
- [ ] synthetic single-figure sidecar case
- [ ] mixed page with below + sidecar hypotheses
- [ ] behavior-preserving: matched ownership output unchanged vs current branch

---

## 6. Stage C — Reservation-Aware Same-Page Commit Gate

**Purpose:** install the minimal commit gate that separates local evaluation from ownership mutation.

**Files likely touched:**
- `paperforge/worker/ocr_figures.py`
- `tests/test_ocr_figures.py`

### Minimal path

- [ ] keep current same-page candidate scoring order
- [ ] convert the selected candidate into a local hypothesis object
- [ ] before appending to `matched_figures` / updating used sets, call the registry commit gate
- [ ] if legend/group is reserved, defer instead of commit

Deferred reserved object rule:

```text
deferred reserved legends/groups remain in the existing reserved/residual flow used by cross-page settlement.
do not append them to ambiguous_figures merely because same-page commit was withheld.
only settlement failure may transition them to ambiguous/held.
```

This stage should not become a full same-page matcher rewrite.

### Required rule

```text
reservation state outranks same-page commit on imbalanced pages
```

### Tests

- [ ] `2HEUD5P9`-style reserve-before-greedy-commit
- [ ] plausible same-page hypothesis exists but is withheld due to reservation
- [ ] non-reserved same-page hypothesis still commits normally

---

## 7. Stage D1 — Shared Fallback Eligibility Helpers

**Purpose:** unify the basic ownership checks before changing fallback behavior.

**Files likely touched:**
- `paperforge/worker/ocr_figures.py`
- `tests/test_ocr_figures.py`

- [ ] add helpers such as:

```python
_fallback_eligible_asset_page_ids(...)
_fallback_eligible_groups(...)
_fallback_can_consume(...)
```

- [ ] no broad scoring changes
- [ ] no fallback behavior expansion yet

### Tests

- [ ] each helper rejects pre-owned objects
- [ ] grouped assets remain unavailable to late fallback unless explicitly allowed

---

## 8. Stage D2 — Sidecar Fallback Guard

**Purpose:** fix the most dangerous ownership-stealing fallback first.

**Files likely touched:**
- `paperforge/worker/ocr_figures.py`
- `tests/test_ocr_figures.py`
- maybe `tests/test_ocr_real_paper_regressions.py`

### Requirements

- [ ] sidecar consumes only still-unowned local assets/groups
- [ ] it may not repartition the whole page after ownership exists
- [ ] it must not rely only on "two narrow captions"; use row-coupled local conditions

Substage isolation rule:

```text
Stage D2 may modify only sidecar fallback plus shared eligibility helpers.
Do not opportunistically adjust legend_bundle, sequential, or sequence_match logic in the same substage.
```

### Tests

- [ ] true sidecar case (`6FGDBFQN`-like)
- [ ] non-sidecar multi-column page must not false-trigger (`3FDT9652`-like)
- [ ] mixed page with one sidecar pair and one ordinary below pair
- [ ] pre-owned object test: sidecar cannot consume already matched/reserved assets

---

## 9. Stage D3 — `legend_bundle` Fallback Guard

**Purpose:** keep preproof/ancient-layout recovery narrow and ownership-safe.

### Requirements

- [ ] grouped assets remain unavailable to bundle fallback
- [ ] interruptions remain honored
- [ ] fallback consumes only eligible post-legend unowned asset/group pages

Substage isolation rule:

```text
Stage D3 may modify only legend_bundle fallback plus shared eligibility helpers.
Do not opportunistically adjust sidecar, sequential, or sequence_match logic in the same substage.
```

### Tests

- [ ] grouped assets are skipped
- [ ] strong body/table/reference interruption blocks bundle fallback
- [ ] pre-owned object test for bundle path

---

## 10. Stage D4 — `group_sequential` / old `sequential` Guard

**Purpose:** keep the two sequential layers from crossing ownership boundaries.

### Requirements

- [ ] `group_sequential` may consume unowned semantic groups, including `single_asset` groups
- [ ] it may not split multi-asset groups or override stronger ownership
- [ ] old `sequential` remains restricted to bare assets outside semantic groups, or an explicitly allowed single-asset compatibility path

Substage isolation rule:

```text
Stage D4 may modify only group_sequential / old sequential plus shared eligibility helpers.
Do not opportunistically adjust sidecar, legend_bundle, or sequence_match logic in the same substage.
```

### Tests

- [ ] `group_sequential` does not split multi-asset groups
- [ ] old sequential cannot consume grouped assets
- [ ] pre-owned object tests for both paths

---

## 11. Stage D5 — `sequence_match` Contract

**Purpose:** make `sequence_match` either a real contract or not a match.

### Requirements

- [ ] promotion may not invent ownership from caption order alone
- [ ] promoted entries must include full matched-figure contract:

```text
page
legend_page
asset_pages
matched_assets
asset_block_ids
settlement_type
```

- [ ] if that payload cannot be formed, stay ambiguous/held instead of promoting

Substage isolation rule:

```text
Stage D5 may modify only sequence_match promotion plus any shared contract helpers strictly required for it.
Do not opportunistically adjust sidecar, legend_bundle, or sequential fallback logic in the same substage.
```

### Tests

- [ ] no promotion without real asset ownership payload
- [ ] promoted sequence matches carry full fields

---

## 12. Stage E — Figure/Table Ownership Conflict Surface

**Purpose:** add global figure/table conflict surfacing, preferably as a separate later sub-plan.

This stage should begin with post-hoc conflict emission, not immediate reordering of table/figure match pipelines.

### Minimum first step

- [ ] collect figure-owned asset IDs
- [ ] collect table-owned asset IDs
- [ ] emit `ownership_conflict` records instead of silent duplication

Suggested helpers:

```python
def _collect_figure_owned_asset_ids(figure_inventory: dict) -> set[tuple[int, str]]: ...
def _collect_table_owned_asset_ids(table_inventory: dict) -> set[tuple[int, str]]: ...
def _build_ownership_conflicts(...) -> list[dict]: ...
```

### Tests

- [ ] conflict surface exists when one block is claimed by both figure and table
- [ ] no silent duplicate ownership on mixed pages

---

## 13. Test Strategy

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

## 14. Verification Commands

```bash
python -m pytest tests/test_ocr_figures.py -v --tb=short
python -m pytest tests/test_ocr_figure_reader.py tests/test_ocr_render.py -v --tb=short
python -m pytest tests/test_ocr_real_paper_regressions.py -v --tb=short
python -m paperforge --vault "D:/L/OB/Literature-hub" ocr rebuild 2HEUD5P9
python -m paperforge --vault "D:/L/OB/Literature-hub" ocr rebuild SAN9AYVR
```

---

## 15. Exit Criteria

This roadmap is complete only when:

1. ownership state is explicit and changed only through helper APIs
2. Stage A and B are behavior-preserving scaffolding layers
3. reservation-aware commit gate exists before major fallback rewiring
4. each fallback class obeys the same ownership guards
5. `sequence_match` is either a real contract or not a match
6. figure/table one-owner rule has at least a post-hoc conflict surface
7. canonical layout families remain stable under verification
