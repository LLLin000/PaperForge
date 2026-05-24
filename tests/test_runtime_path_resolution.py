import sqlite3
from pathlib import Path

from paperforge.commands.annotation import _resolve_paper_key
from paperforge.embedding._chroma import get_vector_db_path
from paperforge.embedding.build_state import get_vector_build_state_path
from paperforge.setup.checker import SetupChecker


def test_resolve_paper_key_uses_configured_memory_db_path(tmp_path: Path) -> None:
    (tmp_path / "paperforge.json").write_text(
        '{"vault_config": {"system_dir": "02_文献管理/System"}}',
        encoding="utf-8",
    )
    db_path = tmp_path / "02_文献管理" / "System" / "PaperForge" / "indexes" / "paperforge.db"
    db_path.parent.mkdir(parents=True)

    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE papers (zotero_key TEXT, pdf_path TEXT)")
    conn.execute(
        "INSERT INTO papers(zotero_key, pdf_path) VALUES (?, ?)",
        ("K1", "[[02_文献管理/System/Zotero/storage/ABCD1234/paper.pdf]]"),
    )
    conn.commit()
    conn.close()

    key = _resolve_paper_key(tmp_path, "02_文献管理/System/Zotero/storage/ABCD1234/paper.pdf")

    assert key == "K1"


def test_setup_checker_uses_configured_system_dir_for_exports(tmp_path: Path) -> None:
    (tmp_path / "paperforge.json").write_text(
        '{"vault_config": {"system_dir": "02_文献管理/System"}}',
        encoding="utf-8",
    )
    exports_dir = tmp_path / "02_文献管理" / "System" / "PaperForge" / "exports"
    exports_dir.mkdir(parents=True)
    (exports_dir / "demo.json").write_text("[]", encoding="utf-8")

    result = SetupChecker(tmp_path).run()

    assert result.details["bbt_exports_found"] is True


def test_vector_runtime_paths_use_configured_system_dir(tmp_path: Path) -> None:
    (tmp_path / "paperforge.json").write_text(
        '{"vault_config": {"system_dir": "02_文献管理/System"}}',
        encoding="utf-8",
    )

    vector_db_path = get_vector_db_path(tmp_path)
    build_state_path = get_vector_build_state_path(tmp_path)

    assert "02_文献管理" in str(vector_db_path)
    assert "02_文献管理" in str(build_state_path)
    assert vector_db_path.name == "vectors"
    assert build_state_path.name == "vector-build-state.json"


def test_preflight_index_path_resolves_correctly(tmp_path: Path) -> None:
    (tmp_path / "paperforge.json").write_text(
        '{"vault_config": {"system_dir": "02_文献管理/System"}}',
        encoding="utf-8",
    )
    from paperforge.config import paperforge_paths
    paths = paperforge_paths(tmp_path)
    expected = tmp_path / "02_文献管理" / "System" / "PaperForge" / "indexes" / "formal-library.json"
    assert paths["index"] == expected.resolve()
