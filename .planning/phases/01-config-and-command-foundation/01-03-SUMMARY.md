---
phase: 01-config-and-command-foundation
plan: "03"
subsystem: config
tags: [config, resolver, worker, ld-deep, setup, validation, paperforge-lite, tdd]

# Dependency graph
requires:
  - phase: 01-config-and-command-foundation
    provides: paperforge.config with load_vault_config and paperforge_paths
provides:
  - Worker load_vault_config wired to shared resolver
  - Worker pipeline_paths returns shared keys + worker-only keys
  - ld_deep._load_vault_config and _paperforge_paths wired to shared resolver
  - setup_wizard deploys paperforge package alongside scripts
  - validate_setup.py uses shared resolver with PAPERFORGE_VAULT first
affects: [01-04, worker, ld-deep, setup_wizard, validate_setup]

# Tech tracking
tech-stack:
  added: [importlib.util, shutil.copytree]
  patterns: [delegate-wrapper pattern, copied-package deployment, env-precedence validation]

key-files:
  created:
    - tests/test_legacy_worker_compat.py
    - tests/test_ld_deep_config.py
  modified:
    - pipeline/worker/scripts/literature_pipeline.py
    - skills/literature-qa/scripts/ld_deep.py
    - setup_wizard.py
    - scripts/validate_setup.py

key-decisions:
  - "Public function names preserved as wrappers: load_vault_config, pipeline_paths in worker; _load_vault_config, _paperforge_paths in ld_deep"
  - "pipeline_paths uses **shared to merge resolver output then adds worker-only keys (pipeline, candidates, search_*, harvest_root, records, review, config, queue, log, bridge_config*, index, ocr_queue)"
  - "setup_wizard deploys paperforge to two parallel locations: <pf_path>/worker/paperforge/ and <skill_dir>/literature-qa/paperforge/"
  - "validate_setup.py falls back to legacy JSON parsing if shared resolver unavailable (pre-01-03 installs)"
  - "Subprocess test sets PYTHONPATH so paperforge is importable when worker runs standalone"

patterns-established:
  - "Pattern: delegate-wrapper — existing public API preserved, implementation delegates to shared resolver"
  - "Pattern: parallel-package deployment — copy resolver package to each script's adjacent directory"

requirements-completed: [CONF-03, CONF-04, CMD-02, DEEP-02]

# Metrics
duration: 15min
completed: 2026-04-23
---

# Phase 1 Plan 3: Config And Command Foundation Summary

**Worker, /LD-deep, setup wizard, and validation all consuming the same `paperforge.config` resolver, with package deployment for copied installations**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-23T03:50:41Z
- **Completed:** 2026-04-23T04:05:30Z
- **Tasks:** 3 (TDD RED + GREEN; no refactor needed)
- **Files modified:** 6 (4 modified, 2 created)

## Accomplishments

- `literature_pipeline.load_vault_config` and `pipeline_paths` now delegate to shared resolver while preserving legacy public names
- `ld_deep._load_vault_config` and `_paperforge_paths` now delegate to shared resolver
- `setup_wizard.py` deploys `paperforge/` package to both worker and skill directories during installation
- `scripts/validate_setup.py` uses shared resolver with `PAPERFORGE_VAULT` checked before `VAULT_PATH`
- Direct worker invocation (`python literature_pipeline.py --vault . status`) works via PYTHONPATH or copied package
- 34 passing tests covering config, worker compat, and ld_deep compat

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: test(01-03): add failing tests for worker and /LD-deep resolver integration** - `618227e` (test)
   - 12 tests covering worker config keys, env overrides, pipeline_paths keys/values, subprocess smoke test, ld_deep config matching, and prepare_deep_reading callable

2. **Task 2 GREEN: feat(01-03): wire worker and /LD-deep to shared resolver** - `fec25c2` (feat)
   - Updated tests to handle PYTHONPATH for subprocess and importlib for ld_deep module loading

3. **Task 3: feat(01-03): replace duplicated resolver logic with shared wrappers** - `1c1e6d7` (feat)
   - `literature_pipeline.py`: load_vault_config and pipeline_paths delegate to paperforge.config
   - `ld_deep.py`: _load_vault_config and _paperforge_paths delegate to shared resolver

4. **Task 4: feat(01-03): deploy paperforge package through setup wizard** - `e0acb64` (feat)
   - Copies paperforge/ to <pf_path>/worker/paperforge/ and <skill_dir>/literature-qa/paperforge/

5. **Task 5: feat(01-03): wire validate_setup.py to shared resolver** - `500d268` (feat)
   - load_config tries shared resolver first, falls back to legacy for pre-01-03 installs
   - resolve_vault_for_validate checks PAPERFORGE_VAULT before VAULT_PATH

## Files Created/Modified

- `tests/test_legacy_worker_compat.py` - 8 tests for worker/shared resolver compatibility (187 lines)
- `tests/test_ld_deep_config.py` - 4 tests for ld_deep/shared resolver compatibility (126 lines)
- `pipeline/worker/scripts/literature_pipeline.py` - load_vault_config and pipeline_paths now delegate to shared resolver
- `skills/literature-qa/scripts/ld_deep.py` - _load_vault_config and _paperforge_paths now delegate to shared resolver
- `setup_wizard.py` - adds shutil.copytree for paperforge package deployment alongside scripts
- `scripts/validate_setup.py` - load_config uses shared resolver first; resolve_vault_for_validate checks PAPERFORGE_VAULT first

## Decisions Made

- Public function names preserved as thin wrappers for backward compatibility with existing callers
- `pipeline_paths` uses `**shared` dict merge to combine shared resolver output with worker-only keys, avoiding key collision since shared uses `library_records` and worker uses `records` and `pipeline`
- `setup_wizard.py` copies `paperforge/` to both locations so either script can import it regardless of deployment scenario
- `validate_setup.py` falls back to legacy config loading if `paperforge` is not installed, maintaining compatibility with pre-01-03 installs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Test import failures: `literature_pipeline` and `ld_deep` are scripts without `__init__.py`, so required `importlib.util.spec_from_file_location` to load as modules in tests, and `PYTHONPATH` env var for subprocess test
- Subprocess test failure (`ModuleNotFoundError: No module named 'paperforge'`): fixed by passing `PYTHONPATH` env to subprocess run, simulating the installed-package scenario

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Worker, `/LD-deep`, setup deployment, and validation all consume the same config contract from `paperforge.config`
- Requirements CONF-03, CONF-04, CMD-02, and DEEP-02 are satisfied
- `setup_wizard.py` now deploys the resolver package alongside scripts, enabling copied installations to import `paperforge` without pip install
- Ready for Plan 01-04: Stable command documentation and setup next-step updates

---
*Phase: 01-config-and-command-foundation*
*Completed: 2026-04-23*
