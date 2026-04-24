"""Status command."""

import argparse
from pathlib import Path


def _get_run_status():
    """Get run_status, preferring cli patches if available."""
    try:
        from paperforge.cli import run_status

        if run_status is not None:
            return run_status
    except Exception:
        pass

    import sys

    repo_root = Path(__file__).resolve().parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from pipeline.worker.scripts.literature_pipeline import run_status

    return run_status


def run(args: argparse.Namespace) -> int:
    """Run status check."""
    vault = getattr(args, "vault_path", None)
    if vault is None:
        from paperforge.config import resolve_vault

        vault = resolve_vault(cli_vault=getattr(args, "vault", None))

    run_status = _get_run_status()
    return run_status(vault)
