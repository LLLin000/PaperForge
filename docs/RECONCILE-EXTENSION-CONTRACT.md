# Reconcile Extension Contract: Core Frozen, Detection Open

- **Status:** APPROVED / INVARIANT
- **Established:** 2026-09-02
- **Scope:** OCR Render Consistency Audit, Reconciliation Engine, and Future Finding Detectors

---

## 1. Context & Architectural Decision

The Reconcile mutation engine is **FROZEN**. It has established a complete, fail-closed, transaction-safe lifecycle:
```text
Observation (Audit)
  ↓
Finding Classification (R / P / BLOCKED)
  ↓
Isolated Staging (r-manifest.json / final-plan.json)
  ↓
Explicit Human/Owner Authority Boundary (promote-r / accept-proposal)
  ↓
CAS / Journal (v2) / Atomic Multi-target Write / Post-audit Rollback
  ↓
Committed Authority Flip (Cleanup / Report failures cannot roll back production)
```

We explicitly freeze this core engine. Further work on edge-case layout heuristics, multi-panel detection, or visual content validation must **NOT** alter the mutation engine, reinvent promotion logic, or bypass the authority boundary. Instead, new detection capabilities operate as open observers that plug into this invariant framework.

---

## 2. The 8 Extension Rules

### Rule 1: Detector Read Whitelist
Detectors are pure observational functions. They may only read:
- `structure/figure_inventory.json` and `structure/table_inventory.json` (Canonical inventory)
- `structure/blocks.structured.jsonl` (Normalized OCR blocks)
- `render/figures/*.md` and `render/tables/*.md` (Rendered Markdown artifacts)
- `assets/figures/*.jpg` and `assets/tables/*.jpg` (Rendered image assets)
- `render/materialization.provenance.json` (Additive crop/render provenance)
- Source PDF pages (for bounding-box / media validation only)
- `render/render.consistency.json` (Prior audit state, read-only)

### Rule 2: Detector Write Blacklist
Detectors are strictly **read-only observers**:
- Detectors MUST NEVER write, touch, truncate, or mutate any production artifact.
- Detectors MUST NEVER create or update `figure_inventory.json` or `table_inventory.json`.
- Detectors MUST NEVER delete or replace files in `assets/` or `render/`.
- Detectors MUST NEVER write to `meta.json` or alter OCR status/hashes.
- Staging writes are owned exclusively by `figure_reconciliation.py`; production writes are owned exclusively by `promote_r.py` and `accept_proposal.py`.

### Rule 3: Finding Minimal Schema
Every detector must emit findings matching this minimal structure:
```json
{
  "finding_id": "string",
  "type": "string",
  "severity": "P0 | P1 | P2",
  "domain": "render_layer | inventory_layer | asset_layer | ocr_layer",
  "object_id": "string | null",
  "diagnosis": "string",
  "recommended_action": "rerender | inspect_inventory | inspect_asset_matching | inspect_render | inspect",
  "repairability": "R | P | BLOCKED",
  "evidence": {
    "page": "number | null",
    "bbox": "array | null",
    "details": {}
  }
}
```

### Rule 4: Prerequisites for "R" (Exact Repair) Classification
A finding may be classified as `repairability = "R"` **ONLY** if ALL of the following hold:
1. The target object already exists in the canonical inventory (`figure_id` or `table_id` is present).
2. The canonical object has valid, unambiguous asset block references (`asset_block_ids` or `matched_assets`).
3. There are no conflicting cross-canonical claims on the same `(page, block_id, bbox)`.
4. The issue is strictly an output materialization defect (missing JPG, dangling Markdown link, missing Markdown header, or caption label drift).
5. If materialization provenance exists, it must not be ambiguous or contradictory.

### Rule 5: Prerequisites for "P" (Proposal) Classification
A finding may be classified as `repairability = "P"` **ONLY** if ALL of the following hold:
1. The target object does **NOT** exist in the canonical inventory.
2. An unassigned visual cluster or asset exists on the page (`unmatched_assets` / `unresolved_clusters`).
3. An unassigned caption/legend exists (`unmatched_captions`).
4. Both can be bounded within a valid structural slot (body flow anchors, page bounds).
5. A `final-plan.json` can be staged with a deterministic SHA-256 `final_plan_hash`.
6. Promotion requires explicit human authorization with the exact `final_plan_hash`.

### Rule 6: Default Fail-Closed to "BLOCKED"
If evidence is incomplete, ambiguous, multi-page disjoint, contradictory, or lacks a verifiable anchor:
- The classifier MUST mark the finding as `repairability = "BLOCKED"`.
- The engine MUST NEVER guess, pick an arbitrary winner, or perform partial materialization.
- When inventory authority is unavailable or duplicate canonical IDs exist, all fulltext and materialization mutations are blocked (`mutation_blocked = True`).

### Rule 7: Audit Schema & Algorithm Versioning
- New finding types enter the report by incrementing `ALGORITHM_VERSION` (currently `4`) in `render_audit.py`.
- Breaking changes to the top-level report structure require incrementing `SCHEMA_VERSION` (currently `1`).
- Existing consumers (`probe lineage`, reconciliation engine) must remain compatible with valid older schema versions or fail closed to `state = "UNKNOWN"`.
- Audit execution crashes or non-object returns MUST atomically overwrite the report with `state = "FAILED"`; they must never leave a stale `CLEAN` or `DEGRADED` report.

### Rule 8: Separation of Detection and Execution
- Detectors emit observations; they **NEVER** contain execution code or mutation callbacks.
- All R executions are dispatched through `promote_r.py` (`paperforge render promote-r`).
- All P executions are dispatched through `accept_proposal.py` (`paperforge render accept-proposal`).
- Neither promoter may be extended or bypassed by detector-specific execution logic.

---

## 3. Core Invariants Summary

1. **Canonical inventory is the sole structural authority** — Audit and detectors never modify it.
2. **Reconcile never silently mutates** — Default is read-only reporting or isolated staging.
3. **R never creates canonical truth** — It only recovers lost renderings of pre-existing canonical objects.
4. **P cannot mutate without reviewed plan hash** — Eliminates blind auto-acceptance and plan drift.
5. **Committed is the authority flip** — Post-commit cleanup or report failures cannot roll back production.
6. **Unknown or failed is never clean** — Preserves state truth across all read models.
