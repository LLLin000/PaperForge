# Phase 26: Traceable AI Context Packs - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Provide CLI commands and plugin entry points that output per-paper and per-collection canonical index entries in JSON format for AI consumption. `ai/` directory in paper workspace is designated for free-form AI conversation records and notes. No separate "context pack" format is designed — the canonical index entry IS the AI entry point.

Does NOT cover LLMWiki concept network (v1.7), evidence extraction frameworks (v2.0), or figure gallery.

Includes: migration of existing flat literature notes (`Literature/<domain>/<key> - <Title>.md`) into the new paper workspace structure (`Literature/<domain>/<key> - <Title>/<key> - <Title>.md` + `deep-reading.md`) without losing the `## 🔍 精读` deep reading content.

</domain>

<decisions>
## Implementation Decisions

### Core principle
- **D-01:** Canonical index entry IS the AI context. There is no separate "context pack" format.
- **D-02:** AI reads the index entry JSON + referenced assets (fulltext, figures, notes) directly.

### ai/ directory
- **D-03:** `ai/` in paper workspace stores free-form AI conversation records, notes, and insights. No fixed file structure.
- **D-04:** Only constraint: content should be reusable (atom-level insights, not raw token dumps).

### CLI command
- **D-05:** New `paperforge context` command with subcommands:
  - `paperforge context <key>` — single paper canonical entry
  - `paperforge context --domain <domain>` — all entries in a domain
  - `paperforge context --collection <path>` — entries matching a collection path
  - `paperforge context --all` — full canonical index
- **D-06:** Output is JSON. Default to individual entry, array for multi-entry modes.

### Plugin integration
- **D-07:** Plugin adds "Copy Context" button for the current paper (copies canonical index entry JSON).
- **D-08:** Plugin adds "Copy Collection Context" button (from Base view, copies filtered entries).

### Provenance
- **D-09:** Provenance is inherent: canonical index entries already have `paper_root`, `main_note_path`, `fulltext_path`, `ocr_path`, `note_path`. No additional provenance layer needed.

### Dependencies
- **D-10:** No new dependencies. Everything uses existing `asset_index.py` index reading.

### Migration
- **D-11:** Existing flat `Literature/<domain>/<key> - <Title>.md` files are migrated to paper workspace on first sync.
- **D-12:** Migration is copy-not-move: original file is copied into workspace dir as the main note, original is preserved.
- **D-13:** `## 🔍 精读` section is extracted from the main note and written into a separate `deep-reading.md` file.
- **D-14:** Canonical index paths are updated to point to the new workspace structure.
- **D-15:** Migration is idempotent: already-migrated papers are skipped.

### the agent's Discretion
- Output format details (indentation, field ordering)
- Plugin button placement (context menu vs dashboard card)
- Whether `--domain` filter is exact match or prefix match

</decisions>

<canonical_refs>
## Canonical References

### Phase scope and requirements
- `.planning/ROADMAP.md` §Phase 26 — Goal: "explainable paper and collection context packs"
- `.planning/REQUIREMENTS.md` — AIC-02, AIC-03, AIC-04
- `.planning/phases/22-configuration-truth-compatibility/22-CONTEXT.md` — D-04 ai/ in workspace

### Source code
- `paperforge/worker/asset_index.py` — build_envelope, build_index, refresh_index_entry, get_index_path
- `paperforge/plugin/main.js` — Dashboard, ACTIONS, _runAction
- `paperforge/cli.py` — CLI command registration pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `paperforge/worker/asset_index.py` `get_index_path()` + `build_envelope()` — index read/write
- `paperforge/worker/asset_state.py` — lifecycle/health/maturity already computed per entry
- `paperforge/plugin/main.js` ACTIONS array — pattern for adding new Quick Actions

### Established Patterns
- CLI commands: separate file in `paperforge/commands/` + argparse subparser in `cli.py`
- Plugin actions: defined in ACTIONS array, executed via _runAction spawning python subprocess
- Data format: canonical index JSON is the standard

### Integration Points
- `paperforge/cli.py` — Add "context" subcommand parser
- `paperforge/commands/` — New `context.py` module
- `paperforge/plugin/main.js` — New "Copy Context" and "Copy Collection Context" actions
- `paperforge/worker/asset_index.py` — get_index_path, read_index

</code_context>

<specifics>
## Specific Ideas

- `paperforge context <key>` should be the primary AI integration command. Agent skills can call it directly.
- "Copy Context" button should work from any paper note (right-click or command palette).
- Collection-level context from Base views: user selects a Base view row, copies context for all visible papers.

</specifics>

<deferred>
None — discussion stayed within phase scope
</deferred>

---

*Phase: 26-traceable-ai-context-packs*
*Context gathered: 2026-05-04*
