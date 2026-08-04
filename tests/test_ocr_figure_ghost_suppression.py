"""#122: ghost matched-figure suppression at inventory emission.

Rules under test (narrow, owner-approved):
  1. within a figure_number group, if ANY entry owns assets, 0-asset
     entries are suppressed (dominated ghost) — figure_number may be
     inferred from the entry's caption text;
  2. a 0-asset entry whose legend block caption resolves to a different
     figure number than its explicit figure_number is suppressed;
  3. entries owning assets are never suppressed (cross-page continuation
     safety);
  4. a lone 0-asset entry (no same-numbered asset owner) is kept.
"""

from pathlib import Path

import pytest

from paperforge.worker.ocr_figures import _suppress_ghost_matched_figures


def _match(
    number=None,
    page=None,
    assets=(),
    legend=None,
    text="",
):
    m = {"figure_number": number, "page": page, "asset_block_ids": list(assets)}
    if legend is not None:
        m["legend_block_id"] = legend
    if text:
        m["text"] = text
    return m


class TestGhostSuppressionRules:
    def test_dominated_zero_asset_ghost_suppressed(self):
        matched = [
            _match(number=4, page=41, assets=("a", "b", "c", "d", "e", "f", "g"), legend="13", text="Fig. 4. Real"),
            _match(number=4, page=40, assets=(), legend="1", text="Fig. 4. Ghost"),
        ]
        kept, suppressed = _suppress_ghost_matched_figures(matched, [])
        assert kept == [matched[0]]
        assert suppressed == [matched[1]]

    def test_inferred_number_ghost_suppressed(self):
        # figure_number=None but the caption text reads "Fig. 4." — the
        # entry is still a dominated ghost when figure 4 owns assets
        # (DWQQK2YB's exact shape).
        matched = [
            _match(number=4, page=41, assets=("x1",), legend="13", text="Fig. 4. Effect of LF-EMF"),
            _match(number=None, page=40, assets=(), legend="1", text="Fig. 4. Effect of LF-EMF"),
        ]
        kept, suppressed = _suppress_ghost_matched_figures(matched, [])
        assert kept == [matched[0]]
        assert suppressed == [matched[1]]

    def test_cross_page_continuation_both_kept(self):
        # Same figure number, BOTH entries own assets — never pick a
        # winner, both survive (figure 2 continuation contract).
        matched = [
            _match(number=2, page=38, assets=("p38a", "p38b"), legend="31", text="Fig. 2. A"),
            _match(number=2, page=39, assets=("p39a",), legend="3", text="Fig. 2. A (cont.)"),
        ]
        kept, suppressed = _suppress_ghost_matched_figures(matched, [])
        assert len(kept) == 2
        assert suppressed == []

    def test_lone_legend_only_kept(self):
        # A single 0-asset entry with no same-numbered asset owner is a
        # legend-only figure, not a ghost.
        matched = [_match(number=7, page=12, assets=(), legend="5", text="Fig. 7. Caption only.")]
        kept, suppressed = _suppress_ghost_matched_figures(matched, [])
        assert kept == matched
        assert suppressed == []

    def test_marker_mismatch_suppressed(self):
        # Explicit figure_number=4 but the legend block's caption text is
        # the Figure 3 caption — identity mismatch (DWQQK2YB ghost: its
        # legend block on p40 is the Fig. 3 caption).
        blocks = [
            {"page": 40, "block_id": "1", "text": "Fig. 3. Magnetic actuation characterization."},
        ]
        matched = [
            _match(number=4, page=40, assets=(), legend="1", text="Fig. 4. Effect of LF-EMF"),
        ]
        kept, suppressed = _suppress_ghost_matched_figures(matched, blocks)
        assert kept == []
        assert suppressed == [matched[0]]

    def test_asset_owner_never_suppressed_even_with_mismatch(self):
        # Rule 2 only applies to 0-asset entries — asset-owning entries
        # carry crop evidence and are trusted.
        blocks = [
            {"page": 40, "block_id": "1", "text": "Fig. 3. Magnetic actuation characterization."},
        ]
        matched = [
            _match(number=4, page=40, assets=("a1",), legend="1", text="Fig. 4. Effect of LF-EMF"),
        ]
        kept, suppressed = _suppress_ghost_matched_figures(matched, blocks)
        assert kept == matched
        assert suppressed == []


@pytest.mark.integration
def test_dwqqk2yb_figure4_ghost_suppressed_in_full_pipeline(tmp_path: Path) -> None:
    """DWQQK2YB regression: Figure 4 keeps only the p41/7-asset entry;
    the p40 0-asset ghost (and its Figure 3 caption block) is gone from
    both the strict inventory and the reader payload."""
    from tests.test_ocr_real_paper_regressions import replay_production_pipeline

    result = replay_production_pipeline("DWQQK2YB", tmp_path)
    inventory = result["figure_inventory"]
    matched = inventory.get("matched_figures", [])

    fig4 = [f for f in matched if f.get("figure_number") == 4 or "Fig. 4" in str(f.get("text", ""))]
    assert len(fig4) == 1, f"Figure 4 should have exactly one entry, got {fig4}"
    assert fig4[0].get("page") == 41, f"Figure 4 must be on page 41, got {fig4[0].get('page')}"
    assert len(fig4[0].get("asset_block_ids") or []) == 7

    reader = result["reader_payload"]
    reader_fig4 = [f for f in reader.get("reader_figures", []) if f.get("figure_number") == 4]
    assert len(reader_fig4) == 1, f"Reader should materialize Figure 4 once, got {len(reader_fig4)}"
    vg = reader_fig4[0].get("visual_groups", [])
    assert vg and vg[0].get("asset_block_ids"), "Figure 4 reader entry must own assets"
