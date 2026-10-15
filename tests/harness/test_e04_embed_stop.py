"""E04 — a stopped vector build leaves the live substrate untouched and serving.

Ported from the H case that clicks Stop during a build.  The oracle here is
byte-level: the published substrate must be *identical* after a stopped forced
build, and it must still answer a search afterwards - a partial candidate that
leaked into the live database would show up as changed bytes.

The provider is the same stub the substrate was built with, switched to a mode
that never answers; re-pointing the endpoint instead would be a different
substrate's provider (see E03).
"""

from __future__ import annotations

import json

import pytest

from .evidence import tree_digest

pytestmark = pytest.mark.harness

CASE_ID = "E04"
TITLE = "A stopped vector build leaves the live substrate byte-identical and serving"
HOST_SPEC_CASE = "stops a running vector build without corrupting the substrate"


def test_stop_leaves_the_substrate_intact(retrieval, case) -> None:
    cli, stub = retrieval.cli, retrieval.stub
    indexes = cli.vault / "System" / "PaperForge" / "indexes"

    built = cli.json("memory", "build")
    case.check("memory build exits 0", built.returncode == 0, built.tail())
    embedded = cli.json("embed", "build")
    case.check("the substrate builds first", embedded.returncode == 0, embedded.tail())

    before = tree_digest(indexes)
    case.check("the substrate is on disk", bool(before), str(indexes))

    # Slow the provider instead of hanging it: the build must stay observable at
    # its own safe points.  A hung request is never a checkpoint - the SDK times
    # out first and the run ends as INTERNAL_ERROR, not as a cancellation.
    stub.delay_s = 1.5
    stub.reset()
    run = cli.action_stream(
        "embed.build",
        (),
        confirm="embed.build",
        timeout_s=180,
        stop_on=lambda event: int(len(stub.requests)) >= 1
        and event.get("event") in ("phase", "progress", "item_result", "preflight"),
        stop_after_s=45,
    )

    case.check(
        "the build reached the provider before the stop",
        len(stub.requests) >= 1,
        json.dumps(stub.counts),
    )
    case.check(
        "the stop returns the documented exit code",
        run.returncode == 130,
        f"rc={run.returncode} terminal={json.dumps(run.terminal or {})[:200]}",
    )
    case.check(
        "the terminal event is cancelled",
        (run.terminal or {}).get("event") == "cancelled",
        json.dumps(run.terminal or {})[:300],
    )

    after = tree_digest(indexes)
    case.check(
        "the live substrate is byte-identical after a stopped build",
        after == before,
        f"changed: {sorted(set(before) ^ set(after)) or [k for k in before if before[k] != after.get(k)]}",
    )
    leftovers = [
        path.name
        for path in indexes.iterdir()
        if path.is_file() and (path.suffix in {".tmp", ".candidate"} or "candidate" in path.name)
    ]
    case.check("no candidate artifact leaked into the substrate directory", not leftovers, str(leftovers))

    # It must still serve: unchanged bytes are worthless if the store is unreadable.
    stub.delay_s = 0.0
    found = cli.json("retrieve", "rotator cuff repair", "--limit", "3")
    hits = (found.data or {}).get("matches") or []
    case.check("retrieve exits 0 after the stopped build", found.returncode == 0, found.tail())
    case.check(
        "the previous substrate still answers a search",
        len(hits) >= 1,
        json.dumps(found.data or {})[:300],
    )

    status = cli.json("embed", "status")
    build_state = ((status.data or {}).get("build_state") or {}) if isinstance(status.data, dict) else {}
    case.check(
        "the substrate still reports its dimension",
        int(build_state.get("vector_dimension") or 0) == stub.dim,
        str(build_state.get("vector_dimension")),
    )

    case.artifact("indexes", indexes)
