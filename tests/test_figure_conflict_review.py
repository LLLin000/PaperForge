from types import SimpleNamespace

from scripts.dev.figure_conflict_review import build_review_records
from scripts.dev.figure_evidence_graph import build_graph


def block(block_id, role, x, y, text="", page=1):
    return {"block_id": block_id, "page": page, "bbox": [x, y, x + 20, y + 10], "role": role,
            "text": text, "page_width": 100, "page_height": 100}


def view(blocks, figures=None, tables=None):
    return SimpleNamespace(key="SYNTH", blocks=blocks, figure_inventory=figures or {}, table_inventory=tables or {})


def test_two_candidates_offer_keep_and_switch():
    source = view([block("cap", "figure_caption", 10, 10, "Figure 1"),
                   block("a1", "figure_asset", 10, 24), block("a2", "figure_asset", 40, 24)],
                  {"matched_figures": [{"figure_id": "fig1", "legend_block_id": "cap", "page": 1,
                                        "matched_assets": [{"block_id": "a1", "page": 1}], "match_pass": "local"}]})
    records = build_review_records(source, build_graph(source))
    record = next(r for r in records if r["caption"]["id"] == "cap")
    assert {a["decision"] for a in record["alternatives"]} >= {"keep", "switch_asset"}
    assert any(a["target_asset_ids"] == ["a2"] for a in record["alternatives"] if a["decision"] == "switch_asset")


def test_assetless_table_offers_attach_asset():
    source = view([block("cap", "table_caption", 10, 10, "Table 1"),
                   block("tab", "table_asset", 10, 24)],
                  tables={"tables": [{"table_id": "t1", "caption_block_id": "cap", "page": 1,
                                      "has_asset": False, "match_status": "UNMATCHED"}]})
    records = build_review_records(source, build_graph(source))
    record = next(r for r in records if r["caption"]["id"] == "cap")
    assert any(a["decision"] == "attach_table_asset" and a["target_asset_ids"] == ["tab"]
               for a in record["alternatives"])


def test_duplicate_identity_is_undetermined_and_records_are_deterministic():
    source = view([block("cap", "figure_caption", 10, 10, "Figure 1"),
                   block("cap", "figure_caption", 50, 10, "Figure 2"), block("asset", "figure_asset", 10, 24)])
    graph = build_graph(source)
    first = build_review_records(source, graph)
    second = build_review_records(source, graph)
    assert first == second
    assert any(r["current"]["match_status"] == "UNDETERMINED" for r in first)
    assert all(r["status"] == "UNREVIEWED" for r in first)


def test_switch_candidates_stay_on_the_caption_page():
    source = view([block("cap", "figure_caption", 10, 10, "Figure 1"),
                   block("far", "figure_asset", 10, 24, page=2)],
                  {"matched_figures": [{"figure_id": "f1", "legend_block_id": "cap", "page": 1,
                                        "matched_assets": []}]})
    records = build_review_records(source, build_graph(source))
    record = next(r for r in records if r["caption"]["id"] == "cap")
    assert not any(r["decision"] == "switch_asset" and r["target_asset_ids"] == ["far"]
                   for r in record["alternatives"])


def test_table_with_figure_asset_offers_role_matched_switch():
    source = view([block("cap", "table_caption", 10, 10, "Table 1"),
                   block("fig", "figure_asset", 10, 40),
                   block("tab", "table_html", 10, 70)],
                  tables={"tables": [{"table_id": "t1", "caption_block_id": "cap", "page": 1,
                                      "has_asset": True, "asset_block_id": "fig", "match_status": "matched"}]})
    records = build_review_records(source, build_graph(source))
    record = next(r for r in records if r["caption"]["id"] == "cap")
    switches = [a for a in record["alternatives"]
                if a["decision"] == "switch_asset" and a["target_asset_ids"] == ["tab"]]
    assert switches and switches[0]["confidence"] == "medium"
