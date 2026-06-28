---
phase: annotation-08-pdf-overlay-rendering-spike-and-implementation
plan: "04"
type: execute
wave: 4
depends_on:
  - annotation-08-03
files_modified:
  - paperforge/plugin/main.js
  - paperforge/plugin/styles.css
  - paperforge/plugin/tests/annotation-overlay.test.mjs
  - paperforge/plugin/tests/annotation-main-runtime.test.mjs
  - paperforge/plugin/tests/annotation-section-dom.test.mjs
  - .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-OBSIDIAN-OVERLAY-HARNESS.md
requirements:
  - OVLY-02
  - OVLY-03
  - OVLY-04
  - OVLY-05
requirements_addressed:
  - OVLY-02
  - OVLY-03
  - OVLY-04
  - OVLY-05
autonomous: false
decision_coverage:
  - D-01
  - D-02
  - D-03
  - D-04
  - D-05
  - D-06
  - D-07
  - D-08
  - D-09
  - D-10
  - D-11
  - D-12
  - D-13
  - D-14
  - D-15
  - D-16
  - D-17
  - D-18
  - D-19
  - D-20
  - D-21
  - D-22
  - D-23
  - D-24
must_haves:
  truths:
    - "OVLY-02: Final gate proves overlay marks render in automated fake viewer tests when supported, or disabled/fallback behavior preserves list/jump when unsupported."
    - "OVLY-03: Final gate proves marks are scoped to active PDF/paper/page and stale marks are removed."
    - "OVLY-04: Clicking or focusing an overlay mark opens a lightweight read-only popover/detail surface."
    - "OVLY-05: Manual Obsidian harness covers only live viewer internals and records safe fallback if internals are unavailable."
    - "Context decision coverage for this phase set is explicit: D-01 D-02 D-03 D-04 D-05 D-06 D-07 D-08 D-09 D-10 D-11 D-12 D-13 D-14 D-15 D-16 D-17 D-18 D-19 D-20 D-21 D-22 D-23 D-24."
    - "This plan directly implements D-03 D-04 D-14 D-15 D-16 D-17 D-18 D-19 D-22 D-23 D-24 and verifies D-01 through D-24 as a phase set."
  artifacts:
    - path: "paperforge/plugin/main.js"
      provides: "Read-only overlay popover/detail interaction"
    - path: "paperforge/plugin/styles.css"
      provides: "Popover and focus styling under the overlay namespace"
    - path: "paperforge/plugin/tests/annotation-overlay.test.mjs"
      provides: "Popover view-model helper coverage"
    - path: "paperforge/plugin/tests/annotation-main-runtime.test.mjs"
      provides: "Popover interaction and final runtime gate"
    - path: "paperforge/plugin/tests/annotation-section-dom.test.mjs"
      provides: "Forbidden controls and overlay/list coexistence regressions"
    - path: ".planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-OBSIDIAN-OVERLAY-HARNESS.md"
      provides: "Manual live Obsidian overlay or fallback verification record"
  key_links:
    - from: "paperforge/plugin/main.js"
      to: "paperforge/plugin/src/testable.js"
      via: "buildAnnotationPopoverViewModel output rendered through textContent/setText"
      pattern: "buildAnnotationPopoverViewModel"
    - from: ".planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-OBSIDIAN-OVERLAY-HARNESS.md"
      to: ".planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PDF-VIEWER-SPIKE.md"
      via: "final manual result references the spike attach/fallback decision"
      pattern: "PDF-VIEWER-SPIKE"
---

<objective>
Add the read-only overlay popover/detail surface and complete the final automated plus live Obsidian verification gate.

Purpose: Users must be able to inspect selected text/comment/source from an overlay mark without editing or writing anything, and Phase 8 must close with proof that either overlay rendering works safely or fallback behavior is intact.
Output: Popover runtime/CSS/tests and `annotation-08-OBSIDIAN-OVERLAY-HARNESS.md`.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md
@.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-RESEARCH.md
@.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PATTERNS.md
@.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PDF-VIEWER-SPIKE.md
@.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-03-SUMMARY.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-03-SUMMARY.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-04-SUMMARY.md
@paperforge/plugin/main.js
@paperforge/plugin/src/testable.js
@paperforge/plugin/styles.css
@paperforge/plugin/tests/annotation-main-runtime.test.mjs
@paperforge/plugin/tests/annotation-section-dom.test.mjs
@paperforge/plugin/tests/annotation-navigation.test.mjs
@paperforge/plugin/tests/annotation-bridge.test.mjs
</context>

<source_audit>
GOAL: Covered by adding the overlay inspection interaction and closing the risk-gated verification loop.
REQ: OVLY-02/OVLY-03 are rechecked by the final gate, OVLY-04 is implemented by the read-only popover, and OVLY-05 is covered by safe fallback harness results.
RESEARCH: Implements the final recommended wave: popover plus automated gate plus manual Obsidian harness.
CONTEXT: Implements D-14 through D-17 directly, verifies D-03/D-04/D-18/D-19/D-22/D-23/D-24, and preserves D-01 through D-13 and D-20 through the final gate. Deferred ideas are not included.
</source_audit>

<tasks>

<task type="auto">
  <name>Task 1: Add read-only overlay popover/detail interaction</name>
  <files>paperforge/plugin/main.js, paperforge/plugin/styles.css, paperforge/plugin/tests/annotation-overlay.test.mjs, paperforge/plugin/tests/annotation-main-runtime.test.mjs, paperforge/plugin/tests/annotation-section-dom.test.mjs</files>
  <action>Wire overlay mark click and keyboard focus/activation to a lightweight PDF-local popover/detail surface per D-14. Render the `buildAnnotationPopoverViewModel()` output with `textContent` or `setText`, showing selected text, comment, page label/page number, source/read-only provenance, attachment identity, and annotation identity per D-15. The popover must be read-only and must not include edit, delete, create, save, write-back, database, import/apply, or concept-card evidence controls per D-17. Per D-16, do not require sidebar/list row synchronization; the existing list and Phase 7 page badge remain independent. Add CSS under `SECTION 41 - PDF Annotation Overlay` using only `.paperforge-annotation-overlay-*` selectors and include focus/close behavior that does not obscure the PDF text more than needed.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check main.js; npm.cmd test -- annotation-overlay.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Overlay marks open a read-only popover with the required annotation details, no forbidden controls, and no sidebar/list/page-badge regression.</acceptance_criteria>
  <done>Popover runtime, CSS, helper tests, runtime tests, and DOM regressions pass.</done>
</task>

<task type="auto">
  <name>Task 2: Create final automated gate and manual Obsidian harness record</name>
  <files>.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-OBSIDIAN-OVERLAY-HARNESS.md, paperforge/plugin/main.js, paperforge/plugin/styles.css, paperforge/plugin/tests/annotation-overlay.test.mjs, paperforge/plugin/tests/annotation-main-runtime.test.mjs, paperforge/plugin/tests/annotation-section-dom.test.mjs</files>
  <action>Create `annotation-08-OBSIDIAN-OVERLAY-HARNESS.md` with sections for `Automated Gate`, `Manual Harness Scope`, `Supported Overlay Check`, `Unsupported Fallback Check`, `Read-Only Safety Check`, `Known Baseline Failures`, and `Final Result`. Record the exact focused commands and results: `node --check main.js`, `annotation-bridge.test.mjs`, `annotation-navigation.test.mjs`, `annotation-overlay.test.mjs`, `annotation-main-runtime.test.mjs`, and `annotation-section-dom.test.mjs`. The harness must state that manual Obsidian verification is only for live viewer internals; all helper/runtime/DOM behavior must be covered by automated tests. The final result must explicitly state whether overlay rendered or fallback remained active, and must confirm no Zotero write-back, no `annotations.db` mutation, no local annotation creation/editing/deletion, no continuous polling, no PDF identity guessing, and no raw error exposure.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check main.js; npm.cmd test -- annotation-bridge.test.mjs annotation-navigation.test.mjs annotation-overlay.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs; Pop-Location; $p='.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-OBSIDIAN-OVERLAY-HARNESS.md'; if (!(Test-Path $p)) { exit 1 }; $t=Get-Content -Raw -Encoding UTF8 $p; @('Automated Gate','Manual Harness Scope','Supported Overlay Check','Unsupported Fallback Check','Read-Only Safety Check','Final Result','OVLY-02','OVLY-03','OVLY-04','OVLY-05') | ForEach-Object { if ($t -notmatch [regex]::Escape($_)) { Write-Error \"missing $_\"; exit 1 } }"</automated>
  </verify>
  <acceptance_criteria>The final gate document exists, records automated test evidence, and defines the exact manual live-viewer verification path.</acceptance_criteria>
  <done>Automated gate passes and the manual harness document is ready for the live Obsidian check.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Perform live Obsidian overlay or fallback harness</name>
  <files>.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-OBSIDIAN-OVERLAY-HARNESS.md</files>
  <action>Run only the live viewer internals portion of the harness in Obsidian. Open a paper with imported annotations, use the Phase 7 page badge to open the source PDF, confirm either: supported mode renders PaperForge-owned semi-transparent overlay marks on the correct page/PDF and clicking/focusing a mark opens the read-only popover; or unsupported mode renders no marks while sidebar/list/filter/group/refresh/page badge remain usable. Confirm switching file/pane/paper or refreshing annotations tears down stale overlay marks. Record the result in the harness document. Do not edit annotations, do not write Zotero, do not mutate `annotations.db`, and do not expose raw errors.</action>
  <verify>
    <automated>powershell -NoProfile -Command "$p='.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-OBSIDIAN-OVERLAY-HARNESS.md'; $t=Get-Content -Raw -Encoding UTF8 $p; @('Final Result','read-only','sidebar/list','page badge','annotations.db') | ForEach-Object { if ($t -notmatch [regex]::Escape($_)) { Write-Error \"missing $_\"; exit 1 } }"</automated>
    <human-check>In Obsidian, approve that either overlay marks/popover work on the active PDF, or unsupported fallback leaves the annotation list and page jump workflow usable.</human-check>
  </verify>
  <acceptance_criteria>The harness result is recorded and validates OVLY-02/03/04/05 through automated tests plus the live viewer check.</acceptance_criteria>
  <done>Manual harness is approved or records actionable live-viewer issues while preserving safe fallback behavior.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Overlay mark DOM -> popover DOM | User-facing annotation text/comment/provenance becomes visible in a PDF-local surface. |
| Automated tests -> live Obsidian internals | Automated harness cannot prove the real PDF viewer DOM; manual harness covers only that boundary. |
| Active viewer lifecycle -> stale popover/marks | Pane/file/paper changes can leave outdated UI unless teardown is complete. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-08-04-S | Spoofing | Popover identity display | mitigate | Show source/read-only/attachment/annotation identity derived from normalized row, not guessed PDF state. |
| T-annotation-08-04-T | Tampering | Popover controls | mitigate | Prohibit edit/delete/create/save/write-back/database/import/apply/evidence controls in tests and harness. |
| T-annotation-08-04-R | Repudiation | Manual harness | mitigate | Record exact automated commands and live Obsidian result in the harness document. |
| T-annotation-08-04-I | Information Disclosure | Popover text/errors | mitigate | Render text via textContent/setText and expose friendly states only; no raw errors, raw JSON, tracebacks, or shell output. |
| T-annotation-08-04-D | Denial of Service | Popover/mark lifecycle | mitigate | Teardown on file/pane/paper/annotation/viewer changes; no continuous polling. |
| T-annotation-08-04-E | Elevation of Privilege | Zotero and annotations DB | mitigate | Read-only display only; no Zotero write-back and no `annotations.db` mutation. |
| T-annotation-08-04-SC | Tampering | npm/pip/cargo installs | accept | No package installs are planned; use existing test stack. |
</threat_model>

<verification>
Final automated gate: `node --check main.js` plus `annotation-bridge.test.mjs`, `annotation-navigation.test.mjs`, `annotation-overlay.test.mjs`, `annotation-main-runtime.test.mjs`, and `annotation-section-dom.test.mjs`. Manual Obsidian verification is limited to live PDF viewer internals.
</verification>

<success_criteria>
- Overlay popover shows selected text, comment, page, source/read-only provenance, and identity without edit/write controls.
- Focused annotation automated suite passes.
- Manual harness records either working overlay render/popover or safe disabled/fallback behavior.
- Sidebar/list/filter/group/refresh and Phase 7 page badge remain usable.
</success_criteria>

<output>
Create `.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-04-SUMMARY.md` when done.
</output>
