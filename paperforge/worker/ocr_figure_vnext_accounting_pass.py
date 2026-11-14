from __future__ import annotations

import math

from .ocr_pairing_types import PassReport, ResourceRef


class FinalAccountingPass:
    """Post-processing pass that computes completeness accounting and checks invariants.

    Runs last in the vnext pipeline.  Inspects all numbered formal legends,
    classifies each as matched / unmatched / gap, populates ``state.completeness``,
    and emits invariant violations to ``report.invariant_errors``.
    """

    name = "final_accounting"

    def run(self, state):
        report = PassReport(pass_name=self.name)
        from . import ocr_figures

        # -- 1. Collect numbered formal legends --------------------------------
        numbered_legends: list[dict] = []
        for legend in state.candidate_index.deduped_legends:  # type: ignore[union-attr]
            text = str(legend.get("text", ""))
            fig_no = ocr_figures._extract_figure_number(text)
            if fig_no is not None:
                numbered_legends.append(legend)

        def _page(item):
            page = item.get("legend_page")
            if page is None:
                page = item.get("page", item.get("page_num"))
            try:
                return int(page) if page is not None else None
            except (TypeError, ValueError):
                return None

        def _legend_key(item):
            block_id = item.get("legend_block_id")
            if block_id is None:
                block_id = item.get("block_id")
            return (_page(item), str(block_id)) if block_id is not None else None

        def _has_resolved_assets(match):
            assets = match.get("matched_assets") or []
            asset_ids = set()
            for asset in assets:
                block_id = asset.get("block_id")
                page = asset.get("page")
                bbox = asset.get("bbox") or []
                if block_id in (None, "") or page is None or len(bbox) < 4:
                    return False
                try:
                    asset_page = int(page)
                    coords = [float(value) for value in bbox[:4]]
                except (TypeError, ValueError):
                    return False
                if asset_page < 1 or not all(math.isfinite(value) for value in coords):
                    return False
                if coords[2] <= coords[0] or coords[3] <= coords[1]:
                    return False
                asset_ids.add(str(block_id))
            declared_ids = {
                str(block_id)
                for block_id in match.get("asset_block_ids", [])
                if block_id is not None
            }
            return bool(assets) and bool(declared_ids) and declared_ids == asset_ids

        invalid_matches = []
        for match in state.matches:
            if (
                match.get("association_status") in {"HOLD", "RESERVED"}
                or not _has_resolved_assets(match)
            ):
                invalid_matches.append(match)
        for match in invalid_matches:
            page = _page(match)
            block_id = match.get("legend_block_id")
            group = {
                "group_id": match.get("group_id"),
                "page": match.get("page"),
                "bbox": match.get("cluster_bbox"),
                "assets": list(match.get("matched_assets") or []),
            }
            state.hold_legend(
                {
                    "association_status": "HOLD",
                    "page": page,
                    "legend_page": page,
                    "legend_block_id": block_id,
                    "figure_id": match.get("figure_id"),
                    "figure_number": match.get("figure_number"),
                    "text": match.get("text", ""),
                    "hold_reason": match.get("hold_reason") or "asset_evidence_invalid",
                    "candidate_groups": [group],
                    "candidate_assets": list(match.get("matched_assets") or []),
                    "candidate_asset_ids": list(match.get("asset_block_ids") or []),
                    "evidence": list(match.get("group_evidence") or []),
                }
            )
        if invalid_matches:
            invalid_ids = {id(match) for match in invalid_matches}
            state.matches[:] = [match for match in state.matches if id(match) not in invalid_ids]

        matched_legend_keys = {
            key
            for match in state.matches
            if match.get("association_status") not in {"HOLD", "RESERVED"}
            and _has_resolved_assets(match)
            and (key := _legend_key(match)) is not None
        }
        unresolved_legend_keys = {
            key
            for entry in [*state.unresolved, *state.holds]
            if (key := _legend_key(entry)) is not None
        }

        # -- 3. Classify each numbered legend ----------------------------------
        details: list[dict] = []
        matched_count = 0
        unmatched_count = 0
        gap_count = 0

        for legend in numbered_legends:
            key = _legend_key(legend)
            lid = str(legend.get("block_id", ""))
            text = str(legend.get("text", ""))
            fig_no = ocr_figures._extract_figure_number(text)

            if key in matched_legend_keys:
                status = "matched"
                matched_count += 1
            elif key in unresolved_legend_keys:
                status = "unmatched"
                unmatched_count += 1
            else:
                status = "gap"
                gap_count += 1

            details.append({
                "legend_block_id": lid,
                "page": _page(legend),
                "figure_number": fig_no,
                "status": status,
            })

        total = len(numbered_legends)
        accounted_for = matched_count + unmatched_count

        # -- 4. Populate state.completeness ------------------------------------
        state.completeness = {  # type: ignore[union-attr]
            "total_numbered_legends": total,
            "accounted_for": accounted_for,
            "gap_count": gap_count,
            "details": details,
        }

        # -- 5. Invariant: every matched asset is owned in the ledger ----------
        for match in state.matches:
            legend_id = str(match.get("legend_block_id", ""))
            asset_records = match.get("matched_assets") or []
            declared_ids = {str(bid) for bid in match.get("asset_block_ids", []) if bid is not None}
            recorded_ids = {str(asset.get("block_id")) for asset in asset_records if asset.get("block_id") is not None}
            if declared_ids != recorded_ids:
                report.invariant_errors.append(
                    f"Legend {legend_id} asset ids do not match page-scoped asset evidence"
                )
            for asset in asset_records:
                page = asset.get("page")
                bid = asset.get("block_id")
                try:
                    ref = ResourceRef(kind="asset", page=int(page), block_id=str(bid))
                except (TypeError, ValueError):
                    report.invariant_errors.append(
                        f"Asset page={page} block_id={bid} for legend {legend_id} "
                        "has no valid page-scoped identity"
                    )
                    continue
                owner = state.ledger.owner_of(ref)  # type: ignore[union-attr]
                if owner is None:
                    report.invariant_errors.append(
                        f"Asset page={page} block_id={bid} for legend "
                        f"{legend_id} is not owned in the ledger"
                    )

        # -- 6. Invariant: accounting is consistent ----------------------------
        if accounted_for != total - gap_count:
            report.invariant_errors.append(
                f"Accounting mismatch: accounted_for={accounted_for} "
                f"!= total={total} - gap_count={gap_count}"
            )

        return report
