# OCR Phase 4.1 Cleanup And Phase 5 Search/Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** First correct the remaining Phase 4 runtime semantics so version-state and rebuild behavior are trustworthy, then add Phase 5 role-based search and agent evidence outputs that consume structured OCR artifacts instead of relying only on flat fulltext or generic vector chunks.

**Architecture:** Treat this as one continuous plan with two layers. Phase 4.1 is a small correctness cleanup: preserve `raw_upgradable` across derived-only rebuilds, move derived rebuild fanout off the critical sync path, and resolve the remaining dirty-runtime-file execution risk before automation depends on it. Phase 5 then adds a role-aware OCR search index and evidence object layer over `blocks.structured.jsonl`, `resolved_metadata.json`, figure/table inventories, and object markdown so `search`, `retrieve`, and `paper-context` can answer with structured provenance rather than only metadata rows or opaque vector chunks.

**Tech Stack:** Python, pytest, current PaperForge OCR pipeline artifacts, SQLite/Memory Layer, existing search/retrieve/context commands, PFResult JSON contracts

---

## File Structure

This combined plan should establish or modify these units:

- `paperforge/worker/ocr_rebuild.py`
  - Phase 4.1 fix: derived rebuild must not clear raw-upgrade state.
- `paperforge/services/sync_service.py`
  - Phase 4.1 fix: derived rebuild orchestration becomes non-blocking or deferred.
- `paperforge/worker/ocr_runtime.py`
  - If not already present, new compact runtime-state helper module for derived rebuild queue/snapshot handling.
- `paperforge/worker/ocr_index.py`
  - New Phase 5 module for role-based OCR search index generation from structured artifacts.
- `paperforge/worker/ocr_evidence.py`
  - New Phase 5 module for evidence object building and normalization.
- `paperforge/memory/schema.py`
  - Extend schema if OCR role-aware evidence/index tables belong in SQLite rather than sidecar JSONL only.
- `paperforge/memory/builder.py`
  - Integrate OCR role/evidence indexing into memory rebuild if SQLite is chosen as the storage layer.
- `paperforge/commands/search.py`
  - Extend to route metadata queries vs OCR structure queries.
- `paperforge/commands/retrieve.py`
  - Extend to return evidence-aware results and route by query intent when structured evidence is a better fit than semantic chunks.
- `paperforge/commands/paper_context.py`
  - Extend to include OCR evidence summary and object paths where useful.
- `paperforge/query_planning.py`
  - Extend intent routing so query-plan can recommend metadata search, OCR evidence search, or vector retrieval more precisely.
- `tests/test_ocr_phase41_cleanup.py`
  - New tests for Phase 4.1 runtime corrections.
- `tests/test_ocr_index.py`
  - New tests for role-based OCR indexing.
- `tests/test_ocr_evidence.py`
  - New tests for evidence object building.
- `tests/test_search_command_diagnostics.py`
  - Extend or create tests for structured OCR search routing.
- `tests/test_retrieve_evidence.py`
  - New tests for retrieve/evidence routing behavior.
- `tests/test_paper_context_evidence.py`
  - New tests for evidence summary in paper-context.

Rationale:

- Phase 4.1 must be finished before Phase 5 uses runtime version state as reliable control flow.
- Phase 5 should not be implemented by piling more heuristics onto vector chunks or memory FTS alone.
- The structured OCR artifact layer now exists; search and evidence should consume it directly.

## Part A: Phase 4.1 Cleanup

### Task 1: Lock The Remaining Runtime Semantics In Tests

**Files:**
- Create: `tests/test_ocr_phase41_cleanup.py`
- Modify: `tests/test_ocr_rebuild.py`
- Modify: `tests/test_sync_service_ocr_versions.py`

- [ ] **Step 1: Write the failing derived-rebuild state test**

```python
from __future__ import annotations


def test_derived_rebuild_does_not_clear_raw_upgradable(tmp_path):
    from paperforge.worker.ocr_rebuild import _apply_post_rebuild_version_flags

    meta = {
        "derived_stale": True,
        "raw_upgradable": True,
    }

    updated = _apply_post_rebuild_version_flags(meta)

    assert updated["derived_stale"] is False
    assert updated["raw_upgradable"] is True
```

- [ ] **Step 2: Write the failing sync non-blocking test**

```python
def test_sync_runtime_summary_can_schedule_derived_rebuild_without_inline_execution():
    from paperforge.services.sync_service import summarize_ocr_runtime_followups

    summary = summarize_ocr_runtime_followups(
        papers=[
            {"zotero_key": "A", "derived_stale": True, "raw_upgradable": False},
            {"zotero_key": "B", "derived_stale": False, "raw_upgradable": True},
        ]
    )

    assert summary["derived_rebuild_count"] == 1
    assert summary["derived_rebuild_mode"] in {"deferred", "queued", "best_effort"}
```

- [ ] **Step 3: Write the failing dirty-runtime preflight escalation test**

Add a test asserting that watched dirty runtime files suppress auto-derived rebuild execution, while still allowing sync to succeed with warnings.

- [ ] **Step 4: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_phase41_cleanup.py tests/test_ocr_rebuild.py tests/test_sync_service_ocr_versions.py -q`
Expected: FAIL because the current implementation clears `raw_upgradable` and executes derived rebuild inline.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ocr_phase41_cleanup.py tests/test_ocr_rebuild.py tests/test_sync_service_ocr_versions.py
git commit -m "test: lock OCR phase4.1 runtime cleanup semantics"
```

### Task 2: Fix Derived-Rebuild Version Flag Semantics

**Files:**
- Modify: `paperforge/worker/ocr_rebuild.py`
- Test: `tests/test_ocr_phase41_cleanup.py`

- [ ] **Step 1: Extract the post-rebuild flag update into a small helper**

Refactor:

```python
def _apply_post_rebuild_version_flags(meta: dict) -> dict:
    ...
```

Rules:

- `derived_stale` becomes `False`
- `raw_upgradable` is preserved
- `version_state_updated_at` is refreshed

- [ ] **Step 2: Use the helper inside `run_derived_rebuild_for_keys()`**

Do not duplicate flag logic inline.

- [ ] **Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_phase41_cleanup.py tests/test_ocr_rebuild.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/ocr_rebuild.py tests/test_ocr_phase41_cleanup.py tests/test_ocr_rebuild.py
git commit -m "fix: preserve raw upgrade state across derived rebuilds"
```

### Task 3: Move Derived Rebuild Off The Critical Sync Path

**Files:**
- Modify: `paperforge/services/sync_service.py`
- Modify: `paperforge/commands/sync.py`
- If needed Create: `paperforge/worker/ocr_runtime.py`
- Test: `tests/test_sync_service_ocr_versions.py`

- [ ] **Step 1: Add a narrow follow-up scheduler abstraction**

Implement a helper such as:

```python
def summarize_ocr_runtime_followups(papers: list[dict]) -> dict:
    ...
```

And a runtime execution mode:

- `deferred`
- `best_effort`
- `suppressed_dirty_runtime`

- [ ] **Step 2: Change sync to record or queue derived rebuild work instead of always executing inline**

Options are acceptable if they stay non-blocking:

- write a queue/snapshot file for later OCR runtime processing
- trigger a background subprocess
- best-effort subprocess with timeout and warning fallback

But sync should no longer depend on the rebuild completing inline.

- [ ] **Step 3: Gate auto-triggering when runtime files are dirty**

If watched OCR runtime files are dirty:

- do not auto-run derived rebuild
- return warnings and a suppressed mode in PFResult

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sync_service_ocr_versions.py tests/test_ocr_phase41_cleanup.py tests/cli/test_json_contracts.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/services/sync_service.py paperforge/commands/sync.py paperforge/worker/ocr_runtime.py tests/test_sync_service_ocr_versions.py tests/test_ocr_phase41_cleanup.py tests/cli/test_json_contracts.py
git commit -m "fix: defer OCR derived rebuilds outside sync critical path"
```

### Task 4: Resolve Or Contain The Dirty Runtime File Risk

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `paperforge/worker/ocr_objects.py`
- Or document/clear their dirty state if changes are intentional

- [ ] **Step 1: Audit the uncommitted changes in `ocr_render.py` and `ocr_objects.py`**

Decide which of these is true:

- the changes are intended and should be committed
- the changes are experimental and should be isolated or discarded by the user

- [ ] **Step 2: If intended, add/adjust tests and commit them**

Prefer a small commit that removes this lingering risk.

- [ ] **Step 3: If not intended, stop auto-runtime fanout from depending on them**

The preflight warning path should remain active until the worktree is clean.

- [ ] **Step 4: Record final state in plan notes**

This task is complete only when the risk is either removed or formally contained.

## Part B: Phase 5 Search And Evidence Layer

### Task 5: Lock Role-Based OCR Index Contract In Tests

**Files:**
- Create: `tests/test_ocr_index.py`
- Modify: `tests/test_ocr.py`
- Reference: `docs/superpowers/specs/2026-06-04-ocr-structured-pipeline-design.md`

- [ ] **Step 1: Write the failing OCR role-index tests**

```python
from __future__ import annotations


def test_role_index_separates_body_caption_table_metadata_reference() -> None:
    from paperforge.worker.ocr_index import build_role_indexes

    structured_blocks = [
        {"paper_id": "KEY001", "page": 1, "block_id": "b1", "role": "body_paragraph", "text": "Methods body"},
        {"paper_id": "KEY001", "page": 1, "block_id": "b2", "role": "figure_caption", "text": "Figure 1. Result"},
        {"paper_id": "KEY001", "page": 1, "block_id": "b3", "role": "table_caption", "text": "Table 1. Data"},
        {"paper_id": "KEY001", "page": 1, "block_id": "b4", "role": "reference_item", "text": "Smith et al. (2024)."},
    ]
    resolved_metadata = {
        "title": {"value": "Paper Title"},
        "doi": {"value": "10.1000/xyz"},
    }

    indexes = build_role_indexes(
        structured_blocks=structured_blocks,
        resolved_metadata=resolved_metadata,
    )

    assert "body" in indexes
    assert "captions" in indexes
    assert "tables" in indexes
    assert "metadata" in indexes
    assert "references" in indexes
```

- [ ] **Step 2: Add an end-to-end artifact assertion**

Extend `tests/test_ocr.py`:

```python
assert (ocr_dir / "index" / "role-index.json").exists()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_index.py tests/test_ocr.py -k role_index -q`
Expected: FAIL because Phase 5 index builder does not exist yet.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ocr_index.py tests/test_ocr.py
git commit -m "test: lock OCR phase5 role index contract"
```

### Task 6: Implement Role-Based OCR Index Builder

**Files:**
- Create: `paperforge/worker/ocr_index.py`
- Modify: `paperforge/worker/ocr.py`
- Test: `tests/test_ocr_index.py`

- [ ] **Step 1: Implement `build_role_indexes()`**

Required buckets:

- `body`
- `captions`
- `tables`
- `metadata`
- `references`
- optionally `all_blocks`

Each indexed item should preserve:

- `paper_id`
- `page`
- `block_id`
- `role`
- `text`
- any object path or evidence reference if available

- [ ] **Step 2: Decide storage format**

Keep Phase 5 simple. A JSON artifact such as `index/role-index.json` is acceptable first.
Only extend SQLite if necessary after the artifact contract is stable.

- [ ] **Step 3: Emit the role index during OCR postprocess and derived rebuild**

Phase 5 should make role indexing rebuildable from Phase 1-3 artifacts, not tied to raw OCR rerun.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_index.py tests/test_ocr.py -k role_index -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_index.py paperforge/worker/ocr.py tests/test_ocr_index.py tests/test_ocr.py
git commit -m "feat: add OCR role-based search index"
```

### Task 7: Lock Evidence Object Contract In Tests

**Files:**
- Create: `tests/test_ocr_evidence.py`
- Modify: `tests/test_paper_context_evidence.py` (create if missing)

- [ ] **Step 1: Write the failing evidence object tests**

```python
from __future__ import annotations


def test_evidence_object_preserves_role_page_confidence_and_asset() -> None:
    from paperforge.worker.ocr_evidence import build_evidence_hit

    hit = build_evidence_hit(
        paper_id="KEY001",
        role="figure_caption",
        page=7,
        block_id="p7_b18",
        text="Figure 3. Results.",
        asset_path="render/figures/figure_003.md",
        confidence=0.84,
        verification="has_page_crop",
    )

    assert hit["source_type"] == "figure_caption"
    assert hit["page"] == 7
    assert hit["asset"] == "render/figures/figure_003.md"
    assert hit["confidence"] == 0.84
```

- [ ] **Step 2: Add a failing paper-context evidence summary test**

Assert that `paper-context` can include an OCR evidence summary or pointers to structured evidence artifacts.

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_evidence.py tests/test_paper_context_evidence.py -q`
Expected: FAIL because evidence helpers do not exist yet.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ocr_evidence.py tests/test_paper_context_evidence.py
git commit -m "test: lock OCR phase5 evidence object contract"
```

### Task 8: Implement OCR Evidence Builder

**Files:**
- Create: `paperforge/worker/ocr_evidence.py`
- Modify: `paperforge/worker/ocr_index.py`
- Modify: `paperforge/commands/paper_context.py`
- Test: `tests/test_ocr_evidence.py`

- [ ] **Step 1: Implement `build_evidence_hit()` and helpers**

Evidence records should preserve:

- `paper_id`
- `source_type`
- `page`
- `block_id`
- `text`
- `asset`
- `confidence`
- `verification`

- [ ] **Step 2: Add evidence conversion for indexed roles**

At minimum support:

- body paragraph
- figure caption
- table caption
- metadata field
- reference item

- [ ] **Step 3: Expose lightweight evidence summary in `paper-context`**

Do not dump entire indexes by default.
Add:

- counts by role
- notable evidence pointers
- object artifact paths where present

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_evidence.py tests/test_paper_context_evidence.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_evidence.py paperforge/worker/ocr_index.py paperforge/commands/paper_context.py tests/test_ocr_evidence.py tests/test_paper_context_evidence.py
git commit -m "feat: add OCR evidence objects and paper-context summary"
```

### Task 9: Extend Query Planning And Search Routing

**Files:**
- Modify: `paperforge/query_planning.py`
- Modify: `paperforge/commands/search.py`
- Modify: `paperforge/commands/retrieve.py`
- Create: `tests/test_search_command_diagnostics.py`
- Create: `tests/test_retrieve_evidence.py`

- [ ] **Step 1: Write the failing routing tests**

Cover at least:

- metadata-style queries -> `search`
- parameter/evidence queries -> OCR role index / evidence route
- vague mechanism/content queries -> semantic `retrieve`

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_search_command_diagnostics.py tests/test_retrieve_evidence.py tests/test_query_plan.py -q`
Expected: FAIL until query routing understands the OCR role index.

- [ ] **Step 3: Extend query-plan runtime suggestions**

Teach `query_plan` to prefer:

- metadata FTS for title/author/year/doi-like queries
- OCR evidence index for exact parameter/supporting-evidence queries
- vector retrieval for broader conceptual content questions

- [ ] **Step 4: Add OCR index lookup path in `search`**

Do not replace current metadata FTS.
Add a structured OCR search mode or auto-route when query-plan indicates evidence search.

- [ ] **Step 5: Add evidence-aware path in `retrieve`**

If the query is better served by OCR evidence than by semantic chunks:

- return structured evidence hits
- include provenance and confidence

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_search_command_diagnostics.py tests/test_retrieve_evidence.py tests/test_query_plan.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add paperforge/query_planning.py paperforge/commands/search.py paperforge/commands/retrieve.py tests/test_search_command_diagnostics.py tests/test_retrieve_evidence.py tests/test_query_plan.py
git commit -m "feat: route search and retrieve through OCR evidence layer"
```

### Task 10: Integrate OCR Role/Evidence Index Into Memory Layer If Needed

**Files:**
- Modify: `paperforge/memory/schema.py`
- Modify: `paperforge/memory/builder.py`
- Modify: `paperforge/memory/fts.py`
- Add tests only if storage extends SQLite

- [ ] **Step 1: Decide whether Phase 5 role/evidence index stays sidecar JSON or enters SQLite**

Prefer the simpler option first.
Use SQLite only if command routing needs transactional or queryable joins that JSON cannot support cleanly.

- [ ] **Step 2: If SQLite is required, add minimal schema extension**

Likely separate tables such as:

- `ocr_blocks_index`
- `ocr_evidence`

Avoid bloating existing `papers` FTS table with role-level OCR content.

- [ ] **Step 3: Integrate memory build or dedicated rebuild path**

Ensure rebuildability from OCR structured artifacts, not from `fulltext.md`.

- [ ] **Step 4: Run tests to verify they pass**

Run: relevant unit tests under `tests/unit/memory/` plus new Phase 5 tests
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/memory/schema.py paperforge/memory/builder.py paperforge/memory/fts.py tests/unit/memory
git commit -m "feat: integrate OCR role evidence into memory layer"
```

### Task 11: Final Verification For Phase 4.1 + Phase 5

**Files:**
- Verify only

- [ ] **Step 1: Run cleanup-focused suite**

Run: `python -m pytest tests/test_ocr_phase41_cleanup.py tests/test_ocr_rebuild.py tests/test_sync_service_ocr_versions.py tests/test_ocr_runtime_preflight.py -q`
Expected: PASS

- [ ] **Step 2: Run Phase 5 focused suite**

Run: `python -m pytest tests/test_ocr_index.py tests/test_ocr_evidence.py tests/test_paper_context_evidence.py tests/test_search_command_diagnostics.py tests/test_retrieve_evidence.py tests/test_query_plan.py -q`
Expected: PASS

- [ ] **Step 3: Run broader OCR/runtime/search regressions**

Run: `python -m pytest tests/test_ocr_versions.py tests/test_ocr_render_v2.py tests/test_ocr_health.py tests/test_ocr.py tests/test_ocr_metadata.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_objects.py tests/test_ocr_state_machine.py tests/test_sync.py tests/test_context.py tests/test_selection_sync_pdf.py tests/test_status.py tests/test_ocr_doctor.py tests/e2e/test_ocr_e2e.py tests/test_ocr_redo.py -q`
Expected: PASS

- [ ] **Step 4: Inspect diff scope**

Run: `git diff -- paperforge docs/superpowers tests`
Expected: changes are limited to runtime cleanup plus OCR search/evidence integration, and do not prematurely introduce Phase 6 UX or other unrelated work.

- [ ] **Step 5: Commit verification-only fixes if needed**

```bash
git add -A
git commit -m "test: finalize OCR phase4.1 cleanup and phase5 evidence search"
```

## Risks To Watch During Execution

1. Do not let derived-only rebuild clear or mask raw-upgrade state.
2. Do not let sync block on expensive derived rebuild fanout.
3. Keep current dirty `ocr_render.py` / `ocr_objects.py` risk explicit until resolved or contained.
4. Do not implement Phase 5 by routing everything back through flat `fulltext.md`.
5. Keep evidence outputs auditable and structured; avoid vague “top chunk” answers when role/page/asset provenance exists.
6. Prefer simpler artifact storage first; only extend SQLite when there is a concrete query-path need.

