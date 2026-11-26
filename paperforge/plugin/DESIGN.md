# PaperForge Plugin Design System

> Authoritative visual, geometric, interaction, and copywriting contract for the PaperForge Obsidian plugin. Every view (`PaperForgeBasesView`, `PaperForgeStatusView`, `PaperForgePdfView`, `PaperForgeSettingTab`, `OcrWorkspaceView`, and modals) must derive styling from this single token specification.

---

## 1. Dual-Mode Token Source (`asterlab` Default vs `obsidian` Theme Bridge)

All surfaces consume semantic `--pf-*` CSS custom properties declared in `paperforge/plugin/styles.css`. Views support two user-selectable palette bindings (`ui_theme_mode` in Settings):

1. **`obsidian`（默认 — 跟随当前 Obsidian 主题）**: Maps `--pf-*` tokens onto Obsidian's live workspace variables (`--background-primary`, `--background-secondary`, `--background-modifier-border`, `--interactive-accent`) so community themes merge seamlessly.
2. **`asterlab`（AsterLab 纯净白纸 / 深空曜石）**: Exact calibration of the AsterLab palette for high-contrast reading and data review.
3. **`warm`（经典暖灰纸质感）**: Classic warm paper surface (`#f7f6f3` / `#171614`, `#5b45c9`).

| Semantic Token       | AsterLab Light (default)  | AsterLab Dark               | Obsidian Bridge Mode                                             | Role                                     |
| -------------------- | ------------------------- | --------------------------- | ---------------------------------------------------------------- | ---------------------------------------- |
| `--pf-canvas`        | `#f7f6f3`                 | `#171614`                   | `var(--background-secondary)`                                    | Outer workspace background               |
| `--pf-surface`       | `#ffffff`                 | `#1e1d1a`                   | `var(--background-primary)`                                      | Active panels, Base table, Inspector     |
| `--pf-elevated`      | `#faf9f7`                 | `#242320`                   | `var(--background-primary-alt)`                                  | Subtle table stripes, hover rows         |
| `--pf-rail`          | `#f1efea`                 | `#171614`                   | `var(--background-secondary)`                                    | Segmented tracks, navigation rail        |
| `--pf-border`        | `#e7e3db`                 | `#37352f`                   | `var(--background-modifier-border)`                              | 1px hairlines, card dividers             |
| `--pf-border-strong` | `#d6d0c5`                 | `#4a473f`                   | `var(--background-modifier-border-hover)`                        | Control borders, focus edges             |
| `--pf-text`          | `#1c1b18`                 | `#f2efe9`                   | `var(--text-normal)`                                             | Primary prose, paper titles              |
| `--pf-text-muted`    | `#5f5a52`                 | `#a9a49a`                   | `var(--text-muted)`                                              | Authors, metadata, secondary labels      |
| `--pf-text-subtle`   | `#8f897f`                 | `#78736a`                   | `var(--text-faint)`                                              | Section captions, counts                 |
| `--pf-accent`        | `#5b45c9`                 | `#a996ff`                   | `var(--interactive-accent)`                                      | Single primary action & active selection |
| `--pf-accent-hover`  | `#4b37ae`                 | `#bcabff`                   | `var(--interactive-accent-hover)`                                | Primary CTA hover                        |
| `--pf-accent-text`   | `#ffffff`                 | `#1b1533`                   | `var(--text-on-accent)`                                          | Contrast label on accent fill            |
| `--pf-accent-soft`   | `rgba(91, 69, 201, 0.10)` | `rgba(169, 150, 255, 0.14)` | `color-mix(in srgb, var(--interactive-accent) 12%, transparent)` | Selection tint                           |
| `--pf-success`       | `#2f7a4f`                 | `#84c9a4`                   | `var(--text-success)`                                            | Healthy readiness only                   |
| `--pf-warning`       | `#7a6233`                 | `#d9b878`                   | `var(--text-warning)`                                            | Actionable attention needed              |
| `--pf-danger`        | `#a3373a`                 | `#e79a9c`                   | `var(--text-error)`                                              | Parse error / provenance drift           |

**Strict Accent Rules**:

- Maximum **one** accent-filled Primary CTA per viewport surface.
- Healthy/parsed literature rows use quiet neutral text (`--pf-text-muted` + `1px` outline if needed)—never loud green pills across normal rows.
- Domain/group indicator dots (`6px`) use the 8-color accessible categorical ladder (`#3b6fd8`, `#2f7a4f`, `#c47f17`, `#7a49c4`, `#c94a5a`, `#1b8a88`, `#5d6bb8`, `#9e6235` in light; luminous equivalents in dark).

---

## 2. Geometry, Spacing, Radii, & Typography

- **4px Base Grid (`Space`)**: Use strictly multiples of `4px` (`4 / 8 / 12 / 16 / 24 / 32 / 48`). Adjacent list/table rows sit tight (`8px`–`10px`); section transitions breathe (`16px`–`24px`).
- **Three-Tier Radius Hierarchy**:
  - `--pf-radius-control`: `6px` (buttons, inputs, compact chips, rows)
  - `--pf-radius-panel`: `10px` (panels, segmented control tracks, cards, selection bar)
  - `--pf-radius-dialog`: `12px` (modals, popovers)
  - `999px` is reserved strictly for short status/count outline badges (`<= 24px` tall).
- **Control & Row Heights**:
  - Buttons & inputs: `30px` (`--pf-control-height`)
  - Table data rows: `32px` compact density (`36px` standard comfortable density)
- **Typography Scale & Alignment**:
  - Page title: `22px / 600` (`--pf-text`)
  - Section / inspector title: `15px / 600` (`--pf-text`)
  - Body / paper title / control label: `13px / 400–500` (`--pf-text`)
  - Metadata / caption / table column header: `12px / 400–500` (`--pf-text-muted` / `--pf-text-subtle`)
  - **Rule**: Dark primary values (`13px`–`14px --pf-text`) always outrank gray labels (`11.5px`–`12px --pf-text-subtle`). Never render bold gray uppercase headers larger than content text.
  - **Tabular Numerals**: Apply `.pf-tnum` (`font-variant-numeric: tabular-nums`) to years, impact factors, page numbers, counts, and progress fractions.

---

## 3. Iconography & Component Contract

- **Zero UI Emojis**: All buttons, badges, toolbars, tabs, and rows use crisp single-color `1.65px` stroke vector line icons (`src/views/icons.ts`, Lucide geometry) rendered as inline `<svg>` in `--pf-text-muted` (hover `--pf-text`, active `--pf-accent`).
- **Structure via Hairlines**: Prefer `1px solid var(--pf-border)` row dividers and whitespace over stacked shadow cards (`Elevation` shadows appear only on floating menus and popovers).
- **Base Literature Workbench (`PaperForgeBasesView`)**:
  - Preserves native Obsidian `.bases-header` chrome with zero duplicate top toolbars.
  - Respects user-configured columns (`config.getOrder()`), display names (`config.getDisplayName()`), and groups (`data.groupedData`).
  - Leftmost `32px` checkbox column drives a **Contextual Multi-Select Header Bar** (`已选 N 篇 · 取消选择` + `[解析全文]`) instead of per-row action button walls.
- **macOS Preview PDF Reader (`PaperForgePdfView`)**:
  - Calm `40px` primary line-icon toolbar featuring Apple Preview's dual-mode split `高亮 | ▾` button (instant highlight on active selection without popup, or toggleable continuous highlighter pen).
  - Collapsible `36px` secondary **`标记` (`Markup`)** bar (`文本选择`, `矩形框选`, `画笔`, `形状 [矩形/椭圆/箭头/直线]`, `文本框 T`, `便签`, plus stroke/fill/width/font style controls).
  - Right-click and sidebar item `拷贝引用至笔记` backlink action absorbed cleanly without toolbar bloat.

---

## 4. Mandatory Scholarly Copywriting Rules

- Write concise, objective academic Chinese/English labels (`解析全文`, `同步文献库`, `原 PDF 文件已变更`, `研究认知记忆`).
- **Prohibited**: Emojis in UI chrome, exclamation marks (`!`), marketing phrasing (`一键...`), and unrequested technical leakage (`seq #`, `SHA-256`, `SQLite`, `zotero_key`, `rev`, `pending`, `done_incomplete`) on primary reading surfaces.
- Low-frequency operational diagnostics, file paths, and queue flags live inside collapsible secondary disclosures (`高级选项与技术标识 >`).

---

## 5. Six-State Capability Model (Settings & Maintenance)

The six canonical `UserState` tokens (`checking`, `ready`, `not_enabled`, `setup_required`, `action_required`, `detection_failed`) render with quiet `1px` outline badges + text (`11.5px` / `6px` dot) so modules never shout visually unless human intervention is required.

---

## 6. Interactive Micro-Craft Rules (`vibedesign.tips` Alignment)

Every interactive control follows five concrete tactile & typographic rules implemented globally in `paperforge/plugin/styles.css`:

### 2. Situational Easing Curves (`#011`) & Architectural Craft Laws

1. **Surface & Hairline Grouping (`Inset Grouped Lists`)**: Never stack bordered card boxes inside bordered card boxes. Related rows (`Control Center` modules, `Memory/OCR` config rows, `.base` table inside workspace) share one unified surface with subtle `1px` inset hairlines.
2. **Borderless Frosted Toolbar Chrome (`macOS Preview` + `#010`)**: Toolbars use translucent warm-stone blur (`backdrop-filter: blur(18px) saturate(180%)`); icon buttons stay borderless at rest, surfacing a quiet capsule on hover and an accent tint when active; related actions cluster inside soft segmented pills.
3. **Zero Raw Browser Form Controls**: All checkboxes render as `16×16` squircles, binary switches render as `32×18` `.pf-switch` macOS capsules (`--pf-ease-overshoot`), `<select>` menus render custom dual-chevron pop-up buttons, and `<details>` disclosures use rotating SVG chevrons.
4. **Situational Motion Tokens (`#011`)**:
   - `--pf-ease-out`: `cubic-bezier(0.22, 1, 0.36, 1)` (entrances, popovers, button settles)
   - `--pf-ease-in-out`: `cubic-bezier(0.45, 0, 0.55, 1)` (tab & chevron shifts)
   - `--pf-ease-overshoot`: `cubic-bezier(0.34, 1.56, 0.64, 1)` (switch thumbs & squircle checkmarks)
5. **Five-Layer Top-Lit Tactile Hierarchy (`#001`)**:
   - **Primary** (`--pf-accent`): subtle top-down gradient, top inner sheen (`--pf-primary-lift`), 1px bottom lip, `translateY(1px)` active press. Max **one** primary CTA per viewport section.
   - **Secondary** (`--pf-surface` / `--pf-action-btn--secondary`): top-lit neutral fill with crisp `--pf-border-strong` rim, compact width (never stretched `100%` across forms).
   - **Danger** (`.paperforge-orphan-delete-btn`): semantic Crimson (`#c4383b` / `#d95357`) for irreversible destructive modal confirmations.
   - **Ghost** (`pf-btn-ghost` / `pf-action-btn--ghost`): borderless transparent rest state, neutral hover capsule, zero resting accent outline.
6. **Concentric & Continuous Corners (`#004`)**: Outer containers (`10px`–`12px`) minus compact padding (`4px`) drive inner control radii (`6px`–`8px`), with `corner-shape: superellipse(1.25)` where supported.
7. **Recessed Input & Segmented Tracks (`#015`)**: Unified search bars and segmented controls sit inside `--pf-well-inset` tracks with an elevated `--pf-surface` capsule casting `--pf-btn-lift`.
8. **CJK / Latin Typography Switches (`#007`)**: Global `text-autospace: normal`, `text-spacing-trim: trim-start`, `text-wrap: balance` on headings, `text-wrap: pretty` on prose, `white-space: nowrap` on buttons/tabs, and `min-width: 0` on all flex truncating headers.

---

## 7. Unified Domain & Mode Vocabulary (AsterLab `ux-contract.md` §3 Alignment)

Every surface (`PaperForgeBasesView`, `PaperForgeStatusView`, `OcrWorkspaceView`, `PaperForgeSettingTab`) shares one canonical vocabulary:

| Context                 | Canonical Chinese Label                                                                   | Canonical English Label                                                                           | Retired Ambiguous / Machine Tokens                                      |
| ----------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Companion Mode          | `全局` / `单篇` / `集合` / `版本历史`                                                     | `Workspace` / `Paper` / `Collection` / `Versions`                                                 | `GLOBAL`, `PAPER`, `COLLECTION` uppercase chrome                        |
| Paper Parse State       | `已精读` / `已解析` / `解析中` / `排队中` / `部分解析` / `解析异常` / `未解析` / `无附件` | `Deep Read` / `Parsed` / `Parsing` / `Queued` / `Partial` / `Parse Error` / `Unparsed` / `No PDF` | `已处理` vs `已解析`, `未完成`, `待处理`, `KEY_DONE`, `OCR Needed`      |
| Toast & Banner Prefixes | Direct calm academic phrasing                                                             | Direct calm academic phrasing                                                                     | `[!!]`, `[OK]`, `[i]` log prefixes                                      |
| Technical Disclosure    | `渲染核查`, `PDF 状态`, `解析状态`, `附件状态`, `笔记路径`                                | `Render Audit`, `PDF Status`, `OCR Status`, `Asset Status`, `Note Path`                           | Raw `Render Quality`, `PDF Health`, `done_incomplete` on surface chrome |

---

## 8. Recoverable Inline Errors (`Cause + Recovery Action`)

Never fail with a fleeting `Notice` alone when user recovery is possible (`AsterLab D8 / UX-02`):

1. Missing PDF, missing fulltext, missing `.base`, failed sync, or rejected state updates persist an inline recoverable banner (`.pf-recovery-banner`) showing the localized error state, human-readable cause, and direct recovery action(s) (`重试` / `重新同步` / `打开设置`) until cleared by dismissal or successful state transition.
2. Transient `Notice` alerts remain supplemental for quick copy confirmations (`已复制标题`) or background start cues, strictly free of `[!!]` / `[OK]` / `[i]` ASCII badges.

---

## 9. Zero-Idle Activity Strip & Evidence DeepLinks (`UI-INT-10` / `CLOSE-07`)

1. **Zero-Idle Global Activity Strip (`.pf-global-activity-strip`)**: When no long-running operation (`Sync`, `OCR`, `Embedding`) is active, the strip renders `0px` (not even empty padding or placeholder chrome). While active, it surfaces real-time progress and provides a DeepLink action jumping directly to the active paper or OCR Workspace.
2. **Memory ↔ PDF DeepLinks**: Evidence page/figure markers inside Living Paper Memory (`[p.N]`, `p.N`, `第 N 页`, `Fig. N`) render as interactive inline DeepLink chips (`.pf-memory-deeplink`) that focus `PaperForgePdfView` and scroll directly to page `N`.

---

## 10. Narrow Pane & Dark Theme Gates

1. **Responsive Split-Pane PDF Toolbar**: When `PaperForgePdfView` sits inside a narrow split pane (`<= 680px`), secondary chrome compacts gracefully so page navigation, zoom, split highlight, and search remain reachable without horizontal clipping.
2. **Continuous Three-Axis Verification**: `scripts/dev/render_obsidian_ui_docs.py` verifies wide desktop Light, **AsterLab Dark**, **320px narrow Companion sidebar**, and **640px narrow split PDF** layouts with zero uncaught console/page errors.

---

## 11. Obsidian Native Radii Sync, Liquid Glass v2, & Four-Tier Micro-Motions (ADR-017)

1. **Four Theme Presets (`ui_theme_mode`)**: Defaults to `"obsidian"` (live host colors + Obsidian native radii), with `"asterlab"` (AsterLab v2 Pure Obsidian `#ffffff / #111215`, `#6c5ce7 / #a596ff`), `"zinc"` (clean high-contrast monospace neutral `#fafafa / #141416`, `#18181b / #e4e4e7`), and `"warm"` (`#f7f6f3 / #171614`, `#5b45c9`) selectable in Control Center.
2. **Three-Tier Spacing Density (`ui_density`)**: Supports `"compact"` (`24px` control / `26px` row), `"default"` (`28px` / `32px`), and `"comfortable"` (`32px` / `38px`) via `pf-density-*` classes and UIKit token scales.
3. **Native Radii Inheritance**: `--pf-radius-control`, `--pf-radius-btn`, `--pf-radius-panel`, and `--pf-radius-dialog` read `--input-radius`, `--button-radius`, `--radius-s/m/l`, and `--modal-radius` with `6 / 10 / 12px` fallbacks.
4. **Liquid Glass Light vs Dark Clear (No Glass-on-Glass)**: Applied strictly to floating toolbars & popovers (`blur(22px) saturate(185%)` + top specular edge in Light; smoked dark clear `rgba(20, 22, 28, 0.86/0.92)` in Dark; toggleable via `ui_liquid_glass`). Sidebars, Base tables, and Modals remain solid surfaces (Anti-XP-Box).
5. **Four-Tier Motion + `ReduceMotion`**: `MotionMicro` (`100ms` active `scale(0.97)`), `MotionSnappy` (`160ms` bar entrance & tab lift), `MotionFluid` (`220ms` spring popovers & chevron rotation), and `pf-nudge` (`±5px` validation shake), disabled cleanly via `reduce_motion` (`body.pf-reduce-motion`) or OS `prefers-reduced-motion`.

---

## 12. Unified UIKit Framework & Living Component Gallery (`src/uikit/`)

- **UIKit Engines (`src/uikit/`)**: Provides shared `theme`, five-tier `elevation` (`canvas` → `surface` → `card` → `floating` → `modal`), LIFO Escape `LayerStack`, `CommandRegistry`, stacked undoable `ToastQueue`, right `SidePeekController` drawer, composable `FilterBar` with saved quick-views, `ContextMenu` with viewport clamping and keyboard navigation, horizontal drag `ScrubNumber` with `Shift`/`Ctrl` precision modifiers, and accessible primitives (`ListItem`, `Keycap`, `InlineBanner`, `EmptyState`, `HoldToConfirm`).
- **Interactive UI Gallery (`PaperForgeGalleryView` + `npm run gallery`)**: Accessible inside Obsidian (`Open UI Gallery & Design System` or Settings → Appearance) and compiled as a zero-server standalone browser HTML prototype (`prototypes/ui-gallery.html`) displaying all real panels, Light/Dark modes, 4 theme presets, 3 densities, 520px narrow responsive mode, and edge-case stress previews.

---

## 13. P0–P2 Craft Polish, Virtualization & Unified Command Architecture

1. **Enter/Exit Transitions, Focus Restore & Collision Flip**:
   - `SidePeekController` and `ContextMenu` drive bidirectional `data-state="open" | "closed"` animations, restore focus to `previousActiveElement` on dismiss, and perform bottom/right viewport edge collision flipping (`.is-flipped-up`).
   - `FilterBar` supports Backspace deletion of the trailing filter pill when search is empty and viewport collision upward-flipping on `.pf-kit-filterbar-popover`.
   - All `.pf-kit-*` and `.pf-gallery-*` interactive buttons/inputs explicitly inherit `--font-interface`; narrow `<= 520px` PDF split containers keep zero horizontal overflow; motion tokens converge on high-damping exponential ease-out (`cubic-bezier(0.22, 1, 0.36, 1)`).
2. **Sonner-Style Stacked Physics `ToastQueue`**: Keyed DOM reconciliation preserves sibling node animations during updates, renders compact depth-scaled stacking (`--pf-toast-depth` / `data-depth`), fans out smoothly on hover, and supports horizontal swipe-to-dismiss gestures (`>= 72px`).
3. **Double-Buffered PDF Zoom & Instant Selection Mini-Bar**:
   - `PaperForgePdfView` keeps previous page canvases CSS-scaled (`.is-stale-buffer`) while painting the new high-DPI zoom canvas off-screen, swapping atomically with zero white flicker.
   - Non-empty text selections in normal `"select"` reading mode surface a compact `.pf-pdf-selection-bar` above the selection with 4 one-click highlight dots, a note action, and citation copy.
4. **Large-Library Virtualization & Inline Frontmatter Editing**: `PaperForgeBasesView` activates viewport windowing (`> 500` slots when scrollable) with fixed overscan + top/bottom spacer rows, sticky scrolled header hairlines, and double-click inline cell editing backed by `app.fileManager.processFrontMatter`.
5. **Full Obsidian Command Palette & Unified `Cmd+K` Switcher**: Registers core navigation, PDF/OCR single-paper contextual commands, embedding build, orphan check, Settings Control Center, and live Appearance cycling in Obsidian `addCommand`, mirrored into `plugin.commandRegistry` for `>` prefix command execution inside `PaperForgeQuickSwitcherModal` (with `<mark class="pf-qs-hl">` token highlighting).
