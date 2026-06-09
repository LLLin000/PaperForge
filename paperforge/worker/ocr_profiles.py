"""OCR span style profile extraction and cross-validation.

Owns: block-level style extraction, family/profile aggregation,
profile-quality scoring, span cross-validation, role-family comparison.
"""

from __future__ import annotations

import json
from pathlib import Path


def extract_block_span_profile(block: dict) -> dict | None:
    """Extract a normalized style profile dict from a block's span_metadata.

    Handles both list format (per-character spans) and dict format
    (legacy/aggregated). Returns None when no span data is available.

    Return shape:
        {"mean_size": float, "max_size": float, "font_families": set[str],
         "is_bold": bool, "is_italic": bool, "is_colored": bool}
    """
    span_meta = block.get("span_metadata")
    if not span_meta:
        return None

    if isinstance(span_meta, list):
        sizes: list[float] = []
        fonts: set[str] = set()
        flags = 0
        colors: set[int] = set()
        for sp in span_meta:
            sz = sp.get("size")
            if sz is not None:
                sizes.append(float(sz))
            fnt = sp.get("font")
            if fnt:
                fonts.add(str(fnt))
            flags |= sp.get("flags", 0) if isinstance(sp.get("flags"), int) else 0
            c = sp.get("color")
            if c is not None:
                colors.add(int(c))
        if not sizes:
            return None
        return {
            "mean_size": sum(sizes) / len(sizes),
            "max_size": max(sizes),
            "font_families": fonts,
            "is_bold": bool(flags & 16),
            "is_italic": bool(flags & 4),
            "is_colored": any(c != 0 for c in colors),
        }

    if isinstance(span_meta, dict):
        size = span_meta.get("size")
        if size is None:
            return None
        flags_val = span_meta.get("flags", 0)
        is_bold: bool
        is_italic: bool
        if isinstance(flags_val, str):
            is_bold = "bold" in flags_val.lower()
            is_italic = "italic" in flags_val.lower()
        else:
            is_bold = bool(flags_val & 16) if isinstance(flags_val, int) else False
            is_italic = bool(flags_val & 4) if isinstance(flags_val, int) else False
        return {
            "mean_size": float(size),
            "max_size": float(size),
            "font_families": {span_meta.get("font", "")} if span_meta.get("font") else set(),
            "is_bold": is_bold,
            "is_italic": is_italic,
            "is_colored": span_meta.get("color", 0) != 0,
        }

    return None


def _profile_quality(block_count: int, dispersion: float) -> str:
    if block_count >= 3 and dispersion <= 0.15:
        return "strong"
    if block_count >= 3:
        return "moderate"
    if block_count >= 2:
        return "weak"
    return "no_data"


def build_role_span_profiles(blocks: list[dict]) -> dict:
    """Aggregate span profiles per role across all blocks.

    Returns dict keyed by role name, each value:
        {"block_count": int, "mean_size": float, "quality": str, ...}
    """
    buckets: dict[str, dict] = {}
    for block in blocks:
        role = block.get("role")
        if not role:
            continue
        profile = extract_block_span_profile(block)
        if profile is None:
            continue
        if role not in buckets:
            buckets[role] = {
                "sizes": [],
                "bold_count": 0,
                "italic_count": 0,
                "font_families": set(),
                "block_count": 0,
                "colored_count": 0,
            }
        buckets[role]["sizes"].extend([profile["mean_size"], profile["max_size"]])
        if profile["is_bold"]:
            buckets[role]["bold_count"] += 1
        if profile["is_italic"]:
            buckets[role]["italic_count"] += 1
        if profile["is_colored"]:
            buckets[role]["colored_count"] += 1
        buckets[role]["font_families"].update(profile["font_families"])
        buckets[role]["block_count"] += 1

    result: dict = {}
    for role, bucket in buckets.items():
        sizes = bucket["sizes"]
        mean_size = sum(sizes) / len(sizes) if sizes else 0.0
        max_size = max(sizes) if sizes else 0.0
        min_size = min(sizes) if sizes else 0.0
        dispersion = (max_size - min_size) / max_size if max_size > 0 else 0.0
        bold_ratio = bucket["bold_count"] / bucket["block_count"] if bucket["block_count"] else 0.0
        result[role] = {
            "block_count": bucket["block_count"],
            "mean_size": round(mean_size, 2),
            "max_size": round(max_size, 2),
            "min_size": round(min_size, 2),
            "dispersion": round(dispersion, 4),
            "quality": _profile_quality(bucket["block_count"], dispersion),
            "bold_ratio": round(bold_ratio, 2),
            "italic_ratio": round(bucket["italic_count"] / bucket["block_count"], 2) if bucket["block_count"] else 0.0,
            "font_families": list(bucket["font_families"]),
        }
    return result


def compare_against_role_family(
    block_profile: dict,
    role_family_profile: dict,
) -> dict:
    """Compare a block's style profile against a role family profile.

    Returns a dict with:
        {"size_compatible": bool, "bold_compatible": bool,
         "size_distance": float, "match_score": float}
    """
    if not block_profile or not role_family_profile:
        return {"size_compatible": False, "bold_compatible": False,
                "size_distance": 1.0, "match_score": 0.0}

    block_size = block_profile.get("mean_size", 0)
    fam_mean = role_family_profile.get("mean_size", 0)
    fam_max = role_family_profile.get("max_size", 0)
    fam_min = role_family_profile.get("min_size", 0)

    if fam_max == fam_min:
        size_compatible = abs(block_size - fam_mean) < 2.0
    else:
        size_compatible = fam_min <= block_size <= fam_max

    size_distance = (
        abs(block_size - fam_mean) / max(fam_mean, 1)
        if fam_mean > 0
        else 1.0
    )

    bold_ratio = role_family_profile.get("bold_ratio", 0)
    block_bold = block_profile.get("is_bold", False)
    bold_compatible = (bold_ratio > 0.5) == block_bold

    match_score = (
        (0.6 * (1 - min(size_distance, 1.0))) +
        (0.4 * (1 if bold_compatible else 0))
    )

    return {
        "size_compatible": size_compatible,
        "bold_compatible": bold_compatible,
        "size_distance": round(size_distance, 4),
        "match_score": round(match_score, 4),
    }


def cross_validate_with_span(
    block: dict,
    tentative_role: str,
    role_profiles: dict,
) -> dict:
    """Cross-validate a block's span profile against role family profiles.

    Never overrides the tentative role — only adjusts confidence and
    suggests alternatives.

    Returns:
        {"role": str, "adjustment": float, "confidence_total": float,
         "suggested_roles": list[str], "match_details": dict}
    """
    block_profile = extract_block_span_profile(block)
    if block_profile is None:
        return {"role": tentative_role, "adjustment": 0.0, "confidence_total": 0.0,
                "suggested_roles": [], "match_details": {}}

    current_match = compare_against_role_family(
        block_profile, role_profiles.get(tentative_role, {})
    )
    base_score = current_match["match_score"]
    quality = role_profiles.get(tentative_role, {}).get("quality", "no_data")

    if quality in ("weak", "no_data"):
        return {"role": tentative_role, "adjustment": 0.0, "confidence_total": base_score,
                "suggested_roles": [], "match_details": {tentative_role: current_match}}

    suggested_roles = []
    for alt_role, alt_profile in role_profiles.items():
        if alt_role == tentative_role:
            continue
        alt_match = compare_against_role_family(block_profile, alt_profile)
        if alt_match["match_score"] > base_score + 0.1:
            suggested_roles.append(alt_role)

    adjustment = round(base_score - 0.5, 4)

    return {
        "role": tentative_role,
        "adjustment": adjustment,
        "confidence_total": round(base_score, 4),
        "suggested_roles": suggested_roles,
        "match_details": {tentative_role: current_match},
    }


FAMILY_DEFINITIONS: dict[str, list[str]] = {
    "body_family": ["body_paragraph", "tail_candidate_body", "backmatter_body"],
    "heading_family": ["section_heading", "subsection_heading", "sub_subsection_heading"],
    "backmatter_heading_family": ["backmatter_heading", "backmatter_boundary_heading", "reference_heading"],
    "reference_family": ["reference_item"],
    "non_body_insert_family": ["non_body_insert"],
    "caption_family": ["figure_caption", "table_caption"],
}

STYLE_FAMILY_TO_PROFILE_FAMILY: dict[str, str] = {
    "body_like": "body_family",
    "heading_like": "heading_family",
    "legend_like": "legend_family",
    "table_caption_like": "table_caption_family",
    "reference_like": "reference_family",
    "support_like": "support_family",
    "unknown_like": "unknown_family",
}


def build_family_profiles(blocks: list[dict]) -> dict:
    """Derive family-level profiles from block role/span data.

    Each family groups related roles (e.g. body_family includes
    body_paragraph, tail_candidate_body, backmatter_body).  Family
    profile format is the same as role profiles with an added
    ``member_roles`` list.

    Returns dict keyed by family name (only families with at least
    one member role having blocks are included).
    """
    role_profiles = build_role_span_profiles(blocks)
    families: dict = {}

    style_family_blocks: dict[str, list[dict]] = {}
    for block in blocks:
        style_family = block.get("style_family")
        if not style_family:
            continue
        style_family_blocks.setdefault(str(style_family), []).append(block)

    for style_family, family_name in STYLE_FAMILY_TO_PROFILE_FAMILY.items():
        members = style_family_blocks.get(style_family, [])
        if not members:
            continue
        profile = _build_profile_from_blocks(members)
        if profile is None:
            continue
        families[family_name] = {
            **profile,
            "member_roles": sorted({str(block.get("role") or "") for block in members if block.get("role")}),
            "source_style_family": style_family,
        }

    for family_name, member_roles in FAMILY_DEFINITIONS.items():
        if family_name in families:
            continue
        available = {
            role: role_profiles[role]
            for role in member_roles
            if role in role_profiles and role_profiles[role]["block_count"] > 0
        }
        if not available:
            continue

        total_count = sum(p["block_count"] for p in available.values())
        weighted_mean_size = (
            sum(p["mean_size"] * p["block_count"] for p in available.values()) / total_count
            if total_count > 0
            else 0.0
        )
        max_size = max(p["max_size"] for p in available.values())
        min_size = min(p["min_size"] for p in available.values())
        dispersion = (max_size - min_size) / max_size if max_size > 0 else 0.0
        bold_ratio = (
            sum(p["bold_ratio"] * p["block_count"] for p in available.values()) / total_count
            if total_count > 0
            else 0.0
        )
        italic_ratio = (
            sum(p["italic_ratio"] * p["block_count"] for p in available.values()) / total_count
            if total_count > 0
            else 0.0
        )
        font_families: set[str] = set()
        for p in available.values():
            font_families.update(p.get("font_families", []))

        families[family_name] = {
            "block_count": total_count,
            "mean_size": round(weighted_mean_size, 2),
            "max_size": round(max_size, 2),
            "min_size": round(min_size, 2),
            "dispersion": round(dispersion, 4),
            "quality": _profile_quality(total_count, dispersion),
            "bold_ratio": round(bold_ratio, 2),
            "italic_ratio": round(italic_ratio, 2),
            "font_families": list(font_families),
            "member_roles": member_roles,
        }
    return families


def _build_profile_from_blocks(blocks: list[dict]) -> dict | None:
    profiles = [extract_block_span_profile(block) for block in blocks]
    usable_profiles = [profile for profile in profiles if profile is not None]
    if not usable_profiles:
        return None

    sizes: list[float] = []
    font_families: set[str] = set()
    bold_count = 0
    italic_count = 0
    colored_count = 0
    for profile in usable_profiles:
        sizes.extend([profile["mean_size"], profile["max_size"]])
        font_families.update(profile["font_families"])
        if profile["is_bold"]:
            bold_count += 1
        if profile["is_italic"]:
            italic_count += 1
        if profile["is_colored"]:
            colored_count += 1

    block_count = len(usable_profiles)
    mean_size = sum(sizes) / len(sizes) if sizes else 0.0
    max_size = max(sizes) if sizes else 0.0
    min_size = min(sizes) if sizes else 0.0
    dispersion = (max_size - min_size) / max_size if max_size > 0 else 0.0
    return {
        "block_count": block_count,
        "mean_size": round(mean_size, 2),
        "max_size": round(max_size, 2),
        "min_size": round(min_size, 2),
        "dispersion": round(dispersion, 4),
        "quality": _profile_quality(block_count, dispersion),
        "bold_ratio": round(bold_count / block_count, 2) if block_count else 0.0,
        "italic_ratio": round(italic_count / block_count, 2) if block_count else 0.0,
        "font_families": list(font_families),
        "colored_ratio": round(colored_count / block_count, 2) if block_count else 0.0,
    }


def compare_against_family(
    block_profile: dict,
    family_profile: dict,
) -> dict:
    """Compare a block's style profile against a family-level aggregated profile.

    Same comparison semantics as ``compare_against_role_family`` but
    operates on family-aggregated stats for broader-baseline matching.

    Returns:
        {"size_compatible": bool, "bold_compatible": bool,
         "size_distance": float, "match_score": float}
    """
    if not block_profile or not family_profile:
        return {"size_compatible": False, "bold_compatible": False,
                "size_distance": 1.0, "match_score": 0.0}

    return compare_against_role_family(block_profile, family_profile)


def write_role_span_profiles(
    blocks: list[dict],
    output_dir: str | Path,
) -> Path:
    """Build and write role_span_profiles.json.

    Returns the path to the written file.
    """
    profiles = build_role_span_profiles(blocks)
    output_path = Path(output_dir) / "role_span_profiles.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)
    return output_path
