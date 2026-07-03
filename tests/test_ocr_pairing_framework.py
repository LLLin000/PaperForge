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


# ── Task 4: Pairing framework runner ──


def test_run_pairing_passes_executes_in_declared_order():
    from paperforge.worker.ocr_pairing_framework import run_pairing_passes
    from paperforge.worker.ocr_pairing_state import FigurePipelineState, OwnershipLedger
    from paperforge.worker.ocr_pairing_types import PassReport

    seen = []

    class FirstPass:
        name = "first"
        def run(self, state):
            seen.append(self.name)
            return PassReport(pass_name=self.name)

    class SecondPass:
        name = "second"
        def run(self, state):
            seen.append(self.name)
            return PassReport(pass_name=self.name)

    state = FigurePipelineState(corpus=None, candidate_index=None, ledger=OwnershipLedger())
    reports = run_pairing_passes(state, [FirstPass, SecondPass])

    assert seen == ["first", "second"]
    assert [r.pass_name for r in reports] == ["first", "second"]


# ── Task 5: Figure domain module ──


def test_figure_domain_module_exports_corpus_and_candidate_index():
    from paperforge.worker.ocr_figure_domain import FigureCandidateIndex, FigureCorpus

    assert FigureCorpus.__name__ == "FigureCorpus"
    assert FigureCandidateIndex.__name__ == "FigureCandidateIndex"


def test_legacy_vnext_corpus_module_reexports_figure_domain_types():
    from paperforge.worker.ocr_figure_domain import FigureCorpus as DomainFigureCorpus
    from paperforge.worker.ocr_figure_vnext_corpus import FigureCorpus as LegacyModuleFigureCorpus

    assert LegacyModuleFigureCorpus is DomainFigureCorpus

def test_resource_ref_supports_text_kind_and_role() -> None:
    from paperforge.worker.ocr_pairing_types import ResourceRef

    ref = ResourceRef(kind="text", page=5, block_id="note1", role="note")

    assert ref.kind == "text"
    assert ref.role == "note"


def test_claim_proposal_exposes_entity_no_alias_and_texts() -> None:
    from paperforge.worker.ocr_pairing_types import ClaimProposal, ResourceRef

    proposal = ClaimProposal(
        pass_name="p",
        figure_no=3,
        claim_type="attach_text",
        legends=[ResourceRef(kind="legend", page=5, block_id="cap1")],
        assets=[],
        groups=[],
        texts=[ResourceRef(kind="text", page=5, block_id="note1", role="note")],
        confidence=0.8,
        evidence_rank=1,
        reason="test",
    )

    assert proposal.entity_no == 3
    assert proposal.texts[0].block_id == "note1"


def test_ownership_ledger_journals_text_attachments() -> None:
    from paperforge.worker.ocr_pairing_state import OwnershipLedger
    from paperforge.worker.ocr_pairing_types import ResourceRef

    ledger = OwnershipLedger()
    owner = ResourceRef(kind="legend", page=5, block_id="cap1", figure_no=5)
    texts = [ResourceRef(kind="text", page=5, block_id="note1", role="note")]

    ledger.journal_text_attachment(texts, owner=owner, reason="table-notes")

    assert ledger.text_attachments_for(owner) == texts


def test_pipeline_state_alias_preserves_figure_state_compatibility() -> None:
    from paperforge.worker.ocr_pairing_state import FigurePipelineState, OwnershipLedger, PipelineState

    state = PipelineState(corpus=None, candidate_index=None, ledger=OwnershipLedger())

    assert FigurePipelineState is PipelineState
    assert state.matches == []
    assert state.reservations == []
