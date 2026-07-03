from __future__ import annotations

from dataclasses import dataclass, field

from .ocr_figure_vnext_types import ClaimProposal, OwnershipConflict, ResourceRef


class OwnershipLedger:
    def __init__(self) -> None:
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

    def accept_match(self, proposal: ClaimProposal, match_record: dict) -> None:
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
