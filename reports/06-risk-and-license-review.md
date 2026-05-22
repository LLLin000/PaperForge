# Risk & License Review

## License Compatibility

| Component | License | Usage | Compatible? |
|-----------|---------|-------|-------------|
| Zotero | AGPL-3.0 | SQLite schema reference, annotations.js implementation patterns | ✅ Read-only reference, no code copied |
| ZotFlow | AGPL-3.0 | Architecture inspiration, not code | ✅ Clean-room design |
| PDF++ | MIT | Overlay technique reference | ✅ MIT allows study/implementation |
| Obsidian | Proprietary | Plugin development | ✅ Plugin API is public |
| PaperForge | (Check LICENSE file) | This project | N/A |

## Technical Risks

### Risk 1: Zotero SQLite Schema Instability
- **Impact**: Schema changes could break annotation import
- **Mitigation**: Version check on Zotero schema; probe script validates detected schema; clear error message if schema is unknown
- **Detection**: Compare detected table columns against known schema version

### Risk 2: Obsidian PDF Viewer Internal API Breakage
- **Impact**: Monkey-patching breaks after Obsidian update
- **Mitigation**: 
  - `requireApiVersion()` checks before applying patches
  - Graceful degradation (no crash if patch fails)
  - Each patch independently try-caught
  - Alert user if annotation overlay cannot initialize
- **Historical context**: PDF++ has survived 254 releases across 2 years, proving the approach is viable

### Risk 3: Concurrent Zotero SQLite Access
- **Impact**: Reading zotero.sqlite while Zotero is running may get stale data or SQLITE_BUSY
- **Mitigation**: 
  - Default behavior: copy zotero.sqlite to temp directory before reading
  - SQLITE_BUSY detection with retry
  - Clear warning in documentation about closing Zotero before import

### Risk 4: Performance with Large Annotation Sets
- **Impact**: 500+ annotations on a single paper could cause slow overlay rendering
- **Mitigation**:
  - Rects merged per page, not per annotation
  - Only render annotations for visible pages
  - Debounce rerender during scroll/zoom
  - Cache computed overlay DOM elements

### Risk 5: Plugin Conflict with PDF++
- **Impact**: Both plugins patch the same PDF viewer methods
- **Detection**: Check for `window.PDFPlus` or `document.querySelector('.pdf-plus-*')` at init
- **Mitigation**: 
  - Document that PaperForge's annotation overlay is incompatible with PDF++ highlights
  - Disable overlay if PDF++ detected, fall back to panel-only mode

## Operational Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| User accidentaly deletes annotations | Data loss | Soft delete by default; export/backup command |
| Corrupted annotations.db | Data loss | WAL mode; integrity_check on startup; backup before migration |
| Zotero upgrade changes SQLite path | Import fails | ZOTERO_DATA_DIR env var; auto-detect from registry/macOS paths |
| Very large position JSON (>65KB) | Truncation risk | Zotero splits annotations >65KB; handle both split and unsplit cases |

## Security Considerations

- **No credential exposure**: Local SQLite reading requires no API keys
- **No network dependency**: Phase 1 is fully offline
- **Future Web API keys**: Will use Obsidian SecretStorage (like ZotFlow), never data.json
- **SQL injection**: All SQL queries use parameterized statements
