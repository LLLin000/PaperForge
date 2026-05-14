from __future__ import annotations

import json


PAPER_COLUMNS = [
    "zotero_key", "citation_key", "title", "year", "doi", "pmid",
    "journal", "first_author", "authors_json", "abstract", "domain",
    "collection_path", "collections_json",
    "has_pdf", "do_ocr", "analyze", "ocr_status", "deep_reading_status",
    "ocr_job_id", "impact_factor",
    "lifecycle", "maturity_level", "maturity_name", "next_step",
    "pdf_path", "note_path", "main_note_path", "paper_root",
    "fulltext_path", "ocr_md_path", "ocr_json_path", "ai_path",
    "deep_reading_md_path", "updated_at",
]


def build_paper_row(entry: dict, generated_at: str) -> dict:
    row = {}
    for col in PAPER_COLUMNS:
        if col == "authors_json":
            row[col] = json.dumps(entry.get("authors", []), ensure_ascii=False)
        elif col == "collections_json":
            row[col] = json.dumps(entry.get("collections", []), ensure_ascii=False)
        elif col == "lifecycle":
            row[col] = entry.get("lifecycle", "")
        elif col == "maturity_level":
            row[col] = entry.get("maturity", {}).get("level", 1)
        elif col == "maturity_name":
            row[col] = entry.get("maturity", {}).get("level_name", "")
        elif col == "next_step":
            row[col] = entry.get("next_step", "")
        elif col == "updated_at":
            row[col] = generated_at
        elif col in ("do_ocr", "analyze"):
            val = entry.get(col)
            row[col] = 1 if val else 0
        elif col == "has_pdf":
            row[col] = 1 if entry.get("has_pdf") else 0
        else:
            row[col] = entry.get(col, "")
    return row
