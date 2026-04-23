# 03-01-SUMMARY: Base Generation Refactor — 8 Views + Incremental Merge + Placeholder Substitution

## What was built

Phase 3 Plan 01 refactors the Base file generation system in `literature_pipeline.py` to produce production-matching 8-view Obsidian Base files with config-aware path placeholders and incremental merge (user views preserved on refresh).

## Files modified

- `pipeline/worker/scripts/literature_pipeline.py`

## New functions added (in order)

| Function | Line | Purpose |
|----------|------|---------|
| `STANDARD_VIEW_NAMES` | 23 | frozenset of 8 standard PaperForge view names |
| `PAPERFORGE_VIEW_PREFIX` | 210 | Comment marker for PaperForge views in .base files |
| `build_base_views()` | 212 | Returns list of 8 view dicts for a domain |
| `substitute_config_placeholders()` | 264 | Replaces ${LIBRARY_RECORDS} etc. with vault-relative paths |
| `_render_views_section()` | 307 | Renders a view dict list to YAML views: section |
| `merge_base_views()` | 318 | Incrementally merges PaperForge views, preserves user views |
| `_build_base_yaml()` | 478 | Builds complete .base YAML with PAPERFORGE_VIEW_PREFIX markers |
| `ensure_base_views()` (replaced) | 504 | Generates domain bases, Literature Hub, PaperForge.base |

## Key behaviors

### 8 views per domain
Each domain Base file now contains exactly 8 views: 控制面板, 推荐分析, 待 OCR, OCR 完成, 待深度阅读, 深度阅读完成, 正式卡片, 全记录

### Config-aware path placeholders
Base files use `${LIBRARY_RECORDS}` (and `${LITERATURE}`, `${CONTROL_DIR}`) placeholders in folder_filter. These are substituted at generation time to vault-relative paths (e.g., `03_Resources/LiteratureControl/library-records/骨科`).

### Incremental merge (preserve user views)
- PaperForge views are marked with `# PAPERFORGE_VIEW: <name>` prefix comments
- On refresh (force=False): only PaperForge views are replaced; user-defined views (no prefix) are preserved
- On refresh (force=True): full regeneration — all views replaced with fresh PaperForge views
- User modifications to standard view filters are reverted on incremental refresh (trade-off for always-current workflow)

### Base files generated
- `<slug>.base` — one per domain (e.g., `guke.base` for 骨科)
- `Literature Hub.base` — cross-domain view (filters on `${LIBRARY_RECORDS}`)
- `PaperForge.base` — legacy all-records view (filters on `${LIBRARY_RECORDS}`)

## Verification

```
$ python -m pytest tests/test_base_views.py tests/test_base_preservation.py -v
tests/test_base_views.py: 11 passed
tests/test_base_preservation.py: 10 passed
```

All 120 tests pass (2 skipped for junction-related tests).

## Notes

- `slugify_filename()` does not transliterate CJK characters — Chinese domain names pass through unchanged, so `骨科.base` is created directly (not `guke.base`)
- The `folder_filter` in domain bases uses placeholder format `${LIBRARY_RECORDS}/骨科` which is substituted at write time
- First-run generation (no existing file) uses `_build_base_yaml()` directly; subsequent refreshes use `merge_base_views()`
