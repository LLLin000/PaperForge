# State: PaperForge Lite Release Hardening

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-23)

**Core value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

**Current focus:** Phase 5 complete — all 5 phases done

## Current Findings

- The parent `D:\L\Med\Research` already has a separate GSD `.planning`; this release repo uses its own local `.planning`.
- The release repo already supports configurable path names through `paperforge.json`, but user-facing commands still expose placeholders.
- PaddleOCR failures need a dedicated preflight and retry path before deeper workflow work.
- Production Base designs are richer than release-generated Bases and should be parameterized.
- `paperforge_lite/config.py` now provides a tested shared resolver; worker, `/LD-deep`, setup wizard, and validation all consume it (01-03 complete).
- `paperforge` CLI launcher provides copy-pasteable commands with resolved paths.
- All Phase 1 workers and agent commands now delegate to shared resolver: legacy public names preserved.
- **Phase 1 fully complete** (01-01 through 01-04): 4 plans, 58 tests, 8/8 must-haves verified.

## Next Action

Begin Phase 5: Release Verification — run `/gsd-plan-phase 5` to plan smoke tests and consistency checks.

## Open Questions

- Confirm the exact PaddleOCR service currently used and whether it expects `Bearer`, `bearer`, API key query params, or another auth contract.
- Decide how aggressive Base refresh should be when user-edited `.base` files already exist.
- Investigate Zotero storage-relative path formats from full local pipeline (`D:\L\Med\Research\99_System\LiteraturePipeline`).

---
*Initialized: 2026-04-23*
*Last updated: 2026-04-23 (Phase 4 complete — Phase 2/3 records corrected, Phase 5 pending)*

## Phase 1 Progress

| Plan | Status | Summary |
|------|--------|---------|
| 01-01 | done | Shared config resolver (`paperforge_lite/config.py`) and 13-key path inventory |
| 01-02 | done | `paperforge` launcher, package entry point, and command dispatch |
| 01-03 | done | Worker, `/LD-deep`, setup, and validation resolver integration |
| 01-04 | done | Stable command documentation and setup next-step updates |

**Completed:** 2026-04-23
**Completed Requirements:** CONF-01, CONF-02, CONF-03, CONF-04, CMD-01, CMD-02, CMD-03, DEEP-02

## Phase 2 Progress

| Plan | Status | Summary |
|------|--------|---------|
| 02-01 | done | PDF Path Resolver + Preflight |
| 02-02 | done | OCR Failure Classification |
| 02-03 | done | OCR Doctor Command with L1-L4 diagnostics |
| 02-04 | done | Selection Sync PDF Reporting |

**Requirements:** OCR-01, OCR-02, OCR-03, OCR-04, OCR-05, ZOT-01, ZOT-02

**Completed:** 2026-04-23

## Phase 3 Progress

| Plan | Status | Summary |
|------|--------|---------|
| 03-01 | done | Base Generation Refactor — 8 Views + Incremental Merge + Placeholder Substitution |
| 03-02 | done | CLI base-refresh + Tests |

**Requirements:** BASE-01, BASE-02, BASE-03, BASE-04

**Completed:** 2026-04-23

## Phase 4 Progress

| Plan | Status | Summary |
|------|--------|---------|
| 04-01 | done | deep-reading 三态输出 + --verbose |
| 04-02 | done | paperforge doctor 子命令 |
| 04-03 | done | AGENTS.md paperforge CLI 更新 |
| 04-04 | done | docs/README.md BBT 配置指南 |

**Requirements:** ONBD-01, ONBD-02, ONBD-03, ZOT-03, DEEP-01, DEEP-03

**Completed:** 2026-04-23

## Phase 5 Progress

| Plan | Status | Summary |
|------|--------|---------|
| 05-01 | done | OCR state machine tests (8 cases) + base views verified (21) + AGENTS.md consistency checked |
| 05-02 | done | Fixture vault factory + smoke test suite |

**Discuss-phase complete (2026-04-23):**
- Test coverage scope: key-path coverage, no mandatory line %
- Smoke test: `tests/smoke_test.py` standalone script, 6-step fixture vault flow
- Doc consistency: extend test_command_docs.py + new INSTALLATION consistency test
- Defect audit: formal audit of all 16 DEFECTS.md items → fixed/deferred/superseded
- v2 requirements: move INT-01/02/03, UX-01/02/03 to backlog.md with defer rationale

**Requirements:** REL-01, REL-02, REL-03

**Status:** Phase 5 complete

---

## Decisions Logged

- **2026-04-23:** Config precedence locked as: explicit overrides > env > JSON nested > JSON top-level > defaults
- **2026-04-23:** `paperforge_paths` returns exactly 13 keys; `command_dir` excluded (not user-facing)
- **2026-04-23:** `resolve_vault` walks cwd upward for `paperforge.json` enabling vault-free invocation
- **2026-04-23:** No `os.environ` mutation; `env` is a read-only parameter
- **2026-04-23:** CLI returns int exit codes (not `sys.exit()`) for testability; worker functions imported at module level for patchability
- **2026-04-23:** `load_simple_env` added to config.py for .env loading before worker dispatch
- **2026-04-23 (01-03):** Worker `load_vault_config` and `pipeline_paths` now delegate to `paperforge_lite.config`; `ld_deep._load_vault_config` and `_paperforge_paths` also delegate; setup wizard deploys `paperforge_lite/` package alongside scripts; validate_setup uses shared resolver with `PAPERFORGE_VAULT` first
- **2026-04-23 (01-03):** Public function names preserved as thin wrappers for backward compatibility with existing callers
- **2026-04-23 (01-03):** `pipeline_paths` uses `**shared` dict merge to combine resolver output with worker-only keys (pipeline, candidates, search_*, harvest_root, records, review, config, queue, log, bridge_config*, index, ocr_queue)
- **2026-04-23 (Phase 2 discuss):** `paperforge ocr doctor` — single command with tiered L1-L4 diagnostics; L4 optional via `--live` flag
- **2026-04-23 (Phase 2 discuss):** PDF preflight checks `has_pdf` + file existence before OCR; junction paths resolved through to actual Zotero storage; missing PDF → `ocr_status: nopdf`
- **2026-04-23 (Phase 2 discuss):** Failure taxonomy: `blocked` (fixable config/path issues) vs `error` (runtime/API issues); no `retry` command — retry = re-run `paperforge ocr`; `meta.json` error field includes fix suggestion
- **2026-04-23 (Phase 2 discuss):** PDF path resolver supports absolute, vault-relative, junction, and Zotero storage-relative formats; investigate full local pipeline at `D:\L\Med\Research\99_System\LiteraturePipeline` for storage path formats; on failure returns empty string + error log
- **2026-04-23 (02-03):** `paperforge ocr doctor` implements tiered L1-L4 diagnostics with early-exit on failure; L4 live PDF test is optional via `--live` flag; test job cancelled immediately after L3 to avoid wasting provider resources
- **2026-04-23 (02-03):** OCR subparser uses `required=False` to preserve backward compatibility of `paperforge ocr` alias defaulting to `run`
- **2026-04-23 (05-01):** Used HTTPError 401 side_effect on mocked requests.post to trigger 'blocked' OCR state (registry token always present in test env; classify_error maps 401 -> 'blocked')
- **2026-04-23 (05-01):** ensure_ocr_meta patched with side_effect factory (not return_value) to avoid shared dict mutation across loop iterations

## Open Questions
