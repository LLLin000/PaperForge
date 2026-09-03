"""paperforge.cli — PaperForge command-line interface.

Exposes `paperforge paths`, `paperforge status`, `paperforge sync`,
`paperforge ocr`, `paperforge ocr --diagnose`, `paperforge deep-reading`,
`paperforge repair`, and `paperforge doctor`.

Backward-compatible aliases (deprecated): `selection-sync`, `index-refresh`,
`ocr run`, `ocr doctor`.

Loads .env from the vault root and from <system_dir>/PaperForge/.env before
dispatching to worker functions, matching the legacy pipeline behavior.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Config / resolver
from paperforge.config import (
    AGENT_PLATFORM_IDS,
    ConfigError,
    load_config,
    load_vault_config,
    paperforge_paths,
    paths_as_strings,
    resolve_paths,
    resolve_vault,
)

# Logging
from paperforge.logging_config import configure_logging

# Worker function stubs — let tests patch cli.run_* directly
run_status = None
run_selection_sync = None
run_index_refresh = None
run_deep_reading = None
run_repair = None
run_ocr = None
ensure_base_views = None

PF_LITE_DIR = Path(__file__).resolve().parent


def _find_repo_root() -> Path:
    """Find the actual PaperForge repo root by scanning upward for pipeline/.

    Handles both cases:
    - Running from repo: cli.py is at <repo>/paperforge/cli.py
    - Deployed vault:   cli.py is at <vault>/PaperForge/paperforge/cli.py
                        and the actual repo is found by looking further up.
    """
    d = PF_LITE_DIR
    for _ in range(8):
        if (d / "pipeline").exists() and (d / "paperforge").exists():
            return d
        parent = d.parent
        if parent == d:
            break
    return PF_LITE_DIR.parent


REPO_ROOT = _find_repo_root()


def _resolve_pipeline():
    """Add repo root to sys.path so 'pipeline' package resolves."""
    repo_pipeline = REPO_ROOT / "pipeline"
    if repo_pipeline.exists():
        repo_root_str = str(REPO_ROOT)
        if repo_root_str not in sys.path:
            sys.path.insert(0, repo_root_str)
    else:
        pf_worker_pipeline = PF_LITE_DIR.parent.parent / "PaperForge" / "worker" / "pipeline"
        if pf_worker_pipeline.exists():
            pf_worker_str = str(pf_worker_pipeline.parent)
            if pf_worker_str not in sys.path:
                sys.path.insert(0, pf_worker_str)


def _import_worker_functions() -> None:
    """Import worker functions into module-level globals, skipping any that are already bound.

    Called after _resolve_pipeline() has added the repo root to sys.path.
    Idempotent: once a global is bound (by this function or by a test patch), it is
    not replaced. This allows tests to patch stubs before main() is called.
    """
    global run_status, run_selection_sync, run_index_refresh
    global run_deep_reading, run_repair, run_ocr, ensure_base_views

    from paperforge.worker.base_views import ensure_base_views as _ebu
    from paperforge.worker.deep_reading import run_deep_reading as _rdr
    from paperforge.worker.ocr import run_ocr as _ro
    from paperforge.worker.repair import run_repair as _rr
    from paperforge.worker.status import run_status as _rs
    from paperforge.worker.sync import run_index_refresh as _rir
    from paperforge.worker.sync import run_selection_sync as _rss

    if run_status is None:
        run_status = _rs
    if run_selection_sync is None:
        run_selection_sync = _rss
    if run_index_refresh is None:
        run_index_refresh = _rir
    if run_deep_reading is None:
        run_deep_reading = _rdr
    if run_repair is None:
        run_repair = _rr
    if run_ocr is None:
        run_ocr = _ro
    if ensure_base_views is None:
        ensure_base_views = _ebu


# ---------------------------------------------------------------------------
# Build parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    from paperforge import __version__

    parser = argparse.ArgumentParser(
        prog="paperforge",
        description="PaperForge \u2014 Obsidian + Zotero literature pipeline CLI",
    )
    parser.add_argument("--version", action="version", version=f"paperforge {__version__}")
    parser.add_argument(
        "--vault",
        metavar="VAULT",
        help="Path to the Obsidian vault root (default: cwd or PAPERFORGE_VAULT env)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG-level diagnostic output on stderr",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bars (tqdm) for all commands",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # paths
    p_paths = sub.add_parser("paths", help="Print resolved vault paths")
    p_paths.add_argument(
        "--json",
        action="store_true",
        help="Output paths as JSON instead of human-readable text",
    )

    # status
    status_p = sub.add_parser("status", help="Run the literature pipeline status check")
    status_p.add_argument("--json", action="store_true", help="Output JSON")

    # sync (new unified command)
    p_sync = sub.add_parser("sync", help="Sync Zotero selection and refresh literature index")
    p_sync.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing",
    )
    p_sync.add_argument(
        "--domain",
        metavar="DOMAIN",
        help="Filter by domain (future feature)",
    )
    p_sync.add_argument(
        "--selection",
        action="store_true",
        help="Run selection-sync only",
    )
    p_sync.add_argument(
        "--index",
        action="store_true",
        help="Run index-refresh only",
    )
    p_sync.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Force full rebuild of the canonical asset index",
    )
    p_sync.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON (PFResult envelope)",
    )
    p_sync.add_argument("--prune", action="store_true", help="Preview orphan cleanup (dry-run)")
    p_sync.add_argument("--prune-force", action="store_true", help="Execute orphan cleanup")

    # selection-sync (backward compat)
    sub.add_parser("selection-sync", help="Sync Zotero selection to library records")

    # index-refresh (backward compat)
    sub.add_parser("index-refresh", help="Refresh formal literature notes from library records")

    # deep-reading
    p_dr = sub.add_parser("deep-reading", help="Check deep-reading queue status")
    p_dr.add_argument("--json", action="store_true", help="Output as PFResult JSON")

    # deep-finalize
    p_df = sub.add_parser("deep-finalize", help="Mark deep reading done and notify dashboard")
    p_df.add_argument("zotero_key", help="Zotero citation key")
    p_df.add_argument("--json", action="store_true", help="Output as PFResult JSON")

    # repair
    p_repair = sub.add_parser(
        "repair",
        help="Repair divergent literature notes (or the runtime with --runtime)",
    )
    p_repair.add_argument(
        "--runtime",
        action="store_true",
        help="Runtime lifecycle repair (#143) — re-ensure deps + re-publish the pointer",
    )
    p_repair.add_argument("--fix", action="store_true", help="Actually apply repairs instead of dry-run")
    p_repair.add_argument("--fix-paths", action="store_true", help="Re-resolve PDF paths for items with path_error")
    p_repair.add_argument("--json", action="store_true", help="Output result as JSON (PFResult envelope)")

    # ocr (unified)
    p_ocr = sub.add_parser("ocr", help="OCR operations")
    p_ocr.add_argument(
        "--diagnose",
        action="store_true",
        help="Diagnose OCR configuration without running",
    )
    p_ocr.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON (PFResult envelope)",
    )
    p_ocr.add_argument(
        "--key",
        metavar="KEY",
        help="Process specific Zotero key",
    )
    ocr_sub = p_ocr.add_subparsers(dest="ocr_action")
    p_ocr_versions = ocr_sub.add_parser(
        "pipeline-versions", help="Per-paper OCR pipeline versions (detail surface, #148)"
    )
    p_ocr_versions.add_argument("--json", action="store_true")
    p_ocr_status = ocr_sub.add_parser("status", help="Live provider status of active OCR jobs (no OCR loop)")
    p_ocr_status.add_argument("--json", action="store_true")
    p_ocr_status.add_argument("--batch", default=None, metavar="ID", help="Only show this batch (filter)")
    p_ocr_resume = ocr_sub.add_parser("resume", help="Re-attach an existing OCR execution (settle done / poll / retry)")
    p_ocr_resume.add_argument("--batch", required=True, metavar="ID", help="Batch id to re-attach (from ocr run / status)")
    p_ocr_resume.add_argument("--json", action="store_true")
    run_parser = ocr_sub.add_parser("run", help="Run OCR queue")
    run_parser.add_argument("keys", nargs="*", metavar="KEY", help="Paper keys to process (default: entire queue)")
    run_parser.add_argument("--keys-file", default=None, metavar="PATH",
                            help="File of paper keys (CRLF/BOM tolerated, deduped — P0-4)")
    doctor_parser = ocr_sub.add_parser("doctor", help="Diagnose OCR configuration and connectivity")
    doctor_parser.add_argument("--live", action="store_true", help="Run live PDF test (L4)")
    redo_parser = ocr_sub.add_parser("redo", help="Re-run OCR for papers marked ocr_redo: true")
    redo_parser.add_argument("--dry-run", action="store_true", help="List papers that would be reset without making changes")
    redo_parser.add_argument("keys", nargs="*", metavar="KEY",
        help="Paper keys to redo (all redoable if empty)")
    redo_parser.set_defaults(ocr_action="redo")
    list_parser = ocr_sub.add_parser("list", help="List all papers with OCR maintenance status")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    list_parser.add_argument("--output", metavar="PATH", help="Write JSON output to file")
    list_parser.add_argument("--manifest", action="store_true",
        help="Output key→sha256 manifest dict instead of full rows")
    list_parser.add_argument("--keys", nargs="*", metavar="KEY",
        help="Only output rows for these specific keys (with --json)")
    rebuild_parser = ocr_sub.add_parser("rebuild", help="Rebuild OCR-derived artifacts from existing raw blocks")
    rebuild_parser.add_argument("keys", nargs="*", metavar="KEY", help="Paper keys to rebuild")
    rebuild_parser.add_argument("--all", action="store_true", help="Rebuild all papers with existing OCR raw data")
    rebuild_parser.add_argument("--status", metavar="STATUS", help="Filter by OCR status (done, done_degraded, failed)")
    rebuild_parser.add_argument("--dry-run", action="store_true", help="List papers that would be rebuilt without executing")
    rebuild_parser.add_argument("--resume", action="store_true", help="Skip papers already in checkpoint")
    parallel_group = rebuild_parser.add_mutually_exclusive_group()
    parallel_group.add_argument("--parallel", type=int, nargs="?", const=4, default=4, metavar="N",
        help="Number of parallel workers (default: 4)")
    parallel_group.add_argument("--no-parallel", dest="parallel", action="store_const", const=0,
        help="Disable parallel processing (serial)")

    # context (Phase 26: traceable AI context packs)
    p_context = sub.add_parser("context", help="Generate traceable AI context pack for paper(s)")
    p_context.add_argument(
        "key",
        nargs="?",
        metavar="KEY",
        help="Zotero citation key for a single paper (outputs single JSON object)",
    )
    p_context.add_argument(
        "--domain",
        metavar="DOMAIN",
        help="Filter by domain (outputs JSON array)",
    )
    p_context.add_argument(
        "--collection",
        metavar="PATH",
        help="Filter by collection path (prefix match, outputs JSON array)",
    )
    p_context.add_argument(
        "--all",
        action="store_true",
        help="Output all entries in the canonical index (JSON array)",
    )

    # dashboard
    p_dash = sub.add_parser("dashboard", help="Aggregated stats and permissions for the plugin dashboard")
    p_dash.add_argument("--json", action="store_true", help="Output as PFResult JSON")

    # Vector DB
    p_embed = sub.add_parser("embed", help="Vector embedding operations")
    p_embed_sp = p_embed.add_subparsers(dest="embed_subcommand", required=True)
    p_embed_build = p_embed_sp.add_parser("build", help="Build vector index from OCR fulltext")
    p_embed_build.add_argument("--json", action="store_true")
    # P0-2: --force and --resume are mutually exclusive — a force rebuild
    # clears the candidate's vector tables, so any resume hash-skip would
    # silently drop those papers' vectors from the published DB.
    _rebuild_mode = p_embed_build.add_mutually_exclusive_group()
    _rebuild_mode.add_argument("--force", action="store_true")
    _rebuild_mode.add_argument("--resume", action="store_true", help="Skip papers already in vector index")
    p_embed_status = p_embed_sp.add_parser("status", help="Check vector DB status")
    p_embed_status.add_argument("--json", action="store_true")
    p_embed_status.add_argument(
        "--probe",
        action="store_true",
        help="Run health probe (KNN query) — slower but verifies vector DB is functional",
    )
    # #137: `embed stop` control-plane retired — no parser; cancellation is
    # the unified token (stdin PAPERFORGE_STOP / SIGINT / SIGTERM).
    p_embed_migrate = p_embed_sp.add_parser("migrate", help="Migrate vectors from ChromaDB to vec0 tables")
    p_embed_migrate.add_argument("--json", action="store_true")


    p_retrieve = sub.add_parser("retrieve", help="Semantic content retrieval across OCR fulltext")
    p_retrieve.add_argument("query", help="Search query")
    p_retrieve.add_argument("--json", action="store_true")
    p_retrieve.add_argument("--limit", type=int, default=5)
    p_retrieve.add_argument("--deep", action="store_true", help="Enable @ Deep Search mode with query rewrite + hybrid retrieval (BM25 + vec0)")
    p_retrieve.add_argument(
        "--expand", dest="expand", action="store_true", default=True, help="Enable context expansion (default: True)"
    )
    p_retrieve.add_argument("--no-expand", dest="expand", action="store_false", help="Disable context expansion")
    p_retrieve.add_argument("--paper", help="Scope retrieval to a single paper by zotero key")

    # Render-layer consistency audit (read-only V1)
    p_render = sub.add_parser("render", help="Audit rendered paper artifacts")
    p_render_sp = p_render.add_subparsers(dest="render_subcommand", required=True)
    p_render_audit = p_render_sp.add_parser("audit", help="Run read-only render consistency audit")
    p_render_audit.add_argument("keys", nargs="*", metavar="KEY", help="Paper keys (default: all OCR papers)")
    p_render_audit.add_argument("--json", action="store_true", help="Output JSON")
    p_render_reconcile = p_render_sp.add_parser("reconcile", help="Stage R/P reconciliation in isolated tmp (production write gated)")
    p_render_reconcile.add_argument("keys", nargs="*", metavar="KEY", help="Paper keys (default: all OCR papers)")
    p_render_reconcile.add_argument("--json", action="store_true", help="Output JSON")
    p_render_reconcile.add_argument("--include-pdf-media", action="store_true", help="Include PDF media validation")
    p_render_reconcile.add_argument("--apply-r", action="store_true", help="Apply verified R repairs to production (gated; currently staging-only)")
    p_render_promote = p_render_sp.add_parser(
        "promote-r",
        help="Promote verified R repair artifacts from isolated reconcile staging",
    )
    p_render_promote.add_argument("key", metavar="KEY", help="Paper key")
    p_render_promote.add_argument(
        "object_ids",
        nargs="*",
        metavar="OBJECT_ID",
        help="Canonical figure IDs (required unless --all is explicit)",
    )
    p_render_promote.add_argument(
        "--all",
        action="store_true",
        help="Explicitly promote all plans in the latest R staging",
    )
    p_render_promote.add_argument("--json", action="store_true", help="Output JSON")
    p_render_accept = p_render_sp.add_parser("accept-proposal", help="Promote a verified P proposal to canonical inventory (authority action)")
    p_render_accept.add_argument("key", metavar="KEY", help="Paper key")
    p_render_accept.add_argument("label", metavar="LABEL", help="Proposal label (e.g. 5)")
    p_render_accept.add_argument("--plan-hash", required=True, help="SHA-256 of the reviewed final-plan.json")
    p_render_accept.add_argument("--json", action="store_true", help="Output JSON")


    # prune
    p_prune = sub.add_parser("prune", help="Delete orphan paper artifacts (dry-run by default)")
    p_prune.add_argument("--force", action="store_true", help="Actually delete (default: dry-run)")
    p_prune.add_argument("--json", action="store_true", help="Output as JSON")
    p_prune.add_argument("keys", nargs="*", metavar="KEY", help="Only process these zotero keys")

    # trash (recoverable deletion — nothing is physically removed)
    p_trash = sub.add_parser("trash", help="Manage recoverable-deletion trash")
    p_trash_sp = p_trash.add_subparsers(dest="trash_subcommand", required=True)
    p_trash_list = p_trash_sp.add_parser("list", help="List trashed items")
    p_trash_restore = p_trash_sp.add_parser("restore", help="Restore a trashed item")
    p_trash_restore.add_argument("trash_id", help="Trash record id (from `paperforge trash list`)")
    p_trash_purge = p_trash_sp.add_parser("purge", help="Physically purge the trash (only trash-root paths)")
    p_trash_purge.add_argument("--older-than", type=int, default=None, metavar="DAYS",
                               help="Only purge items trashed more than DAYS ago")

    # Memory Layer commands
    p_memory = sub.add_parser("memory", help="Manage the Memory Layer")
    p_memory_sp = p_memory.add_subparsers(dest="memory_subcommand", required=True)
    p_memory_build = p_memory_sp.add_parser("build", help="Build the memory database from canonical index")
    p_memory_build.add_argument("--key", action="append", default=[], metavar="KEY",
                               help="Paper key to build (repeatable; papers scope)")
    p_memory_build.add_argument("--json", action="store_true", help="Output as JSON")
    p_memory_status = p_memory_sp.add_parser("status", help="Check memory database status")
    p_memory_status.add_argument("--json", action="store_true", help="Output as JSON")
    p_memory_restore = p_memory_sp.add_parser("restore-backup", help="Restore memory database from a verified backup")
    p_memory_restore.add_argument("--json", action="store_true", help="Output as JSON (PFResult envelope)")

    p_paper_status = sub.add_parser("paper-status", help="Look up a paper's status")
    p_paper_status.add_argument("query", help="Paper identifier (zotero_key, DOI, title, alias)")
    p_paper_status.add_argument("--json", action="store_true", help="Output as JSON")

    p_pc = sub.add_parser("paper-context", help="Get full context for a paper by zotero key, DOI, or citation key")
    p_pc.add_argument("key", help="Paper identifier (zotero key, DOI, or citation key)")
    p_pc.add_argument("--json", action="store_true", help="Output as JSON")
    p_pc.add_argument("--structure", action="store_true", help="Include compact document tree from OCR structure")

    p_read = sub.add_parser("read", help="Canonical local literal read of a paper (fulltext/PDF, no path handling)")
    p_read.add_argument("key", help="Paper identifier (zotero key, DOI, or citation key)")
    p_read.add_argument("--find", required=True, help="Literal term to search (case-insensitive substring, not regex)")
    p_read.add_argument("--source", choices=("auto", "fulltext", "pdf"), default="auto",
                        help="Source to search (default auto = fulltext + canonical PDF)")
    p_read.add_argument("--json", action="store_true", help="Output as JSON")

    p_rl = sub.add_parser("reading-log", help="Record or export reading notes")
    p_rl.add_argument("--write", dest="paper_id", help="Write note for this zotero_key")
    p_rl.add_argument("--section", help="Section (e.g. Discussion P12)")
    p_rl.add_argument("--excerpt", help="Quoted excerpt")
    p_rl.add_argument("--usage", help="How this supports the current writing")
    p_rl.add_argument("--note", help="Optional cross-validation note")
    p_rl.add_argument("--context", help="Full paragraph containing excerpt")
    p_rl.add_argument("--tags", help="Comma-separated tags")
    p_rl.add_argument("--project", help="Associated project name")
    p_rl.add_argument("--render", action="store_true", help="Render reading-log.md for one or all projects")
    p_rl.add_argument("--correct", dest="correct_id", help="ID of prior reading note to correct")
    p_rl.add_argument("--correction", help="Correction text")
    p_rl.add_argument("--reason", help="Reason for correction (e.g. 'Rechecked figure legend')")
    p_rl.add_argument("--since", help="Export notes since date (YYYY-MM-DD)")
    p_rl.add_argument("--limit", type=int, default=50, help="Max notes to export")
    p_rl.add_argument("--output", help="Write markdown to file")
    p_rl.add_argument("--validate", help="Validate a reading-log.md file")
    p_rl.add_argument("--import", dest="import_file", help="Import reading-log.md into paper_events")
    p_rl.add_argument("--lookup", help="Look up all reading notes for a paper key")
    p_rl.add_argument("--json", action="store_true", help="Output as JSON")

    p_pl = sub.add_parser("project-log", help="Record or render project work logs")
    p_pl.add_argument("--write", action="store_true", help="Write a new project log entry")
    p_pl.add_argument("--payload", help="JSON payload for the entry")
    p_pl.add_argument("--project", help="Project name (required for write/list/render)")
    p_pl.add_argument("--list", action="store_true", help="List all entries for a project")
    p_pl.add_argument("--render", action="store_true", help="Render project-log.md")
    p_qp = sub.add_parser("query-plan", help="Classify a literature query and recommend the first retrieval command")
    p_qp.add_argument("query", help="User query to classify")
    p_qp.add_argument("--intent", choices=["discover", "locate", "content", "known-paper"], required=True, help="Retrieval intent (known-paper is an alias for locate)")
    p_qp.add_argument("--json", action="store_true", help="Output as JSON")

    p_search = sub.add_parser("search", help="Metadata FTS search across indexed paper fields")
    p_search.add_argument("query", help="Search query for title/abstract/author/journal/domain/collection metadata")
    p_search.add_argument("--json", action="store_true", help="Output as JSON")
    p_search.add_argument("--limit", type=int, default=20, help="Max results")
    p_search.add_argument("--domain", help="Filter by domain")
    p_search.add_argument("--year-from", type=int, help="Filter by year (inclusive)")
    p_search.add_argument("--year-to", type=int, help="Filter by year (inclusive)")
    p_search.add_argument("--ocr", choices=["done","pending","failed","processing"], help="Filter by OCR status")
    p_search.add_argument("--deep", choices=["done","pending"], help="Filter by deep reading status")
    p_search.add_argument("--lifecycle", choices=["indexed","pdf_ready","fulltext_ready","deep_read_done"], help="Filter by lifecycle")
    p_search.add_argument("--next-step", choices=["sync","ocr","/pf-deep","ready"], help="Filter by next step")
    p_search.add_argument("--evidence", action="store_true", help="Evidence-mode: wrap results as metadata-only candidates")

    # agent-context
    p_ac = sub.add_parser("agent-context", help="Generate agent bootstrap context")
    p_ac.add_argument("--json", action="store_true", help="Output as JSON")

    # runtime-health
    p_rh = sub.add_parser("runtime-health", help="Check memory layer runtime health")
    p_rh.add_argument("--json", action="store_true", help="Output as JSON")

    # base-refresh
    p_base = sub.add_parser("base-refresh", help="Refresh Obsidian Base view files")
    p_base.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force full regeneration (bypasses incremental merge, replaces all views including user views)",
    )

    # doctor
    doctor_p = sub.add_parser("doctor", help="Validate PaperForge setup and configuration")
    doctor_p.add_argument("--json", action="store_true", help="Output JSON")

    # update
    p_update = sub.add_parser("update", help="Update PaperForge to the latest version")
    p_update.add_argument(
        "--json",
        action="store_true",
        help="Emit the #137 NDJSON machine stream with cooperative cancellation",
    )

    # setup wizard
    p_setup = sub.add_parser("setup", help="Set up PaperForge in a vault (use --headless for non-interactive)")
    p_setup.add_argument(
        "--headless",
        action="store_true",
        help="Run setup non-interactively (for AI agents or scripts)",
    )
    p_setup.add_argument(
        "--agent",
        metavar="AGENT",
        default=None,
        choices=list(AGENT_PLATFORM_IDS),
        help="AI Agent platform (default: canonical agent_platform)",
    )
    p_setup.add_argument(
        "--system-dir",
        metavar="NAME",
        help="System directory name (default: System)",
    )
    p_setup.add_argument(
        "--resources-dir",
        metavar="NAME",
        help="Resources directory name (default: Resources)",
    )
    p_setup.add_argument(
        "--literature-dir",
        metavar="NAME",
        help="Literature directory name (default: Literature)",
    )
    p_setup.add_argument(
        "--base-dir",
        metavar="NAME",
        help="Base directory name (default: Bases)",
    )
    p_setup.add_argument(
        "--zotero-data",
        metavar="PATH",
        help="Zotero data directory (auto-detect if omitted)",
    )
    p_setup.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip environment checks (for testing/CI)",
    )
    p_setup.add_argument(
        "--json",
        action="store_true",
        help="Emit the #137 NDJSON machine stream (start/phase/item_result/terminal)",
    )
    p_setup.add_argument(
        "--modular",
        action="store_true",
        help="Use modular setup components (v2.1+)",
    )

    p_skill = sub.add_parser("skill", help="Manage the PaperForge agent skill")
    p_skill_sp = p_skill.add_subparsers(dest="skill_action", required=True)
    p_skill_deploy = p_skill_sp.add_parser("deploy", help="Deploy the paperforge skill into the vault")
    p_skill_deploy.add_argument(
        "--to",
        metavar="DIR",
        default=".agents/skills",
        help="Vault-relative skill directory to deploy into (default: .agents/skills). "
        "Agents choose their harness-native dir, e.g. --to .omp/skills",
    )
    p_skill_deploy.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing paperforge skill dir (used by update)",
    )
    p_skill_deploy.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # Layer 4 gateway commands
    p_paper_lookup = sub.add_parser("paper-lookup", help="Locate a specific paper through the Layer 4 gateway")
    p_paper_lookup.add_argument("query", help="Paper identifier, title fragment, author+year, DOI, or alias")
    p_paper_lookup.add_argument("--json", action="store_true", help="Output JSON")
    p_paper_lookup.add_argument("--limit", type=int, default=5, help="Max results (default 5)")

    p_content_discovery = sub.add_parser("content-discovery", help="Discover content within vault through the Layer 4 gateway")
    p_content_discovery.add_argument("query", help="Topic, domain, or research question for content discovery")
    p_content_discovery.add_argument("--json", action="store_true", help="Output JSON")
    p_content_discovery.add_argument("--limit", type=int, default=5, help="Max results (default 5)")

    p_paper_navigation = sub.add_parser("paper-navigation", help="Navigate paper structure through the Layer 4 gateway")
    p_paper_navigation.add_argument("query", help="Paper identifier or DOI for structural navigation")
    p_paper_navigation.add_argument("--json", action="store_true", help="Output JSON")

    p_scoped_fetch = sub.add_parser("scoped-fetch", help="Fetch paper content scoped by query through the Layer 4 gateway")
    p_scoped_fetch.add_argument("query", help="Paper identifier, title, or scoped query for targeted fetch")
    p_scoped_fetch.add_argument("--json", action="store_true", help="Output JSON")
    p_scoped_fetch.add_argument("--limit", type=int, default=5, help="Max results (default 5)")

    # config (canonical configuration authority, #142)
    p_config = sub.add_parser("config", help="Canonical paperforge.json configuration (Python-owned)")
    p_config_sp = p_config.add_subparsers(dest="config_verb", required=True)
    p_config_list = p_config_sp.add_parser("list", help="List all canonical fields")
    p_config_list.add_argument("--json", action="store_true")
    p_config_get = p_config_sp.add_parser("get", help="Get one canonical field")
    p_config_get.add_argument("key", help="Field key")
    p_config_get.add_argument("--json", action="store_true")
    p_config_set = p_config_sp.add_parser("set", help="Atomically set one canonical field")
    p_config_set.add_argument("key", help="Field key")
    p_config_set.add_argument("value", help="Field value (validated by the field spec)")
    p_config_set.add_argument("--json", action="store_true")
    p_config_unset = p_config_sp.add_parser("unset", help="Atomically remove a stored field")
    p_config_unset.add_argument("key", help="Field key")
    p_config_unset.add_argument("--json", action="store_true")
    p_config_validate = p_config_sp.add_parser("validate", help="Classify configuration state")
    p_config_validate.add_argument("--json", action="store_true")
    p_config_paths = p_config_sp.add_parser("paths", help="Resolved path inventory")
    p_config_paths.add_argument("--json", action="store_true")
    p_config_init = p_config_sp.add_parser("init", help="Create canonical config from defaults (idempotent)")
    p_config_init.add_argument("--json", action="store_true")
    p_config_migrate = p_config_sp.add_parser("migrate", help="Explicit legacy migration")
    p_config_migrate.add_argument("--dry-run", action="store_true", help="Preview without writing")
    p_config_migrate.add_argument("--json", action="store_true")

    # probe
    # ── reconcile (#166 / T5) ──
    p_reconcile = sub.add_parser("reconcile", help="Deficit read model — pure derivation + next_actions channel (#159)")
    p_reconcile.add_argument("--scope", choices=["all", "papers"], default="all", help="Observe scope (papers needs --key)")
    p_reconcile.add_argument("--key", action="append", default=[], metavar="KEY", help="Paper key (repeatable)")
    p_reconcile.add_argument("--json", action="store_true", help="Output as JSON")

    # ── action family (#163 / T2) ──
    p_action = sub.add_parser("action", help="Declarative action registry + runner (#145)")
    action_sub = p_action.add_subparsers(dest="action_verb", required=True)
    p_action_list = action_sub.add_parser("list", help="List registered actions")
    p_action_list.add_argument("--json", action="store_true", help="Output as JSON")
    p_action_describe = action_sub.add_parser("describe", help="Current descriptor for one action (includes preflight)")
    p_action_describe.add_argument("action_id", help="Registered action id")
    p_action_describe.add_argument("--json", action="store_true", help="Output as JSON")
    p_action_run = action_sub.add_parser("run", help="Run one action (preflight + confirmation gate + handler)")
    p_action_run.add_argument("action_id", help="Registered action id")
    p_action_run.add_argument("--scope", choices=["all", "papers"], default="all", help="Request scope kind (papers needs --key)")
    p_action_run.add_argument("--key", action="append", default=[], metavar="KEY", help="Paper key (papers scope; repeatable)")
    p_action_run.add_argument("--keys-file", default=None, metavar="PATH",
                              help="File of paper keys (one per line / whitespace / comma separated; CRLF and BOM tolerated — P0-4)")
    p_action_run.add_argument("--confirm", default=None, help="Exact action id to confirm (confirmation-required actions)")
    # T2 shipped --follow none; T6 (#167) adds auto: automatic-local
    # descendants run inline, remote/destructive stay pending.
    p_action_run.add_argument("--follow", choices=["none", "auto"], default="none",
                              help="Follow-up mode: auto runs automatic-local descendants inline")
    p_action_run.add_argument("--json", action="store_true", help="Output as JSON")
    p_action_preflight = action_sub.add_parser(
        "preflight", help="Observe availability + per-paper applicability WITHOUT executing (M2-C)"
    )
    p_action_preflight.add_argument("action_id", help="Registered action id")
    p_action_preflight.add_argument("--scope", choices=["all", "papers"], default="all",
                                    help="Request scope kind (papers needs --key)")
    p_action_preflight.add_argument("--key", action="append", default=[], metavar="KEY",
                                    help="Paper key (papers scope; repeatable)")
    p_action_preflight.add_argument("--keys-file", default=None, metavar="PATH",
                                    help="File of paper keys (CRLF/BOM tolerated, deduped)")
    p_action_preflight.add_argument("--json", action="store_true", help="Output as JSON")

    # ── auth family (#173 / C1) ──
    p_auth = sub.add_parser("auth", help="Credential authority (keyring + canonical env)")
    auth_sub = p_auth.add_subparsers(dest="auth_verb", required=True)
    p_auth_status = auth_sub.add_parser("status", help="Report credential availability/source")
    p_auth_status.add_argument("kind", nargs="?", choices=["ocr", "embedding"], help="Check one kind (default: vault profiles)")
    p_auth_status.add_argument("--profile", default=None, help="Profile id (default)")
    p_auth_status.add_argument("--json", action="store_true", help="Output as JSON")
    p_auth_set = auth_sub.add_parser("set", help="Store a secret in the keyring (never argv)")
    p_auth_set.add_argument("kind", choices=["ocr", "embedding"])
    p_auth_set.add_argument("--profile", default=None, help="Profile id (default)")
    p_auth_set.add_argument("--stdin", action="store_true", help="Read the secret from stdin (non-TTY)")
    p_auth_set.add_argument("--replace", action="store_true", help="Replace an existing different value")
    p_auth_set.add_argument("--json", action="store_true", help="Output as JSON")
    p_auth_delete = auth_sub.add_parser("delete", help="Delete the keyring entry")
    p_auth_delete.add_argument("kind", choices=["ocr", "embedding"])
    p_auth_delete.add_argument("--profile", default=None, help="Profile id (default)")
    p_auth_delete.add_argument("--yes", action="store_true", help="Confirm deletion (noninteractive)")
    p_auth_delete.add_argument("--json", action="store_true", help="Output as JSON")
    p_auth_migrate = auth_sub.add_parser("migrate", help="Migrate legacy credentials once (never a runtime fallback)")
    p_auth_migrate.add_argument("--from", dest="source", required=True,
                                choices=["dotenv", "environment", "windows-registry"],
                                help="Legacy source to read")
    p_auth_migrate.add_argument("--dry-run", action="store_true", help="Discover only; never store or scrub")
    p_auth_migrate.add_argument("--replace", action="store_true", help="Replace different existing values")
    p_auth_migrate.add_argument("--kind", choices=["ocr", "embedding"], default=None,
                                help="Force target kind for all discovered entries")
    p_auth_migrate.add_argument("--profile", default=None, help="Target profile (default)")
    p_auth_migrate.add_argument("--json", action="store_true", help="Output as JSON")

    p_probe = sub.add_parser("probe", help="Probe a module's capability state")
    p_probe.add_argument(
        "probe_module",
        choices=["installation", "help", "library", "ocr", "memory", "maintenance", "lineage", "all"],
        help="Module to probe (installation, library, ocr, memory, help, maintenance, or all)",
    )
    p_probe.add_argument(
        "--json",
        action="store_true",
        help="Output as schema-v1 capability envelope JSON",
    )
    p_probe.add_argument(
        "--last-operation-exit-code",
        type=int,
        default=None,
        metavar="CODE",
        help="Last operation exit code for library sync failure probe",
    )
    p_probe.add_argument(
        "--expected-version",
        help="Expected PaperForge package version; installation probe reports a mismatch",
    )

    return parser


# ---------------------------------------------------------------------------
# OCR doctor command (kept for backward compat / test patching)
# ---------------------------------------------------------------------------
def _cmd_ocr_doctor(vault: Path, args: argparse.Namespace) -> int:
    """Handle `paperforge ocr doctor` and `paperforge ocr doctor --live`."""
    from paperforge.ocr_diagnostics import ocr_doctor

    result = ocr_doctor(config=None, live=args.live)
    level = result.get("level", 0)
    passed = result.get("passed", False)

    print(f"OCR Doctor — Level {level} diagnostic")
    print("-" * 40)
    if passed:
        print(f"[PASS] {result.get('message', 'All checks passed')}")
        return 0
    else:
        print(f"[FAIL] Level {level}: {result.get('error', 'Unknown failure')}")
        print(f"[FIX]  {result.get('fix', 'No fix suggestion available')}")
        if result.get("raw_response"):
            print(f"[RAW]  {result['raw_response'][:200]}...")
        return 1


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns integer exit code (0 = success)."""
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    # Resolve/import worker modules only for commands that actually need them.
    lightweight_commands = {
        "paths", "sync", "ocr", "status", "deep-reading", "deep-finalize",
        "context", "repair", "dashboard", "memory", "embed", "retrieve",
        "query-plan", "prune", "paper-status", "paper-context", "reading-log",
        "project-log", "search", "agent-context", "runtime-health", "doctor",
        "update", "setup", "selection-sync", "index-refresh", "base-refresh",
        "read",
        "paper-lookup", "content-discovery", "paper-navigation", "scoped-fetch",
        "probe",
    }
    if args.command in lightweight_commands:
        _resolve_pipeline()
    worker_import_commands = {"status", "deep-reading", "ocr", "selection-sync", "index-refresh", "base-refresh"}
    if args.command in worker_import_commands:
        _import_worker_functions()

    # Resolve vault
    try:
        vault = resolve_vault(cli_vault=args.vault)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    args.vault_path = vault

    # Fail-closed config loading: domain commands never operate on guessed
    # paths.  config/setup/probe handle their own missing-config states.
    config_tolerant_commands = frozenset({"config", "setup", "probe", "auth", "action", "skill"})
    try:
        snapshot = load_config(vault)
        args.cfg = {key: str(cv.value).lower() if isinstance(cv.value, bool) else str(cv.value)
                    for key, cv in snapshot.values.items()}
        args.paths = resolve_paths(vault, snapshot)
    except ConfigError as exc:
        if args.command in config_tolerant_commands:
            args.cfg = None
            args.paths = None
        else:
            from paperforge.core.errors import ErrorCode as _EC
            from paperforge.core.result import PFError as _PFE
            from paperforge.core.result import PFResult as _PFR

            message = exc.code
            suggestions = []
            if exc.code == "config.not_found":
                suggestions.append("run 'paperforge config init' or 'paperforge setup'")
            if exc.code == "config.migration_required":
                suggestions.append("run 'paperforge config migrate --dry-run' to preview")
            result = _PFR(
                ok=False,
                command=args.command,
                version=__import__("paperforge", fromlist=["__version__"]).__version__,
                error=_PFE(
                    code=_EC.VALIDATION_ERROR,
                    message=message,
                    details={"config_code": exc.code, **dict(exc.details)},
                    suggestions=suggestions,
                ),
            )
            # #137: stdout carries MACHINE output only - a JSON-mode caller
            # must receive the structured PFResult on stdout, never stderr.
            if getattr(args, "json", False):
                print(result.to_json())
            else:
                print(message, file=sys.stderr)
            return 1

    # Configure logging before command dispatch
    configure_logging(verbose=getattr(args, "verbose", False))

    # -----------------------------------------------------------------------
    # Command dispatch
    # -----------------------------------------------------------------------
    if args.command == "paths":
        return _cmd_paths(vault, args)

    if args.command == "config":
        from paperforge.commands.config import run as run_config

        return run_config(args)

    # New unified commands
    if args.command == "sync":
        from paperforge.commands import sync

        return sync.run(args)

    # OCR — handle both new unified and old subcommand styles
    if args.command == "ocr":
        ocr_action = getattr(args, "ocr_action", None)
        if ocr_action == "doctor":
            # Backward compat: old ocr doctor subcommand
            return _cmd_ocr_doctor(vault, args)
        # New unified ocr (or ocr run)
        from paperforge.commands import ocr

        return ocr.run(args)

    # Backward compat: old selection-sync and index-refresh
    if args.command == "selection-sync":
        from paperforge.commands import sync

        args.selection = True
        args.index = False
        return sync.run(args)

    if args.command == "index-refresh":
        from paperforge.commands import sync

        args.selection = False
        args.index = True
        return sync.run(args)

    # Other commands delegate to their modules
    if args.command == "status":
        from paperforge.commands import status

        return status.run(args)

    if args.command == "deep-reading":
        from paperforge.commands import deep

        return deep.run(args)

    if args.command == "deep-finalize":
        from paperforge.commands import finalize

        return finalize.run(args)

    if args.command == "context":
        from paperforge.commands import context

        return context.run(args)

    if args.command == "repair":
        if getattr(args, "runtime", False):
            # #174 / #143: runtime lifecycle repair is a DIFFERENT
            # operation from literature repair.  NDJSON + cancel when
            # --json is set; otherwise human result.
            from paperforge.worker.runtime_repair import perform_runtime_repair

            result = perform_runtime_repair(ndjson=getattr(args, "json", False))
            if result.get("cancelled"):
                return 130
            return 0 if result["ok"] else 1
        from paperforge.commands import repair

        return repair.run(args)

    if args.command == "dashboard":
        from paperforge.commands import dashboard

        return dashboard.run(args)

    if args.command == "memory":
        from paperforge.commands.memory import run

        return run(args)

    if args.command == "embed":
        from paperforge.commands.embed import run

        return run(args)

    if args.command == "render":
        from paperforge.commands.render import run

        return run(args)

    if args.command == "retrieve":
        from paperforge.commands.retrieve import run

        return run(args)

    if args.command == "query-plan":
        from paperforge.commands.query_plan import run

        return run(args)

    if args.command == "prune":
        from paperforge.commands.prune import run

        return run(args)

    if args.command == "trash":
        from paperforge.commands.trash import run

        return run(args)

    if args.command == "paper-status":
        from paperforge.commands.paper_status import run

        return run(args)

    if args.command == "paper-context":
        from paperforge.commands.paper_context import run

        return run(args)

    if args.command == "read":
        from paperforge.commands.read import run

        return run(args)

    if args.command == "skill":
        return _run_skill(args)

    if args.command == "paper-lookup":
        from paperforge.commands import paper_lookup

        return paper_lookup.run(args)

    if args.command == "content-discovery":
        from paperforge.commands import content_discovery

        return content_discovery.run(args)

    if args.command == "paper-navigation":
        from paperforge.commands import paper_navigation

        return paper_navigation.run(args)

    if args.command == "scoped-fetch":
        from paperforge.commands import scoped_fetch

        return scoped_fetch.run(args)

    if args.command == "reading-log":
        from paperforge.commands.reading_log import run

        return run(args)

    if args.command == "project-log":
        from paperforge.commands.project_log import run

        return run(args)

    if args.command == "search":
        from paperforge.commands.search import run

        return run(args)

    if args.command == "agent-context":
        from paperforge.commands.agent_context import run

        return run(args)

    if args.command == "runtime-health":
        from paperforge.commands.runtime_health import run

        return run(args)

    if args.command == "auth":
        from paperforge.commands.auth import run as run_auth

        return run_auth(args)

    if args.command == "action":
        from paperforge.commands.action import run as run_action

        return run_action(args)

    if args.command == "reconcile":
        from paperforge.commands.reconcile import run as run_reconcile

        return run_reconcile(args)

    if args.command == "base-refresh":
        force = getattr(args, "force", False)
        paths = args.paths
        logger = __import__("logging").getLogger("paperforge")
        logger.info(f"Refreshing Base views in {paths['bases']}")
        ensure_base_views(vault, paths, args.cfg, force=force)
        logger.info("Base refresh complete")
        return 0

    if args.command == "doctor":
        from paperforge.worker.status import run_doctor

        kw = {}
        if getattr(args, "verbose", False):
            kw["verbose"] = True
        if getattr(args, "json", False):
            kw["json_output"] = True
        return run_doctor(vault, **kw)

    if args.command == "update":
        from paperforge.worker.update import run_update

        if getattr(args, "json", False):
            # #174 P0-4: perform_update emits the full #137 stream
            # (start/phase/exactly-one terminal); the CLI maps rc only.
            from paperforge.worker.update import perform_update

            result = perform_update(vault, ndjson=True)
            if result.get("cancelled"):
                return 130
            return 0 if result["ok"] else 1

        return run_update(vault)

    if args.command == "setup":
        # Shared config builder: only EXPLICIT CLI args are written.  An
        # omitted flag stays None -> existing config keeps its value; a
        # fresh vault gets defaults from the canonical FIELD_SPECS (via
        # bootstrap_config).  Never fill defaults here (unspecified !=
        # default) — rerun must not clobber a custom layout.
        _cfg: dict = {}
        for _key in (
            "system_dir", "resources_dir", "literature_dir", "base_dir",
            "control_dir", "skill_dir", "command_dir",
        ):
            _val = getattr(args, _key, None)
            if _val is not None:
                _cfg[_key] = _val
        _zotero = getattr(args, "zotero_data", None)
        if _zotero is not None:
            # Persist the external locator in canonical config so probe and
            # library checks see it (junction alone is not authority).
            _cfg["zotero_data_dir"] = _zotero
        _agent = getattr(args, "agent", None)
        if _agent is not None:
            # Explicit --agent: record the platform identity in canonical
            # config.  Skill TARGET is NOT routed per platform anymore —
            # the agent deploys the skill itself with `paperforge skill
            # deploy --to <dir>` (it knows its harness); setup uses the
            # shared default only.
            _cfg["agent_platform"] = _agent
        _skip = getattr(args, "skip_checks", False)

        if getattr(args, "headless", False):
            print("DEPRECATED: paperforge setup --headless; use --modular instead.", file=sys.stderr)
        elif not getattr(args, "modular", False):
            print("DEPRECATED: bare 'paperforge setup'; use 'paperforge setup --modular' instead.", file=sys.stderr)

        from paperforge.setup.plan import SetupPlan

        plan = SetupPlan(
            vault=vault,
            config=_cfg,
            zotero_path=_zotero,
            agent_type=_agent,
            skip_checks=_skip,
        )
        return plan.execute(
            json_output=getattr(args, "json_output", False),
            ndjson=getattr(args, "json", False),
        )

    if args.command == "probe":
        from paperforge.commands.probe import run as run_probe

        return run_probe(args)

    print(f"Error: unknown command {args.command}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# paths command
# ---------------------------------------------------------------------------
def _run_skill(args: argparse.Namespace) -> int:
    """Handle `paperforge skill deploy [--to DIR]`."""
    vault = args.vault_path
    if getattr(args, "skill_action", None) != "deploy":
        print(f"Error: unknown skill action {getattr(args, 'skill_action', None)}", file=sys.stderr)
        return 2
    from paperforge.services.skill_deploy import deploy_skills

    result = deploy_skills(
        vault,
        overwrite=getattr(args, "overwrite", False),
        target_dir=getattr(args, "to", None),
    )
    if getattr(args, "json", False):
        print(json.dumps({"ok": not result["errors"], **result}, ensure_ascii=False))
    else:
        status = "ok" if not result["errors"] else "failed"
        print(f"skill deploy: {status} -> {vault / result['target_dir'] / 'paperforge'}")
        for err in result["errors"]:
            print(f"  error: {err}", file=sys.stderr)
    return 0 if not result["errors"] else 1


def _cmd_paths(vault: Path, args: argparse.Namespace) -> int:
    """Handle `paperforge paths` and `paperforge paths --json`."""
    cfg = load_vault_config(vault)
    paths = paperforge_paths(vault, cfg)
    all_paths = paths_as_strings(paths)

    if args.json:
        # Output only the keys required by D-Path Output contract
        output_keys = {"vault", "worker_script", "pf_deep_script"}
        filtered = {k: v for k, v in all_paths.items() if k in output_keys}
        filtered["vault"] = str(vault.resolve())
        filtered["worker_script"] = str(paths["worker_script"].resolve())
        filtered["pf_deep_script"] = str(paths["pf_deep_script"].resolve())
        filtered["ld_deep_script"] = filtered["pf_deep_script"]
        print(json.dumps(filtered, ensure_ascii=False, indent=2))
    else:
        for key, path_str in sorted(all_paths.items()):
            print(f"{key}: {path_str}")
    return 0
