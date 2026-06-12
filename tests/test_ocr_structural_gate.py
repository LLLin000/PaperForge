from __future__ import annotations


def test_required_seed_without_verifier_holds_not_accepts() -> None:
    from paperforge.worker.ocr_structural_gate import RoleGateContext, resolve_verified_role

    block = {"block_id": "a1", "seed_role": "authors", "text": "Author One Author Two"}

    decision = resolve_verified_role(block, RoleGateContext())

    assert decision.role == "unknown_structural"
    assert decision.status == "HOLD"
    assert decision.seed_role == "authors"
    assert decision.source == "structural_gate"


def test_non_required_seed_can_accept_as_non_structural() -> None:
    from paperforge.worker.ocr_structural_gate import RoleGateContext, resolve_verified_role

    block = {"block_id": "b1", "seed_role": "body_paragraph", "text": "Regular body paragraph."}

    decision = resolve_verified_role(block, RoleGateContext())

    assert decision.role == "body_paragraph"
    assert decision.status == "ACCEPT"
    assert decision.source == "non_structural_seed"


def test_hold_preserves_candidate_and_hides_from_render_by_default() -> None:
    from paperforge.worker.ocr_structural_gate import RoleGateContext, resolve_verified_role

    block = {"block_id": "r1", "seed_role": "reference_item", "text": "[1] Not actually in references."}

    decision = resolve_verified_role(block, RoleGateContext())
    fields = decision.as_block_fields()

    assert fields["role"] == "unknown_structural"
    assert fields["role_candidate"] == "reference_item"
    assert fields["role_verification_status"] == "HOLD"
    assert fields["render_default"] is False


def test_gate_preserves_pre_normalized_non_structural_role() -> None:
    from paperforge.worker.ocr_structural_gate import RoleGateContext, resolve_verified_role

    block = {"block_id": "i1", "role": "structured_insert", "seed_role": "body_paragraph", "text": "Side note."}

    decision = resolve_verified_role(block, RoleGateContext())

    assert decision.role == "structured_insert"
    assert decision.seed_role == "body_paragraph"
    assert decision.source == "non_structural_normalized_role"


def test_gate_preserves_pre_normalized_safe_role_even_if_seed_is_required() -> None:
    from paperforge.worker.ocr_structural_gate import RoleGateContext, resolve_verified_role

    block = {
        "block_id": "x",
        "role": "frontmatter_noise",
        "seed_role": "authors",
        "text": "Author-like sidebar",
    }

    decision = resolve_verified_role(block, RoleGateContext())

    assert decision.role == "frontmatter_noise"
    assert decision.source == "non_structural_normalized_role"


def test_document_abstract_span_includes_structured_subheadings_and_excludes_support() -> None:
    from paperforge.worker.ocr_structural_gate import build_document_abstract_span

    blocks = [
        {"block_id": "h", "seed_role": "abstract_heading", "text": "Abstract"},
        {"block_id": "q", "seed_role": "section_heading", "text": "Questions/purposes"},
        {"block_id": "a1", "seed_role": "abstract_body", "text": "First abstract sentence."},
        {"block_id": "authors", "seed_role": "authors", "text": "Author One Author Two"},
        {"block_id": "m", "seed_role": "section_heading", "text": "Methods"},
        {"block_id": "a2", "seed_role": "body_paragraph", "text": "Second abstract sentence."},
        {"block_id": "intro", "seed_role": "section_heading", "text": "Introduction"},
        {"block_id": "bad", "seed_role": "abstract_body", "text": "Mislabeled body."},
    ]
    context = {
        "body_start_block_id": "intro",
        "frontmatter_main_zone_ids": {"h", "q", "a1", "m", "a2"},
        "frontmatter_support_zone_ids": {"authors"},
        "publisher_sidebar_zone_ids": set(),
        "correspondence_zone_ids": set(),
        "affiliation_zone_ids": set(),
    }

    span = build_document_abstract_span(blocks, context)

    assert span["status"] == "ACCEPT"
    assert span["heading_block_id"] == "h"
    assert span["body_block_ids"] == ["q", "a1", "m", "a2"]
    assert span["excluded_support_block_ids"] == ["authors"]
    assert span["stop_reason"] == "body_start"


def test_abstract_span_stops_before_intro_even_when_later_block_has_abstract_seed() -> None:
    from paperforge.worker.ocr_structural_gate import build_document_abstract_span

    blocks = [
        {"block_id": "h", "seed_role": "abstract_heading", "text": "Abstract"},
        {"block_id": "a", "seed_role": "abstract_body", "text": "Actual abstract."},
        {"block_id": "intro", "seed_role": "section_heading", "text": "Introduction"},
        {"block_id": "bad", "seed_role": "abstract_body", "text": "Mislabeled body result."},
    ]
    span = build_document_abstract_span(blocks, {"body_start_block_id": "intro"})

    assert span["body_block_ids"] == ["a"]
    assert span["stop_reason"] == "body_start"


def test_abstract_span_stops_at_intro_like_heading_without_body_start_id() -> None:
    from paperforge.worker.ocr_structural_gate import build_document_abstract_span

    blocks = [
        {"block_id": "h", "seed_role": "abstract_heading", "text": "Abstract"},
        {"block_id": "a", "seed_role": "abstract_body", "text": "Actual abstract."},
        {"block_id": "intro", "seed_role": "section_heading", "text": "1. Introduction"},
        {"block_id": "bad", "seed_role": "abstract_body", "text": "Mislabeled body result."},
    ]
    span = build_document_abstract_span(blocks, {})

    assert span["body_block_ids"] == ["a"]
    assert span["stop_reason"] == "intro_like_heading"


def test_reference_zone_adapter_excludes_tail_after_boundary() -> None:
    from paperforge.worker.ocr_structural_gate import build_verified_reference_zone_from_artifacts

    blocks = [
        {"block_id": "body", "seed_role": "reference_item", "text": "[1] body parameter"},
        {"block_id": "refs", "seed_role": "reference_heading", "text": "References"},
        {"block_id": "r1", "seed_role": "reference_item", "text": "[1] Smith J. 2020."},
        {"block_id": "bio", "seed_role": "section_heading", "text": "Biography"},
        {"block_id": "bad", "seed_role": "reference_item", "text": "Biography text mislabeled."},
    ]
    artifacts = {
        "reference_family_anchor": {"heading_block_id": "refs", "item_block_ids": ["r1", "bad"]},
        "region_bus": {"reference_zone_ids": {"refs", "r1"}},
        "tail_spread": {"reference_end_before_block_id": "bio"},
        "reference_numbering_family": {"accepted_item_ids": {"r1"}},
    }

    zone = build_verified_reference_zone_from_artifacts(blocks, artifacts)

    assert zone["status"] == "ACCEPT"
    assert zone["heading_block_id"] == "refs"
    assert zone["item_block_ids"] == ["r1"]


def test_reference_zone_adapter_keeps_multicolumn_reference_items_inside_region() -> None:
    from paperforge.worker.ocr_structural_gate import build_verified_reference_zone_from_artifacts

    blocks = [
        {"block_id": "refs", "seed_role": "reference_heading", "text": "References", "column": 1},
        {"block_id": "r1", "seed_role": "reference_item", "text": "[1] Left column reference.", "column": 1},
        {"block_id": "r2", "seed_role": "reference_item", "text": "[2] Right column reference.", "column": 2},
        {"block_id": "appendix", "seed_role": "section_heading", "text": "Appendix", "column": 1},
    ]
    artifacts = {
        "reference_family_anchor": {"heading_block_id": "refs", "item_block_ids": ["r1", "r2"]},
        "region_bus": {"reference_zone_ids": {"refs", "r1", "r2"}},
        "tail_spread": {"reference_end_before_block_id": "appendix"},
        "reference_numbering_family": {"accepted_item_ids": {"r1", "r2"}},
    }

    zone = build_verified_reference_zone_from_artifacts(blocks, artifacts)

    assert zone["status"] == "ACCEPT"
    assert zone["item_block_ids"] == ["r1", "r2"]


def test_reference_zone_adapter_accepts_without_tail_end_boundary_when_region_is_present() -> None:
    from paperforge.worker.ocr_structural_gate import build_verified_reference_zone_from_artifacts

    blocks = [
        {"block_id": "refs", "seed_role": "reference_heading", "text": "References"},
        {"block_id": "r1", "seed_role": "reference_item", "text": "[1] Smith J. 2020."},
    ]
    artifacts = {
        "reference_family_anchor": {"heading_block_id": "refs", "item_block_ids": ["r1"]},
        "region_bus": {"reference_zone_ids": {"refs", "r1"}},
        "tail_spread": {},
    }

    zone = build_verified_reference_zone_from_artifacts(blocks, artifacts)

    assert zone["status"] == "ACCEPT"
    assert zone["item_block_ids"] == ["r1"]


def test_reference_zone_accepts_heading_when_region_ids_are_plain_block_ids() -> None:
    from paperforge.worker.ocr_structural_gate import build_verified_reference_zone_from_artifacts

    blocks = [
        {"page": 13, "block_id": 10, "text": "References", "seed_role": "reference_heading"},
        {"page": 13, "block_id": 11, "text": "[1] Ref item", "seed_role": "reference_item"},
    ]
    zone = build_verified_reference_zone_from_artifacts(
        blocks,
        {
            "reference_family_anchor": {},
            "region_bus": {"reference_zone_ids": {10, 11}},
            "tail_spread": {},
        },
    )

    assert zone["status"] == "ACCEPT"
    assert zone["heading_block_id"] == 10
    assert zone["item_block_ids"] == [11]


def test_reference_zone_accepts_heading_when_region_ids_are_page_prefixed() -> None:
    from paperforge.worker.ocr_structural_gate import build_verified_reference_zone_from_artifacts

    blocks = [
        {"page": 13, "block_id": 10, "text": "References", "seed_role": "reference_heading"},
        {"page": 13, "block_id": 11, "text": "[1] Ref item", "seed_role": "reference_item"},
    ]
    zone = build_verified_reference_zone_from_artifacts(
        blocks,
        {
            "reference_family_anchor": {},
            "region_bus": {"reference_zone_ids": {"p13:10", "p13:11"}},
            "tail_spread": {},
        },
    )

    assert zone["status"] == "ACCEPT"
    assert zone["heading_block_id"] == 10
    assert zone["item_block_ids"] == [11]
