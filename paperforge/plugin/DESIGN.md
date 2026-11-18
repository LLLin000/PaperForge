# PaperForge Plugin Design System

> Authoritative visual, geometric, interaction, and copywriting contract for the PaperForge Obsidian plugin. Every view (`PaperForgeBasesView`, `PaperForgeStatusView`, `PaperForgePdfView`, `PaperForgeSettingTab`, `OcrWorkspaceView`, and modals) must derive styling from this single token specification.

---

## 1. Dual-Mode Token Source (`asterlab` Default vs `obsidian` Theme Bridge)

All surfaces consume semantic `--pf-*` CSS custom properties declared in `paperforge/plugin/styles.css`. Views support two user-selectable palette bindings (`ui_theme_mode` in Settings):

1. **`asterlab`（默认 — AsterLab 暖白原色 / 暗黑暖灰）**: Exact calibration of the AsterLab MyGo palette for warm, quiet reading and data review.
2. **`obsidian`（跟随当前 Obsidian 主题）**: Maps `--pf-*` tokens onto Obsidian's live workspace variables (`--background-primary`, `--background-secondary`, `--background-modifier-border`, `--interactive-accent`) so community themes merge seamlessly.

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
