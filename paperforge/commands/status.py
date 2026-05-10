"""Status command.

Reports vault statistics including library record counts, OCR progress,
and path_error counts.  Uses PFResult contract for JSON output.
"""

import argparse
import logging
from pathlib import Path

from paperforge.core.result import PFResult

logger = logging.getLogger(__name__)


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
    from paperforge.worker.status import run_status

    return run_status


def run(args: argparse.Namespace) -> int:
    """Run status check.  Worker handles PFResult JSON output when json_output=True."""
    vault = getattr(args, "vault_path", None)
    if vault is None:
        from paperforge.config import resolve_vault

        vault = resolve_vault(cli_vault=getattr(args, "vault", None))

    run_status = _get_run_status()
    exit_code = run_status(vault, verbose=getattr(args, "verbose", False), json_output=getattr(args, "json", False))
    # Worker already prints PFResult when json_output=True; propagate exit code
    return exit_code
