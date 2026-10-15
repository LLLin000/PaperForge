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

    # Slow the provider a little so the stop lands while the build is working.  The
    # trigger waits for the build to have actually reached the provider and produced a
    # further event: an embed build stopped before its first request is a different
    # (and worse) case - see the blocker below.  The timer is only the fallback.
    stub.delay_s = 0.4
    stub.reset()
    run = cli.action_stream(
        "embed.build",
        (),
        confirm="embed.build",
        timeout_s=120,
        stop_on=lambda event: bool(stub.requests)
        and event.get("event") in ("phase", "progress", "item_result", "paper_settled"),
        stop_after_s=40,
    )

    case.check(
        "the build announced a phase before the stop",
        any(event.get("event") == "phase" for event in run.events),
        json.dumps(run.events[:4])[:300],
    )
    stopped_cleanly = (run.terminal or {}).get("event") == "cancelled" and run.returncode == 130
    if run.stopped_by == "deadline" and not stopped_cleanly:
        # The fallback timer had to fire, i.e. the build had not reached the provider and
        # there was no later event to trigger on.  A stop *there* is not honoured: the
        # child produces no further output and must be killed (observed at 90s and 420s,
        # and once at 180s).  Same stdin token, later in the run, cancels cleanly.
        case.blocked(
            "a PAPERFORGE_STOP written before the build reaches its provider is not "
            "honoured: the child produced no further output and was killed after "
            f"{run.duration_ms // 1000}s with no terminal event (the live substrate was "
            "never touched). On Windows this stdin token is the only cooperative "
            "ingress - SIGTERM is a hard kill - so the plugin's Stop only ends such a "
            "build through its kill escalation."
        )
    elif not stopped_cleanly:
        case.check(
            "the stop is honoured with a cancelled terminal",
            False,
            f"rc={run.returncode} stopped_by={run.stopped_by!r} "
            f"terminal={json.dumps(run.terminal or {})[:200]}",
        )
    else:
        case.check(
            "the stop is honoured with a cancelled terminal",
            stopped_cleanly,
            f"rc={run.returncode} after {run.duration_ms // 1000}s "
            f"(stopped_by={run.stopped_by!r})",
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
