from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

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
from paperforge.embedding.preflight import _preflight_check
from paperforge.memory.db import WriterLock, ensure_vec_extension, get_connection, get_memory_db_path, open_live_reader
from paperforge.memory.schema import ensure_schema
from paperforge.retrieval.manifest import RETRIEVAL_POLICY_VERSION, compute_body_units_hash, compute_object_units_hash
from paperforge.worker._progress import progress_bar
from paperforge.worker.asset_index import read_index


logger = logging.getLogger(__name__)

PR9B_MAX_WORKERS = 4

# P0-1: bumped when the persisted embedding identity gains fields — legacy
# libraries (built before recording) are rebuilt once so endpoint/model/
# dimension are stored and future comparisons are meaningful.
# (VECTOR_IDENTITY_VERSION lives in paperforge/embedding/substrate.py — the
# single source of truth shared by run_build, reconcile and preflight.)


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

    if sub == "migrate":
        from paperforge.embedding._chroma import migrate_chroma_to_vec0

        count = migrate_chroma_to_vec0(vault)

        result = PFResult(ok=True, command="embed migrate", version=PF_VERSION, data={"migrated": count})
        if args.json:
            print(result.to_json())
        else:
            print(f"Migrated {count} vectors from ChromaDB to vec0")
        return 0

    # Build — M3-B: canonical preconditions from the SERVICE (package +
    # credential authority).  Obsidian plugin settings are a caller, not
    # configuration authority — never read here.
    from paperforge.services.embedding import assess_embedding_preconditions

    preflight = assess_embedding_preconditions(vault)
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
            # #137: stream chosen → exactly-one terminal, then EOF.
            from paperforge.core.ndjson import emit_terminal

            emit_terminal("error", "embed.build", result)
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
        if args.json:
            print(result.to_json())
        else:
            # #137: stream chosen → exactly-one terminal, then EOF.
            from paperforge.core.ndjson import emit_terminal

            emit_terminal("error", "embed.build", result)
            print(result.error.message, file=sys.stderr)
        return 1

    items = envelope if isinstance(envelope, list) else envelope.get("items", [])
    # M3-A: the build core lives in the embedding SERVICE; the CLI is a
    # thin caller (parse → request → service → render).
    from paperforge.services.embedding import run_embedding_build

    return run_embedding_build(
        vault,
        items,
        keys=getattr(args, "keys", None),
        force=getattr(args, "force", False),
        resume=getattr(args, "resume", False),
        json=bool(getattr(args, "json", False)),
    )

