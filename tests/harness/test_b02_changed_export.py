"""B02 — a changed export entry syncs; every bystander paper is left alone.

The failure this guards is the one #219 shipped: an unrelated sync path
overwrote canonical content and downgraded completed papers.  The oracle is
byte-level, not a status badge.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.harness

CASE_ID = "B02"
TITLE = "Changed export entry syncs, bystanders stay byte-identical"
HOST_SPEC_CASE = "syncs exactly the changed export entry and preserves the bystander paper"

NEW_KEY = "FIXT0010"


def _note_digests(literature: Path) -> dict[str, str]:
    import hashlib

    return {
        note.name: hashlib.sha256(note.read_bytes()).hexdigest()
        for note in sorted(literature.rglob("*.md"))
    }


def _append_export_entry(export: Path, key: str) -> None:
    data = json.loads(export.read_text(encoding="utf-8"))
    items = data["items"]
    template = json.loads(json.dumps(items[0]))  # deep copy of a known-good entry
    template.update(
        {
            "key": key,
            "itemKey": key,
            "title": f"Bystander probe: {key} added by the CLI-host harness",
            "DOI": f"10.9999/harness.{key.lower()}",
        }
    )
    template["attachments"] = [{"path": f"storage:{key}/{key}.pdf", "contentType": "application/pdf"}]
    items.append(template)
    export.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_only_the_changed_entry_moves(cli, vault, case) -> None:
    first = cli.json("sync")
    case.check("baseline sync exits 0", first.returncode == 0, first.tail())

    literature = vault / "Resources" / "Literature"
    before = _note_digests(literature)
    case.check("baseline produced notes", len(before) >= 9, f"{len(before)} notes")

    export = vault / "System" / "PaperForge" / "exports" / "orthopedic.json"
    _append_export_entry(export, NEW_KEY)
    storage = vault / "System" / "Zotero" / "storage" / NEW_KEY
    storage.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        vault / "System" / "Zotero" / "storage" / "FIXT0001" / "FIXT0001.pdf",
        storage / f"{NEW_KEY}.pdf",
    )

    second = cli.json("sync")
    case.check("changed-export sync exits 0", second.returncode == 0, second.tail())

    after = _note_digests(literature)
    case.check(
        "the new export entry got a note",
        f"{NEW_KEY}.md" in after,
        f"notes now: {sorted(after)}",
    )

    changed = sorted(name for name, digest in before.items() if after.get(name) != digest)
    case.check("bystander notes are byte-identical", not changed, f"rewritten: {changed}")

    dashboard = cli.json("dashboard")
    stats = (dashboard.data or {}).get("stats", {}) if isinstance(dashboard.data, dict) else {}
    case.check(
        "paper count grew by exactly one",
        stats.get("papers") == len(before) + 1,
        f"papers={stats.get('papers')} before={len(before)}",
    )

    case.artifact("notes", literature)
    case.artifact("dashboard", vault / "System" / "PaperForge" / "indexes" / "formal-library.json")
