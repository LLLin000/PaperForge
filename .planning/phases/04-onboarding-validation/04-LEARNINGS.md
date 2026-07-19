---
phase: 04
phase_name: "Onboarding Validation"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 8
  lessons: 3
  patterns: 2
  surprises: 0
missing_artifacts:
  - "UAT.md"
  - "VERIFICATION.md"
---

# Phase 04 Learnings: Onboarding Validation

## Decisions

### D1: Three-State `deep-reading` Output
`paperforge deep-reading` outputs three distinct sections: 就绪 (ready — OCR done), 等待 OCR (waiting — `do_ocr=true` and `ocr_status=pending/processing`), 阻塞 (blocked — `analyze=true` but OCR not done and not waiting).

**Rationale:** Users need to see at a glance which papers are ready for deep reading, which are waiting for OCR, and which are blocked by missing OCR configuration. The three-state breakdown prevents confusion between these fundamentally different states.

**Source:** 04-01-PLAN.md, 04-01-SUMMARY.md

---

### D2: `--verbose` Flag Shows Fix Instructions for Blocked Papers
When `--verbose` is passed, each blocked paper shows a specific fix instruction based on its `ocr_status`: pending → "run `paperforge ocr run`", processing → "wait for completion", failed → "check meta.json then retry".

**Rationale:** Blocked papers are the user's action items. Verbose mode eliminates guesswork by telling the user exactly what to do for each blocked paper.

**Source:** 04-01-PLAN.md, 04-01-SUMMARY.md

---

### D3: Doctor Checks 7 Categories
`paperforge doctor` validates 7 categories: Python environment, Vault structure, Zotero link, BBT export, OCR configuration, Worker scripts, Agent scripts.

**Rationale:** Covers the full installation and configuration surface. Each category is independently checkable and has a clear pass/fail/warn outcome.

**Source:** 04-02-PLAN.md, 04-02-SUMMARY.md

---

### D4: Doctor Output Format `[PASS]/[FAIL]/[WARN]` with Fix Suggestions
Each check category prints `[PASS]` / `[FAIL]` / `[WARN]` with a human-readable message. On failure, a "修复步骤" (fix steps) section follows with actionable instructions.

**Rationale:** Users need to quickly scan which checks passed and which need attention. The consistent prefix enables visual scanning while fix steps provide guidance.

**Source:** 04-02-PLAN.md, 04-02-SUMMARY.md

---

### D5: `run_deep_reading` Modified to Accept `verbose: bool = False`
The function signature was changed from `run_deep_reading(vault: Path)` to `run_deep_reading(vault: Path, verbose: bool = False)`.

**Rationale:** Adding an optional parameter with a default value maintains backward compatibility with existing call sites while enabling the new verbose behavior.

**Source:** 04-01-PLAN.md, 04-01-SUMMARY.md

---

### D6: AGENTS.md Uses `paperforge <command>` as Primary Invocation
All command examples in AGENTS.md were updated to show `paperforge <command>` as the primary invocation, with legacy `python ... literature_pipeline.py` paths retained as commented backup.

**Rationale:** New users should never see unresolved path tokens as their primary command reference. Existing users who know the old pattern still have a documented fallback.

**Source:** 04-03-PLAN.md, 04-03-SUMMARY.md

---

### D7: `docs/README.md` as User-Facing BBT Configuration Guide
Created as a separate user-facing document (distinct from AGENTS.md which is agent-facing) containing step-by-step Better BibTeX configuration instructions in Chinese.

**Rationale:** Different audiences need different documentation. Users configuring BBT for the first time need a linear step-by-step guide; agents need a command reference.

**Source:** 04-04-PLAN.md, 04-04-SUMMARY.md

---

### D8: `_is_junction()` Helper Function for Doctor Checks
Added a dedicated helper function `_is_junction(path: Path) -> bool` using Windows reparse point detection for the Zotero link validity check.

**Rationale:** The doctor needs to distinguish between a proper junction/symlink (recommended) and a regular directory copy (warn). The helper encapsulates platform-specific detection logic.

**Source:** 04-02-SUMMARY.md

---

## Lessons

### L1: Three-State Deep-Reading Logic Has Overlapping Categories
A paper with `do_ocr=true`, `analyze=true`, and `ocr_status=pending` is simultaneously "waiting for OCR" AND "blocked for deep reading." The output must handle this overlap without double-counting.

**Context:** The implementation logic uses a priority: ready (done) > waiting OCR (do_ocr + pending/processing) > blocked (analyze + not done and not waiting). An item appears in exactly one category based on the first matching condition.

**Source:** 04-01-PLAN.md

---

### L2: Legacy Commands Must Be Retained as Commented Backup
Users who installed PaperForge before the CLI unified entry point may not have `paperforge` registered as a command. These users need the legacy `python ...` path as a fallback.

**Context:** The command consistency check in Plan 05-01 confirmed that AGENTS.md properly retains legacy paths as commented fallbacks. Removing them entirely would break existing users.

**Source:** 04-03-PLAN.md, 05-01-SUMMARY.md

---

### L3: Handler Function Signature Evolution Requires Test Stub Updates
Adding the `verbose` parameter to `run_deep_reading` required updating the test stub `stub_run_deep_reading` to accept `verbose: bool = False` for backward compatibility.

**Context:** The CLI dispatch test stubs must match the worker function signatures. Adding a parameter to one requires updating all call sites in tests as well.

**Source:** 04-01-SUMMARY.md

---

## Patterns

### P1: Doctor Categorized Check Pattern
Each check category is implemented as an independent function returning a tuple of (status, message, fix_suggestion). The main `run_doctor` function iterates over all checks and collects results into a grouped report.

**When to use:** Validation/diagnostic tools that need to check multiple independent aspects of a system with clear pass/fail outcomes and actionable fixes.

**Source:** 04-02-PLAN.md, 04-02-SUMMARY.md

---

### P2: Handler Function Evolution with Optional Parameters
Adding new behavior to an existing function by adding optional parameters with default values rather than creating a new function or changing required parameters.

**When to use:** When extending an existing function's behavior without breaking existing callers. The default value should match the old behavior for backward compatibility.

**Source:** 04-01-PLAN.md, 04-01-SUMMARY.md

---

## Surprises

No significant surprises were encountered during Phase 04. All four sub-plans executed as written with no deviations, no blocking issues, and no unexpected findings. The work was more mechanical (updating docs, adding straightforward validation commands) than the preceding phases, contributing to the lack of surprises.

**Source:** All four SUMMARY.md files (no deviations or issues sections)
