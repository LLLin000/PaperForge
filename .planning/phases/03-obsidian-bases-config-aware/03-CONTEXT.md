# Phase 3: Config-Aware Obsidian Bases — Context

**Phase:** 03-obsidian-bases-config-aware
**Status:** discuss-phase complete, decisions locked
**Created:** 2026-04-23
**Requirements:** BASE-01, BASE-02, BASE-03, BASE-04

---

## 1. Executive Summary

Phase 3 replaces the simple single-view Base generation with a config-aware 8-view system that matches the real vault workflow. Current `ensure_base_views()` generates only 1 table view per domain Base. Production Bases (骨科.base, 运动医学.base) have 8 named views covering the full pipeline: control panel, recommended analysis, pending OCR, OCR done, pending deep reading, deep reading done, formal cards, and all records.

Key changes:
- `write_base_file()` refactored to accept multiple named views (not just one)
- Path placeholders using `${SCREAMING_SNAKE_CASE}` config keys
- Cross-domain Literature Hub Base with full 8-view structure
- Preservation of user-edited .base files (not overwritten unless refresh flag)

---

## 2. Locked Decisions

### 3.1 Domain Base View Structure — DECIDED (Option A)

**8 views for each domain Base:**

| View Name | Purpose | Key Filter/Sort |
|-----------|---------|-----------------|
| 控制面板 (Control Panel) | Overview stats | All records, ordered by file.name |
| 推荐分析 (Recommended Analysis) | `recommend_analyze: true` | `recommend_analyze = true` |
| 待 OCR (Pending OCR) | `do_ocr: true AND ocr_status: pending` | `do_ocr = true AND ocr_status = pending` |
| OCR 完成 (OCR Done) | `ocr_status: done` | `ocr_status = done` |
| 待深度阅读 (Pending Deep Reading) | `analyze: true AND deep_reading_status: pending` | `analyze = true AND deep_reading_status = pending` |
| 深度阅读完成 (Deep Reading Done) | `deep_reading_status: done` | `deep_reading_status = done` |
| 正式卡片 (Formal Cards) | Records with formal notes | `deep_reading_status = done` |
| 全记录 (All Records) | Complete record list | All, ordered by title |

**Decision record:** Use exactly these 8 view names in Chinese to match production Bases. Each view is a table with the same columns but different filters.

### 3.2 Cross-Domain Base (Literature Hub) — DECIDED (Option A)

**Literature Hub.base** has the same 8-view structure but `file.inFolder` points to the root `library_records` directory (all domains).

**Decision record:** Literature Hub.base is a separate .base file generated alongside domain Bases. It uses the same 8-view template but with `file.inFolder("${LIBRARY_RECORDS}")` instead of `file.inFolder("${LIBRARY_RECORDS}/骨科")`.

### 3.3 Config-aware Path Replacement — DECIDED (Option A)

**Placeholder format:** `${SCREAMING_SNAKE_CASE}` — matches environment variable naming convention.

**Example template:**
```yaml
filters:
  and:
    - file.inFolder("${LIBRARY_RECORDS}/骨科")
properties:
  zotero_key:
    displayName: "Zotero Key"
```

**Generation-time substitution:**
- Replace `${LIBRARY_RECORDS}` with vault-relative path to `paths['library_records']`
- Replace `${LITERATURE}` with vault-relative path to `paths['literature']`
- Replace `${CONTROL_DIR}` with vault-relative path to `paths['control']`

**Decision record:** Placeholders use SCREAMING_SNAKE_CASE to align with env var convention. Substitution happens at generation time using resolved paths from `paperforge_paths()`.

### 3.4 Multi-domain Consistency — DECIDED (Option A)

**Shared template + per-domain instances:**
- One template function generates the 8-view structure
- `ensure_base_views()` calls it once per domain (passing domain name)
- Literature Hub calls it once with special cross-domain parameters

**Decision record:** No domain-specific logic in the template. All domain Bases are generated from the same function with domain name as parameter.

### 3.5 Template Variable Naming — DECIDED (Option A)

**Convention:** `${SCREAMING_SNAKE_CASE}` for all path placeholders.

**List of placeholders to support:**
| Placeholder | Resolved From |
|-------------|---------------|
| `${LIBRARY_RECORDS}` | `paths['library_records']` relative to vault |
| `${LITERATURE}` | `paths['literature']` relative to vault |
| `${CONTROL_DIR}` | `paths['control']` relative to vault |

**Decision record:** SCREAMING_SNAKE_CASE matches env var convention and is immediately recognizable as a placeholder.

---

## 3. Architecture Changes

### 3.1 Refactored `write_base_file()`

Current signature:
```python
def write_base_file(path: Path, folder_filter: str, name: str) -> None:
```

New signature:
```python
def write_base_file(
    path: Path,
    folder_filter: str,
    views: list[dict],  # list of {name, order, filters} dicts
) -> None:
```

Each view dict:
```python
{
    "name": "控制面板",           # view display name
    "order": ["file.name", ...],  # column order (same as current)
    "filter": None,               # optional additional filter expression
}
```

### 3.2 New Function: `build_base_views()`

Builds the 8-view list for a domain:
```python
def build_base_views(domain: str) -> list[dict]:
    """Returns list of 8 view dicts for a domain Base."""
```

### 3.3 New Function: `substitute_config_placeholders()`

Performs `${KEY}` substitution on the generated Base content:
```python
def substitute_config_placeholders(content: str, paths: dict[str, Path]) -> str:
    """Replace ${LIBRARY_RECORDS}, ${LITERATURE}, ${CONTROL_DIR} with vault-relative paths."""
```

### 3.4 Modified `ensure_base_views()`

```python
def ensure_base_views(vault: Path, paths: dict[str, Path], config: dict) -> None:
    # For each domain: generate 8-view Base with placeholders → substitute → write
    # For Literature Hub: same but cross-domain filter
    # Skip if .base file exists and has user edits (check for preservation marker)
```

### 3.5 Preservation Marker

To avoid overwriting user-edited Bases, first line of generated .base files:
```yaml
# GENERATED by PaperForge — do not edit manually (or edits will be lost on refresh)
```

If this marker exists and user may have edited, skip unless `--force-refresh` flag is passed.

---

## 4. 8-View Filter Definitions

Each view has a table type with specific filters:

### View 1: 控制面板 (Control Panel)
- **Filter:** None (all records in domain)
- **Order:** `file.name`

### View 2: 推荐分析 (Recommended Analysis)
- **Filter:** `analyze = true AND recommend_analyze = true`
- **Order:** `year, title`

### View 3: 待 OCR (Pending OCR)
- **Filter:** `do_ocr = true AND ocr_status = pending`
- **Order:** `year, title`

### View 4: OCR 完成 (OCR Done)
- **Filter:** `ocr_status = done`
- **Order:** `year, title`

### View 5: 待深度阅读 (Pending Deep Reading)
- **Filter:** `analyze = true AND ocr_status = done AND deep_reading_status = pending`
- **Order:** `year, title`

### View 6: 深度阅读完成 (Deep Reading Done)
- **Filter:** `deep_reading_status = done`
- **Order:** `year, title`

### View 7: 正式卡片 (Formal Cards)
- **Filter:** `deep_reading_status = done`
- **Order:** `title, year`

### View 8: 全记录 (All Records)
- **Filter:** None (all records)
- **Order:** `title, year`

**Common columns across all views:**
```
file.name, title, year, has_pdf, do_ocr, analyze, ocr_status, deep_reading_status, pdf_path, fulltext_md_path
```

---

## 5. Files to Create / Modify

### New Files
- `tests/test_base_views.py` — tests for 8-view generation and placeholder substitution
- `tests/test_base_preservation.py` — tests for user-edit preservation logic

### Modified Files
- `pipeline/worker/scripts/literature_pipeline.py` — refactor `write_base_file()`, add `build_base_views()`, `substitute_config_placeholders()`, update `ensure_base_views()`

---

## 6. Backward Compatibility

- Existing .base files without the preservation marker are regenerated
- `paperforge base-refresh --force` flag forces regeneration of all Bases including user-edited
- Library record frontmatter schema unchanged

---

## 7. Testing Strategy

| Test | Coverage |
|------|----------|
| `build_base_views("骨科")` returns exactly 8 views | BASE-01 |
| Each view has correct filter expression | BASE-01 |
| Placeholder substitution replaces all 3 placeholders | BASE-02 |
| Vault-relative path computed correctly (Chinese chars safe) | BASE-02 |
| Domain Base with `file.inFolder("${LIBRARY_RECORDS}/骨科")` | BASE-01 |
| Literature Hub Base with `file.inFolder("${LIBRARY_RECORDS}")` | BASE-04 |
| Existing .base without preservation marker → regenerated | BASE-03 |
| Existing .base with preservation marker → skipped | BASE-03 |
| `--force-refresh` overrides preservation → regenerated | BASE-03 |

---

## 8. Reference Links

- Phase 1, 2 CONTEXT: `.planning/phases/01-config-and-command-foundation/CONTEXT.md`, `.planning/phases/02-paddleocr-and-pdf-path-hardening/CONTEXT.md`
- Requirements: `.planning/REQUIREMENTS.md` (BASE-01 through BASE-04)
- Base generation code: `pipeline/worker/scripts/literature_pipeline.py` lines 199–254
- `paperforge/config.py` — `paperforge_paths()` function used for resolution
