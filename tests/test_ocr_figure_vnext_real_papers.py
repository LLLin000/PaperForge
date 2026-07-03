from pathlib import Path

from scripts.dev.compare_figure_inventory_legacy_vs_vnext import compare_blocks_file


def test_real_paper_same_page_milestone_reports_diff_shape():
    blocks_path = Path("tests/fixtures/ocr_vnext_real_papers/2HEUD5P9/blocks.structured.jsonl")
    diff = compare_blocks_file(blocks_path)

    assert diff["paper"] == "2HEUD5P9"
    assert "legacy_matched_count" in diff
    assert "vnext_matched_count" in diff
    assert "legacy_consumed_block_ids" in diff
    assert "vnext_consumed_block_ids" in diff
