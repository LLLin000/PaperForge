from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.chunker import chunk_fulltext
from paperforge.memory.state_snapshot import write_vector_runtime
from paperforge.memory.vector_db import (
    delete_paper_vectors,
    embed_paper,
    get_collection,
    get_embed_status,
    get_vector_db_path,
    mark_vector_build_state,
    read_vector_build_state,
)
from paperforge.worker.asset_index import read_index
from paperforge.worker.vector_db import _preflight_check
from paperforge import __version__ as PF_VERSION


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    sub = getattr(args, "embed_subcommand", "build")

    if sub == "status":
        status = get_embed_status(vault)
        status["build_state"] = read_vector_build_state(vault)

        # Write vector-runtime-state.json snapshot (JS-First Memory State)
        _dep_missing = []
        try:
            import chromadb  # noqa: F401
        except ImportError:
            _dep_missing.append("chromadb")
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            _dep_missing.append("sentence_transformers")
        try:
            import openai  # noqa: F401
        except ImportError:
            _dep_missing.append("openai")
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
            build_state=status.get("build_state"),
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
            except Exception:
                pass
            mark_vector_build_state(vault, status="stopping", message="Stop requested")
        result = PFResult(ok=True, command="embed stop", version=PF_VERSION,
                         data={"state": "stopping" if pid else "idle"})
        if args.json:
            print(result.to_json())
        else:
            print("Stop requested." if pid else "No active build.")
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

    import os as _os
    _now = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat
    mark_vector_build_state(vault,
        status="running",
        current=0, total=total, paper_id="",
        started_at=_now(), finished_at="",
        message="", pid=_os.getpid(),
        model=get_embed_status(vault)["model"],
        mode=get_embed_status(vault)["mode"],
    )

    if args.force:
        db_path = get_vector_db_path(vault)
        if db_path.exists():
            import shutil
            shutil.rmtree(str(db_path), ignore_errors=True)

    papers_embedded = 0
    chunks_embedded = 0
    papers_skipped = 0
    resume = getattr(args, "resume", False)
    i = 0
    for entry in done_papers:
        key = entry.get("zotero_key")
        fulltext_rel = entry.get("fulltext_path", "")
        if not fulltext_rel:
            continue
        fulltext_path = vault / fulltext_rel
        # Skip if already embedded and --resume is set
        if resume:
            try:
                collection = get_collection(vault)
                existing = collection.get(where={"paper_id": key}, limit=1)
                if existing and existing.get("ids") and len(existing["ids"]) > 0:
                    papers_skipped += 1
                    continue
            except Exception:
                pass
        chunks = chunk_fulltext(fulltext_path)
        if not chunks:
            continue
        try:
            i += 1
            print(f"EMBED_PROGRESS:{i}:{total}:{key}", flush=True)
            delete_paper_vectors(vault, key)
            n = embed_paper(vault, key, chunks)
            chunks_embedded += n
            papers_embedded += 1
            mark_vector_build_state(vault,
                current=i, paper_id=key,
                last_update=_now(),
            )
        except Exception as e:
            mark_vector_build_state(vault,
                status="failed", message=str(e), pid=0,
            )
            write_vector_runtime(
                vault,
                enabled=bool(get_embed_status(vault).get("mode", "")),
                mode=get_embed_status(vault)["mode"],
                model=get_embed_status(vault)["model"],
                deps_installed=True,
                deps_missing=None,
                py_version=sys.version.split()[0],
                db_exists=get_vector_db_path(vault).exists(),
                chunk_count=chunks_embedded,
                build_state=read_vector_build_state(vault),
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

    write_vector_runtime(
        vault,
        enabled=bool(get_embed_status(vault).get("mode", "")),
        mode=get_embed_status(vault)["mode"],
        model=get_embed_status(vault)["model"],
        deps_installed=True,
        deps_missing=None,
        py_version=sys.version.split()[0],
        db_exists=True,
        chunk_count=chunks_embedded,
        build_state=read_vector_build_state(vault),
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
