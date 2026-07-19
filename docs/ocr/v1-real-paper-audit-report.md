# OCR v1 Real-Paper Audit Report

> Status: Analysis Only | Not an action plan
> Based on 10 rebuilt papers from Literature-hub vault
> Branch: feat/ocr-structured-pipeline (HEAD ac264e9..7ded399)

---

## 1. Journal Pre-proof Page Detection (DWQQK2YB, affects all Elsevier pre-proof papers)

### Symptom

DWQQK2YB page 1 block 0 has text "Journal Pre-proof" with `raw_label=paragraph_title`. It was assigned `role=paper_title` because it's the first `paragraph_title` on page 1. This poisons everything downstream:

- Real title (block 1) becomes `body_paragraph`
- PII/DOI/Reference info (blocks 4-9) become `body_paragraph`
- Page 1 structure is completely wrong
- Body spine can't find stable pages (pre-proof cover shifts page count)
- Figures pushed into tail section

### Analysis

PaddleOCR correctly detects "Journal Pre-proof" as a text block. The pipeline's page 1 frontmatter logic sees `paragraph_title` at y_top position and assigns `paper_title`. This is a case of "page furniture that looks like a title but isn't."

The fix needs two parts:

**Part A: Pre-proof denial at the seed role level**

Add a pattern in `ocr_roles.py`:

```python
_PREPROOF_MARKER = re.compile(
    r"^(?:journal\s+)?pre-?proof\b",
    re.IGNORECASE,
)
```

In `assign_block_role()`, before any title assignment:

```python
if _PREPROOF_MARKER.match(text.strip()):
    return RoleAssignment(
        role="frontmatter_noise",
        confidence=0.95,
        evidence=["pre-proof journal marker, suppressed as noise"],
    )
```

**Part B: Do NOT delete the page — mark it as skipped**

Deleting the page breaks page numbering (page 2 becomes page 1, breaking all page references). Instead:

- Mark the page's blocks as `frontmatter_noise`
- Exclude them from body spine training
- Body spine anchor detection should ignore page 1 entirely when pre-proof detected
- The rendering already skips `frontmatter_noise` blocks

### What this fixes

- Real title gets `paper_title`
- Real authors on page 1 get `authors`
- Page 1 structure correct
- Body spine uses real content pages
- Figures no longer pushed to tail

### What it doesn't fix

- Author fuzzy matching (separate issue)
- Page 1 Elsevier info blocks (PII/DOI) — they'll be `body_paragraph` but that's acceptable

---

## 2. Author Fuzzy Matching: Initials-to-Fullname Resolution

### Symptom

Several papers show incomplete authors in metadata:

| Paper   | Frontmatter `first_author` | OCR block has full names        |
|---------|---------------------------|---------------------------------|
| DWQQK2YB | A. Yoo                   | Ami Yoo, Gwangjun Go, ...       |
| 4AGGTJE9 | W. H. Marks              | William H. Marks, Tunc Kiymaz.. |

The `first_author` fallback (`_enrich_meta_from_paper_note`) puts the frontmatter value into `meta["authors"]`. But the paper's structured blocks already have the FULL author list with complete names (block 2 in DWQQK2YB: `role=authors`).

### The Problem

The frontmatter `first_author` is a Zotero abbreviation (`A. Yoo`, `W. H. Marks`). The OCR block has full names. No cross-referencing happens. The meta only carries the incomplete frontmatter version.

### The Fix

After the rebuild's `build_structured_blocks()` call, the structured blocks already contain an `authors` block with the full OCR-extracted author list. The `resolve_metadata()` function should:

1. Read the OCR authors from the structured blocks (`role=authors`)
2. Use `first_author` from frontmatter as a **verification signal** (does the OCR list contain a name matching these initials?)
3. If yes, trust the OCR list as it's usually more complete
4. Mark `authors_source = "ocr_blocks_verified_by_first_author"`

**For fuzzy matching of initials:**

```python
_INITIAL_NAME_PATTERN = re.compile(
    r"^(?:[A-Z]\.?\s*)+(?:\s+[A-Z][a-z]+)?$"  # "A. Yoo" or "A Yoo" or "W. H. Marks"
)

def _initials_match(short_name: str, full_name: str) -> bool:
    """Check if 'A. Yoo' matches 'Ami Yoo' or 'W. H. Marks' matches 'William H. Marks'."""
    short_parts = re.findall(r"[A-Z]", short_name.split()[-1])  # last name initials
    full_parts = re.findall(r"[A-Z]", full_name.split()[-1])
    if short_parts != full_parts:
        return False
    # Check given-name initials
    short_given = [w for w in short_name.split()[:-1] if w]
    full_given = [w for w in full_name.split()[:-1] if w]
    if len(short_given) != len(full_given):
        return len(short_given) <= 1 and len(full_given) <= 3  # lenient
    for s, f in zip(short_given, full_given):
        if s[0].upper() != f[0].upper():
            return False
    return True
```

Location: `paperforge/worker/ocr_metadata.py`, in `resolve_metadata()` where authors are compared.

### Acceptance

- "A. Yoo" matches "Ami Yoo" → full OCR list used
- "W. H. Marks" matches "William H. Marks" → full OCR list used
- "G. Go" matches "Gwangjun Go" → full OCR list used
- No match → fall back to `first_author` with `incomplete=True`

---

## 3. Figure Placement (DWQQK2YB "figures all at end")

### Symptom

Figures in DWQQK2YB appear at lines 278-300 of the fulltext, after all body content but before the biography section. The user perceives this as "all at the end."

### Root Cause

Two factors combine:

1. **Pre-proof page (see Section 1)** makes page 1 structure wrong, pushing body spine to offset pages. The body end is detected at page 25 but the figures may be on pages that fall into the tail spread (pages 26-33).

2. **Renderer emits figures at page boundaries**, not inline with captions. This is the fundamental render design: figures are placed at `<!-- page N -->` markers, not embedded at the point of caption reference. When multiple figure pages are consecutive in the tail, they cluster together at the end.

### Why It Happens

The figure inventory is correct (the matched figures ARE the right ones). The issue is rendering placement, not matching. The renderer groups figures by page, and when figure-heavy pages cluster in the tail spread, they appear to be "all at the end."

### Current Design

This is intentional behavior in v1. The renderer does NOT attempt to embed figures inline with their caption reference in the body text. That would require:
- Tracking figure references in the body (inline mentions)  
- Inserting the figure object at the nearest page boundary after the reference
- Managing cross-page figure/caption splits

All of these are v2 features.

### Recommendation

Don't change render behavior in v1. The "figures at end" is a cosmetic issue, not a correctness issue. The figure objects exist, the matching is correct, and the fulltext includes the figure embeds.

---

## 4. M36WA39N — Detailed Analysis

### 4a. Text Cutting ("Concentration of Irisin in Osteoarthritis Rats")

### Symptom

The user shows a paragraph starting with "Concentration of Irisin..." followed by "As shown in Figures 2D,E..." and asks why it's cut.

### Reality

The text is NOT cut in the pipeline. The structured block for page 6 contains:

```
Concentration of Irisin in Osteoarthritis Rats
As shown in Figures 2D,E, the serum level and that of synovial fluid
irisin were increased in all treadmill exercise groups (OAL, OAM, and
OAH) compared with those in the sedentary groups (CG and OAG)
as indicated by ELISA.
```

This is a single `body_paragraph` block. The `\n` between "Rats" and "As shown" comes from PaddleOCR's block segmentation — it detected a paragraph break (likely visual spacing) within what should be a subheading followed by body text.

### Root Cause

PaddleOCR split the page into blocks based on visual spacing. The subheading "Concentration of Irisin in Osteoarthritis Rats" was NOT separated from the following body paragraph because there wasn't enough vertical gap for PaddleOCR to recognize it as a separate block.

### Can this be fixed?

Not at the OCR/pipeline level. PaddleOCR controls the initial block segmentation. The pipeline works with whatever blocks PaddleOCR provides. If PaddleOCR merged the subheading into the body, the pipeline can't separate them without a post-hoc splitting model.

### What CAN be done

Add a post-hoc subheading detector: if a block contains a short line followed by body text, split it into two blocks. But this is heuristic and can break legitimate paragraphs. Recommend deferring to v2.

---

### 4b. Figure Inner Text (A/D/C/E) Binding to Assets

### Symptom

Panel labels (A, B, C, D, E) are correctly classified as `figure_inner_text` but have no association with their parent figure asset. They exist as independent blocks.

### Why This Matters

Without binding, the renderer can't place panel labels within the figure object. The figure asset is cropped from the PDF and displayed as an image; the panel labels stay as loose text blocks.

### Current State

The panel label exclusion (`_PANEL_LABEL_PATTERN`) is working correctly — they're no longer polluting the caption pipeline. But they're also not linked to any asset.

### Spatial Analysis

The panel labels sit OUTSIDE the asset bounding boxes on most pages:

```
Page 10 example:
  Asset A: bbox=[210, 132, 513, 302]
  Label A: bbox=[187, 136, 209, 158] → LEFT of asset (not inside)
  Asset B: bbox=[522, 139, 1012, 355]
  Label B: bbox=[516, 136, 535, 156] → INSIDE asset B (barely)
```

Most panel labels are in the gutter between panels or at the edge. They're associated by PROXIMITY, not containment.

### Implementation (required now)

Add a binding step in `build_figure_inventory()`:

```python
def _bind_inner_text_to_figures(
    structured_blocks: list[dict],
    matched_figures: list[dict],
) -> None:
    """Associate figure_inner_text blocks with the nearest matched figure."""
    inner_texts = [
        (i, b) for i, b in enumerate(structured_blocks)
        if b.get("role") == "figure_inner_text"
    ]
    for idx, block in inner_texts:
        bb = block.get("bbox") or block.get("block_bbox") or [0,0,0,0]
        cx = (bb[0] + bb[2]) / 2
        cy = (bb[1] + bb[3]) / 2
        best = None
        best_dist = float("inf")
        for fig in matched_figures:
            for asset in fig.get("matched_assets", []):
                ab = asset.get("bbox") or [0,0,0,0]
                acx = (ab[0] + ab[2]) / 2
                acy = (ab[1] + ab[3]) / 2
                dist = ((cx - acx)**2 + (cy - acy)**2)**0.5
                if dist < best_dist:
                    best_dist = dist
                    best = fig
        if best and best_dist < 200:
            best.setdefault("panel_labels", []).append({
                "text": block.get("text", ""),
                "bbox": bb,
            })
            block["_bound_to_figure_id"] = best.get("figure_id")
```

Also add the same binding for unresolved clusters:

```python
for cluster in unresolved_clusters:
    cluster_bb = cluster.get("cluster_bbox", [0,0,0,0])
    ccx = (cluster_bb[0] + cluster_bb[2]) / 2
    ccy = (cluster_bb[1] + cluster_bb[3]) / 2
    for idx, block in inner_texts:
        bb = block.get("bbox") or [0,0,0,0]
        cx = (bb[0] + bb[2]) / 2
        cy = (bb[1] + bb[3]) / 2
        dist = ((cx - ccx)**2 + (cy - ccy)**2)**0.5
        if dist < 200:
            cluster.setdefault("panel_labels", []).append({
                "text": block.get("text", ""),
                "bbox": bb,
            })
```

### Acceptance

- figure_inner_text blocks appear as `panel_labels` on matched figures or unresolved clusters
- Render can optionally display panel_labels in figure objects
- No regression in figure matching or caption detection

---

### 4c. Ambiguous Figure Matching Strategy

### Symptom

M36WA39N has 6 ambiguous figures (top scorer gap < 0.15). The current strategy leaves these completely unresolved — no match is made.

### The Problem

The current logic says: `if top1 - top2 < 0.15 → ambiguous_figures.append(...); matched_assets = []`. This means SIX legitimate figures with real assets get zero matches. The assets end up as orphan `unmatched_assets` and the legends become `unmatched_legends`.

### The Fix

Don't give up when scores are close. Add a second verification pass:

```python
if len(close) > 1:
    # Second verification pass: check additional signals
    best_idx, best_asset, best_score = close[0]
    
    # Signal 1: Figure number continuity
    fig_num_ok = True
    if fig_num is not None:
        prev_fig_num = max((m.get("figure_number", 0) for m in matched_figures), default=0)
        fig_num_ok = fig_num == prev_fig_num + 1
    
    # Signal 2: Column compatibility (caption and asset in same column)
    col_ok = True
    legend_col = 0 if lx < page_width * 0.5 else 1
    ab = best_asset.get("bbox") or best_asset.get("block_bbox") or [0,0,0,0]
    asset_col = 0 if (ab[0] + ab[2]) / 2 < page_width * 0.5 else 1
    col_ok = legend_col == asset_col
    
    # Signal 3: Caption-relative-to-asset position
    pos_ok = True
    if len(legend_bb) >= 4 and len(ab) >= 4:
        if legend_bb[3] <= ab[1]:  # caption above asset → natural
            pos_ok = True
        elif ab[3] <= legend_bb[1]:  # asset above caption → acceptable
            pos_ok = True
        else:
            pos_ok = False  # overlapping → suspicious
    
    # Combined decision
    secondary_score = sum([fig_num_ok, col_ok, pos_ok]) / 3.0
    if secondary_score >= 0.67:  # at least 2 of 3 signals positive
        # Accept the match, but mark as low confidence
        matched_assets = [best_asset]
        used_asset_indices.add(best_idx)
        region_match = {"media_blocks": [best_asset], "match_score": best_score}
        match_decision = "matched_low_confidence"
    else:
        # Keep ambiguous
        ambiguous_figures.append({...})
        matched_assets = []
```

### Why This Works

The signals are independent from the primary scorer:
- `score_figure_match()` uses: same_page, x_overlap, nearby_y, caption_above_or_below
- Secondary verification uses: figure continuity, column match, relative position

These are different evidence dimensions, so they catch cases the scorer missed.

### Acceptance

- No more ambiguous figure blocks left completely unmatched when secondary signals are positive
- `matched_low_confidence` status is documented and carries through to health
- Health reports `matched_low_confidence` count separately
- Secondary verification doesn't create false matches (all 3 signals would need to be wrong simultaneously)

---

## Appendix: Issue Priority Matrix

| Issue | Severity | Effort | Urgency | Fix |
|-------|----------|--------|---------|-----|
| Pre-proof marker detection | High | Low (1 pattern) | Now | Add denial in ocr_roles.py |
| Author fuzzy matching | Medium | Medium (1 function) | Before release | Add initials matcher in ocr_metadata.py |
| Figure inner text binding | Medium | Medium (1 function) | Now (user request) | Add binding in ocr_figures.py |
| Ambiguous figure secondary verification | High | Low (logic change) | Now (user request) | Add 3-signal check in ocr_figures.py |
| Figure at-end placement | Low | High | Defer to v2 | Render behavior change |
| Text cutting (PaddleOCR merge) | Low | Impossible | Defer | PaddleOCR limitation |
