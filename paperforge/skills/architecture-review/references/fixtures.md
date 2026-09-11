# Slice A Fixtures

All fixtures live in `paperforge/architecture_audit/fixtures/*.json` as
`{"contract": {...}, "survey": {...}}` payloads and load through the harness:

```bash
python "$SKILL_DIR/scripts/review_harness.py" audit --fixture <name>
```

Load order: the harness validates Contract and Survey, runs the #131
reconciler, and validates the resulting DeterministicAudit — the review never
sees unvalidated input.

## Synthetic fixtures (one rule/edge each)

| Fixture | Edge | Expected deterministic outcome |
|---------|------|-------------------------------|
| `synthetic_query_side_effect` | query performs business mutation | `violated` (blocking) |
| `synthetic_unmatched_signal` | signal without code consumer | `violated` (blocking) |
| `synthetic_ui_canonical_write` | UI writes canonical state | `violated` (blocking) |
| `synthetic_implicit_remote_followup` | remote follow-up without intent | `violated` (blocking) |
| `synthetic_publication_bypass` | writer bypasses publication protocol | `violated` (blocking) |
| `synthetic_planned_gap` | planned rule not yet effective | `planned_gap` (informational) |
| `synthetic_intentional_exception` | violation covered by declared exception | `exception_applied` (blocking) |
| `synthetic_partial_coverage` | required extractor incomplete | assessment `incomplete`, gate not eligible |

## Golden fixtures (real observed evidence, pinned revision)

Recorded revision: `1f02281b`; survey facts carry `observed_static` evidence
with real source digests. Issue text supplies declared intent only — never
treat an issue description as observed evidence.

| Fixture | Trace models | Deterministic findings |
|---------|--------------|------------------------|
| `golden_126_ocr_rebuild` | OCR derived rebuild → publication authority; planned `remote_intent.embed_resume`, `publication.hash_marker`, `signal.rebuild_progress` | `publication.authority` **unresolved (blocking)** — the finding that must be adjudicated |
| `golden_127_sync_embed` | sync → embed build with planned remote follow-up | planned gap only; `query.side_effect_free` satisfied |
| `golden_129_display_restore` | display restore must not imply structural rollback | planned gap only |

## Evidence index

The audit packet indexes every survey evidence item by fact kind, owning
operation, subject, and admissible trace stages. A trace may cite only a
candidate ID listed for the same operation and stage. Evidence without an
operation owner is not silently promoted to a global pool; the model emits
`needs_evidence` until a deterministic edge or a bounded source read connects
it.
