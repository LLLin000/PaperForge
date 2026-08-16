"""Embedding service boundary (M3, Control Plane Closure).

The embedding domain core lives HERE, not in commands/ — the CLI and the
action layer are callers.  This module must never import
paperforge.commands.*, argparse, or read Obsidian plugin settings; the
canonical config + credential authority + memory/vector substrate are the
only inputs.

M3-A: core builder moved out of commands/embed.py (behavior preserved);
M3-B adds retrieval-truth eligibility + canonical preconditions.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.credentials import CredentialError
from paperforge.embedding import (
    delete_paper_vectors,
    get_embed_status,
    mark_vector_build_state,
    read_vector_build_state,
)
from paperforge.embedding._chroma import delete_paper_vectors_in_conn
from paperforge.embedding.build_target import BuildTarget, ShadowBuild, verify_candidate
from paperforge.embedding.dim_detect import ensure_vec_tables
from paperforge.embedding.substrate import VECTOR_IDENTITY_VERSION, assess_vector_substrate
from paperforge.embedding.builder import (
    PaperEmbeddingJob,
    encode_paper_job,
    get_body_units_for_embedding,
    get_object_units_for_embedding,
    prepare_payloads_for_entry,
    write_encoded_payload,
    write_encoded_payload_to_conn,
)
from paperforge.memory.db import WriterLock, ensure_vec_extension, get_connection, get_memory_db_path, open_live_reader
from paperforge.memory.schema import ensure_schema
from paperforge.retrieval.manifest import RETRIEVAL_POLICY_VERSION, compute_body_units_hash, compute_object_units_hash
from paperforge.worker._progress import progress_bar
from paperforge.worker.asset_index import read_index

logger = logging.getLogger(__name__)

# M3: moved from commands/embed.py — worker pool bound for parallel chunking.
PR9B_MAX_WORKERS = 4


@dataclass(frozen=True)
class EmbeddingBuildRequest:
    """M3: stable service request — never argparse.Namespace.

    ``mode``: "build" (global substrate rebuild) or "resume" (incremental).
    ``keys``: papers-scope filter; empty = whole library.
    """

    scope_kind: Literal["all", "papers"] = "all"
    keys: tuple[str, ...] = ()
    mode: Literal["build", "resume"] = "build"
    force: bool = False


def assess_embedding_preconditions(vault: Path) -> dict:
    """M3-B: canonical embedding preconditions — package + credential
    authority ONLY.  Obsidian plugin settings are NOT configuration
    authority and are never read (the old CLI preflight read
    .obsidian/plugins/paperforge/data.json).  Returns {ok, error, fix}."""
    try:
        import openai  # noqa: F401
    except ImportError:
        return {
            "ok": False,
            "error": "openai is not installed",
            "fix": 'Run: pip install "paperforge[vector]"',
        }
    from paperforge.credentials import CredentialKey, status as credential_status

    cred_state = credential_status(CredentialKey("embedding")).state
    if cred_state == "missing":
        return {
            "ok": False,
            "error": "API key not configured",
            "fix": "Run `paperforge auth set embedding --stdin` or supply PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT",
        }
    if cred_state != "available":
        return {
            "ok": False,
            "error": f"Embedding credential unavailable ({cred_state})",
            "fix": "Run `paperforge auth status embedding` for remediation",
        }
    return {"ok": True}


def run_embedding_build(
    vault: Path,
    items: list[dict],
    keys: list[str] | None = None,
    *,
    force: bool = False,
    resume: bool = False,
    json: bool = False,
) -> int:
    """M3-A: the embed build core (moved from commands/embed.run_build;
    signature preserved so behavior is unchanged — M3-C wires the request
    type)."""
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


# #137: the embed control sidecar (embed-control.json / `embed stop`) is
# RETIRED — cancellation is ONE cooperative token (stdin PAPERFORGE_STOP +
# SIGINT + SIGTERM) via paperforge.core.cancellation.  Orphaned builds are
# hard-terminated only; no persistent control plane is invented.

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


def _resolve_lineage_dimension(
    conn, expected_dim: int, stored_dim: int
) -> int:
    """Lineage identity needs the substrate's ACTUAL dimension.  Incremental
    resume builds never recreate vec tables (expected_dim stays 0) and may
    lack build_state.vector_dimension (stored_dim 0) — the vec0 DDL is the
    authoritative self-declaration (same principle as lineage probe)."""
    dim = expected_dim or stored_dim or 0
    if not dim and conn is not None:
        try:
            from paperforge.lineage import _vec_dimension_from_ddl

            dim = _vec_dimension_from_ddl(conn) or 0
        except Exception:  # noqa: BLE001
            dim = 0
    return dim


def _scoped_global_progress(
    vault: Path, items: list[dict], db_path: Path
) -> tuple[str, int, int, str]:
    """Honest post-scoped-build state: a scoped (papers) build's own total is
    the requested subset, so marking ``completed`` with it would claim the
    whole library is embedded while hundreds of papers still lack vectors —
    the probe then shows a false ready with no resume action.  Recompute the
    GLOBAL progress (distinct papers with vectors vs done papers) and report
    ``interrupted`` while papers are missing, so the probe surfaces the
    resume action."""
    try:
        import sqlite3 as _sq

        conn = _sq.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        try:
            embedded = conn.execute(
                "SELECT COUNT(DISTINCT paper_id) FROM vec_body_meta"
            ).fetchone()[0]
        finally:
            conn.close()
        done = sum(1 for e in items if e.get("ocr_status") == "done")
        if embedded < done:
            return (
                "interrupted",
                embedded,
                done,
                f"Embedded {embedded}/{done} papers (scoped build finished)",
            )
        return "completed", embedded, done, ""
    except Exception:  # noqa: BLE001 — fall back to the scoped total
        return "completed", 0, 0, ""




def run_embedding_build(
    vault: Path,
    items: list[dict],
    keys: list[str] | None = None,
    *,
    force: bool = False,
    resume: bool = False,
    json: bool = False,
) -> int:
    """#165/T4: the embed build core.  keys=None -> whole-library behavior;
    keys given -> candidates = done_papers ∩ keys (subset semantics)."""

    done_papers = [e for e in items if e.get("ocr_status") == "done"]
    # #165/T4: papers-scope filter — candidates = done_papers ∩ keys.
    candidates = (
        [e for e in done_papers if e.get("zotero_key") in set(keys)]
        if keys is not None
        else done_papers
    )

    # Resolve DB path unconditionally — shadow/force paths need it even when
    # resume is False (regression: was only assigned inside `if resume:`).
    _db_path = get_memory_db_path(vault)

    total = len(candidates)
    if not json:
        # #137: structured-stream mode — stdout carries NDJSON events only.
        from paperforge.core.ndjson import emit_start

        emit_start("embed.build", total=total)
    # #137: ONE cooperative cancellation token (stdin PAPERFORGE_STOP +
    # SIGINT + SIGTERM); the embed control sidecar is retired.
    from paperforge.core.cancellation import make_cancellation_token

    _is_stopped, _restore_stop = make_cancellation_token()

    import gc as _gc
    import os as _os

    _now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat

    papers_embedded = 0
    chunks_embedded = 0
    papers_skipped = 0
    
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
        # #166 corrective (P0-3): `requested_resume` is what the caller asked
        # for — captured BEFORE any effective-resume gate.  The gates below
        # downgrade `resume` (effective); a downgrade means a full rebuild is
        # required, which must route through shadow.  The old placement after
        # the gates saved the already-downgraded value, silently restoring
        # the in-place degradation the #165 corrective was meant to kill.
        requested_resume = resume
        # RC UX Seam: an interrupted shadow build leaves the candidate file
        # with real vector rows while the LIVE db is still empty (shadow
        # publishes only on completion).  Detect that surviving candidate so
        # the resume gates below can continue it instead of wiping it.
        _candidate_path = _db_path.with_suffix(".db.build")
        _recover_candidate = False
        if resume and _candidate_path.exists():
            try:
                import sqlite3 as _rc_sqlite3

                _rc_conn = _rc_sqlite3.connect(
                    f"file:{_candidate_path.as_posix()}?mode=ro", uri=True
                )
                try:
                    from paperforge.embedding.substrate import _has_any_rows as _rc_has_rows

                    _recover_candidate = _rc_has_rows(_rc_conn)
                finally:
                    _rc_conn.close()
            except Exception:
                _recover_candidate = False
        # Substrate observation (single source of truth, shared with
        # reconcile T5 + embed.resume preflight): desired embedding identity
        # (config) vs published substrate (build_state + vec0 layout).
        _substrate = assess_vector_substrate(vault)
        _current_endpoint = _substrate.current_endpoint
        _stored_dim = _substrate.stored_dimension
        if resume:
            build_state = read_vector_build_state(vault)

            # 门零 (RC UX Seam): a FAILED build whose candidate survived is
            # resumable — the failure (e.g. transient API 402/network) must
            # not force a full rebuild.  Mark interrupted so the probe shows
            # the resume path and progress starts at the failed position.
            if (
                _recover_candidate
                and build_state.get("status") == "failed"
            ):
                msg = (
                    "Previous build failed but its candidate survived. "
                    "Resuming from the surviving candidate."
                )
                if not json:
                    print(msg)
                mark_vector_build_state(
                    vault,
                    _target_db=_candidate_path if _recover_candidate else None,
                    status="interrupted",
                    message="Previous build failed; resuming from candidate",
                    pid=0,
                )

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
                    if _recover_candidate:
                        # RC UX Seam: the previous process died but its
                        # candidate survived — keep progress, mark
                        # interrupted so the probe shows a resume path, and
                        # continue the shadow build below.
                        msg = (
                            "Previous build was interrupted (process gone). "
                            "Resuming from the surviving candidate."
                        )
                        if not json:
                            print(msg)
                        mark_vector_build_state(
                            vault,
                            _target_db=_candidate_path if _recover_candidate else None,
                            status="interrupted",
                            message="Previous process exited; resuming from candidate",
                            pid=0,
                        )
                    else:
                        # Zombie `running` without a candidate: the previous
                        # process died mid-build.  Old code forced resume=False
                        # here -> full rebuild that re-embeds EVERY paper even
                        # when vectors already exist (measured waste on the
                        # 2026-08-14 full resume: 83 already-embedded papers
                        # re-embedded).  Keep resume=True and let 门二
                        # (no rows -> fresh build) / 门三 (model/identity
                        # changed -> full rebuild) decide: existing vectors +
                        # matching identity route through in-place
                        # incremental, only embedding the missing papers.
                        msg = (
                            "Previous build appears stale (crashed?). "
                            "Recovering; resuming from existing vectors."
                        )
                        if not json:
                            print(msg)
                        mark_vector_build_state(
                            vault,
                            status="interrupted",
                            message="Previous process exited (crashed); resuming",
                            pid=0,
                        )
            # 门二：no vec0 rows → fresh build（不是 error）。#167 P0-4:
            # pristine (no rows AND no published vector identity) is a
            # per-paper missing deficit — a scoped resume may INITIALIZE the
            # empty substrate (embed only the requested keys).  Rows lost
            # after a published identity (identity_version > 0) is data
            # loss → full rebuild.  RC UX Seam: a surviving candidate with
            # rows counts as "has rows" for the interrupted-shadow case.
            if (
                not _substrate.has_any_rows
                and _substrate.identity_version > 0
                and not _recover_candidate
            ):
                resume = False
            else:
                # 门三：过三道门后，正常 model check
                stored_model = _substrate.stored_model
                if stored_model and _current_model and stored_model != _current_model:
                    msg = f"Model changed: {stored_model} -> {_current_model}. Re-embedding all papers."
                    if not json:
                        print(msg)
                    resume = False

        # P0-2: full rebuild must never honor resume — the candidate's
        # vector tables are cleared, so a hash-skip would publish a DB
        # missing those papers' vectors.  Force wins over resume at both the
        # CLI (mutually exclusive group) and programmatic call sites.
        if force:
            resume = False
        _force_rebuild = force or (requested_resume and not resume)
        # D5: full rebuilds (force / model change / resume reset) use shadow target.
        # P1: embedding identity is (provider endpoint, model) — a config
        # switch of EITHER must route through shadow.  A plain `embed build`
        # after a model/endpoint change would otherwise let ensure_vec_tables
        # resize vec0 in place on the live DB and expose an empty/partial
        # window mid-build.
        _embedding_identity_changed = _substrate.identity_changed
        if _embedding_identity_changed and not json:
            print(
                f"Embedding identity changed: "
                f"{_substrate.stored_model}@{_substrate.stored_endpoint} -> "
                f"{_substrate.current_model}@{_substrate.current_endpoint}. Re-embedding all papers."
            )
        # P0-3/P1-1: a live vector-layout mismatch must route through shadow —
        # an in-place recreate would destroy live vectors + orphan meta rows.
        # Compare the live layout against the STORED build dimension via the
        # unified inspect_vector_layout contract (six tables + three dims),
        # without an API probe (that would add a network call to every build).
        _vec_layout_incompatible = _substrate.layout_incompatible
        # Legacy libraries (built before identity recording) have no
        # vector_identity_version — rebuild them once so endpoint/model are
        # persisted and future comparisons are meaningful.
        _legacy_identity = _substrate.legacy_identity
        requires_shadow = (
            _force_rebuild
            or _embedding_identity_changed
            or _vec_layout_incompatible
            or _legacy_identity
            # RC UX Seam: resume with a surviving candidate MUST route
            # through shadow-recover.  Substrate is compatible when read via
            # effective_vector_db (it sees the candidate's rows), so without
            # this the resume would go in-place and hash-skip against the
            # EMPTY live table — re-embedding everything from 1.
            or _recover_candidate
        ) and _substrate.db_exists
        # #165/T4: a papers-scoped request must never route through a FRESH
        # shadow rebuild — prepare() clears the candidate's vec tables and
        # EVERY done paper would be re-embedded, violating affected ⊆
        # requested.  RC UX Seam EXCEPTION: a SURVIVING candidate (recover)
        # is never cleared — recover() continues it, so a scoped resume only
        # ADDS the requested keys' vectors.  This is the incremental-publish
        # path: candidate keeps existing rows, embeds the scoped papers, and
        # the checkpoint/final publish merges them into live.
        if keys is not None and (requires_shadow or _force_rebuild) and not _recover_candidate:
            from paperforge.core.errors import ErrorCode as _EC

            result = PFResult(
                ok=False,
                command="embed build",
                version=PF_VERSION,
                error=PFError(
                    code=_EC.ACTION_UNAVAILABLE,
                    message="papers-scope embed requires an in-place resume build — "
                    "a full rebuild was triggered (run `paperforge action run embed.build` first)",
                ),
            )
            if json:
                print(result.to_json())
            else:
                print(result.error.message, file=sys.stderr)
            return 1
        # P0-2: ANY full shadow rebuild clears the candidate's vector tables —
        # resume hash-skips would leave those papers' vectors missing from the
        # published DB (chunks_embedded=0, verifier passes, empty library
        # published).  Shadow ⇒ resume off, for every trigger, not just force.
        # RC UX Seam EXCEPTION: an interrupted shadow build whose candidate
        # survived keeps resume=True — recover() continues that candidate
        # instead of clearing it.  --force / embed.build explicitly OVERRIDES
        # the exception: the user asked for a full rebuild, so the surviving
        # candidate is wiped and rebuilt from scratch.
        if force:
            _recover_candidate = False
            resume = False
        elif requires_shadow and not _recover_candidate:
            resume = False

        if requires_shadow:
            # Maintenance mode message (D2b).
            if not json:
                print(
                    "Maintenance mode: OCR syncs and memory updates are paused "
                    "until the rebuild completes."
                )
            _target = BuildTarget(
                source_path=_db_path,
                vector_path=_db_path.with_suffix(".db.build"),
            )
            _shadow = ShadowBuild(_target)
            if _recover_candidate:
                # RC UX Seam: resume the surviving candidate — no cleanup,
                # no snapshot, no table clear.  recover() validates it has
                # rows and enters BUILDING directly (a second building()
                # call here would raise invalid transition).
                _shadow.recover()
                _candidate_conn = _shadow.candidate_conn()
                ensure_vec_extension(_candidate_conn)
                ensure_schema(_candidate_conn)
                # The candidate may lack build_state.vector_dimension (only
                # written at final completion) — fall back to the vec0 DDL
                # self-declaration so verify() and lineage get the real dim.
                _expected_dim = _resolve_lineage_dimension(
                    _candidate_conn, _stored_dim, _substrate.stored_dimension
                )
            else:
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

        # RC UX Seam: an interrupted-shadow resume starts progress at the
        # interrupted position (build_state.current) instead of 0, and keeps
        # the identity it was building with — the candidate already holds
        # that many papers' vectors.
        if _recover_candidate:
            _resume_base = int(build_state.get("current", 0) or 0)
            _resume_model = str(build_state.get("model", "") or _current_model)
            _resume_endpoint = str(
                build_state.get("vector_provider_endpoint", "") or _current_endpoint
            )
        else:
            _resume_base = 0
            _resume_model = _current_model
            _resume_endpoint = _current_endpoint

        # RC UX Seam: shadow builds write in-flight state to the CANDIDATE
        # (the file every observer reads via effective_vector_db), so the
        # probe/status show real progress instead of the stale live table.
        # The candidate is written through the SAME _candidate_conn the
        # build writes vectors with — a second connection would contend on
        # the WAL and silently fail.
        _mark_target = (
            _target.vector_path if (_shadow is not None) else None
        )

        def _mark(**fields) -> None:
            if _candidate_conn is not None:
                from paperforge.embedding.build_state import _build_state_to_dict, _dict_to_build_state, _default_state

                state = _build_state_to_dict(_candidate_conn) or _default_state()
                state.update(fields)
                _dict_to_build_state(_candidate_conn, state)
                try:
                    _candidate_conn.commit()
                except Exception:  # noqa: BLE001
                    pass
            else:
                mark_vector_build_state(vault, **fields)

        _mark(
            status="running",
            current=_resume_base,
            total=total,
            paper_id="",
            started_at=_now(),
            finished_at="",
            message="",
            pid=_os.getpid(),
            model=_resume_model,
            vector_provider_endpoint=_resume_endpoint,
            vector_identity_version=VECTOR_IDENTITY_VERSION,
            mode=get_embed_status(vault)["mode"],
        )

        try:
            max_workers = PR9B_MAX_WORKERS
            window_size = max_workers * 4

            processed_count = _resume_base
            papers_embedded = 0
            papers_skipped = 0
            chunks_embedded = 0
            # #165/T4: papers whose vectors were genuinely regenerated this
            # run — resume-hash-skipped papers must NOT get lineage rewrites.
            regenerated_papers: set[str] = set()
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
                        _mark(
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
                    regenerated_papers.add(bundle.paper_id)
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

                    if not json:
                        from paperforge.core.ndjson import emit_progress

                        emit_progress("embed.build", processed_count, total,
                                      item_id=bundle.paper_id)
                    _mark(
                        current=processed_count,
                        paper_id=bundle.paper_id,
                        last_update=_now(),
                    )
                return True

            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                papers_iter = progress_bar(candidates, desc="Embedding", disable=json)
                for entry in papers_iter:
                    key = entry.get("zotero_key")
                    if not key:
                        continue

                    # #137: cooperative stop token — never read live DB
                    # status mid-build (it races the publish).
                    if _is_stopped():
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

                                    if _candidate_conn is not None:
                                        conn = _candidate_conn
                                    else:
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
                                        if _candidate_conn is None:
                                            conn.close()
                                except Exception as exc:
                                    logger.warning("Resume body_units check failed for %s: %s", key, exc)

                            if object_units:
                                try:

                                    if _candidate_conn is not None:
                                        conn = _candidate_conn
                                    else:
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
                                        if _candidate_conn is None:
                                            conn.close()
                                except Exception as exc:
                                    logger.warning("Resume object_units check failed for %s: %s", key, exc)

                            if body_ok and object_ok:
                                processed_count += 1
                                papers_skipped += 1
                                print(f"EMBED_PROGRESS:{processed_count}:{total}:{key}", flush=True)
                                _mark(current=processed_count, paper_id=key, last_update=_now())
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
                                f"Run `paperforge memory build` first.",
                                file=sys.stderr,
                            )
                            continue

                        if resume:
                            try:

                                if _candidate_conn is not None:
                                    conn = _candidate_conn
                                else:
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
                                        _mark(
                                            current=processed_count, paper_id=key, last_update=_now()
                                        )
                                        continue
                                finally:
                                    if _candidate_conn is None:
                                        conn.close()
                            except Exception as exc:
                                logger.warning("Resume fulltext check failed for %s: %s", key, exc)

                        payloads = prepare_payloads_for_entry(
                            vault, key, has_body, has_object, [], [], fulltext_rel=fulltext_rel
                        )

                    if not payloads:
                        processed_count += 1
                        print(f"EMBED_PROGRESS:{processed_count}:{total}:{key}", flush=True)
                        _mark(current=processed_count, paper_id=key, last_update=_now())
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

        except CredentialError as exc:
            # #173 corrective: backend credential faults (locked/unavailable/
            # denied) fail loud with the credential code — never reported as
            # a generic missing-key or INTERNAL_ERROR.  Inlined here so the
            # service never imports paperforge.commands.* (M2-F boundary).
            from paperforge.core.errors import ErrorCode as _EC
            from paperforge.core.result import PFError as _PFError

            _code_map = {
                "locked": "credential.locked",
                "unavailable": "credential.backend_unavailable",
                "denied": "credential.backend_denied",
            }
            result = PFResult(
                ok=False,
                command="embed build",
                version=PF_VERSION,
                error=_PFError(
                    code=_code_map.get(str(getattr(exc, "code", "")) or "", _EC.INTERNAL_ERROR),
                    message=str(exc),
                    details=getattr(exc, "details", None),
                ),
            )
            print(result.to_json() if json else result.error.message, file=sys.stderr if not json else sys.stdout)
            if _shadow is not None:
                try:
                    _shadow.close_candidate_conn()
                except Exception:  # noqa: BLE001
                    pass
                logger.info(
                    "Shadow build failed on credential fault; candidate retained for resume; live DB untouched"
                )
            if _write_lock:
                _write_lock.__exit__(None, None, None)
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
            _mark(
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
            print(result.to_json() if json else result.error.message, file=sys.stderr if not json else sys.stdout)
            # Shadow: keep the candidate so `--resume` can continue from the
            # surviving rows (RC UX Seam) — live stays untouched either way.
            # The candidate is a shadow file; the writer lock was held, no
            # other process can be mid-publish on it.  A failed candidate is
            # never published automatically; only an explicit resume (or a
            # force rebuild that wipes it) touches it again.
            if _shadow is not None:
                try:
                    _shadow.close_candidate_conn()
                except Exception:  # noqa: BLE001
                    pass
                logger.info(
                    "Shadow build failed; candidate retained for resume; live DB untouched"
                )
            elif _rebuild_backup_path and _rebuild_backup_path.exists():
                _os.replace(str(_rebuild_backup_path), str(get_memory_db_path(vault)))
                logger.info("Restored paperforge.db from pre-rebuild backup after failed build")
            elif _rebuild_backup_path:
                _rebuild_backup_path.unlink(missing_ok=True)
            if _write_lock:
                _write_lock.__exit__(None, None, None)
            return 1

        # Check if we stopped or were cancelled — exit cleanly without
        # marking completed.  #137: cancelled is a terminal outcome with
        # exit code 130, never a folded rc0.  RC UX Seam: write an explicit
        # interrupted state so the probe can surface a resume path instead
        # of a zombie "running" that reads as ready.
        if _is_stopped():
            logger.info("Build stopped, exiting cleanly")
            try:
                _mark(
                    status="interrupted",
                    message="Build cancelled by user",
                    pid=0,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to mark interrupted state: %s", exc)
            if _shadow is not None:
                # RC UX Seam: user stop KEEPS the candidate so resume can
                # continue from where it stopped.  Wiping it here would
                # discard real progress (like the old abort did).  A full
                # rebuild remains available via --force / embed.build.
                #
                # Checkpoint publish: papers whose vectors were fully
                # embedded this run get lineage rows and the candidate is
                # COPIED (not moved) onto live — they become retrievable
                # now, while the candidate survives for resume.  The copied
                # build_state also carries model/endpoint/dimension/identity,
                # so a later incremental resume no longer needs shadow.
                _partial_published = False
                try:
                    # Partial publish whenever the candidate holds vector
                    # rows — not just when THIS run embedded new papers.  A
                    # stop that lands before any new embedding must still
                    # publish what earlier interrupted runs already built.
                    _has_candidate_rows = False
                    if _candidate_conn is not None:
                        from paperforge.embedding.substrate import _has_any_rows

                        _has_candidate_rows = _has_any_rows(_candidate_conn)
                    if _candidate_conn is not None and _has_candidate_rows:
                        from paperforge.lineage import write_vector_lineage
                        from paperforge.embedding.build_target import (
                            partial_publish_shadow,
                        )

                        _lineage_dim = _resolve_lineage_dimension(
                            _candidate_conn, _expected_dim, int(_stored_dim or 0)
                        )
                        # Partial publish writes lineage for EVERY paper with
                        # vectors in the candidate — not just this run's
                        # regenerated set.  Earlier interrupted runs embedded
                        # papers whose lineage was never written (it is
                        # written at final completion only); without rows they
                        # would probe unknown and the reader gate would drop
                        # them.  paper_ids=None = all papers with vectors.
                        write_vector_lineage(
                            _candidate_conn,
                            vault,
                            endpoint=_current_endpoint,
                            model=_current_model,
                            dimension=_lineage_dim,
                        )
                        _candidate_conn.commit()
                        partial_publish_shadow(
                            _shadow.target.vector_path,
                            _shadow.target.source_path,
                        )
                        _partial_published = True
                        logger.info(
                            "Partial publish: candidate vectors copied to live; "
                            "candidate retained for resume",
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Partial publish skipped (%s); candidate retained for resume, "
                        "live untouched",
                        exc,
                    )
                try:
                    _shadow.close_candidate_conn()
                except Exception:  # noqa: BLE001
                    pass
                logger.info(
                    "Shadow build stopped; candidate retained for resume; live DB %s",
                    "partially updated" if _partial_published else "untouched",
                )
            elif _rebuild_backup_path and _rebuild_backup_path.exists():
                _os.replace(str(_rebuild_backup_path), str(get_memory_db_path(vault)))
                logger.info("Restored paperforge.db from pre-rebuild backup after cancellation")
            if _write_lock:
                _write_lock.__exit__(None, None, None)
            if not json:
                from paperforge.core.ndjson import emit_terminal
                from paperforge.actions.runner import cancelled_result as _cr

                emit_terminal("cancelled", "embed.build",
                              _cr("embed build", "Build cancelled"))
            return 130

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
            # #165/T4: incremental resume builds never recreate vec tables,
            # so _expected_dim stays 0 — fall back to the stored dimension,
            # then to the vec0 DDL self-declaration.
            _lineage_dim = _resolve_lineage_dimension(
                _lineage_conn, _expected_dim, int(_stored_dim or 0)
            )
            write_vector_lineage(
                _lineage_conn,
                vault,
                endpoint=_current_endpoint,
                model=_current_model,
                dimension=_lineage_dim,
                paper_ids=regenerated_papers,
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

            # Scoped builds must not claim global completed (see the final
            # _mark below); compute the honest state once here so the
            # swapped-in live carries it even if post-publish bookkeeping
            # fails.  Reuses the same computation as the final mark.
            if keys is not None:
                _cand_status, _cand_current, _cand_total, _cand_message = (
                    _scoped_global_progress(vault, items, _db_path)
                )
            else:
                _cand_status, _cand_current, _cand_total, _cand_message = (
                    "completed", total, total, ""
                )
            _cand_state = {
                "status": _cand_status,
                "current": _cand_current,
                "total": _cand_total,
                "model": _current_model,
                "vector_provider_endpoint": _current_endpoint,
                "vector_dimension": _expected_dim,
                "vector_identity_version": VECTOR_IDENTITY_VERSION,
                "vector_expected_fulltext": _expected_counts["fulltext"],
                "vector_expected_body": _expected_counts["body"],
                "vector_expected_objects": _expected_counts["objects"],
                "finished_at": _now(),
                "message": _cand_message,
                "pid": 0,
                "mode": "api",
            }
            _dict_to_build_state(_candidate_conn, _cand_state)
            _candidate_conn.commit()
            # P1-1: SEAL the candidate (checkpoint + journal switch) BEFORE
            # verifying — verify_candidate must inspect exactly the file that
            # publish() will swap, not the WAL-backed logical view.
            _shadow.seal()
            # Scoped (papers) builds embed only the requested subset — the
            # candidate already holds other papers' rows, so a per-collection
            # count match against THIS run's accumulators is meaningless.
            # Pass None to skip count comparison; layout/orphan/KNN checks
            # still run.
            _scoped_expected = None if keys is not None else dict(_expected_counts)
            report = verify_candidate(
                _shadow.target.vector_path,
                # P1-2: expected dimension comes from the model detection that
                # built the tables — never re-read from the candidate DDL.
                dimension=_expected_dim,
                expected_count=None if keys is not None else sum(_expected_counts.values()),
                expected_counts=_scoped_expected,
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
                print(result.to_json() if json else result.error.message,
                      file=sys.stderr if not json else sys.stdout)
                return 1
            _shadow.verified()
            _shadow.publish()
            logger.info("Shadow build published: %s → %s",
                        _shadow.target.vector_path, _shadow.target.source_path)
            # RC UX Seam: after publish the candidate path no longer exists
            # (os.replace moved it onto live).  Close the candidate handle so
            # the completed mark writes LIVE (the post-swap truth), never a
            # stale inode or a recreated empty .build file.
            try:
                _shadow.close_candidate_conn()
            except Exception:  # noqa: BLE001
                pass
            _candidate_conn = None
            _mark_target = None

        # Final state: full builds report completed with their own totals; a
        # scoped (papers) build must report GLOBAL progress — its own total
        # is just the requested subset, and claiming completed would hide
        # the remaining missing papers (false ready, no resume action).
        if keys is not None:
            _final_status, _final_current, _final_total, _final_message = (
                _scoped_global_progress(vault, items, _db_path)
            )
        else:
            _final_status, _final_current, _final_total, _final_message = (
                "completed", total, total, ""
            )

        _mark(
            status=_final_status,
            current=_final_current,
            total=_final_total,
            finished_at=_now(),
            message=_final_message,
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


        data = {
            "papers_embedded": papers_embedded,
            "papers_skipped": papers_skipped,
            "chunks_embedded": chunks_embedded,
            "model": get_embed_status(vault)["model"],
            "mode": get_embed_status(vault)["mode"],
        }
        result = PFResult(ok=True, command="embed build", version=PF_VERSION, data=data)
        if not json:
            # #137: exactly one terminal event, then EOF.
            from paperforge.core.ndjson import emit_terminal

            emit_terminal("result", "embed.build", result)
        if json:
            print(result.to_json())
        else:
            skipped = f" ({papers_skipped} skipped)" if papers_skipped else ""
            # #137: stdout carries machine output only — human summary → stderr.
            print(f"Embedded {papers_embedded} papers ({chunks_embedded} chunks){skipped}",
                  file=sys.stderr)
        # Build succeeded: delete pre-rebuild backup (in-place strategy only)
        if _rebuild_backup_path and _rebuild_backup_path.exists():
            _rebuild_backup_path.unlink()
            logger.info("Deleted pre-rebuild backup after successful rebuild")
        if _write_lock:
            _write_lock.__exit__(None, None, None)
        _restore_stop()
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
            if json:
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
            _mark(status="failed", message=str(e), pid=0)
        except Exception:
            pass
        result = PFResult(
            ok=False,
            command="embed build",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
        )
        if json:
            print(result.to_json())
        else:
            from paperforge.core.ndjson import emit_terminal

            emit_terminal("error", "embed.build", result)
            print(result.error.message, file=sys.stderr)
        return 1
    finally:
        if _write_lock:
            _write_lock.__exit__(None, None, None)
        _restore_stop()