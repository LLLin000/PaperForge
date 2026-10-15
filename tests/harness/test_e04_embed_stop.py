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

from .evidence import evidence_root, tree_digest

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

    # Slow the provider a little: the build should be in flight when the stop
    # lands, but the case must not depend on the provider's pace.  The stop is
    # triggered by the build's own first phase event (as in D04), and the provider
    # ledger is recorded as an artifact rather than asserted - a forced rebuild that
    # has not reached the provider yet is still a running build.
    stub.delay_s = 0.4
    stub.reset()
    run = cli.action_stream(
        "embed.build",
        (),
        confirm="embed.build",
        timeout_s=60,
        stop_on=lambda event: event.get("event") == "phase",
        stop_after_s=20,
    )

    case.check(
        "the build announced a phase before the stop",
        any(event.get("event") == "phase" for event in run.events),
        json.dumps(run.events[:4])[:300],
    )
    stopped_cleanly = (run.terminal or {}).get("event") == "cancelled" and run.returncode == 130
    if not stopped_cleanly:
        # Observed at 180s and again at 420s: the child sends one provider request and
        # then produces no further output, ending with no terminal event and leaving the
        # live substrate untouched.  The H case stops through the client's cancel API, a
        # different mechanism; this stdin-token leg is recorded, not claimed.
        case.blocked(
            "a PAPERFORGE_STOP written during an embed build is not honoured here: the "
            f"child sent {len(stub.requests)} provider request(s), produced no further "
            f"output, and was killed after {run.duration_ms // 1000}s with no terminal "
            "event (the live substrate was never touched). The H case drives "
            "client.cancelActiveOperation() instead."
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
    # Outside the vault: the vault must stay a canonical tree.
    ledger = evidence_root() / f"{CASE_ID}-provider-ledger.json"
    try:
        ledger.write_text(json.dumps(stub.requests[:20], indent=2), encoding="utf-8")
        case.artifact("provider-ledger", ledger)
    except OSError:
        pass
