# Roadmap: PaperForge

**Current milestone:** v1.8 AI Discussion & Deep-Reading Dashboard — Planned
**Phase numbering:** Continuous. v1.7 ended at Phase 30. v1.8 begins at Phase 31.

---

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-04-23)
- ✅ **v1.1 Sandbox Onboarding** — Phases 6-8 (shipped 2026-04-24)
- ✅ **v1.2 Systematization & Cohesion** — Phases 9-10 (shipped 2026-04-24)
- ✅ **v1.3 Path Normalization & Architecture Hardening** — Phases 11-12 (shipped 2026-04-24)
- ✅ **v1.4 Code Health & UX Hardening** — Phases 13-19 (shipped 2026-04-28)
- ✅ **v1.5 Obsidian Plugin Setup Integration** — Phases 20-21 (shipped 2026-04-29)
- ✅ **v1.6 AI-Ready Literature Asset Foundation** — Phases 22-26 (shipped 2026-05-04)
- ✅ **v1.7 Context-Aware Dashboard** — Phases 27-30 (shipped 2026-05-04)
- 📋 **v1.8 AI Discussion & Deep-Reading Dashboard** — Phases 31-36 (planned)

*Archive: `.planning/milestones/`*

---

## Phases

<details>
<summary>✅ v1.6 AI-Ready Literature Asset Foundation (Phases 22-26) — SHIPPED 2026-05-04</summary>

- [x] Phase 22: Configuration Truth & Compatibility (3/3)
- [x] Phase 23: Canonical Asset Index & Safe Rebuilds (3/3)
- [x] Phase 24: Derived Lifecycle, Health & Maturity (2/2)
- [x] Phase 25: Surface Convergence, Doctor & Repair (3/3)
- [x] Phase 26: Traceable AI Context Packs (3/3)

</details>

<details>
<summary>✅ v1.7 Context-Aware Dashboard (Phases 27-30) — SHIPPED 2026-05-04</summary>

- [x] Phase 27: Component Library (2/2)
- [x] Phase 28: Dashboard Shell & Context Detection (2/2)
- [x] Phase 29: Per-Paper View (1/1)
- [x] Phase 30: Collection View (1/1)

</details>

### 📋 v1.8 AI Discussion & Deep-Reading Dashboard (Planned)

**Milestone Goal:** Capture AI-paper discussions into structured ai/ records and extend the per-paper dashboard with deep-reading content and AI interaction history.

- [ ] **Phase 31: Bug Fixes** — Restore version display; remove meaningless "ai" UI row
- [ ] **Phase 32: Deep-Reading Mode Detection** — Plugin routes deep-reading.md to dedicated dashboard mode
- [ ] **Phase 33: Deep-Reading Dashboard Rendering** — Status bar, Pass 1 summary, empty-state AI Q&A card
- [x] **Phase 34: Jump to Deep Reading Button** — Per-paper dashboard card links to deep-reading.md (completed 2026-05-06)
- [x] **Phase 35: AI Discussion Recorder** — Python module writes discussion.md + discussion.json into ai/ (completed 2026-05-06)
- [ ] **Phase 36: Integration Verification** — End-to-end pipeline verified with CJK encoding and vault.adapter.read

---

## Phase Details

### Phase 31: Bug Fixes
**Goal**: Plugin version number is displayed correctly and the meaningless "ai" row is removed from all dashboard views.
**Depends on**: Nothing (first phase)
**Requirements**: NAV-02, NAV-03
**Success Criteria** (what must be TRUE):
  1. Plugin header shows the actual PaperForge version (e.g., "v1.8.0") read from package metadata, not a placeholder like "v—"
  2. Dashboard rendering excludes the empty "ai" row across all three render modes (global, paper, collection)
  3. git grep confirms zero references to the removed "ai" row rendering logic in plugin JS and CSS
  4. The Python→JS version bridge (paperforge_version in formal-library.json envelope) is established for future consumption
**Plans**: TBD
**UI hint**: yes

### Phase 32: Deep-Reading Mode Detection
**Goal**: Plugin detects deep-reading.md files by filename (before zotero_key frontmatter check) and routes to a dedicated `deep-reading` dashboard mode without oscillation.
**Depends on**: Phase 31
**Requirements**: DEEP-01
**Success Criteria** (what must be TRUE):
  1. Opening any deep-reading.md file in the vault switches the dashboard to deep-reading mode, validating the parent directory pattern ({8-char key} - {title})
  2. A deep-reading.md file carrying zotero_key frontmatter routes to deep-reading mode, NOT per-paper mode — filename check precedes frontmatter check
  3. Switching away from deep-reading.md (e.g., opening a formal note) transitions to the correct mode without visible flicker or mode oscillation
  4. `_resolveModeForFile()` is extracted as a pure function with identity guard (same mode AND same file path = no-op) to prevent active-leaf-change double-fire
**Plans**: TBD
**UI hint**: yes

### Phase 33: Deep-Reading Dashboard Rendering
**Goal**: Deep-reading dashboard renders reading progress status, Pass 1 full-text summary, and graceful empty states for all four AI discussion data conditions.
**Depends on**: Phase 32
**Requirements**: DEEP-02, DEEP-03
**Success Criteria** (what must be TRUE):
  1. Deep-reading dashboard displays a status bar with Pass 1/2/3 completion indicators and OCR/health/maturity badges
  2. Pass 1 full-text summary card renders content extracted from deep-reading.md markers (e.g., **一句话总览**), supporting regex fallback for formatting variations
  3. AI Q&A history section shows a descriptive Chinese placeholder ("暂无讨论记录") when no discussion.json exists, and "暂无问答内容" when sessions are empty
  4. All four empty-state conditions render user-facing messages without JavaScript errors: (a) missing discussion.json, (b) empty sessions array, (c) missing Pass 1 content, (d) deep-reading.md file not found
  5. CSS additions are scoped under `.paperforge-mode-deepreading` wrapper class with `paperforge-deepreading-*` component prefixes to avoid namespace collisions
**Plans**: TBD
**UI hint**: yes

### Phase 34: Jump to Deep Reading Button
**Goal**: Per-paper dashboard card provides a one-click contextual button to open the associated deep-reading.md file, with file-existence verification before navigation.
**Depends on**: Phase 32, Phase 33
**Requirements**: NAV-01
**Success Criteria** (what must be TRUE):
  1. Per-paper dashboard card renders a "跳转到精读" button when the paper's deep_reading_path exists and deep_reading_status is 'done'
  2. Clicking the button opens deep-reading.md via openLinkText() in the active leaf, which triggers Phase 32 mode detection and renders the Phase 33 dashboard
  3. The button is hidden (not just disabled) when the paper has no deep_reading_path or its status is not 'done'
  4. If deep-reading.md is missing from disk despite the index claiming it exists, app.vault.adapter.getAbstractFileByPath() returns null and a clear Obsidian Notice informs the user instead of crashing
**Plans**: 1 plan
**UI hint**: yes

### Phase 35: AI Discussion Recorder
**Goal**: Agent sessions (`/pf-paper`, `/pf-deep`) produce structured discussion records — JSON (canonical) and Markdown (human-readable) — in each paper's workspace `ai/` directory with atomic writes and UTF-8 encoding.
**Depends on**: Nothing (standalone Python module; can execute in parallel with Phases 32-34)
**Requirements**: AI-01, AI-02, AI-03
**Success Criteria** (what must be TRUE):
  1. Running `/pf-paper` or `/pf-deep` for a paper creates `ai/discussion.json` in that paper's workspace directory, containing `schema_version: "1"`, `paper_key`, and a `sessions[]` array with `session_id`, `agent`, `started`, `model`, and `qa_pairs[]` (each with `question`, `answer`, `source`, `timestamp`)
  2. The same session produces `ai/discussion.md` with human-readable `问题:` / `解答:` format, chronological `##` session headings, and timestamp metadata
  3. Re-running an agent session for the same paper appends a new session entry rather than overwriting previous discussions, using atomic read-modify-write via `tempfile.NamedTemporaryFile` + `os.replace()`
  4. Discussion files are written with explicit `encoding='utf-8'` and `newline='\n'` and are readable in Obsidian without mojibake on Windows CJK systems
  5. `discussion.py` uses only Python stdlib (`json`, `pathlib`, `datetime`, `tempfile`, `os`) — zero new dependencies
**Plans**: 1 plan

Plans:
- [x] 35-01-PLAN.md — Python module (discussion.py) + pf-paper.md integration

### Phase 36: Integration Verification
**Goal**: End-to-end pipeline verified: agent session writes discussion files → dashboard reads and renders AI Q&A history via vault.adapter.read(). Windows CJK encoding and no-btoa() constraints validated.
**Depends on**: Phase 33, Phase 35
**Requirements**: INTEG-01
**Success Criteria** (what must be TRUE):
  1. Full flow works end-to-end: run `/pf-paper` → verify discussion.json and discussion.md exist in `ai/` → open deep-reading.md → dashboard AI Q&A History section renders Q&A pairs from discussion.json (last 3 pairs across all sessions, most recent first)
  2. Chinese content (questions, answers, paper titles) survives the Python→disk→JS pipeline without encoding corruption — verified on Windows with CJK locale
  3. Zero `btoa()` or `atob()` calls exist in any path construction involving paper titles or discussion file paths — uses `Buffer.from(str, 'utf-8').toString('base64')` if base64 needed
  4. Dashboard discussion.json read uses `app.vault.adapter.read()`, not `fs.readFileSync()`, and the vault modify event listener includes `discussion.json` paths to trigger dashboard refresh when Python appends new Q&A
**Plans**: TBD
**UI hint**: yes

---

## Progress

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 27. Component Library | 2/2 | Complete | 2026-05-04 |
| 28. Dashboard Shell & Context Detection | 2/2 | Complete | 2026-05-04 |
| 29. Per-Paper View | 1/1 | Complete | 2026-05-04 |
| 30. Collection View | 1/1 | Complete | 2026-05-04 |
| 31. Bug Fixes | 0/TBD | Not started | - |
| 32. Deep-Reading Mode Detection | 0/TBD | Not started | - |
| 33. Deep-Reading Dashboard Rendering | 0/TBD | Not started | - |
| 34. Jump to Deep Reading Button | 1/1 | Complete    | 2026-05-06 |
| 35. AI Discussion Recorder | 1/1 | Complete   | 2026-05-06 |
| 36. Integration Verification | 0/TBD | Not started | - |

---

*Roadmap updated: 2026-05-06 — v1.8 milestone planned*
