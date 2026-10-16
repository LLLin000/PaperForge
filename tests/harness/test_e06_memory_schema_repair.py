"""E06 — a missing memory database is diagnosed and recovered through the advertised action.

The contract this case asserts is the lane the product publishes: ``probe memory``
reports ``memory.db_missing`` with a primary action, that action rebuilds the
database, and the probe then reports the next honest state.

The H case this was ported from was titled "detects and repairs a missing memory
schema through doctor and repair". That title is retired (#329) because neither half
holds:

* ``doctor`` is a partial diagnostic surface, not the module-state aggregator. With
  ``paperforge.db`` deleted it returns ``verdict=FAIL`` over its own 71 checks and its
  payload never mentions memory; its vector-orphan check only runs while the database
  exists, so a deleted database is outside what it inspects. That is the interface's
  scope, not an omission to patch here — extending it would grow a second Memory state
  machine inside ``doctor``.
* ``repair --fix`` is the path lane and does not restore the database (rc 0, no effect
  on it).

A unified diagnosis surface is a separate design question; this case pins the
probe → advertised action → probe lane end to end.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.harness

CASE_ID = "E06"
TITLE = "A missing memory database is diagnosed and recovered through the advertised action"
HOST_SPEC_CASE = (
    "retired H title: detects and repairs a missing memory schema through doctor and repair"
)


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
    after_state = str(after.get("capability_state") or "")
    after_code = str((after.get("reason") or {}).get("code") or "")
    case.check(
        "the probe reports the next honest state, not a false ready",
        after_state == "ready" or (after_state == "needs_action" and after_code == "memory.index_stale"),
        f"{after_state} {after_code}",
    )

    case.artifact("indexes", vault / "System" / "PaperForge" / "indexes")
