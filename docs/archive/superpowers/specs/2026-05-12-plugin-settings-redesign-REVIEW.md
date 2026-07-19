---
phase: settings-redesign-spec-review
reviewed: 2026-05-12T12:00:00Z
depth: deep
files_reviewed: 5
files_reviewed_list:
  - docs/superpowers/specs/2026-05-12-plugin-settings-redesign.md
  - paperforge/plugin/main.js
  - paperforge/services/skill_deploy.py
  - paperforge/skills/literature-qa/SKILL.md
  - paperforge/skills/literature-logging/SKILL.md
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
status: issues_found
---

# Spec Review: Plugin Settings Redesign

**Reviewed:** 2026-05-12
**Depth:** deep (cross-file analysis across plugin codebase, skill deploy, SKILL.md frontmatter)
**Files Reviewed:** 5
**Status:** ISSUES_FOUND — one BLOCKER must be resolved before implementation

## Summary

Cross-referenced the proposed 2-tab settings redesign against the current PaperForge plugin codebase (`paperforge/plugin/main.js`), the `skill_deploy.py` AGENT_SKILL_DIRS mapping, and the two existing SKILL.md files. The spec's architecture (Claudian tab pattern, DOM-based tab switching, `disable-model-invocation` toggle) is well-reasoned and compatible. However, one data persistence issue is a BLOCKER, and several gaps/ambiguities need resolution before implementation proceeds.

---

## Critical Issues

### CR-01: `saveSettings()` will silently discard all new `data.json` keys

**File:** `paperforge/plugin/main.js:3534-3542`
**Issue:** The spec proposes storing new feature-toggle data in Obsidian's plugin `data.json` under keys like `features`, `vector_db_mode`, `vector_db_model`, `vector_db_api_key`, and `frozen_skills`. However, the current `saveSettings()` method explicitly filters out any key not present in `DEFAULT_SETTINGS`:

```js
async saveSettings() {
    // Only persist non-path settings to plugin data.json
    const dataToSave = {};
    for (const key of Object.keys(DEFAULT_SETTINGS)) {  // ← whitelist filter
        if (key in this.settings) {
            dataToSave[key] = this.settings[key];
        }
    }
    await this.saveData(dataToSave);
}
```

`DEFAULT_SETTINGS` (line 547-556) currently contains only:
- `vault_path`, `setup_complete`, `auto_update`, `agent_platform`, `language`, `paddleocr_api_key`, `zotero_data_dir`, `python_path`

Any new key (`features`, `vector_db_mode`, `frozen_skills`, etc.) will be **silently discarded** on every save. Toggling a feature, changing a vector DB mode, or freezing a skill would appear to work until the user re-opens settings — at which point `loadData()` returns the stale (or default) values.

**Fix:** One of two approaches:

**Option A — Extend DEFAULT_SETTINGS (simpler, less risky):**
```js
const DEFAULT_SETTINGS = {
    vault_path: '',
    setup_complete: false,
    auto_update: true,
    agent_platform: 'opencode',
    language: '',
    paddleocr_api_key: '',
    zotero_data_dir: '',
    python_path: '',
    // NEW: Feature toggles
    features: {
        fts_search: true,
        agent_context: true,
        reading_log: true,
        vector_db: false,
    },
    vector_db_mode: 'local',
    vector_db_model: 'all-MiniLM-L6-v2',
    vector_db_api_key: '',
    frozen_skills: {},
};
```

**Option B — Change save logic to whitelist exclusions rather than inclusions:**
```js
// Persist everything except internal/temporary fields
const EXCLUDE_KEYS = new Set(['_python_path_stale', '_saveTimeout', '_pfConfig']);
const dataToSave = {};
for (const key of Object.keys(this.settings)) {
    if (!EXCLUDE_KEYS.has(key) && typeof this.settings[key] !== 'function') {
        dataToSave[key] = this.settings[key];
    }
}
```

Option A is recommended as it preserves the defensive posture of the existing code.

---

## Warnings

### WR-01: `source` field missing — system skills will be mis-categorized as user skills

**File:** `paperforge/skills/literature-qa/SKILL.md`, `paperforge/skills/literature-logging/SKILL.md`
**Issue:** The spec uses `source: paperforge` frontmatter to identify system-managed skills (with update/freeze controls) vs user skills (`source: user` or no `source` field → toggle only). Neither existing SKILL.md has a `source` field:

```yaml
# literature-qa/SKILL.md (current)
name: literature-qa
description: >
  学术文献库操作：精读、问答、检索、批量阅读...

# literature-logging/SKILL.md (current)
name: literature-logging
description: >
  Literature reading and working log management...
```

Per the spec's rules: skills without `source` are treated as **user** skills (toggle only, no update button). This means the two PaperForge system skills would show up without update/freeze controls on first install — users would need the implementation to retroactively add `source: paperforge` to detect them correctly.

**Fix:** Add `source: paperforge` to both SKILL.md files as part of this implementation, and include it in the `deploy_skills()` copytree operation. Also add a `version` field (currently absent from both) since the spec expects it for GitHub semver comparison.

```yaml
# Proposed addition to both SKILL.md frontmatter blocks
source: paperforge
version: 1.5.5
```

### WR-02: Feature toggle enforcement is missing — no code that reads `features.*` to gate CLI commands

**File:** Spec section "Section 2: Feature Toggles" 
**Issue:** The spec states "When a feature is disabled, the corresponding CLI command returns a clear error message." However, the spec only covers the **settings UI** side — there is no corresponding mechanism described for the Python CLI (`cli.py`) or workers to read `features.*` from `data.json` (which lives in the vault's `.obsidian/plugins/paperforge/` directory, inaccessible at runtime unless the plugin passes the values through `paperforge.json` or an env var).

Either:
- The plugin needs to write toggles into `paperforge.json` so the Python runtime can read them, OR
- The plugin needs to pass toggles as CLI flags/arguments when invoking commands, OR
- The enforcement lives only in the plugin's command palette (never calls CLI for disabled features)

**Fix:** Add explicit documentation of the enforcement mechanism. Recommended: the plugin writes a `feature_toggles` block to `paperforge.json` during `saveSettings()`, mirroring the existing `vault_config` block pattern (see `savePaperforgeJson()` at line 3455). This way both plugin and Python runtime have a single source of truth.

### WR-03: `_debouncedSave()` calls `saveSettings()` — both save paths need updating

**File:** `paperforge/plugin/main.js:2573-2576`
**Issue:** The settings tab has two save pathways:
1. Direct calls: `this.plugin.saveSettings()` (line 2268 in the Python path onChange handler)
2. Debounced calls: `this._debouncedSave()` (lines 2214, 2223) which calls `this.plugin.saveSettings()` after 500ms

Both flow through the same `saveSettings()` method. If CR-01 is fixed (extending DEFAULT_SETTINGS), this is not an additional bug — but it means **any new Setting added to the features tab must use the same save mechanism**. The spec doesn't mention this constraint.

**Fix:** Document in implementation notes that all new toggle handlers should call `this._debouncedSave()` (for inputs) or `this.plugin.saveSettings()` (for immediate actions). For the skill toggle that writes to SKILL.md frontmatter (not data.json), a separate write path is needed — this is handled correctly by the spec but should be called out.

---

## Info

### IN-01: JSON key nesting inconsistency between architecture diagram and data storage section

**File:** `docs/superpowers/specs/2026-05-12-plugin-settings-redesign.md:29-30 vs 170-185`
**Issue:** The architecture diagram nests vector DB config under a `向量数据库` section with `开关`, `模式`, `本地`, `API` as sub-items. The JSON storage section places `features.vector_db` (the master toggle) nested under `features`, but places `vector_db_mode`, `vector_db_model`, and `vector_db_api_key` at the **top level** of data.json — not under `features.vector_db.*`. This is structurally valid but the flat/grouped inconsistency between the spec's labeled options and the flat JSON may cause confusion during implementation.

```json
// Spec proposes:
{
  "features": { "vector_db": false },   // master toggle nested
  "vector_db_mode": "local",            // implementation detail at top level
  "vector_db_model": "...",             // ...
  "vector_db_api_key": ""               // ...
}
```

**Fix:** Consider either fully nesting (`features.vector_db.enabled`, `features.vector_db.mode`, etc.) or fully flattening (`features_vector_db`, `features_vector_db_mode`, etc.). The current mixed approach works but adds mental overhead. The nested approach is cleaner for future feature additions.

### IN-02: Vector DB panel gaps — model detection and error handling unspecified

**File:** `docs/superpowers/specs/2026-05-12-plugin-settings-redesign.md:161-164`
**Issue:** The vector DB panel design leaves several implementation details ambiguous:

1. **Model installation state detection**: The status badge `● 已安装 / ○ 未安装` has no specified detection logic. `sentence-transformers` models download on first use (triggered by `SentenceTransformer('all-MiniLM-L6-v2')`), not by a distinct install step. How does the UI know the model is installed? Checking for cached files in `~/.cache/torch/sentence_transformers/`? Running a probe import?

2. **Installation is async but not cancellable**: "`pip install` is async — show progress bar" — but what happens if the user closes Obsidian or switches vaults mid-install? Is there a cancel mechanism?

3. **No network error handling**: What does the UI show if `pip install` fails due to network issues, disk space, or permissions?

**Fix:** Add implementation details for each of these edge cases to the spec, or document them as deferred design decisions.

### IN-03: Tab state is DOM-preserved between switches but NOT across re-opens

**File:** Spec section "Tab Implementation" vs `paperforge/plugin/main.js:2206-2208`
**Issue:** The spec correctly follows the Claudian pattern (all tabs exist in DOM, CSS toggles visibility). This preserves form field state when switching between 安装 and 功能 tabs within a single settings session. However, Obsidian calls `display()` on every settings tab open, which runs `containerEl.empty()` (line 2208) and rebuilds the entire UI from scratch. This is standard Obsidian behavior, but means:
- Switching tabs: state preserved (correct)
- Closing and reopening settings: state lost (standard, acceptable)
- Running "Sync Runtime" → calls `this.display()` (line 2553, 2562): **entire settings rebuilt, active tab resets to default**

The Sync Runtime action at line 2553/2562 explicitly calls `this.display()` which would reset any partially filled forms or the active tab selection back to default. This shouldn't block the spec, but should be noted: the sync runtime action should either:
- Preserve `this.activeTab` before calling `this.display()`, or
- Not call `this.display()` at all (re-render only the runtime health section)

**Fix:** Add a note to the implementation plan: `this.display()` reset is acceptable for a settings reopen, but the sync runtime flow should preserve `this.activeTab` across the re-render.

---

_Reviewed: 2026-05-12T12:00:00Z_
_Reviewer: VT-OS/OPENCODE (gsd-code-reviewer)_
_Depth: deep_
