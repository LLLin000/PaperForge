# Phase ANN13: Bidirectional Navigation and Fallback Paths - Research

**Researched:** 2026-07-06  
**Domain:** PaperForge Obsidian Reading Canvas navigation, selection state, and v0.2 PDF fallback  
**Confidence:** MEDIUM-HIGH

## User Constraints (from CONTEXT.md)

### Locked Decisions

ANN13 makes the PaperForge Reading Canvas navigable after ANN12's source surface and anchor rendering work. Users can move from an annotation card to its supported source anchor, move from a source anchor back to the corresponding card, keep a clear selected state while reading, and use a safe v0.2 PDF page fallback when canvas source navigation cannot honestly locate the source. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]

- Card selection with an `exact` anchor scrolls to the inline exact highlight; `page-level` scrolls to the page/block marker; `unresolved` does not scroll and instead explains the limitation. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Missing DOM targets must not trigger guessing or automatic PDF fallback; keep the card selected, show an unable-to-locate status, and offer fallback only when eligible. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Source anchor selection focuses the corresponding card; page-level markers with multiple cards select a page-level group rather than pretending there is one exact target. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Paper changes and teardown clear all selection state; successful refresh may preserve selection only when the same card/anchor still exists, without auto-scrolling. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Escape clears card/source/group selection and temporary navigation status messages without changing scroll position. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- PDF fallback appears only when canvas source navigation is unavailable and a trustworthy v0.2 PDF/page target exists; it is triggered only by explicit user click on an "Open PDF page" button. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Fallback must be hidden when there is no trustworthy PDF path, no valid `pageIndex`, `sourceAttachmentKey` mismatch, or paper identity mismatch. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Cards, exact anchors, page-level markers, and fallback buttons are tabbable; Enter/Space activates them; selected states use `aria-selected`; unresolved status text is not tabbable. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- ANN13 must not add connector classes, connector geometry, SVG relationship paths, hover/selected line drawing, native Obsidian PDF viewer DOM dependency, mutation controls, fuzzy matching, or guessed jumps. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]

### the agent's Discretion

The planner may choose exact helper/module names, event wiring structure, selected CSS class names, status message wording, and test filenames as long as the locked navigation, lifecycle, fallback, accessibility, and safety decisions above are preserved. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]

### Deferred Ideas (OUT OF SCOPE)

Connector lines, connector geometry, hover/selected relationship drawing, SVG connector paths, and final visual relationship polish belong to ANN14. Full canvas verification and live harness recording belong to ANN15. Native PDF DOM anchoring, bundled PDF.js rendering, local annotation editing, Zotero write-back, persistent layout, AI cards, and multi-paper boards remain future scope. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]

## Summary

ANN13 should add a small navigation state layer over the already-built ANN11 card models and ANN12 anchor models, then wire that state to DOM focus/scroll and explicit PDF fallback actions. The existing code already exposes stable card IDs, anchor statuses, page indices, and v0.2 PDF resolution helpers, but rendered cards and anchors are not yet tabbable controls and `PaperForgeReadingCanvasView` still renders only an idle shell by default. [VERIFIED: codebase grep]

The safest implementation is a two-plan split: first create pure navigation/fallback helpers and tests, then add DOM/runtime event wiring, ARIA, keyboard handling, status copy, and focused regression gates. Do not loosen ANN12 anchor precision rules; ANN13 consumes `exact`, `page-level`, and `unresolved` rather than recomputing or guessing source positions. [VERIFIED: codebase grep]

**Primary recommendation:** Implement a pure `navigation.js` selection/fallback model, then wire cards and anchors as real focusable DOM targets in `render.js`/`main.js`, reusing `resolveAnnotationPdfTarget()` for explicit fallback. [VERIFIED: codebase grep]

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NAV-01 | Selecting a card focuses or scrolls to the corresponding source anchor when supported. | Existing cards expose `data-card-id`; anchors expose `anchorId`, `cardId`, status, page, and source span, but DOM needs stable anchor IDs and event wiring. [VERIFIED: paperforge/plugin/src/canvas/render.js:285] [VERIFIED: paperforge/plugin/src/canvas/anchors.js:240] |
| NAV-02 | Selecting a source anchor focuses the corresponding card. | `resolveCanvasAnchor()` returns `cardId`; renderer must add focusable anchor elements and look up matching cards by ID. [VERIFIED: paperforge/plugin/src/canvas/anchors.js:421] |
| NAV-03 | Unsupported canvas navigation can fall back to existing v0.2 PDF page navigation path. | `resolveAnnotationPdfTarget()` already performs attachment identity and page conversion checks; fallback must call this path only on explicit button click. [VERIFIED: paperforge/plugin/main.js:1742] |

## Project Constraints (from AGENTS.md)

- Preserve PaperForge's thin plugin/runtime boundary; plugin UI should not duplicate worker-owned business logic. [VERIFIED: AGENTS.md]
- Keep CommonJS plugin modules testable and modular; `main.js` should remain runtime integration rather than a second implementation of canvas helpers. [VERIFIED: AGENTS.md]
- New user-facing plugin text should be routed through `paperforge/plugin/i18n.js` with zh/en keys when practical. [VERIFIED: AGENTS.md]
- Use existing test commands and focused plugin tests before broader gates; existing guidance uses `node --check main.js` and focused plugin tests. [VERIFIED: AGENTS.md]
- Do not expose credentials, raw tracebacks, or raw shell output in user-facing UI. [VERIFIED: AGENTS.md]
- The local AGENTS file is partially encoding-corrupted, so only legible actionable directives were extracted. [VERIFIED: AGENTS.md]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Card-to-source target resolution | Browser / Client | Canvas pure helpers | It maps current DOM/card/anchor state to a target inside the PaperForge-owned canvas, not backend data. [VERIFIED: codebase grep] |
| Source-to-card focus | Browser / Client | Canvas render helpers | It requires DOM focus and lane scroll against already-rendered card elements. [VERIFIED: codebase grep] |
| Selection lifecycle | Browser / Client | Canvas controller | It is session-only UI state cleared on refresh, teardown, paper change, and Escape. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md] |
| PDF fallback eligibility | Canvas pure helpers | Obsidian runtime | Eligibility is pure, but the actual `openLinkText()` call belongs in `main.js`. [VERIFIED: paperforge/plugin/main.js:3207] |
| PDF file opening | Obsidian runtime | v0.2 helper | Opening uses Obsidian workspace APIs after v0.2 target resolution. [VERIFIED: paperforge/plugin/main.js:3193] |
| Keyboard/ARIA | Browser / Client | CSS | Focusability, `aria-selected`, Enter/Space, and Escape are DOM concerns. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md] |

## Code Findings

| Area | Finding | Planner Impact |
|------|---------|----------------|
| Anchor model | `resolveCanvasAnchor()` returns `anchorId`, `cardId`, `status`, `reason`, `matchCount`, `pageIndex`, `sourceSpan`, and diagnostics for exact/page-level/unresolved states. [VERIFIED: paperforge/plugin/src/canvas/anchors.js:240] | Build navigation from these fields; do not redo text matching in ANN13. |
| Exact anchors | Exact anchors are allowed only when `matchCount === 1`; page-level/unresolved preserve reasons. [VERIFIED: paperforge/plugin/src/canvas/anchors.js:417] | Exact card navigation can scroll to a specific highlight; page-level must scroll to marker/group only. |
| Card DOM | `renderCanvasCard()` creates a `div.paperforge-canvas-card` and sets `data-card-id`, but it is not focusable and has no selected ARIA state yet. [VERIFIED: paperforge/plugin/src/canvas/render.js:285] | Add `tabIndex=0`, `role` or semantic focus behavior, and `aria-selected` in ANN13. |
| Anchor DOM | Exact anchors render as plain `span.paperforge-canvas-anchor--exact`; page-level/unresolved render `div` markers/status, with no `data-anchor-id`, `data-card-id`, tabindex, or ARIA yet. [VERIFIED: paperforge/plugin/src/canvas/render.js:570] [VERIFIED: paperforge/plugin/src/canvas/render.js:471] | Add stable navigation attributes to exact and page-level anchors; keep unresolved text non-tabbable. |
| Source grouping | `renderCanvasSourceSurface()` currently groups anchors by `pageIndex`, then renders each source block with anchors for that page. [VERIFIED: paperforge/plugin/src/canvas/render.js:632] | Page-level group selection should use page/card collections derived from the same page grouping. |
| Source integration gap | `renderCanvasView()` `ready` state renders card lanes only; `renderCanvasSourceSurface()` is exported and tested separately, not integrated into `ready` rendering. [VERIFIED: paperforge/plugin/src/canvas/render.js:693] [VERIFIED: paperforge/plugin/src/canvas/render.js:611] | ANN13 should either integrate source+lanes into the ready view or explicitly add a wrapper render path before wiring navigation. |
| Runtime gap | `PaperForgeReadingCanvasView._buildViewModel()` currently returns an idle shell for valid context and does not load annotations/source into the canvas view-model. [VERIFIED: paperforge/plugin/main.js:4620] | Runtime plan must include a narrow load/build/render path or tests will only cover isolated helpers. |
| Source loading | `_loadCanvasSourceInputs()` reads `fulltext_path` first, falls back to `note_path`, and caches by paper key. [VERIFIED: paperforge/plugin/main.js:4505] | Refresh selection preservation must avoid auto-scroll and must invalidate/clear selection when paper key changes. |
| Teardown | `onClose()` tears down the session controller and clears paper/context/view-model fields. [VERIFIED: paperforge/plugin/main.js:4646] | Extend teardown to clear ANN13 selection/status and event listeners. |
| v0.2 fallback | `resolveAnnotationPdfTarget()` fails closed on attachment mismatch and converts zero-based `pageIndex` to one-based `#page=N`. [VERIFIED: paperforge/plugin/main.js:1728] | Fallback eligibility should call this helper and require `ok === true` plus valid page for "Open PDF page". |
| Runtime PDF open | `_openAnnotationPdf()` verifies the target file exists in the vault and opens via `app.workspace.openLinkText(result.linkText, '')`. [VERIFIED: paperforge/plugin/main.js:3193] | Canvas fallback should use the same mechanics but stay explicit and button-triggered. |
| Test baseline | v0.2 focused gate passed `annotation-navigation.test.mjs` plus related tests, while live Obsidian PDF viewer harness remains pending. [VERIFIED: .planning/phases/annotation-09-display-layer-verification-gate/annotation-09-VERIFICATION.md] | ANN13 can rely on automated fallback helper coverage but must not claim live native PDF overlay reliability. |

## Standard Stack

### Core

| Library / Runtime | Version | Purpose | Why Standard |
|-------------------|---------|---------|--------------|
| Obsidian plugin CommonJS runtime | Obsidian dev dependency `^1.12.0` in `paperforge/plugin/package.json` | ItemView, DOM creation, workspace PDF navigation. | Existing plugin architecture and tests already use it. [VERIFIED: paperforge/plugin/package.json] |
| Plain DOM APIs | Browser/Obsidian runtime | Focus, `scrollIntoView`, keyboard events, buttons, ARIA. | Existing renderer uses plain DOM helpers and `createEl` wrappers. [VERIFIED: paperforge/plugin/src/canvas/render.js:35] |
| Vitest | `^2.1.0` | Focused unit/runtime tests. | Existing plugin test script is `vitest run`. [VERIFIED: paperforge/plugin/package.json] |
| jsdom | `^25.0.0` | DOM tests for canvas cards, source anchors, keyboard/focus behavior. | Existing canvas DOM tests use jsdom. [VERIFIED: paperforge/plugin/package.json] |

### Supporting

| Library / Runtime | Version | Purpose | When to Use |
|-------------------|---------|---------|-------------|
| PowerShell | 5.1.26100.2161 available | Windows verification shell. | Use repository's existing PowerShell gate style. [VERIFIED: environment probe] |
| Node.js | v24.16.0 available | `node --check` and Vitest runtime. | Required for plugin syntax and tests. [VERIFIED: environment probe] |
| `npm.cmd` | 11.13.0 available | Runs tests despite PowerShell `npm.ps1` execution-policy block. | Use `npm.cmd test -- ...` in Windows gates. [VERIFIED: environment probe] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain DOM navigation | React/Svelte state layer | Out of scope; roadmap forbids new frontend frameworks for MVP. [VERIFIED: .planning/REQUIREMENTS.md] |
| Existing v0.2 PDF helper | New PDF target resolver | Higher safety risk and duplicate attachment/page logic. [VERIFIED: paperforge/plugin/main.js:1728] |
| Session-only selection | localStorage/settings persistence | Out of scope and violates read-only/no persistent layout boundary. [VERIFIED: .planning/REQUIREMENTS.md] |
| Exact DOM source anchoring | Native Obsidian PDF viewer selectors | Explicitly forbidden for ANN13 canvas navigation foundation. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md] |

**Installation:** No new package installation is recommended for ANN13. [VERIFIED: paperforge/plugin/package.json]

## Package Legitimacy Audit

No external packages should be installed in ANN13. The phase should use the existing `obsidian`, `vitest`, `jsdom`, and `obsidian-test-mocks` dev stack already present in `paperforge/plugin/package.json`. [VERIFIED: paperforge/plugin/package.json]

**Packages removed due to [SLOP] verdict:** none  
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```text
User click/keyboard
  -> card element OR exact/page-level source anchor OR fallback button
  -> navigation model helper
      -> exact anchor present?
          -> select card + anchor -> scroll source highlight -> keep DOM focus/ARIA in sync
      -> page-level marker?
          -> select page group -> scroll page marker -> highlight related cards
      -> unresolved or DOM target missing?
          -> keep/clear selection per lifecycle -> status message
          -> fallback eligible?
              -> show "Open PDF page" button
              -> explicit click -> resolveAnnotationPdfTarget() -> vault file check -> openLinkText()
  -> refresh/stale/teardown/paper change/Escape
      -> preserve only valid same-paper selection without auto-scroll OR clear with status
```

### Recommended Project Structure

```text
paperforge/plugin/src/canvas/
├── navigation.js        # new pure selection, target, group, and fallback eligibility helpers
├── controller.js        # extend session lifecycle or expose selection transition hooks
├── render.js            # focusable cards/anchors/buttons, ARIA, selected classes
├── view-model.js        # include source model/cards/anchors needed for one ready VM
└── index.js             # export narrow ANN13 helper surface
paperforge/plugin/
├── main.js              # thin runtime event coordinator and openLinkText fallback adapter
├── i18n.js              # navigation/fallback/status copy
└── styles.css           # selected/focus/status classes, no connector classes
```

### Pattern 1: Pure Navigation Model First

**What:** Add pure helpers that determine selected card, selected anchor, selected page group, temporary status, fallback eligibility, and lifecycle transitions. [VERIFIED: codebase grep]

**When to use:** Use for all card click, anchor click, refresh preservation, stale-load invalidation, paper change, teardown, and Escape transitions. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]

**Example:**

```javascript
// Source: local codebase pattern in src/canvas/controller.js and anchors.js
const SELECTION_KINDS = Object.freeze({
  NONE: 'none',
  CARD_ANCHOR: 'card-anchor',
  PAGE_GROUP: 'page-group',
});

function selectCardNavigationTarget(card, domAvailability, fallbackTarget) {
  if (!card || !card.id) {
    return { kind: SELECTION_KINDS.NONE, status: 'card-unavailable' };
  }
  if (card.anchor && card.anchor.status === 'exact' && domAvailability.anchorPresent) {
    return { kind: SELECTION_KINDS.CARD_ANCHOR, cardId: card.id, anchorId: card.anchor.anchorId, action: 'scroll-source' };
  }
  if (card.anchor && card.anchor.status === 'page-level' && domAvailability.pageMarkerPresent) {
    return { kind: SELECTION_KINDS.PAGE_GROUP, pageIndex: card.pageIndex, cardIds: domAvailability.pageCardIds, action: 'scroll-page-marker' };
  }
  return { kind: SELECTION_KINDS.CARD_ANCHOR, cardId: card.id, status: 'source-target-unavailable', fallbackTarget };
}
```

### Pattern 2: DOM Attributes as the Lookup Contract

**What:** Render cards and actionable anchors with stable IDs: `data-card-id`, `data-anchor-id`, `data-anchor-status`, and `data-page-index`. [VERIFIED: paperforge/plugin/src/canvas/render.js:285]

**When to use:** Use for event delegation and selection class updates; avoid relying on text content or index order. [VERIFIED: codebase grep]

**Example:**

```javascript
// Source: extends existing renderCanvasCard() data-card-id pattern
cardEl.tabIndex = 0;
cardEl.setAttribute('role', 'button');
cardEl.setAttribute('aria-selected', isSelected ? 'true' : 'false');
cardEl.setAttribute('data-card-id', card.id || '');
cardEl.setAttribute('data-anchor-id', card.anchor && card.anchor.anchorId || '');
```

### Pattern 3: Explicit Fallback Action

**What:** Show a real fallback `button` only when navigation is unresolved/unavailable and `resolveAnnotationPdfTarget(row, entry)` returns a trusted page target. [VERIFIED: paperforge/plugin/main.js:1742]

**When to use:** Use for unresolved anchors, missing DOM target, source unavailable, or unsupported canvas navigation; never call it automatically on card/source selection. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]

**Example:**

```javascript
// Source: existing fallback path in main.js _openAnnotationPdf()
function openCanvasPdfFallback(row, entry, app) {
  const result = resolveAnnotationPdfTarget(row, entry);
  if (!result.ok || result.page == null) return { ok: false, reason: result.reason || 'No PDF page target.' };
  const file = app.vault.getAbstractFileByPath(result.path);
  if (!file) return { ok: false, reason: 'PDF file not found in vault.' };
  app.workspace.openLinkText(result.linkText, '');
  return { ok: true };
}
```

### Anti-Patterns to Avoid

- **Auto-jumping to PDF on unresolved card selection:** Violates D-16 and surprises users by leaving the canvas. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- **Using `pageLabel` for navigation arithmetic:** v0.2 uses machine `pageIndex`, not display label. [VERIFIED: paperforge/plugin/main.js:1802]
- **Making unresolved status tabbable:** It has no action; fallback button is the action. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- **Selecting one card from a multi-card page marker:** Page-level source markers may represent multiple cards and should produce group selection. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- **Adding connector/SVG classes in selected-state CSS:** Connector work belongs to ANN14. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF attachment/page safety | New target resolver | `resolveAnnotationPdfTarget()` plus vault existence check | Existing v0.2 helper already fails closed on attachment mismatch and handles page conversion. [VERIFIED: paperforge/plugin/main.js:1742] |
| Text matching / anchor precision | New fuzzy source matching | ANN12 `resolveCanvasAnchor()` output | ANN12 already owns exact/page-level/unresolved precision and downgrade reasons. [VERIFIED: paperforge/plugin/src/canvas/anchors.js:240] |
| Persistent selection/layout | localStorage, settings, `.canvas` writes | Session-only navigation state | v0.3 safety forbids persistent layout/state writes. [VERIFIED: .planning/REQUIREMENTS.md] |
| Native PDF DOM navigation | `.pdf-viewer`, `.pdf-embed`, `[data-page-number]` selectors | PaperForge-owned canvas DOM and explicit PDF fallback | Native PDF viewer internals remain risk-gated and live harness is pending. [VERIFIED: .planning/phases/annotation-09-display-layer-verification-gate/annotation-09-VERIFICATION.md] |

**Key insight:** ANN13 is an interaction layer over existing tested data contracts; creating new data matching or PDF resolution logic would weaken the safety boundary. [VERIFIED: codebase grep]

## Common Pitfalls

### Pitfall 1: Treating Page-Level as Exact

**What goes wrong:** A page marker selection focuses one card or highlights a sentence, implying precision the data does not support. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]  
**Why it happens:** Existing source rendering groups anchors by page index, which is convenient but not a one-to-one source span. [VERIFIED: paperforge/plugin/src/canvas/render.js:632]  
**How to avoid:** Implement page group selection with related card IDs and a distinct selected-page class. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]  
**Warning signs:** Tests select a page marker and assert only one card is selected. [VERIFIED: codebase grep]

### Pitfall 2: Runtime Helper Drift

**What goes wrong:** Pure helper tests pass while the real `PaperForgeReadingCanvasView` still renders idle or lacks source/card DOM. [VERIFIED: paperforge/plugin/main.js:4620]  
**Why it happens:** ANN12 source surface helpers are exported and tested separately, while `renderCanvasView()` ready state currently renders lanes only. [VERIFIED: paperforge/plugin/src/canvas/render.js:693]  
**How to avoid:** Add runtime tests that set loaded annotation/source state and verify the real canvas DOM has cards, source anchors, selected state, and fallback buttons. [VERIFIED: codebase grep]  
**Warning signs:** Tests call `renderCanvasSourceSurface()` directly but never instantiate `PaperForgeReadingCanvasView`. [VERIFIED: paperforge/plugin/tests/canvas-render.test.mjs]

### Pitfall 3: Fallback Button Eligibility Too Broad

**What goes wrong:** The canvas offers "Open PDF page" even with invalid page, attachment mismatch, or ambiguous multi-PDF entry. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]  
**Why it happens:** v0.2 permits opening a PDF without a page for some row-list scenarios, but ANN13's fallback copy is specifically page fallback. [VERIFIED: paperforge/plugin/main.js:1820]  
**How to avoid:** For ANN13 fallback button, require `resolveAnnotationPdfTarget(...).ok === true` and `page !== null`, plus vault file existence. [VERIFIED: paperforge/plugin/main.js:1807]  
**Warning signs:** Fallback tests pass when `pageIndex` is null, negative, fractional, or a string. [VERIFIED: paperforge/plugin/tests/annotation-navigation.test.mjs]

### Pitfall 4: Auto-Scroll During Refresh

**What goes wrong:** A refresh preserves selected ID and calls `scrollIntoView`, stealing the user's reading position. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]  
**Why it happens:** Selection preservation and navigation activation are conflated. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]  
**How to avoid:** Store an activation reason; only explicit card/source activation may scroll. Refresh may restore CSS/ARIA selection only. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]

### Pitfall 5: Keyboard Support Without Real Focus

**What goes wrong:** Visual selected classes change, but screen readers and keyboard users cannot reach or activate cards/anchors. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]  
**Why it happens:** Current cards and anchors are non-focusable `div`/`span` elements. [VERIFIED: paperforge/plugin/src/canvas/render.js:286] [VERIFIED: paperforge/plugin/src/canvas/render.js:570]  
**How to avoid:** Add `tabIndex=0`, activation key handlers, `aria-selected`, and real `button` elements for fallback. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]

## Implementation Approach

1. Add `paperforge/plugin/src/canvas/navigation.js` with pure helpers for selection state, target lookup decisions, page-group membership, fallback eligibility, refresh preservation, stale invalidation, teardown clearing, and Escape clearing. [VERIFIED: codebase grep]
2. Extend card/anchor view-model data so the navigation helper can map card IDs to original annotation rows for fallback, and to anchor IDs/page groups for source navigation. [VERIFIED: paperforge/plugin/src/canvas/view-model.js:118]
3. Extend `renderCanvasCard()`, `renderSourceBlock()`, `renderPageLevelAnchorMarker()`, and exact anchor rendering to add stable `data-*` attributes, focusability, selected classes, and ARIA without adding connector classes. [VERIFIED: paperforge/plugin/src/canvas/render.js:285]
4. Integrate source surface rendering into the loaded canvas DOM so a single ready view contains source surface plus left/right lanes; direct helper-only rendering is insufficient for runtime navigation tests. [VERIFIED: paperforge/plugin/src/canvas/render.js:693]
5. Add a thin runtime coordinator in `PaperForgeReadingCanvasView` for delegated clicks/keydowns, `scrollIntoView({ block: 'center', inline: 'nearest' })`, focus, Escape, status messages, and explicit PDF fallback. [VERIFIED: paperforge/plugin/main.js:4404]
6. Reuse `resolveAnnotationPdfTarget()` and the same vault existence plus `openLinkText()` mechanics for fallback; do not introduce a new PDF target contract. [VERIFIED: paperforge/plugin/main.js:3193]
7. Add i18n keys for unable-to-locate, card unavailable, previous selection unavailable, source target unavailable, page group selected, and "Open PDF page". [VERIFIED: paperforge/plugin/i18n.js]
8. Add selected/focus/status CSS under `.paperforge-reading-canvas-view`; avoid `paperforge-canvas-connector`, `<svg>`, relationship-line wording, and native PDF selectors. [VERIFIED: paperforge/plugin/styles.css:2923]

## Recommended Plan Decomposition

### ANN13-01: Pure Navigation, Selection, and Fallback Eligibility

**Files:** `src/canvas/navigation.js`, `src/canvas/view-model.js`, `src/canvas/index.js`, `tests/canvas-navigation.test.mjs`, extend `annotation-navigation.test.mjs` if needed. [VERIFIED: codebase grep]

**Scope:**
- Define selection state shapes: none, card-anchor, page-group, temporary unavailable status. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Implement card-to-source target resolution for exact, page-level, unresolved, missing DOM target, and stale/missing card cases. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Implement source-to-card selection including single-card exact selection and multi-card page group selection. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Implement lifecycle reducers for refresh preserve/clear, stale load, paper change, teardown, and Escape. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Implement fallback eligibility over card row + paper entry using v0.2 target helper semantics; require valid page for ANN13 "Open PDF page". [VERIFIED: paperforge/plugin/main.js:1807]

**Gate:**

```powershell
Push-Location paperforge/plugin
node --check src/canvas/navigation.js
npm.cmd test -- canvas-navigation.test.mjs annotation-navigation.test.mjs canvas-source-anchor.test.mjs canvas-viewmodel.test.mjs
Pop-Location
```

### ANN13-02: DOM/Runtime Wiring, Keyboard, ARIA, and Final Fallback Gate

**Files:** `main.js`, `src/canvas/render.js`, `styles.css`, `i18n.js`, `tests/canvas-render.test.mjs`, `tests/canvas-card-dom.test.mjs`, `tests/canvas-main-runtime.test.mjs`. [VERIFIED: codebase grep]

**Scope:**
- Render focusable cards, exact anchors, and page-level markers with `data-card-id`, `data-anchor-id`, `data-page-index`, `tabIndex`, and `aria-selected`. [VERIFIED: paperforge/plugin/src/canvas/render.js:285]
- Keep unresolved statuses non-tabbable, but render fallback as a real `button` only when eligible. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Add delegated click and keydown handling for Enter/Space activation and Escape clearing. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Apply selected classes to card, exact anchor/page marker, and page group related cards; no connector or SVG classes. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Use `scrollIntoView()` only for explicit activation, never during refresh/stale re-render preservation. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
- Add runtime tests for the real `PaperForgeReadingCanvasView` event path, fallback button click, no auto-jump on selection, and teardown/Escape cleanup. [VERIFIED: paperforge/plugin/tests/canvas-main-runtime.test.mjs]

**Gate:**

```powershell
Push-Location paperforge/plugin
node --check main.js
node --check src/canvas/render.js
node --check src/canvas/navigation.js
npm.cmd test -- canvas-navigation.test.mjs canvas-source-anchor.test.mjs canvas-viewmodel.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs annotation-navigation.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs
Pop-Location
```

### Optional ANN13-03 Only If ANN13-02 Grows Too Large

Split out final runtime integration if `PaperForgeReadingCanvasView` must first be upgraded from idle shell to loaded source+cards rendering. This should be a planner call, not a new feature expansion. [VERIFIED: paperforge/plugin/main.js:4620]

## Code Examples

### Selection Reducer Shape

```javascript
// Source: local controller pattern in paperforge/plugin/src/canvas/controller.js
function clearSelection(reason) {
  return {
    selectedCardId: null,
    selectedAnchorId: null,
    selectedPageIndex: null,
    selectedGroupCardIds: [],
    status: reason || null,
    fallbackTarget: null,
  };
}

function preserveSelectionAfterRefresh(previous, nextCardsById) {
  if (!previous || !previous.selectedCardId) return clearSelection(null);
  if (nextCardsById.has(previous.selectedCardId)) {
    return { ...previous, status: null, shouldAutoScroll: false };
  }
  return clearSelection('previous-selection-unavailable');
}
```

### Delegated Activation Pattern

```javascript
// Source: existing DOM event style in main.js and render.js
function isActivationKey(event) {
  return event.key === 'Enter' || event.key === ' ';
}

contentEl.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    this._clearCanvasSelection('escape');
    event.preventDefault();
    return;
  }
  if (isActivationKey(event) && event.target.closest('[data-card-id], [data-anchor-id], [data-fallback-card-id]')) {
    this._activateCanvasNavigationTarget(event.target);
    event.preventDefault();
  }
});
```

### Fallback Button Eligibility

```javascript
// Source: v0.2 resolveAnnotationPdfTarget() contract in main.js
function buildPdfFallbackTarget(row, entry) {
  const result = resolveAnnotationPdfTarget(row, entry);
  if (!result.ok || result.page == null) {
    return { eligible: false, reason: result.reason || 'No PDF page target.' };
  }
  return {
    eligible: true,
    path: result.path,
    page: result.page,
    linkText: result.linkText,
  };
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v0.2 row page badge opens PDF/page from annotation list. | ANN13 uses canvas source navigation first, then explicit PDF page fallback only when canvas navigation cannot locate source. | ANN13 scope on 2026-07-06 | Keeps the canvas useful without auto-jumping away from it. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md] |
| Native PDF overlay as display enhancement. | PaperForge-owned reading surface and anchors are the v0.3 foundation; native PDF overlay remains separate/pending live harness. | v0.3 roadmap | Avoids unstable Obsidian PDF DOM dependency. [VERIFIED: .planning/ROADMAP.md] |
| Card/source navigation deferred. | ANN13 implements selection and bidirectional focus before connector lines. | ANN13 roadmap phase | Makes the canvas navigable before visual relationship lines are added. [VERIFIED: .planning/ROADMAP.md] |

**Deprecated/outdated for ANN13:**
- Whole-row click navigation: v0.2 chose explicit page badge controls; ANN13 should keep explicit controls for fallback. [VERIFIED: .planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md]
- Always opening main PDF when uncertain: v0.2 fails closed on attachment identity mismatch. [VERIFIED: paperforge/plugin/main.js:1775]
- Native PDF viewer DOM selectors for canvas navigation: explicitly forbidden. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `scrollIntoView({ block: 'center', inline: 'nearest' })` is acceptable in the Obsidian desktop DOM for ANN13 navigation. [ASSUMED] | Implementation Approach | If Obsidian panes handle scroll containers differently, runtime tests may need a wrapper seam around scrolling. |
| A2 | A `div`/`span` with `tabIndex=0` and keyboard activation is acceptable for current card/anchor elements instead of changing them to buttons. [ASSUMED] | Architecture Patterns | If accessibility review requires native buttons, render structure changes more substantially. |

## Open Questions (RESOLVED)

1. **Should ANN13 integrate full annotation/source loading into `PaperForgeReadingCanvasView` or keep using injected test states until ANN15?**
   - What we know: current `PaperForgeReadingCanvasView._buildViewModel()` returns idle for valid context. [VERIFIED: paperforge/plugin/main.js:4620]
   - Resolution: ANN13 must include mandatory loaded cards + source surface runtime rendering in `PaperForgeReadingCanvasView`; this is planned in `ANN13-04-PLAN.md` and is no longer conditional. [RESOLVED: 2026-07-06]
   - Rationale: NAV-01 and NAV-02 require real card/source DOM in one runtime tree, not only injected helper tests. [VERIFIED: .planning/ROADMAP.md]

2. **Should fallback require valid `page` or allow plain PDF open?**
   - What we know: ANN13 context says fallback copy is "Open PDF page" and hide when no valid `pageIndex`. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]
   - Resolution: ANN13 fallback requires a valid page target and does not show a plain-PDF degraded fallback. [RESOLVED: 2026-07-06]
   - Rationale: The UI copy is explicitly "Open PDF page"; a plain PDF open would overstate the fallback precision. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node.js | `node --check`, Vitest | yes | v24.16.0 | none needed [VERIFIED: environment probe] |
| `npm.cmd` | Windows test command | yes | 11.13.0 | Use `npm.cmd`; plain `npm` is blocked by PowerShell execution policy. [VERIFIED: environment probe] |
| PowerShell | Planner verification commands | yes | 5.1.26100.2161 | none needed [VERIFIED: environment probe] |

**Missing dependencies with no fallback:** none found. [VERIFIED: environment probe]

**Missing dependencies with fallback:**
- `npm --version` via `npm.ps1` is blocked by execution policy; use `npm.cmd`. [VERIFIED: environment probe]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest `^2.1.0` with jsdom `^25.0.0` [VERIFIED: paperforge/plugin/package.json] |
| Config file | `paperforge/plugin/vitest.config.*` implied by existing test command; exact file not inspected in this research. [ASSUMED] |
| Quick run command | `Push-Location paperforge/plugin; npm.cmd test -- canvas-navigation.test.mjs; Pop-Location` [VERIFIED: paperforge/plugin/package.json] |
| Full focused command | `Push-Location paperforge/plugin; npm.cmd test -- canvas-navigation.test.mjs canvas-source-anchor.test.mjs canvas-viewmodel.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs annotation-navigation.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs; Pop-Location` [VERIFIED: codebase grep] |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| NAV-01 | Card selection scrolls/focuses exact or page-level source target; unresolved does not scroll. | unit + DOM/runtime | `npm.cmd test -- canvas-navigation.test.mjs canvas-render.test.mjs canvas-main-runtime.test.mjs` | no, Wave 0 creates/extends [VERIFIED: codebase grep] |
| NAV-02 | Source anchor focuses card; page-level marker selects group. | unit + DOM/runtime | `npm.cmd test -- canvas-navigation.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs` | no, Wave 0 creates/extends [VERIFIED: codebase grep] |
| NAV-03 | Unsupported canvas navigation shows explicit safe PDF fallback. | unit + runtime | `npm.cmd test -- canvas-navigation.test.mjs annotation-navigation.test.mjs canvas-main-runtime.test.mjs` | partial, `annotation-navigation.test.mjs` exists [VERIFIED: paperforge/plugin/tests/annotation-navigation.test.mjs] |

### Sampling Rate

- **Per task commit:** `Push-Location paperforge/plugin; npm.cmd test -- canvas-navigation.test.mjs; Pop-Location` [VERIFIED: paperforge/plugin/package.json]
- **Per wave merge:** focused command listed above plus `node --check main.js` and `node --check src/canvas/navigation.js`. [VERIFIED: codebase grep]
- **Phase gate:** focused ANN13 + v0.2 annotation navigation/runtime DOM gates green before verify-work. [VERIFIED: .planning/phases/annotation-09-display-layer-verification-gate/annotation-09-VERIFICATION.md]

### Wave 0 Gaps

- [ ] `paperforge/plugin/src/canvas/navigation.js` - pure selection and fallback helpers. [VERIFIED: codebase grep]
- [ ] `paperforge/plugin/tests/canvas-navigation.test.mjs` - model-level selection lifecycle and fallback eligibility tests. [VERIFIED: codebase grep]
- [ ] Runtime loaded-state harness in `canvas-main-runtime.test.mjs` - proves the real view renders source+cards and handles events. [VERIFIED: paperforge/plugin/tests/canvas-main-runtime.test.mjs]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | Local Obsidian plugin feature has no auth boundary in ANN13. [VERIFIED: .planning/REQUIREMENTS.md] |
| V3 Session Management | yes | Session-only selection state cleared on paper change, refresh invalidation, teardown, and Escape. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md] |
| V4 Access Control | yes | Read-only UI; no create/edit/delete/save/import/apply/write-back/evidence mutation controls. [VERIFIED: .planning/REQUIREMENTS.md] |
| V5 Input Validation | yes | Use ANN12 anchor status and v0.2 PDF target validation; no fuzzy source guesses. [VERIFIED: paperforge/plugin/src/canvas/anchors.js:240] |
| V6 Cryptography | no | No cryptography in phase scope. [VERIFIED: .planning/REQUIREMENTS.md] |

### Known Threat Patterns for ANN13

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Wrong-paper stale selection after refresh/paper change | Spoofing | Key selection by paper and clear when card/anchor is absent. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md] |
| Misleading evidence precision | Tampering | Treat exact/page-level/unresolved distinctly; no fuzzy jumps. [VERIFIED: paperforge/plugin/src/canvas/anchors.js:417] |
| Unsafe fallback to wrong attachment | Spoofing | Reuse `resolveAnnotationPdfTarget()` fail-closed attachment matching. [VERIFIED: paperforge/plugin/main.js:1766] |
| DOM injection through status/reason copy | Tampering | Continue safe `textContent`/text node rendering pattern. [VERIFIED: paperforge/plugin/src/canvas/render.js:454] |
| Keyboard trap or inaccessible selection | Denial of Service | Natural tab order, Enter/Space activation, Escape clear, real buttons for fallback. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md] |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Current ready render path lacks integrated source surface. [VERIFIED: paperforge/plugin/src/canvas/render.js:693] | Navigation tests may pass only against isolated helper DOM. | Include runtime loaded-state integration in ANN13-02. |
| Fallback eligibility accidentally inherits v0.2 plain-PDF degradation. [VERIFIED: paperforge/plugin/main.js:1820] | Button says "Open PDF page" but opens PDF without page. | For ANN13, require `page !== null` before rendering fallback button. |
| Selection preserved on refresh triggers scroll. [VERIFIED: .planning/phases/ANN13/ANN13-CONTEXT.md] | User loses reading position. | Separate "selected state preservation" from "explicit navigation activation". |
| Page-level group has many cards. [VERIFIED: paperforge/plugin/src/canvas/render.js:632] | Lane scroll/focus could be noisy. | Highlight group and focus first related card only when user activates a specific card; marker activation should announce/select group. |
| ARIA added inconsistently. [ASSUMED] | Accessibility regressions. | Tests assert `aria-selected` on cards and actionable anchors after each selection transition. |

## Sources

### Primary

- `.planning/PROJECT.md` - v0.3 read-only canvas direction and v0.2 harness caveat. [VERIFIED: file read]
- `.planning/REQUIREMENTS.md` - NAV, SAFE, TEST requirements and scope fences. [VERIFIED: file read]
- `.planning/ROADMAP.md` - ANN13 success criteria and phase ordering. [VERIFIED: file read]
- `.planning/STATE.md` - ANN12 completion state and next-phase context. [VERIFIED: file read]
- `.planning/phases/ANN13/ANN13-CONTEXT.md` - locked ANN13 decisions. [VERIFIED: file read]
- `.planning/phases/ANN12/ANN12-CONTEXT.md`, `ANN12-01-PLAN.md`, `ANN12-02-PLAN.md`, `ANN12-VALIDATION.md` - source/anchor contracts and validation boundary. [VERIFIED: file read]
- `.planning/phases/ANN11/ANN11-CONTEXT.md` - card model, lane, and read-only card constraints. [VERIFIED: file read]
- `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md` - v0.2 PDF jump safety decisions. [VERIFIED: file read]
- `.planning/phases/annotation-09-display-layer-verification-gate/annotation-09-VERIFICATION.md` - automated v0.2 gate and pending live harness. [VERIFIED: file read]
- `paperforge/plugin/main.js`, `src/canvas/anchors.js`, `src/canvas/render.js`, `src/canvas/view-model.js`, `src/canvas/controller.js`, `src/testable.js`, and focused tests listed by the user. [VERIFIED: codebase grep]

### Secondary

- Environment probes for Node.js, `npm.cmd`, and PowerShell availability. [VERIFIED: environment probe]

### Tertiary

- No external web or package-registry sources were used; this phase is constrained by local code and planning artifacts. [VERIFIED: execution log]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies; versions read from local package and environment. [VERIFIED: paperforge/plugin/package.json]
- Architecture: MEDIUM-HIGH - local code seams are clear, but runtime ready-state integration needs implementation confirmation. [VERIFIED: paperforge/plugin/main.js:4620]
- Pitfalls: HIGH - risks are directly evidenced by local code and prior v0.2/ANN12 artifacts. [VERIFIED: codebase grep]
- Live Obsidian PDF behavior: MEDIUM - automated v0.2 gate passed, live native PDF harness remains pending. [VERIFIED: .planning/phases/annotation-09-display-layer-verification-gate/annotation-09-VERIFICATION.md]

**Research date:** 2026-07-06  
**Valid until:** 2026-08-05, unless ANN13 implementation changes the canvas render/runtime seams first.

## RESEARCH COMPLETE
