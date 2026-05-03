# Phase 22: Configuration Truth & Compatibility - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Make `paperforge.json` the single authoritative runtime truth across CLI, workers, setup, and plugin. Eliminate the drift between Python defaults, plugin DEFAULT_SETTINGS, and `paperforge.json` top-level vs `vault_config` formats. Include automatic legacy migration and ensure plugin settings no longer create a second runtime truth.

This phase does NOT cover canonical index, lifecycle state, health diagnostics, surface convergence, or AI context packs — those are Phases 23-26.

</domain>

<decisions>
## Implementation Decisions

### Paper Workspace File Composition

- **D-01:** Paper workspace root directory: `Literature/<domain>/<key> - <Short Title>/`
- **D-02:** Main entry file: `<key> - <Short Title>.md` — in workspace root, Quick Switcher-friendly, unique, readable.
- **D-03:** `fulltext.md` lives in workspace root as the user-facing entry copy. System OCR area (`PaperForge/ocr/<key>/`) retains the authoritative OCR asset. Canonical index records both paths.
- **D-04:** Workspace layout: main files in root + `ai/` subdirectory only.
  - `<key> - <Title>.md` (main card)
  - `fulltext.md` (user-facing fulltext)
  - `deep-reading.md` (deep reading content)
  - `ai/` (pf-paper atom level AI insights, open content structure)
- **D-05:** No extra subdirectories (`reading/`, `assets/`) in workspace for now. Canvas and other reading formats stay in root when created.

### paperforge.json Schema

- **D-06:** `vault_config` block becomes the canonical format. All fields go under `vault_config`.
- **D-07:** New installs write only `vault_config` — no top-level keys.
- **D-08:** Python reads both top-level and `vault_config` block for backward compatibility. `vault_config` takes precedence.
- **D-09:** Add `schema_version` field to `paperforge.json` for future migration detection.
- **D-10:** Plugin reads `paperforge.json` directly. Plugin `DEFAULT_SETTINGS` is removed for path/config fields. Plugin settings page becomes a viewer/editor for `paperforge.json` values.

### Legacy Config Migration

- **D-11:** Auto-migration from top-level keys to `vault_config` block happens during `paperforge sync`.
- **D-12:** Old `paperforge.json` is backed up as `paperforge.json.bak` before migration.
- **D-13:** `paperforge doctor` detects stale top-level config and reports migration status.

### Plugin Config Truth

- **D-14:** Plugin no longer maintains independent `DEFAULT_SETTINGS` for path/config fields. It reads `paperforge.json` at startup.
- **D-15:** Plugin `data.json` no longer stores `system_dir`, `resources_dir`, `literature_dir`, `control_dir`, `base_dir` — those come from `paperforge.json`.
- **D-16:** Plugin Setup/Config tab remains but acts as a UI for viewing/editing `paperforge.json` values.
- **D-17:** Plugin-initiated config saves write directly to `paperforge.json` (not plugin `data.json`).

### the agent's Discretion

- Exact `schema_version` format and increment rules.
- Backup filename format (`.bak` suffixed by timestamp or not).
- Plugin UI layout for editing `paperforge.json` values.
- Whether to remove legacy fields from plugin `data.json` or just ignore them.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements

- `.planning/ROADMAP.md` §Phase 22 — Goal, success criteria, CONF-01..04 requirements
- `.planning/REQUIREMENTS.md` CONF-01..04 — Configuration truth requirements
- `.planning/research/SUMMARY.md` §Phase 1 recommendations — Config truth architecture
- `.planning/research/MILESTONE-RESEARCH-LOCK.md` — Paper workspace and config truth locked research

### Source code

- `paperforge/config.py` — Current config resolution: DEFAULT_CONFIG (line 48), ENV_KEYS (line 59), `load_vault_config()` (line 149), `paperforge_paths()` (line 213). **Primary file to modify.**
- `paperforge/plugin/main.js` — Plugin DEFAULT_SETTINGS (line 145), `loadSettings()` (line 1037), `saveSettings()` (line 1041), `PaperForgeSettingTab` (line 446). **Plugin config truth to refactor.**
- `paperforge/setup_wizard.py` — Where `vault_config` block is written during headless setup (line 1829, line 2035).
- `paperforge/worker/_utils.py` §pipeline_paths (line 241) — Path construction that feeds from config.
- `paperforge/cli.py` — CLI config loading (line 338), `_cmd_paths` (line 453).
- `paperforge/worker/status.py` — doctor checks that validate config (line 191).
- `paperforge/pdf_resolver.py` — PDF resolution that may depend on path config.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `paperforge/config.py` `load_vault_config()` — Already supports merging from vault_config block + top-level keys + env + overrides. Just needs `schema_version` and plugin read path.
- `paperforge/plugin/main.js` `PaperForgeSettingTab` — Already renders all config fields. Needs to be refactored to read/write `paperforge.json` instead of plugin data.
- `paperforge/worker/status.py` `run_doctor()` — Already checks `paperforge.json` existence. Can be extended with migration detection.

### Established Patterns

- Python config resolution uses a locked 5-level precedence chain: defaults → paperforge.json vault_config → paperforge.json top-level → env vars → explicit overrides.
- Plugin settings use Obsidian's `PluginSettingTab` API with `loadData()`/`saveData()` and debounced writes.
- Setup wizard writes `vault_config` block. CLI reads both formats compatibly.

### Integration Points

- `paperforge/config.py:48-56` — `DEFAULT_CONFIG` is the Python truth. Needs `schema_version`.
- `paperforge/plugin/main.js:145-156` — `DEFAULT_SETTINGS` to be removed for path fields.
- `paperforge/config.py:178-190` — `read_paperforge_json()` and merge logic. Where migration from top-level to vault_config happens.
- Plugin `PaperForgeSettingTab.display()` — Where path fields render. Needs to switch to reading `paperforge.json` file.
- `paperforge/setup_wizard.py:2013-2038` — Where `paperforge.json` is written. Already writes `vault_config` block.
</code_context>

<specifics>
## Specific Ideas

- Auto-migration during `paperforge sync` should be silent and safe — users shouldn't notice.
- Plugin reading `paperforge.json` needs to handle the case where the file doesn't exist yet (fresh install).
- Plugin should still cache values in memory for UI responsiveness, but the cache is populated from `paperforge.json` at startup, not from `DEFAULT_SETTINGS`.
- The `paperforge doctor` migration warning should include the backup path so users know where their old config went.

</specifics>

<deferred>

## Deferred Ideas

- Canonical asset index schema — Phase 23
- Paper workspace `ai/` directory content structure — determined later, currently open

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-configuration-truth-compatibility*
*Context gathered: 2026-05-03*
