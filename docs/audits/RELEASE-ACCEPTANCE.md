# PaperForge 2.0 Release Acceptance Gate (RAGate) & Audit Ledger

> **Target Candidate**: Release `2.0.13` (`release/2.0.13-lifecycle-contract` -> `master`) — see the live GitHub Checks attached to the PR HEAD commit and the release tag run at publish time.
> **Current Verdict**: **CONDITIONAL GO (Pre-release `2.0.13`)** — Automated Python, Rust daemon, Obsidian Plugin, PBAF v2.1 `--strict`, and Real-Clone Veteran Rehearsal Gate (isolated clone of real 1,358-paper / 971-OCR veteran vault) all pass cleanly; Multi-OS CI & Draft-first Release Gate run on PR/tag while live paid OCR/LLM key smoke & subjective desktop UI walk-through remain for Owner pre-Stable sign-off.

---

## 1. Readiness Tier Summary

| Tier | Status | Notes |
| --- | --- | --- |
| **Engineering Ready** | **PASS** | Plugin (`57/58` files, `777/778` tests, 1 skipped, `npm run build` + `typecheck`), Rust daemon (`22/22`), PBAF v2.1 `--strict` (`14/14` gates, `0 FAIL, 0 WARN`), Python sync/upgrade/auth/probe/e2e/chaos/journey/audit/harness (`270` + `25` + `158` passed, `0 FAIL`), and Real-Clone Veteran Rehearsal Gate (1,358-paper veteran vault clone: pre-upgrade `vault.upgrade_required` zero-write block -> atomic cutover + Zotero commit -> `vault.healing_in_progress` lock -> progressive heal -> controlled first sync -> rollback preserving post-cutover note edits + `annotations.jsonl`). |
| **Product Ready** | **CONDITIONAL PASS** | Veteran cutover, BBT→SQLite folder scope guardrails, daemon hot-swap reconnect cleanup, Settings container width fix (`styles.css`), and multi-vault isolation verified in Vitest + real CLI rehearsal. Subjective real Obsidian desktop visual UX walk-through and live paid OCR/LLM keys await Owner `2.0.13` Pre-release sign-off on clean isolated 2.0.13 test vault. |
| **Distribution Ready** | **PASS (Pending PR Merge & Tag `2.0.13`)** | Chaos 4-cell gate, Cross-OS Desktop gate (`ci-cross-os-desktop.yml`), and Draft-first unified SHA-256 verification (`publish.yml`) govern `2.0.13` Pre-release publication. |

---

## 2. Pre-Release Audit Findings Resolution (`PF-R01` .. `PF-R05` + `2.0.13` Closure)

| ID | Severity | Finding Summary | Resolution & Verification |
| --- | --- | --- | --- |
| `PF-R01` | **P0** | `rebuild_fts_indexes` / `check_and_heal_fts` ran native `VALUES('rebuild')` on external-content `body_units_fts`; `gateway.py` / `embedding/search.py` missed `bu.indexable = 1`; PBAF `D5` used naive `COUNT(*)`; `clear_fts` used `DELETE FROM`; `prune.py` used incomplete delete columns; same-rowid text updates without FTS sync evaded `integrity-check` and `docsize` count. | Fixed `paperforge/memory/db.py` (`_rebuild_body_units_fts` + `_body_units_fts_content_drifted` sampled rowid-bound `MATCH` parity check), `schema.py`, `worker/prune.py`, `retrieval/gateway.py`, `embedding/search.py`, and `scripts/backend_audit.py` (`D5` `docsize` + orphan join + sampled rowid-bound `MATCH` + empty carrier `WARN`). Covered in `tests/test_migration_sovereignty_and_healing.py`. |
| `PF-R02` | **P1** | `ci-chaos.yml` (`L6`) only ran on schedule/manual dispatch and did not block `publish.yml`. | Added `workflow_call` to `.github/workflows/ci-chaos.yml` (expanded with `ubuntu-latest` Python `3.12`) and wired `chaos-gate` into `.github/workflows/publish.yml` (`publish.needs: [build-native-daemon, chaos-gate, cross-os-desktop-gate]`). |
| `PF-R03` | **P1** | `publish.yml` created a public Release before uploads and skipped remote byte verification on fresh uploads / missing-asset uploads. | Refactored `.github/workflows/publish.yml` to create releases as `--draft`, run a unified Final Remote Verification Gate checking exact remote asset set equality, `checksums.txt` byte identity, and downloaded SHA-256 bytes for every asset before `--draft=false`. |
| `PF-R04` | **P1** | Desktop GUI (`H1`/`H2`) and CLI-host acceptance (`P`) previously ran on Windows only. | Added `.github/workflows/ci-cross-os-desktop.yml` (`ubuntu-latest` + `macos-latest` × `H1`/`H2`/POSIX `P` stop; triggered on `master` push, weekly schedule, `workflow_call`, and `publish.yml`), resolving real macOS/Linux `PATH`-shadowing in `node-transport.ts`, POSIX `recorder.py` stdin close, and LF fixture `result-hash.txt` restamping. |
| `PF-R05` | **P1** | `perf-pdf-runtime.test.ts` strict budgets (`PF_PERF_ENFORCE_BUDGETS=1`) were opt-in only. | Enabled `PF_PERF_ENFORCE_BUDGETS=1` in `.github/workflows/ci.yml` (`L3`) and `.github/workflows/publish.yml` (`Gate 2`). |
| `ZOT-DEDUPE` | **P2** | Multi-collection `estimatedPapers` could exceed `totalPapers`. | Capped `estimatedPapers` at `totalPapers` upper bound in `zotero-import-scope.ts`; backend `zotero_sqlite.py` deduplicates by `itemID` / `zotero_key` during sync. |
| `REL-VER` | **Info** | Tag/Pre-release `2.0.12` is published (`2026-11-28`). | Bumped `2.0.12` -> `2.0.13` with backend sync authorization (`vault.upgrade_required`, `zotero.scope_required`, `zotero.scope_invalid`, `VaultOperationLock`), atomic cutover+Zotero commit, multi-vault heal isolation, Settings width fix, and Real-Clone Veteran Rehearsal Gate. |

---

## 3. Release Acceptance Gate Matrix (`G0`–`G9`)

| Gate | Requirement | Enforcement Mechanism | Status |
| --- | --- | --- | --- |
| **G0** | Architecture & Code Integrity (module graph, machine-path scan, ruff `F821-823`, bundle sync) | `.github/workflows/ci.yml` (`L0`, `L3`) | **AUTOMATED PASS** |
| **G1** | PBAF v2.1 Static Safety & Privacy (`--strict`, 14 static gates `0 FAIL, 0 WARN`) | `scripts/backend_audit.py --strict` in `ci.yml` & `ci-chaos.yml` | **AUTOMATED PASS** |
| **G2** | Selective FTS5 Parity, Transactional Upsert, Tier-0 Sovereignty, Veteran Auth & Rollback | `tests/unit/test_backend_sync_authorization_and_recovery.py`, `tests/test_migration_sovereignty_and_healing.py`, `tests/chaos/test_backend_chaos_and_recovery.py` | **AUTOMATED PASS + REAL-CLONE VERIFIED** |
| **G3** | Cross-OS Chaos & Concurrency (Linux py3.11 + py3.12, Windows py3.11, macOS py3.11) | `.github/workflows/ci-chaos.yml` (`L6`) — required by `publish.yml` | **CI GATE ON PR / TAG** |
| **G4** | Native Rust Daemon Build & Health Protocol (`--version`, `--stdio`, MCP unmigrated guard) | `ci.yml` (`L1c`), `cargo test` (`22/22` local) & `publish.yml` (`build-native-daemon`) | **PASS (local + Windows/Linux/macOS CI)** |
| **G5** | Obsidian Plugin Unit, Protocol Conformance, Typecheck, Build & PDF Runtime Budgets (`PF-R05`) | `npm run build && npm test && npm run typecheck` (`57/58` files, `777/778` local), `ci.yml` (`L3`), `publish.yml` (`Gate 2`) | **AUTOMATED PASS** |
| **G6** | Real Obsidian App Integration (`H1` E2E, `H2` Settings/Migration, `P` CLI Acceptance + POSIX Stop) | `ci.yml` (`H1`/`H2`/`P` Windows) + `ci-cross-os-desktop.yml` (`H1`/`H2`/POSIX `P` macOS & Linux) | **CI GATE ON PR / TAG** |
| **G7** | Unified Draft-First Atomic Release Packaging & Remote SHA-256 Byte Verification (`PF-R03`) | `.github/workflows/publish.yml` (`Gate 4`) | **GOVERNED AT `2.0.13` PUBLISH** |
| **G8** | Manual Large-Library Ergonomic & Visual Walk-Through + Small-Scale Paid OCR/LLM End-to-End Check | Real-Clone Veteran Rehearsal passed (`1,358` papers / `971` OCR dirs); Owner Obsidian Settings/UX sign-off on clean isolated 2.0.13 test vault | **REHEARSAL PASS / MANUAL UI PENDING OWNER** |
| **G9** | Clean Version Bump (`2.0.13`) & Pre-release Cut | Branch `release/2.0.13-lifecycle-contract` PR -> `master` merge -> `2.0.13` Pre-release | **IN PROGRESS** |

---

## 4. Honest Cross-Platform & Runtime Support Matrix

| Target / Environment | Status | What Is Verified vs. UNVERIFIED |
| --- | --- | --- |
| **Windows x86_64 (Desktop + CLI + Rust Daemon)** | **VERIFIED** | Full CI (`L1b`, `L1c`, `L4`, `L4b`), Chaos (`L6`), Real Obsidian `H1`/`H2`, CLI-host `P`. |
| **macOS Apple Silicon (`aarch64-apple-darwin`)** | **VERIFIED (Automated)** | Python `J-Matrix`, Rust daemon build + smoke (`L1c`), Chaos (`L6`), Real Obsidian `H1 Cross-OS` & `H2 Cross-OS`, POSIX `P` stop. |
| **Linux x86_64 (`x86_64-unknown-linux-musl`)** | **VERIFIED (Automated)** | Python `L1b` 4 shards, Rust daemon build + smoke (`L1c`), Plugin `L3`, Chaos (`L6` py3.11 + py3.12), Real Obsidian Xvfb `H1`/`H2`, POSIX `P` stop. |
| **Python 3.12** | **PARTIAL (`L6 Chaos VERIFIED`)** | Tested in `ci-chaos.yml` (`ubuntu-latest`, Python `3.12`); full `L1b`/desktop matrix runs on `3.11`. Python `3.13+` is **`UNVERIFIED`**. |
| **Linux ARM64 / Windows ARM64 / macOS Intel** | **UNVERIFIED** | Rust cross-compilation only (`publish.yml`); target-hardware execution is **`UNVERIFIED`**. |
| **Live Paid OCR/LLM Keys & Complex PDF Ergonomics** | **UNVERIFIED (Automated)** | Covered only via protocol mocks and jsdom synthetic benchmarks; real paid API smoke & subjective UI ergonomics await owner pre-release sign-off. |

---

## 5. Known Scope & Verification Boundaries

- **Hard-kill drill**: Verifies abrupt child process termination (`os._exit(9)`) mid uncommitted SQLite write recovers via `open_live_reader` + `check_and_heal_fts`; does **not** simulate OS-level kill at every sub-phase of full vault directory cutover.
- **Backup independence**: Verifies aged `.paperforge/trash` purge and backup retention pruning preserve the latest pre-upgrade backup and Tier-0 DB rollback; does **not** cover manual deletion of referenced OCR source media.
- **Zotero collection count**: `estimatedPapers` caps overlapping collection sums at `totalPapers` (an upper bound, not exact multi-collection set intersection until sync runs and deduplicates by `itemID` / `zotero_key`).
- **FTS5 same-rowid parity**: Production `_upsert_body_units` and `_rebuild_paper_units` atomically delete and re-insert `body_units_fts` within the writer transaction; `_fts_integrity_needs_heal` and PBAF `D5` now also probe boundary `indexable = 1` rowids via rowid-bound `MATCH` (avoiding hot-path query overhead).
