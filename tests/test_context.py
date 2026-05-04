"""Tests for context.py — paperforge context CLI command.

Phase 26-02 Task 3: Tests for single-key, --domain, --collection, --all
modes, provenance traceability, and AI readiness blocking explanations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_vault(tmp_path: Path) -> Path:
    """Create a minimal vault with paperforge.json for path resolution."""
    vault = tmp_path / "test_vault"
    vault.mkdir(parents=True, exist_ok=True)
    pf_json = vault / "paperforge.json"
    pf_json.write_text(
        json.dumps(
            {
                "version": "1.2.0",
                "vault_config": {
                    "system_dir": "99_System",
                    "resources_dir": "03_Resources",
                    "literature_dir": "Literature",
                    "control_dir": "LiteratureControl",
                    "base_dir": "05_Bases",
                    "skill_dir": ".opencode/skills",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return vault


def _write_index(vault: Path, items: list[dict]) -> None:
    """Write a canonical index envelope to the vault."""
    from paperforge.worker.asset_index import atomic_write_index, build_envelope, get_index_path

    idx_path = get_index_path(vault)
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    envelope = build_envelope(items)
    atomic_write_index(idx_path, envelope)


def _make_entry(key: str, domain: str = "default", **overrides: dict) -> dict:
    """Create a canonical index entry dict with default fields."""
    entry: dict = {
        "zotero_key": key,
        "domain": domain,
        "title": f"Paper {key}",
        "authors": [f"Author {key}"],
        "abstract": f"Abstract for {key}",
        "journal": "Test Journal",
        "year": "2024",
        "doi": f"10.1234/{key}",
        "pmid": "12345",
        "collections": [domain],
        "collection_path": domain,
        "collection_tags": [],
        "has_pdf": True,
        "pdf_path": f"[[storage/{key}/paper.pdf]]",
        "ocr_status": "done",
        "ocr_md_path": f"[[ocr/{key}/fulltext.md]]",
        "ocr_json_path": f"ocr/{key}/meta.json",
        "deep_reading_status": "done",
        "note_path": f"Literature/{domain}/{key} - Paper_{key}.md",
        "deep_reading_md_path": f"Literature/{domain}/{key} - Paper_{key}.md",
        "paper_root": f"Literature/{domain}/{key} - Paper_{key}/",
        "main_note_path": f"Literature/{domain}/{key} - Paper_{key}/{key} - Paper_{key}.md",
        "fulltext_path": f"Literature/{domain}/{key} - Paper_{key}/fulltext.md",
        "deep_reading_path": f"Literature/{domain}/{key} - Paper_{key}/deep-reading.md",
        "ai_path": f"Literature/{domain}/{key} - Paper_{key}/ai/",
        "lifecycle": "ai_context_ready",
        "health": {
            "pdf_health": "healthy",
            "ocr_health": "healthy",
            "note_health": "healthy",
            "asset_health": "healthy",
        },
        "maturity": {"level": 6, "blocking": []},
        "next_step": "ready",
    }
    entry.update(overrides)
    return entry


def _make_args(
    key: str | None = None,
    domain: str | None = None,
    collection: str | None = None,
    all_mode: bool = False,
    vault_path: Path | None = None,
) -> argparse.Namespace:
    """Build an argparse.Namespace for context.run()."""
    return argparse.Namespace(
        key=key,
        domain=domain,
        collection=collection,
        all=all_mode,
        vault_path=vault_path,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestContextSingleKey:
    """AIC-02: single paper context output."""

    def test_context_single_key_output(self, tmp_path: Path) -> None:
        """Single key returns JSON object with matching zotero_key."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        items = [
            _make_entry("KEY001"),
            _make_entry("KEY002"),
        ]
        _write_index(vault, items)

        captured_out: list[str] = []

        def _capture_print(*args, **kwargs) -> None:
            captured_out.extend(str(a) for a in args)

        import builtins
        original_print = builtins.print
        builtins.print = _capture_print

        try:
            code = run(_make_args(key="KEY001", vault_path=vault))
        finally:
            builtins.print = original_print

        assert code == 0
        output = " ".join(captured_out)
        data = json.loads(output)
        assert data["zotero_key"] == "KEY001"
        # Must be a dict (single JSON object), not a list
        assert isinstance(data, dict)

    def test_context_single_key_includes_provenance(self, tmp_path: Path) -> None:
        """Single key output includes _provenance block."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        items = [_make_entry("KEY001")]
        _write_index(vault, items)

        captured_out: list[str] = []

        def _capture_print(*args, **kwargs) -> None:
            captured_out.extend(str(a) for a in args)

        import builtins
        original_print = builtins.print
        builtins.print = _capture_print

        try:
            code = run(_make_args(key="KEY001", vault_path=vault))
        finally:
            builtins.print = original_print

        assert code == 0
        data = json.loads(" ".join(captured_out))
        prov = data.get("_provenance", {})
        assert isinstance(prov, dict)
        assert "paper_root" in prov
        assert "main_note_path" in prov
        assert "fulltext_path" in prov
        assert "pdf_path" in prov

    def test_context_single_key_includes_ai_readiness(self, tmp_path: Path) -> None:
        """Single key output includes _ai_readiness block."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        items = [_make_entry("KEY001")]
        _write_index(vault, items)

        captured_out: list[str] = []

        def _capture_print(*args, **kwargs) -> None:
            captured_out.extend(str(a) for a in args)

        import builtins
        original_print = builtins.print
        builtins.print = _capture_print

        try:
            code = run(_make_args(key="KEY001", vault_path=vault))
        finally:
            builtins.print = original_print

        assert code == 0
        data = json.loads(" ".join(captured_out))
        readiness = data.get("_ai_readiness", {})
        assert isinstance(readiness, dict)
        assert "ai_context_ready" in readiness
        assert "lifecycle" in readiness


class TestContextSingleKeyNotFound:
    """Missing key returns exit code 1."""

    def test_context_key_not_found(self, tmp_path: Path, capsys) -> None:
        """When key is not in index, return 1 and print error."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        items = [_make_entry("KEY001")]
        _write_index(vault, items)

        code = run(_make_args(key="KEY999", vault_path=vault))
        assert code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()


class TestContextDomainFilter:
    """AIC-03: domain-level context output."""

    def test_context_domain_filter(self, tmp_path: Path) -> None:
        """--domain filters to entries in that domain."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        items = [
            _make_entry("KEY001", domain="骨科"),
            _make_entry("KEY002", domain="运动医学"),
            _make_entry("KEY003", domain="骨科"),
        ]
        _write_index(vault, items)

        captured_out: list[str] = []

        def _capture_print(*args, **kwargs) -> None:
            captured_out.extend(str(a) for a in args)

        import builtins
        original_print = builtins.print
        builtins.print = _capture_print

        try:
            code = run(_make_args(domain="骨科", vault_path=vault))
        finally:
            builtins.print = original_print

        assert code == 0
        data = json.loads(" ".join(captured_out))
        assert isinstance(data, list)
        assert len(data) == 2
        for entry in data:
            assert entry["domain"] == "骨科"


class TestContextCollectionFilter:
    """AIC-03: collection-path prefix match."""

    def test_context_collection_filter(self, tmp_path: Path) -> None:
        """--collection filters by prefix match on collections list."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        items = [
            _make_entry("KEY001", domain="骨科", collections=["骨科/脊柱"]),
            _make_entry("KEY002", domain="运动医学", collections=["运动医学"]),
            _make_entry("KEY003", domain="骨科", collections=["骨科/创伤"]),
            _make_entry("KEY004", domain="神经科", collections=["神经科"]),
        ]
        _write_index(vault, items)

        captured_out: list[str] = []

        def _capture_print(*args, **kwargs) -> None:
            captured_out.extend(str(a) for a in args)

        import builtins
        original_print = builtins.print
        builtins.print = _capture_print

        try:
            code = run(_make_args(collection="骨科", vault_path=vault))
        finally:
            builtins.print = original_print

        assert code == 0
        data = json.loads(" ".join(captured_out))
        assert isinstance(data, list)
        assert len(data) == 2
        keys = [e["zotero_key"] for e in data]
        assert "KEY001" in keys
        assert "KEY003" in keys
        assert "KEY002" not in keys


class TestContextAll:
    """--all returns all index entries."""

    def test_context_all(self, tmp_path: Path) -> None:
        """--all outputs all entries as JSON array."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        items = [
            _make_entry("KEY001"),
            _make_entry("KEY002"),
            _make_entry("KEY003"),
        ]
        _write_index(vault, items)

        captured_out: list[str] = []

        def _capture_print(*args, **kwargs) -> None:
            captured_out.extend(str(a) for a in args)

        import builtins
        original_print = builtins.print
        builtins.print = _capture_print

        try:
            code = run(_make_args(all_mode=True, vault_path=vault))
        finally:
            builtins.print = original_print

        assert code == 0
        data = json.loads(" ".join(captured_out))
        assert isinstance(data, list)
        assert len(data) == 3


class TestContextProvenanceTraceability:
    """AIC-04: provenance paths are present and non-empty."""

    def test_provenance_all_paths_present(self, tmp_path: Path) -> None:
        """Output _provenance block has all path keys with non-empty values."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        items = [_make_entry("KEY001")]
        _write_index(vault, items)

        captured_out: list[str] = []

        def _capture_print(*args, **kwargs) -> None:
            captured_out.extend(str(a) for a in args)

        import builtins
        original_print = builtins.print
        builtins.print = _capture_print

        try:
            code = run(_make_args(key="KEY001", vault_path=vault))
        finally:
            builtins.print = original_print

        assert code == 0
        data = json.loads(" ".join(captured_out))
        prov = data.get("_provenance", {})
        expected_keys = [
            "paper_root",
            "main_note_path",
            "fulltext_path",
            "ocr_md_path",
            "pdf_path",
            "deep_reading_path",
            "ai_path",
            "note_path",
            "deep_reading_md_path",
        ]
        for key in expected_keys:
            assert key in prov, f"Missing provenance key: {key}"
            assert isinstance(prov[key], str), f"Provenance key {key} should be a string"
            assert prov[key] != "", f"Provenance key {key} should be non-empty"


class TestContextAiReadinessBlocking:
    """AIC-04: blocking explanation when AI context not ready."""

    def test_ai_context_ready_has_no_blocking(self, tmp_path: Path) -> None:
        """ai_context_ready entry has no blocking factors."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        items = [_make_entry("KEY001", lifecycle="ai_context_ready")]
        _write_index(vault, items)

        captured_out: list[str] = []

        def _capture_print(*args, **kwargs) -> None:
            captured_out.extend(str(a) for a in args)

        import builtins
        original_print = builtins.print
        builtins.print = _capture_print

        try:
            code = run(_make_args(key="KEY001", vault_path=vault))
        finally:
            builtins.print = original_print

        assert code == 0
        data = json.loads(" ".join(captured_out))
        readiness = data["_ai_readiness"]
        assert readiness["ai_context_ready"] is True
        assert readiness["blocking_factors"] == []

    def test_pdf_ready_has_blocking_explanation(self, tmp_path: Path) -> None:
        """pdf_ready entry has blocking explanation about missing OCR."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        items = [
            _make_entry(
                "KEY001",
                lifecycle="pdf_ready",
                has_pdf=True,
                ocr_status="pending",
                deep_reading_status="pending",
                health={"pdf_health": "healthy"},
                maturity={"level": 2, "blocking": ["ocr not done"]},
                next_step="ocr",
            )
        ]
        _write_index(vault, items)

        captured_out: list[str] = []

        def _capture_print(*args, **kwargs) -> None:
            captured_out.extend(str(a) for a in args)

        import builtins
        original_print = builtins.print
        builtins.print = _capture_print

        try:
            code = run(_make_args(key="KEY001", vault_path=vault))
        finally:
            builtins.print = original_print

        assert code == 0
        data = json.loads(" ".join(captured_out))
        readiness = data["_ai_readiness"]
        assert readiness["ai_context_ready"] is False
        assert "blocking_explanation" in readiness
        assert "ocr" in readiness["blocking_explanation"].lower()

    def test_fulltext_ready_has_blocking_explanation(self, tmp_path: Path) -> None:
        """fulltext_ready entry has blocking explanation about missing deep reading."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        items = [
            _make_entry(
                "KEY001",
                lifecycle="fulltext_ready",
                has_pdf=True,
                ocr_status="done",
                deep_reading_status="pending",
                health={
                    "pdf_health": "healthy",
                    "ocr_health": "healthy",
                },
                maturity={"level": 3, "blocking": ["deep reading not done"]},
                next_step="/pf-deep",
            )
        ]
        _write_index(vault, items)

        captured_out: list[str] = []

        def _capture_print(*args, **kwargs) -> None:
            captured_out.extend(str(a) for a in args)

        import builtins
        original_print = builtins.print
        builtins.print = _capture_print

        try:
            code = run(_make_args(key="KEY001", vault_path=vault))
        finally:
            builtins.print = original_print

        assert code == 0
        data = json.loads(" ".join(captured_out))
        readiness = data["_ai_readiness"]
        assert readiness["ai_context_ready"] is False
        assert "blocking_explanation" in readiness
        assert "deep reading" in readiness["blocking_explanation"].lower()


class TestContextNoEntriesMatch:
    """Empty filter results."""

    def test_domain_no_match_returns_empty_array(self, tmp_path: Path, capsys) -> None:
        """When --domain matches nothing, print [] and return 0."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        items = [_make_entry("KEY001", domain="骨科")]
        _write_index(vault, items)

        code = run(_make_args(domain="Nonexistent", vault_path=vault))
        assert code == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "[]"

    def test_no_mode_specified_returns_error(self, tmp_path: Path, capsys) -> None:
        """No key, no flags -> error message and exit code 1."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        _write_index(vault, [])  # empty index

        code = run(
            argparse.Namespace(
                key=None,
                domain=None,
                collection=None,
                all=False,
                vault_path=vault,
            )
        )
        assert code == 1
        captured = capsys.readouterr()
        assert "Specify" in captured.err


class TestContextIndexMissing:
    """Missing index file."""

    def test_index_missing_returns_error(self, tmp_path: Path, capsys) -> None:
        """When no index exists, return 1 with guidance message."""
        from paperforge.commands.context import run

        vault = _minimal_vault(tmp_path)
        # Do NOT write an index

        code = run(_make_args(key="KEY001", vault_path=vault))
        assert code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()
