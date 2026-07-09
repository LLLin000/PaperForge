# Visual Reading Canvas Correction Design

Date: 2026-07-09
Status: Approved design
Milestone: Annotation v0.3 follow-up

## Problem

The current Reading Canvas does not communicate a useful reading workflow. It can
open as a blank surface, and its annotation presentation is too close to an
annotation list. The intended product is a full-paper reading surface where Zotero
annotations remain visibly connected to the source text.

## Product Definition

Reading Canvas is a read-only, annotated full-text reader.

- `fulltext.md` is the only body-text source.
- The canvas renders the complete Markdown document as its central reading surface.
- Zotero highlights are anchored to matching passages in that rendered document.
- Comments, notes, and images appear as side cards connected to their source text.
- The canvas never writes annotation markup back into `fulltext.md`.
- The existing annotation list is secondary, used only for search, filtering, and
  unresolved annotations.

Creating or editing Zotero annotations inside the canvas is out of scope.

## Architecture

The data flow is:

1. Resolve the active paper entry.
2. Locate and read its `fulltext.md`.
3. Render the Markdown through Obsidian's Markdown renderer.
4. Load the paper's imported Zotero annotations.
5. Match annotation text to rendered source text.
6. Inject transient highlights and anchors.
7. Lay out side cards and connector lines.

The implementation is divided into five focused units:

- `source-loader`: resolves and reads the paper's `fulltext.md`.
- `markdown-surface`: owns Obsidian Markdown rendering and source lifecycle.
- `anchor-resolver`: matches annotations to rendered text and reports confidence.
- `annotation-layer`: owns highlights, popovers, and unresolved annotations.
- `canvas-layout`: places cards, avoids overlap, and updates connector geometry.

These units communicate through explicit source, anchor, and annotation view
models. Closing the view removes all transient UI without modifying the vault file.

## Text Anchoring

Anchoring uses a conservative four-stage strategy:

1. Exact selected-text matching.
2. Matching after normalization of whitespace, line breaks, hyphenation, and
   common OCR punctuation differences.
3. Disambiguation of multiple matches using page metadata, nearby context, and
   annotation reading order.
4. An unresolved result when no match is sufficiently reliable.

The resolver must never force an uncertain annotation onto an arbitrary passage.
Every imported annotation must finish in either a matched or unresolved state.
Matching diagnostics include the strategy, confidence, and candidate count.

## Interface And Interaction

The central column is a scrollable rendering of `fulltext.md`, preserving headings,
paragraphs, images, formulas, and links supported by Obsidian.

- Highlight colors follow Zotero colors.
- A plain text highlight stays inline and opens a compact detail popover when
  selected.
- An annotation with a comment, note, or image creates a side card.
- Cards are distributed between the left and right rails and adjusted to avoid
  overlap.
- Selecting a highlight locates and emphasizes its card.
- Selecting a card scrolls to and emphasizes its source passage.
- Connector lines remain visually quiet by default and strengthen on hover or
  selection.

The toolbar contains only refresh, unresolved count, open-PDF, and annotation
visibility controls. On narrow panes, side cards move into a right-side drawer so
the full text remains readable.

The annotation list is removed from the primary canvas composition. It remains
available as a collapsible utility for search and unresolved-item handling.

## Visible States

The canvas must never render an unexplained blank surface.

- Missing `fulltext.md`: show the resolved/missing path and a repair action.
- No annotations: render the full text and state that no annotations are present.
- CLI or database failure: show the error category and a retry action.
- Partial anchor failure: render all matched content and show the unresolved count.
- Markdown rendering failure: show a diagnostic error state.
- Initial loading: show a bounded loading state until source and annotations settle.

Async source and annotation requests use generation guards so switching papers
cannot render stale results into the active canvas.

## Verification

The real paper `BPQ8CXXR` is the primary live acceptance fixture.

- Opening Reading Canvas displays its complete `fulltext.md`.
- All 17 imported Zotero annotations are classified as matched or unresolved.
- Matched annotations visibly correspond to source passages.
- Highlight-to-card and card-to-highlight navigation both work.
- Refreshing, switching papers, closing, and reopening cannot produce a blank or
  cross-paper view.
- Wide desktop and narrow pane layouts remain readable.

Automated coverage must include source resolution, Markdown lifecycle, exact and
normalized matching, ambiguity handling, unresolved states, async stale-result
guards, visible error states, card interactions, and responsive layout contracts.

## Non-Goals

- Editing `fulltext.md` from Reading Canvas.
- Creating, changing, or deleting Zotero annotations.
- Writing generated highlight markup into Markdown.
- Treating the annotation list as the main reading experience.
- Guessing annotation anchors when confidence is insufficient.
