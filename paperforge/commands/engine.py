"""CLI command `paperforge engine` — Unified SQLite SSOT & VaultEngine diagnostics."""

from __future__ import annotations

import argparse
from pathlib import Path

from paperforge import __version__
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult


def run(args: argparse.Namespace) -> int:
    vault = Path(getattr(args, "vault_path", None) or ".").resolve()
    verb = str(getattr(args, "engine_verb", "status") or "status").strip()
    json_output = bool(getattr(args, "json", False))

    from paperforge.services.vault_engine import (
        read_vault_manifest,
        rebuild_db_from_truth,
        sync_ocr_catalog,
        sync_workspace_registry,
    )

    try:
        if verb == "status":
            manifest = read_vault_manifest(vault)
            data = {"vault": str(vault), "manifest": manifest}
        elif verb == "sync-registry":
            ws = sync_workspace_registry(vault)
            ocr = sync_ocr_catalog(vault)
            data = {"workspace_registry": ws, "ocr_catalog": ocr}
        elif verb == "rebuild-db":
            data = rebuild_db_from_truth(vault)
        else:
            raise ValueError(f"Unknown engine verb: {verb}")

        res = PFResult(ok=True, command=f"engine {verb}", version=__version__, data=data)
    except Exception as exc:  # noqa: BLE001
        err_res = PFResult(
            ok=False,
            command=f"engine {verb}",
            version=__version__,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
        print(err_res.to_json() if json_output else f"engine {verb} failed: {exc}")
        return 1

    if json_output:
        print(res.to_json())
    else:
        print(f"engine {verb}: ok -> {data}")
    return 0
