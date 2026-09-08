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


def test_body_line_with_same_key_is_never_touched(tmp_path: Path) -> None:
    """P1-2 regression: the setter must operate strictly on the
    frontmatter segment — a prose line like ``analyze: ...`` in the body
    must stay byte-identical, and the real frontmatter field must be
    created (authority success == durable frontmatter state)."""
    for field in ("do_ocr", "analyze"):
        vault = tmp_path / f"v-{field}"
        vault.mkdir()
        body_line = f"{field}: BODY MUST STAY"
        note = _seed(
            vault,
            f"---\nzotero_key: ABCD1234\ntitle: X\n---\n\n实验参数：\n\n{body_line}\n",
        )
        rc, payload, err = _run(
            vault,
            "set-flag",
            "--key",
            "ABCD1234",
            "--field",
            field,
            "--value",
            "true",
            "--json",
        )
        assert rc == 0, err
        assert payload["data"]["changed"] is True
        text = note.read_text(encoding="utf-8")
        fm = read_frontmatter_dict(text)
        assert fm[field] is True, text
        # the body line survives byte-identical, after the closing fence
        closing = text.index("---", 4)
        assert body_line in text[closing + 3:]
        assert body_line not in text[:closing]
        assert text[closing + 3 :].count(body_line) == 1


def test_note_without_frontmatter_fails_closed(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    note = _seed(vault, "no frontmatter here\n")
    # index points at a note that lost its frontmatter — refuse, never
    # silently fabricate a frontmatter block
    rc, payload, _ = _run(
        vault, "set-flag", "--key", "ABCD1234", "--field", "do_ocr", "--value", "true", "--json"
    )
    assert rc == 1
    assert payload["ok"] is False
    assert "no frontmatter" in payload["error"]["message"]
    assert note.read_text(encoding="utf-8") == "no frontmatter here\n"


def test_inline_dashes_in_value_are_not_a_fence(tmp_path: Path) -> None:
    """P1 fence-parser regression: ``split("---")``-style parsing would
    treat the inline ``---`` inside a title value as the closing fence —
    truncating the frontmatter and corrupting the title on reassembly.
    Line-anchored parsing must keep the value intact."""
    vault = tmp_path / "v"
    vault.mkdir()
    note = _seed(
        vault,
        "---\nzotero_key: ABCD1234\ntitle: State --- X\n---\n\nbody text\n",
    )
    rc, payload, err = _run(
        vault, "set-flag", "--key", "ABCD1234", "--field", "analyze", "--value", "true", "--json"
    )
    assert rc == 0, err
    text = note.read_text(encoding="utf-8")
    fm = read_frontmatter_dict(text)
    assert fm["analyze"] is True
    assert fm["title"] == "State --- X", text
    assert "body text" in text


def test_body_horizontal_rule_stays_body(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    note = _seed(
        vault,
        "---\nzotero_key: ABCD1234\n---\n\n---\nhr line context\n",
    )
    rc, _, err = _run(
        vault, "set-flag", "--key", "ABCD1234", "--field", "do_ocr", "--value", "true", "--json"
    )
    assert rc == 0, err
    text = note.read_text(encoding="utf-8")
    fm = read_frontmatter_dict(text)
    assert fm["do_ocr"] is True
    # the body hr block survives verbatim after the REAL closing fence
    assert text.endswith("---\n\n---\nhr line context\n")


def test_crlf_line_endings_preserved(tmp_path: Path) -> None:
    """_seed writes via text mode, so the on-disk note is CRLF on Windows.
    The setter must preserve each line's original ending (read raw with
    newline="" — read_text would translate CRLF away)."""
    vault = tmp_path / "v"
    vault.mkdir()
    note = _seed(vault, "---\nzotero_key: ABCD1234\ndo_ocr: false\n---\nbody\n")
    rc, _, err = _run(
        vault, "set-flag", "--key", "ABCD1234", "--field", "do_ocr", "--value", "true", "--json"
    )
    assert rc == 0, err
    with open(note, encoding="utf-8", newline="") as f:
        raw = f.read()
    assert "do_ocr: true\r\n" in raw
    assert "---\r\n" in raw
    assert raw.count("\n") == raw.count("\r\n")  # no mixed endings introduced


def test_unterminated_frontmatter_fails_closed_locally(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    note = _seed(vault, "---\nzotero_key: ABCD1234\nno close fence")
    rc, payload, _ = _run(
        vault, "set-flag", "--key", "ABCD1234", "--field", "do_ocr", "--value", "true", "--json"
    )
    # the command-level check (startswith "---") passes, but the adapter
    # must refuse to fabricate a block for an unterminated fence
    assert note.read_text(encoding="utf-8") == "---\nzotero_key: ABCD1234\nno close fence"
    if rc == 0:
        text = note.read_text(encoding="utf-8")
        assert "do_ocr" not in text.split("---")[1], text
