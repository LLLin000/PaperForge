# ANN15 Validation Matrix

**Phase:** ANN15 - Canvas Verification Gate and Live Harness Record  
**Generated:** 2026-07-07  
**Status:** Planned

## Validation Goal

ANN15 is valid when the focused automated canvas/v0.2 fallback gate is explicit and hard-blocking, read-only and native-DOM safety is audited without broad legacy false positives, a live Obsidian harness record exists even when pending, and the final report states exactly which SAFE/TEST requirements are proven, pending, failed, or baseline.

## Wave Structure

| Wave | Plans | Purpose |
| --- | --- | --- |
| 1 | ANN15-01 | Focused automated gate contract, command evidence, focused failure policy, baseline bucket |
| 1 | ANN15-02 | Scoped safety audit and allowlisted legacy occurrence evidence |
| 1 | ANN15-03 | LIVE-HARNESS.md manual checklist and live/native confidence split |
| 2 | ANN15-04 | Final SAFE/TEST matrix, risk narrative, and conditional milestone confidence |

## Requirement Coverage

| Requirement | Planned Coverage | Verification Artifact |
| --- | --- | --- |
| SAFE-01 | ANN15-02 scans strict canvas-owned targets for create, edit, delete, save, import, apply, and write-back controls. ANN15-04 reports status. | `ANN15-SAFETY-AUDIT.md`, `ANN15-VERIFICATION.md` |
| SAFE-02 | ANN15-02 scans strict canvas-owned targets for `annotations.db`, Zotero/vault/settings/localStorage/persistent-layout writes, and classifies legacy hits. ANN15-04 reports status. | `ANN15-SAFETY-AUDIT.md`, `ANN15-VERIFICATION.md` |
| SAFE-03 | ANN15-02 scans strict canvas-owned targets for native PDF viewer DOM selectors and separates allowed v0.2 overlay code. ANN15-04 reports status. | `ANN15-SAFETY-AUDIT.md`, `ANN15-VERIFICATION.md` |
| SAFE-04 | ANN15-03 records live/native split; ANN15-04 reports PaperForge Canvas confidence separately from v0.2 native PDF overlay confidence. | `LIVE-HARNESS.md`, `ANN15-VERIFICATION.md` |
| TEST-01 | ANN15-01 runs focused canvas context/controller coverage for loaded, empty, missing paper, missing DB/source, command failure, stale result, refresh, and teardown. | `ANN15-AUTOMATED-GATE.md` |
| TEST-02 | ANN15-01 runs focused view-model, layout, source-anchor, navigation, connector, and render tests for card/source/connector planning. | `ANN15-AUTOMATED-GATE.md` |
| TEST-03 | ANN15-01 runs focused DOM/runtime tests for rendering, focus, fallback actions, connector teardown, and forbidden write controls; ANN15-02 provides safety scan evidence. | `ANN15-AUTOMATED-GATE.md`, `ANN15-SAFETY-AUDIT.md` |
| TEST-04 | ANN15-01 runs the locked v0.2 annotation fallback preservation slice. | `ANN15-AUTOMATED-GATE.md` |
| TEST-05 | ANN15-03 creates the live Obsidian harness note and ANN15-04 records whether native PDF overlay remains pending. | `LIVE-HARNESS.md`, `ANN15-VERIFICATION.md` |

## Decision Coverage

| Decision | Planned Coverage |
| --- | --- |
| D-01 | ANN15-01 defines the focused v0.3 canvas plus v0.2 fallback preservation hard gate. |
| D-02 | ANN15-01 creates a Baseline bucket for non-ANN15 broader-suite failures. |
| D-03 | ANN15-01 locks the explicit minimum command list and prevents replacement or omission. |
| D-04 | ANN15-01 treats focused-slice failures as blockers unless explicitly proven unrelated baseline behavior. |
| D-05 | ANN15-01 includes `node --check main.js` from `paperforge/plugin`. |
| D-06 | ANN15-01 includes `node --check` for ANN10-ANN14 canvas modules that exist. |
| D-07 | ANN15-01 includes the locked v0.3 canvas Vitest slice. |
| D-08 | ANN15-01 includes the locked v0.2 fallback preservation Vitest slice. |
| D-09 | ANN15-03 creates `LIVE-HARNESS.md`. |
| D-10 | ANN15-03 requires environment, sample paper, steps, observations, statuses, conclusion, and limitations. |
| D-11 | ANN15-03 includes the Canvas-first workflow checklist. |
| D-12 | ANN15-03 and ANN15-04 keep native PDF overlay confidence separately labeled. |
| D-13 | ANN15-03 marks live status `PENDING - not executed in this environment` when Obsidian cannot be opened. |
| D-14 | ANN15-03 and ANN15-04 state that jsdom/automated tests are not live Obsidian proof. |
| D-15 | ANN15-03 uses `PASS`, `FAIL`, `PENDING`, and `NOT APPLICABLE` per-step statuses plus final conclusion. |
| D-16 | ANN15-02 scopes scans to canvas-owned files, relevant tests, and CSS/connector surfaces with allowlists. |
| D-17 | ANN15-02 proves read-only controls, persistence/write side effects, and native PDF DOM dependency boundaries. |
| D-18 | ANN15-02 records allowed legacy occurrences with file, pattern, reason, and disposition. |
| D-19 | ANN15-02 treats canvas-owned violations as blockers and allowlisted legacy occurrences as non-blocking evidence. |
| D-20 | ANN15-02 avoids broad forbidden scans that make legacy v0.2 tokens blockers. |
| D-21 | ANN15-04 creates the SAFE-01 through SAFE-04 and TEST-01 through TEST-05 report matrix. |
| D-22 | ANN15-04 uses `PASS`, `FAIL`, `PENDING`, and `BASELINE` report statuses. |
| D-23 | ANN15-04 writes the risk narrative for automation, live harness, baseline, safety scan, and unproven claims. |
| D-24 | ANN15-04 explicitly states the live/native split. |
| D-25 | ANN15-04 prevents pending items from being called done, verified, or passed. |
| D-26 | ANN15-04 allows conditional completion only when the focused gate passes and `LIVE-HARNESS.md` exists, with pending caveat when applicable. |

## Multi-Source Coverage Audit

| Source Type | Item | Covered By |
| --- | --- | --- |
| GOAL | Verify the full read-only canvas and document automated versus live Obsidian confidence. | ANN15-01, ANN15-02, ANN15-03, ANN15-04 |
| REQ | SAFE-01 | ANN15-02, ANN15-04 |
| REQ | SAFE-02 | ANN15-02, ANN15-04 |
| REQ | SAFE-03 | ANN15-02, ANN15-04 |
| REQ | SAFE-04 | ANN15-03, ANN15-04 |
| REQ | TEST-01 | ANN15-01, ANN15-04 |
| REQ | TEST-02 | ANN15-01, ANN15-04 |
| REQ | TEST-03 | ANN15-01, ANN15-02, ANN15-04 |
| REQ | TEST-04 | ANN15-01, ANN15-04 |
| REQ | TEST-05 | ANN15-03, ANN15-04 |
| RESEARCH | Existing focused Vitest files form the hard gate surface. | ANN15-01 |
| RESEARCH | Minimum command slice must be explicit and run from `paperforge/plugin`. | ANN15-01 |
| RESEARCH | Broader suite failures belong in a baseline bucket when unrelated. | ANN15-01, ANN15-04 |
| RESEARCH | Safety scans must use ownership classification and allowlisted legacy areas. | ANN15-02 |
| RESEARCH | `LIVE-HARNESS.md` exists even when live Obsidian is unavailable. | ANN15-03 |
| RESEARCH | Final report maps SAFE/TEST statuses and separates confidence layers. | ANN15-04 |
| CONTEXT | D-01 through D-08 automated gate decisions. | ANN15-01 |
| CONTEXT | D-09 through D-15 live harness decisions. | ANN15-03 |
| CONTEXT | D-16 through D-20 scoped safety decisions. | ANN15-02 |
| CONTEXT | D-21 through D-26 final report decisions. | ANN15-04 |
| CONTEXT | Deferred scope excludes new UI features, editing, write-back, persistent layout, PDF.js, native PDF DOM anchoring, AI cards, and multi-paper boards. | Out of Scope in all plans |

## Focused Verification Commands

These commands are planned evidence commands, not results. Execute them from `paperforge/plugin` during ANN15-01.

```powershell
Push-Location paperforge/plugin
node --check main.js
node --check src/canvas/context.js
node --check src/canvas/annotations.js
node --check src/canvas/controller.js
node --check src/canvas/view-model.js
node --check src/canvas/layout.js
node --check src/canvas/surface.js
node --check src/canvas/anchors.js
node --check src/canvas/navigation.js
node --check src/canvas/connectors.js
node --check src/canvas/render.js
node --check src/canvas/index.js
npm.cmd test -- canvas-context.test.mjs canvas-controller.test.mjs canvas-viewmodel.test.mjs canvas-layout.test.mjs canvas-source-anchor.test.mjs canvas-navigation.test.mjs canvas-connectors.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs
npm.cmd test -- annotation-navigation.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs annotation-overlay.test.mjs
Pop-Location
```

## Scoped Safety Evidence Commands

These commands gather evidence for ANN15-02. Their output must be classified by ownership; raw hits in legacy v0.2 areas are not blockers.

```powershell
Push-Location paperforge/plugin
$canvasTestFiles = @(
  "tests/canvas-context.test.mjs",
  "tests/canvas-controller.test.mjs",
  "tests/canvas-viewmodel.test.mjs",
  "tests/canvas-layout.test.mjs",
  "tests/canvas-source-anchor.test.mjs",
  "tests/canvas-navigation.test.mjs",
  "tests/canvas-connectors.test.mjs",
  "tests/canvas-render.test.mjs",
  "tests/canvas-card-dom.test.mjs",
  "tests/canvas-main-runtime.test.mjs"
)
function Invoke-Ann15Scan($label, $pattern) {
  Write-Host "## $label"
  rg -n $pattern src/canvas styles.css @canvasTestFiles
  if ($LASTEXITCODE -eq 1) {
    Write-Host "NO HITS"
  } elseif ($LASTEXITCODE -ge 2) {
    throw "rg failed for $label with exit code $LASTEXITCODE"
  }
}
Invoke-Ann15Scan "read-only controls" "contenteditable|create annotation|edit annotation|delete annotation|save annotation|import annotation|apply annotation|write-back|write back|remove annotation|evidence mutation|concept-card mutation"
Invoke-Ann15Scan "persistence/write side effects" "annotations\.db|localStorage|saveData|writeFile|writeText|vault\.modify|modify\(|setItem|persistent layout|layout state"
Invoke-Ann15Scan "native PDF DOM dependency" "pdf-viewer|pdf-embed|pdf-container|data-page-number|PDFViewer|viewerContainer"
Pop-Location
```

## Success Criteria

1. The focused automated gate uses the locked D-05 through D-08 command list and separates optional baseline failures.
2. Safety audit evidence is scoped and allowlisted, not a broad false-positive scan.
3. `LIVE-HARNESS.md` exists and uses honest live statuses.
4. `ANN15-VERIFICATION.md` reports SAFE-01 through SAFE-04 and TEST-01 through TEST-05 using `PASS`, `FAIL`, `PENDING`, and `BASELINE`.
5. Pending live or native PDF overlay items are not described as passed.
