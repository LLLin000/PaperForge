# Domain Pitfalls

**Domain:** Brownfield evolution of PaperForge into an AI-ready local-first literature asset manager
**Researched:** 2026-05-03

## Recommended v1.6 mitigation phases

1. **Phase 1 — Truth model and migration contract**
   - Define source-of-truth ownership for config, user intent, machine facts, and derived state.
2. **Phase 2 — Canonical asset index and rebuild pipeline**
   - Build the index as a deterministic projection with repair/rebuild support.
3. **Phase 3 — Health engine and thin-shell dashboard**
   - Centralize health/readiness logic in Python; plugin renders only.
4. **Phase 4 — AI context packaging and maturity guidance**
   - Add reusable context packs and next-step guidance without hardcoding discipline schemas.
5. **Phase 5 — Brownfield rollout, migration, and verification**
   - Ship compatibility checks, doctor/repair upgrades, and safe rollout gates.

## Critical Pitfalls

### Pitfall 1: Creating multiple truths for the same paper
**What goes wrong:** `paperforge.json`, plugin `data.json`, library-record frontmatter, OCR `meta.json`, formal notes, and the new asset index all start carrying overlapping state. Users then see contradictory answers to simple questions like “is this paper OCR-ready?” or “which path is canonical?”

**Why it happens:** Brownfield systems accrete state by convenience. PaperForge already has proven drift history across queue/status surfaces, and v1.6 adds more derived surfaces unless ownership is locked down first.

**Consequences:** State drift, repair complexity, mistrust in dashboard output, and future migrations that require special-case logic.

**Prevention:**
- Publish a strict ownership matrix before implementation:
  - `paperforge.json` = runtime configuration truth
  - plugin `data.json` = UI draft/cache only, never workflow truth
  - library-record = user intent + stable imported metadata
  - OCR/meta outputs = machine facts
  - asset index = derived projection only
- Ban duplicate writable fields across layers.
- Add a `source_of_truth` note to ADR/docs for every new field.

**Detection:**
- Same concept appears writable in both plugin and CLI outputs
- “Fix” commands need to choose which file wins
- Status differs depending on command/UI surface

**Mitigation phase:** Phase 1

### Pitfall 2: Treating the canonical asset index like a hand-maintained database
**What goes wrong:** The new index becomes a semi-manual store that mixes imported facts, repair flags, health summaries, and UI-only annotations. Once users or multiple commands edit it directly, rebuilds stop being trustworthy.

**Why it happens:** “Canonical index” sounds like “put everything there.” In local-first systems, durable tables often become junk drawers unless they are clearly defined as projections.

**Consequences:** Non-idempotent rebuilds, hard-to-debug corruption, impossible provenance, and brittle plugin/CLI dependencies.

**Prevention:**
- Make the index a deterministic projection from owned sources, not a primary authoring surface.
- Store per-record provenance: input files, mtimes/hashes, generated_at, schema_version.
- Support `rebuild-index` from source artifacts with no data loss.
- Keep manual overrides in a separate override layer if truly needed.

**Detection:**
- Rebuilding the index changes meaning, not just freshness
- Developers hesitate to delete/regenerate the index
- User edits to the index are considered normal workflow

**Mitigation phase:** Phase 2

### Pitfall 3: Mixing user intent, machine facts, and derived readiness in one state machine
**What goes wrong:** Fields like `analyze`, `do_ocr`, `ocr_status`, deep-reading completion, figure readiness, and AI readiness get collapsed into one monolithic lifecycle enum. A user toggle then accidentally overwrites machine facts, or a failed OCR run blocks unrelated workflows forever.

**Why it happens:** A single “state” field feels tidy, but PaperForge already has different actors: user, worker, agent, and derived health logic.

**Consequences:** Sticky bad states, confusing retries, complicated repair code, and unreadable business logic.

**Prevention:**
- Separate three planes explicitly:
  - **Intent:** what the user wants next
  - **Asset facts:** what files/processes actually exist
  - **Derived readiness/health:** computed conclusions
- Model readiness as computed predicates, not stored toggles.
- Only persist state transitions owned by a real actor.

**Detection:**
- One command both changes user intent and marks derived readiness
- Retry flows require manually editing multiple unrelated fields
- “Why is this blocked?” cannot be answered from one explanation chain

**Mitigation phase:** Phase 1

### Pitfall 4: Re-implementing health and lifecycle logic inside the Obsidian plugin
**What goes wrong:** The plugin starts recomputing health, maturity, and readiness in JavaScript because it needs fast dashboard cards. Soon the Python CLI and plugin disagree about counts, warnings, and next steps.

**Why it happens:** UI teams want instant rendering, and dashboard work invites “just compute it here.” But PaperForge already established a thin-shell direction precisely to avoid this split.

**Consequences:** Plugin/CLI duplication, inconsistent support burden, doubled test surface, and brownfield regressions whenever state rules change.

**Prevention:**
- Expose health/index data from Python as stable JSON contracts.
- Plugin consumes rendered summaries or structured check results; it does not infer workflow truth.
- Put contract fixtures in tests used by both CLI and plugin.
- Refuse UI-only derived fields unless they are clearly cosmetic.

**Detection:**
- Same rule exists in JS and Python
- Dashboard numbers differ from `paperforge status`
- Plugin release requires business-rule changes without CLI changes

**Mitigation phase:** Phase 3

### Pitfall 5: Building maturity scores that look smart but are operationally empty
**What goes wrong:** “Library maturity” becomes a vanity number with no evidence trail. Users see 62/100 but cannot tell what to fix next, or why the score changed after a sync.

**Why it happens:** Product scoring is tempting, especially for AI readiness, but scoring before explainability creates opaque UX.

**Consequences:** User distrust, noisy support requests, and pressure to game the score instead of improving library quality.

**Prevention:**
- Every score must decompose into named checks with weights, evidence, and recommended next action.
- Prefer level-based maturity bands at first (`Foundational`, `Usable`, `AI-ready`) over fake precision.
- Show “what improved / what regressed” deltas after worker runs.

**Detection:**
- Score exists without per-check explanations
- Two libraries with different failure modes get the same score
- Users ask “what does this number mean?”

**Mitigation phase:** Phase 4

### Pitfall 6: Over-productizing extraction schemas into the core asset model
**What goes wrong:** v1.6 turns “AI-ready” into built-in PICO tables, mechanism schemas, parameter schemas, or discipline-specific extraction templates embedded in the canonical index.

**Why it happens:** Once context packaging exists, the fastest demo is a hardcoded schema. But the project explicitly wants a framework, not a stack of medical extraction products.

**Consequences:** Schema lock-in, brittle migrations, domain overfitting, poor reuse outside one workflow, and a permanently bloated index contract.

**Prevention:**
- Keep the core asset model generic: provenance, text assets, figures, notes, readiness, health.
- Implement context packs as pluggable packagers/templates over the core assets.
- Allow optional schema manifests outside the canonical index.
- Treat missing structured extraction as a pack-level capability gap, not a library corruption.

**Detection:**
- Core index fields start naming domain-specific extraction slots
- New workflows require core schema migration instead of a new packager
- “AI-ready” is defined as “matches one extraction template”

**Mitigation phase:** Phase 4

### Pitfall 7: Shipping v1.6 without a brownfield migration and rollback story
**What goes wrong:** Existing vaults upgrade into new index/state logic with partial migrations, stale Bases, old commands, and no clean recovery path.

**Why it happens:** Teams focus on the new model, not on the installed base. PaperForge already has real-world path quirks, metadata drift, and existing plugin persistence.

**Consequences:** Broken dashboards, false health alarms, user-edited records rendered invalid, and high-maintenance emergency fixes.

**Prevention:**
- Version every generated artifact and contract.
- Add `doctor` checks for config drift, index schema version, stale Base templates, and orphaned OCR/meta assets.
- Add one-step repair/rebuild commands before turning on new dashboard surfaces.
- Keep rollout reversible: regenerate index, restore previous Bases, ignore unsupported plugin fields gracefully.

**Detection:**
- Upgrade requires manual file surgery
- Users must delete unknown files to recover
- Docs say “reinstall if weird things happen”

**Mitigation phase:** Phase 5

## Moderate Pitfalls

### Pitfall 8: Health checks that are too shallow to be trusted
**What goes wrong:** “PDF Health” only checks path existence, “OCR Health” only checks folder presence, and “Base Health” only checks file existence. Users get green badges on unusable assets.

**Prevention:**
- Validate at the failure mode level: file exists, readable, non-empty, expected sidecars present, schema/version matches, referenced note exists, figure-map parseable.
- Distinguish `missing`, `broken`, `stale`, and `incomplete`.
- Return evidence paths, not just booleans.

**Mitigation phase:** Phase 3

### Pitfall 9: Making AI context packs too heavy, too eager, or too opaque
**What goes wrong:** `ask-this-paper` or `copy-context-pack` assembles huge prompt blobs every time, includes duplicated OCR/note content, and hides where statements came from.

**Prevention:**
- Build packs from explicit sections with token budgets.
- Prefer manifest-first packaging: summary + citations + selected assets + provenance links.
- Cache pack manifests; assemble full text lazily.
- Include source paths for every included block.

**Mitigation phase:** Phase 4

### Pitfall 10: Dashboard-first implementation order
**What goes wrong:** The plugin dashboard is built before the index and health contracts stabilize, so UI demands freeze bad backend assumptions.

**Prevention:**
- Finish JSON contracts and fixture snapshots before dashboard polish.
- Use a temporary debug/JSON view during backend stabilization.
- Only add cards/recommendations after health semantics are verified.

**Mitigation phase:** Phase 3

### Pitfall 11: Ignoring stale generated surfaces beyond the new index
**What goes wrong:** The index updates, but generated Bases, note templates, cached plugin views, and old dashboard expectations still reflect pre-v1.6 fields.

**Prevention:**
- Track generator version on every generated artifact.
- Add stale-template/Base detection to doctor.
- Make regeneration explicit and safe.

**Mitigation phase:** Phase 5

## Minor Pitfalls

### Pitfall 12: Vocabulary drift across health, readiness, and maturity terms
**What goes wrong:** “ready,” “healthy,” “complete,” “indexed,” and “AI-ready” are used inconsistently across CLI, plugin, docs, and Bases.

**Prevention:**
- Publish a term glossary with exact meanings.
- Reuse the same labels in CLI JSON, plugin cards, docs, and Base columns.

**Mitigation phase:** Phase 1

### Pitfall 13: Hiding actionable repair paths behind aggregate status
**What goes wrong:** Users see “12 broken assets” but not the exact records or command to fix them.

**Prevention:**
- Every aggregate status should drill down to paper-level evidence and a fix path.
- CLI and plugin should share the same remediation text.

**Mitigation phase:** Phase 3

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Truth model | Field ownership ambiguity between config, plugin cache, library-record, OCR meta, and index | Publish ownership matrix and forbid duplicate writable fields |
| Canonical index | Index becomes a second database instead of a rebuildable projection | Deterministic projection + provenance + rebuild command |
| Lifecycle model | Intent/facts/readiness collapsed into one enum | Separate planes and compute readiness |
| Health engine | Green badges based on existence-only checks | Failure-mode-level checks with evidence |
| Plugin dashboard | JS duplicates Python business rules | Python emits JSON contracts; plugin renders only |
| Maturity scoring | Opaque score with no next action | Explainable checks, weighted bands, remediation text |
| AI context packaging | Core model polluted by discipline-specific schemas | Keep packagers optional and outside core index |
| Brownfield rollout | Old vaults, Bases, and caches break on upgrade | Versioned artifacts, doctor/repair, reversible rebuild |

## Sources

- `.planning/PROJECT.md` — current v1.6 goals, constraints, and explicit anti-goals. Confidence: HIGH.
- `docs/ARCHITECTURE.md` — worker/agent split, local-first file boundaries, command centralization. Confidence: HIGH.
- `.planning/phases/15-deep-reading-queue-merge/15-LEARNINGS.md` — prior move toward canonical pure data acquisition functions. Confidence: HIGH.
- `.planning/phases/20-plugin-settings-shell-persistence/20-LEARNINGS.md` — proven risk of tracking/implementation drift and plugin thin-shell lessons. Confidence: HIGH.
- Context7 Obsidian developer docs: Plugin settings persistence and ItemView/View registration patterns. Confidence: HIGH.  
  - https://github.com/obsidianmd/obsidian-developer-docs/blob/main/en/Plugins/User%20interface/Settings.md  
  - https://github.com/obsidianmd/obsidian-developer-docs/blob/main/en/Plugins/User%20interface/Views.md
- Ink & Switch, “Local-first software: You own your data, in spite of the cloud” — local-first principle that local data is primary and derived surfaces should preserve ownership and rebuildability. Confidence: HIGH.  
  - https://www.inkandswitch.com/local-first/
- Exa-discovered AI knowledge/RAG articles used only for product-shaping heuristics around explainability, retrieval governance, and avoiding hardcoded schemas. Confidence: LOW.  
  - https://redwerk.com/blog/rag-best-practices/  
  - https://oleno.ai/blog/design-a-knowledge-base-that-makes-ai-content-writing-accurate-and-repeatable/
