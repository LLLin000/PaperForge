# Reference Zone And Ownership Hardening Design

> Date: 2026-06-20
> Status: draft for review
> Scope: add a shared layout-facts layer that hardens reference containment and figure/table ownership on untouched OCR papers

## Goal

Stabilize two remaining high-risk OCR surfaces without reopening the OCR-v2 backbone:

1. keep the `reference_zone` practically complete while preventing non-reference intrusion,
2. keep figure/table ownership coherent on irregular display pages without reintroducing page-swallow behavior.

The design adds one shared intermediate layer after structured blocks and before specialized consumers. That layer records page-level continuity and boundary facts. Reference logic then uses those facts to contain a reference corridor. Ownership logic uses those facts to grow and validate display clusters.

The target is not perfect citation parsing or perfect object semantics. The target is stable containment: the right content stays together, and the wrong content stops leaking in.

## Non-Goals

This design does not:

- redesign OCR-v2 role classification,
- replace the existing `zone` contract with a new semantic system,
- build a full bibliographic metadata parser,
- add free-form text rescue for role classification,
- use whole-page PDF text fallback to re-run reading order,
- replace figure/table matching with a new graph-based architecture.

## Current Assessment

Truth-audit results on untouched papers show that the main residual defects are now concentrated in two places.

### 1. Reference containment is still too fragile on mixed pages

Observed failure pattern:

- references, body, and backmatter can share a page or spread,
- `reference_zone` continuation is too willing to over-extend across weakly separated content,
- `HOLD` states still create too much downstream contamination,
- explicit `References` headings or numbered entries are helpful when present, but cannot be assumed.

The key point is that the system does not need citation-parser precision here.
It needs a practical corridor that keeps reference content together and keeps obvious non-reference content out.

### 2. Ownership is still too brittle on irregular display layouts

Observed failure pattern:

- a large figure or table is visually one display unit,
- OCR inserts empty or weak `unknown_structural` gaps inside that display area,
- caption-to-asset pairing then breaks because local adjacency is too literal,
- current validation protects against dangerous page swallow, but recall is still weak on multi-panel or sparse layouts.

The issue is not primarily caption scoring. The issue is that display continuity is under-modeled.

## Design Principles

### Principle 1: Shared layout facts come before specialized decisions

Reference logic and ownership logic should not each rediscover page geometry from scratch.

The pipeline should first compute lightweight page-level continuity facts, then let each downstream consumer apply its own acceptance rules.

### Principle 2: Keep `zone` and strengthen it

The existing `zone` work is valuable and should remain authoritative at the final surface.

This design does not replace `zone`. It strengthens the evidence used to generate and validate `zone`, especially around:

- mixed body/reference/tail pages,
- display-heavy pages,
- side inserts,
- empty bridge regions.

### Principle 3: Reference logic optimizes for clean containment, not strict citation parsing

For this pass, success means:

- most real reference content remains in `reference_zone`,
- obvious non-reference content does not enter `reference_zone`,
- same-page transitions no longer cause large false spans,
- a small amount of citation-entry imperfection is acceptable.

The design should therefore be wide enough to preserve reference continuity, but strict enough to block body/backmatter/display intrusion.

### Principle 4: Ownership is cluster-first, not nearest-caption-first

Figures and tables on complex pages should first be understood as display clusters.

Only after cluster construction should a caption try to own a primary asset or grouped asset set.

### Principle 5: Text is controlled evidence only

Allowed text use in this design:

- reference family/style detection after reference candidacy already exists,
- journal-abbreviation matching as a supporting reference signal,
- controlled number/marker extraction after structural candidacy exists,
- local PDF text fallback for hard reference-entry repair inside an already accepted reference corridor.

Disallowed text use:

- phrase-based semantic role rescue,
- publisher-wording rules for deciding section meaning,
- global PDF text reordering,
- prose-content matching as the primary basis for ownership.

## Core Design

## 1. Shared Layout-Facts Layer

After structured blocks are built and normalized, compute a lightweight layout-facts layer.

This layer should not emit final semantic judgments. It should emit page-level continuity facts.

### Required facts per block

At minimum:

- `reading_band_id`
- `display_cluster_candidate_id`
- `layout_region`
- `boundary_before`
- `boundary_after`
- `bridge_eligible`

### Meaning of each field

#### `reading_band_id`

Identifies a locally continuous reading stream.

Purpose:

- helps reference continuation stay inside an explainable local flow,
- helps same-page mixed content avoid accidental cross-column or cross-region swallowing.

#### `layout_region`

Coarse page-function region only:

- `body_flow`
- `display_zone`
- `side_insert`
- `tail_candidate`
- `reference_candidate`

This is not a replacement for final role. It is a page-function hint.

#### `boundary_before` and `boundary_after`

Minimal contract:

- `none`
- `weak`
- `hard`

This captures whether reading flow likely changes at a block edge.

Examples of hard-boundary triggers:

- a strong section/backmatter heading,
- a clear transition from dense short reference-like blocks to prose,
- a display cluster start that interrupts reading flow.

#### `bridge_eligible`

Boolean.

Marks a weak or empty structural block that is allowed to act as a display-continuity bridge.

Purpose:

- prevents large display objects from being artificially split by empty OCR gaps,
- must not by itself force ownership.

## 2. Reference Corridor Hardening

Reference handling should be redesigned as a corridor-containment problem.

The system does not need a strict heading-driven `ref-start` model. It needs a way to decide whether a local run of blocks is stable enough to remain in `reference_zone` without admitting intrusions.

### 2.1 Candidate selection stays broad

Reference candidacy may come from several weak-to-strong signals:

- `raw_role` or `raw_label` reference signals,
- `layout_region == reference_candidate`,
- tail-position priors,
- short-block density,
- local reference-style evidence.

No single cue is mandatory.

This is important because untouched papers may have:

- no explicit `References` heading,
- no numbering,
- heavily split entries,
- continuation pages with no clean restart cue.

### 2.2 Final decision is practical containment

Two separate scores should be computed.

#### `ref_membership_score`

How much the block or reconstructed entry looks like reference content.

#### `non_ref_intrusion_score`

How much the block looks like content that should not enter the reference corridor.

Examples of strong intrusion evidence:

- body-style paragraph recovery,
- `Acknowledgements`, `Funding`, `Conflict of Interest`, `Data availability`,
- display captions or object inserts,
- a new section/subsection heading,
- strong side-insert structure.

The decision should optimize for:

- keeping reference-like content inside the corridor,
- stopping when intrusion evidence becomes strong.

### 2.3 Reference family/style detection is a validator

Reference format detection should support corridor stability, not dominate it.

The detector should assign a coarse family to a block or reconstructed entry:

- `vancouver_structured_numbered`
- `vancouver_structured_unnumbered`
- `author_year`
- `book_or_report`
- `unknown`

This family signal is used to answer:

- does this local run look style-consistent,
- does the run continue the same reference rhythm,
- did a likely prose/body segment interrupt the run.

The system must not require every reference entry to classify perfectly before allowing a stable `reference_zone`.

### 2.4 Journal-abbreviation support is strong positive evidence

A compact biomedical journal lexicon should be introduced using NLM-style journal abbreviations.

This lexicon should support:

- exact normalized abbreviation match,
- token-subsequence match for lightly degraded OCR,
- optional conservative fuzzy token match only inside high-confidence reference candidates.

This signal improves detection of biomedical journal references, especially unnumbered Vancouver-like entries.

It must remain optional support.
Failure to match the lexicon must not force a block out of the reference corridor.

### 2.5 Entry reconstruction is local and pragmatic

Because OCR often splits one citation across multiple blocks, the system should form local `reference entry candidates` inside a high-confidence corridor.

Blocks should be merged only when:

- they are local near-neighbors,
- the gap is small,
- the merged text raises reference-family confidence,
- intrusion evidence does not rise.

The goal is not full citation parsing.
The goal is to prevent corridor fragmentation caused by OCR splitting.

### 2.6 PDF text fallback is local repair only

If a local reference entry candidate remains badly fragmented, the system may use PDF text fallback.

This is allowed only when all of the following are true:

- the block run already sits in a high-confidence reference corridor,
- the current OCR blocks are too fragmented to sustain continuity,
- fallback is limited to a small local page window near the current block run,
- the result is used only to improve local style/continuity judgment.

It must not:

- re-run page reading order,
- rewrite the whole corridor from raw PDF text,
- become the primary reference detector.

### 2.7 HOLD must stop contaminating final membership

`HOLD` should remain a diagnostic state, not a final-membership contaminant.

If a corridor is not good enough for acceptance, it should:

- remain a candidate for audit/debugging,
- avoid converting large downstream surfaces into accepted reference content.

## 3. Ownership Hardening Through Display Clusters

Ownership should be rewritten as a display-cluster problem rather than a nearest-neighbor caption problem.

### 3.1 Build display clusters before ownership

For figure and table surfaces, first form a display cluster from:

- assets,
- caption blocks,
- inner display text,
- bridge-eligible weak/empty blocks that connect visually continuous display regions.

This cluster stage does not yet force caption ownership.

### 3.2 `bridge_eligible` exists to preserve visual continuity

Some `unknown_structural` or near-empty blocks are not semantic content, but they still occupy the display field between caption and asset.

These blocks should be allowed as continuity bridges when:

- they sit between display components,
- they do not show strong body-flow evidence,
- the surrounding geometry strongly supports one display unit.

This prevents false fragmentation on:

- large multi-panel figures,
- wide figures with right-column empty gaps,
- sparse table/figure layouts.

### 3.3 Ownership becomes cluster-first

Caption ownership should follow this sequence:

1. identify the best candidate display cluster,
2. validate that the cluster is locally coherent,
3. decide whether the caption owns a primary asset or grouped asset set,
4. demote to grouped evidence or ambiguity if validation fails.

This design keeps the current anti-page-swallow safety goal intact.

### 3.4 Ownership validation remains hard

After a display cluster is formed, validate it before strict ownership.

Validation checks should include:

- whether the cluster crosses another caption control region,
- whether the cluster became too large without internal support,
- whether body-flow or side-insert evidence interrupts the cluster,
- whether another narrower cluster explains the caption better.

If validation fails, the system should prefer:

- `grouped_evidence_only`,
- split,
- or ambiguity,

instead of forcing a strict match.

## Detectable Reference Features

The reference detector should extract weak features at block level, then aggregate them.

### Block-level reference features

- `lead_marker_signature`
- `author_signature`
- `year_signature`
- `journal_signature`
- `volume_issue_pages_signature`
- `online_marker_signature`
- `book_report_signature`
- `surface_style_signature`
- `journal_lexicon_match`

These should not individually decide final membership.

### Run-level continuity features

- local family consistency,
- punctuation rhythm consistency,
- density of short reference-like blocks,
- continuation across neighboring reading bands when the layout strongly supports it,
- conflict with hard boundaries.

## Required Contracts

## Layout-facts contract

At minimum one shared surface should expose enough information for both consumers to reason about continuity without redoing page geometry.

Acceptable implementations:

- add fields to structured blocks,
- or write a parallel `layout_segments.json` plus structured-block annotations.

The first pass should prefer the smaller diff.

## Reference decision contract

At minimum reference processing should expose:

- `ref_membership_score`
- `non_ref_intrusion_score`
- `reference_style_family`
- `reference_style_confidence`
- `reference_continuity_state`
- accepted vs candidate reference membership outcome

The system does not need to expose a full parsed bibliography model in this pass.

## Ownership contract

At minimum figure/table ownership candidates should expose:

- `display_cluster_id`
- `cluster_block_ids`
- `cluster_bbox`
- `bridge_block_ids`
- `ownership_validation_status`
- `ownership_validation_reason`

This is for auditability and debugging, not for user-facing verbosity.

## File Responsibilities

### `paperforge/worker/ocr_document.py` or nearest shared layout module

Owns:

- computation of layout facts that are shared across consumers,
- reading-band continuity,
- coarse layout-region assignment,
- hard/weak boundary detection,
- bridge-eligibility hints.

The exact file can follow the cleanest existing structure, but the responsibilities should remain centralized.

### Reference consumer module(s)

Likely `paperforge.worker` logic near current structural gate / reference-zone handling should own:

- reference candidate selection,
- family/style detection,
- journal-lexicon support,
- local entry reconstruction,
- local PDF text fallback,
- final reference-zone acceptance vs HOLD.

### `paperforge/worker/ocr_figures.py` and `paperforge/worker/ocr_tables.py`

Own:

- display-cluster construction,
- bridge-aware cluster growth,
- cluster-first caption ownership,
- validation before strict ownership.

### Render and health surfaces

Must consume accepted outcomes only.

They should not become rescue layers for weak segmentation or weak ownership.

## Acceptance Criteria

This design is successful when all of the following are true:

1. Untouched high-risk papers show fewer `reference_span_error` findings.
2. Same-page body/reference/tail mixes stop swallowing obvious non-reference content into `reference_zone`.
3. Reference handling remains practically complete even when entries are unnumbered or heading-free.
4. Untouched display-heavy papers show fewer `object_ownership_error` findings.
5. Large multi-panel displays no longer fragment just because weak empty blocks sit inside the display field.
6. No return to page-swallow ownership behavior occurs.
7. PDF fallback remains local and does not become a hidden global reordering system.

## Validation Strategy

Validate on both protected and untouched papers.

### Reference validation

Use:

1. existing gold/regression papers that already exercise reference-tail behavior,
2. untouched high-risk audit papers with same-page boundary failures,
3. untouched papers with unnumbered or heading-free reference regions when available.

Primary check:

- is the reference corridor practically complete,
- are obvious non-reference intrusions gone.

### Ownership validation

Use:

1. existing protected figure/table regressions,
2. untouched multi-panel and display-sparse papers,
3. pages where empty or weak structural gaps currently split one visual object.

Primary check:

- is ownership more coherent,
- are ambiguity and unmatched-asset counts reduced,
- has safety against page swallow remained intact.

## Recommended Execution Order

To keep the first pass small and high value, implement in this order:

1. shared layout-facts layer,
2. reference anti-intrusion corridor hardening,
3. display-cluster and bridge-aware ownership hardening,
4. journal-abbreviation lexicon support,
5. local reference-entry reconstruction,
6. local PDF text fallback for hard reference entry repair.

This order improves containment before adding refinement layers.

## References

- `docs/superpowers/specs/2026-06-19-ocr-rebuild-audit-remediation-design.md`
- `docs/superpowers/specs/2026-06-20-region-growing-figure-merge-design.md`
- `docs/superpowers/specs/2026-06-20-table-note-stabilization-design.md`
- `project/current/ocr_rebuild_audit.md`
- `audit/KIX7SKXQ/audit_report.json`
- `audit/GTRPMM56/audit_report.json`
- `https://www.icmje.org/recommendations/`
- `https://www.nlm.nih.gov/bsd/uniform_requirements.html`
- `https://www.ncbi.nlm.nih.gov/nlmcatalog/journals/`
