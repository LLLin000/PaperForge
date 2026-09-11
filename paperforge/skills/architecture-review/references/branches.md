# Review modes

The deterministic packet decides the scope before the model reads source.
Every mode still adjudicates every `must_adjudicate` finding; the mode narrows
the trace, not high-risk coverage.

## 1. Gate

- **When:** CI only needs deterministic compliance.
- **Scope:** no model trace; consume the audit/gate result.
- **Model work:** none unless the gate is ineligible or violated.

## 2. Delta

- **When:** default development review after a code change.
- **Scope:** operations whose candidate evidence intersects the supplied
  `--changed-file` paths.
- **Trace:** complete typed trace for affected operations only.
- **Stop:** no deterministically affected operation means stop; do not promote
  the run to a full survey.

## 3. Focused

- **When:** the user names one operation or signal chain.
- **Scope:** the named operation(s), intersected with Contract operations.
- **Trace:** complete typed trace for the selected operation(s).
- **Outcome to watch:** an unbound subject becomes `needs_evidence`, not a
  repo-wide search.

## 4. Deep-trace

- **When:** deterministic findings or unresolved edges need owner review.
- **Scope:** all Contract operations unless explicit operations narrow it.
- **Trace:** deepen only packet-listed unresolved stages, then expand callers or
  callees by at most two hops.
- **Outcome to watch:** emit `needs_evidence` with a precise question when the
  edge remains unbound.

## 5. Full-release

- **When:** release certification explicitly requires a complete architecture
  review.
- **Scope:** every Contract operation.
- **Trace:** one complete typed eight-stage trace per operation.
- **Evidence:** only operation/stage candidate IDs from the packet are
  admissible.

## CLI contract

- `gate` has no affected operations and rejects `--operations`/`--changed-file`.
- `delta` derives affected operations from `--changed-file` only.
- `focused` requires `--operations`, rejects `--changed-file`, and refuses unknown operations.
- `deep-trace` takes named operations or all Contract operations; it rejects `--changed-file`.
- `full-release` covers every Contract operation and rejects all narrowing.

## Choosing a mode

Use `delta` by default. Use `focused` when the request names a bounded
operation/signal, `deep-trace` for unresolved or blocking findings, and
`full-release` only for a release gate. `gate` is deterministic compliance,
not a substitute for a model review.
