# R2 failure audit — 2026-11-10

## Decision

**R2f text-fidelity gate: 792 PASS / 1 HOLD.** Historical R2d (793/793 pass)
is preserved, but it used an over-broad `format_only` rule and key+class
waivers. R2e/R2f replace both:

- 91 affected papers re-audited: **53 PASS / 38 HOLD**.
- R2f resolves 30 fulltext-only papers by paragraph attribution: moved blocks,
  figure inner text, table-caption Markdown, or page-marker noise.
- Four block-change papers are cleared as formatting: `IH6K34R9` is a
  legitimate heading merge; `8M2YFJAX`, `CPQ47TBV`, `QPT4IGLD` are
  false-positive splits with both fragments retained.
- **Only `CHILQ4KJ` remains HOLD.** Its headings are semantically truncated by
  `_split_merged_heading_blocks` (`ocr_document.py:3524`); the producer regex
  must be fixed before it can be cleared.
- Waivers are hash-bound and fail-closed: all four SHA-256 fields, `verdict`,
  `evidence`, and `block_changes` are required; an empty shell is rejected.
- Combined revised gate: **792 PASS / 1 HOLD**. Migration eligibility overlay:
  **787 READY**, 1 `TEXT_FIDELITY_HOLD` (`CHILQ4KJ`).
- R2a JSON diagnostic fix, R2b block audit, R2c asset audit, Plan parity, source
  integrity and idempotence remain valid.

**Production migration: still NO-GO.** R3 visual acceptance and a production
canary remain out of scope for this round.

## R2a — JSON source audit

- 472 papers produced 478 `json_parse` errors: 472
  `structure/document_structure.json`, 4 `figure-map.json`, 2
  `chart-type-map.json`.
- All 478 source files are **invalid UTF-8, random binary** (not GBK, not
  JSON). Example `7M6FIW4V`: 622,179 bytes, head `88075fffd981df14...`.
- The rebuild did not touch them because `build_structured_blocks()` returns
  early for `normalize_mode="seed_only"` before writing the diagnostic. Hashes
  were identical before/after rebuild on the sample.
- Fix: seed-only mode now regenerates `document_structure.json` (diagnostic
  only, 5 MB cap preserved). Sample `7M6FIW4V`, `7NY8KK8P`, `7Q3VTNHT`,
  `7S5ZEVSK`, `7TAVQQG2`: all regenerated as valid UTF-8 JSON.
- R2d rebuilds all 793 papers and confirms the production JSON surface parses.
- Remaining `figure-map.json` / `chart-type-map.json` are optional skill
  artifacts, not OCR production inputs. They are reported as
  `optional_unreadable` and must be regenerated separately; they are not
  silently deleted.

Evidence: `docs/evidence/r2-audit/json.json`.

## R2b — content-level diff

- Audited 91 unique papers from `historical_text_decrease`,
  `structured_text_decrease`, `historical_structured_chars_decrease`, and
  `historical_object_missing`.
- Historical result: 91 PASS / 0 HOLD under the old substring rule. **This is
  superseded by R2e**; the old rule misclassified real heading truncation.
- Every changed block is a heading/role normalization, for example:
  - `Received 13 February; accepted 15 May 2006.` → `15 May 2006.`
  - `3.1. Three 10 Min ...` → `10 Min ...`
  - `2.2. ... 2.2.1. ...` → `2.2.1. ...`
- No old body block was missing from the rebuilt corpus. The 85 text decreases
  are normalization/role effects, not content deletion.
- These per-paper PASS results are the only source of the 90 validator waivers
  in R2d.

Evidence: `docs/evidence/r2-audit/content.json`,
`docs/evidence/r2-audit/waivers-r2e.json`.

## R2c — historical asset preservation

`LSTHKPAE/assets/tables/table_001.png`:

- Source file: 298,527 bytes, sha256 `bbac380f...`, head `fcc76bd5...`,
  **not a valid image** (random binary).
- No Markdown note in the vault references `table_001.png` (0 hits).
- Rebuild produces `assets/tables/table_001.jpg`, valid RGB 875×348.
- Classification: `legacy_corrupt_unreferenced_replaced` — the old file was
  unusable bytes, not a preserved table asset. R2d records
  `legacy_corrupt_asset_replaced` as a warning, not a silent skip.
- The migration plan does not yet emit an explicit png→jpg replacement op for
  this legacy case; that remains a plan-hygiene follow-up, not a data-loss
  finding.

Evidence: `docs/evidence/r2-audit/asset.json`.

## R2d — unified revalidation

- Selected READY: 793.
- Rebuilt: 793/793.
- Validation: 793 pass / 0 fail.
- Plan mismatches: 0.
- Source integrity: unchanged on 40/40 chunks.
- Idempotence: 40/40 chunks.
- Evidence-backed waivers: 90 papers
  (`historical_text_decrease` 85, `structured_text_decrease` 5,
  `historical_structured_chars_decrease` 5).
- Optional unreadable: 4 `figure-map.json`, 2 `chart-type-map.json`.
- Warnings: 1 `legacy_corrupt_asset_replaced`.

Evidence: `docs/evidence/r2-audit/final-summary.json`.

## R2e — corrected text-fidelity audit

The old rule `format_only = old in new or new in old` accepted any substring
deletion. It is removed. `format_only` now requires equality after stripping
only Markdown markers, wiki embeds, leading section numbering, and whitespace.

- 91 papers re-audited: **53 PASS / 38 HOLD**.
- 11 changed blocks were reviewed individually. `CHILQ4KJ` p6 b12
  (`3.4. Modulation of Piezo 1-Mediated ...` -> `1 Cells by Small Chemicals`)
  is `text_change`, not format. `IH6K34R9` p13 b11 loses
  `2.2. Three-Dimensional Printing ... for CTE`. Received/Accepted blocks are
  `metadata_normalization`, still HOLD.
- Fulltext is no longer assumed safe from block existence. Old fulltext
  paragraphs absent from the rebuilt fulltext with token coverage < 0.8 are
  recorded as `fulltext_loss` and HOLD.
- Waivers are hash-bound. `waivers-r2e.json` binds each waiver to the paper
  fulltext/structured SHA-256 and each changed block's old/new SHA-256. A
  mutated hash produces `waiver_mismatch:<class>` and the error stays blocking.
- 52 evidence-backed waivers remain; 38 papers have no waiver.
- Revised combined gate: **755 PASS / 38 HOLD** (702 unaffected + 53 R2e pass).
- R2e did not rerun all 793; it re-ran the 91 affected papers in isolated
  vaults. Historical R2d evidence remains at
  `docs/evidence/r2-audit/final-summary.json`.

Evidence: `docs/evidence/r2-audit/content-r2e.json`,
`docs/evidence/r2-audit/waivers-r2e.json`,
`docs/evidence/r2-audit/final-summary-r2e.json`.

## R2f — HOLD attribution

- 30 fulltext-only papers: every suspected paragraph attributed to
  `moved_to_block`, `moved_to_figure_inner_text`, `table_caption_markdown`,
  `suffix_moved`, `non_body_old`, or `page_marker_noise`; 0 unresolved.
- 5 block-change papers: all changes trace to
  `_split_merged_heading_blocks` (`paperforge/worker/ocr_document.py:3524`),
  whose `heading_num` regex treats mid-text numbers/dates as headings.
  `CHILQ4KJ` loses semantic heading text and stays HOLD. `IH6K34R9` is a
  legitimate merge. `8M2YFJAX`/`CPQ47TBV`/`QPT4IGLD` split metadata but retain
  both fragments, so they are formatting-only.
- Evidence: `r2f-attribution.json`, `r2f-attribution-remaining.json`,
  `r2f-block-analysis.json`, `r2f-resolution.json`,
  `final-summary-r2f.json`.

## Residual risks

1. The 4 optional skill maps remain unreadable until regenerated; they are not
   OCR production inputs.
2. The migration plan should explicitly register managed `.png`/`.webp`
   replacements; today the corrupt `LSTHKPAE` png is handled by the validator
   warning.
3. R3 visual acceptance and a production canary are still required before any
   real-vault migration.
