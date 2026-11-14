from __future__ import annotations

from collections.abc import Callable
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
                self._journal.append(
                    {
                        "action": "conflict",
                        "resource": asset,
                        "current_owner": current,
                        "attempted_owner": owner,
                        "reason": reason,
                    }
                )
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

    def release_group_reservation(self, group: ResourceRef, *, reason: str) -> None:
        if group not in self._reserved_groups:
            return
        self._reserved_groups.remove(group)
        self._journal.append(
            {"action": "release_group_reservation", "resource": group, "reason": reason}
        )

    def snapshot(self) -> list[dict[str, object]]:
        return list(self._journal)

    def journal_text_attachment(self, texts: list[ResourceRef], *, owner: ResourceRef, reason: str) -> None:
        for text in texts:
            self._journal.append(
                {
                    "action": "attach_text",
                    "resource": text,
                    "owner": owner,
                    "reason": reason,
                }
            )

    def text_attachments_for(self, owner: ResourceRef) -> list[ResourceRef]:
        return [
            entry["resource"]
            for entry in self._journal
            if entry.get("action") == "attach_text" and entry.get("owner") == owner
        ]


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
    holds: list[dict] = field(default_factory=list)
    completeness: dict = field(default_factory=dict)
    # Hook set by domain code (e.g., figures) to enrich match_records before storing.
    _match_pre_enricher: Callable | None = None

    def accept_match(self, proposal: ClaimProposal, match_record: dict) -> None:
        if self._match_pre_enricher is not None:
            self._match_pre_enricher(proposal, match_record, self)
        self.matches.append(match_record)
        self.diagnostics.append(
            {
                "event": "match_accepted",
                "pass_name": proposal.pass_name,
                "figure_no": proposal.figure_no,
                "reason": proposal.reason,
                "resources": {
                    "legends": proposal.legends,
                    "assets": proposal.assets,
                    "groups": proposal.groups,
                },
            }
        )

    def accept_reservation(self, proposal: ClaimProposal) -> None:
        self.reservations.append(
            {
                "pass_name": proposal.pass_name,
                "figure_no": proposal.figure_no,
                "reason": proposal.reason,
                "status": "RESERVED",
                "legends": [
                    {"page": legend.page, "block_id": legend.block_id}
                    for legend in proposal.legends
                ],
                "groups": [
                    {"page": group.page, "group_id": group.group_id}
                    for group in proposal.groups
                ],
                "diagnostics": dict(proposal.diagnostics),
            }
        )
        self.diagnostics.append(
            {
                "event": "reservation_accepted",
                "pass_name": proposal.pass_name,
                "figure_no": proposal.figure_no,
                "reason": proposal.reason,
                "resources": {"groups": proposal.groups},
            }
        )

    def hold_legend(self, hold: dict) -> None:
        page = hold.get("page", hold.get("legend_page"))
        legend_id = str(hold.get("legend_block_id", hold.get("block_id", "")))
        existing = next(
            (
                item
                for item in self.holds
                if item.get("page", item.get("legend_page")) == page
                and str(item.get("legend_block_id", item.get("block_id", ""))) == legend_id
            ),
            None,
        )
        if existing is None:
            recorded = dict(hold)
            recorded["association_status"] = "HOLD"
            reason = str(recorded.get("hold_reason") or "unresolved_association")
            recorded["hold_reason"] = reason
            recorded["hold_reasons"] = list(dict.fromkeys([*recorded.get("hold_reasons", []), reason]))
            self.holds.append(recorded)
            return

        existing["association_status"] = "HOLD"
        reasons = [*existing.get("hold_reasons", []), existing.get("hold_reason"), hold.get("hold_reason")]
        existing["hold_reasons"] = list(dict.fromkeys(str(reason) for reason in reasons if reason))
        existing.setdefault("hold_reason", hold.get("hold_reason") or "unresolved_association")
        if not existing.get("text") and hold.get("text"):
            existing["text"] = hold["text"]
        groups = {
            (group.get("page"), str(group.get("group_id", ""))): group
            for group in [*existing.get("candidate_groups", []), *hold.get("candidate_groups", [])]
        }
        existing["candidate_groups"] = list(groups.values())
        assets = {
            (asset.get("page"), str(asset.get("block_id", ""))): asset
            for group in existing["candidate_groups"]
            for asset in group.get("assets", [])
        }
        existing["candidate_assets"] = list(assets.values())
        existing["candidate_asset_ids"] = list(dict.fromkeys(
            asset.get("block_id") for asset in assets.values() if asset.get("block_id") is not None
        ))


PipelineState = FigurePipelineState
