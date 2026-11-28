# PaperForge 2.0 Release Acceptance Gate (RAGate) & Audit Ledger

> **Target Candidate**: PR `#438` (`feat/pbaf-v2.1-hardening` -> `master`) — see the live GitHub Checks attached to the PR HEAD commit and the release tag run at publish time.
> **Current Verdict**: **CONDITIONAL GO** — Engineering & Automated Cross-OS CI Gates pass; awaiting owner version bump (`2.0.11` -> `2.0.12`, since tag `2.0.11` is already an existing Pre-release) and owner sign-off on manual desktop UX + live-provider smoke items before cutting `2.0.12`.

---

## 1. Readiness Tier Summary

| Tier | Status | Notes |
| --- | --- | --- |
| **Engineering Ready** | **PASS** | Unit/protocol suites, PBAF v2.1 `--strict`, FTS5 selective-index + sampled same-rowid content-drift contract (`PF-R01`), PDF runtime budget assertions (`PF-R05`), macOS/Linux PATH precedence fix, and 4-cell Chaos suite (3 OSes × 3.11 + Ubuntu 3.12) pass on PR #438 HEAD. |
| **Product Ready** | **CONDITIONAL PASS** | Verified across Windows (`CI`), macOS Apple Silicon & Linux x86_64 real Obsidian GUI `H1`/`H2` + POSIX signal stop (`Cross-OS`), plus isolated 1,358-paper scratch vault benchmarks. Full multi-view Obsidian UX walk-through, complex real-world PDF stress load, and live paid OCR/LLM keys require owner smoke sign-off. |
| **Distribution Ready** | **CONDITIONAL PASS** | Release Chaos Gate (`PF-R02`), Cross-OS Desktop Gate (`ci-cross-os-desktop.yml`), and unified Draft-first exact-asset-set + remote SHA-256 byte verification (`PF-R03`) are wired into `.github/workflows/publish.yml` and await first live execution on tag `2.0.12`. |

---

## 2. Pre-Release Audit Findings Resolution (`PF-R01` .. `PF-R05` + Follow-Ups)

| ID | Severity | Finding Summary | Resolution & Verification |
| --- | --- | --- | --- |
| `PF-R01` | **P0** | `rebuild_fts_indexes` / `check_and_heal_fts` ran native `VALUES('rebuild')` on external-content `body_units_fts`; `gateway.py` / `embedding/search.py` missed `bu.indexable = 1`; PBAF `D5` used naive `COUNT(*)`; `clear_fts` used `DELETE FROM`; `prune.py` used incomplete delete columns; same-rowid text updates without FTS sync evaded `integrity-check` and `docsize` count. | Fixed `paperforge/memory/db.py` (`_rebuild_body_units_fts` + `_body_units_fts_content_drifted` sampled rowid-bound `MATCH` parity check), `schema.py`, `worker/prune.py`, `retrieval/gateway.py`, `embedding/search.py`, and `scripts/backend_audit.py` (`D5` `docsize` + orphan join + sampled rowid-bound `MATCH` + empty carrier `WARN`). Covered in `tests/test_migration_sovereignty_and_healing.py`. |
| `PF-R02` | **P1** | `ci-chaos.yml` (`L6`) only ran on schedule/manual dispatch and did not block `publish.yml`. | Added `workflow_call` to `.github/workflows/ci-chaos.yml` (expanded with `ubuntu-latest` Python `3.12`) and wired `chaos-gate` into `.github/workflows/publish.yml` (`publish.needs: [build-native-daemon, chaos-gate, cross-os-desktop-gate]`). |
| `PF-R03` | **P1** | `publish.yml` created a public Release before uploads and skipped remote byte verification on fresh uploads / missing-asset uploads. | Refactored `.github/workflows/publish.yml` to create releases as `--draft`, run a unified Final Remote Verification Gate checking exact remote asset set equality, `checksums.txt` byte identity, and downloaded SHA-256 bytes for every asset before `--draft=false`. |
| `PF-R04` | **P1** | Desktop GUI (`H1`/`H2`) and CLI-host acceptance (`P`) previously ran on Windows only. | Added `.github/workflows/ci-cross-os-desktop.yml` (`ubuntu-latest` + `macos-latest` × `H1`/`H2`/POSIX `P` stop; triggered on `master` push, weekly schedule, `workflow_call`, and `publish.yml`), resolving real macOS/Linux `PATH`-shadowing in `node-transport.ts`, POSIX `recorder.py` stdin close, and LF fixture `result-hash.txt` restamping. |
| `PF-R05` | **P1** | `perf-pdf-runtime.test.ts` strict budgets (`PF_PERF_ENFORCE_BUDGETS=1`) were opt-in only. | Enabled `PF_PERF_ENFORCE_BUDGETS=1` in `.github/workflows/ci.yml` (`L3`) and `.github/workflows/publish.yml` (`Gate 2`). |
| `ZOT-DEDUPE` | **P2** | Multi-collection `estimatedPapers` could exceed `totalPapers`. | Capped `estimatedPapers` at `totalPapers` upper bound in `zotero-import-scope.ts`; backend `zotero_sqlite.py` deduplicates by `itemID` / `zotero_key` during sync. |
| `REL-VER` | **Info** | Tag/Pre-release `2.0.11` is already published (`2026-11-27T13:15:04Z`). | Owner must bump version (`2.0.11` -> `2.0.12`) before tagging after PR #438 merges. |

---

## 3. Release Acceptance Gate Matrix (`G0`–`G9`)

| Gate | Requirement | Enforcement Mechanism | Status |
| --- | --- | --- | --- |
| **G0** | Architecture & Code Integrity (module graph, machine-path scan, ruff `F821-823`, bundle sync) | `.github/workflows/ci.yml` (`L0`, `L3`) | **AUTOMATED PASS** |
| **G1** | PBAF v2.1 Static Safety & Privacy (`--strict`, 14 static gates `0 FAIL, 0 WARN`) | `scripts/backend_audit.py --strict` in `ci.yml` & `ci-chaos.yml` | **AUTOMATED PASS** |
| **G2** | Selective FTS5 Parity, Transactional Upsert, Tier-0 Sovereignty & Rollback | `tests/test_migration_sovereignty_and_healing.py`, `tests/chaos/test_backend_chaos_and_recovery.py` | **AUTOMATED PASS** |
| **G3** | Cross-OS Chaos & Concurrency (Linux py3.11 + py3.12, Windows py3.11, macOS py3.11) | `.github/workflows/ci-chaos.yml` (`L6`) — required by `publish.yml` | **AUTOMATED PASS** |
| **G4** | Native Rust Daemon Build & Health Protocol (`--version`, `--stdio`) | `ci.yml` (`L1c`) & `publish.yml` (`build-native-daemon`) | **PASS (x64 Linux/Win, arm64 macOS)** / **BUILD-ONLY (ARM64 Linux/Win, Intel macOS)** |
| **G5** | Obsidian Plugin Unit, Protocol Conformance, Typecheck, Build & PDF Runtime Budgets (`PF-R05`) | `ci.yml` (`L3`) & `publish.yml` (`Gate 2`) with `PF_PERF_ENFORCE_BUDGETS=1` | **AUTOMATED PASS** |
| **G6** | Real Obsidian App Integration (`H1` E2E, `H2` Settings/Migration, `P` CLI Acceptance + POSIX Stop) | `ci.yml` (`H1`/`H2`/`P` Windows) + `ci-cross-os-desktop.yml` (`H1`/`H2`/POSIX `P` macOS & Linux) | **PASS (Windows, macOS Apple Silicon, Linux x86_64; latest Obsidian)** |
| **G7** | Unified Draft-First Atomic Release Packaging & Remote SHA-256 Byte Verification (`PF-R03`) | `.github/workflows/publish.yml` (`Gate 4`) | **WIRED (first live execution on tag `2.0.12`)** |
| **G8** | Manual Large-Library Ergonomic & Visual Walk-Through + Small-Scale Paid OCR/LLM End-to-End Check | Owner desktop smoke on isolated clone vault (Obsidian Settings, Bases, OCR Workspace, PDF Reader, Companion) | **MANUAL OWNER SIGN-OFF BEFORE `2.0.12`** |
| **G9** | Clean Version Bump (`2.0.12`) & Signed/Tagged Release Cut | Owner bump PR + tag after PR #438 merges | **PENDING (post-merge)** |

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
