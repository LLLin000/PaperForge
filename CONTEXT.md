# OCR Quality Report — Domain Model

> Established: 2026-07-04
> Status: Draft (Layer 2 design session)

## Core concepts

### Quality Signal (raw)
A deterministic, pipeline-internal measurement.  The pipeline can prove it is correct.
*Example:* `rendered_text_gap_count = 12`, `degraded_mode_active = true`, `figure_asset_count = 8`.

### Quality Indicator (normalized)
A stable, opinion-free normalization of raw signals into a status (`green | yellow | red | unknown`) plus supporting evidence.
*Output of:* `build_quality_indicators()`
*Not:* a score or composite.  Each indicator stands alone.

### User Readiness
A **policy-based internal estimate** of whether the OCR result supports a use case. It is not ground truth and does not by itself create a user-visible problem or maintenance item.

```python
user_readiness = {
    "status": "green|yellow|red",
    "score": 0.0-1.0,
    "policy_version": "ocr_readiness_policy_v1",
    "basis": "policy_estimate",
    "primary_reasons": [...],
}
```

### Usable OCR Result
An OCR result that supports the user's intended reading or retrieval task despite ordinary recognition and layout imperfections.

### User-visible OCR Failure
An OCR outcome that prevents reading or retrieval and has a concrete recovery action likely to improve or restore the result.
*Not:* a low confidence score, minor defect, or internal quality warning with no useful action.

### Recommended Use
A per-use-case assessment, each with its own gate.
- `reading` — rendered text integrity + body flow
- `qa` — text integrity + body/reference + (metadata soft)
- `figure_table_reasoning` — figure/table evidence + match coverage; `not_applicable` when no figure/table evidence
- `section_chunking` — heading integrity + body/reference boundary + layout confidence

Each outputs `status` (ok | caution | not_recommended | not_applicable) plus the `gates` and `reasons` that produced it.

### Readiness Policy
The opinion layer, externalised from pipeline code.  A YAML/JSON configuration containing:
- Weights for the five quality dimensions
- Hard-red override rules
- Use-case gate definitions

Changes to policy do not require re-running OCR — only re-evaluating the quality indicators.

### Human Validation
An explicit user or developer mark on a specific OCR result.
- Must be bound to `result_hash` / `fulltext_hash` to survive re-runs.
- Stored as a sidecar file, not in the pipeline output.
- States: `unreviewed | confirmed | disputed`
- Backed by a `ocr_quality_feedback.json` schema.

### Human Validation v. Implicit Signal
- **Explicit:** user clicks "looks good / has issues / bad OCR"
- **Implicit:** user opens fulltext and does not report an error (very weak signal)
Only explicit marks carry weight in the validation loop.

### Source Corpus
The authoritative research content from which retrieval data is derived: paper notes, OCR outputs, structured blocks, metadata, and user-authored annotations. Source Corpus data must survive retrieval-layer repair or rebuild.

### Retrieval Experience
The user-facing capability for finding either a known paper or knowledge inside papers. It includes metadata lookup, semantic/deep retrieval, and the build/status controls required to keep those paths usable.

### Retrieval Artifact
Regenerable data derived from the Source Corpus for search: FTS indexes, embeddings, vector tables, and their companion metadata. Retrieval Artifacts may be discarded and rebuilt; they are not preservation targets or sources of truth.

### Capability State
The current usability of one operational module. Foundation, Library, OCR, Smart Retrieval, and Agent Integration each report their own state; Maintenance and Help are not modules.

### Activity State
Work currently being performed by a module, such as installing, rebuilding, or stopping. Activity is independent of capability: a module may remain usable while maintenance runs.

### Attention State
Whether a module has a concrete user-visible problem and a backend-authorized action. Internal quality warnings and non-actionable imperfections stay quiet.

### Maintenance Inbox
A derived view of unresolved user-visible problems that have concrete recovery actions. It excludes internal quality signals, non-actionable imperfections, and completed work.

### Managed Runtime
The verified, versioned execution component inside Foundation. Runtime identity and recovery are advanced diagnostics; normal user language refers to the Foundation or PaperForge environment.

## Architecture layers

```
raw blocks ──→ build_ocr_health()
                  ↓ raw diagnostics (old health fields)
               build_quality_indicators()
                  ↓ quality_indicators (stable, normalized)
               evaluate_readiness(policy)
                  ↓ user_readiness + recommended_use
               ──→ human feedback sidecar (feedback.json)
```

## Dimension weights (default policy)

| Dimension | Weight | Purpose |
|-----------|--------|---------|
| rendered_text_integrity | 35% | Main gate — is the body text readable? |
| body_reference_structure | 25% | Can we trust body flow, ref boundary? |
| figure_table_integrity | 20% | Are figures/tables usable? |
| metadata_frontmatter_quality | 10% | Title/author/DOI availability |
| confidence_and_fallbacks | 10% | Was degraded mode or heavy fallback used? |

## Hard-red rules (override composite scoring)

Any of these triggers a direct `red`:
- `rendered_text_gap_count > 10`
- `fulltext_min_chars < 2000`
- reference zone clearly pollutes body text
- critical pipeline artifact missing

## Files

- `paperforge/worker/ocr_quality.py` — `build_quality_indicators()`, `evaluate_readiness()`
- `c:/users/lin/.paperforge/policies/ocr_readiness_v1.yaml` — default readiness policy (or repo path)
- `<paper_dir>/ocr_quality_feedback.json` — human validation sidecar
