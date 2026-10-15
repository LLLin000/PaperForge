"""D07 — a display-version restore replaces the display copy, not the canonical text.

Ported from the H case that uses the Version History modal.  The property that
matters to a reader of the paper is asserted byte-wise: restoring version ``v1``
writes ``render/fulltext.md`` (the display artifact) and **leaves the canonical
``fulltext.md`` alone**, so previewing an older version cannot silently replace the
paper's current text.

Recorded but not asserted, because it is a documentation question rather than a
behaviour one: the restore also rewrites OCR-owned ``meta.json`` (provenance), which
issue #227 tracks against the command's "display-only" wording.  The ADR that owns
this command lists "the restore_provenance mutation" as its own responsibility, so
the wording and the behaviour disagree - this case deliberately does not pick a
side.
"""

from __future__ import annotations

import json

import pytest

from .evidence import digest

pytestmark = pytest.mark.harness

CASE_ID = "D07"
TITLE = "A display-version restore writes the display copy and not the canonical text"
HOST_SPEC_CASE = "restores a display version through the Version History modal"

PAPER = "TSTONE001"


def test_display_restore_does_not_replace_the_canonical_text(render_cli, render_vault, case) -> None:
    cli = render_cli
    ocr = render_vault / "System" / "PaperForge" / "ocr" / PAPER
    canonical = ocr / "fulltext.md"
    display = ocr / "render" / "fulltext.md"
    meta = ocr / "meta.json"

    listed = cli.json("versions", "list")
    case.check("versions list exits 0", listed.returncode == 0, listed.tail())
    papers = ((listed.data or {}).get("papers") or []) if isinstance(listed.data, dict) else []
    row = next((item for item in papers if item.get("key") == PAPER), None)
    labels = [str(v.get("label")) for v in ((row or {}).get("versions") or [])]
    case.check("the fixture ships versions for the paper", "v1" in labels, str(labels))

    shown = cli.json("versions", "show", "--key", PAPER)
    case.check("versions show exits 0", shown.returncode == 0, shown.tail())

    canonical_before = digest(canonical)
    display_before = digest(display)
    meta_before = digest(meta)

    restored = cli.json("versions", "restore", "--key", PAPER, "--label", "v1")
    case.check("versions restore exits 0", restored.returncode == 0, restored.tail())
    data = restored.data if isinstance(restored.data, dict) else {}
    target = str(data.get("target_path") or "")
    case.check(
        "the restore names the display artifact it wrote",
        target.replace("\\", "/").endswith(f"{PAPER}/render/fulltext.md"),
        target[:160],
    )
    provenance = data.get("provenance") if isinstance(data.get("provenance"), dict) else {}
    case.check(
        "the restore records which version was shown",
        str(provenance.get("label") or "") == "v1" and data.get("provenance_persisted") is True,
        json.dumps(data.get("provenance"))[:200],
    )

    case.check(
        "the canonical text is not replaced by the display copy",
        digest(canonical) == canonical_before,
        "canonical fulltext.md changed during a display restore",
    )
    case.check(
        "the display copy was actually written",
        digest(display) != display_before,
        "render/fulltext.md did not change",
    )
    # Recorded, not asserted: the meta rewrite is what #227 questions.
    case.artifact("ocr-dir", ocr)
    if digest(meta) != meta_before:
        case.blocked(
            "display restore rewrites OCR-owned meta.json (provenance); issue #227 tracks "
            "whether that matches the command's display-only declaration"
        )
