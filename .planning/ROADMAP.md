# Roadmap: PaperForge

**Current milestone:** v1.12 Install & Runtime Closure
**Phase numbering:** Continuous. v1.11 ended at Phase 50. v1.12 starts at Phase 51.
**Granularity:** coarse

---

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-04-23)
- ✅ **v1.1 Sandbox Onboarding** — Phases 6-8 (shipped 2026-04-24)
- ✅ **v1.2 Systematization & Cohesion** — Phases 9-10 (shipped 2026-04-24)
- ✅ **v1.3 Path Normalization & Architecture Hardening** — Phases 11-12 (shipped 2026-04-24)
- ✅ **v1.4 Code Health & UX Hardening** — Phases 13-19 (shipped 2026-04-28)
- ✅ **v1.5 Obsidian Plugin Setup Integration** — Phases 20-21 (shipped 2026-04-29)
- ✅ **v1.6 AI-Ready Literature Asset Foundation** — Phases 22-26 (shipped 2026-05-04)
- ✅ **v1.7 Context-Aware Dashboard** — Phases 27-30 (shipped 2026-05-04)
- ✅ **v1.8 AI Discussion & Deep-Reading Dashboard** — Phases 31-36 (shipped 2026-05-07)
- ✅ **v1.9 Frontmatter Rationalization & Library-Record Deprecation** — Phases 37-41 (shipped 2026-05-07)
- ✅ **v1.10 Dependency Cleanup** — Phases 42-45 (shipped 2026-05-07)
- ✅ **v1.11 Merge Gate — v1.9 Ripple Remediation** — Phases 46-50 (shipped 2026-05-07)
- 🚧 **v1.12 Install & Runtime Closure** — Phases 51-54 (planned)

---

## Phases

- [ ] **Phase 51: Runtime Selection & Setup Gate** - Plugin-first setup exposes, validates, and consistently uses one Python interpreter.
- [ ] **Phase 52: Runtime Alignment & Failure Closure** - Runtime/package version drift, install failures, and packaging truth become repairable and non-murky.
- [ ] **Phase 53: Doctor Verdict Surface** - `paperforge doctor` becomes the single verdict and next-action surface for runtime health.
- [ ] **Phase 54: Dashboard Workflow Closure & Onboarding Surface** - Users can drive OCR and `/pf-deep` handoff from the Dashboard while docs point them to the plugin-first path.

## Phase Details

### Phase 51: Runtime Selection & Setup Gate
**Goal**: Users can see which Python interpreter PaperForge will use, override it when needed, and complete setup only when the install path is valid.
**Depends on**: Phase 50
**Requirements**: RUNTIME-01, RUNTIME-02, RUNTIME-03, RUNTIME-06
**Success Criteria** (what must be TRUE):
  1. User can open plugin settings and see the exact Python interpreter path PaperForge will use plus whether it came from auto-detection or manual override.
  2. User can enter a manual interpreter override in plugin settings and gets immediate validation before PaperForge uses it.
  3. When no override is set, install, update, version check, and runtime commands all use the same auto-detected interpreter in a defined order.
  4. Setup cannot complete without a valid `zotero_data_dir`, and the user is told exactly what to fix when it is missing or invalid.
**Plans**: 1 plan

Plan list:
- [ ] 51-001-PLAN.md — Runtime resolvePythonExecutable refactor, settings UI, consistent interpreter usage, zotero_data_dir required+validated
**UI hint**: yes

### Phase 52: Runtime Alignment & Failure Closure
**Goal**: Users can trust that the selected runtime, installed package version, and packaging metadata all line up, and install/runtime failures are classified into actionable repair paths.
**Depends on**: Phase 51
**Requirements**: RUNTIME-04, RUNTIME-05, CLEAN-02, CLEAN-03, CLEAN-04
**Success Criteria** (what must be TRUE):
  1. User can see when the selected interpreter's installed `paperforge` package version does not match the plugin version.
  2. User is offered a safe runtime sync or repair path when runtime/package drift is detected instead of guessing which environment is wrong.
  3. If install or sync fails, the failure is labeled in an actionable category such as missing Python, invalid interpreter, missing pip, dependency failure, package install failure, or network/source failure.
  4. Plugin/runtime version metadata comes from one canonical manifest source, so the version used for comparison is not ambiguous.
  5. The shipped runtime expectations match the actual package environment, including YAML support and tested Obsidian Bases compatibility on the documented minimum app version.
**Plans**: 1 plan

Plan list:
- [ ] 52-001-PLAN.md — Runtime Health settings section, dashboard drift banner, extended failure classification, Copy diagnostic, minAppVersion bump, PyYAML fix

### Phase 53: Doctor Verdict Surface
**Goal**: `paperforge doctor` gives one reliable diagnostic verdict for interpreter choice, installed package state, dependency health, and the user's next action.
**Depends on**: Phase 52
**Requirements**: DOCTOR-01, DOCTOR-02, DOCTOR-03, DOCTOR-04
**Success Criteria** (what must be TRUE):
   1. Running `paperforge doctor` shows the actual interpreter path and Python version being checked.
   2. `paperforge doctor` shows whether `paperforge` is installed in that interpreter, which version and package path it resolves to, and whether the user is in the wrong environment.
   3. `paperforge doctor` explicitly checks critical dependencies such as YAML support and tells the user how to repair missing pieces.
   4. `paperforge doctor` ends with a clear top-level verdict and next action instead of leaving the user with only raw check output.
**Plans**: 1 plan

Plan list:
- [ ] 53-001-PLAN.md — Interpreter resolution + package drift detection + refined dependency checks + final verdict

### Phase 54: Dashboard Workflow Closure & Onboarding Surface
**Goal**: Users can complete the normal OCR-to-agent handoff from the Dashboard, see the privacy boundary before OCR upload, and encounter plugin-first onboarding as the primary documented path.
**Depends on**: Phase 53
**Requirements**: DASH-01, DASH-02, DASH-03, CLEAN-01
**Success Criteria** (what must be TRUE):
  1. User can add or remove a paper from the OCR queue directly from the Dashboard without editing frontmatter by hand.
  2. Before OCR upload starts, the Dashboard shows a clear privacy warning that PDFs are sent to the PaddleOCR API.
  3. After OCR is ready, the Dashboard provides the paper's `zotero_key`, copies the full `/pf-deep <key>` command, and tells the user which Agent context to run it in.
  4. A new user following the main docs is guided to the plugin-first install path before older terminal-first entry points.
**Plans**: TBD
**UI hint**: yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 51. Runtime Selection & Setup Gate | 1/1 | Planned | - |
| 52. Runtime Alignment & Failure Closure | 1/1 | Planned | - |
| 53. Doctor Verdict Surface | 1/1 | Planned | - |
| 54. Dashboard Workflow Closure & Onboarding Surface | 0/TBD | Not started | - |

---
*Roadmap updated: 2026-05-08 — v1.12 roadmap created*
