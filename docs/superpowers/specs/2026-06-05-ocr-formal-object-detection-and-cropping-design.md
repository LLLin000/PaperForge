# OCR Formal Object Detection And Cropping Design

> **Status:** Proposed
> **Date:** 2026-06-05
> **Audience:** Maintainers, contributors, agentic implementers

## 1. Goal

Stabilize PaperForge OCR by separating four concerns that are currently entangled:

1. frontmatter understanding
2. formal object detection
3. object matching and continuation handling
4. asset cropping and render consumption

The immediate trigger is that the current structured pipeline still misclassifies:

- paper title vs ordinary headings
- abstract vs body
- body mentions of `Figure N` vs formal figure legends
- table continuation pages vs distinct formal tables

and recently regressed figure/table asset cropping by mixing OCR image coordinates with PDF coordinates.

This design defines the contracts that should govern these layers so that:

- formal figures and tables are detected conservatively
- body mentions do not become legends
- continuation tables remain one formal table
- legend-only figures remain legend-only
- asset cropping is stable and independent from object identity logic

## 2. Problem Statement

The current OCR pipeline has three architecture problems:

### 2.1 Role leakage

Generic role heuristics are still too permissive:

- unnumbered `paragraph_title` can become `paper_title`
- generic `text` can become a heading
- any `Figure/Fig`-prefixed text can become `figure_caption`

These mistakes then pollute metadata resolution, rendering, health, and indexing.

### 2.2 Formal object confusion

The current figure/table pipeline does not strongly separate:

- formal legends
- body mentions of figures/tables
- candidate legends
- continuation segments
- orphan assets

As a result:

- `Figure 3 shows ...` in body prose can become the formal legend for Figure 3
- a legend-only figure can later be assigned an unrelated orphan asset
- `Table 6 (Continued)` can become a separate formal table object

### 2.3 Cropping-layer regression

The current `assets/` object extraction path introduced a coordinate-system regression:

- OCR block bboxes are in OCR rendered page-image coordinates
- new object extraction treated them as PDF coordinates

The old `images/blocks/` path was stable because it:

1. rendered a page image into OCR coordinates
2. cropped from that page image with OCR bbox coordinates

The new object layer must preserve that stability.

## 3. Design Principles

1. Frontmatter is a dedicated regime, not generic body parsing.
2. Formal object identity must be decided before rendering.
3. Matching decides identity and bbox ownership; cropping only materializes assets.
4. `legend_only` means no asset is assigned.
5. `orphan_asset` means no formal legend claims that asset.
6. Table continuation is one formal table with multiple physical segments.
7. `assets/` is structured truth; `images/` remains compatibility only.
8. Search/index should consume only stabilized formal roles, not raw ambiguous roles.

## 4. Layer Contracts

## 4.1 Frontmatter Analyzer Layer

Responsibility:

- detect title, authors, affiliations, doi, abstract, and journal furniture on the first page
- lock those blocks so they do not later compete for body or heading roles

Inputs:

- OCR raw labels such as `doc_title`, `abstract`, `paragraph_title`, `text`, `header`
- block order and geometry
- source metadata from `raw/source_metadata.json`

Outputs:

- frontmatter object assignments
- confidence and evidence traces
- structured roles for:
  - `paper_title`
  - `authors`
  - `affiliation`
  - `doi`
  - `journal_meta`
  - `abstract_heading`
  - `abstract_body`
  - `frontmatter_noise`

Rules:

- `paper_title` should normally be unique and page-1-only
- OCR `doc_title` should have very high priority
- source metadata should validate and localize, not blindly overwrite block identity
- locked frontmatter blocks should not re-enter generic role inference

## 4.2 Heading Analysis Layer

Responsibility:

- determine the paper’s heading hierarchy globally

Inputs:

- high-confidence OCR heading priors
- numbered heading patterns
- block geometry and alignment
- page-local layout

Outputs:

- `section_heading`
- `subsection_heading`
- `reference_heading`
- or non-heading fallback

Rules:

- generic `text -> heading` promotion must be extremely strict
- long prose-like blocks must never become headings
- heading decisions should use a document-level profile:
  - typical numbering
  - typical width/height
  - left alignment / indentation
  - typical position relative to columns

## 4.3 Formal Figure Detection Layer

Responsibility:

- detect formal figure legends separately from body references

Required categories:

- `formal_figure_legend`
- `candidate_figure_legend`
- `body_figure_mention`
- `figure_asset`
- `orphan_media`

Rules:

### Formal legend

High-confidence formal figure legends include:

- OCR raw `figure_title`
- caption blocks that match formal legend patterns such as `Figure 1`, `Fig. 1`, `FIGURE 4`

But explicit exclusions are required:

- body sentences such as `Figure 3 shows ...`, `Figure 2 illustrates ...`
- inline references such as `as shown in Figure 2`

### Candidate legend

Candidate legends may be admitted when all of these align:

- typography and geometry match known figure legend profile
- strong adjacency to a figure asset or asset cluster
- not shaped like running body prose
- no stronger competing formal legend nearby

Candidate legends must not silently promote to formal legends without sufficient evidence.

## 4.4 Figure Matching Layer

Responsibility:

- map each formal figure legend to zero or more asset blocks

Inputs:

- formal legends
- candidate legends
- clustered figure assets

Outputs:

- `matched_figure`
- `low_confidence_figure`
- `legend_only_figure`
- `orphan_asset`

Rules:

- matching should use page relationship, geometry, clustering, and numbering consistency
- body mentions must never claim assets
- a `legend_only_figure` must remain assetless
- unmatched assets remain orphan assets

Disallowed behavior:

- object-writing layer assigning a random orphan asset to a `legend_only_figure`

## 4.5 Table Detection And Continuation Layer

Responsibility:

- detect formal tables
- merge continuation pages
- preserve image-first truth semantics

Required concepts:

- `formal_table_caption`
- `candidate_table_caption`
- `table_asset_segment`
- `table_continuation`
- `orphan_table_asset`

Rules:

- `Table 6` and `Table 6 (Continued)` are one formal table object
- one formal table may have multiple asset segments
- `fulltext.md` should reference the table object, not inline OCR table HTML
- assistive OCR table text belongs in object notes only

## 4.6 Asset Cropping Layer

Responsibility:

- materialize selected bbox sets into image assets

Inputs:

- page number
- bbox or bbox cluster chosen by the matching layer
- OCR page coordinate system

Rules:

- cropping must use OCR page-image coordinates, not raw PDF coordinates
- preferred order:
  1. existing cached OCR page image
  2. render PDF page into OCR page dimensions, then crop
  3. direct PDF clipping only as a last-resort fallback

Important boundary:

- cropping does not decide which bbox is correct
- cropping does not assign or change formal object identity

## 4.7 Object Note Layer

Responsibility:

- render figure and table object notes from already-decided formal objects

Figure note contract:

- `# Figure <formal_number>`
- image
- `## Legend`
- legend text
- optional page / confidence / warning metadata

Table note contract:

- `# Table <formal_number>`
- one or more table images
- `## Caption`
- optional continuation info
- optional assistive OCR section

Rules:

- titles should use formal numbers, not sequential inventory indexes
- continuation segments should not create new displayed formal numbers

## 4.8 Render Layer

Responsibility:

- assemble `fulltext.md` from stabilized structured roles and formal objects

Rules:

- `fulltext.md` should contain:
  - title
  - metadata
  - abstract
  - body
  - anchored figure/table references
  - references
- tables should be represented by object references or image embeds, not inline HTML
- render should not reinterpret ambiguous raw OCR blocks

## 5. Compatibility Contract

`images/` remains temporarily as compatibility output.

Rules:

- `assets/` is structured truth
- `images/` is compatibility only
- path mapping between `assets/` and `images/` should be explicit in `meta.json`
- future deletion of `images/` requires a separate compatibility migration

## 6. Validation Requirements

The real validation paper is:

- `D:\L\OB\Literature-hub\System\PaperForge\ocr\7C8829BD`

Required real-paper outcomes:

1. abstract is present and isolated
2. title is unique and not polluted by backmatter headings
3. `Figure 3` body prose mention is not used as the formal legend
4. `Figure 4` does not receive an orphan asset fallback
5. `Table 6 (Continued)` remains part of formal Table 6
6. `Table 7` does not drift into `table_009` display numbering
7. `fulltext.md` does not inline raw table HTML
8. asset crops match the old stable page-image crop behavior

## 7. Out Of Scope

This design does not yet specify:

- command-layer search integration
- evidence retrieval API
- plugin UI updates for formal-object inspection

Those should consume the stabilized outputs from this design rather than define them.
