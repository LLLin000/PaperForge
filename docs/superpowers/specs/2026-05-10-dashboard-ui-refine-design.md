# PaperForge Dashboard UI Refine Design

> Approved direction: `Quiet Research Desk`
> Tone: `Calm editorial`
> Color posture: preserve PaperForge's own muted identity more than Obsidian theme accent, while remaining structurally theme-compatible.

---

## Goal

Refine the PaperForge Obsidian dashboard so the three active modes feel stable, readable, and visually intentional.

This pass must remove current interaction defects, increase visual hierarchy in `global` and `collection` modes, and replace the current overly small / overly uniform surface treatment with a warmer, quieter dashboard language that still fits naturally inside Obsidian.

---

## In Scope

1. Fix layout and interaction defects in the current dashboard UI.
2. Simplify and unify dashboard CSS so one visual system controls all three modes.
3. Increase perceived weight and readability of `global` and `collection` views.
4. Preserve `paper` mode as the calmest mode, optimized for reading and discussion.
5. Add restrained color accents inspired by muted Morandi / Maillard / soft American editorial palettes.
6. Keep compatibility with Obsidian themes for structure, contrast, and dark/light behavior.

## Out of Scope

1. Adding new dashboard modes.
2. Changing data contracts or CLI behavior.
3. Major DOM restructuring outside the current dashboard components.
4. Theme-specific per-theme palettes.
5. New analytics, charts, or workflow states.

---

## Problems To Solve

### 1. Bottom clipping in `paper` mode

The dashboard scroll container ends too tightly against Obsidian's lower chrome. Expanded technical details can be visually blocked by the bottom bar.

### 2. Scrollbar-induced layout jump

Opening technical details can push content over the vertical overflow threshold, causing the right scrollbar to appear only in the expanded state. This changes content width and makes text reflow visibly.

### 3. First discussion expand flash

The first click on a discussion expand control can trigger an unnecessary mode refresh due to `active-leaf-change`, which destroys transient local UI state.

### 4. `collection` mode feels underweighted and empty

The funnel, OCR section, and actions are all visually too small and too light relative to the available vertical space. The action row feels like footer utilities instead of primary workflow controls.

### 5. `global` mode feels like a compressed utility panel

Snapshot metrics, system status, and actions do not yet read as a real homepage. Typography and card weight are too restrained.

### 6. Visual language is too uniform and slightly sterile

Nearly every module uses the same thin border, small label, and low-energy box treatment. The result is clean but fatiguing.

### 7. CSS authority is split across duplicated sections

`styles.css` contains overlapping dashboard definitions from multiple iterations. The file currently mixes the newer native-light-surface pass with later redefinitions, causing inconsistency and making further refinement brittle.

---

## Design Principles

### Quiet Research Desk

The dashboard should feel like a well-kept research desk, not an admin console.

- Calm, not cold
- Warm, not decorative
- Structured, not dense
- Native to Obsidian, not generic web SaaS

### Mode personality hierarchy

- `paper`: quietest, most reading-oriented, least chrome
- `collection`: strongest workflow personality, denser operational cues
- `global`: homepage personality, strongest sense of entry and orientation

### Structural theme compatibility

The dashboard should inherit all major structural tokens from Obsidian:

- surfaces
- text hierarchy
- borders
- hover / active interaction colors
- dark/light behavior

### Selective brand tinting

PaperForge should keep a light house style of its own through restrained accent zones only:

- mode badges
- section markers
- emphasized numbers
- status pills
- light hover / focus accents

Accent tinting must never dominate full-card backgrounds.

---

## Color Direction

### Palette family

Use a muted editorial palette rather than a bright product palette.

Candidate families:

- `paper`: sage / dusty teal / cool gray-green
- `collection`: terracotta / muted amber / clay brown
- `global`: navy-gray / smoky blue / quiet brass accent

### Rules

1. No large high-saturation fills.
2. No dependence on the user's Obsidian accent as the primary PaperForge identity.
3. Accent color should be visible mostly in compact anchors, not whole surfaces.
4. Dark mode uses the same family, but with contrast adjusted by theme variables.

### Token ownership

Structural tokens come from Obsidian variables:

- surfaces: `--background-*`
- body and metadata text: `--text-*`
- borders and separators: `--background-modifier-*`
- default hover / active button surfaces: `--interactive-*`
- default focus visibility should remain Obsidian-native unless a stronger PaperForge focus ring is required for contrast

PaperForge-owned tint tokens may be introduced only for:

- mode badges
- section markers
- emphasized metric numbers
- semantic status pills
- optional primary action emphasis
- light card-edge or label accents in `global` and `collection`

PaperForge-owned tints must not replace Obsidian's base surface, body text, or default control contrast model.

---

## Visual System Changes

### Typography

Raise hierarchy contrast across all modes.

- Larger metric numbers in `global` and `collection`
- Section labels become more deliberate but not louder
- Buttons gain more presence through padding and weight, not bright fills
- `paper` body text remains the most reading-friendly text block

Measured targets:

- `global` / `collection` metric values: minimum `22px`, target `22-24px`
- `paper` section body copy: `14px` minimum, no reduction below current reading size
- `global` / `collection` section labels: minimum `12px`
- `global` / `collection` metadata/detail text: minimum `13px`
- primary and contextual action buttons in `global` / `collection`: minimum `13px` text size

### Spacing

- Increase inner card padding in `global` and `collection`
- Add consistent mode-level vertical rhythm
- Add stable bottom safe area to the scroll container
- Reduce cramped micro-gaps around pills, buttons, and disclosure areas

Measured targets:

- root dashboard bottom safe area: minimum `56px`
- primary cards in `global` / `collection`: minimum `16px` inner padding
- action buttons: minimum `34px` visual height
- disclosure body top padding: minimum `8px`
- `collection` / `global` mode section gap: minimum `16px`

### Surfaces

- Use fewer visual formulas, not more
- Primary content modules may remain carded
- Lightweight metadata / disclosure sections should not pretend to be full cards
- Remove mixed old/new box-shadow and border treatments

### Actions

- `collection` and `global` actions must feel like meaningful controls, not utility links
- Action rows should have larger targets and better anchoring in layout
- Primary actions may use slightly stronger tinting, but still muted

Primary action ownership:

- `global`: `Open Literature Hub` is the primary navigational action; `Sync Library` is secondary
- `collection`: `Run OCR` is the primary workflow action; `Sync Library` is secondary
- `paper`: keep file-opening actions neutral; do not introduce a new strong primary tint in the status/file row

Interaction rules:

- focus rings must remain clearly visible in both light and dark themes
- interactive controls must keep at least Obsidian-native focus visibility
- tinted buttons or pills must maintain readable text contrast in both light and dark themes

---

## Mode-Specific Design

### Paper Mode

Keep `paper` mode closest to the current reading companion model.

Changes:

1. Add bottom safety padding so technical details and discussion are never cramped by the Obsidian bottom bar.
2. Stabilize vertical scrollbar reservation to eliminate width jump when expanding sections.
3. Preserve the current header and merged status/file row structure.
4. Keep overview and discussion as the main content cards.
5. Make technical details lighter and calmer than primary cards.
6. Ensure discussion expand/collapse interaction never triggers accidental refresh-state loss.

Measured targets:

- technical-details expand/collapse must not cause horizontal text reflow from scrollbar appearance on supported desktop targets
- local discussion expand state and technical-details disclosure state must survive leaf activation when resolved mode and file identity stay unchanged
- paper mode may use the weakest accent density of the three modes

### Collection Mode

Make `collection` mode feel like an operational workspace.

Changes:

1. Increase funnel visual weight and number emphasis.
2. Make OCR pipeline feel like a central module, not a thin progress strip.
3. Enlarge action controls and treat them as workflow entry points.
4. Reduce the sense of unused lower space by giving the mode stronger section bodies and spacing.
5. Use warmer muted workflow accents than `paper` mode.

Canonical module order:

1. collection header
2. workflow overview
3. OCR pipeline
4. collection actions

Measured targets:

- workflow stage blocks: minimum `72px` visual width
- workflow stage labels: minimum `11px`
- collection action buttons: minimum `36px` visual height
- OCR module must visually read heavier than the action row beneath it
- collection mode must preserve the canonical module order above

### Global Mode

Make `global` mode feel like the dashboard homepage.

Changes:

1. Increase snapshot card presence.
2. Strengthen system status readability.
3. Give the start-working area more intentional prominence.
4. Keep issues clearly visible when present, but not alarmist.
5. Use the calmest version of the homepage accent family so the screen feels trustworthy rather than flashy.

Measured targets:

- snapshot metric blocks: minimum `72px` visual width
- global action buttons: minimum `36px` visual height
- homepage modules should preserve existing inventory and order: snapshot, system status, optional issues, start working

---

## Technical Decisions

### 1. Single CSS authority

Dashboard-specific duplicated definitions in `styles.css` must be consolidated so each dashboard selector has one authoritative definition block.

The implementation should prefer the newer redesign architecture and remove overlapping legacy overrides instead of stacking more overrides on top.

### 2. Stable scroll layout

The root dashboard scroll container should reserve scrollbar space consistently where supported, rather than only when overflow appears.

Fallback rule:

- on desktop targets where native gutter reservation is unavailable or behaves as overlay-only, the implementation must still avoid visible width-jump during technical-details expansion through compatible fallback styling or permanent vertical overflow reservation

### 3. Bottom safe area

The main scroll container or mode content container should include explicit bottom padding sized to prevent visual collision with Obsidian's lower status area.

### 4. Preserve local UI state where appropriate

Mode refreshes should not happen when only the dashboard leaf becomes active while the resolved mode/file identity stays unchanged.

State preservation rules:

- preserve discussion expanded/collapsed state across leaf activation with unchanged identity
- preserve technical-details disclosure expanded/collapsed state across leaf activation with unchanged identity
- reset those states on actual mode change or file identity change
- explicit manual refresh may reset transient state
- file content mutation that changes the current entry data may refresh the view, but must not transiently collapse state before the refresh completes

### 5. Theme-aware implementation model

Implementation should rely on Obsidian variables for structural tokens, and use PaperForge-owned CSS custom properties for restrained accent tints.

---

## Acceptance Criteria

### Functional

1. `paper` mode content is fully readable at the bottom with no visual obstruction from Obsidian chrome.
2. Opening technical details no longer causes a first-order layout jump from scrollbar appearance.
3. Discussion expand/collapse no longer flashes closed on first click.
4. Existing mode routing and dashboard actions continue to work.
5. Leaf activation alone with unchanged resolved mode/file identity does not rebuild the current mode tree.

### Visual

1. `collection` and `global` metric values are visibly larger than current live values and meet the measured targets above.
2. `paper` remains the lowest-accent, reading-first mode.
3. The three modes keep the same module inventory/order described in this spec while gaining differentiated emphasis.
4. Accent color remains limited to small emphasis zones rather than full-card fills.
5. Theme compatibility is preserved in both light and dark contexts.

### Accessibility / Interaction

1. Interactive controls retain visible keyboard focus in light and dark themes.
2. Contextual action buttons in `global` and `collection` meet the minimum visual height targets above.
3. Tinted pills, labels, and emphasized metrics maintain readable contrast against their backgrounds.
4. Expanding technical details must not change content wrap width in Windows desktop verification.

### Code Quality

1. Dashboard CSS duplication is materially reduced.
2. New styling logic is easier to reason about than the current stacked overrides.
3. Existing plugin tests continue to pass.

### UX Contract Deltas Required

`docs/ux-contract.md` must be updated to reflect:

1. `paper` mode bottom-safe-area expectation so lower content is not visually obstructed.
2. `paper` mode technical-details expansion must not introduce layout reflow from scrollbar appearance.
3. `paper` mode discussion expand must not collapse on first click due to leaf activation.
4. `collection` mode must preserve current module inventory and order while using larger visual hierarchy.
5. `global` mode must preserve current module inventory and order while using larger visual hierarchy.
6. light and dark theme verification must be mentioned in dashboard view expectations.

---

## Verification Plan

1. Run plugin test suite after implementation.
2. Manually verify `paper`, `collection`, and `global` modes in Obsidian.
3. Specifically verify:
   - paper bottom spacing
   - technical details expansion stability
   - discussion expand first-click behavior
   - perceived size and hierarchy in collection/global
   - light and dark theme legibility
   - visible keyboard focus on action controls
4. Manual verification targets:
   - Obsidian desktop on Windows in light theme
   - Obsidian desktop on Windows in dark theme

---

## Files Expected To Change

- `paperforge/plugin/styles.css`
- `paperforge/plugin/main.js`
- `docs/ux-contract.md`

Possible test touch-up only if needed:

- `paperforge/plugin/tests/commands.test.mjs`

---

## Notes

This is a refinement pass, not a dashboard rewrite.

The best result is a dashboard that feels more comfortable after ten minutes of use, not just prettier in a screenshot.
