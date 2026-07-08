# OCR Anchor-First Structured Parsing Design

**Date:** 2026-06-08
**Status:** Proposed
**Audience:** Maintainers, contributors, agentic implementers

---

## 1. Summary

PaperForge's OCR pipeline currently commits to semantic roles too early. Raw OCR labels and local text heuristics are promoted into final roles before the system has established stable structure, layout, or document-level constraints. This creates a recurring rescue pattern:

```text
raw_label/text -> final role -> normalize -> rescue -> demote/promote -> attach -> render
```

This design replaces that flow with an anchor-first parsing pipeline:

```text
raw observations
-> structural signatures
-> stable anchors / families
-> zone inference
-> role resolution
-> figure/table validation
-> render + health
```

The key change is not a full rewrite of outputs or CLI behavior. The change is the decision order.

1. External metadata becomes the frontmatter truth source.
2. Body structure is inferred from middle-page dominant families, not from single-block certainty.
3. Reference parsing is tail-first and reference-first.
4. Zone membership does not imply final role.
5. Style/layout family partition happens before body/default paragraph assignment.
6. Figure/table processing remains in v1, but consumes stronger anchor/zone evidence.

The redesign keeps external compatibility where practical:

- existing CLI commands remain the same
- existing `fulltext.md`, `meta.json`, figure/table render outputs, and health outputs remain user-facing artifacts
- new intermediate artifacts may be added for diagnosis and downstream stability

---

## 2. Goals

### 2.1 Primary goals

1. Stop treating raw OCR labels as initial semantic truth.
2. Build stable anchors before final role assignment.
3. Reduce dependence on pure text matching for headings, references, legends, and frontmatter.
4. Protect `reference_zone` integrity even when tail layout diverges from body reading order.
5. Preserve and strengthen current figure/table handling instead of discarding it.
6. Improve explainability: every accepted role should be traceable to known evidence.

### 2.2 Secondary goals

1. Preserve current external artifact contracts as much as possible.
2. Add diagnostics that reveal where the pipeline is uncertain.
3. Keep room for future publisher/profile handling without making it the main driver now.

### 2.3 Non-goals

1. Do not fully redesign user-facing OCR commands.
2. Do not require a new storage location for canonical OCR output.
3. Do not require full explicit parsing of every generic tail/backmatter subtype.
4. Do not attempt template-specific logic for every publisher family in v1.

---

## 3. Core principles

### 3.1 Anchor is not text match

An anchor is not "a block whose text matches a keyword". An anchor is a fact or structure that has enough independent support to constrain later parsing.

These are not stable anchors by themselves:

- `References`
- `Introduction`
- `Methods`
- `Abstract`
- `Figure 1`
- `Table 1`
- `paragraph_title`
- `figure_title`

These are observations, markers, or candidates. They only become stable when reinforced by source, structure, layout, or family consistency.

### 3.2 Source metadata is frontmatter truth

`Zotero / BBT` metadata is the truth source for:

- title
- authors
- doi
- journal
- year

OCR does not invent frontmatter truth. OCR only:

- localizes source-backed fields to block groups
- verifies alignment
- preserves alternatives when OCR disagrees

If OCR cannot localize title/authors/doi, the source metadata still remains canonical.

### 3.3 Zone is not role

`body_zone` means the block lies in the main reading environment. It does not mean the block is a body paragraph.

Within the same zone, blocks may still belong to different style/layout families:

- body-like
- heading-like
- legend-like
- table-caption-like
- reference-like
- support/box/sidebar-like
- unknown

### 3.4 Body is a middle-page dominant family, not a single-block certainty

The system should not ask "is this block absolutely body?" early in the pipeline. Instead it should ask:

```text
Which style/layout family dominates the middle pages across multiple samples,
repeats consistently, and forms the most stable main reading component?
```

That dominant middle-page family becomes the `body_family_anchor`.

### 3.5 Tail parsing is reference-first

Tail parsing should prioritize protecting reference integrity, not solving a perfect generic backmatter boundary.

The system should be willing to leave generic non-reference tail content under weaker labels if that helps avoid reference contamination.

### 3.6 Main component first, deviations second, naming last

The intended parsing order should mimic how a human reads layout:

```text
global layout
-> dominant repeated component
-> deviations from dominant component
-> local textual confirmation
-> global consistency
```

---

## 4. Stable evidence taxonomy

### 4.1 Source-backed anchors

These are derived from external metadata and localized in OCR blocks when possible.

Examples:

- `title_anchor`
- `authors_anchor`
- `doi_anchor`

These anchors may have states such as:

- `CERTAIN` - source value localized to OCR blocks with strong alignment
- `SOURCE_ONLY` - source value known, OCR localization missing or weak

### 4.2 Structure-backed anchors

These rely on numbering, sequence, family closure, or consistent formatting patterns.

Examples:

- heading numbering family
- reference family
- figure legend numbering family
- table caption numbering family

`reference_item` should not be treated as a stable anchor solely because a single block looks citation-like. Instead, a set of mutually validating items forms a `reference_family_anchor`.

### 4.3 Layout-backed anchors

These rely on geometry, span, continuity, and container/column behavior.

Examples:

- body dominant family on middle pages
- main column continuity
- media clusters
- display-like local regions
- preproof cover region

### 4.4 Preproof constraint

Explicit publisher/profile modeling is out of scope for v1, except for `preproof` handling. Preproof signals remain important because they regularly contaminate page-1 frontmatter localization.

`preproof` should not promote arbitrary blocks into semantic roles. It should act as an early suppression / exclusion / zone constraint signal.

---

## 5. Structural signatures

Every block should first be represented as a raw observation plus signatures. At this stage, semantic role remains unassigned.

Suggested block shape:

```json
{
  "block_id": "p2_b14",
  "page": 2,
  "raw_label": "paragraph_title",
  "text": "III. RESULTS AND DISCUSSION",
  "bbox": [207, 141, 504, 162],
  "span_signature": {
    "font_family_norm": "TimesNewRoman",
    "font_size_median": 9.35,
    "bold_ratio": 0.0,
    "italic_ratio": 0.0,
    "line_count": 1,
    "color_hint": null
  },
  "layout_signature": {
    "x0": 207,
    "x_center": 355,
    "width": 297,
    "height": 21,
    "column_hint": "left",
    "container_hint": null
  },
  "marker_signature": {
    "type": "heading_roman",
    "raw_marker": "III.",
    "number": 3,
    "level_hint": 1,
    "normalized_text": "RESULTS AND DISCUSSION"
  },
  "role": "unassigned"
}
```

### 5.1 Marker signature scope

Markers remain useful, but they are supportive evidence, not the primary driver. In most cases, style/layout/continuity should outrank marker-only conclusions.

Marker types should be extensible. Initial categories include:

- `heading_arabic`
- `heading_decimal`
- `heading_roman`
- `heading_alpha`
- `canonical_section_name`
- `figure_number`
- `table_number`
- `reference_numeric_bracket`
- `reference_numeric_dot`
- `reference_numeric_parenthesis`
- `reference_author_year`
- `reference_vancouver_like`
- `publisher_furniture`
- `doi`
- `year`
- `none`

The list is not exhaustive and must not be treated as the main stability source.

---

## 5.2 Shared decision statuses

Anchors, families, zones, and object matches should use a shared small decision vocabulary.

Recommended statuses:

- `ACCEPT`
- `HOLD`
- `REJECT`
- `SOURCE_ONLY`
- `OBSERVATION_ONLY`
- `CONFLICT`

Guidance:

- `ACCEPT`: enough evidence to constrain downstream parsing
- `HOLD`: evidence is promising but insufficient for irreversible commitment
- `REJECT`: candidate contradicted by stronger evidence
- `SOURCE_ONLY`: source metadata is canonical, but OCR localization is missing or weak
- `OBSERVATION_ONLY`: marker/signature exists, but no stable structure has formed yet
- `CONFLICT`: two strong evidence streams disagree and must remain explicit

This vocabulary should be shared across:

- source anchors
- body/reference family anchors
- zones / region bus
- figure/table matches
- health summaries

---

## 5.3 Core module APIs

The implementation should converge on a small explicit API surface. Function names may vary slightly, but responsibilities should map to the following interfaces:

```python
build_structural_signatures(raw_blocks) -> list[SignedBlock]

localize_source_frontmatter(source_meta, signed_blocks) -> SourceAnchors

discover_body_family(signed_blocks, source_anchors, constraints) -> BodyFamilyAnchor

discover_reference_family(signed_blocks, body_family, constraints) -> ReferenceFamilyAnchor

infer_region_bus(signed_blocks, anchors, families) -> RegionBus

partition_families_inside_zones(signed_blocks, region_bus, families) -> FamilyAssignments

resolve_roles_late(signed_blocks, region_bus, family_assignments) -> FinalBlocks

validate_figures_tables(final_blocks, anchors, families, region_bus) -> Inventories
```

Design intent:

- no early function should require final semantic roles as input
- source/frontmatter localization should be early and independent
- family partition should be explicit and not folded invisibly into late role resolution
- figure/table validation should consume the output of late structure, not define it

---

## 6. Zone model

### 6.1 Required zones in v1

The design should not force all blocks into only `frontmatter / body / backmatter`. The following zones are useful enough to justify first-class handling in v1:

1. `preproof_cover_zone`
2. `frontmatter_main_zone`
3. `frontmatter_side_zone`
4. `body_zone`
5. `reference_zone`
6. `display_zone`
7. `tail_nonref_hold_zone`

`tail_nonref_hold_zone` is intentionally weakly named. The system does not need to solve all tail semantics if reference integrity can be protected without it.

### 6.2 Zone semantics

- `frontmatter_main_zone`: title, authors, affiliations, abstract, keywords, doi, source-localized frontmatter
- `frontmatter_side_zone`: correspondence, editorial metadata, boxed frontmatter-side structures, marginal support blocks
- `body_zone`: main reading environment for headings, paragraphs, inline mentions, embedded local structures
- `reference_zone`: a protected tail structure with its own item segmentation and local reading-order logic
- `display_zone`: media, legends, large tables, figure plates, display-heavy local structures
- `tail_nonref_hold_zone`: residual tail structures that are not strongly resolvable but should not disturb references or body

### 6.3 Zone does not collapse family distinctions

Inside `body_zone`, the parser must still partition blocks by style/layout family before final role assignment.

This is critical for preventing legends, table captions, headings, and boxed support blocks from being defaulted into body paragraphs simply because they occur in body pages.

---

## 7. Inference order

The pipeline should proceed in this order:

1. raw observation extraction
2. structural signature extraction
3. preproof exclusion / suppression
4. source-backed frontmatter localization
5. middle-page body family discovery
6. tail reference family discovery
7. zone inference and boundary bands
8. non-body family grouping inside zones
9. role resolution inside zones
10. figure/table validation and matching
11. health generation and markdown emission

### 7.1 Why body family comes early

Body is not identified from a single block. It is discovered from dominant middle-page repeated families sampled across 3-5 middle pages where possible.

The system should prefer a multi-page statistical baseline over page-1 assumptions.

Middle-page sampling must explicitly avoid pages dominated by:

- preproof cover/furniture
- title/authors/abstract-heavy frontmatter
- pure reference tails
- figure-plate / caption-appendix pages

Suggested sampling policy:

- exclude page 1 by default
- exclude the last 20% of pages by default
- prefer the 25%-70% document range when enough pages exist
- skip pages where media/display blocks dominate local area
- skip pages with extreme short-block density or obvious tail/frontmatter contamination

Suggested block eligibility for body-family discovery:

- `word_count >= 25`
- no strong figure/table/reference marker
- usable `span_metadata` or equivalent span signature
- width consistent with main text columns
- repeated across multiple sample pages

Suggested clustering dimensions:

- `font_family_norm`
- `font_size_bucket`
- `width_bucket`
- `x_center_bucket`
- `line_count`
- approximate paragraph length

The chosen family should be the repeated cluster with the strongest cross-page dominance, not the most convenient single page sample.

### 7.2 Why tail reference discovery comes before generic backmatter

Reference handling has the strongest tail-side structural payoff and the greatest downstream formatting impact. Generic tail/backmatter semantics are lower priority when evidence is weak.

---

## 8. Boundary logic

### 8.1 Boundaries are bands, not single hard lines

The parser should model uncertain transitions as boundary bands rather than as single irreversible cuts.

This is especially important for:

- frontmatter -> body transition
- body -> reference transition
- local body -> display interruptions

### 8.2 Frontmatter to body

`frontmatter_main_zone` should expand from source anchors and abstract-like local structure, but should stop when frontmatter-only families fade and body continuity stabilizes.

Useful evidence:

- source-backed title/authors/doi localization
- abstract heading / abstract body patterns
- first stable body family continuity
- short style-divergent interruption followed by return to body continuity (heading-like behavior)

The parser must not assume that `Introduction` or `Abstract` alone gives a perfect boundary.

Observed risk cases from real papers that this boundary logic must tolerate:

- preproof cover on page 1, but actual title/authors localized on page 2
- page-1 abstract with body starting immediately on page 2
- page-2 `Introduction` beginning while residual frontmatter structures are still nearby
- review-style papers whose first body page still visually resembles frontmatter

### 8.3 Body to tail

The system should not aggressively solve a generic `body -> backmatter_nonref` boundary.

Instead:

1. find and protect `reference_zone`
2. let non-reference tail structures remain weakly typed if necessary
3. infer body end only when strong evidence exists

Strong evidence may include:

- stable numbered heading system clearly terminating
- body continuity fading while reference family stabilizes
- display-tail structures clearly detaching from body continuity

If heading/body evidence is weak, the parser should avoid claiming an exact body end.

---

## 9. Reference-first tail parsing

Reference handling is special enough to justify its own parsing contract.

### 9.1 Reference family anchor

References should become stable through family closure, not keyword spotting. A `reference_family_anchor` can be established when multiple blocks support each other through:

- numbering sequence
- author-year pattern consistency
- hanging-indent / continuation pattern
- shared span/layout family
- local tail continuity

### 9.2 Reference heading binding

`References` or `Bibliography` should not be treated as stable anchors by themselves. They are useful binding evidence when a reference family already exists or is strongly emerging.

### 9.3 Reference-local reading order

`reference_zone` may use a reading-order policy different from `body_zone`.

Important case:

- the paper body is effectively two-column
- references begin under a `References` heading
- the references area opens its own local flow that is not simply inherited from the prior body reading order

Therefore:

1. `body reading order` and `reference reading order` must be decoupled
2. once `reference_zone` is accepted, its internal order should be solved using reference-family evidence first
3. body column-major assumptions must not override reference-local structure

Observed risk cases from real papers that this logic must tolerate:

- references beginning before the last page while body-style pages still exist immediately before them
- references laid out under a local `References` heading block with their own left/right progression
- review/reference pages where running journal furniture remains present but should not affect reference-local ordering

### 9.4 Reference item segmentation

Only after `reference_zone` and `reference_family_anchor` are accepted should the parser segment individual `reference_item`s.

This prevents single citation-like body fragments, table notes, or tail support text from being prematurely promoted into references.

If the reference family uses numeric markers such as `numeric_bracket`, `numeric_dot`, or `numeric_parenthesis`:

- item start should be anchored at the numbered entry
- item boundary should run until the next numbered entry
- continuation lines should be absorbed using shared span, indent, `x0`, and hanging-indent evidence
- numbering gaps should trigger `HOLD`, not auto-repair

If the reference family is `author_year` or `vancouver_like` without strong explicit numbered starts:

- accept `reference_zone` first
- permit weaker `family_based` item segmentation
- keep item-boundary confidence lower than numeric-family segmentation

---

## 10. Family partition before role resolution

### 10.1 The required partition step

Inside large zones, especially `body_zone`, the parser must partition blocks into style/layout families before assigning final roles.

Useful family classes:

- `body_like`
- `heading_like`
- `legend_like`
- `table_caption_like`
- `reference_like`
- `support_like`
- `unknown_like`

### 10.2 Why this is necessary

Without this partition step, the parser will repeatedly absorb:

- figure legends into body
- table captions into body
- short headings into body
- side support / boxed structures into body

This is the current failure pattern the redesign is explicitly trying to eliminate.

The partition step must not assume width alone is enough to detect support/sidebar structures. Some non-body structures may be nearly as wide as body text while still breaking continuity through container, position relation, or local family closure.

### 10.3 Body is not the default sink

A block should become `body_paragraph` only after the parser has failed to explain it more strongly as another stable family member.

This is the opposite of the current default-`text`-to-body pattern.

---

## 11. Role resolution contracts

### 11.1 Body paragraph

A block should become `body_paragraph` only when:

- it lies in `body_zone`
- it belongs to `body_like` family
- it fits middle-page body family expectations
- it participates in local reading-flow continuity
- it is not better explained by heading / legend / caption / support families

### 11.2 Heading

Heading should be resolved as a structural interruption pattern rather than from label or marker alone.

Useful evidence:

- style divergence from body family
- short standalone tendency
- heading-family repetition across pages/sections
- local interruption followed by return to body continuity
- numbering marker, if present

### 11.3 Figure legend

Legend resolution should prefer:

- legend-like family divergence from body family
- marker support (`Figure`, `Fig.`) when available
- adjacency to media cluster or display structure
- closure within figure numbering/order validation
- rejection of inline narrative mentions

### 11.4 Table caption

Table caption resolution should prefer:

- table-caption-like family
- adjacency to table/display region
- marker support when available
- local display continuity

### 11.5 Reference item

`reference_item` should only be finalized after `reference_zone` is accepted and the block belongs to `reference_family_anchor`.

### 11.6 Support / boxed / sidebar blocks

V1 should prioritize not polluting body over perfect naming. Many such blocks can remain under intermediate roles such as:

- `support_block`
- `boxed_support_block`
- `non_body_insert`
- `support_candidate`

The essential behavior is to preserve layout integrity and avoid false body absorption.

---

## 12. Figure and table handling

Figure/table handling stays inside v1.

### 12.1 What remains

Current strengths should be preserved where possible:

- media clustering
- asset extraction/cropping
- object markdown rendering
- figure/table inventories

### 12.2 What changes

Current matching should consume stronger upstream evidence:

- legend family membership
- zone context
- body-vs-display distinction
- numbering/order continuity
- local media adjacency

### 12.3 Validation-first matching

Matching should become a validation problem, not a nearest-neighbor shortcut.

Suggested checks:

1. numbering compatibility
2. count compatibility
3. global order compatibility
4. local spatial plausibility
5. conflict detection

Output states should include:

- `ACCEPT`
- `HOLD`
- `REJECT`

### 12.4 Validation does not imply inline placement

Validation-first figure/table matching only decides whether a legend/caption and media/table asset belong together strongly enough to build an object inventory.

It does not require exact markdown insertion at the original visual location.

Accepted v1 outputs include:

- matched figure/table object
- held ambiguous object group
- unmatched legend/caption
- unmatched asset

Inline placement remains a rendering policy. It must not feed back into anchor discovery, zone inference, or role resolution in v1.

---

## 13. Mapping to current code

This redesign is intentionally framed as a sequence correction, not a total replacement.

### 13.1 `paperforge/worker/ocr_blocks.py`

Current role:

```text
raw blocks -> assign_block_role -> normalize_document_structure -> rescue
```

Target role:

```text
raw blocks -> signatures -> anchors/families -> zones -> role resolution
```

`build_structured_blocks()` can remain the orchestration entrypoint, but its internal phases need to be reordered.

### 13.2 `paperforge/worker/ocr_roles.py`

Current role assignment is too eager. The module should be split conceptually into:

1. marker/signature extraction
2. late role resolution inside established context

`assign_block_role()` should no longer be the pipeline's first semantic decision point.

### 13.3 `paperforge/worker/ocr_figures.py`

Preserve:

- media clusters
- figure/table utility functions
- matching inventories

Change inputs from:

```text
raw role = figure_caption/media_asset
```

to:

```text
legend family candidates + media clusters + zone/context evidence
```

### 13.4 `paperforge/worker/ocr_health.py`

Preserve the health/reporting layer, but add anchor/zone/family coverage concepts.

Health should increasingly report:

- source-anchor localization quality
- body-family confidence
- reference-zone confidence
- unresolved family holds
- figure/table validation ambiguity

### 13.5 Existing metadata alignment logic

Keep and elevate the current source-alignment work already implied by:

- `resolve_metadata()`
- `_align_frontmatter_to_source_metadata()`
- author alignment helpers

These should be considered part of the new frontmatter anchor layer, not just downstream metadata cleanup.

---

## 14. Suggested intermediate artifacts

These artifacts are internal and diagnostic. They can be added without breaking external compatibility.

### 14.1 `structural_signatures.jsonl`

One row per block with:

- raw observation
- marker signature
- span signature
- layout signature

### 14.2 `anchors.json`

Document-level stable anchors/families summary, including:

- source anchors
- body family anchor
- heading family anchors
- reference family anchor
- legend/caption families

### 14.3 `region_bus.json`

Accepted zones, boundary bands, and confidence summaries.

### 14.4 enriched `document_structure.json`

If `document_structure.json` remains the canonical diagnostic artifact, it should be expanded to reflect anchor-first sequencing rather than only post-role normalization state.

---

## 15. Health contract

The OCR health report should add or emphasize:

- source anchor localization status
- body family anchor quality
- reference zone confidence
- reference-local reading-order confidence
- number of unresolved / held non-body families
- legend/table matching ambiguity counts
- preproof suppression activation

The report should distinguish between:

- missing evidence
- ambiguous evidence
- explicit conflict

This is more useful than relying only on final role counts.

---

## 16. Implementation phases

### Phase 1: Signatures first

Add `marker_signature`, `span_signature`, and `layout_signature` generation without changing final external outputs.

### Phase 2: Source-backed frontmatter anchors

Move frontmatter truth resolution to a first-class early pipeline stage using current metadata alignment logic.

### Phase 3: Body and reference family anchors

Add:

- middle-page body family anchor discovery
- reference family anchor discovery
- basic tail reference protection

### Phase 4: Zone inference

Introduce:

- `preproof_cover_zone`
- `frontmatter_main_zone`
- `frontmatter_side_zone`
- `body_zone`
- `reference_zone`
- `display_zone`
- `tail_nonref_hold_zone`

### Phase 5: Late role resolution

Move role assignment behind family/zone inference.

### Phase 6: Figure/table validation upgrade

Replace nearest-first assumptions with validation-first matching using anchor/zone/family evidence.

### Phase 7: Health and diagnostics convergence

Expose anchor/zone/family confidence and unresolved holds clearly in health output.

---

## 17. Risks and mitigations

### 17.1 Risk: body family incorrectly learned from complex pages

Mitigation:

- sample multiple middle pages
- use dominant repeated family, not single-block certainty
- reject samples from obvious display-heavy or tail-heavy pages

### 17.2 Risk: legends/captions absorbed into body

Mitigation:

- mandatory family partition before body assignment
- body is not default sink
- use display/media adjacency and legend family closure

### 17.3 Risk: generic tail blocks contaminate references

Mitigation:

- reference-first tail parsing
- reference-local reading-order policy
- weak typing for generic non-reference tail content when needed

### 17.4 Risk: frontmatter complexity is underestimated

Mitigation:

- source-backed localization remains canonical
- frontmatter side/support regions are explicit
- abstract and introduction transition remains boundary-band based, not a keyword cut
- actual title/authors localization must be allowed to occur after a suppressed preproof cover page

### 17.5 Risk: preproof page contaminates frontmatter localization

Mitigation:

- preserve early preproof suppression / exclusion as a dedicated constraint stage

---

## 18. Acceptance criteria

The redesign is successful when:

1. Raw OCR labels are no longer the initial semantic truth source.
2. Title/authors/doi localization is source-backed and does not fall back to OCR invention when misaligned.
3. Body baseline is learned from middle-page dominant families, not page-1 assumptions.
4. `reference_zone` is protected even when its local reading order diverges from the prior body order.
5. Legends/captions/headings are not defaulted into body simply because they occur in body pages.
6. Figure/table matching can surface `HOLD` instead of forcing low-confidence attachment.
7. Health output can explain which anchors/zones/families were accepted, held, or weak.

---

## 19. Final direction

The new OCR architecture should be understood as:

```text
source-backed frontmatter truth
+ middle-page body family anchor
+ reference-first tail protection
+ zone-aware family partition
+ validation-first object matching
```

not as:

```text
raw OCR role
+ local regex rules
+ repeated rescue/demotion/promotion
```

The objective is not to perfectly classify every block immediately. The objective is to let stable evidence reveal the document gradually, while preserving external compatibility and reducing the need for late-stage rescue logic.
