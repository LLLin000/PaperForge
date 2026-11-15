"""E03 — the vector substrate builds against the configured provider and serves a search.

Ported from the H case that drives Smart Retrieval.  The oracle is stronger here:
the provider's own request ledger proves the build went to the configured
endpoint (not to a local fallback), and the search result names the retrieval
unit it came from.

One property worth knowing while writing more retrieval cases: the substrate binds
to the provider endpoint it was built with, so re-pointing the endpoint between a
build and a query makes the query return nothing.  A case must keep one stub for
the whole flow (a re-pointed provider is not the same substrate's provider).
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.harness

CASE_ID = "E03"
TITLE = "The substrate builds against the configured provider and serves a search"
HOST_SPEC_CASE = "builds the vector substrate against a controlled provider and serves deep search"

PAPER = "TSTONE001"


def test_substrate_builds_and_serves_search(retrieval, case) -> None:
    cli, stub = retrieval.cli, retrieval.stub

    memory = cli.json("memory", "build")
    case.check("memory build exits 0", memory.returncode == 0, memory.tail())
    db = cli.vault / "System" / "PaperForge" / "indexes" / "paperforge.db"
    case.check("the memory database was written", db.is_file(), str(db))
    case.check(
        "the canonical index was indexed into memory",
        int((memory.data or {}).get("papers_indexed") or 0) >= 1,
        json.dumps(memory.data or {})[:200],
    )

    built = cli.action_stream(
        "embed.build", (), confirm="embed.build", timeout_s=300
    )
    terminal = built.terminal or {}
    action_result = terminal.get("result")
    action_result = action_result if isinstance(action_result, dict) else {}
    data = action_result.get("data")
    data = data if isinstance(data, dict) else {}
    case.check(
        "registry embed.build settles with a result terminal",
        terminal.get("event") == "result" and action_result.get("ok") is True,
        json.dumps(terminal)[:300],
    )
    case.check("registry embed.build exits 0", built.returncode == 0, f"rc={built.returncode}")
    case.check(
        "registry build embeds chunks",
        int(data.get("chunks_embedded") or 0) >= 1,
        json.dumps(data)[:200],
    )
    case.check(
        "registry build uses the configured model",
        str(data.get("model") or "") == "stub-embedding",
        str(data.get("model")),
    )
    case.check(
        "the configured provider was actually called",
        int(stub.counts.get("requests") or 0) >= 1,
        json.dumps(stub.counts),
    )

    resumed = cli.json("embed", "build", "--resume")
    resume_data = resumed.data if isinstance(resumed.data, dict) else {}
    case.check(
        "a resume build finds nothing left to embed",
        int(resume_data.get("papers_embedded") or 0) == 0,
        json.dumps(resume_data)[:200],
    )

    registry_resumed = cli.action_stream(
        "embed.resume", (), confirm="embed.resume", timeout_s=300
    )
    registry_terminal = registry_resumed.terminal or {}
    registry_result = registry_terminal.get("result")
    registry_result = registry_result if isinstance(registry_result, dict) else {}
    registry_data = registry_result.get("data")
    registry_data = registry_data if isinstance(registry_data, dict) else {}
    case.check(
        "registry embed.resume settles with a result terminal",
        registry_terminal.get("event") == "result"
        and registry_result.get("ok") is True
        and registry_resumed.returncode == 0,
        json.dumps(registry_terminal)[:300],
    )
    case.check(
        "registry resume finds no completed work to repeat",
        int(registry_data.get("papers_embedded") or 0) == 0,
        json.dumps(registry_data)[:200],
    )

    status = cli.json("embed", "status")
    build_state = ((status.data or {}).get("build_state") or {}) if isinstance(status.data, dict) else {}
    case.check(
        "the substrate reports the provider's dimension",
        int(build_state.get("vector_dimension") or 0) == stub.dim,
        str(build_state.get("vector_dimension")),
    )
    case.check(
        "the substrate records the endpoint it was built with",
        str(build_state.get("vector_provider_endpoint") or "") == stub.base_url,
        str(build_state.get("vector_provider_endpoint")),
    )

    before_query = int(stub.counts.get("requests") or 0)
    found = cli.json("retrieve", "suture anchor fixation", "--limit", "3")
    case.check("retrieve exits 0", found.returncode == 0, found.tail())
    hits = (found.data or {}).get("matches") or []
    case.check("the search returns hits", len(hits) >= 1, json.dumps(found.data or {})[:300])
    first = hits[0] if hits else {}
    case.check(
        "the hit names the paper it came from",
        str(first.get("zotero_key") or "") == PAPER,
        json.dumps(first)[:200],
    )
    case.check(
        "the hit names the retrieval unit",
        bool(first.get("unit_id")) and bool(first.get("text")),
        json.dumps({k: first.get(k) for k in ("unit_id", "source_kind")})[:200],
    )
    case.check(
        "the query itself went through the configured provider",
        int(stub.counts.get("requests") or 0) > before_query,
        json.dumps(stub.counts),
    )

    from paperforge.memory.db import ensure_vec_extension, get_connection, get_memory_db_path

    conn = get_connection(get_memory_db_path(cli.vault))
    ensure_vec_extension(conn)
    try:
        rows = conn.execute(
            "SELECT rowid FROM vec_body_meta WHERE paper_id = ?", (PAPER,)
        ).fetchall()
        case.check("the substrate contains body vectors before interruption", bool(rows), str(len(rows)))
        for row in rows:
            conn.execute("DELETE FROM vec_body WHERE rowid = ?", (row["rowid"],))
            conn.execute("DELETE FROM vec_body_meta WHERE rowid = ?", (row["rowid"],))
        conn.commit()
        remaining = conn.execute(
            "SELECT (SELECT COUNT(*) FROM vec_fulltext_meta WHERE paper_id = ?) "
            "+ (SELECT COUNT(*) FROM vec_objects_meta WHERE paper_id = ?)",
            (PAPER, PAPER),
        ).fetchone()[0]
        case.check("other vector families survive the interruption", int(remaining) > 0, str(remaining))
    finally:
        conn.close()

    before_resume = int(stub.counts.get("requests") or 0)
    resumed_missing = cli.action_stream(
        "embed.resume", (), confirm="embed.resume", timeout_s=300
    )
    missing_terminal = resumed_missing.terminal or {}
    missing_result = missing_terminal.get("result")
    missing_result = missing_result if isinstance(missing_result, dict) else {}
    missing_data = missing_result.get("data")
    missing_data = missing_data if isinstance(missing_data, dict) else {}
    case.check(
        "registry embed.resume settles after missing vectors",
        missing_terminal.get("event") == "result"
        and missing_result.get("ok") is True
        and resumed_missing.returncode == 0,
        json.dumps(missing_terminal)[:300],
    )
    case.check(
        "registry resume rebuilds the incomplete paper",
        int(missing_data.get("papers_embedded") or 0) == 1
        and int(missing_data.get("chunks_embedded") or 0) > 0,
        json.dumps(missing_data)[:200],
    )
    case.check(
        "registry resume calls the configured provider",
        int(stub.counts.get("requests") or 0) > before_resume,
        json.dumps(stub.counts),
    )
    conn = get_connection(get_memory_db_path(cli.vault))
    try:
        restored_body_rows = conn.execute(
            "SELECT COUNT(*) FROM vec_body_meta WHERE paper_id = ?", (PAPER,)
        ).fetchone()[0]
    finally:
        conn.close()
    case.check("body vector metadata is restored", int(restored_body_rows) > 0, str(restored_body_rows))
    recovered = cli.json("retrieve", "suture anchor fixation", "--limit", "3")
    recovered_hits = (recovered.data or {}).get("matches") or []
    case.check("search still serves the resumed paper", len(recovered_hits) >= 1, recovered.tail())

    case.artifact("memory-db", db)
