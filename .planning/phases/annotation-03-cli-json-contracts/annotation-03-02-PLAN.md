---
phase: annotation-03-cli-json-contracts
plan: 02
type: execute
wave: 2
depends_on:
  - annotation-03-01
files_modified:
  - paperforge/commands/annotation.py
  - tests/cli/test_annotation_import_json.py
autonomous: true
requirements:
  - CLI-01
  - CLI-05
  - SAFE-03

must_haves:
  truths:
    - "D-04: `paperforge annotation import` defaults to preview mode"
    - "D-05: Real import writes require explicit `--apply`"
    - "D-06: JSON output clearly distinguishes preview from applied import"
    - "D-07: Import JSON includes inserted, updated, unchanged, stale, skipped, invalid/total counts when available"
    - "D-08: The main paper selector is `--paper KEY`"
    - "D-09: `--paper KEY` should resolve through PaperForge paper identity where possible rather than forcing internal IDs"
    - "D-10: `--attachment-key` is optional disambiguation for multi-PDF papers"
    - "D-11: Do not make `--zotero-key` the only public entry point because annotations.db is source-agnostic"
  artifacts:
    - path: "paperforge/commands/annotation.py"
      provides: "Import subcommand preview/apply behavior"
    - path: "tests/cli/test_annotation_import_json.py"
      provides: "Import JSON success/error contract tests"
  key_links:
    - from: "paperforge/commands/annotation.py"
      to: "paperforge/annotation/importer.py"
      via: "calls Phase 2 importer on --apply"
      pattern: "import_zotero_annotations_for_paper"
    - from: "paperforge/commands/annotation.py"
      to: "paperforge/annotation/zotero_probe.py"
      via: "uses Zotero snapshot/probe helpers"
      pattern: "zotero_snapshot"
---

<objective>
Implement `paperforge annotation import --json` with safe preview/apply behavior.

Purpose: Give users and automation a stable import command that previews by default and only mutates `annotations.db` when `--apply` is explicit.
Output: import command behavior and JSON contract tests.
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

Phase 2 backend:
@paperforge/annotation/importer.py
@paperforge/annotation/zotero_probe.py
@paperforge/annotation/zotero_normalize.py
@paperforge/annotation/errors.py
@.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-VERIFICATION.md
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Add failing import JSON contract tests</name>
  <files>tests/cli/test_annotation_import_json.py</files>
  <action>
    Create CLI tests for `paperforge annotation import --json`.

    Cover:
    1. Import without `--apply` returns `ok=true`, `command="annotation.import"`, `data.dry_run=true`, `data.applied=false`.
    2. Preview mode does not mutate `annotations.db`.
    3. Import with `--apply` calls the backend and returns `data.applied=true` plus counts.
    4. Missing `--paper` produces valid PFResult error JSON.
    5. Missing or unreadable `--zotero-db` produces valid PFResult error JSON with stable annotation error code/details.
    6. Invalid Zotero schema maps to stable JSON error output.

    Prefer minimal fixture setup using Phase 2 test helper patterns. Do not rely on the invalid old sandbox `zotero.sqlite`.
  </action>
  <verify>
    <automated>python -m pytest tests/cli/test_annotation_import_json.py -q</automated>
  </verify>
  <done>Tests fail until import behavior is implemented.</done>
</task>

<task type="auto">
  <name>Task 2: Wire import preview/apply to Phase 2 backend</name>
  <files>paperforge/commands/annotation.py</files>
  <action>
    Implement import subcommand behavior:
    - Resolve `annotations_db` through `args.paths["annotations_db"]`.
    - Resolve Zotero DB from `--zotero-db` or a config/env path if already supported; do not hardcode OS folders.
    - Run Phase 2 probe and normalization/import flow.
    - In preview mode, report projected information without writing to `annotations.db`. If the backend has no dry-run path yet, implement preview by reading/probing/normalizing and returning counts without calling the writer.
    - In apply mode, call `import_zotero_annotations_for_paper`.
    - Include `paper`, `attachment_key`, `dry_run`, `applied`, `source`, and `counts` under `data`.

    Keep CLI code thin: use Phase 2 helpers rather than duplicating SQL import logic.
  </action>
  <verify>
    <automated>python -m pytest tests/cli/test_annotation_import_json.py tests/cli/test_annotation_command_shape.py -q</automated>
  </verify>
  <done>Import JSON contract tests pass and command-shape tests remain green.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/cli/test_annotation_import_json.py tests/cli/test_annotation_command_shape.py -q`
- `python -m compileall paperforge/commands paperforge/annotation`
</verification>

<success_criteria>
- [ ] Import defaults to preview mode.
- [ ] `--apply` is required for writes.
- [ ] Preview/apply state is explicit in JSON.
- [ ] Counts are stable and machine-readable.
- [ ] Import failures return PFResult JSON under `--json`.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-03-cli-json-contracts/annotation-03-02-SUMMARY.md`.
</output>
