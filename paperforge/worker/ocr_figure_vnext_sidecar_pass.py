from __future__ import annotations

from .ocr_figure_vnext_types import ClaimProposal, PassReport, ResourceRef


def _resource_page(block: dict) -> int | None:
    """Extract page number from a block dict (page or page_num)."""
    page = block.get("page")
    if page is None:
        page = block.get("page_num")
    return int(page) if page is not None else None


class SidecarPass:
    """Fallback pass matching narrow captions to same-page assets.

    The PrimarySamePagePass targets wide legends with high-confidence
    scoring.  Narrow captions (aligned in a side column, width <60 % of
    page width) often score poorly because they lack the spatial
    signatures of a full-width figure caption.  SidecarPass rescues
    these by partitioning same-page assets into caption-aligned bands
    and claiming each band's assets for its narrow caption.
    """

    name = "sidecar"

    def run(self, state):
        report = PassReport(pass_name=self.name)
        from . import ocr_figures

        sidecar_candidates = getattr(state.candidate_index, "sidecar_candidates", None) or {}

        for page, narrow_captions in sidecar_candidates.items():
            page_assets = [a for a in state.corpus.raw_assets if _resource_page(a) == page]
            if not page_assets:
                continue

            # Compute page_height from blocks on this page (same pattern as
            # ocr_figures.py:_sidecar_page_promotion, line 4117).
            page_blocks = [b for b in state.corpus.blocks if _resource_page(b) == page]
            page_height = float(
                max((b.get("bbox") or [0, 0, 0, 0])[3] for b in page_blocks) or 1200
            )

            bands = ocr_figures._partition_assets_by_caption_bands(
                narrow_captions, page_assets, page_height
            )

            for caption in narrow_captions:
                cid = str(caption.get("block_id", ""))

                # Skip captions already protected by an earlier pass
                protected = False
                for match in state.matches:
                    if str(match.get("legend_block_id", "")) == cid:
                        if ocr_figures._has_protected_figure_ownership(match):
                            protected = True
                            break
                if protected:
                    continue

                band_assets = bands.get(cid, [])
                if not band_assets:
                    continue

                asset_refs = []
                for asset in band_assets:
                    apage = _resource_page(asset)
                    if apage is None:
                        continue
                    asset_refs.append(ResourceRef(
                        kind="asset", page=apage, block_id=str(asset.get("block_id", "")),
                    ))

                if not asset_refs:
                    continue

                legend_ref = ResourceRef(kind="legend", page=page, block_id=cid)
                figure_text = str(caption.get("text", ""))
                figure_no = ocr_figures._extract_figure_number(figure_text)

                proposal = ClaimProposal(
                    pass_name=self.name,
                    figure_no=figure_no,
                    claim_type="match",
                    legends=[legend_ref],
                    assets=asset_refs,
                    groups=[],
                    confidence=0.3,
                    evidence_rank=5,
                    reason="sidecar_match",
                    diagnostics={"caption_block_id": cid, "page": page},
                )

                conflict = state.ledger.try_claim_assets(
                    proposal.assets, owner=proposal.legends[0], reason=proposal.reason,
                )
                if conflict is not None:
                    report.conflicts.append(conflict)
                    report.rejected.append(proposal)
                    continue

                namespace = ocr_figures._extract_figure_namespace(figure_text)
                if figure_no is None:
                    figure_id = f"figure_unknown_{len(state.matches):03d}"
                else:
                    figure_id = ocr_figures._format_figure_id(namespace, figure_no)

                match_record = {
                    "legend_block_id": cid,
                    "figure_id": figure_id,
                    "figure_number": figure_no,
                    "settlement_type": "sidecar",
                    "flags": ["sidecar_match"],
                    "page": page,
                    "matched_assets": [ocr_figures._project_asset_record(a) for a in band_assets],
                    "evidence": [],
                    "pass_name": self.name,
                }

                state.accept_match(proposal, match_record)
                report.accepted.append(proposal)

        return report
