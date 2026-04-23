"""paperforge_lite.cli — PaperForge Lite command-line interface.

Exposes `paperforge paths`, `paperforge status`, `paperforge selection-sync`,
`paperforge index-refresh`, `paperforge ocr run`, and `paperforge deep-reading`.

Loads .env from the vault root and from <system_dir>/PaperForge/.env before
dispatching to worker functions, matching the legacy pipeline behavior.
"""

from __future__ import annotations

import argparse
import json
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

# Worker functions — imported at module level so tests can patch them
from pipeline.worker.scripts.literature_pipeline import (
    run_status,
    run_selection_sync,
    run_index_refresh,
    run_deep_reading,
    run_ocr,
)


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
    sub.add_parser("deep-reading", help="Check deep-reading queue status")

    # ocr (parent with nested run)
    p_ocr = sub.add_parser("ocr", help="Run OCR on PDFs requiring processing")
    p_ocr.add_argument(
        "action",
        nargs="?",
        default="run",
        choices=["run"],
        help="OCR action (default: run)",
    )

    return parser


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

    # Dispatch
    if args.command == "paths":
        return _cmd_paths(vault, args)

    dispatch_map = {
        "status": run_status,
        "selection-sync": run_selection_sync,
        "index-refresh": run_index_refresh,
        "deep-reading": run_deep_reading,
        "ocr": run_ocr,
    }

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
