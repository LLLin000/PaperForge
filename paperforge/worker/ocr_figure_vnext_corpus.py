from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FigureCorpus:
    blocks: list[dict]
    page_width: float
    raw_legends: list[dict] = field(default_factory=list)
    raw_assets: list[dict] = field(default_factory=list)
    locator_candidates: list[dict] = field(default_factory=list)
    page_layouts: dict[int, Any] = field(default_factory=dict)

    @classmethod
    def from_blocks(cls, blocks: list[dict], page_width: float = 1200) -> "FigureCorpus":
        from . import ocr_figures
        from .ocr_document import _build_page_layout_profiles

        raw_legends = [b for b in blocks if b.get("role") in {"figure_caption", "figure_caption_candidate"}]
        raw_assets = [b for b in blocks if b.get("role") in {"figure_asset", "media_asset"}]
        locator_candidates = [b for b in raw_legends if ocr_figures._is_previous_page_legend_locator(b)]
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
    formal_legends: list[dict]
    held_legends: list[dict]
    rejected_legends: list[dict]
    deduped_legends: list[dict]
    candidate_groups: list[dict]
    competing_caption_pages: set[int]
    sidecar_candidates: dict[int, list[dict]]
    bundle_source_legend_ids: set[str]
    locator_candidates: list[dict]

    @classmethod
    def from_corpus(cls, corpus: FigureCorpus) -> "FigureCandidateIndex":
        from . import ocr_figures

        formal_legends = [
            b for b in corpus.raw_legends if ocr_figures._is_formal_legend(str(b.get("text", "")), b, corpus.page_width)
        ]
        rejected_legends = [b for b in corpus.raw_legends if b not in formal_legends]
        candidate_groups = ocr_figures._build_candidate_figure_groups_from_assets(
            corpus.raw_assets,
            formal_legends,
            corpus.blocks,
            page_width=corpus.page_width,
        )
        competing_caption_pages = {
            int(leg.get("page"))
            for leg in formal_legends
            if leg.get("page") is not None and ocr_figures._extract_figure_number(str(leg.get("text", ""))) is not None
        }
        return cls(
            formal_legends=formal_legends,
            held_legends=[],
            rejected_legends=rejected_legends,
            deduped_legends=formal_legends,
            candidate_groups=candidate_groups,
            competing_caption_pages=competing_caption_pages,
            sidecar_candidates={},
            bundle_source_legend_ids=set(),
            locator_candidates=corpus.locator_candidates,
        )
