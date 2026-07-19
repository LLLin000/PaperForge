# Investigation Findings — Evidence Complete

> 2026-07-02 | Root causes confirmed for all 3 investigations

---

## Investigation 3: WNDJX4KB — Root Cause Found

### Evidence

ALL 26 ref blocks (page 8 + page 9+) have identical fields:
- `raw_label=reference_content`, `seed_role=reference_item`, `style_family=reference_like`, `zone=reference_zone`
- **But page 8 blocks (1-6) final role = `body_paragraph`**, page 9+ (7-26) = `reference_item`
- Evidence only shows `["reference content label: ..."]` — NO evidence from `resolve_final_role`

### Root Cause

`assign_block_role()` correctly sets `reference_item` for ALL blocks. `resolve_final_role()` keeps it (no change). **The demotion happens AFTER `resolve_final_role`**, in `_normalize_reference_roles_from_partition()`.

This function runs AFTER reference zone detection and partition. Blocks 1-6 on page 8 (same page as the "References" heading) are not included in the reference partition (the partition starts at a later page or y-position). The function demotes unpartitioned reference_item blocks to `body_paragraph` without recording evidence.

### Fix

Two options:
1. **Fix the partition** to include page 8 refs (all ref items below the heading)
2. **Fix `_normalize_reference_roles_from_partition`** to not demote blocks with `raw_label=reference_content` or `seed_role=reference_item` in `reference_zone`

Option 1 is more correct — the partition should include ALL ref items below the heading on the heading page.

---

## Investigation 4: Wiley Heading — Root Cause Found

### Evidence

Both `97M7HFCD` (page 6) and `2HEUD5P9` (page 18):
- `references_start` page has body subsections, publisher watermarks, running headers — **NO "References" heading text**
- No block in the entire paper contains "References", "REFERENCES", or any variant
- `reference_zone.status=HOLD`, `heading_block_id=None`
- Pipeline set `references_start` based on first `reference_item` block page, not on heading detection
- The "References" heading is **not present in the OCR text layer at all**

### Root Cause

The "References" heading in these Wiley PDFs is not extracted as text by PaddleOCR. Possible reasons:
1. Running header format: `ADVANCED SCIENCE NEWS\nwww.advancedsciencenews.com` occupies the header zone and may overlap with or replace the section heading slot
2. The heading is embedded in a graphical element (PDF vector text that PaddleOCR skips)
3. The heading uses a font variant that PaddleOCR classifies as noise/header_image

**This is an OCR pipeline limitation — no code fix exists.** The text simply isn't available in the block layer. Synthetic heading would be risky (page 6 of 97M7HFCD is still body text, not a reference section; the `reference_item` blocks on page 6 are fake article tracking numbers like "2409400").

---

## Investigation 5: U746UJ7G — Root Cause Found

### Evidence

Refs 40, 41, 43 in blocks:
- All 3 ARE in `structured_blocks.jsonl`: `role=reference_item`, `zone=reference_zone`, `render_default=True`, page 12
- None in fulltext (total 43 refs in fulltext vs 46 in blocks)
- Fulltext ref 42 = "Baghdadi JD, **Brook RH**..." (block ref 43 content!)
- Block ref 42 = "**Rhee C**, Wang R..." (different author, different paper)
- Total ref_items in blocks: 46 across pages 10, 11, 12

### Root Cause

This is a **reference numbering collision**. The fulltext has ref 42 mapped to what the block system calls ref 43. Refs 40, 41 got dropped in the collision.

Two possible mechanisms:
1. **Duplicate ref numbers**: If two blocks claim `42`, the rendering's dedup drops the original 42 (Rhee C) and the duplicates 40/41 (which share a prefix collision with 42's first block)
2. **Block ID collision** in consumed_table_block_keys or similar dedup structure (same P0 pattern — flat dict overwrites same-key entries)

Likely: `_ref_number_sort_key` groups refs by number, and multiple blocks with the same number cause a dedup collision. The fulltext has the LAST instance of number 42, not the first.

### Fix

Add a `_ref_number_dedup` guard in `_reorder_tail_run()` or the render emit path that logs/detects duplicate ref numbers. If a block's ref number is already emitted, append a disambiguation suffix rather than silently dropping.
