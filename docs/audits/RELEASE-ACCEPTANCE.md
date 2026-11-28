# PaperForge 2.0 Release Acceptance Gate (RAGate) & Audit Ledger

> **Target Candidate**: PR `#438` (`feat/pbaf-v2.1-hardening` -> `master`)
> **Base Commit Reviewed**: `402303ec12e4` (plus hardening fixes in this follow-up series)
> **Current Verdict**: **CONDITIONAL GO** — Engineering Ready after P0/P1 audit fixes; awaiting owner version bump (`2.0.11` -> `2.0.12`, since tag `2.0.11` is already an existing Pre-release) and explicit sign-off on cross-OS desktop items marked `UNVERIFIED`.

---

## 1. Readiness Tier Summary

| Tier | Status | Notes |
| --- | --- | --- |
| **Engineering Ready** | **PASS (after P0/P1 closure)** | Unit/protocol suites, PBAF v2.1 `--strict`, FTS5 selective-index contract (`PF-R01`), PDF runtime budget assertions (`PF-R05`), and 3-OS Chaos suite pass. |
| **Product Ready** | **CONDITIONAL PASS** | Verified on Windows Obsidian real E2E (`H1`/`H2`) and CLI-host acceptance (`P`), plus isolated 1,358-paper scratch vault benchmarks. Real Obsidian GUI on macOS & Linux and live paid OCR/LLM keys remain `UNVERIFIED`. |
| **Distribution Ready** | **CONDITIONAL PASS** | Release Chaos Gate (`PF-R02`) and atomic Draft-first byte-verified asset publishing (`PF-R03`) wired into `.github/workflows/publish.yml`. Owner must bump `2.0.11` -> `2.0.12` before tagging (existing Pre-release `2.0.11` is immutable). |

---

## 2. Pre-Release Audit Findings Resolution (`PF-R01` .. `PF-R05` + Additional Checks)

| ID | Severity | Finding Summary | Resolution & Verification |
| --- | --- | --- | --- |
| `PF-R01` | **P0** | `rebuild_fts_indexes` and `check_and_heal_fts` ran native `VALUES('rebuild')` on external-content `body_units_fts`, indexing vetoed `indexable=0` rows and leaking them to `gateway.py` / `embedding/search.py`; PBAF `D5` compared `body_units` vs `body_units_fts` `COUNT(*)` (false green); `clear_fts` used `DELETE FROM`; `prune.py` used incomplete FTS delete columns. | Fixed `paperforge/memory/db.py`, `schema.py`, `worker/prune.py`, `retrieval/gateway.py`, `embedding/search.py`, and `scripts/backend_audit.py` (`D5` uses `body_units_fts_docsize`, orphan join, `MATCH` probe, and non-empty carrier check). Regression covered in `tests/test_migration_sovereignty_and_healing.py::test_pf_r01_selective_body_units_fts_contract_heal_retrieval_and_d5`. |
| `PF-R02` | **P1** | `ci-chaos.yml` (`L6`) only triggered on `schedule` / `workflow_dispatch`; `publish.yml` did not gate release on L6 for the release SHA. | Added `workflow_call` to `.github/workflows/ci-chaos.yml` and wired `chaos-gate` into `.github/workflows/publish.yml` (`publish.needs: [build-native-daemon, chaos-gate]`). |
| `PF-R03` | **P1** | `publish.yml` created a public GitHub Release before uploading assets and skipped remote byte SHA-256 verification on retries. | Refactored `.github/workflows/publish.yml` to create releases as `--draft`, verify remote asset bytes against `checksums.txt` on retries, verify full asset list, and atomically transition `--draft=false`. |
| `PF-R04` | **P1** | Desktop GUI (`H1`/`H2`) and CLI-host acceptance (`P`) run on `windows-latest` only; ARM64 Linux/Windows and x86_64 macOS native daemon binaries build without smoke tests. | Explicitly documented in Section 4 below so unverified targets are never mislabeled `PASS`. |
| `PF-R05` | **P1** | `perf-pdf-runtime.test.ts` strict target budgets were gated on `PF_PERF_ENFORCE_BUDGETS=1` without CI or Publish enabling the flag. | Enabled `PF_PERF_ENFORCE_BUDGETS=1` in `.github/workflows/ci.yml` (`L3`) and `.github/workflows/publish.yml` (`Gate 2`). |
| `ZOT-DEDUPE` | **P2** | Multi-collection selection in `zotero-import-scope.ts` summed per-collection `item_count`, which could exceed `totalPapers` when papers live in multiple folders. | Capped `estimatedPapers` at `totalPapers` when collections overlap; backend `zotero_sqlite.py` already deduplicates by `itemID` / `zotero_key`. Covered in `zotero-import-scope.test.ts`. |
| `REL-VER` | **Info** | Tag/Pre-release `2.0.11` is already published (`2026-11-27T13:15:04Z`). `publish.yml` Release Identity Gate blocks re-using `2.0.11` on a new SHA. | Owner must bump version (`paperforge/__init__.py`, `manifest.json`, `paperforge/plugin/manifest.json`, `crates/paperforge-daemon/Cargo.toml`) to `2.0.12` (or `2.0.12-rc.1`) when ready to cut a release. |

---

## 3. Release Acceptance Gate Matrix (`G0`–`G9`)

| Gate | Requirement | Enforcement Mechanism | Status |
| --- | --- | --- | --- |
| **G0** | Architecture & Code Integrity (module graph, machine-path scan, ruff `F821-823`, bundle sync) | `.github/workflows/ci.yml` (`L0`, `L3`) | **AUTOMATED PASS** |
| **G1** | PBAF v2.1 Static Safety & Privacy (`--strict`, 14 static gates `0 FAIL, 0 WARN`) | `scripts/backend_audit.py --strict` in `ci.yml` & `ci-chaos.yml` | **AUTOMATED PASS** |
| **G2** | Selective FTS5 Integrity, Tier-0 Sovereignty & Rollback (`PF-R01`, hard-kill, purge-independent restore) | `tests/test_migration_sovereignty_and_healing.py`, `tests/chaos/test_backend_chaos_and_recovery.py` | **AUTOMATED PASS** |
| **G3** | Cross-OS Chaos & Concurrency (Linux, Windows, macOS) | `.github/workflows/ci-chaos.yml` (`L6`) — now required by `publish.yml` | **AUTOMATED PASS** |
| **G4** | Native Rust Daemon Build & Health Protocol (`--version`, `--stdio`) | `ci.yml` (`L1c`) & `publish.yml` (`build-native-daemon`) | **PASS (x64 Linux/Win, arm64 macOS)** / **BUILD-ONLY (ARM64 Linux/Win, Intel macOS)** |
| **G5** | Obsidian Plugin Unit, Protocol Conformance, Typecheck, Build & PDF Runtime Budgets (`PF-R05`) | `ci.yml` (`L3`) & `publish.yml` (`Gate 2`) with `PF_PERF_ENFORCE_BUDGETS=1` | **AUTOMATED PASS** |
| **G6** | Real Obsidian App Integration (`H1` E2E, `H2` Settings/Migration, `P` CLI Acceptance) | `ci.yml` (`H1`, `H2`, `P` on `windows-latest`) | **PASS (Windows)** / **UNVERIFIED (macOS, Linux)** |
| **G7** | Atomic Release Packaging & Byte-Verified Immutability (`PF-R03`) | `.github/workflows/publish.yml` (`Gate 4`) | **WIRED (verified at tag publish)** |
| **G8** | Real-User Large-Library Smoke (>=1,000 papers scratch clone, PBAF `D1-D5`, OCR + Search + Reader) | Isolated scratch clone + PBAF `D5` verification | **MANUAL OWNER SIGN-OFF REQUIRED BEFORE FINAL TAG** |
| **G9** | Clean Version Bump (`2.0.12`) & Signed/Tagged Release Cut | Owner bump PR + tag after PR #438 merges | **PENDING (post-merge)** |

---

## 4. Honest Cross-Platform & Runtime Support Matrix

| Target / Environment | Status | What Is Verified vs. UNVERIFIED |
| --- | --- | --- |
| **Windows x86_64 (Desktop + CLI + Rust Daemon)** | **VERIFIED** | Full CI (`L1b`, `L1c`, `L4`, `L4b`), 3-OS Chaos (`L6`), Real Obsidian E2E (`H1`, `H2`), CLI-host Acceptance (`P`). |
| **macOS Apple Silicon (`aarch64-apple-darwin`)** | **PARTIAL (`GUI UNVERIFIED`)** | Python tests (`J-Matrix`), Rust daemon build + smoke test (`L1c`), 3-OS Chaos (`L6`). **Real Obsidian macOS GUI (`H1`/`H2`): `UNVERIFIED`.** |
| **Linux x86_64 (`x86_64-unknown-linux-musl`)** | **PARTIAL (`GUI UNVERIFIED`)** | Python CI (`L1b` 4 shards), Rust daemon build + smoke (`L1c`), Plugin Vitest (`L3`), 3-OS Chaos (`L6`). **Real Obsidian Linux GUI (`H1`/`H2`): `UNVERIFIED`.** |
| **Linux ARM64 / Windows ARM64 / macOS Intel** | **UNVERIFIED** | Rust cross-compilation only (`publish.yml` `build-native-daemon`); runtime binary execution on target hardware is **`UNVERIFIED`**. |
| **Python 3.12+ / Obsidian Latest vs Minimum (`1.11.4`)** | **UNVERIFIED (CI=3.11)** | CI executes Python `3.11`; `3.12+` runtime matrix and live paid OCR/LLM provider keys are **`UNVERIFIED`** in CI. |
