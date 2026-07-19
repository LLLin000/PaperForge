from __future__ import annotations

import json
from pathlib import Path


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "ocr_real_papers"
LEDGER_PATH = Path(__file__).resolve().parents[1] / "audit" / "coverage_ledger.json"


def _load_manifest() -> dict:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def test_gold_set_covers_readiness_layout_classes() -> None:
    manifest = _load_manifest()
    all_layouts = {tag for paper in manifest["papers"] for tag in paper.get("layout_tags", [])}
    assert "preproof_frontmatter" in all_layouts
    assert "same_page_ref_body_split" in all_layouts
    assert any(tag in all_layouts for tag in {"side_caption", "multi_panel"})
    assert "post_reference_biography" in all_layouts
    assert any(tag in all_layouts for tag in {"review_callout", "special_structure"})


def test_layout_class_manifest_has_named_representatives() -> None:
    manifest = _load_manifest()
    by_tag: dict[str, set[str]] = {}
    for paper in manifest["papers"]:
        for tag in paper.get("layout_tags", []):
            by_tag.setdefault(tag, set()).add(paper["paper_key"])

    assert by_tag["preproof_frontmatter"]
    assert by_tag["same_page_ref_body_split"]
    assert by_tag["post_reference_biography"]
    assert by_tag["review_callout"] or by_tag["special_structure"]


def test_every_audit_paper_has_at_least_one_layout_tag() -> None:
    manifest = _load_manifest()

    missing = [paper["paper_key"] for paper in manifest["papers"] if not paper.get("layout_tags")]

    assert missing == []
