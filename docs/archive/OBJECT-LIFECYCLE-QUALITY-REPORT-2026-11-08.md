# Figure/Table End-to-End Correctness — quality report (2026-11-08)

Master after E0–E4: `fe126199`. The OCR vault was **not** rebuilt; the 952-paper
snapshot remains the historical baseline. Current-chain numbers come from
read-only replays of the merged code.

## Delivered

| Phase | PR | Change | Result |
|---|---|---|---|
| E0 | #379 | lifecycle contract, frozen baseline, audit tools, goldens, tracked-file guard | contract + tooling merged |
| E3 | #380 | reader synthesis after ownership arbitration; delivery reconciliation; orphan classifier | 6 orphan embeds, 19 asset-bearing undelivered, 1,519 assets classified |
| E1 | #381 | stable canonical identity; compound numbering; continuation merge; page-qualified legends; artifact collision guard | SRNJDAA2 1 id/24 dups/2 colliding paths → 21/0/0 |
| E1b | #381 | `(page, block_id)` legend identity in reservation/settlement/continuation/composite/bundle/locator/sidecar/legacy paths | 388XI46Q p15 no longer borrows page 9's caption text |
| E2 | #382 | side-by-side caption/figure relation | 2AZ2EGQB Fig 4 → asset 3 |
| E4 | #383 | table-structure evaluation and decision | no output change; HTML not emitted |

## Measured (40-paper current chain)

| Metric | Before | After |
|---|---:|---:|
| Duplicate figure ids (40-paper replay) | 0 | 0 |
| Figure entries (40 papers) | — | 230 |
| Two-entry parity (first parse vs rebuild) | 40/40 | **40/40 identical** |
| 2AZ2EGQB p9 Figure 4 | unmatched | asset 3, same_page |
| SRNJDAA2 unique ids / duplicate ids / colliding paths | 1 / 24 / 2 | 21 / 0 / 0 |
| 2BYRLKQS claims | 4/0/0 | 4/0/0 (unchanged) |

## Historical snapshot still reports (vault not rebuilt)

- 181 papers / 355 duplicate id entries; 16,989 orphan markdown; 6 orphan embeds;
  233 canonical md never embedded (19 asset-bearing objects undelivered);
  3 stale canonical md.
- Tables: 1,766 total, 293 assetless, 1,432 with HTML, 121 notes, 146 continuation;
  structured markdown/fulltext emissions: 0.

These numbers describe the old artifacts, not the merged code. A full rebuild is
required to apply E1–E4 to the vault, after a dry-run migration preview.

## No-Go / deferred

1. **Backward cross-page reservation** (388XI46Q p14–15): the p15 caption is not
   in the corpus legend list and forward reservation interferes; a heuristic
   version also attached p19 assets to 28ALPCY7's assetless Figure 6. Deferred
   until a dedicated pass with ground truth. Figure 5 remains missing.
2. **Structured table output**: image remains truth; HTML fidelity (numbers,
   P values, units, merged cells, footnotes, continuation) is unvalidated.
3. **Full-vault rebuild**: needs a dry-run migration report (new ids, unique
   paths, link validity) and rollback evidence.

## Remaining risks

- H (Obsidian) CI job fails on an external Obsidian download 504; all code gates
  (L0/L1/L1b/L3/L4/L4b/J-Matrix/P) are green on the merged heads.
- `figure_inner_text` ownership: 6,713 rows, 606 owned; labels may fall outside
  crops in some layouts (visual samples preserved them).
- Table rows/digits remain image-only until E4 criteria are met.
- The intermittent tracked-test-file disappearance has a guard test now
  (`tests/test_tracked_files_present.py`); the cause is still unidentified.
