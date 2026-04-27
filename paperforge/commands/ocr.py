"""OCR command — unifies OCR run and diagnose."""

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _diagnose(vault: Path, live: bool = False) -> int:
    """Run OCR diagnostics and print results."""
    from paperforge.ocr_diagnostics import ocr_doctor

    result = ocr_doctor(config=None, live=live)
    level = result.get("level", 0)
    passed = result.get("passed", False)

    print(f"OCR Doctor — Level {level} diagnostic")
    print("-" * 40)
    if passed:
        print(f"[PASS] {result.get('message', 'All checks passed')}")
        return 0
    else:
        print(f"[FAIL] Level {level}: {result.get('error', 'Unknown failure')}")
        print(f"[FIX]  {result.get('fix', 'No fix suggestion available')}")
        if result.get("raw_response"):
            print(f"[RAW]  {result['raw_response'][:200]}...")
        return 1


def _get_run_ocr():
    """Get run_ocr, preferring cli patches if available."""
    try:
        from paperforge.cli import run_ocr

        if run_ocr is not None:
            return run_ocr
    except Exception:
        pass

    import sys

    repo_root = Path(__file__).resolve().parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from paperforge.worker.ocr import run_ocr

    return run_ocr


def run(args: argparse.Namespace) -> int:
    """Run OCR command.

    Default behavior: run OCR queue.
    --diagnose: diagnose only (no upload).
    --key KEY: process specific item (passed through if supported).
    """
    vault = getattr(args, "vault_path", None)
    if vault is None:
        from paperforge.config import resolve_vault

        vault = resolve_vault(cli_vault=getattr(args, "vault", None))

    diagnose_only = getattr(args, "diagnose", False)
    key = getattr(args, "key", None)
    live = getattr(args, "live", False)

    # Backward compat: if subcommand was "doctor", diagnose
    ocr_action = getattr(args, "ocr_action", None)
    if ocr_action == "doctor" or diagnose_only:
        return _diagnose(vault, live=live)

    if key:
        logger.info("Processing specific key: %s", key)

    run_ocr = _get_run_ocr()
    exit_code = run_ocr(vault, verbose=getattr(args, "verbose", False), no_progress=getattr(args, "no_progress", False))

    # Auto-diagnose after successful run (new unified behavior)
    if exit_code == 0 and ocr_action is None and not diagnose_only and not key:
        logger.info("Running post-OCR diagnostic...")
        try:
            diag_code = _diagnose(vault, live=False)
            if diag_code != 0:
                logger.warning("Post-OCR diagnostic found issues, but OCR completed successfully.")
        except Exception as e:
            logger.warning("Auto-diagnose failed: %s", e)

    return exit_code
