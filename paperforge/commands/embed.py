from __future__ import annotations

import argparse
import contextlib
import logging
import os
import shutil
import sys
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
import sqlite3

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.embedding import (
    delete_paper_vectors,
    get_embed_status,
    mark_vector_build_state,
    read_vector_build_state,
)
from paperforge.embedding._chroma import delete_paper_vectors_in_conn
from paperforge.embedding.build_target import BuildTarget, ShadowBuild, verify_candidate
from paperforge.embedding.dim_detect import ensure_vec_tables
from paperforge.embedding.builder import (
    PaperEmbeddingJob,
    encode_paper_job,
    get_body_units_for_embedding,
    get_object_units_for_embedding,
    prepare_payloads_for_entry,
    write_encoded_payload,
    write_encoded_payload_to_conn,
)
from paperforge.embedding.preflight import _preflight_check
from paperforge.memory.db import WriterLock, ensure_vec_extension, get_connection, get_memory_db_path, open_live_reader
from paperforge.memory.schema import ensure_schema
from paperforge.retrieval.manifest import RETRIEVAL_POLICY_VERSION, compute_body_units_hash, compute_object_units_hash
from paperforge.worker._progress import progress_bar
from paperforge.worker.asset_index import read_index


def _has_body_units_in_db(vault: Path, key: str) -> bool:
    """Check if paper has body_units in the memory DB."""
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return False
    with open_live_reader(vault, db_path) as conn:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM body_units WHERE paper_id=? AND indexable=1",
            (key,),
        ).fetchone()[0]
        return cnt > 0


def _has_object_units_in_db(vault: Path, key: str) -> bool:
    """Check if paper has object_units in the memory DB."""
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return False
    with open_live_reader(vault, db_path) as conn:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM object_units WHERE paper_id=? AND indexable=1",
            (key,),
        ).fetchone()[0]
        return cnt > 0


def _stop_control_path(vault: Path) -> Path:
    """Control-plane sidecar: stop requests never touch the live DB (P0-5) —
    a publish swaps the whole DB, and stop must stay usable while the build
    holds the writer lock."""
    return get_memory_db_path(vault).with_name("paperforge.embed-control.json")


def _stop_requested(vault: Path, build_pid: int) -> bool:
    """True when a stop request for THIS build process exists."""
    import json as _json

    p = _stop_control_path(vault)
    try:
        if not p.exists():
            return False
        data = _json.loads(p.read_text(encoding="utf-8"))
        return data.get("target_pid", 0) == build_pid and bool(data.get("stop_requested"))
    except Exception:
        return False


def _clear_stop_request(vault: Path) -> None:
    p = _stop_control_path(vault)
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass


def _pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running (cross-platform)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import subprocess
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                timeout=5,
            )
            return str(pid) in r.stdout.decode("utf-8", errors="replace")
        except Exception:
            return False
    try:
        os.kill(pid, 0)  # signal 0 = existence probe, no signal sent
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but owned by another user
    except Exception:
        return False



logger = logging.getLogger(__name__)

PR9B_MAX_WORKERS = 4

# P0-1: bumped when the persisted embedding identity gains fields — legacy
# libraries (built before recording) are rebuilt once so endpoint/model/
# dimension are stored and future comparisons are meaningful.
VECTOR_IDENTITY_VERSION = 1


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    sub = getattr(args, "embed_subcommand", "build")

    if sub == "status":
        status = get_embed_status(vault, probe=getattr(args, "probe", False))
        status["build_state"] = read_vector_build_state(vault)

        _dep_missing = []
        try:
            import openai  # noqa: F401
        except ImportError:
            _dep_missing.append("openai")
        try:
            import sqlite_vec  # noqa: F401
        except ImportError:
            _dep_missing.append("sqlite_vec")

        result = PFResult(ok=True, command="embed status", version=PF_VERSION, data=status)
        if args.json:
            print(result.to_json())
        else:
            for k, v in status.items():
                if k == "build_state":
                    print(f"  {k}: {v['status']} ({v['current']}/{v['total']})")
                else:
                    print(f"  {k}: {v}")
        return 0

    if sub == "stop":
        state = read_vector_build_state(vault)
        pid = state.get("pid", 0)
        _st = state.get("status", "")
        if pid and _st in ("running", "stopping"):
            # P0-5: stop is control-plane — write a sidecar file instead of
            # touching the live DB (the build holds the writer lock, and a
            # publish would overwrite an in-DB signal anyway).
            import json as _json
            import time as _time

            _ctrl = _stop_control_path(vault)
            try:
                # P0-5: atomic sidecar write (tmp + os.replace) so a reader
                # never observes a half-written control file.
                _ctrl.parent.mkdir(parents=True, exist_ok=True)
                _tmp = _ctrl.with_name(_ctrl.name + ".tmp")
                _tmp.write_text(
                    _json.dumps({
                        "stop_requested": True,
                        "target_pid": pid,
                        "requested_at": __import__("datetime").datetime.now(
                            __import__("datetime").timezone.utc
                        ).isoformat(),
                    }),
                    encoding="utf-8",
                )
                os.replace(str(_tmp), str(_ctrl))
            except OSError:
                pass
            # Wait for build process to notice the sidecar and exit (8s)
            _deadline = _time.time() + 8.0
            while _time.time() < _deadline:
                if not _pid_alive(pid):
                    break
                _time.sleep(0.2)
            # Force-kill if still alive after timeout
            if _pid_alive(pid):
                import signal
                with contextlib.suppress(Exception):
                    os.kill(pid, signal.SIGTERM)
            _wait_deadline = _time.time() + 3.0
            while _time.time() < _wait_deadline:
                if not _pid_alive(pid):
                    break
                _time.sleep(0.2)
            if _pid_alive(pid):
                # P0-5: do NOT claim stopped while the build still runs —
                # keep the sidecar so the build stops at its next checkpoint.
                result = PFResult(
                    ok=False,
                    command="embed stop",
                    version=PF_VERSION,
                    error=PFError(
                        code=ErrorCode.INTERNAL_ERROR,
                        message=f"Unable to stop embed build (pid {pid} still running)",
                    ),
                )
                if args.json:
                    print(result.to_json())
                else:
                    print(
                        f"Unable to stop embed build (pid {pid} still running). "
                        "Stop request left in place.",
                        file=sys.stderr,
                    )
                return 1
            # Build exited: settle to idle (writer lock is free now).  Narrow
            # race: the build may have COMPLETED between the last stop-check
            # and its exit — don't downgrade a successful build to idle.
            try:
                with WriterLock(vault, timeout=30):
                    _latest = read_vector_build_state(vault)
                    if _latest.get("status") == "completed" and _latest.get("pid") == 0:
                        _settled = "completed_before_stop"
                    else:
                        _current = _latest.get("current", state.get("current", 0))
                        mark_vector_build_state(vault, status="idle", current=_current, pid=0, message="")
                        _settled = "stopped"
            except Exception:
                _settled = "stopped"
            _clear_stop_request(vault)
            result = PFResult(ok=True, command="embed stop", version=PF_VERSION, data={"state": _settled})
        else:
            _clear_stop_request(vault)
            result = PFResult(ok=True, command="embed stop", version=PF_VERSION, data={"state": "idle"})
        if args.json:
            print(result.to_json())
        else:
            if result.data["state"] == "stopped":
                msg = "Build stopped."
            elif result.data["state"] == "completed_before_stop":
                msg = "Build already completed before stop request."
            else:
                msg = "No active build."
            print(msg)
        return 0


    if sub == "migrate":
        from paperforge.embedding._chroma import migrate_chroma_to_vec0

        count = migrate_chroma_to_vec0(vault)

        result = PFResult(ok=True, command="embed migrate", version=PF_VERSION, data={"migrated": count})
        if args.json:
            print(result.to_json())
        else:
            print(f"Migrated {count} vectors from ChromaDB to vec0")
        return 0

    # Build

    # Read plugin settings for preflight
    settings: dict = {}
    dc_json = vault / ".obsidian" / "plugins" / "paperforge" / "data.json"
    if dc_json.exists():
        try:
            import json

            settings = json.loads(dc_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    preflight = _preflight_check(vault, settings)
    if not preflight["ok"]:
        result = PFResult(
            ok=False,
            command="embed-build",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.VALIDATION_ERROR, message=preflight["error"]),
            data={"fix": preflight.get("fix", "")},
        )
        if args.json:
            print(result.to_json())
        else:
            print(f"Error: {preflight['error']}", file=sys.stderr)
            print(f"Fix: {preflight['fix']}", file=sys.stderr)
        return 1

    envelope = read_index(vault)
    if not envelope:
        result = PFResult(
            ok=False,
            command="embed build",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.PATH_NOT_FOUND, message="Canonical index not found. Run paperforge sync first."
            ),
        )
        print(result.to_json() if args.json else result.error.message, file=sys.stderr if not args.json else sys.stdout)
        return 1

    items = envelope if isinstance(envelope, list) else envelope.get("items", [])
    done_papers = [e for e in items if e.get("ocr_status") == "done"]

    # Resolve DB path unconditionally — shadow/force paths need it even when
    # resume is False (regression: was only assigned inside `if resume:`).
    _db_path = get_memory_db_path(vault)

    total = len(done_papers)
    print(f"EMBED_START:{total}", flush=True)

    import gc as _gc
    import os as _os

    _now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat

    papers_embedded = 0
    chunks_embedded = 0
    papers_skipped = 0
    resume = getattr(args, "resume", False)

    from paperforge.embedding._config import get_api_model

    _current_model = get_api_model(vault)

    # P0-1: cleanup state initialized BEFORE the lock and the outer try —
    # resume/model checks may raise, and the outer handler unconditionally
    # references these (an UnboundLocalError would mask the real error).
    _shadow: ShadowBuild | None = None
    _candidate_conn = None
    _rebuild_backup_path: Path | None = None
    # P1-2: set by the prepare step from the dimension detection that built
    # the tables; verification MUST use this, not candidate-DDL re-reading.
    _expected_dim: int = 0
    # P1-1: per-collection expected vector counts, accumulated per payload.
    _expected_counts: dict[str, int] = {"fulltext": 0, "body": 0, "objects": 0}

    # D2: writer lock acquired ONCE before ANY resume/model checks (they
    # open rw connections and may mutate schema), held through verify and
    # publish.  Released by the outer finally on every path.
    _write_lock = WriterLock(vault)
    _write_lock.__enter__()
    try:
        # P0-5: clear any stale stop request (from a previous build) that
        # does not target this process before starting.
        _clear_stop_request(vault)
        if resume:
            build_state = read_vector_build_state(vault)

            # 门一：stale running state 检测
            if build_state.get("status") == "running":
                stale = False
                pid = build_state.get("pid", 0)
                if not pid or not _pid_alive(pid):
                    stale = True
                else:
                    started = build_state.get("started_at", "")
                    if started:
                        try:
                            dt = __import__("datetime").datetime.fromisoformat(started)
                            if (
                                __import__("datetime").datetime.now(__import__("datetime").timezone.utc) - dt
                            ).total_seconds() > 43200:
                                stale = True
                        except Exception:
                            pass
                if stale:
                    msg = "Previous build appears stale (crashed?). Recovering and rebuilding from scratch."
                    print(msg)
                    mark_vector_build_state(vault, status="idle", current=0, pid=0)
                    resume = False
            # 门二：no vec0 rows → fresh build（不是 error）

            _db_path = get_memory_db_path(vault)
            _any_rows = False
            if _db_path.exists():
                _conn = get_connection(_db_path)
                try:
                    ensure_vec_extension(_conn)
                    ensure_schema(_conn)
                    for _mt in ("vec_fulltext_meta", "vec_body_meta", "vec_objects_meta"):
                        _r = _conn.execute(f"SELECT COUNT(*) AS cnt FROM {_mt}").fetchone()
                        if _r and _r["cnt"] > 0:
                            _any_rows = True
                            break
                except Exception:
                    pass
                finally:
                    _conn.close()
            if not _any_rows:
                resume = False
            else:
                # 门三：过三道门后，正常 model check
                stored_model = build_state.get("model", "")
                if stored_model and _current_model and stored_model != _current_model:
                    msg = f"Model changed: {stored_model} -> {_current_model}. Re-embedding all papers."
                    if not getattr(args, "json", False):
                        print(msg)
                    resume = False

        # P0-2: full rebuild must never honor resume — the candidate's
        # vector tables are cleared, so a hash-skip would publish a DB
        # missing those papers' vectors.  Force wins over resume at both the
        # CLI (mutually exclusive group) and programmatic call sites.
        if args.force:
            resume = False
        _force_rebuild = args.force or (resume is False and getattr(args, "resume", False))
        # D5: full rebuilds (force / model change / resume reset) use shadow target.
        # P1: embedding identity is (provider endpoint, model) — a config
        # switch of EITHER must route through shadow.  A plain `embed build`
        # after a model/endpoint change would otherwise let ensure_vec_tables
        # resize vec0 in place on the live DB and expose an empty/partial
        # window mid-build.
        from paperforge.embedding._config import (
            DEFAULT_OPENAI_BASE_URL,
            get_effective_api_base_url,
        )

        _bs = read_vector_build_state(vault)
        _stored_model = _bs.get("model", "")
        _stored_endpoint = _bs.get("vector_provider_endpoint", "")
        # P0-1: compare the EFFECTIVE endpoint (empty config = OpenAI
        # default) with NO truthiness guard — default→custom migration must
        # trigger shadow, and an empty stored value (old build before
        # endpoint recording) counts as "different" when a custom endpoint
        # is now configured.
        _current_endpoint = get_effective_api_base_url(vault)
        _stored_endpoint_norm = (_stored_endpoint or DEFAULT_OPENAI_BASE_URL).rstrip("/")
        _embedding_identity_changed = bool(
            _stored_model and _current_model and _stored_model != _current_model
        ) or (_stored_endpoint_norm != _current_endpoint)
        if _embedding_identity_changed and not getattr(args, "json", False):
            print(
                f"Embedding identity changed: "
                f"{_stored_model}@{_stored_endpoint_norm} -> "
                f"{_current_model}@{_current_endpoint}. Re-embedding all papers."
            )
        # P0-3/P1-1: a live vector-layout mismatch must route through shadow —
        # an in-place recreate would destroy live vectors + orphan meta rows.
        # Compare the live layout against the STORED build dimension via the
        # unified inspect_vector_layout contract (six tables + three dims),
        # without an API probe (that would add a network call to every build).
        _vec_layout_incompatible = False
        _stored_dim = _bs.get("vector_dimension", 0)
        if _db_path.exists() and _stored_dim:
            try:
                from paperforge.embedding.dim_detect import inspect_vector_layout

                _lc = sqlite3.connect(f"file:{_db_path.as_posix()}?mode=ro", uri=True)
                try:
                    _layout = inspect_vector_layout(_lc, int(_stored_dim))
                    _vec_layout_incompatible = not _layout.compatible
                finally:
                    _lc.close()
            except Exception:
                # P0-2: fail-closed — an unreadable layout must route to
                # shadow, never be treated as compatible.
                _vec_layout_incompatible = True
        # Legacy libraries (built before identity recording) have no
        # vector_identity_version — rebuild them once so endpoint/model are
        # persisted and future comparisons are meaningful.
        _identity_version = _bs.get("vector_identity_version", 0)
        _legacy_identity = bool(
            _identity_version != VECTOR_IDENTITY_VERSION
            and _db_path.exists()
            and _vec_layout_incompatible is False
        )
        requires_shadow = (
            _force_rebuild
            or _embedding_identity_changed
            or _vec_layout_incompatible
            or _legacy_identity
        ) and _db_path.exists()
        # P0-2: ANY full shadow rebuild clears the candidate's vector tables —
        # resume hash-skips would leave those papers' vectors missing from the
        # published DB (chunks_embedded=0, verifier passes, empty library
        # published).  Shadow ⇒ resume off, for every trigger, not just force.
        if requires_shadow:
            resume = False

        if requires_shadow:
            # Maintenance mode message (D2b).
            if not getattr(args, "json", False):
                print(
                    "Maintenance mode: OCR syncs and memory updates are paused "
                    "until the rebuild completes."
                )
            _target = BuildTarget(
                source_path=_db_path,
                vector_path=_db_path.with_suffix(".db.build"),
            )
            _shadow = ShadowBuild(_target)
            # D6: unconditional stale-candidate cleanup (no build_state dependency)
            _shadow.cleanup_stale()
            _shadow.prepare()
            _candidate_conn = _shadow.candidate_conn()
            try:
                # 1. Consistent snapshot: live → candidate via online backup API
                import sqlite3 as _sqlite3
                _src_conn = _sqlite3.connect(str(_db_path))
                _dst_conn = _sqlite3.connect(str(_target.vector_path))
                try:
                    _src_conn.backup(_dst_conn, pages=64)
                finally:
                    _src_conn.close()
                    _dst_conn.close()

                # 2. Clear vec tables in candidate; recreate at model dim
                ensure_vec_extension(_candidate_conn)
                for _t in ("vec_fulltext_meta", "vec_body_meta", "vec_objects_meta",
                           "vec_fulltext", "vec_body", "vec_objects"):
                    _candidate_conn.execute(f'DROP TABLE IF EXISTS "{_t}"')
                ensure_schema(_candidate_conn)
                # P1-2: the dimension comes FROM the model detection that
                # actually built the tables — never re-derive it from the
                # candidate DDL later (that would be self-verification).
                _expected_dim = ensure_vec_tables(
                    _candidate_conn, vault, allow_recreate=True
                )
                _candidate_conn.commit()
                _shadow.building()
            except Exception:
                _shadow.abort()
                if _write_lock:
                    _write_lock.__exit__(None, None, None)
                raise
        elif _force_rebuild:
            # Conservative in-place rebuild with restorable backup (fallback).
            # (Shadow build is the default; this is the "inplace" strategy.)
            import datetime as _dt_mod
            _ts = _dt_mod.datetime.now(_dt_mod.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _rebuild_backup_path = _db_path.with_name(f"paperforge.pre-rebuild-{_ts}.db")

            import sqlite3 as _sqlite3
            _src_conn = _sqlite3.connect(str(_db_path))
            _dst_conn = _sqlite3.connect(str(_rebuild_backup_path))
            try:
                _src_conn.backup(_dst_conn, pages=64)
            finally:
                _src_conn.close()
                _dst_conn.close()

            _conn = get_connection(_db_path)
            try:
                ensure_vec_extension(_conn)
                for _t in ("vec_fulltext_meta", "vec_body_meta", "vec_objects_meta",
                           "vec_fulltext", "vec_body", "vec_objects"):
                    _conn.execute(f'DROP TABLE IF EXISTS "{_t}"')
                ensure_schema(_conn)
                _expected_dim = ensure_vec_tables(_conn, vault, allow_recreate=True)
                _conn.commit()
            except Exception:
                _conn.close()
                if _rebuild_backup_path and _rebuild_backup_path.exists():
                    _os.replace(str(_rebuild_backup_path), str(_db_path))
                raise
            _conn.close()

        mark_vector_build_state(
            vault,
            status="running",
            current=0,
            total=total,
            paper_id="",
            started_at=_now(),
            finished_at="",
            message="",
            pid=_os.getpid(),
            model=_current_model,
            vector_provider_endpoint=_current_endpoint,
            vector_identity_version=VECTOR_IDENTITY_VERSION,
            mode=get_embed_status(vault)["mode"],
        )

        try:
            max_workers = PR9B_MAX_WORKERS
            window_size = max_workers * 4

            processed_count = 0
            papers_embedded = 0
            papers_skipped = 0
            chunks_embedded = 0
            in_flight: dict = {}

            def _submit_job(job: PaperEmbeddingJob, pool):
                fut = pool.submit(encode_paper_job, vault, job)
                in_flight[fut] = job

            def _complete_one(pool, block: bool = True) -> bool:
                nonlocal processed_count, papers_embedded, chunks_embedded, _expected_counts
                if not in_flight:
                    return True
                done, _ = wait(in_flight.keys(), return_when=FIRST_COMPLETED)
                for fut in done:
                    job = in_flight.pop(fut)
                    try:
                        bundle = fut.result()
                    except Exception as exc:
                        mark_vector_build_state(
                            vault,
                            status="failed",
                            message=str(exc),
                            paper_id=job.paper_id,
                            pid=0,
                        )
                        return False  # abort: worker failure must not mark success
                    if _candidate_conn is not None:
                        delete_paper_vectors_in_conn(_candidate_conn, bundle.paper_id)
                        for payload in bundle.payloads:
                            write_encoded_payload_to_conn(_candidate_conn, payload)
                        _candidate_conn.commit()
                    else:
                        delete_paper_vectors(vault, bundle.paper_id)
                        for payload in bundle.payloads:
                            write_encoded_payload(vault, payload)

                    processed_count += 1
                    papers_embedded += 1
                    chunks_embedded += bundle.chunk_count
                    # P1-1: track per-collection expected counts so the
                    # verifier can catch body/objects redistribution that a
                    # total count would miss.
                    for _p in bundle.payloads:
                        _coll_key = {
                            "paperforge_fulltext": "fulltext",
                            "paperforge_body": "body",
                            "paperforge_objects": "objects",
                        }.get(_p.collection_name)
                        if _coll_key:
                            _expected_counts[_coll_key] += len(_p.ids)

                    print(f"EMBED_PROGRESS:{processed_count}:{total}:{bundle.paper_id}", flush=True)
                    mark_vector_build_state(
                        vault,
                        current=processed_count,
                        paper_id=bundle.paper_id,
                        last_update=_now(),
                    )
                return True

            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                papers_iter = progress_bar(done_papers, desc="Embedding", disable=args.json)
                for entry in papers_iter:
                    key = entry.get("zotero_key")
                    if not key:
                        continue

                    # P0-5: cancellation is a control-sidecar check — never
                    # read live DB status mid-build (it races the publish).
                    if _stop_requested(vault, _os.getpid()):
                        logger.info("Build cancelled at paper %s", key)
                        break

                    has_body = _has_body_units_in_db(vault, key)
                    has_object = _has_object_units_in_db(vault, key)

                    if has_body or has_object:
                        body_units = get_body_units_for_embedding(vault, key) if has_body else []
                        object_units = get_object_units_for_embedding(vault, key) if has_object else []

                        if resume:
                            body_ok = not body_units
                            object_ok = not object_units

                            if body_units:
                                try:

                                    db_path = get_memory_db_path(vault)
                                    conn = get_connection(db_path)
                                    try:
                                        ensure_vec_extension(conn)
                                        ensure_schema(conn)
                                        row = conn.execute(
                                            "SELECT body_units_hash, retrieval_policy_version FROM vec_body_meta WHERE paper_id = ? LIMIT 1",
                                            (key,),
                                        ).fetchone()
                                        if row:
                                            current_body_hash = compute_body_units_hash(body_units)
                                            body_ok = (
                                                row["body_units_hash"] == current_body_hash
                                                and row["retrieval_policy_version"] == RETRIEVAL_POLICY_VERSION
                                            )
                                    finally:
                                        conn.close()
                                except Exception as exc:
                                    logger.warning("Resume body_units check failed for %s: %s", key, exc)

                            if object_units:
                                try:

                                    db_path = get_memory_db_path(vault)
                                    conn = get_connection(db_path)
                                    try:
                                        ensure_vec_extension(conn)
                                        ensure_schema(conn)
                                        row = conn.execute(
                                            "SELECT object_units_hash, retrieval_policy_version FROM vec_objects_meta WHERE paper_id = ? LIMIT 1",
                                            (key,),
                                        ).fetchone()
                                        if row:
                                            current_obj_hash = compute_object_units_hash(object_units)
                                            object_ok = (
                                                row["object_units_hash"] == current_obj_hash
                                                and row["retrieval_policy_version"] == RETRIEVAL_POLICY_VERSION
                                            )
                                    finally:
                                        conn.close()
                                except Exception as exc:
                                    logger.warning("Resume object_units check failed for %s: %s", key, exc)

                            if body_ok and object_ok:
                                processed_count += 1
                                papers_skipped += 1
                                print(f"EMBED_PROGRESS:{processed_count}:{total}:{key}", flush=True)
                                mark_vector_build_state(vault, current=processed_count, paper_id=key, last_update=_now())
                                continue

                        payloads = prepare_payloads_for_entry(vault, key, has_body, has_object, body_units, object_units)
                    else:
                        fulltext_rel = entry.get("fulltext_path", "")
                        if not fulltext_rel:
                            continue
                        vault / fulltext_rel

                        ocr_root = vault / "System" / "PaperForge" / "ocr" / key
                        has_files = (ocr_root / "structure" / "blocks.structured.jsonl").exists() and (
                            ocr_root / "index" / "structure-tree.json"
                        ).exists()
                        if has_files and not has_body:
                            print(
                                f"Skip {key}: has structured blocks but no body_units in DB. "
                                f"Run `paperforge memory build` first."
                            )
                            continue

                        if resume:
                            try:

                                db_path = get_memory_db_path(vault)
                                conn = get_connection(db_path)
                                try:
                                    ensure_vec_extension(conn)
                                    ensure_schema(conn)
                                    row = conn.execute(
                                        "SELECT 1 FROM vec_fulltext_meta WHERE paper_id = ? LIMIT 1", (key,)
                                    ).fetchone()
                                    if row:
                                        processed_count += 1
                                        papers_skipped += 1
                                        print(f"EMBED_PROGRESS:{processed_count}:{total}:{key}", flush=True)
                                        mark_vector_build_state(
                                            vault, current=processed_count, paper_id=key, last_update=_now()
                                        )
                                        continue
                                finally:
                                    conn.close()
                            except Exception as exc:
                                logger.warning("Resume fulltext check failed for %s: %s", key, exc)

                        payloads = prepare_payloads_for_entry(
                            vault, key, has_body, has_object, [], [], fulltext_rel=fulltext_rel
                        )

                    if not payloads:
                        processed_count += 1
                        print(f"EMBED_PROGRESS:{processed_count}:{total}:{key}", flush=True)
                        mark_vector_build_state(vault, current=processed_count, paper_id=key, last_update=_now())
                        continue

                    job = PaperEmbeddingJob(paper_id=key, payloads=payloads)
                    _submit_job(job, pool)

                    if len(in_flight) >= window_size:
                        ok = _complete_one(pool, block=True)
                        if not ok:
                            # P0-5: raise so the unified except handler aborts the
                            # shadow, closes connections, and releases the lock —
                            # a bare `return 1` here would leak all three.
                            raise RuntimeError("Embed worker failed; build aborted")

                while in_flight:
                    ok = _complete_one(pool, block=True)
                    if not ok:
                        raise RuntimeError("Embed worker failed; build aborted")

        except Exception as e:
            try:
                _actual = get_embed_status(vault).get("chunk_count", chunks_embedded)
                _mode = get_embed_status(vault).get("mode", "")
                _model = get_embed_status(vault).get("model", "")
            except Exception:
                _actual = chunks_embedded
                _mode = ""
                _model = ""
            mark_vector_build_state(
                vault,
                status="failed",
                message=str(e),
                pid=0,
            )
            result = PFResult(
                ok=False,
                command="embed build",
                version=PF_VERSION,
                error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            )
            print(result.to_json() if args.json else result.error.message, file=sys.stderr if not args.json else sys.stdout)
            # Shadow: abort candidate, live untouched. In-place: restore backup.
            if _shadow is not None:
                _shadow.abort()
                logger.info("Shadow build aborted; live DB untouched")
            elif _rebuild_backup_path and _rebuild_backup_path.exists():
                _os.replace(str(_rebuild_backup_path), str(get_memory_db_path(vault)))
                logger.info("Restored paperforge.db from pre-rebuild backup after failed build")
            elif _rebuild_backup_path:
                _rebuild_backup_path.unlink(missing_ok=True)
            if _write_lock:
                _write_lock.__exit__(None, None, None)
            return 1

        # Check if we stopped or were cancelled — exit cleanly without marking completed
        if _stop_requested(vault, _os.getpid()):
            logger.info("Build stopped, exiting cleanly")
            if _shadow is not None:
                _shadow.abort()
                logger.info("Shadow build aborted on cancellation; live DB untouched")
            elif _rebuild_backup_path and _rebuild_backup_path.exists():
                _os.replace(str(_rebuild_backup_path), str(get_memory_db_path(vault)))
                logger.info("Restored paperforge.db from pre-rebuild backup after cancellation")
            if _write_lock:
                _write_lock.__exit__(None, None, None)
            print("EMBED_DONE", flush=True)
            return 0

        # #162/T1: write vector lineage rows — into the candidate BEFORE the
        # seal/publish swap (atomic with publish), or onto the live DB for
        # the in-place fallback.  Papers without a retrieval identity (legacy
        # manifests) get no row → probe reports unknown, never stale.
        from paperforge.lineage import write_vector_lineage

        if _candidate_conn is not None:
            _lineage_conn = _candidate_conn
        elif _db_path.exists():
            _lineage_conn = get_connection(_db_path)
            ensure_vec_extension(_lineage_conn)
        else:
            _lineage_conn = None
        try:
            write_vector_lineage(
                _lineage_conn,
                vault,
                endpoint=_current_endpoint,
                model=_current_model,
                dimension=_expected_dim,
            )
            if _lineage_conn is not None:
                _lineage_conn.commit()
        finally:
            if _lineage_conn is not None and _lineage_conn is not _candidate_conn:
                _lineage_conn.close()

        # Shadow: verify candidate, publish (swap), then mark completed on new live.
        if _shadow is not None:
            # P0-2: write the FINAL build metadata into the candidate BEFORE
            # sealing — once os.replace commits, the new live is already
            # complete (status/model/endpoint/dimension/identity/counts),
            # independent of any post-publish bookkeeping that might fail.
            from paperforge.embedding.build_state import _dict_to_build_state

            _cand_state = {
                "status": "completed",
                "current": total,
                "total": total,
                "model": _current_model,
                "vector_provider_endpoint": _current_endpoint,
                "vector_dimension": _expected_dim,
                "vector_identity_version": VECTOR_IDENTITY_VERSION,
                "vector_expected_fulltext": _expected_counts["fulltext"],
                "vector_expected_body": _expected_counts["body"],
                "vector_expected_objects": _expected_counts["objects"],
                "finished_at": _now(),
                "message": "",
                "pid": 0,
                "mode": "api",
            }
            _dict_to_build_state(_candidate_conn, _cand_state)
            _candidate_conn.commit()
            # P1-1: SEAL the candidate (checkpoint + journal switch) BEFORE
            # verifying — verify_candidate must inspect exactly the file that
            # publish() will swap, not the WAL-backed logical view.
            _shadow.seal()
            report = verify_candidate(
                _shadow.target.vector_path,
                # P1-2: expected dimension comes from the model detection that
                # built the tables — never re-read from the candidate DDL.
                dimension=_expected_dim,
                expected_count=sum(_expected_counts.values()),
                expected_counts=dict(_expected_counts),
            )
            if not report["ok"]:
                _shadow.abort()
                logger.error("Shadow verify failed: %s", report.get("reason"))
                if _write_lock:
                    _write_lock.__exit__(None, None, None)
                result = PFResult(
                    ok=False,
                    command="embed build",
                    version=PF_VERSION,
                    error=PFError(
                        code=ErrorCode.INTERNAL_ERROR,
                        message=f"Candidate verification failed: {report.get('reason')}",
                    ),
                )
                print(result.to_json() if args.json else result.error.message,
                      file=sys.stderr if not args.json else sys.stdout)
                return 1
            _shadow.verified()
            _shadow.publish()
            logger.info("Shadow build published: %s → %s",
                        _shadow.target.vector_path, _shadow.target.source_path)

        mark_vector_build_state(
            vault,
            status="completed",
            current=total,
            total=total,
            finished_at=_now(),
            message="",
            pid=0,
            # Shadow publish swaps live for a candidate whose build_state table
            # holds pre-build defaults (the live mark above was written before
            # the swap) — without model/mode the next resume's gate-3 misreads a
            # model change and re-embeds everything.
            model=_current_model,
            vector_provider_endpoint=_current_endpoint,
            vector_identity_version=VECTOR_IDENTITY_VERSION,
            mode=get_embed_status(vault)["mode"],
        )
        try:
            _status = get_embed_status(vault)
            _real_chunks = _status.get("chunk_count", chunks_embedded)
            _mode = _status.get("mode", "")
            _model = _status.get("model", "")
            _body_chunks = _status.get("body_chunk_count", 0)
            _object_chunks = _status.get("object_chunk_count", 0)
            _total_chunks = _status.get("total_chunks", 0)
        except Exception:
            _real_chunks = chunks_embedded
            _mode = ""
            _model = ""
            _body_chunks = 0
            _object_chunks = 0
            _total_chunks = 0


        print("EMBED_DONE", flush=True)

        data = {
            "papers_embedded": papers_embedded,
            "papers_skipped": papers_skipped,
            "chunks_embedded": chunks_embedded,
            "model": get_embed_status(vault)["model"],
            "mode": get_embed_status(vault)["mode"],
        }
        result = PFResult(ok=True, command="embed build", version=PF_VERSION, data=data)
        if args.json:
            print(result.to_json())
        else:
            skipped = f" ({papers_skipped} skipped)" if papers_skipped else ""
            print(f"Embedded {papers_embedded} papers ({chunks_embedded} chunks){skipped}")
        # Build succeeded: delete pre-rebuild backup (in-place strategy only)
        if _rebuild_backup_path and _rebuild_backup_path.exists():
            _rebuild_backup_path.unlink()
            logger.info("Deleted pre-rebuild backup after successful rebuild")
        _clear_stop_request(vault)
        if _write_lock:
            _write_lock.__exit__(None, None, None)
        return 0
    except Exception as e:
        # P0-2: once PUBLISHED the swap is the commit point — abort() is a
        # no-op and marking failed would misreport a live new DB.  Any
        # post-publish bookkeeping failure becomes a success-with-warning.
        if _shadow is not None and _shadow.state == ShadowBuild.PUBLISHED:
            logger.exception("Post-publish bookkeeping failed: %s", e)
            _warning = f"Vectors published; bookkeeping incomplete: {e}"
            result = PFResult(
                ok=True,
                command="embed build",
                version=PF_VERSION,
                data={
                    "papers_embedded": papers_embedded,
                    "papers_skipped": papers_skipped,
                    "chunks_embedded": chunks_embedded,
                    "model": _current_model,
                    "mode": "api",
                    "published": True,
                    "warning": _warning,
                },
                warnings=[_warning],
            )
            # P0-1: ok=True has error=None — never touch result.error.message
            # on the non-JSON path (AttributeError).
            if args.json:
                print(result.to_json())
            else:
                print(
                    f"Embedded {papers_embedded} papers ({chunks_embedded} chunks). "
                    f"Warning: {_warning}",
                    file=sys.stderr,
                )
            return 0
        # Only pre-commit failures may abort/restore/mark-failed.
        if _shadow is not None:
            _shadow.abort()
            logger.info("Shadow build aborted; live DB untouched")
        elif _rebuild_backup_path and _rebuild_backup_path.exists():
            _os.replace(str(_rebuild_backup_path), str(get_memory_db_path(vault)))
            logger.info("Restored paperforge.db from pre-rebuild backup after failed build")
        elif _rebuild_backup_path:
            _rebuild_backup_path.unlink(missing_ok=True)
        try:
            mark_vector_build_state(vault, status="failed", message=str(e), pid=0)
        except Exception:
            pass
        result = PFResult(
            ok=False,
            command="embed build",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
        )
        print(result.to_json() if args.json else result.error.message,
              file=sys.stderr if not args.json else sys.stdout)
        return 1
    finally:
        if _write_lock:
            _write_lock.__exit__(None, None, None)
