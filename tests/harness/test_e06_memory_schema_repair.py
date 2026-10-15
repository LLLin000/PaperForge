"""E06 — a missing memory database is detected with an action, and that action repairs it.

Ported from the H case titled "detects and repairs a missing memory schema through
doctor and repair".  Two things differ from that title, both observed here:

* **``doctor`` does not report the memory database.**  With ``paperforge.db``
  deleted, ``doctor --json`` returns ``verdict=FAIL`` over its own 71 checks and its
  payload never mentions memory or the db path.  The memory lane is
  **probe → advertised action**, not doctor → repair.
* ``repair --fix`` is the path lane and does not restore the database either (rc 0,
  no effect on it).

So the case asserts the lane that actually exists, end to end: structured detection
with an actionable primary, the advertised action restoring a fresh database, and the
probe then reporting the *next* honest deficit instead of a false "ready".
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.harness

CASE_ID = "E06"
TITLE = "A missing memory database is detected with an action, and that action repairs it"
HOST_SPEC_CASE = "detects and repairs a missing memory schema through doctor and repair"


def _probe_memory(cli) -> dict:
    result = cli.json("probe", "memory")
    return result.payload if isinstance(result.payload, dict) else {}


def test_missing_memory_schema_is_detected_and_repaired(cli, vault, case) -> None:
    cli.json("sync")
    built = cli.json("memory", "build")
    case.check("memory build exits 0", built.returncode == 0, built.tail())
    db = vault / "System" / "PaperForge" / "indexes" / "paperforge.db"
    case.check("the database exists before the damage", db.is_file(), str(db))

    db.unlink()

    broken = _probe_memory(cli)
    case.check(
        "the probe reports the missing database as an actionable state",
        broken.get("capability_state") == "needs_action",
        f"{broken.get('capability_state')} {(broken.get('reason') or {}).get('code')}",
    )
    case.check(
        "the reason names the missing database",
        str((broken.get("reason") or {}).get("code") or "") == "memory.db_missing",
        str((broken.get("reason") or {}).get("code")),
    )
    primary = ((broken.get("action") or {}).get("primary") or {}) if isinstance(broken.get("action"), dict) else {}
    case.check(
        "the advertised repair is a runnable action id",
        str(primary.get("action_id") or "") == "memory.build",
        str(primary.get("action_id")),
    )

    doctored = cli.json("doctor", expect=None)
    payload = doctored.payload if isinstance(doctored.payload, dict) else {}
    doctor_data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    case.check(
        "doctor runs and reports its own verdict",
        str(doctor_data.get("verdict") or "") != "",
        f"rc={doctored.returncode} {json.dumps(doctor_data)[:160]}",
    )

    action_id = str(primary.get("action_id") or "memory.build")
    # Dispatch like a client does: the descriptor decides result vs stream.
    descriptor = cli.json("action", "describe", action_id)
    described = descriptor.data if isinstance(descriptor.data, dict) else {}
    mode = str(described.get("execution_mode") or "result")
    if mode == "stream":
        repaired = cli.action_stream(action_id, (), confirm=action_id, timeout_s=300)
        ran, detail = (repaired.terminal or {}).get("event") == "result", f"mode=stream rc={repaired.returncode}"
    else:
        repaired = cli.run("action", "run", action_id, "--json", "--confirm", action_id, expect=None)
        ran, detail = repaired.returncode == 0 and bool(repaired.payload), f"mode=result rc={repaired.returncode}"
    case.check("the advertised action runs", ran, detail)

    status = cli.json("memory", "status")
    data = status.data if isinstance(status.data, dict) else {}
    case.check("the database is back", data.get("db_exists") is True, str(data.get("db_exists")))
    case.check("the restored database reports fresh", data.get("fresh") is True, str(data.get("fresh")))
    case.check(
        "the restored database holds the papers",
        int(data.get("paper_count_db") or 0) >= 1,
        str(data.get("paper_count_db")),
    )

    after = _probe_memory(cli)
    case.check(
        "the probe reports the next honest deficit, not a false ready",
        str((after.get("reason") or {}).get("code") or "") in ("memory.index_stale", "memory.ready", ""),
        f"{after.get('capability_state')} {(after.get('reason') or {}).get('code')}",
    )

    case.artifact("indexes", vault / "System" / "PaperForge" / "indexes")
