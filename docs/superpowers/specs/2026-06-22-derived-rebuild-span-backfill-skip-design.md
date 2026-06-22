# Derived Rebuild Span Backfill Skip Design

> Date: 2026-06-22
> Status: proposed
> Scope: allow derived rebuild to skip PDF span backfill when existing raw enrichment is still valid

## Goal

Reduce derived rebuild time by avoiding unconditional re-execution of `backfill_span_metadata_from_pdf()` when the stored raw blocks already contain sufficiently complete and still-valid PDF span enrichment.

This design applies only to rebuild-time reuse of existing raw enrichment.

It does not change:

- OCR parsing,
- role resolution,
- render rules,
- object extraction semantics,
- the shape of `span_metadata` itself.

## Why This Is Separate from the Low-Risk Perf Patch

This change is not just a local de-dup optimization.

It introduces a rebuild invalidation policy:

- when existing raw enrichment is trusted,
- when it must be recomputed,
- which metadata fields define validity,
- how version changes force re-execution.

That makes it broader and riskier than the `ocr_objects.py` PDF/page reuse slice. It therefore needs its own contract and tests.

## Current Problem

`run_derived_rebuild_for_keys()` currently does this on every rebuild when a source PDF exists:

```python
backfill_span_metadata_from_pdf(all_raw_blocks, source_pdf_path)
write_raw_blocks_jsonl(artifacts.blocks_raw, all_raw_blocks)
```

That means rebuild reopens the PDF, walks the raw blocks, and rewrites `blocks.raw.jsonl` even when the current raw blocks already contain usable:

- `span_metadata`,
- `_in_visual_container`,
- `_container_bbox`,
- `_container_text`.

This is expensive because PDF span backfill does per-block PDF extraction and per-page visual-container inspection.

## Non-Goals

This design does not:

- redesign the span extraction algorithm,
- change the contents or format of `span_metadata`,
- change object extraction,
- change rebuild command UX,
- introduce probabilistic cache eviction,
- skip backfill without explicit validity checks.

## Design Principle

Stored raw enrichment is reusable only when the algorithm version and source PDF identity both still match.

This is a validity problem, not a “did we already do this once?” problem.

## Required Validity Contract

Derived rebuild may skip span backfill only if all of the following are true:

1. `meta["span_backfill_version"] == CURRENT_SPAN_BACKFILL_VERSION`
2. `meta["span_pdf_fingerprint"] == current_pdf_fingerprint`
3. stored coverage is at or above a configured threshold
4. visual-container enrichment version also matches the current expected version

If any of those checks fails, rebuild must rerun PDF span backfill.

## Eligibility Rule

Coverage must not use all raw blocks as the denominator.

It must use only eligible text-like raw blocks.

Preferred eligibility rule:

- raw block has non-empty `text`,
- raw block has a valid `bbox`,
- raw block is text-like by label.

Acceptable first-pass label set:

- `text`
- `paragraph_title`
- `abstract`
- `reference_content`
- `figure_title`

Equivalent implementation is also acceptable if it uses an explicit helper such as `is_text_like_raw_block(block)` and keeps the same intent.

Coverage formula:

```text
span_backfill_coverage = blocks_with_span_metadata / eligible_text_like_blocks
```

This exists to avoid penalizing image-heavy or asset-heavy papers whose non-text raw blocks were never expected to carry PDF span metadata.

## Proposed Metadata Fields

Store the following in `meta.json` after a successful rebuild-time span backfill pass:

- `span_backfill_version`
- `span_visual_container_version`
- `span_pdf_fingerprint`
- `span_backfill_coverage`
- `span_backfill_status`
- `span_backfill_eligible_count`
- `span_backfill_covered_count`

Suggested initial version strings:

- `span_backfill_version = "2026-06-22.1"`
- `span_visual_container_version = "2026-06-22.1"`

These values are explicit invalidation levers. If the span algorithm or visual-container algorithm changes later, bump the version and rebuild will automatically stop trusting the old enrichment.

## Coverage Rule

Coverage should measure the fraction of eligible text-like raw blocks that already contain `span_metadata`.

Suggested initial threshold:

- `0.90`

This threshold is intentionally conservative. It allows reuse only when the stored raw enrichment is already mostly complete.

The exact threshold must be a module-level constant, not an ad hoc literal buried in rebuild logic.

## Fingerprint Rule

`span_pdf_fingerprint` must represent the source PDF identity strongly enough that rebuild can detect a replaced PDF.

Fingerprint source is fixed for this design:

1. compute the current source-PDF fingerprint with the existing `compute_pdf_fingerprint(source_pdf_path)` helper when the source PDF is available,
2. compare that current value against `meta["span_pdf_fingerprint"]`,
3. existing historical OCR metadata such as `raw_meta.json` may be used as reference context, but skip validity must compare against the current resolved PDF fingerprint when the PDF is available.

This rule exists because path stability does not imply content stability.

## Rebuild Decision Flow

### Current flow

```text
read raw blocks
resolve source PDF
always run span backfill
always rewrite raw blocks
continue rebuild
```

### Proposed flow

```text
read raw blocks
resolve source PDF
measure current eligible-text-like coverage

if source PDF unavailable:
  record span_backfill_status = "unavailable_pdf_missing"
  do not run span backfill
  continue rebuild using stored raw blocks as-is
elif source PDF available:
  compute current PDF fingerprint
  check version + fingerprint + coverage + visual-container version

if valid:
  skip span backfill
else:
  run span backfill
  rewrite raw blocks
  persist new span metadata fields into meta.json after raw write succeeds

continue rebuild
```

## Error Handling

The skip path must be fail-safe.

Rules:

- if the source PDF cannot be resolved, rebuild may continue using stored raw blocks, but it must not treat the span enrichment as freshly verified against the current PDF identity,
- if the source PDF cannot be resolved, set `span_backfill_status = "unavailable_pdf_missing"` or an equivalent explicit status value,
- if `current_pdf_fingerprint == "unknown"`, fingerprint validation has failed and rebuild must not treat the stored enrichment as valid for skip,
- if the current fingerprint cannot be computed while the source PDF is present, do not silently trust old enrichment,
- if metadata fields are missing, treat the paper as needing backfill,
- if coverage is below threshold, rerun backfill,
- if `write_raw_blocks_jsonl()` fails, do not update the `span_*` validity fields,
- only update the `span_*` metadata fields after raw-block persistence succeeds,
- if later derived rebuild stages fail after the raw blocks were written successfully, leaving updated `span_*` fields is acceptable because the raw enrichment itself is already persisted.

## Status Recording

Every rebuild that evaluates the skip contract should record a concrete decision status.

Recommended values:

- `skipped_valid`
- `rerun_version_mismatch`
- `rerun_fingerprint_mismatch`
- `rerun_low_coverage`
- `rerun_visual_container_version_mismatch`
- `unavailable_pdf_missing`

At minimum, rebuild should also record:

- `span_backfill_eligible_count`
- `span_backfill_covered_count`

This makes performance behavior debuggable without rereading the raw blocks manually.

## Testing Requirements

This design needs dedicated tests because the risk is incorrect skipping, not syntax failure.

Minimum coverage:

1. skip when version, fingerprint, coverage, and visual-container version all match
2. rerun when `span_backfill_version` mismatches
3. rerun when PDF fingerprint mismatches
4. rerun when coverage is below threshold
5. rerun when visual-container version mismatches
6. first rebuild with no span metadata fields still runs backfill and writes fields
7. image-heavy paper coverage uses eligible text-like blocks, not all raw blocks
8. PDF missing path records explicit unavailable status rather than silently claiming a valid skip

## Ponytail Review

No new package should be added.

This design should use:

- existing JSON/meta machinery,
- existing PDF resolver path,
- existing raw-block scan,
- stdlib hashing if a new fingerprint must be computed.

Do not add a cache library, database table, or general invalidation framework for this.

## Implementation Boundary

If implemented later, the expected files are likely:

- `paperforge/worker/ocr_rebuild.py`
- `paperforge/worker/ocr_pdf_spans.py` or a nearby helper module if the version/coverage helpers live there
- `tests/test_ocr_rebuild.py`
- `PROJECT-MANAGEMENT.md`

This should be planned separately from the current low-risk rebuild de-dup execution plan.
