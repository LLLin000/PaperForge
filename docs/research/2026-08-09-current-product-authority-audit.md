# Current Product-Authority Boundary Audit

- Date: 2026-08-09
- Wayfinder task: [#136](https://github.com/LLLin000/PaperForge/issues/136)
- Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
- Base: `master` at `44e9d0ad`
- Scope: Factual repository audit only; no target design or production implementation.

Evidence-backed inventory of current product-authority boundaries at base `master 44e9d0ad`. Read-only audit; no recommendations.

## 0. Executive boundary summary

Three consumer classes: **Python backend** (`paperforge/`, producer of nearly all canonical facts), **Obsidian plugin** (`paperforge/plugin/src/**`, TS: heavy direct reader of canonical files + own judgments + credential provider + subprocess owner), **Agent layer** (skills/command files/scripts + harness `.omp/` + `.ai-bridge/`).

Canonical stores: `paperforge.json` (config), `System/PaperForge/indexes/formal-library.json` (asset index), `System/PaperForge/indexes/paperforge.db` (SQLite memory layer, schema v7), `System/PaperForge/ocr/<key>/meta.json` (OCR state), `System/PaperForge/logs/*.jsonl` (permanent logs), formal-note frontmatter, `System/PaperForge/config/domain-collections.json`.

Dominant boundary pattern: **Python owns writes; plugin owns presentation but duplicates path resolution, config interpretation, readiness judgment, and orchestration policy in TS** (§3). Three separate config/path parsers exist (Python `config.py`, plugin `memory-state.ts`, `runtime_health._check_bootstrap`), plus hardcoded paths (`commands/sync.py:162`, `commands/dashboard.py:56`). Plugin re-derives memory/vector/health readiness from Python-written JSON snapshots and re-implements freshness decisions.

Duplicated action policy: backend ships typed `next_actions` in PFResult (`core/next_actions.py`; attached by `commands/sync.py`) AND plugin keeps a parallel fixed argv allowlist (`next-actions-orchestrator.ts`) AND a separate fixed OCR-success→memory-build→embed chain (`ocr-workspace.ts:884`).

Phantom path: plugin resolves `vector-build-state.json` (`memory-state.ts:137`) but no Python writer emits it — Python stores vector build state in SQLite `build_state` table (`embedding/build_state.py`).

---

## 1. Canonical facts — owner/storage (Python | Obsidian-plugin | Agent consumers)

| Fact | Owner/storage | Canonical writer | Consumers | Evidence |
|---|---|---|---|---|
| Vault path config | `paperforge.json` (v2 `vault_config`) | `setup/config_writer.py:36-130`; `config.migrate_paperforge_json` `config.py:395-457` | Python `config.load_vault_config` `config.py:110-214`; plugin `memory-state.ts:52-99`; Agent `setup --agent` `cli.py:511-523` | `config.py:23-42` |
| Canonical asset index | `System/PaperForge/indexes/formal-library.json` (envelope v2) | `worker/asset_index.py` `atomic_write_index` `:107-150`, `build_envelope` `:82-105` | Python `memory.builder`, `retrieval.gateway`, `embed`; plugin `views/dashboard.ts:353-360,509-516`, `views/ocr-workspace.ts:121-135` | `asset_index.py:36-40`, `:155-175` |
| Memory DB | `System/PaperForge/indexes/paperforge.db` (SQLite v7, WAL) | `memory/schema.ensure_schema` `schema.py:308-337`; `memory/builder.py:238-244` | Python `memory/query.py`, `retrieval/*`, `embedding/status.py`; plugin `memory-state.ts:125` | `schema.py:11`, `memory/db.py:22-33` |
| Per-paper OCR state | `System/PaperForge/ocr/<key>/meta.json` | `worker/ocr.py` `ensure_ocr_meta` `:200-204`; `worker/paper_meta.py:13-80` | Python `ocr_health`/`ocr_maintenance`/`status`; plugin `main.ts:284-288`, `version-history.ts:225-231` (writes `restore_provenance`) | `ocr_artifacts.py:25-35` |
| OCR queue | `System/PaperForge/ocr/ocr-queue.json` | `worker/ocr.py` `write_ocr_queue` `:310-320`, `sync_ocr_queue` `:322-375` | Python `run_ocr`; plugin via `ocr run` | `ocr.py:273-308` |
| Formal note frontmatter | `Resources/Literature/<domain>/<key> - <title>/…md` | `worker/sync.py` `frontmatter_note` `:1000-1004` | Python `asset_index._build_entry` `:266-300`, `adapters/obsidian_frontmatter.py:398-401`; plugin `constants.ts:137-157`, `dashboard.ts:919-923,3092-3108` | `schema/field_registry.yaml` (owners obsidian/sync/ocr/user/deep_reading/index) |
| Lifecycle/OCR-status enums + transitions | `core/state.py` | code | Python `worker/asset_state`, `memory.builder`; Agent docs | `state.py:10-44,46-57,59-75,77-131` |
| Derived lifecycle/health/maturity/next_step | computed per entry | `worker/asset_state.py` (pure) | Python `asset_index`, `memory.builder`; plugin dashboard stepper `views/dashboard.ts:715-719,861-869`, next-step card `:1757-1793` | `asset_state.py:24-65,68-116,119-200` |
| OCR pipeline version/hashes | `meta.json` (`ocr_pipeline_version`, `raw_version`, `derived_version`) | `worker/ocr_versions.py`, `ocr_artifacts.py:36-56` | Python `services/sync_service.py:26-42`; plugin OCR workspace | `ocr_artifacts.py:38-54` |
| Permanent logs | `System/PaperForge/logs/*.jsonl` | `memory/permanent.py` `append_*` | Python `memory/builder.py:96-190` (re-import to SQLite); commands reading-log/project-log | `permanent.py:27-31,118-122,149-153` |
| Vector build state | SQLite `build_state` table | `embedding/build_state.py:73-91,93-110` | Python `runtime_health._check_vector`; plugin polls `embed status --json` | `build_state.py:15-24` |
| Embedding dimension | model-derived; process-global cache | `embedding/dim_detect.py:52-76` | Python `ensure_vec_tables`, `status`; vec0 DDL | `dim_detect.py:26-32,95-110` |
| OCR readiness policy | `policies/ocr_readiness_v1.yaml` (+ `~/.paperforge/policies/` override) | code (yaml) | Python `worker/ocr_quality.py:329-403,406-425` | `ocr_readiness_v1.yaml:1-44` |
| Retrieval policy version | computed (`l4.body.v3`) | `retrieval/manifest.py` | Python `memory.builder` (vec meta `retrieval_policy_version`) | `manifest.py:9` |
| Domain collections | `System/PaperForge/config/domain-collections.json` | `setup_wizard.py:728-737`; `worker/_domain.py` | Python sync/repair | `config.py:365-369` |
| Plugin settings | `.obsidian/plugins/paperforge/data.json` | plugin `settings.ts` | **Python reads it**: `embedding/_config.py:8-12`, `commands/probe.py:736-742`, `commands/embed.py:295-300`, `memory/runtime_health.py:124-130` | `_config.py:8-12` |

## 2. Semantic interpreters & action/follow-up policies (Python backend)

| Interpreter/policy | Inputs | Decision output | Evidence |
|---|---|---|---|
| `compute_lifecycle` | has_pdf/ocr_status/deep_reading_status | indexed/pdf_ready/fulltext_ready/deep_read_done | `asset_state.py:24-65` |
| `compute_health` | pdf/ocr/note/workspace paths | per-dimension healthy/fix string | `asset_state.py:68-116` |
| `compute_maturity` | lifecycle + checks | level 1-4 + blocking | `asset_state.py:119-200` |
| `compute_next_step` | ocr_status, has_pdf, paths, deep status | sync/ocr/repair//pf-deep/rebuild index/ready | `asset_state.py:204-262` |
| `get_memory_status` | DB schema, counts, `canonical_index_hash` | fresh/needs_rebuild | `memory/query.py:24-75` |
| `get_embed_status` | vec0/meta counts, dimension, layout | vector_state ready/stale/not_built, healthy | `embedding/status.py:33-112` |
| `get_runtime_health` | paperforge.json, index, DB, logs writability, plugin data.json | layers ok/degraded/blocked + safe_read/write/build/vector + capabilities | `memory/runtime_health.py:9-34,42-66,88-154,157-195` |
| `lookup_paper` scoring | identifier/author/year/title signals + alias | coverage-scored candidates | `memory/query.py:130-227`; signals `query_planning.py:136-236` |
| `build_query_plan` | query signals + intent | primary command+args, fallback triggers, scope | `query_planning.py:238-414`; enrichment `:416-458` |
| Probe capability states | canonical sources per module | schema-v2 envelope (capability_state/user_state/maintenance_eligible/action) | `commands/probe.py:177,283,463,721,1041`; schema `:27-28` |
| OCR error classifier/retry | provider response stage | queue_status + meta status (retryable ≤3, fatal) | `ocr.py:189-198,2522-2616` |
| Zombie reset | meta.ocr_started_at | queued/running→pending after 30 min | `ocr.py:2530-2555` |
| Per-paper timeout | ocr_started_at | retryable_error after 10 min | `ocr.py:63-67` |
| Poll loop | provider state | settle queue; 15s × ≤60 | `ocr.py:2792-2988` |
| OCR settled statuses | queue_status | done/done_degraded/fatal_error/blocked/nopdf/error | `ocr.py:157` |
| OCR maintenance recommendation | meta version/status/artifacts | redo/rebuild action | `ocr_maintenance.py:208-282` |
| OCR readiness gates | quality indicators | use-case gating + hard-red | `ocr_quality.py:306-327,406-425,465-515` |
| Deep-reading status sync | note content vs frontmatter | done/pending via refresh_index_entry | `deep_reading.py:25-66` |
| Field-registry drift validation | entry vs registry | MISSING/DRIFT/TYPE_MISMATCH | `doctor/field_validator.py:9-110` |
| Next-action construction | registry + invariants | remote/destructive ⇒ confirm, never automatic | `core/next_actions.py:29-66,100-161,183-201` |
| Sync follow-up attachment | full-sync success | memory.build (auto) + embed.resume (confirm) | `commands/sync.py:63-92`; terminal runner `:94-113` |
| Embed shadow-publish policy | build_state + vector layout | shadow vs in-place; stop sidecar | `commands/embed.py:69-73,679-682`; `dim_detect.py:113-160` |

## 3. Plugin authority leaks — direct canonical reads/writes, duplicate judgments, orchestration

| Leak | Kind | Evidence |
|---|---|---|
| Duplicate path resolver + config parser with own defaults `System/Resources/Literature/Bases` | config/path duplication | `memory-state.ts:52-99` (parser), `:101-148` (resolver), defaults `:85-91` |
| `isMemoryReady`/`isVectorReady`/`isHealthOk` re-derive readiness from snapshots; `isVectorReady` adds own chunk-sum rule | duplicate readiness judgment | `memory-state.ts:273-297`; summary `:375-405` |
| `getMemoryRuntime`: execFileSync CLI fallback then **plugin writes snapshot file itself** | cache double-writer | `memory-state.ts:163-205` |
| `getVectorRuntime` 2s module cache + snapshot + CLI fallback | duplicate freshness judgment | `memory-state.ts:207-263` |
| `overlayEntryWorkflowState` reads frontmatter and overlays on index entries | direct canonical read (frontmatter) | `constants.ts:137-157` |
| Dashboard reads `formal-library.json` directly + aggregates stats | direct canonical read; re-derives what `summarize_index` does | `views/dashboard.ts:353-360,509-516`; watcher `:3341-3344` |
| OCR workspace reads `formal-library.json` directly | direct canonical read | `views/ocr-workspace.ts:121-135` |
| `modals.ts` reads `sync-orphan-state.json` (hardcoded producer path) | direct canonical read | `modals.ts:272-276`; producer `commands/sync.py:162` |
| `version-history.ts` **writes** `restore_provenance` into `meta.json` | plugin writes canonical OCR file | `services/version-history.ts:225-231` |
| `settings.ts` reads/writes vault `.env` directly | credential/config write | `settings.ts:4767-4771` |
| Auto-sync: 120s `setInterval` mtime-poll exports + meta.json → spawn `sync --json` | polling + trigger policy (Python has no watcher) | `main.ts:218-224,226-243,276-312,245-274` |
| `ACTIONS` fixed argv allowlist | action-policy duplication | `constants.ts:62-125`; `python-bridge.ts:345-361` |
| Next-action orchestrator own `ALLOWED_ACTIONS` + auto/confirm/dedupe/depth | action-policy duplication | `next-actions-orchestrator.ts:44-52,104-158`; bridge `next-actions-bridge.ts:22-62` |
| OCR-success fixed chain: memory build → confirmed embed | third orchestration policy | `views/ocr-workspace.ts:884-897` |
| OCR maintenance UI cache file | plugin cache | `ocr-maintenance-ui.ts:187-189,218-224` |
| Managed runtime pointer `~/.paperforge/runtime/{os-arch}/active-runtime.json`, TTL cache, install/repair/rollback | config/subprocess authority split from Python update | `managed-runtime.ts:14-24,441-458,450-557` |
| Credential injection `buildTargetedEnv`/`stripCredentialEnv` at spawn | credential source for subprocesses | `secret-storage.ts:236-248`; `main.ts:170-193`; OCR controller `main.ts:127-138` |
| Built `main.js` diverges from TS: `OCR_RUN` prefix; DONE drops counts | presentation drift | `plugin/main.js:4233,4259-4261` vs `src/services/progress-parser.ts:39,97-107` |

## 4. Process / subprocess ownership

| Process | Owner | Mechanism | Evidence |
|---|---|---|---|
| Auto `sync --json` | plugin `main.ts` | execFile 120s timeout | `main.ts:245-274` |
| ACTIONS commands | plugin `main.ts` | execFile; ocr timeout 1_800_000 | `main.ts:170-193`; `constants.ts:73-124` |
| `ocr run/redo/rebuild` | plugin `OcrProcessController` (singleton busy-guard) | spawn; stdin `PAPERFORGE_STOP\n`; exit 130 = stop | `ocr-process-controller.ts:104-160,77-92,59-71` |
| `embed build` | plugin `EmbedBuildController` | spawn after credentials; stop via `embed stop --json`; status poll 2s; dispose kill | `embed-build-controller.ts:96-133,186-216,240-263,268-280` |
| memory/embed status probes | plugin `memory-state.ts` | execFileSync 10s | `memory-state.ts:166-205,227-252` |
| OCR workers (backend) | Python `run_ocr` | tqdm + poll loop | `ocr.py:2642-2643,2797-2988` |
| Embed parallel workers | Python `commands/embed.py` | PR9B_MAX_WORKERS=4; PID tracking; tasklist | `embed.py:104-114` |
| pip/venv installs | Python setup | subprocess.run pip | `setup_wizard.py:118-120,781-805`; `setup/runtime.py:36-38` |
| Zotero junction | Python setup | `mklink /J` / which | `setup_wizard.py:182-228,544-546`; `setup/vault.py:79-81` |
| git ops | Python | subprocess git diff/pull/rev-parse | `services/sync_service.py:31-34`; `worker/update.py:182-190`; `architecture_audit/collectors/orchestrator.py:70-112` |
| Project-memory panel server | Python `project_memory_panel/server.py` | ThreadingHTTPServer 127.0.0.1:8765; git show | `server.py:268-336,126-139` |
| pf_bootstrap interpreter probe | Agent script | subprocess.run version/rg | `pf_bootstrap.py:132-148,324-327` |

## 5. Caches, snapshots, paths, config, credentials, polling

### 5a. Caches
| Cache | Owner | Evidence |
|---|---|---|
| `pages/` render cache (regenerable) | Python OCR | `ocr_artifacts.py:86-110` |
| OCR result-hash pending cache | Python | `ocr_hash.py` via `ocr.py:1844-1846` |
| Runtime snapshot JSONs | Python writes; **plugin also writes memory-runtime-state.json** | `state_snapshot.py:12-20,33-52,61-64`; `memory-state.ts:196-201` |
| Plugin in-memory vector cache (2s) | plugin | `memory-state.ts:207-210` |
| Managed-runtime TTL cache (stale→unknown) | plugin | `managed-runtime.ts:441-458` |
| Embedding dimension process cache | Python | `dim_detect.py:26-32,62-75` |
| OCR workspace content cache | plugin | `ocr-workspace.ts:1136-1164` |
| OCR maintenance UI cache | plugin | `ocr-maintenance-ui.ts:187-189` |

### 5b. Snapshot producers/consumers
| Snapshot | Producer | Consumers | Evidence |
|---|---|---|---|
| memory-runtime-state.json | Python `worker/status.py:1074-1116`, `state_snapshot.py:12-20`; **plugin `memory-state.ts:196-201`** | plugin `memory-state.ts:163-164` | `status.py:1074-1116` |
| vector-runtime-state.json | Python `commands/embed.py:142-160`, `state_snapshot.py:33-52` | plugin `memory-state.ts:261` | `embed.py:142-160` |
| runtime-health.json | Python `state_snapshot.py:61-64` (via runtime-health cmd) | plugin `memory-state.ts:270` | `commands/runtime_health.py:9-17` |
| sync-orphan-state.json | Python `commands/sync.py:161-168` — **hardcoded path** | plugin `modals.ts:272-276` | `sync.py:162` |
| vector-build-state.json | **no producer found (phantom)** | plugin `memory-state.ts:137` | grep: only `plugin/main.js:128`, `memory-state.ts:137` |
| paperforge.embed-control.json | Python `commands/embed.py:69-73,191-205` | Python `:679-682`; plugin via `embed stop` | `embed.py:69-73` |
| formal-library.json.bak / paperforge.json.bak | Python legacy migrations | — | `asset_index.py:180-200`; `config.py:444-450` |

### 5c. Config/path resolvers (4 competing)
| Resolver | Location | Coverage | Evidence |
|---|---|---|---|
| `resolve_vault`/`load_vault_config`/`paperforge_paths` | Python `config.py` | authoritative; PAPERFORGE_* env | `config.py:78-108,110-214,216-280` |
| `pipeline_paths` | Python `worker/_utils.py:260-285` | delegates + extras | `_utils.py:260-285` |
| `readPathConfig`/`resolveVaultPaths` | plugin `memory-state.ts:52-148` | duplicate; env not honored | `memory-state.ts:85-91` |
| `_check_bootstrap` inline parser | Python `memory/runtime_health.py:42-66` | third parser | `runtime_health.py:49-58` |
| Hardcoded paths | Python | `sync.py:162`; `dashboard.py:56`; `ocr.py:26` | `sync.py:162`, `dashboard.py:56`, `ocr.py:26` |

### 5d. Credential sources
| Credential | Chain (priority) | Evidence |
|---|---|---|
| PaddleOCR token | env PADDLEOCR_API_TOKEN → _USER → vault/.env → System/PaperForge/.env → plugin data.json | `ocr.py:24-61` |
| Vector DB key/base/model | env VECTOR_DB_API_KEY/OPENAI_API_KEY → plugin data.json → vault/.env | `_config.py:8-46` |
| Plugin SecretStorage | app.secretStorage; ids paddleocr-api-key / vector-db-api-key-v2-<sha256(base|model)>; allowlist ocr/memory/embed; redact PADDLEOCR_/VECTOR_DB_/OPENAI_ | `secret-storage.ts:15-25,33-44,96-158,203-248` |
| .env writer | Python `setup_wizard._merge_env_incremental` (append-only) | `setup_wizard.py:394-426,715-726` |
| data.json path | `.obsidian/plugins/paperforge/data.json` — read by 4 Python modules | `_config.py:8-12` |

### 5e. File watchers / polling loops
| Loop | Owner | Period | Evidence |
|---|---|---|---|
| Exports + OCR meta mtime poll → auto-sync | plugin `main.ts` | 120 000 ms | `main.ts:218-224` |
| formal-library.json modify event | plugin `dashboard.ts` | event | `dashboard.ts:3341-3344` |
| Embed build status poll | plugin `embed-build-controller.ts` | 2000 ms | `embed-build-controller.ts:240-263` |
| Embed stop wait/force-kill | Python `embed.py` | 8s+3s, 200ms sleeps | `embed.py:200-227` |
| OCR provider poll cycle | Python `ocr.py` | 15s × ≤60 (env-tunable) | `ocr.py:2792,2797-2988` |
| OCR doctor live probe | Python `ocr_diagnostics.py` | 5s × 10 | `ocr_diagnostics.py:170-187` |
| Project-memory panel watcher + idle guard | Python `project_memory_panel/server.py` | 2s / 5s | `server.py:44-60,62-77` |
| Auto-update check cadence | repo `paperforge.json` (root) | check_interval_days: 7 | root `paperforge.json` |

## 6. Agent-facing command / JSON / progress contracts

| Contract | Shape | Producer | Consumer | Evidence |
|---|---|---|---|---|
| PFResult envelope | {ok, command, version, data, error{code,message,details,suggestions}, warnings, next_actions} | all commands | plugin, Agent skills, scripts | `core/result.py:17-80` |
| ErrorCode catalog | 25 codes; unknown→UNKNOWN | Python | plugin `classifyError` (mirror subset) | `core/errors.py:9-55`; `python-bridge.ts:102-184` |
| next_actions schema v1 | ids memory.build / embed.resume | `core/next_actions.py` + `commands/sync.py:63-92` | plugin bridge/orchestrator (allowlist) | `core/next_actions.py:29-66,100-201` |
| Probe schema-v2 envelope | capability_state/user_state/maintenance_eligible/action | `commands/probe.py` | plugin settings/dashboard; `constants.ts:258-360` | `probe.py:27-28`; `constants.ts:171-360` |
| Progress tokens | EMBED_*/OCR_REDO_*/OCR_REBUILD_* (START/PROGRESS/RESULT/DONE) | Python | plugin `progress-parser.ts` | emitters `embed.py:341,663,745,781,797,877,988`; `ocr.py:287-361`; `ocr_rebuild.py:601-640`; parser `progress-parser.ts:39-131` |
| Cooperative stop stdin | `PAPERFORGE_STOP\n`; exit 130 | plugin spawn | Python ocr run/rebuild | `ocr-process-controller.ts:77-92`; `commands/ocr.py:230-275` |
| Command registry | 40+ subcommands incl. gateway intents | `cli.py` | plugin ACTIONS, skills, scripts, tests | `cli.py:145-548`; dispatch `:565-700` |
| runtime-health capabilities | safe_read/write/build/vector + 5 capability booleans | `memory/runtime_health.py` | Agent skill pre-flight gate | `runtime_health.py:9-34,157-195`; `SKILL.md:77-95` |
| query-plan contract | {intent, scope, primary, fallback} | `query_planning.py` | Agent retrieval routing | `query_planning.py:238-414`; `docs/COMMANDS.md:1-63` |
| Skill bootstrap chain | bootstrap → agent-context → runtime-health → route → molecule; `--agent` choices (opencode default) | `SKILL.md:1-90`; `pf_bootstrap.py` | Agent platform | `SKILL.md:77-95`; `cli.py:511-523` |
| /pf-* command docs | pf-status/pf-ocr/pf-sync/pf-deep/pf-paper/pf-end/pf-log-* | repo | Agent (opencode active; codex/claude future) | `command_files/pf-status.md:1-60`, `pf-ocr.md:1-80` |

## 7. Known non-plugin / non-Python consumers

| Consumer | Role | Evidence |
|---|---|---|
| Harness `.omp/AGENTS.md` | PM rules; declares PROJECT-MANAGEMENT.md projection-only; lifecycle truth hierarchy | `.omp/AGENTS.md:1-46` |
| `.ai-bridge/` | stale (2026-06-28) handoff; empty logs | `.ai-bridge/agent-status.md:1-6` |
| `project_memory_panel/` | separate HTTP panel (8765) over project-memory/*.md — second memory subsystem | `server.py:268-336` |
| `scripts/` | welcome/consistency_audit/bump/check_version_sync/sync-plugin-version/validate_setup | root `scripts/` |
| Deployed skills | .opencode/skills, .agents/skills, .opencode/command + skills-lock.json | `setup/agent.py:22-69` |
| Project ledger | PROJECT-MANAGEMENT.md, project/current, project/archive, .planning | projection-only per .omp |
| Vault runtime artifacts | System/PaperForge/{indexes,logs,ocr}, Bases/*.base, manifest.json v1.5.15 | vault tree |
| Tests | 150+ files pinning contracts | tests/, plugin/tests/ |
| architecture_audit/ | internal collector/report subsystem with git determinism | architecture_audit/ |

## 8. Uncertainties / gaps

1. **vector-build-state.json phantom**: plugin `memory-state.ts:137` resolves it; no Python writer found. Either dead path or external producer. [Evidence: `memory-state.ts:137` vs `embedding/build_state.py:15-24`]
2. **main.js vs src drift**: `main.js:4233` includes `OCR_RUN` prefix (absent from `progress-parser.ts:39`); `main.js:4259-4261` DONE drops counts (TS `:97-107`). [INFERENCE: build-lag, unverified by rebuild]
3. **Sync-orphan hardcode**: `commands/sync.py:162` bypasses `paperforge_paths`; behavior with custom `system_dir` untested.
4. **Credential duplication**: PaddleOCR token lives in plugin data.json (Python reads file) AND SecretStorage (plugin reads) — two live stores, one-way migration.
5. **Readiness definitions diverge**: `get_memory_status.fresh` (schema+count+hash) vs plugin `isMemoryReady` vs snapshot summary `memory-state.ts:384-405`.
6. **ocr run emits no OCR_RUN_* tokens** though compiled bundle parses OCR_RUN; queue-mode progress relies on tqdm only. [Evidence: emitters `ocr.py:287-361` (redo), `ocr_rebuild.py:601-640` (rebuild); none for run]
7. `.ai-bridge/` handoff stale (June 28).
8. `pf_bootstrap.py:339-344` self-admitted placeholder for `semantic_ready`.

## 9. Evidence index (key files)

| Path | Role |
|---|---|
| `paperforge/config.py` | vault/config/path resolver (canonical) |
| `paperforge/core/state.py`, `result.py`, `errors.py`, `next_actions.py` | state machine, wire envelope, error codes, action policy |
| `paperforge/worker/asset_index.py`, `asset_state.py` | canonical index writer + derived-state interpreters |
| `paperforge/worker/sync.py`, `services/sync_service.py` | formal note + index producers |
| `paperforge/worker/ocr.py`, `ocr_rebuild.py`, `ocr_maintenance.py`, `ocr_health.py`, `ocr_artifacts.py`, `ocr_versions.py`, `paper_meta.py` | OCR state/artifacts/readiness |
| `paperforge/memory/{schema,db,builder,query,permanent,runtime_health,state_snapshot,refresh,paper_state}.py` | memory layer + snapshots |
| `paperforge/embedding/{_config,status,build_state,dim_detect,_chroma}.py` | vector config/status/state |
| `paperforge/retrieval/{gateway,manifest,units}.py`, `query_planning.py` | retrieval contracts |
| `paperforge/commands/{probe,sync,ocr,embed,dashboard,memory,status…}.py`, `cli.py` | command contracts + dispatch |
| `paperforge/schema/field_registry.yaml`, `doctor/field_validator.py`, `policies/ocr_readiness_v1.yaml` | field ownership + validation policy |
| `paperforge/adapters/{obsidian_frontmatter,bbt,zotero_paths}.py` | vault/Zotero adapters |
| `paperforge/plugin/src/services/{python-bridge,managed-runtime,secret-storage,memory-state,next-actions-*,ocr-process-controller,embed-build-controller,progress-parser,version-history,ocr-maintenance-ui}.ts` | plugin boundary |
| `paperforge/plugin/src/{constants,main,settings}.ts`, `views/{dashboard,ocr-workspace,modals}.ts` | plugin UI + direct reads |
| `paperforge/skills/paperforge/SKILL.md`, `command_files/*.md`, `docs/COMMANDS.md`, `AGENTS.md`, `.omp/AGENTS.md` | agent contracts |
| `project_memory_panel/`, `.ai-bridge/`, `scripts/`, `System/PaperForge/` | external consumers / runtime artifacts |