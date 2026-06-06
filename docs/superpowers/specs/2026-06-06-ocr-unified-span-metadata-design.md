# Unified Span Metadata Design

> **Status:** Revised Proposal  
> **Date:** 2026-06-06  
> **Audience:** Maintainers, contributors, agentic implementers

## 1. Goal

Build a persistent, paper-local `span_metadata` system that strengthens OCR role assignment through **cross-validation**, **family discovery**, and **consistency checks**.

`span_metadata` is **not** a replacement for:

- text pattern heuristics
- bbox/page geometry
- raw Paddle labels
- body/backmatter/references regime logic

Instead, it becomes a second vote that:

- boosts or reduces confidence,
- helps distinguish role families that look similar in text but different in typography,
- removes brittle absolute thresholds.

The target is not “font-size-based classification.” The target is **paper-local style reasoning**.

---

## 2. Core Principles

### 2.1 Span is a validator, not a decider

Primary decision path remains:

1. raw label / OCR prior
2. text morphology
3. geometry / page regime
4. zone ownership

`span_metadata` is only allowed to:

- raise confidence,
- lower confidence,
- nominate a block for second-pass reconsideration.

It must not:

- override a decisive formal text signal by itself,
- create a role from nothing,
- replace boundary logic or ownership logic.

### 2.2 Profiles are learned per paper, never hardcoded globally

No global:

- `font_size >= 14`
- `font_size >= 12 and bold`
- “blue text means heading”
- `page_num >= 8 means backmatter`

All such rules are too brittle across journals.

Instead:

1. first-pass roles are assigned with existing heuristics
2. span profiles are aggregated per role family inside one paper
3. later low-confidence candidates are compared against those local profiles

So the system asks:

- “does this block look like *this paper’s* section headings?”
- not:
- “is this block 14pt bold?”

### 2.3 Profiles are role-family profiles, not only role labels

For OCR, the useful comparisons are often not exact role-to-role, but **family-to-family**:

- title family
- heading family
- backmatter heading family
- body family
- reference family
- caption family
- frontmatter furniture family

So profile storage should support both:

- exact role aggregation
- cross-role family comparison

### 2.4 No absolute page gates

Any rule like:

- `page >= 8`
- `page <= 1`

may exist only as a **weak prior**, never as a hard veto, unless it is logically unavoidable.

For example:

- page-1 frontmatter zoning can be page-1-only
- but backmatter detection must use **relative tail position** or structural boundary, not fixed page numbers

### 2.5 Graceful degradation

If `span_metadata` is missing:

- behavior should remain close to current output
- no role should become impossible to assign

This is especially important for:

- older OCR outputs
- scanned PDFs
- mixed backfill corpora

---

## 3. Unified Span Representation

Every structured block should be able to carry:

```json
{
  "span_metadata": {
    "mean_size": 11.4,
    "max_size": 13.2,
    "font_families": ["TimesNewRomanPS-BoldMT"],
    "is_bold": true,
    "is_italic": false,
    "is_colored": false,
    "dominant_color": 0,
    "line_count": 1,
    "bbox_height": 29,
    "bbox_width": 540
  }
}
```

This is block-level normalized metadata.  
It is not intended to preserve every individual character span forever.

Required block-level features:

- `mean_size`
- `max_size`
- `font_families`
- `is_bold`
- `is_italic`
- `is_colored`
- `dominant_color`
- `line_count`
- `bbox_height`
- `bbox_width`

Optional future additions:

- caps ratio
- center alignment score
- left-indent score
- small-caps heuristic

---

## 4. Profile Quality Model

Profiles should be tagged by confidence band:

| quality    | criteria |
|------------|----------|
| `strong`   | block_count >= 3 and dispersion low and style coherence high |
| `moderate` | block_count >= 3 and dispersion acceptable |
| `weak`     | block_count >= 2 but dispersion high |
| `no_data`  | insufficient span availability |

Rules:

- only `moderate` or `strong` profiles may affect confidence materially
- `weak` profiles may annotate evidence but should not re-rank aggressively
- `no_data` profiles do nothing

---

## 5. Per-Role Span Integration Matrix

This section is the most important operational part of the design.

For each role we define:

- primary signals
- whether span is strong / medium / weak
- what span is allowed to do
- what hardcoded logic must be removed

---

### 5.1 `paper_title`

**Primary signals**

- page-1 title zone
- raw `doc_title`
- top-of-page geometry
- width/centering relative to first-page content

**Span usage level:** medium-to-strong

**Span should do**

- rank title candidates within page 1
- distinguish title family from authors / furniture / running text
- reinforce or weaken a tentative title candidate

**Additional validator**

- fuzzy title similarity against Zotero title

**Span must not do**

- create a title outside the title zone by itself

**Remove / reduce**

- any hidden dependence on fixed font-size thresholds

---

### 5.2 `authors`

**Primary signals**

- first-page author zone
- author-list morphology
- relation to title and affiliations

**Span usage level:** medium

**Span should do**

- separate author line from journal furniture
- support distinction between author block and affiliation block

**Span must not do**

- replace zone logic
- override clear affiliation text patterns

**Important**

- affiliation lines must never retain `authors` role just because they share similar style

---

### 5.3 `affiliation`

**Primary signals**

- first-page affiliation zone
- institution keywords
- superscript markers
- proximity below author zone

**Span usage level:** medium

**Span should do**

- reinforce that affiliation belongs to the same frontmatter family as authors but a distinct subtype
- help distinguish affiliation from body/furniture

**Span must not do**

- dominate institution-text logic

---

### 5.4 `frontmatter_noise`

**Primary signals**

- page-1 regime
- side-column / margin placement
- furniture patterns

**Span usage level:** strong

**Span should do**

- differentiate journal furniture from body-family text
- distinguish:
  - editorial metadata
  - DOI/citation furniture
  - copyright/license blocks
  - keyword/subject blocks

**This role should become more zone+style driven than text driven.**

**Remove / reduce**

- over-reliance on phrase-only matching

---

### 5.5 `section_heading` / `subsection_heading` / `sub_subsection_heading`

**Primary signals**

- numbered heading morphology
- `paragraph_title`
- position and spacing

**Span usage level:** strong

This is the highest-value span target.

**Span should do**

- build a document-local heading family hierarchy
- classify unnumbered heading candidates into level families
- validate numbered headings instead of replacing numbering

**Allowed model**

1. collect high-confidence heading seeds
2. cluster heading families using:
   - size
   - boldness
   - color
   - spacing before/after
   - line shape / bbox height
3. use cluster match to infer heading level for unnumbered papers

**Remove**

- hardcoded:
  - `font_size >= 14`
  - `font_size >= 12 and bold`
as primary heading logic

These may remain only as extremely weak bootstrap hints if necessary.

---

### 5.6 `backmatter_heading`

**Primary signals**

- boundary already crossed
- child heading behavior inside tail region
- local page/spread ownership

**Span usage level:** strong

**Span should do**

- validate that candidate child headings inside backmatter form a coherent family
- distinguish backmatter headings from residual body-like emphasized text

**Critical rule**

After the backmatter boundary, all non-reference headings should be normalized into one backmatter heading family.

So span here is used to support:

- child heading coherence
- heading/body distinction

not to create a parallel heading taxonomy.

---

### 5.7 `backmatter_boundary_heading`

**Primary signals**

- tail-region location
- container-like text
- followed by multiple declaration-like children
- references later in the same region

**Span usage level:** strong

**Span should do**

- help detect that a boundary heading is visually distinct from its children
- support container detection in unnumbered journals

**Must remove**

- hard page cutoff such as `page_num < 8 -> False`

**Replace with**

- relative tail position
- body_end/backmatter_start reconciliation
- container-child-follow-through

This role is a structural boundary helper, not a content bucket.

---

### 5.8 `reference_heading`

**Primary signals**

- explicit references heading
- start of references zone

**Span usage level:** medium

**Span should do**

- validate heading distinctiveness
- help separate it from sibling backmatter headings if styling differs

But the real source of truth here is:

- boundary logic
- subsequent reference-item density

---

### 5.9 `reference_item`

**Primary signals**

- raw `reference_content`
- reference regex
- references zone

**Span usage level:** strong

This is the second-highest-value span target after heading families.

**Span should do**

- build reference-family consistency profile
- up-rank borderline items that match the family
- down-rank regex-only items that look like body text

**Example use**

- distinguish true bibliography entries from body sentences containing citation-like patterns

---

### 5.10 `figure_caption`

**Primary signals**

- formal prefix
- raw `figure_title`
- caption geometry relative to figure candidates
- body-mention veto
- embedded-figure-text veto

**Span usage level:** medium-to-strong

**Span should do**

- distinguish long captions from body paragraphs
- validate candidate caption family
- support second-pass reconsideration for low-confidence caption/body ambiguity

**Span must not do**

- override the formal-legend validation contract by itself

---

### 5.11 `table_caption`

**Primary signals**

- formal prefix
- table geometry

**Span usage level:** medium

**Span should do**

- support caption-vs-body disambiguation
- reinforce consistency among table captions

---

### 5.12 `body_paragraph`

**Primary signals**

- fallback when no stronger role wins
- body zone / section flow

**Span usage level:** weak-to-medium

**Span should do**

- support a second-pass mismatch queue
- identify when a block looks much more like heading/caption/reference than body

**Span must not do**

- directly create body role

This remains a fallback role, not a style-discovered family leader.

---

### 5.13 `noise` (`header` / `footer` / `number`)

**Primary signals**

- raw labels
- page-edge geometry

**Span usage level:** medium

**Span should do**

- cross-page consistency checks
- flag anomalous header/footer classifications

This is useful, but lower priority than heading/reference/frontmatter work.

---

## 6. Shared Infrastructure

### 6.1 `ocr_profiles.py`

Move shared span/style logic out of `ocr_render.py` into:

- `paperforge/worker/ocr_profiles.py`

This module should own:

- block-level style extraction
- family/profile aggregation
- profile-quality scoring
- span cross-validation

### 6.2 Suggested public helpers

```python
def extract_block_span_profile(block: dict) -> dict | None
def build_role_span_profiles(blocks: list[dict]) -> dict
def cross_validate_with_span(block: dict, tentative_role: str, role_profiles: dict) -> dict
def compare_against_role_family(block_profile: dict, role_family_profile: dict) -> dict
```

### 6.3 Second-pass queue

Second pass should be explicit, not implied.

Candidate blocks:

- low-confidence body paragraphs
- low-confidence heading candidates
- low-confidence captions
- regex-only references

The second pass should:

- adjust confidence
- optionally swap role if the current role is weak and alternative family match is strong

But it should never override:

- strong formal text prefix decisions
- tail/references zone boundaries

---

## 7. Data Flow

```text
raw OCR blocks
  -> carry span_metadata into raw blocks
  -> first-pass role assignment
  -> build role/family span profiles
  -> cross-validate low-confidence blocks
  -> write structured blocks with span evidence
  -> write role_span_profiles.json
```

Outputs:

- `blocks.structured.jsonl` includes normalized `span_metadata`
- `role_span_profiles.json` records family/profile summaries

---

## 8. Explicit Risk Removals

These behaviors are considered design defects and should be removed:

1. absolute page gates for backmatter, especially `page >= 8`
2. fixed heading font-size gates such as `>= 14` or `>= 12 bold` as primary rules
3. phrase-only frontmatter/backmatter noise suppression as dominant logic

---

## 9. Acceptance Criteria

- `span_metadata` is preserved through raw and structured layers
- `role_span_profiles.json` exists with profile quality
- heading families are discovered dynamically per paper
- unnumbered heading hierarchy uses family matching, not hardcoded size thresholds
- `backmatter_boundary_heading` no longer depends on absolute page number
- `reference_item` gets family consistency support
- `frontmatter_noise` becomes more zone/style driven than phrase driven
- second-pass cross-validation exists for low-confidence body/caption/heading/reference ambiguity
- zero span data produces near-zero behavior change

