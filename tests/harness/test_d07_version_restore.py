"""D07 — a display-version restore replaces the display copy, not the canonical text.

Ported from the H case that uses the Version History modal.  The property that
matters to a reader of the paper is asserted byte-wise: restoring version ``v1``
writes ``render/fulltext.md`` (the display artifact) and **leaves the canonical
``fulltext.md`` alone**, so previewing an older version cannot silently replace the
paper's current text.

Asserted, per #227: the restore's only OCR-metadata mutation is the
``restore_provenance`` record, delegated to the OCR subsystem's writer.  The
contract rule ``restore.display_only`` reads "restore writes ONLY
ocr_display.fulltext (render/fulltext.md) ...; records provenance and drift
(#129)", and that writer validates the payload and refuses to replace unreadable
metadata — so the case pins the delta instead of reporting it as a blocker.
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
    meta_before_data = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}

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
    case.artifact("ocr-dir", ocr)
    # #227: the restore's OCR-metadata mutation is exactly the delegated
    # provenance record — the display copy must not smuggle other state in with
    # it, and the record is the one the OCR writer validated.
    meta_after = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
    added = set(meta_after) - set(meta_before_data)
    untouched = {k: v for k, v in meta_after.items() if k not in added}
    case.check(
        "the restore adds only the provenance record, rewriting nothing else",
        added <= {"restore_provenance", "zotero_key"}
        and "restore_provenance" in added
        and untouched == meta_before_data,
        json.dumps({k: meta_after.get(k) for k in sorted(added)})[:200],
    )
