# Annotation Phase 7: PDF Jump Navigation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-06-20
**Phase:** annotation-07-pdf-jump-navigation
**Areas discussed:** Jump entry, source PDF matching, page landing and fallback, workspace opening behavior

---

## Jump Entry

| Option | Description | Selected |
|--------|-------------|----------|
| Page badge action | Clicking the existing page badge opens the source PDF/page and keeps row expansion separate. | Yes |
| Dedicated open icon | Add another icon button to every compact row. | |
| Whole-row click | Clicking anywhere on a row navigates, conflicting with expansion and text scanning. | |

**User's choice:** Follow the recommended page-badge action.
**Notes:** The user selected all discussion areas and delegated the detailed choice to the recommended approach.

---

## Source PDF Matching

| Option | Description | Selected |
|--------|-------------|----------|
| Attachment-first, fail closed | Match `sourceAttachmentKey`; do not guess or open the main PDF when the attachment is uncertain. | Yes |
| Always use main PDF | Open the canonical paper PDF even for annotations that may come from supplementary attachments. | |
| Guess from raw Zotero path | Construct or open an external path from annotation metadata. | |

**User's choice:** Follow the recommended attachment-first, fail-closed behavior.
**Notes:** Correct-document navigation is prioritized over a misleading successful click.

---

## Page Landing and Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Exact page, then PDF fallback | Convert zero-based `pageIndex`; if precise positioning fails, open the correct PDF and notify the user. | Yes |
| Exact page or nothing | Do not open the PDF when page targeting is unsupported. | |
| Always open first page | Ignore annotation page metadata. | |

**User's choice:** Follow the recommended exact-page-first fallback.
**Notes:** Missing page data may degrade to opening the correct PDF, but uncertain attachment identity may not.

---

## Workspace Opening Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Native Obsidian behavior | Reuse the plugin's current link-opening behavior and preserve the sidebar state. | Yes |
| Force right split | Always create or reuse a right-side editor split. | |
| Force new tab/window | Always create a separate navigation target. | |

**User's choice:** Follow the recommended native Obsidian behavior.
**Notes:** The jump should not unexpectedly rearrange the user's workspace.

## the agent's Discretion

- Exact helper/function names and pure-helper boundaries.
- Exact familiar icon, tooltip, disabled styling, and friendly notice wording.
- Selection of the most stable currently supported Obsidian page-navigation mechanism during research/planning.

## Deferred Ideas

- PDF annotation overlay rendering and popovers remain in Annotation Phase 8.
- Full display-layer/manual navigation verification remains in Annotation Phase 9.
- Editing, write-back, and concept-card evidence integration remain future work.
