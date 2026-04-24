# Roadmap: v1.2 Systematization & Cohesion

> Phase plan for Milestone v1.2. See REQUIREMENTS-v1.2.md for detailed requirements.

---

## Overview

**Goal:** Transform PaperForge Lite from a functional-but-scattered prototype into a cohesive, user-centric system.

**Approach:** Two-phase roadmap — first unify commands and simplify CLI, then document and ensure cohesion.

**Success Criteria:**
- All agent commands use `/pf-*` namespace
- CLI has user-centric command set
- Documentation is consistent and complete
- Existing tests still pass
- Migration path exists for existing users

---

## Phase 9: Command Unification & CLI Simplification

**Goal:** Implement unified `/pf-*` namespace and simplify CLI commands.

### Tasks

1. **Agent Command Aliases**
   - Create `/pf-deep` as alias for `/LD-deep`
   - Create `/pf-paper` as alias for `/LD-paper`
   - Create `/pf-ocr` as alias for `/lp-ocr`
   - Create `/pf-sync` as alias for `/lp-selection-sync` + `/lp-index-refresh`
   - Create `/pf-status` as alias for `/lp-status`
   - Add `/pf-doctor` command
   - Add deprecation warnings to old commands

2. **CLI Command Simplification**
   - Implement `paperforge sync` (combines selection-sync + index-refresh)
   - Add `--full` and `--dry-run` flags to `sync`
   - Add "consider using sync" hints to `selection-sync` and `index-refresh`
   - Evaluate `ocr run` + `ocr doctor` merger
   - Update CLI help text to be user-centric

3. **Command Dispatch Layer**
   - Create unified command dispatch module
   - Ensure `/pf-*` and CLI commands share implementation
   - Add command metadata (description, prerequisites, examples)

4. **Backward Compatibility Tests**
   - Test old commands still work during deprecation
   - Test deprecation warnings appear
   - Verify no regression in existing smoke tests

### Deliverables
- `command/pf-deep.md`, `command/pf-paper.md`, `command/pf-ocr.md`, `command/pf-sync.md`, `command/pf-status.md`, `command/pf-doctor.md`
- Updated `paperforge/cli.py` with simplified commands
- `tests/test_unified_commands.py`

### Definition of Done
- All `/pf-*` commands work in sandbox
- All old commands work with deprecation warnings
- `paperforge sync` works end-to-end
- 17 existing smoke tests still pass
- New unified command tests pass

---

## Phase 10: Documentation & Cohesion

**Goal:** Document architecture, create migration guide, ensure consistency.

### Tasks

1. **Architecture Documentation**
   - Create `docs/ARCHITECTURE.md`
   - Document two-layer design (Worker + Agent)
   - Document command dispatch pattern
   - Document directory structure rationale

2. **Unified Command Reference**
   - Create `docs/COMMANDS.md`
   - Include agent ↔ CLI mapping matrix
   - Cross-reference related commands
   - Update AGENTS.md with unified reference

3. **Migration Guide**
   - Create `docs/MIGRATION-v1.2.md`
   - Old → new command mapping table
   - Deprecation timeline
   - FAQ for common issues

4. **Command Doc Restructuring**
   - Restructure all `command/*.md` files
   - Standard template: purpose, prerequisites, examples, related commands
   - Deprecation notices on old command docs

5. **Consistency Audit**
   - Audit all docs for consistent terminology
   - Ensure "PaperForge" branding is consistent
   - Verify command examples work in sandbox
   - Check cross-references are valid

### Deliverables
- `docs/ARCHITECTURE.md`
- `docs/COMMANDS.md`
- `docs/MIGRATION-v1.2.md`
- Restructured `command/*.md` files
- Updated `AGENTS.md`

### Definition of Done
- All docs use unified `/pf-*` naming
- Migration guide is complete and tested
- Architecture doc accurately describes current system
- No broken cross-references
- Consistency audit passed

---

## Timeline

| Phase | Estimated Duration | Dependencies |
|-------|-------------------|--------------|
| 9 | 1-2 sessions | v1.1 complete |
| 10 | 1 session | Phase 9 complete |

**Total:** 2-3 sessions

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Users confused by command changes | Medium | Medium | Deprecation warnings, migration guide |
| Tests break during refactoring | Medium | High | Maintain backward compatibility, test both old and new |
| Docs become inconsistent | Medium | Medium | Consistency audit as final task |
| Scope creep (adding features) | Medium | High | Strict "no new features" rule |

---

## Post-v1.2 Ideas (Backlog)

- Remove `/LD-*` and `/lp-*` commands (v1.3)
- Add `paperforge config` command for user settings
- Plugin system for OCR providers
- Scheduled/automated worker triggers (if design changes)

---

*Created: 2026-04-24*
*Milestone: v1.2 Systematization & Cohesion*
