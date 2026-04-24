"""Deep-reading queue command."""

import argparse
from pathlib import Path


def _get_run_deep_reading():
    """Get run_deep_reading, preferring cli patches if available."""
    try:
        from paperforge.cli import run_deep_reading

        if run_deep_reading is not None:
            return run_deep_reading
    except Exception:
        pass

    import sys

    repo_root = Path(__file__).resolve().parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from pipeline.worker.scripts.literature_pipeline import run_deep_reading

    return run_deep_reading


def run(args: argparse.Namespace) -> int:
    """Run deep-reading queue check."""
    vault = getattr(args, "vault_path", None)
    if vault is None:
        from paperforge.config import resolve_vault

        vault = resolve_vault(cli_vault=getattr(args, "vault", None))

    run_deep_reading = _get_run_deep_reading()
    return run_deep_reading(vault, verbose=getattr(args, "verbose", False))
