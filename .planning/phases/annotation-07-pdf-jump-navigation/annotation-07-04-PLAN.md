---
phase: annotation-07-pdf-jump-navigation
plan: 04
type: execute
wave: 4
depends_on:
  - annotation-07-03
files_modified: []
autonomous: false
requirements:
  - OVLY-01

must_haves:
  truths:
    - "D-01/D-02: In Obsidian, the annotation page badge is visibly and accessibly the jump action."
    - "D-03/D-13: Real navigation leaves expansion, search, grouping, filter, and loaded rows intact."
    - "D-04 through D-08: A known matching source attachment opens the correct PDF and converts zero-based pageIndex to the expected one-based page."
    - "D-09 through D-12: Obsidian follows its normal link-opening behavior and lands on the requested page when supported, with the tested plain-PDF fallback otherwise."
    - "D-14/D-15: User feedback stays concise and the workflow remains read-only."
  artifacts:
    - path: "paperforge/plugin/tests/annotation-navigation.test.mjs"
      provides: "Automated helper verification evidence"
    - path: "paperforge/plugin/tests/annotation-main-runtime.test.mjs"
      provides: "Automated Obsidian runtime verification evidence"
    - path: "paperforge/plugin/tests/annotation-section-dom.test.mjs"
      provides: "Automated DOM and interaction verification evidence"
    - path: ".planning/phases/annotation-07-pdf-jump-navigation/annotation-07-04-SUMMARY.md"
      provides: "Recorded result of the manual Obsidian navigation check"
  key_links:
    - from: "annotation page badge"
      to: "native Obsidian PDF view"
      via: "the Phase 7 resolver and workspace.openLinkText"
      pattern: "#page="
---

<objective>
Verify the completed OVLY-01 flow in a real Obsidian session after all automated helper, runtime, and DOM gates pass.

Purpose: Confirm that Obsidian's installed PDF viewer honors the planned page link and that navigation preserves the PaperForge panel state.
Output: Automated gate evidence plus a blocking human verification result recorded in the plan summary.
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
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-01-SUMMARY.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-02-SUMMARY.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-03-SUMMARY.md
</context>

## Artifacts this phase produces

- Passing focused helper, runtime, and DOM test evidence.
- A real Obsidian navigation result recorded in `annotation-07-04-SUMMARY.md`.

<tasks>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 1: Verify source-PDF page navigation in Obsidian</name>
  <files>
    None; verification-only checkpoint.
  </files>
  <read_first>
    - `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-03-SUMMARY.md` for implementation and automated test results.
    - `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md` D-01 through D-15 acceptance intent.
  </read_first>
  <action>
    Run the automated gate first. Then pause for the user to verify a recognized paper in the actual Obsidian vault using an imported annotation whose source attachment key matches the canonical PDF candidate. Do not modify vault notes, annotation data, Zotero data, or plugin settings as part of the check.
  </action>
  <what-built>
    A page-badge jump action that resolves a canonical source PDF, converts `pageIndex + 1`, uses Obsidian's normal opening behavior, degrades to the same plain PDF when precise positioning is unavailable, and preserves the annotation list state.
  </what-built>
  <how-to-verify>
    1. Open Obsidian with the PaperForge plugin and a recognized paper that has at least one imported annotation for its known source PDF.
    2. In the PaperForge annotation section, set a non-default search, grouping, or type/color filter and expand one row so state preservation is observable.
    3. Confirm the target row's page badge is a distinct interactive control with an explanatory tooltip; click it without clicking the expand control.
    4. Confirm Obsidian opens the corresponding source PDF in its normal workspace location and lands on the annotation page (`pageIndex + 1`) when the installed viewer supports `#page=` links.
    5. Return focus to the PaperForge panel and confirm search/group/filter values, expanded rows, and loaded annotations remain intact.
    6. Confirm no overlay marks/popovers appear and no annotation, note frontmatter, Zotero record, or PaperForge metadata is changed.
  </how-to-verify>
  <verify>
    <automated>node --check paperforge/plugin/main.js</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-navigation.test.mjs tests/annotation-main-runtime.test.mjs tests/annotation-section-dom.test.mjs tests/annotation-bridge.test.mjs</automated>
    <human-check>Complete steps 1-6 above and report whether the exact PDF/page opened and panel state remained intact.</human-check>
  </verify>
  <acceptance_criteria>
    Focused automated suites pass; the real page badge opens the matching source PDF at the expected page where supported; panel state remains unchanged; no overlay or write behavior occurs.
  </acceptance_criteria>
  <done>The user approves the Obsidian navigation behavior or reports a concrete discrepancy for gap planning.</done>
  <resume-signal>Type "approved" or describe the PDF, page, fallback, state-preservation, accessibility, or read-only discrepancy.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Automated mocks -> installed Obsidian | The final viewer behavior depends on the user's installed Obsidian PDF implementation. |
| Human observation -> completion record | The checkpoint result must distinguish exact-page success from plain-PDF degradation. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-07-12 | Spoofing | manual target identity | mitigate | Use a known annotation/PDF pair and verify the corresponding source document, not merely any open PDF. |
| T-annotation-07-13 | Repudiation | manual result | mitigate | Record exact PDF/page/fallback and state-preservation outcome in `annotation-07-04-SUMMARY.md`. |
| T-annotation-07-14 | Tampering | live vault data | mitigate | Verification is navigation-only and explicitly excludes editing notes, annotations, settings, metadata, and Zotero records. |
| T-annotation-07-SC | Tampering | package supply chain | accept | The checkpoint installs no packages and runs only existing project tests plus the installed plugin. |
</threat_model>

## Multi-Source Coverage Audit

| SOURCE | ID | Feature/Requirement | Plan | Status | Notes |
|--------|----|---------------------|------|--------|-------|
| GOAL | — | Jump from an annotation row to the corresponding PDF and page | 01-04 | COVERED | Pure resolution, runtime opening, DOM action, and real Obsidian verification. |
| REQ | OVLY-01 | Jump from list item to corresponding PDF/page when source PDF is available | 01-04 | COVERED | All plans carry OVLY-01. |
| RESEARCH | — | Research and UI-SPEC explicitly skipped by developer | — | EXCLUDED | No RESEARCH.md assertions exist to plan. |
| PATTERNS | — | Pure helper mirrored into runtime bundle | 01-02 | COVERED | Exported helper tests plus equivalent inlined runtime helpers. |
| PATTERNS | — | Existing vault/workspace opening seam and friendly Notice behavior | 02 | COVERED | Uses getAbstractFileByPath then openLinkText with sanitized fallback notices. |
| PATTERNS | — | Semantic page button, separate expansion control, and compact styles | 03 | COVERED | DOM and CSS regression coverage. |
| PATTERNS | — | Exact page-link behavior lacked an analog | 01-04 | COVERED | Isolated `#page=` contract, runtime fallback, and manual installed-Obsidian check. |
| CONTEXT | D-01 | Page badge is the explicit primary jump action | 03-04 | COVERED | Semantic button and manual check. |
| CONTEXT | D-02 | Tooltip and accessible label explain the jump | 03-04 | COVERED | DOM assertions and manual check. |
| CONTEXT | D-03 | Expand and navigation stay independent | 03-04 | COVERED | Bidirectional event-isolation tests. |
| CONTEXT | D-04 | Resolve specific attachment identity first | 01-02 | COVERED | Pure exact-match gate consumed by runtime. |
| CONTEXT | D-05 | Use canonical metadata/path conventions; no guessed/external path | 01-02 | COVERED | Canonical path parser and vault check. |
| CONTEXT | D-06 | Main-PDF fallback only after confirmation or one identity-free candidate | 01 | COVERED | Explicit helper cases. |
| CONTEXT | D-07 | Uncertain attachment identity fails closed | 01-03 | COVERED | No target, no open, disabled affordance. |
| CONTEXT | D-08 | pageIndex is authoritative and converted to one-based page | 01-02 | COVERED | Helper arithmetic and runtime target tests. |
| CONTEXT | D-09 | Use supported page fragment/viewer behavior | 01-04 | COVERED | Isolated page link and real viewer check. |
| CONTEXT | D-10 | Failed exact positioning opens the same plain PDF and notices | 02 | COVERED | Bounded retry test. |
| CONTEXT | D-11 | Invalid page does not block a confirmed PDF | 01-03 | COVERED | Plain target remains enabled and opens. |
| CONTEXT | D-12 | Follow existing Obsidian opening behavior | 02-04 | COVERED | `openLinkText(..., '')`, no forced split. |
| CONTEXT | D-13 | Annotation panel state remains intact | 02-04 | COVERED | State snapshots, DOM isolation, manual check. |
| CONTEXT | D-14 | Friendly notices reveal no raw diagnostics | 01-02 | COVERED | Stable reasons and sanitization tests. |
| CONTEXT | D-15 | Navigation is read-only | 02-04 | COVERED | Mutation spies, scope regressions, manual check. |

Deferred overlay rendering/popovers, local annotation editing, Zotero write-back, database mutation, concept-card evidence, and the Phase 9 display-layer gate are intentionally absent.

<verification>
- Focused Phase 7 helper, runtime, DOM, and bridge suites pass.
- Manual steps confirm the installed Obsidian viewer behavior and panel-state preservation.
</verification>

<success_criteria>
- [ ] All automated Phase 7 suites pass before the checkpoint.
- [ ] User confirms the correct source PDF opens.
- [ ] User confirms exact page landing where installed Obsidian supports it, or the tested plain-PDF fallback and notice occur.
- [ ] Annotation panel state remains intact.
- [ ] No overlay or write behavior appears.
</success_criteria>

<output>
After approval, create `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-04-SUMMARY.md` and record the exact manual outcome.
</output>
