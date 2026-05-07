# Stack Research — v1.8 AI Discussion Recording & Deep-Reading Dashboard

**Domain:** AI discussion recording + deep-reading dashboard mode for PaperForge Obsidian plugin
**Researched:** 2026-05-06
**Confidence:** HIGH

## Executive Summary

v1.8 adds two new capabilities to the existing PaperForge stack: (1) AI discussion recording that captures `/pf-paper` and agent chat interactions into structured `ai/` records, and (2) a 4th dashboard mode activated when the user views `deep-reading.md`. Both features extend the existing thin-shell plugin architecture — the plugin reads JSON from the filesystem and renders Pure CSS/DOM components; the Python side provides templates and optional recording helpers. **No new npm dependencies, no new Python packages.** All additions are new modules/files within the existing architecture.

## Recommended Stack

### Core Technologies (unchanged from v1.6–v1.7)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Obsidian CommonJS plugin | existing (`main.js`) | Dashboard/settings/commands UI | Pure Obsidian API — no bundler, no npm deps, no build step |
| Python 3.10+ | existing | Single owner of business logic, templates, schema | Already owns config, lifecycle, health, maturity, index; extends naturally to discussion templates |
| Filesystem JSON | UTF-8, no schema library needed | `discussion.json` per paper | Plugin reads via `fs.readFileSync`, localStorage-free, vault-native, traceable |
| Filesystem Markdown | Obsidian-flavored | `discussion.md` per paper | Human-readable, Obsidian-editable, wikilink-compatible |

### File Format Additions (NEW for v1.8)

#### 1. `discussion.json` — Structured AI Q&A Record

**Location:** `<paper_workspace>/ai/discussion.json`

**Schema (v1):**

```json
{
  "schema_version": "1",
  "paper_key": "ABCDEFG",
  "generated_at": "2026-05-06T12:00:00+08:00",
  "source": "/pf-paper",                    // or "/pf-deep", "agent-chat"
  "history": [
    {
      "index": 1,
      "timestamp": "2026-05-06T12:00:00+08:00",
      "question": "这篇论文的主要发现是什么？",
      "answer": "该研究发现...",
      "tags": ["background", "results"],
      "agent_model": "deepseek-v4-pro"
    }
  ],
  "summary": {
    "total_qa": 5,
    "last_updated": "2026-05-06T12:30:00+08:00",
    "top_tags": ["methods", "results"]
  }
}
```

**Why this shape:**
- `schema_version` for forward compatibility
- `history[]` is a flat append-only list (no nested threads — keeps dashboard rendering simple)
- `index` field enables stable references even if history is reordered
- `tags` enable future dashboard filtering without schema change
- `summary` provides pre-computed metadata the plugin can read with a single parse (avoids looping through all history entries for total count)

**Integration:** Plugin reads this file directly via `fs.readFileSync` when rendering the deep-reading dashboard. No Python intermediary needed for read path.

#### 2. `discussion.md` — Human-Readable Q&A Log

**Location:** `<paper_workspace>/ai/discussion.md`

**Template format:**

```markdown
# AI 讨论记录 — 文献标题

> **来源:** /pf-paper | **生成时间:** 2026-05-06 12:00 | **模型:** deepseek-v4-pro

---

## 讨论 1

**问题:** 这篇论文的主要发现是什么？

**解答:** 该研究发现...

*标签: `background`, `results`*

---

## 讨论 2

**问题:** 研究者用了什么统计方法？

**解答:** ...

*标签: `methods`*
```

**Why this format:**
- Each discussion is a `## 讨论 N` section — natural Obsidian heading hierarchy
- `**问题:**` and `**解答:**` bold markers are scannable in both Reading and Source mode
- Horizontal rules (`---`) visually separate discussions
- Tags as inline code spans — searchable in Obsidian's global search
- Frontmatter-compatible metadata line at top

### Plugin JS Additions (NEW for v1.8 — no new npm deps)

All additions stay within the single `paperforge/plugin/main.js` file and `paperforge/plugin/styles.css`.

| Module/Function | Type | Purpose |
|---------|------|---------|
| `_detectAndSwitch()` extension | Mode detection logic | Add `deep-reading` as 4th mode: detect when active file path ends with `deep-reading.md` and resolve paper context from workspace path |
| `_renderDeepReadingMode()` | New render function | Renders deep-reading dashboard: status bar, Pass 1 summary, AI discussion history |
| `_renderDiscussionHistory()` | New render function | Reads `discussion.json` from paper `ai/` directory and renders Q&A cards |
| `_readDiscussionJson(key)` | New utility | Resolves `ai_path` → reads `discussion.json` → returns parsed object or null |
| `_renderPass1Summary()` | New render function | Renders Pass 1 overview extracted from deep-reading.md content |
| `_renderPaperMode()` extension | Existing function | Add "Jump to Deep Reading" contextual button when `deep_reading_path` exists |
| `_versionBadge` fix | Bug fix | Restore version display by reading from `paperforge/__init__.py` `__version__` or `manifest.json` |
| "ai" row removal | Bug fix | Remove the meaningless "ai" UI row (track down which render path creates it) |

**Mode detection logic (how `_detectAndSwitch()` grows):**

```javascript
// Existing: checks for .base, .md with zotero_key
// NEW: check if active file basename is "deep-reading.md"
if (ext === 'md' && activeFile.basename === 'deep-reading') {
    // Resolve paper key from parent directory name
    const parentDir = activeFile.parent.path;  // e.g., "Literature/骨科/ABC12345 - Title"
    const match = parentDir.match(/([A-Z0-9]{8})/);
    if (match) {
        this._currentPaperKey = match[1];
        this._currentPaperEntry = this._findEntry(match[1]);
        this._switchMode('deep-reading');
        return;
    }
}
```

### CSS Additions (NEW for v1.8)

All additions go into the existing `paperforge/plugin/styles.css` file after Section 17.

| CSS Class | Purpose |
|-----------|---------|
| `.paperforge-deep-reading-view` | Root container for deep-reading mode layout (flex column, gap: 20px) |
| `.paperforge-dr-status-bar` | Status indicator bar: shows Pass 1/2/3 completion, OCR status badge, last-updated timestamp |
| `.paperforge-dr-pass-summary` | Pass 1 summary card: bordered card with muted background for the overview text |
| `.paperforge-dr-discussion-card` | Individual Q&A card: question in bold, answer below, tag chips, timestamp |
| `.paperforge-dr-discussion-list` | Scrollable container for stacked discussion cards |
| `.paperforge-dr-tag-chip` | Small pill for tags (font-size: 10px, border-radius: 8px) |
| `.paperforge-dr-empty` | Empty state: "No AI discussions recorded yet" with muted styling |
| `.paperforge-dr-section-title` | Section header within deep-reading view (uppercase, letter-spaced) |

### Python Additions (NEW for v1.8 — no new dependencies)

| File | Purpose |
|------|---------|
| `paperforge/worker/discussion.py` | NEW module: `record_discussion(key, vault, question, answer, source, model)` — writes both `discussion.md` and `discussion.json` to paper `ai/` directory |
| `paperforge/worker/discussion.py` | `load_discussion_json(key, vault)` → dict — reads existing discussion.json, returns parsed dict |
| `paperforge/worker/discussion.py` | `append_discussion(key, vault, qa_pair)` — appends to existing discussion history (read-modify-write atomic via tempfile + os.replace) |

**Why a separate module:**
- Discussion recording crosses the Worker/Agent boundary (Agent generates content, Worker writes files)
- Keeps discussion I/O isolated from OCR, sync, and index logic
- Enables future `/pf-discuss` command or discussion-search features without refactoring

**No new Python packages required.** All I/O uses `json`, `pathlib`, and `datetime` (stdlib). Atomic write uses the same `tempfile` + `os.replace` pattern already proven in `asset_index.py`.

### Integration Points (with existing canonical index)

| Integration | Direction | How |
|-------------|-----------|-----|
| `ai_path` in canonical index | Read by plugin | Already exists: `entry.ai_path` = `"Literature/<domain>/<key> - <Title>/ai/"` |
| Resolve `discussion.json` path | Plugin computed | `path.join(vaultPath, entry.ai_path, 'discussion.json')` |
| Deep-reading mode detection | Plugin computed | Check `activeFile.basename === 'deep-reading'` + resolve key from parent directory |
| Jump-to-deep-reading button visibility | Plugin check | `entry.deep_reading_path` non-empty → show button |
| Discussion recording write path | Python writes | `record_discussion()` resolves paths via `paperforge_paths()` → writes to workspace ai/ |

## What NOT to Add

| Category | Avoid | Why | Use Instead |
|----------|-------|-----|-------------|
| JS dependencies | Any npm package (React, Vue, chart libs, date-fns) | Plugin must stay pure Obsidian CommonJS; adding a build chain breaks the single-file deployment model and Obsidian Community Plugin requirements | Pure DOM API (`createEl`, `addClass`, `setText`) |
| Database for discussions | SQLite, IndexedDB, localStorage | Discussions belong to the paper workspace — they must be vault-native, backup-friendly, and git-trackable | Filesystem JSON + Markdown in `ai/` |
| Python dependencies for discussion | `pydantic`, `jsonschema` | Overkill for a flat Q&A list; adds import cost and version coupling for a simple structure | Plain `dict` with documented keys, validated by `assert` in tests |
| Second plugin file | Splitting `main.js` into modules | Adds complexity without benefit at ~2100 lines; Obsidian plugin import resolution is fragile | Inline functions in `main.js` (as all existing render functions are) |
| Schema library in plugin | AJV, Zod, or custom JSON validator | Plugin should read, not validate; schema enforcement lives in Python tests | Trust but handle: `try/catch` around `JSON.parse`, fallback to empty state |
| New CLI command (v1.8) | `paperforge discuss` or `paperforge record` | Discussion recording happens inside Agent sessions; adding a CLI command would require users to manually run it after each Q&A | Python module callable from Agent scripts (`/pf-paper` → calls `record_discussion()` internally) |

## Version Compatibility

| Component | Current Version | Notes |
|-----------|----------------|-------|
| PaperForge Python | 1.4.15 (→ 1.8.0) | No breaking changes to existing CLI or index schema |
| Canonical index schema | v2 (`formal-library.json`) | `ai_path` field already present; no schema version bump needed |
| Obsidian API | 1.5+ | Existing API surface used (ItemView, metadataCache, vault.adapter) |
| Node.js (for Obsidian) | 18+ (Electron embedded) | `fs.readFileSync`, `path.join` — all stdlib since Node 0.x |

## Installation

No new installation steps. v1.8 is additive:

```bash
# No new pip packages needed
# No new npm packages needed

# Plugin update: replace main.js + styles.css + manifest.json + versions.json
# Python update: add paperforge/worker/discussion.py
```

## Sources

- Existing codebase analysis: `paperforge/plugin/main.js` (2067 lines), `paperforge/plugin/styles.css` (1325 lines), `paperforge/worker/asset_index.py` (577 lines), `paperforge/worker/asset_state.py` (243 lines), `paperforge/worker/sync.py` (1829 lines) — HIGH confidence
- `.planning/PROJECT.md` — v1.8 milestone definition, ai/ directory already created per paper — HIGH confidence
- AGENTS.md — Lite architecture, Worker/Agent split, plugin thin-shell constraint — HIGH confidence
- `.planning/research/STACK.md` (v1.6) — existing stack decisions, Pydantic version, filelock version, "what NOT to add" — HIGH confidence
- Actual test fixtures: `tests/test_asset_state.py` — ai_path field verified in lifecycle/health computation — HIGH confidence

---

*Stack research for: PaperForge v1.8 AI Discussion Recording & Deep-Reading Dashboard*
*Researched: 2026-05-06*
