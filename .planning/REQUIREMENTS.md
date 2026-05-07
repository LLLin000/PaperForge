# Requirements: PaperForge v1.11 Merge Gate

**Defined:** 2026-05-07
**Core Value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.

## v1 Requirements

### PATH — Index Path Resolution (6 requirements)

**Root cause:** `asset_index.py:334-338` hardcodes `"Literature/"` in 5 workspace-path index fields. 11 downstream consumers (plugin, context, discussion, etc.) depend on these paths.

- [ ] **PATH-01**: Five workspace-path fields in `asset_index.py:334-338` (`paper_root`, `main_note_path`, `fulltext_path`, `deep_reading_path`, `ai_path`) use config-resolved `literature_dir` instead of hardcoded `"Literature/"`. Verified: all 11 consumers resolve correct paths.
- [ ] **PATH-02**: `config.py:331` `library_records` path key returns `<control>/library-records` (matches docstring) or the key is removed with all consumers updated.
- [ ] **PATH-03**: `config.py:65` env var name `paperforgeRATURE_DIR` fixed to `PAPERFORGE_LITERATURE_DIR` (missing `LI` from concatenation). Test at `test_config.py:175` updated.
- [ ] **PATH-04**: `config.py:358-364` migration includes `skill_dir` and `command_dir` in `CONFIG_PATH_KEYS` so legacy top-level settings move into `vault_config`.
- [ ] **PATH-05**: `base_views.py:154` `${LIBRARY_RECORDS}` placeholder substitution key removed. No shipping `.base` template references it.
- [ ] **PATH-06**: `discussion.py:266` unnecessary Windows `replace("/","\\")` removed (pathlib handles forward slashes natively).

### LEGACY — Library-Records Deprecation Cleanup (7 requirements)

**Root cause:** v1.9 eliminated library-records creation but 15 residual traces remain across production code and documentation.

- [x] **LEGACY-01**: `status.py:525-533` stale-record detection scans `<control>/library-records/` explicitly (not `<control>/` which is the current `library_records` key value). `status.py:728` output label changed from `library_records` to `formal_notes`.
- [x] **LEGACY-02**: `sync.py:722-723` dead `record_path` construction and `parse_existing_library_record()` call removed. Function at `sync.py:652-669` removed if no other callers.
- [x] **LEGACY-03**: `ld_deep.py:39` unused `records` key removed from `_paperforge_paths()` return dict. Docstring at line 32 updated.
- [x] **LEGACY-04**: `repair.py:33` docstring reads "Scan formal literature notes" (not "library-records").
- [x] **LEGACY-05**: `setup_wizard.py:1306-1307` post-install instruction text describes single `paperforge sync` workflow (not old `--selection`/`--index` two-phase flow).
- [x] **LEGACY-06**: Five command files (`pf-sync.md`, `pf-ocr.md`, `pf-status.md`, `pf-paper.md`, `pf-deep.md`) — all library-records references replaced with formal notes workflow. Verified: zero remaining library-records mentions.
- [x] **LEGACY-07**: All hardcoded `"Literature/"` strings in docstrings and print labels in `sync.py` (lines 1557-1562, 1759) and `discussion.py` (line 94) use variable references or generic labels.

### DEPR — Deprecate Textual TUI Setup Wizard (3 requirements)

**Root cause:** The Textual TUI setup wizard (`paperforge setup` without `--headless`) is broken (NameError crash), unreachable from either real install workflow (plugin settings tab uses `--headless`, AI agents use `--headless`), and adds ~1200 lines of Textual-dependent code to maintain.

- [x] **DEPR-01**: `paperforge setup` (bare, no `--headless`) prints a help message redirecting to `--headless` or the plugin settings tab. Textual TUI classes removed from `setup_wizard.py`: `WelcomeStep`, `DirOverviewStep`, `VaultStep`, `PlatformStep`, `DeployStep`, `DoneStep`, `SetupWizardApp`, `ContentSwitcher`, `StepScreen`, and all TUI-only import paths. `headless_setup()` and shared utilities (`EnvChecker`, `AGENT_CONFIGS`, `_copy_file_incremental`, `_merge_env_incremental`) preserved.
- [x] **DEPR-02**: Three documentation files updated: `docs/setup-guide.md`, `docs/INSTALLATION.md`, `README.md` — all bare `paperforge setup` references changed to `paperforge setup --headless`.
- [x] **DEPR-03**: Post-install instruction text in `setup_wizard.py:1306-1307` and `headless_setup` completion message updated to reflect headless-only workflow. `--non-interactive` removed from CLI options. `textual` removed from project optional dependencies.

### HARDEN — Module Hardening (7 requirements)

**Root cause:** New modules (`discussion.py`, `asset_state.py`) and the Obsidian plugin were built quickly during v1.6-v1.8 and lack safety hardening.

- [x] **HARDEN-01**: `discussion.py:281-314` file-level locking around JSON and MD read-modify-write cycles. Concurrent `/pf-paper` and `/pf-deep` calls for the same paper do not silently drop sessions.
- [x] **HARDEN-02**: `discussion.py:170-171` Markdown special characters (`*`, `#`, `[`, `_`, `` ` ``) escaped in QA question/answer fields. Individual QA dict keys validated before building session.
- [x] **HARDEN-03**: `discussion.py:40` hardcoded CST (UTC+8) replaced with UTC. All timestamps use `datetime.now(timezone.utc)`.
- [x] **HARDEN-04**: `main.js:2116` PaddleOCR API key passed via environment variable, not command-line argument. `spawn()` with `env: { PADDLEOCR_API_TOKEN: ... }`.
- [x] **HARDEN-05**: `main.js:1815` `innerHTML` assignment replaced with `createEl()` DOM API for directory tree rendering. No XSS vector from user-configured directory names.
- [x] **HARDEN-06**: `asset_state.py:225-226` workspace integrity checks performed before returning `"/pf-deep"`. Checks currently at lines 233-240 moved before line 226.
- [x] **HARDEN-07**: `status.py:687-690` `lifecycle_level_counts`, `health_aggregate`, `maturity_distribution` return empty dicts `{}` when no canonical index exists (not `null`/`None`). Downstream JSON parsers do not crash on field access.

### REPAIR — Repair Blind Spots (4 requirements)

**Root cause:** `repair.py` three-way divergence detection and `--fix` mode have logic gaps where detected problems are silently skipped.

- [x] **REPAIR-01**: `repair.py:252,258` condition 4 detects `note_ocr_status == "pending"` vs `meta done/failed` divergence. Previously required `note_ocr_status != "pending"` to trigger, missing this case entirely.
- [x] **REPAIR-02**: `repair.py:278-363` `--fix` covers all 6 detected divergence types (not just the 2 currently handled). Unhandled types produce a warning line in console output so the user is not silently misled.
- [x] **REPAIR-03**: `repair.py:226,306-307,347-348,355-356` bare `except Exception: pass` blocks replaced with `logger.warning()` calls. Index write failures during fix are logged rather than silently ignored.
- [x] **REPAIR-04**: `repair.py:196` dead `load_domain_config` call and unused dict comprehension removed.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Publish to Obsidian Community Plugins | Deferred until post-merge stabilization |
| v1.8 deep-reading dashboard features | Paused, not cancelled; resumes after v1.11 merge |
| Full OCR provider abstraction | PaddleOCR remains the only provider |
| Plugin auto-update | Blocked until Community Plugin listing |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PATH-01 | Phase 46 | Pending |
| PATH-02 | Phase 46 | Pending |
| PATH-03 | Phase 46 | Pending |
| PATH-04 | Phase 46 | Pending |
| PATH-05 | Phase 46 | Pending |
| PATH-06 | Phase 46 | Pending |
| LEGACY-01 | Phase 47 | Complete |
| LEGACY-02 | Phase 47 | Complete |
| LEGACY-03 | Phase 47 | Complete |
| LEGACY-04 | Phase 47 | Complete |
| LEGACY-05 | Phase 47 | Complete |
| LEGACY-06 | Phase 47 | Complete |
| LEGACY-07 | Phase 47 | Complete |
| DEPR-01 | Phase 48 | Complete |
| DEPR-02 | Phase 48 | Complete |
| DEPR-03 | Phase 48 | Complete |
| HARDEN-01 | Phase 49 | Complete |
| HARDEN-02 | Phase 49 | Complete |
| HARDEN-03 | Phase 49 | Complete |
| HARDEN-04 | Phase 49 | Complete |
| HARDEN-05 | Phase 49 | Complete |
| HARDEN-06 | Phase 49 | Complete |
| HARDEN-07 | Phase 49 | Complete |
| REPAIR-01 | Phase 50 | Complete |
| REPAIR-02 | Phase 50 | Complete |
| REPAIR-03 | Phase 50 | Complete |
| REPAIR-04 | Phase 50 | Complete |

**Coverage:**
- v1 requirements: 27 total
- Mapped to phases: 27
- Unmapped: 0

---
*Requirements defined: 2026-05-07*
*Last updated: 2026-05-07 after initial definition*
