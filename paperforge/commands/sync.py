"""Sync command — unified sync through SyncService."""

import argparse
import inspect
import logging

from paperforge import __version__
from paperforge.config import migrate_paperforge_json
from paperforge.core.result import PFResult

logger = logging.getLogger(__name__)


def run(args: argparse.Namespace) -> int:
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
    prune_flag = getattr(args, "prune", False)
    prune_force = getattr(args, "prune_force", False)

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
    run_kwargs = {
        "verbose": verbose,
        "json_output": json_output,
        "selection_only": selection_only,
        "index_only": index_only,
        "prune": prune_flag,
        "prune_force": prune_force,
        "rebuild_index": getattr(args, "rebuild_index", False),
    }
    try:
        sig = inspect.signature(svc.run)
        accepted = {name for name in sig.parameters.keys() if name != "self"}
        filtered_kwargs = {k: v for k, v in run_kwargs.items() if k in accepted}
    except Exception:
        filtered_kwargs = run_kwargs
    result = svc.run(**filtered_kwargs)

    _write_orphan_state(vault, result)

    if result.warnings and not json_output:
        for w in result.warnings:
            print(f"[WARN] {w}")

    if json_output:
        print(result.to_json())
        if result.ok and not dry_run and not index_only and not selection_only:
            try:
                from paperforge.memory.builder import build_from_index
                build_from_index(vault)
            except Exception:
                pass
            try:
                import subprocess
                import sys
                subprocess.Popen(
                    [sys.executable, "-m", "paperforge", "embed", "build", "--resume"],
                    cwd=str(vault),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
                )
            except Exception:
                pass
        return 0

    if not result.ok:
        return 1

    try:
        from paperforge.memory.builder import build_from_index
        counts = build_from_index(vault)
        tag = " (fast)" if counts.get("hash_match") else ""
        print(f"memory: {counts.get('papers_indexed', 0)} papers{tag}")
    except Exception as e:
        print(f"memory: deferred ({e})")

    try:
        import subprocess
        import sys
        subprocess.Popen(
            [sys.executable, "-m", "paperforge", "embed", "build", "--resume"],
            cwd=str(vault),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
    except Exception:
        pass

    return 0


def _write_orphan_state(vault, result: PFResult) -> None:
    preview = (result.data or {}).get("prune", {}) if result.data else {}
    items = preview.get("preview", []) if isinstance(preview, dict) else []
    orphan_path = vault / "System" / "PaperForge" / "indexes" / "sync-orphan-state.json"
    if not items:
        try:
            orphan_path.unlink(missing_ok=True)
        except Exception:
            pass
        return

    import json as _json

    orphan_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        orphan_path.write_text(_json.dumps({"orphans": items, "count": len(items)}, indent=2), encoding="utf-8")
    except Exception:
        pass
