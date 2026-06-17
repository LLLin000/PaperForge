---
phase: annotation-02-zotero-probe-safe-import
plan: 02
type: execute
wave: 2
depends_on:
  - annotation-02-01
files_modified:
  - paperforge/annotation/zotero_normalize.py
  - paperforge/annotation/__init__.py
  - tests/unit/annotation/test_zotero_normalize.py
autonomous: true
requirements:
  - ZOT-01
  - ZOT-03
  - ZOT-05

must_haves:
  truths:
    - "D-06: Imported identity includes source, source_library_id, source_parent_key, source_attachment_key, and source_annotation_key"
    - "D-07: Zotero-sourced normalized records are read-only in PaperForge"
    - "D-09: Normalization preserves selected text, comment, color, page label/index, sort index, tags, position JSON, Zotero modified time, attachment key, parent item key, and library scope"
    - "Normalization uses the existing source-agnostic annotations schema from Annotation Phase 1"
  artifacts:
    - path: "paperforge/annotation/zotero_normalize.py"
      provides: "Zotero raw row to PaperForge annotation row normalization"
      exports: ["NormalizedAnnotation", "normalize_zotero_annotation"]
    - path: "tests/unit/annotation/test_zotero_normalize.py"
      provides: "Normalization field preservation and identity tests"
  key_links:
    - from: "paperforge/annotation/zotero_normalize.py"
      to: "paperforge/annotation/schema.py"
      via: "emits rows compatible with annotations table columns"
      pattern: "paper_id"
    - from: "tests/unit/annotation/test_zotero_normalize.py"
      to: "paperforge/annotation/zotero_normalize.py"
      via: "imports normalizer"
      pattern: "from paperforge.annotation.zotero_normalize import"
---

<objective>
Normalize raw Zotero annotation rows into PaperForge annotation records.

Purpose: Convert Zotero's storage shape into a stable source-agnostic record that can be inserted into `annotations.db` while preserving the fields researchers need.
Output: normalization module and tests for identity, read-only state, JSON payloads, and field preservation.
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

Current schema:
@paperforge/annotation/schema.py
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Add failing normalization tests</name>
  <files>tests/unit/annotation/test_zotero_normalize.py</files>
  <action>
    Create tests for `normalize_zotero_annotation`.

    Cover:
    1. Output `source` is `zotero`.
    2. `source_library_id`, `source_parent_key`, `source_attachment_key`, and `source_annotation_key` are all populated.
    3. The generated `id` is deterministic and includes source/library/attachment/annotation identity, not the bare annotation key alone.
    4. `selected_text`, `comment`, `color`, `page_label`, `page_index`, `sort_index`, and `source_modified_at` are preserved.
    5. `tags_json`, `position_json`, and `selector_json` are valid JSON strings.
    6. Zotero-sourced records have `is_readonly = 1` and an imported/synced-style `sync_state`.
    7. Invalid required fields raise a structured import error rather than silently creating a weak row.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_zotero_normalize.py -q</automated>
  </verify>
  <done>Tests fail because normalization module is not implemented yet.</done>
</task>

<task type="auto">
  <name>Task 2: Implement normalized annotation model and converter</name>
  <files>
    paperforge/annotation/zotero_normalize.py
    paperforge/annotation/__init__.py
  </files>
  <action>
    Implement a small `NormalizedAnnotation` dataclass or equivalent typed structure.

    Implement `normalize_zotero_annotation(raw, paper_id)`:
    - Accept raw rows from `zotero_probe` as dict-like objects.
    - Validate required identity fields.
    - Build a deterministic PaperForge annotation `id`, such as `zotero:{library}:{attachment}:{annotation}`.
    - Map Zotero annotation type to PaperForge `type`, preserving original type when possible.
    - Convert tags/position/selector to compact JSON strings.
    - Set `source = "zotero"`.
    - Set `is_readonly = 1`.
    - Set `deleted_at = None`.

    Export the normalizer from `paperforge.annotation.__init__` only if this matches the package's current export style. Keep imports lightweight.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/annotation/test_zotero_normalize.py tests/unit/annotation/test_zotero_probe.py -q</automated>
  </verify>
  <done>Normalization tests pass and probe tests remain green.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/unit/annotation/test_zotero_normalize.py tests/unit/annotation/test_zotero_probe.py -q`
- `python -m compileall paperforge/annotation`
</verification>

<success_criteria>
- [ ] Normalized records preserve all required annotation content and provenance.
- [ ] Identity includes source/library/parent/attachment/annotation scope.
- [ ] Zotero rows normalize as read-only.
- [ ] JSON fields are valid JSON strings.
- [ ] Invalid raw payloads fail clearly.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-02-SUMMARY.md`.
</output>
