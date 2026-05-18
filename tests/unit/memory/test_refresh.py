from __future__ import annotations

from pathlib import Path

from paperforge.memory.refresh import refresh_paper


def test_refresh_paper_returns_false_when_no_db():
    assert refresh_paper(Path("/nonexistent/vault"), {"zotero_key": "KEY001"}) is False


def test_refresh_paper_returns_false_for_empty_key():
    assert refresh_paper(Path("/nonexistent/vault"), {}) is False


def test_refresh_paper_returns_false_for_missing_key():
    assert refresh_paper(Path("/nonexistent/vault"), {"title": "No Key"}) is False


def test_refresh_paper_rebuild_from_index_removes_stale_rows(tmp_path):
    from paperforge.memory.builder import build_from_index
    from paperforge.memory.db import get_connection, get_memory_db_path
    from paperforge.worker.asset_index import build_envelope, get_index_path

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        '{"vault_config":{"system_dir":"System","resources_dir":"Resources","literature_dir":"Literature","base_dir":"Bases","control_dir":"LiteratureControl"}}',
        encoding="utf-8",
    )

    index_path = get_index_path(vault)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    first = [{"zotero_key": "AAA", "title": "Paper A", "domain": "test", "has_pdf": False, "ocr_status": "pending", "analyze": False, "deep_reading_status": "pending", "pdf_path": "", "note_path": "", "main_note_path": "", "fulltext_path": "", "ocr_json_path": "", "ai_path": "", "paper_root": "", "citation_key": "", "doi": "", "journal": "", "first_author": "", "collection_path": "", "collections": [], "authors": [], "abstract": "", "zotero_storage_key": "", "attachment_count": 0, "supplementary": [], "recommend_analyze": False, "path_error": "", "analysis_note": "", "lifecycle": "indexed", "maturity": {"score": 0}, "next_step": "ready"}]
    index_path.write_text(__import__("json").dumps(build_envelope(first), ensure_ascii=False, indent=2), encoding="utf-8")

    build_from_index(vault)

    second = []
    index_path.write_text(__import__("json").dumps(build_envelope(second), ensure_ascii=False, indent=2), encoding="utf-8")
    build_from_index(vault)

    conn = get_connection(get_memory_db_path(vault), read_only=True)
    try:
        count = conn.execute("SELECT COUNT(*) AS c FROM papers").fetchone()["c"]
    finally:
        conn.close()

    assert count == 0
