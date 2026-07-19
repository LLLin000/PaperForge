# PaperForge Plugin Design System

## 1. Atmosphere & Identity

PaperForge is an Obsidian-native, quiet professional control center: calm when work is healthy, explicit when the user must act, and technical only when support needs evidence. Its signature is progressive clarity — every surface leads with a plain-language outcome, while implementation detail stays out of the reading path.

## 2. Color

PaperForge inherits the active Obsidian theme. It does not define independent light/dark hex palettes.

| Role              | Obsidian token                       | Usage                                    |
| ----------------- | ------------------------------------ | ---------------------------------------- |
| Primary surface   | `--background-primary`               | Page and card background                 |
| Secondary surface | `--background-secondary`             | Grouped sections, historical status      |
| Hover surface     | `--background-modifier-hover`        | Hovered rows and navigation              |
| Default border    | `--background-modifier-border`       | Cards, dividers, inputs                  |
| Hover border      | `--background-modifier-border-hover` | Hovered clickable cards                  |
| Primary text      | `--text-normal`                      | Headings and body                        |
| Secondary text    | `--text-muted`                       | Explanations and metadata                |
| Tertiary text     | `--text-faint`                       | Nonessential timestamps only             |
| Accent            | `--interactive-accent`               | Primary action, active navigation, focus |
| Accent text       | `--text-on-accent`                   | Text on accent surfaces                  |
| Success           | `--text-success`                     | Ready state only                         |
| Warning           | `--text-warning`                     | Setup Required and Action Required       |
| Error             | `--text-error`                       | Detection Failed and destructive effects |

Rules:

- Color communicates status or interactivity; it is never decorative.
- `Not Enabled` is neutral, not warning-colored.
- `Checking` uses muted text plus activity, not a warning color.
- Status color is always paired with text; color is never the only signal.
- Raw RGB or hex values are prohibited. Alpha tints use `color-mix()` with an Obsidian semantic token.

## 3. Typography

PaperForge inherits Obsidian font families and UI scale.

| Level              | Token / value                      | Weight            | Usage                                           |
| ------------------ | ---------------------------------- | ----------------- | ----------------------------------------------- |
| Page heading       | `--font-ui-large`                  | `--font-semibold` | Overview, Maintenance, Help                     |
| Module heading     | `18px`                             | `--font-semibold` | Module Detail title                             |
| Section heading    | `--font-ui-medium`                 | `--font-semibold` | Module body sections                            |
| Body               | `--font-ui-small`                  | normal            | Explanations and configuration summaries        |
| Metadata           | `12px`                             | normal            | Counts, timestamps, secondary facts             |
| Badge              | `11px`                             | medium            | Six-state labels                                |
| Diagnostic excerpt | `--font-monospace-theme` at `12px` | normal            | Copied or explicitly revealed support data only |

Rules:

- User-facing content uses Obsidian’s interface font; technical excerpts alone use monospace.
- Body copy is never smaller than Obsidian’s configured small UI font.
- Headings use sentence case. Uppercase eyebrow labels are removed.
- Error codes and raw commands never serve as headings or explanatory copy.

## 4. Spacing & Layout

### Base unit

All PaperForge spacing is a multiple of 4px.

| Token     | Value | Usage                            |
| --------- | ----: | -------------------------------- |
| `space-1` |   4px | Icon-to-label, compact metadata  |
| `space-2` |   8px | Inline groups and list gaps      |
| `space-3` |  12px | Compact panel padding            |
| `space-4` |  16px | Card padding and section gaps    |
| `space-5` |  20px | Summary panel horizontal padding |
| `space-6` |  24px | Major section separation         |
| `space-8` |  32px | Page-level separation            |

### Layout

- Settings content uses the host-provided width; PaperForge does not impose a competing page width.
- Overview module cards use two columns above a 620px container width and one column at or below 620px.
- Module Detail uses five visible module tabs above 620px and one native module select at or below 620px.
- Forms and maintenance items become one column at or below 620px.
- Nested vertical scrolling inside Settings is prohibited; long operational tables open in a full-width PaperForge workspace.

## 5. Components

### Control Center Navigation

- **Structure**: three top-level tabs — Overview, Maintenance, Help.
- **States**: default, hover, active, focus-visible.
- **Accessibility**: tab semantics, arrow-key movement, Enter/Space activation, visible focus.
- **Rule**: Module Detail is contextual and never appears as a top-level tab.

### Control Center Summary

- **Structure**: baseline conclusion, one supporting sentence, maintenance count, last-updated state, global Refresh Status.
- **Variants**: baseline ready, baseline blocked, refreshing, refresh failed with last-known result.
- **Rule**: Not Enabled optional capabilities do not lower the baseline conclusion.

### Module Card

- **Structure**: module name, six-state badge, one plain-language sentence, at most one key metric, navigation affordance.
- **Interaction**: the entire card opens Module Detail; no operation executes from the card.
- **States**: default, hover, active, focus-visible, refreshing, detection failed.
- **Accessibility**: one keyboard-focusable target with an accessible name containing module and status.

### Module Status Badge

- **Variants**: Checking, Ready, Not Enabled, Setup Required, Action Required, Detection Failed.
- **Rule**: badge wording is identical across modules; reason-specific detail belongs in body copy.
- **Accessibility**: text label is mandatory; status changes use polite live announcements.

### Module Detail Shell

- **Structure**: return navigation, responsive five-module switcher, module title, Module Status, plain-language summary, Contextual Primary Action area, custom module body, Support Diagnostic entry.
- **Responsive states**: tab list above 620px; native select at or below 620px.
- **Navigation memory**: persist only top-level destination or selected module; refresh state on reopen.
- **Accessibility**: restore focus to the source card or maintenance item on return.

### Contextual Primary Action

- **Structure**: one backend-authorized action localized by stable action ID.
- **States**: absent when Ready, enabled, hover, active, focus-visible, disabled while starting, running in Module Activity, terminal error.
- **Rule**: multiple competing primary actions and generic action menus are prohibited.

### Module Activity

- **Structure**: task label, bounded current/total progress when known, affected scope, safe Stop when supported.
- **Rule**: activity is separate from Module Status and does not enter Maintenance until terminal failure.
- **Accessibility**: `role="progressbar"` for bounded progress; polite live updates; Stop always remains reachable.

### Configuration Summary

- **Structure**: safe read-only value or configured state, explanation, explicit Change control.
- **Edit state**: local form with Cancel and Save and Verify.
- **Credentials**: show configured/not configured only; never repopulate plaintext.
- **Error state**: keep the verified saved value while explaining why the draft failed validation.

### User-visible Problem

- **Structure**: what happened, what is and is not affected, one next step, Copy Diagnostic Information.
- **Rule**: raw stderr, reason codes, paths, and exception text are excluded from the user explanation.
- **Accessibility**: error heading receives focus after a failed foreground action; copied state is announced.

### Maintenance Item

- **Structure**: owning module, User-visible Problem, affected scope, one Maintenance Action.
- **Eligibility**: only enabled-module blockers, failed requested tasks, unusable outputs, or material data risk.
- **Excluded**: optional modules never enabled, optimization suggestions, internal OCR quality signals, stale cache alone.
- **Interaction**: safe retry may run in place; configuration, scoped, batch, or destructive work navigates with context.

### Impact Confirmation

- **Structure**: affected count/scope, replaced derived outputs, preserved sources and user data, interruptibility, Cancel, concrete action verb.
- **Rule**: generic “Are you sure?” and typed confirmation for regenerable artifacts are prohibited.
- **Accessibility**: focus trap, Escape cancellation, initial focus on Cancel, restore focus to invoker.

### Setup Journey

- **Structure**: four dynamic stages — Foundation, Library, selected Optional Capabilities, review and begin.
- **States**: checking, ready to continue, validation failed, operation running, optional capability skipped, complete.
- **Rule**: Setup Completion never reverses automatically because of later health failures.

## 6. Motion & Interaction

| Type     | Duration | Easing      | Usage                                  |
| -------- | -------: | ----------- | -------------------------------------- |
| Micro    |    120ms | ease-out    | Hover, press, focus surface response   |
| Standard |    180ms | ease-in-out | Disclosure and module-body replacement |

Rules:

- Motion is subordinate to Obsidian and limited to opacity and transform.
- Progress uses transform-based fill where practical.
- No entrance choreography, decorative animation, or layout-property animation.
- `prefers-reduced-motion: reduce` disables nonessential transitions.
- A visible hover, active, and focus-visible state is required for every interactive element.

## 7. Depth & Surface

**Strategy: borders-only.** PaperForge uses Obsidian surfaces and borders, without decorative shadows.

| Surface         | Treatment                                                   |
| --------------- | ----------------------------------------------------------- |
| Page            | `--background-primary`, no border                           |
| Clickable card  | primary surface, 1px default border, host radius            |
| Grouped section | secondary surface or a top divider, not a nested card stack |
| Status tint     | semantic text color mixed at low opacity with transparency  |
| Modal           | Obsidian-owned modal surface and elevation                  |

Rules:

- Avoid cards inside cards.
- Use spacing before adding a divider; use a divider before adding another container.
- PaperForge does not override Obsidian modal shadows or global radii.
- Current “Vercel-inspired” styling, inline CSS duplication, raw emoji warning icons, overview action buttons, and permanently visible technical diagnostics are migration targets, not accepted primitives.
