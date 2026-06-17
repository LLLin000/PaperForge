---
phase: annotation-03-cli-json-contracts
plan: 03
type: execute
wave: 3
depends_on:
  - annotation-03-02
files_modified:
  - paperforge/commands/annotation.py
  - tests/cli/test_annotation_read_json.py
autonomous: true
requirements:
  - CLI-02
  - CLI-03
  - CLI-04
  - SAFE-03

must_haves:
  truths:
    - "D-20: `annotation list --json` is the lightweight ordered paper view"
    - "D-21: `list --json` includes scan fields: id, type, page, text, comment, color, source, read-only state, and provenance"
    - "D-22: `annotation export --json` is the full structured payload for plugins and downstream tools"
    - "D-23: `export --json` is paper-scoped and includes full content, source identity, timestamps, JSON position/selector fields, tags, and soft-delete state"
    - "D-24: list/export work without Obsidian plugin runtime"
    - "CLI-03: status reports schema version, DB path, total counts, source counts, and health checks"
  artifacts:
    - path: "paperforge/commands/annotation.py"
      provides: "List/status/export subcommands"
    - path: "tests/cli/test_annotation_read_json.py"
      provides: "List/status/export JSON contract tests"
  key_links:
    - from: "paperforge/commands/annotation.py"
      to: "paperforge/annotation/db.py"
      via: "opens annotations.db through configured path"
      pattern: "get_annotations_connection"
    - from: "paperforge/commands/annotation.py"
      to: "paperforge/annotation/schema.py"
      via: "reads schema version and annotation table state"
      pattern: "get_schema_version"
---

<objective>
Implement read-only annotation CLI commands: list, status, and export.

Purpose: Let users, plugins, and automation inspect `annotations.db` through stable JSON without needing Obsidian plugin runtime or internal Python imports.
Output: list/status/export behavior and JSON contract tests.
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

Annotation storage:
@paperforge/annotation/db.py
@paperforge/annotation/schema.py
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Add failing read-command JSON contract tests</name>
  <files>tests/cli/test_annotation_read_json.py</files>
  <action>
    Create tests for:
    1. `paperforge annotation status --json` on an empty vault returns schema/db health, db path, total counts, source counts, read-only counts, and deleted count.
    2. `paperforge annotation list --paper KEY --json` returns ordered lightweight annotation rows.
    3. `list --json` requires `--paper` and returns valid PFResult error JSON if missing or invalid.
    4. `paperforge annotation export --paper KEY --json` returns full paper-scoped annotations, including source identity and JSON position/selector/tags fields.
    5. list/export ignore or clearly mark soft-deleted rows according to the chosen command behavior; export may include deleted rows if documented in `data`.
    6. These commands work without loading Obsidian plugin code.
  </action>
  <verify>
    <automated>python -m pytest tests/cli/test_annotation_read_json.py -q</automated>
  </verify>
  <done>Tests fail until list/status/export behavior is implemented.</done>
</task>

<task type="auto">
  <name>Task 2: Implement list/status/export subcommands</name>
  <files>paperforge/commands/annotation.py</files>
  <action>
    Implement read-only subcommands:

    `status --json`:
    - Ensure/open `annotations.db` as appropriate.
    - Return schema version, DB path, health flags, total annotations, source counts, read-only counts, and deleted count.
    - If DB is absent, return a healthy empty-state or an actionable error according to existing annotation DB helper behavior; keep output stable.

    `list --paper KEY --json`:
    - Query non-deleted rows for the paper by default.
    - Order by `page_index`, `sort_index`, then `id`.
    - Return lightweight scan fields.

    `export --paper KEY --json`:
    - Query paper-scoped rows.
    - Return complete payload for downstream tools.
    - Include `format_version`.

    All `--json` failures must return PFResult JSON. Text mode can be minimal but must not traceback.
  </action>
  <verify>
    <automated>python -m pytest tests/cli/test_annotation_read_json.py tests/cli/test_annotation_import_json.py tests/cli/test_annotation_command_shape.py -q</automated>
  </verify>
  <done>Read-command tests pass and import/shape tests remain green.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/cli/test_annotation_read_json.py tests/cli/test_annotation_import_json.py tests/cli/test_annotation_command_shape.py -q`
- `python -m compileall paperforge/commands paperforge/annotation`
</verification>

<success_criteria>
- [ ] `annotation list --json` returns ordered paper-scoped lightweight rows.
- [ ] `annotation status --json` reports DB/schema/count health.
- [ ] `annotation export --json` returns full paper-scoped payload.
- [ ] All read commands work without Obsidian plugin runtime.
- [ ] JSON failures are stable and actionable.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-03-cli-json-contracts/annotation-03-03-SUMMARY.md`.
</output>
