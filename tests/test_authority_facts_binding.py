"""#229: authority facts need call-site evidence, not a definition line.

A bound symbol that still exists but no longer performs its role must not
produce a pre-declared fact — the rule has to fall back to `unresolved`, and
the gate has to fail.  These cases run the real collector against a sandbox
repo containing the bound sources, so the negative is a source change (not a
hand-built audit payload).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from paperforge.architecture_audit import ArchitectureContract
from paperforge.architecture_audit.collectors.authority import collect_authority_facts

REPO = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO / "docs" / "architecture-audit-2026-08-06" / "contract.json"
BOUND_SOURCES = (
    "paperforge/worker/ocr.py",
    "paperforge/plugin/src/views/ocr-workspace.ts",
    "paperforge/plugin/src/settings.ts",
    "paperforge/commands/versions.py",
    "paperforge/memory/builder.py",
)


def _contract() -> ArchitectureContract:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    body = payload["contract"] if isinstance(payload.get("contract"), dict) else payload
    return ArchitectureContract.from_dict(body)


def _sandbox(tmp_path: Path, edits: dict[str, tuple[str, str]]) -> Path:
    root = tmp_path / "repo"
    for rel in BOUND_SOURCES:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, target)
    for rel, (old, new) in edits.items():
        path = root / rel
        text = path.read_text(encoding="utf-8")
        assert old in text, f"anchor missing in {rel}: {old!r}"
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return root


def _facts(root: Path) -> set[tuple[str, str]]:
    facts, _diagnostics = collect_authority_facts(root, _contract())
    return {
        (
            str(fact.get("operation_id") or fact.get("unit_id") or ""),
            "publication" if fact.get("unit_id") else str(fact.get("role") or ""),
        )
        for fact in facts
    }


def test_clean_bound_sources_evidence_every_binding(tmp_path: Path) -> None:
    facts = _facts(_sandbox(tmp_path, {}))
    assert ("ocr_run", "execution") in facts
    assert ("ocr_rebuild", "stop") in facts
    assert ("embed_build_resume", "stop") in facts
    assert ("ocr_display.fulltext", "publication") in facts
    assert ("retrieval.units", "publication") in facts


def test_authority_moved_out_of_the_symbol_yields_no_fact(tmp_path: Path) -> None:
    """The #229 N1 injection: the symbol stays, the stop call moves away."""
    root = _sandbox(
        tmp_path,
        {
            "paperforge/plugin/src/settings.ts": (
                "client.cancelActiveOperation();",
                "host.pfStopEmbed?.();",
            )
        },
    )
    facts = _facts(root)
    assert ("embed_build_resume", "stop") not in facts
    # the untouched sibling binding keeps its evidence
    assert ("ocr_rebuild", "stop") in facts


def test_definition_removed_yields_no_fact(tmp_path: Path) -> None:
    root = _sandbox(
        tmp_path,
        {"paperforge/commands/versions.py": ("def _run_restore(", "def _run_restore_retired(")},
    )
    facts = _facts(root)
    assert ("ocr_display.fulltext", "publication") not in facts
    assert ("retrieval.units", "publication") in facts


def test_a_hollowed_publisher_yields_no_fact(tmp_path: Path) -> None:
    root = _sandbox(
        tmp_path,
        {
            "paperforge/commands/versions.py": (
                "provenance_persisted = record_restore_provenance(vault, key, provenance)",
                "provenance_persisted = False",
            )
        },
    )
    facts = _facts(root)
    assert ("ocr_display.fulltext", "publication") not in facts


def _foreign(root: Path, rel: str, body: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def test_a_foreign_writer_emits_a_canonical_write_fact(tmp_path: Path) -> None:
    """#339: authorized publishers intact, a third writer appears."""
    root = _sandbox(tmp_path, {})
    _foreign(
        root,
        "paperforge/worker/foreign_writer.py",
        "def sneaky_publish(render_root, text):\n"
        "    (render_root / 'fulltext.md').write_text(text, encoding='utf-8')\n",
    )
    raw = collect_authority_facts(root, _contract())[0]
    writers = [
        str(fact.get("writer_id"))
        for fact in raw
        if fact.get("unit_id") == "ocr_display.fulltext" and fact.get("writer_id")
    ]
    assert any("foreign_writer.py:sneaky_publish" in writer for writer in writers), writers


def test_a_backup_writer_is_not_a_publisher(tmp_path: Path) -> None:
    root = _sandbox(tmp_path, {})
    _foreign(
        root,
        "paperforge/worker/backup_writer.py",
        "def backup_render_before_rebuild(render_root, dest):\n"
        "    dest.write_text((render_root / 'fulltext.md').read_text(encoding='utf-8'))\n",
    )
    raw = collect_authority_facts(root, _contract())[0]
    assert not [f for f in raw if "backup_writer.py" in str(f.get("writer_id"))]


def test_test_tree_writers_are_ignored(tmp_path: Path) -> None:
    root = _sandbox(tmp_path, {})
    _foreign(
        root,
        "paperforge/plugin/test/fixtures/builder.py",
        "def build(render_root, text):\n"
        "    (render_root / 'fulltext.md').write_text(text, encoding='utf-8')\n",
    )
    raw = collect_authority_facts(root, _contract())[0]
    assert not [f for f in raw if "builder.py" in str(f.get("writer_id"))]
