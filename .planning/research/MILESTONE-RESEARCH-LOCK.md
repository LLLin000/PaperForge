# Milestone Research Lock

**Created:** 2026-05-03
**Purpose:** Freeze the already-completed milestone-level research conclusions for v1.6 and v1.7 so future workflows do not repeat the same product-direction research.

---

## Scope Of This Lock

This file records research that is considered settled enough to skip re-research later.

It does **not** lock implementation details.
It does **not** replace discuss-phase clarification.
It does **not** replace phase planning.

It only means the product-direction and architecture-direction questions below do not need another milestone-level research pass unless the project direction changes materially.

---

## v1.6 Locked Research

**Milestone:** AI-Ready Literature Asset Foundation

### Direction Locked

- PaperForge should evolve toward long-term literature asset management, not prompt-button sprawl.
- The system should converge around a canonical asset index derived from existing source artifacts.
- Python remains the sole owner of lifecycle, health, maturity, and context-pack logic.
- The plugin remains a thin shell over CLI/index outputs.
- `paper workspace` is the preferred long-term user-facing model, but exact file composition remains a discuss/planning concern, not a re-research concern.
- `ai/` belongs in the paper workspace and stores `/pf-paper`-style atomized, reusable AI notes rather than system caches.
- Complex OCR intermediate artifacts remain system assets unless explicitly promoted into the user workspace.

### What Does Not Need Re-Research

- Whether PaperForge should focus on asset management instead of hardcoded extraction tools.
- Whether a canonical index is needed.
- Whether plugin logic should stay thin-shell.
- Whether health/lifecycle/maturity should be centralized.
- Whether the paper workspace direction is valid.

### What Still Needs Discuss/Planning

- Exact workspace file names and folder boundaries.
- Whether workspace `fulltext.md` is a mirrored user entry or the only visible copy.
- Exact canonical index schema fields.
- Migration sequencing inside phases 22-26.

---

## v1.7 Locked Research

**Milestone:** LLMWiki Concept Network

### Direction Locked

- `LLMWiki` should be a cross-paper synthesis layer above `Literature/`, not a replacement for it.
- The primary early use case is concept/mechanism network building.
- Wiki outputs must stay source-traceable and reviewable.
- The wiki should compile from canonical assets and curated AI atoms, not raw unstable system byproducts.
- The wiki is a knowledge compilation layer, not a freeform dumping ground and not a domain-specific extraction table factory.

### What Does Not Need Re-Research

- Whether v1.7 should introduce an LLM-managed wiki layer.
- Whether the first use case should be concept/mechanism synthesis.
- Whether wiki outputs must be traceable.
- Whether the wiki should be downstream of canonical index + paper workspaces.

### What Still Needs Discuss/Planning

- Exact top-level folder name (`LLMWiki/`, `Knowledge/`, etc.).
- Page taxonomy: Topics vs Concepts vs Mechanisms vs Methods.
- Refresh/rebuild policy.
- How atom notes map into wiki nodes and evidence trails.

---

## Workflow Guidance

For future milestone and phase workflows:

- **Do not rerun general product-direction research for v1.6 or v1.7 by default.**
- Use these files as upstream context:
  - `.planning/research/SUMMARY.md`
  - `.planning/research/MILESTONE-RESEARCH-LOCK.md`
- If clarification is needed, handle it in discuss/planning as a design decision, not as a fresh ecosystem research cycle.

Only reopen research if one of the following changes:

- PaperForge abandons the Python-first thin-shell architecture.
- The project moves away from local-first literature asset management.
- v1.7 changes from concept/mechanism wiki to a substantially different product direction.

---

*Status: active research lock for v1.6 and v1.7*
