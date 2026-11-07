"""Region tree: what the page space looks like, before any role reasoning.

Contract
--------
`build_region_tree(refs, page) -> list[Region]`

Every block of the page must be a member of exactly one non-container region,
or of exactly one container region (containers own their member blocks, so the
column region that geometrically covers them does not list them again).
Regions are returned in reading order of their own `(y_top, x_left)` — the
order is the builder's, not the caller's.

See `paperforge.worker.layout.model` for the dataclasses and the region kinds.
"""

from .model import (
    REGION_COLUMN,
    REGION_CONTAINER,
    REGION_FULL_WIDTH,
    REGION_MARGIN,
    BlockRef,
    Region,
)

_CONTAINER_ROLES = {"structured_insert", "table_html", "non_body_insert"}


def build_region_tree(refs: list[BlockRef], page: int) -> list[Region]:
    page_refs = sorted((ref for ref in refs if ref.page == page), key=lambda ref: ref.uid)
    if not page_refs:
        return []

    boxed = [ref for ref in page_refs if ref.bbox is not None]
    width = max((ref.page_width for ref in page_refs), default=0.0)
    height = max((ref.page_height for ref in page_refs), default=0.0)
    width = width if width > 0 else max((ref.bbox[2] for ref in boxed), default=0.0)
    height = height if height > 0 else max((ref.bbox[3] for ref in boxed), default=0.0)
    tolerance = width * 0.02

    def order(ref: BlockRef) -> tuple[float, float, str]:
        assert ref.bbox is not None
        return ref.bbox[1], ref.bbox[0], ref.uid

    # BlockRef carries only what survives into the plan; container-ness comes
    # from the role, so `_container_text` markers are not consulted here.
    # Running heads and folios repeat on every page and never belong to the
    # body path. They still need a region (coverage), so each margin band
    # becomes one region that the reading graph emits after the body.
    margin_top = height * 0.08
    margin_bottom = height * 0.92
    # Geometry alone is not enough: body text and section headings reach into
    # the top/bottom band on real pages, and moving them to the end of the page
    # is a content-order error. Only furniture-like roles are treated as margin.
    _furniture_roles = {"noise", "footnote", "frontmatter_noise"}
    margin_refs = [
        ref for ref in boxed
        if (ref.center_y is not None)
        and (ref.center_y < margin_top or ref.center_y > margin_bottom)
        and (ref.role or "") in _furniture_roles
    ]
    margin_uids = {ref.uid for ref in margin_refs}
    content = [ref for ref in boxed if ref.uid not in margin_uids]

    wide = [
        ref for ref in content
        if (ref.bbox[2] - ref.bbox[0]) >= width * 0.75
        and ref.role not in _CONTAINER_ROLES
    ]
    wide.sort(key=order)
    bands: list[tuple[float, float]] = []
    band_top = 0.0
    for ref in wide:
        top, bottom = max(band_top, ref.bbox[1]), min(height, ref.bbox[3])
        if top < ref.bbox[1]:
            bands.append((band_top, ref.bbox[1]))
        elif not bands and band_top == 0.0 and ref.bbox[1] > 0:
            bands.append((0.0, ref.bbox[1]))
        band_top = max(band_top, ref.bbox[3])
    if band_top < height or not bands:
        bands.append((band_top, height))

    # Descriptors keep parent references stable until final reading-order IDs exist.
    entries: list[dict[str, object]] = []
    for ref in wide:
        entries.append(dict(kind=REGION_FULL_WIDTH, left=ref.bbox[0], right=ref.bbox[2],
                            top=ref.bbox[1], bottom=ref.bbox[3], members=(ref.uid,),
                            parent=None, confidence=0.9,
                            evidence=(f"bbox width {ref.bbox[2] - ref.bbox[0]:g} >= 75% page width {width:g}",)))

    # Containers cut their band vertically: a table sitting between two
    # paragraphs must not be emitted after the whole column, or the reading
    # path jumps. Each cut produces a piece that gets its own column split.
    containers_all = [ref for ref in content if ref.role in _CONTAINER_ROLES]
    pieces: list[tuple[float, float]] = []
    for top, bottom in bands:
        cuts = {top, bottom}
        for container in containers_all:
            for edge in (container.bbox[1], container.bbox[3]):
                if top < edge < bottom:
                    cuts.add(edge)
        ordered_cuts = sorted(cuts)
        for lower, upper in zip(ordered_cuts, ordered_cuts[1:], strict=False):
            if upper - lower > 1.0:
                pieces.append((lower, upper))
    if not pieces:
        pieces = list(bands)

    # Every non-wide, non-container block belongs to exactly one piece. OCR
    # emits blocks whose centre falls outside a piece (overlapping a full-width
    # element, or exactly on a boundary), so the nearest piece takes them.
    wide_uids = {ref.uid for ref in wide}
    container_uids = {ref.uid for ref in containers_all}
    piece_for: dict[str, int] = {}
    for ref in content:
        if ref.uid in wide_uids:
            continue
        centre = ref.center_y
        chosen: int | None = None
        for index, (top, bottom) in enumerate(pieces):
            if top <= centre < bottom:
                chosen = index
                break
        if chosen is None:
            chosen = min(
                range(len(pieces)),
                key=lambda index: (
                    0.0 if pieces[index][0] <= centre <= pieces[index][1]
                    else min(abs(centre - pieces[index][0]), abs(centre - pieces[index][1])),
                    index,
                ),
            )
        piece_for[ref.uid] = chosen

    owners: dict[str, dict[str, object]] = {}
    column_entries: list[dict[str, object]] = []
    for piece_index, (top, bottom) in enumerate(pieces):
        members = [
            ref for ref in content
            if piece_for.get(ref.uid) == piece_index and ref.uid not in container_uids
        ]
        centers = sorted((ref.center_x, ref.uid, ref) for ref in members)
        split: int | None = None
        gap = 0.0
        if len(centers) >= 2:
            candidates = [(centers[i + 1][0] - centers[i][0], i + 1) for i in range(len(centers) - 1)]
            gap, split = max(candidates, key=lambda item: (item[0], -item[1]))
            if gap < width * 0.03:
                split = None
        groups = [members]
        confidence = 0.9
        evidence = (f"x-center gutter {gap:g} ({3}% page width {width:g})",)
        if split is not None:
            left_uids = {item[1] for item in centers[:split]}
            right_uids = {item[1] for item in centers[split:]}
            # Two clusters are columns only if their horizontal ranges are
            # (almost) disjoint. A single-column page still yields the largest
            # centre gap between a wide heading and a narrower paragraph, but
            # the two groups then overlap in x almost completely.
            left_span = [min(ref.bbox[0] for ref in members if ref.uid in left_uids),
                         max(ref.bbox[2] for ref in members if ref.uid in left_uids)]
            right_span = [min(ref.bbox[0] for ref in members if ref.uid in right_uids),
                          max(ref.bbox[2] for ref in members if ref.uid in right_uids)]
            overlap = max(0.0, min(left_span[1], right_span[1]) - max(left_span[0], right_span[0]))
            narrowest = max(min(left_span[1] - left_span[0], right_span[1] - right_span[0]), 1.0)
            separated = overlap <= narrowest * 0.2
            if len(left_uids) >= 2 and len(right_uids) >= 2 and separated:
                # Two blocks either side is enough to read column-major: keeping
                # them in one region interleaves the columns by y, which is the
                # one order that is never right for a two-column band.
                groups = [[ref for ref in members if ref.uid in left_uids],
                          [ref for ref in members if ref.uid in right_uids]]
                confidence = 0.75 if min(len(left_uids), len(right_uids)) >= 3 else 0.5
                if confidence < 0.75:
                    evidence += ("two blocks per column; column order assumed",)
            else:
                confidence = 0.5
                evidence += ("gutter clusters below 2-block threshold or overlapping",)
        if not members:
            continue
        for group in groups:
            left = 0.0 if len(groups) == 1 else min(ref.bbox[0] for ref in group)
            right = width if len(groups) == 1 else max(ref.bbox[2] for ref in group)
            entry: dict[str, object] = dict(kind=REGION_COLUMN, left=left, right=right, top=top,
                                            bottom=bottom, members=(), parent=None,
                                            confidence=confidence, evidence=evidence)
            column_entries.append(entry)
            for ref in group:
                owners[ref.uid] = entry

    # A container owns no column membership, but its region still names the
    # column piece it sits in: the geometric nearest one, since the container's
    # own span is cut out of the pieces and may leave an empty piece behind.
    def _column_distance(entry: dict[str, object], container: BlockRef) -> tuple[float, float]:
        cx, cy = container.center_x or 0.0, container.center_y or 0.0
        dx = max(float(entry["left"]) - cx, 0.0, cx - float(entry["right"]))
        dy = max(float(entry["top"]) - cy, 0.0, cy - float(entry["bottom"]))
        return (dy, dx)

    for container in containers_all:
        if not column_entries:
            continue
        owners[container.uid] = min(
            column_entries, key=lambda entry: _column_distance(entry, container)
        )

    # Containers own every eligible intersecting block in their column; nested
    # overlaps resolve to the smallest container so membership stays exclusive.
    containers = containers_all
    container_for: dict[str, BlockRef] = {}
    for ref in containers:
        for candidate in content:
            # A full-width strip is its own region; a container must not take it.
            if candidate.uid in wide_uids:
                continue
            if (ref.bbox[0] - tolerance <= candidate.bbox[0]
                    and candidate.bbox[2] <= ref.bbox[2] + tolerance
                    and ref.bbox[1] - tolerance <= candidate.bbox[1]
                    and candidate.bbox[3] <= ref.bbox[3] + tolerance):
                previous = container_for.get(candidate.uid)
                area = (ref.bbox[2] - ref.bbox[0]) * (ref.bbox[3] - ref.bbox[1])
                previous_area = ((previous.bbox[2] - previous.bbox[0]) *
                                 (previous.bbox[3] - previous.bbox[1])) if previous else float("inf")
                if area < previous_area or (area == previous_area and ref.uid < previous.uid):
                    container_for[candidate.uid] = ref

    for container in containers:
        # A page that is all table (or whose only other blocks are margins and
        # full-width strips) has no column to own the container; the region is
        # still emitted so the block cannot disappear from the plan.
        column = owners.get(container.uid)
        owned = [ref for ref in content if container_for.get(ref.uid) is container]
        entries.append(dict(kind=REGION_CONTAINER, left=container.bbox[0], right=container.bbox[2],
                            top=container.bbox[1], bottom=container.bbox[3],
                            members=tuple(ref.uid for ref in sorted(owned, key=order)),
                            parent=column, confidence=0.9,
                            evidence=(f"container bbox expanded by 2% page width {width:g}",)))

    # A container owns its blocks outright; whichever column region covered them
    # drops them, so membership stays exclusive even for cross-gutter tables.
    for column in column_entries:
        own = [ref.uid for ref in sorted(content, key=order)
               if owners.get(ref.uid) is column
               and ref.uid not in container_for
               and ref.uid not in container_uids]
        column["members"] = tuple(own)
        entries.append(column)

    if margin_refs:
        entries.append(dict(kind=REGION_MARGIN, left=0.0, right=width,
                            top=min(ref.bbox[1] for ref in margin_refs),
                            bottom=max(ref.bbox[3] for ref in margin_refs),
                            members=tuple(ref.uid for ref in sorted(margin_refs, key=order)),
                            parent=None, confidence=0.8,
                            evidence=(f"outside the 8%-92% body band of {height:g}",)))

    missing = [ref for ref in page_refs if ref.bbox is None]
    if missing:
        entries.append(dict(kind=REGION_COLUMN, left=0.0, right=width, top=height, bottom=height,
                            members=tuple(ref.uid for ref in sorted(missing, key=lambda ref: ref.uid)),
                            parent=None, confidence=0.1, evidence=("missing bbox",)))

    entries.sort(key=lambda entry: (entry["top"], entry["left"], entry["kind"], entry["members"]))
    ids = {id(entry): f"p{page}:r{index}" for index, entry in enumerate(entries)}
    return [
        Region(ids[id(entry)], page, entry["kind"], entry["left"], entry["right"],
               entry["top"], entry["bottom"], entry["members"],
               ids.get(id(entry["parent"])) if entry["parent"] is not None else None,
               entry["confidence"], entry["evidence"])
        for entry in entries
    ]
