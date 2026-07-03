from __future__ import annotations

from dataclasses import dataclass, field

from .ocr_pairing_types import ClaimProposal, OwnershipConflict, ResourceRef


class OwnershipLedger:
    def __init__(self) -> None:
        self._reserved_groups: set[ResourceRef] = set()
        self._owners: dict[ResourceRef, ResourceRef] = {}
        self._journal: list[dict[str, object]] = []

    def claim_assets(self, assets: list[ResourceRef], *, owner: ResourceRef, reason: str) -> None:
        conflict = self.try_claim_assets(assets, owner=owner, reason=reason)
        if conflict is not None:
            raise ValueError(f"asset already owned: {conflict.resource}")

    def try_claim_assets(
        self, assets: list[ResourceRef], *, owner: ResourceRef, reason: str
    ) -> OwnershipConflict | None:
        for asset in assets:
            current = self._owners.get(asset)
            if current is not None and current != owner:
                conflict = OwnershipConflict(
                    resource=asset,
                    current_owner=current,
                    attempted_owner=owner,
                    reason=reason,
                )
                self._journal.append({
                    "action": "conflict",
                    "resource": asset,
                    "current_owner": current,
                    "attempted_owner": owner,
                    "reason": reason,
                })
                return conflict
        for asset in assets:
            self._owners[asset] = owner
            self._journal.append({"action": "claim", "resource": asset, "owner": owner, "reason": reason})
        return None

    def owner_of(self, resource: ResourceRef) -> ResourceRef | None:
        return self._owners.get(resource)

    def owner_of_asset(self, *, page: int, block_id: int | str) -> ResourceRef | None:
        return self.owner_of(ResourceRef(kind="asset", page=page, block_id=block_id))

    def reserve_group(self, group: ResourceRef, *, reason: str) -> None:
        self._reserved_groups.add(group)
        self._journal.append({"action": "reserve_group", "resource": group, "reason": reason})

    def can_claim_group(self, group: ResourceRef) -> bool:
        return group not in self._reserved_groups

    def transition_reserved_group_to_claimed(
        self, group: ResourceRef, *, owner: ResourceRef, reason: str
    ) -> None:
        self._reserved_groups.discard(group)
        self._journal.append({
            "action": "transition_to_claimed",
            "resource": group,
            "owner": owner,
            "reason": reason,
        })

    def snapshot(self) -> list[dict[str, object]]:
        return list(self._journal)


@dataclass
class FigurePipelineState:
    corpus: object | None
    candidate_index: object | None
    ledger: OwnershipLedger
    matches: list[dict] = field(default_factory=list)
    unresolved: list[dict] = field(default_factory=list)
    hypotheses: list[dict] = field(default_factory=list)
    diagnostics: list[dict] = field(default_factory=list)
    reservations: list[dict] = field(default_factory=list)
    completeness: dict = field(default_factory=dict)

    def accept_match(self, proposal: ClaimProposal, match_record: dict) -> None:
        # Enrich match_record with rotation metadata if the legend has rotated text.
        self._enrich_rotation(proposal, match_record)
        self.matches.append(match_record)
        self.diagnostics.append({
            "event": "match_accepted",
            "pass_name": proposal.pass_name,
            "figure_no": proposal.figure_no,
            "reason": proposal.reason,
            "resources": {
                "legends": proposal.legends,
                "assets": proposal.assets,
                "groups": proposal.groups,
            },
        })

    def _enrich_rotation(self, proposal: ClaimProposal, match_record: dict) -> None:
        """Detect rotated caption and add rotation_correction_deg + cluster_bbox."""
        from .ocr_figures import _caption_has_rotated_text, _prepare_rotated_caption_normalization

        if not self.corpus or not proposal.legends:
            return
        legend_ref = proposal.legends[0]
        # Find the legend block in the corpus
        legend_block = None
        for b in self.corpus.blocks:
            if str(b.get("block_id", "")) == str(legend_ref.block_id) and b.get("page") == legend_ref.page:
                legend_block = b
                break
        if legend_block is None or not _caption_has_rotated_text(legend_block):
            return
        # Find the first asset block from the proposal
        if not proposal.assets or not self.corpus.raw_assets:
            return
        asset_ref = proposal.assets[0]
        asset_block = None
        for a in self.corpus.raw_assets:
            if str(a.get("block_id", "")) == str(asset_ref.block_id) and a.get("page") == asset_ref.page:
                asset_block = a
                break
        if asset_block is None:
            return
        normalized = _prepare_rotated_caption_normalization(legend_block, asset_block)
        if normalized is not None:
            match_record["rotation_correction_deg"] = normalized["rotation_correction_deg"]
            match_record["cluster_bbox"] = normalized["rotation_union_bbox"]

    def accept_reservation(self, proposal: ClaimProposal) -> None:
        self.reservations.append({
            "pass_name": proposal.pass_name,
            "figure_no": proposal.figure_no,
            "reason": proposal.reason,
            "legends": list(proposal.legends),
            "groups": list(proposal.groups),
        })
        self.diagnostics.append({
            "event": "reservation_accepted",
            "pass_name": proposal.pass_name,
            "figure_no": proposal.figure_no,
            "reason": proposal.reason,
            "resources": {"groups": proposal.groups},
        })
