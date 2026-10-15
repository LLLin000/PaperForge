"""B07 — workflow flags live on the canonical note, and a refusal is atomic.

Ported from the two H cases that toggle the flag through the dashboard.  The
regression this guards is #230: ``note set-flag`` resolved a stale flat
``note_path`` and failed for every workspace-layout paper — which is every paper
this vault has, since notes live at
``Resources/Literature/<domain>/<key> - <title>/<key>.md``.
"""

from __future__ import annotations

import os
import stat

import pytest

from .canonical import frontmatter

pytestmark = pytest.mark.harness

CASE_ID = "B07"
TITLE = "A workflow flag persists on the canonical note and a refused toggle writes nothing"
HOST_SPEC_CASE = "persists a workflow flag toggled in the UI, across a restart"

KEY = "FIXT0001"
FIELD = "do_ocr"


def _set_flag(cli, value: str, *, expect: int | None):
    return cli.json(
        "note", "set-flag", "--key", KEY, "--field", FIELD, "--value", value, expect=expect
    )


def test_flag_persists_and_refusals_are_atomic(cli, vault, case) -> None:
    cli.json("sync")

    note = cli.note(KEY)
    case.check("the workspace-layout note resolves", note.is_file(), str(note))
    case.check(
        "the note is not the legacy flat path",
        note.parent.name != "Literature",
        str(note.relative_to(vault)),
    )

    enabled = _set_flag(cli, "true", expect=0)
    case.check("set-flag exits 0", enabled.returncode == 0, enabled.tail())
    case.check(
        "the flag is true on the canonical note",
        frontmatter(note).get(FIELD) is True,
        str(frontmatter(note).get(FIELD)),
    )
    reported = str((enabled.data or {}).get("note_path") or "")
    case.check(
        "the command reports the canonical note it wrote",
        reported.replace("\\", "/").endswith(note.relative_to(vault).as_posix()),
        reported[:160],
    )

    repeated = _set_flag(cli, "true", expect=0)
    case.check("repeating the same value is accepted", repeated.returncode == 0, repeated.tail())
    case.check(
        "the flag is still true after the repeat",
        frontmatter(note).get(FIELD) is True,
        str(frontmatter(note).get(FIELD)),
    )

    before = note.read_bytes()
    os.chmod(note, stat.S_IREAD)
    try:
        refused = _set_flag(cli, "false", expect=None)
    finally:
        os.chmod(note, stat.S_IWRITE)

    case.check("a refused toggle is reported as a failure", refused.returncode != 0, f"rc={refused.returncode}")
    case.check(
        "the refusal is a payload, not a traceback",
        "Traceback" not in refused.stderr,
        refused.stderr[-200:],
    )
    case.check(
        "a refused toggle leaves the note byte-identical",
        note.read_bytes() == before,
        "the note changed on a refused write",
    )
    case.check(
        "the flag is still true after the refusal",
        frontmatter(note).get(FIELD) is True,
        str(frontmatter(note).get(FIELD)),
    )

    case.artifact("note", note)
