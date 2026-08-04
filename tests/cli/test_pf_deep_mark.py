"""CLI helper coverage for pf_deep mark."""

from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent
_SPEC = spec_from_file_location(
    "pf_deep",
    _REPO_ROOT / "paperforge" / "skills" / "paperforge" / "scripts" / "pf_deep.py",
)
pf_deep = module_from_spec(_SPEC)
sys.modules["pf_deep"] = pf_deep
assert _SPEC.loader is not None
_SPEC.loader.exec_module(pf_deep)


def _make_vault(tmp_path: Path) -> Path:
    (tmp_path / "System" / "PaperForge" / "ocr").mkdir(parents=True)
    literature = tmp_path / "Resources" / "Literature" / "Oncology"
    literature.mkdir(parents=True)
    (tmp_path / "paperforge.json").write_text(
        json.dumps(
            {
                "vault_config": {
                    "system_dir": "System",
                    "resources_dir": "Resources",
                    "literature_dir": "Literature",
                    "control_dir": "LiteratureControl",
                }
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_mark_deep_reading_updates_existing_status(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path)
    note = vault / "Resources" / "Literature" / "Oncology" / "ABC12345 - Paper.md"
    note.write_text(
        "---\n"
        "zotero_key: ABC12345\n"
        "domain: Oncology\n"
        "analyze: true\n"
        "deep_reading_status: pending\n"
        "---\n\n"
        "## 精读\n",
        encoding="utf-8",
    )

    result = pf_deep.mark_deep_reading(vault, "ABC12345")

    assert result["status"] == "ok"
    assert 'deep_reading_status: "done"' in note.read_text(encoding="utf-8")


def test_mark_deep_reading_adds_missing_status(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path)
    note = vault / "Resources" / "Literature" / "Oncology" / "ABC12345 - Paper.md"
    note.write_text(
        "---\n"
        "zotero_key: ABC12345\n"
        "domain: Oncology\n"
        "analyze: true\n"
        "---\n\n"
        "## 精读\n",
        encoding="utf-8",
    )

    result = pf_deep.mark_deep_reading(vault, "ABC12345", status="done")

    assert result["status"] == "ok"
    assert 'deep_reading_status: "done"' in note.read_text(encoding="utf-8")
