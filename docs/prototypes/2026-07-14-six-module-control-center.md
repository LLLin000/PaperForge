# Issue #71 — Six-Module Control Center Prototype

**Date:** 2026-07-15
**Author:** ControlCenterPrototype
**Prototype:** `docs/prototypes/2026-07-14-six-module-control-center.html`
**Parent:** Wayfinder #65 — Make the PaperForge control center self-explanatory
**Inputs:** #69 capability state/action contract, #66 contract audit, #67 Obsidian patterns, #68 desktop runtime patterns, DESIGN.md

---

## 1. Design Overview

A first-time and returning-user control center for six modules: 安装 / 文献库 / OCR / 记忆 / 维护 / 帮助. The layout uses a two-zone structure:

- **Primary Attention Zone** (top): shows the single module needing most urgent attention, with its primary action as a dark pill button. Normal state says "一切正常" with a less prominent refresh action.
- **Module Grid** (3-column, responsive to 1-column at 768px): six independent cards, each showing module name, capability state badge, reason text, actionable details, optional progress/activity, a single action button (only when non-ready), and an expandable "诊断信息" diagnostic disclosure.

### Design language

Vercel-inspired grayscale palette from `DESIGN.md`: `#171717` ink, `#4d4d4d` body, `#888888` mute, `#ebebeb` hairline, `#ffffff` canvas, `#fafafa` canvas-soft, `#f5f5f5` canvas-soft-2. Green (`#22a67e`) for ready states uses the same chroma-to-value ratio as the existing warning (`#f5a623`) and error (`#ee0000`) signals, not a saturated green that would clash with the grayscale system. No emojis, no glassmorphism, no gradient text, no cyan-on-black.

---

## 2. State Model (from #69 capability contract)

Three orthogonal axes per module:

```
Availability  x  Activity  x  Attention
```

| Axis | Values | Notes |
|------|--------|-------|
| Availability | `unknown < unavailable < missing_input < needs_action < limited < ready` | Ordinal, worst-to-best |
| Activity | `idle` / `running` | Never masks availability badge |
| Attention | Derived from availability | One primary action per module, `null` when ready |

### Contract rules implemented in prototype

| Rule | Implementation |
|------|---------------|
| One primary action per module | Action button shown only when state is not `ready`. Button label maps to verb table ($\leq 12$ verbs). |
| Running never hides warning | Activity spinner + progress bar shown alongside the warning badge. OCR with `needs_action` + progress bar keeps yellow badge. |
| Stale → unknown by TTL | Short-TTL modules (60–300s) render as `unknown` (grey) when TTL expired. Long-TTL modules (3600s: installation, help) remain `ready` when still within TTL. Never leaks last-known state. |
| Maintenance is derived view, no batch action | 维护 card has `action: null` in all scenarios. No batch "全部处理" or "run" button. Lists constituent module issues as inline bullets; users act on individual modules. |
| Primary zone exposes one concrete action | Hero action is the single highest-priority verb (e.g. `rebuild_derived` for OCR), never a generic "查看详情". |
| Plain buttons, not ARIA tabpanel | Scenario switcher uses `<button>` elements with `aria-current="true"`. No `role="tab"`, `role="tablist"`, or `role="tabpanel"`. Clicking a scenario changes the entire page state — inconsistent with tabpanel pattern. |
| Quiet ready states | `ready` modules show green "就绪" badge with no action button, just a brief reason text. |
| Advanced details without JSON | Expandable "诊断信息" section uses `dl`/`dt`/`dd` pairs, never raw JSON or Python traceback. |
---

## 3. Scenario State Definitions

### First Run (`first-run`)

| Module | State | Action |
|--------|-------|--------|
| 安装 | `missing_input` — 需要配置 | 开始安装 (primary) |
| 文献库 | `missing_input` — Zotero 导出路径未设置 | 配置路径 |
| OCR | `missing_input` — API 密钥未配置 | 配置密钥 |
| 记忆 | `missing_input` — 记忆库尚未创建 | 配置记忆库 |
| 维护 | `needs_action` — 4 个模块需要注意 | null (派生视图，无批量操作) |
| 帮助 | `ready` — 随时可用 | null |

Primary zone: "PaperForge 尚未安装" (warning, yellow left border).

### Partially Ready (`partial`)

| Module | State | Action |
|--------|-------|--------|
| 安装 | `ready` — 运行正常 | null |
| 文献库 | `ready` — 已同步 | null |
| OCR | `needs_action` — 12 篇论文衍生文件过期 | **重建衍生文件** (primary) |
| 记忆 | `needs_action` — 索引需要更新 | 重建索引 |
| 维护 | `needs_action` — 2 个模块需要注意 | null (派生视图，无批量操作) |
| 帮助 | `ready` — 随时可用 | null |

Primary zone: "OCR 处理结果已过期，记忆库索引需要更新" (warning, yellow left border). Hero action is **"重建衍生文件"** (`rebuild_derived`) — the single highest-priority concrete action. The description also notes the second item: memory index rebuild. Demonstrates **one concrete primary action** when multiple modules need attention.

### Stale Snapshot (`stale`)

Simulates a state where **short-TTL probes have expired** (library 300s, OCR 60s, memory 300s) while **long-TTL probes remain fresh** (installation 3600s, help 3600s). Last probe was 6 minutes ago.

| Module | State | Action |
|--------|-------|--------|
| 安装 | `ready` — 运行正常（缓存有效） | null |
| 文献库 | `unknown` — 状态未知（缓存已过期） | 检测 |
| OCR | `unknown` — 状态未知（缓存已过期） | 检测 |
| 记忆 | `unknown` — 状态未知（缓存已过期） | 检测 |
| 维护 | `unknown` — 状态未知（依赖模块已过期） | 检测 |
| 帮助 | `ready` — 随时可用（缓存有效） | null |

Primary zone: "部分模块状态已过期" (warning, yellow left border, label "缓存过期"). Cards: 2 green, 4 grey. Action is "刷新过期模块" (`probe`). Demonstrates **TTL-respecting fail-closed state**: fresh modules never go unknown when their TTL has not expired.

---

## 4. Interaction & UX Design

### Primary action per attention item (contract rule)

Each non-ready card has **exactly one action button**. The button label maps to a verb from the $12$-verb table. When the module is `ready`, no button appears. This satisfies the #69 invariant: `action.primary` is `null` when ready.

### Active operation feedback

When activity is `running`, the card shows:
- CSS spinner (animated border rotation, `--link` blue to signal process health)
- Activity label text ("处理中")
- Progress bar with `role="progressbar"` and `aria-valuenow`/`aria-valuemin`/`aria-valuemax`
- Fractional counter ("3/12")
- Badge remains visible (yellow warning badge coexists with spinner in "active-ocr" scenario)

### Advanced diagnostic disclosure

The "诊断信息" toggle expands a `dl` panel with key-value diagnostic data. No JSON, no Python error messages, no raw tracebacks. Example entries:
- "版本: 1.3.0"
- "运行环境: Python 3.11.4"
- "API 状态: 有效"
- "全文索引: 已构建"
- "待处理: 2 项"

The toggle is a text-only link (`<button>` styled as underlined text, `--link` blue) that says "诊断信息" when collapsed and "收起诊断信息" when expanded.

### Snackbar feedback

Every action button click shows a translucent snackbar at the bottom of the viewport with a Chinese message describing the action being taken ("PaperForge: 正在启动安装流程...", "OCR: 正在重建衍生文件..."). The snackbar auto-dismisses after 2.5 seconds.

### Keyboard navigation

- Scenario tabs are `role="tablist"` with arrow key navigation (Left/Right arrow switches tab)
- All buttons are natively focusable `<button>` elements
- Focus moves to the primary action button on scenario switch
- `:focus-visible` uses `--link` blue outline (`#0070f3`) at 2px with offset
- Diagnostics toggle reports `aria-expanded` state

### Responsive design

- Default: 3-column grid
- `< 900px`: 2-column grid
- `< 768px`: single-column grid (verified: `720px` card width within `768px` viewport, no overflow, no clipped controls)
- All controls visible and functional at 768px (verified: 17 buttons, 0 clipped)

---

## 5. Adopt/Reject Decisions

| Decision | Adopt/Reject | Rationale |
|----------|-------------|-----------|
| Primary zone with one dominant module | **Adopt** | Follows #69 "one primary action per attention" and #68 "per-module actionable maintenance, never global OK" pattern (VS Code, Docker Desktop). |
| Unknown state as solid grey, never last-known color | **Adopt** | Directly from #69 contract: "Stale is never ready". Grey conveys "no information" without implying readiness or failure. |
| Expandable diagnostics without JSON | **Adopt** | Does not expose XML/JSON structure; uses native `dl`/`dt`/`dd` for definition list. From #68 "local diagnostic export with user review before issue creation" (VS Code pattern). |
| Chinese-first copy with English only behind disclosure | **Adopt** | Target audience reads zh-CN. Diagnostic panel uses same Chinese labels for field names; only version identifiers and technical codes use English when unavoidable ("Python 3.11.4", "PaddleOCR v4"). |
| Maintenance as derived view with item list | **Adopt** | From #69: maintenance aggregates non-ready states; has `items[]` array referencing constituent modules. Shown as bullet list in "首次运行" and "部分就绪". |
| No emoji module icons | **Adopt** | Contract says no emojis. Used monochrome geometric symbols (`◐`, `▤`, `◇`, `△`, `⚙`) as CSS content instead. |
| Scenario switches as styled pills | **Adopt** | Follows Vercel muted pill tab pattern from DESIGN.md (`.tab-ghost`). Active state inverts to solid `--ink` background. |
| Action buttons: dark pill for primary, outlined for secondary | **Adopt** | Matches `button-primary` / `button-secondary` from DESIGN.md. Primary scenario action uses solid `--ink`; module-level primary actions also solid; secondary actions use outlined style. |
| Activity spinner in CSS only (no JS animation frame) | **Adopt** | Simpler, lower energy, no JS dependency. Uses `@keyframes spin` with `border-top-color` trick. |
| Progress bar with ARIA progressbar role | **Adopt** | Accessibility requirement; screen readers get exact numeric progress. |
| Snackbar for action feedback | **Adopt** | From #67 Obsidian Notice pattern: transient message at bottom of viewport with 2.5s auto-dismiss. Used instead of a true Notice to stay in vanilla HTML/JS. |
| Focus management on scenario switch | **Adopt** | MVP of #67 "`checkCallback` probe + re-evaluate" pattern: switching scenario focuses the primary action button so keyboard users don't lose context. |
| No error state (red badge) in current demo | **Reject** (deferred) | The `unavailable` state with `error` severity exists in the contract but is not exercised by the five demo scenarios. A future prototype or #72 maintenance view should demonstrate `unavailable` (e.g., "Python runtime not found"). |
| Maintenance item list as inline bullets | **Adopt** | Clearer than links or hidden details. Each item shows module name + issue type ("OCR: 12 篇衍生文件过期"). Unobtrusive at `13px` body color. |
| TTL values hardcoded in diagnostic text | **Adopt** | Matches #69 note: "actual TTLs should be calibrated during the #71 prototype phase". Each `unknown` card shows both `lastProbe` and `ttl` as plain text under diagnostics. This makes TTL calibration observable. |
| Plain buttons instead of ARIA tabpanel | **Adopt** (after review) | Original used `role="tablist"`/`role="tab"`/`aria-selected` with keyboard arrow navigation. Changed to plain `<button>` with `aria-current` because clicking a scenario changes the entire page state — inconsistent with the tabpanel pattern where each tab reveals a panel with `aria-labelledby`. Arrow key navigation preserved. |
| Maintenance card has no action button | **Adopt** (after review) | Removed all maintenance card `action` fields (were `probe` or `run` in various scenarios). Maintenance is a derived view per #69 contract — no independent action. Users act on individual modules. Item list shows constituent issues. |
| Stale scenario preserves long-TTL modules as ready | **Adopt** (after review) | Original stale scenario set all modules to `unknown`. Fixed: installation and help (3600s TTL) remain `ready` because 6 minutes < 60 minutes. Library/OCR/memory (60–300s TTL) render as `unknown`. Maintenance depends on the expired modules so also `unknown`. |
| Partial hero shows concrete action, not generic | **Adopt** (after review) | Primary zone action changed from `investigate` ("查看详情") to `rebuild_derived` ("重建衍生文件"). The priority algorithm selects OCR's action as the most urgent concrete verb across all non-ready modules. |

---

| Test | Result | Detail |
|------|--------|--------|
| First-run scenario | Pass | Primary: "PaperForge 尚未安装". Badges: 1 ready, 5 warning. Maintenance has no action button. |
| Partial scenario | Pass | Primary: "OCR 处理结果已过期，记忆库索引需要更新". Hero action: "重建衍生文件". Badges: 3 ready, 3 warning. Maintenance has no batch action. |
| Active OCR scenario | Pass | Primary: "OCR 正在处理 3/12 篇论文". OCR card has spinner + progress bar. Warning badge visible despite running activity. Maintenance has no action. |
| Stale scenario | Pass | Primary: "部分模块状态已过期" with label "缓存过期". Badges: 2 ready (install+help), 4 unknown (library/OCR/memory/maintenance). Install/help preserved as ready under 3600s TTL. |
| All-ready scenario | Pass | Primary: "一切正常". All 6 badges: ready (green). No action buttons on any card. |
| Diagnostic toggle | Pass | Click opens `dl` panel, toggles label to "收起诊断信息", sets `aria-expanded="true"`. Multiple panels open simultaneously. |
| Action button feedback | Pass | Each action click shows snackbar with module-specific Chinese message. Primary: "PaperForge: 正在启动安装流程...". OCR: "OCR: 正在重建衍生文件...". |
| 768px responsive | Pass | Single column grid (720px cards within 768px viewport). No overflow. All 16 buttons visible and unclipped. Diagnostics fits within card width. |
| Keyboard navigation | Pass | Arrow keys switch scenario buttons. Focus moves to primary action on scenario switch. |
| Plain buttons (no ARIA tab role) | Pass | No `role="tab"`, `role="tablist"`, or `role="tabpanel"`. Active button uses `aria-current="true"`. Arrow key navigation preserved via JS. |
| No external resources | Pass | Zero network requests. System font stack. No external CSS/JS. |
| 768px responsive | Pass | Single column grid ($720\text{ px}$ cards within $768\text{ px}$ viewport). No overflow. All 16 buttons visible and unclipped. Diagnostics fits within card width. Keyboard focusable at this width. |
| Keyboard tab navigation | Pass | Arrow keys switch scenario buttons. Focus moves to primary action on scenario switch. |
---

## 7. Relationship to Issue #72

This prototype is scoped to #71 (control center information hierarchy and interaction model). It does not implement:

- Actionable stale/failed/corrupt work filtering (maintenance inbox)
- Successful update disappearance
- Privacy-safe GitHub Issue draft generation and review

These are the #72 scope and will be addressed in a separate prototype (`docs/prototypes/2026-07-14-maintenance-inbox.html`).

The two prototypes share:
- Same CSS token set and design language
- Same capability state model (`unknown/unavailable/missing_input/needs_action/limited/ready`)
- Same action verb table (`setup/set_config/sync/rebuild_derived/rebuild_index/probe/investigate/run/migrate/update/restore_backup/redo`)
- Same "stale is never ready" fail-closed contract

---

## 8. Open Questions for #79 Design Review

1. **TTL calibration**: Current values (60–3600s, from contract) are placeholders. Should installation really have a 3600s TTL if config changes at runtime are rare but the consequences of stale config are high?
2. **Error state (`unavailable`, red)**: Not exercised in any scenario. Should a "breakage" scenario be added showing a missing runtime or corrupt database?
3. **Action confirmation**: Destructive actions (`redo`, `restore_backup`) need a confirmation modal in production that this prototype does not mock.
4. **First-run vs Returning-user differentiation**: The "首次运行" scenario shows all missing input. How does the system distinguish true first-run (never probed) from all-modules-unknown (TTL expired)? The contract says `unknown` for both; the banner label could differ.
5. **Primary zone priority algorithm**: Currently hardcoded per scenario. The production system needs a deterministic algorithm: worst severity first, then earliest `updated_at`, then alphabetical by module id.
6. **Help module probes**: The contract TTL is 3600s, but what does probing help actually check? File existence? File content integrity? Version match with plugin?
