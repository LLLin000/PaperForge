# Feature Research: v1.8 AI Discussion Recording & Deep-Reading Dashboard

**Domain:** AI discussion recording and deep-reading dashboard for Obsidian literature asset management
**Researched:** 2026-05-06
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Category | Feature | Why Expected | Complexity | Notes |
|----------|---------|--------------|------------|-------|
| AI Discussion | **Discussion history in workspace** | Researchers expect to find past AI conversations about a paper next to the paper itself, not scattered in browser tabs or chat logs | MEDIUM | Already have `ai/` directory; just need to populate it |
| AI Discussion | **Human-readable Q&A format** | Users need to browse and reference past discussions without parsing JSON or opening special tools | LOW | Markdown Q&A format (问题:/解答:) is naturally scannable |
| AI Discussion | **Timestamped chronology** | Every AI chat platform shows timestamps; users expect to know "when did I discuss this?" | LOW | Simple date/time stamp per Q&A pair |
| Deep-Reading Dashboard | **Know what deep-reading exists** | When viewing a paper's `deep-reading.md`, users expect to see at a glance whether Pass 1/2/3 are complete, without scrolling through the entire note | MEDIUM | Status bar at the top of the dashboard; parse Pass headers |
| Deep-Reading Dashboard | **Quick navigation to deep-reading content** | The deep-reading.md is a long file; users need a way to jump directly to it from the paper dashboard | LOW | "Jump to Deep Reading" contextual button |
| Navigation | **Jump-to-deep-reading from per-paper card** | If the user is looking at a paper's health/lifecycle dashboard, the natural next question is "can I read the deep analysis?" | LOW | Single button on the per-paper dashboard card |
| Bug Fixes | **Version number shown** | Users expect to confirm which version of PaperForge they're running, especially when reporting issues | LOW | Restore the `_versionBadge` update path |
| Bug Fixes | **No meaningless UI rows** | If a UI element shows irrelevant data (like the "ai" row), it erodes trust in the rest of the dashboard | LOW | Remove or replace with meaningful data |

### Differentiators (Competitive Advantage)

Features that set PaperForge apart from generic Zotero sync or AI chat tools.

| Category | Feature | Value Proposition | Complexity | Notes |
|----------|---------|-------------------|------------|-------|
| AI Discussion | **Dual-format output: discussion.md + discussion.json** | Human-readable markdown for browsing AND structured JSON for dashboard consumption. No other literature tool bridges this gap with local-first files. | MEDIUM | JSON feeds the dashboard Q&A history card; markdown is the reference copy |
| AI Discussion | **Chronological session grouping with metadata** | Groups Q&A pairs by session (each `/pf-paper` or `/pf-deep` invocation), with start time, model, and agent type recorded. Enables session-level browsing. | MEDIUM | Tier-of-sessions > questions-within-session structure |
| Deep-Reading Dashboard | **Context-aware mode: deep-reading.md auto-detection** | When user opens `deep-reading.md`, the dashboard switches to a dedicated mode showing Pass status, AI Q&A history, and fulltext summary — NOT the per-paper lifecycle dashboard | MEDIUM | Extends existing mode-switching architecture (already has global/paper/collection) |
| Deep-Reading Dashboard | **Pass status overview with completion indicators** | Shows at-a-glance which of the three Keshav passes are complete, with content snippets. Reduces need to scroll through long deep-reading.md files. | MEDIUM | Parse `### Pass 1: 概览`, `### Pass 2: 精读还原`, `### Pass 3: 深度理解` |
| Deep-Reading Dashboard | **Recent AI Q&A from discussion.json** | The dashboard surfaces the most recent AI discussions about the paper directly in the deep-reading mode view. Bridges the gap between dashboard and chat history. | MEDIUM | Read `discussion.json` from `ai/` directory; show last N Q&A pairs |
| AI Discussion | **Voluntary recording model (never auto-triggered)** | Differentiates from "AI logs everything" approaches. Users opt in by running `/pf-paper` or `/pf-deep` — the recording is explicit, not surveillance. | LOW | Recording happens as a side-effect of user-initiated agent commands |

### Anti-Features

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Auto-recording all agent conversations** | "I never want to lose a conversation" | Creates noise files for abandoned/toy prompts; violates the worker/agent boundary; may capture sensitive or experimental prompts user wants ephemeral | Record only when user runs `/pf-paper` or `/pf-deep` for a specific paper — voluntary and targeted |
| **Full chat transcription in markdown** | "I want to replay the entire conversation" | Long, unstructured, hard to extract value; duplicates what the agent already stores internally | Store structured Q&A pairs with 问题:/解答: format; only meaningful exchanges, not every tool call and status message |
| **Deep-reading dashboard as a replacement for deep-reading.md** | "I just want the dashboard, not the long note" | The deep-reading.md is the authoritative source; a dashboard summary that diverges creates inconsistency and distrust | Dashboard is an index/summary view INTO the deep-reading.md; it links to the full content, never replaces it |
| **Real-time dashboard updates during deep-reading** | "I want to see progress live" | Deep reading is agent-executed outside the plugin; real-time sync would require polling or WebSocket complexity for marginal value | Dashboard refreshes on active-leaf-change (already built); shows final state after deep reading completes |
| **Discussion search across all papers** | "Find any discussion about 'osteoporosis' across my library" | Full-text search is already handled by Obsidian; rebuilding search in the plugin duplicates functionality poorly | Rely on Obsidian's built-in vault search for cross-paper discussion search |

## Feature Dependencies

```
AI Discussion Recorder (discussion.md + discussion.json)
    ├──requires──> Existing ai/ directory (v1.6 workspace migration)
    ├──requires──> /pf-paper and /pf-deep agent commands exist
    └──feeds──> Deep-Reading Dashboard (AI Q&A History card)

Deep-Reading Dashboard Mode
    ├──requires──> Existing mode-switching architecture (global/paper/collection)
    ├──requires──> deep-reading.md exists in paper workspace
    ├──requires──> discussion.json exists for AI Q&A card
    └──enhances──> Per-paper Dashboard (provides entry point via Jump button)

Jump-to-Deep-Reading Button
    ├──requires──> Per-paper dashboard exists (v1.7)
    ├──requires──> deep_reading_path in canonical index
    └──triggers──> Deep-Reading Dashboard mode (navigates user there)

Bug Fix: Version Number
    ├──requiress──> _versionBadge element exists (v1.7)
    └──requires──> version field populated in _cachedStats

Bug Fix: Meaningless "ai" Row
    └──removes──> Stale UI element from pre-workspace era
```

### Dependency Notes

- **AI Discussion Recorder feeds Deep-Reading Dashboard:** The dashboard's AI Q&A History card reads `discussion.json`. Without the recorder, this card shows an empty state. Both features should be built in the same phase.
- **Deep-Reading Dashboard extends paper mode detection:** The existing `_detectAndSwitch()` already handles `.md` files with `zotero_key` frontmatter. The new mode adds a check: if the active file is named `deep-reading.md` and resides in a paper workspace directory, switch to `deep-reading` mode instead of falling back to `global`.
- **Jump-to-Deep-Reading bridges per-paper and deep-reading dashboards:** This is a one-click navigation affordance on the per-paper card. It depends on the `deep_reading_path` field in the canonical index (already populated by `asset_index.py` v1.6).
- **Bug fixes are independent:** They don't block any new feature and can be shipped independently, but bundling in v1.8 improves perceived quality of the new features.

## MVP Definition

### Must Have (v1.8 Launch)

These define the milestone. Without them, "v1.8 AI Discussion & Deep-Reading Dashboard" is not delivered.

- [x] **AI Discussion Recorder (discussion.md + discussion.json):** Python recorder module that writes structured Q&A to `ai/discussion.md` (human-readable) and `ai/discussion.json` (dashboard-consumable) when `/pf-paper` or `/pf-deep` is run.
- [x] **Deep-Reading Dashboard Mode:** Plugin detects `deep-reading.md` as active file, switches to `deep-reading` mode showing Pass status summary + AI Q&A history.
- [x] **Jump-to-Deep-Reading Button:** On per-paper dashboard card, a button that opens the paper's `deep-reading.md` in Obsidian and triggers the deep-reading dashboard mode.
- [x] **Bug Fix: Version Number:** Restore version badge display in the plugin header (reads from canonical index or plugin manifest).
- [x] **Bug Fix: Remove meaningless "ai" row:** Identify and remove the stale "ai" UI row from the dashboard.

### Should Have (v1.8.x Follow-Up)

Deferrable without breaking the milestone.

- [ ] **Discussion session merging:** If a user runs `/pf-paper` twice for the same paper, append to existing `discussion.md` rather than overwrite.
- [ ] **Session metadata in discussion.json:** Record agent type (pf-paper vs pf-deep), model, and duration for each session.
- [ ] **Pass completion percentage in deep-reading dashboard:** Calculate rough completion (filled headings / total headings) for each Pass.

### Future Consideration (v2+)

- [ ] **Discussion search across library:** A dashboard view or Base showing all AI discussions across all papers.
- [ ] **Discussion export to context pack:** Include relevant discussion.json in the AI context pack for follow-up questions.
- [ ] **Deep-reading maturity integration:** Factor deep-reading completion into the existing maturity gauge/score.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| AI Discussion Recorder (discussion.md) | HIGH — researchers lose conversations in chat logs | MEDIUM — new Python module, template, integration with agent commands | P1 |
| AI Discussion Recorder (discussion.json) | MEDIUM — enables dashboard, but markdown is the primary value | MEDIUM — JSON serialization layer on top of discussion.md data | P1 |
| Deep-Reading Dashboard: Pass status | HIGH — immediate answer to "how complete is my reading?" | MEDIUM — new plugin render function, markdown parsing | P1 |
| Deep-Reading Dashboard: AI Q&A history | MEDIUM — surfaces recorded discussions in dashboard | LOW — reads existing discussion.json, renders cards | P1 |
| Deep-Reading Dashboard: Mode detection | HIGH — entry point for the whole feature | LOW — extends existing _detectAndSwitch() | P1 |
| Jump-to-Deep-Reading button | HIGH — bridges paper dashboard to deep reading | LOW — single contextual button + Obsidian openLinkText() | P1 |
| Bug Fix: Version number | MEDIUM — users notice when absent | LOW — single-line fix in _renderStats / _cachedStats | P1 |
| Bug Fix: Remove "ai" row | LOW — cosmetic | LOW — remove dead code | P1 |

## Feature Details: AI Discussion Recording

### Discussion Format

**discussion.md** (human-readable, one file per paper, chronologically appended):

```markdown
---
paper_key: ABCDEFG
paper_title: "Mechanisms of Osteoarthritis..."
created: 2026-05-06T10:30:00Z
updated: 2026-05-06T14:45:00Z
session_count: 2
---

# AI Discussions

## Session 2026-05-06 10:30 — Quick Summary

**Agent:** /pf-paper
**Started:** 2026-05-06 10:30:00

### 问题: What is the main finding of this paper?

**解答:** The paper demonstrates that Piezo1 mechanosensitive ion channels mediate...
(Observed in Figure 3: IHC staining shows Piezo1 expression in chondrocytes...)

**来源:** Pass 1 overview, Figure 3

---

### 问题: What signaling pathways are involved?

**解答:** The study identifies Ca²⁺/NFAT and YAP/TAZ as downstream pathways...

---

## Session 2026-05-06 14:00 — Deep Reading Discussion

**Agent:** /pf-deep
**Started:** 2026-05-06 14:00:00

### 问题: Is the sample size adequate for the conclusions drawn?

**解答:** The study uses n=6 per group which is standard for rodent OA models...
However, the power analysis was not reported — a limitation noted in the Discussion.

**来源:** Pass 3 analysis, Methods section
```

**Key design decisions:**
- **问题:/解答: format:** Natural for Chinese-speaking biomedical researchers. Minimally structured — easy to write, easy to scan.
- **Session grouping:** Each `/pf-paper` or `/pf-deep` invocation creates a new session header. Prevents one giant undifferentiated blob.
- **来源 field:** Traces each answer back to specific Pass or section — maintains PaperForge's provenance principle.
- **Append-only:** New sessions append to the end. Never rewrites old sessions. Preserves history naturally.

**discussion.json** (structured, dashboard-consumable):

```json
{
  "paper_key": "ABCDEFG",
  "schema_version": "1",
  "updated": "2026-05-06T14:45:00Z",
  "sessions": [
    {
      "session_id": "2026-05-06T10:30:00",
      "agent": "pf-paper",
      "started": "2026-05-06T10:30:00Z",
      "qa_pairs": [
        {
          "question": "What is the main finding of this paper?",
          "answer": "The paper demonstrates that Piezo1 mechanosensitive ion channels mediate...",
          "source": "Pass 1 overview, Figure 3",
          "timestamp": "2026-05-06T10:31:15Z"
        },
        {
          "question": "What signaling pathways are involved?",
          "answer": "The study identifies Ca²⁺/NFAT and YAP/TAZ as downstream pathways...",
          "source": null,
          "timestamp": "2026-05-06T10:33:42Z"
        }
      ]
    },
    {
      "session_id": "2026-05-06T14:00:00",
      "agent": "pf-deep",
      "started": "2026-05-06T14:00:00Z",
      "qa_pairs": [
        {
          "question": "Is the sample size adequate for the conclusions drawn?",
          "answer": "The study uses n=6 per group which is standard...",
          "source": "Pass 3 analysis, Methods section",
          "timestamp": "2026-05-06T14:05:30Z"
        }
      ]
    }
  ]
}
```

**Key design decisions:**
- **Minimal schema:** Only what the dashboard needs. Avoids duplicating the full markdown content.
- **session_id = ISO timestamp:** Timestamps are unique enough to serve as IDs without a UUID dependency.
- **qa_pairs array:** Flat, filterable, order-preserving.
- **source field optional:** Not all Q&A has a clear source section; null means "general discussion."

### Recorder Integration Points

The recorder lives as a new Python module: `paperforge/worker/discussion_recorder.py`

**Entry points (two):**

1. **`/pf-paper` completion:** When the agent finishes a `/pf-paper` session, the orchestrator invokes `discussion_recorder.record_session(key, agent="pf-paper", qa_pairs=[...])` 
2. **`/pf-deep` completion:** Same pattern, with `agent="pf-deep"`

**Key constraint from architecture (PROJECT.md):**
> "No auto-triggering of AI agents allowed — recording must be voluntary/user-initiated."

The recorder is invoked at the END of a user-initiated agent session, writing output to files. It does NOT trigger agents, watch for new prompts, or run in background.

**File operations:**
- Read existing `discussion.md` / `discussion.json` if they exist
- Append new session data
- Write updated files back to `ai/` directory
- All operations are idempotent: re-running the same session with the same session_id overwrites that session's entry, not duplicates it

## Feature Details: Deep-Reading Dashboard Mode

### Mode Detection

The plugin's `_detectAndSwitch()` adds a new check BEFORE the existing `.md` → `zotero_key` check:

```javascript
// Pseudocode for deep-reading mode detection:
if (ext === 'md') {
    // Check if this is a deep-reading.md in a paper workspace
    const parentDir = activeFile.parent?.name || '';
    const workspaceMatch = parentDir.match(/^([A-Z0-9]+) - /);
    const isDeepReading = activeFile.basename === 'deep-reading';
    
    if (isDeepReading && workspaceMatch) {
        // deep-reading mode
        this._currentPaperKey = workspaceMatch[1]; // extract zotero_key
        this._switchMode('deep-reading');
        return;
    }
    
    // Existing zotero_key check for per-paper mode
    // ...
}
```

**Detection hierarchy (in order):**
1. `.base` → collection mode (existing)
2. `deep-reading.md` in `{KEY} - {Title}/` workspace → deep-reading mode (NEW)
3. `.md` with `zotero_key` frontmatter → per-paper mode (existing)
4. Everything else → global mode (existing)

### Dashboard Layout (Deep-Reading Mode)

```
┌─────────────────────────────────────────────┐
│ [DEEP READING]   Paper Title (truncated)    │  ← Mode badge + context
├─────────────────────────────────────────────┤
│                                             │
│  📊 Reading Progress                        │
│  ┌─────────────────────────────────────┐    │
│  │ Pass 1: 概览            ✓ Complete  │    │  ← Status bar
│  │ Pass 2: 精读还原         ✓ Complete  │    │
│  │ Pass 3: 深度理解         ○ Pending   │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  📝 Pass 1 Summary                          │
│  ┌─────────────────────────────────────┐    │
│  │ One-liner from 一句话总览 field       │    │  ← Snippet from deep-reading.md
│  │ Category: Original Research          │    │
│  │ Context: Osteoarthritis models...    │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  💬 Recent AI Discussions (2 sessions)      │
│  ┌─────────────────────────────────────┐    │
│  │ Q: What is the main finding?         │    │  ← From discussion.json
│  │ A: The paper demonstrates...    [↗]  │    │     (last 3 Q&A pairs)
│  ├─────────────────────────────────────┤    │
│  │ Q: Is the sample size adequate?      │    │
│  │ A: The study uses n=6...       [↗]  │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  🔗 Quick Links                             │
│  [Open Fulltext]  [Open Main Note]  ...     │  ← Contextual buttons
│                                             │
└─────────────────────────────────────────────┘
```

### Section Details

#### 1. Reading Progress (Status Bar)

**What:** Three-line indicator showing Pass completion status.

**How:**
- Parse `deep-reading.md` content for section markers:
  - Pass 1 complete if `### Pass 1: 概览` section has non-scaffold content (not empty, not just template text)
  - Pass 2 complete if `### Pass 2: 精读还原` + `#### Figure-by-Figure 解析` have filled content
  - Pass 3 complete if `### Pass 3: 深度理解` has filled content
- Simple heuristic: if section has more than X non-empty lines after the heading, it's "complete"
- Visual: ✓ (green) for complete, ○ (gray) for pending, ⚠ (yellow) for partial

**Why not just check deep_reading_status:** The canonical index's `deep_reading_status` is binary (done/pending). The dashboard needs granularity: a paper might have Pass 1 complete but Pass 2 in progress. Parsing the file directly avoids needing Python-side updates for this granular state.

#### 2. Pass 1 Summary

**What:** Quick overview extracted from the deep-reading.md.

**How:**
- Extract the `**一句话总览**` content (the first non-empty line after that marker)
- Extract the 5 Cs fields from the Pass 1 section
- Show as a card with max 5 lines, "Read more →" link to full deep-reading.md

#### 3. AI Q&A History

**What:** Recent Q&A pairs from discussion.json.

**How:**
- Read `ai/discussion.json` (same workspace directory)
- Show last 3 Q&A pairs across all sessions (most recent first)
- Each card shows: question (truncated to 80 chars) + answer preview (40 chars)
- Click expands to full answer, or opens discussion.md for full context
- Empty state: "No AI discussions yet. Run /pf-paper or /pf-deep to start."

#### 4. Quick Links

**What:** Navigation buttons to related files.

**How:**
- "Open Fulltext" → opens `fulltext.md` in workspace (reuse existing _openFulltext)
- "Open Main Note" → opens the main paper note in workspace
- "Open Discussion" → opens `ai/discussion.md` (if exists)
- These replace the per-paper mode's contextual buttons since the context is different

### What the Deep-Reading Dashboard is NOT

- **NOT a replacement for deep-reading.md:** The full note remains the authoritative source. The dashboard is a navigation/view layer.
- **NOT a re-render of the per-paper dashboard:** The lifecycle stepper, health matrix, and maturity gauge belong to the per-paper card. Deep-reading mode is focused on the reading content itself.
- **NOT a real-time monitor:** No polling for agent progress. Dashboards refresh on active-leaf-change (existing pattern).

## Feature Details: Jump-to-Deep-Reading Button

### Placement

On the per-paper dashboard card, in the contextual actions row (where "Copy Context" and "Open Fulltext" currently live).

### Behavior

1. **Visible condition:** Button appears when `entry.deep_reading_path` is non-empty in the canonical index (meaning deep-reading.md exists in the workspace).
2. **Click action:** Opens `deep-reading.md` in Obsidian using `this.app.workspace.openLinkText()`. The dashboard auto-detects the new active file and switches to deep-reading mode.
3. **Visual:** Similar to existing contextual buttons (`paperforge-contextual-btn` class), with an icon + text: "🔬 Deep Reading" (or a Unicode character that renders well).

### Implementation

```javascript
// In _renderPaperMode(), after the existing contextual buttons:
if (entry.deep_reading_path) {
    const drBtn = actionsRow.createEl('button', { cls: 'paperforge-contextual-btn' });
    drBtn.createEl('span', { cls: 'paperforge-contextual-btn-icon', text: '\uD83D\uDD2C' }); // 🔬
    drBtn.createEl('span', { text: 'Deep Reading' });
    drBtn.addEventListener('click', () => {
        this.app.workspace.openLinkText(entry.deep_reading_path, '', false);
    });
}
```

## Feature Details: Bug Fixes

### Bug: Version Number Not Displaying

**Root cause:** The `_versionBadge` element is created in `_buildPanel()` but only updated in `_renderStats()`. The `_cachedStats.version` field is set to `'\u2014'` (em dash) on first load and never overwritten because the version field isn't populated from the canonical index.

**Fix:** Two changes:
1. In `_fetchStats()`, after building `this._cachedStats`, add: `this._cachedStats.version = index.schema_version || index.version || '\u2014';`
2. Alternatively, read the version from `paperforge/__init__.py` via Python subprocess, or from `paperforge/plugin/manifest.json` plugin version. The canonical index should carry a version field.

**Simplest fix:** The plugin manifest already has `"version": "1.4.15"`. Read it at plugin init and supply to the badge:

```javascript
// In onOpen() or _buildPanel():
const manifest = this.app.plugins.plugins['paperforge']?.manifest;
if (manifest?.version) {
    this._versionBadge.setText('v' + manifest.version);
}
```

### Bug: Meaningless "ai" Row

**Root cause:** From the v1.6 workspace migration era, the per-paper dashboard or global dashboard may have a row/label displaying "ai" — likely a leftover from when `ai/` directory creation was tracked as a health dimension.

**Fix:** Identify the source. Likely in the `_renderHealthMatrix()` call or `_renderNextStepCard()` where a stale field like `health.ai_health` is being rendered. Remove any reference to an "ai" health dimension from:
1. `paperforge/worker/asset_index.py` — `compute_health()` function
2. `paperforge/plugin/main.js` — `_renderHealthMatrix()` dimensions array
3. `paperforge/plugin/main.js` — `_fetchStats()` health aggregation

## Competitor / Ecosystem Analysis

| Tool | Discussion Recording | Dashboard Integration | Notes |
|------|---------------------|-----------------------|-------|
| **Obsidian Smart Chat** | Saves thread URLs + status inline in notes; markdown codeblocks | Dataview dashboards from `chat-active`/`chat-done` fields | Closest pattern: inline recording + dashboard querying. PaperForge differs by having dedicated per-paper workspace + structured Q&A format |
| **Obsidian Copilot** | Saves conversations as `.md` with YAML frontmatter; project-aware isolation | Chat history popover with fuzzy search, time grouping | Strong inspiration for session grouping and naming conventions |
| **Gemini Scribe** | Per-note history file: `[Note] - Gemini History.md`; auto-appending | History files linked to source notes; graph integration | One-file-per-note model — simple, but doesn't support multi-session grouping well |
| **Claude Sessions** | Reads Claude Code JSONL logs; renders interactive timeline | Summary dashboard with hero cards, token charts, tool charts; Base dashboards | Over-engineered for PaperForge's needs (full timeline rendering), but the "summary dashboard + Bases" pattern is relevant |
| **Smart2Brain** | Save chats; continue later | RAG-powered Q&A with vault note references | Focuses on knowledge retrieval, not discussion recording |
| **Omi Conversations** | Auto-sync from Omi device; daily-indexed conversations | Hub dashboard with tabs (tasks, conversations, memories, stats, map) | The folder-per-day + index structure is clean. PaperForge's session-per-invocation is simpler and sufficient |

**Key insight from ecosystem:** The Obsidian plugin ecosystem overwhelmingly favors **file-based recording** (markdown in the vault) over database-backed storage. PaperForge's `discussion.md` + `discussion.json` dual-format approach fits this pattern while adding dashboard-queryable structure that pure markdown lacks.

## Architecture Alignment

All new features must respect existing architecture principles from `.planning/research/ARCHITECTURE.md`:

1. **Thin-shell plugin:** The plugin reads JSON (canonical index + discussion.json), never recomputes lifecycle or health. The deep-reading mode parsing (Pass status) is a read-only display concern — not business logic duplication.
2. **Python-owned truth:** Discussion recording logic lives in `paperforge/worker/discussion_recorder.py`. The plugin only reads the output files.
3. **No new canonical index fields needed:** The deep-reading dashboard reads `deep_reading.md` content directly and `discussion.json` from the workspace. No changes to `formal-library.json` required (though a `discussion_count` field could be added later for the per-paper card).
4. **Mode switching extends existing pattern:** Deep-reading mode is a fourth mode (`deep-reading`) alongside global, paper, and collection. It uses the same `_switchMode()`, `_renderModeHeader()`, and `_refreshCurrentMode()` infrastructure.

## Sources

- **PaperForge internal code inspection:** `paperforge/plugin/main.js` — mode switching architecture (global/paper/collection), per-paper dashboard rendering, contextual buttons, event subscriptions — HIGH confidence
- **PaperForge internal code inspection:** `paperforge/worker/sync.py` — workspace migration creating `ai/` directory (lines 1680-1749) — HIGH confidence
- **PaperForge internal code inspection:** `paperforge/worker/asset_index.py` — canonical index `_build_entry()` creating workspace paths including `ai_path`, `deep_reading_path` — HIGH confidence
- **PaperForge internal code inspection:** `paperforge/skills/literature-qa/scripts/ld_deep.py` — deep-reading scaffold structure, Pass 1/2/3 markers, figure block format — HIGH confidence
- **Obsidian Smart Chat documentation:** Chat thread linking within notes, Dataview dashboards, chat-active/chat-done tracking — https://smartconnections.app/smart-chat/ — HIGH confidence (official plugin docs)
- **Obsidian Copilot (DeepWiki):** Chat persistence and history system — markdown files with YAML frontmatter, session grouping, recent usage tracking — https://deepwiki.com/logancyang/obsidian-copilot/8-chat-persistence-and-history — HIGH confidence (documented architecture)
- **Gemini Scribe chat history guide:** Per-note history file pattern, auto-appending, markdown formatting — https://github.com/allenhutchison/obsidian-gemini — MEDIUM confidence (community plugin docs)
- **Claude Sessions plugin:** Session timeline rendering, summary dashboard with hero cards, Obsidian Bases dashboards — https://github.com/gapmiss/claude-sessions — HIGH confidence (well-documented community plugin)
- **PaulGP llms.txt proposal:** Discussion of AI-readable paper annotations, limitations-first orientation — https://paulgp.com/2026/03/10/llms-txt-for-academic-papers.html — MEDIUM confidence (academic blog post, design philosophy reference)
- **Effortless Academic discussion writing guide:** Q&A-style paper discussion structure — MEDIUM confidence (practitioner guide)

---

*Feature research for: v1.8 AI Discussion Recording & Deep-Reading Dashboard*
*Researched: 2026-05-06*
