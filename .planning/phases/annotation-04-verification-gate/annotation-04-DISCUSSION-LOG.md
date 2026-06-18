# Annotation Phase 4: Annotation Verification Gate - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** annotation-04-verification-gate
**Areas discussed:** gate strictness, fixture policy, failure classification, release commands, safety audit

---

## Gate Strictness

| Option | Description | Selected |
|--------|-------------|----------|
| Targeted annotation gate | Annotation unit tests, affected CLI tests, and compile checks are blocking; full repo is advisory. | Yes |
| Entire repository must be green | Stronger but not appropriate while unrelated upstream baseline failures are already known. | |

**User's choice:** User asked to follow the recommended direction.
**Notes:** Phase 4 should not hide unrelated baseline failures, but should not let them obscure annotation-specific readiness.

---

## Fixture Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Generate SQLite fixtures in tests | Transparent, deterministic, and easy to evolve with schema expectations. | Yes |
| Commit a binary SQLite fixture | Closer to a real file but harder to inspect and easier to rot. | |

**User's choice:** User asked to follow the recommended direction.
**Notes:** The generated fixture should include a parent item, PDF attachment, and multiple annotation rows.

---

## Failure Classification

| Option | Description | Selected |
|--------|-------------|----------|
| Three-bucket verification report | Split blocking annotation failures, known unrelated baseline failures, and advisory risks. | Yes |
| Single pass/fail bucket | Simpler but makes existing unrelated failures look like annotation regressions. | |

**User's choice:** User asked to follow the recommended direction.
**Notes:** This is important because prior phases already identified unrelated baseline failures in config tests and optional dependencies.

---

## Release Gate Commands

| Option | Description | Selected |
|--------|-------------|----------|
| Annotation-focused command set | Run annotation unit tests, annotation CLI tests, compile checks, and optional CLI smoke. | Yes |
| Full repo as blocking release gate | Too broad for this phase because known unrelated failures are outside annotation v0.1. | |

**User's choice:** User asked to follow the recommended direction.
**Notes:** The final verification document can still mention full-repo status as advisory.

---

## Safety Audit

| Option | Description | Selected |
|--------|-------------|----------|
| Include explicit safety audit | Confirm no Zotero write-back and no Obsidian runtime dependency. | Yes |
| Rely only on tests | Tests are necessary but the release gate should make safety evidence visible. | |

**User's choice:** User asked to follow the recommended direction.
**Notes:** The audit should check that writes target PaperForge `annotations.db`, not Zotero SQLite.

---

## Agent's Discretion

- Exact test-file split.
- Exact verification report format.
- Whether service/export behavior is covered through direct unit tests, CLI tests, or both.

## Deferred Ideas

- Obsidian PDF overlay.
- Local annotation editing.
- Zotero write-back.
- Concept-card/deep-reading evidence integration.
- Full baseline cleanup unrelated to annotation v0.1.
