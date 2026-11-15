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

    built = cli.json("embed", "build")
    case.check("embed build exits 0", built.returncode == 0, built.tail())
    data = built.data if isinstance(built.data, dict) else {}
    case.check(
        "chunks were embedded",
        int(data.get("chunks_embedded") or 0) >= 1,
        json.dumps(data)[:200],
    )
    case.check(
        "the configured model was used",
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

    case.artifact("memory-db", db)
