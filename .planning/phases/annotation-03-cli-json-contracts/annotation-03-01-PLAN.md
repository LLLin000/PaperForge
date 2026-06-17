---
phase: annotation-03-cli-json-contracts
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - paperforge/cli.py
  - paperforge/commands/annotation.py
  - tests/cli/test_annotation_command_shape.py
autonomous: true
requirements:
  - CLI-01
  - CLI-02
  - CLI-03
  - CLI-04
  - SAFE-03

must_haves:
  truths:
    - "D-01: Annotation commands live under the single `paperforge annotation ...` namespace"
    - "D-02: The namespace exposes import, list, status, and export subcommands"
    - "D-03: Do not scatter annotation behavior into sync, status, doctor, or memory commands"
    - "D-12: Annotation JSON commands use the PFResult-style envelope"
    - "D-16: Annotation `--json` failures return valid JSON instead of traceback text"
  artifacts:
    - path: "paperforge/commands/annotation.py"
      provides: "Annotation CLI command module and shared PFResult/error helpers"
      exports: ["run"]
    - path: "paperforge/cli.py"
      provides: "Annotation parser namespace and dispatch"
    - path: "tests/cli/test_annotation_command_shape.py"
      provides: "Parser/namespace and base JSON shape contract tests"
  key_links:
    - from: "paperforge/cli.py"
      to: "paperforge/commands/annotation.py"
      via: "dispatches annotation command"
      pattern: "from paperforge.commands import annotation"
    - from: "tests/cli/test_annotation_command_shape.py"
      to: "paperforge/cli.py"
      via: "invokes `paperforge annotation ...` through CLI fixture"
      pattern: "annotation"
---

<objective>
Create the `paperforge annotation` CLI namespace and command module scaffold.

Purpose: Establish the user-facing command shape and shared JSON/error output helpers before wiring individual subcommand behavior.
Output: parser registration, annotation command dispatch, and command-shape tests.
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

Existing CLI patterns:
@paperforge/cli.py
@paperforge/core/result.py
@paperforge/core/errors.py
@paperforge/commands/sync.py
@paperforge/commands/status.py
@tests/cli/conftest.py
@tests/cli/test_json_contracts.py
@tests/cli/test_error_codes.py
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Add failing command-shape and base JSON tests</name>
  <files>tests/cli/test_annotation_command_shape.py</files>
  <action>
    Create tests that use the existing `cli_invoker` fixture.

    Cover:
    1. `paperforge annotation --help` exits 0 and lists `import`, `list`, `status`, and `export`.
    2. `paperforge annotation status --json` returns valid JSON with PFResult keys: `ok`, `command`, `version`, `data`, `error`.
    3. `command` values use the `annotation.*` namespace.
    4. Unknown annotation subcommands fail without Python traceback.
    5. JSON failure paths still produce valid JSON when `--json` is provided.

    Keep tests red before adding parser/command code.
  </action>
  <verify>
    <automated>python -m pytest tests/cli/test_annotation_command_shape.py -q</automated>
  </verify>
  <done>Tests fail because the `annotation` command is not registered yet.</done>
</task>

<task type="auto">
  <name>Task 2: Add annotation parser namespace and command module scaffold</name>
  <files>
    paperforge/cli.py
    paperforge/commands/annotation.py
  </files>
  <action>
    Update `paperforge/cli.py`:
    - Add top-level `annotation` subparser.
    - Add nested subcommands: `import`, `list`, `status`, `export`.
    - Add shared `--json` flags for all subcommands.
    - Add basic flags required by later plans:
      - `import`: `--paper`, `--zotero-db`, `--attachment-key`, `--apply`, `--json`
      - `list`: `--paper`, `--json`
      - `status`: `--json`
      - `export`: `--paper`, `--json`
    - Dispatch `args.command == "annotation"` to `paperforge.commands.annotation.run(args)`.

    Create `paperforge/commands/annotation.py`:
    - `run(args) -> int`
    - subcommand dispatch based on `args.annotation_command` or equivalent parser dest.
    - PFResult helper functions for success and error output.
    - Structured exception mapping for annotation-domain errors from Phase 2.

    If extending `paperforge.core.errors.ErrorCode` is low-risk, add annotation-specific values there. If not, preserve stable annotation codes in `error.details["annotation_error_code"]` while using the nearest existing enum value.
  </action>
  <verify>
    <automated>python -m pytest tests/cli/test_annotation_command_shape.py -q</automated>
    <automated>python -m compileall paperforge/commands paperforge/annotation</automated>
  </verify>
  <done>Annotation namespace exists and base PFResult JSON/error shape tests pass.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/cli/test_annotation_command_shape.py -q`
- `python -m compileall paperforge/commands paperforge/annotation`
</verification>

<success_criteria>
- [ ] `paperforge annotation --help` exposes import/list/status/export.
- [ ] `paperforge annotation status --json` emits PFResult JSON.
- [ ] Unknown/invalid annotation commands do not show traceback.
- [ ] Parser work does not alter existing `sync`, `status`, `doctor`, or `memory` behavior.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-03-cli-json-contracts/annotation-03-01-SUMMARY.md`.
</output>
