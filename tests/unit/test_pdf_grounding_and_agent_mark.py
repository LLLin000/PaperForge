"""Unit tests for Commit 2 (v2.2): 3-stage fuzzy PDF grounding engine and agent-mark layer."""
from __future__ import annotations

import json
from pathlib import Path

from paperforge.services.annotations_service import (
    add_annotation,
    adopt_agent_annotation,
    agent_mark_annotation,
    clear_agent_annotations,
    list_annotations,
)
from paperforge.services.pdf_grounding import ground_target_in_pdf
from paperforge.worker.asset_index import atomic_write_index
from tests.conftest import canonical_test_config


def _make_pdf_test_vault(tmp_path: Path, key: str = "GRD00001") -> tuple[Path, Path]:
    import pymupdf

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")
    pf = vault / ".paperforge"
    ws = vault / "Resources" / "Literature" / "Ortho" / f"{key} - Test Paper"
    ws.mkdir(parents=True)
    (ws / f"{key}.md").write_text(f'---\nzotero_key: "{key}"\n---\n', encoding="utf-8")

    zot_st = pf / "Zotero" / "storage" / "GR1"
    zot_st.mkdir(parents=True)
    pdf_path = zot_st / "paper.pdf"

    with pymupdf.open() as doc:
        # Page 1: hyphenation, symbol drift, and a two-column split block
        p1 = doc.new_page(width=600, height=800)
        p1.insert_text(
            (60, 120),
            "PEMF stimulation at 75 Hz ± 5 µM markedly enhanced galvano-\ntaxis of primary chondrocytes in agarose hydrogels.",
            fontsize=11,
        )
        p1.insert_text(
            (320, 420),
            "Second column continuation:\nmultivariate regression confirmed\nage independence across all 64 rabbits.",
            fontsize=11,
        )
        # Page 2: pure graphic/scanned page with zero extractable text characters
        p2 = doc.new_page(width=600, height=800)
        p2.draw_rect(pymupdf.Rect(70, 180, 520, 320), color=(0.2, 0.2, 0.2))
        doc.save(pdf_path)

    atomic_write_index(
        pf / "indexes" / "formal-library.json",
        {
            "version": 1,
            "items": [
                {
                    "zotero_key": key,
                    "title": "Test Paper",
                    "domain": "Ortho",
                    "has_pdf": True,
                    "pdf_path": "storage:GR1/paper.pdf",
                    "paper_root": f"Resources/Literature/Ortho/{key} - Test Paper/",
                    "main_note_path": f"Resources/Literature/Ortho/{key} - Test Paper/{key}.md",
                    "note_path": f"Resources/Literature/Ortho/{key} - Test Paper/{key}.md",
                }
            ],
        },
    )

    ocr_struct = pf / "ocr" / key / "structure"
    ocr_struct.mkdir(parents=True)
    blocks = [
        {
            "block_id": "blk_hyp",
            "page": 1,
            "page_width": 600,
            "page_height": 800,
            "bbox": [55, 105, 290, 165],
            "section_path": "Results > 3.1 Parameters",
            "text": "PEMF stimulation at $75\\,\\mathrm{Hz}$ ± 5 uM markedly enhanced galvanotaxis of primary chondrocytes in agarose hydrogels.",
        },
        {
            "block_id": "blk_merged_col",
            "page": 1,
            "page_width": 600,
            "page_height": 800,
            # Left column box only — tests Stage 2b same-page cross-column rescue!
            "bbox": [55, 400, 280, 460],
            "section_path": "Results > 3.2 Regression",
            "text": "Second column continuation: multivariate regression confirmed age independence across all 64 rabbits.",
        },
        {
            "block_id": "blk_scanned",
            "page": 2,
            "page_width": 600,
            "page_height": 800,
            "bbox": [70, 180, 520, 320],
            "section_path": "Discussion > Limitations",
            "text": "Scanned older figure caption and paragraph with zero embedded PDF text.",
        },
    ]
    (ocr_struct / "blocks.structured.jsonl").write_text(
        "\n".join(json.dumps(b, ensure_ascii=False) for b in blocks) + "\n",
        encoding="utf-8",
    )
    (ocr_struct / "figure_inventory.json").write_text(
        json.dumps(
            {
                "matched_figures": [
                    {
                        "figure_id": "figure_001",
                        "page": 2,
                        "page_width": 600,
                        "page_height": 800,
                        "cluster_bbox": [70, 180, 520, 320],
                        "caption_text": "Dose response diagram",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return vault, pdf_path


def test_grounding_handles_hyphenation_cross_column_scanned_and_figure(tmp_path: Path):
    vault, pdf_path = _make_pdf_test_vault(tmp_path)

    # 1. Stage 2a: hyphenation + symbol/LaTeX normalization -> exact_sentence
    g1 = ground_target_in_pdf(
        vault,
        "GRD00001",
        pdf_path,
        quote="PEMF stimulation at 75 Hz ± 5 uM markedly enhanced galvanotaxis of primary chondrocytes",
    )
    assert g1["grounding_tier"] == "exact_sentence"
    assert g1["kind"] == "highlight"
    assert g1["page"] == 1
    assert len(g1["rects"]) >= 1

    # 2. Stage 2b: cross-column merged OCR bbox -> exact_cross_column rescue on right half (x0 > 0.5)
    g2 = ground_target_in_pdf(
        vault,
        "GRD00001",
        pdf_path,
        quote="Second column continuation: multivariate regression confirmed age independence across all 64 rabbits.",
    )
    assert g2["grounding_tier"] == "exact_cross_column"
    assert g2["kind"] == "highlight"
    assert g2["rects"][0][0] > 0.45

    # 3. Stage 3: scanned page -> honest margin bracket fallback (never misplaces random highlights)
    g3 = ground_target_in_pdf(
        vault,
        "GRD00001",
        pdf_path,
        quote="Scanned older figure caption and paragraph with zero embedded PDF text.",
    )
    assert g3["grounding_tier"] == "margin_fallback"
    assert g3["kind"] == "margin"
    assert g3["page"] == 2
    assert g3["rects"][0][2] - g3["rects"][0][0] <= 0.03

    # 4. Figure object resolution
    g4 = ground_target_in_pdf(vault, "GRD00001", pdf_path, figure_id="figure_001")
    assert g4["grounding_tier"] == "exact_object"
    assert g4["kind"] == "area"
    assert g4["page"] == 2


def test_agent_mark_adopt_and_clear_preserves_user_highlights(tmp_path: Path):
    vault, _pdf = _make_pdf_test_vault(tmp_path, key="GRD00002")

    user_ann = add_annotation(
        vault,
        "GRD00002",
        page=1,
        rects=[[0.1, 0.14, 0.4, 0.17]],
        kind="highlight",
        color="yellow",
        comment="My own reading note",
    )
    ai_ann1 = agent_mark_annotation(
        vault,
        "GRD00002",
        quote="PEMF stimulation at 75 Hz ± 5 uM markedly enhanced galvanotaxis",
        comment="Check whether 5 uM refers to extracellular medium",
        lens="critique",
    )
    ai_ann2 = agent_mark_annotation(
        vault,
        "GRD00002",
        figure_id="figure_001",
        comment="Primary dose curve",
        lens="skeleton",
    )

    assert ai_ann1["author"] == "agent"
    assert ai_ann1["grounding_tier"] == "exact_sentence"
    assert ai_ann2["author"] == "agent"
    assert ai_ann2["kind"] == "area"

    adopted = adopt_agent_annotation(vault, "GRD00002", ai_ann1["ann_id"])
    assert adopted["author"] == "user"

    # Clearing agent annotations deletes ai_ann2, leaves user_ann AND adopted ai_ann1 untouched
    cleared = clear_agent_annotations(vault, "GRD00002")
    assert cleared["deleted_count"] == 1
    assert cleared["deleted_ids"] == [ai_ann2["ann_id"]]
    remaining_ids = {a["ann_id"] for a in list_annotations(vault, "GRD00002")}
    assert remaining_ids == {user_ann["ann_id"], ai_ann1["ann_id"]}
