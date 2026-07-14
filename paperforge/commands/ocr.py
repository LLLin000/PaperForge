"""OCR command — unifies OCR run and diagnose."""

import argparse
import json
import signal
from collections.abc import Callable
import logging
from pathlib import Path

from paperforge import __version__
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult

from paperforge.worker.ocr_artifacts import artifact_paths_for_root
from paperforge.worker.ocr_versions import classify_version_state, compute_structured_hash, expected_derived_payload
from paperforge.worker.ocr_maintenance import _can_rebuild
from paperforge.core.io import read_json, write_json

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


def _make_cooperative_stop() -> tuple[Callable[[], bool], Callable[[], None]]:
    """Install cooperative stop mechanisms: SIGINT handler + stdin reader.

    SIGINT (POSIX/terminal): sets flag.
    Stdin line "PAPERFORGE_STOP": daemon reader thread sets flag
      (reliable on Windows where SIGINT can't be caught in subprocesses).

    Returns (is_stopped, restore):
        is_stopped(): returns True if stop was requested
        restore(): restores original SIGINT handler
    """
    import threading as _threading

    _flag: list[bool] = [False]
    _reader_active: list[bool] = [True]

    # ── SIGINT handler (POSIX/terminal) ──
    def _handler(_signum: int, _frame: object) -> None:
        _flag[0] = True

    _old = signal.signal(signal.SIGINT, _handler)

    # ── Stdin reader daemon thread (Windows-reliable) ──
    def _stdin_reader() -> None:
        import sys as _sys
        try:
            while _reader_active[0]:
                line = _sys.stdin.readline()
                if not line:  # EOF (pipe closed)
                    break
                if line.strip() == "PAPERFORGE_STOP":
                    _flag[0] = True
                    break
        except (OSError, ValueError, AttributeError, RuntimeError):
            pass  # stdin unavailable in testing/headless

    _reader_thread = _threading.Thread(target=_stdin_reader, daemon=True)
    _reader_thread.start()

    def _restore() -> None:
        _reader_active[0] = False
        signal.signal(signal.SIGINT, _old)

    return (lambda: _flag[0], _restore)



def _run_ocr_redo(vault: Path, keys: list[str] | None = None, dry_run: bool = False,
                   verbose: bool = False, no_progress: bool = False) -> int:
    """Re-run OCR for papers.

    If keys provided, delegate to redo_papers_for_keys which handles the
    full artifact-delete + OCR run + post-check cycle per paper, supporting
    per-paper progress tokens and cooperative stop.

    If no keys, scan for ocr_redo: true papers (legacy behavior).

    Progress tokens (multi-key non-dry-run only):
      OCR_REDO_START:{total}
      OCR_REDO_PROGRESS:{current}:{total}:{key}
      OCR_REDO_DONE

    Cooperative stop: SIGINT sets flag checked between papers.
    """
    from paperforge.worker.ocr import ocr_redo_papers, redo_papers_for_keys

    if not keys:
        return ocr_redo_papers(vault, dry_run=dry_run, verbose=verbose, no_progress=no_progress)


    total = len(keys)
    batch = total > 1 and not dry_run

    if batch:
        print(f"OCR_REDO_START:{total}", flush=True)
        _is_stopped, _restore_signal = _make_cooperative_stop()
    else:
        _is_stopped = lambda: False
        _restore_signal = lambda: None

    if dry_run:
        print(f"Would redo {total} paper(s):")
        for k in keys:
            print(f"  - {k}: would delete artifacts and re-run OCR")
        print("Dry-run: no changes made. Run without --dry-run to execute.")
        if batch:
            print(f"OCR_REDO_DONE", flush=True)
        return 0

    # Track current for progress token
    _current = [0]

    def _progress_callback(key: str) -> None:
        _current[0] += 1
        print(f"OCR_REDO_PROGRESS:{_current[0]}:{total}:{key}", flush=True)

    def _stop_check() -> bool:
        return _is_stopped()

    try:
        result = redo_papers_for_keys(
            vault, keys,
            verbose=verbose,
            progress_callback=_progress_callback if batch else None,
            stop_check=_stop_check if batch else None,
        )

        success_keys = result.get("success_keys", [])
        failed_keys = result.get("failed_keys", [])
        worker_exit_code = result.get("exit_code", 0)
        if success_keys:
            print(f"Redo OCR done={len(success_keys)}: {', '.join(success_keys)}", flush=True)
        if failed_keys:
            print(f"Redo OCR pending/failed={len(failed_keys)}: {', '.join(failed_keys)}", flush=True)

        if batch and _is_stopped():
            print(f"Batch stopped (SIGINT) after {_current[0]} paper(s).")

        if batch:
            print(f"OCR_REDO_DONE", flush=True)
    finally:
        _restore_signal()

    if batch and _is_stopped():
        return 130
    return worker_exit_code





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
        dicts = []
        for r in rows:
            d = r.to_dict()
            need, _reason = _needs_derived_rebuild(vault, r.key)
            d["needs_derived_rebuild"] = need
            dicts.append(d)
        payload = _json.dumps(dicts, ensure_ascii=False, default=str)
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
    header = f"{'Key':12s} {'Title':42s} {'Status':8s} {'Health':6s} {'Hash':12s} {'Ver':4s} {'Time':11s} {'Pg':>3s} {'Blk':>4s} {'Act'}"
    print(header)
    print("-" * len(header))

    for r in rows:
        act = r.recommended_action or "-"
        h = (r.structured_content_hash[:12] if r.structured_content_hash else "-")
        print(
            f"{r.key:12s} {r.title:42s} {r.status:8s} {r.health:6s} "
            f"{h:12s} {r.version:4s} {r.finished_at:11s} {r.pages:>3d} {r.blocks:>4d} {act}"
        )


def _needs_derived_rebuild(vault: Path, key: str) -> tuple[bool, str]:
    """检测一篇论文是否需要重建。返回 (need, reason)。"""
    from paperforge.worker._utils import pipeline_paths

    ocr_root = Path(pipeline_paths(vault)["ocr"])
    artifacts = artifact_paths_for_root(ocr_root, key)
    paper_dir = artifacts.paper_root

    if not artifacts.meta_json.exists():
        return False, "no_meta"

    meta = read_json(artifacts.meta_json)

    has_raw = artifacts.blocks_raw.exists()
    has_source_meta = artifacts.source_metadata.exists()
    if not _can_rebuild(meta, has_raw, has_source_meta):
        return False, "cannot_rebuild"
    # ── Legacy OCR detection ──
    has_structured = artifacts.blocks_structured.exists()
    if not has_structured and not meta.get("derived_version"):
        return False, "legacy_ocr"
    # ── Two-tier content-hash detection ──
    content_hash = meta.get("structured_content_hash")
    if content_hash is not None:
        blocks_path = artifacts.blocks_structured
        if not blocks_path.exists():
            return True, "missing:blocks.structured.jsonl"
        try:
            stat = blocks_path.stat()
            stored_mtime = meta.get("structured_mtime")
            stored_size = meta.get("structured_size")

            # Tier 1: stat check — skip I/O when mtime+size unchanged
            if stored_mtime == stat.st_mtime and stored_size == stat.st_size:
                return False, "current"

            # Tier 2: hash check
            current_hash = compute_structured_hash(vault, key)
            if current_hash == content_hash:
                # False alarm — mtime changed but content identical
                meta["structured_mtime"] = stat.st_mtime
                meta["structured_size"] = stat.st_size
                write_json(artifacts.meta_json, meta)
                return False, "current"

            return True, "content_hash_changed"
        except OSError:
            # Stat failed — fall through to version constants
            pass

    # ── 版本检测（运行时比较，不依赖 meta.derived_stale）──
    state = classify_version_state(
        meta,
        expected_raw={},
        expected_derived=expected_derived_payload(),
    )
    if state["derived_stale"]:
        return True, "version_mismatch"

    # 产物完整性检测
    required = [
        "structure/blocks.structured.jsonl",
        "render/render-map.json",
        "index/structure-tree.json",
        "index/role-index.json",
        "fulltext.md",
        "health/ocr_health.json",
    ]
    for rel in required:
        if not (paper_dir / rel).exists():
            return True, f"missing:{rel.split('/')[-1]}"

    return False, "current"


def _select_rebuild_keys(vault, rows, all_papers, status_filter, keys):
    """确定需要重建的论文列表。

    --all: 只选 _needs_derived_rebuild()=True 的论文
    --status: 按用户指定状态，不过滤版本
    explicit keys: manual override，不过滤版本

    Returns (selected_keys: list[str], reasons: dict[str, str])
    """
    by_key = {r.key: r for r in rows}

    if all_papers:
        selected = []
        reasons = {}
        for r in rows:
            if not r.can_rebuild:
                continue
            need, reason = _needs_derived_rebuild(vault, r.key)
            if need:
                selected.append(r.key)
                reasons[r.key] = reason
        return selected, reasons

    if status_filter:
        selected = [r.key for r in rows if r.status == status_filter and r.can_rebuild]
        return selected, {}

    if keys:
        selected = [k for k in keys if k in by_key and by_key[k].can_rebuild]
        return selected, {}

    return [], {}

def _run_ocr_rebuild(
    vault: Path,
    keys: list[str] | None = None,
    all_papers: bool = False,
    status_filter: str | None = None,
    dry_run: bool = False,
    resume: bool = False,
    parallel_workers: int = 4,
) -> int:
    """Rebuild OCR-derived artifacts from existing raw blocks.

    Progress tokens (multi-key non-dry-run only):
      OCR_REBUILD_START:{total}
      OCR_REBUILD_PROGRESS:{current}:{total}:{key}
      OCR_REBUILD_DONE
    """
    from paperforge.worker.ocr_maintenance import collect_maintenance_rows
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    rows = collect_maintenance_rows(vault)
    selected, reasons = _select_rebuild_keys(vault, rows, all_papers, status_filter, keys)

    if not selected:
        print("No papers matched for rebuild.")
        return 0

    if resume:
        print("Note: OCR rebuild resume is now version/artifact based; .done markers are ignored.")

    total = len(selected)
    batch = total > 1 and not dry_run

    if dry_run:
        print(f"Would rebuild {total} paper(s):")
        for k in selected:
            reason = reasons.get(k, "manual_override")
            print(f"  - {k}: {reason}")
        return 0

    from paperforge.worker._progress import progress_bar

    if batch:
        print(f"OCR_REBUILD_START:{total}", flush=True)
        _count = 0
        def _on_progress(key: str) -> None:
            nonlocal _count
            _count += 1
            print(f"OCR_REBUILD_PROGRESS:{_count}:{total}:{key}", flush=True)
        # Force sequential for cooperative stop; parallel pool can't stop mid-batch
        parallel_workers = 0
        _is_stopped, _restore_signal = _make_cooperative_stop()
        def _stop_check() -> bool:
            return _is_stopped()
    else:
        _on_progress = None  # type: ignore[assignment]
        _is_stopped = lambda: False
        _restore_signal = lambda: None
        _stop_check = None

    try:
        result = run_derived_rebuild_for_keys(
            vault, selected,
            progress_bar=progress_bar,
            parallel=parallel_workers,
            on_progress=_on_progress,
            stop_check=_stop_check,
        )
        count = result.get("rebuild_count", 0)
        print(f"Done. Rebuilt {count} paper(s).")
        if batch:
            print(f"OCR_REBUILD_DONE", flush=True)
    finally:
        _restore_signal()
    return 0 if not _is_stopped() else 130



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
