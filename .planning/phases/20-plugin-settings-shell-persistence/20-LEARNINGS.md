---
phase: 20
phase_name: "Plugin Settings Shell & Persistence"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 6
  lessons: 3
  patterns: 3
  surprises: 3
missing_artifacts:
  - "UAT.md"
---

## Decisions

### All code in main.js
All settings code stays in `main.js` with no build system — Obsidian's `require('obsidian')` works natively, and a second file would add path complexity.

**Rationale/Context:** CommonJS `require` from Obsidian already works in the plugin context. A separate settings file would need careful path handling relative to the plugin directory. Keeping everything in one file is simpler and avoids build tooling.

**Source:** 20-PLAN.md, 20-SUMMARY.md

---

### Debounced save at 500ms
In-memory settings update immediately on input change; disk write is debounced via `setTimeout`/`clearTimeout` with 500ms delay.

**Rationale/Context:** Prevents thrashing `data.json` on every keystroke while ensuring responsive UI. User sees instant feedback; disk writes are batched.

**Source:** 20-PLAN.md, 20-SUMMARY.md

---

### String fields only
All 8 settings are text inputs; no toggles/selects needed. Password field type for API key.

**Rationale/Context:** All configuration values in this phase (vault_path, system_dir, resources_dir, etc.) are path strings or API keys. No boolean toggles or dropdown selections are required.

**Source:** 20-PLAN.md

---

### display() lifecycle for tab switch survival
`display()` reconstructs DOM from `this.plugin.settings` on each call (tab switch). In-memory settings preserve state with zero data loss.

**Rationale/Context:** Obsidian's settings tab calls `display()` each time the tab is shown. By rebuilding from the in-memory settings object (not re-reading disk), typed values survive tab switches without disk I/O on every transition.

**Source:** 20-PLAN.md, 20-SUMMARY.md

---

### Null-safe merge for fresh install
`Object.assign({}, DEFAULTS, await this.loadData())` prevents TypeError on fresh install when `loadData()` returns null.

**Rationale/Context:** Obsidian's `loadData()` returns `null` when no prior `data.json` exists. `Object.assign` silently ignores null/undefined sources, so the merge produces defaults without a TypeError guard check.

**Source:** 20-PLAN.md, 20-SUMMARY.md, 20-VERIFICATION.md

---

### No CSS additions needed
Obsidian's built-in `.setting-item` styles render the settings tab perfectly; no custom styles needed.

**Rationale/Context:** Obsidian's settings UI framework provides complete styling for setting items (labels, descriptions, input fields, sections). Custom CSS would be redundant.

**Source:** 20-SUMMARY.md, 20-VERIFICATION.md

---

## Lessons

### Tasks 1+2 are functionally interdependent
Both modify `main.js` and share state (tab UI calls `plugin.settings` and `plugin.saveSettings()`), so they were combined into one atomic commit.

**Context:** Task 1 (data model + persistence methods) and Task 2 (settings tab UI) both modify the same class and cannot be tested independently. The tab UI immediately references methods added in Task 1.

**Source:** 20-SUMMARY.md

---

### Obsidian PluginSettingTab API is straightforward
Extending `PluginSettingTab` with the `Setting` form builder works well and requires minimal boilerplate.

**Context:** The entire settings tab with 8 fields in 3 sections was implemented in ~87 lines using Obsidian's built-in settings API. No custom HTML or event handling needed.

**Source:** 20-SUMMARY.md

---

### Requirements tracking metadata can drift from implementation
The SUMMARY (`requirements-completed: [SETUP-01, SETUP-02]`) and REQUIREMENTS.md both show SETUP-03 as unchecked, but the actual code in `main.js` fully implements SETUP-03.

**Context:** The code was written and committed implementing immediate in-memory updates, debounced disk writes, and tab switch survival — all satisfying SETUP-03. But the tracking metadata was not updated to reflect this.

**Source:** 20-VERIFICATION.md

---

## Patterns

### Debounced persistence pattern
`clearTimeout`/`setTimeout` wrapper with 500ms delay for debounced disk writes on field change.

**When to use:** When you need instant UI responsiveness but want to batch/rate-limit expensive persistence operations. Applicable to any Obsidian plugin with editable settings.

**Source:** 20-SUMMARY.md, 20-VERIFICATION.md

---

### Null-safe merge pattern
`Object.assign({}, DEFAULTS, await this.loadData())` as a safe initialization pattern for Obsidian plugin settings.

**When to use:** When merging Obsidian plugin defaults with persisted settings. Handles fresh install (null/undefined), partial settings (missing keys get defaults), and full settings (all values override).

**Source:** 20-SUMMARY.md, 20-VERIFICATION.md

---

### In-memory state on change + deferred disk write
Immediate memory update for responsiveness, 500ms debounce for persistence.

**When to use:** When you need low-latency UI feedback but want to avoid excessive disk I/O. The in-memory object serves as the single source of truth during the session; disk is only a persistence layer.

**Source:** 20-SUMMARY.md

---

## Surprises

### Very fast execution
2 minutes to complete the entire phase (3 tasks, 87 lines added to main.js).

**Impact:** The phase was substantially faster than anticipated because the plan was well-specified and the Obsidian API had no surprises. The code already existed in the working tree matching the plan.

**Source:** 20-SUMMARY.md

---

### No CSS changes needed
Obsidian's default setting-item styles handle the settings tab perfectly without any custom CSS.

**Impact:** Eliminated an entire task from the plan. The Obsidian settings UI framework is more comprehensive than initially assumed.

**Source:** 20-SUMMARY.md

---

### Metadata gap between tracking and implementation
SUMMARY and REQUIREMENTS.md disagree on SETUP-03 status (tracked as unchecked but actually implemented in code).

**Impact:** This could lead to incorrect status reports and confusion about what's actually implemented. Highlights the need for automated verification that cross-references tracking metadata against actual code.

**Source:** 20-VERIFICATION.md
