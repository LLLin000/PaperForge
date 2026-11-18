"""CLI command `paperforge migrate-storage`."""
from __future__ import annotations

import argparse
from pathlib import Path

from paperforge import __version__
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult


def run(args: argparse.Namespace) -> int:
    vault = Path(getattr(args, "vault_path", None) or ".").resolve()
    dry_run = bool(getattr(args, "dry_run", False))
    json_output = bool(getattr(args, "json", False))

    from paperforge.services.storage_migration import migrate_vault_storage

    try:
        report = migrate_vault_storage(vault, dry_run=dry_run)
        result = PFResult(
            ok=True,
            command="migrate-storage",
            version=__version__,
            data=report,
        )
    except Exception as exc:  # noqa: BLE001
        result = PFResult(
            ok=False,
            command="migrate-storage",
            version=__version__,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
        print(result.to_json() if json_output else f"migrate-storage failed: {exc}")
        return 1

    if json_output:
        print(result.to_json())
    else:
        prefix = "[DRY-RUN] " if dry_run else ""
        print(
            f"{prefix}Migrated storage -> .paperforge: "
            f"moved={report['entries_moved']}, "
            f"assets={report['visual_assets_materialized']}, "
            f"notes_rewritten={report['notes_rewritten']}, "
            f"workspace_fulltexts_removed={report['workspace_fulltexts_removed']}"
        )
    return 0
