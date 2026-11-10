# R2f Block-Change Analysis

Five block-change HOLD keys. All mutations trace to a single producer:
`paperforge/worker/ocr_document.py::_split_merged_heading_blocks` (invoked in
`normalize_document_structure` ~line 2704). The function splits a heading block
whenever its text contains >=2 matches of

```
heading_num = re.compile(r"\b(\d+(?:\.\d+)*\.?\s+[A-Z])")
```

## Findings

### CHILQ4KJ — heading_truncation (NOT clearable)
7 subsection headings split because a mid-text number followed by a capital
word is misread as a heading number: "10 Min", "16 Hz", "SCP-1 Cells" -> "1
Cells", "Piezo 1 Promoted" -> "1 Promoted", "Piezo 1 Partly" -> "1 Partly".
Example p6 b12: "3.4. Modulation of Piezo 1-Mediated ... Influx into SCP-1
Cells by Small Chemicals" -> "1 Cells by Small Chemicals" (prefix truncated to
"... SCP-"). Stage: `_split_merged_heading_blocks`. Recommendation: fix
producer (require a dotted heading number); do not clear.

### IH6K34R9 — heading_merge (clearable as formatting)
p13 b11 legitimately contains two heading numbers ("2.2." and "2.2.1."); split
into two coherent headings; prefix retained as sibling block. No fulltext loss.

### 8M2YFJAX / CPQ47TBV / QPT4IGLD — metadata blocks (clearable as formatting)
Attribution labeled these `metadata_normalization`, but they are NOT an
intentional metadata policy. The same regex splits "Received ... accepted 15
May 2006." at "15 May", "Received: ... / Accepted: 9 April 2025" at "9
April", "Received: ... / Accepted: 3 July 2024" at "3 July". Both fragments
retained; no semantic loss. Clearable as pure formatting.

## Code reference
- `paperforge/worker/ocr_document.py:3524` `_split_merged_heading_blocks`
- regex `heading_num` at ~3531
- call site ~2704 in `normalize_document_structure`
- Evidence from isolated rebuilds under C:/rtools44/tmp (not production vault).

## Recommendation
Fix producer regex to require a dotted heading number (e.g. `\d+\.\d+` or
`\d+\.`) so mid-text quantities and dates are not treated as headings. After
fix, CHILQ4KJ truncation and the metadata splits disappear; IH6K34R9
legitimate merge remains.
