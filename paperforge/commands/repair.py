"""Repair command."""

import argparse
from pathlib import Path


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
    from pipeline.worker.scripts.literature_pipeline import run_repair

    return run_repair


def run(args: argparse.Namespace) -> int:
    """Run repair command."""
    vault = getattr(args, "vault_path", None)
    paths = getattr(args, "paths", None)
    if vault is None:
        from paperforge.config import resolve_vault, paperforge_paths, load_vault_config

        vault = resolve_vault(cli_vault=getattr(args, "vault", None))
        cfg = load_vault_config(vault)
        paths = paperforge_paths(vault, cfg)

    run_repair = _get_run_repair()
    return run_repair(
        vault,
        paths,
        verbose=getattr(args, "verbose", False),
        fix=getattr(args, "fix", False),
    )
