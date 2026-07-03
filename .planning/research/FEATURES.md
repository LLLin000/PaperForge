# Feature Landscape: annotation v0.3 Visual Reading Canvas

**Domain:** Local-first visual PDF/text reading canvas for PaperForge annotations  
**Researched:** 2026-07-02  
**Scope:** Expected behavior for the new canvas features only. Annotation import, storage, CLI contracts, and v0.2 list/overlay behavior are treated as existing inputs.  
**Overall confidence:** HIGH for PaperForge requirements and safety boundaries; MEDIUM for external product-inspired feature prioritization because the target reference image is implied, not attached in this research prompt.

## Executive Recommendation

Build annotation v0.3 as a **read-only, source-grounded reading canvas**, not as a full visual thinking app. The MVP should prove that a researcher can open a paper, see central reading content, scan annotation cards in left/right lanes, understand which source span each card belongs to, and round-trip between a card and the source page/location. That is the valuable next step beyond v0.2's sidebar/list and PDF overlay.

The reference-image-inspired features should be included only where they strengthen grounding: side cards, colored anchors, connector geometry, selected-card emphasis, and card view-models that can later hold richer content. Do not build freeform mind maps, editable note cards, AI synthesis, multi-paper boards, or Zotero write-back in this milestone.

## Product Posture

PaperForge should position the canvas between three existing patterns:

| Pattern | What Mature Tools Prove | PaperForge v0.3 Takeaway |
|---------|--------------------------|---------------------------|
| Zotero reader | Users expect annotation colors, page grounding, note integration, and "show on page" behavior. | Preserve provenance and page/source round-trips as table stakes. |
| Readwise Reader | Power readers value annotation-first workflows, PDFs in the reading flow, rich highlights, keyboard navigation, and export to tools like Obsidian. | Make annotations feel like first-class reading objects inside Obsidian. |
| MarginNote / visual study tools | Deep reading products turn highlights into cards with bidirectional source links, mind maps, search, recall, and later synthesis. | Adopt card + anchor affordances now; defer mind-map/flashcard/AI scope. |
| Obsidian Canvas | Users understand cards, 2D layout, connectors, colors, pan/zoom, and grouping as visual note primitives. | Borrow the visual language but keep PaperForge canvas deterministic and source-controlled. |

## Table Stakes

These are required for the MVP. Missing any of them makes the canvas feel decorative rather than useful.

| Feature | Observable User Behavior | Why Expected | Complexity | Notes |
|---------|--------------------------|--------------|------------|-------|
| Canvas entry point for active paper | User can open "PaperForge Reading Canvas" from a paper context and it loads the same paper-scoped annotations as v0.2. | v0.3 is a new reading surface, not a separate data product. | Medium | Must reuse v0.2 bridge/list/export contracts. |
| Central reading surface | User sees the paper's readable source in the center: PDF-backed view where supported, with a clear fallback to text/page-level representation when PDF embedding is unavailable. | The target UI is reading-first; cards without source context become another sidebar. | High | Do not claim live native PDF overlay completion until the pending v0.2 Obsidian harness is recorded. |
| Left/right annotation lanes | User sees annotation cards arranged beside the reading surface, split into left/right lanes by deterministic layout rules. | The reference visual depends on side cards framing the document. | Medium | Deterministic layout is enough; manual dragging can wait. |
| Annotation card view-model | Each card shows selected text, comment if present, page label/number, color/type, source, attachment identity when useful, and read-only state. | Mature readers make annotations scannable without opening raw JSON. | Low | Keep cards compact; long text should clamp/expand without breaking layout. |
| Colored source anchors | User can identify where a card is grounded in the source through a colored highlight/anchor marker when position data exists. | Color is already part of annotation semantics and supports quick visual matching. | Medium | If exact coordinates are missing, show a page-level anchor/fallback badge. |
| Card-to-source navigation | Selecting a card scrolls or jumps the central source to the annotation's page/location and visually emphasizes the matching anchor. | Zotero-style "show on page" behavior is table stakes for grounded annotations. | Medium | Use existing Phase 7 navigation behavior as fallback. |
| Source-to-card navigation | Selecting a visible anchor focuses the corresponding card and reveals its details without requiring list search. | The canvas promise is bidirectional grounding. | Medium | This is testable with DOM focus/selection state even before live PDF checks. |
| Connector foundation | User sees connector lines for the active, hovered, or selected card-anchor pair; connectors update on scroll, resize, lane changes, and refresh. | The reference image's core affordance is visual linkage. | High | Draw only focused connectors in MVP to avoid clutter and geometry risk. |
| Safe fallback path | If canvas prerequisites fail, user can still use the v0.2 annotation list/PDF jump/overlay fallback without broken controls. | v0.2 explicitly risk-gated PDF internals; v0.3 must not regress it. | Medium | Fallback state should name what is unavailable and offer the existing list. |
| Refresh and lifecycle handling | User can refresh annotations; stale cards/connectors/anchors are removed when the paper, pane, file, PDF, or annotations change. | v0.2 already requires refresh and teardown safety; canvas adds more state to clean up. | Medium | Include regression tests for stale connector/card teardown. |
| Empty and error states | User sees clear states for no annotations, missing paper identity, missing PDF/text source, unsupported coordinates, command failure, and missing DB. | A blank canvas is indistinguishable from a broken canvas. | Low | No raw tracebacks or shell noise. |
| Read-only safety boundary | User cannot create, edit, delete, push, or mutate Zotero/PaperForge annotations from the canvas. | v0.3 is explicitly read-only. | Low | Any edit-looking affordance is a bug in this milestone. |
| Accessibility and keyboard basics | User can tab through cards, activate card/source navigation from keyboard, and read labels for anchors/connectors. | Canvas UI should not be mouse-only for core review flows. | Medium | Full keyboard canvas authoring is deferred. |
| Layout resilience | Cards, anchors, and connectors remain readable at normal desktop widths; text does not overlap buttons, lanes, or the source surface. | Visual canvas failures are often layout failures. | Medium | Test at narrow and wide plugin pane widths. |

## Differentiators

These should be included only if the table-stakes behavior is stable. They make PaperForge feel purpose-built rather than like a generic canvas clone.

| Feature | Value Proposition | Complexity | MVP Guidance |
|---------|-------------------|------------|--------------|
| Evidence-grade card metadata | A researcher can see not just a quote, but its paper, page, source attachment, annotation source, and read-only provenance. | Low | Include as subtle metadata, not noisy chrome. |
| Deterministic lane placement by reading order | Cards appear near their source page/anchor order, making the side lanes feel tied to the paper rather than random. | Medium | Prefer predictable layout over user-authored placement in v0.3. |
| Focused connector mode | Only active/hovered/selected connectors are emphasized, making the canvas readable with many annotations. | Medium | This is the right MVP compromise between target visual and clutter. |
| Card density modes | User can switch between compact scan cards and expanded detail cards without losing source focus. | Medium | Useful if long comments/selected text are common. Can be a late MVP stretch. |
| Annotation type/color legend | User can interpret colors/types consistently across cards and anchors. | Low | Add if colors are prominent in the design. |
| Source-aware unsupported-position handling | Cards without precise coordinates still participate through page badges and jump actions. | Low | Important because imported Zotero data may vary in position fidelity. |
| Future-rich card schema | Canvas cards are modeled so later figure snippets, extracted tables, concept evidence, and AI notes can be added without rewriting card state. | Medium | Build the model seam, not the rich card features. |

## Deferred Features

These are valuable later, but should not be in the v0.3 MVP because they expand the product from reading canvas to authoring, synthesis, or study system.

| Deferred Feature | Why Defer | Future Trigger |
|------------------|-----------|----------------|
| Local annotation creation/editing/deletion | Violates the read-only milestone boundary and requires conflict semantics. | After canvas grounding is proven and a local annotation model is designed. |
| Zotero write-back | Requires credentials/API design, conflict review, and safety controls. | Separate write-back milestone only. |
| Full target visual with freeform draggable cards | Adds persistence, collision handling, selection controls, and layout migration before the reading value is proven. | After deterministic canvas succeeds and users ask for layout authorship. |
| Persistent user-authored canvas files | Obsidian Canvas-style persistence is tempting but creates a second source of truth. | Only after defining how generated annotation cards and user layout coexist. |
| Multi-paper / literature-review boards | Useful for synthesis, but v0.3 should stay paper-scoped. | Evidence/concept-card milestone. |
| AI summaries, clustering, or question-answering inside cards | Expands scope into v1.8/v1.7-style AI workflows and requires traceability review. | After card schema and source grounding are stable. |
| Mind maps, flashcards, spaced repetition | MarginNote proves value, but this is a study system, not a canvas MVP. | Separate learning/study milestone. |
| Rich media cards for figures/tables/images | Requires extraction/cropping/OCR/image handling and persistence. | Later rich-card milestone. |
| Cross-document backlinks and global annotation search | Valuable, but current milestone is the reading surface for one active paper. | Collection-level annotation milestone. |
| Mobile/touch-optimized canvas | PaperForge's current Obsidian plugin work is desktop-oriented. | After desktop canvas behavior stabilizes. |
| Full pan/zoom infinite canvas | The central document plus side lanes does not need infinite-space semantics in MVP. | Only if the canvas becomes a synthesis board. |

## Anti-Features

Do not build these in v0.3. They either violate the safety boundary or create fragile complexity.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Edit controls on annotation cards | Users may assume changes sync to Zotero or PaperForge storage. | Render read-only cards with provenance and navigation actions only. |
| Direct Zotero SQLite mutation | Existing project decision: unsafe. | Keep Zotero annotations as imported read-only source data. |
| Canvas-only annotation state | A hidden canvas state would diverge from `annotations.db` and v0.2 CLI contracts. | Generate canvas state from the existing annotation bridge every load/refresh. |
| All connectors always visible | Dense connector webs become unreadable and fragile under scroll/resize. | Show focused connectors by default; optionally reveal nearby connectors. |
| Reliance on private Obsidian PDF internals as the only path | v0.2 already proved native PDF internals are risk-gated and live harness remains pending. | Provide text/page-level fallback and v0.2 list/jump fallback. |
| Generic Obsidian Canvas clone | It would compete with Obsidian's core Canvas and dilute the source-grounded reading use case. | Build a PaperForge-controlled reading canvas with deterministic generated cards. |
| Auto-writing notes/cards from every annotation | Turns read-only review into authoring and can spam the vault. | Provide explicit later export/apply flows. |
| Raw JSON/debug panels in user UI | Breaks the polished Obsidian experience and exposes implementation noise. | Keep debug detail in tests/logs; show concise user states. |
| Re-researching annotation import/storage | v0.1/v0.2 already settled this line. | Treat storage/import as upstream inputs. |

## Feature Dependencies

```text
v0.2 annotation bridge/list data
  -> canvas card view-models
  -> side lane rendering
  -> card selection state
  -> card-to-source and source-to-card navigation
  -> focused connector geometry
  -> refresh/teardown regression coverage

PDF/text source resolver
  -> central reading surface
  -> anchor placement
  -> exact connectors when coordinates exist
  -> page-level fallback when coordinates are unavailable

Read-only safety contract
  -> no edit/delete/write-back controls
  -> provenance labels
  -> fallback to v0.2 list/jump/overlay behavior
```

## MVP Recommendation

Prioritize:

1. **Paper-scoped canvas shell:** open from active paper, load v0.2 annotation data, show central source with left/right lanes.
2. **Card and anchor grounding:** render read-only cards, colored anchors, page/source metadata, and deterministic lane placement.
3. **Bidirectional navigation:** card -> source and source -> card focus, with existing PDF/page jump fallback.
4. **Focused connector foundation:** draw and update selected/hovered card-anchor connector lines only.
5. **Safety/fallback/test states:** empty/error states, refresh/teardown, no edit controls, no raw tracebacks, v0.2 fallback preserved.

Defer: freeform dragging, persistent layout files, local editing, Zotero write-back, rich media cards, multi-paper synthesis, AI cards, mind maps, flashcards, full infinite-canvas behavior.

## Suggested Requirement IDs for v0.3

| ID | Requirement Seed |
|----|------------------|
| CANVAS-01 | User can open a PaperForge Reading Canvas for the active paper. |
| CANVAS-02 | Canvas loads paper-scoped annotations through existing v0.2 contracts. |
| CANVAS-03 | Canvas shows central reading content and left/right annotation card lanes. |
| CARD-01 | Cards show selected text, comments, page, color/type, source, and read-only provenance. |
| CARD-02 | Cards handle long/missing text/comment fields without broken layout. |
| ANCHOR-01 | Source anchors render for annotations with supported position data. |
| ANCHOR-02 | Page-level fallback anchors render when exact coordinates are unavailable. |
| NAV-01 | Selecting a card focuses or jumps to its source page/location. |
| NAV-02 | Selecting a source anchor focuses the corresponding card. |
| CONN-01 | Focused connector lines link selected/hovered cards to source anchors. |
| CONN-02 | Connectors update or disappear correctly on scroll, resize, refresh, and paper changes. |
| FALLBACK-01 | Unsupported canvas/PDF prerequisites fall back to the v0.2 list/jump surface. |
| SAFE-01 | Canvas is read-only and exposes no create/edit/delete/write-back controls. |
| SAFE-02 | Canvas display code does not mutate `annotations.db` or Zotero data. |
| TEST-01 | DOM/helper tests cover loaded, empty, missing, unsupported, refresh, and command-failure states. |
| TEST-02 | Verification distinguishes automated canvas behavior from the still-pending live Obsidian PDF viewer harness. |

## Roadmap Implications

Recommended phase structure:

1. **Canvas State and Shell** - Establish the PaperForge-owned view, reuse v0.2 annotation data, and render safe empty/error states.
2. **Cards and Source Surface** - Build read-only card view-models, lane layout, central source fallback, and responsive styling.
3. **Anchors and Bidirectional Navigation** - Add source anchors, card/source focus, and page-level fallback behavior.
4. **Focused Connector Layer** - Add geometry for active card-anchor pairs, plus scroll/resize/teardown tests.
5. **Verification Gate** - Confirm read-only safety, fallback to v0.2, no stale visual state, and explicitly preserve the pending live Obsidian PDF viewer note.

Phase ordering rationale: card layout depends on stable canvas state; navigation depends on cards and source anchors; connector geometry depends on both anchor and card DOM measurements; verification should come after the visual state surface exists.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Table stakes | HIGH | Project docs clearly define central reading content, side cards, anchors/connectors, read-only safety, and fallback requirements. |
| Differentiators | MEDIUM | External products consistently support annotation-first and card/source-link patterns, but the exact target visual was not attached. |
| Deferred scope | HIGH | Existing PaperForge decisions explicitly defer editing, Zotero write-back, and evidence-card mutation. |
| Anti-features | HIGH | v0.1/v0.2 safety decisions and v0.3 project notes are explicit. |

## Sources

- `.planning/PROJECT.md` - v0.3 goal, target features, v0.2 carry-over safety, decisions to build a PaperForge-controlled canvas and keep it read-only.
- `.planning/REQUIREMENTS.md` - v0.2 bridge/list/overlay/read-only requirements and future editing/evidence/write-back deferrals.
- `.planning/ROADMAP.md` - completed v0.2 phases, fallback posture, and pending live Obsidian PDF viewer harness.
- `.planning/phases/annotation-09-display-layer-verification-gate/annotation-09-VERIFICATION.md` - automated gate passed, live Obsidian viewer check pending, focused annotation tests passed.
- Zotero PDF Reader documentation, updated 2026-05-05 - annotation colors, annotations to notes, PDF page links, and show-on-page behavior: https://www.zotero.org/support/pdf_reader
- Readwise Reader product page - annotation-first reading, PDFs, rich highlights, keyboard reading, Obsidian export: https://readwise.io/read
- MarginNote product page - highlights as cards, bidirectional source links, mind maps/flashcards/AI as broader non-MVP scope: https://www.marginnote.com/en/index.html
- Obsidian Canvas documentation - cards, connectors, colors, pan/zoom, and `.canvas` file behavior as visual language reference: https://help.obsidian.md/plugins/canvas
