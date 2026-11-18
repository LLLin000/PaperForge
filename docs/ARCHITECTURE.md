# PaperForge Architecture

> Maintainer-facing documentation covering the control/data/retrieval planes, provider seams, module-boundary gates, key design decisions, and extension points.
>
> **Last updated:** 2026-11-18 | **Version:** v2.0 | **Target audience:** maintainers and contributors

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Control Plane & Privacy Boundary](#control-plane--privacy-boundary)
3. [Data Flow & V3 OCR Contract](#data-flow--v3-ocr-contract)
4. [Retrieval & Pluggable Embedding Plane](#retrieval--pluggable-embedding-plane)
5. [Directory Structure](#directory-structure)
6. [Module Boundaries & Architecture Gates](#module-boundaries--architecture-gates)
7. [Diagnostics & Troubleshooting](#diagnostics--troubleshooting)
8. [Commands Package](#commands-package)
9. [Design Decision Records (ADR)](#design-decision-records-adr)
10. [Extension Points](#extension-points)

---

## System Overview

PaperForge is a local-first literature workflow that bridges Zotero (reference management) and Obsidian (knowledge management) for medical researchers. Its v2.0 architecture cleanly separates three planes plus a cognitive agent layer:

- **Control Plane (`paperforge.json`, `paperforge/actions/`, `paperforge/probes/`, `paperforge/runtime_installer.py`, `plugin/src/client/`)**: The Obsidian plugin is a typed thin client (`PaperForgeClient` in `paperforge/plugin/src/client/paperforge-client.ts`) that communicates with Python solely through structured `PFResult` JSON, the frozen NDJSON progress stream (`core/streaming.py`), declarative action descriptors in `paperforge/actions/registry.py`, and Schema-v2 capability probes in `paperforge/probes/`. Command strings and raw argv never cross the wire.
- **Data Plane (`paperforge/providers/`, `paperforge/worker/`, `paperforge/render_audit.py`, `paperforge/reconcile_figures.py`)**: Deterministic pipeline stages transform Better BibTeX (BBT) exports into formal Markdown notes, normalized OCR raw blocks via pluggable `OCRProvider` adapters, V3-structured artifacts (`blocks.structured.jsonl`, inventories, cropped assets, `render/fulltext.md`), and audited render consistency reports.
- **Retrieval & Pluggable Embedding Plane (`paperforge/memory/`, `paperforge/retrieval/`, `paperforge/embedding/providers/`)**: SQLite + FTS5 metadata/body retrieval (`paperforge.db`) combined with `sqlite-vec` (`vec0`) hybrid search driven by unified embedding provider resolution (`openai_sdk` and `requests`).
- **Agent Layer (`paperforge/skills/paperforge/`)**: Interactive cognitive workflows (`/pf-deep`, `/pf-paper`, retrieval routing via `query-plan`) operate strictly over Worker-prepared canonical outputs and CLI contracts. Workers never trigger Agents, and Agents never mutate underlying SQLite/OCR stores directly.

---

## Control Plane & Privacy Boundary

- **Managed Runtime Pointer**: `paperforge runtime install|update|repair|status` manages an isolated Python runtime and atomically publishes a `pointer.json` record only after candidate verification succeeds. The plugin treats the pointer as read-only and never mutates the active environment in-place.
- **Modular Capability Probes (`paperforge/probes/`)**: Six domain probe modules (`installation.py`, `library.py`, `ocr.py`, `memory.py`, `maintenance.py`, `help.py`) plus shared Schema-v2 envelope builders (`envelope.py`) synthesize semantic read models consumed by Dashboard and Settings views; `paperforge/commands/probe.py` acts as a compatibility facade and CLI dispatcher.
- **Declarative Action Registry (`paperforge/actions/registry.py`)**: Owns action metadata (`safety_class`, `confirmation_required`, `interruptible`, `scope`) and preflight projections (`preflight_projection.py`).
- **Support & Issue Egress Redaction**: User-facing support diagnostics and GitHub issue drafts (`PublicSupportReport` in `paperforge/plugin/src/primitives.ts` and `PublicIssueDraft` in `paperforge/plugin/src/views/modals.ts`) allowlist structured public fields (known OCR reason codes, bounded counts, static labels) and redact local paths, tokens, paper titles, PDF filenames, and raw stderr/stage logs.

---

## Data Flow & V3 OCR Contract

The complete pipeline flows from Zotero exports to Obsidian notes and retrieval stores through deterministic, resumable stages:

```text
+----------+     Better BibTeX      +-----------------------------------+
|  Zotero  |  ------------------->  | <system_dir>/PaperForge/exports/  |
| Library  |     auto-export        | library.json                      |
+----------+                        +-----------------+-----------------+
                                                      |
                                              paperforge sync
                                                      v
+-----------------------------------+  +-----------------------------------+
| <resources_dir>/<literature_dir>/ |  | <system_dir>/PaperForge/indexes/  |
| <KEY> - <Title>.md (Formal Notes) |  | formal-library.json (v2 envelope) |
+-----------------------------------+  +-----------------+-----------------+
                                                         |
                                      paperforge ocr run / action ocr.run
                                                         v
+-------------------------------------------------------------------------+
| <system_dir>/PaperForge/ocr/<KEY>/                                      |
|   raw/                  source_metadata.json, raw_meta.json              |
|   canonical/            blocks.raw.jsonl (provider-normalized truth)    |
|   structure/            blocks.structured.jsonl, figure_inventory.json, |
|                         table_inventory.json, reader_figures.json       |
|   render/               fulltext.md, render-map.json,                   |
|                         render.consistency.json, materialization...json |
|   assets/               cropped figure & table images                   |
|   health/               ocr_health.json                                 |
|   index/                structure-tree.json, role-index.json,           |
|                         result-hash.txt (atomic publication gate)       |
|   meta.json, fulltext.md (compat projection)                            |
+------------------------------------+------------------------------------+
                                     |
              paperforge memory build + paperforge embed build
                                     v
+-------------------------------------------------------------------------+
| <system_dir>/PaperForge/indexes/paperforge.db                           |
|   papers + paper_fts (FTS5) + body_units / body_units_fts               |
|   object_units + vec_body / vec_objects / vec_fulltext (sqlite-vec)     |
+-------------------------------------------------------------------------+
```

### Pluggable OCR Provider Seam (`paperforge/providers/`)

- `paperforge/providers/base.py` defines the runtime-checkable `OCRProvider` protocol (`submit_pdf`, `poll_job`, `parse_result`) and `ProviderStatus`.
- `paperforge/providers/__init__.py` exposes `resolve_ocr_provider(provider_name)` and inbound schema helpers (`extract_paddleocr_result_url`, `iter_paddleocr_page_results`, `parse_paddleocr_page_blocks`, `parse_paddleocr_raw_blocks`).
- `paperforge/worker/ocr_blocks.py` and `paperforge/worker/ocr.py` normalize vendor responses exclusively through the provider boundary before writing `canonical/blocks.raw.jsonl`.

### V3 OCR Pipeline Stage Contract

The V3 derived pipeline (enabled by default; `OCR_PIPELINE_V3=0` reverts to legacy order) executes a strict contract sequence because downstream stages consume candidate and ownership fields stamped by earlier ones:

```text
raw blocks
  → build_structured_blocks(..., normalize_mode="seed_only")   # seed_role + signatures
  → pre_match_normalize                                        # shadow role_candidate
  → run_association_stage (ocr_object_stage.py)                # figures, bio cleanup, tables, conflicts
  → post_match_normalize                                       # tail settlement + role commit
  → commit_object_roles / apply_object_writebacks              # _object_owner_id + figure_inner_text
  → write inventories & blocks.structured.jsonl
  → extract_and_write_objects                                  # bbox-expanded image/table crops
  → render_fulltext_markdown & write_render_outputs            # fulltext.md + render.consistency.json
  → publish_ocr_result_hash                                    # clear result-hash.pending gate
```

Heavy native libraries (`pymupdf`, `PIL`, `torch`, `chromadb`, `pdfplumber`) are strictly lazy-loaded inside worker functions (enforced by `tests/test_import_weight.py` and `check_module_graph.py` R4) so Windows multiprocessing spawn never imports them at module load time.

### Stage-by-Stage Overview

| Stage | Primary Command / Module | Inputs | Authoritative Outputs |
|-------|--------------------------|--------|-----------------------|
| **1. Export** | Better BibTeX | Zotero items | `exports/library.json` |
| **2. Sync** | `paperforge sync` | `library.json` | `indexes/formal-library.json`, Formal Notes |
| **3. OCR Raw** | `paperforge ocr run` | Source PDF via `pdf_resolver.py` | `canonical/blocks.raw.jsonl`, `raw/` |
| **4. OCR Derived** | `paperforge ocr rebuild` / `ocr_rebuild.py` | `blocks.raw.jsonl`, `source_metadata.json` | `structure/`, `assets/`, `render/`, `index/result-hash.txt` |
| **5. Memory Substrate** | `paperforge memory build` | `formal-library.json`, published OCR `index/` + `structure/` | `indexes/paperforge.db` (FTS5 + structural units) |
| **6. Vector Index** | `paperforge embed build` | `body_units`, `object_units` | `vec_*` virtual tables in `paperforge.db` |

---

## Retrieval & Pluggable Embedding Plane

All embedding operations route through `paperforge/embedding/providers/__init__.py`:

- `check_embedding_provider_prereqs(vault)` verifies runtime dependencies for the configured `vector_db_provider_type` (`openai_sdk` checks `openai`; `requests` checks `requests` and does not require `openai`).
- `resolve_embedding_provider(vault, default_cls=...)` instantiates `paperforge.embedding.providers.openai_compatible.OpenAICompatibleProvider` or `paperforge.embedding.providers.requests_fallback.OpenAICompatibleProvider` uniformly across `preflight.py`, `builder.py`, `dim_detect.py`, and `search.py`.

---

## Retrieval Architecture

PaperForge 的检索系统分两层：**工作流意图**（由 Agent molecule 编排）和 **检索意图**（由 query-plan 规划）。

```
用户工作流意图
├── read_known_paper
├── discover_papers
├── find_supporting_evidence
├── deep_analyze_paper
└── capture_project_knowledge
        ↓
检索意图（query-plan 分类）
├── locate    — 定位一篇已明确的论文
├── discover  — 发现一批相关论文
└── content   — 查找正文中的事实、参数、方法或证据
        ↓
CLI 执行器
├── paper-context [--structure]
├── search
└── retrieve [--deep] [--paper KEY]
```

### 合约要点

1. **query-plan 是唯一的检索规划器。** Agent 不自行选择检索策略。query-plan 返回 `primary` + 最多一个 `fallback`。
2. **最多一次 fallback。** primary 零结果时才触发 fallback。scope=paper 时不执行 fallback。
3. **StructureTree** 是章节导航地图，不是全文内容替代品。`paper-context --structure` 返回论文的章节树（node_id、parent_id、path、depth、page_span），用于确定 evidence 所在章节；同时返回用户在内置 PDF 批注器留下的 `user_annotations`（`questions` 与 `highlights`）。
4. **Evidence 由结构化字段判定。** `source_kind=body` + `structure_resolved=true` = 可靠正文证据；`source_kind=object` = 图表证据。
5. **全并集混合检索（BM25 ∪ Vector）。** `retrieve --deep` 对 FTS5 BM25 与 `vec_body` / `vec_objects` 执行并集融合与元数据水合，不会因单一 BM25 命中而截断纯语义向量结果，亦可在未构建向量索引时回退到 BM25 检索。
6. **Agent 只理解 CLI contract。** 不接触 vec0、FTS5、embedding、SQLite 等存储层实现。

### 简化过程

v1.5 用三个检索意图取代了旧版的 L4 gateway 系统（content-discovery、scoped-fetch、paper-lookup、paper-navigation）。
旧 gateway 命令保留向后兼容，但 Agent 不再使用。

## Directory Structure

PaperForge uses structured directories under the Obsidian vault root. All paths are configured in schema-v2 `paperforge.json` and resolved through `paperforge/config.py` (`load_config` / `resolve_paths`, see [ADR-001](#adr-001-config-precedence)). Fresh setups default `system_dir` to hidden `.paperforge` (keeping tens of thousands of OCR JSONL/markdown intermediates invisible to Obsidian's file scanner), while legacy `System/PaperForge` vaults remain supported and can migrate in place via `paperforge migrate-storage`. Internal `fulltext.md` stays inside the engine directory; user-facing visual crops materialize as `<workspace>/assets/<KEY>_figure_NNN.jpg` / `<KEY>_table_NNN.jpg` and non-destructive PDF highlights/crops persist in `<workspace>/annotations.jsonl` (+ SQLite `paper_annotations`).

```text
{vault_root}/
|-- <resources_dir/>                          # User data and notes (indexed by Obsidian)
|   |-- <literature_dir/>                     # Formal literature notes & per-paper workspaces
|       |-- <domain>/
|           |-- ABCDEFG - Paper Title/
|               |-- ABCDEFG - Paper Title.md  # Formal note + ## 精读 + ![[ABCDEFG_figure_001.jpg]]
|               |-- annotations.jsonl         # Non-destructive Zotero-style PDF sidecar annotations
|               |-- assets/
|                   |-- ABCDEFG_figure_001.jpg  # Unique key-prefixed figure crop (collision-free)
|                   |-- ABCDEFG_ann_xxx.jpg     # PDF area selection screenshot crop
|
|-- .paperforge/ (or <system_dir>/PaperForge/) # Engine artifacts hidden from Obsidian indexer
|   |-- exports/
|   |   |-- library.json                      # Zotero BBT auto-export
|   |-- indexes/
|   |   |-- formal-library.json               # Canonical asset index (v2 envelope)
|   |   |-- paperforge.db                     # SQLite FTS5 + retrieval units + vec0 + paper_annotations
|   |-- ocr/
|       |-- ABCDEFG/                          # One OCR store per zotero_key
|           |-- raw/                          # source_metadata.json, raw_meta.json
|           |-- canonical/blocks.raw.jsonl
|           |-- structure/                    # blocks.structured.jsonl, figure/table inventories
|           |-- render/                       # internal machine fulltext.md, render.consistency.json
|           |-- assets/                       # source figure/table crops (syncs to workspace/assets/)
|           |-- health/ocr_health.json
|           |-- index/                        # structure-tree.json, role-index.json, result-hash.txt
|           |-- meta.json
|           |-- fulltext.md                   # Internal machine projection (hidden from user workspaces)
|
|-- Zotero/storage/                           # External or vault-local Zotero PDF attachments
|
|-- .agents/skills/paperforge/                # Deployed PaperForge agent skill
|-- paperforge.json                           # Canonical schema-v2 configuration
|-- .env                                      # Local secrets/overrides (never exported by diagnostics)
```

### Directory Rationale

| Directory | Purpose | Generated By | Modified By |
|-----------|---------|--------------|-------------|
| `<resources_dir>/<literature_dir>/` | Formal notes (`<KEY>.md`), per-paper `annotations.jsonl`, unique `<KEY>_*.jpg` crops | `paperforge sync`, PDF Annotator (`PaperForgePdfView`) | Agent (writes `## 精读`), User |
| `.paperforge/exports/` | Better BibTeX JSON export | Zotero + BBT | Read-only for PaperForge |
| `.paperforge/indexes/` | Canonical asset index + SQLite FTS5/`vec0`/`paper_annotations` database | `paperforge sync`, `memory build`, `embed build` | Python backend only |
| `.paperforge/ocr/` | Normalized raw OCR, V3 structured blocks, internal machine `fulltext.md` (hidden from Obsidian) | `paperforge ocr`, `ocr rebuild` | Read-only for Agent / OCR Workspace diagnostic preview |
| `<zotero_data_dir>/` | Vault-local or external Zotero data directory (`storage/`) | User (setup step) | Read-only for PaperForge |

---

## Module Boundaries & Architecture Gates

Module boundaries are enforced in automated CI (`L0 static` + Python/Plugin suites) rather than convention alone:

| Gate | Tool / Test | What It Enforces |
|------|-------------|------------------|
| **Module Graph & Layering** | `scripts/check_module_graph.py --check` (`tests/test_module_graph.py`) | **R1** zero import cycles (`rings: []`); **R2/R2b** no cross-module `_private` access (aliased or local-shadowed) outside shrinking frozen ratchet; **R3** zero `worker/ -> commands/` or `worker/ -> plugin/` violations (`layer_violations: {}`); **R4** no new top-level heavy imports (`torch`, `chromadb`, `fitz`, `pymupdf`, `pdfplumber`, `PIL`). |
| **Worker Import Weight** | `tests/test_import_weight.py` | Subprocess check proving importing `paperforge.worker.ocr` never pulls in `torch`, `chromadb`, `pdfplumber`, `fitz`, `pymupdf`, or `PIL`. |
| **Cross-Layer Contract Audit** | `paperforge/architecture_audit/` (`docs/architecture-audit-2026-08-06/build_audit.py --check`) | Python AST + TypeScript AST collectors verifying single mutation/publication authorities, read-only query surfaces, cooperative stop authority, and display-only version restore. |
| **Plugin Transport Ratchet** | `tests/test_architecture_boundaries.py` & plugin Vitest | `PaperForgeClient` owns all subprocess spawns and error redaction; UI views consume typed DTOs only. |
| **CI Shard Partition** | `scripts/ci_shard.py --write` (`tests/test_ci_shard_map.py`, `tests/test_ci_coverage_contract.py`) | Ensures every tracked test file is covered by the merge gate without blind spots. |

---

## Diagnostics & Troubleshooting

PaperForge provides layered read-only diagnostic surfaces before mutating vault artifacts:

1. **System & Environment Health (`paperforge probe all --json`)**: Queries the 6 modular probes in `paperforge/probes/` (`installation`, `library`, `ocr`, `memory`, `help`, `maintenance`) to inspect managed runtime status, config validity, index health, and pending repairs without side effects.
2. **Per-Paper End-to-End Bottleneck Locator (`paperforge inspect <query> [--json]`)**: Implemented in `paperforge/commands/inspect_paper.py`. Resolves a paper by `zotero_key`, `citation_key`, `DOI`, title, or OCR directory and reports structured status across all 6 stages (`source`, `lineage`, `ocr`, `objects_and_render`, `memory`, `vectors`) plus actionable remediation commands. Opens `paperforge.db` strictly via SQLite `?mode=ro` URI when present and leaves the vault byte-identical.
3. **OCR Provider Connectivity (`paperforge ocr doctor [--live]`)**: Verifies OCR endpoint reachability and response parsing.
4. **Offline V3 Stage Debugger (`python scripts/dev/ocr_rebuild_paper.py --dump-stages-only --ocr-dir <ocr_root> <KEY>`)**: Replays the 5 in-memory V3 structural stages (`1_seed_roles` → `2_pre_match_normalize` → `3_object_matching` → `4_post_match_normalize` → `5_object_writebacks`) from `canonical/blocks.raw.jsonl` and emits role counts and block-level state transitions to `stages_summary.json`.

---

### Render Reconciliation and R/P Authority

The render reconciliation layer is an independent post-render consumer. It reads existing OCR inventory, render artifacts, materialization provenance, audit output, and optional PDF evidence. It does not modify the preceding OCR or front-render modules (`ocr_figures.py`, `ocr_objects.py`, `ocr.py`, `ocr_rebuild.py`, or `ocr_render.py`).

```text
existing OCR/render output
        ↓
render audit
        ↓
R/P reconciliation report
        ├── R exact plans → isolated staging → manifest-gated promote-r
        ├── P proposals → human review → accept-proposal
        └── blocked identity/ownership/source cases
```

The authority boundary is deliberate:

- Duplicate canonical `figure_id` occurrences, cross-canonical `(page, block_id, normalized_bbox)` claims, duplicate provenance paths, malformed provenance, and unavailable fulltext sources are blocked. Reconcile never chooses a winner or merges `table_html` into a figure.
- R promotion is relationship-exact: it verifies identity, ordered refs, ownership, source snapshot, staged outputs, destination CAS, journal recovery, and post-audit rollback. Recovery accepts only journal schema 2, transaction paths under `.paperforge-r-promotion/<32-hex-id>`, shared allowlisted destinations (`assets/figures/*.jpg`, `render/figures/*.md`, `render/materialization.provenance.json`, plus P-only `structure/figure_inventory.json` and `render/reconciliation.proposals.json`), in-transaction integer `.bak` files, and non-symlink raw path components; unsafe paths fail closed. It does not prove semantic figure coverage.
- A committed promotion never rolls back because the final report refresh or cleanup fails. `state=committed` recovery does not require backups, best-effort cleans the transaction directory, and removes the journal while preserving production. Normal promotion catches cleanup `OSError` after the commit marker and returns `committed=true, cleanup=pending` with `cleanup_error`, leaving the journal for the next recovery. A report that writes successfully but returns audit `state=FAILED` is surfaced as `report_refresh=written` plus `report_audit_state=FAILED`; refresh exceptions/non-object results use `report_refresh=failed`. The shared `write_render_outputs` boundary handles automatic audit exceptions fail-closed by atomically replacing any prior consistency report with `state=FAILED`; if replacement fails, it attempts to remove the prior report rather than leave it as current.

- P acceptance is the sole authority action that may create a reviewed canonical figure. It requires the caller-supplied SHA-256 of the exact reviewed `final-plan.json`, then revalidates that plan's live snapshot, exact staged paths, plan-owned member refs, unique canonical identity/asset ownership, and valid staged image/Markdown. It uses the same paper lock, schema-v2 journal, destination CAS, atomic writes, rollback-before-commit, committed-cleanup recovery, provenance merge, and post-audit/report-refresh boundary as R. It may update only the accepted figure's canonical inventory row, JPG, Markdown, materialization provenance, and proposal report; it never changes OCR blocks, source PDFs, asset indexes, `meta.json`, or user-authored notes.
- An existing image is not considered authoritative merely because it exists. Missing, ambiguous, unreadable, or mismatched materialization provenance is surfaced as `R_CONTENT_UNVERIFIED` and cannot be promoted or treated as an exact repair.
- Fulltext reconciliation requires a valid canonical figure inventory. Missing, unreadable, non-object, non-list, or malformed authority rows produce `F0_CANONICAL_AUTHORITY_UNAVAILABLE`, set `mutation_blocked`, and emit no patches.
- P remains a human-authority action, not an automatic consequence of a dry-run. `render reconcile --json` exposes each staged plan's `final_plan_hash`; acceptance may create the canonical object only when the supplied hash selects the exact reviewed plan bytes (identical duplicate bytes use a stable path tie-break) and its live authority checks pass. Bounded-slot anchors derive from unique, non-conflicted `main` rows.
- `render reconcile` is staging-only. `render promote-r` requires explicit object IDs or `--all`; production batch rollout is a separate owner gate.
Current known limits are part of the contract: semantic figure-coverage suspects remain diagnostic and never auto-repaired; no bbox/pixel ratio establishes that a panel was not absorbed by `table_html`. Fulltext duplicate canonical identities and unavailable fulltext authority block all patches rather than allowing a partial mutation.

The Reconcile mutation engine is **FROZEN** under the extension contract (`docs/RECONCILE-EXTENSION-CONTRACT.md`). Future detectors must remain read-only finding producers without implementing private execution paths. The system's cross-layer integration follows the 5 backend contracts and 6 product projection domains documented in `docs/BACKEND-FRONTEND-CONTRACT-MAPPING.md`.
---



## Commands Package

### Why `paperforge/commands/`?

In v1.1 and earlier, CLI commands were implemented directly in `cli.py` or invoked through the legacy `literature_pipeline.py` script. This created three problems:

1. **Code duplication**: The same sync logic existed in the CLI path and the worker script path.
2. **Test fragility**: CLI tests had to patch `sys.path` and mock imports differently from worker tests.
3. **Agent divergence**: Agent commands (`/pf-deep`) could not reuse CLI logic because the CLI was tightly coupled to `argparse`.

In Phase 9 (v1.2), we extracted shared command logic into `paperforge/commands/` — a package where each module implements a single command as a pure function taking an `args` namespace. Both the CLI (`cli.py`) and Agent skills import from this package.

### Registry Pattern

The `commands/__init__.py` exposes a registry for dynamic dispatch:

```python
# paperforge/commands/__init__.py
_COMMAND_REGISTRY: dict[str, str] = {
    "sync":   "paperforge.commands.sync",
    "ocr":    "paperforge.commands.ocr",
    "deep":   "paperforge.commands.deep",
    "repair": "paperforge.commands.repair",
    "status": "paperforge.commands.status",
}

def get_command_module(name: str):
    """Dynamically import a command module by name."""
    import importlib
    module_path = _COMMAND_REGISTRY.get(name)
    if module_path is None:
        raise ValueError(f"Unknown command: {name}")
    return importlib.import_module(module_path)
```

### Command Module Structure

Each command module follows a uniform contract:

```python
# paperforge/commands/sync.py
import argparse

def run(args: argparse.Namespace) -> int:
    """Execute the command. Returns exit code (0 = success)."""
    # 1. Resolve inputs from args namespace
    vault = getattr(args, "vault_path", None)
    cfg = getattr(args, "cfg", {})

    # 2. Import worker functions (with fallback for test patching)
    run_selection_sync = _get_run_selection_sync()

    # 3. Execute business logic
    if getattr(args, "selection", False) or not getattr(args, "index", False):
        run_selection_sync(vault)
    if getattr(args, "index", False) or not getattr(args, "selection", False):
        run_index_refresh(vault)

    return 0
```

### CLI Integration

`cli.py` dispatches to command modules after resolving the vault and loading config:

```python
# paperforge/cli.py (excerpt)
if args.command == "sync":
    from paperforge.commands import sync
    return sync.run(args)

if args.command == "status":
    from paperforge.commands import status
    return status.run(args)

if args.command == "deep-reading":
    from paperforge.commands import deep
    return deep.run(args)
```

### Agent Integration

Deployed skills in `.agents/skills/paperforge/` call documented `paperforge` CLI JSON contracts (`query-plan`, `paper-context`, `search`, `retrieve`, `inspect`) rather than mutating vault stores or SQLite directly.

### Backward Compatibility

Old command names (`selection-sync`, `index-refresh`, `ocr run`) are mapped to the new unified commands in `cli.py`:

```python
if args.command == "selection-sync":
    from paperforge.commands import sync
    args.selection = True
    args.index = False
    return sync.run(args)
```

---

## Design Decision Records (ADR)

### ADR-001: Config Precedence & Fail-Closed Authority

**Status:** Accepted (updated v2.0)
**Phase:** 1 (Foundation) -> Config v2 (#142)
**Context:** PaperForge needs to support multiple configuration sources: built-in defaults, schema-v2 `paperforge.json`, process environment variables, and explicit invocation overrides, while refusing silent guesses or secret fields in config files.
**Decision:** Python (`paperforge/config.py:load_config`, `resolve_paths`) is the sole config parser, validator, and writer, enforcing four deterministic precedence levels:

1. **Built-in defaults** (`FIELD_SPECS`)
2. **`paperforge.json`** (schema v2 nested `vault_config` + top-level scalar fields)
3. **Process environment variables** (`PAPERFORGE_*`, `VECTOR_DB_*`, `PADDLEOCR_*`, `ZOTERO_DATA_DIR`)
4. **Explicit invocation overrides**

Missing, corrupt, legacy (`config.migration_required`), future-schema, or secret-bearing configs fail closed. `paperforge_paths()` and `load_vault_config()` delegate to `resolve_paths()` and `load_config()`.
**Consequences:**
- (+) Predictable fail-closed resolution shared across CLI, workers, probes, and actions.
- (+) No secret leakage into `paperforge.json`; credentials are managed separately via `auth`.
- (+) Testable via explicit overrides without mutating global state.

---

### ADR-002: Pipeline Split into Worker/Agent

**Status:** Accepted
**Phase:** 1 (Foundation)
**Context:** The original prototype mixed automated tasks (sync, OCR) with interactive tasks (deep reading) in a single script. This made it unclear what ran automatically vs. what required human judgment.
**Decision:** Split the system into two layers:
- **Worker layer**: Automated, deterministic, CLI-triggered. Handles mechanical tasks.
- **Agent layer**: Interactive, reasoning-driven, user-triggered. Handles cognitive tasks.

Workers never trigger Agents, and Agents never trigger Workers. The handoff point is the formal note frontmatter: users set `do_ocr: true` or `analyze: true`, then run the appropriate worker or agent command.
**Consequences:**
- (+) Clear mental model: users understand what runs automatically vs. on demand.
- (+) Isolated failure domains: an OCR failure cannot corrupt an Agent's analysis.
- (+) Agent independence: users can skip automation and trigger deep reading manually.
- (-) Requires user to run multiple commands instead of a single "do everything" button.

---

### ADR-003: OCR Async with State Machine

**Status:** Accepted
**Phase:** 2 (OCR Integration)
**Context:** PaddleOCR API calls are asynchronous and may take minutes for large PDFs. The system must handle pending, processing, completed, and failed states without blocking the user.
**Decision:** Track OCR status through a finite state machine (`pending` -> `processing` -> `done`/`failed`) persisted in two places:
1. Per-paper `meta.json` in `<system_dir>/PaperForge/ocr/<key>/`
2. Per-paper `ocr_status` field in the formal note frontmatter

The `paperforge ocr` command scans all formal notes for `do_ocr: true` and `ocr_status != done`, uploads PDFs, and updates both persistence layers. The `paperforge deep-reading` command checks `ocr_status == done` before listing a paper as "ready."
**Consequences:**
- (+) Resilient to crashes: status is persisted, not in-memory.

---

### ADR-003a: OCR Reading Order — Layered Pipeline

**Status:** Proposed (May 2026)
**Phase:** OCR Improvement

**Context:** The original `paperforge/worker/ocr.py` bundled block normalization, figure/caption grouping, body-width estimation, embedded-media suppression, column reordering, and markdown emission into one file with intertwined responsibilities. Fixes to one page class often regressed others because rules were not separated by decision responsibility.

**Decision:** Refactor OCR processing into explicit layers, treating PaddleOCR output as the primary structural prior with PaperForge rules as confidence-aware local corrections.

Layer responsibilities:

| Layer | Module | Role |
|-------|--------|------|
| Normalization | `ocr_normalize.py` | Text cleanup, bbox normalization, raw provenance |
| Role Assignment | `ocr_roles.py` | Assign document roles (`section_heading`, `body_paragraph`, `figure_caption`, etc.) with Paddle labels as priors |
| Body Spine | `ocr_body_spine.py` | Extract body-text candidates; exclude figures, captions, references from body ordering |
| Layout Zones | `ocr_layout.py` | Detect local 1/2/3-column regimes per zone (not per page); build body reading order |
| Attachment | `ocr_attach.py` | Bind captions to media; attach non-body objects to body spine anchors |
| Emission | `ocr_emit.py` | Serialize ordered spine + attachment graph into markdown |

Design principles:

- PaddleOCR `block_order`, labels, and local grouping are the default prior
- PaperForge rules only override when contradiction evidence is strong
- Low-confidence decisions degrade conservatively (preserve OCR prior)
- Section headings are first-class structural signals, not subject to media suppression
- Fallback: when model and rules disagree without decisive evidence, preserve OCR order

**Consequences:**

- (+) Failures are diagnosable by layer: role, spine, regime, ordering, or attachment
- (+) Mixed-regime pages (body + figure + caption) no longer break body flow
- (-) Increased module count requires fixture-driven regression matrix before rollout
- (+) Idempotent: re-running `paperforge ocr` skips already-done papers.
- (+) Observable: users can check status without re-running the worker.
- (-) Requires dual persistence: `meta.json` and formal note frontmatter must stay in sync.

---

### ADR-004: Base Views Config-Aware

**Status:** Accepted
**Phase:** 3 (Base Views)
**Context:** Obsidian Base views (`.base` files) provide a database-like UI for formal notes. Hardcoded paths in Base views break when users customize their directory structure.
**Decision:** Generate Base views from Jinja2 templates at setup time, injecting resolved paths from `paperforge_paths()`. Templates live in `paperforge/templates/bases/` and are rendered into `<base_dir>/` with user-configured directory names substituted.
**Consequences:**
- (+) Base views work out of the box regardless of directory configuration.
- (+) Users can customize paths in `paperforge.json` without breaking views.
- (+) Template-based generation is easier to maintain than static files.
- (-) Requires template maintenance when new fields are added to formal notes.

---

### ADR-005: Deep Reading Three-Pass

**Status:** Accepted
**Phase:** 4 (Deep Reading)
**Context:** Deep reading of academic papers is a skill. The system needs a structured method that ensures comprehensive understanding without overwhelming the user.
**Decision:** Adopt S. Keshav's three-pass method, implemented as three distinct phases in `/pf-deep`:

1. **Pass 1 — Overview (5-10 minutes):** Scan title, abstract, headers, conclusions. Identify paper type, context, and contribution.
2. **Pass 2 — Content:** Read figures, tables, and methodology in detail. Reconstruct the author's argument.
3. **Pass 3 — Critical:** Evaluate assumptions, limitations, and relevance to the reader's own research. Generate迁移思考 (transfer thinking).

Each pass produces structured Markdown output inserted into the formal note under `## 精读`.
**Consequences:**
- (+) Research-backed methodology ensures consistent analysis quality.
- (+) Structured output makes notes searchable and comparable.
- (+) Three passes naturally bound Agent context window usage.
- (-) Requires OCR completion (Pass 2 needs figures/tables).

---

### ADR-006: Fixture-Based Smoke Tests

**Status:** Accepted
**Phase:** 5 (Testing)
**Context:** Integration tests for a literature pipeline require realistic inputs: Zotero JSON, PDFs, and Obsidian vault structures. Generating these dynamically in every test run is slow and non-deterministic.
**Decision:** Commit deterministic test fixtures to `tests/sandbox/` and `tests/fixtures/`:
- `library.json` fixtures with known Zotero items
- Minimal PDF fixtures for OCR testing
- Complete vault structures generated by `generate_sandbox.py`

Smoke tests (Phase 8) use these fixtures to validate end-to-end behavior without requiring a live Zotero instance or PaddleOCR API key.
**Consequences:**
- (+) Tests run offline and in CI without external dependencies.
- (+) Deterministic: same input always produces same output.
- (+) Fast: no network calls, no PDF generation during test runs.
- (-) Fixtures must be updated when data formats change.
- (-) Repository size increases with binary fixtures.

---

### ADR-007: CLI/Worker Consistency

**Status:** Accepted
**Phase:** 6 (CLI Hardening)
**Context:** Early versions had path resolution logic duplicated between `literature_pipeline.py` and the CLI wrapper. Changes to one often broke the other.
**Decision:** Extract shared path resolution and config loading into `paperforge/config.py`. Both the CLI and worker scripts import from this module. The `paperforge_paths()` function returns a dict of resolved `Path` objects used consistently across the system.
**Consequences:**
- (+) Single source of truth for path construction.
- (+) CLI `paperforge paths --json` outputs exactly the paths workers use.
- (+) Tests can patch `paperforge_paths` to redirect output.
- (-) Requires careful import ordering to avoid circular dependencies.

---

### ADR-008: Three-Way Repair

**Status:** Accepted
**Phase:** 7 (Repair & Consistency)
**Context:** Over time, two sources of truth for a paper's status can diverge: the formal note frontmatter and the actual OCR output directory. Users may manually edit one without updating the other.
**Decision:** Implement `paperforge repair` with divergence detection:
1. Scan all formal notes
2. Compare `ocr_status` in formal note vs. `meta.json`
3. Report discrepancies in a structured table
4. With `--fix`, propagate the most reliable source (OCR directory > formal note)

Default mode is `--dry-run`: show discrepancies without modifying files.
**Consequences:**
- (+) Detects and fixes silent data drift.
- (+) Safe by default: dry-run lets users review before applying.
- (+) Verbose mode explains exactly which source was chosen and why.
- (-) Cannot detect semantic divergence (e.g., user intentionally wants different statuses).


---

### ADR-009: Rollback in Prepare

**Status:** Accepted
**Phase:** 8 (Agent Hardening)
**Context:** The `prepare_deep_reading()` function in `ld_deep.py` writes multiple files (figure-map.json, chart-type-map.json) and modifies the formal note before the Agent begins reading. If any step fails, partial writes leave the vault in an inconsistent state.
**Decision:** Implement rollback tracking in `prepare_deep_reading()`:
1. Before writing, snapshot the formal note content.
2. Track every file written or modified in a `written_files` list.
3. If any step raises an exception, delete all written files and restore the formal note.
4. Return an error dict with the exception message.

Tests in `test_prepare_rollback.py` verify this behavior by mocking failures at each step.
**Consequences:**
- (+) Failed preparations do not corrupt user data.
- (+) Idempotent retries: user can re-run `/pf-deep` after fixing the issue.
- (+) Explicit contract: `prepare_deep_reading()` returns `{"status": "ok"}` or `{"status": "error"}`.
- (-) Slightly more complex prepare logic; requires careful file tracking.

---

### ADR-010: Command Unification

**Status:** Accepted
**Phase:** 9 (Systematization)
**Context:** v1.1 had fragmented command namespaces: CLI used `selection-sync`/`index-refresh`, Agent used `/LD-deep`/`/LD-paper`, and legacy scripts used `/lp-*` prefixes. This confused users and complicated documentation.
**Decision:** Unify under a single namespace:
- **CLI:** `paperforge sync` (replaces `selection-sync` + `index-refresh`), `paperforge ocr` (replaces `ocr run`)
- **Agent:** `/pf-deep`, `/pf-paper`, `/pf-ocr`, `/pf-sync`, `/pf-status`
- **Code:** Shared implementations in `paperforge/commands/` package

Old commands remain as backward-compatible aliases in `cli.py` but are deprecated in documentation.
**Consequences:**
- (+) Single mental model: one command name maps to one concept.
- (+) Reduced documentation surface: one doc per command, not three.
- (+) Easier to add new platforms: agent commands reference the same registry.
- (-) Breaking change for v1.1 users: requires migration guide (see `docs/MIGRATION-v1.2.md`).

---

### ADR-011: Zotero Path Normalization Strategy

**Status:** Accepted
**Phase:** 11 (Path Normalization & Architecture Hardening)
**Context:** Better BibTeX (BBT) exports attachment paths in three different formats depending on export settings and platform: absolute Windows paths (`D:\Zotero\storage\KEY\file.pdf`), `storage:` prefixed paths (`storage:KEY/file.pdf`), and bare relative paths (`KEY/file.pdf`). PaperForge needs to normalize these to a single internal representation and generate valid Obsidian wikilinks that work across Windows and macOS/Linux. Additionally, users may keep their Zotero data directory outside the Obsidian vault, requiring junction/symlink resolution.

**Decision:** Implement a three-stage normalization pipeline with explicit decisions for each ambiguity:

1. **D-01 — Normalize all paths to `storage:KEY/filename.pdf`:** `_normalize_attachment_path()` handles all three BBT formats and converts them to a unified `storage:` representation with forward slashes. Absolute paths outside Zotero storage get an `absolute:` prefix for explicit handling.

2. **D-02 — Hybrid main PDF selection:** `_identify_main_pdf()` uses a three-priority strategy: (1) attachment with `title == "PDF"`, (2) largest file by size (or shortest title if sizes are equal/unavailable), (3) first PDF in the list. All other PDFs become `supplementary`.

3. **D-03 — Store raw BBT path for debugging:** Every attachment carries `bbt_path_raw` preserving the original export string, enabling diagnosis when normalization produces unexpected results.

4. **D-04 — Extract 8-character storage key:** `zotero_storage_key` is extracted from absolute paths (`.../storage/8CHARKEY/...`) or `storage:8CHARKEY/...` prefix. This key is used for OCR directory naming and cross-referencing.

5. **D-05 — Resolve junctions before computing relative paths:** `absolutize_vault_path()` gains a `resolve_junction=True` parameter. When enabled, Windows junctions/symlinks in the path are resolved to their targets before `relative_to(vault)` is computed, ensuring wikilinks point to the true file location.

6. **D-06 — Track path errors explicitly:** A `path_error` frontmatter field (`not_found`, `invalid`, `permission_denied`) is set when PDF resolution fails. `paperforge repair --fix-paths` can re-run normalization and clear the error if the issue is resolved.

7. **D-07 — Doctor detects Zotero location and recommends junction:** `paperforge doctor` checks whether Zotero is inside the vault, outside with a junction, or missing. When outside without junction, it prints the exact `mklink /J` command needed.

8. **D-08 — Wikilinks use forward slashes exclusively:** All generated `pdf_path` values use `[[relative/path/file.pdf]]` format with `/` separators, even on Windows. `Path.as_posix()` is used instead of string replacement for robustness.

**Consequences:**
- (+) All real-world BBT export formats are handled without user configuration changes.
- (+) Wikilinks are vault-relative and work on all platforms.
- (+) Junctions are transparently resolved; users don't need to know the real Zotero data dir path.
- (+) Path errors are visible, diagnosable, and auto-repairable.
- (-) `storage:` prefix semantics are overloaded: it means "relative to Zotero data dir" in `pdf_resolver.py`, but the actual Zotero structure has an intermediate `storage/` directory. This requires `zotero_dir` configuration to point to the correct level.
- (-) One extra frontmatter field (`path_error`) adds noise to formal notes; it is omitted when empty.

---

### ADR-012: Shared Utilities Extraction (`_utils.py`)

**Status:** Accepted
**Phase:** 14 (Shared Utilities Extraction)
**Context:** Approximately 1,610 lines of utility code were copy-pasted across 7 worker modules; changes to one copy often missed others; bug fixes had to be applied N times. Each worker module independently defined `read_json`, `write_json`, `yaml_quote`, `slugify_filename`, `lookup_impact_factor`, and other helpers — with identical logic but subtle behavioral drifts over time.

**Decision:** Create `paperforge/worker/_utils.py` as a pure leaf module organized by category (JSON I/O, YAML Helpers, String/Path Utils, Journal Database, Constants). The module must never import from `paperforge.worker.*` or `paperforge.commands.*` — only from stdlib and `paperforge.config`. Functions are imported by workers as `from paperforge.worker._utils import read_json, ...`. Re-exports with `# Re-exported from _utils.py for backward compatibility` comments preserve backward compatibility in original modules.

**Consequences:**
- (+) Single source of truth for utility functions — changes in one place propagate to all workers.
- (+) Easier testing — dedicated `_utils.py` unit tests (Phase 19).
- (+) No circular imports — leaf module constraint enforced by code review and consistency audit hook.
- (-) Re-export comments add minor clutter to original worker modules.
- (-) Module must be carefully audited at every change to maintain leaf status (import only stdlib + `paperforge.config`).

---

### ADR-013: Dual-Output Logging Strategy

**Status:** Accepted
**Phase:** 13 (Logging Foundation)
**Context:** The codebase used ad-hoc `print()` calls for all output — user-facing status, diagnostic traces, and error messages. This made it impossible to filter log levels, broke piped command output when diagnostic text appeared on stdout, and provided no structured error reporting for troubleshooting.

**Decision:** Implement a dual-output strategy:
1. `print()` preserved for user-facing formatted output on stdout only — existing piped commands and Agent scripts that parse stdout remain unmodified.
2. `logging.getLogger(__name__)` used for all diagnostic/trace/error output to stderr.
3. A `configure_logging(verbose: bool)` function in `paperforge/logging_config.py` configures the root logger.
4. Log level defaults to `INFO` (from `PAPERFORGE_LOG_LEVEL` env var) and switches to `DEBUG` when `--verbose`/`-v` is passed.

**Consequences:**
- (+) Structured log output with levels, module names, and timestamps — dramatically easier debugging.
- (+) Piped stdout remains clean — downstream consumers (Agent scripts, `grep`) see only user-facing output.
- (+) `--verbose` enables per-module debugging without modifying code.
- (-) Two output channels require documentation — users must know stdout (user-facing) vs stderr (diagnostic).
- (-) Existing `print()` calls for user-facing output remain as-is — behavioral change guarantee maintained.

---

### ADR-014: Native Obsidian Bases View, Daemon-Free State Reactivity & Living Paper Memory (v2.2)

**Status:** Accepted
**Context:** Relying purely on Markdown YAML frontmatter for both user queues (`do_ocr`, `analyze`) and mutable machine states caused redundant YAML rewrites, lacked real-time UI updates between external CLI runs and Obsidian, and exposed overly heavy manual forms in the sidebar and PDF popover. Additionally, Agents lacked an error-tolerant mechanism to anchor highlights onto real PDF pages across OCR hyphenation, symbol drift, and scanned pages.

**Decision:**
1. **Native Obsidian `BasesView` (`paperforge-table`) + YAML Read/Write Decoupling**: `paperforge/worker/base_views.py` configures `.base` files with `type: paperforge-table`, handled by `PaperForgeBasesView` (`plugin/src/views/paperforge-base-view.ts`). Machine state (`ocr_status`, `deep_reading_status`, cognitive counts) renders read-only from SQLite/index via `paperforge memory-card base-snapshot --json`, while user queue checkboxes route through `client.setNoteFlag()`. `asset_index.py:_build_entry` enforces a no-op write guard to skip redundant YAML rewrites.
2. **Daemon-Free Live UI Reactivity (`.state-seq.json`)**: `paperforge/services/state_signal.py` atomically increments `<indexes_dir>/.state-seq.json` on Python state mutations (`sync`, `ocr`, `memory-card`, `annotations`). `main.ts` watches `.state-seq.json` with a 150ms debounce and broadcasts `"paperforge:state-changed"` so open Base tables, PDF viewers, and Dashboard memory cards refresh live without a persistent background daemon.
3. **Evolving Living Paper Memory Cards**: `paper_memory_cards` + `paper_memory_history` (plus `<workspace>/ai/memory-card.json`) maintain 5 refined facets (`idea_logic`, `methods_params`, `research_craft`, `critique_limits`, `my_connection`) updated via `paperforge memory-card refine`.
4. **3-Stage Fuzzy PDF Sentence Grounding (`paperforge/services/pdf_grounding.py`)**: Stage 1 narrows candidate OCR blocks (`±1` page); Stage 2a/2b folds ligatures, hyphenation, and math symbols on PyMuPDF `rawdict` word streams (including same-page cross-column rescue for merged columns); Stage 3 honestly degrades scanned/unmatched blocks to left-margin vertical brackets (`kind="margin"`, `grounding_tier="margin_fallback"`). All AI marks carry `author="agent"` for independent toggling and adoption (`[✓ 采纳]`) in `PaperForgePdfView`.

---

## Extension Points

### Adding a New CLI Command

1. **Create command module** in `paperforge/commands/<command_name>.py`:
   ```python
   import argparse

   def run(args: argparse.Namespace) -> int:
       """Execute the new command."""
       # Your logic here
       return 0
   ```

2. **Register in `paperforge/commands/__init__.py`**:
   ```python
   _COMMAND_REGISTRY = {
       # ... existing commands ...
       "mycommand": "paperforge.commands.mycommand",
   }
   ```

3. **Add CLI parser entry** in `paperforge/cli.py` `build_parser()`:
   ```python
   sub.add_parser("mycommand", help="Description of my command")
   ```

4. **Add dispatch branch** in `paperforge/cli.py` `main()`:
   ```python
   if args.command == "mycommand":
       from paperforge.commands import mycommand
       return mycommand.run(args)
   ```

5. **Assign the new test file to a CI shard and check module boundaries**:
   ```bash
   python scripts/ci_shard.py --write
   python scripts/check_module_graph.py --check
   ```

### Adding an OCR Provider

1. Implement the `OCRProvider` protocol (`paperforge/providers/base.py`) so `submit_pdf`, `poll_job`, and `parse_result` return normalized canonical raw-block schemas.
2. Register the provider in `resolve_ocr_provider()` inside `paperforge/providers/__init__.py`.
3. Add offline contract tests under `tests/unit/` asserting zero impact on `paperforge/worker/ocr_blocks.py` or downstream V3 stages.

### Adding an Embedding Provider

1. Implement `EmbeddingProvider` (`paperforge/embedding/providers/base.py`).
2. Add its prerequisite check and instantiation branch to `check_embedding_provider_prereqs()` and `resolve_embedding_provider()` in `paperforge/embedding/providers/__init__.py`, and register the `vector_db_provider_type` choice in `paperforge/config.py`.
3. Verify `preflight.py`, `builder.py`, `dim_detect.py`, and `search.py` resolve through the factory uniformly without extra optional SDK imports at preflight time.

### Agent Skill Packaging & Platforms

Packaged Agent skill prompts and workflows live in `paperforge/skills/paperforge/` and are deployed into any supported harness directory via `paperforge skill deploy --to <dir>` (default `.agents/skills`). Supported platform IDs are enumerated in `paperforge/config.py:AGENT_PLATFORM_IDS`.

---

### OCR-v2 Structural Role Gate

OCR-v2 treats OCR labels and `assign_block_role()` output as observations, not semantic truth. `build_structured_blocks()` stores `seed_role`, `seed_confidence`, and `seed_evidence` while leaving final roles unassigned. `normalize_document_structure()` builds document-level anchors, zones, families, `abstract_span`, `reference_zone`, and figure/table reader evidence before assigning final high-risk roles.

Any final role in `VERIFY_REQUIRED` must have `role_verification_status: ACCEPT`, `role_source`, and `role_evidence`. If a high-risk seed is not accepted by a verifier, production downgrades it to a safe non-final role or candidate and reports the correction in `role_gate_summary`; it does not silently pass the seed through. After the gate runs, role mutators may only write candidate fields, move before the gate, or re-run the gate.

`render_fulltext_markdown()` consumes accepted artifacts: Abstract from `abstract_span`, References from `reference_zone`, figures from `reader_figures`, and tables from table reader/table inventory artifacts. It must not rebuild semantic sections by globally scanning bare role labels. OCR health includes `role_gate_summary`; corrected seeds are warning/info, while final unverified roles and seed passthrough degrade health.

---

## Glossary

- **Canonical Fact** — a fact whose single authority is a canonical storage location (paperforge.json, formal-library.json, OCR meta/artifacts, paperforge.db, build_state). Never re-derived or duplicated as a competing truth.
- **Semantic Read Model** — a Python-produced, versioned interpretation of canonical facts (`probe(module)`, `probe all`, typed detail commands). The only surface clients may consume for meaning; provenance/freshness-stamped projections, never competing facts.
- **Action Contract** — the declarative Python ActionSpec registry + generic runner: stable `action_id` names an executable operation, producers emit intent only, policy lives in one registry, confirmation is exact per-action, follow-up execution is explicit, and no command string or argv appears on any wire.
- **Bootstrap Adapter** — now read-only in Obsidian: it reads the Python-published runtime pointer and launches Core commands. A separate `paperforge runtime` CLI owns candidate environment creation, package lifecycle, verification, and pointer publication; Vault setup remains per-Vault configuration.
- **Client Cache** — the plugin's display-only last-known CLI responses in `data.json` (per module, `received_at`-stamped), rendered only for stale/error display; actions stay disabled until a fresh response newer than the last mutation arrives. Detail sets are in-memory only.
- **Convergence Tick** — one invocation of `paperforge sync` (external source detection + library sync + `reconcile(all)`), fired by a dumb client timer or headless scheduler. All triggers converge on the same Python semantics.

## Cross-References

- User-facing guide: [`AGENTS.md`](../AGENTS.md)
- Installation instructions: [`docs/getting-started.md`](getting-started.md)
- Command reference: [`docs/COMMANDS.md`](COMMANDS.md)
- Migration guide: [`docs/MIGRATION-v1.2.md`](MIGRATION-v1.2.md)
- Product requirements: `docs/prd-*.md`

---

*PaperForge | Architecture Documentation | For Maintainers and Contributors*
