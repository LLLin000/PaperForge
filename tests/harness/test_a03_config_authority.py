"""A03 — config authority: canonical write, resolver semantics, fail-closed edit.

Ported from the H case that drives the settings form.  Its subject is what a
config edit does to the canonical document and to the resolved paths — both
file-level facts — plus the invariant that an invalid edit leaves the document
byte-identical.

Note for whoever reads the failure detail: the directory fields are
**resources-relative**.  Setting ``literature_dir`` to ``Resources/Literature``
is accepted and resolves to ``Resources/Resources/Literature`` (observed while
probing this case), so the assertion below pins the *resolved* path rather than
the raw field.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .canonical import vault_config

pytestmark = pytest.mark.harness

CASE_ID = "A03"
TITLE = "A config edit is canonical, resolvable, and rejects escapes without writing"
HOST_SPEC_CASE = (
    "A03 config edit: a path set in Settings reaches paperforge.json, doctor reads "
    "it back, and a restart keeps it"
)

FIELD = "control_dir"
VALUE = "LiteratureControlHarness"


def test_config_edit_is_canonical_and_validated(cli, vault, case) -> None:
    config_path = vault / "paperforge.json"
    original = config_path.read_bytes()

    edited = cli.json("config", "set", FIELD, VALUE)
    case.check("config set exits 0", edited.returncode == 0, edited.tail())
    case.check("the canonical document changed", config_path.read_bytes() != original, "byte-identical")

    stored = vault_config(vault).get("vault_config") or {}
    case.check(
        "the value is stored in the canonical document",
        str(stored.get(FIELD, "")) == VALUE,
        json.dumps(stored)[:300],
    )
    case.check(
        "config get reads the value back",
        cli.config_get(FIELD) == VALUE,
        cli.config_get(FIELD),
    )

    validated = cli.json("config", "validate")
    case.check(
        "the document still validates",
        (validated.data or {}).get("state") == "valid",
        json.dumps(validated.data)[:200],
    )

    paths = cli.json("config", "paths")
    resolved_raw = ((paths.data or {}).get("paths") or {}).get("control", "")
    expected = vault / "Resources" / VALUE
    # Resolve both sides: the resolver canonicalizes the vault prefix (on Windows a
    # CI temp directory arrives in its short form, e.g. RUNNER~1), so comparing the
    # unresolved pair would compare two spellings of the same path.
    resolved = Path(str(resolved_raw))
    case.check(
        "the resolver places the value under the resources directory",
        bool(str(resolved_raw)) and resolved.resolve() == expected.resolve(),
        f"resolved={resolved_raw!r} expected={str(expected)!r}",
    )

    before_refusal = config_path.read_bytes()
    refused = cli.json("config", "set", FIELD, "../escape", expect=None)
    case.check("an escaping value is refused", refused.returncode != 0, f"rc={refused.returncode}")
    case.check(
        "the refusal names the validation failure",
        "config.invalid" in f"{refused.stdout}{refused.stderr}",
        (refused.stdout or refused.stderr)[:200],
    )
    case.check(
        "a refused edit leaves the canonical document byte-identical",
        config_path.read_bytes() == before_refusal,
        "the document changed on a refused edit",
    )

    # Every CLI call is its own process, so this is the restart leg the H case
    # proves through a window reload.
    case.check(
        "the value survives a new process",
        cli.config_get(FIELD) == VALUE,
        cli.config_get(FIELD),
    )

    case.artifact("paperforge.json", config_path)
