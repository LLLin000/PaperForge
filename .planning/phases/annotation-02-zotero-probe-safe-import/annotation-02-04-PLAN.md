---
phase: annotation-02-zotero-probe-safe-import
plan: 04
type: execute
wave: 4
depends_on:
  - annotation-02-03
files_modified:
  - tests/unit/annotation/test_zotero_import_flow.py
  - .planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-VERIFICATION.md
autonomous: true
requirements:
  - ZOT-01
  - ZOT-02
  - ZOT-03
  - ZOT-04
  - ZOT-05
  - SAFE-01
  - SAFE-02
  - SAFE-04

must_haves:
  truths:
    - "D-01: Phase 2 verification excludes CLI, overlay, editor UI, and evidence/card integration"
    - "D-02: End-to-end coverage proves paper-scoped import first"
    - "D-03: End-to-end coverage proves unrelated paper rows survive scoped stale reconciliation"
    - "D-04: End-to-end coverage uses temp-copy mode for Zotero reads"
    - "D-08: Error-path tests prove schema probe failures are actionable"
  artifacts:
    - path: "tests/unit/annotation/test_zotero_import_flow.py"
      provides: "End-to-end probe-normalize-import regression tests"
    - path: ".planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-VERIFICATION.md"
      provides: "Phase 2 verification notes and unrelated baseline status"
  key_links:
    - from: "tests/unit/annotation/test_zotero_import_flow.py"
      to: "paperforge/annotation/zotero_probe.py"
      via: "reads copied Zotero snapshot"
      pattern: "zotero_snapshot"
    - from: "tests/unit/annotation/test_zotero_import_flow.py"
      to: "paperforge/annotation/importer.py"
      via: "imports normalized rows into annotations.db"
      pattern: "import_zotero_annotations_for_paper"
---

<objective>
Add end-to-end verification for Zotero probe, normalization, and paper-scoped import.

Purpose: Prove the pieces from plans 01-03 work together and that Phase 2 satisfies the read-only safety and scope-isolation contract.
Output: flow regression tests and Phase 2 verification notes.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-CONTEXT.md
@.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-RESEARCH.md
@.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-01-PLAN.md
@.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-02-PLAN.md
@.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-03-PLAN.md

Current annotation modules:
@paperforge/annotation/db.py
@paperforge/annotation/schema.py
@paperforge/annotation/zotero_probe.py
@paperforge/annotation/zotero_normalize.py
@paperforge/annotation/importer.py
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Add end-to-end import flow tests</name>
  <files>tests/unit/annotation/test_zotero_import_flow.py</files>
  <action>
    Create tests that build a minimal Zotero-style SQLite DB and a temporary PaperForge `annotations.db`.

    Cover:
    1. Probe finds annotation schema in copied snapshot.
    2. Raw rows normalize and import into `annotations.db`.
    3. Selected text, comment, color, page, tags, position JSON, and source modified time survive the full flow.
    4. Re-running import for one paper does not soft-delete rows belonging to another paper.
    5. Unknown Zotero schema fails before any PaperForge import mutation happens.
    6. Temporary Zotero snapshot cleanup happens after the flow.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_zotero_import_flow.py -q</automated>
  </verify>
  <done>Flow tests fail until probe/normalize/import modules are wired correctly.</done>
</task>

<task type="auto">
  <name>Task 2: Run targeted Phase 2 verification and document results</name>
  <files>
    tests/unit/annotation/test_zotero_probe.py
    tests/unit/annotation/test_zotero_normalize.py
    tests/unit/annotation/test_importer.py
    tests/unit/annotation/test_zotero_import_flow.py
    .planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-VERIFICATION.md
  </files>
  <action>
    Run targeted tests:

    ```powershell
    python -m pytest tests/unit/annotation/test_zotero_probe.py tests/unit/annotation/test_zotero_normalize.py tests/unit/annotation/test_importer.py tests/unit/annotation/test_zotero_import_flow.py -q
    python -m pytest tests/unit/annotation -q
    python -m compileall paperforge/annotation
    ```

    Create `annotation-02-VERIFICATION.md` with:
    - commands run
    - pass/fail counts
    - confirmation that no Zotero write-back path exists
    - note that CLI/overlay/editor/evidence integration is intentionally out of scope
    - any unrelated upstream baseline failures, clearly separated
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation -q</automated>
    <automated>python -m compileall paperforge/annotation</automated>
  </verify>
  <done>Phase 2 targeted tests pass or unrelated baseline failures are documented separately.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/unit/annotation/test_zotero_probe.py tests/unit/annotation/test_zotero_normalize.py tests/unit/annotation/test_importer.py tests/unit/annotation/test_zotero_import_flow.py -q`
- `python -m pytest tests/unit/annotation -q`
- `python -m compileall paperforge/annotation`
</verification>

<success_criteria>
- [ ] Full probe-normalize-import flow works against a valid minimal Zotero SQLite fixture.
- [ ] All Phase 2 requirements are covered by targeted tests.
- [ ] Paper-scoped stale handling is regression-tested end to end.
- [ ] Schema errors fail before PaperForge annotation rows are mutated.
- [ ] Verification notes distinguish Phase 2 status from unrelated baseline failures.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-04-SUMMARY.md`.
</output>
