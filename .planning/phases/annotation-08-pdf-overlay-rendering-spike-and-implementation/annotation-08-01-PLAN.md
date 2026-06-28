---
phase: annotation-08-pdf-overlay-rendering-spike-and-implementation
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PDF-VIEWER-SPIKE.md
requirements:
  - OVLY-02
  - OVLY-05
requirements_addressed:
  - OVLY-02
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
    - "OVLY-02: Overlay rendering is treated as available only after a documented live viewer attachment contract exists."
    - "OVLY-05: If Obsidian PDF viewer internals cannot be confirmed, overlay support is disabled fail-closed and the sidebar/list/jump workflow remains usable."
    - "Context decision coverage for this phase set is explicit: D-01 D-02 D-03 D-04 D-05 D-06 D-07 D-08 D-09 D-10 D-11 D-12 D-13 D-14 D-15 D-16 D-17 D-18 D-19 D-20 D-21 D-22 D-23 D-24."
    - "This plan directly implements D-01 D-02 D-03 D-04 D-20 D-21 D-23 D-24."
  artifacts:
    - path: ".planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PDF-VIEWER-SPIKE.md"
      provides: "Viewer probe notes, attach contract, support decision, and fallback decision"
  key_links:
    - from: ".planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PDF-VIEWER-SPIKE.md"
      to: "paperforge/plugin/main.js"
      via: "named attach contract consumed by runtime overlay implementation"
      pattern: "Attach Contract"
---

<objective>
Create the Phase 8 viewer probe/spike document and the attach contract that gates all overlay implementation.

Purpose: Overlay rendering depends on live Obsidian PDF viewer internals, so Phase 8 must first record what is safe to attach to and must choose a disabled/fallback path when those internals cannot be confirmed.
Output: `.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PDF-VIEWER-SPIKE.md`.
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
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md
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
GOAL: Covered by creating the risk gate required before native PDF overlay rendering.
REQ: OVLY-02 is covered by defining when native viewer overlay is supported; OVLY-05 is covered by the disabled/fallback decision.
RESEARCH: Follows the recommended first wave: viewer probe and fallback contract before pure helpers or runtime rendering.
CONTEXT: Implements D-01, D-02, D-03, D-04, D-20, D-21, D-23, and D-24 directly. D-05 through D-19 and D-22 remain represented in the attach contract fields consumed by later plans. Deferred ideas from CONTEXT are not included.
</source_audit>

<tasks>

<task type="auto">
  <name>Task 1: Write viewer spike document and support decision</name>
  <files>.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PDF-VIEWER-SPIKE.md</files>
  <action>Create the spike document with these sections: `Scope`, `Live Probe Environment`, `Observed Viewer DOM`, `Attach Contract`, `Coordinate Contract`, `Lifecycle Hooks`, `Fallback Decision`, `Manual Probe Notes`, and `Implementation Handoff`. Per D-01 and D-21, document how the plugin should automatically try overlay only when active paper/PDF identity and a PDF page layer are confirmed. Per D-02 and D-24, the `Fallback Decision` must be either `supported` with exact attach fields or `unsupported` with a disabled/fallback reason. The document must state that Phase 8 is read-only, does not write Zotero, does not mutate `annotations.db`, does not replace sidebar/list/jump, does not continuously poll, does not guess PDF identity, and does not expose raw DOM/JSON/stack errors per D-03 and D-04.</action>
  <verify>
    <automated>powershell -NoProfile -Command "$p='.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PDF-VIEWER-SPIKE.md'; if (!(Test-Path $p)) { exit 1 }; $t=Get-Content -Raw -Encoding UTF8 $p; @('Attach Contract','Fallback Decision','D-01','D-02','D-03','D-04','D-21','D-24','read-only','annotations.db') | ForEach-Object { if ($t -notmatch [regex]::Escape($_)) { Write-Error \"missing $_\"; exit 1 } }"</automated>
  </verify>
  <acceptance_criteria>The spike document exists and gives the executor a concrete supported or unsupported overlay mode without requiring any code changes in this plan.</acceptance_criteria>
  <done>Spike document is present, includes the attach contract fields, and records a fail-closed fallback decision.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Verify live Obsidian viewer internals only where automation cannot</name>
  <files>.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PDF-VIEWER-SPIKE.md</files>
  <action>Use Obsidian only for the live viewer internals that cannot be proven in Vitest: open a PaperForge paper with a PDF, use the Phase 7 page badge to open the source PDF, inspect whether the active PDF view exposes a stable viewer root, page layer, active file/PDF identity signal, and usable coordinate frame. Record the observed selectors/hook names and whether attachment is supported. If any identity/page/layer signal cannot be confirmed, record `unsupported` and the disabled/fallback reason per D-02, D-03, and D-24. Do not edit annotations, do not write Zotero, do not run import/apply, and do not mutate `annotations.db`.</action>
  <verify>
    <automated>powershell -NoProfile -Command "$p='.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PDF-VIEWER-SPIKE.md'; $t=Get-Content -Raw -Encoding UTF8 $p; @('viewerRoot','pageLayer','activePdfIdentity','supportDecision','fallbackReason') | ForEach-Object { if ($t -notmatch $_) { Write-Error \"missing contract field $_\"; exit 1 } }"</automated>
    <human-check>In Obsidian, confirm the spike document accurately reflects the current PDF viewer: either a supported attach contract is recorded, or the unsupported fallback decision is recorded and the existing annotation list/page badge still works.</human-check>
  </verify>
  <acceptance_criteria>The live-only probe result is captured in the spike document and either enables later rendering safely or locks the later implementation to disabled/fallback behavior.</acceptance_criteria>
  <done>Manual live viewer result is recorded, and no implementation files were changed by Plan 01.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Obsidian PDF viewer DOM -> PaperForge overlay gate | Unstable viewer internals enter PaperForge only through the documented attach contract. |
| Annotation metadata -> spike decision | Imported annotation identity and position fields are untrusted until matched to the active PDF/page. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-08-01-S | Spoofing | Active PDF identity | mitigate | Require documented active PDF identity signal; if absent, record unsupported per D-02/D-24. |
| T-annotation-08-01-T | Tampering | PDF viewer DOM | mitigate | The plan only documents attach points and prohibits writing or deleting non-PaperForge DOM. |
| T-annotation-08-01-I | Information Disclosure | Spike notes and UI reasons | mitigate | Record friendly reasons only; no raw DOM errors, raw JSON, stack traces, shell output, or private local paths. |
| T-annotation-08-01-D | Denial of Service | Viewer probing | mitigate | No continuous polling; probe is manual/documented and later implementation must be event-driven per D-20. |
| T-annotation-08-01-E | Elevation of Privilege | Annotation data stores | mitigate | Plan forbids Zotero write-back, `annotations.db` mutation, import/apply commands, edit/delete/create controls. |
| T-annotation-08-01-SC | Tampering | npm/pip/cargo installs | accept | No package installs are planned; use existing Obsidian/Vitest/jsdom stack. |
</threat_model>

<verification>
Automated verification checks the spike document exists and contains the attach/fallback contract fields. Human verification is limited to live Obsidian PDF viewer internals.
</verification>

<success_criteria>
- `annotation-08-PDF-VIEWER-SPIKE.md` exists in the annotation-08 phase directory.
- The document records `supported` or `unsupported` with a clear fallback decision.
- The document preserves D-01 through D-04, D-20, D-21, D-23, and D-24 and keeps later plans read-only and fail-closed.
</success_criteria>

<output>
Create `.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-01-SUMMARY.md` when done.
</output>
