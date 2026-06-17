---
phase: annotation-03-cli-json-contracts
plan: 04
type: execute
wave: 4
depends_on:
  - annotation-03-03
files_modified:
  - tests/cli/test_annotation_json_contracts.py
  - tests/cli/test_annotation_error_contracts.py
  - .planning/phases/annotation-03-cli-json-contracts/annotation-03-VERIFICATION.md
autonomous: true
requirements:
  - CLI-01
  - CLI-02
  - CLI-03
  - CLI-04
  - CLI-05
  - SAFE-03

must_haves:
  truths:
    - "D-12: All annotation JSON commands use PFResult envelope"
    - "D-13: Command-specific payload lives under data"
    - "D-14: command values are stable: annotation.import/list/status/export"
    - "D-15: JSON keys are stable English identifiers; user-facing messages may be Chinese-friendly"
    - "D-17: JSON failures include stable error code, message, details, and optional suggestions"
    - "D-18: Error messages are actionable in plain language and may use Chinese-friendly user-facing text"
    - "D-19: Representative missing DB, unreadable DB, schema, invalid payload/filter, and missing annotation DB errors are covered"
  artifacts:
    - path: "tests/cli/test_annotation_json_contracts.py"
      provides: "End-to-end success contract coverage for annotation JSON commands"
    - path: "tests/cli/test_annotation_error_contracts.py"
      provides: "Representative annotation JSON error contract coverage"
    - path: ".planning/phases/annotation-03-cli-json-contracts/annotation-03-VERIFICATION.md"
      provides: "Phase 3 verification report"
  key_links:
    - from: "tests/cli/test_annotation_json_contracts.py"
      to: "paperforge/commands/annotation.py"
      via: "exercises all success JSON commands"
      pattern: "annotation"
    - from: "tests/cli/test_annotation_error_contracts.py"
      to: "paperforge/commands/annotation.py"
      via: "exercises stable error JSON mapping"
      pattern: "annotation"
---

<objective>
Add final annotation CLI contract verification and document Phase 3 results.

Purpose: Prove all annotation CLI JSON success/error contracts work together and distinguish Phase 3 status from unrelated baseline failures.
Output: consolidated contract tests and verification notes.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/annotation-03-cli-json-contracts/annotation-03-CONTEXT.md
@.planning/phases/annotation-03-cli-json-contracts/annotation-03-RESEARCH.md
@.planning/phases/annotation-03-cli-json-contracts/annotation-03-01-PLAN.md
@.planning/phases/annotation-03-cli-json-contracts/annotation-03-02-PLAN.md
@.planning/phases/annotation-03-cli-json-contracts/annotation-03-03-PLAN.md

Existing CLI tests:
@tests/cli/test_json_contracts.py
@tests/cli/test_error_codes.py
@tests/cli/test_contract_helpers.py
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Add consolidated success/error contract tests</name>
  <files>
    tests/cli/test_annotation_json_contracts.py
    tests/cli/test_annotation_error_contracts.py
  </files>
  <action>
    Add consolidated tests that exercise the full CLI surface:
    - `annotation import --json`
    - `annotation import --apply --json`
    - `annotation list --json`
    - `annotation status --json`
    - `annotation export --json`

    Add error tests for:
    - missing Zotero DB
    - unreadable/invalid Zotero DB
    - unknown Zotero annotation schema
    - missing/invalid `--paper`
    - missing or mismatched `annotations.db` schema
    - invalid annotation payload, if this is reachable through CLI fixtures

    These tests may overlap with plan 01-03 tests but should read as the final contract matrix for Phase 3.
  </action>
  <verify>
    <automated>python -m pytest tests/cli/test_annotation_json_contracts.py tests/cli/test_annotation_error_contracts.py -q</automated>
  </verify>
  <done>Contract tests fail until any remaining JSON output gaps are closed.</done>
</task>

<task type="auto">
  <name>Task 2: Close remaining contract gaps and run targeted verification</name>
  <files>
    paperforge/commands/annotation.py
    paperforge/cli.py
    tests/cli/test_annotation_command_shape.py
    tests/cli/test_annotation_import_json.py
    tests/cli/test_annotation_read_json.py
    tests/cli/test_annotation_json_contracts.py
    tests/cli/test_annotation_error_contracts.py
    .planning/phases/annotation-03-cli-json-contracts/annotation-03-VERIFICATION.md
  </files>
  <action>
    Fix any remaining gaps found by the final contract tests.

    Run:

    ```powershell
    python -m pytest tests/cli/test_annotation_command_shape.py tests/cli/test_annotation_import_json.py tests/cli/test_annotation_read_json.py tests/cli/test_annotation_json_contracts.py tests/cli/test_annotation_error_contracts.py -q
    python -m pytest tests/unit/annotation -q
    python -m compileall paperforge/commands paperforge/annotation
    ```

    Create `annotation-03-VERIFICATION.md` with:
    - commands run
    - pass/fail counts
    - confirmation that annotation commands use PFResult under `--json`
    - confirmation that no Zotero write-back path was added
    - confirmation that Obsidian overlay/editor/evidence integration remain out of scope
    - unrelated baseline failures, if any, separated from Phase 3 status
  </action>
  <verify>
    <automated>python -m pytest tests/cli/test_annotation_command_shape.py tests/cli/test_annotation_import_json.py tests/cli/test_annotation_read_json.py tests/cli/test_annotation_json_contracts.py tests/cli/test_annotation_error_contracts.py -q</automated>
    <automated>python -m pytest tests/unit/annotation -q</automated>
    <automated>python -m compileall paperforge/commands paperforge/annotation</automated>
  </verify>
  <done>All targeted annotation CLI contract tests pass and verification notes are written.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/cli/test_annotation_command_shape.py tests/cli/test_annotation_import_json.py tests/cli/test_annotation_read_json.py tests/cli/test_annotation_json_contracts.py tests/cli/test_annotation_error_contracts.py -q`
- `python -m pytest tests/unit/annotation -q`
- `python -m compileall paperforge/commands paperforge/annotation`
</verification>

<success_criteria>
- [ ] All four annotation subcommands have passing JSON success tests.
- [ ] Representative error cases return stable PFResult JSON.
- [ ] Phase 2 unit annotation tests still pass.
- [ ] No Zotero write-back path is introduced.
- [ ] Phase 3 verification notes clearly record status and residual risks.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-03-cli-json-contracts/annotation-03-04-SUMMARY.md`.
</output>
