"""OCR command — unifies OCR run and diagnose."""

import argparse
import json
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


def _collect_ocr_health_summary(vault: Path) -> list[dict]:
    """Scan OCR directories for health/ocr_health.json files and return summaries."""
    from paperforge.worker._utils import pipeline_paths

    paths = pipeline_paths(vault)
    ocr_root = paths.get("ocr")
    if not ocr_root or not ocr_root.exists():
        return []
    summaries = []
    for dir_path in sorted(ocr_root.iterdir()):
        if not dir_path.is_dir():
            continue
        health_path = dir_path / "health" / "ocr_health.json"
        if health_path.exists():
            try:
                health = json.loads(health_path.read_text(encoding="utf-8"))
                summaries.append({
                    "key": dir_path.name,
                    "overall": health.get("overall", "unknown"),
                    "page_count": health.get("page_count", 0),
                    "blocks_count": health.get("blocks_count", 0),
                    "figure_count": health.get("figure_caption_count", 0),
                    "table_count": health.get("table_caption_count", 0),
                })
            except Exception:
                continue
    return summaries


def _diagnose(vault: Path, live: bool = False, json_output: bool = False) -> int:
    """Run OCR diagnostics and print results."""
    from paperforge.ocr_diagnostics import ocr_doctor

    result = ocr_doctor(config=None, live=live)
    level = result.get("level", 0)
    passed = result.get("passed", False)

    # Collect OCR version state
    _version_state_summary: dict = {
        "total_papers": 0, "derived_stale": [], "raw_upgradable": [],
        "legacy_backfilled": [],
    }
    try:
        from paperforge.config import load_vault_config
        cfg = load_vault_config(vault)
        ocr_root = vault / cfg["system_dir"] / "PaperForge" / "ocr"
        if ocr_root.exists():
            from paperforge.worker._utils import read_json
            _version_papers = []
            for paper_dir in ocr_root.iterdir():
                if not paper_dir.is_dir():
                    continue
                meta_path = paper_dir / "meta.json"
                if meta_path.exists():
                    meta = read_json(meta_path)
                    has_state = "raw_version" in meta or "derived_version" in meta
                    if has_state:
                        _version_papers.append(meta)
                    elif meta.get("ocr_status") == "done" and meta.get("is_backfilled"):
                        _version_papers.append({**meta, "is_legacy": True})
            _version_state_summary = {
                "total_papers": len(_version_papers),
                "derived_stale": [m.get("zotero_key", "?") for m in _version_papers if m.get("derived_stale")],
                "raw_upgradable": [m.get("zotero_key", "?") for m in _version_papers if m.get("raw_upgradable")],
                "legacy_backfilled": [m.get("zotero_key", "?") for m in _version_papers if m.get("is_legacy")],
            }
    except Exception:
        pass

    if json_output:
        queue_data = _collect_ocr_queue_data(vault)
        structured_health = _collect_ocr_health_summary(vault)
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
                "structured_health": structured_health,
                "ocr_version_state": _version_state_summary,
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
    else:
        print(f"[FAIL] Level {level}: {result.get('error', 'Unknown failure')}")
        print(f"[FIX]  {result.get('fix', 'No fix suggestion available')}")
        if result.get("raw_response"):
            print(f"[RAW]  {result['raw_response'][:200]}...")

    structured_health = _collect_ocr_health_summary(vault)
    if structured_health:
        print()
        print("--- Structured OCR Health ---")
        print(f"Papers with health data: {len(structured_health)}")
        for entry in structured_health:
            print(
                f"- {entry['key']}: overall={entry['overall']}, "
                f"{entry['page_count']} pages, {entry['blocks_count']} blocks, "
                f"{entry['figure_count']} figures, {entry['table_count']} tables"
            )

    if _version_state_summary["total_papers"] > 0:
        print()
        print("--- OCR Version State ---")
        print(f"  ocr_version_state: {_version_state_summary['total_papers']} paper(s)")
        if _version_state_summary["derived_stale"]:
            print(f"    derived_stale: {len(_version_state_summary['derived_stale'])} paper(s)")
            for k in _version_state_summary["derived_stale"]:
                print(f"      - {k}")
        if _version_state_summary["raw_upgradable"]:
            print(f"    raw_upgradable: {len(_version_state_summary['raw_upgradable'])} paper(s)")
            for k in _version_state_summary["raw_upgradable"]:
                print(f"      - {k}")
        if _version_state_summary.get("legacy_backfilled"):
            print(f"    legacy_backfilled: {len(_version_state_summary['legacy_backfilled'])} paper(s)")
            for k in _version_state_summary["legacy_backfilled"]:
                print(f"      - {k}")

    return 0 if passed else 1


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


def _run_ocr_redo(vault: Path, keys: list[str] | None = None, dry_run: bool = False,
                   verbose: bool = False, no_progress: bool = False) -> int:
    """Re-run OCR for papers.
    If keys provided, only redo those papers.
    If no keys, scan for ocr_redo: true papers (old behavior).
    """
    from paperforge.worker.ocr import ocr_redo_papers

    if keys:
        # Keyed redo: process specific papers
        from paperforge.worker.ocr import ensure_ocr_meta, write_json
        from paperforge.worker._utils import pipeline_paths
        from pathlib import Path

        paths = pipeline_paths(vault)
        ocr_root = paths.get("ocr")
        if not ocr_root or not ocr_root.exists():
            print("No OCR root directory.")
            return 1

        for key in keys:
            meta_path = ocr_root / key / "meta.json"
            if not meta_path.exists():
                print(f"{key}: no meta.json, skipping")
                continue
            meta = __import__("json").loads(meta_path.read_text(encoding="utf-8"))
            current = str(meta.get("ocr_status", "") or "").strip().lower()
            if current == "nopdf":
                print(f"{key}: nopdf — cannot redo (missing PDF)")
                continue
            # Reset meta to pending
            meta["ocr_status"] = "pending"
            meta["ocr_job_id"] = ""
            meta["ocr_started_at"] = ""
            meta["ocr_finished_at"] = ""
            meta["error"] = ""
            meta["retry_count"] = 0
            if dry_run:
                print(f"{key}: would reset to pending (dry-run)")
            else:
                write_json(meta_path, meta)
                print(f"{key}: reset to pending")

        if not dry_run:
            print(f"Triggering OCR run for {len(keys)} paper(s)...")
        return 0

    return ocr_redo_papers(vault, dry_run=dry_run, verbose=verbose, no_progress=no_progress)


def _run_ocr_list(vault: Path, json_output: bool = False, output_file: str | None = None,
                   manifest: bool = False, keys: list[str] | None = None) -> int:
    """List all papers with OCR maintenance status."""
    from paperforge.worker.ocr_maintenance import collect_maintenance_rows, compute_maintenance_manifest
    import json as _json

    if manifest:
        m = compute_maintenance_manifest(vault)
        payload = _json.dumps(m, ensure_ascii=False, default=str)
        if output_file:
            Path(output_file).write_text(payload, encoding="utf-8")
            print(f"Wrote {len(m)} entries to {output_file}")
        else:
            print(payload)
        return 0

    rows = collect_maintenance_rows(vault)
    if keys is not None:
        keys_set = set(keys)
        rows = [r for r in rows if r.key in keys_set]

    if json_output:
        payload = _json.dumps([r.to_dict() for r in rows], ensure_ascii=False, default=str)
        if output_file:
            Path(output_file).write_text(payload, encoding="utf-8")
            print(f"Wrote {len(rows)} rows to {output_file}")
        else:
            print(payload)
        return 0

    # Terminal table output (unchanged)
    if not rows:
        print("No OCR papers found.")
        return 0
    header = f"{'Key':12s} {'Title':42s} {'Status':8s} {'Health':6s} {'Ver':4s} {'Time':11s} {'Pg':>3s} {'Blk':>4s} {'Act'}"
    print(header)
    print("-" * len(header))
    for r in rows:
        act = r.recommended_action or "-"
        print(
            f"{r.key:12s} {r.title:42s} {r.status:8s} {r.health:6s} "
            f"{r.version:4s} {r.finished_at:11s} {r.pages:>3d} {r.blocks:>4d} {act}"
        )
    return 0


def _run_ocr_rebuild(
    vault: Path,
    keys: list[str] | None = None,
    all_papers: bool = False,
    status_filter: str | None = None,
    dry_run: bool = False,
    resume: bool = False,
    parallel_workers: int = 4,
) -> int:
    """Rebuild OCR-derived artifacts from existing raw blocks."""
    from paperforge.worker.ocr_maintenance import collect_maintenance_rows
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    rows = collect_maintenance_rows(vault)

    if all_papers:
        keys = [r.key for r in rows if r.can_rebuild]
    elif status_filter:
        keys = [r.key for r in rows if r.status == status_filter and r.can_rebuild]
    elif keys:
        valid = {r.key for r in rows}
        keys = [k for k in keys if k in valid]
    else:
        print("Specify paper keys, --all, or --status")
        return 1

    if not keys:
        print("No papers matched for rebuild.")
        return 0

    # Resume: skip keys already in checkpoint (.done.* markers)
    cp_dir = vault / "System" / "PaperForge" / ".ocr_rebuild_checkpoint"
    if resume and cp_dir.exists():
        done = {p.name.removeprefix(".done.") for p in cp_dir.glob(".done.*")}
        skipped = [k for k in keys if k in done]
        keys = [k for k in keys if k not in done]
        if skipped:
            print(f"Skipped {len(skipped)} paper(s) already in checkpoint.")

    if not keys:
        print("No papers to rebuild (all done).")
        return 0

    if dry_run:
        print(f"Would rebuild {len(keys)} paper(s):")
        for k in keys:
            print(f"  - {k}")
        return 0

    from paperforge.worker._progress import progress_bar
    result = run_derived_rebuild_for_keys(
        vault, keys,
        progress_bar=progress_bar,
        checkpoint_dir=cp_dir if resume else None,
        parallel=parallel_workers,
    )
    count = result.get("rebuild_count", 0)
    print(f"Done. Rebuilt {count} paper(s).")
    return 0


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

    if ocr_action == "redo":
        logger.info("OCR redo: scanning for ocr_redo: true papers...")
        rc = _run_ocr_redo(
            vault,
            keys=getattr(args, "keys", None) or None,
            dry_run=getattr(args, "dry_run", False),
            verbose=getattr(args, "verbose", False),
            no_progress=getattr(args, "no_progress", False),
        )
        return rc

    if ocr_action == "list":
        return _run_ocr_list(
            vault,
            json_output=json_output,
            output_file=getattr(args, "output", None),
            manifest=getattr(args, "manifest", False),
            keys=getattr(args, "keys", None) or None,
        )

    if ocr_action == "rebuild":
        parallel_workers = 0 if getattr(args, "no_parallel", False) else max(1, int(getattr(args, "parallel", 4) or 4))
        return _run_ocr_rebuild(
            vault,
            keys=getattr(args, "keys", None) or None,
            all_papers=getattr(args, "all", False),
            status_filter=getattr(args, "status", None),
            dry_run=getattr(args, "dry_run", False),
            resume=getattr(args, "resume", False),
            parallel_workers=parallel_workers,
        )

    if key:
        logger.info("Processing specific key: %s", key)

    run_ocr = _get_run_ocr()
    selected_keys = {key} if key else None
    exit_code = run_ocr(
        vault,
        verbose=getattr(args, "verbose", False),
        no_progress=getattr(args, "no_progress", False),
        selected_keys=selected_keys,
    )

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
