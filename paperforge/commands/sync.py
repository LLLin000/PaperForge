"""Sync command — unified sync through SyncService."""

import argparse
import contextlib
import inspect
import logging

from paperforge import __version__
from paperforge.core.result import PFResult
from paperforge.reconcile import reconcile

logger = logging.getLogger(__name__)


def run(args: argparse.Namespace) -> int:
    vault = getattr(args, "vault_path", None)
    if vault is None:
        from paperforge.config import resolve_vault
        vault = resolve_vault(cli_vault=getattr(args, "vault", None))

    verbose = getattr(args, "verbose", False)

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
        accepted = {name for name in sig.parameters if name != "self"}
        filtered_kwargs = {k: v for k, v in run_kwargs.items() if k in accepted}
    except Exception:
        filtered_kwargs = run_kwargs
    result = svc.run(**filtered_kwargs)

    _write_orphan_state(vault, result)
    _cleanup_legacy_snapshot_files(vault)

    if result.warnings and not json_output:
        for w in result.warnings:
            print(f"[WARN] {w}")

    # T6 (#167) convergence cutover: sync completes external source
    # detection + canonical library sync, then runs reconcile(all) — never
    # changed_keys-only, because a broken eager chain must recover even
    # when the source is unchanged (#159 §4).  The generic follow-up chain
    # runner executes the emitted intents; reconcile is the SINGLE
    # producer — no command-specific branch, no hardcoded follow-ups.
    if result.ok and not index_only and not selection_only:
        _reconcile_and_attach(vault, result, execute=not json_output)

    if json_output:
        print(result.to_json())
        return 0

    if not result.ok:
        return 1

    return 0


def _reconcile_and_attach(vault, result: PFResult, *, execute: bool) -> None:
    """T6: reconcile(all) is the single producer of follow-up intents.

    JSON mode attaches the intents and never executes; terminal mode runs
    them through the generic follow-up chain (automatic-local inline,
    remote/destructive/confirmation-required pending) with the chain
    transcript attached to the result data.
    """
    from paperforge.actions.chain import run_chain
    from paperforge.actions.runner import build_context

    context = build_context(vault)
    initial = reconcile(vault)
    result.next_actions = list(initial.next_actions or [])

    if not execute:
        return

    chain = run_chain(result.next_actions, context)
    data = dict(result.data or {})
    data["chain"] = chain.to_wire()
    result.data = data
    result.next_actions = chain.pending
    for step in chain.steps:
        if step.status == "executed":
            print(f"ok: {step.action_id}")
        elif step.status == "pending":
            print(f"[INFO] follow-up '{step.action_id}' needs confirmation "
                  f"({step.reason_code}); run it explicitly or from the plugin.")
        else:
            print(f"[INFO] follow-up '{step.action_id}' skipped ({step.reason_code}).")


# T6 (#167): the shared follow-up chain runner replaces the hardcoded
# memory.build terminal branch.


def _cleanup_legacy_snapshot_files(vault) -> None:
    """#148: best-effort removal of the retired snapshot contract files.

    Zero readers + zero writers make these inert garbage; hygiene only —
    failure to clean never fails the cutover and never affects the result.
    """
    from pathlib import Path

    for name in ("memory-runtime-state.json", "vector-runtime-state.json", "runtime-health.json"):
        try:
            legacy = Path(vault) / "99_System" / "PaperForge" / "indexes" / name
            legacy.unlink(missing_ok=True)
        except OSError:
            logger.debug("legacy snapshot cleanup skipped for %s", name)


def _write_orphan_state(vault, result: PFResult) -> None:
    preview = (result.data or {}).get("prune", {}) if result.data else {}
    items = preview.get("preview", []) if isinstance(preview, dict) else []
    orphan_path = vault / "System" / "PaperForge" / "indexes" / "sync-orphan-state.json"
    if not items:
        with contextlib.suppress(Exception):
            orphan_path.unlink(missing_ok=True)
        return

    import json as _json

    orphan_path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(Exception):
        orphan_path.write_text(_json.dumps({"orphans": items, "count": len(items)}, indent=2), encoding="utf-8")
