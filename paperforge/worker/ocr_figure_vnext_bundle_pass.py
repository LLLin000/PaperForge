from __future__ import annotations

from .ocr_pairing_types import ClaimProposal, PassReport, ResourceRef

_NON_PURE_ROLES = frozenset({
    "body_paragraph",
    "section_heading",
    "subsection_heading",
    "table_caption",
    "table_asset",
    "table_html",
    "backmatter_heading",
    "backmatter_body",
    "reference_item",
})


def _resource_page(block: dict) -> int | None:
    page = block.get("page")
    if page is None:
        page = block.get("page_num")
    return int(page) if page is not None else None


class LegendBundlePass:
    """Fallback pass: bundle ≥3 orphan captions to subsequent pure-asset pages.

    When a page packs 3+ figure captions with zero same-page assets
    (common in preproof/early-view layouts), match captions 1:1 by page
    order to subsequent pages that each hold unclaimed assets and have
    no body/table text.
    """

    name = "legend_bundle"

    def run(self, state):
        from . import ocr_figures

        report = PassReport(pass_name=self.name)

        # ----- 1. Compute unmatched legends -----
        matched_legend_ids = {
            str(m.get("legend_block_id", ""))
            for m in state.matches
        }
        unmatched_legends = [
            leg for leg in state.candidate_index.deduped_legends
            if str(leg.get("block_id", "")) not in matched_legend_ids
        ]

        # ----- 2. Compute unmatched assets (not owned by ledger) -----
        unmatched_assets = []
        for ast in state.corpus.raw_assets:
            page = _resource_page(ast)
            bid = ast.get("block_id")
            if page is None or bid is None:
                continue
            owner = state.ledger.owner_of_asset(page=page, block_id=str(bid))
            if owner is None:
                unmatched_assets.append(ast)

        if not unmatched_legends or not unmatched_assets:
            return report

        # ----- 3. Group unmatched numbered legends by page -----
        bundle_source_ids = state.candidate_index.bundle_source_legend_ids
        page_captions: dict[int, list[dict]] = {}
        for leg in unmatched_legends:
            cp = _resource_page(leg)
            if cp is None:
                continue
            if ocr_figures._extract_figure_number(str(leg.get("text", ""))) is None:
                continue
            page_captions.setdefault(cp, []).append(leg)

        # ----- 4. Process each caption page -----
        for cp, caps in sorted(page_captions.items()):
            has_bundle_source = any(
                str(cap.get("block_id", "")) in bundle_source_ids
                for cap in caps
            )
            if len(caps) < 3 and not has_bundle_source:
                continue

            # Skip if the caption page itself has unclaimed assets
            page_has_assets = any(
                _resource_page(a) == cp for a in unmatched_assets
            )
            if page_has_assets:
                continue

            caps_sorted = sorted(
                caps,
                key=lambda b: (b.get("bbox") or [0, 0, 0, 0])[1],
            )

            # Collect subsequent pages with unclaimed assets
            asset_pages: dict[int, list[dict]] = {}
            for ast in unmatched_assets:
                ap = _resource_page(ast)
                if ap is None or ap <= cp:
                    continue
                asset_pages.setdefault(ap, []).append(ast)

            page_order = sorted(asset_pages.keys())
            if not page_order:
                continue

            # Validate: no body/table on intervening pages
            intervening_pages = set(range(cp + 1, page_order[0]))
            intervening_body = any(
                _resource_page(b) in intervening_pages
                and b.get("role", "") in _NON_PURE_ROLES
                for b in state.corpus.blocks
            )
            if intervening_body:
                continue

            # Validate each asset page has no body/table
            valid_pages: list[int] = []
            for ap in page_order:
                page_has_body = any(
                    _resource_page(b) == ap
                    and b.get("role", "") in _NON_PURE_ROLES
                    for b in state.corpus.blocks
                )
                if not page_has_body:
                    valid_pages.append(ap)

            if not valid_pages:
                continue

            # Cap captions to available pages
            caps_to_match = caps_sorted[:len(valid_pages)]

            # ----- 5. Match captions 1:1 to valid asset pages -----
            for idx, cap in enumerate(caps_to_match):
                if idx >= len(valid_pages):
                    break
                ap = valid_pages[idx]
                page_assets = asset_pages.get(ap, [])
                if not page_assets:
                    continue

                figure_no = ocr_figures._extract_figure_number(
                    str(cap.get("text", ""))
                )
                namespace = ocr_figures._extract_figure_namespace(
                    str(cap.get("text", ""))
                )

                legend_ref = ResourceRef(
                    kind="legend",
                    page=cp,
                    block_id=cap.get("block_id"),
                    figure_no=figure_no,
                )

                asset_refs = [
                    ResourceRef(
                        kind="asset",
                        page=ap,
                        block_id=ast.get("block_id"),
                    )
                    for ast in page_assets
                ]

                proposal = ClaimProposal(
                    pass_name=self.name,
                    figure_no=figure_no,
                    claim_type="match",
                    legends=[legend_ref],
                    assets=asset_refs,
                    groups=[],
                    confidence=0.3,
                    evidence_rank=4,
                    reason="legend_bundle",
                    diagnostics={
                        "evidence": ["legend_bundle_fallback"],
                    },
                )

                # Try to claim assets through ledger
                conflict = state.ledger.try_claim_assets(
                    asset_refs, owner=legend_ref, reason="legend_bundle"
                )
                if conflict is not None:
                    report.conflicts.append(conflict)
                    report.rejected.append(proposal)
                    continue

                # Build match record
                matched_assets = [
                    ocr_figures._project_asset_record(a)
                    for a in page_assets
                ]

                if figure_no is not None:
                    figure_id = ocr_figures._format_figure_id(
                        namespace, figure_no
                    )
                else:
                    figure_id = f"figure_unknown_{len(state.matches):03d}"

                match_record = {
                    "figure_id": figure_id,
                    "figure_namespace": namespace,
                    "figure_number": figure_no,
                    "legend_block_id": cap.get("block_id", ""),
                    "page": ap,
                    "text": str(cap.get("text", "")),
                    "matched_assets": matched_assets,
                    "asset_block_ids": sorted(
                        str(a.get("block_id", "")) for a in page_assets
                    ),
                    "settlement_type": "legend_bundle",
                    "confidence": 0.3,
                    "match_score": {
                        "score": 0.3,
                        "decision": "matched",
                        "evidence": ["legend_bundle_fallback"],
                    },
                    "flags": ["legend_bundle_match"],
                    "bridge_block_ids": [],
                }

                state.accept_match(proposal, match_record)
                report.accepted.append(proposal)

        # Remove claimed assets from the pool so subsequent caption-page
        # groups don't compete for already-owned assets.  Within a single
        # caption-page group, 1:1 index matching (idx → valid_pages[idx])
        # ensures each caption claims a unique page — the ledger prevents
        # double-claiming across groups.
        newly_matched_count = len([
            p for p in report.accepted
            if p.pass_name == self.name and p.diagnostics.get("evidence") == ["legend_bundle_fallback"]
        ])
        if newly_matched_count > 0:
            claimed_ids = {
                str(a.get("block_id", ""))
                for m in state.matches[-newly_matched_count:]
                for a in m.get("matched_assets", [])
            }
            if claimed_ids:
                unmatched_assets = [
                    a for a in unmatched_assets
                    if str(a.get("block_id", "")) not in claimed_ids
                ]

        return report
