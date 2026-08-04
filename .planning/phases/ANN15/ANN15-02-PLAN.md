---
phase: ANN15
plan: ANN15-02
type: execute
status: planned
wave: 1
depends_on: []
files_modified:
  - .planning/phases/ANN15/ANN15-SAFETY-AUDIT.md
requirements:
  - SAFE-01
  - SAFE-02
  - SAFE-03
requirements_addressed:
  - SAFE-01
  - SAFE-02
  - SAFE-03
user_setup: []
autonomous: true
decision_coverage:
  - D-16
  - D-17
  - D-18
  - D-19
  - D-20
must_haves:
  truths:
    - "D-16/D-20: Safety scans are scoped to canvas-owned files, relevant tests, and CSS/connector surfaces, with legacy v0.2 occurrences classified by ownership."
    - "D-17: The audit proves no read-only-breaking controls, no canvas-owned persistence/write side effects, and no canvas-owned native PDF viewer DOM dependency."
    - "D-18: Existing main.js storage/settings/native-overlay hits are recorded in an Allowed legacy occurrences table."
    - "D-19: Canvas-owned violations are blockers; allowlisted legacy occurrences are evidence, not blockers."
  artifacts:
    - path: ".planning/phases/ANN15/ANN15-SAFETY-AUDIT.md"
      provides: "Scoped safety scan evidence, strict canvas-owned blockers, and allowlisted legacy occurrences"
  key_links:
    - from: ".planning/phases/ANN15/ANN15-SAFETY-AUDIT.md"
      to: ".planning/phases/ANN15/ANN15-VERIFICATION.md"
      via: "SAFE-01/SAFE-02/SAFE-03 evidence consumed by final report"
      pattern: "Allowed legacy occurrences"
---

# ANN15-02 Plan: Scoped Safety Audit and Legacy Allowlist

## Objective

Create the ANN15 safety audit evidence that proves the Reading Canvas remains read-only, has no canvas-owned persistence/write side effects, and does not depend on native Obsidian PDF viewer DOM internals as its foundation.

## Scope

- Create `.planning/phases/ANN15/ANN15-SAFETY-AUDIT.md`.
- Audit canvas-owned modules, canvas-focused tests, and Reading Canvas CSS/connector surfaces.
- Record allowed legacy v0.2 storage/settings/native overlay occurrences without making them ANN15 blockers.
- Classify each finding as `PASS`, `FAIL`, `BASELINE`, or `NOT APPLICABLE`.

## Out of Scope

- Do not remove or rewrite legacy v0.2 fallback, storage, settings, native PDF overlay, `annotations.db`, `localStorage`, `saveData`, `pdf-viewer`, `pdf-embed`, or `data-page-number` occurrences simply because they appear in broad scans.
- Do not broaden ANN15 into new read/write controls, annotation editing, Zotero write-back, native PDF anchoring, or persistent layout.

## Tasks

### Task 1: Define Strict Targets and Allowlisted Legacy Areas

**Files:** `.planning/phases/ANN15/ANN15-SAFETY-AUDIT.md`

**Action:** Create `ANN15-SAFETY-AUDIT.md` with sections for `Strict canvas-owned targets`, `Evidence-gathering scans`, `Blockers`, and `Allowed legacy occurrences`. Strict targets must include `paperforge/plugin/src/canvas/*.js`, `paperforge/plugin/tests/canvas-*.test.mjs`, and Reading Canvas CSS/connector selectors in `paperforge/plugin/styles.css` per D-16. Allowed legacy areas must include existing `main.js` settings/storage/saveData paths, existing v0.2 native PDF overlay selectors, `src/testable.js`, and annotation tests that intentionally reference `annotations.db`, `localStorage`, PDF target resolution, or overlay behavior per D-18/D-20.

**Verify:**

```powershell
Select-String -Path .planning/phases/ANN15/ANN15-SAFETY-AUDIT.md -Pattern "Strict canvas-owned targets","Allowed legacy occurrences","main.js","annotations.db","pdf-viewer"
```

**Done:** The audit document makes ownership classification explicit before any scan evidence is interpreted.

### Task 2: Gather Scoped Read-Only, Persistence, and Native-DOM Evidence

**Files:** `.planning/phases/ANN15/ANN15-SAFETY-AUDIT.md`

**Action:** Run scoped evidence scans and record results in `ANN15-SAFETY-AUDIT.md` per D-16/D-17/D-19. Treat scan output as evidence to classify, not as a raw exit-code gate. Hits in canvas-owned production code for create/edit/delete/save/import/apply/write-back controls, canvas-owned persistence/write side effects, or native PDF viewer selectors are `FAIL` blockers. Hits in negative tests, comments explaining absence, or allowlisted legacy areas are recorded with rationale.

**Verify:**

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

**Done:** `ANN15-SAFETY-AUDIT.md` contains the command output summaries and a classification for read-only controls, persistence/write side effects, and native PDF DOM dependency.

### Task 3: Build the Allowed Legacy Occurrences Table

**Files:** `.planning/phases/ANN15/ANN15-SAFETY-AUDIT.md`

**Action:** Add an `Allowed legacy occurrences` table with columns `File`, `Pattern`, `Reason`, and `Disposition` per D-18/D-20. Include legacy `main.js` storage/settings/saveData paths, native PDF overlay selectors such as `pdf-viewer`, `pdf-embed`, and `data-page-number`, and any annotation fallback tests or helper code that intentionally preserve v0.2 behavior. State that these are not ANN15 blockers because they are outside canvas-owned code and are protected by v0.2 fallback tests.

**Verify:**

```powershell
Select-String -Path .planning/phases/ANN15/ANN15-SAFETY-AUDIT.md -Pattern "Allowed legacy occurrences","saveData","pdf-embed","data-page-number","BASELINE"
```

**Done:** The audit has no raw broad-scan blocker list; every legacy occurrence is either allowlisted with rationale or classified as a focused ANN15 blocker.

## Acceptance Criteria

- SAFE-01, SAFE-02, and SAFE-03 have scoped evidence.
- D-16 through D-20 are implemented exactly.
- The final report can cite the safety audit without inheriting ANN14's broad-scan false-positive problem.
