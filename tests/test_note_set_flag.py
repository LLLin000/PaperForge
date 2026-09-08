"""``paperforge note set-flag`` — Python-authoritative workflow flag mutation.

Final-leaf-census corrective (Ticket 07 step 6): the dashboard workflow
toggles must never mutate Obsidian frontmatter client-side. Python owns
its literature notes; the thin client passes only the canonical key,
field, and value.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from paperforge.adapters.obsidian_frontmatter import read_frontmatter_dict
from paperforge.worker.asset_index import get_index_path
from tests.conftest import canonical_test_config


def _seed(vault: Path, fm_text: str) -> Path:
    canonical_test_config(vault, resources_dir="03_Resources", literature_dir="Literature")
    note_dir = vault / "03_Resources" / "Literature" / "Cardio" / "ABCD1234 - Smith"
    note_dir.mkdir(parents=True, exist_ok=True)
    note = note_dir / "ABCD1234.md"
    note.write_text(fm_text, encoding="utf-8")
    index_path = get_index_path(vault)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "zotero_key": "ABCD1234",
                        "note_path": note.relative_to(vault)
                        .as_posix(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return note


def _run(vault: Path, *extra: str) -> tuple[int, dict | None, str]:
    r = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(vault), "note", *extra],
        capture_output=True,
        text=True,
    )
    try:
        return r.returncode, json.loads(r.stdout), r.stderr
    except json.JSONDecodeError:
        return r.returncode, None, r.stdout + r.stderr


def test_set_flag_writes_an_unquoted_yaml_bool(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    note = _seed(vault, "---\nzotero_key: ABCD1234\ndo_ocr: false\n---\nbody")
    rc, payload, err = _run(
        vault, "set-flag", "--key", "ABCD1234", "--field", "do_ocr", "--value", "true", "--json"
    )
    assert rc == 0, err
    assert payload["ok"] is True
    assert payload["data"]["changed"] is True
    fm = read_frontmatter_dict(note.read_text(encoding="utf-8"))
    # isinstance(v, bool) is the index derivation contract — a quoted
    # 'true' string would silently fall back to legacy derivation
    assert isinstance(fm["do_ocr"], bool)
    assert fm["do_ocr"] is True


def test_set_flag_false_and_idempotent_noop(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    note = _seed(vault, "---\nzotero_key: ABCD1234\ndo_ocr: true\n---\nbody")
    rc, payload, err = _run(
        vault, "set-flag", "--key", "ABCD1234", "--field", "analyze", "--value", "true", "--json"
    )
    assert rc == 0, err
    fm = read_frontmatter_dict(note.read_text(encoding="utf-8"))
    assert fm["analyze"] is True
    # re-setting the same value is an authoritative no-op (changed=false)
    rc2, payload2, err2 = _run(
        vault, "set-flag", "--key", "ABCD1234", "--field", "analyze", "--value", "true", "--json"
    )
    assert rc2 == 0, err2
    assert payload2["data"]["changed"] is False
    rc3, _, _ = _run(
        vault, "set-flag", "--key", "ABCD1234", "--field", "do_ocr", "--value", "false", "--json"
    )
    assert rc3 == 0
    fm2 = read_frontmatter_dict(note.read_text(encoding="utf-8"))
    assert fm2["do_ocr"] is False


def test_unknown_field_fails_closed(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    _seed(vault, "---\nzotero_key: ABCD1234\n---\nbody")
    rc, payload, _ = _run(
        vault, "set-flag", "--key", "ABCD1234", "--field", "arbitrary_key", "--value", "true", "--json"
    )
    assert rc == 1
    assert payload["ok"] is False
    assert "field must be one of" in payload["error"]["message"]


def test_unknown_paper_key_fails_closed(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    _seed(vault, "---\nzotero_key: ABCD1234\n---\nbody")
    rc, payload, _ = _run(
        vault, "set-flag", "--key", "ZZZZ9999", "--field", "do_ocr", "--value", "true", "--json"
    )
    assert rc == 1
    assert payload["ok"] is False
    assert "unknown paper key" in payload["error"]["message"]


def test_wikilinked_note_path_resolves(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    note = _seed(vault, "---\nzotero_key: ABCD1234\n---\nbody")
    index_path = get_index_path(vault)
    index_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "zotero_key": "ABCD1234",
                        "note_path": f"[[{note.relative_to(vault).as_posix()}]]",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    rc, payload, err = _run(
        vault, "set-flag", "--key", "ABCD1234", "--field", "do_ocr", "--value", "true", "--json"
    )
    assert rc == 0, err
    fm = read_frontmatter_dict(note.read_text(encoding="utf-8"))
    assert fm["do_ocr"] is True
