# Unified artifact materialization state contract

The 2026-08-14 prune incident and the post-recovery audit (682/818 restored OCR
files were random binary, DB rolled back to an older snapshot with 0 vectors)
exposed that `probe_ocr` and the per-paper vector probe maintained parallel,
sometimes contradicting status vocabularies: `blocks_invalid` folded four
phenomena, "DB has body_units" was informally treated as retrieval current,
and candidate was treated as truth even though the gateway serves live.

We decided on ONE artifact-lineage decision tree as the per-paper state
authority: `raw → derived → published → retrieval → vector → serving`, each
layer answering facts / integrity / identity, and `reconcile` emitting the
minimal action for the FIRST broken frontier. The backend owns the single
source of truth; `probe lineage` is the unified output port; repair tooling is
explicit CLI (`repair scan`, `ocr run --keys-file`, `doctor --deep`); each
file stage's state is explicit (`missing/empty/unreadable/invalid/partial/
not_file/permission` + `invalid_value` for data). Frontend presentation is
out of scope for now.

Status: accepted
Considered: keep extending the two parallel probes (rejected — state drift is
the bug class we just lived through); a per-layer status explosion (rejected —
states cluster by repair action, phenomena live in details).
Consequences: `lineage.py` becomes a projection over `paperforge/materialization/`;
`effective_vector_db()` splits into build_carrier vs serving_carrier; reconcile
gains `report_only` output for "file corrupt but data materialized" (no
automatic remote OCR); vector write path validates length/dimension/finite at
ingest, not by probe scan.
