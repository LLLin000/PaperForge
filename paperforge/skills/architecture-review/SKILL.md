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
skill_version: 2026-09-11.2
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

## 1. Resolve the audit and build the packet

Load the validated audit first — never review unvalidated input:

```bash
python "$SKILL_DIR/scripts/review_harness.py" audit --fixture golden_126_ocr_rebuild \
  --out /tmp/golden_126_audit.json
```

Then build the deterministic packet. Daily development review defaults to
`delta`; pass the changed files explicitly:

```bash
python "$SKILL_DIR/scripts/review_harness.py" plan \
  --audit /tmp/golden_126_audit.json \
  --fixture golden_126_ocr_rebuild \
  --mode delta \
  --changed-file paperforge/worker/status.py \
  --out /tmp/review-packet.json
```

Use `gate` for deterministic compliance only, `delta` for changed-code review,
`focused` for named operations, `deep-trace` for unresolved/high-risk paths,
and `full-release` for certification. The packet is the review scope. Its
`scope` is derived from a Contract whose digest matches the audit, while its
evidence candidates are derived from a Survey whose digest matches the audit;
missing or mismatched context is a refusal.

**Completion:** packet bindings, affected operations, required adjudications,
operation/stage evidence candidates, exact source reads, and stop conditions
are written down.

## 2. Investigate only unresolved edges

Every finding in `must_adjudicate` (deterministic `violated`/`unresolved`)
gets exactly one adjudication from the five kinds in
`references/adjudication-taxonomy.md`. The packet's candidate evidence is
already operation- and stage-scoped. Use it before searching.

Read only packet-listed file/symbol candidates. If evidence is insufficient,
expand callers or callees by one hop, at most twice. After two hops, emit
`needs_evidence` with a precise question; do not continue repo-wide search
unless the packet says the subject or wrapper is unbound.

**Completion:** every `must_adjudicate` finding has an adjudication or the
emission fails.

## 3. Reconcile the typed trace

Fill one trace entry per packet `affected_operation`, with all eight stages:
`input`, `output`, `transport`, `side_effects`, `publication`, `invalidation`,
`failure`, and `final_consumer`. Every stage is exactly one typed object:

```json
{"status": "observed", "evidence_ids": ["evidence:..."]}
{"status": "not_applicable", "reason_code": "no_publication"}
{"status": "needs_evidence", "question": "Which path publishes this state?"}
```

`observed` may cite only the packet's candidate IDs for that operation/stage.
`not_applicable` requires a registered reason code. `needs_evidence` requires
a question. Free-text fillers and a global evidence pool are rejected.

**Completion:** every affected operation has all eight typed stages, with no
empty stage and no cross-operation evidence.

## 4. Emit the overlay

Assemble the `ArchitectureReview` JSON with `reviewer_type`, `run_metadata`
(model/session identity and created time), the four bindings from the audit,
adjudications, semantic findings (`inferred`/`unresolved` only), evidence
requests, and rationale. Emit must consume the exact deterministic packet that
defined the trace scope:

```bash
python "$SKILL_DIR/scripts/review_harness.py" emit \
  --audit /tmp/golden_126_audit.json \
  --plan /tmp/review-packet.json \
  --fixture golden_126_ocr_rebuild \
  --review <draft.json> \
  --trace <typed-trace.json> \
  --out <review.json>
```

The harness re-derives the packet selector against the digest-bound
Contract/Survey and rejects changed mode, selector, bindings, scope, affected
operations, rule IDs, or finding IDs. `gate` packets cannot produce a model
overlay; there is no independent emit-time operations narrowing.

It also rejects stale digests, a mismatched reconciler version, observed static
claims, fabricated finding IDs, missing adjudications, missing bound
Contract/Survey context, cross-operation/stage evidence, and incomplete typed
traces. `REFUSED`/`PROBLEMS` means rework — never bypass.

**Completion:** emit prints `OK` and writes the review file.

## 5. Benchmark v1 versus v2

Run the executable fixture corpus before comparing model runs:

```bash
python "$SKILL_DIR/scripts/skill_benchmark.py"
```

The corpus covers all 11 deterministic fixtures plus issue-grounded historical
cases #220, #229, and #231. Historical cases without replay fixtures are
reported as `not_run`, never scored as passes. Supply recorded answer artifacts
only when real Skill executions exist:

```bash
python "$SKILL_DIR/scripts/skill_benchmark.py" \
  --answers-v1 /path/to/v1-answers.json \
  --answers-v2 /path/to/v2-answers.json
```

The evaluator reports only supplied validity, evidence-scope, typed-trace,
tool-use, token, and timing fields. Missing fields stay missing; no A/B result
is inferred from the deterministic corpus.

## Completion checklist

- [ ] audit loaded and validated (REFUSED on invalid input → stop, report)
- [ ] deterministic packet built; daily review uses `delta`
- [ ] every affected operation has one typed trace with all eight stages
- [ ] every `must_adjudicate` finding adjudicated (or `needs_evidence`)
- [ ] every claim labeled `inferred` or `unresolved`
- [ ] review bound to exact digests + reconciler version
- [ ] emit prints `OK`; review file written

## References (read on demand)

- `references/adjudication-taxonomy.md` — the five adjudication kinds,
  epistemic rules, severity mapping
- `references/branches.md` — Gate, Delta, Focused, Deep-trace, and Full-release
- `references/fixtures.md` — Slice A fixture inventory and golden semantics
- `references/benchmark-cases.json` — executable and historical v1/v2 corpus
