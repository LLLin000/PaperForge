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

def _drop_units(vault: Path, keys: tuple[str, ...]) -> None:
    import json

    from paperforge.lineage import compute_retrieval_identity
    from paperforge.memory.db import get_connection, get_memory_db_path
    from paperforge.retrieval.manifest import (
        compute_body_units_hash,
        compute_object_units_hash,
    )

    conn = get_connection(get_memory_db_path(vault))
    try:
        conn.executemany("DELETE FROM body_units WHERE paper_id = ?", ((key,) for key in keys))
        conn.execute(
            "DELETE FROM object_units WHERE paper_id IN ({})".format(
                ",".join("?" for _ in keys)
            ),
            keys,
        )
        for key in keys:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = ?", (f"manifest:{key}",)
            ).fetchone()
            if not row:
                continue
            manifest = json.loads(row[0])
            manifest["body_unit_count"] = 0
            manifest["body_units_hash"] = compute_body_units_hash([])
            manifest["object_unit_count"] = 0
            manifest["object_units_hash"] = compute_object_units_hash([])
            manifest["retrieval_identity"] = compute_retrieval_identity(
                ocr_result_hash=manifest["ocr_result_hash"],
                retrieval_policy_version=manifest["retrieval_policy_version"],
                structure_tree_hash=manifest["structure_tree_hash"],
                body_units_hash=manifest["body_units_hash"],
                object_units_hash=manifest["object_units_hash"],
            )
            conn.execute(
                "UPDATE meta SET value = ? WHERE key = ?",
                (json.dumps(manifest), f"manifest:{key}"),
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
    _drop_units(vault, ("KEY2",))
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
    _drop_units(vault, ("PURE",))
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


def test_build_and_resume_share_one_selector(tmp_path: Path) -> None:
    """M3-F: embed.build and embed.resume MUST consume the SAME eligibility
    selector — no divergent candidate sets (a 'build correct, scoped
    resume wrong' split is the failure mode this closes)."""
    import inspect

    from paperforge.services import embedding

    # both modes route through run_embedding_build, which calls
    # select_embedding_candidates — assert the single call site exists
    # and there is no other done_papers/ocr_status filter anywhere.
    src = inspect.getsource(embedding.run_embedding_build)
    assert "select_embedding_candidates" in src
    assert 'get("ocr_status")' not in src, "candidate selection must not consult ocr_status"
    src_all = inspect.getsource(embedding)
    assert src_all.count("select_embedding_candidates(") <= 3, (
        "one selector, used by build/resume/progress — no parallel logic"
    )
