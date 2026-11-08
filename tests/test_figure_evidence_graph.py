from types import SimpleNamespace

from scripts.dev.figure_evidence_graph import build_graph


def block(block_id, role, x, y, page=1, text=""):
    return {"block_id": block_id, "page": page, "bbox": [x, y, x + 20, y + 10], "role": role, "text": text,
            "page_width": 100, "page_height": 100}


def view(blocks, figures=None, tables=None):
    return SimpleNamespace(key="SYNTH", blocks=blocks, figure_inventory=figures or {}, table_inventory=tables or {})


def test_matched_pair_and_nearby_competing_asset():
    blocks = [block("cap", "figure_caption", 10, 10, text="Figure 1"),
              block("a1", "figure_asset", 10, 24), block("a2", "figure_asset", 40, 24)]
    inv = {"matched_figures": [{"figure_id": "fig1", "legend_block_id": "cap", "page": 1,
                                "matched_assets": [{"block_id": "a1", "page": 1}], "match_pass": "local", "score": 0.8}]}
    graph = build_graph(view(blocks, inv))
    assert any(e["relation"] == "group_asset" and e["status"] == "MATCHED" for e in graph["edges"])
    assert any(e["relation"] == "caption_asset" and e["target"].startswith("asset:1:a2:")
               and e["status"] == "CANDIDATE" for e in graph["edges"])


def test_two_groups_claiming_asset_report_conflict():
    blocks = [block("c1", "figure_caption", 10, 10), block("c2", "figure_caption", 50, 10),
              block("a", "figure_asset", 10, 25)]
    inv = {"matched_figures": [
        {"figure_id": "f1", "legend_block_id": "c1", "page": 1, "matched_assets": [{"block_id": "a", "page": 1}]},
        {"figure_id": "f2", "legend_block_id": "c2", "page": 1, "matched_assets": [{"block_id": "a", "page": 1}]},
    ]}
    graph = build_graph(view(blocks, inv))
    assert any(c["kind"] == "asset_multiple_groups" for c in graph["conflicts"])


def test_duplicate_block_identity_is_undetermined_not_linked():
    blocks = [block("cap", "figure_caption", 10, 10), block("cap", "figure_caption", 50, 10),
              block("asset", "figure_asset", 10, 25)]
    inv = {"matched_figures": [{"figure_id": "f", "legend_block_id": "cap", "page": 1,
                                "matched_assets": [{"block_id": "asset", "page": 1}]}]}
    graph = build_graph(view(blocks, inv))
    assert any(c["kind"] == "duplicate_identity" and c["status"] == "UNDETERMINED" for c in graph["conflicts"])
    assert not any(e["relation"] == "caption_group" for e in graph["edges"])
    assert any(e["relation"] == "caption_asset" and e["status"] == "UNDETERMINED" for e in graph["edges"])


def test_json_keys_are_stable():
    graph = build_graph(view([block("c", "table_caption", 1, 1), block("t", "table_asset", 1, 20)],
                             tables={"tables": [{"table_id": "t1", "caption_block_id": "c", "page": 1,
                                                 "asset_block_id": "t"}]}))
    assert list(graph) == ["key", "nodes", "edges", "conflicts"]
    assert all(list(node) == ["id", "type", "page", "block_id", "bbox", "role", "text"]
               for node in graph["nodes"] if node["type"] != "group")


def test_table_without_asset_is_hold_not_matched():
    blocks = [block("c", "table_caption", 1, 1), block("t", "table_asset", 1, 20)]
    inv = {"tables": [{"table_id": "t1", "caption_block_id": "c", "page": 1, "has_asset": False}]}
    graph = build_graph(view(blocks, tables=inv))
    caption_edges = [e for e in graph["edges"] if e["relation"] == "caption_group"]
    assert caption_edges and all(e["status"] == "HOLD" for e in caption_edges)
    assert caption_edges[0]["evidence"]["status_reason"] == "no_asset"
    assert not any(e["status"] == "MATCHED" and e["relation"] == "caption_group" for e in graph["edges"])


def test_spatial_candidates_are_marked_as_such():
    blocks = [block("cap", "figure_caption", 10, 10), block("a1", "figure_asset", 10, 24)]
    graph = build_graph(view(blocks, {"matched_figures": []}))
    candidates = [e for e in graph["edges"] if e["relation"] == "caption_asset"]
    assert candidates
    assert all(e["origin"] == "spatial" and e["proposed_by"] == "spatial_proximity" for e in candidates)
