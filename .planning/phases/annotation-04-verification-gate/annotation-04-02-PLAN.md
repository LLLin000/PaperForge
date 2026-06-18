---
phase: annotation-04-verification-gate
plan: 02
type: execute
wave: 2
depends_on:
  - annotation-04-01
files_modified:
  - tests/cli/test_annotation_json_contracts.py
  - tests/cli/test_annotation_error_contracts.py
  - tests/cli/test_annotation_import_json.py
  - tests/cli/test_annotation_read_json.py
autonomous: true
requirements:
  - TEST-02
  - TEST-03
  - TEST-04

must_haves:
  truths:
    - "D-01: Targeted annotation tests, affected CLI JSON tests, and compile checks are the hard release gate"
    - "D-02: Full repository tests may be advisory but do not block annotation v0.1 for known unrelated baseline failures"
    - "D-07: Verification results classify blocking annotation failures, known unrelated baseline failures, and advisory risks"
    - "D-10: Required command set covers annotation unit tests, annotation CLI JSON tests, and compile checks"
    - "D-11: Planner may include selected CLI smoke tests if they prove commands work together"
    - "D-12: Entire repository green status is not a formal requirement for this phase"
  artifacts:
    - path: "tests/cli/test_annotation_json_contracts.py"
      provides: "Final success JSON matrix for annotation import/list/status/export"
    - path: "tests/cli/test_annotation_error_contracts.py"
      provides: "Final failure JSON matrix for representative annotation errors"
  key_links:
    - from: "tests/cli/test_annotation_json_contracts.py"
      to: "paperforge/commands/annotation.py"
      via: "exercises all annotation CLI success contracts"
      pattern: "annotation"
    - from: "tests/cli/test_annotation_error_contracts.py"
      to: "paperforge/commands/annotation.py"
      via: "exercises JSON error mapping without tracebacks"
      pattern: "annotation"
---

<objective>
Lock the final CLI JSON and regression test matrix for annotation v0.1.

Purpose: Make Phase 4's hard gate executable from tests rather than relying on the Phase 3 verification report alone.
Output: passing annotation CLI success/error tests covering import, list, status, export, and representative failure cases.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/annotation-04-verification-gate/annotation-04-CONTEXT.md
@.planning/phases/annotation-04-verification-gate/annotation-04-RESEARCH.md
@.planning/phases/annotation-04-verification-gate/annotation-04-01-PLAN.md
@.planning/phases/annotation-03-cli-json-contracts/annotation-03-VERIFICATION.md

Existing CLI tests:
@tests/cli/test_annotation_command_shape.py
@tests/cli/test_annotation_import_json.py
@tests/cli/test_annotation_read_json.py
@tests/cli/test_annotation_json_contracts.py
@tests/cli/test_annotation_error_contracts.py
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Verify CLI success matrix remains complete</name>
  <files>
    tests/cli/test_annotation_json_contracts.py
    tests/cli/test_annotation_import_json.py
    tests/cli/test_annotation_read_json.py
  </files>
  <action>
    Review and strengthen the success tests so they cover:
    - `annotation import --json` preview mode;
    - `annotation import --apply --json` write mode;
    - `annotation list --paper KEY --json`;
    - `annotation status --json`;
    - `annotation export --paper KEY --json`;
    - stable PFResult keys: `ok`, `command`, `version`, `data`, `error`;
    - stable command values: `annotation.import`, `annotation.list`, `annotation.status`, `annotation.export`;
    - source provenance and read-only state for Zotero rows.
  </action>
  <verify>
    <automated>python -m pytest tests/cli/test_annotation_json_contracts.py tests/cli/test_annotation_import_json.py tests/cli/test_annotation_read_json.py -q</automated>
  </verify>
  <done>TEST-03 success JSON coverage is complete and passes.</done>
</task>

<task type="tdd">
  <name>Task 2: Verify CLI error matrix remains stable and actionable</name>
  <files>
    tests/cli/test_annotation_error_contracts.py
    tests/cli/test_annotation_command_shape.py
    paperforge/commands/annotation.py
  </files>
  <action>
    Review and strengthen representative failure tests:
    - missing `--paper` where required;
    - missing Zotero DB;
    - invalid or unknown Zotero annotation schema;
    - absent `annotations.db`;
    - corrupt or unreadable `annotations.db`;
    - unknown annotation subcommand with no Python traceback.

    For `--json`, failures must return parseable JSON with a stable error object. User-facing messages may be Chinese-friendly, but JSON keys remain English identifiers.
  </action>
  <verify>
    <automated>python -m pytest tests/cli/test_annotation_error_contracts.py tests/cli/test_annotation_command_shape.py -q</automated>
  </verify>
  <done>TEST-03 failure JSON coverage is complete and passes without tracebacks.</done>
</task>

<task type="auto">
  <name>Task 3: Run the annotation hard-gate command set</name>
  <files>
    tests/cli/test_annotation_command_shape.py
    tests/cli/test_annotation_import_json.py
    tests/cli/test_annotation_read_json.py
    tests/cli/test_annotation_json_contracts.py
    tests/cli/test_annotation_error_contracts.py
    tests/unit/annotation
  </files>
  <action>
    Run the full Phase 4 hard gate command set:

    ```powershell
    python -m pytest tests/unit/annotation -q
    python -m pytest tests/cli/test_annotation_command_shape.py tests/cli/test_annotation_import_json.py tests/cli/test_annotation_read_json.py tests/cli/test_annotation_json_contracts.py tests/cli/test_annotation_error_contracts.py -q
    python -m compileall paperforge/annotation paperforge/commands
    ```

    Fix annotation-specific failures only. If a failure is a known unrelated baseline problem, do not alter unrelated code in this plan; record it for plan 03's verification report.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation -q</automated>
    <automated>python -m pytest tests/cli/test_annotation_command_shape.py tests/cli/test_annotation_import_json.py tests/cli/test_annotation_read_json.py tests/cli/test_annotation_json_contracts.py tests/cli/test_annotation_error_contracts.py -q</automated>
    <automated>python -m compileall paperforge/annotation paperforge/commands</automated>
  </verify>
  <done>The hard gate command set passes or any remaining failure is clearly outside annotation scope.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/unit/annotation -q`
- `python -m pytest tests/cli/test_annotation_command_shape.py tests/cli/test_annotation_import_json.py tests/cli/test_annotation_read_json.py tests/cli/test_annotation_json_contracts.py tests/cli/test_annotation_error_contracts.py -q`
- `python -m compileall paperforge/annotation paperforge/commands`
</verification>

<success_criteria>
- [ ] All annotation unit tests pass.
- [ ] All annotation CLI JSON success/error tests pass.
- [ ] Compile checks for annotation-related modules are clean.
- [ ] Any non-annotation failure is classified for the verification report rather than silently mixed into the gate.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-04-verification-gate/annotation-04-02-SUMMARY.md`.
</output>
