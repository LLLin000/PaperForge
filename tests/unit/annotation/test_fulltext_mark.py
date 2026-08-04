"""Tests for writing imported annotation highlights back to fulltext.md."""

from __future__ import annotations

import sqlite3
import json
from pathlib import Path

from paperforge.annotation.fulltext_mark import (
    apply_annotations_to_fulltext_file,
    apply_imported_annotations_to_fulltext,
)
from paperforge.annotation.schema import ensure_schema


def test_apply_annotations_to_fulltext_file_writes_colored_marks(tmp_path: Path) -> None:
    fulltext = tmp_path / "fulltext.md"
    fulltext.write_text(
        "TROP2 expression marks one sentence.\n\n"
        "A second yellow sentence is also highlighted.",
        encoding="utf-8",
    )
    rows = [
        {
            "id": "ann-1",
            "selected_text": "TROP2 expression",
            "color": "#ffd400",
            "page_index": 0,
            "page_label": "1",
            "sort_index": "0",
        },
        {
            "id": "ann-2",
            "selected_text": "second yellow sentence",
            "color": "#ffd400",
            "page_index": 1,
            "page_label": "2",
            "sort_index": "1",
        },
    ]

    result = apply_annotations_to_fulltext_file(fulltext, rows)

    assert result == {"applied": 2, "unresolved": 0, "fulltext_path": str(fulltext)}
    text = fulltext.read_text(encoding="utf-8")
    assert text.count('class="paperforge-annotation-highlight"') == 2
    assert 'data-paperforge-annotation-id="ann-1"' in text
    assert 'data-page-label="1"' in text
    assert 'style="background-color: #ffd400;"' in text
    assert ">TROP2 expression</mark>" in text


def test_apply_annotations_to_fulltext_file_is_idempotent(tmp_path: Path) -> None:
    fulltext = tmp_path / "fulltext.md"
    fulltext.write_text("The same selected text should not be wrapped twice.", encoding="utf-8")
    rows = [{
        "id": "ann-1",
        "selected_text": "same selected text",
        "color": "#ffd400",
        "page_index": 0,
        "page_label": "1",
        "sort_index": "0",
    }]

    first = apply_annotations_to_fulltext_file(fulltext, rows)
    second = apply_annotations_to_fulltext_file(fulltext, rows)

    text = fulltext.read_text(encoding="utf-8")
    assert first["applied"] == 1
    assert second["applied"] == 1
    assert text.count('data-paperforge-annotation-id="ann-1"') == 1
    assert "<mark" in text
    assert "<mark" not in text.split("<mark", 1)[1]


def test_apply_annotations_to_fulltext_file_reports_unmatched_text(tmp_path: Path) -> None:
    fulltext = tmp_path / "fulltext.md"
    fulltext.write_text("Only existing text is available.", encoding="utf-8")
    rows = [{
        "id": "ann-missing",
        "selected_text": "missing TROP2 text",
        "color": "#ffd400",
        "page_index": 0,
        "page_label": "1",
        "sort_index": "0",
    }]

    result = apply_annotations_to_fulltext_file(fulltext, rows)

    assert result["applied"] == 0
    assert result["unresolved"] == 1
    assert "<mark" not in fulltext.read_text(encoding="utf-8")


def test_apply_annotations_to_fulltext_file_prefers_matching_page_marker(tmp_path: Path) -> None:
    fulltext = tmp_path / "fulltext.md"
    fulltext.write_text(
        "<!-- page 1 -->\n"
        "Repeated TROP2 phrase appears here first.\n\n"
        "<!-- page 2 -->\n"
        "Repeated TROP2 phrase appears here second.",
        encoding="utf-8",
    )
    rows = [{
        "id": "ann-page-2",
        "selected_text": "Repeated TROP2 phrase",
        "color": "#ffd400",
        "page_index": 1,
        "page_label": "2",
        "sort_index": "0",
    }]

    result = apply_annotations_to_fulltext_file(fulltext, rows)

    assert result["applied"] == 1
    text = fulltext.read_text(encoding="utf-8")
    first, second = text.split("<!-- page 2 -->")
    assert "<mark" not in first
    assert 'data-paperforge-annotation-id="ann-page-2"' in second


def test_apply_annotations_to_fulltext_file_matches_markdown_math_ocr_variants(
    tmp_path: Path,
) -> None:
    fulltext = tmp_path / "fulltext.md"
    fulltext.write_text(
        "<!-- page 3 -->\n"
        "Notably, acinar cells of $Ptf1a^{ERT}$ control and "
        "$Ptf1a^{ERT};K^{*}$ mice showed slight differences.",
        encoding="utf-8",
    )
    rows = [{
        "id": "ann-math",
        "selected_text": "acinar cells of Ptf1aERT control and Ptf1aERT;K* mice",
        "color": "#ffd400",
        "page_index": 2,
        "page_label": "3",
        "sort_index": "0",
    }]

    result = apply_annotations_to_fulltext_file(fulltext, rows)

    assert result["applied"] == 1
    text = fulltext.read_text(encoding="utf-8")
    assert 'data-paperforge-annotation-id="ann-math"' in text
    assert "$Ptf1a^{ERT}$ control" in text


def test_apply_annotations_to_fulltext_file_matches_long_selection_with_internal_ocr_variant(
    tmp_path: Path,
) -> None:
    fulltext = tmp_path / "fulltext.md"
    fulltext.write_text(
        "<!-- page 3 -->\n"
        "such as $Cela1$ and $Cpa1$. $Cela1$ showed lower expression levels in "
        "acinar cells of $Ptf1a^{ERT};K^{*}$ and $Ptf1a^{ERT};K^{*};Pdx1^{E/F}$ "
        "animals, an indicator of distinct differentiation states (Fig. 1D).",
        encoding="utf-8",
    )
    rows = [{
        "id": "ann-anchor",
        "selected_text": (
            "such as Cela1 and Cpa1. Cela1 showed lower expression levels in "
            "acinar cells of Ptf1aERT;K* and Ptf1aERT;K*;Pdx1f/f animals, "
            "an indicator of distinct differentiation states (Fig. 1D)."
        ),
        "color": "#ffd400",
        "page_index": 2,
        "page_label": "3",
        "sort_index": "0",
    }]

    result = apply_annotations_to_fulltext_file(fulltext, rows)

    assert result["applied"] == 1
    text = fulltext.read_text(encoding="utf-8")
    assert 'data-paperforge-annotation-id="ann-anchor"' in text
    assert "$Ptf1a^{ERT};K^{*};Pdx1^{E/F}$" in text


def test_apply_annotations_to_fulltext_file_matches_html_superscript_variants(
    tmp_path: Path,
) -> None:
    fulltext = tmp_path / "fulltext.md"
    fulltext.write_text(
        "<!-- page 3 -->\n"
        "from benign models (Villin1-Cre<sup>ER</sup> Apc<sup>fl/fl</sup>) "
        "to invasive adenocarcinoma models.",
        encoding="utf-8",
    )
    rows = [{
        "id": "ann-html-sup",
        "selected_text": (
            "from benign models (Villin1–CreER Apcfl/fl) "
            "to invasive adenocarcinoma models"
        ),
        "color": "#ffd400",
        "page_index": 2,
        "page_label": "3",
        "sort_index": "0",
    }]

    result = apply_annotations_to_fulltext_file(fulltext, rows)

    assert result["applied"] == 1
    text = fulltext.read_text(encoding="utf-8")
    assert 'data-paperforge-annotation-id="ann-html-sup"' in text
    assert "<sup>ER</sup>" in text


def test_apply_annotations_to_fulltext_file_matches_long_html_selection_with_ocr_confusions(
    tmp_path: Path,
) -> None:
    fulltext = tmp_path / "fulltext.md"
    fulltext.write_text(
        "<!-- page 3 -->\n"
        "from benign models (Villin1-Cre<sup>ER</sup> Apc<sup>fl/fl</sup>, "
        "Villin1-Cre<sup>ER</sup> Apc<sup>fl/fl</sup>, Trp53<sup>fl/fl</sup>, "
        "Villin1-Cre<sup>ER</sup> Apc<sup>fl/fl</sup> Kras<sup>G12D/+</sup>) "
        "to invasive adenocarcinoma models (Villin1-Cre<sup>ER</sup> Apc<sup>fl/+</sup>, "
        "Kras<sup>G12D/+</sup>, Trp53<sup>fl/fl</sup> (VAKP), "
        "Villin1-CreER<sup>ER</sup> Kras<sup>G12D/+</sup>, Trp53<sup>fl/fl</sup> (VKP)) "
        "to highly metastatic adenocarcinoma models (Villin1-Cre<sup>ER</sup> "
        "Apc<sup>fl/+</sup>, Kras<sup>G12D/+</sup>, Trp53<sup>fl/fl</sup> "
        "Smad4<sup>fl/fl</sup> (VAKPS), Villin1-CreER<sup>ER</sup> "
        "Kras<sup>G12D/+</sup>, Trp53<sup>fl/fl</sup> Rosa26<sup>Nlicd/+</sup> (VKPN)), "
        "we found higher TROP2 levels.",
        encoding="utf-8",
    )
    rows = [{
        "id": "ann-long-html",
        "selected_text": (
            "from benign models (Villin1–CreER Apcfl/fl, Villin1–CreER Apcfl/fl "
            "Trp53fl/fl, Villin1–CreER Apcfl/fl KrasG12D/+) to invasive "
            "adenocarcinoma models (Villin1–CreER Apcfl/+ KrasG12D/+ Trp53fl/fl "
            "(VAKP), Villin1–CreER KrasG12D/+ Trp53fl/fl(VKP)) to highly metastatic "
            "adenocarcinoma models (Villin1–CreER Apcfl/+ KrasG12D/+ Trp53fl/fl "
            "Smad4fl/fl (VAKPS), Villin1–CreER KrasG12D/+ Trp53fl/fl "
            "Rosa26N1icd/+ (VKPN))"
        ),
        "color": "#ffd400",
        "page_index": 2,
        "page_label": "3",
        "sort_index": "0",
    }]

    result = apply_annotations_to_fulltext_file(fulltext, rows)

    assert result["applied"] == 1
    text = fulltext.read_text(encoding="utf-8")
    assert 'data-paperforge-annotation-id="ann-long-html"' in text
    assert "Rosa26<sup>Nlicd/+</sup> (VKPN))</mark>" in text
    assert "we found higher TROP2 levels" not in text.split("</mark>", 1)[0]


def test_apply_annotations_to_fulltext_file_accepts_sqlite_rows(tmp_path: Path) -> None:
    fulltext = tmp_path / "fulltext.md"
    fulltext.write_text("SQLite row selected text is present.", encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE annotations (id TEXT, selected_text TEXT, color TEXT, page_index INTEGER, page_label TEXT, sort_index TEXT)"
    )
    conn.execute(
        "INSERT INTO annotations VALUES ('ann-row', 'selected text', '#ffcc00', 3, '4', '7')"
    )
    row = conn.execute("SELECT * FROM annotations").fetchone()

    result = apply_annotations_to_fulltext_file(fulltext, [row])

    assert result["applied"] == 1
    assert 'data-page-index="3"' in fulltext.read_text(encoding="utf-8")
    conn.close()


def test_apply_imported_annotations_to_fulltext_uses_library_index(tmp_path: Path) -> None:
    vault = tmp_path
    index_path = vault / "System" / "PaperForge" / "indexes" / "formal-library.json"
    index_path.parent.mkdir(parents=True)
    fulltext = vault / "Resources" / "Literature" / "TROP2" / "fulltext.md"
    fulltext.parent.mkdir(parents=True)
    fulltext.write_text(
        "TROP2 has one yellow highlight.\n\n"
        "The second imported highlight should be visible in the markdown.",
        encoding="utf-8",
    )
    index_path.write_text(
        json.dumps({
            "items": [{
                "zotero_key": "TROP2KEY",
                "fulltext_path": "Resources/Literature/TROP2/fulltext.md",
            }]
        }),
        encoding="utf-8",
    )

    db_path = index_path.parent / "annotations.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        conn.executemany(
            """INSERT INTO annotations (
                id, paper_id, type, selected_text, color, page_index, page_label,
                sort_index, created_at, updated_at
            ) VALUES (?, ?, 'highlight', ?, ?, ?, ?, ?, '2024-01-01', '2024-01-01')""",
            [
                ("ann-yellow-1", "TROP2KEY", "one yellow highlight", "#ffd400", 0, "1", "0"),
                ("ann-yellow-2", "TROP2KEY", "second imported highlight", "#ffd400", 1, "2", "1"),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    result = apply_imported_annotations_to_fulltext(vault, "TROP2KEY", db_path)

    assert result["total"] == 2
    assert result["applied"] == 2
    text = fulltext.read_text(encoding="utf-8")
    assert text.count('class="paperforge-annotation-highlight"') == 2
    assert 'data-paperforge-annotation-id="ann-yellow-1"' in text


def test_apply_imported_annotations_to_fulltext_prefers_literature_fulltext_before_ocr(
    tmp_path: Path,
) -> None:
    vault = tmp_path
    (vault / "paperforge.json").write_text(
        json.dumps({
            "schema_version": "2",
            "vault_config": {
                "system_dir": "System",
                "resources_dir": "4.Paper",
                "literature_dir": "Literature",
                "control_dir": "LiteratureControl",
                "base_dir": "05_Bases",
                "skill_dir": ".opencode/skills",
                "command_dir": ".opencode/command",
            },
        }),
        encoding="utf-8",
    )
    literature_fulltext = (
        vault / "4.Paper" / "Literature" / "Tumor" / "TROP2KEY - Paper" / "fulltext.md"
    )
    literature_fulltext.parent.mkdir(parents=True)
    literature_fulltext.write_text("Visible TROP2 highlight belongs here.", encoding="utf-8")
    ocr_fulltext = vault / "System" / "PaperForge" / "ocr" / "TROP2KEY" / "fulltext.md"
    ocr_fulltext.parent.mkdir(parents=True)
    ocr_fulltext.write_text("Visible TROP2 highlight should not be marked here.", encoding="utf-8")

    db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
    db_path.parent.mkdir(parents=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        conn.execute(
            """INSERT INTO annotations (
                id, paper_id, type, selected_text, color, created_at, updated_at
            ) VALUES ('ann-lit', 'TROP2KEY', 'highlight', 'Visible TROP2 highlight', '#ffd400',
                '2024-01-01', '2024-01-01')"""
        )
        conn.commit()
    finally:
        conn.close()

    result = apply_imported_annotations_to_fulltext(vault, "TROP2KEY", db_path)

    assert result["fulltext_path"] == str(literature_fulltext)
    assert 'data-paperforge-annotation-id="ann-lit"' in literature_fulltext.read_text(encoding="utf-8")
    assert "<mark" not in ocr_fulltext.read_text(encoding="utf-8")
