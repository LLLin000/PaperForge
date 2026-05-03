# Architecture Patterns

**Domain:** PaperForge v1.6 literature asset foundation integration
**Researched:** 2026-05-03

## Recommended Architecture

Evolve the existing `formal-library.json` into the canonical asset index rather than introducing a second competing index. The current code already has a single write point for the file in `paperforge/worker/sync.py` (`run_index_refresh`) and a stable path contract in `_utils.pipeline_paths()["index"]`. Reusing that artifact preserves the current layout, minimizes migration risk, and avoids a new “which index is truth?” problem.

The target model should be:

```text
paperforge.json / vault_config                    -> configuration truth
library-records/*.md                              -> user intent truth
ocr/<key>/meta.json + fulltext/images/json        -> OCR asset truth
Literature/<domain>/<key> - <title>.md            -> formal note + deep-reading truth
indexes/formal-library.json                       -> canonical derived read model
plugin dashboard / status / health / maturity UI  -> thin-shell views over canonical index
```

This keeps PaperForge local-first and file-based, but makes one important shift: lifecycle, health, readiness, and maturity are no longer recomputed ad hoc by each surface. They are derived once in Python and published through the canonical index.

## Architecture Diagram

```text
                   +----------------------+
                   |  paperforge.json     |
                   |  vault_config        |
                   +----------+-----------+
                              |
                              v
                    paperforge.config.py
                              |
         +--------------------+--------------------+
         |                    |                    |
         v                    v                    v
 selection-sync         ocr worker          deep-reading sync
 (user intent mirror)   (asset producer)    (agent-result sync)
         |                    |                    |
         +--------------------+--------------------+
                              |
                              v
              NEW: asset index builder / state resolver
                              |
                              v
     <system_dir>/PaperForge/indexes/formal-library.json
                              |
              +---------------+----------------+
              |                                |
              v                                v
     CLI JSON views/status              Obsidian plugin dashboard
     doctor/repair summaries            Base-support mirror fields
```

## Decision: Evolve `formal-library.json`, do not add a second canonical index

### Recommendation

Keep the path:

`<system_dir>/PaperForge/indexes/formal-library.json`

but change its schema from a bare list of note rows to a versioned envelope:

```json
{
  "schema_version": "2",
  "generated_at": "2026-05-03T12:00:00Z",
  "config_snapshot": {
    "system_dir": "99_System",
    "resources_dir": "03_Resources",
    "literature_dir": "Literature",
    "control_dir": "LiteratureControl",
    "base_dir": "05_Bases"
  },
  "summary": {
    "total_assets": 0,
    "health": {},
    "maturity": {}
  },
  "items": [
    {
      "zotero_key": "ABCDEFG",
      "domain": "骨科",
      "title": "...",
      "intent": { "analyze": false, "do_ocr": false },
      "assets": { "pdf": {}, "ocr": {}, "note": {}, "figures": {} },
      "state": { "lifecycle": "ocr_ready", "ai_ready": false },
      "health": { "library": "healthy", "pdf": "ok", "ocr": "pending" },
      "maturity": { "score": 35, "level": 2, "next_step": "run_ocr" },
      "paths": { "record": "...", "note": "...", "ocr_meta": "..." }
    }
  ]
}
```

### Why not a new file?

| Option | Verdict | Why |
|---|---|---|
| Add `asset-index.json` beside `formal-library.json` | Reject | Duplicates responsibility and creates migration drift immediately |
| Rename `formal-library.json` to a new filename | Reject for v1.6 | Touches path contracts and upgrade logic without enough payoff |
| Evolve `formal-library.json` in place | Accept | Lowest-risk change, existing path already centralized |

### Migration rule

Add one tolerant reader in Python that accepts both:
- legacy list format
- new envelope format with `items`

Writers should emit only the new envelope after v1.6 migration.

## Data Ownership Boundaries

### 1. Configuration truth

**Authoritative source:** `paperforge.json` + `vault_config`

**Owner:** `paperforge/config.py`

**Rule:** plugin settings are not runtime truth. They are only a UI cache/draft until written back through Python.

Implication:
- `paperforge/plugin/main.js` should stop owning independent defaults like `System`, `Resources`, `Notes`, `Index_Cards`, `Base`.
- plugin should load resolved config from Python or from `paperforge.json`, then persist only as a mirror.
- any config-changing UI should write via setup/config command flow, not invent JS-only state.

### 2. User intent truth

**Authoritative source:** `library-records/<domain>/<key>.md` frontmatter

**User-owned fields:**
- `analyze`
- `do_ocr`
- future manual workflow flags

**Machine-mirrored fields:**
- `has_pdf`
- `pdf_path`
- `ocr_status`
- `deep_reading_status`
- `fulltext_md_path`
- future `asset_state`, `library_health`, `maturity_score`, `next_step`

Rule: users may edit intent fields; workers may overwrite mirrored fields.

### 3. OCR asset truth

**Authoritative source:**
- `ocr/<key>/meta.json`
- `ocr/<key>/fulltext.md`
- `ocr/<key>/json/result.json`
- `ocr/<key>/images/*`

**Owner:** `paperforge/worker/ocr.py`

Rule: no other component should invent OCR completion state without validating these files.

### 4. Deep-reading truth

**Authoritative source:** formal note content under `## 🔍 精读`

**Owner:** agent output + `has_deep_reading_content()` / `run_deep_reading()`

Rule: `deep_reading_status` is derived from actual note content, not from the plugin.

### 5. Canonical derived truth

**Authoritative source for lifecycle/health/maturity/dashboard:** `formal-library.json`

**Owner:** new asset-index builder in Python

Rule: plugin, `status`, health UI, and future context pack features read from this index instead of recomputing from filesystem independently.

## Recommended New/Modified Artifacts

### New Python modules

| Artifact | Type | Responsibility |
|---|---|---|
| `paperforge/worker/asset_index.py` | New | Read all source artifacts, derive canonical item rows, write `formal-library.json` |
| `paperforge/worker/asset_state.py` | New | Pure lifecycle/readiness/health/maturity derivation functions |
| `paperforge/worker/context_pack.py` | New | Build per-paper/per-collection AI context packs from canonical items |
| `paperforge/commands/config.py` | New | JSON get/set surface for plugin config sync |
| `paperforge/commands/context_pack.py` | New | CLI wrapper for ask-this-paper / ask-this-collection / copy-context-pack |

### Modified Python modules

| Artifact | Change |
|---|---|
| `paperforge/config.py` | Make resolved config the single runtime truth; expose stable JSON-serializable config payload |
| `paperforge/worker/sync.py` | Split note-writing from index-building; call asset index refresh after selection/index changes |
| `paperforge/worker/ocr.py` | After each touched key, refresh canonical index rows for those keys |
| `paperforge/worker/deep_reading.py` | Refresh canonical index after syncing deep-reading status |
| `paperforge/worker/status.py` | Read summary counts from canonical index instead of recounting raw files where possible |
| `paperforge/worker/repair.py` | Repair source artifacts first, then refresh canonical index |
| `paperforge/worker/base_views.py` | Add derived display columns/filters fed by mirrored fields from canonical index |
| `paperforge/setup_wizard.py` | Stop writing duplicated top-level path fields unless needed for backward compatibility; prefer `vault_config` |
| `paperforge/plugin/main.js` | Read config/dashboard data from Python, never own lifecycle logic |

### Modified on-disk artifacts

| Artifact | Status | Notes |
|---|---|---|
| `<system_dir>/PaperForge/indexes/formal-library.json` | Evolve | Canonical index envelope |
| `library-records/*.md` | Extend | Add derived mirror fields for Base/UI filtering |
| `paperforge.json` | Tighten | Single config truth; preserve legacy top-level keys only as compatibility shim |

### New on-disk artifacts

| Artifact | Purpose |
|---|---|
| `<system_dir>/PaperForge/indexes/context-packs/<key>.md` | Cached per-paper AI context pack |
| `<system_dir>/PaperForge/indexes/context-packs/collections/<slug>.md` | Cached per-collection AI context pack |
| `<system_dir>/PaperForge/indexes/health-report.json` | Optional summarized health snapshot for dashboard and diagnostics |

## State Model

The new model should explicitly separate intent, assets, and derived state.

### Intent layer

From `library-record` frontmatter:

```text
analyze
do_ocr
```

This is what the user wants.

### Asset layer

Observed from files:

```text
export present?
pdf resolvable?
ocr meta present?
ocr payload complete?
formal note present?
deep-reading content present?
figure assets present?
```

This is what actually exists.

### Derived state layer

Computed in Python only:

```text
imported
indexed
pdf_ready
ocr_requested
ocr_processing
fulltext_ready
figure_ready
deep_read_ready
deep_read_done
ai_context_ready
```

Recommended item schema section:

```json
"state": {
  "lifecycle": "fulltext_ready",
  "readiness": {
    "pdf": true,
    "ocr": true,
    "deep_read": false,
    "ai_context": false
  },
  "next_actions": ["generate_context_pack", "run_pf_deep"]
}
```

## Read/Write Flow

### Worker write flow

```text
Zotero export change
  -> run_selection_sync()
  -> update library-records (intent + mirrors)
  -> refresh_asset_index(keys=changed)

OCR job change
  -> run_ocr()
  -> update meta.json/fulltext/assets
  -> refresh_asset_index(keys=touched)

Deep-reading state change
  -> run_deep_reading()
  -> sync deep_reading_status mirror
  -> refresh_asset_index(keys=touched)

Repair change
  -> run_repair()
  -> fix source artifacts
  -> refresh_asset_index(keys=fixed)
```

### Plugin read/write flow

```text
Plugin action button
  -> spawn `python -m paperforge <command>`
  -> command mutates source artifacts
  -> command refreshes canonical index
  -> plugin re-reads JSON summary/query output

Plugin dashboard load
  -> spawn `python -m paperforge status --json` for summary
  -> spawn `python -m paperforge context-pack/index query --json` for lists/detail
  -> render only; no lifecycle recomputation in JS
```

### Critical rule

The plugin should never determine:
- whether OCR is truly complete
- whether a paper is AI-ready
- whether health is red/yellow/green
- what the next step should be

Those are Python-derived fields.

## Integration Points in Existing Code

### `paperforge/config.py`

Current strength: already centralizes precedence. Current problem: plugin defaults drift from Python defaults and setup writes both top-level keys and `vault_config`.

Recommendation:
- keep `load_vault_config()` as the only resolver
- add a JSON export helper used by plugin
- prefer nested `vault_config` as canonical
- keep top-level path keys only as compatibility read support, not required write support

### `paperforge/worker/sync.py`

Current role is overloaded:
1. ingest export rows
2. write library-records
3. write formal notes
4. write `formal-library.json`

Recommendation:
- leave `run_selection_sync()` focused on control records
- leave `run_index_refresh()` focused on formal notes
- move canonical index assembly into `asset_index.py`
- have both call `refresh_asset_index()` rather than hand-building `index_rows`

This is the cleanest way to integrate new lifecycle/health fields without making `sync.py` larger.

### `paperforge/worker/ocr.py`

Current role is already the source of OCR truth via `meta.json` and validation. Keep it that way.

Recommendation:
- do not push health logic into the plugin
- after status transitions, refresh canonical rows for touched keys
- expose validated OCR health in index as derived fields, not ad hoc status strings scattered across surfaces

### `paperforge/worker/deep_reading.py`

Current role is status synchronization, which fits v1.6 well.

Recommendation:
- continue deriving deep-read completion from note content
- publish the result into canonical index and mirrored record fields
- let maturity scoring depend on this derived state

### `paperforge/worker/status.py`

Current role manually counts files and scans frontmatter.

Recommendation:
- keep doctor-style filesystem checks in place
- move dashboard/status summaries to canonical index summary where possible
- use raw scans only as fallback if index missing/corrupt

This gives one consistent count across CLI and plugin.

### `paperforge/worker/repair.py`

Current role already handles state divergence.

Recommendation:
- extend it to compare source artifacts vs canonical index freshness
- never repair the index directly; repair sources, then rebuild index

### `paperforge/worker/base_views.py`

Current Base strategy is still good. Do not replace Bases with a new system.

Recommendation:
- add columns like `asset_state`, `library_health`, `maturity_level`, `next_step`
- continue filtering on `analyze`, `do_ocr`, `ocr_status`, `deep_reading_status`
- derive these extra display fields from canonical index and mirror them back into library-record frontmatter during refresh

This preserves current user workflow while making the dashboard and Bases agree.

### `paperforge/plugin/main.js`

Current plugin is correctly thin in command execution, but too independent in configuration and too limited in dashboard data.

Recommendation:
- keep CommonJS and the current shell approach; do not do a front-end rewrite
- add a config fetch path from Python
- add dashboard JSON fetches backed by canonical index
- keep all writes as CLI subprocesses
- keep settings as UI cache only, not truth

## Patterns to Follow

### Pattern 1: Canonical read model over file truths
**What:** derive one authoritative JSON read model from multiple file-backed truths.
**When:** whenever multiple surfaces need the same counts, health, lifecycle, or readiness logic.
**Example:**

```python
item = build_asset_item(
    export_row=export_row,
    record=parse_library_record(record_path),
    ocr_meta=load_meta(meta_path),
    note_state=inspect_note(note_path),
)
```

### Pattern 2: User-intent fields stay editable, derived fields stay overwriteable
**What:** keep manual controls and machine mirrors separate in the same markdown record.
**When:** preserving current Base workflow without losing canonical derivation.
**Example:**

```yaml
analyze: true          # user-owned
do_ocr: true           # user-owned
asset_state: "ocr_ready"      # machine-owned mirror
library_health: "warning"     # machine-owned mirror
maturity_score: 55            # machine-owned mirror
```

### Pattern 3: Thin-shell plugin, thick Python semantics
**What:** JS renders and triggers commands; Python decides meaning.
**When:** any dashboard, health, maturity, or AI-ready feature.
**Example:**

```text
plugin -> python -m paperforge status --json -> render cards
plugin -> python -m paperforge context-pack PAPER123 --json -> render/copy
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Second lifecycle implementation in the plugin
**What:** JS infers OCR/deep-read/health from file presence or cached settings.
**Why bad:** guaranteed drift from CLI and workers.
**Instead:** plugin reads Python-produced JSON only.

### Anti-Pattern 2: Treating `formal-library.json` as user-editable data
**What:** manual edits or plugin patch writes into canonical index.
**Why bad:** index becomes a source instead of a read model.
**Instead:** source artifacts change first; index is regenerated.

### Anti-Pattern 3: Making `library-record` the source of all truth
**What:** stuffing every derived health/lifecycle decision into frontmatter and reading only that.
**Why bad:** repeats current divergence problems.
**Instead:** frontmatter stores intent plus mirrors; source truths remain separate.

### Anti-Pattern 4: Creating a greenfield asset database layer
**What:** SQLite/daemon/service rewrite for v1.6.
**Why bad:** violates local-first simplicity and existing file-based contract.
**Instead:** improve the current JSON + markdown architecture.

## Scalability Considerations

| Concern | At 100 users/papers | At 10K papers | At 1M papers |
|---|---|---|---|
| Index rebuild cost | Full rebuild acceptable | Prefer keyed/incremental refresh | Would need sharding or DB, out of scope |
| Plugin dashboard load | Read whole index fine | Add filtered JSON queries and summary endpoints | Full file read impractical |
| Base mirrors | Direct frontmatter update fine | Batch writes should be keyed and minimal | Too many markdown rewrites |
| Context packs | On-demand generation fine | Cache per paper/collection | Need streaming/chunking |

For v1.6, optimize for incremental per-key refresh, not a new database.

## Suggested Build Order

### Phase 1: Configuration truth hardening
- Normalize plugin defaults to Python defaults
- Add config JSON read surface
- Make `vault_config` the canonical write target
- Verify plugin, CLI, setup, and workers resolve identical paths

### Phase 2: Canonical index builder
- Add `asset_index.py`
- Evolve `formal-library.json` schema
- Add tolerant legacy reader
- Make `run_index_refresh()` delegate index writing here

### Phase 3: Unified state + health derivation
- Add lifecycle/readiness/health/maturity pure functions in `asset_state.py`
- Feed from library-records, OCR meta, formal notes
- Mirror selected display fields back into library-record frontmatter

### Phase 4: Status/repair/dashboard convergence
- Make `status --json` read canonical summary
- Make `repair` rebuild index after fixes
- Update plugin dashboard to read canonical summaries/query endpoints

### Phase 5: Maturity scoring + next-step recommendations
- Add scoring rules to canonical items
- Surface next-step guidance in plugin and Base views

### Phase 6: AI context packs
- Generate per-paper and per-collection context packs from canonical items
- Store pack paths/readiness in index
- Keep pack bodies outside the main index to avoid bloat

## Practical Field Additions

Recommended mirrored `library-record` fields for Bases/UI:

```yaml
asset_state: "fulltext_ready"
pdf_health: "ok"
ocr_health: "warning"
template_health: "ok"
library_health: "warning"
maturity_score: 62
maturity_level: 3
next_step: "run_pf_deep"
context_pack_ready: false
```

Recommended canonical index sections per item:

```json
"intent": {},
"assets": {},
"state": {},
"health": {},
"maturity": {},
"recommendations": {},
"paths": {}
```

## Sources

- Internal code inspection: `paperforge/config.py` — config precedence and path resolution
- Internal code inspection: `paperforge/worker/_utils.py` — existing `formal-library.json` path contract
- Internal code inspection: `paperforge/worker/sync.py` — current library-record/note/index write flow
- Internal code inspection: `paperforge/worker/ocr.py` — OCR truth and validation flow
- Internal code inspection: `paperforge/worker/deep_reading.py` — deep-reading state sync
- Internal code inspection: `paperforge/worker/status.py` — current summary/dashboard JSON producer
- Internal code inspection: `paperforge/worker/repair.py` — divergence repair model
- Internal code inspection: `paperforge/plugin/main.js` — current plugin thin-shell pattern and config drift risk
