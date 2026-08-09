"""Sync command — unified sync through SyncService."""

import argparse
import contextlib
import inspect
import logging

from paperforge import __version__
from paperforge.core.result import PFResult

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

    if result.warnings and not json_output:
        for w in result.warnings:
            print(f"[WARN] {w}")

    # #127: the command core only produces follow-ups; it never executes
    # remote/destructive work. JSON mode prints the final PFResult exactly
    # once and performs no follow-up; the terminal runner may execute
    # automatic-local actions inline (see _run_terminal_followups).
    if result.ok and not index_only and not selection_only:
        _attach_next_actions(result)

    if json_output:
        print(result.to_json())
        return 0

    if not result.ok:
        return 1

    _run_terminal_followups(vault, result)
    return 0


def _attach_next_actions(result: PFResult) -> None:
    """Append the canonical follow-up actions for a successful full sync.

    - memory.build: automatic, local, mutating — executors may run it inline.
    - embed.resume: remote-possible, mutating — never automatic, always
      requires confirmation (the sync command must not silently spend API
      cost on embedding).
    """
    from paperforge.core.next_actions import (
        NextActionScope,
        build_next_action,
        next_actions_to_dicts,
    )

    result.next_actions = next_actions_to_dicts((
        build_next_action(
            "memory.build",
            reason="library index changed after sync",
            scope=NextActionScope(kind="all"),
        ),
        build_next_action(
            "embed.resume",
            reason="changed papers need vector embeddings",
            scope=NextActionScope(kind="all"),
        ),
    ))


def _run_terminal_followups(vault, result: PFResult) -> None:
    """Terminal runner policy: execute automatic-local actions inline, never
    execute remote/destructive work, and surface what needs confirmation."""
    from paperforge.core.next_actions import (
        automatic_local_actions,
        next_actions_from_dicts,
        remote_or_destructive_actions,
    )

    actions = next_actions_from_dicts(result.next_actions)
    for action in automatic_local_actions(actions):
        if action.action_id == "memory.build":
            _run_memory_build(vault)
    for action in remote_or_destructive_actions(actions):
        print(
            f"[INFO] follow-up '{action.action_id}' needs confirmation "
            f"({action.cost}, {action.impact}); run it explicitly or from the plugin."
        )


def _run_memory_build(vault) -> None:
    try:
        from paperforge.memory.builder import build_from_index

        counts = build_from_index(vault)
        tag = " (fast)" if counts.get("hash_match") else ""
        print(f"memory: {counts.get('papers_indexed', 0)} papers{tag}")
    except Exception as e:  # noqa: BLE001 — local follow-up failure must not fail sync
        print(f"memory: deferred ({e})")


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
