---
phase: annotation-01-storage-foundation
plan: 03
type: execute
wave: 3
depends_on:
  - annotation-01-02
files_modified:
  - tests/unit/annotation/test_rebuild_isolation.py
  - tests/unit/annotation/test_schema.py
  - tests/unit/annotation/test_db.py
autonomous: true
requirements:
  - DATA-04

must_haves:
  truths:
    - "Memory rebuild operates only on paperforge.db and does not remove annotations.db"
    - "Annotation tables are never added to paperforge.memory.schema.ALL_TABLES"
    - "Regression test creates annotations.db with sentinel data, runs memory rebuild/drop path, and verifies sentinel remains"
    - "Verification documents unrelated upstream baseline failures separately"
  artifacts:
    - path: "tests/unit/annotation/test_rebuild_isolation.py"
      provides: "Regression test proving memory rebuild isolation"
    - path: ".planning/phases/annotation-01-storage-foundation/annotation-01-VERIFICATION.md"
      provides: "Planning/execution verification note once Annotation Phase 1 executes"
  key_links:
    - from: "tests/unit/annotation/test_rebuild_isolation.py"
      to: "paperforge/memory/schema.py"
      via: "assert annotation tables absent from ALL_TABLES"
      pattern: "from paperforge.memory.schema import ALL_TABLES"
    - from: "tests/unit/annotation/test_rebuild_isolation.py"
      to: "paperforge/annotation/schema.py"
      via: "creates annotation sentinel schema"
      pattern: "from paperforge.annotation.schema import ensure_schema"
---

<objective>
Add regression coverage that proves `annotations.db` is independent from PaperForge memory rebuild behavior.

Purpose: Prevent future refactors from treating annotation data as rebuildable machine memory. This protects user evidence.
Output: isolation regression tests and final targeted verification commands for Annotation Phase 1.
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

Current rebuild code:
@paperforge/memory/schema.py
@paperforge/memory/builder.py
@paperforge/memory/db.py

Plan dependencies:
@.planning/phases/annotation-01-storage-foundation/annotation-01-01-PLAN.md
@.planning/phases/annotation-01-storage-foundation/annotation-01-02-PLAN.md
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Add memory isolation regression tests</name>
  <files>tests/unit/annotation/test_rebuild_isolation.py</files>
  <action>
    Create `tests/unit/annotation/test_rebuild_isolation.py` with tests for:
    1. Annotation table names are not present in `paperforge.memory.schema.ALL_TABLES`.
    2. Calling `paperforge.memory.schema.drop_all_tables()` on `paperforge.db` does not affect a separate `annotations.db` file.
    3. If practical, run `build_from_index(vault)` against a tiny canonical index fixture after creating an annotation sentinel row, then verify the sentinel row still exists.

    Keep the fixture minimal:
    - create `paperforge.json` only if needed
    - create `System/PaperForge/indexes/formal-library.json`
    - include one index item with `zotero_key`, `title`, and safe defaults expected by `build_from_index`

    If full `build_from_index` setup becomes brittle, keep the stronger direct `drop_all_tables` regression and document the limitation in the summary.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_rebuild_isolation.py -q</automated>
  </verify>
  <done>Regression tests prove annotation tables are outside memory drop/rebuild table lists and separate DB file remains intact.</done>
</task>

<task type="auto">
  <name>Task 2: Run targeted Annotation Phase 1 verification</name>
  <files>
    tests/unit/annotation/test_db.py
    tests/unit/annotation/test_schema.py
    tests/unit/annotation/test_rebuild_isolation.py
  </files>
  <action>
    Run the complete targeted Annotation Phase 1 test set:

    ```powershell
    python -m pytest tests/unit/annotation/test_db.py tests/unit/annotation/test_schema.py tests/unit/annotation/test_rebuild_isolation.py -q
    ```

    Also run the directly affected config tests if `paperforge_paths` was changed:

    ```powershell
    python -m pytest tests/test_config.py -q
    ```

    Do not claim whole-repo green. Existing upstream baseline failures around `ld_deep_script`/`pf_deep_script` and missing `snapshot` fixture must be reported separately if encountered.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_db.py tests/unit/annotation/test_schema.py tests/unit/annotation/test_rebuild_isolation.py -q</automated>
  </verify>
  <done>Targeted Annotation Phase 1 tests pass, or unrelated baseline failures are documented separately.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/unit/annotation/test_db.py tests/unit/annotation/test_schema.py tests/unit/annotation/test_rebuild_isolation.py -q`
- `python -m pytest tests/test_config.py -q` if `paperforge/config.py` changed
- `python -m compileall paperforge/annotation`
</verification>

<success_criteria>
- [ ] Annotation tables are absent from `paperforge.memory.schema.ALL_TABLES`.
- [ ] Separate `annotations.db` survives memory table drop/rebuild paths.
- [ ] Targeted annotation tests pass.
- [ ] Verification output clearly distinguishes annotation status from unrelated upstream baseline failures.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-01-storage-foundation/annotation-01-03-SUMMARY.md`.
</output>
