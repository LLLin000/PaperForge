from __future__ import annotations

from .ocr_figure_vnext_types import PassReport, ResourceRef


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

        # -- 2. Build lookup sets ----------------------------------------------
        matched_legend_ids: set[str] = set()
        for match in state.matches:
            lid = match.get("legend_block_id")
            if lid is not None:
                matched_legend_ids.add(str(lid))

        unresolved_legend_ids: set[str] = set()
        for entry in state.unresolved:
            lid = entry.get("legend_block_id")
            if lid is not None:
                unresolved_legend_ids.add(str(lid))

        # -- 3. Classify each numbered legend ----------------------------------
        details: list[dict] = []
        matched_count = 0
        unmatched_count = 0
        gap_count = 0

        for legend in numbered_legends:
            lid = str(legend.get("block_id", ""))
            text = str(legend.get("text", ""))
            fig_no = ocr_figures._extract_figure_number(text)

            if lid in matched_legend_ids:
                status = "matched"
                matched_count += 1
            elif lid in unresolved_legend_ids:
                status = "unmatched"
                unmatched_count += 1
            else:
                status = "gap"
                gap_count += 1

            details.append({
                "legend_block_id": lid,
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
            page = match.get("page")
            for bid in match.get("asset_block_ids", []):
                ref = ResourceRef(
                    kind="asset",
                    page=page,
                    block_id=bid,
                )
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
