"""A06 — canonical config is what the provider request actually uses.

Ported from the H case that saves provider settings in the UI and then observes a
controlled request.  Its subject is authority, not plumbing: the value written through
the product's own command is the value the next process sends, a changed value is
picked up, and a broken endpoint fails the build instead of silently falling back to
anything else.

Every CLI call is a new process, which is the restart leg the H version proves through
a window reload.
"""

from __future__ import annotations

import json

import pytest

from .evidence import digest, tree_digest

pytestmark = pytest.mark.harness

CASE_ID = "A06"
TITLE = "The provider request uses canonical config, and a change is picked up"
HOST_SPEC_CASE = (
    "proves provider config authority through UI, restart, and a controlled embed request"
)

PAPER = "TSTONE001"


def test_provider_requests_follow_canonical_config(retrieval, case) -> None:
    cli, stub = retrieval.cli, retrieval.stub
    indexes = cli.vault / "System" / "PaperForge" / "indexes"

    built = cli.json("memory", "build")
    case.check("memory build exits 0", built.returncode == 0, built.tail())
    first = cli.json("embed", "build")
    case.check("the first build exits 0", first.returncode == 0, first.tail())
    case.check(
        "the first request carried the configured model",
        any(row.get("model") == "stub-embedding" for row in stub.requests),
        json.dumps(stub.requests[:2]),
    )

    # A changed value must reach the next request: same process family, new config.
    changed = cli.config_set("vector_db_api_model", "stub-embedding-v2")
    case.check("the model change exits 0", changed.returncode == 0, changed.tail())
    stub.reset()
    forced = cli.json("embed", "build", "--force")
    case.check("the forced rebuild exits 0", forced.returncode == 0, forced.tail())
    case.check(
        "the rebuild request carried the changed model",
        any(row.get("model") == "stub-embedding-v2" for row in stub.requests),
        json.dumps(stub.requests[:2]),
    )

    # A dead endpoint must fail the build, not fall back to something else.
    db = indexes / "paperforge.db"
    before = tree_digest(indexes)
    before_db = digest(db) if db.is_file() else ""
    dead = cli.config_set("vector_db_api_base", "http://127.0.0.1:9")
    case.check("the endpoint change exits 0", dead.returncode == 0, dead.tail())
    failed = cli.run("embed", "build", "--force", "--json", expect=None)
    case.check(
        "a dead endpoint fails the build",
        failed.returncode != 0,
        f"rc={failed.returncode} {(failed.stdout or failed.stderr)[-200:]}",
    )
    case.check(
        "the failed build left the live substrate alone",
        digest(db) == before_db and tree_digest(indexes) == before,
        f"db changed={digest(db) != before_db} files={sorted(set(before) ^ set(tree_digest(indexes)))}",
    )

    case.artifact("indexes", indexes)
