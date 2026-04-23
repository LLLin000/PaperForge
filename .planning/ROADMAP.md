# Roadmap: PaperForge Lite Release Hardening

**Created:** 2026-04-23  
**Scope:** Make the local release flow reliable from setup through first deep-reading queue.

## Phase 1: Config And Command Foundation

**Goal:** Replace agent/manual placeholder path handling with a shared config resolver and stable user commands.

**Requirements:** CONF-01, CONF-02, CONF-03, CONF-04, CMD-01, CMD-02, CMD-03, DEEP-02

**Success Criteria:**
1. `paperforge paths` prints resolved vault, system, resources, literature, control, base, worker, and skill paths.
2. Environment variables override `paperforge.json` without breaking existing installs.
3. Worker and `/LD-deep` use one shared config/path resolver or equivalent duplicated-tested contract.
4. Documentation can show stable commands without `<system_dir>` placeholders.

**Implementation Notes:**
- Add a small CLI entrypoint or launcher script while keeping direct `literature_pipeline.py --vault ...` supported.
- Prefer a pure Python resolver module that can be reused by worker, validation, setup, and agent helpers.
- Keep `.env` loading deterministic: vault root, PaperForge `.env`, then process environment precedence rules documented clearly.

**Plans:** 4 plans

Plans:
- [x] 01-01-PLAN.md — Shared config resolver and path inventory contract (COMPLETE: 2026-04-23)
- [x] 01-02-PLAN.md — `paperforge` launcher, package entry point, and command dispatch (COMPLETE: 2026-04-23)
- [x] 01-03-PLAN.md — Worker, `/LD-deep`, setup, and validation resolver integration (COMPLETE: 2026-04-23)
- [x] 01-04-PLAN.md — Stable command documentation and setup next-step updates (COMPLETE: 2026-04-23)

## Phase 2: PaddleOCR And PDF Path Hardening

**Goal:** Make OCR failures diagnosable and retryable, especially for the API key/URL issue already observed.

**Requirements:** OCR-01, OCR-02, OCR-03, OCR-04, OCR-05, ZOT-01, ZOT-02

**Success Criteria:**
1. `paperforge ocr doctor` distinguishes missing token, bad URL, unauthorized response, network timeout, schema mismatch, and unreadable PDF.
2. OCR worker resolves common Zotero PDF paths before submission and records the resolved path in diagnostics.
3. Blocked/error records can be reset or retried with a documented command.
4. `meta.json` error messages are actionable and include a suggested next command.

**Implementation Notes:**
- Add tests with mocked `requests.post/get` responses for auth failure, changed schema, pending, running, done, provider error, and timeout.
- Add PDF resolver tests for absolute, vault-relative, system Zotero junction, and missing file cases.
- Consider normalizing auth header to `Bearer` and allowing an env override for header name/scheme if PaddleOCR requires it.

**Plans:** 4 plans

Plans:
- [x] 02-01-PLAN.md — PDF Path Resolver + Preflight (ZOT-01, OCR-02, ZOT-02) (COMPLETE: 2026-04-23)
- [x] 02-02-PLAN.md — OCR Failure Classification (OCR-03, OCR-04, OCR-05) (COMPLETE: 2026-04-23)
- [x] 02-03-PLAN.md — OCR Doctor Command (OCR-01) (COMPLETE: 2026-04-23)
- [x] 02-04-PLAN.md — Selection Sync PDF Reporting (ZOT-02) (COMPLETE: 2026-04-23)

## Phase 3: Config-Aware Obsidian Bases

**Goal:** Generate Base views that match the real operational workflow and respect custom directory names.

**Requirements:** BASE-01, BASE-02, BASE-03, BASE-04

**Success Criteria:**
1. Generated domain Bases include control, recommended analysis, pending OCR, completed OCR, pending deep reading, completed deep reading, formal cards, and all-records views.
2. `Literature Hub.base` provides cross-domain overview views.
3. Generated filters use resolved relative paths, not hardcoded `03_Resources`.
4. Existing user-edited `.base` files are not overwritten unless a refresh flag is used.

**Implementation Notes:**
- Convert the useful structure from `骨科.base`, `运动医学.base`, and `Literature Hub.base` into templates.
- Avoid depending on a single domain name; render per export/domain.
- Add snapshot-style tests for default paths and custom paths.

**Plans:** 2 plans

Plans:
- [x] 03-01-PLAN.md — Base Generation Refactor — 8 Views + Incremental Merge + Placeholder Substitution (COMPLETE: 2026-04-23)
- [x] 03-02-PLAN.md — CLI base-refresh + Tests (COMPLETE: 2026-04-23)

## Phase 4: End-To-End Onboarding And Validation

**Goal:** Turn setup into a guided, verifiable path from registration/configuration to a ready deep-reading queue.

**Requirements:** ONBD-01, ONBD-02, ONBD-03, ZOT-03, DEEP-01, DEEP-03

**Success Criteria:**
1. Install docs and `AGENTS.md` describe the exact full flow and current commands.
2. `validate_setup.py` or `paperforge doctor` reports category-level readiness: Python, vault, config, Zotero link, BBT export, Base files, OCR config, worker scripts, agent scripts.
3. After each worker command, output includes next steps and blocker-specific instructions.
4. `/LD-deep` prepare failures point to the command that fixes the blocker.

**Implementation Notes:**
- The docs should include a first-paper checklist with expected outputs.
- Validation should not require a real OCR job unless the user opts into live provider validation.
- Keep Chinese user-facing docs consistent with command output.

**Plans:** 4 plans

Plans:
- [x] 04-01-PLAN.md — deep-reading 三态 + verbose (ONBD-03, DEEP-01) (COMPLETE: 2026-04-23)
- [x] 04-02-PLAN.md — paperforge doctor 子命令 (ONBD-02) (COMPLETE: 2026-04-23)
- [x] 04-03-PLAN.md — AGENTS.md paperforge CLI 更新 (ONBD-03) (COMPLETE: 2026-04-23)
- [x] 04-04-PLAN.md — docs/README.md BBT 配置指南 (ONBD-01, ZOT-03) (COMPLETE: 2026-04-23)

## Phase 5: Release Verification

**Goal:** Prove the release is robust enough to ship and maintain.

**Requirements:** REL-01, REL-02, REL-03

**Success Criteria:**
1. Unit tests cover config resolver, path resolver, OCR state machine, Base rendering, and launcher commands.
2. A smoke test runs on a fixture vault without touching the real vault.
3. Release docs, setup wizard, command files, and generated AGENTS guide are internally consistent.
4. Known defects from `.planning/research/DEFECTS.md` are either fixed or explicitly deferred.

**Implementation Notes:**
- Use fixture Better BibTeX JSON and dummy PDFs.
- Mock network calls for normal CI; keep live PaddleOCR validation manual/optional.
- Do not overwrite the existing user-facing `AGENTS.md` with generic GSD instructions.

**Plans:** 2 plans

Plans:
- [x] 05-01-PLAN.md — Test coverage gaps: OCR state machine, Base rendering, command docs (REL-01, REL-03)
- [x] 05-02-PLAN.md — Fixture smoke test suite (REL-02)

## Phase Summary

| # | Phase | Goal | Requirements | Status |
|---|-------|------|--------------|--------|
| 1 | Config And Command Foundation | Stable commands and shared path/env resolution | 8 | COMPLETE |
| 2 | PaddleOCR And PDF Path Hardening | Diagnosable, retryable OCR | 7 | COMPLETE |
| 3 | Config-Aware Obsidian Bases | Real workflow Bases without hardcoded paths | 4 | COMPLETE |
| 4 | End-To-End Onboarding And Validation | User can complete first-paper flow | 6 | COMPLETE |
| 5 | Release Verification | Tests and docs prove ship readiness | 3 | COMPLETE |

---
*Roadmap created: 2026-04-23*
