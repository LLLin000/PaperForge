# Adjudication Taxonomy

The single authority for review-layer semantics. Deterministic rule status
(`satisfied | violated | planned_gap | exception_applied | unresolved |
not_evaluated`) comes only from the DeterministicAudit — this skill never
re-evaluates rules.

## Adjudication kinds (exactly one per finding)

| Kind | Use when | Resulting review state |
|------|----------|------------------------|
| `confirmed` | The deterministic finding is correct and remains a real risk | Finding stands, rationale records the traced confirmation |
| `false_positive` | The finding is wrong; the evidence chain shows the rule fired on a non-issue | Finding is explained as spurious; deterministic finding is untouched |
| `contract_drift` | The Contract no longer matches implemented intent (or vice versa); the rule or its subject is the wrong target | Contract change or rule retirement recommended — never performed here |
| `intentional_exception_recommended` | The violation is deliberate and safe, but no exception is declared in the Contract yet | Recommend a declared exception; the deterministic `exception_applied` state is Contract-owned |
| `needs_evidence` | The edge cannot be resolved with current evidence | Record the precise evidence IDs or questions required |

`confirmed` is never written into the DeterministicAudit. Review can only
recommend an exception; it can never apply one.

## Epistemic status

| Status | Who may claim it | Allowed in Review |
|--------|------------------|-------------------|
| `declared` | Contract | no |
| `observed_static` | Survey collectors | no |
| `observed_runtime` | Survey runtime collectors | no |
| `inferred` | Review (judgment on evidence) | yes |
| `unresolved` | Review (no basis to judge) | yes |

Every adjudication and semantic finding carries `inferred` or `unresolved`.
Confidence (`exact | high | medium | low`) is separate from epistemic status.

## Severity mapping

- Deterministic findings carry severity from enforcement: `blocking`,
  `advisory`, `informational` (planned gaps).
- `must_adjudicate` = `violated` or `unresolved` findings (blocking/advisory).
  Planned gaps and `exception_applied` are declarative — no adjudication
  required.
- Review attention follows severity: blocking first, then advisory, then the
  remaining scope.

## Evidence requests

`EvidenceRequest {request_id, subject, question}` — for edges that need
collector or runtime evidence (Slice C material). Precise questions beat
vague ones; each request names the subject it concerns.
