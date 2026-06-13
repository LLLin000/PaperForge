## OCR Real-Paper Regression And Spec Realignment Design

**Date:** 2026-06-13
**Status:** Approved for planning
**Audience:** Maintainers, contributors, agentic implementers

---

## 1. Summary

OCR v2 is currently passing too many local helper tests while still failing on real papers. The implementation has drifted away from the approved anchor-first design and now behaves like a rescue-first pipeline:

```text
raw label -> early role guess -> reorder rescue -> render rescue
```

This design introduces a two-layer protection system before further OCR v2 fixes:

1. Real-paper regression tests based on two audited papers.
2. Spec-contract tests that lock the original architectural invariants.

The immediate goal is not a full OCR rewrite. The immediate goal is to create a trustworthy gate, then repair the shortest high-impact failure chain in:

1. role assignment
2. layered body reordering
3. page rendering

---

## 2. Goals

### 2.1 Primary goals

1. Add regression coverage that reflects real OCR failures, not toy examples.
2. Prevent future implementations from passing tests while violating page-level structure.
3. Re-anchor implementation decisions to the approved anchor-first OCR design.
4. Fix the most damaging behavior in the current rescue-first chain without requiring a full redesign in one step.

### 2.2 Secondary goals

1. Keep the first repair cycle small enough to ship safely.
2. Make failures explainable at page/block level.
3. Prepare the codebase for later convergence toward explicit anchor/family/zone stages.

### 2.3 Non-goals

1. Do not fully reimplement the entire anchor-first OCR architecture in this phase.
2. Do not snapshot entire real-paper `fulltext.md` outputs as brittle golden files.
3. Do not add publisher-specific logic beyond what is required to stop demonstrated regressions.

---

## 3. Problem Statement

The approved OCR architecture says structure should be established before final roles are assigned. In practice, the current codebase still commits to semantic guesses too early and then attempts to recover later.

Observed consequences from audited real papers:

1. Title, author, footnote, and frontmatter blocks are misclassified or silently dropped.
2. Normal body paragraphs are misclassified as references.
3. Reference continuations leak into body output.
4. Long paragraph titles are downgraded into body prose.
5. Left/right column order is repaired only partially, causing headings, body paragraphs, references, and figures to interleave incorrectly.
6. Figure pages, legend pages, continuation legends, and embedded labels are rendered through overlapping rescue rules, producing duplicate or mispositioned reader output.

Current tests do not reliably catch these failures because they mostly validate local helper behavior rather than real page outcomes.

---

## 4. Chosen Approach

The approved approach is a dual-gate design:

1. One comprehensive real-paper sample for structure/order/reference failures.
2. One dedicated real-paper sample for figure/legend/reader-output failures.
3. A second layer of spec-contract tests that encode architectural invariants independent of any one paper.

### 4.1 Selected papers

#### A. `CAQNW9Q2`

Use as the comprehensive structure sample.

Representative failures:

1. `doc_title` not recognized as a first-class role.
2. Author line dropped.
3. Footnotes unrecognized.
4. Long section titles downgraded into body prose.
5. Reference pages absorbed into body flow.
6. `Conclusion` inserted into the middle of references.

#### B. `DWQQK2YB`

Use as the figure/legend sample.

Representative failures:

1. `Journal Pre-proof` leaking into body heading flow.
2. Multi-page `abstract` label pollution.
3. Figure-summary pages and formal figure pages duplicating captions.
4. Multi-panel figures split into unstable media groups.
5. Continuation figure captions treated as fresh page-local legends.

---

## 5. Regression Strategy

## 5.1 Layer 1: Real-paper regression

This layer uses audited real samples and checks page-level outcomes.

It must not depend on temporary desktop folders. The selected sample data must be copied into stable repo fixtures.

### Required fixture contents

For each sample:

1. `annotated_pages/*.png`
2. replayable OCR page payloads sufficient to reconstruct `parsing_res_list`
3. a structured expectation file

The expectation file must be keyed by page and contain only user-relevant outcomes.

Suggested fields:

```json
{
  "pages": {
    "7": {
      "expected_roles": [
        {"block_id": 3, "role": "section_heading"}
      ],
      "expected_non_body": [8, 9, 10],
      "expected_order_relations": [
        {"before": 3, "after": 6}
      ],
      "expected_reference_rules": [
        {"block_id": 17, "must_not_render_as_body": true}
      ],
      "expected_figure_rules": [
        {"caption_block_id": 11, "must_render_once": true}
      ]
    }
  }
}
```

### Why expectations are structured instead of full snapshots

Full markdown snapshots are too brittle. Small harmless formatting changes would create noisy failures. The regression fixture should instead assert:

1. specific role correctness
2. body/non-body membership
3. critical ordering relations
4. critical render invariants
5. figure/reference hygiene

This keeps tests aligned with the actual paper-reading failures that matter.

## 5.2 Layer 2: Spec-contract tests

This layer protects design intent even outside the selected papers.

Initial contract set:

1. `zone != role`
   - Being in the body reading environment does not automatically imply `body_paragraph`.
2. `reference tail first`
   - Reference sections must be protected against contamination from generic tail content.
3. `frontmatter source-backed`
   - OCR may localize frontmatter, but OCR uncertainty must not invent or silently discard canonical frontmatter structure.
4. `figure reader-visible without body pollution`
   - Formal figure information must remain reader-visible without leaking into body prose flow.

These tests should not encode current helper internals. They should encode observable contract behavior.

---

## 6. Test Entry Points

The regression harness must test near the real production path, not just isolated helpers.

### 6.1 Page-level structured replay

Each selected page should replay through the effective pipeline path:

1. role assignment
2. column validation
3. layered body reorder
4. page rendering

This is the right seam for catching:

1. role misclassification
2. body-spine admission mistakes
3. left/right column interleave bugs
4. embedded-figure-text false positives
5. caption/media/local legend output mistakes

### 6.2 Document-level regression

Selected sample documents should also run through a reduced multi-page test that checks cross-page invariants.

Examples:

1. references are not polluted by body continuations
2. conclusion text does not land inside references
3. figure-summary page captions do not duplicate formal figure-page captions incorrectly
4. continuation legends do not produce duplicate or reassigned reader-visible figures

---

## 7. Root Cause Of Design Drift

The original OCR spec was not wrong. The implementation drifted because the design boundaries were not enforced.

### 7.1 Drift pattern

The intended architecture was:

```text
raw observations
-> signatures
-> anchors/families
-> zones
-> late role resolution
-> figure/table validation
-> render
```

The effective implementation became:

```text
raw label/text
-> early role guess
-> helper fallback to body
-> reorder rescue
-> render rescue
```

### 7.2 Main causes

1. Local patching replaced staged structure discovery.
2. Module boundaries did not converge to the spec phases.
3. Tests protected helper behavior instead of architectural invariants.
4. Reader-facing figure output, strict matching, and audit/debug responsibilities remained mixed together.

### 7.3 Practical implication

This phase must not attempt to jump directly from the current code to the final architecture in one move. It must first remove the most dangerous rescue-first behavior and re-establish trustworthy boundaries.

---

## 8. First Repair Scope

Once the regression gate exists, the first repair cycle should target only three high-impact locations.

### 8.1 Role assignment

Primary file:

- `paperforge/worker/ocr_roles.py`

Required direction:

1. tighten reference heuristics
2. stop treating common ordinal/body openings as reference-like by default
3. add explicit handling for missing high-value labels such as `doc_title` and `footnote`
4. remove the most dangerous fallback paths that silently convert uncertain structural blocks into `body_paragraph`

### 8.2 Layered body reorder

Primary file:

- `paperforge/worker/ocr_orchestrator.py`

Required direction:

1. stop slot-preserving refill behavior that reintroduces original bad positions
2. produce a true ordered output sequence for body blocks
3. keep non-body handling explicit instead of implicitly preserving accidental interleaving

### 8.3 Page rendering

Primary file:

- `paperforge/worker/ocr.py`

Required direction:

1. reduce false skips from embedded-figure-text logic
2. stop duplicating or misplacing reader-visible figure/caption output
3. stop leaking references or figure-local text into body flow
4. keep rendering from acting as a silent semantic rescue layer for upstream structural failures

---

## 9. File Structure

### New test fixtures

- `tests/fixtures/ocr_real_papers/CAQNW9Q2/...`
- `tests/fixtures/ocr_real_papers/DWQQK2YB/...`

### New or expanded tests

- `tests/test_ocr_real_paper_regressions.py`
  - page-level replay assertions
  - document-level cross-page assertions
- `tests/test_ocr_spec_contracts.py`
  - architecture contract tests

### Existing production files expected in first repair cycle

- `paperforge/worker/ocr_roles.py`
- `paperforge/worker/ocr_orchestrator.py`
- `paperforge/worker/ocr.py`

Existing tests such as `tests/test_ocr_roles.py` and `tests/test_ocr_rendering.py` may be adjusted, but they must no longer encode harmful fallback behavior as desired behavior.

---

## 10. Success Criteria

This design is successful when all of the following are true:

1. The two selected real-paper samples have stable regression coverage inside the repo.
2. The regression suite fails on current known bad behavior and passes after the intended fixes.
3. The codebase no longer relies on render-time rescue to mask upstream structural mistakes in the audited cases.
4. Spec-contract tests make it difficult to reintroduce early-role, body-default, or figure-body pollution drift.
5. The first repair cycle improves real papers without requiring a full OCR v2 rewrite.

---

## 11. Risks And Mitigations

### Risk 1: Fixtures become too large or too brittle

Mitigation:

1. store only the minimum replayable payloads
2. use structured expectations instead of full fulltext snapshots

### Risk 2: New tests overfit current audited pages

Mitigation:

1. pair real-paper tests with spec-contract tests
2. keep expectations outcome-focused, not implementation-specific

### Risk 3: First repair scope expands into full architecture rewrite

Mitigation:

1. explicitly limit first repair cycle to three production files/functions
2. defer full anchor-first restaging to later phases

---

## 12. Implementation Readiness

This design is ready for implementation planning.

The implementation plan should be organized in this order:

1. import and normalize the two selected real-paper fixtures
2. add page-level and document-level regression harnesses
3. add spec-contract tests
4. update failing legacy tests that currently protect incorrect fallback behavior
5. repair `ocr_roles.py`
6. repair `ocr_orchestrator.py`
7. repair `ocr.py`
8. verify the selected real papers now satisfy the locked expectations
