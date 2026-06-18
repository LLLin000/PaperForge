---
phase: annotation-04-verification-gate
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/unit/annotation/conftest.py
  - tests/unit/annotation/test_zotero_import_flow.py
  - tests/unit/annotation/test_importer.py
  - tests/unit/annotation/test_service_contracts.py
autonomous: true
requirements:
  - TEST-01
  - TEST-02
  - TEST-04

must_haves:
  truths:
    - "D-04: Tests generate minimal Zotero SQLite fixtures at runtime instead of committing binary SQLite fixtures"
    - "D-05: Generated fixture includes at least one parent paper, one PDF attachment, and multiple annotation rows"
    - "D-06: Fixture helpers stay readable enough to show simulated Zotero tables and columns"
    - "D-08: Blocking annotation failures include storage, probe/import, service behavior, and CLI JSON contracts"
    - "D-14: Writes target annotations.db while Zotero access stays read-only/temp-copy based"
  artifacts:
    - path: "tests/unit/annotation/conftest.py"
      provides: "Reusable generated Zotero SQLite fixture helpers for annotation verification"
    - path: "tests/unit/annotation/test_service_contracts.py"
      provides: "Service-level list/export/status coverage independent of CLI"
  key_links:
    - from: "tests/unit/annotation/conftest.py"
      to: "tests/unit/annotation/test_zotero_import_flow.py"
      via: "shared generated two-paper Zotero fixture"
      pattern: "zotero"
    - from: "tests/unit/annotation/test_service_contracts.py"
      to: "paperforge/commands/annotation.py"
      via: "validates read-only query behavior used by list/status/export"
      pattern: "annotation"
---

<objective>
Build the generated fixture and service-test foundation for the Phase 4 release gate.

Purpose: Make TEST-01 and the non-CLI portions of TEST-02/TEST-04 explicit and reusable.
Output: shared generated Zotero SQLite fixture helpers plus focused service-level regression tests.
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
@.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-VERIFICATION.md
@.planning/phases/annotation-03-cli-json-contracts/annotation-03-VERIFICATION.md

Existing tests:
@tests/unit/annotation/test_zotero_import_flow.py
@tests/unit/annotation/test_importer.py
@tests/unit/annotation/test_zotero_probe.py
@tests/cli/test_annotation_read_json.py
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Consolidate generated Zotero fixture helpers</name>
  <files>
    tests/unit/annotation/conftest.py
    tests/unit/annotation/test_zotero_import_flow.py
    tests/unit/annotation/test_importer.py
  </files>
  <action>
    Create or extend `tests/unit/annotation/conftest.py` with a generated Zotero SQLite fixture helper that includes:
    - parent paper A;
    - parent paper B;
    - one PDF attachment for each paper;
    - multiple annotations for paper A;
    - at least one annotation for paper B;
    - tags and position JSON;
    - a reduced variant that omits one paper A annotation for stale-row testing.

    Refactor duplicated fixture builders in `test_zotero_import_flow.py` and `test_importer.py` only where it clearly reduces duplication without changing test meaning. Keep the SQL readable; the fixture itself is part of the verification evidence.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_zotero_import_flow.py tests/unit/annotation/test_importer.py -q</automated>
  </verify>
  <done>The shared fixture satisfies TEST-01 and existing import-flow/importer tests still pass.</done>
</task>

<task type="tdd">
  <name>Task 2: Add service-level read/export/status contract tests</name>
  <files>
    tests/unit/annotation/test_service_contracts.py
    paperforge/commands/annotation.py
  </files>
  <action>
    Add unit tests for the lower-level read behavior behind `annotation list/status/export`:
    - list/export reads only from `annotations.db`;
    - paper filtering returns only the selected paper;
    - ordering remains stable by page/sort/id;
    - deleted rows are excluded from list by default but represented correctly where export/status expects them;
    - provenance fields remain present for Zotero-sourced rows.

    If the current logic is command-local rather than service-module based, test the smallest callable helpers already present. Do not introduce a new service abstraction unless it removes meaningful duplication.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_service_contracts.py -q</automated>
  </verify>
  <done>TEST-02 read/list/export behavior is covered without requiring the CLI harness.</done>
</task>

<task type="auto">
  <name>Task 3: Confirm paper-scoped stale deletion regression remains explicit</name>
  <files>
    tests/unit/annotation/test_zotero_import_flow.py
    tests/unit/annotation/test_importer.py
  </files>
  <action>
    Ensure the tests explicitly prove that importing one paper does not soft-delete annotations for another paper. Keep or strengthen the existing regression:
    - import paper A and paper B;
    - re-import paper A from the same or reduced fixture;
    - assert paper B rows still exist and `deleted_at IS NULL`.

    This is the highest-risk historical bug from the old annotation branch, so the test name and assertion message should make the scope-isolation intent obvious.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_zotero_import_flow.py tests/unit/annotation/test_importer.py -q</automated>
  </verify>
  <done>TEST-04 is covered by a named regression test with clear failure output.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/unit/annotation/test_zotero_import_flow.py tests/unit/annotation/test_importer.py tests/unit/annotation/test_service_contracts.py -q`
</verification>

<success_criteria>
- [ ] Generated SQLite fixtures satisfy parent paper, PDF attachment, and multiple annotation row coverage.
- [ ] Fixture helpers are shared enough to avoid obvious drift.
- [ ] Service/list/export/status behavior is covered below the CLI layer.
- [ ] Paper-scoped stale deletion regression is explicit and passing.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-04-verification-gate/annotation-04-01-SUMMARY.md`.
</output>
