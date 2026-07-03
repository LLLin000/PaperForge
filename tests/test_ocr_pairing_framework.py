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
