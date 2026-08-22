# Materialization

Per-paper truth about the OCR → retrieval → vector → serving pipeline: what
exists at each layer, whether it is trustworthy, and what the minimal repair
is. Governed by the Artifact Materialization State Contract
(docs/research/2026-08-15-artifact-materialization-state-contract.md).

## Language

### Layers

**Raw artifact**:
The OCR provider's initial structured output (`canonical/blocks.raw.jsonl`).
The deepest materialization frontier — if it is broken, re-running OCR
(`ocr.run`) is the only fix.
_Avoid_: blocks, source blocks

**Derived artifact**:
Everything materialized from raw: `blocks.structured.jsonl`, structure-tree,
role-index. Broken here with healthy raw means `ocr.rebuild_derived`, never a
remote OCR call.
_Avoid_: processed blocks, structure files

**Published identity**:
The `result-hash.txt` contract that pins which OCR output was published.
Missing or mismatched means the layer is not current even if artifacts exist.
_Avoid_: hash file, snapshot

**Retrieval materialization**:
The DB carrier of searchable units: manifest + body_units + object_units.
Present but untrusted (hash/count mismatch) is `stale`, never `current`.

**Vector materialization**:
The DB carrier of embeddings: vec meta + rows. Per-paper completeness and
value integrity (finite, correct dimension) are its own facts.

**Build carrier**:
The candidate DB an in-progress build writes to. Its `current` state says
nothing about what users can search.
_Avoid_: candidate, effective db

**Serving carrier**:
The live DB the retrieval gateway actually reads. Serving readiness is judged
here and only here.
_Avoid_: live, effective db

### States (top-level, layer-qualified)

**current**:
A layer's materialization is complete AND its identity/hash matches. Always
qualified by layer (`ocr.current`, `serving.current`) — one layer being
current never implies another is.
_Avoid_: bare "current"

**materialized**:
Present and internally consistent, but not necessarily trusted against the
upstream identity (details-level distinction from `current`).

**stale**:
Identity or hash no longer matches the upstream layer.

**missing**:
No materialization at all in this layer.

**incomplete**:
Some material exists but the layer's chain is broken (e.g. tree missing while
blocks exist).

**unknown**:
The layer cannot be judged (probe failure, missing provenance).

**failed / blocked / not_started / running / queued**:
Lifecycle states of the OCR/memory/embed operations themselves.

### Artifact file conditions (suffix set)

**missing**: does not exist.
**empty**: exists but zero bytes / zero rows.
**unreadable**: exists but cannot be decoded (random bytes, e.g. restore
corruption).
**invalid**: decodes but fails syntax/structure checks.
**partial**: some lines/rows valid, then broken (interrupted write).
**not_file**: a directory where a file is expected.
**permission**: exists but unreadable due to access control.
_Avoid_: corrupt (ambiguous — use unreadable/invalid for files,
invalid_value for data)

**invalid_value**:
Data is present but not usable (NaN/Inf embedding, wrong dimension).

### Repair actions

**ocr.run**: re-run remote OCR — only when raw is broken or absent.
**ocr.rebuild_derived**: re-materialize derived artifacts from healthy raw.
**memory.build**: rebuild retrieval materialization (manifest + units).
**memory.rebuild**: full-text index realignment from the canonical library.
**embed.resume**: incrementally embed missing/stale per-paper vectors.
**embed.build**: (re)build the vector substrate (global, shadow).
**library.prune**: remove all carriers of a residual (Zotero-absent) paper.

### Render reconciliation vocabulary

**Canonical object**:
An existing figure or table object in the canonical inventory. Reconciliation
may reference it, but may not create or rewrite it.

**Supported formal figure set**:
Figure labels supported by caption text and optional PDF-media evidence. This
is a high-evidence candidate set, not canonical truth.

**Render repair**:
A render-layer action that materializes an already-existing canonical object.
It may write render images, render markdown, provenance, and consistency
reports; it must not change OCR truth or inventory.

**Inventory proposal**:
A constrained caption/asset candidate for which no canonical object exists.
It is report-only and never creates a figure or table object.

**Reservation artifact**:
A temporary cross-page or unresolved object placeholder. It is not a formal
figure and must not be counted as one without independent evidence.

**Blocked**:
Evidence is contradictory, ambiguous, or missing. No render repair is
authorized.

**Visual correctness**:
Whether the pixels semantically show the captioned object. Structural
reconciliation can test assignment and provenance, but does not prove visual
meaning without PDF or human visual verification.

**Exact repair candidate**:
A canonical object whose current render output is missing or inconsistent and
whose canonical asset evidence is unique. It is a plan candidate, not proof
that execution may start.

**Repair-ready**:
An exact repair candidate whose live preconditions still match and whose
materialization input/result is observable. A candidate without fresh
provenance remains `needs_fresh_provenance`.
**Canonical-to-render gap**:
An existing canonical object has a unique ordered asset reference, but its
render image or markdown image link is absent or invalid. This is a render-only
repair candidate; it does not mean the figure's visual semantics are proven.

**Canonical-missing figure candidate**:
Caption, source-image, or PDF-media evidence suggests a figure, but no
canonical inventory object exists. This is an inventory proposal only: no
canonical ID, ownership claim, or render artifact may be created.

**Repair dry-run**:
A read-only precondition check. It never writes images, markdown, inventory,
or canonical metadata. It may verify against a live snapshot or a persisted
audit snapshot; only the live mode can support an execution gate.

**Bounded repair**:
A repair accepted because it has clear user benefit, preserves canonical
identity, and passes render-layer preconditions and postconditions. It does
not claim perfect semantic or visual truth.

**Structurally unique proposal**:
Within a bounded slot, after kind, namespace, ownership, reservation,
page-range, and existing-group filters, exactly one visual candidate remains.
It is still an inventory proposal, never canonical truth.

**Candidate enumeration**:
The reconciliation record of raw candidates, rejected candidates with reasons,
and surviving candidates. “Unique” is valid only after this enumeration.

**Paper-level candidate exclusivity**:
Within one paper, a surviving visual candidate may be claimed by at most one
proposal. A group claimed by multiple proposals is a conflict: every claiming
proposal becomes blocked until ownership evidence resolves the conflict.

**Visual claim identity**:
A proposal claims not only a group ID but the group's member block references.
Two proposals conflict when they claim the same group or overlapping block
references, even if their top-level candidate IDs differ.

**Exact evidence**:
Evidence that the existing canonical object and its ordered asset references
are preserved exactly for a render-only operation. It does not mean that the
source PDF's visual meaning has been proven with absolute certainty.

**Repair policy**:
Prefer a measurable, low-risk improvement over a perfect-but-unavailable
decision. Apply only when a wrong repair is less likely and less damaging than
leaving the known render defect; otherwise produce a proposal or block.
