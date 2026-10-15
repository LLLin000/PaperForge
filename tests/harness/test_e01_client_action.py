"""E01 — one action, dispatched the way a client dispatches it.

Ported from the H case that clicks a dashboard action.  The subject is the client
contract: the descriptor says whether the action is executable and in which mode, the
preflight says whether it may run now, and the run's side effects are visible in the
store it owns.
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.harness

CASE_ID = "E01"
TITLE = "A client action is described, preflighted and executed with its effects"
HOST_SPEC_CASE = "executes an action through the client (memory.build)"

ACTION = "memory.build"


def _descriptor(cli) -> dict:
    listed = cli.json("action", "describe", ACTION)
    data = listed.data if isinstance(listed.data, dict) else {}
    return data


def test_action_round_trip(cli, vault, case) -> None:
    cli.json("sync")

    described = _descriptor(cli)
    case.check(
        "the descriptor names an execution mode",
        str(described.get("execution_mode") or "") in ("result", "stream"),
        json.dumps(described)[:200],
    )
    case.check(
        "the descriptor declares its availability",
        isinstance(described.get("availability"), str) and bool(described.get("availability")),
        str(described.get("availability")),
    )

    preflight = cli.json("action", "preflight", ACTION)
    case.check("preflight exits 0", preflight.returncode == 0, preflight.tail())

    # Dispatch like a client does: the descriptor decides result vs stream.
    mode = str(described.get("execution_mode") or "result")
    if mode == "stream":
        ran = cli.action_stream(ACTION, (), confirm=ACTION, timeout_s=300)
        settled = (ran.terminal or {}).get("event") == "result"
        detail = f"mode=stream rc={ran.returncode} {json.dumps(ran.terminal or {})[:200]}"
    else:
        ran = cli.run("action", "run", ACTION, "--json", "--confirm", ACTION, expect=None)
        settled = ran.returncode == 0 and bool(ran.payload)
        detail = f"mode=result rc={ran.returncode} {(ran.stdout or ran.stderr)[-200:]}"
    case.check("the action settles with a result", settled, detail)

    db = vault / "System" / "PaperForge" / "indexes" / "paperforge.db"
    case.check("the action wrote the database it owns", db.is_file(), str(db))
    status = cli.json("memory", "status")
    data = status.data if isinstance(status.data, dict) else {}
    case.check("the store reports fresh after the action", data.get("fresh") is True, str(data.get("fresh")))
    case.check(
        "the store holds the synced papers",
        int(data.get("paper_count_db") or 0) >= 1,
        str(data.get("paper_count_db")),
    )

    case.artifact("indexes", vault / "System" / "PaperForge" / "indexes")
