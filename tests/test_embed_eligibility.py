"""M3-B: retrieval-truth embed eligibility — select_embedding_candidates.

Eligibility asks the DIRECT parent (retrieval materialization), never
ocr_status == 'done'.  Three mutually-exclusive classes:
eligible (should have vectors), no_content (satisfied terminal, M1.1),
not_ready (retrieval missing — must NOT be embedded).
"""

from __future__ import annotations

from pathlib import Path

from tests.test_lineage import _make_vault


def _seed_units(vault: Path, keys: tuple[str, ...]) -> None:
    """Seed indexable body_units so eligibility sees content."""
    from paperforge.memory.db import get_connection, get_memory_db_path, ensure_vec_extension
    from paperforge.memory.schema import ensure_schema

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    try:
        ensure_vec_extension(conn)
        ensure_schema(conn)
        for k in keys:
            conn.execute(
                "INSERT OR IGNORE INTO body_units "
                "(unit_id, paper_id, section_path, unit_text, page_span_json, "
                "block_span_json, token_estimate, indexable, veto_reason, quality_hints_json) "
                "VALUES (?, ?, '/', 'content', '[]', '[]', 1, 1, '', '{}')",
                (f"{k}-u1", k),
            )
        conn.commit()
    finally:
        conn.close()


def _drop_manifest(vault: Path, key: str) -> None:
    """Remove the retrieval manifest so probe reports retrieval missing."""
    from paperforge.memory.db import get_connection, get_memory_db_path

    conn = get_connection(get_memory_db_path(vault))
    try:
        conn.execute("DELETE FROM meta WHERE key=?", (f"manifest:{key}",))
        conn.commit()
    finally:
        conn.close()


def test_eligible_no_content_not_ready_partition(tmp_path: Path) -> None:
    """Three mutually-exclusive classes from retrieval truth.  _make_vault
    builds KEY1/KEY2/KEY3 with complete OCR + retrieval manifests; KEY1
    gets content (eligible), KEY2 stays contentless (no_content), KEY3's
    manifest is dropped (not_ready)."""
    from paperforge.services.embedding import select_embedding_candidates

    vault = _make_vault(tmp_path, keys=("KEY1", "KEY2", "KEY3"))
    _seed_units(vault, ("KEY1",))
    _drop_manifest(vault, "KEY3")

    cand = select_embedding_candidates(vault, keys=["KEY1", "KEY2", "KEY3"])
    assert cand["eligible"] == ["KEY1"]
    assert cand["no_content"] == ["KEY2"]
    assert cand["not_ready"] == ["KEY3"]


def test_no_content_never_eligible(tmp_path: Path) -> None:
    """A pure-image paper (0 units) is a satisfied terminal — never
    eligible, so embed.resume can never be emitted for it."""
    from paperforge.services.embedding import select_embedding_candidates

    vault = _make_vault(tmp_path, keys=("PURE",))
    cand = select_embedding_candidates(vault, keys=["PURE"])
    assert cand["eligible"] == []
    assert cand["no_content"] == ["PURE"]


def test_not_ready_never_eligible(tmp_path: Path) -> None:
    """Retrieval not current must block embedding entirely."""
    from paperforge.services.embedding import select_embedding_candidates

    vault = _make_vault(tmp_path, keys=("NOREADY",))
    _seed_units(vault, ("NOREADY",))  # content exists but no retrieval
    _drop_manifest(vault, "NOREADY")
    cand = select_embedding_candidates(vault, keys=["NOREADY"])
    assert cand["eligible"] == []
    assert cand["not_ready"] == ["NOREADY"]
