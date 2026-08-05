---
name: architecture-review
description: >
  Use when asked to trace PaperForge architecture evidence end to end and
  emit a bound ArchitectureReview overlay over a validated DeterministicAudit —
  "架构审计" "audit trace" "trace this operation" "review this finding",
  or when another skill needs review-overlay semantics (adjudication,
  epistemic labeling, digest-bound review). Never for collecting facts,
  editing code, or changing the Contract.
source: paperforge
skill_version: 2026-08-05.1
skill_api_version: 2
---
# PaperForge Architecture Review

Model-invoked review overlay (#132, Slice B). Consumes a validated
DeterministicAudit, adjudicates every high-risk and unresolved edge, and emits
an `ArchitectureReview` bound to exact Contract, Survey, and Audit semantic
digests plus reconciler version. It never edits source, Contract, Survey,
DeterministicAudit, issues, or production artifacts — the only output is one
review JSON.

**Leading word: trace.** Every scoped operation ends in one trace covering
input, output, transport, side effects, publication, invalidation, failure,
and final consumer — recorded in the trace manifest, backed by evidence IDs
from the audit, and checked by the harness before the review is accepted.

## 0. Invariants (never violated)

- No source/Contract/Survey/Audit/issue edits; output is one review file.
- Claims are `inferred`/`unresolved` only. Observed facts come only from the
  audit; never manufacture observed-static/runtime evidence.
- Architecture rules live only in the Contract (reached through the audit).
  This skill adds process, never policy; it never re-evaluates rules.

## 1. Resolve scope

Load the validated audit first — never review unvalidated input:

```bash
python "$SKILL_DIR/scripts/review_harness.py" audit --fixture golden_126_ocr_rebuild \
  --out /tmp/golden_126_audit.json
# or: --contract <path> --survey <path> ; or: --audit <saved-audit.json>
```

The command refuses invalid input (exit 1, `REFUSED`). Its output fixes the
review's bindings: `audit_digest`, `contract_digest`, `survey_digest`,
`reconciler_version`, plus `scope` (operations to trace), `must_adjudicate`
(findings that demand an adjudication), and `evidence_pool`. `--out` saves
the validated audit JSON that step 4's emit validates against.

**Completion:** scope written down. Default = the audit's full scope
(full-survey branch); narrow only when the user named specific operations
(`references/branches.md`).

## 2. Investigate high-risk and unresolved edges

Every finding in `must_adjudicate` (deterministic `violated`/`unresolved`)
gets exactly one adjudication from the five kinds in
`references/adjudication-taxonomy.md`. Legwork for the judgment: LSP,
codebase-memory, and focused source reads on the evidence files named in the
audit (paths are repo-relative); never guess from the finding message alone.

For edges where evidence is missing, adjudicate `needs_evidence` with the
precise evidence IDs or questions required — do not stop at the first
plausible finding.

**Completion:** every `must_adjudicate` finding has an adjudication or the
emission fails.

## 3. Reconcile the trace

Fill the trace manifest: one entry per scoped operation, all eight stages
(`input`, `output`, `transport`, `side_effects`, `publication`,
`invalidation`, `failure`, `final_consumer`). A stage carries evidence IDs
from `evidence_pool` or a one-line note explaining why the stage has no
evidence. No stage may be silently skipped. Branch shapes are in
`references/branches.md`.

**Completion:** every scoped operation has all eight stages, no empty stage.

## 4. Emit the overlay

Assemble the `ArchitectureReview` JSON with `reviewer_type`, `run_metadata`
(model/session identity and created time), the four bindings from step 1,
adjudications, semantic findings (`inferred`/`unresolved` only), evidence
requests, and rationale. Then validate:

```bash
python "$SKILL_DIR/scripts/review_harness.py" emit \
  --audit <audit.json> --review <draft.json> --trace <manifest.json> \
  --fixture golden_126_ocr_rebuild --out <review.json>
```

`--fill-digests` copies the four bindings from the audit before validation.
The harness rejects stale digests, a mismatched reconciler version,
observed-static claims, fabricated finding IDs, missing adjudications, and
incomplete traces. A `REFUSED`/`PROBLEMS` result means rework — never bypass.

**Completion:** emit prints `OK` and writes the review file.

## Completion checklist

- [ ] audit loaded and validated (REFUSED on invalid input → stop, report)
- [ ] every scoped operation has one trace with all eight stages
- [ ] every `must_adjudicate` finding adjudicated (or `needs_evidence`)
- [ ] every claim labeled `inferred` or `unresolved`
- [ ] review bound to exact digests + reconciler version
- [ ] emit prints `OK`; review file written

## References (read on demand)

- `references/adjudication-taxonomy.md` — the five adjudication kinds,
  epistemic rules, severity mapping
- `references/branches.md` — full-survey / focused-signal / changed-interface
- `references/fixtures.md` — Slice A fixture inventory and golden semantics
