# PaperForge Control Center UX Redesign

**Status:** Approved design baseline
**Date:** 2026-07-19
**Scope:** Obsidian plugin setup, control center, operational module details, maintenance, help, and OCR workspace entry
**Design system:** [`paperforge/plugin/DESIGN.md`](../../paperforge/plugin/DESIGN.md)
**Domain language:** [`paperforge/plugin/CONTEXT.md`](../../paperforge/plugin/CONTEXT.md)

## 1. Problem

The current settings surface exposes implementation concepts and duplicate actions without a stable user model. “Installation” acts as a permanent module while also containing runtime, Python, Zotero, Agent, and Skills configuration. `Install`, `Sync Runtime`, `Check`, `Check Status`, `Retry`, `Update Runtime`, and `Rollback` overlap without telling the user which outcome each produces. Module Detail is a top-level destination but the Installation renderer exposes only its own selector, while Library, OCR, and Memory use a separate four-module shell. Cached probe expiry is rendered as “Pending/待接入,” making a healthy installation appear absent.

The redesign must make the control center understandable without knowledge of Python, runtime slots, probe envelopes, schema versions, or CLI commands.

## 2. Product model

### 2.1 Operational baseline

PaperForge is usable when:

1. Foundation is ready.
2. Library is connected.

OCR, Smart Retrieval, and Agent Integration are optional. A capability the user never enabled does not block Setup Completion, lower the overall summary, or enter Maintenance.

### 2.2 Operational modules

The five modules are:

1. **Foundation** — the PaperForge environment on this device.
2. **Library** — Zotero connection and literature synchronization.
3. **OCR** — OCR availability, summary, service configuration, and entry to paper-level work.
4. **Smart Retrieval** — retrieval coverage, freshness, and service configuration.
5. **Agent Integration** — target agent platform, deployment state, and Skills management.

Maintenance and Help are destinations, not modules.

### 2.3 Status vocabulary

Every module maps backend facts into exactly one user status:

| User status | Meaning | Default user treatment |
|---|---|---|
| Checking | A refresh is running | Preserve Last Known Status and show separate refresh activity |
| Ready | Capability is usable | Quiet; no Contextual Primary Action |
| Not Enabled | Optional capability was not selected | Neutral explanation and an Enable entry in detail only |
| Setup Required | Required information is missing | Explain the missing user choice and offer one setup action |
| Action Required | Enabled capability has a blocking, failed, unusable, or materially risky condition | Explain impact and offer one backend-authorized action |
| Detection Failed | Current status cannot be confirmed | Show Retry and a timestamped Last Known Status when available |

`unknown`, `stale`, TTL expiry, internal quality color, and raw reason code are not user statuses.

### 2.4 Action ownership

The backend owns:

- stable action ID;
- exact executable command and scope;
- availability;
- destructive flag and preservation facts;
- confirmation requirement.

The plugin owns:

- localized label and explanation;
- visual priority;
- whether a safe action runs in place or routes to context;
- focus, progress, and completion feedback.

The plugin must not infer an action from status alone. Backend labels and CLI commands must not be displayed as user copy.

## 3. Information architecture

```text
First use
└─ Setup Journey
   ├─ 1 Foundation
   ├─ 2 Connect Library
   ├─ 3 Selected Optional Capabilities
   └─ 4 Review and Begin

Normal Control Center
├─ Overview
│  ├─ Control Center Summary
│  └─ Five Module Cards
├─ Maintenance
└─ Help

Module Detail — contextual drill-down
├─ Foundation
├─ Library
├─ OCR ──→ full-width OCR Operational Workspace
├─ Smart Retrieval
└─ Agent Integration
```

Module Detail is not a top-level tab. It is entered from a Module Card or Maintenance Action. The fixed detail shell contains return navigation, responsive module switching, title, status, summary, primary action area, and Support Diagnostic entry. Bodies are module-specific.

The last top-level destination or selected module is persisted. Reopening refreshes current state but does not restore drafts, selections, confirmations, disclosure state, or scroll position.

## 4. Screen specifications

### 4.1 Setup Journey

The Setup Journey appears only before durable Setup Completion.

1. **Foundation:** automatically check and establish PaperForge. Do not expose Runtime or Python unless recovery fails.
2. **Connect Library:** configure and validate Zotero plus safe default vault locations.
3. **Optional Capabilities:** let the user select OCR, Smart Retrieval, and Agent Integration; render configuration only for selected capabilities.
4. **Review and Begin:** summarize what is ready, what was intentionally skipped, and where skipped capabilities can be enabled later.

Later module health failures never reopen the Setup Journey automatically. Module-owned Change actions handle reconfiguration.

### 4.2 Overview

Header:

- overall statement based on Operational Baseline;
- count of Maintenance items for enabled modules;
- last update or refresh activity;
- one global **Refresh Status** action.

Module Cards:

- Foundation, Library, OCR, Smart Retrieval, Agent Integration;
- six-state badge;
- one plain-language summary;
- at most one key metric;
- full-card navigation to Module Detail;
- no Check, repair, configuration, destructive, or secondary action buttons.

On open, show Last Known Status immediately and refresh in the background. Never replace stale cached data with Not Enabled or Detection Failed before attempting refresh.

### 4.3 Foundation Detail

Default body:

- PaperForge version and compatibility in user language;
- current environment availability;
- update or recovery outcome when relevant.

Action rules:

| Condition | Contextual Primary Action |
|---|---|
| Ready | None |
| Foundation absent | Install PaperForge |
| Plugin/backend version mismatch | Complete Update |
| Environment damaged | Repair PaperForge |
| Detection failed | Retry |

Runtime slot, Python executable, raw path, rollback, and support logs are excluded from default content. Rollback remains an advanced recovery action and must target the previous runtime identity, not merely a matching version number.

### 4.4 Library Detail

A connection and synchronization workbench:

- Zotero connection state;
- corpus size;
- last synchronization and its result;
- current sync activity and progress;
- source configuration summary;
- an explicit Change flow for Zotero path and synchronization scope;
- a normal-use Sync Literature action inside the sync section, not as a health warning.

Zotero configuration exists only here and in the relevant Setup Journey stage.

### 4.5 OCR Detail

Settings body:

- OCR availability;
- usable, pending, running, and unusable result counts;
- current OCR activity;
- OCR provider and credential Configuration Summary;
- entry to the full-width OCR Operational Workspace.

The full-width workspace owns:

- all paper-level OCR records;
- filtering and sorting;
- selection and scope preview;
- paper-level failure explanation;
- batch reprocessing;
- live progress and cooperative stop.

An OCR result enters Maintenance only when it cannot support reading or retrieval and a concrete recovery action is likely to restore or improve it. Internal quality scores, ordinary OCR imperfections, and non-actionable low-confidence signals remain internal.

### 4.6 Smart Retrieval Detail

The body focuses on:

- retrievable papers versus Library total;
- coverage percentage;
- last successful build/update;
- current build activity;
- model/provider Configuration Summary;
- one build/update action only when backend facts authorize it.

Schema, vector dimensions, database paths, manifest internals, and “Memory Layer” terminology are excluded from user copy.

### 4.7 Agent Integration Detail

The body contains:

- selected agent platform;
- target deployment location as a safe summary;
- deployment state: Not Configured, Configured, Synchronized, or Synchronization Required;
- system and user Skills counts;
- Skills search, grouping, and enable/disable controls;
- Sync to Agent only when content drift exists.

Do not claim a live connection when integration is file deployment.

### 4.8 Maintenance

Maintenance contains only enabled-module problems that:

- block use;
- fail a requested task;
- make an output unusable; or
- create material data risk;

and have a concrete backend-authorized resolution.

Every item shows:

1. what happened;
2. what is and is not affected;
3. affected scope;
4. one next step.

Safe reversible retries may execute in place. Configuration, scoped, batch, or destructive work navigates to the owning Module Detail or Operational Workspace with context preserved. Optional modules never enabled, optimization suggestions, stale cache alone, and internal OCR quality signals are excluded. Successful resolution removes the item automatically.

### 4.9 Help

Help provides:

- getting-started entries for Library, OCR, Smart Retrieval, and Agent Integration;
- common task guidance;
- guidance for current User-visible Problems;
- one-click Copy Diagnostic Information;
- links to deeper documentation and issue reporting.

Help has no capability status badge.

## 5. User-visible problems and support diagnostics

All user-facing failures use:

1. **What happened** — direct, nontechnical title.
2. **Impact** — what cannot currently happen and what data/capability remains safe.
3. **Next step** — one concrete action.

**Copy Diagnostic Information** produces a privacy-safe clipboard report containing:

- timestamp;
- plugin and backend versions;
- module and internal state;
- stable reason/action IDs;
- recent attempted action;
- exit code or process outcome;
- bounded error excerpt.

It excludes secrets, environment variables containing credentials, document content, local username, and raw absolute paths. Paths are represented as logical locations. Copy completes in one action and announces success.

## 6. Activity and impact confirmation

Module Activity is separate from Module Status. Running work shows task name, progress or indeterminate activity, scope, and Stop when supported. Running work does not enter Maintenance; terminal failure may.

High-impact confirmation states:

- affected object count and scope;
- derived output that will be replaced;
- source and user data that remain preserved;
- whether work can be stopped;
- concrete confirmation verb.

Generic “Are you sure?” and raw backend destructive text are prohibited.

## 7. Responsive and accessibility contract

- Use Obsidian theme variables and native controls.
- Five module tabs appear above 620px container width; a native module select replaces them at or below 620px.
- Overview is two columns above 620px and one column below.
- No nested vertical scrolling or horizontal overflow in Settings.
- Every interaction supports keyboard activation and visible focus.
- Tab semantics and arrow-key behavior apply to top navigation and wide module switching.
- Focus returns to the originating card or maintenance item after back navigation or modal closure.
- Status and copied feedback use appropriate live regions.
- Impact confirmation traps focus, starts on Cancel, supports Escape, and restores focus.
- Reduced-motion preferences disable nonessential transitions.
- Status never relies on color alone.

## 8. Acceptance matrix

| Surface | Required observable contract |
|---|---|
| First open, incomplete | Four-stage Setup Journey; optional capabilities can be skipped; completion persists independently of health |
| Reopen, completed | Restore last top-level destination or selected module; refresh state; no draft/selection restoration |
| Overview | Three top-level destinations; five navigation-only Module Cards; one global refresh; baseline summary ignores Not Enabled optional modules |
| Refreshing | Last Known Status remains visible with separate activity; no false Pending/Not Enabled transition |
| Refresh failed | Detection Failed plus Retry and timestamped last successful state; plain-language impact and diagnostic copy |
| Detail navigation | No top-level Module Detail tab; fixed five-module shell; responsive select at narrow width; correct return context |
| Foundation Ready | No primary action and no Runtime/Python terminology in default body |
| Foundation mismatch | One Complete Update action; successful update refreshes Foundation and Help |
| Library | Connection, corpus, sync result/activity, and module-owned Zotero configuration appear in one workbench |
| OCR | Settings summary links to full workspace; only unusable actionable outcomes enter Maintenance |
| Smart Retrieval | Coverage and freshness are primary; Memory/vector/schema language remains internal |
| Agent Integration | Platform, deployment state, Skills search/group/toggles; no false live-connection wording |
| Maintenance empty | Clear no-action-needed state and no module-health fiction |
| Maintenance populated | Only qualifying problems; one action each; safe retry inline; complex work routes with context |
| Help | Task guidance, current problem guidance, one-click privacy-safe diagnostic, no health badge |
| Running work | Status and activity both visible; progress announced; Stop reachable; no Maintenance item until terminal failure |
| High-impact action | Scope, replacement, preservation, interruptibility, concrete confirm verb, focus restoration |
| Localization | Obsidian language by default, explicit override, no raw backend English labels in localized UI |
| Visual QA | Obsidian light/dark themes, 730px and 620px-adjacent widths, hover/focus/disabled/loading/empty/error states, no overflow |

## 9. Dependency-ordered implementation slices

Each slice must be one agent-ready issue and one authoritative worktree under the Ask Matt lifecycle.

1. **Capability presentation contract**
   Add stable action IDs, six-state mapping inputs, user-impact fields, preservation facts, and Maintenance eligibility. Separate internal OCR quality from User-visible OCR Failure. No UI redesign depends on backend prose after this slice.

2. **Shared control-center state and primitives**
   Implement Last Known Status refresh behavior, global Refresh Status, Support Diagnostic redaction, navigation memory, and reusable design-system primitives with a state showcase.

3. **Information architecture and Overview**
   Remove Module Detail as a top-level tab; render Overview/Maintenance/Help; replace six mixed cards with five navigation-only module cards and baseline summary.

4. **Setup Journey and Foundation**
   Implement durable Setup Completion, four dynamic stages, Foundation user model, one contextual action, and advanced recovery separation. Correct rollback to target previous runtime identity.

5. **Library module**
   Build the connection/synchronization workbench and move Zotero configuration ownership out of Foundation.

6. **Smart Retrieval module**
   Replace Memory user language; render coverage/update body; move provider configuration ownership; keep technical index facts internal.

7. **Agent Integration module**
   Add the fifth module contract, platform/deployment state, module-owned platform configuration, and Skills management.

8. **Maintenance and Help**
   Enforce qualifying-problem-only projection, contextual routing, task support, plain-language failure anatomy, and one-click Support Diagnostic.

9. **OCR module and Operational Workspace**
   Reduce Settings OCR detail to summary/configuration/workspace entry; build full-width paper-level filtering, selection, batch actions, progress, stop, and Impact Confirmation.

10. **Cutover and consistency cleanup**
    Delete legacy Installation/Runtime wording, duplicate Sync/Check controls, old four-module selector, raw backend labels, stale-as-pending mapping, inline duplicated styles, and obsolete tests. Run full Obsidian light/dark and responsive accessibility verification.

## 10. Non-goals

- A new visual brand independent of Obsidian.
- A general system-monitoring dashboard.
- Exposing raw probe envelopes or CLI commands to ordinary users.
- Treating optional capability adoption as maintenance debt.
- Showing every internal OCR quality concern.
- Embedding large operational tables inside Settings.
- Reintroducing a global health-derived `setup_complete` boolean.
