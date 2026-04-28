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
    load_simple_env,
    load_vault_config,
    paperforge_paths,
    paths_as_strings,
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
    parser = argparse.ArgumentParser(
        prog="paperforge",
        description="PaperForge — Obsidian + Zotero literature pipeline CLI",
    )
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
    status_p.add_argument("--json", action="store_true", dest="json_output", help="Output JSON")

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

    # selection-sync (backward compat)
    sub.add_parser("selection-sync", help="Sync Zotero selection to library records")

    # index-refresh (backward compat)
    sub.add_parser("index-refresh", help="Refresh formal literature notes from library records")

    # deep-reading
    sub.add_parser("deep-reading", help="Check deep-reading queue status")

    # repair
    p_repair = sub.add_parser("repair", help="Repair divergent literature notes")
    p_repair.add_argument("--fix", action="store_true", help="Actually apply repairs instead of dry-run")
    p_repair.add_argument("--fix-paths", action="store_true", help="Re-resolve PDF paths for items with path_error")

    # ocr (unified)
    p_ocr = sub.add_parser("ocr", help="OCR operations")
    p_ocr.add_argument(
        "--diagnose",
        action="store_true",
        help="Diagnose OCR configuration without running",
    )
    p_ocr.add_argument(
        "--key",
        metavar="KEY",
        help="Process specific Zotero key",
    )
    ocr_sub = p_ocr.add_subparsers(dest="ocr_action")
    ocr_sub.add_parser("run", help="Run OCR queue")
    doctor_parser = ocr_sub.add_parser("doctor", help="Diagnose OCR configuration and connectivity")
    doctor_parser.add_argument("--live", action="store_true", help="Run live PDF test (L4)")

    # base-refresh
    p_base = sub.add_parser("base-refresh", help="Refresh Obsidian Base view files")
    p_base.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force full regeneration (bypasses incremental merge, replaces all views including user views)",
    )

    # doctor
    sub.add_parser("doctor", help="Validate PaperForge setup and configuration")

    # update
    sub.add_parser("update", help="Update PaperForge to the latest version")

    # setup wizard
    p_setup = sub.add_parser("setup", help="Run the setup wizard (Textual-based)")
    p_setup.add_argument(
        "--headless",
        action="store_true",
        help="Run setup non-interactively (for AI agents or scripts)",
    )
    p_setup.add_argument(
        "--agent",
        metavar="AGENT",
        default="opencode",
        choices=["opencode", "cursor", "claude", "windsurf", "github_copilot", "cline", "augment", "trae"],
        help="AI Agent platform (default: opencode)",
    )
    p_setup.add_argument(
        "--paddleocr-key",
        metavar="KEY",
        help="PaddleOCR API Key",
    )
    p_setup.add_argument(
        "--paddleocr-url",
        metavar="URL",
        default="https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
        help="PaddleOCR API URL",
    )
    p_setup.add_argument(
        "--system-dir",
        metavar="NAME",
        help="System directory name (default: 99_System)",
    )
    p_setup.add_argument(
        "--resources-dir",
        metavar="NAME",
        help="Resources directory name (default: 03_Resources)",
    )
    p_setup.add_argument(
        "--literature-dir",
        metavar="NAME",
        help="Literature directory name (default: Literature)",
    )
    p_setup.add_argument(
        "--control-dir",
        metavar="NAME",
        help="Control directory name (default: LiteratureControl)",
    )
    p_setup.add_argument(
        "--base-dir",
        metavar="NAME",
        help="Base directory name (default: 05_Bases)",
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

    _resolve_pipeline()
    _import_worker_functions()

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    # Resolve vault
    try:
        vault = resolve_vault(cli_vault=args.vault)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Load .env files exactly as legacy pipeline does
    load_simple_env(vault / ".env")
    cfg = load_vault_config(vault)
    pf_env = vault / cfg["system_dir"] / "PaperForge" / ".env"
    load_simple_env(pf_env)

    # Attach resolved values to args for command modules
    args.vault_path = vault
    args.cfg = cfg
    args.paths = paperforge_paths(vault, cfg)

    # Configure logging before command dispatch
    configure_logging(verbose=getattr(args, "verbose", False))

    # -----------------------------------------------------------------------
    # Command dispatch
    # -----------------------------------------------------------------------
    if args.command == "paths":
        return _cmd_paths(vault, args)

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

    if args.command == "repair":
        from paperforge.commands import repair

        return repair.run(args)

    if args.command == "base-refresh":
        force = getattr(args, "force", False)
        paths = args.paths
        logger = __import__("logging").getLogger("paperforge")
        logger.info(f"Refreshing Base views in {paths['bases']}")
        ensure_base_views(vault, paths, cfg, force=force)
        logger.info("Base refresh complete")
        return 0

    if args.command == "doctor":
        from paperforge.worker.status import run_doctor

        return run_doctor(vault)

    if args.command == "update":
        from paperforge.worker.update import run_update

        return run_update(vault)

    if args.command == "setup":
        if getattr(args, "headless", False):
            from paperforge.setup_wizard import headless_setup

            return headless_setup(
                vault=vault,
                agent_key=args.agent,
                paddleocr_key=getattr(args, "paddleocr_key", None),
                paddleocr_url=getattr(args, "paddleocr_url",
                    "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"),
                system_dir=getattr(args, "system_dir", None) or "99_System",
                resources_dir=getattr(args, "resources_dir", None) or "03_Resources",
                literature_dir=getattr(args, "literature_dir", None) or "Literature",
                control_dir=getattr(args, "control_dir", None) or "LiteratureControl",
                base_dir=getattr(args, "base_dir", None) or "05_Bases",
                zotero_data=getattr(args, "zotero_data", None),
                skip_checks=getattr(args, "skip_checks", False),
            )
        else:
            from paperforge.setup_wizard import main as run_setup

            return run_setup(sys.argv[2:])

    print(f"Error: unknown command {args.command}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# paths command
# ---------------------------------------------------------------------------
def _cmd_paths(vault: Path, args: argparse.Namespace) -> int:
    """Handle `paperforge paths` and `paperforge paths --json`."""
    cfg = load_vault_config(vault)
    paths = paperforge_paths(vault, cfg)
    all_paths = paths_as_strings(paths)

    if args.json:
        # Output only the keys required by D-Path Output contract
        output_keys = {"vault", "worker_script", "ld_deep_script"}
        filtered = {k: v for k, v in all_paths.items() if k in output_keys}
        filtered["vault"] = str(vault.resolve())
        filtered["worker_script"] = str(paths["worker_script"].resolve())
        filtered["ld_deep_script"] = str(paths["ld_deep_script"].resolve())
        print(json.dumps(filtered, ensure_ascii=False, indent=2))
    else:
        for key, path_str in sorted(all_paths.items()):
            print(f"{key}: {path_str}")
    return 0
