"""Sync command — unified sync through SyncService."""

import argparse
import logging

from paperforge.config import migrate_paperforge_json
from paperforge.core.result import PFResult
from paperforge import __version__

logger = logging.getLogger(__name__)


def run(args: argparse.Namespace) -> int:
    """Run sync command through SyncService.

    By default runs both selection-sync and index-refresh + cleanup.
    Use --selection or --index to run only one phase.
    SyncService is the canonical entry point for all sync operations.
    """
    vault = getattr(args, "vault_path", None)
    if vault is None:
        from paperforge.config import resolve_vault

        vault = resolve_vault(cli_vault=getattr(args, "vault", None))

    verbose = getattr(args, "verbose", False)
    migrated = migrate_paperforge_json(vault)
    if migrated:
        logger.info("Migrated paperforge.json to vault_config canonical format")
        if verbose:
            print("[INFO] paperforge.json migrated to canonical format (backup: paperforge.json.bak)")

    dry_run = getattr(args, "dry_run", False)
    selection_only = getattr(args, "selection", False)
    index_only = getattr(args, "index", False)
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
        return 0

    from paperforge.services.sync_service import SyncService

    svc = SyncService(vault)
    result = svc.run(verbose=verbose, json_output=json_output, selection_only=selection_only, index_only=index_only)

    if json_output:
        print(result.to_json())
        return 0

    return 0 if result.ok else 1
