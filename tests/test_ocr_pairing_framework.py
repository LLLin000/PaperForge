from __future__ import annotations

"""Baseline lock tests for the OCR pairing framework.

These tests lock the current vnext types/state module surface before extraction.
They verify the framework types are importable and constructable.
"""


def test_vnext_types_module_is_currently_generic_surface():
    from paperforge.worker.ocr_figure_vnext_types import ClaimProposal, PassReport, ResourceRef

    assert ResourceRef.__name__ == "ResourceRef"
    assert ClaimProposal.__name__ == "ClaimProposal"
    assert PassReport.__name__ == "PassReport"


def test_vnext_state_module_is_currently_generic_surface():
    from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger

    state = FigurePipelineState(corpus=None, candidate_index=None, ledger=OwnershipLedger())

    assert state.matches == []
    assert state.reservations == []
    assert state.unresolved == []


# ── Task 2: Generic pairing types extraction ──


def test_pairing_types_module_exports_generic_types():
    from paperforge.worker.ocr_pairing_types import ClaimProposal, PassReport, ResourceRef

    ref = ResourceRef(kind="legend", page=1, block_id="b1")
    proposal = ClaimProposal(
        pass_name="p",
        figure_no=1,
        claim_type="match",
        legends=[ref],
        assets=[],
        groups=[],
        confidence=0.9,
        evidence_rank=1,
        reason="test",
    )
    report = PassReport(pass_name="p")

    assert proposal.pass_name == "p"
    assert report.pass_name == "p"
    assert ref.page == 1


def test_figure_vnext_types_module_reexports_framework_types():
    from paperforge.worker.ocr_pairing_types import ResourceRef as FrameworkResourceRef
    from paperforge.worker.ocr_figure_vnext_types import ResourceRef as FigureModuleResourceRef

    assert FigureModuleResourceRef is FrameworkResourceRef


def test_resource_ref_rejects_page_agnostic_asset():
    import pytest

    from paperforge.worker.ocr_pairing_types import ResourceRef

    with pytest.raises(ValueError):
        ResourceRef(kind="asset", page=None, block_id="a1")


def test_resource_ref_normalizes_block_id_type():
    from paperforge.worker.ocr_pairing_types import ResourceRef

    assert ResourceRef(kind="asset", page=1, block_id=1) == ResourceRef(kind="asset", page=1, block_id="1")


def test_resource_ref_rejects_group_without_group_id():
    import pytest

    from paperforge.worker.ocr_pairing_types import ResourceRef

    with pytest.raises(ValueError):
        ResourceRef(kind="group", page=1, block_id=None)


# ── Task 3: Generic state and ledger extraction ──


def test_pairing_state_module_exports_ownership_ledger():
    from paperforge.worker.ocr_pairing_state import OwnershipLedger
    from paperforge.worker.ocr_pairing_types import ResourceRef

    ledger = OwnershipLedger()
    owner = ResourceRef(kind="legend", page=1, block_id="cap")
    asset = ResourceRef(kind="asset", page=1, block_id="asset")

    assert ledger.try_claim_assets([asset], owner=owner, reason="test") is None
    assert ledger.owner_of_asset(page=1, block_id="asset") == owner


def test_figure_vnext_state_module_reexports_framework_ledger():
    from paperforge.worker.ocr_pairing_state import OwnershipLedger as FrameworkLedger
    from paperforge.worker.ocr_figure_vnext_state import OwnershipLedger as FigureModuleLedger

    assert FigureModuleLedger is FrameworkLedger
