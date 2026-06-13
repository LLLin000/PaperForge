# OCR Real-Paper Production-Path Spec Realignment Design

**Date:** 2026-06-13
**Status:** Approved for planning
**Audience:** Maintainers, contributors, agentic implementers

---

## 1. Summary

OCR-v2 already has a document-shaped production pipeline. The current remediation problem is not that the architecture is missing on paper; it is that real-paper failures are still slipping through because the most trustworthy tests are either:

1. helper-level and too local, or
2. environment-driven live-vault audits that are informative but not stable enough to serve as the primary regression gate.

This design adds a production-path-first regression harness based on audited real papers and aligns the regression contract with the actual OCR-v2 output chain:

```text
OCR payload
-> build_raw_blocks_for_result_lines()
-> backfill_span_metadata_from_pdf()
-> build_structured_blocks()
-> normalize_document_structure()
-> build_figure_inventory()
-> synthesize_reader_figures()
-> build_table_inventory()
-> extract_and_write_objects()
-> ocr_render.render_fulltext_markdown()
```

The immediate goal is not a full architecture redesign. The goal is to establish a regression gate that matches the production path, then repair the highest-risk failure chain in:

1. seed role normalization
2. document-level structure and reading segments
3. figure/table object ownership
4. final structured rendering consumption

---

## 2. Goals

### 2.1 Primary goals

1. Add real-paper regression coverage that executes the OCR-v2 production path, not a legacy page-render seam.
2. Lock the core anchor-first invariants with explicit spec-contract tests.
3. Prevent future fixes from passing helper tests while still failing on mixed real-paper pages.
4. Converge implementation behavior toward boundary-first, artifact-first rendering without requiring a full rewrite in one pass.

### 2.2 Secondary goals

1. Keep first-pass repairs focused on the production modules that actually determine final `fulltext.md`.
2. Preserve explainability at page/block/object level.
3. Preserve the existing env-driven real-vault audit suite as a secondary safety net.

### 2.3 Non-goals

1. Do not take a new dependency on full-document golden snapshots of `fulltext.md`.
2. Do not make legacy `render_page_blocks()` behavior the main source of truth for OCR-v2 fixes.
3. Do not re-open unrelated OCR v1/vlegacy rendering paths except to reduce confusion or side effects.

---

## 3. Problem Statement

The approved OCR-v2 architecture already moved beyond page-local rescue rendering, but the regression gate has not fully caught up. As a result, the code can still regress in production-path behavior while local tests remain green.

Observed real-paper failures still cluster into four groups:

1. **Seed-role mistakes**
   - frontmatter/support blocks treated as body or headings
   - body ordinal prose (`First,`, `Fourth,`, `Metabolically,`) treated as reference-like
   - reference continuations demoted into body output

2. **Document-structure mistakes**
   - mixed body/reference pages interleaved incorrectly
   - conclusion/body continuation crossing into references
   - heading authority and tail-segment ownership applied inconsistently

3. **Object-ownership mistakes**
   - figure summary pages and body figure pages duplicating caption ownership
   - continuation legends treated as fresh local legends
   - table caption, table asset, and table note split across unrelated flows

4. **Renderer-consumption mistakes**
   - consumed object blocks re-emitted as body or loose captions
   - renderer falling back to semantic rescue instead of consuming accepted artifacts only

The problem is therefore not “write more helper tests.” The problem is “lock the actual production seam and the artifact contracts that determine final output.”

---

## 4. Chosen Approach

Use a two-layer regression gate, but bind the first layer to the OCR-v2 production chain.

### 4.1 Layer 1: production-path real-paper replay

Run selected audited pages and documents through the production pipeline artifacts:

1. raw block construction
2. optional PDF span backfill
3. structured block building
4. document normalization
5. figure inventory
6. reader figure synthesis
7. table inventory
8. object extraction metadata
9. final structured rendering

This becomes the primary regression gate.

### 4.2 Layer 2: spec-contract tests

Lock architectural invariants that must remain true even as implementation details evolve.

This prevents future drift back to role-first rescue behavior.

---

## 5. Selected Paper Coverage

## 5.1 Core document fixtures

Two papers remain the primary audited fixtures:

### A. `CAQNW9Q2`

Use as the comprehensive structure sample.

Representative failures:

1. title/author/frontmatter handling
2. long heading degradation
3. references contamination of body flow
4. conclusion/reference ordering failure

### B. `DWQQK2YB`

Use as the figure/legend sample.

Representative failures:

1. preproof/frontmatter pollution
2. abstract leakage across pages
3. figure summary page vs formal figure page ownership duplication
4. continuation legend and multi-panel grouping drift

## 5.2 Required supplemental page fixture

Add `A8E7SRVS` as a page-level supplemental fixture, not necessarily a full-paper primary fixture.

Required page coverage:

1. **Page 5**
   - multi-figure ordering and reader-visible figure presence
2. **Page 6**
   - caption continuation must remain legend/object-owned, not body-owned
3. **Page 7**
   - table caption, table asset, and table note must stay in one table object contract
4. **Page 12**
   - conclusion/reference ordering on mixed tail pages

Reason:

`CAQNW9Q2` and `DWQQK2YB` are necessary but not sufficient to lock the highest-value figure/table and mixed-tail cases already demonstrated in audit work.

---

## 5.3 Confirmed failure families from five audited OCR-v2 samples

The five desktop sample directories used in this investigation are OCR-v2 outputs, not master outputs. They are treated here as evidence of failure families, not as complete root-cause proofs.

Important discipline rule:

```text
Observed sample symptom -> production-path artifact family -> candidate responsible module(s)
```

Not:

```text
Observed sample symptom -> forced single-module blame without artifact confirmation
```

### A. High-confidence, repeated failure families

These failure families appear across multiple papers and map cleanly to OCR-v2 production-path stages.

1. **Seed-role misclassification remains a top-level failure source**
   - repeated patterns:
     - frontmatter/support text leaking into body or heading flow
     - long headings degrading into body prose
     - ordinal body prose being treated as reference-like
     - reference continuations falling back into body
   - strongest affected samples:
     - `CAQNW9Q2`
     - `A8E7SRVS`
     - `TSCKAVIS`
     - `M36WA39N`
   - high-confidence responsibility layer:
     - `ocr_roles.py`
   - downstream layers may amplify this, but this family consistently begins at the seed-role layer.

2. **Document boundary enforcement is still unstable on mixed tail pages**
   - repeated patterns:
     - body continuation crossing into references
     - references appearing before left-column body completion
     - conclusion/backmatter/reference ordering drift
     - abstract/frontmatter/support boundaries not staying isolated
   - strongest affected samples:
     - `CAQNW9Q2`
     - `DWQQK2YB`
     - `A8E7SRVS`
     - `M36WA39N`
   - high-confidence responsibility layer:
     - `ocr_document.py`
     - `ocr_structural_gate.py`
   - rationale:
     - these are boundary and segment-authority failures, not merely local block-label failures.

3. **Object ownership is still not sufficiently exclusive**
   - repeated patterns:
     - figure summary pages and formal figure pages duplicating ownership
     - continuation legends treated as fresh local figures
     - table caption, asset, and note splitting into separate flows
     - figure-local fragments reappearing outside accepted object ownership
   - strongest affected samples:
     - `DWQQK2YB`
     - `A8E7SRVS`
     - `TSCKAVIS`
   - high-confidence responsibility layer:
     - `ocr_figures.py`
     - `ocr_figure_reader.py`
     - `ocr_tables.py`

4. **Final renderer still visibly amplifies upstream ownership/segment mistakes**
   - repeated patterns:
     - consumed object-like material reappearing as loose body/caption output
     - tail sections surfacing in the wrong visible order
     - reader-visible output reflecting mixed ownership instead of accepted artifact contracts
   - strongest affected samples:
     - all five, with different severity
   - high-confidence responsibility layer:
     - `ocr_render.py`
   - caution:
     - renderer is often the visible failure surface, but not always the originating root cause.

### B. Medium-confidence module mappings

These are plausible and useful for planning, but should remain framed as candidate mappings until confirmed by production-path replay fixtures and artifact assertions.

1. `CAQNW9Q2`
   - strong symptom set:
     - reference contamination of body flow
     - conclusion/reference ordering failure
     - long heading degradation
   - current best mapping:
     - `ocr_roles.py`
     - `ocr_document.py`
     - `ocr_structural_gate.py`

2. `DWQQK2YB`
   - strong symptom set:
     - preproof/frontmatter pollution
     - abstract leakage across pages
     - figure summary page vs formal figure page duplication
   - current best mapping:
     - `ocr_document.py`
     - `ocr_structural_gate.py`
     - `ocr_figures.py`
     - `ocr_figure_reader.py`

3. `M36WA39N`
   - strong symptom set:
     - frontmatter left rail leaking into body
     - sustained double-column order drift
     - figure-local text leaking into body
   - current best mapping:
     - `ocr_roles.py`
     - `ocr_document.py`
     - `ocr_render.py`

4. `TSCKAVIS`
   - strong symptom set:
     - heading hygiene failure
     - true subsection titles degrading into body
     - legend/table support material not staying cleanly out of body flow
   - current best mapping:
     - `ocr_roles.py`
     - `ocr_document.py`
     - `ocr_tables.py`
     - `ocr_render.py`

5. `A8E7SRVS`
   - strong symptom set:
     - ordinal prose becoming `reference_item`
     - reference continuation leaking into body
     - table object adjacency/ownership instability
   - current best mapping:
     - `ocr_roles.py`
     - `ocr_document.py`
     - `ocr_structural_gate.py`
     - `ocr_tables.py`

### C. Explicit non-claims

This design intentionally does **not** claim the following without further artifact-backed proof:

1. that every per-paper symptom can already be localized to exactly one module
2. that all renderer-visible failures originate inside `ocr_render.py`
3. that all figure failures begin in `ocr_figures.py` rather than earlier document segmentation
4. that page-local traces alone are sufficient to prove final production-path causality

Where confidence is only medium, the implementation plan should add replay fixtures and artifact assertions before treating those mappings as root-cause truth.

---

## 6. Test Entry Points

The regression harness must distinguish the real OCR-v2 production path from legacy diagnostic helpers.

### 6.1 Primary harness: production-path document replay

Input:

1. replayable OCR payloads (`all_results` shape)
2. source metadata
3. optional source PDF or precomputed span metadata fallback

Execution path:

```text
build_raw_blocks_for_result_lines()
-> backfill_span_metadata_from_pdf() [optional in tests]
-> build_structured_blocks()
-> normalize_document_structure()
-> build_figure_inventory()
-> synthesize_reader_figures()
-> build_table_inventory()
-> extract_and_write_objects() [artifact assertions, no need to require image crop success]
-> render_fulltext_markdown()
```

Assertable surfaces:

1. structured blocks
2. document structure artifacts
3. figure inventory
4. reader figure payload
5. table inventory
6. final markdown invariants

This is the main regression seam.

### 6.2 Secondary harness: env-driven real-vault rebuild audit

Keep the existing `PAPERFORGE_REAL_OCR_VAULT` rebuild tests, but explicitly classify them as:

1. audit/integration coverage
2. broad drift detection
3. non-primary regression gate

They remain valuable because they validate more papers, but they must not be the only protection for deterministic regression.

### 6.3 Legacy harness: page-local renderer replay

`render_page_blocks()`-style page replay may still exist as a diagnostic seam for old traces, but it must be labeled explicitly as:

1. diagnostic only
2. not final fulltext truth
3. not the main repair target for OCR-v2

---

## 7. Fixture Shape

Do not store full-document markdown snapshots as the primary expected output.

Instead, each audited fixture should provide structured expectations at the page/document/object level.

### 7.1 Structured expectation categories

Each fixture may contain:

```json
{
  "pages": {
    "6": {
      "expected_roles": [],
      "expected_zone_membership": [],
      "expected_segment_order": [],
      "expected_object_ownership": [],
      "expected_render_invariants": []
    }
  },
  "document": {
    "expected_reader_figure_count_min": 3,
    "expected_reference_zone": true,
    "expected_abstract_span": true
  }
}
```

### 7.2 Required ownership fields

Figure/table failures are not captured well enough by `must_render_once` alone.

Expectations must be able to assert object ownership directly, for example:

```json
{
  "expected_object_ownership": [
    {
      "object_type": "figure",
      "figure_number": 5,
      "caption_block_ids": ["p6_b5", "p6_b6"],
      "asset_block_ids": ["p6_b4"],
      "must_render_as_object": true,
      "must_not_render_caption_blocks_as_body": true
    },
    {
      "object_type": "table",
      "table_number": 3,
      "caption_block_ids": ["p7_b4"],
      "asset_block_ids": ["p7_b5"],
      "note_block_ids": ["p7_b6"],
      "must_render_as_object": true,
      "must_not_split_by_body_blocks": true
    }
  ]
}
```

### 7.3 Required render invariant fields

Examples:

```json
{
  "expected_render_invariants": [
    {"type": "before_text", "before": "Conclusion", "after": "References"},
    {"type": "not_in_body", "text_contains": "The angle between these two lines"},
    {"type": "no_duplicate_caption", "caption_regex": "Fig\\.\\s*5"}
  ]
}
```

### 7.4 Required consumption fields

Object ownership alone cannot verify that a consumed block stays consumed. Consumption assertions close this gap:

```json
{
  "expected_consumption": [
    {
      "block_id": "p6_b5",
      "consumed_by": "figure_005",
      "must_not_render_as_body": true,
      "must_not_render_as_loose_caption": true
    },
    {
      "block_id": "p7_b4",
      "consumed_by": "table_003",
      "must_not_render_as_body": true
    }
  ]
}
```

This keeps expectations stable while still checking the real contract that users care about.

---

## 8. Spec-Contract Tests

Keep the original four contracts and add three missing ones.

### 8.1 Existing required contracts

1. `zone != role`
2. `reference tail first`
3. `frontmatter source-backed`
4. `figure reader-visible without body pollution`

### 8.2 Additional required contracts

1. **`object ownership is exclusive`**
   - a block consumed by an accepted figure/table object must not also render as loose body/caption text

2. **`renderer is not a semantic rescue layer`**
   - renderer may format accepted artifacts, but must not re-decide semantic membership from raw text or seed roles

3. **`reading segments are authoritative`**
   - mixed body/reference tail pages must follow document-level reading segments, not raw page-local y/x rescue

These three contracts are required to prevent the current loop of “fix role, renderer re-breaks it” and “fix object ownership, loose blocks still leak into body.”

---

## 9. Repair Scope

This phase must target the production modules that govern final OCR-v2 output.

### 9.1 Seed role normalization

Primary file:

- `paperforge/worker/ocr_roles.py`

Required direction:

1. normalize frontmatter seeds into source-backed frontmatter candidates
2. explicitly handle `footnote`, `vision_footnote`, `aside_text`, and similar non-body support signals
3. prevent body ordinal openings from becoming `reference_item` without supporting tail/zone/numbering evidence
4. stop dangerous fallback paths that silently turn weak structural candidates into body by default

Clarification:

`doc_title` handling is not “missing entirely”; it already exists in the broader pipeline. The required fix is to make title/frontmatter seed handling artifact-shaped and source-backed, not merely render-safe.

### 9.2 Document structure, reading segments, and structural gate

Primary files:

- `paperforge/worker/ocr_document.py`
- `paperforge/worker/ocr_structural_gate.py`

Required direction:

1. produce explicit page/document reading segments
2. preserve `abstract_span`, `reference_zone`, `backmatter_regions`, and body flow boundaries through mixed pages
3. treat reading segments as authoritative for tail ordering
4. prevent mixed body/reference pages from being interleaved by page-local geometry alone
5. keep structural verification honest: weak evidence becomes `HOLD`, candidate, or safe demotion, not fake acceptance

### 9.3 Figure ownership and reader figure synthesis

Primary files:

- `paperforge/worker/ocr_figures.py`
- `paperforge/worker/ocr_figure_reader.py`

Required direction:

1. preserve formal legend detection without allowing inline narrative leakage
2. resolve summary-page vs body-page duplication at ownership level
3. attach continuation legends to the correct reader-visible figure contract
4. keep reader-visible statuses (`LEGEND_ONLY`, `GROUPED_APPROXIMATE`, `HOLD`) explicit and separate from strict status
5. guarantee consumed caption/asset ids are complete enough for renderer duplicate suppression

### 9.4 Table ownership

Primary file:

- `paperforge/worker/ocr_tables.py`

Required direction:

1. keep table caption, table asset, and table note under one table ownership contract
2. support continuation semantics honestly
3. prevent table fragments from bypassing inventory authority and leaking into body flow

### 9.5 Final structured rendering

Primary file:

- `paperforge/worker/ocr_render.py`

Required direction:

1. render only accepted artifacts and accepted body blocks
2. consume figure/table/reference/abstract blocks exactly once
3. suppress loose media/caption output after object ownership is accepted
4. do not use renderer text heuristics as semantic rescue for membership decisions

### 9.6 Legacy seam cleanup

Secondary file, optional cleanup only:

- `paperforge/worker/ocr.py`

Allowed scope:

1. reduce confusion around legacy helper paths
2. keep compatibility outputs honest
3. do not make this file the main semantic repair surface for OCR-v2

`ocr_orchestrator.py` is not a first-priority production repair target for this phase.

---

## 10. Implementation Order

The implementation plan should follow this order:

1. import and normalize selected real-paper fixtures into repo-local deterministic test data
2. add production-path replay harness
3. add structured expectations for page/document/object/render invariants
4. add or tighten spec-contract tests
5. classify existing env-driven live-vault tests as secondary audit coverage
6. classify legacy page-local renderer tests as diagnostic only
7. repair `ocr_roles.py`
8. repair `ocr_document.py` + `ocr_structural_gate.py`
9. repair `ocr_figures.py` + `ocr_figure_reader.py`
10. repair `ocr_tables.py`
11. repair `ocr_render.py`
12. optionally reduce legacy helper side effects in `ocr.py`

---

## 11. Success Criteria

This design is successful when all of the following are true:

1. The primary regression suite executes the actual OCR-v2 production path.
2. `CAQNW9Q2` and `DWQQK2YB` are locked as deterministic real-paper fixtures.
3. `A8E7SRVS` page-level supplemental checks cover figure/table and mixed-tail cases not fully captured by the two main papers.
4. Object ownership is asserted directly, not inferred indirectly from final markdown alone.
5. Renderer duplicate suppression and region consumption are validated as artifact contracts, not left to heuristics.
6. The codebase cannot drift back to rescue-first semantics without failing contract tests.

---

## 12. Risks And Mitigations

### Risk 1: Repo-local fixtures become too large

Mitigation:

1. store only replayable payload subsets and selected annotated pages
2. avoid full-document markdown snapshots

### Risk 2: Real-vault and repo-local tests diverge

Mitigation:

1. keep repo-local fixtures as the primary deterministic gate
2. keep env-driven rebuild tests as broader audit coverage
3. periodically reconcile them when adding new fixture cases

### Risk 3: Fixes overfocus on old seams

Mitigation:

1. bind primary tests to the production path
2. explicitly downgrade legacy page-local seams to diagnostic-only status

---

## 13. Implementation Readiness

This design is ready for implementation planning.

The resulting plan should be production-path-first, fixture-backed, and artifact-contract-driven.
