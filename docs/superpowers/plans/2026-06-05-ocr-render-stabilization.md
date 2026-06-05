# OCR Render And Structure Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize OCR structured roles, metadata recovery, figure/table object contracts, and `fulltext.md` rendering so legacy backfilled papers such as `D:\L\OB\Literature-hub\System\PaperForge\ocr\7C8829BD` become structurally correct, Obsidian-compatible, and safe to use as the future basis for search/evidence integration.

**Architecture:** This phase closes the remaining gap between the OCR structured pipeline spec and the current implementation. The fix is not “render polish”; it is a coordinated repair of Layer 3 through Layer 6: first-page/frontmatter analysis, global heading profile inference, raw-label-aware role assignment, metadata recovery with multi-source locking, more conservative figure/table detection and matching, render assembly that follows the paper-note contract, and compatibility containment of the old `images/` directory while `assets/` becomes the structured truth. This phase also hardens the producer side of `role-index.json` so later search integration is not built on polluted roles.

**Tech Stack:** Python, pytest, current OCR artifact pipeline, Obsidian-flavored Markdown, legacy OCR corpus at `D:\L\OB\Literature-hub`

---

## Scope

This phase must fix all issues that currently block OCR from being considered stable:

1. first-page/title/authors/abstract/doi/frontmatter role stability
2. heading hierarchy stability across the whole paper
3. reference zone stability
4. figure legend detection and figure-asset matching robustness
5. table detection/matching robustness with image-as-truth rendering
6. object note contracts and asset path compatibility
7. `fulltext.md` assembly and Obsidian math syntax
8. compatibility state drift such as `images/` versus `assets/`
9. health/index outputs that currently inherit polluted roles

This phase does **not** yet implement command-layer OCR evidence search. It prepares the OCR artifacts so that later search integration is worth doing.

## File Structure

This phase should focus on these files and modules:

- `paperforge/worker/ocr_roles.py`
  - Replace permissive fallback rules with raw-label-aware role mapping plus conservative heuristics.
- `paperforge/worker/ocr_metadata.py`
  - Recover metadata from frontmatter and OCR raw blocks without polluting non-metadata roles.
- `paperforge/worker/ocr_figures.py`
  - Harden legend detection and matching with profile-based and multi-signal scoring.
- `paperforge/worker/ocr_tables.py`
  - Harden table caption/asset matching and preserve image-first truth semantics.
- `paperforge/worker/ocr_render.py`
  - Render the intended paper note structure and normalize Obsidian-safe markdown/math.
- `paperforge/worker/ocr_objects.py`
  - Normalize object note contracts, figure/table headings, and asset references.
- `paperforge/worker/ocr_index.py`
  - Ensure role-index buckets reflect stabilized roles and are no longer polluted by frontmatter/body confusion.
- `paperforge/worker/ocr_health.py`
  - Make health reflect corrected abstract/reference/figure/table state.
- `paperforge/worker/ocr.py`
  - Keep orchestration stable while preserving `images/` compatibility and moving structured truth to `assets/`.
- `tests/test_ocr_roles.py`
  - Add global heading/frontmatter/reference regressions.
- `tests/test_ocr_metadata.py`
  - Add frontmatter-locked metadata recovery regressions.
- `tests/test_ocr_figures.py`
  - Add legend detection and matching regressions.
- `tests/test_ocr_tables.py`
  - Add table caption/asset matching regressions.
- `tests/test_ocr_objects.py`
  - Add object note contract and image-path compatibility regressions.
- `tests/test_ocr_rendering.py`
  - Add render assembly and heading-sanity regressions.
- `tests/test_ocr_health.py`
  - Add abstract/reference/figure/table health regressions.
- `tests/test_ocr_index.py`
  - Add role-index pollution regressions.
- `tests/test_ocr_render_stabilization.py`
  - New focused end-to-end structured render fixture tests.

## Real Paper Acceptance Target

The real validation paper for this phase is:

- `D:\L\OB\Literature-hub\System\PaperForge\ocr\7C8829BD`

The phase is not complete until this paper satisfies all of:

1. `paper_title` is assigned only to the real paper title block
2. authors and affiliations are recovered or at least correctly isolated
3. abstract is present in `fulltext.md`
4. `References` and reference items are recognized
5. no bogus heading such as `## 2 mT, f = 15 Hz...`
6. figure/table object notes are correctly formed
7. figure/table links are not dumped blindly at the tail
8. `role-index.json` body bucket no longer begins with frontmatter furniture
9. `meta.json` compatibility state remains coherent

## Failure Modes To Eliminate

1. `doc_title` not recognized
2. `abstract` raw blocks ignored
3. `reference_content` ignored
4. any unnumbered `paragraph_title` promoted to `paper_title`
5. generic `text` blocks promoted to headings too easily
6. metadata resolver consuming polluted role output
7. formal figure legends missed because text rules are too narrow
8. asset/legend mispairing because matching is too greedy
9. table OCR text leaking into `fulltext.md`
10. object note image links breaking in Obsidian
11. `images/` and `assets/` semantics drifting apart invisibly

## Design Contracts For This Phase

### 1. Frontmatter Analyzer Contract

Frontmatter analysis is a dedicated regime, not just generic block classification.

Rules:

- operate on page 1 first, optionally page 2 frontmatter spillover if needed
- detect and lock:
  - title zone
  - author zone
  - affiliation zone
  - journal furniture zone
  - abstract zone
  - doi/journal metadata zone
- once a block is locked as frontmatter object material, it should not re-enter body/heading competition

Signals to combine:

- OCR raw label (`doc_title`, `abstract`, `header`, `paragraph_title`, `text`)
- block geometry
- block order on page
- frontmatter keywords
- source metadata from `raw/source_metadata.json`

### 2. Heading Contract

Heading detection must be globally consistent and conservative.

Rules:

- trust high-confidence OCR heading priors first
- do not broadly promote `text` blocks into headings
- infer a document-specific heading profile from high-confidence headings:
  - numbering patterns
  - block length
  - bbox height/width
  - left alignment / indentation
  - page placement
- only admit low-confidence heading candidates if they fit that profile

Outcomes:

- `section_heading`
- `subsection_heading`
- `reference_heading`
- or not a heading at all

### 3. Metadata Locking Contract

Metadata recovery should use three sources together:

1. source metadata (`raw/source_metadata.json`)
2. frontmatter-analyzer output
3. OCR raw first-page blocks / structured role output

Rules:

- Zotero/source metadata stays primary when present
- OCR/frontmatter provides:
  - block localization
  - alternates
  - fallback when source metadata is sparse
- once title/authors/doi/abstract blocks are locked, they stop affecting unrelated role inference

### 4. Figure Contract

Figure handling remains caption-first, but should not depend on text prefix alone.

Legend detection must split into:

- high-confidence legends:
  - explicit `Figure/Fig/...`
  - OCR raw `figure_title`
  - strong image adjacency
- candidate legends:
  - panel-style text
  - geometry and typography similar to known legends
  - image adjacency

Matching must combine:

- page relationship
- geometry overlap / distance
- above/below caption convention
- panel clustering
- numbering consistency
- one-to-one or one-to-cluster consistency

Outputs must support:

- matched formal figure
- low-confidence match
- legend-only figure
- orphan asset

### 5. Table Contract

Tables remain image-first truth objects.

Rules:

- table image is truth
- OCR/parsed text is assistive only
- `fulltext.md` should not expand assistive OCR table text inline
- caption/asset matching should use multi-signal scoring similar to figures, with table-specific continuation handling

### 6. Asset Compatibility Contract

For now:

- `assets/` is the structured truth
- `images/` remains as compatibility output only

Rules:

- do not delete `images/`
- maintain an explicit mapping between old `images/` and new `assets/`
- update state and object rendering so future migration can flip consumers safely
- do not let new structured code keep treating `images/` as the primary semantic directory

### 7. Object Note Contract

Figure object notes must not use the whole legend as the title.

Correct shape:

- `# Figure 1`
- image embed or image reference
- `## Legend`
- legend text
- page / confidence / optional warning if needed

Table object notes should follow the same pattern:

- `# Table 1`
- image
- `## Caption`
- optional assistive OCR section

## Task 1: Lock All Current Structural Failures In Tests

**Files:**
- Create: `tests/test_ocr_render_stabilization.py`
- Modify: `tests/test_ocr_roles.py`
- Modify: `tests/test_ocr_metadata.py`
- Modify: `tests/test_ocr_figures.py`
- Modify: `tests/test_ocr_tables.py`
- Modify: `tests/test_ocr_objects.py`
- Modify: `tests/test_ocr_rendering.py`
- Modify: `tests/test_ocr_health.py`
- Modify: `tests/test_ocr_index.py`

- [ ] **Step 1: Add a failing frontmatter-locking role test**

Use a fixture modeled on `7C8829BD` page 1 and assert:

- `doc_title -> paper_title`
- `abstract -> abstract_body`
- frontmatter furniture -> `frontmatter_noise`
- author line is not `body_paragraph` by default if clearly inside author zone

- [ ] **Step 2: Add a failing heading-sanity regression**

Assert that a long `text` block such as the current `2 mT, f = 15 Hz...` paragraph cannot become a section heading.

- [ ] **Step 3: Add a failing reference-zone regression**

Assert that `reference_content` blocks after `References` are recognized as `reference_item`.

- [ ] **Step 4: Add a failing metadata recovery regression**

Assert that sparse source metadata plus usable OCR frontmatter still yields:

- title
- authors
- doi

without polluted title alternatives.

- [ ] **Step 5: Add failing figure legend/matching regressions**

Include cases for:

- explicit high-confidence legend
- candidate legend with no `Figure N` prefix but strong geometry
- legend-only degradation
- orphan asset preservation

- [ ] **Step 6: Add failing table object/render regressions**

Assert that `fulltext.md` links to table object notes instead of inlining assistive OCR table text.

- [ ] **Step 7: Add failing object-note contract regressions**

Assert that:

- object note title is `Figure 1` / `Table 1`
- image reference resolves through the current compatibility contract
- legend/caption body is separated from the title

- [ ] **Step 8: Add failing role-index pollution regressions**

Assert that frontmatter furniture does not enter the `body` bucket.

- [ ] **Step 9: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_render_stabilization.py tests/test_ocr_roles.py tests/test_ocr_metadata.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_objects.py tests/test_ocr_rendering.py tests/test_ocr_health.py tests/test_ocr_index.py -q`

Expected: FAIL because current implementation still exhibits the known structural failures.

- [ ] **Step 10: Commit**

```bash
git add tests/test_ocr_render_stabilization.py tests/test_ocr_roles.py tests/test_ocr_metadata.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_objects.py tests/test_ocr_rendering.py tests/test_ocr_health.py tests/test_ocr_index.py
git commit -m "test: lock OCR structure and render stabilization regressions"
```

## Task 2: Rebuild Role Assignment Around Raw Priors And Global Consistency

**Files:**
- Modify: `paperforge/worker/ocr_roles.py`
- Test: `tests/test_ocr_roles.py`

- [ ] **Step 1: Add explicit raw-label mappings**

Add dedicated handling for at least:

- `doc_title -> paper_title`
- `abstract -> abstract_body`
- `reference_content -> reference_item`
- `figure_title -> figure_caption`
- `header/footer/number -> noise`

- [ ] **Step 2: Replace unsafe `paragraph_title` fallback**

Remove the current “unnumbered `paragraph_title` becomes `paper_title`” rule.

Replace it with:

- frontmatter-aware title admission only on page 1
- explicit references heading detection
- conservative heading classification
- `unknown_structural` fallback when not confident

- [ ] **Step 3: Remove permissive `text -> heading` upgrades**

`text` blocks should only be upgraded to headings under very strong constraints:

- short length
- heading-like geometry
- heading-profile compatibility
- not parameter/prose-like

Default should remain `body_paragraph` or `unknown`, not heading.

- [ ] **Step 4: Introduce heading-profile-aware helpers**

Use already-detected high-confidence headings to infer:

- numbering pattern
- max length
- bbox/indent profile

and use that profile to reject bogus heading candidates.

- [ ] **Step 5: Introduce a simple frontmatter-zone helper**

The role layer should know when a block is inside the frontmatter regime so it can prevent leakage into generic body roles.

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_roles.py -q`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add paperforge/worker/ocr_roles.py tests/test_ocr_roles.py
git commit -m "fix: stabilize OCR role assignment with raw priors and heading profiles"
```

## Task 3: Build A Real Frontmatter-Locked Metadata Recovery Path

**Files:**
- Modify: `paperforge/worker/ocr_metadata.py`
- Possibly modify: `paperforge/worker/ocr.py`
- Test: `tests/test_ocr_metadata.py`

- [ ] **Step 1: Expand frontmatter candidate extraction**

Extract and preserve:

- title candidates
- author block candidates
- affiliation block candidates
- doi candidates
- journal/publish metadata candidates
- abstract-zone evidence if helpful

- [ ] **Step 2: Separate OCR block localization from resolved value choice**

Resolved metadata should not just say “what the title is”; it should know which block established it so that render and role stabilization can stay aligned.

- [ ] **Step 3: Add OCR-first fallback when source metadata is sparse**

When Zotero/source metadata is missing:

- use locked OCR/frontmatter candidates
- do not return empty authors/title if strong frontmatter evidence exists

- [ ] **Step 4: Prevent polluted alternates**

Do not admit late-paper headings like `Generative AI statement` as title alternatives.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_metadata.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_metadata.py paperforge/worker/ocr.py tests/test_ocr_metadata.py
git commit -m "fix: recover OCR metadata from frontmatter without role pollution"
```

## Task 4: Harden Figure Legend Detection And Matching

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Possibly modify: `paperforge/worker/ocr_roles.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Split legend detection into formal and candidate paths**

Formal:

- explicit figure-prefix legend
- OCR `figure_title`

Candidate:

- panel-style nearby text
- typography/geometry similar to formal legends
- strong adjacency to media asset

- [ ] **Step 2: Build a legend profile from high-confidence legends**

Use high-confidence legends to infer:

- typical width
- typical relative placement to figure asset
- typical text length/style

- [ ] **Step 3: Improve asset matching from greedy local to multi-signal matching**

In scoring, include:

- same-page / adjacent-page
- vertical relation
- overlap
- horizontal alignment
- candidate asset size
- competing legend proximity
- numbering continuity if present

- [ ] **Step 4: Preserve explicit degradation states**

Support:

- matched figure
- low-confidence matched figure
- legend-only
- orphan asset

Populate inventory fields honestly instead of silently forcing a match.

- [ ] **Step 5: Keep `unmatched_legends` and `unmatched_assets` real**

Do not leave them structurally present but empty by implementation accident.

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_figures.py -q`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add paperforge/worker/ocr_figures.py paperforge/worker/ocr_roles.py tests/test_ocr_figures.py
git commit -m "fix: harden OCR figure legend detection and matching"
```

## Task 5: Harden Table Matching While Keeping Image Truth

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`
- Test: `tests/test_ocr_tables.py`
- Test: `tests/test_ocr_rendering.py`

- [ ] **Step 1: Add multi-signal caption/asset scoring**

Use:

- page relationship
- geometry
- width/height expectations
- continuation handling for `Table N (Continued)`

- [ ] **Step 2: Preserve image-first truth**

Make sure assistive OCR text stays in object notes only and is not expanded inline into `fulltext.md`.

- [ ] **Step 3: Distinguish table object title from caption body**

Do not use the full caption as the object note title.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_tables.py tests/test_ocr_rendering.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_tables.py tests/test_ocr_tables.py tests/test_ocr_rendering.py
git commit -m "fix: stabilize OCR table matching and image-first rendering"
```

## Task 6: Normalize Object Note Contracts And Asset Compatibility

**Files:**
- Modify: `paperforge/worker/ocr_objects.py`
- Modify: `paperforge/worker/ocr.py`
- Test: `tests/test_ocr_objects.py`

- [ ] **Step 1: Normalize figure/table object note headings**

Use:

- `# Figure 1`
- `# Table 1`

not the entire legend/caption text as the note heading.

- [ ] **Step 2: Add explicit section structure inside object notes**

For figures:

- title
- image
- `## Legend`
- optional warning or page/confidence note

For tables:

- title
- image
- `## Caption`
- optional assistive OCR section

- [ ] **Step 3: Preserve `images/` as compatibility only**

Implement or document a clear mapping so that:

- new structured logic prefers `assets/`
- old consumers can still find `images/`

At minimum:

- do not let `meta.assets_path` misrepresent the structured truth silently
- preserve a deterministic path mapping

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_objects.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_objects.py paperforge/worker/ocr.py tests/test_ocr_objects.py
git commit -m "fix: normalize OCR object notes and asset compatibility mapping"
```

## Task 7: Reassemble `fulltext.md` Around The Intended Note Contract

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_render_stabilization.py`
- Test: `tests/test_ocr_rendering.py`

- [ ] **Step 1: Define the render order explicitly**

Render as:

1. `# Title`
2. metadata block
3. `## Abstract`
4. structured body sections
5. anchored figure/table object references
6. references
7. tail matter as appropriate

- [ ] **Step 2: Add heading sanity checks at render time**

Renderer should not blindly emit `##` for absurdly long or obviously paragraph-like headings even if a low-confidence upstream role slipped through.

- [ ] **Step 3: Anchor figure/table links near relevant content**

Use page/caption/section proximity rather than blind tail dumping.

- [ ] **Step 4: Keep page markers compatible**

Do not regress page-marker coverage while filtering frontmatter/body noise.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_render_stabilization.py tests/test_ocr_rendering.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_render.py tests/test_ocr_render_stabilization.py tests/test_ocr_rendering.py
git commit -m "fix: reassemble OCR fulltext around the structured note contract"
```

## Task 8: Normalize Obsidian Math And Protect Health/Index Outputs

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `paperforge/worker/ocr_health.py`
- Modify: `paperforge/worker/ocr_index.py`
- Test: `tests/test_ocr_health.py`
- Test: `tests/test_ocr_index.py`
- Test: `tests/test_ocr_render_stabilization.py`

- [ ] **Step 1: Expand inline math normalization conservatively**

Fix:

- `$ ^{...} $ -> $^{...}$`
- `$ B_{rms} $ -> $B_{rms}$`
- remove padding around inline delimiters

without over-aggressively converting prose to math.

- [ ] **Step 2: Make health consume stabilized roles**

After role fixes:

- `abstract_found` should become true when real abstract exists
- `references_found` should become true when references zone exists

- [ ] **Step 3: Make role-index consume stabilized roles**

Ensure:

- frontmatter furniture does not enter `body`
- references enter `references`
- abstract enters the intended bucket

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_health.py tests/test_ocr_index.py tests/test_ocr_render_stabilization.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_render.py paperforge/worker/ocr_health.py paperforge/worker/ocr_index.py tests/test_ocr_health.py tests/test_ocr_index.py tests/test_ocr_render_stabilization.py
git commit -m "fix: stabilize OCR math, health, and role-index outputs"
```

## Task 9: Real-Corpus Validation On `7C8829BD`

**Files:**
- Verify only

- [ ] **Step 1: Rebuild the real paper with the updated derived pipeline**

Use the current branch code against:

`D:\L\OB\Literature-hub\System\PaperForge\ocr\7C8829BD`

- [ ] **Step 2: Verify structured artifacts directly**

Check:

- `blocks.structured.jsonl`
- `resolved_metadata.json`
- `figure_inventory.json`
- `table_inventory.json`
- `role-index.json`
- `ocr_health.json`

- [ ] **Step 3: Verify rendered artifacts directly**

Check:

- `fulltext.md`
- `render/fulltext.md`
- `render/figures/*.md`
- `render/tables/*.md`

- [ ] **Step 4: Confirm all real-paper acceptance targets**

Especially:

- no bogus long heading promotion
- abstract present
- references recognized
- object note headings are clean
- figure/table placement is reasonable
- `images/` compatibility is preserved while `assets/` remains the structured truth

- [ ] **Step 5: If needed, capture the paper as a durable regression fixture**

This paper should remain the canonical stabilization target before any wider search rollout.

## Task 10: Final Verification

**Files:**
- Verify only

- [ ] **Step 1: Run focused stabilization suite**

Run: `python -m pytest tests/test_ocr_render_stabilization.py tests/test_ocr_roles.py tests/test_ocr_metadata.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_objects.py tests/test_ocr_rendering.py tests/test_ocr_health.py tests/test_ocr_index.py -q`

Expected: PASS

- [ ] **Step 2: Run broader OCR regressions**

Run: `python -m pytest tests/test_ocr_versions.py tests/test_ocr_render_v2.py tests/test_ocr_state_machine.py tests/test_sync.py tests/test_context.py tests/test_selection_sync_pdf.py tests/test_status.py tests/test_ocr_doctor.py tests/e2e/test_ocr_e2e.py tests/test_ocr_redo.py -q`

Expected: PASS

- [ ] **Step 3: Run one real-corpus smoke rebuild**

Expected:

- real paper becomes structurally coherent
- no obvious frontmatter/body/heading corruption remains

- [ ] **Step 4: Commit verification-only fixes if needed**

```bash
git add -A
git commit -m "test: finalize OCR structure and render stabilization"
```

## Risks And Mitigations

1. **Risk: fixing title detection pollutes other headings**
   - Mitigation: restrict `paper_title` to frontmatter/title-zone logic only.

2. **Risk: abstract fallback accidentally captures introduction text**
   - Mitigation: only trust raw `abstract`, frontmatter zone, or strong proximity to title/authors on page 1.

3. **Risk: heading profile becomes too strict and misses real headings**
   - Mitigation: build profile from high-confidence headings and allow low-confidence candidates only when strongly consistent.

4. **Risk: figure candidate legend logic starts swallowing ordinary body text**
   - Mitigation: require agreement among geometry, profile, and media adjacency before promotion.

5. **Risk: object-note cleanup breaks old consumers using `images/`**
   - Mitigation: preserve `images/` as explicit compatibility output for this phase and add deterministic mapping.

6. **Risk: render looks nicer but role-index is still polluted**
   - Mitigation: test `ocr_index.py` directly and gate the phase on clean producer outputs.

7. **Risk: aggressive math normalization corrupts prose**
   - Mitigation: keep normalization conservative and test against real OCR snippets.

8. **Risk: local fixes only work for `7C8829BD`**
   - Mitigation: include synthetic tests plus at least one additional smoke rebuild if time permits.

## Execution Notes

Implementation order matters:

1. roles
2. metadata
3. figures/tables
4. object contracts
5. render
6. health/index
7. real-corpus validation

Do not start search/evidence command integration again until this phase is complete.
