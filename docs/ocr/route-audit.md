# OCR Route Audit

> Generated: 2026-06-08 | Source: import scan of `paperforge/worker/ocr*.py` and `tests/test_ocr*.py`

## Production Chain

The OCR pipeline entry point is `paperforge/worker/ocr.py::run_ocr()` which calls `postprocess_ocr_result()`. The canonical production artifact sequence is:

```text
result.json
  → canonical/blocks.raw.jsonl          (ocr_blocks.py: build_raw_blocks_for_result_lines)
  → structure/blocks.structured.jsonl    (ocr_blocks.py: build_structured_blocks, ocr_document.py: normalize_document_structure)
  → structure/document_structure.json    (ocr_document.py: normalize_document_structure)
  → structure/figure_inventory.json      (ocr_figures.py: build_figure_inventory)
  → structure/table_inventory.json       (ocr_tables.py: build_table_inventory)
  → assets/ + render/object notes        (ocr_objects.py: extract_and_write_objects)
  → render/fulltext.md + fulltext.md     (ocr_render.py: render_fulltext_markdown)
  → health/ocr_health.json               (ocr_health.py: build_ocr_health)
  → index/role-index.json                (ocr_index.py: build_role_indexes)
```

### Production modules (imported in `ocr.py`)

| Module | Function | Production Role |
| --- | --- | --- |
| `ocr_blocks.py` | `build_raw_blocks_for_result_lines`, `build_structured_blocks`, `write_raw_blocks_jsonl`, `write_structured_blocks_jsonl` | Core block pipeline |
| `ocr_document.py` | `normalize_document_structure` | Document structure normalization (called by `ocr_blocks.py`) |
| `ocr_figures.py` | `build_figure_inventory`, `write_figure_inventory` | Figure extraction and inventory |
| `ocr_tables.py` | `build_table_inventory`, `write_table_inventory` | Table extraction and inventory |
| `ocr_objects.py` | `extract_and_write_objects` | Object asset extraction (figures, tables) |
| `ocr_render.py` | `render_fulltext_markdown`, `write_render_outputs` | Fulltext markdown rendering |
| `ocr_health.py` | `build_ocr_health`, `write_ocr_health` | OCR health report |
| `ocr_index.py` | `build_role_indexes`, `write_role_index` | Role-based indexes |
| `ocr_metadata.py` | `extract_frontmatter_candidates`, `resolve_metadata`, `write_resolved_metadata` | Metadata extraction |
| `ocr_artifacts.py` | `artifact_paths_for_key`, `build_version_payload`, `compute_json_hash`, `compute_pdf_fingerprint` | Artifact management |
| `ocr_roles.py` | `assign_block_role` | Block role assignment (try-import, not guaranteed) |

### Production chain call order (from `ocr.py::postprocess_ocr_result`)

```
1. build_structured_blocks(raw_results)        → structure/blocks.structured.jsonl + document_structure
2. build_figure_inventory(structured)           → structure/figure_inventory.json
3. build_table_inventory(structured)            → structure/table_inventory.json
4. extract_and_write_objects(...)               → assets/ + render/object notes
5. render_fulltext_markdown(...)                → render/fulltext.md + fulltext.md
6. build_ocr_health(...)                        → health/ocr_health.json
7. build_role_indexes(...)                      → index/role-index.json
```

## Module Ownership

| Module | Owned By | Production? |
| --- | --- | --- |
| `ocr.py` | Core orchestrator | **production** |
| `ocr_blocks.py` | Block pipeline | **production** |
| `ocr_document.py` | Document structure | **production** |
| `ocr_figures.py` | Figure inventory | **production** |
| `ocr_tables.py` | Table inventory | **production** |
| `ocr_objects.py` | Object extraction | **production** |
| `ocr_render.py` | Fulltext rendering | **production** |
| `ocr_health.py` | Health reporting | **production** |
| `ocr_index.py` | Role indexes | **production** |
| `ocr_metadata.py` | Metadata | **production** |
| `ocr_artifacts.py` | Artifact management | **production** |
| `ocr_roles.py` | Block role assignment | **production** (try-import) |
| `ocr_math.py` | Math detection | supplemental |
| `ocr_pdf_spans.py` | PDF span extraction | supplemental |
| `ocr_profiles.py` | OCR profiles | config |
| `ocr_versions.py` | Version management | utility |
| `ocr_evidence.py` | Evidence tracking | utility |
| `ocr_rebuild.py` | Rebuild orchestration | **production** |
| `ocr_orchestrator.py` | Legacy block ordering shell | **not in production path** |
| `ocr_layout.py` | Legacy layout zone detection | **not in production path** |
| `ocr_attach.py` | Legacy attachment graph builder | **not in production path** |
| `ocr_emit.py` | Legacy page markdown emitter | **not in production path** |

## Not Used In Production Path

The following modules exist in `paperforge/worker/` but are **not imported by any production module** (`ocr.py`, `ocr_blocks.py`, `ocr_document.py`, `ocr_rebuild.py`). They are referenced only by test files for legacy/experimental verification.

| Module | Reason Not In Production | Tests That Still Import It |
| --- | --- | --- |
| `ocr_orchestrator.py` | Compatibility shell; `reorder_blocks_layered` returns blocks unchanged. Real reordering uses column-major fallback in `ocr_blocks.py::_apply_layered_body_reorder`. | `test_ocr_integration_fixtures.py` |
| `ocr_layout.py` | Simplified midpoint layout helper; `detect_layout_zones` does naive left/right split. Superseded by `ocr_document.py::normalize_document_structure`. | `test_ocr_layout_zones.py` |
| `ocr_attach.py` | Distance-only caption-media attachment; `build_attachment_graph` pairs by Y-distance only. Superseded by `ocr_figures.py::build_figure_inventory` and `ocr_tables.py::build_table_inventory`. | `test_ocr_attachments.py` |
| `ocr_emit.py` | Legacy page-level markdown emitter; `emit_page_markdown` produces per-page output. Production renderer is `ocr_render.py::render_fulltext_markdown`. | `test_ocr_emission_regressions.py` |

## Duplicate Capabilities

| Capability | Legacy Module | Production Replacement |
| --- | --- | --- |
| Block ordering/structuring | `ocr_orchestrator.py::reorder_blocks_layered` | `ocr_document.py::normalize_document_structure` |
| Layout zone detection | `ocr_layout.py::detect_layout_zones` | `ocr_document.py` regime detection |
| Caption-media attachment | `ocr_attach.py::build_attachment_graph` | `ocr_figures.py::build_figure_inventory` + `ocr_tables.py::build_table_inventory` |
| Fulltext markdown rendering | `ocr_emit.py::emit_page_markdown` | `ocr_render.py::render_fulltext_markdown` |

## Delete / Keep / Experimental Decisions

| Module | Disposition | Reason | Required Action |
| --- | --- | --- | --- |
| `ocr_orchestrator.py` | not used in production path | Compatibility shell / no production call from `ocr.py` | Add header marker or delete if import scan is empty |
| `ocr_layout.py` | not used in production path | Simplified midpoint layout helper, superseded by `ocr_document.py` | Add header marker or move experimental |
| `ocr_attach.py` | not used in production path | Distance-only attachment helper, superseded by figure/table inventories | Add header marker or move experimental |
| `ocr_emit.py` | not used in production path | Legacy emission helper, production renderer is `ocr_render.py` | Add header marker or delete if unused |

**Decision:** Keep all four modules with header warning markers. Each is still imported by dedicated test files that verify legacy behavior and serve as regression guards. Deletion or relocation can be done in a follow-up cleanup cycle after confirming test files can be retired.

## Test Coverage Map

| Test File | Covers |
| --- | --- |
| `test_ocr.py` | Core OCR pipeline (`run_ocr`, `postprocess_ocr_result`) |
| `test_ocr_blocks.py` | Block building pipeline |
| `test_ocr_document.py` | Document structure normalization |
| `test_ocr_rendering.py` | Fulltext markdown rendering |
| `test_ocr_figures.py` | Figure inventory |
| `test_ocr_tables.py` | Table inventory |
| `test_ocr_objects.py` | Object extraction |
| `test_ocr_health.py` | Health reporting |
| `test_ocr_index.py` | Role indexes |
| `test_ocr_metadata.py` | Metadata extraction |
| `test_ocr_artifacts.py` | Artifact management |
| `test_ocr_roles.py` | Role assignment |
| `test_ocr_rebuild.py` | Rebuild orchestration |
| `test_ocr_integration_fixtures.py` | Legacy `ocr_orchestrator.py` imports |
| `test_ocr_layout_zones.py` | Legacy `ocr_layout.py` imports |
| `test_ocr_attachments.py` | Legacy `ocr_attach.py` imports |
| `test_ocr_emission_regressions.py` | Legacy `ocr_emit.py` imports |
| `test_ocr_route_audit.py` | This route audit existence contract |

## Follow-Up Risks

- **Deletion risk:** Removing any of the four legacy modules will break their dedicated test files. Tests must be retired first.
- **Hidden callers:** A grep of the full codebase confirmed no production imports of `ocr_orchestrator`, `ocr_layout`, `ocr_attach`, or `ocr_emit`. However, external plugins or scripts not in this repo could import them.
- **`ocr_orchestrator.py::BlockAnnotated` dataclass:** Not imported anywhere. Safe to remove if no external consumers exist.
- **`ocr_layout.py::LayoutZone` dataclass:** Not imported anywhere. Safe to remove if no external consumers exist.
- **`ocr_attach.py::Attachment` dataclass:** Not imported anywhere. Safe to remove if no external consumers exist.
