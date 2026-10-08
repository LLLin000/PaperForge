"""Regenerate the TSTONE001 e2e OCR fixture's derived artifacts.

The fixture ships legacy-shaped ``json/result.json`` (``{pages:[{page_num,
markdown}]}``) with EMPTY ``canonical/blocks.raw.jsonl`` and
``structure/blocks.structured.jsonl``, so the memory unit builder yields zero
chunks and every vector-dependent e2e case (C03/E03/E04) is blocked.

This script synthesizes a modern provider payload from the fixture's own page
text, runs the real postprocess against a scratch vault, and mirrors the
regenerated artifacts back into both fixture trees.  Run it with the published
runtime interpreter (or any environment where ``paperforge`` is importable):

    <runtime>/Scripts/python.exe scripts/regen-ocr-fixture.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "tests" / "sandbox" / "ocr-complete" / "TSTONE001"
# Only the tracked fixture source is written: the e2e vault is a build
# artifact of paperforge/plugin/test/fixtures/build_e2e_vault.py, which
# injects the paper identity (title/venue) from the library export — mirroring
# this directory over it would drop that identity.  Run the builder after
# this script to refresh the vault.
TARGETS = (SRC,)


def synth_payload(legacy: dict) -> list[dict]:
    """One layoutParsingResults payload per legacy page, blocks from the text.

    Bounding boxes are distributed INSIDE the page: the role inference runs
    zone heuristics against the page box, and blocks pushed past the page
    bottom (the first version stacked 120px each) fall out of every zone and
    never receive a body role — leaving the unit builder with zero units.
    """
    pages: list[dict] = []
    for page in legacy.get("pages", []):
        text = str(page.get("markdown", "") or "")
        paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
        height = 1584
        top, bottom = 100, height - 100
        span = max(1, len(paragraphs) - 1)
        row = max(40, (bottom - top) // max(1, len(paragraphs)))
        blocks = []
        for index, paragraph in enumerate(paragraphs):
            y = top + (span and index * (bottom - top) // span)
            is_heading = paragraph.lstrip().startswith("#")
            blocks.append(
                {
                    "block_label": "paragraph_title" if is_heading else "text",
                    "block_content": paragraph.lstrip("# ").strip()
                    if is_heading
                    else paragraph,
                    "block_bbox": [100, y, 1100, min(height - 20, y + row)],
                    "block_id": index,
                    "block_order": index,
                    "group_id": 0,
                }
            )
        # Figures/tables come from the legacy result's own records; the
        # downstream figure pipeline derives its maps from figure/table
        # labelled blocks, so the smoke contract needs them present.
        page_num = int(page.get("page_num", 0) or 0)
        for kind, records in (
            ("figure", legacy.get("figures", [])),
            ("table", legacy.get("tables", [])),
        ):
            for record in records:
                if int(record.get("page", 0) or 0) != page_num:
                    continue
                index = len(blocks)
                y = top + min(bottom - top - 40, index * row)
                blocks.append(
                    {
                        "block_label": kind,
                        "block_content": str(record.get("caption", "") or ""),
                        "block_bbox": [100, y, 1100, min(height - 20, y + row)],
                        "block_id": index,
                        "block_order": index,
                        "group_id": 0,
                    }
                )
        pages.append(
            {
                "layoutParsingResults": [
                    {
                        "prunedResult": {
                            "width": 1224,
                            "height": 1584,
                            "parsing_res_list": blocks,
                        }
                    }
                ]
            }
        )
    return pages


def main() -> int:
    legacy = json.loads((SRC / "json" / "result.json").read_text(encoding="utf-8"))
    if isinstance(legacy, list):
        print("fixture result.json is already the modern list; nothing to do")
        return 0

    # The postprocess rewrites the paper directory and drops/empties the
    # handcrafted figure/table artifacts the other tests rely on (smoke:
    # "should have figures").  Snapshot them and restore after the run.
    preserved_names = (
        "json/result.json",
        "fulltext.md",
        "figure-map.json",
        "chart-type-map.json",
        "structure/figure_inventory.json",
        "structure/table_inventory.json",
        "structure/reader_figures.json",
    )
    preserved = {
        name: (SRC / name).read_bytes()
        for name in preserved_names
        if (SRC / name).exists()
    }

    all_results = synth_payload(legacy)
    scratch = Path(tempfile.mkdtemp(prefix="pf-fixture-"))
    vault = scratch / "vault"
    ocr_dir = vault / "System" / "PaperForge" / "ocr" / "TSTONE001"
    shutil.copytree(SRC, ocr_dir, dirs_exist_ok=True)
    (vault / "paperforge.json").write_text(
        json.dumps({"schema_version": 2, "vault_config": {}}), encoding="utf-8"
    )

    # Provenance is fail-closed: without the SOURCE PDF the fingerprint
    # cannot be verified and the lineage reports provenance_unknown, which
    # blocks embed eligibility.  Place the PDF at the canonical locator and
    # point meta.source_pdf at it before the postprocess.
    pdf_dir = vault / "System" / "Zotero" / "storage" / "TSTONE001"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        REPO / "tests" / "sandbox" / "TestZoteroData" / "storage" / "TSTONE001" / "TSTONE001.pdf",
        pdf_dir / "TSTONE001.pdf",
    )

    from paperforge.worker.ocr import postprocess_ocr_result

    meta = json.loads((ocr_dir / "meta.json").read_text(encoding="utf-8"))
    # Identity fields the pipeline does not own: keep them verbatim so the
    # workspace rows and search keep the paper's real title/venue.  The
    # authoritative source is the library index (the OCR meta may already
    # have lost them in an earlier regeneration).
    identity_fields = (
        "title",
        "year",
        "journal",
        "doi",
        "authors",
        "first_author",
        "authors_source",
    )
    identity = {key: meta[key] for key in identity_fields if key in meta}
    index_path = (
        REPO
        / "paperforge"
        / "plugin"
        / "test"
        / "vaults"
        / "e2e"
        / "System"
        / "PaperForge"
        / "indexes"
        / "formal-library.json"
    )
    if index_path.exists():
        try:
            library = json.loads(index_path.read_text(encoding="utf-8"))
            for item in library.get("items", []):
                if item.get("zotero_key") == "TSTONE001":
                    for key in identity_fields:
                        if item.get(key):
                            identity[key] = item[key]
                    break
        except (TypeError, ValueError):
            pass
    meta["source_pdf"] = "System/Zotero/storage/TSTONE001/TSTONE001.pdf"
    postprocess_ocr_result(vault, "TSTONE001", all_results, meta=meta)
    meta.update(identity)
    (ocr_dir / "meta.json").write_text(
        json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    for name, data in preserved.items():
        target = ocr_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    raw_lines = [
        line
        for line in (ocr_dir / "canonical" / "blocks.raw.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    structured_lines = [
        line
        for line in (ocr_dir / "structure" / "blocks.structured.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    print(f"regenerated: raw={len(raw_lines)} structured={len(structured_lines)}")
    if not raw_lines or not structured_lines:
        print("regeneration produced empty blocks; aborting")
        return 1

    for target in TARGETS:
        shutil.copytree(ocr_dir, target, dirs_exist_ok=True)
        print(f"mirrored -> {target}")

    # Sanity: the memory unit builder must now yield units (the postprocess
    # writes a sectioned tree from the heading labels).
    from paperforge.memory.builder import build_body_units

    tree = json.loads((SRC / "index" / "structure-tree.json").read_text(encoding="utf-8"))
    blocks = [
        json.loads(line)
        for line in (SRC / "structure" / "blocks.structured.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    print(f"body_units={len(units)}")
    return 0 if units else 1


if __name__ == "__main__":
    sys.exit(main())
