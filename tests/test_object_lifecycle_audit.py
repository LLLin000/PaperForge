import json
from pathlib import Path

from scripts.dev.object_lifecycle_audit import audit_paper, main


def make_paper(root: Path, *, duplicate: bool = False, broken: bool = False,
               missing_delivery: bool = False, embedded_orphan: bool = False) -> Path:
    paper = root / "PAPER1"
    figures = [{"figure_id": "fig1", "figure_number": 1, "matched_assets": [{"block_id": "a"}],
                "consumed_block_ids": ["a"]}]
    if duplicate:
        figures.append({"figure_id": "fig1", "figure_number": 1, "matched_assets": []})
    table = {"table_id": "table1", "table_number": 1, "has_asset": True,
             "assistive_text": "<table></table>", "note_texts": ["note"], "continuation": True}
    (paper / "structure").mkdir(parents=True)
    (paper / "render/figures").mkdir(parents=True)
    (paper / "render/tables").mkdir(parents=True)
    (paper / "structure/figure_inventory.json").write_text(json.dumps({"matched_figures": figures}), encoding="utf-8")
    (paper / "structure/table_inventory.json").write_text(json.dumps({"tables": [table]}), encoding="utf-8")
    rows = [
        {"block_id": "a", "role": "figure_inner_text", "_object_owner_id": "fig1",
         "_object_consumed": True, "_post_match_role_override": "figure_asset"},
        {"block_id": "z", "_object_owner_id": "missing"},
    ]
    (paper / "structure/blocks.structured.jsonl").write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
    (paper / "render/figures/fig1.md").write_text("Figure", encoding="utf-8")
    if embedded_orphan:
        (paper / "render/figures/orphan_1.md").write_text("orphan", encoding="utf-8")
    (paper / "render/tables/table_001.md").write_text(
        "Table 1: caption\n\n![table](table1.jpg)\n\n## Notes\nnote", encoding="utf-8")
    embeds = [] if missing_delivery else ["![[render/figures/fig1.md]]"]
    if broken:
        embeds.append("![[render/figures/not-present.md]]")
    if embedded_orphan:
        embeds.append("![[render/figures/orphan_1.md]]")
    (paper / "render/fulltext.md").write_text("\n".join(embeds), encoding="utf-8")
    return paper


def test_audit_counts_lifecycle_metrics(tmp_path: Path) -> None:
    paper = make_paper(tmp_path)
    result = audit_paper(paper)
    assert result["identity"] == {
        "figures_total": 1, "unique_figure_ids": 1, "duplicate_id_extra": 0,
        "duplicate_id_papers": 0, "duplicate_id_paths": [], "figures_without_assets": 0,
        "figures_without_number": 0,
    }
    assert result["delivery"]["figure_md_count"] == 1
    assert result["delivery"]["canonical_figure_md_count"] == 1
    assert result["delivery"]["canonical_md_missing"] == []
    assert result["delivery"]["figure_embeds"] == 1
    assert result["delivery"]["unique_ids_not_embedded"] == []
    assert result["orphans"]["orphan_md_count"] == 0
    assert result["orphans"]["embedded_orphan_count"] == 0
    assert result["tables"] == {
        "tables_total": 1, "no_asset": 0, "with_html": 1, "with_notes": 1,
        "continuation": 1, "table_md_count": 1, "md_missing_caption": 0,
        "md_missing_image": 0, "tables_with_notes_missing_md_notes": 0,
        "table_embeds_in_fulltext": 0,
    }
    assert result["ownership"] == {
        "figure_inner_text_rows": 1, "owned_figure_inner_text_rows": 1,
        "rows_with_object_consumed": 1, "rows_owner_without_inventory_claim": 1,
        "rows_post_match_role_override": 1,
    }
    assert not any(result["violations"].values())


def test_clean_paper_has_no_failures(tmp_path: Path) -> None:
    paper = make_paper(tmp_path)
    assert main(["--ocr-root", str(tmp_path), "--keys", paper.name, "--fail-on",
                 "duplicate_identity,broken_embed,missing_delivery,orphan_embedded"]) == 0


def test_each_fail_on_invariant(tmp_path: Path) -> None:
    cases = {
        "duplicate_identity": {"duplicate": True},
        "broken_embed": {"broken": True},
        "missing_delivery": {"missing_delivery": True},
        "orphan_embedded": {"embedded_orphan": True},
    }
    for invariant, kwargs in cases.items():
        case_root = tmp_path / invariant
        case_root.mkdir()
        make_paper(case_root, **kwargs)
        assert main(["--ocr-root", str(case_root), "--fail-on", invariant]) == 1
        if invariant == "orphan_embedded":
            result = audit_paper(case_root / "PAPER1")
            assert result["orphans"]["embedded_orphan_count"] == 1
            assert result["orphan_embeds"] == [
                {"paper": "PAPER1", "text": "![[render/figures/orphan_1.md]]"}
            ]


def test_missing_artifacts_are_zero_and_corpus_is_deterministic(tmp_path: Path) -> None:
    empty = tmp_path / "EMPTY"
    empty.mkdir()
    assert audit_paper(empty)["identity"]["figures_total"] == 0
    one = make_paper(tmp_path)
    result = audit_paper(one)
    assert json.dumps(result, sort_keys=True) == json.dumps(audit_paper(one), sort_keys=True)
