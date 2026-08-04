# Phase ANN13: Bidirectional Navigation and Fallback Paths - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-07-06
**Phase:** ANN13 - Bidirectional Navigation and Fallback Paths
**Areas discussed:** Card to Source Navigation, Source to Card Focus, Selection Lifecycle, PDF Page Fallback, Keyboard and Accessibility

---

## Card to Source Navigation

**Question:** When a user selects an annotation card, how should source navigation behave by anchor status?

| Option | Description | Selected |
|--------|-------------|----------|
| Exact scrolls, page-level scrolls to marker, unresolved explains with fallback | Exact anchors scroll to inline highlight; page-level anchors scroll to page/block marker; unresolved anchors do not scroll. | Yes |
| Only exact scrolls | Most conservative, but page-level anchors feel less useful. | |
| Exact/page-level scroll, unresolved automatically falls back to PDF | Fast but too surprising and risks overstating grounding. | |

**Question:** How long should visual feedback remain after scrolling to a source anchor?

| Option | Description | Selected |
|--------|-------------|----------|
| Persistent selected state until another selection or Escape | Best for sustained reading. | Yes |
| Temporary pulse/highlight that fades out | Lighter but can lose current relationship. | |
| Scroll only, no selected state | Simplest but weak navigation feedback. | |

**Question:** What happens if the target source anchor is not currently found in the DOM?

| Option | Description | Selected |
|--------|-------------|----------|
| Do not guess; show temporarily unable to locate and fallback entry | Honest, keeps card selected, avoids wrong jumps. | Yes |
| Try nearest page/block marker | Helpful but may imply unsupported precision. | |
| Immediately use v0.2 PDF page fallback | Too abrupt for a canvas navigation failure. | |

**Question:** How should card-triggered source scrolling interact with existing scroll position?

| Option | Description | Selected |
|--------|-------------|----------|
| Only explicit card selection scrolls; refresh/re-render does not steal scroll | User action triggers navigation, system updates do not interrupt reading. | Yes |
| Restore selected card source anchor after refresh | Continuous but can hijack scroll. | |
| Never scroll automatically, only mark selected | Too weak for NAV-01. | |

---

## Source to Card Focus

**Question:** When a user clicks a source anchor, how should the card side respond?

| Option | Description | Selected |
|--------|-------------|----------|
| Focus corresponding card and scroll card lane to make it visible | Strong bidirectional navigation. | Yes |
| Only mark the card selected without scrolling the lane | Less disruptive but feedback may be offscreen. | |
| Only select the source anchor without affecting card lanes | Not enough for NAV-02. | |

**Question:** If one page-level marker corresponds to multiple cards, which card should be selected?

| Option | Description | Selected |
|--------|-------------|----------|
| Select the page-level group and highlight/list related cards | Honest representation of page-level precision. | Yes |
| Select the first card by reading order | Simple but misleading. | |
| Cycle through matching cards | Stateful and hard to explain. | |

**Question:** After source-to-card focus, should DOM focus actually move to the card?

| Option | Description | Selected |
|--------|-------------|----------|
| Move DOM focus to the corresponding card | Best for keyboard and screen-reader feedback. | Yes |
| Only update selected styling without moving DOM focus | Lighter but less accessible. | |
| Move focus only for keyboard-triggered source anchors | Nuanced but more branches to test. | |

**Question:** What happens if the corresponding card is unavailable due to refresh, stale load, paper change, or teardown?

| Option | Description | Selected |
|--------|-------------|----------|
| Show card unavailable and clear selection | Avoids dangling selections. | Yes |
| Keep source selected and wait for the card to return | Continuity but stale-prone. | |
| Fallback to the PDF page | Does not match source-to-card semantics. | |

---

## Selection Lifecycle

**Question:** What should happen to selection on paper change or canvas teardown?

| Option | Description | Selected |
|--------|-------------|----------|
| Immediately clear all selection/focus state | Prevents cross-paper leakage. | Yes |
| Try to restore same cardId/anchorId selection | Dangerous across papers. | |
| Keep visual state until new data finishes loading | Smooth but can mislead. | |

**Question:** After a successful refresh, should selection be preserved if the same card/anchor still exists?

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve selected state without auto-scrolling | Keeps context without stealing scroll. | Yes |
| Clear selection | Simple but loses context. | |
| Preserve selection and auto-scroll back to the selected anchor | Conflicts with scroll-stealing decision. | |

**Question:** After refresh, what if the selected card/anchor no longer exists?

| Option | Description | Selected |
|--------|-------------|----------|
| Clear selection and show a one-time status message | Honest and simple. | Yes |
| Keep old selection marked stale | Might imply old anchor can still navigate. | |
| Automatically select the nearest card/anchor | Guessing, therefore rejected. | |

**Question:** What should Escape clear?

| Option | Description | Selected |
|--------|-------------|----------|
| Clear card/source/group selection and temporary prompts without changing scroll | Clear exit behavior without moving the reader. | Yes |
| Only clear selected styling and keep prompts | Sticky state. | |
| Clear selection and scroll back to the original reading position | Too much hidden state. | |

---

## PDF Page Fallback

**Question:** When should the PDF fallback action be shown?

| Option | Description | Selected |
|--------|-------------|----------|
| Only when canvas source navigation is unavailable and a trustworthy PDF/page target exists | Keeps fallback explicit and safe. | Yes |
| Show for all page-level and unresolved anchors | Too noisy for page-level anchors. | |
| Show only after the user expands an error or explanation | Too hidden. | |

**Question:** How should the fallback action be triggered?

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit fallback button only; never auto-jump PDF | Avoids surprising navigation out of canvas. | Yes |
| Automatically jump for unresolved anchors | Too abrupt. | |
| First click shows button, second click auto-jumps | Too complex. | |

**Question:** What should the fallback button say?

| Option | Description | Selected |
|--------|-------------|----------|
| Open PDF page / localized equivalent | Clear that this opens the PDF page path. | Yes |
| Jump to source | Confuses source anchor navigation with fallback. | |
| Try fallback | Honest but vague. | |

**Question:** When must the PDF fallback be hidden?

| Option | Description | Selected |
|--------|-------------|----------|
| Hide if PDF path, pageIndex, attachment identity, or paper identity is not trustworthy | Preserves v0.2 navigation safety. | Yes |
| Show whenever pdf_path exists, even without pageIndex | May open the wrong/too broad target. | |
| Show only when the entire source surface is unavailable | Too restrictive. | |

---

## Keyboard and Accessibility

**Question:** Which navigation elements should be reachable through Tab?

| Option | Description | Selected |
|--------|-------------|----------|
| Cards, exact anchors, page-level markers, and fallback buttons are tabbable; unresolved status is not | Actionable elements only. | Yes |
| All anchors and statuses are tabbable | Too noisy. | |
| Only cards and fallback buttons are tabbable | Missing source-to-card keyboard path. | |

**Question:** How should keyboard activation work?

| Option | Description | Selected |
|--------|-------------|----------|
| Enter/Space activate focused card/anchor/button; Escape clears selection | Standard keyboard behavior. | Yes |
| Only Enter activates; Space keeps page scrolling behavior | More conservative but less button-like. | |
| No keyboard activation beyond Tab and mouse click | Not accessible enough. | |

**Question:** How should ARIA and selected state be expressed?

| Option | Description | Selected |
|--------|-------------|----------|
| aria-selected for card/source selected; real button plus aria-label for fallback | Clear without a heavy widget pattern. | Yes |
| Full roving tabindex/listbox pattern | Too complex for ANN13. | |
| CSS classes only, no ARIA | Weak accessibility. | |

**Question:** How should keyboard Tab order be arranged?

| Option | Description | Selected |
|--------|-------------|----------|
| Stable natural DOM order; no custom roving focus | Simple, testable, and consistent. | Yes |
| All cards first, then all anchors, then fallback buttons | Less aligned with visual flow. | |
| Custom roving focus with arrow-key movement | Too heavy for ANN13. | |

---

## the agent's Discretion

- Exact helper/module names, event wiring shape, CSS selected class names, status copy, and test file organization.

## Deferred Ideas

- Connector lines and relationship geometry remain ANN14.
- Final live harness and full verification remain ANN15.
