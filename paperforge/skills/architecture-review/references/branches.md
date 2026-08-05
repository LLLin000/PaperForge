# Branches

Three distinct review shapes, each a different trace scope. The primary
SKILL.md steps are the same for all; only scope resolution and trace depth
differ. All branches still adjudicate every `must_adjudicate` finding — the
branch narrows the trace, never the high-risk coverage.

## 1. Full-survey

- **When:** no narrowing request; review the whole audit.
- **Scope:** every operation in the audit's `scope` list.
- **Trace:** one full eight-stage trace per operation.
- **Fixture targets:** `golden_126_ocr_rebuild` (publication authority
  unresolved + planned gaps), `golden_127_sync_embed` (planned remote
  follow-up), `golden_129_display_restore` (planned canonical writer).

## 2. Focused-signal

- **When:** the user names one signal chain — producer, transport, consumer.
- **Scope:** the operation(s) touching that signal; e.g. `OCR_REBUILD_PROGRESS`
  (golden_126) or `EVENT_BUS_EMIT` (`synthetic_unmatched_signal`).
- **Trace:** deepen the signal stages (`transport`, `side_effects`,
  `final_consumer`); the other scoped operations still get complete traces.
- **Outcome to watch:** orphaned signals (no code consumer) are deterministic
  violations — adjudicate why the consumer is missing or why the rule is
  wrong (`false_positive` / `contract_drift`).

## 3. Changed-interface

- **When:** the user asks about an interface or authority change — publication
  authority identity, delegated executors, observers, writers.
- **Scope:** the affected publication unit / operation; e.g.
  `ocr_derived.generation` in `synthetic_publication_bypass` (writer bypassed
  the publication protocol) or golden_126's unresolved `publication.authority`.
- **Trace:** emphasize `side_effects` → `publication` → `invalidation` →
  `final_consumer`.
- **Outcome to watch:** authority identity mismatch between Contract and
  observed writer is a deterministic violation; adjudicate `confirmed` with
  the traced writer chain, or `contract_drift` if the Contract names the
  wrong authority.

## Deciding between branches

- Full-survey is the default; focused-signal for one signal; changed-interface
  for authority/interface questions. If the user request does not fit a
  branch, default to full-survey and note the deviation in `rationale`.
