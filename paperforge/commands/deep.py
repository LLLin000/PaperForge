"""Deep-reading queue command."""

import argparse
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from paperforge import __version__
from paperforge.core.result import PFResult


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
    from paperforge.worker.deep_reading import run_deep_reading

    return run_deep_reading


def run(args: argparse.Namespace) -> int:
    """Run deep-reading queue check. Supports --json for PFResult output."""
    vault = getattr(args, "vault_path", None)
    if vault is None:
        from paperforge.config import resolve_vault

        vault = resolve_vault(cli_vault=getattr(args, "vault", None))

    json_output = getattr(args, "json", False)
    run_deep_reading = _get_run_deep_reading()

    if json_output:
        # The worker keeps a human summary for text mode. Machine mode must
        # expose one JSON envelope, not a summary line followed by JSON.
        with redirect_stdout(StringIO()):
            exit_code = run_deep_reading(
                vault, verbose=getattr(args, "verbose", False)
            )
    else:
        exit_code = run_deep_reading(vault, verbose=getattr(args, "verbose", False))

    if json_output:
        from paperforge.worker._utils import get_analyze_queue

        queue = get_analyze_queue(vault)
        ready = [r for r in queue if r.get("ocr_status") == "done"]
        blocked = [r for r in queue if r.get("ocr_status") != "done"]

        pf = PFResult(
            ok=True,
            command="deep-reading",
            version=__version__,
            data={
                "queue": [
                    {
                        "zotero_key": r["zotero_key"],
                        "domain": r["domain"],
                        "title": r["title"],
                        "ocr_status": r.get("ocr_status", "pending"),
                        "ready": r.get("ocr_status") == "done",
                    }
                    for r in queue
                ],
                "summary": {
                    "total": len(queue),
                    "ready": len(ready),
                    "blocked": len(blocked),
                },
            },
        )
        print(pf.to_json())
        return 0

    return exit_code
