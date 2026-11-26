"""CLI command `paperforge upgrade` — census, fast cutover, progressive heal, & rollback."""

from __future__ import annotations

import argparse
from pathlib import Path

from paperforge import __version__
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult


def run(args: argparse.Namespace) -> int:
    vault = Path(getattr(args, "vault_path", None) or ".").resolve()
    json_output = bool(getattr(args, "json", False))
    do_rollback = bool(getattr(args, "rollback", False))
    do_heal = bool(getattr(args, "heal", False))
    raw_apply = bool(getattr(args, "apply", False))
    raw_dry_run = bool(getattr(args, "dry_run", False))
    raw_plan = bool(getattr(args, "plan", False))
    apply_changes = raw_apply and not raw_dry_run
    fast_cutover = bool(getattr(args, "fast_cutover", False))
    backfill_ocr = bool(getattr(args, "backfill_ocr", False))
    quarantine_residuals = bool(getattr(args, "quarantine_residuals", False))
    quarantine_ids_raw = str(getattr(args, "quarantine_ids", "") or "").strip()
    quarantine_ids = [x.strip() for x in quarantine_ids_raw.split(",") if x.strip()] if quarantine_ids_raw else None
    rebuild_db = not bool(getattr(args, "no_rebuild_db", False))
    priority_key = str(getattr(args, "priority_key", "") or "").strip() or None
    heal_limit = getattr(args, "limit", None)

    if fast_cutover and not raw_apply and not raw_dry_run and not raw_plan and not do_rollback and not do_heal:
        msg = "--fast-cutover requires --apply. Use --apply --fast-cutover to execute cutover."
        err_result = PFResult(
            ok=False,
            command="upgrade",
            version=__version__,
            error=PFError(code=ErrorCode.VALIDATION_ERROR, message=msg),
        )
        print(err_result.to_json() if json_output else f"upgrade error: {msg}")
        return 2

    from paperforge.services.vault_upgrade import (
        execute_vault_upgrade,
        heal_vault_progressive,
        inspect_vault_upgrade,
        rollback_vault_upgrade,
    )

    try:
        if do_rollback:
            data = rollback_vault_upgrade(vault)
        elif do_heal:
            data = heal_vault_progressive(
                vault,
                limit=heal_limit,
                priority_key=priority_key,
                backfill_ocr=backfill_ocr,
            )
        elif not apply_changes:
            data = inspect_vault_upgrade(vault)
        else:
            data = execute_vault_upgrade(
                vault,
                dry_run=False,
                fast_cutover=fast_cutover,
                backfill_ocr=backfill_ocr,
                quarantine_residuals=quarantine_residuals,
                quarantine_ids=quarantine_ids,
                rebuild_db=rebuild_db,
            )
        result = PFResult(ok=True, command="upgrade", version=__version__, data=data)
    except Exception as exc:  # noqa: BLE001
        err_result = PFResult(
            ok=False,
            command="upgrade",
            version=__version__,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
        print(err_result.to_json() if json_output else f"upgrade failed: {exc}")
        return 1

    if json_output:
        print(result.to_json())
    else:
        if do_rollback or do_heal:
            print(f"upgrade: {data}")
            return 0
        plan = data if not apply_changes else data.get("post_check", {})
        summary = plan.get("summary", {})
        ocr_atoms = summary.get("ocr_atoms", {})
        prefix = "[APPLIED] " if apply_changes else "[PLAN / DRY-RUN] "
        print(
            f"{prefix}Vault={vault} (provenance={plan.get('provenance', {}).get('state')})\n"
            f"  Auto-migratable: {summary.get('auto_count', 0)} (fast_cutover={summary.get('fast_cutover_count', 0)}, progressive={summary.get('progressive_heal_count', 0)})\n"
            f"  Reconfig: critical={summary.get('reconfig_critical_count', 0)}, minor={summary.get('reconfig_minor_count', 0)}\n"
            f"  Tamper/integrity: {summary.get('tamper_count', 0)}\n"
            f"  OCR atoms: total={ocr_atoms.get('total', 0)}, current={ocr_atoms.get('current', 0)}, "
            f"backfill_zero_cost={ocr_atoms.get('backfill_from_result_json', 0)}, re_ocr_needed={ocr_atoms.get('re_ocr_needed', 0)}\n"
            f"  Cleanup candidates: {summary.get('cleanup_candidate_count', 0)}"
        )
    return 0
