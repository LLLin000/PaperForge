# OCR Real-Paper Regression Ledger

**Date:** 2026-06-10
**Branch:** `ocr-v2`
**Scope:** Real-paper rebuild check against `D:\L\OB\Literature-hub\System\PaperForge\ocr`

---

## 1. Purpose

This document records the current high-value real-paper failures that remain after the anchor-first OCR v2 implementation landed.

The goal is not to restate the architecture. The goal is to identify exactly where the current implementation still violates the architecture when run on real papers.

These regressions were observed after rebuilding the following papers using the current `ocr-v2` code:

- `TSCKAVIS`
- `CAQNW9Q2`
- `A8E7SRVS`
- `DWQQK2YB`
- `M36WA39N`

---

## 2. Rebuild evidence

Rebuild command result:

```text
run_derived_rebuild_for_keys(...) -> {'rebuild_count': 5}
```

Sources verified from `meta.json`:

- `TSCKAVIS` -> `54TEMR6D\Stegen和Carmeliet - 2024 - Metabolic regulation of skeletal cell fate and function.pdf`
- `CAQNW9Q2` -> `ABQK8XPM\Buckland-Wright - 1994 - Quantitative radiography of osteoarthritis..pdf`
- `A8E7SRVS` -> `JATXULKN\Caffard 等 - 2023 - High Acromial Slope and Low Acromiohumeral Distance Increase the Risk of Retear of the Supraspinatus.pdf`
- `DWQQK2YB` -> `E2P2XT7J\Yoo 等 - 2020 - Magnetoresponsive stem cell spheroid-based cartilage recovery platform utilizing electromagnetic fie.pdf`
- `M36WA39N` -> `FPJ6P2GV\Jia 等 - 2022 - Mechanical Stimulation Protects Against Chondrocyte Pyroptosis Through Irisin-Induced Suppression of.pdf`

Observed health summary:

- `TSCKAVIS` -> `overall=red`
- `CAQNW9Q2` -> `overall=red`
- `A8E7SRVS` -> `overall=red`
- `DWQQK2YB` -> `overall=yellow`
- `M36WA39N` -> `overall=yellow`

---

## 3. Main failure classes

### 3.1 Frontmatter side/main separation is not authoritative enough

Real observed symptom:

- author lines
- received/accepted/published metadata
- copyright text
- correspondence blocks
- edited/reviewed/citation blocks
- keywords / highlight bullets

still enter the body rendering stream as `body_paragraph` or equivalent renderable prose.

This means the following intended chain is still incomplete:

```text
source metadata truth
-> frontmatter localization
-> frontmatter_main/frontmatter_side zoning
-> exclusion from body flow
```

### 3.2 Reference items are more mature than reference-zone authority

Real observed symptom:

- many papers produce many `reference_item` blocks
- but `reference_family_anchor` often remains `HOLD`
- and `reference_zone` often remains `REJECT`
- some reference-like blocks still show `zone = body_zone`

This means the implementation is often succeeding at local tail item recognition before it succeeds at stable zone-level tail authority.

### 3.3 Family partition exists, but final body-flow protection is incomplete

Real observed symptom:

- figure titles / legends / table captions / boxed support text / tail headings
  still sometimes survive as body-flow output
- non-body blocks can still be rendered or preserved as body prose even when their style family already diverges

This means the following intended chain is also incomplete:

```text
zone
-> family partition
-> final role resolution
-> render policy
```

The family artifact exists, but it is not yet strong enough as the final authority.

---

## 4. Paper-specific findings

### 4.1 `TSCKAVIS`

**What improved**

- title / journal / doi are localized correctly
- `Key points` is rendered as a callout block
- main body is largely readable

**What is still wrong**

- table-related display content is still leaking into heading/body flow
- `Table 1 | ...` appears as a heading-like body insertion
- `Table 1 (continued)` also appears as heading-like content before rendered table objects

**Likely architecture miss**

- `display_zone` and `table_caption_like` are not strong enough to prevent heading/body render behavior

### 4.2 `CAQNW9Q2`

**What improved**

- body is readable enough for an old single-column paper
- references are largely recoverable as `reference_item`

**What is still wrong**

- heading preservation is weak (`Standard radiography` and similar section markers are not stably preserved as headings)
- health still reports `reference_family_anchor = HOLD`, `reference_zone = REJECT`

**Likely architecture miss**

- old-paper heading family is not closing strongly enough
- reference-zone authority is weaker than item-level detection

### 4.3 `A8E7SRVS`

**What is still wrong**

- page-1 author line renders as body text
- page-1 journal furniture / copyright / conflict statement leak into body flow
- early frontmatter/body transition is not cut cleanly
- `Introduction` begins only after multiple leaked frontmatter paragraphs

**Why this matters**

This is the clearest real-paper proof that frontmatter complexity is still underestimated in the live authority path.

**Likely architecture miss**

- `frontmatter_side_zone` is not being enforced strongly enough against body rendering
- frontmatter-side/support blocks still inherit body authority too easily

### 4.4 `DWQQK2YB`

**What improved**

- preproof cover is no longer dumped directly into final content as one giant page-1 body region
- many references do resolve into `reference_item`

**What is still wrong**

- page-2 author/correspondence/highlight bullets still leak into the body stream
- tail non-reference blocks (`Conflict of Interest`, acknowledgements-style content) still render like body paragraphs
- many reference-like blocks still appear with `zone = body_zone`

**Likely architecture miss**

- preproof suppression exists, but post-preproof frontmatter relocation is still weak
- `reference_zone` authority still lags behind local item detection

### 4.5 `M36WA39N`

**What improved**

- Frontiers-style numbered body headings and many figure captions are better than earlier iterations
- main body is broadly readable

**What is still wrong**

- page-1 editorial furniture (`Edited by`, `Reviewed by`, `Correspondence`, `Citation`) still renders as body prose
- tail headings like `ETHICS STATEMENT` and `AUTHOR CONTRIBUTIONS` collapse back into body paragraphs
- references exist but still often do not own zone authority strongly enough

**Likely architecture miss**

- `frontmatter_side_zone` is still not final-authoritative
- `tail_nonref_hold_zone` is not protecting non-reference tail headings strongly enough

---

## 5. Mapping failures back to the design

### 5.1 Spec area: source-backed frontmatter truth

**Design intent**

Source metadata is canonical and OCR only localizes/aligns it.

**Current gap**

Canonical source truth is largely respected, but the downstream zoning and exclusion path is not strong enough. The issue is no longer primarily metadata truth. The issue is authority transfer from localized frontmatter evidence into final rendering.

### 5.2 Spec area: zone is not role

**Design intent**

`body_zone` is not equivalent to `body_paragraph`.

**Current gap**

In real papers, many frontmatter-side and tail-side blocks are still effectively treated as body in the rendered output, even when their zone/family artifacts suggest otherwise.

### 5.3 Spec area: reference-first tail parsing

**Design intent**

Reference-zone integrity should be protected even if generic backmatter remains weakly typed.

**Current gap**

The implementation often reaches `reference_item` without fully closing `reference_zone`. This means local reference recognition is ahead of zone-level authority.

### 5.4 Spec area: family partition before role resolution

**Design intent**

Family partition should keep legends, table captions, support blocks, and tail headings out of default body flow.

**Current gap**

Family partition exists as an artifact, but body-flow rendering and final semantic outcomes are still not consistently subordinate to it.

---

## 6. Highest-value next fixes

### Priority 1: frontmatter side zoning must become authoritative

Target symptoms:

- `A8E7SRVS` page-1 authors / metadata leakage
- `DWQQK2YB` page-2 author / highlights / correspondence leakage
- `M36WA39N` Frontiers editorial furniture leakage

### Priority 2: reference-zone closure must catch up to reference-item detection

Target symptoms:

- `reference_item` present while `reference_zone` stays weak or rejected
- reference-like blocks remaining in `body_zone`

### Priority 3: tail non-reference headings/support blocks must stop collapsing to body

Target symptoms:

- `ETHICS STATEMENT`
- `AUTHOR CONTRIBUTIONS`
- acknowledgements / conflict / supplementary-material headers

### Priority 4: display/table insertions must stop behaving like body headings

Target symptoms:

- `TSCKAVIS` table-heading leakage

---

## 7. Recovery target

This recovery pass should not aim to "improve OCR generally".

It should aim to make these five papers pass these practical conditions:

1. frontmatter-side blocks no longer render as ordinary body paragraphs
2. reference zones become accepted where reference items are already stable
3. tail non-reference headings are no longer collapsed into body paragraphs
4. display/table caption content does not appear as ordinary body headings

If those four outcomes are achieved on the five-paper set, the current anchor-first design will have crossed from promising architecture into reliable real-paper behavior.
