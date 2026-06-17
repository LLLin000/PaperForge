---
phase: annotation-02-zotero-probe-safe-import
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - paperforge/annotation/errors.py
  - paperforge/annotation/zotero_probe.py
  - tests/unit/annotation/test_zotero_probe.py
autonomous: true
requirements:
  - ZOT-01
  - ZOT-04
  - SAFE-01
  - SAFE-02
  - SAFE-04

must_haves:
  truths:
    - "D-01: Phase 2 only implements backend Zotero probe/import support; no CLI, Obsidian overlay, editor UI, or evidence/card integration"
    - "D-04: Zotero access defaults to temp-copy mode and opens the copied snapshot read-only"
    - "D-05: Zotero database path comes from an explicit input/config path and never from a hardcoded OS-specific folder"
    - "D-08: Probe failures use structured domain errors that later CLI code can convert to stable JSON and Chinese messages"
    - "SAFE-04: No function in this plan writes to Zotero SQLite"
  artifacts:
    - path: "paperforge/annotation/errors.py"
      provides: "Structured annotation import/probe exception types"
      exports: ["AnnotationImportError", "ZoteroDatabaseError", "ZoteroSchemaError"]
    - path: "paperforge/annotation/zotero_probe.py"
      provides: "Zotero SQLite snapshot, read-only open, schema probe, and raw row fetch helpers"
    - path: "tests/unit/annotation/test_zotero_probe.py"
      provides: "Fixture-backed probe and safety tests"
  key_links:
    - from: "paperforge/annotation/zotero_probe.py"
      to: "paperforge/annotation/errors.py"
      via: "raises structured domain errors"
      pattern: "from paperforge.annotation.errors import"
    - from: "tests/unit/annotation/test_zotero_probe.py"
      to: "paperforge/annotation/zotero_probe.py"
      via: "imports probe helpers"
      pattern: "from paperforge.annotation.zotero_probe import"
---

<objective>
Create the Zotero SQLite snapshot/probe foundation.

Purpose: Let PaperForge safely inspect and read Zotero PDF annotation rows from a copied, read-only database snapshot before any import logic writes to `annotations.db`.
Output: structured errors, Zotero snapshot/probe helpers, and minimal valid SQLite fixture tests.
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

Phase 1 dependencies:
@paperforge/annotation/db.py
@paperforge/annotation/schema.py

Related config/path code:
@paperforge/config.py
@paperforge/adapters/zotero_paths.py
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Add failing Zotero probe tests with a valid SQLite fixture</name>
  <files>tests/unit/annotation/test_zotero_probe.py</files>
  <action>
    Create `tests/unit/annotation/test_zotero_probe.py`.

    Build a minimal valid Zotero-style SQLite fixture inside each test using sqlite3, not the existing invalid `tests/sandbox/TestZoteroData/zotero.sqlite`.

    Tests should cover:
    1. A helper copies `zotero.sqlite` to a temp snapshot and opens the copy in read-only mode.
    2. The live Zotero DB file remains unchanged after probe/read.
    3. Temporary snapshot files are cleaned up after the context exits.
    4. Missing DB path raises `ZoteroDatabaseError`.
    5. Unknown/missing annotation table or required column raises `ZoteroSchemaError` with table/column detail.
    6. Probe discovers expected annotation tables/columns for the fixture.

    Keep tests red first by importing the not-yet-existing module.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_zotero_probe.py -q</automated>
  </verify>
  <done>Tests fail because `paperforge.annotation.zotero_probe` and structured errors do not exist.</done>
</task>

<task type="auto">
  <name>Task 2: Implement structured errors and read-only snapshot/probe helpers</name>
  <files>
    paperforge/annotation/errors.py
    paperforge/annotation/zotero_probe.py
  </files>
  <action>
    Create `paperforge/annotation/errors.py` with a small exception hierarchy:
    - `AnnotationImportError`
    - `ZoteroDatabaseError`
    - `ZoteroSchemaError`

    Create `paperforge/annotation/zotero_probe.py` with:
    - A context manager such as `zotero_snapshot(db_path: Path)` that copies the source DB to a temporary file and removes the copy afterward.
    - `open_zotero_readonly(snapshot_path: Path) -> sqlite3.Connection` using SQLite URI `mode=ro` and `sqlite3.Row`.
    - `probe_zotero_annotation_schema(conn)` that validates required tables/columns and returns a compact probe result.
    - A narrow raw fetch helper for annotation rows by library/parent/attachment scope if that can be done without importing into PaperForge yet.

    Keep path handling explicit: accept `Path` arguments; do not auto-discover Zotero folders in this plan.

    Do not add any INSERT/UPDATE/DELETE statement against Zotero SQLite.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_zotero_probe.py -q</automated>
  </verify>
  <done>Zotero probe tests pass and no code path writes to Zotero SQLite.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/unit/annotation/test_zotero_probe.py -q`
- `python -m compileall paperforge/annotation`
</verification>

<success_criteria>
- [ ] Missing/unreadable Zotero DB paths produce structured errors.
- [ ] Unknown/missing annotation schema produces structured errors.
- [ ] Zotero DB access copies to a temporary snapshot by default.
- [ ] Snapshot is opened read-only and cleaned up.
- [ ] No Zotero write-back or live SQLite mutation path is introduced.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-01-SUMMARY.md`.
</output>
