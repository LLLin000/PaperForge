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


def test_cluster_chars_splits_dual_column_gutter_and_ignores_giant_spaces():
    import pymupdf
    from paperforge.services.pdf_grounding import _cluster_chars_to_rects, _rects_look_distorted

    class FakePage:
        rect = pymupdf.Rect(0, 0, 600, 800)

    chars = [
        ("a", pymupdf.Rect(50, 100, 120, 112), "left"),
        # Oversized invisible space glyph spanning gutter
        ("", pymupdf.Rect(120, 100, 340, 112), " "),
        # Right column word at exact same Y
        ("b", pymupdf.Rect(340, 100, 420, 112), "right"),
    ]
    rects, _ = _cluster_chars_to_rects(chars, FakePage())
    assert len(rects) == 2
    assert rects[0][2] <= 0.25
    assert rects[1][0] >= 0.55

    assert _rects_look_distorted([[0.05, 0.1, 0.96, 0.12]], char_count=10) is True
    assert _rects_look_distorted([[0.05, 0.1, 0.45, 0.12]], char_count=18) is False


def test_agent_apply_enforces_ocr_dedup_paraphrase_cap_and_replace_lens(tmp_path: Path, monkeypatch):
    import io
    import pytest
    from paperforge import cli
    from paperforge.services.annotations_service import agent_apply_annotations

    vault, _pdf = _make_pdf_test_vault(tmp_path, key="APPLY001")

    # 1. Existing user highlight & adopted highlight on page 1
    user_ann = add_annotation(
        vault,
        "APPLY001",
        page=1,
        rects=[[0.1, 0.80, 0.4, 0.84]],
        kind="highlight",
        color="yellow",
        comment="Personal highlight stays forever",
    )

    # 2. Batch transaction with: valid quote, paraphrase reject, short reject, duplicate skip, figure, and cap=2
    res = agent_apply_annotations(
        vault,
        "APPLY001",
        [
            {
                "quote": "PEMF stimulation at 75 Hz ± 5 uM markedly enhanced galvanotaxis",
                "comment": "PEMF stimulation at 75 Hz ± 5 uM markedly enhanced galvanotaxis",
            },
            {
                "quote": "PEMF stimulation at 75 Hz ± 5 uM markedly enhanced galvanotaxis",
                "comment": "Too短",
            },
            {
                "quote": "PEMF stimulation at 75 Hz ± 5 uM markedly enhanced galvanotaxis",
                "comment": "Primary upstream electrical trigger defining the experimental therapeutic window.",
            },
            {
                "quote": "PEMF stimulation at 75 Hz ± 5 uM markedly enhanced galvanotaxis",
                "comment": "Duplicate target should be skipped rather than stacked onto the same text.",
            },
            {
                "figure_id": "figure_001",
                "comment": "Confirm whether error bars represent SD or SEM across independent donors.",
            },
            {
                "quote": "Second column continuation: multivariate regression confirmed age independence",
                "comment": "This 3rd created item exceeds max_items=2 and should be rejected cleanly.",
            },
        ],
        lens="skeleton",
        max_items=2,
        batch_id="batch_test01",
    )
    assert res["created_count"] == 2
    assert res["skipped_count"] == 1
    assert res["rejected_count"] == 3
    reasons = {r["reason"] for r in res["rejected"]}
    assert reasons == {"comment_paraphrases_quote", "comment_too_short", "batch_limit_exceeded"}
    assert all(c["batch_id"] == "batch_test01" for c in res["created"])
    assert res["skipped"][0]["reason"] == "duplicate_target"

    # 3. replace_lens=True clears old skeleton agent marks while keeping user highlights
    buf = io.StringIO()
    payload = json.dumps(
        {
            "lens": "skeleton",
            "replace_lens": True,
            "items": [
                {
                    "quote": "Second column continuation: multivariate regression confirmed age independence across all 64 rabbits.",
                    "comment": "Cross-column regression evidence supporting model generalizability.",
                }
            ],
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    from contextlib import redirect_stdout

    with redirect_stdout(buf):
        rc = cli.main(["--vault", str(vault), "annotations", "agent-apply", "APPLY001", "--input", "-", "--json"])
    assert rc == 0, buf.getvalue()
    cli_out = json.loads(buf.getvalue())
    assert cli_out["ok"] is True
    assert cli_out["data"]["replaced_count"] == 2
    assert cli_out["data"]["created_count"] == 1
    active = list_annotations(vault, "APPLY001")
    assert {a["ann_id"] for a in active if a["author"] == "user"} == {user_ann["ann_id"]}
    assert len([a for a in active if a["author"] == "agent"]) == 1

    # 4. OCR-not-ready blocks AI annotation unless OCR status or fulltext exists
    import shutil
    shutil.rmtree(vault / ".paperforge" / "ocr" / "APPLY001")
    with pytest.raises(ValueError, match="OCR is not ready"):
        agent_apply_annotations(
            vault,
            "APPLY001",
            [{"figure_id": "figure_001", "comment": "Should fail because OCR artifacts and status are not ready"}],
        )


def test_agent_apply_atomic_replace_and_vault_boundary(tmp_path: Path):
    """PF-OCR-004 & PF-SEC-008: replace_lens=True never wipes prior marks if 0 items stage; rejects bad page_hint/color & path escape."""
    import pytest
    from paperforge.services.annotations_service import _resolve_paper_location, agent_apply_annotations, list_annotations
    from paperforge.worker.asset_index import atomic_write_index, build_envelope, get_index_path

    vault, _ = _make_pdf_test_vault(tmp_path, key="ATOMIC1")
    first = agent_apply_annotations(
        vault,
        "ATOMIC1",
        [
            {
                "quote": "PEMF stimulation at 75 Hz ± 5 uM markedly enhanced galvanotaxis",
                "comment": "Primary effect magnitude showing strong chondrogenic stimulation across groups.",
                "tags": "efficacy",  # bare string normalized cleanly, not split into characters
            }
        ],
        lens="skeleton",
        replace_lens=True,
    )
    assert first["created_count"] == 1
    assert first["created"][0]["tags"] == ["efficacy"]

    # Malformed / ungrounded batch with replace_lens=True must NOT delete the prior annotation
    bad = agent_apply_annotations(
        vault,
        "ATOMIC1",
        [
            {"quote": "PEMF", "comment": "Analytical insight cleanly formatted here.", "page_hint": "not-an-int"},
            {"quote": "PEMF", "comment": "Analytical insight cleanly formatted here.", "color": "neon_pink"},
            {"quote": "nonexistent text xyz", "comment": "Analytical insight cleanly formatted here."},
        ],
        lens="skeleton",
        replace_lens=True,
    )
    assert bad["created_count"] == 0
    assert bad["replaced_count"] == 0
    assert bad["rejected_count"] == 3
    reasons = {r["reason"] for r in bad["rejected"]}
    assert reasons == {"invalid_page_hint", "invalid_color", "grounding_failed"}
    remaining = [a for a in list_annotations(vault, "ATOMIC1") if a["author"] == "agent"]
    assert len(remaining) == 1

    # PF-SEC-008: paper_root traversal outside vault raises ValueError
    atomic_write_index(
        get_index_path(vault),
        build_envelope([{"zotero_key": "EVIL01", "paper_root": "../../outside_vault"}]),
    )
    with pytest.raises(ValueError, match="escapes vault boundary"):
        _resolve_paper_location(vault, "EVIL01")
