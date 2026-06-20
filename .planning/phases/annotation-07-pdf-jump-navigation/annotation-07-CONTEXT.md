# Annotation Phase 7: PDF Jump Navigation - Context

**Gathered:** 2026-06-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Annotation Phase 7 lets the user jump from one annotation row in the existing PaperForge paper panel to the corresponding source PDF and annotation page.

This phase adds a clear row-level navigation action, resolves the PDF through existing PaperForge metadata and path conventions, converts the stored zero-based annotation page index into the page number expected by Obsidian, and degrades safely when the exact attachment or page cannot be resolved.

This phase does not render annotation overlays, edit annotations, write to Zotero or `annotations.db`, create a separate annotation pane, or connect annotations to concept-card evidence.

</domain>

<decisions>
## Implementation Decisions

### Jump Entry
- **D-01:** The page badge in each annotation row is the primary jump action. It should become an explicit interactive control rather than making the whole row clickable.
- **D-02:** The jump control must have a concise tooltip and accessible label that explain it opens the source PDF at the annotation page.
- **D-03:** The existing expand/collapse button remains independent. Clicking the page badge must not expand the row, and clicking expand must not navigate.

### Source PDF Resolution
- **D-04:** Resolve the annotation's specific source attachment first using `pdfLocation.sourceAttachmentKey` or the equivalent preserved provenance field.
- **D-05:** Use existing PaperForge paper metadata and PDF path conventions as the source of truth. Do not guess a filesystem path from the annotation key and do not open a raw external Zotero path directly when it cannot be resolved through the vault/PaperForge path model.
- **D-06:** A canonical main-PDF path may be used only when the attachment identity is confirmed to refer to that PDF, or when the annotation has no attachment identity and the paper has exactly one unambiguous PDF candidate.
- **D-07:** If the specific attachment cannot be matched confidently, do not silently open the paper's main PDF. Keep the action unavailable or fail it safely with a friendly message that the corresponding attachment could not be found.

### Page Landing and Fallback
- **D-08:** Treat `pdfLocation.pageIndex` as the authoritative zero-based machine location and convert it to a one-based PDF page number for Obsidian navigation. `pageLabel` remains display information and is not the primary arithmetic source.
- **D-09:** When Obsidian supports a PDF page fragment or viewer command, open the PDF at the converted target page.
- **D-10:** If the PDF is resolved but exact page navigation is unsupported or fails, still open the correct PDF without a page target and show a brief notice that precise page positioning was unavailable.
- **D-11:** Missing or invalid page data should not block opening a confidently resolved PDF; it should open the PDF normally and explain that no valid page location was available.

### Workspace Behavior and Feedback
- **D-12:** Follow Obsidian's existing link-opening behavior already used by PaperForge. Do not force a new split, tab, or window.
- **D-13:** The PaperForge annotation panel, filters, grouping, search, expansion state, and loaded rows remain intact after navigation.
- **D-14:** Navigation failures use concise user-facing notices and never expose raw exceptions, Python tracebacks, shell output, or raw annotation JSON.
- **D-15:** The jump action is read-only. It must not mutate annotation state, the annotation database, Zotero data, or PaperForge paper metadata.

### the agent's Discretion
- The planner may choose exact helper names and whether path/page resolution is split into pure helpers, provided the logic is independently testable.
- The planner may choose the exact familiar navigation icon, tooltip wording, disabled styling, and notice wording while preserving the decisions above.
- The planner may select the most stable Obsidian-supported page-opening mechanism after researching the plugin API and current PDF-link behavior.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/ROADMAP.md` - Annotation Phase 7 goal, dependency, and success criteria.
- `.planning/REQUIREMENTS.md` - OVLY-01, SAFE boundaries, and TEST-03 verification expectation.
- `.planning/STATE.md` - Current annotation v0.2 position and known unrelated baseline failures.
- `.planning/PROJECT.md` - Thin-shell plugin, local-first behavior, and annotation v0.2 scope decisions.

### Direct Dependency
- `.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-CONTEXT.md` - Locked list placement, row interaction, provenance display, and Phase 7 boundary.
- `.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-04-SUMMARY.md` - Final compact row DOM/CSS structure and regression-test surface consumed by navigation.

### Plugin Runtime and Tests
- `paperforge/plugin/main.js` - `PaperForgeStatusView`, normalized `pdfLocation`, annotation row renderer, active-paper entry, and existing PDF-open behavior.
- `paperforge/plugin/tests/annotation-section-dom.test.mjs` - Annotation row DOM harness and Phase 6 no-navigation assertions that Phase 7 must update intentionally.
- `paperforge/plugin/tests/annotation-main-runtime.test.mjs` - Obsidian runtime stubs, current-paper state, and `openLinkText` test seam.
- `paperforge/plugin/tests/annotation-bridge.test.mjs` - Preserved `sourceAttachmentKey`, `pageIndex`, `pageLabel`, and location normalization contracts.

### PDF Path Conventions
- `paperforge/adapters/zotero_paths.py` - Vault-relative Obsidian PDF wikilink generation and Zotero junction handling.
- `paperforge/pdf_resolver.py` - Existing absolute, vault-relative, junction, and Zotero storage-relative PDF resolution rules.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `normalizeAnnotationExportRow()` already preserves `pageIndex`, `pageLabel`, `sourceAttachmentKey`, position data, and row identity under `pdfLocation`.
- `PaperForgeStatusView._renderAnnotationRows()` already creates a page badge and a separate expand button, giving Phase 7 a precise navigation control without changing whole-row behavior.
- `_currentPaperEntry` and `_findEntry()` expose canonical paper metadata to the paper panel.
- The paper status strip already resolves `entry.pdf_path`, verifies it through `vault.getAbstractFileByPath()`, and opens it with `workspace.openLinkText()`.

### Established Patterns
- Plugin UI is built with Obsidian `createEl()` and explicit event listeners rather than a component framework.
- Annotation UI state is session-only and rerenders from `_annotationUiState`; navigation should not reset it.
- The plugin remains a thin shell over canonical PaperForge state and must show friendly errors instead of raw runtime output.
- Testable navigation decisions should be expressed in pure helpers or through the existing exported/runtime test seams.

### Integration Points
- Add the jump affordance at the page badge inside `_renderAnnotationRows()` while preserving the expand button event path.
- Resolve the target using the current paper entry plus the row's `pdfLocation`/provenance data.
- Reuse the existing Obsidian workspace/vault opening APIs and extend the annotation DOM/runtime tests with successful, degraded, and unresolved cases.

</code_context>

<specifics>
## Specific Ideas

- The visible page badge doubles as the jump control; the whole annotation row remains non-navigating.
- Correct attachment identity matters more than opening something. A supplemental-PDF annotation must not silently land in the main article PDF.
- A useful degradation path is: exact page when supported, correct PDF without exact page when page targeting fails, and no navigation when the source attachment itself is uncertain.
- Keep Obsidian's normal opening behavior so the feature feels native and does not unexpectedly rearrange the workspace.

</specifics>

<deferred>
## Deferred Ideas

- Highlight/overlay rendering and PDF-viewer popovers belong to Annotation Phase 8.
- End-to-end display-layer verification and the documented manual navigation harness belong to Annotation Phase 9, though Phase 7 should add focused automated tests where possible.
- Local annotation editing, Zotero write-back, and concept-card evidence integration remain outside annotation v0.2.

</deferred>

---

*Phase: annotation-07-pdf-jump-navigation*
*Context gathered: 2026-06-20*
