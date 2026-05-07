---
phase: 18
phase_name: "Documentation UX Polish"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 10
  lessons: 4
  patterns: 5
  surprises: 0
missing_artifacts:
  - "UAT.md"
  - "VERIFICATION.md"
---

## Decisions

### auto_analyze_after_ocr defaults to false (opt-in)

Users must explicitly set `auto_analyze_after_ocr: true` in paperforge.json. This avoids unexpected behavioral changes — existing workflows remain unchanged until the user opts in.

**Source:** 18-01-PLAN.md (task 1, line 77), 18-01-SUMMARY.md

---

### Config option placed as top-level key in paperforge.json

The new field sits alongside changelog_url at the top level, not nested under a sub-key. Simple access pattern consistent with other single-value settings.

**Source:** 18-01-PLAN.md (task 1, line 77), 18-01-SUMMARY.md

---

### Hook wrapped in try/except so a single failure does not abort OCR batch

If the auto_analyze hook fails (e.g., library-record not found, JSON parse error), the error is logged as a warning and the OCR batch continues processing remaining items.

**Source:** 18-01-PLAN.md (task 1, lines 84-101), 18-01-SUMMARY.md

---

### CHANGELOG.md uses Keep a Changelog format

Standardized format with [Unreleased], version headers, and Added/Changed/Fixed subsections. Ensures consistency and readability.

**Source:** 18-01-PLAN.md (task 2), 18-01-SUMMARY.md

---

### CHANGELOG.md does NOT update paperforge.json changelog_url

The existing changelog_url in paperforge.json points to GitHub Releases for update checking. The new CHANGELOG.md is a local document for user reference — separate purposes, separate URLs.

**Source:** 18-01-PLAN.md (task 2, line 169), 18-01-SUMMARY.md

---

### ADR-012 documents _utils.py leaf module constraint from Phase 14

Formal architecture decision record capturing the leaf module constraint — _utils.py must never import from paperforge.worker.* or paperforge.commands.* — only from stdlib and paperforge.config.

**Source:** 18-02-PLAN.md (task 2, lines 140-146), 18-02-SUMMARY.md

---

### ADR-013 documents dual-output logging strategy from Phase 13

Formal architecture decision record capturing the stdout (user-facing) vs stderr (diagnostic) split, configure_logging() function, and PAPERFORGE_LOG_LEVEL env var pattern.

**Source:** 18-02-PLAN.md (task 2, lines 148-154), 18-02-SUMMARY.md

---

### AGENTS.md command mapping table follows v1.2 namespace conventions

The "操作速查" table maps paperforge CLI commands to /pf-* agent commands, following the established v1.2+ naming convention.

**Source:** 18-02-PLAN.md (task 2, lines 163-174), 18-02-SUMMARY.md

---

### chart-reading INDEX ordered by biomedical commonness per D-04

19 guides ordered from most common (bar/column charts, forest plots) to least common (QQ plots). Guides not in D-04's primary list appended in logical groups.

**Source:** 18-02-PLAN.md (task 3, lines 201-243), 18-02-SUMMARY.md

---

### README.md orphaned code lines removed rather than enclosed in fences

Three orphaned lines (legacy python <resolved_worker_script> commands) and their lone closing backtick were removed outright, letting the quote block flow directly to the License section.

**Source:** 18-02-PLAN.md (task 1, lines 113-118), 18-02-SUMMARY.md

---

## Lessons

### OCR hook placement matters: must run BEFORE selection-sync

The auto_analyze hook inserts at line 1499 (after ocr_status=done) but before _sync.run_selection_sync(vault) at line ~1589. This ensures the frontmatter change to analyze:true is not overwritten by the sync.

**Context:** selection-sync does not overwrite user-controlled fields like analyze, but placing the hook after sync would still cause a timing issue where the user would see the record before the auto-update.

**Source:** 18-01-PLAN.md (task 1, lines 108-109), 18-01-SUMMARY.md

---

### Existing re and read_json imports eliminated need for new imports in ocr.py

Both `re` and `read_json` (from _utils.py) were already imported in ocr.py. The auto_analyze hook required no new import statements, simplifying the change.

**Source:** 18-01-PLAN.md (task 1, line 105), 18-01-SUMMARY.md

---

### Keep a Changelog format provides clear structure with minimal maintenance

The format's Added/Changed/Fixed subsections and version-header structure makes it easy to review release history without over-documenting individual commits.

**Source:** 18-01-PLAN.md (task 2), 18-01-SUMMARY.md

---

### Using v1.2 migration doc as template for v1.4 migration doc ensured consistency

Following the established structure (What's New, Breaking Changes, Detailed sections, Migration Steps, Rollback, FAQ) from MIGRATION-v1.2.md provided a familiar format for users upgrading from v1.3.

**Source:** 18-02-PLAN.md (task 1, line 97), 18-02-SUMMARY.md

---

## Patterns

### try/except Guard for Non-Critical Automation Hooks

The auto_analyze hook wraps its entire body in try/except so failure (missing file, parse error, etc.) is logged but never aborts the parent operation (OCR batch).

**Source:** 18-01-PLAN.md (task 1), 18-01-SUMMARY.md

---

### re.sub with MULTILINE Flag for Frontmatter Field Substitution

Using `re.sub(r"^analyze:.*$", "analyze: true", text, count=1, flags=re.MULTILINE)` for frontmatter field replacement — same pattern used by deep_reading.py's status sync.

**Source:** 18-01-PLAN.md (task 1, lines 93-98), 18-01-SUMMARY.md

---

### ADR Format Consistently Applied Across Architecture Decisions

All 13 ADRs follow the same format (Status, Phase, Context, Decision, Consequences), providing consistent reference regardless of when the decision was made.

**Source:** 18-02-PLAN.md (task 2), 18-02-SUMMARY.md

---

### Migration Doc Template Reuse

MIGRATION-v1.4.md uses the same structure as MIGRATION-v1.2.md (What's New, Breaking Changes, Detailed sections, Migration Steps, Rollback, FAQ). This provides a familiar experience for users who previously upgraded.

**Source:** 18-02-PLAN.md (task 1), 18-02-SUMMARY.md

---

### Command Mapping Table as User Reference

The "操作速查" table in AGENTS.md maps user intent ("what you want to do") to both the terminal command and the Agent command, serving as a quick reference for users switching between interfaces.

**Source:** 18-02-PLAN.md (task 2), 18-02-SUMMARY.md

---

## Surprises

None documented. Both plans executed exactly as written with zero deviations.

**Source:** 18-01-SUMMARY.md, 18-02-SUMMARY.md
