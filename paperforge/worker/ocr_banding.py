from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import median


@dataclass
class LayoutBandEstimate:
    header_band: float | None
    footer_band: float | None
    status: str
    method: str
    accepted_candidates: list[dict]
    excluded_candidates: list[dict]
    support_pages: list[int]
    warnings: list[str]


@dataclass
class UsableContentDecision:
    usable: bool
    policy: str
    reason: list[str]
    header_band: float | None
    footer_band: float | None
    role: str


def _block_text(block: dict) -> str:
    return str(block.get("text") or block.get("block_content") or "")


def _block_bbox(block: dict) -> list[float] | None:
    bbox = block.get("bbox") or block.get("block_bbox")
    return bbox if bbox and len(bbox) >= 4 else None


def collect_layout_band_candidates(blocks: list[dict]) -> list[dict]:
    records: list[dict] = []
    for block in blocks:
        bbox = _block_bbox(block)
        if not bbox:
            continue
        page_width = float(block.get("page_width") or 0)
        page_height = float(block.get("page_height") or 0)
        if page_width <= 0 or page_height <= 0:
            continue
        role = str(block.get("role") or "")
        raw_label = str(block.get("raw_label") or "")
        if role not in {"noise", "header", "footer", "number"} and raw_label not in {"header", "footer", "number"}:
            continue

        x1, y1, x2, y2 = bbox
        width = max(0.0, x2 - x1)
        height = max(0.0, y2 - y1)
        touches_header_band = y1 < page_height * 0.15
        inside_header_band = y2 < page_height * 0.15
        touches_footer_band = y2 > page_height * 0.85
        inside_footer_band = y1 > page_height * 0.85
        if not (touches_header_band or touches_footer_band):
            continue

        records.append(
            {
                "page": int(block.get("page") or 0),
                "page_width": page_width,
                "page_height": page_height,
                "role": role,
                "raw_label": raw_label,
                "text": _block_text(block),
                "bbox": [x1, y1, x2, y2],
                "x1_ratio": x1 / page_width,
                "x2_ratio": x2 / page_width,
                "y1_ratio": y1 / page_height,
                "y2_ratio": y2 / page_height,
                "width_ratio": width / page_width,
                "height_ratio": height / page_height,
                "candidate_side": "header" if touches_header_band else "footer",
                "inside_header_band": inside_header_band,
                "inside_footer_band": inside_footer_band,
                "decision": "accepted",
                "reason": [],
                "evidence": list(block.get("evidence") or []),
            }
        )
    return records


def _is_margin_band_like(candidate: dict) -> bool:
    return candidate["height_ratio"] > 0.08 and candidate["width_ratio"] < 0.35


def _is_watermark_text(candidate: dict) -> bool:
    text = candidate["text"].lower()
    return any(s in text for s in ["downloaded from", "accepted manuscript", "publisher", "onlinelibrary", "copyright"])


def _exclude_candidates(candidates: list[dict]) -> tuple[list[dict], list[dict]]:
    accepted: list[dict] = []
    excluded: list[dict] = []
    for c in candidates:
        reasons: list[str] = []
        if c["height_ratio"] > 0.12:
            reasons.append("abnormally_tall_noise")
        if c["height_ratio"] > 0.04 and not c["text"].strip():
            reasons.append("empty_tall_noise")
        if _is_margin_band_like(c):
            reasons.append("margin_band_geometry")
        if _is_margin_band_like(c) and (_is_watermark_text(c) or any("margin-band" in e or "margin_band" in e for e in c.get("evidence", []))):
            reasons.append("watermark_margin_band")

        if reasons:
            excluded.append({**c, "decision": "excluded", "reason": reasons})
        else:
            accepted.append(c)
    return accepted, excluded


def _cluster_tolerance(page_heights: list[float]) -> float:
    med = median(page_heights) if page_heights else 0.0
    return max(25.0, 0.015 * med)


def _cluster_values(values: list[tuple[int, float]], tolerance: float) -> list[list[tuple[int, float]]]:
    if not values:
        return []
    values = sorted(values, key=lambda x: x[1])
    clusters: list[list[tuple[int, float]]] = [[values[0]]]
    for item in values[1:]:
        if abs(item[1] - clusters[-1][-1][1]) <= tolerance:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    return clusters


def estimate_layout_bands(blocks: list[dict]) -> LayoutBandEstimate:
    candidates = collect_layout_band_candidates(blocks)
    accepted, excluded = _exclude_candidates(candidates)
    if not accepted:
        return LayoutBandEstimate(None, None, "EMPTY", "robust_cluster", [], excluded, [], ["no_accepted_candidates"])

    page_heights = [c["page_height"] for c in accepted]
    tolerance = _cluster_tolerance(page_heights)
    header_page_values: dict[int, float] = {}
    footer_page_values: dict[int, float] = {}
    for c in accepted:
        page = c["page"]
        if c["candidate_side"] == "header":
            header_page_values[page] = max(header_page_values.get(page, c["bbox"][3]), c["bbox"][3])
        else:
            footer_page_values[page] = min(footer_page_values.get(page, c["bbox"][1]), c["bbox"][1])

    def support_threshold(n: int) -> int:
        return max(2, math.ceil(0.2 * n))

    def choose(values: dict[int, float], side: str) -> tuple[float | None, list[int], str]:
        if not values:
            return None, [], "none"
        clusters = _cluster_values(list(values.items()), tolerance)
        clusters.sort(key=lambda cl: (-len(cl), min(v for _, v in cl)))
        best = clusters[0]
        if len(best) < support_threshold(len(values)):
            return None, [], "hold"
        only_vals = sorted(v for _, v in best)
        if side == "header":
            value = only_vals[math.ceil(0.9 * (len(only_vals) - 1))]
        else:
            value = only_vals[math.floor(0.1 * (len(only_vals) - 1))]
        return value, sorted(p for p, _ in best), "accept"

    header_band, header_pages, header_status = choose(header_page_values, "header")
    footer_band, footer_pages, footer_status = choose(footer_page_values, "footer")

    status = "ACCEPT" if (header_status == "accept" or footer_status == "accept") else "HOLD_NO_STABLE_BAND"
    if header_status == "none" and footer_status == "none":
        status = "EMPTY"

    support_pages = sorted({*header_pages, *footer_pages})
    warnings: list[str] = []
    if status == "HOLD_NO_STABLE_BAND":
        warnings.append("no_stable_cluster")

    return LayoutBandEstimate(header_band, footer_band, status, "robust_cluster", accepted, excluded, support_pages, warnings)


def choose_runtime_bands(
    robust_estimate: LayoutBandEstimate,
    legacy_header_band: float | None,
    legacy_footer_band: float | None,
    *,
    max_page_height: float,
) -> tuple[float | None, float | None, str]:
    if robust_estimate.status == "ACCEPT":
        return robust_estimate.header_band, robust_estimate.footer_band, "robust"

    legacy_header_safe = legacy_header_band is not None and legacy_header_band < 0.2 * max_page_height
    legacy_footer_safe = legacy_footer_band is not None and legacy_footer_band > 0.8 * max_page_height
    if legacy_header_safe or legacy_footer_safe:
        return legacy_header_band if legacy_header_safe else None, legacy_footer_band if legacy_footer_safe else None, "legacy_safe"

    return None, None, "none"


def decide_usable_content(block: dict, band_estimate: LayoutBandEstimate | None, *, context: str) -> UsableContentDecision:
    role = str(block.get("role") or "")
    strong_bypass = {
        "reference_heading",
        "reference_item",
        "reference_body",
        "backmatter_heading",
        "backmatter_boundary_heading",
    }
    if role in strong_bypass:
        return UsableContentDecision(True, "role_bypass", ["strong_role_bypass"], band_estimate.header_band if band_estimate else None, band_estimate.footer_band if band_estimate else None, role)

    bbox = _block_bbox(block)
    if not bbox or band_estimate is None:
        return UsableContentDecision(True, "no_band", ["missing_bbox_or_band"], band_estimate.header_band if band_estimate else None, band_estimate.footer_band if band_estimate else None, role)

    y1, y2 = bbox[1], bbox[3]
    if band_estimate.header_band is not None and y2 < band_estimate.header_band:
        return UsableContentDecision(False, context, ["above_header_band"], band_estimate.header_band, band_estimate.footer_band, role)
    if band_estimate.footer_band is not None and y1 > band_estimate.footer_band:
        return UsableContentDecision(False, context, ["below_footer_band"], band_estimate.header_band, band_estimate.footer_band, role)
    return UsableContentDecision(True, context, ["within_usable_band"], band_estimate.header_band, band_estimate.footer_band, role)
