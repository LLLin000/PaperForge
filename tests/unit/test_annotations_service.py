"""Unit tests for Commit 2B: non-destructive sidecar PDF annotations, OCR binding, and DB persistence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from paperforge.cli import main as cli_main
from paperforge.memory.builder import build_for_keys
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.permanent import read_all_reading_notes
from paperforge.services.annotations_service import (
    add_annotation,
    delete_annotation,
    get_paper_pdf_context,
    list_annotations,
    promote_to_reading_log,
    update_annotation,
)
from tests.conftest import canonical_test_config


def _setup_annotated_paper_vault(tmp_path: Path, *, key: str = "ANNKEY01"):
    import pymupdf

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")

    pf = vault / ".paperforge"
    ws = vault / "Resources" / "Literature" / "Ortho" / f"{key} - Sample ACL Study"
    ws.mkdir(parents=True)
    (ws / f"{key}.md").write_text("---\ntitle: Sample ACL Study\n---\n", encoding="utf-8")

    zot_storage = pf / "Zotero" / "storage" / "AT01"
    zot_storage.mkdir(parents=True)
    pdf_path = zot_storage / "study.pdf"
    with pymupdf.open() as doc:
        p1 = doc.new_page(width=600, height=800)
        p1.insert_text((72, 120), "ACL graft tunnel widening was lower in group A.")
        p1.draw_rect(pymupdf.Rect(60, 300, 500, 600), color=(0, 0, 1), fill=(0.9, 0.9, 1.0))
        doc.save(pdf_path)

    idx_path = pf / "indexes" / "formal-library.json"
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx_path.write_text(
        json.dumps(
            {
                "version": 1,
                "items": [
                    {
                        "zotero_key": key,
                        "citation_key": "lin2026acl",
                        "domain": "Ortho",
                        "title": "Sample ACL Study",
                        "authors": ["Lin"],
                        "first_author": "Lin",
                        "year": "2026",
                        "journal": "AJSM",
                        "has_pdf": True,
                        "pdf_path": "storage:AT01/study.pdf",
                        "paper_root": f"Resources/Literature/Ortho/{key} - Sample ACL Study/",
                        "main_note_path": f"Resources/Literature/Ortho/{key} - Sample ACL Study/{key}.md",
                        "note_path": f"Resources/Literature/Ortho/{key} - Sample ACL Study/{key}.md",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    # Seed V3 OCR artifacts for spatial binding
    ocr_dir = pf / "ocr" / key
    (ocr_dir / "structure").mkdir(parents=True)
    (ocr_dir / "index").mkdir(parents=True)
    blocks = [
        {
            "block_id": "blk_p1_001",
            "page": 1,
            "page_width": 600,
            "page_height": 800,
            "bbox": [60, 80, 540, 180],
            "role": "body_paragraph",
            "text": "ACL graft tunnel widening was lower in group A.",
        },
        {
            "block_id": "blk_p1_fig1",
            "page": 1,
            "page_width": 600,
            "page_height": 800,
            "bbox": [60, 300, 500, 600],
            "role": "figure_image",
            "text": "",
        },
    ]
    (ocr_dir / "structure" / "blocks.structured.jsonl").write_text(
        "\n".join(json.dumps(b) for b in blocks) + "\n",
        encoding="utf-8",
    )
    (ocr_dir / "index" / "structure-tree.json").write_text(
        json.dumps(
            {
                "paper_id": key,
                "nodes": [
                    {
                        "node_id": "sec:results",
                        "title": "Results",
                        "level": 1,
                        "own_block_ids": [],
                        "subtree_block_ids": ["blk_p1_001", "blk_p1_fig1"],
                        "children": [
                            {
                                "node_id": "sec:subgroup",
                                "title": "Tunnel Widening",
                                "level": 2,
                                "own_block_ids": ["blk_p1_001", "blk_p1_fig1"],
                                "subtree_block_ids": ["blk_p1_001", "blk_p1_fig1"],
                                "children": [],
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (ocr_dir / "structure" / "figure_inventory.json").write_text(
        json.dumps(
            {
                "matched_figures": [
                    {
                        "figure_id": "figure_001",
                        "page": 1,
                        "cluster_bbox": [60, 300, 500, 600],
                        "associated_text_block_ids": ["blk_p1_fig1"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return vault, ws, pdf_path


def test_annotations_lifecycle_area_crop_ocr_binding_and_pdf_immutability(
    tmp_path: Path,
) -> None:
    vault, ws, pdf_path = _setup_annotated_paper_vault(tmp_path)
    original_sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()

    ctx = get_paper_pdf_context(vault, "ANNKEY01")
    assert ctx["page_count"] == 1
    assert ctx["pdf_sha256"] == original_sha

    # 1. Text highlight -> binds V3 block_id + section_path
    h = add_annotation(
        vault,
        "ANNKEY01",
        page=1,
        rects=[[0.15, 0.12, 0.70, 0.18]],
        kind="highlight",
        color="yellow",
        intent="evidence",
        exact_text="ACL graft tunnel widening was lower in group A.",
        comment="Primary outcome evidence",
    )
    assert h["block_id"] == "blk_p1_001"
    assert h["section_path"] == "Results > Tunnel Widening"
    assert h["provenance_status"] == "verified"

    # 2. Area crop -> saves JPG asset inside <workspace>/assets/ + binds figure_id
    a = add_annotation(
        vault,
        "ANNKEY01",
        page=1,
        rects=[[0.12, 0.40, 0.80, 0.72]],
        kind="area",
        color="blue",
        intent="question",
        comment="Check error bar definition",
    )
    assert a["figure_id"] == "figure_001"
    assert a["crop_asset_rel"].endswith(".jpg")
    assert (vault / a["crop_asset_rel"]).exists()
    assert a["embed_wikilink"].startswith("![[ANNKEY01_ann_")

    # Source PDF bytes MUST remain byte-identical!
    assert hashlib.sha256(pdf_path.read_bytes()).hexdigest() == original_sha

    # 3. Update & Delete
    upd = update_annotation(vault, "ANNKEY01", h["ann_id"], intent="quote", comment="Updated")
    assert upd["intent"] == "quote"
    assert upd["comment"] == "Updated"
    assert len(list_annotations(vault, "ANNKEY01")) == 2

    # 4. Promote to reading-log.jsonl
    promoted = promote_to_reading_log(vault, "ANNKEY01", h["ann_id"], usage="primary_outcome", project="ACLReview")
    assert promoted["promoted"] is True
    notes = read_all_reading_notes(vault)
    assert len(notes) == 1
    assert notes[0]["paper_id"] == "ANNKEY01"
    assert notes[0]["project"] == "ACLReview"

    # 5. DB rebuild ingests annotations from workspace annotations.jsonl
    build_res = build_for_keys(vault)
    assert build_res["papers_indexed"] == 1
    conn = get_connection(get_memory_db_path(vault), read_only=True)
    try:
        rows = conn.execute("SELECT ann_id, intent, figure_id FROM paper_annotations ORDER BY page").fetchall()
        assert len(rows) == 2
        assert any(r["figure_id"] == "figure_001" for r in rows)
    finally:
        conn.close()

    # 6. Deleting an annotation removes it from list and live DB
    delete_annotation(vault, "ANNKEY01", a["ann_id"])
    remaining = list_annotations(vault, "ANNKEY01")
    assert len(remaining) == 1
    assert remaining[0]["ann_id"] == h["ann_id"]

    # 7. Mutating PDF flags provenance_status == "changed"
    pdf_path.write_bytes(pdf_path.read_bytes() + b"\n%modified")
    changed = list_annotations(vault, "ANNKEY01")
    assert changed[0]["provenance_status"] == "changed"


def test_annotations_cli_json_roundtrip(tmp_path: Path, capsys) -> None:
    vault, _, _ = _setup_annotated_paper_vault(tmp_path, key="CLIANN01")

    rc = cli_main(
        [
            "--vault",
            str(vault),
            "annotations",
            "add",
            "CLIANN01",
            "--page",
            "1",
            "--rects-json",
            "[[0.15, 0.12, 0.7, 0.18]]",
            "--intent",
            "method",
            "--exact-text",
            "Sample text",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    ann_id = payload["data"]["ann_id"]

    rc2 = cli_main(["--vault", str(vault), "annotations", "list", "CLIANN01", "--json"])
    assert rc2 == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["ok"] is True
    assert listed["data"]["annotations"][0]["ann_id"] == ann_id
