"""Sync command — unifies selection-sync and index-refresh."""

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_run_selection_sync():
    """Get run_selection_sync, preferring cli patches if available."""
    try:
        from paperforge.cli import run_selection_sync

        if run_selection_sync is not None:
            return run_selection_sync
    except Exception:
        pass

    import sys

    repo_root = Path(__file__).resolve().parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from paperforge.worker.sync import run_selection_sync

    return run_selection_sync


def _get_run_index_refresh():
    """Get run_index_refresh, preferring cli patches if available."""
    try:
        from paperforge.cli import run_index_refresh

        if run_index_refresh is not None:
            return run_index_refresh
    except Exception:
        pass

    import sys

    repo_root = Path(__file__).resolve().parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from paperforge.worker.sync import run_index_refresh

    return run_index_refresh


def run(args: argparse.Namespace) -> int:
    """Run sync command.

    By default runs both selection-sync and index-refresh.
    Use --selection or --index to run only one phase.
    """
    vault = getattr(args, "vault_path", None)
    if vault is None:
        from paperforge.config import resolve_vault

        vault = resolve_vault(cli_vault=getattr(args, "vault", None))

    dry_run = getattr(args, "dry_run", False)
    selection_only = getattr(args, "selection", False)
    index_only = getattr(args, "index", False)
    domain = getattr(args, "domain", None)

    if dry_run:
        print("[DRY-RUN] Would run sync operations")
        if not selection_only and not index_only:
            print("  - selection-sync")
            print("  - index-refresh")
        else:
            if selection_only:
                print("  - selection-sync")
            if index_only:
                print("  - index-refresh")
        if domain:
            print(f"  Filtered by domain: {domain}")
        return 0

    exit_code = 0

    if not index_only:
        run_selection_sync = _get_run_selection_sync()
        code = run_selection_sync(vault, verbose=getattr(args, "verbose", False))
        if code != 0:
            exit_code = code

    if not selection_only:
        run_index_refresh = _get_run_index_refresh()
        code = run_index_refresh(vault, verbose=getattr(args, "verbose", False))
        if code != 0 and exit_code == 0:
            exit_code = code

    return exit_code
