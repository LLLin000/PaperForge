"""OCR command — unifies OCR run and diagnose."""

import argparse
import sys
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
    from paperforge.credentials import CredentialError as _CredentialError
    from paperforge.ocr_diagnostics import ocr_doctor

    try:
        result = ocr_doctor(config=None, live=live)
    except _CredentialError as exc:
        # #173 corrective: a backend fault (locked/unavailable/denied) is a
        # distinct diagnostic finding — never crashed and never disguised as
        # a missing key.
        from paperforge.commands.auth import _error_result as _cred_error_result

        failed = _cred_error_result("ocr.diagnose", exc)
        if json_output:
            print(failed.to_json())
        else:
            # Text-mode diagnose keeps its diagnostic shape — the backend
            # fault is the finding (level 1, distinct from a missing key).
            print("OCR Doctor — Level 1 diagnostic")
            print(f"Status: {failed.error.code if failed.error else 'error'}")
            print(f"Reason: {failed.error.message if failed.error else str(exc)}")
            print("Fix: run `paperforge auth status ocr` for remediation")
        return 1
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
    """#137 unified cooperative stop: one token fed by stdin
    PAPERFORGE_STOP + SIGINT + SIGTERM (shared core.cancellation)."""
    from paperforge.core.cancellation import make_cancellation_token

    return make_cancellation_token()



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
    """  # noqa: D205
    # #99-B: recover interrupted redo transactions before starting new work.
    # Dry-run must remain side-effect free — never consume recovery state
    # from a no-op probe.
    if not dry_run:
        from paperforge.worker.ocr import recover_redo_orphans

        recover_redo_orphans(vault)

    from paperforge.worker.ocr import ocr_redo_papers, redo_papers_for_keys

    if not keys:
        return ocr_redo_papers(vault, dry_run=dry_run, verbose=verbose, no_progress=no_progress)


    total = len(keys)
    # #168 T7 P0-5: a single paper's remote OCR is still a long task — every
    # non-dry-run keyed redo uses the same NDJSON stream.
    batch = not dry_run

    if batch:
        from paperforge.core.ndjson import emit_start

        emit_start("ocr.redo", total=total)
        _is_stopped, _restore_signal = _make_cooperative_stop()
    else:
        _is_stopped = lambda: False
        _restore_signal = lambda: None

    if dry_run:
        print(f"Would redo {total} paper(s):")
        for k in keys:
            print(f"  - {k}: would delete artifacts and re-run OCR")
        print("Dry-run: no changes made. Run without --dry-run to execute.")
        return 0

    # Track current for progress token
    _current = [0]

    def _progress_callback(key: str) -> None:
        _current[0] += 1
        from paperforge.core.ndjson import emit_progress

        emit_progress("ocr.redo", _current[0], total, item_id=key)

    def _stop_check() -> bool:
        return _is_stopped()

    try:
        result = redo_papers_for_keys(
            vault, keys,
            verbose=verbose,
            progress_callback=_progress_callback if batch else None,
            stop_check=_stop_check if batch else None,
        )
    except Exception as exc:  # noqa: BLE001 — exactly-one error terminal
        from paperforge.core.ndjson import emit_terminal
        from paperforge import __version__ as _PFV
        from paperforge.core.result import PFResult, PFError
        from paperforge.core.errors import ErrorCode as _EC

        if batch:
            emit_terminal("error", "ocr.redo", PFResult(
                ok=False, command="ocr redo", version=_PFV,
                error=PFError(code=_EC.INTERNAL_ERROR, message=str(exc)),
            ))
        _restore_signal()
        return 1

    success_keys = result.get("success_keys", [])
    failed_keys = result.get("failed_keys", [])
    worker_exit_code = result.get("exit_code", 0)
    # #137: human logs → stderr; stdout carries machine output only.
    if success_keys:
        print(f"Redo OCR done={len(success_keys)}: {', '.join(success_keys)}",
              file=sys.stderr, flush=True)
    if failed_keys:
        print(f"Redo OCR pending/failed={len(failed_keys)}: {', '.join(failed_keys)}",
              file=sys.stderr, flush=True)

    _real_stop = batch and _is_stopped() and _current[0] < total
    if _real_stop:
        print(f"Batch stopped (SIGINT) after {_current[0]} paper(s).", file=sys.stderr)

    if batch:
        from paperforge.core.ndjson import emit_terminal
        from paperforge import __version__ as _PFV
        from paperforge.core.result import PFResult

        if _real_stop:
            emit_terminal("cancelled", "ocr.redo",
                          PFResult(ok=False, command="ocr redo", version=_PFV))
        else:
            emit_terminal("result", "ocr.redo", PFResult(
                ok=not failed_keys,
                command="ocr redo",
                version=_PFV,
                data={"done": len(success_keys), "failed": len(failed_keys)},
            ))
    _restore_signal()

    if batch and _is_stopped() and _current[0] < total:
        return 130
    return worker_exit_code





def _collect_batch_unsettled(vault: Path, batch_id: str) -> list[str]:
    """G1: keys of papers whose meta.provider_batch_id == batch_id and are
    NOT settled — the exact set ocr resume re-attaches.  Settled papers of
    the batch are never re-OCR'd."""
    import json as _json

    from paperforge.worker.ocr import OCR_SETTLED_STATUSES

    ocr_root = vault / "System" / "PaperForge" / "ocr"
    if not ocr_root.exists():
        return []
    keys: list[str] = []
    for meta_dir in sorted(ocr_root.iterdir()):
        meta_path = meta_dir / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = _json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — corrupt meta has no batch
            continue
        if str(meta.get("provider_batch_id", "") or "") != batch_id:
            continue
        status = str(meta.get("ocr_status", "") or "").strip().lower()
        # M1.1 (owner review): a paper in submission_state=submitting is in
        # the crash window — the remote job MAY exist without a persisted
        # job_id.  Blindly re-submitting risks a double remote job, so
        # auto-resume EXCLUDES it (execution_unknown — operator inspects
        # via ocr status, which exposes submission_state).
        if str(meta.get("submission_state", "") or "") == "submitting":
            continue
        if status in OCR_SETTLED_STATUSES:
            continue
        keys.append(meta_dir.name)
    return keys


def _run_ocr_resume(vault: Path, batch_id: str, json_output: bool = False) -> int:
    """G1 (Control Plane Closure): re-attach an EXISTING OCR execution.

    Finds every paper whose meta.provider_batch_id == batch_id and is not
    settled, then runs the normal controller over exactly those keys with
    the SAME batch id — provider-done papers get fetched/settled,
    queued/running continue polling, failed papers resubmit (bounded,
    same logical batch).  This is the 'provider result fetched' recovery
    frontier: it never re-OCRs a settled paper."""
    import json as _json

    from paperforge.worker.ocr import run_ocr

    keys = _collect_batch_unsettled(vault, batch_id)
    if not keys:
        if json_output:
            print(
                _json.dumps(
                    {"batch": batch_id, "papers": [], "message": "no unfinished papers"},
                    ensure_ascii=False,
                )
            )
        else:
            print(f"No unfinished papers in batch {batch_id}.")
        return 0
    if json_output:
        print(
            _json.dumps(
                {"batch": batch_id, "papers": len(keys), "resuming": True},
                ensure_ascii=False,
            )
        )
    rc = run_ocr(vault, selected_keys=set(keys), batch_id=batch_id)
    return rc


def _run_ocr_status(vault: Path, json_output: bool = False, batch: str | None = None) -> int:
    """Live per-paper OCR job status (owner request 2026-08-16): show every
    active provider job — key, provider state, elapsed, job id — by querying
    the provider directly, WITHOUT running the OCR loop.  Lets an operator
    watch a batch's real-time progress and decide when to re-run the poll.

    Reads only meta.json (OCR-subsystem writer owns it); never mutates.
    ``batch`` filters to one logical execution (provider_batch_id)."""
    import json as _json

    from pathlib import Path as _Path

    from paperforge.worker._utils import pipeline_paths
    from paperforge.worker.ocr import _resolve_paddleocr_token

    paths = pipeline_paths(vault)
    ocr_root = paths.get("ocr")
    jobs: list[dict] = []
    if ocr_root and ocr_root.exists():
        for meta_dir in sorted(ocr_root.iterdir()):
            meta_path = meta_dir / "meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = _json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 — corrupt meta has no active job
                continue
            status = str(meta.get("ocr_status", "") or "").strip().lower()
            job_id = str(meta.get("ocr_job_id", "") or "")
            if batch and str(meta.get("provider_batch_id", "") or "") != batch:
                continue
            # Show every unsettled paper: active provider jobs (queued/
            # running) AND local pending/not-yet-submitted rows — the
            # operator wants per-paper state, not just in-flight jobs.
            if status in ("queued", "running", "pending"):
                jobs.append(
                    {
                        "key": meta_dir.name,
                        "job_id": job_id,
                        "status": status,
                        "started_at": str(meta.get("ocr_started_at", "") or ""),
                        "source_pdf": str(meta.get("source_pdf", "") or "")[:48],
                    }
                )
    if not jobs:
        if json_output:
            print(_json.dumps({"count": 0, "jobs": []}, ensure_ascii=False))
        else:
            print("No active OCR jobs.")
        return 0

    import os as _os
    import time as _time

    import requests as _requests

    token = _resolve_paddleocr_token(vault)
    job_url = _os.environ.get(
        "PADDLEOCR_JOB_URL", "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
    ).strip()
    now = _time.time()
    rows = []
    for j in jobs:
        provider_state = "?"
        if j["job_id"]:
            try:
                if token:
                    resp = _requests.get(
                        f"{job_url}/{j['job_id']}",
                        headers={"Authorization": f"bearer {token}"},
                        timeout=60,
                    )
                    if resp.status_code == 200:
                        provider_state = str(resp.json()["data"]["state"])
                    else:
                        provider_state = f"http_{resp.status_code}"
            except Exception as exc:  # noqa: BLE001 — status query is best-effort
                provider_state = f"err:{type(exc).__name__}"
        else:
            provider_state = "-"  # not yet submitted to the provider
        elapsed = ""
        if j["started_at"]:
            try:
                from datetime import datetime as _dt

                started = _dt.fromisoformat(j["started_at"])
                elapsed = f"{max(0, int(now - started.timestamp()))}s"
            except Exception:
                pass
        rows.append({**j, "provider_state": provider_state, "elapsed": elapsed})
    if json_output:
        print(_json.dumps({"count": len(rows), "jobs": rows}, ensure_ascii=False, default=str))
        return 0
    print(f"Active OCR jobs: {len(rows)}")
    header = f"{'Key':12s} {'Provider':10s} {'Local':9s} {'Elapsed':8s} {'Job ID':16s} {'Source'}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['key']:12s} {r['provider_state']:10s} {r['status']:9s} {r['elapsed']:8s} "
            f"{r['job_id'][:14]:16s} {r['source_pdf']}"
        )
    return 0


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

    #126 progress contract — every non-dry-run rebuild (including a single
    explicit key) emits the full token sequence:
      OCR_REBUILD_START:{total}
      OCR_REBUILD_PROGRESS:{current}:{total}:{key}
      OCR_REBUILD_RESULT:{key}:ok|failed|skipped
      OCR_REBUILD_DONE:{success}:{failed}:{skipped}

    Exit codes: all requested keys succeeded → 0; any failed/skipped requested
    key → 1; user stop → 130; --all with nothing needing rebuild → 0; explicit
    keys with no candidates → 1.
    """
    from paperforge.worker.ocr_maintenance import collect_maintenance_rows
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    rows = collect_maintenance_rows(vault)
    selected, reasons = _select_rebuild_keys(vault, rows, all_papers, status_filter, keys)

    # #126: explicit keys that cannot enter rebuild must surface as skipped —
    # never silently dropped (rc must be 1, DONE must count them).
    dropped: list[dict] = []
    if keys:
        selected_set = set(selected)
        dropped = [
            {"key": key, "reason": reasons.get(key, "not_rebuildable")}
            for key in keys
            if key not in selected_set
        ]

    if not selected:
        print("No papers matched for rebuild.", file=sys.stderr)
        if dropped:
            print(
                "Skipped requested key(s) not rebuildable: "
                + ", ".join(item["key"] for item in dropped),
                file=sys.stderr,
                flush=True,
            )
        if keys:
            # #137: stream chosen → exactly-one terminal (error), then EOF.
            from paperforge.core.ndjson import emit_terminal
            from paperforge import __version__ as _PFV
            from paperforge.core.result import PFResult

            emit_terminal("error", "ocr.rebuild", PFResult(
                ok=False, command="ocr rebuild", version=_PFV,
                error=__import__("paperforge").core.errors.PFError(
                    __import__("paperforge").core.errors.ErrorCode.ACTION_UNAVAILABLE,
                    "No papers matched for rebuild",
                ),
            ))
        # #126: an explicit key list that cannot enter rebuild is a failure.
        return 1 if keys else 0

    if dropped:
        print(
            "Skipped requested key(s) not rebuildable: "
            + ", ".join(item["key"] for item in dropped),
            file=sys.stderr,
            flush=True,
        )

    if resume:
        print("Note: OCR rebuild resume is now version/artifact based; .done markers are ignored.",
              file=sys.stderr)

    total = len(selected)

    if dry_run:
        print(f"Would rebuild {total} paper(s):")
        for k in selected:
            reason = reasons.get(k, "manual_override")
            print(f"  - {k}: {reason}")
        return 0

    from paperforge.worker._progress import progress_bar
    from paperforge.core.ndjson import emit_item_result, emit_progress, emit_start

    emit_start("ocr.rebuild", total=total)
    _count = 0

    def _on_progress(key: str, result: dict) -> None:
        nonlocal _count
        _count += 1
        status = result.get("status", "unknown")
        emit_progress("ocr.rebuild", _count, total, item_id=key)
        emit_item_result("ocr.rebuild", key, status)

    # Force sequential for cooperative stop; the parallel path now stops
    # between chunks (#126 G5), but serial remains the CLI default.
    parallel_workers = 0
    _is_stopped, _restore_signal = _make_cooperative_stop()

    def _stop_check() -> bool:
        return _is_stopped()

    try:
        result = run_derived_rebuild_for_keys(
            vault, selected,
            progress_bar=progress_bar,
            parallel=parallel_workers,
            on_progress=_on_progress,
            stop_check=_stop_check,
        )
    except Exception as exc:  # noqa: BLE001 — exactly-one error terminal
        from paperforge.core.ndjson import emit_terminal
        from paperforge import __version__ as _PFV
        from paperforge.core.result import PFResult, PFError
        from paperforge.core.errors import ErrorCode as _EC

        emit_terminal("error", "ocr.rebuild", PFResult(
            ok=False, command="ocr rebuild", version=_PFV,
            error=PFError(code=_EC.INTERNAL_ERROR, message=str(exc)),
        ))
        _restore_signal()
        return 1

    # #126: merge dropped explicit keys into skipped so the outcome is
    # complete and rc is non-zero.
    result["skipped"] = [*result["skipped"], *dropped]
    result["results"] = [
        *result["results"],
        *[{"key": d["key"], "status": "skipped", "reason": d["reason"]} for d in dropped],
    ]
    success_count = len(result["success_keys"])
    failed_count = len(result["failed_keys"])
    skipped_count = len(result["skipped"])
    print(f"Done. Rebuilt {success_count} paper(s).", file=sys.stderr, flush=True)
    _real_stop = _is_stopped() and _count < total
    from paperforge.core.ndjson import emit_terminal
    from paperforge import __version__ as _PFV
    from paperforge.core.result import PFResult

    _terminal = (
        ("cancelled", PFResult(ok=False, command="ocr rebuild", version=_PFV))
        if _real_stop
        else ("result", PFResult(
            ok=not (failed_count or skipped_count),
            command="ocr rebuild",
            version=_PFV,
            data={"rebuilt": success_count, "failed": failed_count, "skipped": skipped_count},
        ))
    )
    emit_terminal(_terminal[0], "ocr.rebuild", _terminal[1])
    _restore_signal()

    if _real_stop:
        return 130
    if failed_count or skipped_count:
        return 1
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
    live = getattr(args, "live", False)
    json_output = getattr(args, "json", False)
    keys: list[str] = getattr(args, "keys", None) or []

    # P0-4: canonical key normalization — CRLF / BOM / duplicates from
    # Windows scripts must not silently drop keys (recovery repeatedly hit
    # '\r'-suffixed keys that never matched).
    keys_file = getattr(args, "keys_file", None)
    if keys_file:
        try:
            keys.append(Path(keys_file).read_text(encoding="utf-8-sig"))
        except Exception as exc:  # noqa: BLE001
            print(f"Error: cannot read keys file {keys_file}: {exc}", file=sys.stderr)
            return 1
    from paperforge.core.keys import normalize_paper_keys

    keys = normalize_paper_keys(keys)

    # Backward compat: if subcommand was "doctor", diagnose
    ocr_action = getattr(args, "ocr_action", None)
    if ocr_action == "doctor" or diagnose_only:
        return _diagnose(vault, live=live, json_output=json_output)

    import sys as _sys

    from paperforge.credentials import CredentialError as _CredentialError

    try:
        return _run_ocr_dispatch(args, vault, json_output, ocr_action, keys, diagnose_only)
    except _CredentialError as exc:
        from paperforge.commands.auth import _error_result as _cred_error_result

        result = _cred_error_result("ocr.run", exc)
        print(result.to_json() if json_output else result.error.message, file=_sys.stderr if not json_output else _sys.stdout)
        return 1


def _run_ocr_dispatch(args, vault, json_output, ocr_action, keys, diagnose_only) -> int:

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

    if ocr_action == "pipeline-versions":
        return _run_ocr_pipeline_versions(vault, json_output=json_output)

    if ocr_action == "status":
        return _run_ocr_status(vault, json_output=json_output, batch=getattr(args, "batch", None))

    if ocr_action == "resume":
        batch_id = getattr(args, "batch", None)
        if not batch_id:
            print("Error: ocr resume requires --batch <id>", file=sys.stderr)
            return 2
        return _run_ocr_resume(vault, batch_id, json_output=json_output)

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

    if keys:
        logger.info("Processing specific keys: %s", keys)

    run_ocr = _get_run_ocr()
    selected_keys: set | None = set(keys) if keys else None

    # #174 RC: whole-queue ocr.run is a long task — the TS controller parses
    # the #137 NDJSON stream.  Without this stream the controller's
    # fail-closed parser reports "EOF without terminal event" even on a
    # successful run (contract break).  json mode keeps the single PFResult.
    _stream = not json_output and ocr_action in (None, "run") and not diagnose_only
    if _stream:
        from paperforge.core.cancellation import make_cancellation_token
        from paperforge.core.ndjson import emit_progress, emit_start, emit_terminal

        emit_start("ocr.run")
        _is_stopped, _restore = make_cancellation_token()
        _current = [0]

        def _progress(key: str) -> None:
            _current[0] += 1
            emit_progress("ocr.run", _current[0], len(selected_keys or ()), item_id=key)
    else:
        _is_stopped, _restore = (lambda: False), (lambda: None)
        _progress = None

    def _finish_stream(exit_code: int) -> None:
        if not _stream:
            return
        _restore()
        if exit_code == 130:
            emit_terminal("cancelled", "ocr.run", PFResult(ok=False, command="ocr run", version=__version__))
        else:
            emit_terminal(
                "result" if exit_code == 0 else "error",
                "ocr.run",
                PFResult(ok=exit_code == 0, command="ocr run", version=__version__),
            )

    try:
        exit_code = run_ocr(
            vault,
            verbose=getattr(args, "verbose", False),
            no_progress=getattr(args, "no_progress", False),
            selected_keys=selected_keys,
            stop_check=_is_stopped,
            progress_callback=_progress,
        )
    except Exception as exc:  # noqa: BLE001 — exactly-one error terminal
        if _stream:
            _restore()
            emit_terminal(
                "error",
                "ocr.run",
                PFResult(
                    ok=False,
                    command="ocr run",
                    version=__version__,
                    error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
                ),
            )
        return 1
    _finish_stream(exit_code)

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

    if exit_code == 130:
        return 130

    # Auto-diagnose after successful run (new unified behavior)
    if exit_code == 0 and ocr_action is None and not diagnose_only and not keys:
        logger.info("Running post-OCR diagnostic...")
        try:
            diag_code = _diagnose(vault, live=False)
            if diag_code != 0:
                logger.warning("Post-OCR diagnostic found issues, but OCR completed successfully.")
        except Exception as e:
            logger.warning("Auto-diagnose failed: %s", e)

    return exit_code

def _run_ocr_pipeline_versions(vault: Path, *, json_output: bool) -> int:
    """#148 detail surface: per-paper OCR pipeline versions."""
    from paperforge.commands.probe import paper_pipeline_versions
    from paperforge.worker.ocr_maintenance import collect_maintenance_rows

    rows = collect_maintenance_rows(vault)
    versions = paper_pipeline_versions(vault, rows)
    result = PFResult(
        ok=True,
        command="ocr pipeline-versions",
        version=__import__("paperforge", fromlist=["__version__"]).__version__,
        data={"total": len(versions), "versions": versions},
    )
    print(result.to_json() if json_output else f"{len(versions)} papers")
    return 0
