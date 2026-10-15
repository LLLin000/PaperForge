"""B01 — initial sync from the export into an empty derived state.

Host-agnostic: the subject is what `paperforge sync` materializes, not how a view
renders it.  Ported from the H spec case of the same name (see HOST_SPEC_CASE).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.harness

CASE_ID = "B01"
TITLE = "Initial sync from the export into empty derived state"
HOST_SPEC_CASE = "performs an initial sync from the export into empty derived state"

EXPECTED_PAPERS = 9


def _frontmatter(note: Path) -> dict[str, object]:
    parts = note.read_text(encoding="utf-8").split("---", 2)
    if len(parts) < 3:
        return {}
    import yaml

    return yaml.safe_load(parts[1]) or {}


def test_initial_sync_materializes_notes_and_index(cli, vault, case) -> None:
    synced = cli.json("sync")
    case.check("sync exits 0", synced.returncode == 0, synced.tail())

    literature = vault / "Resources" / "Literature"
    notes = sorted(literature.rglob("*.md"))
    case.check(
        f"sync creates one formal note per export entry ({EXPECTED_PAPERS})",
        len(notes) == EXPECTED_PAPERS,
        f"found {len(notes)} notes: {[n.name for n in notes][:12]}",
    )

    for note in notes:
        meta = _frontmatter(note)
        # Presence, not truthiness: a paper with no PDF legitimately carries
        # `has_pdf: false`, and that is not an incomplete note.
        missing = [
            field
            for field in ("zotero_key", "domain", "has_pdf", "ocr_status")
            if field not in meta
        ]
        case.check(f"frontmatter complete in {note.name}", not missing, f"missing {missing}")

    index = vault / "System" / "PaperForge" / "indexes" / "formal-library.json"
    case.check("canonical index written", index.is_file(), str(index))
    if index.is_file():
        index_payload = json.loads(index.read_text(encoding="utf-8"))
        items = index_payload.get("items", []) if isinstance(index_payload, dict) else []
        case.check(
            f"index carries every synced paper ({EXPECTED_PAPERS})",
            isinstance(items, list)
            and len(items) == EXPECTED_PAPERS
            and index_payload.get("paper_count") == EXPECTED_PAPERS,
            f"items={len(items) if isinstance(items, list) else 'n/a'} "
            f"paper_count={index_payload.get('paper_count') if isinstance(index_payload, dict) else 'n/a'}",
        )
        case.artifact("index", index)

    dashboard = cli.json("dashboard")
    stats = (dashboard.data or {}).get("stats", {}) if isinstance(dashboard.data, dict) else {}
    case.check(
        "dashboard reports the synced paper count",
        stats.get("papers") == EXPECTED_PAPERS,
        json.dumps(stats)[:300],
    )

    # A second sync on unchanged input must be a no-op, not a rewrite: the
    # re-sync case (B02) depends on this being true.
    before = {note.name: note.read_bytes() for note in notes}
    cli.json("sync")
    after = {note.name: note.read_bytes() for note in notes}
    rewritten = [name for name in before if before[name] != after.get(name)]
    case.check("re-sync of unchanged input rewrites nothing", not rewritten, f"rewritten: {rewritten}")

    case.artifact("notes", literature)
