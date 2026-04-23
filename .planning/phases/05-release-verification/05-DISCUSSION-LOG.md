# Phase 5: Release Verification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 05-release-verification
**Areas discussed:** Test Coverage Scope, Smoke Test Design, Doc Consistency, Defect Audit, v2 Backlog

---

## Area: Test Coverage Scope (REL-01)

| Option | Description | Selected |
|--------|-------------|----------|
| 行覆盖率 80%+ | Require 80% line coverage on all key modules | |
| 关键路径覆盖 | Key modules have tests for critical paths, no percentage required | ✓ |
| 功能覆盖 | Every feature has at least one test | |

**User's choice:** 关键路径覆盖（no mandatory line/branch coverage percentage）
**Notes:** Phase 5 研究者需要检查 resolve_vault() fallback, load_simple_env() exception handling, Chinese path handling

---

## Area: Smoke Test Design (REL-02)

| Option | Description | Selected |
|--------|-------------|----------|
| pytest fixture | Runs as pytest fixture within existing test suite | |
| standalone script | tests/smoke_test.py as standalone Python script | ✓ |
| CI workflow | GitHub Actions workflow with sequential steps | |

**User's choice:** standalone script (tests/smoke_test.py)
**Notes:** 覆盖 6 步流程（doctor → selection-sync → index-refresh → ocr doctor dry-run → ocr queue dry-run → deep-reading）；OCR 只做 preflight，不真实提交 job

---

## Area: Doc Consistency (REL-03)

| Option | Description | Selected |
|--------|-------------|----------|
| manual review | Manual check by developer before release | |
| automated check via existing tests | extend test_command_docs.py + add README vs INSTALLATION.md check | ✓ |

**User's choice:** 扩展 test_command_docs.py + 新增 INSTALLATION 一致性测试
**Notes:** AGENTS.md 已更新为 paperforge CLI 格式（Phase 4），需要确认无残留 `<system_dir>` placeholder

---

## Area: Defect Audit

| Option | Description | Selected |
|--------|-------------|----------|
| informal确认 | Just confirm tests pass = no high-risk defects | |
| formal audit |逐条 DEFECTS.md 对照 Phase 1-4 实现，确认 fixed/deferred/superseded | ✓ |

**User's choice:** formal audit — 审计结果写回 DEFECTS.md，每条标注状态
**Notes:** Phase 5 研究者执行审计，对照 Phase 1-4 plan 文件和实现代码

---

## Area: v2 Requirements

| Option | Description | Selected |
|--------|-------------|----------|
| ignore | v2 requirements are future work, don't document deferral | |
| defer to backlog | Move to .planning/backlog.md with rationale | ✓ |

**User's choice:** 移到 backlog，用中文标注 defer 原因
**Notes:** INT-01/02/03/UX-01/02/03 都 defer；ROADMAP.md Phase 5 Implementation Notes 加一句说明

---

## Deferred Ideas

- INT-01: OCR provider plugin system — PaddleOCR must stabilize first
- INT-02: BBT settings auto-detection — requires BBT plugin API research
- INT-03: Scheduled worker automation — conflicts with Lite two-layer design
- UX-01: Setup wizard repair mode — current install flow sufficient
- UX-02: Base file import parameterization — base-refresh covers this
- UX-03: Pipeline health dashboard — not core to v1 value