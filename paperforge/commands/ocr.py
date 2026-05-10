"""OCR command — unifies OCR run and diagnose."""

import argparse
import logging
from pathlib import Path

from paperforge import __version__
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult

logger = logging.getLogger(__name__)


def _collect_ocr_queue_data(vault: Path) -> dict:
    """Scan OCR meta files and build queue status data dict.

    Returns dict shaped as:
      {queue: {pending: [...], processing: [...], done: [...], failed: [...]},
       total: N, done: N, failed: N, pending: N, processing: N}
    """
    from paperforge.worker._utils import pipeline_paths, read_json

    paths = pipeline_paths(vault)
    queue_lists = {"pending": [], "processing": [], "done": [], "failed": []}
    ocr_root = paths.get("ocr")
    if ocr_root and ocr_root.exists():
        for meta_path in sorted(ocr_root.glob("*/meta.json")):
            try:
                meta = read_json(meta_path)
            except Exception:
                continue
            key = str(meta.get("zotero_key", "") or "").strip()
            status = str(meta.get("ocr_status", "") or "").strip().lower()
            if not key:
                continue
            if status == "done":
                queue_lists["done"].append(key)
            elif status in ("queued", "running", "processing"):
                queue_lists["processing"].append(key)
            elif status == "pending":
                queue_lists["pending"].append(key)
            else:
                queue_lists["failed"].append(key)
    return {
        "queue": queue_lists,
        "total": sum(len(v) for v in queue_lists.values()),
        "done": len(queue_lists["done"]),
        "failed": len(queue_lists["failed"]),
        "pending": len(queue_lists["pending"]),
        "processing": len(queue_lists["processing"]),
    }


def _diagnose(vault: Path, live: bool = False, json_output: bool = False) -> int:
    """Run OCR diagnostics and print results."""
    from paperforge.ocr_diagnostics import ocr_doctor

    result = ocr_doctor(config=None, live=live)
    level = result.get("level", 0)
    passed = result.get("passed", False)

    if json_output:
        queue_data = _collect_ocr_queue_data(vault)
        pf_error = None
        if not passed:
            if level == 1:
                ec = ErrorCode.OCR_TOKEN_MISSING
            elif level == 2:
                ec = ErrorCode.OCR_UPLOAD_FAILED
            elif level == 3:
                ec = ErrorCode.OCR_RESULT_INVALID
            else:
                ec = ErrorCode.INTERNAL_ERROR
            pf_error = PFError(
                code=ec,
                message=result.get("error", "OCR diagnosis failed"),
                details={"level": level, "fix": result.get("fix", "")},
            )
        pf_result = PFResult(
            ok=passed,
            command="ocr-diagnose",
            version=__version__,
            data={
                "diagnosis": {
                    "level": level,
                    "passed": passed,
                    "message": result.get("message", result.get("error", "")),
                },
                **queue_data,
            },
            error=pf_error,
        )
        print(pf_result.to_json())
        return 0 if passed else 1

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
    Supports --json for PFResult output in both diagnose and normal modes.
    """
    vault = getattr(args, "vault_path", None)
    if vault is None:
        from paperforge.config import resolve_vault

        vault = resolve_vault(cli_vault=getattr(args, "vault", None))

    diagnose_only = getattr(args, "diagnose", False)
    key = getattr(args, "key", None)
    live = getattr(args, "live", False)
    json_output = getattr(args, "json", False)

    # Backward compat: if subcommand was "doctor", diagnose
    ocr_action = getattr(args, "ocr_action", None)
    if ocr_action == "doctor" or diagnose_only:
        return _diagnose(vault, live=live, json_output=json_output)

    if key:
        logger.info("Processing specific key: %s", key)

    run_ocr = _get_run_ocr()
    exit_code = run_ocr(vault, verbose=getattr(args, "verbose", False), no_progress=getattr(args, "no_progress", False))

    if json_output:
        queue_data = _collect_ocr_queue_data(vault)
        pf = PFResult(
            ok=exit_code == 0,
            command="ocr",
            version=__version__,
            data=queue_data,
        )
        print(pf.to_json())
        return 0 if pf.ok else 1

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
