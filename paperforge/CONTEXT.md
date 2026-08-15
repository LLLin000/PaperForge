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
