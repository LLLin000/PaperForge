# Headless E2E and Remote-Service Simulation Research

- Date: 2026-08-09
- Wayfinder ticket: [#155](https://github.com/LLLin000/PaperForge/issues/155)
- Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
- Scope: Repository-grounded acceptance-test research; no production implementation.

Standalone Markdown, repo-grounded (PaperForge `master`, read 2026-08-09). **[VERIFIED repo]** = file path on master; official-doc anchors cited by URL. Destination statement corrected per #155 resolution: **Python alone owns and operates the vault + SQLite; clients (Obsidian plugin / agents) consume CLI read models via versioned JSON; runtime snapshot files retire after consumer cutover** — nothing here assumes clients read SQLite or snapshots. No new test pyramid, no new provider-simulation framework.

---

## 0. Verified current state (reuse, don't rebuild)

| Asset | Path (master) | What it already proves |
|---|---|---|
| Real-subprocess CLI invoker (headless, no GUI/plugin) | `tests/cli/conftest.py` (`cli_invoker`), `tests/e2e/conftest.py` (`e2e_cli_invoker`) — `subprocess.run([sys.executable, "-m", "paperforge", "--vault", str(vault)] + args, capture_output=True, text=True, timeout=60/120, env={...PAPERFORGE_VAULT})` | **The headless E2E pattern**: CLI proven as a standalone process; Obsidian/plugin never runs |
| Fixture vault builder | `fixtures/vault_builder.py` (`VaultBuilder.build("minimal"|"standard"|"full")`) + `tests/conftest.py` (`create_test_vault()` → `tests/sandbox/00_TestVault`) — `paperforge.json`, `.env`, BBT exports, mock PDFs, Zotero storage, OCR fixtures, formal notes | Fixture vault construction exists and is used |
| Deterministic OCR substitute | `fixtures/ocr/mock_ocr_backend.py` + `fixtures/ocr/paddleocr_*.json` + `tests/cli/conftest.py::mock_ocr_backend` — **`responses` library** intercepts PaddleOCR submit/poll/result (success/pending/error/timeout) | Deterministic remote substitute exists; project standard is `responses` |
| Contract fixtures | `tests/cli/test_error_codes.py`, `test_json_contracts.py`, `test_text_contracts.py`, `test_ocr_progress_contracts.py`, `tests/cli/snapshots/` | Exit codes (0/2), `--help`/`--version`, no-traceback errors, deterministic stderr, versioned JSON read models |
| Env-gated real-remote tests | `tests/conftest.py::api_key_available()` — live-embed tests skip unless `VECTOR_DB_API_KEY`/`OPENAI_API_KEY` set | Remote tests already optional; prove provider compatibility only |
| Fault injection / chaos | `tests/chaos/` (`test_corrupted_inputs.py`, `test_filesystem_errors.py`, `test_network_failures.py`) + `.github/workflows/ci-chaos.yml` (weekly `-m chaos --timeout=120`) | Corrupted inputs, FS errors, network failures |
| Cross-platform matrix | `.github/workflows/ci.yml` — `unit-tests` job: `matrix os: [ubuntu-latest, windows-latest, macos-latest] × py3.11`, `--timeout=60` | Windows+POSIX coverage exists |
| Merge gate | `.github/workflows/ci.yml` — `alls-green` `needs:` [version-check, ruff, unit-tests, protocol-tests, ocr-regression, plugin-tests, e2e-tests, architecture-gate] | Required-status-check release gate exists; no merge queue needed |
| Markers | `pyproject.toml [tool.pytest.ini_options]` — `unit, cli, e2e, journey, chaos, audit, integration, e2e_fast, slow, snapshot` + `--strict-markers` | Marker taxonomy exists; reuse |
| SQLite memory DB (WAL) | `paperforge/memory/db.py` (WAL), `paperforge/memory/builder.py` (build→insert→FTS5→meta incl. `canonical_index_hash`→COMMIT) per `.planning/intel/ARCH.md` | Crash-safe SQLite layer Python owns |

**Verified gap:** `ci.yml` wires only `tests/cli/test_ocr_progress_contracts.py` (in `ocr-regression`) and `tests/e2e/ -m e2e` + `tests/audit/ -m audit`; `tests/cli/test_error_codes.py`, `test_json_contracts.py`, `test_text_contracts.py`, `tests/journey/`, `tests/integration/` are not referenced by any job. The smallest matrix is mostly a **wiring fix**.

---

## 1. Smallest acceptance matrix (minimum destination gate)

Destination: prove the **standalone Python product** — Python alone owns/operates the vault and SQLite — by real subprocess journeys against the existing fixture vault with the existing deterministic substitutes, with **no Obsidian/plugin installed or running**; clients consume CLI read models (versioned JSON where machine-consumed; note: a uniform `error` field in that JSON was explicitly deferred by #154 — do not assert it; a `--json` flag on literally every command is likewise not claimed here unless verified per command). Remote providers are never validated by fixtures.

| Gate | Contents | Mechanism (all existing) | Where |
|---|---|---|---|
| **L2 contract (PR, 3-OS matrix)** | `tests/cli/` — exit codes, versioned-JSON/text contracts, OCR progress contract | `cli_invoker` subprocess + `VaultBuilder` + `responses` mock OCR | add `tests/cli/` to the `unit-tests` matrix job (or its own job on `[ubuntu-latest, windows-latest]`) — **[VERIFIED gap]** only `ocr_progress_contracts.py` is wired today |
| **L4 headless E2E (PR)** | `tests/e2e/ -m e2e` (sync pipeline, OCR e2e, status/doctor/repair, multi-domain) + `tests/audit/ -m audit` (validates L1 mocks vs real pipeline output — the "fixtures ≠ remote" honesty guard) | `e2e_cli_invoker` + `full_vault` + `mock_ocr_backend` | already in `ci.yml`; optionally add `tests/journey/ -m journey` |
| **L3 real-remote smoke (release/manual, OPTIONAL)** | live PaddleOCR (real token) + live embedding (env-gated via `api_key_available()`) | existing env-gate pattern | never in the PR gate |
| **Merge gate** | `alls-green` required status checks (L0 version-sync, L0.5 ruff, L1 unit, L2 contract, L2.5 OCR regression, L3 plugin vitest, L4 e2e+audit, L4b architecture gate) | existing | add newly wired jobs to `needs:` |

Windows+POSIX: `tests/cli/` runs on the existing 3-OS matrix (exit codes, path handling, `os.replace`/locking behavior differ). **Windows structured cancellation from the Obsidian host is owned by #150**; a POSIX SIGINT smoke is explicitly optional/deferred (§3).

---

## 2. Exact minimal journeys (minimum gate = J1–J3; J4/J5 optional/deferred)

All journeys: real subprocess `[sys.executable, "-m", "paperforge", "--vault", <fixture_vault>, ...]` via the existing `cli_invoker`/`e2e_cli_invoker`; Obsidian/plugin never installed or running.

- **J1 — CLI contract (exists: `tests/cli/test_error_codes.py`; reuse + wire):** `--version` → exit 0; `--help` → exit 0 + usage; unknown command → exit ≠ 0 + stderr; missing vault → error message, **no traceback**; same error twice → byte-identical stderr (determinism). Where commands are machine-consumed, assert their **versioned JSON read model** (as `test_json_contracts.py` already does for the commands it covers) — without asserting fields #154 deferred.
- **J2 — `sync` headless (exists: `tests/e2e/test_sync_pipeline.py`; reuse + one assertion):** standard vault + BBT export → exit 0; formal notes under `Resources/Literature/<domain>/`; `System/PaperForge/indexes/formal-library.json` parses with ≥1 item; `.base` views generated. **Add:** sha256 of the fixture corpus before/after → only whitelisted paths (System/PaperForge/*, Literature/*, Bases/*) change; exports unchanged; and assert the CLI never creates/writes `.obsidian/*` (vault = plain-Markdown folder; `.obsidian/workspace.json` is Obsidian-owned and churns on file open — https://publish.obsidian.md/help/Advanced+topics/How+Obsidian+stores+data).
- **J3 — OCR with deterministic substitute (exists: `tests/cli/test_ocr_progress_contracts.py` + `mock_ocr_backend`):** `with mock_ocr_backend(): invoker(["ocr", ...])` → submit→poll→result replayed from `fixtures/ocr/*.json`; assert the progress/result contract; `mock_ocr_error(401)`/`mock_ocr_timeout()` branches. **Honesty rule:** proves the OCR pipeline contract against canned data — says nothing about the live PaddleOCR API; only J6 (real-remote) touches the provider.
- **J6 — real-remote smoke (release/manual, OPTIONAL):** live PaddleOCR submit/poll with a real token; live embed when `api_key_available()`. Provider compatibility only.

**Deferred/optional (NOT part of the minimum destination gate):**
- **J4 — `memory build` integrity + crash-resume:** idempotent double-run, `PRAGMA integrity_check = ok` (https://www.sqlite.org/pragma.html), and one kill-mid-build → re-run → recovery test (SQLite recovery is automatic — https://www.sqlite.org/howtocorrupt.html). Belongs in the existing weekly `tests/chaos/` layer when the chaos backlog is expanded; not a requirement for the destination gate.
- **J5 — POSIX cancellation smoke:** send SIGINT to a long-running subprocess (SIGINT → KeyboardInterrupt — https://docs.python.org/3/library/signal.html), assert documented exit code + unchanged vault. Optional and POSIX-only (`skipif win32`); Windows cancellation is **#150's** scope.

---

## 3. Adopt / Defer / Reject

### Adopt (wire or extend what exists — the whole matrix)
1. **Wire `tests/cli/` into the PR gate** (all contract files, not just `ocr_progress_contracts.py`) on the existing matrix. [VERIFIED gap]
2. **Reuse `cli_invoker`/`e2e_cli_invoker`** real-subprocess pattern as THE headless proof (Python `subprocess.run`; pytest's own `pytester` runs pytest as a subprocess — https://docs.pytest.org/en/stable/reference/reference.html#pytester).
3. **Reuse `VaultBuilder` + `create_test_vault`** fixture vaults; add sha256-preservation + `.obsidian`-must-not-touch assertions to J2 (small asserts, no new framework).
4. **Reuse `responses`-based `mock_ocr_backend`** as the deterministic OCR substitute.
5. **Reuse the env-gated real-remote pattern** (`api_key_available`) for the release-only provider smoke.
6. **Reuse markers + `--strict-markers`** and the **`alls-green` merge gate** (add newly wired jobs to `needs:`).
7. **Reuse `tests/audit/`** (`-m audit`: "validate L1 mocks against L4 real pipeline output") as the mandatory honesty guard that local fixtures stay faithful to real output.

### Defer
1. **Windows cancellation/crash-recovery from the Obsidian host** → owned by #150; not built here.
2. **J4 memory-build integrity/crash-resume** → existing weekly chaos layer, when expanded; not a destination-gate requirement.
3. **J5 POSIX cancellation smoke** → optional, POSIX-only, when cancellation semantics matter; not a destination-gate requirement.
4. **GUI/browser smoke (Playwright or real Obsidian)** → release-only manual checklist item; plugin JS logic already covered by vitest (`ci.yml` L3 job). Not part of this matrix.
5. **Merge queue (GitHub)** → `alls-green` required checks already gate merges; single-maintainer repo; revisit only if merge contention appears.

### Reject
1. **VCR.py record/replay** — project already standardized on `responses` with committed fixture JSON; VCR adds a second HTTP-simulation framework and its re-record cadence solves a problem the release-only real-remote smoke already solves.
2. **text2image / Tesseract synthetic OCR images** — OCR is a remote PaddleOCR API; the deterministic substitute is canned JSON via `responses`, already in place. No native OCR dependency needed.
3. **New Protocol seams for OCR/embedding** — adapter/service layering + transport-level `responses` interception already provide the seam.
4. **New marker taxonomy** — existing 10 markers suffice.
5. **PR-gating real-remote tests** — env-gated, release/manual only (existing `api_key_available` pattern).
6. **Playwright workflow prescriptions** — plugin E2E in real Obsidian is out of scope for #155; vitest + manual release checklist cover it.
7. **Asserting a uniform PFResult `error` field or `--json` on every command** — #154 deferred the error field and per-command `--json` is unverified; assert versioned JSON only where machine-consumed and verified.

---

## 4. Evidence anchors (primary)
- PaperForge repo files (read-only, master): `tests/cli/conftest.py`, `tests/e2e/conftest.py`, `tests/e2e/test_sync_pipeline.py`, `tests/cli/test_error_codes.py`, `fixtures/vault_builder.py`, `fixtures/ocr/mock_ocr_backend.py`, `tests/conftest.py`, `.github/workflows/ci.yml`, `.github/workflows/ci-chaos.yml`, `pyproject.toml`, `.planning/intel/ARCH.md` — https://github.com/LLLin000/PaperForge.
- Official guidance: Python `subprocess` https://docs.python.org/3/library/subprocess.html · pytest `pytester` https://docs.pytest.org/en/stable/reference/reference.html#pytester · pytest markers https://docs.pytest.org/en/stable/how-to/mark.html · pytest skipif https://docs.pytest.org/en/stable/how-to/skipping.html · SQLite `PRAGMA integrity_check` https://www.sqlite.org/pragma.html · SQLite crash recovery https://www.sqlite.org/howtocorrupt.html · Python `signal` https://docs.python.org/3/library/signal.html · GitHub Actions matrix https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/running-variations-of-jobs-in-a-workflow · required status checks https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches · Obsidian vault storage https://publish.obsidian.md/help/Advanced+topics/How+Obsidian+stores+data · JSON Canvas 1.0 https://jsoncanvas.org/spec/1.0/ · pytest flaky (split suites, delete covered tests) https://docs.pytest.org/en/stable/explanation/flaky.html · pytest-timeout https://pypi.org/project/pytest-timeout/ · VCR.py record modes (why rejected) https://vcrpy.readthedocs.io/en/latest/usage.html · Tesseract text2image (why rejected) https://github.com/tesseract-ocr/tesseract/blob/main/doc/text2image.1.asc · PaperForge #155 (this ticket) and #150 (Windows cancellation owner).

## 5. Open risks / notes for the parent
1. **Destination assumption:** clients consume CLI read models (versioned JSON); runtime snapshot files retire after consumer cutover — the acceptance matrix does not depend on snapshots or on clients reading SQLite.
2. **CI wiring gap is the real work:** confirm whether `tests/unit/` exists and whether `tests/cli/*` (non-OCR), `tests/journey/`, `tests/integration/` are collected anywhere; if not, add them to the matrix jobs (smallest diff: extend `unit-tests` and `e2e-tests` run paths).
3. `.obsidian/workspace.json`-touch contract: fixture corpus has no `.obsidian` today; J2's assertion must tolerate its absence and fail if it appears.
4. The `audit` layer is the project's existing "fixtures ≠ remote" honesty mechanism — keep it mandatory.
5. Everything above is read-only research; no repo files were modified.