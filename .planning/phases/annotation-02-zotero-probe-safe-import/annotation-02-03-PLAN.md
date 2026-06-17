---
phase: annotation-02-zotero-probe-safe-import
plan: 03
type: execute
wave: 3
depends_on:
  - annotation-02-02
files_modified:
  - paperforge/annotation/importer.py
  - tests/unit/annotation/test_importer.py
autonomous: true
requirements:
  - ZOT-01
  - ZOT-02
  - ZOT-03
  - ZOT-05
  - SAFE-04

must_haves:
  truths:
    - "D-02: Paper-scoped import is the primary Phase 2 behavior"
    - "D-03: Stale reconciliation is limited to the requested paper/source/library/parent/attachment scope"
    - "D-06: Import matching uses source/library/parent/attachment/annotation identity rather than a bare Zotero key"
    - "D-07: Imported Zotero rows remain read-only in PaperForge"
    - "SAFE-04: Importer writes only to PaperForge annotations.db and never to Zotero SQLite"
  artifacts:
    - path: "paperforge/annotation/importer.py"
      provides: "Scoped import reconciliation service for normalized annotations"
      exports: ["ImportResult", "import_zotero_annotations_for_paper"]
    - path: "tests/unit/annotation/test_importer.py"
      provides: "Upsert, stale-scope, and read-only import tests"
  key_links:
    - from: "paperforge/annotation/importer.py"
      to: "paperforge/annotation/db.py"
      via: "uses PaperForge annotations.db connection only"
      pattern: "get_annotations_connection"
    - from: "paperforge/annotation/importer.py"
      to: "paperforge/annotation/schema.py"
      via: "ensures annotations schema before writes"
      pattern: "ensure_schema"
    - from: "paperforge/annotation/importer.py"
      to: "paperforge/annotation/zotero_normalize.py"
      via: "persists normalized annotation rows"
      pattern: "NormalizedAnnotation"
---

<objective>
Implement paper-scoped Zotero annotation import into `annotations.db`.

Purpose: Safely insert/update Zotero annotations and mark stale rows only inside the requested paper scope, so one paper import cannot damage unrelated paper annotation state.
Output: importer service, import result counts, scoped stale reconciliation tests.
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

Current annotation DB:
@paperforge/annotation/db.py
@paperforge/annotation/schema.py
@paperforge/annotation/zotero_normalize.py
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Add failing importer reconciliation tests</name>
  <files>tests/unit/annotation/test_importer.py</files>
  <action>
    Create importer tests against a temporary `annotations.db`.

    Cover:
    1. Importing new normalized Zotero rows inserts rows into `annotations`.
    2. Re-importing the same identity updates content/comment/color/source_modified_at instead of duplicating rows.
    3. Missing rows from the latest import are soft-deleted or marked stale only within the requested paper/source/library/parent/attachment scope.
    4. Rows for a different `paper_id` are untouched.
    5. Rows for a different Zotero library or attachment are untouched.
    6. Local PaperForge rows (`source = 'paperforge'`) are untouched.
    7. Imported rows keep `is_readonly = 1`.
    8. Import returns counts for inserted, updated, unchanged, stale/deleted, and skipped/invalid rows.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_importer.py -q</automated>
  </verify>
  <done>Tests fail because importer does not exist yet.</done>
</task>

<task type="auto">
  <name>Task 2: Implement scoped importer service</name>
  <files>paperforge/annotation/importer.py</files>
  <action>
    Implement an importer service that accepts:
    - target `annotations.db` path or open connection
    - `paper_id`
    - `source_library_id`
    - `source_parent_key`
    - optional `source_attachment_key`
    - iterable of normalized annotations

    Behavior:
    - Call `ensure_schema` before writes.
    - Upsert by deterministic `id` or by the source identity fields.
    - Preserve `created_at` on update and refresh `updated_at`.
    - Set `deleted_at = NULL` when a previously stale row reappears.
    - Mark stale only for Zotero rows matching the explicit paper scope.
    - Never update or delete local PaperForge rows.
    - Return an `ImportResult` with stable count fields for Phase 3 CLI JSON.

    Keep this module free of CLI parsing and Obsidian plugin dependencies.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_importer.py tests/unit/annotation/test_zotero_normalize.py tests/unit/annotation/test_zotero_probe.py -q</automated>
  </verify>
  <done>Importer tests pass and lower-level probe/normalize tests remain green.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/unit/annotation/test_importer.py tests/unit/annotation/test_zotero_normalize.py tests/unit/annotation/test_zotero_probe.py -q`
- `python -m compileall paperforge/annotation`
</verification>

<success_criteria>
- [ ] Import inserts new Zotero annotations.
- [ ] Re-import updates matching rows without duplicates.
- [ ] Stale marking is limited to the requested paper/source/library/attachment scope.
- [ ] Unrelated paper/library/attachment/local rows are untouched.
- [ ] Import results expose counts for later CLI JSON.
- [ ] Importer writes only to `annotations.db`.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-03-SUMMARY.md`.
</output>
