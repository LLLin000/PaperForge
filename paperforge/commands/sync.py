"""Sync command — unifies selection-sync and index-refresh."""

import argparse
import json as _json
import logging
from pathlib import Path

from paperforge import __version__
from paperforge.config import migrate_paperforge_json
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult

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

    verbose = getattr(args, "verbose", False)
    # Auto-migrate paperforge.json from legacy top-level keys to vault_config block
    migrated = migrate_paperforge_json(vault)
    if migrated:
        logger.info("Migrated paperforge.json to vault_config canonical format")
        if verbose:
            print("[INFO] paperforge.json migrated to canonical format (backup: paperforge.json.bak)")

    dry_run = getattr(args, "dry_run", False)
    selection_only = getattr(args, "selection", False)
    index_only = getattr(args, "index", False)
    rebuild_index = getattr(args, "rebuild_index", False)
    domain = getattr(args, "domain", None)
    json_output = getattr(args, "json", False)

    if dry_run:
        if json_output:
            result = PFResult(
                ok=True,
                command="sync",
                version=__version__,
                data={"dry_run": True, "selection": not index_only, "index": not selection_only},
            )
            print(result.to_json())
            return 0
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
    sync_counts = {"new": 0, "updated": 0, "skipped": 0, "failed": 0, "errors": []}

    if not index_only:
        run_selection_sync = _get_run_selection_sync()
        result = run_selection_sync(vault, verbose=getattr(args, "verbose", False), json_output=json_output)
        if json_output:
            sync_counts = result
        elif result != 0:
            exit_code = result

    if not selection_only:
        run_index_refresh = _get_run_index_refresh()
        code = run_index_refresh(vault, verbose=getattr(args, "verbose", False), rebuild_index=rebuild_index, json_output=json_output)
        if code != 0 and exit_code == 0:
            exit_code = code

    if json_output:
        errors = sync_counts.get("errors", [])
        pf_error = None
        if errors or exit_code != 0:
            pf_error = PFError(
                code=ErrorCode.SYNC_FAILED,
                message=f"Sync completed with {len(errors)} error(s)",
                details={"errors": errors, "exit_code": exit_code},
            )
        result = PFResult(
            ok=exit_code == 0 and not errors,
            command="sync",
            version=__version__,
            data=sync_counts,
            error=pf_error,
        )
        print(result.to_json())
        return 0

    return exit_code
