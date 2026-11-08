"""Author biographies in the tail must not be reclassified as references."""

from __future__ import annotations

from paperforge.worker.ocr_bio import post_ref_bio_cleanup


def _block(bid, text, role, zone="reference_zone", page=2, seed_role=None):
    return {
        "page": page,
        "block_id": bid,
        "text": text,
        "role": role,
        "seed_role": seed_role or role,
        "zone": zone,
        "bbox": [0, 0, 100, 20],
    }


def _inventory():
    return {"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []}


BIO = (
    "Yuxin Bai is now a postdoctoral fellow in Professor Rongrong Zhu's group at Tongji University, "
    "School of Life Science and Technology. He obtained his Ph.D. degree from Tongji University in 2023."
)


def test_tail_prose_with_bio_signals_becomes_backmatter_body() -> None:
    blocks = [_block("b1", BIO, "reference_item", seed_role="footnote")]
    post_ref_bio_cleanup(_inventory(), blocks, ref_start_page=1)
    assert blocks[0]["role"] == "backmatter_body"
    assert blocks[0]["zone"] == ""
    assert blocks[0]["_object_owner_family"] == "author_bio"


def test_real_reference_item_is_untouched() -> None:
    reference = (
        "[12] A. Author, B. Author, C. Author, Bioactive materials for bone regeneration, "
        "Biomaterials 2023, 25, 445."
    )
    blocks = [_block("b2", reference, "reference_item")]
    post_ref_bio_cleanup(_inventory(), blocks, ref_start_page=1)
    assert blocks[0]["role"] == "reference_item"


def test_correspondence_address_is_untouched() -> None:
    address = "Address correspondence to:\nMichael S. Detamore, PhD\nUniversity of Kansas\nLawrence, KS"
    blocks = [_block("b3", address, "reference_item", seed_role="footnote")]
    post_ref_bio_cleanup(_inventory(), blocks, ref_start_page=1)
    assert blocks[0]["role"] == "reference_item"


def test_short_prose_without_bio_evidence_is_untouched() -> None:
    blocks = [_block("b4", "This work was supported by a grant.", "footnote")]
    post_ref_bio_cleanup(_inventory(), blocks, ref_start_page=1)
    assert blocks[0]["role"] == "footnote"
