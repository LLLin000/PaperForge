---
phase: 03
phase_name: "Obsidian Bases Config-Aware"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 9
  lessons: 3
  patterns: 3
  surprises: 2
missing_artifacts:
  - "UAT.md"
  - "VERIFICATION.md"
---

# Phase 03 Learnings: Obsidian Bases Config-Aware

## Decisions

### D1: Exactly 8 Views Per Domain Base File
Each domain Base file contains exactly 8 views: 控制面板, 推荐分析, 待 OCR, OCR 完成, 待深度阅读, 深度阅读完成, 正式卡片, 全记录.

**Rationale:** These 8 views map directly to the production workflow pipeline stages. Any fewer would miss workflow states; any more would add unnecessary complexity for this version.

**Source:** 03-01-PLAN.md, 03-01-SUMMARY.md

---

### D2: Config-Aware Path Placeholders (`${LIBRARY_RECORDS}`, etc.)
Base files use `${LIBRARY_RECORDS}`, `${LITERATURE}`, and `${CONTROL_DIR}` placeholders in `folder_filter` expressions instead of hardcoded paths.

**Rationale:** The user can configure custom directory names in `paperforge.json`. Placeholders ensure generated Base files always use the correct paths regardless of configuration.

**Source:** 03-01-PLAN.md, 03-01-SUMMARY.md

---

### D3: `# PAPERFORGE_VIEW:` Marker Prefix for View Identification
Each PaperForge-generated view is preceded by a comment marker `# PAPERFORGE_VIEW: <name>` in the .base file for unambiguous identification.

**Rationale:** The incremental merge mechanism needs to know which views are PaperForge-owned vs user-defined. The marker provides a stable, parseable identifier that survives content changes.

**Source:** 03-01-PLAN.md, 03-01-SUMMARY.md

---

### D4: Incremental Merge — Replace PF Views, Preserve User Views
On refresh (default): PaperForge standard views are always replaced with fresh content. User-defined views (those without the PAPERFORGE_VIEW prefix) are never touched.

**Rationale:** PaperForge must keep its 8 standard views aligned with the current workflow definition. User customizations to non-standard views are valuable and must survive refreshes. User customizations to standard view filters are intentionally reverted (trade-off).

**Source:** 03-01-PLAN.md, 03-01-SUMMARY.md

---

### D5: `--force` Flag for Full Regeneration
The `base-refresh --force` flag bypasses merge entirely and regenerates all views from scratch, wiping any user customizations.

**Rationale:** Provides an escape hatch when the Base file becomes corrupted or the user wants to reset to factory defaults. Without this, there is no way to clean up a broken Base file.

**Source:** 03-01-PLAN.md, 03-02-PLAN.md

---

### D6: Literature Hub.base and PaperForge.base in Addition to Per-Domain Bases
Three types of Base files are generated: one per domain (e.g., `骨科.base`), a cross-domain `Literature Hub.base` (filters on `${LIBRARY_RECORDS}` root), and a legacy `PaperForge.base` (all records).

**Rationale:** Different users need different views of the data — per-domain for focused work, cross-domain for overview, and an all-records view for complete inventory.

**Source:** 03-01-SUMMARY.md

---

### D7: `ensure_base_views` Accepts `force: bool = False` Parameter
The function signature was updated from `ensure_base_views(vault, paths, config)` to `ensure_base_views(vault, paths, config, force=False)`.

**Rationale:** The inner `refresh_base` function branches on `force`: when False, calls `merge_base_views` for incremental merge; when True, calls `_build_base_yaml` directly for full regeneration.

**Source:** 03-02-PLAN.md

---

### D8: `folder_filter` Uses Placeholder Format, Substituted After Merge
The `folder_filter` parameter (e.g., `${LIBRARY_RECORDS}/骨科`) is passed in placeholder format and only substituted after merge is complete.

**Rationale:** Merging operates on raw YAML content, not resolved paths. Substituting after merge ensures the merge logic works with stable placeholder strings, not machine-specific paths.

**Source:** 03-01-PLAN.md, 03-01-SUMMARY.md

---

### D9: STANDARD_VIEW_NAMES as a `frozenset`
The 8 standard view names are defined as a module-level `frozenset` for fast membership checks in the merge logic.

**Rationale:** `merge_base_views()` needs to identify PaperForge views by name. A frozenset provides O(1) lookup and immutability guarantees.

**Source:** 03-01-PLAN.md

---

## Lessons

### L1: User Filter Modifications on Standard Views Are Reverted
If a user modifies the filter expression of a standard PaperForge view (e.g., changes the "OCR 完成" filter), the next incremental refresh reverts it to the template definition.

**Context:** This is an intentional trade-off — standard views must match the current workflow definition. User customizations to standard views are not preserved.

**Source:** 03-01-PLAN.md, 03-01-SUMMARY.md

---

### L2: `slugify_filename()` Does Not Transliterate CJK Characters
Chinese characters like `骨科` pass through unchanged, producing `骨科.base` rather than being transliterated to `guke.base`.

**Context:** The slugify function handles whitespace and special characters but does not convert CJK to Latin. This is acceptable for this project but was surprising during initial verification.

**Source:** 03-01-SUMMARY.md

---

### L3: `folder_filter` Must Use Placeholder Format Substituted After Merge
Placeholders must survive the merge operation. If paths were substituted before merge, the merge logic would see machine-specific absolute paths and fail to match views correctly.

**Context:** The merge strategy depends on stable, predictable content to identify and replace PaperForge views. Resolved paths vary between machines and would break merge matching.

**Source:** 03-01-PLAN.md, 03-01-SUMMARY.md

---

## Patterns

### P1: Incremental Merge with Marker Comments
Use a stable comment prefix to mark owned content. On merge, replace all marked content with fresh versions while preserving everything else. The prefix serves as both documentation and merge boundary.

**When to use:** When multiple writers (a tool and a user) modify the same structured file and the tool needs to update its own sections without clobbering user additions.

**Source:** 03-01-PLAN.md, 03-01-SUMMARY.md

---

### P2: Template Placeholder Substitution at Generation Time
Use `${SCREAMING_SNAKE_CASE}` tokens in template content. Resolve to real values at write time based on configuration. Unrecognized placeholders are left unchanged.

**When to use:** When generated content must reference configurable paths, names, or values that are only known at generation time, not at template authoring time.

**Source:** 03-01-PLAN.md, 03-01-SUMMARY.md

---

### P3: Shared Properties YAML Template
Define the properties section (which is identical across all Base files) as a single YAML template string, reused by all Base file generators.

**When to use:** When multiple generated files share a common structured section. Avoids duplication and ensures consistent field definitions across all outputs.

**Source:** 03-01-PLAN.md

---

## Surprises

### S1: Chinese Filenames Pass Through `slugify` Unchanged
The `slugify_filename()` function does not transliterate CJK characters, producing `骨科.base` directly instead of `guke.base`.

**Impact:** Domain Base files use Chinese filenames. This is correct behavior for this project but was surprising because typical slugify implementations convert all non-ASCII characters. No functional issue.

**Source:** 03-01-SUMMARY.md

---

### S2: 120 Tests Pass Without Regression
The Base generation refactor (touching ~300 lines of core logic) did not break any existing tests. All 120 tests pass, including 2 skipped junction tests.

**Impact:** Demonstrates that the test suite provides good regression coverage. The incremental merge system was complex enough that some test failures were expected but none occurred.

**Source:** 03-01-SUMMARY.md, 03-02-SUMMARY.md
