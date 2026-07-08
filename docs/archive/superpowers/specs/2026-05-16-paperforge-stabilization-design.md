# PaperForge Stabilization and Complexity-Reduction Design

**Date:** 2026-05-16
**Status:** Proposed
**Audience:** Maintainers, contributors, agentic implementers

---

## 1. Summary

PaperForge's architecture direction is sound, but the product currently suffers from four classes of contract drift:

1. Runtime state and path contracts are not consistently enforced.
2. Skill/workflow instructions are not fully aligned with the live CLI surface.
3. Documentation mixes audiences and duplicates workflow guidance.
4. The normal user experience exposes too much implementation complexity too early.

This design proposes a medium-scope stabilization program that prioritizes existing power users first. The program explicitly does **not** begin with a frontend rewrite. Instead, it hardens runtime contracts, aligns the command and skill surfaces, rebuilds documentation information architecture, and only then reduces user-facing complexity through progressive disclosure.

---

## 2. Product Decision

### Chosen Priority

- **Primary audience for this program:** existing power users
- **Refactor intensity:** medium
- **Principle:** do not rewrite the frontend first

### Why

The most dangerous current failures are not discoverability issues alone, but cases where the system appears healthy while state, commands, or paths silently drift. Improving onboarding before stabilizing these contracts would increase user trust in workflows that are not yet reliable enough.

---

## 3. Problem Statement

PaperForge is currently "strong but brittle":

- Runtime snapshots are treated as a contract by the plugin, but not fully implemented as contract-grade files.
- Index mutation paths are not fully serialized, enabling stale or overwritten state.
- `sync` can publish pre-clean rather than post-clean truth.
- The plugin still hardcodes `System/PaperForge/...` in key places, breaking the real meaning of configurable paths.
- Agent skill workflows contain stale commands, stale enums, stale paths, and ambiguous router behavior.
- `AGENTS.md`, `README*`, and `docs/COMMANDS.md` collide in purpose and repeat the same flows.
- New users are exposed to too many layers at once: runtime, OCR, Zotero storage linking, memory layer, vector DB, agent setup, dashboard modes, frontmatter toggles, and chat commands.

The result is a system with high capability but avoidable operational risk and cognitive overhead.

---

## 4. Goals

### 4.1 Primary Goals

1. Eliminate silent state drift across plugin, index, DB, and filesystem.
2. Make the CLI the single truth source for all documented and skill-invoked commands.
3. Separate user, agent, and maintainer documentation cleanly.
4. Reduce complexity of the first-value path without large UI surgery.

### 4.2 Secondary Goals

1. Improve confidence in `/pf-*` routing and workflow reliability.
2. Make custom path configuration genuinely supported end-to-end.
3. Reduce future maintenance cost by clarifying truth boundaries.

### 4.3 Non-Goals

1. No full dashboard redesign.
2. No broad `main.js` extraction project unless needed to support a chosen package.
3. No major new features.
4. No attempt to make PaperForge beginner-perfect in one pass.

---

## 5. Guiding Principles

1. **CLI is the command truth source.** Skill docs, user docs, plugin guidance, and examples must all match the live CLI surface.
2. **Python is the runtime truth source.** JS reads canonical runtime state; it does not infer it.
3. **One document, one audience.** README, tutorial, AGENTS, command reference, and maintainer docs must not overlap in purpose.
4. **First value before full configuration.** Users should be able to reach first sync before OCR, vector DB, or deep agent setup becomes mandatory.
5. **Mechanical commands and thinking workflows are different classes.** `/pf-sync`, `/pf-ocr`, `/pf-status` must not be treated like `/pf-deep` and `/pf-paper`.

---

## 6. Proposed Program Structure

The work is split into four packages executed in order.

### 6.0 Package Ownership Rules

| Package | Allowed changes | Disallowed changes | Owned files | Cross-package rule |
|---|---|---|---|---|
| A | runtime state writes, path resolution, sync truth, lifecycle control, regression tests | UX copy cleanup, documentation restructuring, information architecture changes | runtime Python modules, plugin runtime path/state logic | May touch `paperforge/plugin/main.js` only for runtime path/state behavior |
| B | CLI/skill/workflow alignment, route ownership, command examples, validation tests | runtime contract redesign, doc IA restructuring, UX layout changes | `paperforge/cli.py`, relevant commands, `paperforge/skills/paperforge/*` | May depend on A outputs, but does not redefine A runtime behavior |
| C | README shrink, tutorial/troubleshooting split, AGENTS narrowing, maintainer doc ownership | runtime behavior changes, route logic changes, UI behavior changes | README, AGENTS, docs tree | Owns documentation structure and glossary decisions |
| D | staged setup gating, visibility toggles, primary action placement, user-facing error copy, terminology adoption in UI | runtime contract changes, command-surface changes, full visual redesign, component extraction project | plugin presentation behavior and user-facing copy | Must consume frozen outputs from C and cannot restructure docs |

#### Boundary Invariants

- Package A may touch plugin code only for runtime path/state correctness.
- Package D may touch plugin code only for presentation, visibility, and copy behavior.
- `README*` ownership belongs to Package C only.
- `AGENTS.md` ownership belongs to Package C only.
- Package D may consume terminology decisions from Package C, but may not redefine them.

### Package A: Runtime Contract Hardening

**Goal:** make runtime state, path resolution, and end-of-command truth reliable.

#### Scope

- Convert all runtime snapshot writes to atomic writes.
- Create one safe mutation path for `formal-library.json` updates.
- Define `sync` final state as cleaned, canonical end state.
- Remove plugin hardcoded assumptions about `System/PaperForge/...`.
- Fix runtime lifecycle gaps such as `embed stop`, snapshot bootstrap semantics, and startup update behavior.

#### Required Outcomes

- Plugin never reads half-written snapshot JSON.
- Path overrides from `paperforge.json` are respected end-to-end.
- `sync` no longer leaves pre-clean truth published as final truth.
- `embed stop` returns success only when it has either issued a real stop signal or explicitly reports that no stoppable job exists.
- First-launch bootstrap generates every runtime snapshot file the plugin checks during startup.

#### Files in Scope

- `paperforge/memory/state_snapshot.py`
- `paperforge/memory/vector_db.py`
- `paperforge/core/io.py`
- `paperforge/worker/asset_index.py`
- `paperforge/worker/repair.py`
- `paperforge/services/sync_service.py`
- `paperforge/memory/refresh.py`
- `paperforge/commands/embed.py`
- `paperforge/commands/runtime_health.py`
- `paperforge/plugin/main.js`

### Package B: Command & Skill Truth Alignment

**Goal:** eliminate stale or incorrect command instructions and router ambiguity.

#### Scope

- Audit live CLI surface in `paperforge/cli.py` and relevant command modules.
- Redefine compound skill routing so mechanical commands have explicit handling.
- Correct stale workflow examples, enum values, render paths, and fallback logic.
- Ensure `agent-context` exposed usage strings match the real command surface.

#### Required Outcomes

- Every documented workflow command can actually run.
- Every `/pf-*` route has one clear owner.
- Workflow docs no longer reference nonexistent flags or stale output paths.
- CI or fixture validation detects if workflow docs or agent-context examples reference commands or flags not present in the live CLI surface.

#### Files in Scope

- `paperforge/cli.py`
- `paperforge/commands/paper_context.py`
- `paperforge/commands/paper_status.py`
- `paperforge/commands/search.py`
- `paperforge/commands/reading_log.py`
- `paperforge/commands/project_log.py`
- `paperforge/commands/agent_context.py`
- `paperforge/memory/runtime_health.py`
- `paperforge/skills/paperforge/SKILL.md`
- `paperforge/skills/paperforge/workflows/*.md`

### Package C: Documentation IA Reset

**Goal:** separate audiences and establish one authoritative workflow tutorial.

#### Scope

- Shrink `README.md` and `README.en.md` into entry pages.
- Create a canonical end-user tutorial.
- Create a dedicated troubleshooting document.
- Convert `AGENTS.md` into agent-only operating guidance.
- Convert `docs/COMMANDS.md` into pure command reference.
- Move maintainer architecture, release, testing, and versioning guidance into maintainer-facing docs.

#### Required Outcomes

- Users do not need `AGENTS.md` to use the product.
- Agents do not rely on user tutorial content for repository operating rules.
- One workflow is documented once, then referenced elsewhere.
- Stale links, stale version markers, and audience collisions are removed.
- Ownership is explicit:
  - `docs/getting-started.md` owns the end-user happy path
  - `docs/troubleshooting.md` owns user failure recovery
  - `docs/COMMANDS.md` owns CLI reference only
  - `docs/maintainer-guide.md` owns release, testing, versioning, migration, and architecture links

#### Files in Scope

- `README.md`
- `README.en.md`
- `AGENTS.md`
- `docs/COMMANDS.md`
- `docs/ARCHITECTURE.md`
- new `docs/getting-started.md`
- new `docs/troubleshooting.md`
- new `docs/maintainer-guide.md`

### Package D: Progressive Disclosure UX

**Goal:** reduce user complexity without a frontend rewrite.

#### Scope

- Make the setup wizard staged instead of fully front-loaded.
- Fix global/home surface so core mechanical actions are consistently visible.
- Hide advanced memory/vector/runtime surfaces until needed.
- Rewrite user-facing error messages to lead with action.
- Normalize core product terms across UI and docs.

#### Required Outcomes

- New users can reach first sync before confronting OCR/agent/vector configuration.
- The Home/Global surface exposes `Sync`, `OCR`, `Status`, `Doctor`, and `Repair` in one persistent primary action group on first run and after setup completion.
- Advanced memory/vector/runtime controls are hidden behind one collapsed `Advanced` section by default.
- A controlled glossary of core product terms is defined in Package C, and user-visible strings in plugin UI adopt those exact terms.

#### Files in Scope

- `paperforge/plugin/main.js`

#### In Scope

- staged setup gating
- action placement
- visibility toggles
- user-facing copy
- terminology normalization

#### Out of Scope

- new navigation architecture
- component extraction project
- visual redesign
- settings subsystem rewrite
- dashboard information model redesign

---

## 7. Execution Order

### Required Order

1. Package A
2. Package B
3. Package C
4. Package D

### Rationale

- Package A stabilizes truth.
- Package B stabilizes command semantics built on that truth.
- Package C stabilizes explanations of those semantics.
- Package D improves surface complexity only after the lower layers stop moving.

### Release Strategy

- **Milestone 1:** Package A only, released as a stability hardening version.
- **Milestone 2:** Package B only, released as command and agent alignment.
- **Milestone 3:** Package C only, released as documentation IA reset.
- **Milestone 4:** Package D only, released as progressive-disclosure UX simplification.

This sequencing keeps release narratives clean and reduces regression blast radius.

---

## 8. Design Details by Risk Area

### 8.1 Snapshot Contract

Snapshots are now part of the runtime contract and must be treated as such.

#### Decision

- All snapshot writes become atomic (`.tmp` then replace).
- Snapshot readers may still degrade gracefully, but parse failure should become exceptional rather than expected.
- The first-launch bootstrap must generate the files the plugin is actually checking for.

#### Acceptance Criteria

- No direct `write_text(json.dumps(...))` remains for contract snapshots.
- Plugin startup no longer relies on a bootstrap command that writes a different file than the one being checked.

### 8.2 Canonical Index Mutation

`formal-library.json` must not be mutated through multiple partially safe paths.

#### Decision

- Introduce one canonical mutation path for read-modify-write behavior.
- The safety boundary includes read, merge, write, and replace, not only the last write.
- Repair and incremental refresh should use the same safety primitive.

#### Acceptance Criteria

- No code path directly writes the canonical index outside the shared mutation layer.
- Concurrency-sensitive tests exist for overlapping update scenarios.

### 8.3 `sync` Final-State Truth

The system must choose whether sync publishes pre-clean or post-clean truth. This design chooses **post-clean truth only**.

#### Decision

- Cleanup is part of the sync transaction semantics.
- `formal-library.json` and DB refreshes must reflect the cleaned end state, not an intermediate build stage.

#### Acceptance Criteria

- A completed sync cannot leave deleted notes present in the canonical index or memory DB.
- Sync tests assert cleaned-end-state semantics explicitly.

### 8.4 Path Configuration Contract

Custom path configuration is either real or it is not. This design treats it as real.

#### Decision

- The plugin must resolve runtime files through one configuration-aware path source.
- Hardcoded `System/PaperForge` assumptions in runtime reads, polling, and bootstrap logic are removed.

#### Authority and Bootstrap Contract

- **Authority:** resolved runtime paths derive from vault root + `paperforge.json` configuration, using one configuration-aware resolution flow.
- **Bootstrap:** plugin startup must load config before constructing runtime file paths.
- **Fallback:** if config is missing or corrupt, plugin falls back to documented defaults and surfaces a recoverable warning instead of silently constructing mixed paths.
- **Invariant:** plugin runtime path construction must not use hardcoded `System/PaperForge/...` literals outside the shared path resolution flow.

#### Acceptance Criteria

- A vault with non-default `system_dir` still gets working snapshots, export polling, OCR polling, and dashboard stats.

### 8.5 Mechanical vs Cognitive Routes

The skill layer must reflect the actual distinction in the product.

#### Decision

- `/pf-sync`, `/pf-ocr`, `/pf-status` are mechanical execution routes.
- `/pf-deep`, `/pf-paper` are cognitive workflows.
- The compound skill router must represent this explicitly.

#### Routing Ownership Matrix

| Route | Owner | Behavior |
|---|---|---|
| `/pf-sync` | mechanical executor | run CLI sync path and return execution/result interpretation |
| `/pf-ocr` | mechanical executor | run CLI OCR path and return execution/result interpretation |
| `/pf-status` | mechanical executor | run CLI status/health path and return execution/result interpretation |
| `/pf-deep` | cognitive workflow | run deep-reading workflow with runtime gating |
| `/pf-paper` | cognitive workflow | run paper-qa workflow with identifier resolution first |

Unknown or malformed slash commands must not fall through silently into `project-engineering`; they should trigger explicit clarification or an unsupported-command response.

#### Acceptance Criteria

- No slash command relies on accidental fallback into `project-engineering`.
- Known slash commands map to exactly one owner.
- Unknown slash commands produce a deterministic clarification path.
- Workflow routing examples match live behavior.

### 8.6 Documentation Audience Separation

Current documentation is content-rich but structurally unsound.

#### Decision

- `AGENTS.md` becomes repository operating guidance only.
- Tutorial ownership moves to a dedicated getting-started guide.
- README becomes a navigation page, not the entire product manual.
- `docs/maintainer-guide.md` is required, not optional.

#### Acceptance Criteria

- A normal user can complete the main workflow without opening `AGENTS.md`.
- A contributor/agent can learn repo operating rules without reading end-user tutorial content.
- Installation, upgrade, release compatibility, and migration ownership are assigned to maintainer-facing docs rather than spread across README and AGENTS.

### 8.7 UX Simplification Without Rewrite

This program reduces complexity via staging and hiding, not by redesigning every screen.

#### Decision

- The first-value path ends at sync.
- OCR, agent setup, memory layer, and vector DB are later-stage surfaces.
- Global/Home view must always expose core mechanical actions.

#### Acceptance Criteria

- The setup flow no longer blocks first sync on OCR or advanced features.
- On first visit after setup, runtime/setup/core workflow remain visible while advanced memory/vector/runtime controls are collapsed by default.
- OCR, agent, memory, and vector configuration are not required to complete first sync.

---

## 9. Compatibility and Migration Considerations

### 9.1 Existing Users

- Existing power users should not lose access to advanced runtime, memory, or vector controls.
- Advanced controls may move behind clearer grouping, but not disappear.

### 9.2 Existing Documentation Links

- README and AGENTS restructuring will require link updates across docs.
- Redirect-by-reference is sufficient; no file-system redirect mechanism is needed.

### 9.3 Existing Agent Habits

- Some users may already treat `/pf-sync` as a broad engineering discussion trigger.
- After alignment, mechanical slash commands should act more literally and predictably.

### 9.4 Path Overrides

- Supporting custom `system_dir` fully means tests and plugin reads must cover non-default path layouts, not only defaults.

---

## 10. Risks

1. **Over-expansion risk:** this program can accidentally become a full frontend refactor unless file boundaries are enforced.
2. **Contract churn risk:** changing plugin path logic and sync semantics simultaneously can create regression clusters if not tested incrementally.
3. **Documentation drift risk during transition:** if docs are edited before command alignment is done, they will drift again.
4. **Behavioral surprise risk for power users:** moving advanced controls or changing slash-command routing may break habit memory if changelog messaging is weak.

### Mitigations

- Ship in four milestones.
- Treat Package A and Package B as contract work with explicit regression tests.
- Do not start Package D until Package C terminology is settled.
- Use changelog notes to explain route and doc entry changes.

---

## 11. Testing Strategy

### Package A

- Unit tests for atomic snapshot write helpers.
- Integration tests for concurrent index mutation paths.
- Integration tests for sync post-clean final-state semantics.
- Plugin-facing tests for non-default path resolution assumptions where feasible.

### Package B

- Command-surface verification tests.
- Workflow reference audit tests or fixture-based validation where practical.
- Manual verification of each `/pf-*` route against documented behavior.
- CI validation that skill/workflow examples and `agent-context` command references do not mention nonexistent commands or flags.

### Package C

- Link integrity pass.
- Manual audience review: user flow, agent flow, maintainer flow.

### Package D

- Manual first-run walkthrough.
- Manual regression on advanced settings visibility.
- String/term consistency pass across docs and UI.

---

## 12. Success Criteria

This program is successful if all of the following are true:

1. The plugin and Python package agree on path layout and runtime state without hardcoded default assumptions.
2. `sync`, `repair`, and incremental updates no longer leave contradictory truth between filesystem, index, and DB.
3. Every shipped skill/workflow command reference matches the live CLI.
4. `AGENTS.md` is no longer required reading for end users.
5. There is exactly one canonical user tutorial.
6. A user can reach first sync without being forced through OCR, vector DB, or deep agent setup.
7. Documentation ownership is explicit and implemented by file structure, not only by prose intent.

---

## 13. Out of Scope Follow-Ups

These are intentionally deferred until after this program:

- Large-scale `main.js` decomposition
- full Settings/UI component extraction
- broader design polish work
- new workflows or major memory/vector features

---

## 14. Implementation Handoff

The implementation plan should preserve the four-package structure and convert it into dependency-aware tasks with:

- explicit file lists
- regression-first testing
- milestone-based execution
- no large opportunistic refactors outside scope
