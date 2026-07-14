# Wayfinder #73 — Migration & Acceptance Specification

**Date:** 2026-07-15 | **Parent:** [Issue #73](https://github.com/LLLin000/PaperForge/issues/73) | **Prerequisites:** #69, #70, #71, #72

---

## 0. Locked Decisions (from #69/#70, override scout speculation)

| Domain | Decision | Source |
|--------|----------|--------|
| 维护 is a derived view | No independent probe. Aggregates non-ready states of five modules. | #69 §1 |
| Stale is never ready | TTL-expired envelope renders as `unknown`, never as stored state. | #69 §1 |
| Backend owns facts and actions | Plugin never reclassifies severity, derives actions, or decides maintenance visibility. | #69 §1 |
| Source materials preserved on destructive ops | Redo never deletes raw images/exports/config without confirmation. | #69 §1 |
| API keys migrate to Obsidian SecretStorage | `minAppVersion` becomes 1.11.4. **N:** copy to SecretStorage, readback-verify, then delete `data.json` plaintext. Failed verification retains legacy value as fallback-with-warning. **N+1:** all **plugin** credential reads use SecretStorage exclusively. **N+2:** remove legacy plaintext readers. Headless CLI may continue `.env` inputs via `embedding/_config.py`. | #73 locked (user contract) |
| macOS auto-download disabled until signed | Published checksummed artifacts must pass x64/arm64 smoke gates; no Gatekeeper bypass instructions. | #73 locked (user contract) |
| Flatpak/Snap unsupported in first release | Detect and explain native/AppImage/deb/external Python alternatives. | #73 locked (user contract) |
| Three-release cutover | N: SecretStorage copy-verify-delete, capability envelope, ManagedRuntime with read-only fallbacks; v1 READ fallback active, v1 writes avoided. N+1: all new writes use vault_config only; v1 READ fallback still accepted. N+2: remove v1 reader, old setup_complete, old resolvers, legacy snapshots. | #73 locked (user contract) |
| Python 3.11+ for new/repair runtime | Existing verified 3.10 survives N with deprecation warning. New installs and all repairs use 3.11+. All manual-install instructions say 3.11+. At N+1, 3.10 becomes `needs_repair`. | #73 locked (user contract) |
| Stay on Obsidian 1.11.4, imperative PluginSettingTab | No declarative 1.13 requirement or Workspace View. | #73 locked (user contract) |
| No credentials through ManagedRuntime | Operation subprocesses get only explicit ephemeral secrets; ManagedRuntime never receives them. | #70 §Security |
| Single resolver after Phase 2 | Every command dispatch reads from `runtime.current().pythonPath`. | #70 §Acceptance 9 |
| Orthogonal capability/activity/attention | Activity never masks availability; maintenance is derived projection. | #69 §2 |
| **Managed runtime is machine-local, shared across vaults** | Runtime directory is `~/.paperforge/runtime/{os-arch}/v{version}` outside vault, outside Obsidian Sync. Active pointer file at `~/.paperforge/runtime/active-runtime.json`. One runtime identity per machine shared by all PaperForge vaults. No secrets in runtime paths. | #73 refinement of #70 |

---

## 1. Three-Release Cutover

| Area | N | N+1 | N+2 (shim removal) |
|------|----|-----|---------------------|
| **Config migration** | v1 fallback reads top-level keys with warning; vault_config authoritative for v2+ | All writes new-only (vault_config). v1 READ fallback still accepted | Delete read-side v1 reader |
| **Plugin settings** | Add `capability_state` map alongside `setup_complete`. Migrate old `true` -> all `unknown`. `_autoUpdate` gated on installation capability, not global bool | `saveSettings` excludes path fields; all callers read from `paperforge.json` | Remove `setup_complete` from I/O; remove rendering |
| **Runtime identity** | `ManagedRuntime` class added. Machine-local `~/.paperforge/runtime/{os-arch}/v{version}`. `status()` reads `active-runtime.json` at `~/.paperforge/runtime/`; absent -> fall back to existing resolvers | Setup wizard uses `runtime.ensure()`. Existing users get one prompt for migration | Remove `resolvePythonExecutable`, `getCachedPython`, `getVectorRuntime`, `checkRuntimeVersion`, `buildRuntimeInstallCommand` |
| **Python min version** | 3.10 verified accepted with deprecation warning; new installs/repairs require 3.11+ | 3.10 becomes `needs_repair`; `ensure()` rejects <3.11 | — |
| **Snapshots** | v2 schema with `runtime_identity`, `config_revision`, `canonical_index_revision`, `source_db_revision`, `ttl_seconds` | Plugin rejects schema<2 or age>TTL as `stale` | Remove v1-only read path |
| **Maintenance cache** | Add `cache_version` field; Python backend owns `action`/`label`/`severity`/`visible` | Delete `categorizeMaintenanceRow` + derived TS types; render from backend fields | Remove cache_version compat |
| **Vector build-state** | Keep legacy JSON read path; all writes go to SQLite `build_state` | Stop writing JSON | Remove `get_vector_build_state_path` |
| **Credentials** | Copy to SecretStorage, readback-verify, then delete `data.json` plaintext. Failed verify retains legacy as fallback-with-warning. Headless CLI may continue `.env`. | All N+1 **plugin** credential reads use SecretStorage only. Headless CLI retains `.env`/env. Legacy fallback removed from plugin | Remove legacy plaintext credential readers from plugin |
| **Setup paths** | Merge headless + modular into one canonical engine. Legacy bare `setup` delegates with deprecation warning. Fix P0 pip-skip, P1 literature-dir drop, P1 JSON exit code | Bare `setup` routes exclusively to canonical modular engine (no error). Legacy TUI inactive | Delete legacy TUI code |
| **Obsidian API** | Stay on 1.11.4 imperative `PluginSettingTab`; Obsidian 1.13+ features MAY appear in research but not required | — | — |
| **Platform detection** | Flatpak/Snap -> explanation + manual alternative. macOS auto-download disabled | Add Flatpak/Snap test if user demand appears | — |

---

## 2. Compatibility Migration Tables

### 2.1 `paperforge.json` path schema

| Aspect | Detail |
|--------|--------|
| **Current** | Python: `top_level OVERRIDES vault_config`. Plugin: `vault_config OVERRIDES top_level`. `savePaperforgeJson` deletes top-level path keys. `load_vault_config` strips `schema_version` from output. |
| **Target** | N: `v1` fallback reads top-level keys with warning; `v2` vault_config only. Plugin and Python share same precedence. |
| **Schema version** | `schema_version: 2` in `paperforge.json` (file format). `load_vault_config` returns version with paths. |
| **Rollback** | v1 READ fallback active N and N+1; removed at N+2. Starting N+1, all writes are vault_config-only. Downgraded plugin reads vault_config-only file (reads v1 if present). |
| **Test seam** | `unit/config/test_load_vault_config.py` — v1 vs v2 fixture. `unit/plugin/test_readPaperforgeJson.ts` — same. |
| **Files** | `paperforge/config.py:166-337` (load_vault_config, paperforge_paths). `plugin/src/main.ts:224-300` (readPaperforgeJson, savePaperforgeJson). `plugin/src/services/memory-state.ts:79-116` (readPathConfig). `paperforge.json` (root config). |

### 2.2 Global `setup_complete` -> per-module capability_state

| Aspect | Detail |
|--------|--------|
| **Current** | `PaperForgeSettings.setup_complete` bool at `constants.ts:73`. Invalidated only when `paperforge.json` missing (`settings.ts:191-196`). Gates `_autoUpdate` (`main.ts:78`). Contradictory wizard validation (`step3-gate.ts:3-10` vs `modals.ts:766-775`). |
| **Target** | `capabilityState: Record<string, CapabilityState>` alongside `setup_complete` in N. Migrate old `true` -> all `unknown`. `_autoUpdate` gated on `installation.capability_state`. |
| **Versioning** | Plugin `data.json` schema version tracked internally. Migration runs once on load. |
| **Idempotence** | Re-migration at same state writes same capabilityState. |
| **Rollback** | **Most dangerous** — changes auto-update gate. Mitigation: `override_to_ready` escape hatch in plugin settings on N. |
| **Test seam** | `unit/plugin/test_capability_state.ts` (load old data.json). `unit/plugin/test_auto_update_gate.ts`. |
| **Files** | `plugin/src/constants.ts:69-113` (PaperForgeSettings). `plugin/src/main.ts:78,307-325` (loadSettings, _autoUpdate). `plugin/src/settings.ts:180-230` (render setup_complete). `plugin/src/views/modals.ts:617-775` (Wizard). `plugin/src/views/step3-gate.ts:3-10`. |

### 2.3 Duplicate Python resolvers -> ManagedRuntime
| Aspect | Detail |
|--------|--------|
| **Current** | `resolvePythonExecutable` (python-bridge.ts:62-117) — one-shot. `getCachedPython` (memory-state.ts:274-303) — process-global cache, Windows-only venv candidates. `getVectorRuntime` (memory-state.ts:173-221) — independent Windows-only crawl. All non-functional on POSIX. |
| **Target** | `ManagedRuntime` class (plugin/src/services/managed-runtime.ts). Directory: `~/.paperforge/runtime/{os-arch}/v{version}` outside vault. Single pointer at `~/.paperforge/runtime/active-runtime.json`. `current()` sync, fails closed. `status()` async probe. `ensure()` builds/verifies slots. N: coexists, absent -> current resolver. N+1: setup uses ensure(). N+2: old resolvers removed. |
| **Versioning** | `active-runtime.json` schema_version. `status()` returns `stale: true` when cache outside TTL. |
| **Idempotence** | Deterministic given same filesystem and perms. Caching prevents re-resolution. |
| **Rollback** | Manual `python_path` override still takes priority. Old slots kept (2) before cleanup. |
| **Test seam** | `unit/plugin/test_managed_runtime.ts` (mocked fs+exec). `unit/plugin/test_resolver_cache_invalidation.ts`. `integration/test_runtime_lifecycle.py`. `e2e/test_runtime_rollback.py`. |
| **Files** | `plugin/src/services/python-bridge.ts:62-117`. `plugin/src/services/memory-state.ts:173-303`. `~/.paperforge/runtime/` (machine-local runtime dir). `.worktrees/retrieval-recovery/docs/research/2026-07-14-managed-runtime-architecture.md §Interface §Directory Layout §Migration`. |
### 2.4 Memory/vector snapshot freshness

| Aspect | Detail |
|--------|--------|
| **Current** | `state_snapshot.py:17-71` — schema_version=1, updated_at only. Plugin `buildSnapshot` (memory-state.ts:305-353) — no freshness check. Stale green renders as `ready`. |
| **Target** | v2 schema with `runtime_identity`, `config_revision`, `canonical_index_revision`, `source_db_revision`, `computed_at`. Plugin rejects schema<2 or age>TTL as `stale`. Backfill v1 on first read. |
| **Versioning** | `schema_version` gates check. Plugin rejects <2 -> stale -> triggers refresh. |
| **Idempotence** | Overwrite-always write. Same inputs -> same snapshot (modulo timestamps). |
| **Rollback** | Backfill corruption -> stale triggers re-probe; safe. |
| **Test seam** | `unit/embedding/test_snapshot_v2.py`. `unit/plugin/test_snapshot_freshness.ts`. `integration/test_snapshot_lifecycle.py`. |
| **Files** | `paperforge/memory/state_snapshot.py:17-71`. `plugin/src/services/memory-state.ts:305-380` (buildSnapshot, isMemoryReady, isVectorReady). |

### 2.5 OCR maintenance cache

| Aspect | Detail |
|--------|--------|
| **Current** | `ocrMaintenanceCachePath` (ocr-maintenance-ui.ts:127-134) hardcodes `System/PaperForge/cache/`. `categorizeMaintenanceRow` (62-118) type-over-type duplication of backend logic. `MaintenanceCache` (37-40) has no version field. |
| **Target** | Path uses `resolveVaultPaths()` for correct paperforge dir + `cache/ocr_maintenance.json`. Delete `categorizeMaintenanceRow` + derived types. Add `cache_version` field to `MaintenanceCache`. Render from backend fields. |
| **Versioning** | `cache_version` integer in cache. Bump on display schema changes. Miss -> full refresh. |
| **Idempotence** | Overwrite-always cache write. Same backend data -> same cache (modulo timestamps). |
| **Rollback** | Old cache at wrong path -> stale -> full refresh, slightly slower first load. Old plugin reads old hardcoded path (no effect). `cache_version` gate ensures old cache schema rejected. |
| **Test seam** | `unit/plugin/test_maintenance_cache_path.ts`. `unit/plugin/test_maintenance_display.ts`. `unit/plugin/test_cache_version.ts`. `unit/plugin/test_incremental_refresh.ts`. |
| **Files** | `plugin/src/services/ocr-maintenance-ui.ts:37-243`. `paperforge/worker/ocr_maintenance.py:284-393` (compute_maintenance_manifest, collect_maintenance_rows). |

### 2.6 Embedding credential resolution

| Aspect | Detail |
|--------|--------|
| **Credential handoff protocol** | Plugin launcher reads SecretStorage immediately before an OCR or Memory subprocess, passes the single required token in an allowlisted ephemeral env var (`PADDLEOCR_API_TOKEN`, `VECTOR_DB_API_KEY`). Token is NEVER forwarded to `ManagedRuntime.ensure()/status()/current()`, NEVER persisted to logs, NEVER included in diagnostic dumps, NEVER injected into child-process env beyond the single targeted subprocess. Headless CLI independently reads explicit env/`.env` via `embedding/_config.py` (no SecretStorage path). |
| **Target (N)** | `redact_env()` filter on child process env (strip `PADDLEOCR_*`, `VECTOR_DB_*`, `OPENAI_*` patterns). Remove explicit `VECTOR_DB_API_KEY` from child env. Add `credential_source` field. **SecretStorage migration:** copy from data.json/.env to SecretStorage, readback-verify the stored value against original, then delete data.json plaintext. If readback fails (wrong value returned), retain legacy value as fallback-with-warning. |
| **Target (N+1)** | All **plugin** credential reads use SecretStorage exclusively. Legacy `.env`/data.json readers in plugin code removed. Headless CLI retains `.env`/env inputs via `embedding/_config.py` (unchanged). `credential_last_4_for_verification` only in diagnostics. |
| **Target (N+2)** | Remove legacy plaintext credential readers from plugin entirely. |
| **Versioning** | Migration warning if both `.env` and SecretStorage have key (indicates incomplete migration). |
| **Idempotence** | Re-running migration at same state: SecretStorage has value, data.json cleanly deleted. Safe re-run. |
| **Test seam** | `unit/plugin/test_credential_redaction.ts`. `integration/test_credential_migration.py` (copy->verify->delete). `unit/plugin/test_child_env_filter.ts`. `unit/plugin/test_secret_storage_readback.ts`. `integration/test_credential_handoff_ephemeral.py` — verify ephemeral env allowlist, no leak to ManagedRuntime, no log/diag persistence |
| **Files** | `paperforge/embedding/_config.py:8-29`. `plugin/src/services/python-bridge.ts:469-482` (paperforgeEnrichedEnv). `plugin/src/settings.ts:1251-1254`. `plugin/src/views/modals.ts:718-750` (diagnostic copy). `tests/conftest.py:64-69` (test .env). |

| Aspect | Detail |
|--------|--------|
| **Current** | Three setup implementations (headless, modular, TUI). P0: source-checkout headless skips pip (`setup_wizard.py:774-817`). P1: `--literature-dir` silently dropped (`cli.py:749-762`). P1: Modular JSON exits 0 despite failures (`setup/plan.py:81-84`). P1: Modular directory semantics differ from canonical path builder. |
| **Target** | Merge headless + modular into one canonical engine. N: legacy bare `setup` delegates with deprecation warning — paves path. N+1: bare `setup` routes exclusively to canonical modular engine (no error). N+2: delete legacy TUI code. Fix P0 pip-skip, P1 literature-dir drop, P1 JSON exit code throughout. |
| **Versioning** | CLI: bare `setup` delegates/warns in N; routes to canonical engine in N+1; TUI removed N+2. All steps data-op idempotent. |
| **Idempotence** | Re-running after fix correctly installs runtime. Setup already incremental. |
| **Rollback** | New validation may be too strict (network unreachable), but clear error is correct behavior per #66. Legacy TUI unavailable after N+1 upgrade; prepare users. |
| **Test seam** | `integration/test_headless_setup.py` (no network -> non-zero exit). `unit/test_cli_dispatch.py` (literature_dir forwarded). `unit/setup/test_plan_json_exit.py`. `e2e/test_setup_cli.py`. |
| **Files** | `paperforge/setup_wizard.py:428-865`. `paperforge/setup/plan.py:19-96`. `paperforge/cli.py:733-766`. `paperforge/config.py:166-337` (paperforge_paths). |

---

## 3. Security & Privacy Threat Gates

| Gate | Requirement | Blocking? | Test |
|------|-------------|-----------|------|
| SG-01 | Strips `PADDLEOCR_*`, `VECTOR_DB_*`, `OPENAI_*` before all non-targeted subprocesses (pip install, ManagedRuntime ensure/status, diagnostic probes, etc.). Does NOT strip the single allowlisted token from its one targeted OCR/Memory subprocess per §2.6 handoff protocol. | **BLOCKING** (N) | `unit/plugin/test_child_env_filter.ts` — verify env stripped for install/ensure/diag but allowlisted token reaches its target subprocess |
| SG-02 | **Forbidden:** broad `process.env` forwarding to all child processes (e.g. `paperforgeEnrichedEnv()` before pip install); injecting credentials into unrelated subprocesses. **Allowed:** single SecretStorage-derived token in allowlisted env var (`PADDLEOCR_API_TOKEN`, `VECTOR_DB_API_KEY`) for the one targeted OCR/Memory subprocess, immediately before launch, per §2.6 handoff protocol. Headless CLI reads env/`.env` independently via `_config.py`. | **BLOCKING** (N) | `unit/plugin/test_child_env_allowlist.ts` — verify only allowlisted vars reach their target subprocess; no credential in pip/install subprocess; headless CLI path unchanged |
| SG-03 | Diagnostic clipboard / export redacts all credential values, vault path, Zotero path, paper titles to `[redacted]`. | **BLOCKING** (N) | `unit/plugin/test_diagnostic_redaction.ts` — all patterns redacted |
| SG-04 | Issue draft modal: editable title, redacted fields, no auto-submit, no token in URL, manual GitHub open (`window.open`, not `window.location`). | **BLOCKING** (N) | `integration/test_issue_draft_privacy.py` — URL parse + no-auto-upload + DOM |
| SG-06 | `ManagedRuntime.ensure()/status()/current()` never receives credentials. Plugin passes token via allowlisted ephemeral child-process env var immediately before OCR/Memory subprocess only. Headless CLI reads env/`.env`. Machine-local runtime path `~/.paperforge/runtime/` contains no secrets. | **BLOCKING** (N) | `integration/test_runtime_no_credential_leak.py`. `integration/test_credential_handoff_ephemeral.py` — verify token present in OCR subprocess env but absent from ManagedRuntime calls, logs, and diagnostic output |
| SG-07 | Bootstrap Python path never stored — only venv path from `active-runtime.json`. | BLOCKING (N) | `unit/plugin/test_active_runtime_no_bootstrap_path.ts` |
| SG-08 | `~/.paperforge/runtime/active-runtime.json` stores version metadata and pythonPath only — no credentials, no vault paths, no bootstrap-Python path. | BLOCKING (N) | `unit/plugin/test_active_runtime_contents.ts` — JSON shape check |
| SG-09 | OCR upload consent modal (`PaperForgeOcrPrivacyModal`) remains as-is; issue draft consent explicit before browser open. | BLOCKING (N) | `e2e/test_ocr_upload_consent.py` (manual check: modal present) |
| SG-10 | No FileHandler logger; stderr-only StreamHandler; JSONL logs (reading-log, project-log, correction-log) contain paper keys only, no credential values. | Post-release audit | `unit/test_logging_no_file_handler.py` + code review |

**Rejected (scout speculation, overridden by locked decisions):**
- "Use OS keychain for credentials" — locked decision says Obsidian SecretStorage (1.11.4), not OS keychain. (#73 contract)
- "Flatpak credential isolation" — Flatpak/Snap explicitly unsupported in first release. (#73 contract)

---

## 4. Platform Support Matrix

| Triplet | Bootstrap | Auto-Download | Release Gate | macOS Signing | Notes |
|---------|-----------|---------------|--------------|---------------|-------|
| **win-x64** | `py -3.11` -> `py -3` -> registered Python | Published, checksummed, CI-smoke-tested | **Gate: pointer atomicity on win-x64** | N/A | LongPathsEnabled may be needed |
| **macos-x64** | `/usr/bin/python3` -> Homebrew -> `which python3` | **Disabled until signed/notarized** | **Gate: signed artifact + pointer atomicity on macos-x64** | Required ($99/yr) | No Gatekeeper bypass. Manual Python: install 3.11+ |
| **macos-arm64** | Same as macos-x64 | **Disabled until signed/notarized** | **Gate: signed artifact + pointer atomicity on macos-arm64** | Required ($99/yr) | x64/arm64 smoke gates required before enable |
| **linux-x64** | `/usr/bin/python3` -> `$PATH python3` | Published, checksummed, CI-smoke-tested | **Gate: pointer atomicity on linux-x64** | N/A | `python3-venv` separate on Debian/Ubuntu |
| **win-arm64** | Not available from upstream | Not available | Not validated | N/A | Manual: install Python 3.11+ from python.org |
| **linux-arm64** | Published, not CI-smoke-tested | Not validated | Not validated | N/A | Manual: install Python 3.11+ via package manager |
| Flatpak/Snap | Detect -> explain native alternatives | N/A | **First release: unsupported** | N/A | Detect `container`/`flatpak` env indicator. Manual: install Python 3.11+ natively |

**MacOS signing release gate** (blocking before auto-download enable):
1. Apple Developer Program enrollment ($99/yr) confirmed.
2. Notarization workflow built into CI pipeline.
3. Downloaded python-build-standalone binary signed and notarized.
4. x64 and arm64 smoke tests pass in CI.
5. Checksums published in release-owned checksums file.
6. Verification test: `codesign -dv` on artifact, `spctl --assess --type execute` on first launch.

**Cross-platform pointer atomicity gate** (blocking per triplet, before that triplet is supported):
On every supported triplet, `write-temp-file + rename` must be verified atomic in CI before the triplet is marked supported.
Runs on the machine-local path `~/.paperforge/runtime/` (same-filesystem rename guaranteed on NTFS/APFS/ext4).

**Platform test gaps (post-release hardening, not blocking):**
- E2E on Windows/macOS CI (currently ubuntu-only). (PlatformAcceptance §Finding)
- Chaos tests on Windows/macOS. (PlatformAcceptance §Finding)
- Path-with-spaces unit test (zero coverage today). (PlatformAcceptance §Test Gaps)
- `MAX_PATH` / LongPathsEnabled acceptance on Windows. (PlatformAcceptance §Test Gaps)
- Flatpak/Snap vault write access test. (PlatformAcceptance §Unresolved 3)

---

## 5. Accessibility Gates

| Gate | Requirement | Source | Method |
|------|-------------|--------|--------|
| AG-01 | Module cards use plain `<button>` elements, not ARIA tabpanel. Arrow-key scenario navigation for multi-module layouts. | #71 prototype (docs/prototypes/2026-07-14-six-module-control-center.md) | Keyboard nav test: Tab through all cards, activate with Enter/Space |
| AG-02 | Focus moves to the primary action button on scenario switch. | #71 prototype decision | Integration: tab.observe() focus target after switch |
| AG-03 | Progress bars: `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`. | #71 prototype | Unit: rendered HTML attributes |
| AG-04 | Snackbar/notifications: `role="status"`, `aria-live="polite"`. | #71 prototype | Unit: rendered HTML attributes |
| AG-05 | Maintenance modal: focus trap (Tab cycle, Escape closes), `inert` on background, focus restoration to trigger element on close. | #72 prototype | Integration: keyboard Tab trap test, focus restoration test |
| AG-06 | Diagnostic disclosure: `aria-expanded` toggles; content hidden/shown. | #71 prototype | Unit: aria-expanded attribute toggles |
| AG-07 | Confirmation modals for destructive actions: focus trap + clear scope disclosure. | #69 §10, #72 §4 | Integration: focus trapped inside modal, Escape closes, background inert |
| AG-08 | `prefers-reduced-motion` media query for spinners / pulse animations. | AccessibilityAcceptance §Gaps | CSS test: animation disabled when prefers-reduced-motion |
| AG-09 | Color-coded severity badges (`ok`/`warning`/`error`/`unknown`) are not the sole channel: text label accompanies every badge. | WCAG 1.4.1 | Visual audit: label present alongside color badge |
| AG-10 | Search results keyboard nav pattern (arrows/enter/escape/ctrl+enter) reused for any list-based module items. | Existing `dashboard.ts` | Unit: keyboard events mapped correctly |
| AG-11 | No `<style>` injection inline; all styles in `styles.css`. | ObsidianPatterns §TabNav | Code review: no inline `<style>` in DOM |
| AG-12 | Focus-visible ring on all interactive elements; `outline: none` fallback replaced with `outline: 2px solid` + `box-shadow` pair. | AccessibilityAcceptance §Gaps | CSS audit: focus-visible on buttons/inputs |

---

## 6. E2E Acceptance & Release Matrix

### Tier 1: Release-Blocking (must pass to ship N)

| ID | Scenario | Fixture | Pass criteria | Priority |
|----|----------|---------|---------------|----------|
| QA-01 | `paperforge setup --headless --vault {tmp}` exits 0, produces all artifacts | Fresh tmp_path, subprocess | exit 0; `paperforge.json` with version/system_dir/resources_dir/literature_dir; all expected dirs exist; `~/.paperforge/runtime/active-runtime.json` exists with valid pythonPath; `ManagedRuntime.current().pythonPath` resolves to an interpreter; setup completes without requiring OCR token (`ocr.api_key_missing` is separate `missing_input` state); second run idempotent | P0 |
| QA-02 | Capability envelope contract: backend probe returns #69-compliant JSON | Established vault + probe import | Envelope has all required fields (§3); `capability_state` ordinal correct; stale envelope renders as `unknown`; `ready` has `action.primary === null`; activity `running` never masks availability badge | P0 |
| QA-03 | Envelope -> UI rendering: module card has correct badge color, action button, reason text | Envelope JSON -> vitest DOM | Badge color maps to severity; action button text matches verb; reason text displayed | P0 |
| QA-04 | Maintenance projection: non-ready modules appear; ready modules absent; dismissal badge-only | Mock module states | Worst ordinal aggregated; all-ready -> `items: []`; transition ready->needs_action adds item; action completes -> item removed; dismissal does not change underlying state | P1 |
| QA-05 | One-primary-action priority: module with overlapping issues returns highest-priority action only | Mock states with known priority | Priority: setup > set_config > restore_backup > redo > run > migrate > update > rebuild_* > investigate > probe; `ready` -> `null`; `unknown` -> `probe` | P1 |
| QA-06 | Destructive action confirmation: redo/restore_backup requires confirmation with scope disclosure | Mock envelope + subprocess | `destructive: true` -> `confirmation_required: true`; prompt contains `destructive_scope` + `effect`; `destructive_scope: "all"` requires two-step; non-destructive (`rebuild_derived`) has `false` | P1 |
| QA-07 | Child process env redaction: no credential in any subprocess env | Env filter unit test | `PADDLEOCR_*`, `VECTOR_DB_*`, `OPENAI_*` vars stripped; whitelisted vars pass through | P0 |
| QA-08 | Diagnostic export redaction: no vault path, Zotero path, credential, paper title in clipboard output | Diagnostic capture unit test | All sensitive fields replaced with `[redacted]`; credential value never appears | P0 |
| QA-09 | Setup pip validation: source-checkout without runtime exits non-zero | Mock source checkout, no network | `result.returncode != 0`; error message identifies missing package | P0 |
| QA-10 | `ManagedRuntime.status()` never returns `ready` without passing probe | Mock probe returning fail | State is `needs_repair` or `unknown`, never `ready` | P1 |
| QA-11 | `ManagedRuntime.ensure()` atomic write: kill mid-rename leaves valid pointer | Crash injection test | Old pointer intact and references valid slot, or new pointer references valid slot. No partial state | P1 |
| QA-12 | Cross-platform pointer atomicity on `~/.paperforge/runtime/` | Machine-local path, CI on target triplet | After simulated crash mid-rename: old pointer intact references valid slot, or new pointer references verified slot. No partial state | P0 |

### Tier 2: Post-Release / Manual Evidence (not blocking N ship)

| ID | Scenario | Evidence type | Target release |
|----|----------|---------------|----------------|
| QA-13 | ManagedRuntime rollback via pointer rewrite | Integration test | N+1 |
| QA-14 | Immutable slots: upgrade builds new directory, never modifies old | Directory audit after upgrade | N+1 |
| QA-15 | Offline per-capability: OCR `limited` but Library `ready` | Integration test with bad PADDLEOCR_JOB_URL | N+1 |
| QA-16 | Full input-to-screen: setup -> sync -> OCR -> capability envelope -> plugin rendering | Playwright or vitest DOM + subprocess | N+1 |
| QA-17 | Flatpak/Snap detection + explanation | Manual test on Flatpak Obsidian | N |

---
## 7. Preserve / Migrate / Recompute / Delete Inventory

| Artifact | Action | Rationale | Release |
|----------|--------|-----------|---------|
| `paperforge/config.py` path inventory + explicit source tracing | **Preserve** | Canonical path builder | — |
| Per-paper OCR `meta.json`, version hashes, raw/canonical split | **Preserve** | Durable OCR truth, no change | — |
| SQLite schema migrations, `build_state`, FTS, vec0, canonical-index hash | **Preserve** | Durable index truth | — |
| `formal-library.json` atomic/filelock writes | **Preserve** | Canonical paper catalog | — |
| OCR maintenance SHA256 manifest invalidation | **Preserve** | Cache correctness | — |
| `setup_complete` field + wizard rendering | **Migrate** -> per-module capability states | Global bool replaced by 6-state ordinal | N (add alongside), N+2 (remove) |
| All command dispatch resolvers | **Migrate** -> `ManagedRuntime.current().pythonPath` | Single resolver invariant | N (coexistence), N+2 (old removed) |
| Top-level path keys in `paperforge.json` | **Migrate** -> vault_config only | Resolve Python/Plugin precedence conflict | N (v1 read fallback active), N+1 (v1 reads accepted, writes new-only), N+2 (v1 reader removed) |
| Legacy TUI setup path | **Delete** | Three implementations -> one | N+2 |
| `vector-build-state.json` legacy path | **Delete** | SQLite build_state is authoritative | N+1 (stop writing), N+2 (remove reader) |
| `auto_update` field (keep `auto_update_on_startup`) | **Delete** | Duplicate field | N |
| `selected_skill_platform` (keep `agent_platform`) | **Delete** | Duplicate field | N |
| Standalone validation scripts (`scripts/validate_setup.py`, `scripts/consistency_audit.py`) | **Delete** | Duplicated by capability probes | N+2 |
| `KMP_ROOT_MARKER`/`System/PaperForge/cache/` hardcoded path | **Recompute** -> vault_config-aware path | Path resolution correctness | N |
| `~/.paperforge/runtime/` machine-local directory | **Create** | Single runtime per machine, outside vault/Obsidian Sync | N |

---

## 8. Failure Codes & User Actions

| Code | State | User-facing action | Source |
|------|-------|--------------------|--------|
| `installation.config_missing` | unavailable | `setup` -> run setup wizard or headless | #69 §4 |
| `installation.runtime_not_found` | unavailable | `setup` -> install Python runtime | #69 §4 |
| `installation.runtime_version_mismatch` | limited | `update` -> update runtime | #69 §4 |
| `installation.vault_path_invalid` | missing_input | `set_config` -> correct vault path | #69 §4 |
| `installation.platform_unsupported` | unavailable | Show manual Python 3.11+ install instructions | #73 contract |
| `installation.flatpak_detected` | unavailable | Explain native/AppImage/deb alternatives | #73 contract |
| `library.zotero_path_invalid` | missing_input | `set_config` -> correct Zotero path | #69 §4 |
| `library.sync_not_run` | needs_action | `sync` -> run Zotero sync | #69 §4 |
| `library.index_stale` | needs_action | `rebuild_index` -> rebuild index | #69 §4 |
| `ocr.api_key_missing` | missing_input | `set_config` -> configure PaddleOCR token | #69 §4 |
| `ocr.artifacts_stale` | needs_action | `rebuild_derived` -> rebuild derived artifacts | #69 §4 |
| `ocr.quality_unacceptable` | needs_action | `investigate` -> run diagnostics | #69 §4 |
| `ocr.api_unreachable` | limited | `investigate` -> check network | #69 §4 |
| `memory.db_missing` | needs_action | `run` -> initialize memory DB | #69 §4 |
| `memory.db_corrupt` | unavailable | `restore_backup` -> restore from backup | #69 §4 |
| `memory.index_stale` | needs_action | `rebuild_index` -> rebuild vector index | #69 §4 |
| `memory.snapshot_stale` | unknown | `probe` -> refresh capability check | #69 §4 |
| `maintenance.no_items` | ready | (none) | #69 §8 |
| `maintenance.items_present` | needs_action | (none — act on constituent module actions) | #69 §8 |
| `NO_PYTHON` | unavailable | Install Python 3.11+ manually | #70 §Failure |
| `PYTHON_TOO_OLD` | needs_repair | Upgrade to Python 3.11+ or set python_path | #70 §Failure |
| `NETWORK_UNAVAILABLE` | limited | Retry when online | #70 §Failure |
| `MAX_PATH` (Windows) | needs_repair | Shorten vault path / enable LongPathsEnabled | #70 §Failure |
| `FALLBACK_UNAVAILABLE` | unavailable | Manual Python install instructions | #70 §Failure |
| `INCOMPATIBLE_VERSION` | needs_repair | Indicates broken release; manual install | #70 §Gate |

---

## 9. Production File Seams (untouched by this spec)

| File | Role | Status |
|------|------|--------|
| `paperforge/worker/ocr_*.py` (blocks, roles, document, render, figures, tables, health, quality, etc.) | OCR pipeline engine | **Out of scope** — existing domain code |
| `paperforge/embedding/` (build_state, _config, embed, retrieve) | Embedding engine | **Out of scope** |
| `paperforge/memory/` (state_snapshot.py, runtime_health.py) | Snapshot/health writing | **Recompute** (v2 schema) but content engine unchanged |
| `paperforge/commands/` (sync.py, ocr.py) | CLI command handlers | **Out of scope** — command dispatch unchanged |
| `paperforge/cli.py` | CLI entry | **Seam** — setup dispatch only; other commands unchanged |
| `paperforge/config.py` | Path resolution | **Seam** — load_vault_config schema-aware read only |
| `paperforge/setup_wizard.py` | Setup engine | **Migrate** — merge with SetupPlan; fix P0/P1 bugs |
| `paperforge/setup/plan.py` | Setup step model | **Migrate** — merge into headless |
| `paperforge/worker/ocr_maintenance.py` | Backend maintenance state | **Preserve** — already canonical |
| `paperforge/worker/update.py` | Python update | **Preserve** — behind one owner |
| `paperforge/logging_config.py` | Logging config | **Preserve + audit** — stderr-only invariant |
| `paperforge/embedding/_config.py` | Credential resolution for headless CLI | **Preserve** — env / `.env` reader for headless CLI path. Plugin reads switch to SecretStorage at N+1 |
| `plugin/src/main.ts` | Plugin lifecycle | **Seam** — _autoUpdate gate changes; loadSettings path migration |
| `plugin/src/settings.ts` | Settings tab | **Seam** — add capability state rendering alongside existing |
| `plugin/src/services/python-bridge.ts` | Python subprocess | **Seam** — env filter addition; resolver removal at N+2 |
| `plugin/src/services/memory-state.ts` | Memory/vector state | **Seam** — snapshot freshness gate addition; resolver removal at N+2 |
| `plugin/src/services/ocr-maintenance-ui.ts` | Maintenance UI state | **Seam** — cache path/cache_version/remove categorizeMaintenanceRow |
| `plugin/src/constants.ts` | Settings interface | **Seam** — add capabilityState, remove setup_complete at N+2 |
| `plugin/src/views/modals.ts` | Wizard + diagnostic | **Seam** — add redact utility; issue draft modal |
| `plugin/src/views/step3-gate.ts` | Setup gate | **Seam** — rewritten for per-module state |
| `plugin/src/services/managed-runtime.ts` | **New file** | ManagedRuntime class (#70 interface). Target: `~/.paperforge/runtime/{os-arch}/v{version}`. Pointer: `~/.paperforge/runtime/active-runtime.json` |
| `plugin/src/utils/redact.ts` | **New file** | Redaction utility for diagnostics |
| `plugin/styles.css` | Styles | **Seam** — add prefers-reduced-motion, focus-visible, no inline style |

## 10. Explicit Out-of-Scope

| Item | Rationale | Re-entry condition |
|------|-----------|-------------------|
| Declarative Obsidian Settings API (1.13+) | Stay on imperative `PluginSettingTab` per locked decision | User upgrades minAppVersion requirement |
| Obsidian Workspace View / ItemView | Not required by #71 prototype | New feature requiring multi-pane layout |
| macOS code-signing pipeline implementation | Documented as release gate, not implementation | Before auto-download on macOS is enabled |
| Flatpak/Snap compatibility | Explicitly unsupported in first release | User demand after first release |
| OS keychain / system credential store | Locked decision specifies Obsidian SecretStorage | SecretStorage proves insufficient |
| Mobile / tablet support | `isDesktopOnly: true` in manifest | Plugin paradigm change |
| Machine-local runtime (`~/.paperforge/runtime/`) sync concern | Runtime outside vault, outside Obsidian Sync by design. No mitigation needed. | — |
| Whisper / speech-to-text for diagnostic dictation | Not in any prototype or contract | Feature request |
| `chunker.py` section-aware refactor | Layer 4 downstream tooling | #73 not scoped for downstream tools |
| Group-first figure matching | Deferred in decision log | OCR pipeline improvement cycle |
| i18n / localization beyond reason-code key mapping | Backend owns English codes only | Plugin i18n framework introduced |
| Theme customization beyond Obsidian CSS variables | Plugin follows Obsidian theme | Design system expansion |
| PaperForge mobile app / Electron rebuild | Not in manifest or contract | Product strategy change |

---

## 11. Acceptance Checklist (copy-ready for PRD issue splitting)

### P0 — Release N (blocking, each item is a standalone issue)

- [ ] QA-01: CLI Setup E2E — fix P0 pip-skip, P1 literature-dir drop, P1 JSON exit code; one `--headless` engine
- [ ] QA-02: Capability envelope contract — backend probe per module returning #69 envelope; TTL enforcement; stale->unknown
- [ ] QA-03: Envelope->UI rendering — module card renders badge/action/reason from envelope; scenario switcher
- [ ] QA-04: Maintenance projection — aggregate non-ready module states; dismissal badge-only
- [ ] QA-05: One-primary-action priority — priority sort; `ready`->null; `unknown`->probe
- [ ] QA-06: Destructive action confirmation — confirmation gate for redo/restore_backup; scope disclosure
- [ ] QA-07: Child process env redaction — `redact_env()` filter in `paperforgeEnrichedEnv()`
- [ ] QA-08: Diagnostic redaction — utility; `[redacted]` for vault path, Zotero path, credentials, paper titles
- [ ] QA-09: Setup pip validation — source-checkout without runtime exits non-zero
- [ ] QA-10: `ManagedRuntime.status()` never returns `ready` without probe
- [ ] QA-11: `ManagedRuntime.ensure()` atomic write — crash-mid-rename invariant
- [ ] QA-12: Cross-platform pointer atomicity on `~/.paperforge/runtime/` — verify before triplet supported
- [ ] SG-04: Issue draft privacy — redacted fields, no auto-submit, manual GitHub open (`window.open`)
- [ ] SecretStorage credential migration (N): copy data.json/.env -> SecretStorage, readback-verify, delete plaintext; failed verify retains legacy fallback-with-warning
- [ ] Accessibility: AG-01 through AG-12 (keyboard nav, focus trap, ARIA, prefers-reduced-motion, focus-visible)
- [ ] `paperforge.json` schema v2 — vault_config only; v1 fallback active; `load_vault_config` returns version with paths
- [ ] `setup_complete` -> per-module capabilityState map; `_autoUpdate` gated on installation state; `override_to_ready` escape hatch
- [ ] Memory/vector snapshot v2 schema with freshness gate; reject schema<2 or age>TTL as stale
- [ ] OCR maintenance cache: vault_config-aware cache path; `cache_version` field; backend canonical action ownership
- [ ] Setup consolidation: canonical engine; legacy bare delegates with deprecation warning; fix P0 pip-skip, P1 literature-dir drop, P1 JSON exit code
- [ ] `ManagedRuntime` class: add alongside existing resolvers; target `~/.paperforge/runtime/{os-arch}/v{version}`; absent -> fallback
- [ ] `~/.paperforge/runtime/active-runtime.json` pointer: version+pythonPath only, no secrets

### P1 — N+1 (all new-only reads/writes)

- [ ] ManagedRuntime Phase 1: setup wizard uses `runtime.ensure()`; existing users get one prompt
- [ ] Python 3.10 -> `needs_repair`; 3.11+ required for new installs and repairs
- [ ] Plugin credential reads use SecretStorage exclusively; remove `.env`/data.json legacy readers from plugin
- [ ] Bare `setup` routes exclusively to canonical modular engine (no error)
- [ ] Delete `categorizeMaintenanceRow` + derived TS types; render from backend fields
- [ ] Stop writing `vector-build-state.json`; remove legacy path
- [ ] Platform: add E2E smoke on Windows/macOS CI; path-with-spaces test
- [ ] Offline per-capability integration test (QA-15)
- [ ] ManagedRuntime Phase 2: `resolvePythonExecutable()` -> `runtime.current().pythonPath`; remove `getCachedPython`, `getVectorRuntime`, `checkRuntimeVersion`

### P2 — N+2 (legacy shim removal)

- [ ] Remove `setup_complete` from I/O and rendering
- [ ] Remove old resolvers: `resolvePythonExecutable`, `buildRuntimeInstallCommand`, `_autoUpdate` inline path
- [ ] Remove legacy plaintext credential readers from plugin entirely
- [ ] Remove v1 `paperforge.json` READ fallback reader
- [ ] Delete legacy TUI setup code
- [ ] Remove standalone validation scripts (`validate_setup.py`, `consistency_audit.py`)
- [ ] Remove `auto_update` field; consolidate on `auto_update_on_startup`
- [ ] Remove `selected_skill_platform`; consolidate on `agent_platform`
