---
phase: annotation-04-verification-gate
plan: 03
type: execute
wave: 3
depends_on:
  - annotation-04-02
files_modified:
  - .planning/phases/annotation-04-verification-gate/annotation-04-VERIFICATION.md
  - .planning/ROADMAP.md
  - .planning/STATE.md
autonomous: true
requirements:
  - TEST-01
  - TEST-02
  - TEST-03
  - TEST-04
  - TEST-05

must_haves:
  truths:
    - "D-03: Known unrelated baseline failures are documented separately rather than mixed into annotation failures"
    - "D-07: Phase 4 verification output classifies results into blocking annotation failures, known unrelated baseline failures, and advisory risks"
    - "D-09: Known unrelated baseline failures include Windows tmp_path PermissionError, ld_deep_script versus pf_deep_script mismatch, and missing filelock"
    - "D-13: Phase 4 includes an explicit safety audit showing PaperForge never writes to Zotero SQLite"
    - "D-14: Writes target annotations.db while Zotero access remains read-only/temp-copy based"
    - "D-15: Phase 4 verifies annotation backend/CLI flows do not require the Obsidian plugin runtime"
  artifacts:
    - path: ".planning/phases/annotation-04-verification-gate/annotation-04-VERIFICATION.md"
      provides: "Final annotation v0.1 release-gate evidence and failure classification"
    - path: ".planning/STATE.md"
      provides: "Phase 4 ready/complete state after execution"
    - path: ".planning/ROADMAP.md"
      provides: "Phase 4 plan progress and completion evidence"
  key_links:
    - from: ".planning/phases/annotation-04-verification-gate/annotation-04-VERIFICATION.md"
      to: "paperforge/annotation"
      via: "records tests, compile checks, and safety audit"
      pattern: "annotation"
---

<objective>
Create the final annotation v0.1 verification report and close the milestone gate.

Purpose: Make the release decision readable to a future maintainer: what passed, what failed, what is unrelated, and why annotation v0.1 is safe to build on.
Output: `annotation-04-VERIFICATION.md` plus roadmap/state updates.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/PROJECT.md
@.planning/phases/annotation-04-verification-gate/annotation-04-CONTEXT.md
@.planning/phases/annotation-04-verification-gate/annotation-04-RESEARCH.md
@.planning/phases/annotation-04-verification-gate/annotation-04-01-PLAN.md
@.planning/phases/annotation-04-verification-gate/annotation-04-02-PLAN.md
@.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-VERIFICATION.md
@.planning/phases/annotation-03-cli-json-contracts/annotation-03-VERIFICATION.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Produce final verification report</name>
  <files>
    .planning/phases/annotation-04-verification-gate/annotation-04-VERIFICATION.md
  </files>
  <action>
    Create `annotation-04-VERIFICATION.md` with:
    - commands run;
    - pass/fail counts;
    - TEST-01 through TEST-05 coverage table;
    - hard gate result;
    - failure classification table with the three buckets:
      - blocking annotation failures;
      - known unrelated baseline failures;
      - advisory risks or gaps;
    - explicit conclusion for annotation v0.1.

    If all annotation hard-gate commands passed, mark annotation v0.1 as passed even if unrelated baseline failures remain documented.
  </action>
  <verify>
    <manual>Verification report includes TEST-01 through TEST-05 and the three failure buckets.</manual>
  </verify>
  <done>`annotation-04-VERIFICATION.md` can be read independently to understand release readiness.</done>
</task>

<task type="auto">
  <name>Task 2: Run and document safety audit</name>
  <files>
    .planning/phases/annotation-04-verification-gate/annotation-04-VERIFICATION.md
    paperforge/annotation
    paperforge/commands/annotation.py
  </files>
  <action>
    Audit code paths and record the result in the verification report:
    - Zotero access uses snapshot/temp-copy helpers and read-only SQLite opening.
    - There is no Zotero `INSERT`, `UPDATE`, `DELETE`, or `commit()` write path.
    - PaperForge mutations target `annotations.db`.
    - Annotation CLI/backend tests do not require the Obsidian plugin runtime.

    Use `rg` or equivalent source searches as supporting evidence, and quote commands/results concisely in the report.
  </action>
  <verify>
    <automated>rg -n "zotero_conn\\.execute|open_zotero_readonly|zotero_snapshot|INSERT|UPDATE|DELETE|commit\\(" paperforge/annotation paperforge/commands/annotation.py</automated>
    <manual>All write paths identified in the report target PaperForge annotation storage, not Zotero SQLite.</manual>
  </verify>
  <done>SAFE-04/no-Obsidian dependency evidence is explicit in the final report.</done>
</task>

<task type="auto">
  <name>Task 3: Update planning state for Phase 4 readiness/completion</name>
  <files>
    .planning/ROADMAP.md
    .planning/STATE.md
  </files>
  <action>
    After verification passes, update roadmap/state using GSD-safe handlers where available. If handlers do not support annotation-named phases, edit only the annotation v0.1 planning entries manually and keep changes scoped:
    - mark Phase 4 plan progress as complete after execution;
    - record the final verification status;
    - keep known unrelated baseline failures in the blocker/concern section until a separate cleanup phase handles them.

    Do not rewrite old non-annotation phases.
  </action>
  <verify>
    <manual>ROADMAP and STATE reflect annotation Phase 4 status without changing old milestone history.</manual>
  </verify>
  <done>Planning state points to annotation v0.1 complete or ready for closeout, depending on execution results.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/unit/annotation -q`
- `python -m pytest tests/cli/test_annotation_command_shape.py tests/cli/test_annotation_import_json.py tests/cli/test_annotation_read_json.py tests/cli/test_annotation_json_contracts.py tests/cli/test_annotation_error_contracts.py -q`
- `python -m compileall paperforge/annotation paperforge/commands`
- source audit recorded in `.planning/phases/annotation-04-verification-gate/annotation-04-VERIFICATION.md`
</verification>

<success_criteria>
- [ ] Final verification report covers TEST-01 through TEST-05.
- [ ] Blocking annotation failures are separated from unrelated baseline failures.
- [ ] Safety audit confirms no Zotero write-back path.
- [ ] Report confirms no Obsidian runtime dependency for annotation v0.1 backend/CLI.
- [ ] ROADMAP/STATE updates are scoped to annotation Phase 4.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-04-verification-gate/annotation-04-03-SUMMARY.md`.
</output>
