from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FigureCorpus:
    """Immutable facts extracted from structured blocks.

    This dataclass stores raw, unfiltered data plus computed layout profiles.
    No derived hypotheses or candidate logic lives here.
    """

    blocks: list[dict]
    page_width: float
    raw_legends: list[dict] = field(default_factory=list)
    raw_assets: list[dict] = field(default_factory=list)
    locator_candidates: list[dict] = field(default_factory=list)
    page_layouts: dict[int, Any] = field(default_factory=dict)

    @classmethod
    def from_blocks(cls, blocks: list[dict], page_width: float = 1200) -> FigureCorpus:
        from paperforge.worker.ocr_document import _build_page_layout_profiles

        from . import ocr_figures

        raw_legends = [
            b for b in blocks if ocr_figures._match_role(b) in {"figure_caption", "figure_caption_candidate"}
        ]
        raw_assets = [
            b for b in blocks if ocr_figures._match_role(b) in {"figure_asset", "media_asset"}
        ]
        locator_candidates = [
            b for b in raw_legends if ocr_figures._is_previous_page_legend_locator(b)
        ]
        return cls(
            blocks=list(blocks),
            page_width=page_width,
            raw_legends=raw_legends,
            raw_assets=raw_assets,
            locator_candidates=locator_candidates,
            page_layouts=_build_page_layout_profiles(blocks),
        )


@dataclass
class FigureCandidateIndex:
    """Derived hypotheses and candidates built from a FigureCorpus.

    These are derived interpretations — lists of formal legends, deduped legends
    (currently same as formal_legends — dedup over groups may be added later),
    rejected legends that didn't meet criteria for formal status, candidate
    groups built from assets, and per-page maps for sidecar/competition detection.
    """

    formal_legends: list[dict]
    held_legends: list[dict]
    rejected_legends: list[dict]
    deduped_legends: list[dict]
    candidate_groups: list[dict]
    competing_caption_pages: set[int]
    sidecar_candidates: dict[int, list[dict]]
    bundle_source_legend_ids: set[str]
    locator_candidates: list[dict]
    composite_parent_candidates: list[dict] = field(default_factory=list)

    @classmethod
    def from_corpus(cls, corpus: FigureCorpus) -> FigureCandidateIndex:
        from . import ocr_figures

        formal_legends = [
            b
            for b in corpus.raw_legends
            if ocr_figures._is_formal_legend(
                str(b.get("text", "")), b, corpus.page_width
            )
        ]
        for leg in formal_legends:
            text = str(leg.get("text", ""))
            if ocr_figures._is_figure_continuation_caption(text):
                leg["_figure_continuation"] = True
                leg["_continuation_base_number"] = ocr_figures._extract_base_figure_number(text)
        rejected_legends = [b for b in corpus.raw_legends if b not in formal_legends]
        candidate_groups = ocr_figures._build_candidate_figure_groups_from_assets(
            corpus.raw_assets,
            corpus.blocks,
            formal_legends,
            page_width=corpus.page_width,
        )
        competing_caption_pages = {
            int(leg.get("page"))
            for leg in formal_legends
            if leg.get("page") is not None
            and ocr_figures._extract_figure_number(str(leg.get("text", "")))
            is not None
        }
        # Populate sidecar_candidates: pages with >=2 aligned narrow captions.
        sidecar_candidates: dict[int, list[dict]] = {}
        _legends_by_page: dict[int, list[dict]] = {}
        for leg in formal_legends:
            _legends_by_page.setdefault(int(leg.get("page", 0) or 0), []).append(leg)
        for sp, spl in _legends_by_page.items():
            narrow_set = ocr_figures._same_page_narrow_caption_column(spl, corpus.page_width)
            if len(narrow_set) >= 2:
                sidecar_candidates[sp] = narrow_set

        # Populate bundle_source_legend_ids: legends on pages with >=3 numbered legends
        # and zero assets on that page.
        bundle_source_legend_ids = ocr_figures._identify_bundle_source_legend_ids(
            formal_legends, corpus.raw_assets
        )

        # Populate composite_parent_candidates: same-page atomic groups with
        # horizontal alignment + vertical adjacency (2x2 grid, columnar stacks).
        composite_parent_candidates = ocr_figures._build_composite_parent_figure_groups_visual_only(
            candidate_groups,
            corpus.raw_assets,
            corpus.blocks,
            corpus.page_width,
        )
        return cls(
            formal_legends=formal_legends,
            held_legends=[],
            rejected_legends=rejected_legends,
            deduped_legends=formal_legends,
            candidate_groups=candidate_groups,
            competing_caption_pages=competing_caption_pages,
            sidecar_candidates=sidecar_candidates,
            bundle_source_legend_ids=bundle_source_legend_ids,
            locator_candidates=corpus.locator_candidates,
            composite_parent_candidates=composite_parent_candidates,
        )
