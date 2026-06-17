---
phase: annotation-01-storage-foundation
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - paperforge/annotation/__init__.py
  - paperforge/annotation/db.py
  - paperforge/config.py
  - tests/unit/annotation/test_db.py
  - tests/test_config.py
autonomous: true
requirements:
  - DATA-01

must_haves:
  truths:
    - "annotations.db resolves through PaperForge configuration, not hardcoded vault folders"
    - "annotations.db is colocated with paperforge.db under the configured PaperForge indexes directory"
    - "annotation write connections create parent directories, set sqlite3.Row, enable WAL, and enable foreign keys"
    - "read-only annotation connections use SQLite URI mode=ro and do not create missing DB files"
    - "No Zotero probe/import/CLI/plugin overlay code is added in this plan"
  artifacts:
    - path: "paperforge/annotation/__init__.py"
      provides: "Annotation package marker and public exports"
      min_lines: 1
    - path: "paperforge/annotation/db.py"
      provides: "Annotation DB path and SQLite connection helpers"
      exports: ["get_annotations_db_path", "get_annotations_connection"]
    - path: "paperforge/config.py"
      provides: "Optional annotations_db path inventory key"
    - path: "tests/unit/annotation/test_db.py"
      provides: "Path and connection helper tests"
  key_links:
    - from: "paperforge/annotation/db.py"
      to: "paperforge/config.py"
      via: "paperforge_paths(vault)"
      pattern: "from paperforge.config import paperforge_paths"
    - from: "tests/unit/annotation/test_db.py"
      to: "paperforge/annotation/db.py"
      via: "imports helper functions"
      pattern: "from paperforge.annotation.db import"
---

<objective>
Create the annotation package and database path/connection helpers. This plan establishes where `annotations.db` lives and how code opens it, without defining the annotation schema yet.

Purpose: Make annotation storage a first-class PaperForge path while keeping it independent from rebuildable memory databases.
Output: `paperforge/annotation/__init__.py`, `paperforge/annotation/db.py`, path inventory tests.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/annotation-01-storage-foundation/annotation-01-CONTEXT.md
@.planning/phases/annotation-01-storage-foundation/annotation-01-RESEARCH.md
@.planning/phases/annotation-01-storage-foundation/annotation-01-PATTERNS.md

Current analogs:
@paperforge/memory/db.py
@paperforge/config.py
@tests/unit/memory/test_schema.py
@tests/test_config.py
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Add failing tests for annotation DB path and connection helpers</name>
  <files>
    tests/unit/annotation/test_db.py
    tests/test_config.py
  </files>
  <action>
    Create `tests/unit/annotation/test_db.py` with tests for:
    1. `get_annotations_db_path(tmp_path)` returns an absolute path named `annotations.db`.
    2. The path is under the same parent directory as `paperforge_paths(vault)["memory_db"]`.
    3. A write connection creates the parent directory and enables WAL.
    4. A read-only connection works after the DB exists and returns `sqlite3.Row` rows.
    5. A read-only connection to a missing DB raises `sqlite3.OperationalError` instead of creating the file.

    Update `tests/test_config.py` path inventory expectations only if adding `annotations_db` to `paperforge_paths`.

    Keep this task red first: run the new tests before implementing `paperforge.annotation`.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_db.py -q</automated>
  </verify>
  <done>Tests fail because `paperforge.annotation.db` does not exist yet.</done>
</task>

<task type="auto">
  <name>Task 2: Implement annotation package and DB helpers</name>
  <files>
    paperforge/annotation/__init__.py
    paperforge/annotation/db.py
    paperforge/config.py
  </files>
  <action>
    Create `paperforge/annotation/__init__.py` with a short package docstring and `__all__`.

    Create `paperforge/annotation/db.py` following `paperforge/memory/db.py`:
    - `get_annotations_db_path(vault: Path) -> Path`
    - `get_annotations_connection(db_path: Path, read_only: bool = False) -> sqlite3.Connection`

    Preferred path logic:
    - If `paperforge_paths(vault)` exposes `annotations_db`, use it.
    - Otherwise derive from `paperforge_paths(vault)["memory_db"].with_name("annotations.db")`.

    Update `paperforge/config.py` to include `"annotations_db": paperforge / "indexes" / "annotations.db"` in `paperforge_paths`, unless this creates wider compatibility problems. If added, update path inventory tests to include it.

    Do not import or depend on Zotero code here.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_db.py tests/test_config.py -q</automated>
  </verify>
  <done>Path and connection tests pass; `annotations.db` is config-resolved and colocated with `paperforge.db`.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/unit/annotation/test_db.py -q`
- `python -m pytest tests/test_config.py -q`
</verification>

<success_criteria>
- [ ] `paperforge.annotation` package exists.
- [ ] `get_annotations_db_path(vault)` resolves to configured `PaperForge/indexes/annotations.db`.
- [ ] write connections enable WAL and foreign keys.
- [ ] read-only connections do not create a missing DB.
- [ ] No import/probe/CLI/plugin overlay code is introduced.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-01-storage-foundation/annotation-01-01-SUMMARY.md`.
</output>
