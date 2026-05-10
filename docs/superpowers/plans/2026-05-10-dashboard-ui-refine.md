# Dashboard UI Refine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the PaperForge Obsidian dashboard so `paper`, `collection`, and `global` modes feel stable, readable, and visually intentional while fixing the current layout and interaction defects.

**Architecture:** Keep the existing three-mode dashboard structure in `paperforge/plugin/main.js`, but reduce refresh-related state loss and clean up the dashboard CSS into one authoritative visual system in `paperforge/plugin/styles.css`. Preserve Obsidian structural tokens for surfaces/text/borders, then layer a muted PaperForge accent system on top for badges, metrics, pills, and primary actions.

**Tech Stack:** Obsidian plugin DOM API, CommonJS plugin runtime, Vitest, CSS custom properties, Obsidian theme variables.

---

## File Structure

- Modify: `paperforge/plugin/main.js`
  - Dashboard leaf activation / refresh behavior
  - Paper-mode transient state preservation
  - Small DOM/class adjustments only if required by the new visual system
- Modify: `paperforge/plugin/styles.css`
  - Consolidate duplicate dashboard CSS
  - Add stable scroll / bottom-safe-area behavior
  - Implement the `Quiet Research Desk` palette and hierarchy rules
- Modify: `docs/ux-contract.md`
  - Update workflow contract expectations for `paper`, `collection`, and `global`
- Test: `paperforge/plugin/tests/*.mjs`
  - Keep existing suite green
  - Add a focused regression test only if a new pure helper or testable branch is extracted

---

### Task 1: Lock Scroll Stability and Preserve the Existing Refresh Fix

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/styles.css`
- Test: `paperforge/plugin/tests/*.mjs`

- [ ] **Step 1: Add a regression note to the plan execution log**

Record the two interaction defects at the top of your execution scratchpad / task notes to preserve focus during implementation:

```text
- First discussion expand must not collapse on first click.
- Technical-details expand must not trigger width jump from late scrollbar appearance.
```

- [ ] **Step 2: Verify the current automated baseline before edits**

Run: `npm test`
Workdir: `paperforge/plugin`
Expected: `40 passed` (or current equivalent with zero failures)

- [ ] **Step 3: Verify the existing discussion-refresh fix remains intact**

Do not re-implement the `active-leaf-change` guard if it is already present. Instead, confirm the current `main.js` logic still short-circuits leaf-focus-only transitions and does not get accidentally removed while refining UI code.

Verification target:

```text
If resolved mode and file path are unchanged, active-leaf-change must not rebuild the mode tree.
```

This protection must continue to preserve both:

```text
- discussion expanded/collapsed state
- technical-details expanded/collapsed state
```

- [ ] **Step 4: Stabilize the root scroll container in `styles.css`**

Apply bottom safe-area and stable vertical scrollbar behavior at the dashboard container level.

Implementation shape:

```css
.paperforge-status-panel {
    overflow-y: auto;
    scrollbar-gutter: stable;
    padding: 14px 14px 56px 14px;
}
```

If `scrollbar-gutter` alone is insufficient during manual verification, add a compatible fallback without changing mode structure, for example a permanent vertical overflow reservation strategy at the same container boundary.

- [ ] **Step 5: Run the automated suite again**

Run: `npm test`
Workdir: `paperforge/plugin`
Expected: zero failures

- [ ] **Step 6: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/styles.css
git commit -m "fix: stabilize dashboard leaf refresh and scroll layout"
```

---

### Task 2: Consolidate Dashboard CSS Authority

**Files:**
- Modify: `paperforge/plugin/styles.css`
- Test: `paperforge/plugin/tests/*.mjs`

- [ ] **Step 1: Identify the authoritative dashboard section blocks**

Use the existing redesign spec as the source of truth and remove overlapping duplicate selector definitions for:

```text
.paperforge-section-label
.paperforge-contextual-btn
.paperforge-status-strip
.paperforge-paper-overview
.paperforge-discussion-card
.paperforge-technical-details*
.paperforge-workflow-overview*
.paperforge-library-snapshot*
.paperforge-system-status*
.paperforge-global-actions*
.paperforge-workflow-toggles*
```

- [ ] **Step 2: Rewrite to one authoritative visual system**

Prefer a single final selector block per dashboard component family. Do not stack another layer of overrides at the bottom of the file.

Target structure:

```css
/* shared tokens */
/* paper mode */
/* collection mode */
/* global mode */
/* dark theme overrides */
```

- [ ] **Step 3: Introduce muted PaperForge accent tokens**

Keep surfaces/text/borders Obsidian-native, and add a restrained PaperForge tint layer.

Implementation shape:

```css
.paperforge-status-panel {
    --pf-paper-accent: ...;
    --pf-collection-accent: ...;
    --pf-global-accent: ...;
    --pf-warm-line: ...;
}
```

Do not apply these as large full-card backgrounds.

- [ ] **Step 4: Run the automated suite**

Run: `npm test`
Workdir: `paperforge/plugin`
Expected: zero failures

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/styles.css
git commit -m "refactor: unify dashboard style system"
```

---

### Task 3: Rebalance Paper Mode

**Files:**
- Modify: `paperforge/plugin/styles.css`
- Modify: `paperforge/plugin/main.js` (only if a class hook is needed)
- Test: `paperforge/plugin/tests/*.mjs`

- [ ] **Step 1: Raise paper-mode comfort without changing module order**

Keep the existing order:

```text
paper header
status/file row
overview card
next-step or complete row
discussion card
technical details
```

- [ ] **Step 2: Make technical details lighter than primary cards**

Use disclosure styling that reads as metadata, not as a full secondary card.

Implementation shape:

```css
.paperforge-technical-details-toggle {
    width: 100%;
    min-height: 34px;
}

.paperforge-technical-details-body {
    padding-top: 8px;
}
```

- [ ] **Step 3: Keep file actions neutral and discussion readable**

Preserve neutral file-opening actions in `paper` mode; do not promote them with strong tinting. Maintain body copy at `14px` minimum and keep discussion/overview as the most legible blocks.

- [ ] **Step 4: Run the automated suite**

Run: `npm test`
Workdir: `paperforge/plugin`
Expected: zero failures

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/styles.css
git commit -m "style: rebalance paper mode for reading"
```

---

### Task 4: Strengthen Collection and Global Hierarchy

**Files:**
- Modify: `paperforge/plugin/styles.css`
- Modify: `paperforge/plugin/main.js` (only if action classes or wrappers need a tiny hook)
- Test: `paperforge/plugin/tests/*.mjs`

- [ ] **Step 1: Scale up collection metrics and workflow stage presence**

Meet the measured targets from the spec:

```css
.paperforge-workflow-stage {
    min-width: 72px;
}

.paperforge-snapshot-pill {
    min-width: 72px;
}

.paperforge-collection-actions .paperforge-contextual-btn,
.paperforge-global-actions-row .paperforge-contextual-btn {
    font-size: 13px;
}

.paperforge-workflow-stage-value,
.paperforge-snapshot-value {
    font-size: 22px;
}
```

Also keep `collection` / `global` labels and detail text at spec minimums:

```css
.paperforge-workflow-stage-label,
.paperforge-snapshot-label {
    font-size: 11px;
}

.paperforge-section-label {
    font-size: 12px;
}

.paperforge-status-label,
.paperforge-status-detail,
.paperforge-collection-count {
    font-size: 13px;
}
```

- [ ] **Step 2: Promote the primary actions explicitly**

Apply stronger but muted emphasis only to:

```text
global: Open Literature Hub
collection: Run OCR
```

Keep `Sync Library` secondary in both modes.

Enforce button size targets while doing this:

```css
.paperforge-collection-actions .paperforge-contextual-btn,
.paperforge-global-actions-row .paperforge-contextual-btn {
    min-height: 36px;
}
```

- [ ] **Step 3: Increase global homepage presence without changing inventory/order**

Keep the current order:

```text
library snapshot
system status
optional issues
start working
```

Make cards, labels, and controls read as a homepage rather than a compact utility panel.
Keep the OCR module visually heavier than the collection action row by giving the OCR section stronger padding / surface presence than the actions beneath it.

- [ ] **Step 4: Run the automated suite**

Run: `npm test`
Workdir: `paperforge/plugin`
Expected: zero failures

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/styles.css
git commit -m "style: strengthen collection and global dashboard hierarchy"
```

---

### Task 5: Update UX Contract and Final Verification

**Files:**
- Modify: `docs/ux-contract.md`
- Test: `paperforge/plugin/tests/*.mjs`

- [ ] **Step 1: Update Workflow 4 contract entries**

Reflect the refined dashboard expectations in `docs/ux-contract.md`:

```text
- paper mode bottom-safe-area expectation
- no scrollbar reflow on technical-details expand
- no first-click discussion collapse
- preserved module order for collection mode
- collection-mode issues remain scoped inside the collection view rather than being promoted into a separate extra module
- preserved module order for global mode
- light/dark theme verification expectation
```

- [ ] **Step 2: Run the full automated suite**

Run: `npm test`
Workdir: `paperforge/plugin`
Expected: zero failures

- [ ] **Step 3: Perform manual verification in Obsidian desktop**

Checklist:

```text
- Windows light theme: paper bottom content is fully visible
- Windows light theme: technical details expand without width jump
- Windows light theme: first discussion expand does not flash closed
- Windows light theme: with discussion expanded, leaf activation alone does not collapse it when resolved identity is unchanged
- Windows light theme: with technical details expanded, leaf activation alone does not collapse it when resolved identity is unchanged
- Windows light theme: collection feels larger and action hierarchy is obvious
- Windows light theme: global feels like a homepage, not a utility panel
- Windows light theme: keyboard focus is visible on collection/global action controls
- Windows dark theme: contrast, focus visibility, and muted accents remain readable
- Windows dark theme: keyboard focus is visible on collection/global action controls
```

- [ ] **Step 4: Commit**

```bash
git add docs/ux-contract.md paperforge/plugin/main.js paperforge/plugin/styles.css
git commit -m "docs: align dashboard ux contract with refined ui"
```

---

## Implementation Notes

- Do not add new dashboard modes.
- Do not change CLI/data contracts.
- Do not introduce theme-specific palettes.
- Prefer removing duplicate CSS over overriding it again.
- If automated UI regression coverage requires extracting a small pure helper, keep the extraction minimal and local to dashboard behavior.

## Final Verification Commands

```bash
cd paperforge/plugin
npm test
```

Expected:

```text
Test Files  3 passed
Tests       40 passed
```
