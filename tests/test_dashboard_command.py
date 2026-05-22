from pathlib import Path

from paperforge.commands.dashboard import _dashboard_from_db


def test_dashboard_from_db_uses_configured_system_dir(tmp_path: Path) -> None:
    (tmp_path / "paperforge.json").write_text(
        '{"vault_config": {"system_dir": "02_文献管理/System"}}',
        encoding="utf-8",
    )
    db_path = tmp_path / "02_文献管理" / "System" / "PaperForge" / "indexes" / "paperforge.db"
    db_path.parent.mkdir(parents=True)

    import sqlite3

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE papers (domain TEXT, has_pdf INTEGER, ocr_status TEXT)"
    )
    conn.execute(
        "INSERT INTO papers(domain, has_pdf, ocr_status) VALUES (?, ?, ?)",
        ("Sports", 1, "done"),
    )
    conn.commit()
    conn.close()

    data = _dashboard_from_db(tmp_path)

    assert data is not None
    assert data["stats"]["papers"] == 1
