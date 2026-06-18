# Annotation Phase 4: Annotation Verification Gate - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Annotation Phase 4 is the release verification gate for annotation v0.1.

In plain terms: Phase 1 created the PaperForge-owned annotation database, Phase 2 safely imported Zotero PDF annotations into it, and Phase 3 exposed that behavior through stable CLI JSON commands. Phase 4 does not add a new user-facing feature. It proves the full v0.1 path works and clearly separates annotation regressions from unrelated upstream baseline failures.

This phase validates:

- Generated Zotero SQLite fixtures that behave like a small real Zotero library.
- Annotation storage, Zotero probing, normalization, import reconciliation, services, and CLI JSON behavior.
- Paper-scoped import safety, especially that importing one paper does not soft-delete annotations for another paper.
- No write-back to Zotero SQLite.
- No Obsidian runtime dependency for backend/CLI annotation workflows.

This phase intentionally does not implement the Obsidian PDF overlay, local PDF annotation editing, Zotero write-back, or concept-card/evidence integration.

</domain>

<decisions>
## Verification Decisions

### Gate Strictness
- **D-01:** Phase 4 should use targeted annotation tests, affected CLI JSON tests, and compile checks as the hard release gate.
- **D-02:** A full repository test run may be recorded as advisory, but it must not block annotation v0.1 when failures match known unrelated upstream baseline issues.
- **D-03:** Known unrelated baseline failures must be documented separately rather than mixed into annotation failures.

### Fixture Policy
- **D-04:** Tests should generate a minimal Zotero SQLite database at runtime instead of committing a brittle binary SQLite fixture.
- **D-05:** The generated fixture must include at least one parent paper, one PDF attachment, and multiple annotation rows.
- **D-06:** Fixture helpers should stay readable enough that future contributors can see which Zotero tables and columns are being simulated.

### Failure Classification
- **D-07:** Phase 4 verification output should classify results into three buckets:
  - blocking annotation failures;
  - known unrelated baseline failures;
  - advisory risks or gaps.
- **D-08:** Blocking annotation failures are failures in annotation storage, Zotero probe/import, annotation service behavior, or annotation CLI JSON contracts.
- **D-09:** Known unrelated baseline failures include the already documented Windows `tmp_path` PermissionError, `ld_deep_script` versus `pf_deep_script` key mismatch, and missing `filelock` dependency.

### Release Gate Commands
- **D-10:** The required command set should cover annotation unit tests, annotation CLI JSON tests, and Python compile checks for annotation-related modules.
- **D-11:** The planner may include a selected CLI smoke test if it helps prove the commands work together.
- **D-12:** The planner should avoid making the entire repository green a formal requirement for this phase because unrelated baseline failures are already known.

### Safety Audit
- **D-13:** Phase 4 must include an explicit safety audit showing that PaperForge never writes to Zotero SQLite.
- **D-14:** The safety audit should verify that writes target `annotations.db`, while Zotero access remains read-only/temp-copy based.
- **D-15:** Phase 4 must verify annotation backend/CLI flows do not require the Obsidian plugin runtime.

### Agent Discretion
- The planner may decide the exact test-file split.
- The planner may decide whether service/export coverage lives in unit tests or CLI tests, as long as both direct service behavior and user-facing JSON contracts are covered.
- The planner may decide the exact verification report format, as long as it preserves the three failure buckets above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/ROADMAP.md` - Annotation Phase 4 goal, dependencies, and success criteria.
- `.planning/REQUIREMENTS.md` - TEST-01 through TEST-05 and safety requirements.
- `.planning/STATE.md` - Current milestone state and known unrelated baseline failures.
- `.planning/PROJECT.md` - Current annotation v0.1 scope and out-of-scope boundaries.

### Prior Annotation Work
- `.planning/phases/annotation-01-storage-foundation/annotation-01-CONTEXT.md` - Storage foundation decisions.
- `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-CONTEXT.md` - Read-only Zotero import and scoped reconciliation decisions.
- `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-VERIFICATION.md` - Phase 2 verification evidence and known baseline failures.
- `.planning/phases/annotation-03-cli-json-contracts/annotation-03-CONTEXT.md` - CLI JSON contract decisions.
- `.planning/phases/annotation-03-cli-json-contracts/annotation-03-04-PLAN.md` - CLI success/error contract verification plan.

### Code and Tests
- `paperforge/annotation/` - Annotation database, schema, Zotero probe, normalization, importer, and service code.
- `paperforge/commands/annotation.py` - Annotation CLI command implementation.
- `paperforge/cli.py` - CLI parser and dispatch.
- `tests/unit/annotation/` - Existing annotation unit and integration tests.
- `tests/cli/` - Existing CLI JSON contract tests and helpers.

</canonical_refs>

<code_context>
## Existing Verification Evidence

Phase 2 already recorded:

- Targeted Phase 2 suite: 53 passed.
- Full annotation unit directory: 71 passed, 1 expected skip.
- Annotation modules compile cleanly.
- Code-path audit confirmed no Zotero write-back path.

Phase 3 state records:

- Annotation CLI JSON contracts are complete.
- 52 CLI tests and 71 unit tests passed after Phase 3 execution.
- Commands now cover `paperforge annotation import/list/status/export --json`.

Known unrelated baseline failures are already tracked in STATE.md and Phase 2 verification:

- Windows `tmp_path` PermissionError in `tests/test_config.py`.
- `ld_deep_script` versus `pf_deep_script` key mismatch.
- Missing `filelock` dependency causing a skipped or blocked memory rebuild integration path.

## Test Design Implications

- Phase 4 should prefer deterministic generated fixtures over hand-maintained binary test data.
- Phase 4 should verify both lower-level annotation behavior and user-facing CLI JSON contracts.
- Phase 4 should make the safety story visible in a verification note, not only implied by passing tests.

</code_context>

<specifics>
## Specific Ideas

- Add or consolidate fixture helpers that create a small Zotero-like SQLite DB in `tmp_path`.
- Include multiple annotations for one attachment and at least one unrelated paper/attachment to prove scoped reconciliation.
- Verify import preview and apply behavior through CLI JSON.
- Verify list/export output ordering and provenance fields.
- Verify status output includes schema/database health.
- Add a final `annotation-04-VERIFICATION.md` with:
  - commands run;
  - pass/fail summary;
  - requirement coverage for TEST-01 through TEST-05;
  - safety audit results;
  - known unrelated baseline failures.

</specifics>

<deferred>
## Deferred Ideas

- Obsidian PDF overlay remains deferred to a later annotation milestone.
- Local annotation editing remains deferred.
- Zotero write-back remains deferred and must not be implemented through direct SQLite mutation.
- Concept-card/deep-reading evidence integration remains deferred until annotation backend and CLI contracts stabilize.
- Full repository green status remains a broader baseline cleanup task, not a blocker for annotation v0.1 if annotation-specific gates pass.

</deferred>

---

*Phase: annotation-04-verification-gate*
*Context gathered: 2026-06-18*
