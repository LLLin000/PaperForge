"""paperforge_lite.cli — PaperForge Lite command-line interface.

Exposes `paperforge paths`, `paperforge status`, `paperforge selection-sync`,
`paperforge index-refresh`, `paperforge ocr run`, `paperforge ocr doctor`,
and `paperforge deep-reading`.

Loads .env from the vault root and from <system_dir>/PaperForge/.env before
dispatching to worker functions, matching the legacy pipeline behavior.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Config / resolver
from paperforge_lite.config import (
    load_simple_env,
    load_vault_config,
    resolve_vault,
    paperforge_paths,
    paths_as_strings,
)

# Worker functions — imported via deferred approach so the repo root
# can be resolved relative to this file's location at call time (not import
# time), avoiding ModuleNotFoundError when paperforge.exe is invoked from
# the vault directory via an editable install.
PF_LITE_DIR = Path(__file__).resolve().parent


def _find_repo_root() -> Path:
    """Find the actual PaperForge repo root by scanning upward for pipeline/.

    Handles both cases:
    - Running from repo: cli.py is at <repo>/paperforge_lite/cli.py
    - Deployed vault:   cli.py is at <vault>/PaperForge/paperforge_lite/cli.py
                        and the actual repo is found by looking further up.
    """
    d = PF_LITE_DIR
    for _ in range(8):
        if (d / "pipeline").exists() and (d / "paperforge_lite").exists():
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


# Worker function stubs — let tests patch cli.run_* directly
run_status = None
run_selection_sync = None
run_index_refresh = None
run_deep_reading = None
run_repair = None
run_ocr = None
ensure_base_views = None

# ---------------------------------------------------------------------------
# Build parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paperforge",
        description="PaperForge Lite — Obsidian + Zotero literature pipeline CLI",
    )
    parser.add_argument(
        "--vault",
        metavar="VAULT",
        help="Path to the Obsidian vault root (default: cwd or PAPERFORGE_VAULT env)",
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
    sub.add_parser("status", help="Run the literature pipeline status check")

    # selection-sync
    sub.add_parser("selection-sync", help="Sync Zotero selection to library records")

    # index-refresh
    sub.add_parser("index-refresh", help="Refresh formal literature notes from library records")

    # deep-reading
    p_dr = sub.add_parser("deep-reading", help="Check deep-reading queue status")
    p_dr.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show fix instructions for blocked papers"
    )

    # repair
    p_repair = sub.add_parser("repair", help="Repair divergent literature notes")
    p_repair.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed divergence report"
    )
    p_repair.add_argument(
        "--fix", action="store_true",
        help="Actually apply repairs instead of dry-run"
    )

    # ocr subcommands
    p_ocr = sub.add_parser("ocr", help="OCR operations")
    ocr_sub = p_ocr.add_subparsers(dest="ocr_action")
    ocr_sub.add_parser("run", help="Run OCR queue")
    doctor_parser = ocr_sub.add_parser("doctor", help="Diagnose OCR configuration and connectivity")
    doctor_parser.add_argument("--live", action="store_true", help="Run live PDF test (L4)")

    # base-refresh
    p_base = sub.add_parser("base-refresh", help="Refresh Obsidian Base view files")
    p_base.add_argument(
        "--force", "-f", action="store_true",
        help="Force full regeneration (bypasses incremental merge, replaces all views including user views)"
    )

    # doctor
    sub.add_parser("doctor", help="Validate PaperForge Lite setup and configuration")

    return parser


# ---------------------------------------------------------------------------
# OCR doctor command
# ---------------------------------------------------------------------------
def _cmd_ocr_doctor(vault: Path, args: argparse.Namespace) -> int:
    """Handle `paperforge ocr doctor` and `paperforge ocr doctor --live`."""
    from paperforge_lite.ocr_diagnostics import ocr_doctor

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


def _import_worker_functions() -> None:
    """Import worker functions into module-level globals, skipping any that are already bound.

    Called after _resolve_pipeline() has added the repo root to sys.path.
    Idempotent: once a global is bound (by this function or by a test patch), it is
    not replaced. This allows tests to patch stubs before main() is called.
    """
    global run_status, run_selection_sync, run_index_refresh
    global run_deep_reading, run_repair, run_ocr, ensure_base_views

    from pipeline.worker.scripts.literature_pipeline import (
        run_status as _rs,
        run_selection_sync as _rss,
        run_index_refresh as _rir,
        run_deep_reading as _rdr,
        run_repair as _rr,
        run_ocr as _ro,
        ensure_base_views as _ebu,
    )

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

    if args.command == "paths":
        return _cmd_paths(vault, args)

    if args.command == "ocr":
        ocr_action = getattr(args, "ocr_action", None) or "run"
        if ocr_action == "run":
            return run_ocr(vault)
        elif ocr_action == "doctor":
            return _cmd_ocr_doctor(vault, args)
        else:
            print(f"Error: unknown ocr action {ocr_action}", file=sys.stderr)
            return 1

    if args.command == "base-refresh":
        force = getattr(args, "force", False)
        paths = paperforge_paths(vault, cfg)
        logger = __import__("logging").getLogger("paperforge")
        logger.info(f"Refreshing Base views in {paths['bases']}")
        ensure_base_views(vault, paths, cfg, force=force)
        logger.info("Base refresh complete")
        return 0

    # Lazy-load dispatch targets after _resolve_pipeline() has adjusted sys.path
    _import_worker_functions()

    dispatch_map = {
        "status": run_status,
        "selection-sync": run_selection_sync,
        "index-refresh": run_index_refresh,
    }

    if args.command == "deep-reading":
        return run_deep_reading(vault, verbose=getattr(args, "verbose", False))

    if args.command == "repair":
        cfg = load_vault_config(vault)
        paths = paperforge_paths(vault, cfg)
        return run_repair(
            vault,
            paths,
            verbose=getattr(args, "verbose", False),
            fix=getattr(args, "fix", False),
        )

    if args.command == "doctor":
        from pipeline.worker.scripts.literature_pipeline import run_doctor
        return run_doctor(vault)

    worker_fn = dispatch_map.get(args.command)
    if worker_fn is None:
        print(f"Error: unknown command {args.command}", file=sys.stderr)
        return 1

    return worker_fn(vault)


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
