# PaperForge Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden PaperForge's runtime contracts, align CLI/skill/doc truth sources, reset documentation IA, and reduce user-facing complexity without a frontend rewrite.

**Architecture:** Execute four sequential packages. Package A seals runtime and path truth. Package B aligns command and skill truth to the live CLI. Package C rebuilds documentation boundaries around single-audience ownership. Package D reduces first-run complexity by progressive disclosure while preserving the existing frontend architecture.

**Tech Stack:** Python 3.10+, Obsidian plugin JS, argparse CLI, SQLite, JSON snapshots, Vitest, pytest, GitHub Actions

---

## File Map

### Runtime Contract Files

- `paperforge/memory/state_snapshot.py` — canonical runtime snapshot writers
- `paperforge/memory/vector_db.py` — existing atomic-write reference for build state
- `paperforge/core/io.py` — candidate shared JSON atomic write helper
- `paperforge/worker/asset_index.py` — canonical index building and incremental refresh
- `paperforge/worker/repair.py` — direct index mutations to be routed through shared safe path
- `paperforge/services/sync_service.py` — sync orchestration and final-state semantics
- `paperforge/memory/refresh.py` — DB refresh behavior after index changes
- `paperforge/commands/embed.py` — build/status/stop lifecycle behavior
- `paperforge/commands/runtime_health.py` — startup/runtime snapshot behavior
- `paperforge/plugin/main.js` — runtime path/state reads and startup/update behavior

### Command and Skill Truth Files

- `paperforge/cli.py` — live command truth source
- `paperforge/commands/paper_context.py`
- `paperforge/commands/paper_status.py`
- `paperforge/commands/search.py`
- `paperforge/commands/reading_log.py`
- `paperforge/commands/project_log.py`
- `paperforge/commands/agent_context.py`
- `paperforge/memory/runtime_health.py`
- `paperforge/skills/paperforge/SKILL.md`
- `paperforge/skills/paperforge/workflows/*.md`

### Documentation IA Files

- `README.md`
- `README.en.md`
- `AGENTS.md`
- `docs/COMMANDS.md`
- `docs/ARCHITECTURE.md`
- `docs/getting-started.md` (new)
- `docs/troubleshooting.md` (new)
- `docs/maintainer-guide.md` (new)

### UX Simplification Files

- `paperforge/plugin/main.js`
- `README.md`
- `README.en.md`
- `docs/getting-started.md`
- `docs/troubleshooting.md`

### Likely Test Files

- `tests/unit/commands/test_embed.py`
- `tests/unit/commands/test_runtime_health.py`
- `tests/unit/memory/test_runtime_health.py`
- `tests/unit/memory/test_refresh.py`
- `tests/test_asset_index.py`
- `tests/test_asset_index_integration.py`
- `tests/test_repair.py`
- `tests/cli/test_json_contracts.py`
- `tests/test_command_docs.py`
- `tests/journey/test_onboarding.py`
- `paperforge/plugin/tests/runtime.test.mjs`
- `paperforge/plugin/tests/commands.test.mjs`
- `paperforge/plugin/tests/errors.test.mjs`

---

## Package A: Runtime Contract Hardening

### Task A1: Establish Safe Snapshot Write Primitive

**Files:**
- Modify: `paperforge/memory/state_snapshot.py`
- Modify: `paperforge/core/io.py`
- Test: `tests/unit/commands/test_runtime_health.py`
- Test: `tests/unit/commands/test_embed.py`

- [ ] **Step 1: Add failing tests for contract snapshot writes**

Add tests that assert snapshot writers use atomic replace semantics rather than direct in-place writes. Prefer behavioral checks around helper calls or final file integrity after interrupted write simulation.

- [ ] **Step 2: Run targeted tests to confirm current failure or gap**

Run: `python -m pytest tests/unit/commands/test_runtime_health.py tests/unit/commands/test_embed.py -v --tb=short`

- [ ] **Step 3: Introduce shared atomic JSON write helper**

Implement a minimal helper in `paperforge/core/io.py` or a similarly narrow shared location that writes JSON via temp file then replace, with UTF-8 encoding and parent creation only if already consistent with project patterns.

- [ ] **Step 4: Route runtime snapshot writers through the helper**

Update `write_memory_runtime()`, `write_vector_runtime()`, and `write_runtime_health()` to use the shared helper.

- [ ] **Step 5: Re-run targeted tests**

Run: `python -m pytest tests/unit/commands/test_runtime_health.py tests/unit/commands/test_embed.py -v --tb=short`

- [ ] **Step 6: Record checkpoint without committing unless user requests it**

Expected state: snapshot writers are atomic and targeted tests pass.

### Task A2: Unify Canonical Index Mutation Path

**Files:**
- Modify: `paperforge/core/io.py`
- Modify: `paperforge/worker/asset_index.py`
- Modify: `paperforge/worker/repair.py`
- Test: `tests/test_asset_index.py`
- Test: `tests/test_asset_index_integration.py`
- Test: `tests/test_repair.py`

- [ ] **Step 1: Add failing tests for overlapping index mutation scenarios**

Cover at least:
- refresh-style update preserves unrelated entries
- repair-style update does not bypass shared mutation path
- canonical index writes are not direct plain writes from multiple locations

- [ ] **Step 2: Run index-related tests and observe current behavior**

Run: `python -m pytest tests/test_asset_index.py tests/test_asset_index_integration.py tests/test_repair.py -v --tb=short`

- [ ] **Step 3: Implement one shared read-modify-write primitive for canonical index updates**

The primitive must own: lock acquisition, fresh read, mutation callback/application, atomic write, and replace.

- [ ] **Step 4: Migrate incremental refresh and repair paths to the shared primitive**

Remove direct `write_text` / `write_json` style index overwrites from these paths.

- [ ] **Step 5: Re-run index-related tests**

Run: `python -m pytest tests/test_asset_index.py tests/test_asset_index_integration.py tests/test_repair.py -v --tb=short`

- [ ] **Step 6: Record checkpoint without committing unless user requests it**

Expected state: one sanctioned mutation path owns canonical index edits.

### Task A3: Redefine `sync` Final-State Truth

**Files:**
- Modify: `paperforge/services/sync_service.py`
- Modify: `paperforge/worker/asset_index.py`
- Modify: `paperforge/memory/refresh.py`
- Test: `tests/unit/memory/test_refresh.py`
- Test: `tests/e2e/test_sync_pipeline.py`
- Test: `tests/test_asset_index_integration.py`

- [ ] **Step 1: Add or extend tests for cleaned end-state semantics**

Assertions should prove that after `sync` completes, deleted/orphaned notes do not remain in canonical index or refreshed DB state.

- [ ] **Step 2: Run the focused sync/state tests**

Run: `python -m pytest tests/unit/memory/test_refresh.py tests/e2e/test_sync_pipeline.py tests/test_asset_index_integration.py -v --tb=short`

- [ ] **Step 3: Adjust sync ordering or post-clean rebuild logic**

Choose the minimal change that guarantees published final truth is post-clean, not intermediate.

- [ ] **Step 4: Verify DB refresh semantics match the new sync contract**

Update `paperforge/memory/refresh.py` only as needed to avoid stale DB-visible papers after cleanup.

- [ ] **Step 5: Re-run focused sync/state tests**

Run: `python -m pytest tests/unit/memory/test_refresh.py tests/e2e/test_sync_pipeline.py tests/test_asset_index_integration.py -v --tb=short`

- [ ] **Step 6: Record checkpoint without committing unless user requests it**

Expected state: sync success means cleaned end-state truth everywhere.

### Task A4: Make Plugin Runtime Paths Configuration-Aware

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/config.py` only if a minimal shared contract helper is needed
- Test: `paperforge/plugin/tests/runtime.test.mjs`
- Test: `paperforge/plugin/tests/commands.test.mjs`
- Test: `tests/test_config.py`

- [ ] **Step 1: Add failing tests for non-default path layouts and fallback behavior**

Cover:
- runtime snapshot lookup under non-default `system_dir`
- missing `paperforge.json`
- corrupt `paperforge.json`
- fallback to documented defaults
- recoverable warning behavior instead of silent mixed-path construction

- [ ] **Step 2: Run focused plugin/runtime tests**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs tests/commands.test.mjs`

- [ ] **Step 3: Introduce one config-aware path resolution flow inside plugin runtime code**

Reuse existing `paperforge.json` reading patterns where possible. Do not expand into a broader refactor.

- [ ] **Step 4: Replace hardcoded `System/PaperForge/...` runtime file assumptions**

Touch only runtime bootstrap, snapshot reads, export polling, and OCR polling code paths.

- [ ] **Step 5: Re-run plugin/runtime tests plus targeted Python config tests**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs tests/commands.test.mjs`

Run: `python -m pytest tests/test_config.py -v --tb=short`

- [ ] **Step 6: Record checkpoint without committing unless user requests it**

Expected state: plugin runtime paths honor configured directory names and handle missing/corrupt config with explicit fallback behavior.

### Task A5: Tighten Runtime Lifecycle Behavior

**Files:**
- Modify: `paperforge/commands/embed.py`
- Modify: `paperforge/commands/runtime_health.py`
- Modify: `paperforge/plugin/main.js`
- Test: `tests/unit/commands/test_embed.py`
- Test: `tests/unit/commands/test_runtime_health.py`
- Test: `paperforge/plugin/tests/errors.test.mjs`

- [ ] **Step 1: Add failing tests for `embed stop` and first-launch snapshot bootstrap**

Cover:
- missing `os` import / real stop signal path
- truthful idle vs stopping result
- startup bootstrap producing files the plugin actually checks

- [ ] **Step 2: Run focused lifecycle tests**

Run: `python -m pytest tests/unit/commands/test_embed.py tests/unit/commands/test_runtime_health.py -v --tb=short`

Run: `cd paperforge/plugin && npx vitest run tests/errors.test.mjs tests/runtime.test.mjs`

- [ ] **Step 3: Fix stop behavior and bootstrap contract**

Implement minimal truthful behavior. If stop is best-effort, make the result explicit instead of pretending success.

- [ ] **Step 4: Restrict startup auto-update behavior to the approved safer model**

Adjust plugin startup so runtime mutation on load is no longer eager and opaque.

- [ ] **Step 5: Re-run focused lifecycle tests**

Run: `python -m pytest tests/unit/commands/test_embed.py tests/unit/commands/test_runtime_health.py -v --tb=short`

Run: `cd paperforge/plugin && npx vitest run tests/errors.test.mjs tests/runtime.test.mjs`

- [ ] **Step 6: Run Package A regression slice**

Run: `python -m pytest tests/unit/commands/test_embed.py tests/unit/commands/test_runtime_health.py tests/unit/memory/test_refresh.py tests/test_asset_index.py tests/test_asset_index_integration.py tests/test_repair.py tests/e2e/test_sync_pipeline.py -v --tb=short`

- [ ] **Step 7: Record Package A milestone without committing unless user requests it**

Expected state: runtime, path, and final-state contracts are hardened.

---

## Package B: Command & Skill Truth Alignment

### Task B1: Freeze the Live CLI Surface as Reference

**Files:**
- Modify: `paperforge/cli.py` only if help text or surface clarification is required
- Modify: `paperforge/commands/paper_context.py` if surfaced contract is wrong
- Modify: `paperforge/commands/paper_status.py` if surfaced contract is wrong
- Modify: `paperforge/commands/search.py` if surfaced contract is wrong
- Modify: `paperforge/commands/reading_log.py` if surfaced contract is wrong
- Modify: `paperforge/commands/project_log.py` if surfaced contract is wrong
- Modify: `paperforge/commands/agent_context.py`
- Test: `tests/cli/test_json_contracts.py`
- Test: `tests/test_command_docs.py`

- [ ] **Step 1: Add or extend tests that assert command reference truth comes from the live CLI surface**

Cover at least command names, supported flags, and any surfaced usage strings emitted to agents.

- [ ] **Step 2: Run focused CLI/doc tests**

Run: `python -m pytest tests/cli/test_json_contracts.py tests/test_command_docs.py -v --tb=short`

- [ ] **Step 3: Minimize CLI ambiguity where necessary**

Only fix help/usage or agent-context surfaced command metadata if current output itself is stale or misleading.

- [ ] **Step 3a: Audit whether drift originates in docs only or in command outputs too**

For each audited mismatch, record whether the truth must be fixed in docs/workflows or in surfaced command output/help text.

- [ ] **Step 4: Re-run focused CLI/doc tests**

Run: `python -m pytest tests/cli/test_json_contracts.py tests/test_command_docs.py -v --tb=short`

- [ ] **Step 5: Record checkpoint without committing unless user requests it**

Expected state: Package B has a stable CLI reference baseline.

### Task B2: Define Explicit Slash-Route Ownership

**Files:**
- Modify: `paperforge/skills/paperforge/SKILL.md`
- Test: `tests/test_command_docs.py`

- [ ] **Step 1: Add failing assertions or fixtures for slash-command ownership mapping**

Cover `/pf-sync`, `/pf-ocr`, `/pf-status`, `/pf-deep`, `/pf-paper`, plus unknown-command fallback behavior if testable through doc fixtures.

- [ ] **Step 2: Update compound skill routing to separate mechanical from cognitive routes**

Do not add new workflows unless needed. Prefer a clear routing table and explicit unsupported/clarification behavior.

- [ ] **Step 3: Re-run focused route/doc tests**

Run: `python -m pytest tests/test_command_docs.py -v --tb=short`

- [ ] **Step 4: Record checkpoint without committing unless user requests it**

Expected state: slash routes have one owner each.

### Task B3: Repair Workflow Command Accuracy

**Files:**
- Modify: `paperforge/skills/paperforge/workflows/paper-search.md`
- Modify: `paperforge/skills/paperforge/workflows/paper-qa.md`
- Modify: `paperforge/skills/paperforge/workflows/deep-reading.md`
- Modify: `paperforge/skills/paperforge/workflows/reading-log.md`
- Modify: `paperforge/skills/paperforge/workflows/project-log.md`
- Modify: `paperforge/skills/paperforge/workflows/project-engineering.md`
- Test: `tests/test_command_docs.py`

- [ ] **Step 1: Add failing doc-validation cases for known stale examples**

Cover the audited issues:
- `paper-context` misuse for non-key identifiers
- stale lifecycle enum values
- invalid `--vault` on `pf_deep.py postprocess-pass2`
- stale log render paths

- [ ] **Step 2: Run focused doc-validation tests**

Run: `python -m pytest tests/test_command_docs.py -v --tb=short`

- [ ] **Step 3: Rewrite workflow commands to reflect the live CLI exactly**

Use `paper-status` or `search` first where identifier resolution is needed. Remove or replace stale flags and values. Fix stale output-path language.

- [ ] **Step 4: Re-run focused doc-validation tests**

Run: `python -m pytest tests/test_command_docs.py -v --tb=short`

- [ ] **Step 5: Record checkpoint without committing unless user requests it**

Expected state: workflow markdown no longer teaches invalid commands.

### Task B4: Add Anti-Drift Validation for CLI vs Skill/Docs

**Files:**
- Modify: `tests/test_command_docs.py`
- Modify: `tests/cli/test_json_contracts.py`
- Modify: `.github/workflows/ci.yml` only if coverage needs to include the validation target

- [ ] **Step 1: Create a repeatable validation mechanism**

Prefer fixture- or parser-based checks that detect nonexistent commands/flags in workflow docs and `agent-context` examples.

- [ ] **Step 2: Run local validation tests**

Run: `python -m pytest tests/test_command_docs.py tests/cli/test_json_contracts.py -v --tb=short`

- [ ] **Step 3: Ensure CI executes the validation path**

Add minimal workflow coverage only if current CI would miss it.

- [ ] **Step 4: Re-run the same validation tests**

Run: `python -m pytest tests/test_command_docs.py tests/cli/test_json_contracts.py -v --tb=short`

- [ ] **Step 5: Run Package B regression slice**

Run: `python -m pytest tests/test_command_docs.py tests/cli/test_json_contracts.py -v --tb=short`

- [ ] **Step 6: Record Package B milestone without committing unless user requests it**

Expected state: doc/skill command drift is machine-detectable.

### Task B5: Verify Live Slash-Route Ownership and Fallback Behavior

**Files:**
- Reference: `paperforge/skills/paperforge/SKILL.md`
- Reference: `paperforge/skills/paperforge/workflows/*.md`
- Reference: `paperforge/cli.py`

- [ ] **Step 1: Define the expected owner and behavior for each known slash route**

Cover `/pf-sync`, `/pf-ocr`, `/pf-status`, `/pf-deep`, `/pf-paper`.

- [ ] **Step 2: Verify one malformed or unknown slash command path**

Confirm it triggers deterministic clarification or unsupported-command behavior rather than accidental fallback.

- [ ] **Step 3: Record expected vs actual behavior in the milestone notes**

Capture owner, execution path, and fallback result for each checked route.

- [ ] **Step 4: Treat this verification as a Package B milestone gate**

Package B is not complete until route ownership and fallback behavior have been manually verified.

---

## Package C: Documentation IA Reset

### Task C1: Create Canonical User Tutorial and Troubleshooting Docs

**Files:**
- Create: `docs/getting-started.md`
- Create: `docs/troubleshooting.md`
- Modify: `README.md`
- Modify: `README.en.md`

- [ ] **Step 1: Draft `docs/getting-started.md` as the single user happy-path source**

Cover install-after-check, BBT export, first sync, OCR when needed, `/pf-deep`, `/pf-paper`, and the shortest normal path.

- [ ] **Step 2: Draft `docs/troubleshooting.md` for failure recovery only**

Move user-facing troubleshooting guidance out of README and AGENTS.

- [ ] **Step 3: Update README links to the new docs only after both docs exist**

Ensure no duplicate full workflow remains in README.

- [ ] **Step 4: Manually verify tutorial ownership and link integrity**

Expected: only one canonical workflow narrative remains.

- [ ] **Step 5: Record checkpoint without committing unless user requests it**

Expected state: user docs are split into entry page + tutorial + troubleshooting.

### Task C2: Reshape README into Entry Pages

**Files:**
- Modify: `README.md`
- Modify: `README.en.md`

- [ ] **Step 1: Create a target outline for both READMEs**

The outline must be limited to overview, install options, quickstart, and doc map.

- [ ] **Step 2: Rewrite `README.md` as a navigation-first entry page**

Remove full tutorial, deep troubleshooting, and maintainer detail.

- [ ] **Step 3: Rewrite `README.en.md` to match the same structure**

Keep scope equivalent even if wording differs.

- [ ] **Step 4: Verify both README files point to the new canonical docs**

Manually check links and scope boundaries.

- [ ] **Step 5: Record checkpoint without committing unless user requests it**

Expected state: README is no longer the entire manual.

### Task C3: Convert `AGENTS.md` into Agent-Only Guidance

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/getting-started.md`
- Modify: `docs/troubleshooting.md`

- [ ] **Step 1: Strip end-user tutorial, FAQ, and user update content from `AGENTS.md`**

Keep repo operating rules, architecture boundaries, source-of-truth guidance, and doc map for agents.

- [ ] **Step 2: Move any removed user guidance into the correct user docs**

Do not silently drop content that still matters.

- [ ] **Step 3: Add a concise doc map in `AGENTS.md`**

Point agents to README, getting-started, troubleshooting, commands, architecture, and maintainer docs by audience.

- [ ] **Step 4: Manually verify that a normal user no longer needs `AGENTS.md`**

- [ ] **Step 5: Record checkpoint without committing unless user requests it**

Expected state: `AGENTS.md` is agent-only.

### Task C4: Purify Command Reference and Establish Maintainer Ownership

**Files:**
- Modify: `docs/COMMANDS.md`
- Modify: `docs/ARCHITECTURE.md`
- Create: `docs/maintainer-guide.md`

- [ ] **Step 1: Rewrite `docs/COMMANDS.md` into pure reference form**

Keep command purpose, prerequisites, key flags, examples. Remove tutorial and stale platform roadmap language.

- [ ] **Step 2: Refresh `docs/ARCHITECTURE.md` to current architecture reality or reduce it to a stable maintainer overview**

Remove stale version framing and outdated file ownership claims.

- [ ] **Step 3: Create `docs/maintainer-guide.md`**

Own release, testing, versioning, migration links, and architecture-navigation concerns here.

- [ ] **Step 4: Verify link integrity and audience split manually**

- [ ] **Step 5: Run doc-validation tests if they cover links or command examples**

Run: `python -m pytest tests/test_command_docs.py -v --tb=short`

- [ ] **Step 6: Record Package C milestone without committing unless user requests it**

Expected state: doc IA is explicit by file ownership.

---

## Package D: Progressive Disclosure UX

### Task D1: Stage the Setup Wizard Around First Sync

**Files:**
- Modify: `paperforge/plugin/main.js`
- Test: `paperforge/plugin/tests/runtime.test.mjs`
- Test: `tests/journey/test_onboarding.py`

- [ ] **Step 1: Define and encode first-sync-only required fields**

Separate mandatory-for-first-sync from later-stage OCR/agent/vector configuration.

- [ ] **Step 2: Add or update onboarding tests to reflect staged requirements**

Run: `python -m pytest tests/journey/test_onboarding.py -v --tb=short`

- [ ] **Step 3: Implement staged setup gating in the plugin**

Do not redesign the wizard; only change requirement timing and copy.

- [ ] **Step 5: Re-run onboarding and plugin tests**

Run: `python -m pytest tests/journey/test_onboarding.py -v --tb=short`

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs`

- [ ] **Step 6: Record checkpoint without committing unless user requests it**

Expected state: first sync is no longer blocked by later-stage features.

### Task D2: Fix Persistent Core Action Visibility

**Files:**
- Modify: `paperforge/plugin/main.js`
- Test: `paperforge/plugin/tests/commands.test.mjs`

- [ ] **Step 1: Identify the current primary action rendering path for the Home/Global surface**

Map where Sync, OCR, Status, Doctor, Repair, and Open Library are conditionally shown.

- [ ] **Step 2: Add or extend tests for persistent primary action visibility**

Run: `cd paperforge/plugin && npx vitest run tests/commands.test.mjs`

- [ ] **Step 3: Consolidate core actions into one persistent primary action group**

Do not redesign the information model; only normalize placement.

- [ ] **Step 4: Re-run plugin action tests**

Run: `cd paperforge/plugin && npx vitest run tests/commands.test.mjs`

- [ ] **Step 5: Record checkpoint without committing unless user requests it**

Expected state: users no longer have to guess where core mechanical actions live.

### Task D3: Collapse Advanced Controls and Normalize User-Facing Copy

**Files:**
- Modify: `paperforge/plugin/main.js`
- Test: `paperforge/plugin/tests/errors.test.mjs`

- [ ] **Step 1: Freeze the glossary chosen by Package C**

List the canonical terms for Dashboard/Home, Runtime update action, Paper view naming, and other repeated surfaces.

- [ ] **Step 2: Hide advanced memory/vector/runtime controls behind one default-collapsed section**

Retain access for power users.

- [ ] **Step 3: Rewrite user-facing errors to lead with next action**

Keep technical details available secondarily.

- [ ] **Step 4: Sweep docs and UI copy for glossary compliance**

Touch only user-facing strings inside plugin UI. Documentation glossary adoption belongs to Package C.

- [ ] **Step 5: Re-run focused plugin error tests and perform a manual first-run walkthrough**

Run: `cd paperforge/plugin && npx vitest run tests/errors.test.mjs`

- [ ] **Step 6: Record Package D milestone without committing unless user requests it**

Expected state: complexity is reduced by staging, hiding, and consistent terms rather than by a rewrite.

---

## Final Verification

- [ ] **Step 1: Run the Python contract/doc regression slice**

Run: `python -m pytest tests/unit/commands/test_embed.py tests/unit/commands/test_runtime_health.py tests/unit/memory/test_refresh.py tests/test_asset_index.py tests/test_asset_index_integration.py tests/test_repair.py tests/cli/test_json_contracts.py tests/test_command_docs.py tests/journey/test_onboarding.py -v --tb=short`

- [ ] **Step 2: Run plugin regression slice**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs tests/commands.test.mjs tests/errors.test.mjs tests/vector-ready.test.mjs`

- [ ] **Step 3: Run broader repo checks if time and scope allow**

Run: `python -m pytest tests/e2e/test_sync_pipeline.py tests/e2e/test_status_doctor_repair.py -v --tb=short`

- [ ] **Step 4: Verify docs manually by audience**

Check:
- user can navigate from README to getting-started without reading AGENTS
- agent can learn repo rules from AGENTS without user workflow noise
- maintainer can find release/testing/version docs from `docs/maintainer-guide.md`

- [ ] **Step 5: Prepare release notes by milestone, but do not create commits unless the user explicitly asks**
