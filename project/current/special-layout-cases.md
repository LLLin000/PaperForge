# Special-Layout Case Registry

Cases where the standard figure pipeline produced unexpected results due to unusual PDF layout or content patterns. Each case is recorded for future targeted investigation.

---

## 3P98ZJJA — QR code picked as Figure 1 candidate

**Date:** 2026-08-21
**Census result:** `no` (vision confirmed mismatch)

### What happened
The bounded-slot reconciliation selected a QR code image block as the sole surviving candidate for Figure 1. The true Figure 1 (anchor insertion illustration) exists on page 3 but was not in the unmatched_assets or unresolved_clusters pool.

### Actual PDF layout (confirmed by visual inspection)

Page 3 contains a **2×2 four-panel grid**:

```
┌─────────────────────┐  ┌─────────────────────┐
│ Figure 1 (bordered) │  │ Figure 2a            │
│ anchor illustration │  │ arthroscopic photo   │
├─────────────────────┤  ├─────────────────────┤
│ Figure 2b           │  │ Figure 2c            │
│ arthroscopic photo  │  │ arthroscopic photo   │
└─────────────────────┘  └─────────────────────┘
```

- **Figure 1**: bordered box, left-top. Two sub-panels (insertion + removal). Caption below.
- **Figure 2a/2b/2c**: three separate arthroscopic photos, each with its own caption (Figure 2a, 2b, 2c).

### Root cause analysis

1. **Four-grid layout**: OCR treats each quadrant as a separate image block. Figure 1's bordered box may further fragment its two sub-panels into smaller blocks.
2. **Figure 2 has a/b/c sub-figures**: the pipeline needs to group 2a + 2b + 2c as one canonical "Figure 2" but also preserve individual panel boundaries for cropping. This multi-subfigure-within-one-number pattern is not handled cleanly.
3. **QR code on page 1** was a clean standalone media block that outcompeted the fragmented true figure blocks.
4. **Result**: no unmatched_asset or unresolved_cluster contained Figure 1 or Figure 2's panels → slot reconciliation found only the QR code.

### Why this matters
Multi-column journal layouts with 2×2 figure grids and lettered sub-figures (2a/2b/2c) are common in surgical/orthopedic journals. The pipeline must:

- Group same-figure sub-panels across grid quadrants
- Distinguish bordered-box figures from standalone images
- Not let small decorative assets (QR codes) compete when real figures are fragmented

### Future investigation

- Detect 2×2 / multi-quadrant figure grids and treat them as one composite region per figure number
- Handle lettered sub-figure captions (2a, 2b, 2c) as one canonical object with multiple render panels
- Filter unmatched_assets by minimum meaningful size relative to page
- Consider whether QR codes should be explicitly excluded from figure candidacy

---

## JD8T7YHD — Cross-figure caption confusion + Figure/Scheme coexistence

**Date:** 2026-08-21
**Census result:** `no` for Figure 1 (candidate = chemical structure, true Figure 1 = IR spectrum)

### What happened

Multiple figures were mis-assigned. The root cause is **not** a single bad crop but a **cascade of cross-figure caption confusion** starting at page 4.

### Actual PDF layout

```
Page 3:  Scheme 1 (chemical synthesis) + body text
Page 4:  [Figure 1 caption: "Figure 1. The IR spectra of CS and GTMAC-CS."]
         [Figure 1 chart asset: block 6]
         [body_paragraph: "...the ¹H NMR spectrum was performed and shown in Figure 2..."]
Page 5:  [Figure 2 caption: "Figure 2. The ¹H NMR spectra of GTMAC-CS."]
         [Figure 2 image asset: block 4]
         [Figure 3a,b caption: "Figure 3a,b show..."]
...
Page 10: [Figure 6 caption + Figure 6 chart assets (blocks 3,5)]
```

### Cascade of errors

1. **Figure 1's chart (p4 block 6) was stolen by figure_002.** The matcher used the body_paragraph on p4 block 7 ("...shown in Figure 2...") as Figure 2's legend, and bound it to Figure 1's chart asset on the same page.

2. **Real Figure 2's image (p5 block 4) was stolen by figure_003.** The matcher used Figure 3's caption text (p5 block 5) as legend and bound it to Figure 2's image on the same page.

3. **Figure 6's assets (p10 blocks 3,5) were stolen by figure_007.** The matcher bound them to Figure 7's caption from p11.

4. **Result**: Figure 1 and Figure 6 have no matched_assets. Figure 1's chart is inside figure_002, Figure 6's charts are inside figure_007. The unmatched_assets pool only has Scheme 1's chemical structure (p3 block 6).

### Root cause

The matcher's "nearby caption" heuristic binds assets to the **closest caption-like text**, but body paragraphs that mention "Figure N" in passing are treated as formal captions. In a paper where figures appear immediately after the body text discusses them, the body paragraph is closer than the real caption on the next page.

This is a **cross-figure caption confusion** pattern:

```
p4: [Fig 1 caption] [Fig 1 asset] [body text mentioning Fig 2]
                                        ↓
                              matcher binds asset → "Figure 2" (wrong!)
```

### Why this matters

- The bounded-slot reconciliation correctly identified Figure 1 as missing, but the only surviving candidate was Scheme 1's chemical structure (the sole unmatched_asset).
- The real Figure 1 asset is locked inside figure_002's matched_assets.
- This is not fixable at the render layer — the upstream matcher produced wrong ownership.

### Future investigation

- Distinguish formal captions (`Figure N. Description`) from body text mentioning `Figure N` in passing
- Check whether the matcher should require the caption to START with the figure number
- Consider whether cross-page caption search should prefer the nearest FORMAL caption over the nearest text block
- Audit whether this cascade pattern (asset stolen by next figure's body text) occurs in other papers
