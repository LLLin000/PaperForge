"""Tests for author biography detection."""

from paperforge.worker.ocr_bio import (
    _add_block_keys,
    _bio_text_score,
    _has_formal_figure_number,
    _is_portrait_like,
    _is_protected_strong_figure,
    _is_strongly_figure_matched,
    _looks_like_reference,
    _nearby_blocks,
    _resolve_ref_start_page,
    post_ref_bio_cleanup,
    prune_figure_inventory_after_bio,
    residual_author_bio_pass,
)

# --- _bio_text_score tests ---

def test_bio_text_score_professor():
    """Full career-position bio should score >= 4 with >= 2 categories."""
    text = (
        "Marco P. Soares dos Santos is assistant professor at the "
        "Department of Mechanical Engineering of the University of Aveiro, "
        "Portugal. His research interests include biomedical devices."
    )
    score, cats = _bio_text_score(text)
    assert score >= 4, f"score={score}"
    assert len(cats) >= 2, f"categories={cats}"


def test_bio_text_score_phd_student():
    """PhD-student bio should score >= 4."""
    text = (
        "José G. S. Figueiredo is a Ph.D. student of Rehabilitation Sciences "
        "at Institute of Biomedicine (iBiMED), Department of Medical Sciences, "
        "University of Aveiro."
    )
    score, cats = _bio_text_score(text)
    assert score >= 4, f"score={score}"


def test_bio_text_score_received_phd():
    """Received PhD + institution should score >= 4."""
    text = (
        "Rongrong Zhu obtained her Ph.D. at Tongji University, China, in 2007. "
        "She went on postdoctoral research at Stony Brook University."
    )
    score, cats = _bio_text_score(text)
    assert score >= 4, f"score={score}"


def test_bio_text_score_postdoc():
    """Postdoc with research interests."""
    text = (
        "Yuxin Bai is now a postdoctoral fellow at the Department of "
        "Biomedical Engineering, City University of Hong Kong. Her research "
        "focus is on nanomaterials for bone regeneration."
    )
    score, cats = _bio_text_score(text)
    assert score >= 4, f"score={score}"


def test_bio_text_score_reference_false_positive():
    """Standard reference must score 0."""
    text = (
        "[1] H. Wang, S. Zhang, J. Lv, Y. Cheng, "
        "View 2021, 2, 20200026."
    )
    score, _ = _bio_text_score(text)
    assert score == 0, f"score={score}"


def test_bio_text_score_figure_caption():
    """Figure caption without bio content must score 0."""
    text = (
        "Figure 1. Characterization of HAP scaffolds. "
        "(A) SEM image showing porous structure. (B) XRD pattern."
    )
    score, _ = _bio_text_score(text)
    assert score == 0, f"score={score}"


def test_bio_text_score_too_short():
    """Text under 5 words must score 0."""
    assert _bio_text_score("Hello world") == (0, set())


def test_bio_text_score_too_long():
    """Text over 80 words must score 0."""
    long = "word " * 81
    assert _bio_text_score(long) == (0, set())


def test_bio_text_score_phd_abbreviation():
    """MD/PhD standalone abbreviation alone must not trigger bio (score 0-1)."""
    text = "PhD, MD, MSc"
    score, cats = _bio_text_score(text)
    assert score == 0, f"score={score}"


# --- _is_portrait_like tests ---

def test_is_portrait_like_square_image():
    """Small square image is portrait-like."""
    block = {"bbox": [100, 100, 250, 250], "raw_label": "image"}
    assert _is_portrait_like(block)


def test_is_portrait_like_chart():
    """Chart is NOT portrait-like."""
    block = {"bbox": [100, 100, 250, 250], "raw_label": "chart"}
    assert not _is_portrait_like(block)


def test_is_portrait_like_too_wide():
    """Full-width image is NOT portrait-like."""
    block = {"bbox": [50, 100, 1150, 500], "raw_label": "image"}
    assert not _is_portrait_like(block)


# --- _has_formal_figure_number tests ---

def test_has_formal_figure_number_fig():
    assert _has_formal_figure_number("Fig. 1. Cell proliferation.")
    assert _has_formal_figure_number("Figure 2. Western blot analysis.")
    assert _has_formal_figure_number("Supplementary Fig. S1. Additional data.")
    assert _has_formal_figure_number("Table 1. Primer sequences.")
    assert _has_formal_figure_number("Extended Data Fig. 1. Clinical data.")


def test_has_formal_figure_number_bio_text():
    """Bio text must NOT match formal figure number."""
    assert not _has_formal_figure_number(
        "Marco Soares dos Santos is assistant professor at DAU."
    )


# --- _looks_like_reference tests ---

def test_looks_like_reference_true():
    assert _looks_like_reference("[1] H. Wang, S. Zhang, View 2021, 2, 20200026.")
    assert _looks_like_reference("[10] Author AB, et al. Journal 2020;10:100.")


def test_looks_like_reference_false():
    assert not _looks_like_reference(
        "Marco Soares dos Santos is assistant professor at UA."
    )


# --- _nearby_blocks tests ---

def test_nearby_blocks_finds_adjacent():
    blocks = [
        {"page": 1, "block_id": "a1", "bbox": [0, 0, 100, 50], "text": ""},
        {"page": 1, "block_id": "a2", "bbox": [0, 60, 100, 110], "text": ""},
    ]
    nearby = _nearby_blocks(blocks, blocks[0], max_distance=100, same_page=True)
    assert any(b["block_id"] == "a2" for b in nearby)


def test_nearby_blocks_exclude():
    blocks = [
        {"page": 1, "block_id": "a1", "bbox": [0, 0, 100, 50], "text": ""},
        {"page": 1, "block_id": "a2", "bbox": [0, 60, 100, 110], "text": ""},
    ]
    nearby = _nearby_blocks(
        blocks, blocks[0], max_distance=100, same_page=True,
        exclude_block_ids={"a2"},
    )
    assert not any(b["block_id"] == "a2" for b in nearby)


# --- _resolve_ref_start_page tests ---

def test_resolve_ref_start_page():
    blocks = [
        {"page": 1, "role": "body_paragraph", "zone": "body_zone"},
        {"page": 21, "role": "reference_heading", "zone": "reference_zone"},
        {"page": 22, "role": "reference_item", "zone": "reference_zone"},
    ]
    assert _resolve_ref_start_page(blocks) == 21


def test_resolve_ref_start_page_no_refs():
    blocks = [
        {"page": 1, "role": "body_paragraph", "zone": "body_zone"},
    ]
    assert _resolve_ref_start_page(blocks) is None


# --- _add_block_keys tests ---

def test_add_block_keys():
    keys: set[tuple[int, str]] = set()
    _add_block_keys(keys, {"page": 3, "block_id": "b5"})
    assert (3, "b5") in keys


# --- Strong/weak figure match tests ---

def test_is_strongly_figure_matched_true():
    fig_inv = {
        "matched_figures": [{
            "figure_number": 1,
            "legend_page": 5,
            "legend_block_id": "leg_1",
            "settlement_type": "same_page",
            "confidence": 0.9,
            "matched_assets": [{"page": 5, "block_id": "ast_1"}],
        }]
    }
    assert _is_strongly_figure_matched((5, "leg_1"), fig_inv)
    assert _is_strongly_figure_matched((5, "ast_1"), fig_inv)


def test_is_strongly_figure_matched_false():
    fig_inv = {"matched_figures": [], "ambiguous_figures": [], "held_figures": []}
    assert not _is_strongly_figure_matched((1, "unknown"), fig_inv)


def test_is_protected_strong_figure_numbered():
    fig = {"figure_number": 2, "confidence": 0.8}
    assert _is_protected_strong_figure(fig)


def test_is_protected_strong_figure_unconfirmed():
    fig = {"figure_number": None, "confidence": 0.3}
    assert not _is_protected_strong_figure(fig)


# --- post_ref_bio_cleanup tests ---

def test_post_ref_bio_cleanup_reference_item():
    """4AG67PBH-like b8: reference_item in reference_zone with bio text."""
    blocks = [
        {
            "page": 25, "block_id": "b8", "zone": "reference_zone",
            "role": "reference_item", "render_default": True,
            "text": (
                "Marco P. Soares dos Santos is assistant professor at the "
                "Department of Mechanical Engineering of the University of Aveiro."
            ),
        },
    ]
    fig_inv = {"matched_figures": [], "ambiguous_figures": [], "held_figures": []}
    post_ref_bio_cleanup(fig_inv, blocks, ref_start_page=21)
    assert blocks[0]["role"] == "backmatter_body"
    assert blocks[0].get("_object_owner_family") == "author_bio"


def test_post_ref_bio_cleanup_skips_reference():
    """Real reference must not be touched."""
    blocks = [
        {
            "page": 22, "block_id": "r1", "zone": "reference_zone",
            "role": "reference_item",
            "text": "[1] H. Wang, S. Zhang, View 2021, 2, 20200026.",
        },
    ]
    fig_inv = {"matched_figures": [], "ambiguous_figures": [], "held_figures": []}
    post_ref_bio_cleanup(fig_inv, blocks, ref_start_page=21)
    assert blocks[0]["role"] == "reference_item"


def test_post_ref_bio_cleanup_skips_early_page():
    """Blocks before ref_start_page must not be touched."""
    blocks = [
        {
            "page": 5, "block_id": "b1", "zone": "body_zone",
            "role": "body_paragraph",
            "text": (
                "Marco Soares dos Santos is assistant professor at DAU."
            ),
        },
    ]
    fig_inv = {"matched_figures": [], "ambiguous_figures": [], "held_figures": []}
    post_ref_bio_cleanup(fig_inv, blocks, ref_start_page=21)
    assert blocks[0]["role"] == "body_paragraph"


def test_post_ref_bio_cleanup_skips_figure_matched():
    """Block consumed by strong figure must not be touched."""
    blocks = [
        {
            "page": 22, "block_id": "leg_1", "zone": "reference_zone",
            "role": "reference_item",
            "text": (
                "Marco Soares dos Santos is assistant professor at DAU."
            ),
        },
    ]
    fig_inv = {
        "matched_figures": [{
            "figure_number": 1, "legend_page": 22,
            "legend_block_id": "leg_1", "settlement_type": "same_page",
            "confidence": 0.9, "matched_assets": [],
        }],
        "ambiguous_figures": [],
        "held_figures": [],
    }
    post_ref_bio_cleanup(fig_inv, blocks, ref_start_page=21)
    assert blocks[0]["role"] == "reference_item"  # unchanged


# --- prune_figure_inventory_after_bio tests ---

def test_prune_figure_inventory_after_bio():
    """Prune removes ambiguous_figures entries matching bio artifacts."""
    fig_inv = {
        "matched_figures": [],
        "ambiguous_figures": [
            {"page": 25, "legend_page": 25, "legend_block_id": "amb_1"},
            {"page": 10, "legend_page": 10, "legend_block_id": "amb_2"},
        ],
        "held_figures": [],
        "_pruned_author_bio_artifacts": [
            {"source": "test", "page": 25, "block_id": "amb_1"},
        ],
    }
    prune_figure_inventory_after_bio(fig_inv)
    remaining_ids = [
        a.get("legend_block_id") for a in fig_inv["ambiguous_figures"]
    ]
    assert "amb_1" not in remaining_ids
    assert "amb_2" in remaining_ids


# --- residual_author_bio_pass tests ---

def test_residual_bio_detects_portrait_asset_with_bio_text():
    """Portrait unmatched_asset with nearby bio text -> moved to bio."""
    blocks = [
        {"page": 1, "block_id": "portrait", "role": "media_asset",
         "bbox": [100, 100, 200, 250], "raw_label": "image", "text": ""},
        {"page": 1, "block_id": "bio_text", "role": "body_paragraph",
         "bbox": [100, 300, 400, 350],
         "text": "Dr. Smith is a professor at the University of Tokyo. His research interests include AI."},
    ]
    fig_inv = {
        "unmatched_assets": [dict(blocks[0])],
        "unresolved_clusters": [],
        "matched_figures": [],
        "ambiguous_figures": [],
        "held_figures": [],
    }
    residual_author_bio_pass(fig_inv, blocks)
    assert len(fig_inv["unmatched_assets"]) == 0
    assert len(fig_inv["_pruned_author_bio_artifacts"]) == 1
    assert blocks[0].get("_object_owner_family") == "author_bio"
    assert blocks[0].get("role") == "author_bio_asset"


def test_residual_bio_skips_non_portrait_asset():
    """Non-portrait asset (chart) must NOT be moved."""
    blocks = [
        {"page": 1, "block_id": "chart", "role": "media_asset",
         "bbox": [100, 100, 600, 250], "raw_label": "chart", "text": ""},
    ]
    fig_inv = {
        "unmatched_assets": [dict(blocks[0])],
        "unresolved_clusters": [],
        "matched_figures": [],
        "ambiguous_figures": [],
        "held_figures": [],
    }
    residual_author_bio_pass(fig_inv, blocks)
    assert len(fig_inv["unmatched_assets"]) == 1
    assert len(fig_inv.get("_pruned_author_bio_artifacts", [])) == 0


def test_residual_bio_detects_portrait_cluster_with_bio_text():
    """Portrait unresolved_cluster with nearby bio text -> moved to bio."""
    blocks = [
        {"page": 1, "block_id": "portrait1", "role": "media_asset",
         "bbox": [100, 100, 200, 250], "raw_label": "image", "text": ""},
        {"page": 1, "block_id": "bio_text", "role": "body_paragraph",
         "bbox": [100, 300, 400, 350],
         "text": "Dr. Smith is a professor at the University of Tokyo. His research interests include AI."},
    ]
    fig_inv = {
        "unmatched_assets": [],
        "unresolved_clusters": [{
            "page": 1, "key": "cluster_1",
            "media_block_ids": ["portrait1"],
            "cluster_bbox": [100, 100, 200, 250],
        }],
        "matched_figures": [],
        "ambiguous_figures": [],
        "held_figures": [],
    }
    residual_author_bio_pass(fig_inv, blocks)
    assert len(fig_inv["unresolved_clusters"]) == 0
    assert len(fig_inv["_pruned_author_bio_artifacts"]) == 1


def test_residual_bio_skips_cluster_without_bio_text():
    """Cluster without bio text nearby must NOT be moved."""
    blocks = [
        {"page": 1, "block_id": "portrait1", "role": "media_asset",
         "bbox": [100, 100, 200, 250], "raw_label": "image", "text": ""},
        {"page": 1, "block_id": "ref_text", "role": "reference_item",
         "bbox": [100, 300, 400, 350],
         "text": "[1] Smith et al. Journal 2020;10:100."},
    ]
    fig_inv = {
        "unmatched_assets": [],
        "unresolved_clusters": [{
            "page": 1, "key": "cluster_1",
            "media_block_ids": ["portrait1"],
            "cluster_bbox": [100, 100, 200, 250],
        }],
        "matched_figures": [],
        "ambiguous_figures": [],
        "held_figures": [],
    }
    residual_author_bio_pass(fig_inv, blocks)
    assert len(fig_inv["unresolved_clusters"]) == 1


def test_residual_bio_ambiguous_figures_not_touched():
    """ambiguous_figures must NOT be touched in P1 (gated)."""
    fig_inv = {
        "unmatched_assets": [],
        "unresolved_clusters": [],
        "ambiguous_figures": [{"legend_block_id": "amb_1", "page": 1}],
        "matched_figures": [],
        "held_figures": [],
    }
    residual_author_bio_pass(fig_inv, [])
    assert len(fig_inv["ambiguous_figures"]) == 1


# --- post_ref_bio_cleanup P1: figure_caption support ---

def test_post_ref_bio_cleanup_figure_caption():
    """figure_caption in post-ref with bio text -> backmatter_body."""
    blocks = [
        {
            "page": 25, "block_id": "b4", "zone": "reference_zone",
            "role": "figure_caption", "render_default": True,
            "text": (
                "Marco P. Soares dos Santos is assistant professor at the "
                "Department of Mechanical Engineering of the University of Aveiro."
            ),
        },
    ]
    fig_inv = {"matched_figures": [], "ambiguous_figures": [], "held_figures": []}
    post_ref_bio_cleanup(fig_inv, blocks, ref_start_page=21)
    assert blocks[0]["role"] == "backmatter_body"
    assert blocks[0].get("_object_owner_family") == "author_bio"


def test_post_ref_bio_cleanup_skips_formal_figure_caption():
    """formal figure_caption (Fig. 1. ...) must NOT be touched."""
    blocks = [
        {
            "page": 25, "block_id": "b4", "zone": "reference_zone",
            "role": "figure_caption",
            "text": "Fig. 1. Cell proliferation assay. (A) Control group. (B) Treatment group.",
        },
    ]
    fig_inv = {"matched_figures": [], "ambiguous_figures": [], "held_figures": []}
    post_ref_bio_cleanup(fig_inv, blocks, ref_start_page=21)
    assert blocks[0]["role"] == "figure_caption"  # unchanged