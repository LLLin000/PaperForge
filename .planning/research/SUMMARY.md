# Project Research Summary

**Project:** PaperForge v1.8 — AI Discussion Recording & Deep-Reading Dashboard
**Domain:** Brownfield Obsidian plugin — extending mode-based dashboard with AI discussion capture
**Researched:** 2026-05-06
**Confidence:** HIGH

## Executive Summary

PaperForge v1.8 adds two tightly-coupled capabilities to the existing PaperForge Obsidian plugin: **(1) AI discussion recording** that captures `/pf-paper` and `/pf-deep` conversations into structured `ai/discussion.json` and human-readable `ai/discussion.md` files within each paper's workspace directory; and **(2) a 4th dashboard mode** (`deep-reading`) activated automatically when the user opens a `deep-reading.md` file, showing Pass 1/2/3 completion status, Pass 1 summary, and recent AI Q&A history.

The recommended approach is **thin-shell extension** — zero new dependencies, zero new CLI commands. The Obsidian plugin (CommonJS, single `main.js` file) gains one new mode renderer and one mode detection branch. A new Python module (`paperforge/worker/discussion.py`) handles writing discussion files at the end of Agent sessions. The canonical index (`formal-library.json`) serves as the bridge — JS reads pre-computed lifecycle/health/maturity from it, while `discussion.json` (vault-internal) should use `vault.adapter.read()` for cache consistency, **not** `fs.readFileSync()` as the older index pattern does.

The three key risks are: (1) mode detection ordering — `deep-reading.md` carries the same `zotero_key` frontmatter as the formal note and will incorrectly trigger per-paper mode unless the `deep-reading.md` filename check comes *first*; (2) encoding corruption on Windows with CJK locales — Chinese Q&A content written by Python must use explicit `encoding='utf-8'` and Node.js must read with matching encoding to avoid mojibake; and (3) `discussion.json` must include `schema_version` from day one to prevent silent data loss on format changes. All three are preventable with the right discipline in Phase 1 and Phase 2.

## Key Findings

### Recommended Stack

v1.8 is purely additive to the existing v1.6–v1.7 stack. **No new npm packages, no new Python packages.** The plugin remains a single CommonJS file (`main.js`, currently ~2067 lines) with CSS in `styles.css` (~1325 lines). Python gains one new module (`discussion.py`) using only stdlib (`json`, `pathlib`, `datetime`, `tempfile`, `os`).

**Core technologies (unchanged):**
- **Obsidian CommonJS plugin** (`main.js`, no bundler): Dashboard/settings/commands UI — pure Obsidian API, no build step
- **Python 3.10+** (existing CLI): Single owner of business logic, templates, schema; extends naturally to discussion recording
- **Filesystem JSON** (`formal-library.json`, `discussion.json`): Contract between Python and JS; vault-native, git-trackable, backup-friendly
- **Filesystem Markdown** (`discussion.md`): Human-readable companion, Obsidian-editable, wikilink-compatible

**New file formats for v1.8:**
- `ai/discussion.json` — structured AI Q&A record with `schema_version`, `paper_key`, `sessions[]` array containing `session_id`, `agent`, `started`, and `qa_pairs[]`
- `ai/discussion.md` — human-readable Q&A log with session-grouped `##` headings, `**问题:**`/`**解答:**` markers, timestamp metadata

**Key "what NOT to add" decisions (all researchers agree):**
- No npm packages (React, Vue, chart libs) — breaks single-file deployment
- No database (SQLite, IndexedDB) — discussions belong to the paper workspace, must be vault-native
- No Python schema libraries (Pydantic, jsonschema) — overkill for flat Q&A list
- No second plugin file — import resolution is fragile in Obsidian
- No new CLI command (`paperforge discuss`) — recording happens inside Agent sessions

### Expected Features

**Must have (table stakes — v1.8 launch):**
- AI Discussion Recorder: Writes `discussion.md` + `discussion.json` when `/pf-paper` or `/pf-deep` completes — researchers expect past AI conversations next to the paper, not scattered in browser tabs
- Deep-Reading Dashboard Mode: Plugin detects `deep-reading.md` as active file, switches to dedicated mode showing Pass 1/2/3 status + AI Q&A history — users want at-a-glance reading progress without scrolling
- Jump-to-Deep-Reading Button: Contextual button on per-paper dashboard card that opens deep-reading.md — bridges paper lifecycle view to reading content
- Version Number Display Fix: Restore the `_versionBadge` — users need to confirm version for issue reporting
- "ai" UI Row Removal: Remove the meaningless row — erodes trust in dashboard accuracy

**Should have (v1.8.x follow-up, deferrable):**
- Discussion session merging (append, not overwrite, on repeated `/pf-paper` for same paper)
- Session metadata in discussion.json (model, duration, agent type)
- Pass completion percentage calculation

**Future consideration (v2+):**
- Cross-library discussion search (rely on Obsidian built-in search)
- Discussion export to AI context packs
- Deep-reading maturity integration into maturity gauge

**Anti-features explicitly rejected:**
- Auto-recording all agent conversations (creates noise, violates worker/agent boundary)
- Full chat transcription in markdown (unstructured, duplicates agent's internal logs)
- Deep-reading dashboard as replacement for deep-reading.md (dashboard is index/summary view only)
- Real-time dashboard updates during deep-reading (agent executes outside plugin; refresh on active-leaf-change is sufficient)
- Discussion search across all papers (Obsidian's built-in search already handles this)

### Architecture Approach

The architecture extends PaperForge's existing **thin-shell plugin pattern**: Python owns all business logic and writes structured data to the filesystem; the Obsidian JS plugin reads that data and renders Pure CSS/DOM components. No business logic is duplicated in JS.

The key architectural addition is a **4th mode dispatch** in the existing `_detectAndSwitch()` → `_switchMode()` → `case 'mode': renderX()` pattern. The mode detection hierarchy (in strict order) becomes:

```
1. no active file        → 'global'      (existing)
2. .base file            → 'collection'   (existing)
3. deep-reading.md       → 'deep-reading' (NEW — MUST precede zotero_key check)
4. .md with zotero_key   → 'paper'       (existing)
5. fallback              → 'global'      (existing)
```

**Major components affected:**
1. **`_detectAndSwitch()` + `_switchMode()`** — Mode detection extended with deep-reading.md filename check; must be checked *before* zotero_key frontmatter to prevent hijacking by per-paper mode
2. **`_renderDeepReadingMode()` (NEW)** — Dedicated render method consuming data from formal-library.json (lifecycle/health/maturity), deep-reading.md (Pass 1 summary), and ai/discussion.json (AI Q&A history)
3. **`_renderPaperMode()` extension** — Adds "Jump to Deep Reading" contextual button when `deep_reading_path` exists
4. **`discussion.py` (NEW Python module)** — `record_discussion()` writes both discussion.md and discussion.json; `load_discussion_json()` reads existing record; `append_discussion()` appends new Q&A pairs atomically
5. **`asset_index.py` build_envelope()** — Adds `paperforge_version` field for the version badge fix

**Key data flow:**
```
User runs /pf-deep → ld_deep.py generates scaffold → Agent completes session
    → discussion_recorder.py writes ai/discussion.{md,json}
User opens deep-reading.md → _detectAndSwitch() detects it → _renderDeepReadingMode()
    → reads formal-library.json (status badges) + deep-reading.md (Pass 1 summary) + ai/discussion.json (Q&A history)
```

### Critical Pitfalls

All researchers independently flagged these — they represent consensus on highest-risk items:

1. **Mode detection ordering regression** — `deep-reading.md` carries the same `zotero_key` frontmatter as the formal note. If the filename check isn't placed FIRST in the `.md` handler (before the `zotero_key` check), the dashboard enters per-paper mode instead of deep-reading mode. **Fix:** Insert `if (activeFile.basename === 'deep-reading')` as the first branch inside the `.md` handler.

2. **Encoding corruption on Windows CJK systems** — Python may write GBK-encoded files while Node.js reads as UTF-8, producing mojibake for Chinese Q&A content. This is a well-documented Obsidian + Windows + Chinese locale problem. **Fix:** Python must use `open(path, 'w', encoding='utf-8')` explicitly; JS reads must match. Use `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1` environment variables for child processes.

3. **`discussion.json` schema version missing** — Shipping without `schema_version` repeats the `formal-library.json` v1→v2 migration pain from v1.6/v1.7. Every format change becomes a breaking change. **Fix:** Include `"schema_version": "1"` in the envelope from day one. Always use object envelope, never top-level array.

4. **`btoa()` crash on Chinese filenames** — `window.btoa()` only supports Latin1 characters. If any path construction for `ai/` directory uses `btoa()` with Chinese paper titles, it throws `InvalidCharacterError`. **Fix:** Ban `btoa()` and `atob()` from the plugin. Use `Buffer.from(str, 'utf-8').toString('base64')` instead.

5. **`active-leaf-change` double-firing mode oscillation** — Obsidian fires this event twice during tab switches (old leaf blur + new leaf focus). The 300ms debounce can catch either, causing a visible flash of global mode between per-paper and deep-reading modes. **Fix:** Extract `_resolveModeForFile()` as a pure function; guard with identity check (same mode AND same file path = no-op); increase debounce to 500ms during transitions.

## Researcher Conflicts Resolved

The four researchers produced high-quality, mostly aligned outputs. However, two substantive conflicts emerged:

### Conflict 1: `discussion.json` schema shape

| Researcher | Schema Proposal |
|------------|----------------|
| **STACK.md** | Flat `history[]` array with `index`, `timestamp`, `question`, `answer`, `tags`, `agent_model`. Summary at top level with `total_qa`, `last_updated`, `top_tags`. |
| **FEATURES.md** | Nested `sessions[]` with `session_id`, `agent`, `started`, and `qa_pairs[]` array. Each QA pair has `question`, `answer`, `source`, `timestamp`. |
| **ARCHITECTURE.md** | Similar to FEATURES: `sessions[]` with `session_id`, `timestamp`, `model`, `command`, `summary`, `message_count`, `messages[]` with `role`/`content`. Separate `format_version` (not `schema_version`). |
| **PITFALLS.md** | Warns against bare array format, recommends `schema_version` envelope. |

**Resolution: Adopt the FEATURES.md sessions-based schema with these adjustments:**
- Use `schema_version: "1"` (from PITFALLS) — not `format_version`
- Keep session grouping (`sessions[]` → `qa_pairs[]`) — this is the right semantic model; a flat history loses the session boundary that `/pf-paper` vs `/pf-deep` invocations represent
- Use `timestamp` per QA pair (from FEATURES/STACK) — individual message timing matters for chronology
- Include `source` field as optional (from FEATURES) — traces answers back to specific Pass/section
- Add `model` at session level (from STACK/ARCHITECTURE) — the model is per-session, not per-QA
- Drop `message_count` (ARCHITECTURE proposes it but it's derivable from `qa_pairs.length`)

**Rationale:** Sessions are the natural grouping unit — each `/pf-paper` or `/pf-deep` invocation creates a new session. A flat history array loses this structure. The FEATURES.md schema best captures this while staying minimal.

### Conflict 2: How the plugin reads `discussion.json`

| Researcher | Recommendation |
|------------|----------------|
| **STACK.md** | `fs.readFileSync()` — same pattern as `formal-library.json` reading |
| **ARCHITECTURE.md** | `fs.readFileSync()` — "same pattern for discussion.json... from ai/ directory" |
| **PITFALLS.md** | **DO NOT use `fs.readFileSync()`** — use `vault.adapter.read()` because discussion.json is vault-internal (paper workspace), not system-directory. `fs.readFileSync` bypasses vault cache, misses modify events, risks encoding issues. |
| **FEATURES.md** | Doesn't specify read method, only says "reads discussion.json" |

**Resolution: PITFALLS.md is correct. Use `app.vault.adapter.read()` for discussion.json.**

**Rationale:** `fs.readFileSync()` is the correct pattern for `formal-library.json` because it lives in `<system_dir>/PaperForge/indexes/` — outside the Obsidian vault, invisible to vault cache. But `discussion.json` lives in `Literature/<domain>/<key> - <Title>/ai/` — inside the vault, visible in Obsidian's file explorer. Using `fs.readFileSync()` on vault-internal files:
- Bypasses Obsidian's metadata cache
- Prevents `modify` events from triggering dashboard refresh when Python writes new discussions
- Risks encoding mismatch on Windows CJK systems (vault adapter normalizes encoding)

The STACK.md and ARCHITECTURE.md researchers made a natural but incorrect assumption that the existing pattern extends unmodified. The PITFALLS researcher caught the distinction: system-directory files use `fs`, vault-internal files use `vault.adapter`.

## Implications for Roadmap

Based on dependency analysis across all four research files, the research converges on a **7-phase build order**. Phases 31a and 31b are quick-win bug fixes; Phase 32 establishes the mode detection infrastructure; Phase 33 builds the dashboard renderer; Phase 34 adds navigation; Phases 35-36 build the data pipeline end-to-end.

### Phase 31a: Fix Version Number Display

**Rationale:** Lowest risk, no dependencies. Single change in Python (`build_envelope()` adds `paperforge_version`) + single change in JS (`_fetchStats()` reads it). Quick win that improves perceived quality before new features ship.

**Delivers:** Version badge shows actual PaperForge version (e.g., `v1.8.0`) instead of `v—` placeholder.

**Addresses:** Bug Fix: Version Number (FEATURES.md)
**Avoids:** Pitfall 8 — version badge race condition (reads from plugin manifest as floor, Python index as ceiling)

**Stack elements used:** Python `__version__` from `paperforge/__init__.py`; JS `_cachedStats.version` read path.

### Phase 31b: Fix "ai" Row Bug

**Rationale:** Independent bug fix, but must be applied AFTER Phase 31a because understanding which UI element is "ai" requires reading current dashboard render paths. Grep all render paths before removal.

**Delivers:** Dashboard no longer shows a meaningless "ai" row.

**Addresses:** Bug Fix: Remove meaningless "ai" row (FEATURES.md)
**Avoids:** Pitfall 9 — "ai" row removal without checking all render paths

**Stack elements used:** `grep -rn 'ai' paperforge/plugin/main.js paperforge/plugin/styles.css` to identify source; surgical removal scoped to the specific render path.

### Phase 32: Add Deep-Reading Mode Detection

**Rationale:** This is the architectural foundation for everything in v1.8. Must be built before any deep-reading rendering can happen. Dependencies: nothing (pure JS change in `_detectAndSwitch()`).

**Delivers:** When user opens `Literature/<domain>/<key> - <Title>/deep-reading.md`, the plugin detects it and dispatches to `deep-reading` mode (even though the stub renderer is a placeholder until Phase 33).

**Implements:** Architecture component — `_detectAndSwitch()` extension, `_switchMode()` `case 'deep-reading'` branch.

**Avoids:** Pitfall 1 (mode detection ordering — check `basename === 'deep-reading'` BEFORE `zotero_key` frontmatter); Pitfall 5 (active-leaf-change double-fire — extract `_resolveModeForFile()` as pure function with identity guard); Pitfall 3 (filename-based heuristic — verify parent directory matches `{8-char key} - {slug}` pattern, not just basename).

**Key implementation constraint:**
```javascript
// Inside .md handler, BEFORE zotero_key check:
if (activeFile.basename === 'deep-reading') {
    const parentDir = activeFile.parent?.name || '';
    const match = parentDir.match(/^([A-Z0-9]{8})\s+-\s+(.+)$/);
    if (match) {
        this._currentPaperKey = match[1];
        this._currentPaperEntry = this._findEntry(match[1]);
        this._switchMode('deep-reading');
        return;
    }
}
// THEN: existing zotero_key check for per-paper mode
```

### Phase 33: Build `_renderDeepReadingMode()` Component

**Rationale:** Depends on Phase 32 (mode detection must route to this renderer). This is the largest single JS change. Must implement the sub-components (status bar, paper info header, Pass 1 summary, AI Q&A history placeholder, navigation) with empty-state handling for all data sources.

**Delivers:** Deep-reading dashboard that shows:
- Status bar with lifecycle/OCR/deep-reading/maturity badges
- Paper info header (title, authors, year, domain)
- Pass 1 summary extracted from deep-reading.md
- AI Q&A history section (placeholder until Phase 36; shows empty state)
- Navigation link back to the per-paper dashboard

**Implements:** Architecture component — `_renderDeepReadingMode()` with all sub-renderers.

**Avoids:** Pitfall 6 (empty discussion.json states — implement `_loadDiscussionData()` helper returning discriminated union for all 4 empty states: `no_ai_dir`, `not_found`, `empty`, `no_discussions`, `ok`); Pitfall 13 (CSS namespace collision — use `paperforge-deepreading-*` prefix, scope under `.paperforge-mode-deepreading` wrapper class); Pitfall 3 (anti-pattern: deep-reading dashboard replacing deep-reading.md — dashboard is index/summary only, never authoritative).

**CSS additions** (all scoped under `.paperforge-mode-deepreading`):
- `.paperforge-deep-reading-view` — root container (flex column, gap: 20px)
- `.paperforge-dr-status-bar` — Pass 1/2/3 completion indicator row
- `.paperforge-dr-pass-summary` — Pass 1 summary card
- `.paperforge-dr-discussion-card` — individual Q&A card
- `.paperforge-dr-discussion-list` — scrollable card container
- `.paperforge-dr-tag-chip` — tag pills (font-size: 10px, border-radius: 8px)
- `.paperforge-dr-empty` — empty state styling
- `.paperforge-dr-section-title` — section headers

### Phase 34: Add "Jump to Deep Reading" Button

**Rationale:** Depends on Phase 32 (deep-reading path resolution) and Phase 33 (deep-reading dashboard must exist for navigation to matter). Simple modification to `_renderPaperMode()`.

**Delivers:** On per-paper dashboard card, a "Jump to Deep Reading" button appears when `entry.deep_reading_path` is non-empty and `entry.deep_reading_status === 'done'`. Click navigates to `deep-reading.md`, which triggers Phase 32 mode detection.

**Implements:** Architecture component — integration point on per-paper dashboard contextual actions row.

**Avoids:** Pitfall 7 (Jump button assumes file exists — verify `getAbstractFileByPath()` before `openLinkText()`, show clear `Notice` on missing file); Anti-feature (dashboard replacing deep-reading.md — button opens the actual file, dashboard is a view layer).

**Condition to show button:** `entry.deep_reading_path && entry.deep_reading_status === 'done'` — don't show for papers that haven't had deep reading performed.

### Phase 35: AI Discussion Recorder (Python)

**Rationale:** Depends on nothing (standalone Python module). Can be built in parallel with Phases 32-34. Writes the data that Phase 36 will read. Must implement atomic writes to prevent corruption during concurrent access.

**Delivers:** `paperforge/worker/discussion.py` with:
- `record_discussion(key, vault, agent, qa_pairs)` — writes both `discussion.md` and `discussion.json`
- `load_discussion_json(key, vault)` — reads existing record
- `append_discussion(key, vault, qa_pair)` — appends to existing (read-modify-write atomic via tempfile + os.replace)

**Implements:** Architecture component — Python discussion recording module, integration with `/pf-paper` and `/pf-deep` Agent commands.

**Uses:** Existing stdlib only (`json`, `pathlib`, `datetime`, `tempfile`, `os`); same atomic write pattern as `asset_index.py`.

**Avoids:** Pitfall 3 (schema version missing — ship with `schema_version: "1"` in envelope); Pitfall 2 (encoding corruption — use `encoding='utf-8'` explicitly, set `PYTHONIOENCODING=utf-8` env var); Pitfall 4 (btoa on Chinese — path resolution uses zotero_key only, never writes slugified title paths); Pitfall 10 (.md vs .json inconsistency — define .json as canonical, .md as derived view); Pitfall 11 (tabs/newlines breaking Obsidian callouts — use `newline='\n'` consistently, avoid tabs); Pitfall 15 (heading collisions — use unique heading prefix `## AI Discussions` for discussion.md).

**File operations must be atomic:** Use the proven `tempfile.NamedTemporaryFile` + `os.replace()` pattern to prevent partial writes during concurrent access. Do NOT write directly to the target file.

### Phase 36: Wire AI Q&A History into Deep-Reading Dashboard

**Rationale:** Depends on Phase 33 (renderer exists) and Phase 35 (data exists). This is the integration step that connects the data pipeline end-to-end.

**Delivers:** When deep-reading dashboard shows, the AI Q&A History section renders actual discussion data from `ai/discussion.json` (last 3 Q&A pairs across all sessions, most recent first). Empty state shown when no discussions exist.

**Implements:** Architecture component — `_renderDiscussionHistory()` in deep-reading mode renderer.

**Avoids:** Pitfall 2 (fs.readFileSync bypasses vault API — use `app.vault.adapter.read()` for vault-internal discussion.json, NOT `fs.readFileSync`); Pitfall 12 (debounce timer leak — add 2-second cooldown after refresh, use mtime comparison to avoid redundant re-renders).

**Key integration detail:** The modify event filter must include `discussion.json` paths to trigger dashboard refresh when Python appends new Q&A:
```javascript
const modifyHandler = this.app.vault.on('modify', (file) => {
    if (file?.path?.endsWith('formal-library.json') || file?.path?.endsWith('discussion.json')) {
        this._invalidateIndex();
        this._refreshCurrentMode();
    }
});
```

### Phase 37: Integration Testing & Polish

**Rationale:** After all components are built, verify end-to-end flow and fix edge cases. Must test: empty states, Chinese filenames/content, split-pane mode switching, rapid Q&A recording.

**Delivers:** Verified end-to-end flow: `/pf-deep` → discussion files written → deep-reading dashboard shows Q&A history → Jump button navigates correctly → mode doesn't oscillate in split panes.

**Avoids:** All pitfalls together — uses the "Looks Done But Isn't" checklist from PITFALLS.md (13 verification items).

### Phase Ordering Rationale

- **Fixes first (31a, 31b):** Low risk, no dependencies, quick wins that improve perceived quality before new features ship. Version fix also establishes the Python→JS version bridge that Phase 33 needs.
- **Detection before rendering (32 → 33):** Mode detection is the routing infrastructure; the renderer can't work without it. Building detection first allows incremental testing.
- **Renderer before data integration (33 → 36):** Build the UI with proper empty states first, then wire real data in. This ensures graceful degradation when no discussions exist.
- **Python recorder parallel to JS dashboard (35 parallel to 32-34):** No runtime dependency — the recorder writes files, the dashboard reads them. Can be developed in parallel.
- **Integration last (36 → 37):** Wire the full data pipeline only after both ends exist. Test end-to-end only after wiring.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 32 (Mode Detection):** The `active-leaf-change` double-fire behavior varies by Obsidian version and platform. May need platform-specific debounce tuning during implementation. Consider `/gsd-research-phase` if Obsidian API behavior is uncertain.
- **Phase 35 (AI Discussion Recorder):** The exact integration point with `/pf-paper` and `/pf-deep` scripts needs implementation-level detail. How does the Agent session signal completion? What's the handoff protocol? May need `/gsd-research-phase` if the Agent integration surface is unclear.

**Phases with standard patterns (skip research-phase):**
- **Phase 31a (Version Fix):** Well-understood pattern — add field to envelope, read in fetch. Standard PaperForge index pattern.
- **Phase 33 (Dashboard Rendering):** Pattern established across 3 existing modes (global, paper, collection). Deep-reading mode follows the same `_renderXMode()` template.
- **Phase 34 (Jump Button):** Established contextual button pattern (`paperforge-contextual-btn` class) with `openLinkText()` navigation. Used elsewhere in `_renderPaperMode()`.
- **Phase 36 (Data Wiring):** Reading a JSON file and rendering DOM. Standard pattern used by `_fetchStats()` and all existing renderers.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | No new dependencies. All additions are new modules/files in existing well-understood architecture. Verified against actual source code at `paperforge/plugin/main.js` (2067 lines), `paperforge/plugin/styles.css` (1325 lines), `paperforge/worker/asset_index.py` (577 lines), `paperforge/worker/sync.py` (1829 lines). Actual test fixtures confirm `ai_path` field already exists. |
| Features | **HIGH** | Feature landscape verified against Obsidian plugin ecosystem (Smart Chat, Copilot, Gemini Scribe, Claude Sessions — 5 plugins analyzed). MVP definition maps directly to v1.8 milestone requirements from PROJECT.md. Anti-features identified by consensus (3 researchers independently flagged auto-recording as a problem). |
| Architecture | **HIGH** | All integration points verified against existing source code. Mode detection hierarchy, file ownership boundaries (Python vs JS), and data flow confirmed by code inspection at specific line ranges. Canonical index schema (`formal-library.json` v2) already carries `ai_path` field. Build order derived from dependency graph analysis. |
| Pitfalls | **HIGH** | 15 pitfalls identified across 3 severity tiers. Top 5 critical pitfalls each have verified root causes from Obsidian Forum (#31841, #91927), opencode-obsidian Issue #28, nodejs/undici Issue #5002, and paperclipai Issue #3940. Recovery strategies estimated for each pitfall. "Looks Done But Isn't" checklist provides 13 concrete verification items. |

**Overall confidence: HIGH**

All four researchers worked from the same source code (verified at specific line ranges), the same project context (PROJECT.md, STATE.md, AGENTS.md), and came to convergent conclusions. The two conflicts (schema shape, file read strategy) are well-characterized and resolved above. No areas of fundamental disagreement or missing information remain.

### Gaps to Address

- **Agent integration surface for discussion recording:** The exact API/callback for `discussion_recorder.record_session()` when an Agent session completes needs to be confirmed during Phase 35 implementation. Does `/pf-paper` emit a completion event? Where does the Q&A pair extraction happen? This is an implementation detail, not a research gap — it can be resolved during planning.
- **Deep-reading.md content parsing robustness:** The Pass 1 summary extraction relies on parsing `**一句话总览**` markers from deep-reading.md. If the agent generates different formatting in edge cases (non-standard headings, multiline bold), parsing could fail. Phase 33 should include a regex fallback that handles variations.
- **Performance at scale:** Current linear scan of index items for `_findEntry()` is O(n) and acceptable for ~100 papers. If the library grows past ~1000 papers, the dashboard may lag on mode switch. This is a known gap documented in ARCHITECTURE.md — address in a future performance phase, not v1.8.
- **Cross-platform UTF-8 path handling:** The research covers Windows CJK encoding issues thoroughly, but Linux/macOS with non-UTF-8 filesystem encodings (rare edge case) is not covered. No known users on these systems — defer until reported.

## Sources

### Primary (HIGH confidence)
- **PaperForge source code** (`paperforge/plugin/main.js` lines 1-2067, `paperforge/plugin/styles.css` lines 1-1325, `paperforge/worker/asset_index.py` lines 1-577, `paperforge/worker/sync.py` lines 1677-1749, `paperforge/worker/asset_state.py` lines 1-243) — verified mode detection, switch, rendering, index building, workspace migration, lifecycle/health/maturity computation
- **PaperForge project context** (`.planning/PROJECT.md`, `.planning/STATE.md`, `AGENTS.md`) — v1.8 milestone definition, thin-shell constraint, bug reports
- **Obsidian Developer Docs** (Context7: `/obsidianmd/obsidian-developer-docs`) — Event system, `registerEvent()`, `active-leaf-change`, `debounce()` best practices
- **Obsidian Forum #31841** — `active-leaf-change` double-fire behavior confirmed by multiple plugin developers
- **Obsidian Forum #91927** — GB2312 to UTF-8 conversion corrupting Chinese files — encoding mismatch pattern
- **opencode-obsidian Issue #28** — `btoa()` crash with Chinese characters — verified fix: `Buffer.from(str).toString('base64')`

### Secondary (MEDIUM confidence)
- **Obsidian Smart Chat** — Chat thread linking, Dataview dashboards, chat-active/chat-done tracking
- **Obsidian Copilot (DeepWiki)** — Chat persistence and history system with markdown files, YAML frontmatter, session grouping
- **Claude Sessions plugin** — Session timeline rendering, summary dashboard, Obsidian Bases dashboards
- **Gemini Scribe** — Per-note history file pattern, auto-appending
- **nodejs/undici Issue #5002** — Multi-byte UTF-8 character corruption at chunk boundaries with CJK text
- **paperclipai/paperclip Issue #3940** — GBK-UTF8 encoding mismatch on Windows with CJK child process output
- **Excalidraw plugin commit 5c628e0** — Real-world debounce timer cleanup in Obsidian plugin `onunload`
- **obsidian-current-view commit ad110f7** — Replacing requestAnimationFrame with setTimeout debounce

### Tertiary (LOW confidence)
- **PaulGP llms.txt proposal** — AI-readable paper annotations design philosophy (context only, not implementation reference)
- **Effortless Academic discussion writing guide** — Q&A-style paper discussion structure (practitioner guide, not technical reference)
- **Templater Issue #1629** — `app.vault.modify()` race condition with multiple handlers (relevant but unverified for PaperForge's specific use case)

---

*Research completed: 2026-05-06*
*Ready for roadmap: yes*
*Conflicts resolved: 2 (schema shape → sessions-based; file read strategy → vault.adapter.read for vault-internal files)*
*Gates cleared: Zero new dependencies, zero CLI command changes, thin-shell principle preserved*
