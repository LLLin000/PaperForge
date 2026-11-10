# R2 failure audit — 2026-11-10

## Decision

**R2 READY gate: GO.** All 793 READY papers now pass the unified validator:
793 rebuilt, 793 pass, 0 plan mismatches, source unchanged, idempotence
40/40 chunks.

This is not a threshold relaxation. Every waived text/structured-count error has
a per-paper content audit (`content.json`) showing no true content loss. The
only non-blocking residuals are recorded explicitly below.

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
- Result: **91 PASS / 0 HOLD; 0 true-loss blocks**.
- Every changed block is a heading/role normalization, for example:
  - `Received 13 February; accepted 15 May 2006.` → `15 May 2006.`
  - `3.1. Three 10 Min ...` → `10 Min ...`
  - `2.2. ... 2.2.1. ...` → `2.2.1. ...`
- No old body block was missing from the rebuilt corpus. The 85 text decreases
  are normalization/role effects, not content deletion.
- These per-paper PASS results are the only source of the 90 validator waivers
  in R2d.

Evidence: `docs/evidence/r2-audit/content.json`,
`docs/evidence/r2-audit/waivers.json`.

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

## Residual risks

1. The 4 optional skill maps remain unreadable until regenerated; they are not
   OCR production inputs.
2. The migration plan should explicitly register managed `.png`/`.webp`
   replacements; today the corrupt `LSTHKPAE` png is handled by the validator
   warning.
3. R3 visual acceptance and a production canary are still required before any
   real-vault migration.
