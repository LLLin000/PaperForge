# Artifact Materialization State Contract

**Date:** 2026-08-15
**Status:** Contract (the SINGLE per-paper state authority for OCR → retrieval → vector → serving)
**Origin:** 2026-08-14 production prune incident + post-recovery audit (restored vault had 682/818 corrupt OCR files, 0 vectors, stale DB). Review by owner 2026-08-15: do NOT keep adding parallel states to `probe_ocr` / per-paper vector probe — converge on ONE artifact-lineage decision tree.
**Supersedes:** ad-hoc per-probe status reasoning in `paperforge/lineage.py`, `paperforge/reconcile.py`.

---

## 1. Motivation

Two independent probes (`probe_ocr`, per-paper vector probe) accumulated
parallel, sometimes contradicting status vocabularies:

- `blocks_invalid` folded four distinct phenomena (unreadable / malformed /
  partial / not-a-file) into one state and routed all of them to a remote
  `ocr.run`.
- `DB has body_units` was informally treated as "retrieval current", but
  materialization ≠ trust ≠ serving.
- `vector_identity_version` (a GLOBAL substrate version) was used as
  per-paper "was embedded before" evidence.
- candidate (`effective_vector_db`) was treated as truth even though the
  retrieval gateway serves the LIVE db.

The contract fixes ONE ordering and lets `reconcile` find the FIRST broken
frontier — no new parallel state machines.

## 2. Core Principles

1. **Layered DAG, fixed order.** Every per-paper state is the result of
   walking one chain; a lower layer can never be "current" while an upper
   layer's inputs are broken.
2. **Each layer answers exactly three questions:**
   - *Facts* — what exists?
   - *Integrity* — is it valid/consistent (not merely present)?
   - *Identity* — is it what we expect (provenance/hash match)?
3. **`reconcile` emits the minimal action for the FIRST broken frontier.**
   Never let "search still returns something" prove an upstream layer is
   current.
4. **Filesystem truth ≠ DB truth ≠ serving truth.** They are separate
   carriers, reported separately.
5. **Write-boundary validation beats probe-time scanning.** Corruption is
   refused at birth (vector finite/dimension checks on ingest), not
   hunted per-probe over tens of thousands of rows.

## 3. The Contract Tree

```
Zotero / canonical index
│
├─ paper 不存在
│    └─ 其他 carrier 还有数据
│         → residual → library.prune
│
└─ paper 存在
     │
     ▼
[0] Canonical source identity
     ├─ 无 PDF                        → blocked.no_pdf → user action
     ├─ PDF 不可读                    → blocked.source_unreadable → user action
     └─ PDF 有效
          ▼
[1] OCR lifecycle / provenance (meta.json)
     ├─ meta 不存在
     │    ├─ raw artifacts 也不存在   → not_started → ocr.run
     │    └─ raw artifacts 存在       → legacy_or_untrusted → provenance validation
     ├─ pending / none                → not_started → ocr.run
     ├─ queued/running/processing
     │    ├─ zombie (past timeout)    → interrupted → ocr.run
     │    └─ alive                    → running → wait
     ├─ retryable/fatal/legacy failed → failed → ocr.run
     ├─ nopdf / blocked               → blocked → user action
     └─ done*
          ▼
[2] OCR ownership / source provenance
     ├─ meta.zotero_key != dir/canonical key            → source_misbound
     ├─ recorded PDF fingerprint != canonical PDF fingerprint → source_changed
     ├─ source_pdf points to disallowed location        → path_untrusted
     └─ match                                           → source_current
          ▼
[3] RAW OCR truth — canonical/blocks.raw.jsonl + provider result
     ├─ missing        → raw_missing    → ocr.run
     ├─ empty          → raw_empty      → ocr.run
     ├─ unreadable     → raw_unreadable → ocr.run
     ├─ malformed/partial → raw_corrupt → ocr.run
     └─ valid
          ▼
[4] Derived OCR artifacts — blocks.structured.jsonl
     ├─ missing / empty / unreadable / invalid JSONL / partial JSONL / not-a-file
     │    → derived_invalid → ocr.rebuild_derived   ← NOT ocr.run when raw is valid
     ▼
     structure-tree.json
     ├─ missing / empty / invalid            → ocr.rebuild_derived
     ├─ node/block refs inconsistent with blocks → tree_inconsistent → ocr.rebuild_derived
     ▼
     role-index.json
     ├─ missing / invalid / inconsistent     → ocr.rebuild_derived
          ▼
[5] OCR publication identity
     ├─ result-hash.pending
     │    ├─ recent → publishing → wait
     │    └─ stale  → interrupted_publish → ocr.rebuild_derived
     ├─ result-hash.txt missing             → publish_metadata_missing → local repair / rebuild_derived
     │                                       (NOT silent current — see §5.3)
     ├─ stored hash != recomputed hash      → derived_stale → ocr.rebuild_derived
     └─ match                               → OCR CURRENT
          ▼
[6] Retrieval materialization — manifest + body_units + object_units + FTS
     ├─ manifest missing                          → retrieval_missing → memory.build
     ├─ manifest OCR hash != OCR current          → retrieval_stale  → memory.build
     ├─ retrieval policy changed                  → retrieval_stale  → memory.build
     ├─ body/object count != manifest count       → retrieval_partial → memory.build
     ├─ body/object hash != manifest hash         → retrieval_corrupt → memory.build
     └─ identity match                            → RETRIEVAL MATERIALIZED
          ▼
[7] Global vector substrate
     ├─ vec schema/dimension incompatible
     ├─ model changed / endpoint changed
     ├─ legacy identity with published rows
     ├─ globally corrupt layout
     │    → embed.build(all, shadow)
     └─ compatible
          ▼
[8] Per-paper vector materialization
     ├─ 无 vector rows
     │    ├─ lineage 有该 paper 的 vector row → previously_published_but_missing → embed.resume(paper)
     │    └─ 无 lineage                        → never_materialized → embed.resume(paper)
     ├─ duplicate unit_id                        → vector_duplicate → delete paper vectors + re-embed
     ├─ expected unit count != actual count      → vector_partial → embed.resume(paper)
     ├─ body/object units hash mismatch          → vector_stale → embed.resume(paper)
     ├─ NaN / Inf (write gate missed)            → vector_corrupt → delete paper vectors + re-embed
     ├─ lineage retrieval identity mismatch      → vector_stale → embed.resume(paper)
     └─ identity + count + integrity match       → VECTOR MATERIALIZED
          ▼
[9] Publication / serving carrier
     ├─ candidate building              → build_progress (does NOT change live current)
     ├─ candidate complete, live old    → publish_pending → publish / resume
     ├─ candidate interrupted           → resume candidate
     └─ live identity == expected       → SERVING CURRENT ✅
```

**Build carrier (candidate) and serving carrier (live) are distinct.**
`materialization_candidate = current` while `serving = stale`,
`publication = pending` — never collapse into one "current".

## 4. Layer Contracts

| Layer | Facts | Integrity | Identity | Minimal action on first break |
|---|---|---|---|---|
| [0] source | PDF exists | PDF readable | canonical key match | user action |
| [1] lifecycle | meta status | — | — | ocr.run / wait / user |
| [2] provenance | zotero_key, source_pdf, pdf_fingerprint | — | fingerprint == canonical PDF | source repair / ocr.run |
| [3] raw | blocks.raw exists | valid JSONL | (provider result) | ocr.run |
| [4] derived | blocks.structured / tree / role-index | valid shape; tree↔blocks closure | — | ocr.rebuild_derived |
| [5] published | result-hash | hash == recomputed | — | rebuild_derived / local repair |
| [6] retrieval | manifest + units | count + hash match manifest | manifest OCR hash == OCR current | memory.build |
| [7] substrate | vec schema/layout | dimension/model/endpoint compatible | identity recorded | embed.build(all, shadow) |
| [8] per-paper vector | vec rows | count == expected; distinct unit_id; finite | retrieval identity + hash match | embed.resume(paper) / delete+re-embed |
| [9] serving | live DB | layout | live identity == expected | publish / resume |

## 5. Extreme-Case Decisions (owner-adjudicated)

| # | Scenario | Decision | Priority |
|---|---|---|---|
| 1 | OCR 文件串位 (paper A dir holds paper B content, valid-looking) | **P0**. No title/DOI heuristic — use `meta.zotero_key == canonical key` AND `meta.raw_version.pdf_fingerprint == fingerprint(canonical PDF)` | P0-B |
| 2 | tree 与 blocks 不一致 (stale/foreign tree) | **P1**. Validate node/block reference closure; no dangling block ids | P1-C |
| 3 | NaN/Inf vector | **P0 write gate**: `isfinite()` on provider output before `EncodedPayload` accept; failure = whole-paper transaction rollback. Legacy scan lives in `doctor --deep`, not per-probe | P0-C |
| 4 | vector chunk partial (count < expected) | **P1**. manifest already stores `body_unit_count`/`object_unit_count` — compare with `COUNT(vec_*_meta WHERE paper_id=?)`. All DB-metadata, cheap | P1-D |
| 5 | meta missing + artifacts exist | NOT current. Label `legacy_or_untrusted`; backfill only after provenance validation | P1-B |
| 6 | BOM / CRLF / GBK | CRLF fine; accept UTF-8 BOM (`utf-8-sig`); **NO GBK fallback** — canonical artifacts stay UTF-8 | P2 |
| 7 | directory where file expected | Explicit `is_file()`; state `artifact_not_file` | P1-A |
| 8 | permission vs corruption | **Do not merge.** Permission = user fix; corruption = rebuild | P1-A |
| 9 | oversized blocks | Streaming validation; suspicious-size guard, no tiny hard cap that hurts long papers | P2 |
| 10 | 0-line JSONL | Covered as `empty` | — |
| 11 | duplicate vectors | `COUNT(*) vs COUNT(DISTINCT unit_id)`; eventual uniqueness invariant | P1-D |
| 12 | mtime anomalies | mtime is NEVER freshness truth; only grace/cache. Identity = hashes only | P2 |
| 13 | symlink/junction | Probe reports path provenance; all destructive/write actions go through resolve + allowed-root safety (trash layer) | P2 |
| 14 | candidate exists, live stale | **P0 semantics**: candidate = build truth, live = serving truth; `serving = stale`, `publication = pending` | P0-D |

## 6. Current implementation status (2026-08-17)

The decision tree is the active contract, not a historical design sketch.
The following branches are implemented and are the only branches that may
drive RC decisions:

### Closed branches

- **Source and lifecycle:** missing/unreadable PDF, `nopdf`, `blocked`,
  pending, queued/running, zombie, retryable/fatal failure, and legacy
  failure remain distinct. `nopdf` is a valid URL-only terminal state;
  `pdf_missing` is a blocked source state.
- **Provenance:** the canonical key, canonical PDF fingerprint, and raw-block
  fingerprint are checked fail-closed. Unverifiable provenance is `unknown`,
  never `current`.
- **Raw and derived OCR:** raw-layer defects route to `ocr.run`; a healthy
  raw layer with broken derived artifacts routes to
  `ocr.rebuild_derived`. The raw validator distinguishes missing, empty,
  unreadable, malformed, partial, not-a-file, and permission states.
- **Publication identity:** `result-hash.pending`, missing publication
  metadata, stale hashes, and matching hashes are separate states. A matching
  artifact without its publication identity is not silently current.
- **Retrieval:** retrieval currency is decided from the manifest, units,
  hashes, policy, and OCR identity. `ocr_status == done` is not a retrieval
  authority.
- **Embedding eligibility:** build and resume share one selector. A paper is
  eligible only when retrieval is current and it has indexable content;
  no-content is a satisfied terminal outcome and is not an embed deficit.
- **Vector substrate and serving:** model/endpoint/dimension/identity and
  layout are global substrate facts. Candidate/build state is distinct from
  live/serving state; a candidate never makes stale live serving current.
- **Action ownership:** probe observes only. `reconcile` emits the minimal
  first-frontier intent. Preflight, confirmation, execution settlement, and
  post-action re-observation belong to the action runner.

### Deferred deep-audit items

These do not change the RC decision tree or justify product-source mutation:

1. in-range semantic rowid misbinding and full vector checksum auditing;
2. oversized-block suspicion policy and symlink/junction provenance review;
3. removal of the remaining EmbeddingService stdout relay before the
   post-RC Goal/Ensure kernel.

The third item is presentation-channel debt only: Action already calls the
embedding service directly, service code does not import `paperforge.commands`,
and structured execution results remain the truth surface.

## 7. Implementation priority

The priority list below records the contract's completed closure and the
remaining post-RC audit, rather than reopening already-closed materialization
work:

```
CLOSED  unified first-broken-frontier decision tree
CLOSED  OCR lifecycle, provenance, raw/derived validation, publication hash
CLOSED  retrieval identity and no-content terminal semantics
CLOSED  vector substrate identity and candidate/live serving split
CLOSED  shared embedding eligibility for build and resume
POST-RC  in-range rowid semantic binding / deep vector checksum audit
POST-RC  oversized suspicious blocks / symlink path provenance
POST-RC  structured EmbeddingService return/event sink (remove stdout relay)
```

No item in the POST-RC list requires re-OCR, retrieval rebuild, or re-embed
for existing users unless a future audit proves a materialization defect.
Validation-only edits to this contract are `none / none / none`.

## 8. Relationship to Existing Code

- `paperforge/lineage.py` — per-paper {ocr, retrieval, vector} states;
  will become the projection of this contract's first-broken-frontier.
- `paperforge/reconcile.py` — emits minimal intents per frontier layer
  (ocr.run / ocr.rebuild_derived / memory.build / embed.resume /
  embed.build / library.prune / publish).
- `paperforge/embedding/build_state.py` + `substrate.py` — [7] substrate
  and [9] serving carrier facts.
- `paperforge/worker/trash.py` — destructive actions safety layer
  (2026-08-14 incident).
- `paperforge/embedding/_chroma.py::delete_paper_vectors*` — vector
  delete for [8] corrupt/duplicate cases (rowid-verified, transactional).
- `paperforge/ocr_hash.py` — [5] publication identity authority.
- `paperforge/adapters/ocr_pdf_fingerprint*` — [2] provenance evidence.

## 9. Recovery Incident Context (2026-08-14)

The contract is written against a real production failure: a prune
`shutil.rmtree(Path(), ignore_errors=True)` deleted the vault root;
DiskGenius restoration brought back files where 682/818 OCR
`blocks.structured.jsonl` were random binary (data-block misalignment),
DB rolled back to a 2026-08-12 snapshot (0 vectors, no lineage table),
and `.venv` site-packages was partially corrupted. The contract's
fine-grained per-layer states are the toolset that makes such a state
reported honestly (OCR unreadable ≠ retrieval materialized ≠ serving
current) and repaired minimally (only the 37 papers with corrupt blocks
AND no DB units need re-OCR; 645 with DB units do not).

## 10. Decision procedure for an observed paper

This is the operational decision tree used by `probe` and `reconcile`.
Observation never mutates the vault. Execution is a separate, confirmed
action followed by a fresh probe.

```
observe paper + global substrate
│
├─ canonical paper absent, but any carrier remains
│    └─ residual → library.prune (destructive confirmation required)
│
├─ source missing/unreadable or URL-only nopdf
│    └─ blocked/no-pdf → user action; emit no OCR or embed intent
│
├─ OCR lifecycle/provenance/raw is not current
│    ├─ pending/zombie/failed/raw defect
│    │    └─ ocr.run
│    ├─ raw current, derived/tree/role-index defect
│    │    └─ ocr.rebuild_derived
│    └─ publication identity defect
│         └─ local repair or ocr.rebuild_derived
│
├─ retrieval is not current
│    └─ memory.build for the successful OCR scope
│
├─ retrieval current but global vector substrate is incompatible
│    └─ embed.build(all, shadow) → verify candidate → publish live
│
├─ retrieval current and indexable content exists
│    ├─ paper vectors missing/partial/stale
│    │    └─ embed.resume(paper)
│    └─ paper vectors current
│         └─ inspect candidate/live publication state
│
├─ retrieval current but no indexable content exists
│    └─ vector_no_content → satisfied terminal; no embed action
│
└─ all identities and carriers current
     └─ serving current; no action
```

For every emitted intent the required control path is:

```
probe observation
  → reconcile first frontier
  → action preflight (availability × applicability)
  → confirmation gate
  → handler/service execution
  → PFResult settlement
  → materialization commit
  → fresh probe
  → UI/read projection
```

The old-user impact of this document-only closure is zero: no
re-OCR/rebuild/embed is required, no production vault is touched, and the
existing materialization authority is unchanged.
