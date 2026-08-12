"""Repair command."""

import argparse
import logging
from pathlib import Path

from paperforge import __version__
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult

logger = logging.getLogger(__name__)


def _get_run_repair():
    """Get run_repair, preferring cli patches if available."""
    try:
        from paperforge.cli import run_repair

        if run_repair is not None:
            return run_repair
    except Exception:
        pass

    import sys

    repo_root = Path(__file__).resolve().parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from paperforge.worker.repair import run_repair

    return run_repair


def run(args: argparse.Namespace) -> int:
    """Run repair command. Supports --json for PFResult output."""
    vault = getattr(args, "vault_path", None)
    paths = getattr(args, "paths", None)
    if vault is None:
        from paperforge.config import resolve_vault
        from paperforge.worker._utils import pipeline_paths

        vault = resolve_vault(cli_vault=getattr(args, "vault", None))
        paths = pipeline_paths(vault)
    elif paths is None or "config" not in paths:
        from paperforge.worker._utils import pipeline_paths

        paths = pipeline_paths(vault)

    run_repair = _get_run_repair()
    json_output = getattr(args, "json", False)
    result = run_repair(
        vault,
        paths,
        verbose=getattr(args, "verbose", False),
        fix=getattr(args, "fix", False),
        fix_paths=getattr(args, "fix_paths", False),
    )

    # ── Build PFResult ──
    divergent: list = result.get("divergent", [])
    path_errors: dict = result.get("path_errors", {})
    divergent_count = len(divergent)
    path_error_total = path_errors.get("total", 0)
    has_issues = divergent_count > 0 or path_error_total > 0

    pf_error = None
    if has_issues:
        pf_error = PFError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Repair found {divergent_count} divergences and {path_error_total} path errors",
            details=result,
        )

    pf = PFResult(
        ok=not has_issues,
        command="repair",
        version=__version__,
        data={
            "scanned": result.get("scanned", 0),
            "divergent": divergent,
            "fixed": result.get("fixed", 0),
            "errors": result.get("errors", []),
            "rebuilt": result.get("rebuilt", 0),
            "path_errors": result.get("path_errors", {}),
        },
        error=pf_error,
    )

    if json_output:
        print(pf.to_json())
        return 0 if pf.ok else 1

    # Human-readable output
    path_errors = result.get("path_errors", {})
    if path_errors.get("total", 0) > 0:
        error_summary = ", ".join(f"{count} {err}" for err, count in sorted(path_errors.get("by_type", {}).items()))
        print(f"repair: Found {path_errors['total']} items with path_error: {error_summary}")
    return 1 if has_issues else 0
