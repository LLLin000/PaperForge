# Requirements: v1.2 Systematization & Cohesion

> Requirements for Milestone v1.2. Derived from PROJECT.md and architecture research.

---

## Context

Milestone v1.1 hardened the sandbox onboarding flow. v1.2 transforms the project from a functional-but-scattered prototype into a cohesive, user-centric system.

Current state:
- Agent commands: `/LD-deep`, `/LD-paper`, `/lp-ocr`, `/lp-index-refresh`, `/lp-selection-sync`, `/lp-status`
- CLI commands: `paperforge selection-sync`, `index-refresh`, `ocr run`, `ocr doctor`, `deep-reading`, `repair`, `status`
- Two naming conventions confuse users
- `selection-sync` + `index-refresh` are almost always run together but are separate commands

---

## Requirements

### SYS-01: Unified Agent Command Namespace

**Description:** All agent commands must use the `/pf-*` prefix consistently.

**Acceptance Criteria:**
- [ ] `/pf-deep` replaces `/LD-deep` (deep reading)
- [ ] `/pf-paper` replaces `/LD-paper` (quick summary)
- [ ] `/pf-ocr` replaces `/lp-ocr` (OCR worker)
- [ ] `/pf-sync` replaces `/lp-selection-sync` + `/lp-index-refresh` (combined sync)
- [ ] `/pf-status` replaces `/lp-status` (status check)
- [ ] `/pf-doctor` is available (diagnostics)
- [ ] Old commands (`/LD-*`, `/lp-*`) still work but show deprecation warning
- [ ] All command docs updated to use new namespace

**Priority:** P0

---

### SYS-02: CLI Simplification

**Description:** Combine frequently-co-occurring CLI commands into user-centric workflows.

**Acceptance Criteria:**
- [ ] `paperforge sync` combines `selection-sync` + `index-refresh` with sensible defaults
- [ ] `paperforge sync --full` runs both with verbose output
- [ ] `paperforge sync --dry-run` previews what would happen
- [ ] Old commands (`selection-sync`, `index-refresh`) still work but show "consider using sync" hint
- [ ] `paperforge ocr` is simplified (evaluate whether `ocr run` + `ocr doctor` should merge)
- [ ] CLI help text is user-centric, not worker-centric

**Priority:** P0

---

### SYS-03: Command Consistency Matrix

**Description:** Ensure 1:1 mapping between agent commands and CLI commands where appropriate.

**Acceptance Criteria:**
- [ ] Matrix documenting agent command ↔ CLI command mapping exists
- [ ] Where functionality overlaps, names align (`/pf-sync` ↔ `paperforge sync`)
- [ ] Agent-only commands (`/pf-deep`) have clear CLI equivalents or documented rationale for absence
- [ ] CLI-only commands (`paperforge repair`) have documented agent equivalents or rationale

**Priority:** P1

---

### SYS-04: Architecture Documentation

**Description:** Document the intended architecture for contributors and advanced users.

**Acceptance Criteria:**
- [ ] `docs/ARCHITECTURE.md` exists explaining the two-layer design (Worker + Agent)
- [ ] `docs/COMMANDS.md` exists with unified command reference
- [ ] Command dispatch pattern documented (how `/pf-*` maps to implementation)
- [ ] Directory structure rationale documented

**Priority:** P1

---

### SYS-05: Migration Guide

**Description:** Help existing users transition from old commands to new commands.

**Acceptance Criteria:**
- [ ] `docs/MIGRATION-v1.2.md` exists
- [ ] Old → new command mapping table provided
- [ ] Deprecation timeline documented (when will `/LD-*` and `/lp-*` be removed?)
- [ ] No breaking changes to data formats or storage

**Priority:** P1

---

### SYS-06: Command Doc Restructuring

**Description:** Restructure command docs to match unified namespace and improve discoverability.

**Acceptance Criteria:**
- [ ] All command docs in `command/` use `/pf-*` naming
- [ ] Each command doc includes: purpose, prerequisites, examples, related commands
- [ ] Cross-references between agent and CLI versions of same command
- [ ] AGENTS.md updated with unified command reference

**Priority:** P1

---

### SYS-07: Test Coverage for Unified Commands

**Description:** Ensure tests cover both old and new command names during deprecation period.

**Acceptance Criteria:**
- [ ] Smoke tests verify `/pf-*` commands work
- [ ] Backward compatibility tests verify `/LD-*` and `/lp-*` still work
- [ ] Deprecation warnings are tested
- [ ] No regression in existing 17 smoke tests

**Priority:** P1

---

## Out of Scope

- No new functional features (no new AI capabilities, no new OCR features)
- No breaking changes to data formats, storage, or `.planning/` structure
- No changes to Zotero/Better BibTeX integration
- No changes to OCR provider (still PaddleOCR)
- No scheduled/automated worker triggers

---

## Dependencies

- v1.1 must be complete (Phase 8 done, all tests passing)
- All existing command docs must be readable
- `get-shit-done-main` architecture research completed

---

## Success Criteria

1. A new user can look at the command list and understand what each command does without knowing implementation details
2. Existing users can continue using old commands during deprecation period
3. All tests pass (existing 17 + new unified command tests)
4. Documentation is consistent across agent and CLI interfaces
5. The system "feels" cohesive — one namespace, one mental model

---

*Created: 2026-04-24*
*Milestone: v1.2 Systematization & Cohesion*
