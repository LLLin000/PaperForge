# PaperForge — HTML Prototype → Obsidian CSS Mapping

> Maps every design token, component, and layout pattern from the kami prototypes to their Obsidian CSS variable equivalents.
> This is the implementation reference for ticket #100 (CSS rewrite).
>
> Source prototypes:
> - `paperforge/plugin/prototypes/control-center-ux.html`
> - `paperforge/plugin/prototypes/setup-journey.html`
> - `paperforge/plugin/prototypes/ocr-workspace.html`

---

## 1. Color Tokens

| kami prototype token | Obsidian CSS variable | Notes |
|---------------------|----------------------|-------|
| `--page: #f5f4ed` | `--background-primary` | Page/card backgrounds |
| `--ivory: #faf9f5` | `--background-secondary` | Grouped sections, cards |
| `--sand: #e8e6dc` | `--background-modifier-hover` | Hover states, secondary buttons |
| `--ink: #1B365D` | `--interactive-accent` | Primary actions, active nav, section numbers |
| `--ink-light: #2D5A8A` | `--interactive-accent-hover` | Hover accent |
| `--near-black: #141413` | `--text-normal` | Headings and body text |
| `--dark-warm: #3d3d3a` | `--text-normal` (slightly muted) | Secondary headings |
| `--olive: #504e49` | `--text-muted` | Descriptions, lede text |
| `--stone: #6b6a64` | `--text-faint` | Captions, metadata, nonessential timestamps |
| `--stone-light: #87867f` | `--text-faint` | Arrows, tertiary elements |
| `--border: #e8e6dc` | `--background-modifier-border` | Card borders, dividers |
| `--border-soft: #e5e3d8` | `--background-modifier-border` (opacity 0.7) | Softer internal dividers |
| `--tag-bg: #E4ECF5` | (derived from `--interactive-accent` at 10% opacity) | Ready badge, tag backgrounds |
| `--warn-bg: #fdf0e6` | (derived from `--text-warning` at 8% opacity) | Warning backgrounds |
| `--warn-text: #b85c1a` | `--text-warning` | Warning text, needs-action badges |
| `--danger-bg: #fef0f0` | (derived from `--text-error` at 6% opacity) | Danger backgrounds |
| `--danger-text: #b53333` | `--text-error` | Danger text |
| `--dark-surface: #30302e` | Not used in production (sidebar is Obsidian-owned) | Prototype-only |
| `--deep-dark: #141413` | Not used in production | Prototype-only |

### Opacity derivations for Obsidian

CSS variables don't support alpha channels natively. Use these patterns:

```css
/* Tag background from accent */
--pf-tag-bg: color-mix(in srgb, var(--interactive-accent) 10%, transparent);

/* Warning background */
--pf-warn-bg: color-mix(in srgb, var(--text-warning) 8%, transparent);

/* Danger background */
--pf-danger-bg: color-mix(in srgb, var(--text-error) 6%, transparent);
```

---

## 2. Typography

| kami prototype | Obsidian CSS variable | Notes |
|---------------|----------------------|-------|
| `--serif: Charter, Georgia, serif` | `--font-text` | Obsidian's text font; may or may not be serif |
| `--mono: JetBrains Mono, Consolas` | `--font-monospace` | Obsidian's monospace |
| `--sans: var(--serif)` | `--font-interface` | UI font for labels/badges |
| font-weight: 500 | `--font-semibold` or direct `500` | kami uses 500 exclusively for headings |
| font-weight: 400 | inherit / `--font-normal` | Body text |
| font-size: 32px | h1 in settings panel | Page title |
| font-size: 20-22px | h2 in settings panel | Section title |
| font-size: 15-16px | h3 in settings panel | Module title |
| font-size: 13-14px | `--font-ui-small` | Body, descriptions |
| font-size: 12px | `--font-ui-smaller` | Captions, metadata |
| font-size: 11px | `--font-ui-smaller` | Badges, labels, eyebrows |

---

## 3. Spacing & Grid

| kami prototype | Obsidian equivalent | Notes |
|---------------|-------------------|-------|
| 4px grid base | 4px grid base | Same — Obsidian uses 4px |
| 8px (2×) | gap, padding defaults | Standard spacing |
| 12px | gap in cards, toolbars | Tight spacing |
| 16px | section padding | Comfortable spacing |
| 20px | card padding | Component interior |
| 24px | section gap | Between sections |
| 32px | hero margin | Generous spacing |
| Host-provided width | Settings panel width | Do not impose a second max-width inside Obsidian Settings |
| Single-column editorial | Default settings layout | No 2-column card grid — use the available width |

---

## 4. Component Patterns

### Badges

```css
/* kami prototype */
.badge {
  display: inline-block;
  font: 500 11px/1 var(--serif);
  padding: 2px 9px;
  border-radius: 4px;
  letter-spacing: 0.4px;
  text-transform: uppercase;
}
.badge.ready { color: var(--ink); background: var(--tag-bg); }
.badge.needs_action { color: var(--warn-text); background: var(--warn-bg); }
.badge.not_enabled { color: var(--stone); background: var(--sand); }

/* Obsidian mapping */
.pf-badge {
  font-size: var(--font-ui-smaller);
  font-weight: var(--font-semibold);
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.pf-badge--ready {
  color: var(--interactive-accent);
  background: color-mix(in srgb, var(--interactive-accent) 10%, transparent);
}
.pf-badge--needs-action {
  color: var(--text-warning);
  background: color-mix(in srgb, var(--text-warning) 8%, transparent);
}
.pf-badge--not-enabled {
  color: var(--text-faint);
  background: var(--background-modifier-hover);
}
```

### Buttons

```css
/* kami prototype */
.btn-primary {
  color: var(--ivory);
  background: var(--ink);
  box-shadow: 0 0 0 1px var(--ink);  /* ring shadow */
}
.btn-secondary {
  color: var(--dark-warm);
  background: var(--sand);
  box-shadow: 0 0 0 1px var(--border);
}

/* Obsidian mapping */
.pf-btn--primary {
  color: var(--text-on-accent);
  background: var(--interactive-accent);
  box-shadow: 0 0 0 1px var(--interactive-accent);
  border-radius: 8px;
  padding: 7px 16px;
  font-weight: var(--font-semibold);
}
.pf-btn--secondary {
  color: var(--text-normal);
  background: var(--background-modifier-hover);
  box-shadow: 0 0 0 1px var(--background-modifier-border);
  border-radius: 8px;
  padding: 7px 16px;
}
```

### Cards

```css
/* kami prototype */
.card {
  background: var(--ivory);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 22px 24px;
}
.card:hover { box-shadow: 0 4px 24px rgba(0,0,0,0.05); }

/* Obsidian mapping */
.pf-card {
  background: var(--background-secondary);
  border: 1px solid var(--background-modifier-border);
  border-radius: 8px;
  padding: 20px 24px;
}
.pf-card:hover {
  box-shadow: 0 0 0 1px var(--background-modifier-border-hover);
}
```

### Info Box (blue left-border callout)

```css
/* kami prototype */
.info-box {
  background: #eef2f7;
  border-left: 2px solid var(--ink);
  padding: 12px 16px;
  border-radius: 0 6px 6px 0;
}

/* Obsidian mapping */
.pf-info-box {
  background: color-mix(in srgb, var(--interactive-accent) 6%, transparent);
  border-left: 2px solid var(--interactive-accent);
  padding: 12px 16px;
  border-radius: 0 6px 6px 0;
}
```

### Impact Box (warning left-border callout)

```css
/* kami prototype */
.impact {
  background: var(--warn-bg);
  border-left: 2px solid var(--warn-text);
  padding: 12px 16px;
  border-radius: 0 6px 6px 0;
}

/* Obsidian mapping */
.pf-impact-box {
  background: color-mix(in srgb, var(--text-warning) 8%, transparent);
  border-left: 2px solid var(--text-warning);
  padding: 12px 16px;
  border-radius: 0 6px 6px 0;
}
```

### Module Row (Overview list item)

```css
/* kami prototype */
.module-row {
  display: flex; gap: 16px;
  padding: 18px 0;
  border-bottom: 1px solid var(--border-soft);
}
.module-row:hover {
  background: var(--ivory);
  margin: 0 -16px; padding: 18px 16px;
  border-radius: 8px;
}

/* Obsidian mapping */
.pf-module-row {
  display: flex; gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid var(--background-modifier-border);
  cursor: pointer;
}
.pf-module-row:hover {
  background: var(--background-modifier-hover);
  margin: 0 -12px; padding-left: 12px; padding-right: 12px;
  border-radius: 8px;
}
```

### Progress Bar

```css
/* kami prototype */
.pbar { height: 4px; background: var(--sand); border-radius: 2px; }
.pbar .fill { height: 100%; background: var(--ink); border-radius: 2px; transition: width 0.3s; }

/* Obsidian mapping */
.pf-progress {
  height: 4px;
  background: var(--background-modifier-hover);
  border-radius: 2px;
  overflow: hidden;
}
.pf-progress__fill {
  height: 100%;
  background: var(--interactive-accent);
  border-radius: 2px;
  transition: width 0.3s ease;
}
```

### Setup Progress Steps

```css
/* kami prototype — horizontal step indicators */
.steps { display: flex; }
.step { flex: 1; text-align: center; border-bottom: 3px solid var(--border-soft); }
.step.active { border-bottom-color: var(--ink); }
.step.done { border-bottom-color: var(--dark-warm); }

/* Obsidian mapping */
.pf-setup-steps { display: flex; }
.pf-setup-step {
  flex: 1; text-align: center; padding: 10px 8px;
  border-bottom: 3px solid var(--background-modifier-border);
}
.pf-setup-step--active { border-bottom-color: var(--interactive-accent); }
.pf-setup-step--done { border-bottom-color: var(--text-muted); }
```

### Config Row (key-value display)

```css
/* kami prototype */
.config-row { display: flex; align-items: center; gap: 12px; padding: 10px 0; }
.config-row .key { font: 500 13px/1 var(--serif); color: var(--dark-warm); min-width: 160px; }
.config-row .val { font: 400 13px/1.4 var(--mono); color: var(--near-black); }

/* Obsidian mapping */
.pf-config-row {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 0; border-bottom: 1px solid var(--background-modifier-border);
}
.pf-config-row__key {
  font-weight: var(--font-semibold); font-size: var(--font-ui-small);
  color: var(--text-normal); min-width: 140px;
}
.pf-config-row__val {
  font-family: var(--font-monospace); font-size: var(--font-ui-small);
  color: var(--text-muted);
}
```

---

## 5. Layout Patterns

| kami pattern | Obsidian implementation |
|-------------|----------------------|
| Left dark sidebar | **DROP** — Obsidian owns the sidebar. Settings panel fills the content area. |
| `← Overview` back link | Top of each module detail page, simple `<a>` with accent color |
| Module numbering (01–05) | Accent-color section numbers preceding each module title |
| Section eyebrow (short hierarchy label) | Small lowercase or sentence-case text in `--text-faint` above sections |
| Card hover: ring shadow | `box-shadow: 0 0 0 1px var(--background-modifier-border-hover)` |
| Divider before containers | `border-bottom: 1px solid var(--background-modifier-border)` |
| Modal | Obsidian's native `Modal` class — do NOT create custom overlay |

---

## 6. Structural Genes (non-color patterns to preserve)

| Gene | Description |
|------|------------|
| **Single-column editorial** | No 2-column card grids. Content flows top-to-bottom. |
| **Section numbering** | Modules numbered 01–05 in accent color. |
| **Serif-first** | Headings use `--font-text` (may be serif or sans depending on Obsidian theme). |
| **Ring shadows** | Buttons and cards use `box-shadow: 0 0 0 1px` instead of drop shadows. |
| **Small radius** | 4px badges, 6px inputs, 8px cards/buttons. Never > 16px. |
| **Tight line heights** | Headings: 1.15–1.3. Body: 1.45–1.55. Labels: 1.0. |
| **Info-box pattern** | Colored left-border box for status/next-step information. |
| **Impact-box pattern** | Warning-colored left-border box for consequences/risks. |
| **Badge pattern** | Small caps, 4px radius, accent color for ready, warning color for needs-action. |
| **Config-row pattern** | Key-value pairs in monospace values. |
| **Progress bar** | 4px tall, accent-color fill, smooth transition. |

---

## 7. CSS File Structure (for #100)

```
paperforge/plugin/src/styles/
├── variables.css          # All Obsidian CSS variable mappings
├── primitives.css         # Badge, button, card, info-box, impact-box, config-row, progress
├── settings-overview.css  # Overview page structure
├── settings-modules.css   # Foundation, Library, SmartRetrieval, Agent detail pages
├── settings-ocr.css       # OCR Settings 3-state UX
├── ocr-workspace.css      # Workspace table, toolbar, detail panel
├── setup-journey.css      # 4-stage wizard
├── help.css               # Help page
└── main.css               # @import all of the above
```

Build: esbuild bundles `src/styles/main.css` → `styles.css` via `@import` resolution.