# OCR Structured Pipeline Design

> **Status:** Proposed
> **Date:** 2026-06-04
> **Audience:** Maintainers, contributors, agentic implementers

## 1. Goal

Redesign PaperForge OCR from a single render-heavy workflow into a layered paper parsing pipeline that is:

- cacheable
- rebuildable
- verifiable
- degradable
- version-aware

The central architectural move is:

- `result.json` becomes the expensive raw truth
- all semantic structure, assets, render output, and health reports become derived artifacts
- `paperforge ocr redo` means full-paper rerun using the current pipeline and current OCR model

This design keeps `zotero_key` as the canonical paper identifier and keeps all OCR artifacts under one paper-local directory.

## 2. Why The Current Design Is Not Enough

The current OCR worker still compresses too many responsibilities into one path:

- OCR raw ingestion
- block filtering
- role inference
- reading-order repair
- figure/table binding
- metadata scraping
- asset cropping
- markdown rendering

This makes `fulltext.md` appear more important than it should be and forces future improvements to accumulate inside render-time heuristics.

The core gap is not only reading order. The larger gap is that the system lacks a stable structured paper object layer between OCR raw output and Obsidian render output.

## 3. Design Principles

1. `zotero_key` remains the only canonical paper key.
2. All OCR artifacts stay under `System/PaperForge/ocr/<zotero_key>/`.
3. Expensive layers run rarely; derived layers rebuild freely.
4. `result.json` is the expensive fact source.
5. `fulltext.md` is never a fact source.
6. Metadata is multi-source and confidence-scored.
7. Figure and table objects are first-class outputs.
8. Table image is the truth source; parsed text is assistive.
9. `ocr_status` reflects OCR/raw execution success, not semantic quality.
10. Semantic quality is reported separately in health outputs.
11. User-facing redo means full-paper rerun, not partial rebuild.
12. Derived-version drift should be mostly user-invisible.

## 4. Canonical Directory Layout

All artifacts for one paper live under:

`System/PaperForge/ocr/<zotero_key>/`

Proposed layout:

```text
System/PaperForge/ocr/<zotero_key>/
  meta.json
  fulltext.md
  json/
    result.json
  raw/
    raw_meta.json
    source_metadata.json
  canonical/
    blocks.raw.jsonl
  structure/
    blocks.structured.jsonl
    figure_inventory.json
    table_inventory.json
  metadata/
    resolved_metadata.json
  assets/
    figures/
      figure_001.jpg
    tables/
      table_001.jpg
    orphans/
      orphan_001.jpg
  render/
    fulltext.md
    figures/
      figure_001.md
    tables/
      table_001.md
  health/
    ocr_health.json
```

Compatibility contract during migration:

- keep top-level `meta.json`
- keep top-level `fulltext.md`
- keep `json/result.json`
- allow new consumers to read the layered artifacts
- allow old consumers to keep working until migrated

## 5. Layer Model

### 5.1 Layer 0: Source Input

Responsibility:

- preserve paper identity and upstream metadata from Zotero / Better BibTeX
- preserve resolved PDF path and provenance

Artifact:

- `raw/source_metadata.json`

Example fields:

```json
{
  "zotero_key": "ABCD1234",
  "title": "Paper title",
  "authors": ["A", "B"],
  "year": 2024,
  "journal": "Journal",
  "doi": "10.xxxx/xxxx",
  "pdf_path": "D:/...",
  "bbt_citekey": "smith2024paper",
  "source": "zotero_bbt"
}
```

### 5.2 Layer 1: OCR Raw

Responsibility:

- preserve OCR provider output exactly enough to support full downstream rebuild

Artifacts:

- `json/result.json`
- `raw/raw_meta.json`

Rules:

- do not treat `fulltext.md` as OCR truth
- do not require rerun when only downstream structure changes

### 5.3 Layer 2: Canonical Blocks

Responsibility:

- flatten OCR raw output into stable page-local block records
- preserve all blocks, including noise and uncertain blocks

Artifact:

- `canonical/blocks.raw.jsonl`

Each block record should preserve at least:

```json
{
  "paper_id": "ABCD1234",
  "page": 4,
  "block_id": "p4_b32",
  "raw_label": "text",
  "raw_order": 32,
  "bbox": [100, 230, 900, 320],
  "text": "Figure 2. ...",
  "page_width": 1200,
  "page_height": 1700,
  "source": "ocr_raw"
}
```

### 5.4 Layer 3: Structured Blocks

Responsibility:

- assign structural roles
- preserve uncertainty and evidence
- never delete blocks merely because they should not be rendered

Artifact:

- `structure/blocks.structured.jsonl`

Role taxonomy should support at least:

- `paper_title`
- `authors`
- `affiliation`
- `journal_meta`
- `doi`
- `abstract_heading`
- `abstract_body`
- `keywords`
- `section_heading`
- `subsection_heading`
- `body_paragraph`
- `figure_caption`
- `figure_asset`
- `figure_inner_text`
- `table_caption`
- `table_asset`
- `table_inner_text`
- `formula`
- `reference_heading`
- `reference_item`
- `page_header`
- `page_footer`
- `frontmatter_noise`
- `noise`
- `unknown`

Each structured block should include:

- `role`
- `role_confidence`
- `evidence`
- `render_default`
- `index_default`

### 5.5 Layer 4: Metadata Resolver

Responsibility:

- preserve all candidate metadata sources
- choose resolved values with confidence
- never silently discard OCR/frontmatter candidates

Artifact:

- `metadata/resolved_metadata.json`

Priority order:

1. Zotero / Better BibTeX
2. external structured sources if later added
3. PDF embedded metadata
4. OCR frontmatter
5. OCR fulltext regex candidates

Important rule:

- OCR should not casually override Zotero title/authors
- OCR candidates remain preserved as alternates and validation evidence

Example shape:

```json
{
  "title": {
    "value": "Paper title",
    "source": "zotero",
    "confidence": 0.99,
    "alternatives": [
      {
        "value": "Paper Title",
        "source": "ocr_frontmatter",
        "confidence": 0.83
      }
    ]
  },
  "authors": {
    "value": ["A", "B", "C"],
    "source": "zotero",
    "confidence": 0.99,
    "alternatives": [
      {
        "value": ["A", "B", "C"],
        "source": "ocr_frontmatter",
        "confidence": 0.67
      }
    ]
  },
  "doi": {
    "value": "10.xxxx/xxxx",
    "source": "zotero",
    "confidence": 0.99
  },
  "raw_frontmatter": {
    "author_block": "...",
    "affiliation_block": "...",
    "correspondence": "...",
    "published_date": "..."
  }
}
```

### 5.6 Layer 5: Figure/Table Objects

Responsibility:

- turn detected media into first-class paper objects
- separate formal objects from orphan media

Artifacts:

- `structure/figure_inventory.json`
- `structure/table_inventory.json`
- `assets/figures/*.jpg`
- `assets/tables/*.jpg`
- `assets/orphans/*.jpg`
- `render/figures/*.md`
- `render/tables/*.md`

Figure object rules:

- official figure count is based on formal legend count
- unmatched formal legends may still produce `legend-only` figure objects
- orphan media does not enter the formal figure list

Table object rules:

- table image is the truth source
- parsed OCR text is assistive only
- `fulltext.md` should not expand low-confidence parsed tables inline
- prefer a callout or wikilink to the table object

### 5.7 Layer 6: Render

Responsibility:

- produce user-facing Obsidian markdown from structured objects only

Artifacts:

- `render/fulltext.md`
- compatibility mirror at top-level `fulltext.md`

Render rules:

- renderer consumes structured blocks, resolved metadata, figure objects, table objects
- renderer does not perform primary semantic inference
- renderer may decide how to display low-confidence artifacts, but not what they are

### 5.8 Layer 7: Health

Responsibility:

- report structural quality and parse confidence

Artifact:

- `health/ocr_health.json`

Health is independent of raw OCR success.

### 5.9 Layer 8: Version / Rebuild

Responsibility:

- track raw truth version
- track derived artifact version
- let sync and redo make correct decisions

## 6. Version Model

The design requires two version families.

### 6.1 Raw Version

Raw version governs whether OCR raw truth is outdated.

Fields should include at least:

- `ocr_provider`
- `ocr_model`
- `ocr_raw_schema_version`
- `pdf_fingerprint`
- `result_json_hash`

Example:

```json
{
  "raw_version": {
    "ocr_provider": "PaddleOCR",
    "ocr_model": "PaddleOCR-VL-1.6",
    "ocr_raw_schema_version": "1.0.0",
    "pdf_fingerprint": "sha256:...",
    "result_json_hash": "sha256:..."
  }
}
```

### 6.2 Derived Version

Derived version governs whether rebuildable outputs are stale.

Fields should include at least:

- `canonical_block_version`
- `structure_version`
- `metadata_resolver_version`
- `asset_extractor_version`
- `renderer_version`
- `doctor_version`

Example:

```json
{
  "derived_version": {
    "canonical_block_version": "1.0.0",
    "structure_version": "1.0.0",
    "metadata_resolver_version": "1.0.0",
    "asset_extractor_version": "1.0.0",
    "renderer_version": "2.0.0",
    "doctor_version": "1.0.0"
  }
}
```

## 7. Status Model

`ocr_status` should remain about raw OCR execution state, not downstream semantic quality.

Allowed interpretation:

- `pending`: raw OCR not completed
- `queued` / `running`: raw OCR active
- `done`: raw OCR succeeded and minimum raw contract exists
- `done_incomplete`: raw contract broken
- `blocked` / `error` / `nopdf`: raw execution issues

Health contract:

- `health/ocr_health.json` carries semantic quality
- overall quality may be `green`, `yellow`, or `red`
- `red` does not necessarily mean `ocr_status != done`

## 8. OCR And Redo Command Semantics

The spec should align with the current CLI structure instead of inventing a parallel command family.

### 8.1 User-Facing Commands

- `paperforge ocr`
- `paperforge ocr redo`
- `paperforge ocr doctor`

### 8.2 `paperforge ocr`

Meaning:

- process normal OCR queue
- for selected papers, run the full pipeline
- raw OCR if needed
- derived rebuilds as needed

The user does not need to understand downstream rebuild stages.

### 8.3 `paperforge ocr redo`

Meaning:

- full-paper redo for notes marked `ocr_redo: true`
- clear existing raw and derived OCR artifacts for those papers
- rerun the entire OCR pipeline
- use the current configured OCR model by default

Redo does not mean “partial rebuild”.
Redo means “do the whole OCR pipeline again for this paper”.

### 8.4 `paperforge ocr doctor`

Meaning:

- diagnose configuration/runtime health
- no paper mutation

### 8.5 Internal Rebuild Stages

Internally, the OCR engine may be split into stages such as:

- raw ingest
- block rebuild
- structure rebuild
- metadata resolve
- asset rebuild
- render rebuild
- health rebuild

But these are implementation details or maintainer capabilities, not the main user-facing redo semantics.

## 9. Sync Integration Contract

Sync should become version-aware.

### 9.1 Derived Drift

If derived versions are stale:

- sync should finish quickly
- sync should mark the paper as needing derived rebuild
- sync may trigger render/derived rebuild asynchronously or as a follow-up task
- sync completion should not be blocked on slow downstream rebuilds

### 9.2 Raw Drift

If raw version is stale:

- do not auto-rerun OCR during sync
- surface this in the redo panel as informational upgrade opportunity
- user decides whether to mark `ocr_redo: true`

### 9.3 Redo Panel Meaning

The redo panel should show:

- papers already marked `ocr_redo: true`
- papers whose raw output is from an older OCR model/version

But execution still goes through `paperforge ocr redo`.

## 10. Figure Strategy

Figure extraction should be centered on a formal figure inventory, not only on image crops.

### 10.1 Formal Figure Definition

Formal figures are anchored by formal legends, not by raw image count.

Accepted examples include patterns like:

- `Figure 1`
- `Fig. 1`
- `Extended Data Fig. 1`
- `Supplementary Fig. S1`

But text rules alone are not enough.

### 10.2 Figure Detection Inputs

Legend detection should combine:

- text pattern
- OCR raw label prior
- page geometry
- local media adjacency
- numbering continuity
- section compatibility
- neighboring block context

### 10.3 Matching Strategy

Matching should be caption-first:

1. detect formal legend candidates
2. build media candidates
3. cluster media if needed
4. score caption-to-asset pairs
5. choose globally consistent matches
6. degrade to `legend-only` when not reliable

### 10.4 Figure Inventory Shape

`structure/figure_inventory.json` should support:

```json
{
  "figure_legends": [],
  "figure_assets": [],
  "matched_figures": [],
  "unmatched_legends": [],
  "unmatched_assets": []
}
```

### 10.5 Figure Confidence

Each figure match should record:

- same-page / adjacent-page evidence
- overlap evidence
- distance evidence
- section compatibility
- multi-panel clustering
- rejection flags

Low-confidence matches should be preserved with warning, not silently promoted.

## 11. Table Strategy

Tables should be treated differently from body text and slightly differently from figures.

### 11.1 Truth Source

Primary truth:

- table image crop

Secondary assistive source:

- OCR text
- parsed table markdown

### 11.2 Render Policy

Default `fulltext.md` behavior:

- do not expand table body inline by default
- render a callout or wikilink to the table object
- keep parsed OCR available in `render/tables/table_001.md`

This avoids polluting paper body text with low-confidence table transcription while still giving text-only agents something to read.

## 12. Health Contract

`health/ocr_health.json` should report content quality metrics such as:

- `page_count`
- `blocks_count`
- `abstract_found`
- `references_found`
- `figure_caption_count`
- `figure_asset_count`
- `table_caption_count`
- `table_asset_count`
- `media_without_caption_count`
- `caption_without_media_count`
- `empty_table_count`
- `page_order_anomaly_score`
- `frontmatter_quality`
- `overall`

Doctor must be able to explain:

- missing figures
- unmatched legends
- orphan media
- low-confidence matches
- stale derived outputs

## 13. Compatibility Rules

During migration:

1. keep `meta.json` as the compatibility state file
2. add raw and derived version fields there
3. keep `json/result.json`
4. keep top-level `fulltext.md` as compatibility output
5. gradually migrate internal consumers to layered artifacts
6. never require downstream consumers to parse `render_page_blocks()` internals

## 14. Runtime State Additions

`meta.json` should grow to include:

- raw version
- derived version
- created/updated timestamps
- PDF fingerprint
- rebuild-needed markers
- latest health summary snapshot

This allows sync, dashboard, and doctor to reason about the same paper state.

## 15. Out Of Scope For Phase 1

Phase 1 should not fully productize:

- role-separated search indexes
- agent evidence retrieval objects
- full UI/UX redesign of version upgrade interactions

But the spec must record their future interfaces and dependencies.

## 16. Phase Plan

### Phase 1: Structured Pipeline Foundation

Deliver:

- paper-local layered directory structure
- raw/source metadata preservation
- `blocks.raw.jsonl`
- `blocks.structured.jsonl`
- raw/derived version fields
- compatibility-preserving `fulltext.md`

Success condition:

- downstream render no longer depends on raw OCR blocks alone as the only durable intermediate representation

### Phase 2: Metadata + Figure/Table Objects

Deliver:

- `resolved_metadata.json`
- `figure_inventory.json`
- `table_inventory.json`
- figure/table/orphan asset generation
- object markdown for figures and tables

Success condition:

- metadata and media stop being implicit render-time side effects

### Phase 3: Renderer V2 + Health

Deliver:

- renderer driven by structured artifacts
- table callout/wikilink behavior
- figure warning behavior
- `ocr_health.json`

Success condition:

- `fulltext.md` becomes a pure derived render product

### Phase 4: Sync / Version Integration

Deliver:

- sync detection of derived drift
- background or follow-up rebuild trigger contract
- redo panel version hints
- `meta.json` state integration

Success condition:

- stale derived outputs are repaired without forcing user redo

### Phase 5: Search / Agent Interfaces

Deliver:

- role-based indexing design
- evidence object contract
- metadata/caption/table/body retrieval routing

Success condition:

- future agent retrieval can rely on structured OCR artifacts rather than only flat fulltext

## 17. Open Design Notes

These are intentionally deferred, but must be remembered:

1. how plugin/dashboard should display raw-version upgrade opportunities
2. whether sync-triggered derived rebuild is immediate, queued, or batched
3. whether render rebuild should happen inline for single-paper interactions
4. what minimal schema versioning guarantees are needed for long-lived old OCR outputs

## 18. Implementation Constraints

1. Preserve current user-facing command entrypoints.
2. Do not redefine redo as partial rebuild.
3. Avoid introducing a second paper identity system.
4. Keep rebuildable layers deterministic from raw truth.
5. Prefer preserving uncertain structure over deleting it.
6. Keep table image primary.
7. Keep metadata candidates auditable.
8. Maintain backward-compatible top-level outputs until consumers migrate.

## 19. Immediate Next Deliverables

1. implementation plan for Phase 1 only
2. file-by-file target decomposition
3. fixture and regression matrix for structured artifacts
4. version drift rules for sync integration

