# Phase 10: Documentation & Cohesion — Execution Plan

## Phase Goal

Document architecture and design decisions, create migration guide for v1.1 → v1.2, establish unified command documentation template, and perform consistency audit.

## Requirements Mapping

| Requirement | Task | Acceptance Criteria |
|-------------|------|---------------------|
| SYS-03 | Task 1 | ARCHITECTURE.md covers two-layer design, data flow, ADR records |
| SYS-06 | Task 2 | MIGRATION-v1.2.md covers all breaking changes + rollback |
| SYS-04 | Tasks 3-4 | docs/COMMANDS.md + command/*.md with unified template |
| SYS-05 | Tasks 5-6 | Consistency audit passes (scripts + checklist) |

---

## Task 1: Create ARCHITECTURE.md

**Objective:** Comprehensive architecture documentation for maintainers.

**Deliverable:** `docs/ARCHITECTURE.md`

**Content:**
1. **System Overview** — Two-layer design (Worker + Agent)
2. **Data Flow** — Complete pipeline from Zotero → Obsidian
3. **Directory Structure** — Rationale for each directory
4. **Commands Package** — Why `paperforge/commands/` pattern
5. **Design Decision Records (ADR)** — Key decisions from Phases 1-9:
   - ADR-001: Config precedence (Phase 1)
   - ADR-002: Pipeline split into worker/agent (Phase 1)
   - ADR-003: OCR async with state machine (Phase 2)
   - ADR-004: Base views config-aware (Phase 3)
   - ADR-005: Deep reading three-pass (Phase 4)
   - ADR-006: Fixture-based smoke tests (Phase 5)
   - ADR-007: CLI/worker consistency (Phase 6)
   - ADR-008: Three-way repair (Phase 7)
   - ADR-009: Rollback in prepare (Phase 8)
   - ADR-010: Command unification (Phase 9)
6. **Extension Points** — How to add new commands, new agent platforms

**Acceptance Criteria:**
- [ ] All 10 ADRs documented
- [ ] Data flow diagram (ASCII or markdown)
- [ ] Directory structure with rationale
- [ ] Extension guide for contributors

---

## Task 2: Create MIGRATION-v1.2.md

**Objective:** Complete migration guide from v1.1 to v1.2.

**Deliverable:** `docs/MIGRATION-v1.2.md`

**Content:**
1. **Overview** — What's new in v1.2
2. **Breaking Changes**
   - Package rename: `paperforge_lite` → `paperforge`
   - Command rename: `selection-sync` → `sync`, `index-refresh` → `sync`, `ocr run` → `ocr`
   - Agent commands: `/LD-*`, `/lp-*` → `/pf-*`
3. **Migration Steps**
   - Step 1: Backup
   - Step 2: Uninstall old package
   - Step 3: Install new package
   - Step 4: Update scripts/aliases
   - Step 5: Verify
4. **Import Path Changes**
   - `from paperforge_lite...` → `from paperforge...`
5. **Rollback Instructions**
   - How to downgrade to v1.1
6. **FAQ**
   - Common issues and solutions

**Acceptance Criteria:**
- [ ] All breaking changes documented
- [ ] Step-by-step migration instructions
- [ ] Rollback instructions included
- [ ] FAQ covers common issues

---

## Task 3: Create docs/COMMANDS.md

**Objective:** Master command reference with Agent ↔ CLI mapping.

**Deliverable:** `docs/COMMANDS.md`

**Content:**
1. **Command Matrix** — All commands in a table:
   | Agent Command | CLI Command | Description | Requires |
   |---------------|-------------|-------------|----------|
   | /pf-deep | paperforge sync + ocr | Deep reading | OCR done |
   | /pf-paper | paperforge sync | Quick summary | Formal note |
   | /pf-ocr | paperforge ocr | OCR extraction | PDF + do_ocr |
   | /pf-sync | paperforge sync | Sync literature | Zotero JSON |
   | /pf-status | paperforge status | System status | Config |
2. **Quick Reference** — One-liner for each command
3. **Platform Notes** — Differences between OpenCode/Codex/Claude Code

**Acceptance Criteria:**
- [ ] All 5 agent commands mapped
- [ ] All CLI commands mapped
- [ ] Platform differences noted

---

## Task 4: Unify command/*.md Template

**Objective:** Standardize all per-command docs with unified template.

**Deliverable:** Updated `command/pf-*.md` files

**Template Structure:**
```markdown
# /{command-name}

## Purpose
## CLI Equivalent
## Prerequisites
## Arguments
## Example
## Output
## Error Handling
## Platform Notes (OpenCode/Codex/Claude Code)
```

**Files to Update:**
- `command/pf-deep.md`
- `command/pf-paper.md`
- `command/pf-ocr.md`
- `command/pf-sync.md`
- `command/pf-status.md`

**Acceptance Criteria:**
- [ ] All 5 docs follow unified template
- [ ] Platform notes section present
- [ ] CLI equivalent clearly stated

---

## Task 5: Consistency Audit Scripts

**Objective:** Automated checks for hard constraints.

**Deliverable:** `scripts/consistency_audit.py`

**Checks:**
1. No old command names in active code/docs
   - `paperforge selection-sync` (except migration guide)
   - `paperforge index-refresh` (except migration guide)
   - `paperforge ocr run` (except migration guide)
   - `/LD-deep`, `/LD-paper`
   - `/lp-ocr`, `/lp-index-refresh`, `/lp-selection-sync`, `/lp-status`
2. No references to `paperforge_lite` in Python code
3. No dead internal links in markdown
4. All command/*.md files have valid structure

**Acceptance Criteria:**
- [ ] Script runs without errors
- [ ] All hard constraints pass
- [ ] Script can be run in CI

---

## Task 6: Manual Consistency Checklist

**Objective:** Human review for soft constraints.

**Deliverable:** `docs/CONSISTENCY-CHECKLIST.md`

**Checklist Items:**
- [ ] Terminology: "PaperForge Lite" vs "PaperForge" usage consistent
- [ ] Branding: All user-facing docs use correct product name
- [ ] Style: Markdown formatting consistent (headers, lists, code blocks)
- [ ] Cross-references: All internal links work
- [ ] Version numbers: All docs reference correct version (v1.2)
- [ ] Command examples: All use `python -m paperforge` (not paperforge_lite)
- [ ] Agent commands: All use `/pf-*` (not /LD-* or /lp-*)

**Acceptance Criteria:**
- [ ] Checklist created
- [ ] All items reviewed
- [ ] Issues documented (if any)

---

## Task 7: Verification & State Update

**Objective:** Final verification and project state update.

**Steps:**
1. Run consistency audit script
2. Review manual checklist
3. Run test suite: `pytest tests/ -v`
4. Update STATE.md — Phase 10 complete
5. Update ROADMAP.md — Phase 10 marked done
6. Create 10-SUMMARY.md
7. Commit all changes

**Acceptance Criteria:**
- [ ] Audit script passes
- [ ] Test suite passes (or matches baseline)
- [ ] STATE.md updated
- [ ] ROADMAP.md updated
- [ ] 10-SUMMARY.md created

---

## Wave Structure

| Wave | Tasks | Description |
|------|-------|-------------|
| 1    | Task 1 | ARCHITECTURE.md |
| 2    | Task 2 | MIGRATION-v1.2.md |
| 3    | Tasks 3-4 | COMMANDS.md + command/*.md template |
| 4    | Tasks 5-6 | Consistency audit (script + checklist) |
| 5    | Task 7  | Verification & state update |

## Estimated Duration

~2.5 hours

## Dependencies

- Phase 9 complete (command unification done)
- All prior context files accessible
