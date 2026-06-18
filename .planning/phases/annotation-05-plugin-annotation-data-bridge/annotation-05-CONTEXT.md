# Annotation Phase 5: Plugin Annotation Data Bridge - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Annotation Phase 5 connects the Obsidian plugin to the verified annotation v0.1 CLI JSON contract and converts that CLI output into a stable UI-ready state.

In plain terms: v0.1 already proved that PaperForge can import Zotero PDF annotations into its own `annotations.db` and expose them through `paperforge annotation ... --json`. Phase 5 is the bridge inside the Obsidian plugin. It lets the plugin identify the active paper, call the annotation CLI, parse the PFResult JSON, preserve provenance and PDF-location fields, and report clear data states for later UI phases.

This phase intentionally does not build the annotation sidebar/list UI, PDF jump action, PDF overlay rendering, local annotation editing, Zotero write-back, or concept-card evidence integration. Those remain scoped to later annotation phases.

</domain>

<decisions>
## Implementation Decisions

### CLI Entry Point
- **D-01:** The plugin annotation bridge must use `paperforge annotation export --paper KEY --json` as its primary data source.
- **D-02:** `annotation export` is preferred over `annotation list` because it preserves the full fields needed by later PDF jump and overlay work, including attachment identity, source provenance, `position_json`, and `selector_json`.
- **D-03:** The bridge may normalize a lightweight display shape for the UI, but it must not discard the original export row.
- **D-04:** `annotation list` may remain useful for future lightweight views, but Phase 5 should not build a dual-source bridge unless a concrete performance problem appears.

### Active Paper Resolution
- **D-05:** The annotation bridge should reuse the existing dashboard paper-resolution behavior instead of inventing a second identity path.
- **D-06:** Active paper detection should support Markdown note frontmatter `zotero_key`, PDF path matching through the canonical index, and paper workspace path detection.
- **D-07:** If no active paper can be resolved, the bridge should return a structured `missing-paper` state rather than calling the CLI with an empty or guessed key.

### UI-Ready State Machine
- **D-08:** Phase 5 should define a complete annotation load state, not just return an array of annotation rows.
- **D-09:** Required states are `idle`, `loading`, `ready`, `empty`, `missing-paper`, `missing-db`, `cli-error`, and `invalid-json`.
- **D-10:** The state object should carry at least `paperKey`, `annotations`, `message`, `errorCode`, and optionally raw CLI/PFResult details for debugging.
- **D-11:** Phase 6 UI should be able to render list, empty, and error states from this bridge state without reinterpreting raw CLI output.

### Missing and Failure States
- **D-12:** Missing or unreadable `annotations.db` must be represented as `missing-db`, not as `empty`.
- **D-13:** `empty` means the annotation system is available but the current paper has no annotations.
- **D-14:** CLI process failures should become `cli-error`; invalid stdout or malformed JSON should become `invalid-json`.
- **D-15:** User-facing messages should be clear and friendly, avoiding raw Python tracebacks or shell noise.

### Annotation Row Shape
- **D-16:** Each normalized annotation should keep a compact `display` section for list UI fields: page, page label, type, color, selected text, and comment.
- **D-17:** Each normalized annotation should keep a `provenance` section for source, read-only state, source library, parent key, attachment key, annotation key, sync state, and timestamps where available.
- **D-18:** Each normalized annotation should keep a `pdfLocation` section for page index/label, source attachment identity, `position_json`, `selector_json`, and sort/index fields needed by jump and overlay phases.
- **D-19:** Each normalized annotation should keep the raw export row under `raw` so later phases can extend behavior without changing the bridge contract again.

### Refresh and Lifecycle
- **D-20:** Phase 5 should update annotation state when the active paper changes, using the same mode/current-paper state already used by the dashboard.
- **D-21:** Phase 5 should not add database polling or a full visible refresh workflow; Phase 6 owns the annotation list UI and visible refresh button.
- **D-22:** The bridge should expose a reusable loader function that later UI code can call explicitly for manual refresh.

### the agent's Discretion
- The planner may choose exact helper/function names and file placement, as long as the bridge is testable without a live Obsidian runtime where possible.
- The planner may decide whether `missing-db` is detected from `annotation export` output, `annotation status --json`, or a small preflight helper, as long as the final state distinguishes it from `empty`.
- The planner may decide whether normalized row sections are plain nested objects or a documented flat shape with grouped names, as long as the semantic groups above are preserved.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/ROADMAP.md` - Annotation Phase 5 goal, dependencies, and success criteria.
- `.planning/REQUIREMENTS.md` - BRDG-01 through BRDG-04 and v0.2 boundaries.
- `.planning/STATE.md` - Current milestone state, known baseline failures, and phase numbering decision.
- `.planning/PROJECT.md` - Annotation v0.2 project framing and key decisions.

### Prior Annotation Work
- `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-CONTEXT.md` - Read-only Zotero source and scoped import decisions that the plugin must not violate.
- `.planning/phases/annotation-03-cli-json-contracts/annotation-03-CONTEXT.md` - `paperforge annotation import/list/status/export --json` CLI and PFResult contract decisions.
- `.planning/phases/annotation-04-verification-gate/annotation-04-CONTEXT.md` - v0.1 verification boundary and safety gate.
- `.planning/phases/annotation-04-verification-gate/annotation-04-VERIFICATION.md` - Recorded v0.1 verification evidence, if present during planning.

### Plugin Code
- `paperforge/plugin/main.js` - Existing Obsidian plugin shell, dashboard paper-mode detection, subprocess command patterns, and current UI view code.
- `paperforge/plugin/src/testable.js` - Existing Node-testable helpers for Python resolution, subprocess running, command args, and runtime parsing.
- `paperforge/plugin/tests/` - Existing Vitest tests and patterns for plugin-side helper coverage.
- `paperforge/plugin/package.json` - Plugin-side test and build scripts.

### Annotation CLI and Contracts
- `paperforge/commands/annotation.py` - `annotation export/list/status/import` command implementation and JSON payload fields.
- `paperforge/annotation/` - Annotation storage, schema, import, and normalization modules.
- `tests/cli/test_annotation_json_contracts.py` - Cross-command PFResult contract coverage.
- `tests/cli/test_annotation_read_json.py` - Existing list/status/export JSON read contract tests.
- `tests/cli/test_annotation_import_json.py` - Existing import JSON and error behavior tests.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PaperForgeStatusView._resolveModeForFile()` already resolves active paper context from Markdown frontmatter, PDF path, and workspace path.
- `PaperForgeStatusView._currentPaperKey` and `_currentPaperEntry` already store the active paper identity for dashboard rendering.
- `resolvePythonExecutable()` already centralizes Python detection in both `main.js` and `src/testable.js`.
- `runSubprocess()` in `src/testable.js` already provides a testable subprocess wrapper with injected spawn support.
- `paperforge/commands/annotation.py` already returns `annotation.export` PFResult JSON with full provenance and PDF-location fields.

### Established Patterns
- Plugin helper logic that should be unit-tested lives in `paperforge/plugin/src/testable.js` and is inlined into `main.js` for Obsidian compatibility.
- The plugin generally remains a thin shell over Python CLI commands and canonical PaperForge state.
- Plugin user-facing errors should be friendly and should not expose raw tracebacks.
- Existing dashboard mode detection should stay the single interpretation of "current paper" to avoid drift between dashboard and annotation surfaces.

### Integration Points
- Phase 5 should connect near the per-paper dashboard state rather than creating a separate annotation-only mode detector.
- The bridge should call the CLI through existing Python resolution/subprocess patterns.
- Normalized annotation state should be available to Phase 6 list rendering without forcing Phase 6 to parse PFResult or raw CLI stdout again.
- Tests should cover parsing success, empty, missing paper, missing DB, CLI failure, and invalid JSON states through plugin-side fixtures.

</code_context>

<specifics>
## Specific Ideas

- Use `annotation export --paper KEY --json` as the single source of truth for plugin annotation data.
- Normalize export rows into sections such as `display`, `provenance`, `pdfLocation`, and `raw`.
- Treat `missing-db` as "annotation system not prepared yet" and `empty` as "this paper has no annotations."
- Keep Phase 5 read-only and invisible or minimally surfaced; Phase 6 owns the visible sidebar/list.
- No polling in Phase 5. Active-paper change and explicit loader calls are enough.

</specifics>

<deferred>
## Deferred Ideas

- Visible annotation sidebar/list, grouping, filtering, and refresh button belong to Annotation Phase 6.
- Jumping from an annotation row to PDF/page belongs to Annotation Phase 7.
- PDF overlay rendering and popovers belong to Annotation Phase 8.
- Display-layer safety and final verification gate belong to Annotation Phase 9.
- Local annotation editing, Zotero write-back, and concept-card evidence integration remain future requirements outside annotation v0.2 Phase 5.

</deferred>

---

*Phase: annotation-05-plugin-annotation-data-bridge*
*Context gathered: 2026-06-18*
