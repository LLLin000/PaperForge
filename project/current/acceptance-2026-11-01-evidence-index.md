# Acceptance run 2026-11-01 — archived evidence index

Status: **archive only — no acceptance verdict is claimed.** This file records what the run
produced, where it now lives, and which records did not pass. Nothing here re-binds a candidate.

## 1. Where the evidence is

| Item | Value |
|---|---|
| Archive root | `%USERPROFILE%\PaperForge-evidence\acceptance-2026-11-01` |
| Manifest | `MANIFEST.json` — per-file `bytes` + `sha256` (1034 files) |
| Size | ~21.8 MB |
| Source of archive | `%TEMP%\PF-FunctionalAcceptance-20261101` + `%TEMP%\PF-OfflinePreview-20261030` (deleted after capture) |
| Deleted | per-journey vaults/venvs/portable Obsidian and the 1.14.5 installer (~29.9 GB); no evidence files were deleted |
| Recorded window | 2026-10-30 15:32 → 2026-11-03 11:59 (+0800), from 197 embedded timestamps |

## 2. What was under test

From `update-v6-test-notes.txt` in the archive:

- frozen v6 pair — source `f9e382c13d24b4b5250cbfa32858071ccd64947b5b807db096b43228a84a6a37`,
  wheel `76ac2720c2b5473ca3c192c3dd4735eb114fc7f472f596a45723830f9e3fdc76`,
  bundle `04c53639352f099f8290d7ea106c0e5bd90baa2d2fe4e220376fc3695958622f`
- prior runtime baseline — official `2.0.0rc4` wheel `1ca976acfd537e7bf50a5b980a1967bc1fb6dac8122680f4c3076992ada9540a`
- update target — locally controlled to `2.0.0rc6`; pip index disabled, offline wheelhouse only
- no paid provider, production credential or production vault was used

Every case record in the archive carries `source_sha = a51b86ab97970e219c11261c088cf5cfd66466a3`
(the product source the pair was built from). That SHA is **not** the ledger candidate
`56407222…`/`76c17945…`, so this run does not rebind the release candidate by itself.

## 3. Case records by group

| group | evidence files | cases | statuses |
|---|---:|---:|---|
| `journey-10` | 31 | 31 | LIVE_PASS ×14, BLOCKED ×4, NOT VERIFIED ×4, INCOMPLETE ×2, DIAGNOSTIC_ONLY ×2, LIVE_FAIL ×2, CLEANED_IN_ISOLATED_PROFILE ×2, VERIFIED |
| `journey-11` | 8 | 8 | VERIFIED ×8 |
| `journey-18` | 2 | 2 | LIVE_PASS ×2 |
| `journey-19` | 4 | 4 | LIVE_PASS ×4 |
| `journey-2` | 28 | 28 | VERIFIED ×14, PASS ×10, FAIL ×2, OBSERVED ×2 |
| `journey-21` | 8 | 8 | LIVE_PASS ×8 |
| `journey-22` | 14 | 14 | LIVE_PASS ×14 |
| `journey-25` | 34 | 38 | VERIFIED ×30, LIVE_PASS ×4, FAILURE ×4 |
| `journey-26` | 28 | 28 | LIVE_PASS ×24, LIVE_PARTIAL ×2, LIVE_FAIL ×2 |
| `journey-27` | 8 | 8 | LIVE_PASS ×8 |
| `journey-28` | 6 | 6 | LIVE_PASS ×6 |
| `journey-29` | 3 | 3 | ABORTED_NOT_ACCEPTANCE ×2, VERIFIED |
| `journey-30` | 4 | 4 | LIVE_PASS ×4 |
| `journey-31` | 14 | 14 | LIVE_PASS ×14 |
| `journey-32` | 20 | 20 | LIVE_PASS ×10, LIVE_FAIL ×10 |
| `journey-33` | 24 | 24 | LIVE_FAIL ×24 |
| `journey-34` | 2 | 2 | LIVE_PASS ×2 |
| `journey-35` | 2 | 2 | LIVE_PASS ×2 |
| `journey-36` | 2 | 2 | LIVE_PASS ×2 |
| `journey-37` | 2 | 2 | LIVE_PASS ×2 |
| `journey-38` | 6 | 6 | LIVE_FAIL ×4, LIVE_PASS ×2 |
| `journey-39` | 10 | 10 | LIVE_PASS ×8, UPDATE_PASS_RECOVERY_PENDING ×2 |
| `journey-40` | 20 | 20 | LIVE_PASS ×10, LIVE_FAIL ×8, UPDATE_PASS_RECOVERY_PENDING ×2 |
| `journey-41` | 12 | 12 | LIVE_PASS ×10, UPDATE_PASS_RECOVERY_PENDING ×2 |
| `journey-42` | 8 | 8 | LIVE_PASS ×6, UPDATE_PASS_RECOVERY_PENDING ×2 |
| `journey-5` | 14 | 14 | LIVE_PASS ×12, VERIFIED ×2 |
| `journey-6` | 6 | 6 | VERIFIED ×4, LIVE_PASS ×2 |
| `journey-8` | 24 | 24 | LIVE_PASS ×12, VERIFIED ×6, FAILED_BEFORE_VERIFIED_POINTER ×2, INVALID_TEST_MATRIX ×2, ISOLATED_RUNTIME_PASS ×2 |
| `journey-9` | 26 | 26 | LIVE_PASS ×20, VERIFIED ×6 |
| `journey-searchfix-b` | 3 | 3 | LIVE_PASS ×2, VERIFIED |
| `dashboard-flag-fix-82ddbbf9` | 7 | 11 | VERIFIED ×6, LIVE_PASS ×4, LIVE_FAIL |
| `paired-after-setup-fix` | 20 | 38 | VERIFIED ×38 |
| `upgrade-rc4-to-rc5-20261102` | 1 | 1 | LIVE_FAIL |
| `upgrade-rc4-to-rc5-ui-20261102` | 4 | 4 | LIVE_FAIL ×3, LIVE_PASS |

Status strings are reproduced verbatim; the run used several vocabularies
(`VERIFIED`, `LIVE_PASS`, `PASS`, `LIVE_FAIL`, `BLOCKED`, …) and this index does not normalize them.

## 4. Records that did not pass

87 of 431 case records carry a non-pass status. Grouped (case id × status):

> Later journeys repeat earlier cases (the `journey-3x` update/recovery series and the
> `upgrade-rc4-to-rc5*` runs overlap). This list is **not** de-duplicated by recency: a
> `LIVE_FAIL` here may have been re-run successfully later. Read the record's own timestamp
> before treating an entry as the final state.

- `dashboard-flag-fix-82ddbbf9`
  - `LIVE-DASHBOARD-WORKFLOW-FLAG-PROJECTION-REPAIR` — LIVE_FAIL
- `journey-10`
  - `help.restore-current-pair-attempt-1` — BLOCKED
  - `help.restore-current-pair-attempt-2` — NOT VERIFIED
  - `B08-OCR-Workspace-fulltext-preview` — BLOCKED
  - `B08-OCR-WORKSPACE-DIAGNOSTIC` — INCOMPLETE
  - `A06-runtime-reinstall` — LIVE_FAIL
  - `setup-wizard-current-pair-attempt-1` — NOT VERIFIED
- `journey-2`
  - `LIVE-HELP-RESTORE-ROUTE-DIAGNOSTIC` — FAIL
- `journey-25`
  - `runtime-reinstall-diagnostic` — FAILURE
  - `runtime-reinstall-interpreter-diagnostic` — FAILURE
- `journey-26`
  - `LIVE-FOUNDATION-UPDATE-PYTHON-REPAIR-DOCTOR-V5` — LIVE_PARTIAL
  - `LIVE-OCR-DIAGNOSE-CLIPBOARD-PRIVACY-V5` — LIVE_FAIL
- `journey-29`
  - `V6-WRONG-SPEC-SELECTION` — ABORTED_NOT_ACCEPTANCE
- `journey-32`
  - `LIVE-FOUNDATION-UPDATE-RC4-TO-RC6-journey-32` — LIVE_FAIL
- `journey-33`
  - `LIVE-FOUNDATION-UPDATE-RC4-TO-RC6-journey-33` — LIVE_FAIL
- `journey-38`
  - `LIVE-FOUNDATION-UPDATE-CORRUPT-RUNTIME-BOOTSTRAP-RECOVERY` — LIVE_FAIL
  - `LIVE-FOUNDATION-UPDATE-CANCEL-RECOVERY-journey-38-V10` — LIVE_FAIL
- `journey-39`
  - `LIVE-FOUNDATION-UPDATE-CANCEL-RECOVERY-journey-39-V10` — UPDATE_PASS_RECOVERY_PENDING
- `journey-40`
  - `LIVE-DASHBOARD-WORKFLOW-FLAG-RESTART-READBACK` — LIVE_FAIL
  - `LIVE-FOUNDATION-UPDATE-CANCEL-RECOVERY-journey-40-V10` — UPDATE_PASS_RECOVERY_PENDING
  - `LIVE-FOUNDATION-REPAIR-LOCALIZATION-AND-FAILURE-FEEDBACK` — LIVE_FAIL
- `journey-41`
  - `LIVE-FOUNDATION-UPDATE-CANCEL-RECOVERY-journey-41-CURRENT-SOURCE` — UPDATE_PASS_RECOVERY_PENDING
- `journey-42`
  - `LIVE-FOUNDATION-UPDATE-CANCEL-RECOVERY-journey-42-CURRENT-SOURCE` — UPDATE_PASS_RECOVERY_PENDING
- `journey-8`
  - `LIVE-HELP-RESTORE-REINSTALL-DIAGNOSTIC` — FAILED_BEFORE_VERIFIED_POINTER
  - `managed-runtime-version-mismatch` — INVALID_TEST_MATRIX
- `upgrade-rc4-to-rc5-20261102`
  - `LIVE-FOUNDATION-UPDATE-RC4-TO-RC5` — LIVE_FAIL
- `upgrade-rc4-to-rc5-ui-20261102`
  - `LIVE-FOUNDATION-MISSING-PYTHON-SETUP-ENTRY-FIXED` — LIVE_FAIL
  - `LIVE-FOUNDATION-REPAIR-MISSING-PYTHON-UI` — LIVE_FAIL
  - `LIVE-FOUNDATION-UPDATE-RC4-TO-RC5-UI` — LIVE_FAIL

## 5. Evidence that is not a case record

- `dashboard-flag-fix-82ddbbf9/evidence-retry/` — projection repair JSON + restart readback JSON + PNG screenshots
- `credential-migration-live-20261103/credential-migration-live.json`
- `missing-vector-extras-2dc3b4ae99704c539e53064874405e19/missing-vector-extras-install.json`
- `evidence/` — paired source identity / file inventory (`paired-source-files.json`, `source-identity-after-setup-fix*.json`)
- `source-snapshot/` — code snapshot of the tested tree
- harness: 52 `.ps1`, 6 `.py`, 19 `.ts`, 10 `.js` (pair build, update feed, dashboard flag, doctor UI, upgrade rc4→rc5, diagnostics)

## 6. Gaps and how to use this

- The run is **not** mapped to W01–W22 issue numbers; treat it as raw evidence, not as gate closure.
- No single pass/fail verdict exists in the tree; per-case statuses above are the only truth.
- To cite a fact, quote `archive file path + sha256 from MANIFEST.json` — never the deleted sandbox path.
- Re-running any journey needs the harness scripts plus the offline wheelhouse; the deleted vaults are fixtures, not evidence.

## 7. Suggested next step

1. Pick the cases that map to open gates (W18–W21) and read their records directly, taking the
   latest attempt per case id by timestamp.
2. Anything still failing becomes an issue with the record path + sha256 as evidence.
3. Only then decide whether this run can be cited in a gate closure — it currently is not.

No acceptance or release claim is made by this file.
