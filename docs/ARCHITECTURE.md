# PaperForge Lite Architecture

> Maintainer-facing documentation covering the two-layer design, data flow, directory structure, key design decisions, and extension points.
>
> **Last updated:** 2026-04-24 | **Version:** v1.2 | **Target audience:** maintainers and contributors

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Data Flow](#data-flow)
3. [Directory Structure](#directory-structure)
4. [Commands Package](#commands-package)
5. [Design Decision Records (ADR)](#design-decision-records-adr)
6. [Extension Points](#extension-points)

---

## System Overview

PaperForge Lite is a local-first literature workflow that bridges Zotero (reference management) and Obsidian (knowledge management) for medical researchers. The system is intentionally split into two distinct layers: the **Worker layer** and the **Agent layer**. This separation is the defining architectural choice of the project.

The **Worker layer** (`literature_pipeline.py` and the `paperforge/commands/` package) handles all automated, mechanical tasks: detecting new literature from Zotero via Better BibTeX JSON export, generating library records and formal notes, running OCR through the PaddleOCR API, and maintaining state consistency across the system. Workers are deterministic, idempotent where possible, and designed to run without human intervention. They are triggered by CLI commands such as `paperforge sync` or `paperforge ocr`.

The **Agent layer** (OpenCode Agent skills like `/pf-deep` and `/pf-paper`) handles interactive, cognitive tasks: deep reading, critical analysis, figure interpretation, and synthesis writing. Agents require human direction — they are triggered by explicit user commands and operate on data prepared by the Worker layer. An Agent never triggers a Worker automatically, and a Worker never triggers an Agent automatically.

This separation matters for three reasons. First, it keeps the automation layer simple and testable — workers are plain Python functions with clear inputs and outputs. Second, it respects user agency — deep reading is a deliberate act, not a background process. Third, it isolates failure domains: a bug in OCR handling cannot corrupt a user's carefully written analysis, and an Agent hallucination cannot damage the underlying library index.

---

## Data Flow

The complete pipeline flows from Zotero to Obsidian through six stages, with file formats and state transitions at each step.

```
+----------+     Better BibTeX      +---------------------------+
|  Zotero  |  ------------------->  |  library.json (JSON)      |
|  (User   |     auto-export        |  <system_dir>/PaperForge/ |
|  Library)|                        |  exports/                 |
+----------+                        +------------+--------------+
                                                 |
                              paperforge sync --selection
                                                 |
                                                 v
+-----------------------------------+  +---------------------------+
|  library-records/<domain>/<key>.md|  |  Markdown + YAML          |
|  (Control Files)                  |  |  frontmatter              |
+-----------------------------------+  +---------------------------+
                                                 |
                              paperforge sync --index
                                                 |
                                                 v
+-----------------------------------+  +---------------------------+
|  Literature/<domain>/<key> -      |  |  Markdown + YAML          |
|  <Title>.md (Formal Notes)        |  |  frontmatter              |
+-----------------------------------+  +---------------------------+
                                                 |
                              User sets do_ocr: true
                                                 |
                                                 v
+-----------------------------------+  +---------------------------+
|  <system_dir>/PaperForge/ocr/     |  |  fulltext.md (Markdown)   |
|  <key>/ (OCR Output)              |  |  images/ (PNG/JPEG)       |
|                                   |  |  meta.json (JSON)         |
|                                   |  |  figure-map.json (JSON)   |
+-----------------------------------+  +---------------------------+
                                                 |
                              User sets analyze: true
                              paperforge deep-reading (check queue)
                                                 |
                                                 v
+-----------------------------------+  +---------------------------+
|  /pf-deep <zotero_key>            |  |  Agent-generated Markdown |
|  (Agent Deep Reading)             |  |  inserted into Formal     |
|                                   |  |  Note ## 精读 section     |
+-----------------------------------+  +---------------------------+
```

### Stage-by-Stage Explanation

| Stage | Input | Output | Trigger | Actor |
|-------|-------|--------|---------|-------|
| **1. Export** | Zotero items | `library.json` | Automatic (BBT "Keep updated") | Better BibTeX |
| **2. Selection Sync** | `library.json` | `library-records/<key>.md` | `paperforge sync --selection` | Worker |
| **3. Index Refresh** | `library-records/*.md` | `Literature/<key> - <Title>.md` | `paperforge sync --index` | Worker |
| **4. OCR** | PDF attachments | `ocr/<key>/` directory | `paperforge ocr` | Worker |
| **5. Queue Check** | `library-records` frontmatter | Console table | `paperforge deep-reading` | Worker |
| **6. Deep Reading** | OCR output + formal note | Annotated formal note | `/pf-deep <key>` | Agent |

### State Machine (OCR)

Each literature item tracks `ocr_status` through a finite state machine:

```
       pending  <----  User sets do_ocr: true
          |
          v
    processing  <----  Worker uploads PDF to PaddleOCR
          |
    +-----+-----+
    |           |
    v           v
   done      failed
    |           |
    v           v
  Ready      User may retry
  for deep   by resetting
  reading    do_ocr: true
```

---

## Directory Structure

PaperForge Lite uses **5 core directories** under the Obsidian vault root. All paths are configurable via `paperforge.json` and resolved through the shared config resolver (see [ADR-001](#adr-001-config-precedence)).

```
{vault_root}/
|
|-- <resources_dir>/                          # User data and notes
|   |-- <literature_dir>/                     # Formal literature notes
|   |   |-- 骨科/
|   |   |   |-- ABCDEFG - Paper Title.md      # Generated by index-refresh
|   |   |-- 运动医学/
|   |   |   |-- HIJKLMN - Another Title.md
|   |   |
|   |-- <control_dir>/                        # State tracking
|   |   |-- library-records/                  # Generated by selection-sync
|   |   |   |-- 骨科/
|   |   |   |   |-- ABCDEFG.md                # User-editable control file
|   |   |   |-- 运动医学/
|   |   |   |   |-- HIJKLMN.md
|
|-- <system_dir>/                             # System-generated data
|   |-- PaperForge/
|   |   |-- exports/                          # BBT JSON export
|   |   |   |-- library.json                  # Auto-exported by Zotero
|   |   |-- ocr/                              # OCR results
|   |   |   |-- ABCDEFG/                      # One directory per Zotero key
|   |   |   |   |-- fulltext.md               # Extracted text with page markers
|   |   |   |   |-- images/                   # Auto-cut figures and tables
|   |   |   |   |-- meta.json                 # OCR status and metadata
|   |   |   |   |-- figure-map.json           # Figure index (auto-generated)
|   |   |   |   |-- chart-type-map.json       # Chart type classification
|   |   |-- worker/scripts/
|   |   |   |-- literature_pipeline.py        # Core worker script
|   |
|   |-- Zotero/                               # Junction/symlink to Zotero storage
|   |   |-- storage/                          # Actual PDF attachments
|
|-- <agent_config_dir>/                       # Agent configuration
|   |-- skills/
|   |   |-- literature-qa/                    # Deep reading skill
|   |   |   |-- scripts/
|   |   |   |   |-- ld_deep.py                # /pf-deep implementation
|   |   |   |-- prompt_deep_subagent.md       # Agent prompt template
|   |   |   |-- chart-reading/                # 14 chart type guides
|   |-- command/
|   |   |-- pf-deep.md                        # Command documentation
|   |   |-- pf-paper.md
|   |   |-- pf-ocr.md
|   |   |-- pf-sync.md
|   |   |-- pf-status.md
|
|-- paperforge.json                           # Configuration file
|-- .env                                      # API keys (not committed)
|-- AGENTS.md                                 # User guide
```

### Directory Rationale

| Directory | Purpose | Generated By | Modified By |
|-----------|---------|--------------|-------------|
| `<resources_dir>/<literature_dir>/` | Final output: formal notes with frontmatter + deep reading annotations | `sync --index` (Worker) | Agent (writes `## 精读`), User |
| `<resources_dir>/<control_dir>/library-records/` | State tracking: per-paper metadata flags (`do_ocr`, `analyze`, `ocr_status`) | `sync --selection` (Worker) | User (toggles flags), Worker (updates status) |
| `<system_dir>/PaperForge/exports/` | Better BibTeX JSON export | Zotero + BBT (external) | Read-only for PaperForge |
| `<system_dir>/PaperForge/ocr/` | OCR extraction results: text, images, metadata | `paperforge ocr` (Worker) | Read-only for Agent |
| `<system_dir>/Zotero/` | Junction or symlink to Zotero data directory | User (installation step) | Read-only for PaperForge |

The separation between `<resources_dir>/` (user-facing, should be backed up) and `<system_dir>/` (system-generated, can be rebuilt) is intentional. If a vault is lost, `<resources_dir>/` contains the valuable intellectual output; `<system_dir>/PaperForge/ocr/` and `<system_dir>/PaperForge/exports/` can be regenerated by re-running workers.

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

Agent skills (e.g., `skills/literature-qa/scripts/ld_deep.py`) reuse the same resolver logic but call `paperforge.commands` functions directly rather than going through the CLI argument parser.

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

### ADR-001: Config Precedence

**Status:** Accepted  
**Phase:** 1 (Foundation)  
**Context:** PaperForge needs to support multiple configuration sources: built-in defaults, JSON config files, environment variables, and explicit function arguments. Users need predictable override behavior.  
**Decision:** Establish a locked five-level precedence hierarchy:

1. **Explicit overrides** (function parameter)
2. **Process environment variables** (`PAPERFORGE_*`)
3. **`paperforge.json` nested `vault_config` block**
4. **`paperforge.json` top-level keys** (legacy backward-compat)
5. **Built-in defaults**

The `load_vault_config()` function in `paperforge/config.py` merges sources in this exact order. No source can accidentally override a higher-precedence source.  
**Consequences:**
- (+) Predictable behavior: users know exactly which setting wins.
- (+) Backward compatible: legacy top-level JSON keys still work.
- (+) Testable: tests can inject overrides without mutating global state.
- (-) Slightly more complex than a single config dict; requires documentation.

---

### ADR-002: Pipeline Split into Worker/Agent

**Status:** Accepted  
**Phase:** 1 (Foundation)  
**Context:** The original prototype mixed automated tasks (sync, OCR) with interactive tasks (deep reading) in a single script. This made it unclear what ran automatically vs. what required human judgment.  
**Decision:** Split the system into two layers:
- **Worker layer**: Automated, deterministic, CLI-triggered. Handles mechanical tasks.
- **Agent layer**: Interactive, reasoning-driven, user-triggered. Handles cognitive tasks.

Workers never trigger Agents, and Agents never trigger Workers. The handoff point is the `library-record` frontmatter: users set `do_ocr: true` or `analyze: true`, then run the appropriate worker or agent command.  
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
2. Per-paper `ocr_status` field in the `library-record` frontmatter

The `paperforge ocr` command scans all library-records for `do_ocr: true` and `ocr_status != done`, uploads PDFs, and updates both persistence layers. The `paperforge deep-reading` command checks `ocr_status == done` before listing a paper as "ready."  
**Consequences:**
- (+) Resilient to crashes: status is persisted, not in-memory.
- (+) Idempotent: re-running `paperforge ocr` skips already-done papers.
- (+) Observable: users can check status without re-running the worker.
- (-) Requires two-phase commit: `meta.json` and `library-record` must stay in sync.

---

### ADR-004: Base Views Config-Aware

**Status:** Accepted  
**Phase:** 3 (Base Views)  
**Context:** Obsidian Base views (`.base` files) provide a database-like UI for library-records. Hardcoded paths in Base views break when users customize their directory structure.  
**Decision:** Generate Base views from Jinja2 templates at setup time, injecting resolved paths from `paperforge_paths()`. Templates live in `paperforge/templates/bases/` and are rendered into `<base_dir>/` with user-configured directory names substituted.  
**Consequences:**
- (+) Base views work out of the box regardless of directory configuration.
- (+) Users can customize paths in `paperforge.json` without breaking views.
- (+) Template-based generation is easier to maintain than static files.
- (-) Requires template maintenance when new fields are added to library-records.

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
**Context:** Over time, three sources of truth for a paper's status can diverge: the formal note frontmatter, the library-record frontmatter, and the actual OCR output directory. Users may manually edit one without updating the others.  
**Decision:** Implement `paperforge repair` with three-way divergence detection:
1. Scan all library-records
2. Compare `ocr_status` in library-record vs. formal note vs. `meta.json`
3. Report discrepancies in a structured table
4. With `--fix`, propagate the most reliable source (OCR directory > library-record > formal note)

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

5. **Add tests** in `tests/test_mycommand.py` following the fixture-based pattern.

### Adding a New Agent Command

1. **Create command documentation** in `<agent_config_dir>/command/pf-mycmd.md` following the unified template (see `docs/COMMANDS.md`).

2. **Implement skill logic** in `<agent_config_dir>/skills/<skill-name>/scripts/`:
   - Import from `paperforge.commands` for shared logic.
   - Or call `paperforge.cli.main(["mycmd", ...])` for CLI reuse.

3. **Register with agent platform**:
   - **OpenCode:** Add to `.opencode/command/` directory.
   - **Codex:** Add to `.codex/commands/` (structure TBD — follow platform conventions).
   - **Claude Code:** Add to `.claude/commands/` (structure TBD — follow platform conventions).

### Adding Support for a New Agent Platform

The current implementation targets **OpenCode Agent** (`.opencode/skills/` and `.opencode/command/`). To add **Codex** or **Claude Code**:

1. **Analyze platform conventions**: Each platform has its own skill/command directory structure and metadata format.

2. **Create platform-specific wrappers**:
   ```python
   # paperforge/agents/codex_adapter.py
   from paperforge.commands import get_command_module
   
   def run_codex_command(name: str, vault: Path, **kwargs):
       """Adapter for Codex agent commands."""
       module = get_command_module(name)
       # Construct argparse.Namespace from Codex inputs
       args = argparse.Namespace(vault_path=vault, **kwargs)
       return module.run(args)
   ```

3. **Add platform directories** to `DEFAULT_CONFIG` in `paperforge/config.py`:
   ```python
   DEFAULT_CONFIG = {
       # ... existing keys ...
       "codex_skill_dir": ".codex/skills",
       "claude_skill_dir": ".claude/skills",
   }
   ```

4. **Update setup wizard** (`setup_wizard.py`) to generate platform-specific config and directories.

5. **Document platform differences** in `docs/COMMANDS.md` under "Platform Notes."

---

## Cross-References

- User-facing guide: [`AGENTS.md`](../AGENTS.md)
- Installation instructions: [`docs/INSTALLATION.md`](INSTALLATION.md)
- Command reference: [`docs/COMMANDS.md`](COMMANDS.md)
- Migration guide: [`docs/MIGRATION-v1.2.md`](MIGRATION-v1.2.md)
- Requirements: [`.planning/REQUIREMENTS-v1.2.md`](../.planning/REQUIREMENTS-v1.2.md)

---

*PaperForge Lite | Architecture Documentation | For Maintainers and Contributors*
