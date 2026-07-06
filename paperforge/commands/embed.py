from __future__ import annotations

import argparse
import os
import sys

import logging
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from paperforge.embedding.builder import (
    PaperEmbeddingJob,
    encode_paper_job,
    write_encoded_payload,
    prepare_payloads_for_entry,
)
from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.retrieval.manifest import compute_body_units_hash, compute_object_units_hash, RETRIEVAL_POLICY_VERSION
from paperforge.core.result import PFError, PFResult
from paperforge.embedding import (
    delete_paper_vectors,
    embed_paper,
    get_collection,
    get_embed_status,
    get_vector_db_path,
    mark_vector_build_state,
    read_vector_build_state,
)
from paperforge.embedding.preflight import _preflight_check
from paperforge.memory.chunker import chunk_fulltext
from paperforge.memory.state_snapshot import write_vector_runtime
from paperforge.worker.asset_index import read_index
from paperforge.worker._progress import progress_bar
from paperforge.embedding.builder import embed_body_units, embed_object_units, get_body_units_for_embedding, get_object_units_for_embedding
from paperforge.memory.db import get_connection, get_memory_db_path


def _has_body_units_in_db(vault: Path, key: str) -> bool:
    """Check if paper has body_units in the memory DB."""
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return False
    conn = get_connection(db_path, read_only=True)
    try:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM body_units WHERE paper_id=? AND indexable=1",
            (key,),
        ).fetchone()[0]
        return cnt > 0
    finally:
        conn.close()

def _has_object_units_in_db(vault: Path, key: str) -> bool:
    """Check if paper has object_units in the memory DB."""
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return False
    conn = get_connection(db_path, read_only=True)
    try:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM object_units WHERE paper_id=? AND indexable=1",
            (key,),
        ).fetchone()[0]
        return cnt > 0
    finally:
        conn.close()

def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import subprocess
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True, timeout=5
            )
            return str(pid) in r.stdout
        except:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def _assert_collections_healthy(vault: Path) -> tuple[bool, str]:
    """Probe three collections. Doesn't depend on get_embed_status."""
    for name in ("paperforge_fulltext", "paperforge_body", "paperforge_objects"):
        try:
            col = get_collection(vault, name=name)
            col.count()
        except Exception as exc:
            return False, f"{name}: {exc}"
    return True, ""
logger = logging.getLogger(__name__)

PR9B_MAX_WORKERS = 4

def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    sub = getattr(args, "embed_subcommand", "build")

    if sub == "status":
        status = get_embed_status(vault)
        status["build_state"] = read_vector_build_state(vault)

        # Write vector-runtime-state.json snapshot (JS-First Memory State)
        _dep_missing = []
        try:
            import openai  # noqa: F401
        except ImportError:
            _dep_missing.append("openai")
        try:
            import chromadb  # noqa: F401
        except ImportError:
            _dep_missing.append("chromadb")
        write_vector_runtime(
            vault,
            enabled=bool(status.get("mode", "")),
            mode=status.get("mode", ""),
            model=status.get("model", ""),
            deps_installed=len(_dep_missing) == 0,
            deps_missing=_dep_missing if _dep_missing else None,
            py_version=sys.version.split()[0],
            db_exists=status.get("db_exists", False),
            chunk_count=status.get("chunk_count", 0),
            body_chunk_count=status.get("body_chunk_count", 0),
            object_chunk_count=status.get("object_chunk_count", 0),
            total_chunks=status.get("total_chunks", 0),
            build_state=status.get("build_state"),
            healthy=status.get("healthy", True),
            corrupted=status.get("corrupted", False),
            error=status.get("error", ""),
        )

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
        if pid and state["status"] == "running":
            import signal
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception as exc:
                result = PFResult(
                    ok=False,
                    command="embed stop",
                    version=PF_VERSION,
                    error=PFError(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to stop embed build: {exc}"),
                    data={"state": "running", "pid": pid},
                )
                if args.json:
                    print(result.to_json())
                else:
                    print(result.error.message, file=sys.stderr)
                return 1
            mark_vector_build_state(vault, status="stopping", message="Stop requested")
            result = PFResult(ok=True, command="embed stop", version=PF_VERSION, data={"state": "stopping", "pid": pid})
        else:
            result = PFResult(ok=True, command="embed stop", version=PF_VERSION, data={"state": "idle"})
        if args.json:
            print(result.to_json())
        else:
            print("Stop requested." if result.data["state"] == "stopping" else "No active build.")
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
        result = PFResult(ok=False, command="embed build", version=PF_VERSION,
                         error=PFError(code=ErrorCode.PATH_NOT_FOUND,
                                       message="Canonical index not found. Run paperforge sync first."))
        print(result.to_json() if args.json else result.error.message, file=sys.stderr if not args.json else sys.stdout)
        return 1

    items = envelope if isinstance(envelope, list) else envelope.get("items", [])
    done_papers = [e for e in items if e.get("ocr_status") == "done"]

    total = len(done_papers)
    print(f"EMBED_START:{total}", flush=True)

    import gc as _gc
    import os as _os
    _now = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat

    papers_embedded = 0
    chunks_embedded = 0
    papers_skipped = 0
    resume = getattr(args, "resume", False)

    from paperforge.embedding._config import get_api_model
    _current_model = get_api_model(vault)

    if resume:
        build_state = read_vector_build_state(vault)

        # 门一：stale running state 检测
        if build_state.get("status") == "running":
            stale = False
            pid = build_state.get("pid", 0)
            if not pid:
                stale = True
            elif not _pid_alive(pid):
                stale = True
            else:
                started = build_state.get("started_at", "")
                if started:
                    try:
                        dt = __import__('datetime').datetime.fromisoformat(started)
                        if (__import__('datetime').datetime.now(__import__('datetime').timezone.utc) - dt).total_seconds() > 43200:
                            stale = True
                    except:
                        pass
            if stale:
                msg = "Previous build appears stale (crashed?). Use --force to rebuild."
                print(msg)
                return 1

        # 门二：missing DB → fresh build（不是 error）
        db_path = get_vector_db_path(vault)
        if not db_path.exists():
            resume = False
        else:
            # 门三：corrupted DB
            ok, err = _assert_collections_healthy(vault)
            if not ok:
                msg = f"Vector DB corrupted ({err}). Use --force to rebuild."
                print(msg)
                return 1

            # 过三道门后，正常 model check
            stored_model = build_state.get("model", "")
            if stored_model and _current_model and stored_model != _current_model:
                msg = f"Model changed: {stored_model} -> {_current_model}. Re-embedding all papers."
                if not getattr(args, "json", False):
                    print(msg)
                resume = False

    _force_rebuild = args.force or (resume is False and getattr(args, "resume", False))
    if _force_rebuild:
        _gc.collect()
        db_path = get_vector_db_path(vault)
        if db_path.exists():
            import shutil
            shutil.rmtree(str(db_path), ignore_errors=True)
            if db_path.exists():
                import time
                time.sleep(0.5)
                shutil.rmtree(str(db_path), ignore_errors=True)

    mark_vector_build_state(vault,
        status="running",
        current=0, total=total, paper_id="",
        started_at=_now(), finished_at="",
        message="", pid=_os.getpid(),
        model=_current_model,
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
            nonlocal processed_count, papers_embedded, chunks_embedded
            if not in_flight:
                return True
            done, _ = wait(in_flight.keys(), return_when=FIRST_COMPLETED)
            for fut in done:
                job = in_flight.pop(fut)
                try:
                    bundle = fut.result()
                except Exception as exc:
                    mark_vector_build_state(vault,
                        status="failed", message=str(exc),
                        paper_id=job.paper_id, pid=0,
                    )
                    return False

                delete_paper_vectors(vault, bundle.paper_id)
                for payload in bundle.payloads:
                    write_encoded_payload(vault, payload)

                processed_count += 1
                papers_embedded += 1
                chunks_embedded += bundle.chunk_count

                print(f"EMBED_PROGRESS:{processed_count}:{total}:{bundle.paper_id}", flush=True)
                mark_vector_build_state(vault,
                    current=processed_count, paper_id=bundle.paper_id,
                    last_update=_now(),
                )
            return True

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            papers_iter = progress_bar(done_papers, desc="Embedding", disable=args.json)
            for entry in papers_iter:
                key = entry.get("zotero_key")
                if not key:
                    continue

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
                                col = get_collection(vault, name="paperforge_body")
                                existing = col.get(where={"paper_id": key}, limit=1)
                                if existing.get("ids"):
                                    meta = existing.get("metadatas", [{}])[0]
                                    current_body_hash = compute_body_units_hash(body_units)
                                    body_ok = (meta.get("body_units_hash") == current_body_hash
                                               and meta.get("retrieval_policy_version") == RETRIEVAL_POLICY_VERSION)
                            except Exception:
                                pass

                        if object_units:
                            try:
                                col = get_collection(vault, name="paperforge_objects")
                                existing = col.get(where={"paper_id": key}, limit=1)
                                if existing.get("ids"):
                                    meta = existing.get("metadatas", [{}])[0]
                                    current_obj_hash = compute_object_units_hash(object_units)
                                    object_ok = (meta.get("object_units_hash") == current_obj_hash
                                                 and meta.get("retrieval_policy_version") == RETRIEVAL_POLICY_VERSION)
                            except Exception:
                                pass

                        if body_ok and object_ok:
                            processed_count += 1
                            papers_skipped += 1
                            print(f"EMBED_PROGRESS:{processed_count}:{total}:{key}", flush=True)
                            mark_vector_build_state(vault, current=processed_count, paper_id=key, last_update=_now())
                            continue

                    payloads = prepare_payloads_for_entry(
                        vault, key, has_body, has_object, body_units, object_units
                    )
                else:
                    fulltext_rel = entry.get("fulltext_path", "")
                    if not fulltext_rel:
                        continue
                    fulltext_path = vault / fulltext_rel

                    ocr_root = vault / "System" / "PaperForge" / "ocr" / key
                    has_files = ((ocr_root / "structure" / "blocks.structured.jsonl").exists()
                                 and (ocr_root / "index" / "structure-tree.json").exists())
                    if has_files and not has_body:
                        print(f"Skip {key}: has structured blocks but no body_units in DB. "
                              f"Run `paperforge memory build` first.")
                        continue

                    if resume:
                        try:
                            collection = get_collection(vault)
                            existing = collection.get(where={"paper_id": key}, limit=1)
                            if existing.get("ids") and len(existing["ids"]) > 0:
                                processed_count += 1
                                papers_skipped += 1
                                print(f"EMBED_PROGRESS:{processed_count}:{total}:{key}", flush=True)
                                mark_vector_build_state(vault, current=processed_count, paper_id=key, last_update=_now())
                                continue
                        except Exception as exc:
                            err = str(exc).lower()
                            if "hnsw" in err or "compaction" in err:
                                logger.warning("ChromaDB index corrupted — rebuilding from scratch. Use --force next time for clean rebuild.")
                            pass

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
                        return 1

            while in_flight:
                ok = _complete_one(pool, block=True)
                if not ok:
                    return 1

    except Exception as e:
        try:
            _actual = get_embed_status(vault).get("chunk_count", chunks_embedded)
            _mode = get_embed_status(vault).get("mode", "")
            _model = get_embed_status(vault).get("model", "")
        except Exception:
            _actual = chunks_embedded
            _mode = ""
            _model = ""
        mark_vector_build_state(vault,
            status="failed", message=str(e), pid=0,
        )
        write_vector_runtime(
            vault,
            enabled=bool(_mode),
            mode=_mode,
            model=_model,
            deps_installed=True,
            deps_missing=None,
            py_version=sys.version.split()[0],
            db_exists=get_vector_db_path(vault).exists(),
            chunk_count=_actual,
            body_chunk_count=0,
            object_chunk_count=0,
            total_chunks=_actual,
            build_state=read_vector_build_state(vault),
            healthy=False,
            error=str(e),
        )
        result = PFResult(ok=False, command="embed build", version=PF_VERSION,
                         error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(e)))
        print(result.to_json() if args.json else result.error.message, file=sys.stderr if not args.json else sys.stdout)
        return 1

    mark_vector_build_state(vault,
        status="completed",
        current=total, finished_at=_now(),
        message="", pid=0,
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

    write_vector_runtime(
        vault,
        enabled=bool(_mode),
        mode=_mode,
        model=_model,
        deps_installed=True,
        deps_missing=None,
        py_version=sys.version.split()[0],
        db_exists=True,
        chunk_count=_real_chunks,
        body_chunk_count=_body_chunks,
        object_chunk_count=_object_chunks,
        total_chunks=_total_chunks,
        build_state=read_vector_build_state(vault),
        healthy=True,
        error="",
    )

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
    return 0
