---
phase: 10-documentation-and-cohesion
plan: 10
subsystem: docs
tags: [documentation, commands, cli, agent-commands, markdown]

# Dependency graph
requires:
  - phase: 09-command-unification
    provides: unified /pf-* command namespace and paperforge CLI
provides:
  - docs/COMMANDS.md master reference with Agent/CLI matrix
  - Unified template for all command/*.md files
  - Platform notes (OpenCode/Codex/Claude Code) in every command doc
  - Cross-references between command docs, AGENTS.md, and COMMANDS.md
  - scripts/consistency_audit.py automated hard-constraint checker
  - docs/CONSISTENCY-CHECKLIST.md manual soft-constraint checklist
affects:
  - AGENTS.md (referenced, not modified)
  - command/*.md (all 5 files)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Unified documentation template: Purpose, CLI Equivalent, Prerequisites, Arguments, Example, Output, Error Handling, Platform Notes, See Also"
    - "Agent-CLI command matrix mapping"
    - "Bilingual documentation: English headers, Chinese content"

key-files:
  created:
    - docs/COMMANDS.md
    - scripts/consistency_audit.py
    - docs/CONSISTENCY-CHECKLIST.md
  modified:
    - command/pf-deep.md
    - command/pf-paper.md
    - command/pf-ocr.md
    - command/pf-sync.md
    - command/pf-status.md
    - AGENTS.md
    - docs/COMMANDS.md
    - paperforge/cli.py
    - paperforge/ocr_diagnostics.py
    - pipeline/worker/scripts/literature_pipeline.py
    - scripts/welcome.py
    - skills/literature-qa/prompt_deep_subagent.md
    - skills/literature-qa/scripts/ld_deep.py

key-decisions:
  - "Preserved Chinese as primary content language for consistency with existing docs and AGENTS.md"
  - "Used English section headers per template spec for standardization"
  - "Added Platform Notes section to all 5 command docs even for CLI-only commands"
  - "Preserved all detailed functional content (subagent spawn guide, reading structure, diagnostic levels) during reformatting"

patterns-established:
  - "Command docs: 9-section template mandatory for all /pf-* documentation"
  - "Cross-reference linking: every command doc links to COMMANDS.md and AGENTS.md"
  - "Platform Notes: document OpenCode current behavior + Codex/Claude Code future plans"

requirements-completed: [SYS-04, SYS-05]

# Metrics
duration: 6min
completed: 2026-04-24
---

# Phase 10 (Wave 3): Command Documentation Summary

**Master command reference (docs/COMMANDS.md) with Agent/CLI matrix, plus all 5 command docs standardized to unified 9-section template with platform notes and cross-references**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-24T00:00:00Z
- **Completed:** 2026-04-24T00:06:00Z
- **Tasks:** 2 (Tasks 3-4 of Phase 10)
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- Created `docs/COMMANDS.md` with full Agent/CLI command matrix, quick reference, workflow guide, and platform notes
- Standardized all 5 `command/*.md` files to unified template:
  - Purpose, CLI Equivalent, Prerequisites, Arguments, Example, Output, Error Handling, Platform Notes, See Also
- Preserved all existing functional content during reformatting:
  - `/pf-deep`: subagent spawn guide, Keshav 3-pass structure, figure requirements, supplementary rules
  - `/pf-paper`: Q&A mode rules, multi-paper loading, parsing rules
  - `/pf-ocr`: diagnostic levels L1-L4, options table, exit codes
  - `/pf-sync`: phased execution examples, options table
  - `/pf-status`: installation checks, path verification
- Added Platform Notes section (OpenCode/Codex/Claude Code) to all 5 docs
- Added See Also cross-references linking to AGENTS.md and COMMANDS.md

## Task Commits

Each task was committed atomically:

1. **Task 3: Create docs/COMMANDS.md** - `5aeacae` (docs)
2. **Task 4: Unify command/*.md template** - `cf761d1` (docs)

## Files Created/Modified

- `docs/COMMANDS.md` - Master command reference with matrix, workflow, platform notes (created)
- `command/pf-deep.md` - Restructured to unified template; preserved subagent guide and reading structure
- `command/pf-paper.md` - Restructured to unified template; preserved Q&A mode and multi-paper rules
- `command/pf-ocr.md` - Restructured to unified template; preserved diagnostic levels and options
- `command/pf-sync.md` - Restructured to unified template; preserved phased execution examples
- `command/pf-status.md` - Restructured to unified template; preserved status check descriptions

## Decisions Made

- **Language consistency**: Kept Chinese as primary content language (matching AGENTS.md and existing docs), using English for command names and section headers per template spec
- **Content preservation priority**: During reformatting, all detailed content (spawn guides, structure templates, diagnostic levels) was preserved rather than summarized or truncated
- **CLI-only command treatment**: Even though `/pf-ocr`, `/pf-sync`, `/pf-status` are primarily CLI commands, documented them with the same template and noted their CLI-only nature in Platform Notes
- **Platform notes for all**: Added OpenCode/Codex/Claude Code sections to every command doc, noting current vs. future support

## Deviations from Plan

None - plan executed exactly as written.

All content from the original command/*.md files was preserved during reformatting. No functional changes were made.

## Issues Encountered

None. All files written successfully. Git commits completed without errors.

## Next Phase Readiness

- Wave 3 (Tasks 3-4) complete
- Wave 4 (Tasks 5-6) complete
- Remaining Phase 10 waves:
  - Wave 5: Task 7 — Verification & state update
- Consistency audit infrastructure is in place and passing
- Command documentation foundation is solid and ready for final verification

---

# Phase 10 (Wave 4): Consistency Audit Summary

**Automated consistency audit script (`scripts/consistency_audit.py`) and manual checklist (`docs/CONSISTENCY-CHECKLIST.md`) for hard and soft constraint verification**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 (Tasks 5-6 of Phase 10)
- **Files created:** 2 (1 script, 1 checklist)
- **Files modified:** 12 (violations fixed across codebase)

## Accomplishments

- Created `scripts/consistency_audit.py` with 4 automated checks:
  - Check 1: No old command names in active code/docs
  - Check 2: No `paperforge_lite` references in Python code
  - Check 3: No dead internal links in markdown
  - Check 4: All command/*.md files have required structure sections
- Created `docs/CONSISTENCY-CHECKLIST.md` with manual review items:
  - Terminology, commands, cross-references, version references
  - Style, branding, platform notes
  - Review sign-off table
- Fixed all violations discovered by the audit:
  - Updated `paperforge/ocr_diagnostics.py` error messages to use `paperforge ocr --diagnose`
  - Updated `pipeline/worker/scripts/literature_pipeline.py` generated content to use `/pf-deep`
  - Updated `scripts/welcome.py` to recommend `/pf-deep`
  - Updated `skills/literature-qa/prompt_deep_subagent.md` title to `/pf-deep`
  - Updated `skills/literature-qa/scripts/ld_deep.py` docstrings and error messages to `/pf-deep`
  - Fixed dead links in `docs/COMMANDS.md` (command file references)
  - Fixed dead links in all `command/*.md` files (COMMANDS.md references)
  - Updated `AGENTS.md` section 11 to reference `MIGRATION-v1.2.md`
  - Updated `paperforge/cli.py` module docstring to use current command names

## Task Commits

1. **Task 5: Consistency audit script** - `abab8df` (feat)
2. **Task 6: Manual consistency checklist** - `f0d2fa1` (docs)

## Files Created/Modified

- `scripts/consistency_audit.py` - Automated audit script with 4 checks (created)
- `docs/CONSISTENCY-CHECKLIST.md` - Manual review checklist (created)
- `paperforge/ocr_diagnostics.py` - Updated error messages to use new commands
- `pipeline/worker/scripts/literature_pipeline.py` - Updated generated content to use `/pf-deep`
- `scripts/welcome.py` - Updated welcome message to use `/pf-deep`
- `skills/literature-qa/prompt_deep_subagent.md` - Updated title to `/pf-deep`
- `skills/literature-qa/scripts/ld_deep.py` - Updated docstrings and error messages
- `docs/COMMANDS.md` - Fixed dead links to command files
- `command/pf-deep.md` - Fixed dead link to COMMANDS.md
- `command/pf-paper.md` - Fixed dead link to COMMANDS.md
- `command/pf-ocr.md` - Fixed dead link to COMMANDS.md
- `command/pf-sync.md` - Fixed dead link to COMMANDS.md
- `command/pf-status.md` - Fixed dead link to COMMANDS.md
- `AGENTS.md` - Updated migration section to reference migration guide
- `paperforge/cli.py` - Updated module docstring to use current commands

## Decisions Made

- **Audit scope**: Exclude migration guide (`docs/MIGRATION-v1.2.md`), architecture ADR docs (`docs/ARCHITECTURE.md`), planning docs (`.planning/`), and the audit script itself from checks
- **Backward compatibility documentation**: `cli.py` docstrings and `setup_wizard.py` migration notes are acceptable since they explicitly document deprecated aliases
- **Historical context**: ADR-010 in `ARCHITECTURE.md` mentions old command names as historical context; this is acceptable

## Deviations from Plan

**Auto-fixed Issues (Rule 1 & 2)**

1. **[Rule 1 - Bug] Fixed dead internal links**
   - **Found during:** Task 5 (Check 3)
   - **Issue:** `docs/COMMANDS.md` linked to `pf-deep.md` etc. as relative paths, but those files are in `command/`, not `docs/`
   - **Fix:** Updated all command file links to use `../command/pf-*.md`
   - **Files modified:** `docs/COMMANDS.md`, `command/pf-*.md` (5 files)
   - **Commit:** `abab8df`

2. **[Rule 1 - Bug] Fixed user-facing old command references**
   - **Found during:** Task 5 (Check 1)
   - **Issue:** Multiple user-facing strings still referenced old commands (`paperforge ocr doctor`, `/LD-deep`, `index-refresh`)
   - **Fix:** Updated error messages, generated content, welcome messages, and skill docstrings to use current command names
   - **Files modified:** `paperforge/ocr_diagnostics.py`, `pipeline/worker/scripts/literature_pipeline.py`, `scripts/welcome.py`, `skills/literature-qa/prompt_deep_subagent.md`, `skills/literature-qa/scripts/ld_deep.py`, `AGENTS.md`, `paperforge/cli.py`
   - **Commit:** `abab8df`

## Issues Encountered

None blocking. All violations were straightforward fixes.

## Next Phase Readiness

- Wave 4 (Tasks 5-6) complete
- Remaining Phase 10 waves:
  - Wave 5: Task 7 — Verification & state update
- Consistency audit infrastructure is in place and passing
- Command documentation foundation is solid and ready for final verification

---

*Phase: 10-documentation-and-cohesion (Wave 4)*
*Completed: 2026-04-24*

---

*Phase: 10-documentation-and-cohesion (Wave 3)*
*Completed: 2026-04-24*

## Self-Check: PASSED

- [x] `docs/COMMANDS.md` exists and is readable
- [x] `command/pf-deep.md` exists and is readable
- [x] `command/pf-paper.md` exists and is readable
- [x] `command/pf-ocr.md` exists and is readable
- [x] `command/pf-sync.md` exists and is readable
- [x] `command/pf-status.md` exists and is readable
- [x] `scripts/consistency_audit.py` exists and runs (4/4 checks pass)
- [x] `docs/CONSISTENCY-CHECKLIST.md` exists and is readable
- [x] Commit `5aeacae` (Task 3) verified in git log
- [x] Commit `cf761d1` (Task 4) verified in git log
- [x] Commit `abab8df` (Task 5) verified in git log
- [x] Commit `f0d2fa1` (Task 6) verified in git log
- [x] All 15 files created/modified as expected
