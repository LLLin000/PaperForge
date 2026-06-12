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
