"""Real-PDF E2E & accuracy tests for non-OCR grounding, CropBox/rotation, span-bloat guard, and single-commit batching."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.services import annotations_service
from paperforge.services.annotations_service import (
    add_annotation,
    adopt_agent_annotation,
    agent_apply_annotations,
    agent_mark_annotation,
    clear_agent_annotations,
    list_annotations,
)
from paperforge.services.pdf_grounding import (
    _align_folded_quote,
    ground_target_in_pdf,
)
from paperforge.worker.asset_index import atomic_write_index
from tests.conftest import canonical_test_config


def _assert_rects_in_unit_bounds(rects: list[list[float]]) -> None:
    assert rects, "Expected at least one rect"
    for r in rects:
        assert len(r) == 4
        x0, y0, x1, y1 = r
        assert 0.0 <= x0 <= x1 <= 1.0, f"Invalid X bounds in {r}"
        assert 0.0 <= y0 <= y1 <= 1.0, f"Invalid Y bounds in {r}"


def _build_realistic_multicolumn_pdf_vault(
    tmp_path: Path,
    *,
    key: str = "REALPDF1",
    with_ocr: bool = False,
) -> tuple[Path, Path]:
    import pymupdf

    vault = tmp_path / f"vault_{'ocr' if with_ocr else 'noocr'}"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")
    pf = vault / ".paperforge"
    ws = vault / "Resources" / "Literature" / "Ortho" / f"{key} - Realistic Paper"
    ws.mkdir(parents=True)
    (ws / f"{key}.md").write_text(f'---\nzotero_key: "{key}"\nocr_status: "{"done" if with_ocr else "pending"}"\n---\n', encoding="utf-8")

    zot_st = pf / "Zotero" / "storage" / "RL1"
    zot_st.mkdir(parents=True)
    pdf_path = zot_st / "realistic.pdf"

    with pymupdf.open() as doc:
        # Page 1: Dual-column layout with hyphenated wraps, symbol drift, cross-column sentence,
        # and native Figure 1 + Table 1 captions.
        p1 = doc.new_page(width=612, height=792)
        p1.insert_text(
            (54, 110),
            "Introduction: electro-\nstimulation at 50 Hz ± 5 µM\naccelerated tendon healing.",
            fontsize=10.5,
        )
        p1.insert_text(
            (54, 660),
            "In our cohort, logistic regression\nconfirmed that baseline tear size",
            fontsize=10.5,
        )
        p1.insert_text(
            (320, 110),
            "predicted retear at 24 months.\nSubgroup analysis showed stable\neffects across all centers.",
            fontsize=10.5,
        )
        # Native Figure 1 drawing + caption in right column
        p1.draw_rect(pymupdf.Rect(320, 220, 550, 340), color=(0.1, 0.2, 0.8), fill=(0.85, 0.9, 1.0))
        p1.insert_text(
            (320, 360),
            "Figure 1. Kaplan-Meier survival curve stratified by graft diameter.",
            fontsize=10,
        )
        # Native Table 1 caption in right column
        p1.insert_text(
            (320, 440),
            "Table 1: Baseline demographic and surgical characteristics.",
            fontsize=10,
        )

        # Page 2: Non-zero CropBox (cropped from 650x850 to [50, 60, 550, 740])
        p2 = doc.new_page(width=650, height=850)
        p2.insert_text(
            (110, 140),
            "CropBox page validation: biomechanical stiffness reached 412 N/mm.",
            fontsize=11,
        )
        p2.set_cropbox(pymupdf.Rect(50, 60, 550, 740))

        # Page 3: Rotated 90 degrees clockwise (landscape table/figure page) with CropBox
        p3 = doc.new_page(width=600, height=800)
        p3.draw_rect(pymupdf.Rect(100, 100, 380, 260), color=(0.8, 0.1, 0.1), fill=(1.0, 0.85, 0.85))
        p3.insert_text(
            (100, 285),
            "Figure 2. Landscape rotated shear-modulus plot across cycles.",
            fontsize=11,
        )
        p3.insert_text(
            (100, 340),
            "Rotated page finding: cyclic creep plateaued after 1000 loading cycles.",
            fontsize=11,
        )
        p3.set_cropbox(pymupdf.Rect(50, 60, 550, 740))
        p3.set_rotation(90)

        # Page 4: Pure scanned / vector page with zero extractable text characters
        p4 = doc.new_page(width=600, height=800)
        p4.draw_rect(pymupdf.Rect(80, 150, 520, 400), color=(0.3, 0.3, 0.3))

        doc.save(pdf_path)

    atomic_write_index(
        pf / "indexes" / "formal-library.json",
        {
            "version": 1,
            "items": [
                {
                    "zotero_key": key,
                    "title": "Realistic Multi-Column Study",
                    "domain": "Ortho",
                    "has_pdf": True,
                    "ocr_status": "done" if with_ocr else "pending",
                    "pdf_path": "storage:RL1/realistic.pdf",
                    "paper_root": f"Resources/Literature/Ortho/{key} - Realistic Paper/",
                    "main_note_path": f"Resources/Literature/Ortho/{key} - Realistic Paper/{key}.md",
                    "note_path": f"Resources/Literature/Ortho/{key} - Realistic Paper/{key}.md",
                }
            ],
        },
    )

    if with_ocr:
        ocr_struct = pf / "ocr" / key / "structure"
        ocr_struct.mkdir(parents=True)
        blocks = [
            {
                "block_id": "blk_p1_intro",
                "page": 1,
                "page_width": 612,
                "page_height": 792,
                "bbox": [50, 95, 290, 155],
                "section_path": "Introduction",
                "text": "Introduction: electrostimulation at $50\\,\\mathrm{Hz}$ ± 5 uM accelerated tendon healing.",
            },
            {
                "block_id": "blk_p1_col1_end",
                "page": 1,
                "page_width": 612,
                "page_height": 792,
                "bbox": [50, 645, 290, 690],
                "section_path": "Results > Regression",
                "text": "In our cohort, logistic regression confirmed that baseline tear size",
            },
            {
                "block_id": "blk_p1_col2_top",
                "page": 1,
                "page_width": 612,
                "page_height": 792,
                "bbox": [315, 95, 560, 155],
                "section_path": "Results > Regression",
                "text": "predicted retear at 24 months. Subgroup analysis showed stable effects across all centers.",
            },
            {
                "block_id": "blk_p2_crop",
                "page": 2,
                "page_width": 500,
                "page_height": 680,
                "bbox": [55, 60, 460, 100],
                "section_path": "Results > Biomechanics",
                "text": "CropBox page validation: biomechanical stiffness reached 412 N/mm.",
            },
            {
                "block_id": "blk_p3_rot",
                "page": 3,
                "page_width": 680,
                "page_height": 500,
                "bbox": [330, 45, 420, 460],
                "section_path": "Results > Cyclic",
                "text": "Rotated page finding: cyclic creep plateaued after 1000 loading cycles.",
            },
            {
                "block_id": "blk_p4_scan",
                "page": 4,
                "page_width": 600,
                "page_height": 800,
                "bbox": [80, 150, 520, 400],
                "section_path": "Supplement",
                "text": "Scanned supplement diagram with zero text layer.",
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
                            "page": 1,
                            "page_width": 612,
                            "page_height": 792,
                            "cluster_bbox": [320, 220, 550, 375],
                            "caption_text": "Figure 1. Kaplan-Meier survival curve stratified by graft diameter.",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    return vault, pdf_path


@pytest.mark.parametrize("with_ocr", [False, True])
def test_e2e_realistic_pdf_grounding_with_and_without_ocr(tmp_path: Path, with_ocr: bool) -> None:
    key = "REALOCR" if with_ocr else "REALRAW"
    vault, pdf_path = _build_realistic_multicolumn_pdf_vault(tmp_path, key=key, with_ocr=with_ocr)

    # 1. Hyphenation + micro/LaTeX symbol drift -> exact_sentence
    g_hyp = ground_target_in_pdf(
        vault,
        key,
        pdf_path,
        quote="electrostimulation at 50 Hz ± 5 uM accelerated tendon healing.",
    )
    assert g_hyp["grounding_tier"] == "exact_sentence"
    assert g_hyp["page"] == 1
    _assert_rects_in_unit_bounds(g_hyp["rects"])

    # 2. Adjacent cross-column quote spanning bottom of col 1 -> top of col 2
    g_cross = ground_target_in_pdf(
        vault,
        key,
        pdf_path,
        quote="confirmed that baseline tear size predicted retear at 24 months.",
    )
    assert g_cross["grounding_tier"] in {"exact_cross_column", "exact_sentence"}
    assert g_cross["page"] == 1
    assert len(g_cross["rects"]) >= 2
    _assert_rects_in_unit_bounds(g_cross["rects"])
    # Must span from left column (x0 < 0.4) to right column (x0 > 0.45) without bridging gutter
    assert any(r[0] < 0.4 for r in g_cross["rects"])
    assert any(r[0] > 0.45 for r in g_cross["rects"])

    # 3. Short quote (< 35 chars) spanning 2 adjacent blocks, uniquely matched on page 1
    g_short = ground_target_in_pdf(
        vault,
        key,
        pdf_path,
        quote="baseline tear size predicted retear",
    )
    assert g_short["grounding_tier"] in {"exact_cross_column", "exact_sentence"}
    assert g_short["page"] == 1
    _assert_rects_in_unit_bounds(g_short["rects"])

    # 4. CropBox page (page 2)
    g_crop = ground_target_in_pdf(
        vault,
        key,
        pdf_path,
        quote="CropBox page validation: biomechanical stiffness reached 412 N/mm.",
    )
    assert g_crop["grounding_tier"] == "exact_sentence"
    assert g_crop["page"] == 2
    _assert_rects_in_unit_bounds(g_crop["rects"])
    # Text was inserted at (110, 140) on 650x850, cropped to [50, 60, 550, 740] -> visual x ~ 60/500 = 0.12
    assert 0.05 <= g_crop["rects"][0][0] <= 0.25
    assert 0.05 <= g_crop["rects"][0][1] <= 0.25

    # 5. Rotated 90-degree page (page 3) — must NOT be distorted/rejected into margin_fallback
    g_rot = ground_target_in_pdf(
        vault,
        key,
        pdf_path,
        quote="cyclic creep plateaued after 1000 loading cycles.",
    )
    assert g_rot["grounding_tier"] == "exact_sentence"
    assert g_rot["page"] == 3
    _assert_rects_in_unit_bounds(g_rot["rects"])
    # On 90-deg rotated page, text at raw y=340 -> raw-crop y=280 -> rotated visual x ~ (680-280)/680 = 0.588
    assert g_rot["rects"][0][0] > 0.45

    # 6. Figure & Table resolution (OCR inventory OR native caption fallback)
    g_fig1 = ground_target_in_pdf(vault, key, pdf_path, figure_id="figure_001")
    assert g_fig1["grounding_tier"] == "exact_object"
    assert g_fig1["kind"] == "area"
    assert g_fig1["page"] == 1
    _assert_rects_in_unit_bounds(g_fig1["rects"])

    g_tbl1 = ground_target_in_pdf(vault, key, pdf_path, figure_id="table_001")
    assert g_tbl1["grounding_tier"] == "exact_object"
    assert g_tbl1["kind"] == "area"
    assert g_tbl1["page"] == 1
    _assert_rects_in_unit_bounds(g_tbl1["rects"])

    g_fig2 = ground_target_in_pdf(vault, key, pdf_path, figure_id="Fig. 2")
    assert g_fig2["grounding_tier"] == "exact_object"
    assert g_fig2["kind"] == "area"
    assert g_fig2["page"] == 3
    _assert_rects_in_unit_bounds(g_fig2["rects"])

    # 7. Scanned-only page (page 4) with page_hint -> honest margin_fallback
    g_scan = ground_target_in_pdf(
        vault,
        key,
        pdf_path,
        quote="Scanned supplement diagram with zero text layer.",
        page_hint=4,
    )
    assert g_scan["grounding_tier"] == "margin_fallback"
    assert g_scan["kind"] == "margin"
    assert g_scan["page"] == 4
    _assert_rects_in_unit_bounds(g_scan["rects"])
    assert g_scan["rects"][0][2] - g_scan["rects"][0][0] <= 0.03


def test_scanned_only_pdf_without_ocr_requires_page_hint_or_gives_actionable_error(tmp_path: Path) -> None:
    import pymupdf

    vault = tmp_path / "vault_scan"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")
    pf = vault / ".paperforge"
    ws = vault / "Resources" / "Literature" / "Ortho" / "SCAN01 - Scan Only"
    ws.mkdir(parents=True)
    (ws / "SCAN01.md").write_text('---\nzotero_key: "SCAN01"\n---\n', encoding="utf-8")

    zot_st = pf / "Zotero" / "storage" / "SC1"
    zot_st.mkdir(parents=True)
    pdf_path = zot_st / "scan.pdf"
    with pymupdf.open() as doc:
        p1 = doc.new_page(width=600, height=800)
        p1.draw_rect(pymupdf.Rect(50, 50, 550, 750), color=(0.5, 0.5, 0.5))
        p2 = doc.new_page(width=600, height=800)
        p2.draw_rect(pymupdf.Rect(50, 50, 550, 750), color=(0.5, 0.5, 0.5))
        doc.save(pdf_path)

    atomic_write_index(
        pf / "indexes" / "formal-library.json",
        {
            "version": 1,
            "items": [
                {
                    "zotero_key": "SCAN01",
                    "title": "Scan Only",
                    "domain": "Ortho",
                    "has_pdf": True,
                    "ocr_status": "pending",
                    "pdf_path": "storage:SC1/scan.pdf",
                    "paper_root": "Resources/Literature/Ortho/SCAN01 - Scan Only/",
                }
            ],
        },
    )

    # Without page_hint -> clear actionable error
    with pytest.raises(ValueError, match="no extractable text layer"):
        ground_target_in_pdf(vault, "SCAN01", pdf_path, quote="Some sentence from scanned page")

    # With page_hint -> honest margin_fallback on that page
    res = agent_apply_annotations(
        vault,
        "SCAN01",
        [
            {
                "quote": "Some sentence from scanned page",
                "comment": "Important scanned finding verified manually on page 2.",
                "page_hint": 2,
            }
        ],
        lens="skeleton",
    )
    assert res["created_count"] == 1
    assert res["created"][0]["page"] == 2
    assert res["created"][0]["kind"] == "margin"
    assert res["created"][0]["grounding_tier"] == "margin_fallback"
    _assert_rects_in_unit_bounds(res["created"][0]["rects"])


def test_align_folded_quote_prevents_fuzzy_span_bloat() -> None:
    import pymupdf

    # Build a synthetic 900-char paragraph where "that" appears at offset 0 and "with" at offset 850,
    # while the target 52-char quote (with 1 minor OCR char diff) sits around offset 400.
    prefix = "that " + ("alpha beta gamma delta epsilon zeta eta theta iota kappa " * 7)
    target_in_pdf = "biomechanical stiffness increased markedly after repair"
    suffix = (" lambda mu nu xi omicron pi rho sigma tau upsilon phi chi" * 8) + " with"
    full_text = prefix + target_in_pdf + suffix

    pdf_chars = [
        (c.lower() if c.isalnum() else "", pymupdf.Rect(10 + i, 100, 11 + i, 112), c)
        for i, c in enumerate(full_text)
    ]

    # Quote with a 2-char OCR mismatch ("markdely" instead of "markedly")
    q_norm = "biomechanicalstiffnessincreasedmarkdelyafterrepair"
    hit, score = _align_folded_quote(
        pdf_chars,
        q_norm,
        require_unique=False,
        min_fuzzy_score=0.72,
    )
    assert hit is not None
    assert score >= 0.85
    # Span length MUST stay tight around q_norm (no stretching to "that" at 0 or "with" at end!)
    assert len(hit) <= max(int(len(q_norm) * 1.45), len(q_norm) + 25)
    recovered = "".join(c[2] for c in hit)
    assert "biomechanical" in recovered
    assert not recovered.startswith("that")
    assert not recovered.endswith("with")

    # Purely scattered 4-char noise across a huge span must be rejected, not bloated
    noise_hit, _ = _align_folded_quote(
        pdf_chars,
        "thatzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzwith",
        require_unique=False,
        min_fuzzy_score=0.5,
    )
    assert noise_hit is None


def test_nonzero_page_rect_origin_cropbox_alignment() -> None:
    import pymupdf
    from paperforge.services.pdf_grounding import _norm_rect_for_pdfjs

    class OffsetCropPage:
        rect = pymupdf.Rect(50, 60, 550, 740)
        rotation = 0

    # A box at (100, 120, 300, 140) in PDF space on a [50, 60, 550, 740] CropBox
    norm = _norm_rect_for_pdfjs(pymupdf.Rect(100, 120, 300, 140), OffsetCropPage())
    assert norm == [0.1, 0.0882, 0.5, 0.1176]


def test_batch_performance_single_open_sha_and_single_seq_bump(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pymupdf

    vault, _pdf = _build_realistic_multicolumn_pdf_vault(tmp_path, key="PERF001", with_ocr=False)

    bump_calls: list[tuple[str, str]] = []
    orig_bump = annotations_service._bump_seq_safe
    monkeypatch.setattr(
        annotations_service,
        "_bump_seq_safe",
        lambda v, reason, k: (bump_calls.append((reason, k)), orig_bump(v, reason, k))[1],
    )

    sha_calls: list[Path] = []
    orig_sha = annotations_service._sha256_file
    monkeypatch.setattr(
        annotations_service,
        "_sha256_file",
        lambda p: (sha_calls.append(p), orig_sha(p))[1],
    )

    open_calls: list[str] = []
    orig_open = pymupdf.open

    def tracked_open(*args, **kwargs):
        open_calls.append(str(args[0]) if args else "")
        return orig_open(*args, **kwargs)

    monkeypatch.setattr(pymupdf, "open", tracked_open)

    # Batch with multiple lenses, figure_id, and a rejected paraphrase
    items = [
        {
            "quote": "electrostimulation at 50 Hz ± 5 uM accelerated tendon healing.",
            "comment": "Establishes electrical frequency and micromolar baseline for the model.",
            "lens": "skeleton",
        },
        {
            "quote": "confirmed that baseline tear size predicted retear at 24 months.",
            "comment": "Cross-column multivariate predictor linking baseline lesion to failure.",
            "lens": "methods",
        },
        {
            "quote": "biomechanical stiffness reached 412 N/mm.",
            "comment": "CropBox page primary mechanical endpoint measurement.",
            "lens": "critique",
        },
        {
            "quote": "cyclic creep plateaued after 1000 loading cycles.",
            "comment": "Rotated landscape outcome demonstrating fatigue stabilization.",
            "lens": "custom",
        },
        {
            "figure_id": "figure_001",
            "comment": "Survival separation requires verifying censoring assumptions at 24 months.",
            "lens": "skeleton",
        },
        {
            "figure_id": "table_001",
            "comment": "Check group balance on age and tear width in Table 1.",
            "lens": "methods",
        },
    ]

    res = agent_apply_annotations(vault, "PERF001", items, lens="skeleton")
    assert res["created_count"] == 6
    assert len(bump_calls) == 1, f"Expected exactly 1 _bump_seq_safe per batch, got {bump_calls}"
    assert bump_calls[0] == ("annotations.agent_apply", "PERF001")
    assert len(sha_calls) == 1, f"Expected 1 SHA-256 computation per batch, got {len(sha_calls)}"
    assert len(open_calls) == 1, f"Expected 1 pymupdf.open per batch, got {len(open_calls)}"

    for rec in res["created"]:
        _assert_rects_in_unit_bounds(rec["rects"])
        if rec["kind"] == "area":
            assert rec["crop_asset_rel"].endswith(".jpg")
            assert (vault / rec["crop_asset_rel"]).is_file()

    # Empty/all-rejected batch with replace_lens=True must trigger 0 seq bumps & preserve prior marks
    bump_calls.clear()
    bad_res = agent_apply_annotations(
        vault,
        "PERF001",
        [{"quote": "nonexistent ghost sentence xyz", "comment": "Should fail grounding cleanly."}],
        lens="skeleton",
        replace_lens=True,
    )
    assert bad_res["created_count"] == 0
    assert bad_res["replaced_count"] == 0
    assert len(bump_calls) == 0

    # replace_lens=True with valid replacement replaces only skeleton marks in 1 bump
    bump_calls.clear()
    repl = agent_apply_annotations(
        vault,
        "PERF001",
        [
            {
                "quote": "Subgroup analysis showed stable effects across all centers.",
                "comment": "Replaces earlier skeleton marks with multi-center generalizability check.",
            }
        ],
        lens="skeleton",
        replace_lens=True,
    )
    assert repl["replaced_count"] == 2  # the 2 skeleton items from first batch
    assert repl["created_count"] == 1
    assert len(bump_calls) == 1

    # Adopt one agent annotation & clear remaining agent marks
    target_id = repl["created"][0]["ann_id"]
    adopted = adopt_agent_annotation(vault, "PERF001", target_id)
    assert adopted["author"] == "user"

    user_ann = add_annotation(
        vault,
        "PERF001",
        page=1,
        rects=[[0.1, 0.2, 0.3, 0.23]],
        kind="highlight",
        comment="User manual highlight",
    )

    cleared = clear_agent_annotations(vault, "PERF001")
    assert cleared["deleted_count"] == 4  # 2 methods + 1 critique + 1 custom
    remaining_ids = {a["ann_id"] for a in list_annotations(vault, "PERF001")}
    assert remaining_ids == {target_id, user_ann["ann_id"]}

    # agent_mark_annotation also works directly without OCR
    single = agent_mark_annotation(
        vault,
        "PERF001",
        quote="Figure 1. Kaplan-Meier survival curve stratified by graft diameter.",
        comment="Single-item agent mark works cleanly without OCR.",
        lens="custom",
    )
    assert single["author"] == "agent"
    _assert_rects_in_unit_bounds(single["rects"])
