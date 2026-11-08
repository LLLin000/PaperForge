"""OCR post-match normalization — v3 final role commit.

Consumes figure/table inventories and commits the final public `role`.
Reuses tail settlement from Workstream B.
"""

from __future__ import annotations

from paperforge.worker.ocr_document import DocumentStructure, normalize_document_structure
from paperforge.worker.ocr_document import rescue_roles_with_document_context
from paperforge.worker.ocr_profiles import build_role_span_profiles
from paperforge.worker.ocr_tail_settlement import settle_tail_and_backmatter
from paperforge.worker.ocr_blocks import _CANDIDATE_ROLES


def _sync_render_index_defaults(rows: list[dict]) -> None:
    """Mirror the legacy build_structured_blocks post-normalize sync."""
    for row in rows:
        role = row.get("role", "")
        if row.get("_container_of"):
            # Consumed by a Box callout: the container renders the text, the
            # child must stay suppressed regardless of its own role.
            row["render_default"] = False
            row["index_default"] = role not in _CANDIDATE_ROLES
            continue
        if row.get("_suppressed_heading"):
            row["render_default"] = False
            row["index_default"] = False
        else:
            row["render_default"] = role not in ({"noise", "unknown_structural", "ocr_raw_error"} | _CANDIDATE_ROLES)
            if role in {
                "noise",
                "page_header",
                "page_footer",
                "frontmatter_noise",
                "non_body_insert",
                "structured_insert",
                "author_bio_asset",
                "ocr_raw_error",
            }:
                row["render_default"] = False
            row["index_default"] = role not in _CANDIDATE_ROLES
            if role in {
                "noise",
                "frontmatter_noise",
                "table_html",
                "non_body_insert",
                "structured_insert",
                "author_bio_asset",
                "ocr_raw_error",
            }:
                row["index_default"] = False


def _inventory_claimed_roles(
    rows: list[dict],
    figure_inventory: dict | None,
    table_inventory: dict | None,
) -> tuple[dict[tuple[int, str], str], dict[tuple[int, str], str]]:
    """Roles already decided by figure/table matching, before writeback.

    Ownership is committed by the inventories, not by ``_object_owner_id``:
    apply_object_writebacks stamps that field only after post-match. A claim is
    unsafe to protect when the identity is duplicated in the rows (the
    normalizer cannot tell which row the inventory meant) or when the figure and
    table inventories both claim the same block with different roles (a
    contested object; the conflict resolver owns that decision, not this
    guard). Unsafe claims are returned with their reason.
    """
    claimed: dict[tuple[int, str], str] = {}
    families: dict[tuple[int, str], set[str]] = {}

    def _claim(page: object, block_id: object, role: str, family: str) -> None:
        if block_id is None or block_id == "":
            return
        try:
            page_number = int(page or 0)
        except (TypeError, ValueError):
            return
        key = (page_number, str(block_id))
        claimed[key] = role
        families.setdefault(key, set()).add(family)

    for figure in (figure_inventory or {}).get("matched_figures", []) or []:
        page = figure.get("page", 0)
        _claim(page, figure.get("legend_block_id"), "figure_caption", "figure")
        for block_id in figure.get("asset_block_ids") or []:
            _claim(page, block_id, "figure_asset", "figure")
    for table in (table_inventory or {}).get("tables", []) or []:
        page = table.get("page", 0)
        _claim(page, table.get("caption_block_id"), "table_caption", "table")
        if table.get("has_asset"):
            _claim(page, table.get("asset_block_id"), "table_html", "table")

    counts: dict[tuple[int, str], int] = {}
    for row in rows:
        key = (int(row.get("page", 0) or 0), str(row.get("block_id", "")))
        counts[key] = counts.get(key, 0) + 1
    unsafe: dict[tuple[int, str], str] = {}
    for key in claimed:
        if counts.get(key, 0) > 1:
            unsafe[key] = "duplicate_identity"
        elif len(families.get(key, set())) > 1:
            unsafe[key] = "contested_ownership"
    for key in unsafe:
        claimed.pop(key, None)
    return claimed, unsafe


def _reassert_claimed_roles(rows: list[dict], claimed: dict[tuple[int, str], str]) -> None:
    """Ownership outranks normalization: a claimed block keeps its object role.

    The normalize shadow and the tail settlement are free to classify body text;
    they do not get to un-claim a caption or an asset that figure/table matching
    already committed. Any disagreement is recorded for the audit, not applied.
    """
    for row in rows:
        key = (int(row.get("page", 0) or 0), str(row.get("block_id", "")))
        expected = claimed.get(key)
        if expected is None:
            continue
        actual = str(row.get("role") or "")
        if actual != expected:
            row["_post_match_role_override"] = {
                "role": actual,
                "expected": expected,
                "source": "figure_table_inventory",
            }
        row["role"] = expected


def post_match_normalize(
    rows: list[dict],
    figure_inventory: dict,
    table_inventory: dict,
    *,
    document_structure: DocumentStructure,
    source_frontmatter_anchors: dict | None = None,
) -> tuple[list[dict], DocumentStructure]:
    """Shadow normalize rows, commit final roles, run tail settlement."""
    live_rows = [dict(row) for row in rows]
    claimed_roles, unsafe_roles = _inventory_claimed_roles(
        live_rows, figure_inventory, table_inventory
    )
    for row in live_rows:
        key = (int(row.get("page", 0) or 0), str(row.get("block_id", "")))
        if key in unsafe_roles:
            row["_post_match_role_ambiguous"] = {"reason": unsafe_roles[key]}
        owner_id = row.get("_object_owner_id")
        if owner_id and key not in unsafe_roles and key not in claimed_roles:
            claimed_roles[key] = str(row.get("role") or "")
    shadow_doc, shadow_rows = normalize_document_structure(
        [dict(row) for row in rows],
        source_frontmatter_anchors=source_frontmatter_anchors,
    )
    for live, shadow in zip(live_rows, shadow_rows):
        live_role = live.get("role")
        shadow_role = shadow.get("role", live_role)
        # A block the bio cleanup classified as a biography is not a reference
        # item; the reference-zone fallback must not undo that decision.
        if (
            live.get("_object_owner_family") == "author_bio"
            and live_role == "backmatter_body"
            and shadow_role != "backmatter_body"
        ):
            shadow_role = "backmatter_body"
            live["render_default"] = True
        live["role"] = shadow_role
        live["role_source"] = shadow.get("role_source", live.get("role_source"))
        live["role_confidence"] = shadow.get("role_confidence", live.get("role_confidence"))
        live["role_candidate"] = live.get("role_candidate") or shadow.get("role")
        live["render_default"] = shadow.get("render_default", live.get("render_default"))
        live["index_default"] = shadow.get("index_default", live.get("index_default"))
        # Box ownership is a shadow-normalize product; without it the renderer
        # both drops the callout text and re-renders the children as body.
        if shadow.get("_container_text") is not None:
            live["_container_text"] = shadow["_container_text"]
        if shadow.get("_container_of"):
            live["_container_of"] = shadow["_container_of"]
    # Rescue: document-context corrections (same as legacy build_structured_blocks)
    paper_context: dict = {}
    if len(live_rows) >= 10:
        paper_context["role_profiles"] = build_role_span_profiles(live_rows)
    source_anchors = getattr(shadow_doc, "source_frontmatter_anchors", {}) if shadow_doc else {}
    legacy_rescue_enabled = not bool(source_anchors)
    if paper_context.get("role_profiles") and shadow_doc and legacy_rescue_enabled:
        live_rows = rescue_roles_with_document_context(
            live_rows, paper_context["role_profiles"], shadow_doc
        )
    settle_tail_and_backmatter(structured_blocks=live_rows, document_structure=shadow_doc)
    if claimed_roles:
        _reassert_claimed_roles(live_rows, claimed_roles)
    _sync_render_index_defaults(live_rows)
    return live_rows, shadow_doc
