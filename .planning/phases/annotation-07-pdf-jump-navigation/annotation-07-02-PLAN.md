---
phase: annotation-07-pdf-jump-navigation
plan: 02
type: execute
wave: 2
depends_on:
  - annotation-07-01
files_modified:
  - paperforge/plugin/main.js
  - paperforge/plugin/tests/annotation-main-runtime.test.mjs
autonomous: true
requirements:
  - OVLY-01

must_haves:
  truths:
    - "D-04/D-07: Runtime opening uses the tested resolver and performs no workspace open when attachment identity is unresolved."
    - "D-09: A valid resolved page is opened with the Obsidian PDF page fragment produced by the helper."
    - "D-10: If page-target opening fails, runtime retries the same confirmed PDF without a page target and shows a concise notice."
    - "D-11: A confidently resolved PDF with invalid page data opens normally and reports that precise positioning is unavailable."
    - "D-12: Navigation uses the existing `vault.getAbstractFileByPath` and `workspace.openLinkText(path, '')` seam without forcing workspace layout."
    - "D-13: Navigation does not rerender or mutate annotation query, grouping, filter, expansion, or loaded rows."
    - "D-14: Failures produce concise Notice text without raw exceptions, tracebacks, shell output, or annotation JSON."
    - "D-15: Navigation performs no frontmatter, annotation database, Zotero, paper metadata, filesystem, or subprocess mutation."
  artifacts:
    - path: "paperforge/plugin/main.js"
      provides: "Mirrored resolver contract and PaperForgeStatusView annotation PDF opener"
      contains: "resolveAnnotationPdfTarget"
    - path: "paperforge/plugin/tests/annotation-main-runtime.test.mjs"
      provides: "Runtime tests for page landing, plain-PDF fallback, notices, state isolation, and read-only behavior"
  key_links:
    - from: "paperforge/plugin/main.js"
      to: "paperforge/plugin/src/testable.js"
      via: "equivalent inlined helper contract required by the existing plugin bundle pattern"
      pattern: "extractVaultPdfPath|buildPaperPdfCandidates|resolveAnnotationPdfTarget"
    - from: "PaperForgeStatusView annotation opener"
      to: "Obsidian workspace"
      via: "vault existence check followed by workspace.openLinkText(target, '')"
      pattern: "getAbstractFileByPath|openLinkText"
---

<objective>
Wire the tested resolver into the Obsidian runtime and implement safe page-target opening, plain-PDF degradation, and read-only failure handling for OVLY-01.

Purpose: Turn the pure attachment/page decision into reliable workspace behavior without exposing raw errors or changing annotation UI state.
Output: Runtime navigation method plus success, fallback, and safety tests.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-PATTERNS.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-01-SUMMARY.md
@paperforge/plugin/main.js
@paperforge/plugin/src/testable.js
@paperforge/plugin/tests/annotation-main-runtime.test.mjs

<interfaces>
Plan 01 provides `resolveAnnotationPdfTarget(row, entry)` returning a structured resolved or unavailable result. `PaperForgeStatusView` already has `_currentPaperEntry`, `app.vault.getAbstractFileByPath(path)`, `app.workspace.openLinkText(linkText, '')`, `_annotationUiState`, and `Notice` imported from Obsidian.
</interfaces>
</context>

## Artifacts this phase produces

- An async annotation PDF opening method in `paperforge/plugin/main.js`.
- Runtime coverage for exact page navigation, safe fallback, failure notices, state preservation, and no writes.

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: Add runtime success and attachment-failure navigation</name>
  <files>
    paperforge/plugin/main.js
    paperforge/plugin/tests/annotation-main-runtime.test.mjs
  </files>
  <read_first>
    - `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-01-SUMMARY.md` for the exact helper result contract.
    - `paperforge/plugin/main.js` inlined annotation helper block and existing paper status PDF opener.
    - `paperforge/plugin/tests/annotation-main-runtime.test.mjs` Obsidian module stub, `makeStubApp`, and `makeRuntimeView`.
  </read_first>
  <behavior>
    - A confirmed attachment with `pageIndex: 2` checks the plain vault path and opens `{path}#page=3` with source `''`.
    - An unmatched specific attachment opens nothing and shows only a friendly corresponding-attachment notice.
    - A missing vault file opens nothing and reports that the source PDF is unavailable.
    - The resolver contract in `main.js` stays behaviorally equivalent to Plan 01's exported helper contract.
  </behavior>
  <action>
    Mirror the three Plan 01 pure helpers into the existing annotation helper section of `main.js`, following the established inlined-helper bundle pattern. Add an async `PaperForgeStatusView` method dedicated to annotation PDF opening. It must call `resolveAnnotationPdfTarget(row, this._currentPaperEntry)`, stop with a concise Notice when resolution fails, and verify the plain resolved path with `vault.getAbstractFileByPath()` before any `openLinkText()` call.

    Extend the runtime test stub so Notice calls are observable without changing production behavior. Add success and failure tests with canonical storage-path fixtures whose attachment keys either match or conflict. Notice assertions must compare friendly messages and must not rely on raw exception text.
  </action>
  <verify>
    <automated>node --check paperforge/plugin/main.js</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-navigation.test.mjs</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-main-runtime.test.mjs</automated>
  </verify>
  <acceptance_criteria>
    Confirmed identity opens the expected page link; unresolved identity and missing files perform zero workspace opens; helper parity and friendly notices are covered by automated tests.
  </acceptance_criteria>
  <done>The runtime has a callable, tested annotation opener for success and fail-closed attachment cases.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: Add page degradation, state isolation, and read-only guarantees</name>
  <files>
    paperforge/plugin/main.js
    paperforge/plugin/tests/annotation-main-runtime.test.mjs
  </files>
  <read_first>
    - `paperforge/plugin/main.js` method added in Task 1 and `_annotationUiState` lifecycle.
    - `paperforge/plugin/tests/annotation-main-runtime.test.mjs` existing refresh and state-persistence assertions.
    - `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md` decisions D-09 through D-15.
  </read_first>
  <behavior>
    - A rejected page-fragment open retries the same confirmed plain PDF exactly once and shows a precise-page-unavailable notice.
    - Invalid or missing pageIndex opens the confirmed plain PDF directly and shows a no-valid-page notice.
    - Failure of both page-target and plain-PDF opens is caught and rendered as a concise generic notice with no raw rejection content.
    - Successful and degraded navigation leave `_annotationUiState`, `_annotationState`, and `_lastRenderableAnnotationState` unchanged and do not call `_renderPaperMode`.
    - Navigation never calls `fileManager.processFrontMatter`, annotation loaders, subprocess helpers, filesystem writers, or metadata patch helpers.
  </behavior>
  <action>
    Complete the async opener so valid page targets are awaited, a page-target rejection retries only the already confirmed plain path, and invalid page data bypasses page targeting. Catch plain-open failures and emit a generic user message without interpolating the error. Do not mutate view state or rerender in any navigation branch.

    Add runtime tests that snapshot the relevant state objects before each call, exercise page rejection and invalid-page branches, and spy on all available mutation seams. Use a rejection message containing traceback-like text and raw JSON to prove Notice output does not disclose it per D-14.
  </action>
  <verify>
    <automated>node --check paperforge/plugin/main.js</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-main-runtime.test.mjs</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-navigation.test.mjs tests/annotation-bridge.test.mjs</automated>
  </verify>
  <acceptance_criteria>
    Page-target failures degrade to the same plain PDF, invalid pages do not block opening, raw errors stay hidden, all annotation UI/data state remains unchanged, and every available write/mutation spy remains untouched.
  </acceptance_criteria>
  <done>D-09 through D-15 are enforced at the runtime boundary with automated coverage.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Pure resolver result -> Obsidian runtime | A structured target crosses into side-effecting workspace APIs. |
| Obsidian workspace rejection -> user Notice | Runtime errors must be reduced to non-sensitive feedback. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-07-04 | Tampering | workspace open target | mitigate | Check the plain canonical path in the vault before opening; never open an unresolved target. |
| T-annotation-07-05 | Information Disclosure | Notice error handling | mitigate | Use fixed concise messages and tests containing sensitive-looking rejection text that must never reach Notice. |
| T-annotation-07-06 | Tampering | annotation/view state | mitigate | Runtime tests snapshot state and spy on render, metadata patch, loader, and frontmatter mutation seams. |
| T-annotation-07-07 | Denial of Service | page open retry | mitigate | Retry only once with the same confirmed plain PDF; no recursive retry or repeated resolution. |
| T-annotation-07-SC | Tampering | package supply chain | accept | No package-manager install occurs; runtime tests use existing Vitest and Obsidian mocks. |
</threat_model>

<verification>
- `node --check paperforge/plugin/main.js`
- `npm.cmd --prefix paperforge/plugin test -- tests/annotation-main-runtime.test.mjs`
- `npm.cmd --prefix paperforge/plugin test -- tests/annotation-navigation.test.mjs tests/annotation-bridge.test.mjs`
</verification>

<success_criteria>
- [ ] Valid targets open the confirmed PDF at `pageIndex + 1` through existing Obsidian link behavior.
- [ ] Failed precise positioning retries only the same confirmed plain PDF.
- [ ] Invalid page data opens the confirmed plain PDF without blocking.
- [ ] Uncertain attachment identity and missing files perform no open.
- [ ] Notices are concise and non-sensitive.
- [ ] Navigation leaves UI/data state intact and performs no write.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-02-SUMMARY.md`.
</output>
