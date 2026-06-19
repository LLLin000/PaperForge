# Annotation Phase 6: Annotation Sidebar and List View - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-06-19
**Phase:** annotation-06-annotation-sidebar-and-list-view
**Areas discussed:** entry placement, row display, ordering/grouping/filtering, refresh/loading/failure states

---

## Entry Surface

| Option | Description | Selected |
|--------|-------------|----------|
| Embed in paper panel | Add an Annotations section to the existing `PaperForgeStatusView` paper mode. | Yes |
| Separate annotation sidebar | Create a dedicated annotation view/pane. | |
| Embed first, extract later | Build in paper panel now but keep design extractable later. | |

**User's choice:** 1
**Notes:** The list should be part of the current paper reading companion, not a new top-level UI surface.

---

## Section Placement

| Option | Description | Selected |
|--------|-------------|----------|
| After paper overview, before Next Step | Show paper summary first, then annotations, then workflow recommendation. | Yes |
| After Next Step, before Recent Discussion | Preserve current workflow recommendation before annotations. | |
| Default collapsed before technical details | Keep the page lighter but make annotations less visible. | |

**User's choice:** 1
**Notes:** Annotation content should be treated as reading evidence immediately after the paper overview.

---

## Default Visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Expanded by default | Show annotations immediately when the paper panel opens. | Yes |
| Expanded only when content exists | Keep empty/error states compact. | |
| Collapsed by default | Show only count/status until user expands. | |

**User's choice:** 1
**Notes:** Phase 6's core value is making annotations visible. Long lists should be bounded internally rather than collapsing the whole section.

---

## Row Density

| Option | Description | Selected |
|--------|-------------|----------|
| Compact row list | One or two-line rows optimized for scanning, expandable for detail. | Yes |
| Card list | Larger per-annotation cards with more visible text. | |
| Page-grouped blocks | Page headers with annotations nested under each page. | |

**User's choice:** 1
**Notes:** Compact rows fit the paper panel and leave room for filtering/grouping controls.

---

## Text Preview Length

| Option | Description | Selected |
|--------|-------------|----------|
| Selected text 2 lines, comment 1 line | Show marked text as primary and comment as secondary. | Yes |
| Selected text 1 line, comment 1 line | More compact but less informative. | |
| Selected text 3 lines, comment 2 lines | More complete but too tall for long papers. | |

**User's choice:** 1
**Notes:** Rows should support inline expansion for longer selected text/comments.

---

## Always-Visible Row Fields

| Option | Description | Selected |
|--------|-------------|----------|
| Page, color/type, selected text, comment icon/summary | Keep provenance details in expansion. | Yes |
| Page, color/type, selected text, comment, source/read-only | More transparent but crowded. | |
| Page and selected text mainly | Cleaner but loses annotation structure. | |

**User's choice:** 1
**Notes:** Trust/provenance data remains available in details without crowding the scan view.

---

## Color and Type Display

| Option | Description | Selected |
|--------|-------------|----------|
| Color swatch plus type text | Preserve color while keeping meaning accessible. | Yes |
| Color dot/bar only | Lightweight but ambiguous. | |
| Type text only | Accessible but loses Zotero color signal. | |

**User's choice:** 1
**Notes:** The list should not rely on color alone.

---

## Default Ordering

| Option | Description | Selected |
|--------|-------------|----------|
| PDF reading order | Page ascending plus source sort/index within page. | Yes |
| Type/color grouping | Useful by annotation intent but breaks reading order. | |
| Recently updated | Useful for resuming work but not for paper scanning. | |

**User's choice:** 1
**Notes:** The default view should follow the paper itself.

---

## Grouping Control

| Option | Description | Selected |
|--------|-------------|----------|
| No grouping / by page / by type-color | Simple grouping toggle with no grouping as default. | Yes |
| Fixed by page | Strong reading order but less flexible. | |
| Fixed by type-color | Strong color/type view but breaks reading order. | |

**User's choice:** 1
**Notes:** This satisfies the requirement while keeping the default list clean.

---

## Filters and Search

| Option | Description | Selected |
|--------|-------------|----------|
| Type/color filters plus search | Filter by type/color and search selected text/comment. | Yes |
| Type/color filters only | Simpler but weaker for finding content. | |
| Search only | Lighter but loses quick color/type scanning. | |

**User's choice:** 1
**Notes:** Search scope is selected text and comment only, not raw/provenance fields.

---

## Filter Persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Current panel session only | Keep settings during the session but do not persist across restart. | Yes |
| Per-paper persistence | More tailored but more complex state. | |
| Global persistence | Convenient but can hide annotations unexpectedly after restart. | |

**User's choice:** 1
**Notes:** Non-persistent controls reduce confusion when a stale filter would otherwise make annotations appear missing.

---

## Refresh Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Annotation section header | Refresh only annotations from the section header. | Yes |
| Top global refresh only | Fewer buttons but unclear scope. | |
| Both section and global refresh | Complete but more complex behavior. | |

**User's choice:** 1
**Notes:** Refresh scope should be explicit and local to annotations.

---

## Refresh Failure Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve old list with error banner | Keep last successful data visible and mark it stale. | Yes |
| Clear list and show error | Strict but brittle during reading. | |
| Preserve old list silently | Less disruptive but misleading. | |

**User's choice:** 1
**Notes:** Reading should not lose useful annotation data because a refresh command failed once.

---

## Empty and Error States

| Option | Description | Selected |
|--------|-------------|----------|
| Distinguish reasons and next actions | Separate `empty`, `missing-db`, `missing-paper`, and errors with appropriate guidance. | Yes |
| Generic no annotations | Simple but conflates absence with failure. | |
| Errors only, no actions | Easy to implement but less usable. | |

**User's choice:** 1
**Notes:** Users should know whether they need to import annotations, initialize data, or open a recognized paper.

---

## Loading State

| Option | Description | Selected |
|--------|-------------|----------|
| Section-local loading | Show loading only in the annotation section. | Yes |
| Whole paper panel loading | Too disruptive for an auxiliary module. | |
| Refresh-button only | Too subtle for first load. | |

**User's choice:** 1
**Notes:** Annotation loading should not block paper overview, Next Step, or other paper-panel content.

---

## the agent's Discretion

- Exact CSS class names and DOM structure.
- Exact bounded-list behavior for long lists.
- Exact grouping control widget shape.
- Exact concise UI labels, as long as they remain friendly and do not expose raw tracebacks/shell noise.

## Deferred Ideas

- Jump-to-PDF/page belongs to Annotation Phase 7.
- PDF overlay rendering and viewer popovers belong to Annotation Phase 8.
- Local annotation editing, Zotero write-back, and concept-card evidence integration remain future requirements outside this phase.
