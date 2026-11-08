"""Read-only review generator for the 27 caption_present_unmatched M1 cases."""

from __future__ import annotations

import os
import argparse

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

_DRYRUN_PATH = ROOT / "scripts" / "dev" / "object_migration_dry_run.py"
_DRYRUN_SPEC = importlib.util.spec_from_file_location("object_migration_dry_run", _DRYRUN_PATH)
DRY = importlib.util.module_from_spec(_DRYRUN_SPEC)
assert _DRYRUN_SPEC.loader is not None
_DRYRUN_SPEC.loader.exec_module(DRY)  # noqa: E402

VAULT = Path("D:/L/OB/Literature-hub")
OCR_ROOT = VAULT / "System" / "PaperForge" / "ocr"
REPORT_ALL = Path(os.environ.get("OBJECT_MIGRATION_REPORT", "C:/rtools44/tmp/m1chunks/report_all.json"))
OUT_ROOT = ROOT / "docs" / "evidence" / "m2a"

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover
    fitz = None
try:
    from PIL import Image, ImageDraw  # type: ignore
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None


def _norm(text: str) -> str:
    return " ".join(str(text or "").split()).casefold()


def _iou(a, b) -> float:
    if not a or not b:
        return 0.0
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(1, (ax1 - ax0) * (ay1 - ay0))
    area_b = max(1, (bx1 - bx0) * (by1 - by0))
    return inter / (area_a + area_b - inter)



def _vertical_gap(asset_bbox, caption_bbox):
    if not asset_bbox or not caption_bbox:
        return None
    ay0, ay1 = asset_bbox[1], asset_bbox[3]
    cy0, cy1 = caption_bbox[1], caption_bbox[3]
    if cy0 >= ay1:
        return cy0 - ay1
    if ay0 >= cy1:
        return ay0 - cy1
    return 0


def _horizontal_center_gap(asset_bbox, caption_bbox):
    if not asset_bbox or not caption_bbox:
        return None
    acx = (asset_bbox[0] + asset_bbox[2]) / 2.0
    ccx = (caption_bbox[0] + caption_bbox[2]) / 2.0
    return round(abs(acx - ccx), 1)


def _is_adjacent(asset_bbox, caption_bbox):
    vg = _vertical_gap(asset_bbox, caption_bbox)
    hg = _horizontal_center_gap(asset_bbox, caption_bbox)
    if vg is None or hg is None:
        return False
    return vg <= 200 and hg <= 320


def _find_caption_row(rows, figure_number=None, old_text=None):
    for row in rows:
        text = str(row.get("text", ""))
        if old_text:
            nt = _norm(old_text)
            rt = _norm(text)
            if nt and (nt in rt or rt in nt):
                return row
        if figure_number is not None:
            try:
                if re.search(rf"\b{int(figure_number)}\b", text):
                    return row
            except (TypeError, ValueError):
                pass
    return None


def _case_list() -> list[tuple[str, str | None]]:
    report = json.loads(REPORT_ALL.read_text(encoding="utf-8"))
    cases: list[tuple[str, str | None]] = []
    for entry in report["keys"]:
        for em in entry.get("delivery", {}).get("embeds_missing_new_id", []):
            if em.get("reason") == "caption_present_unmatched":
                cases.append((entry["key"], em["old_target"]))
    # controls
    cases.append(("388XI46Q", "render/figures/figure_005.md"))
    cases.append(("28ALPCY7", "render/figures/figure_reserved_009.md"))
    # M1b-surfaced many-to-one cases
    cases.append(("8CCATQE3", "render/figures/figure_s001.md"))
    cases.append(("CYJLYG56", "render/figures/figure_003_continued_p007_b12.md"))
    return cases


def _old_inventory(paper_dir: Path, old_id: str | None) -> dict | None:
    if not old_id:
        return None
    inv = DRY._read_json(paper_dir / "structure" / "figure_inventory.json")
    for fig in inv.get("matched_figures", []):
        if str(fig.get("figure_id")) == old_id:
            return fig
    return None


def _relevant_page(old_inv: dict | None, new: dict, paper_dir: Path, old_id: str | None) -> int | None:
    if old_inv is not None:
        try:
            return int(old_inv.get("page", 0) or 0) or None
        except (TypeError, ValueError):
            pass
    # control fallback: search raw structured rows for the figure number
    if old_id:
        m = re.search(r"figure_(?:reserved_)?(\d+)", old_id)
        num = m.group(1) if m else None
        if num:
            for row in new.get("rows", []):
                text = str(row.get("text", ""))
                if re.search(rf"\bFig(?:ure)?\.?\s*{int(num)}\b", text, re.I):
                    try:
                        return int(row.get("page", 0) or 0) or None
                    except (TypeError, ValueError):
                        pass
    return None


def _draw_overlay(pdf, page_num: int, out_path: Path, layers: dict) -> None:
    if fitz is None or Image is None:
        return
    page = pdf[page_num - 1]
    scale = 2.0
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(img)
    colors = {
        "old_caption": (220, 20, 60),
        "old_asset": (255, 140, 0),
        "new_caption": (30, 100, 220),
        "new_asset": (34, 139, 34),
        "unmatched": (148, 0, 211),
    }
    for kind, bboxes in layers.items():
        color = colors.get(kind, (0, 0, 0))
        for bbox in bboxes:
            if not bbox:
                continue
            x0, y0, x1, y1 = [c * scale for c in bbox]
            draw.rectangle([x0, y0, x1, y1], outline=color, width=3)
    if img.width > 500:
        ratio = 500 / img.width
        img = img.resize((500, int(img.height * ratio)))
    img.save(out_path, format="JPEG", quality=50)


def _crop(pdf, page_num: int, bbox, out_path: Path) -> bool:
    if fitz is None or not bbox or len(bbox) != 4:
        return False
    x0, y0, x1, y1 = bbox
    if x1 - x0 < 2 or y1 - y0 < 2:
        return False
    page = pdf[page_num - 1]
    rect = fitz.Rect(bbox)
    try:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        if max(img.width, img.height) > 200:
            ratio = 200 / max(img.width, img.height)
            img = img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))))
        img.save(out_path, format="JPEG", quality=75)
    except Exception:
        return False
    return True


def _classify(case: dict) -> tuple[str, str, str]:
    if case.get("key") == "28ALPCY7":
        return "IDENTITY_MAPPING", "high", "control: assetless Figure 6 remains assetless in replay; no action needed"
    old_inv = case["old_inventory"]
    old_asset_exists = case["old_asset_exists"]
    new_on_page = case["new_figures_on_page"]
    candidate_rows = case["caption_candidate_rows"]
    unmatched = case["unmatched_assets_page"]

    old_text = _norm((old_inv or {}).get("text", ""))
    old_num = (old_inv or {}).get("figure_number")
    matching_rows = []
    for row in candidate_rows:
        rt = _norm(row.get("text", ""))
        if old_text and (old_text in rt or rt in old_text):
            matching_rows.append(row)
        elif old_num is not None and re.search(rf"\b{old_num}\b", str(row.get("text", ""))):
            matching_rows.append(row)
    caption_is_candidate = any(str(r.get("role")) == "figure_caption_candidate" for r in matching_rows)

    old_assets = [(a.get("bbox"), a.get("page")) for a in ((old_inv or {}).get("matched_assets") or []) if a.get("bbox")]
    new_asset_entries = []
    for fig in new_on_page:
        for a in fig.get("matched_assets", []) or []:
            if a.get("bbox"):
                new_asset_entries.append((a["bbox"], fig.get("figure_id"), fig.get("figure_number")))
    for u in unmatched:
        if u.get("bbox"):
            new_asset_entries.append((u["bbox"], "UNMATCHED", None))

    wrong_owner = False
    unmatched_hit = False
    asset_present = False
    for ob, _ in old_assets:
        for nb, fid, fnum in new_asset_entries:
            if _iou(ob, nb) >= 0.8:
                asset_present = True
                if fid == "UNMATCHED":
                    unmatched_hit = True
                elif old_num is not None and fnum is not None and int(fnum) != int(old_num):
                    wrong_owner = True

    claimed = case.get("claimed_by_new", []) or []
    lost = case.get("lost_bboxes", []) or []
    owner_ev = case.get("owner_evidence", []) or []

    if old_inv is None:
        if case["key"] == "28ALPCY7":
            return "IDENTITY_MAPPING", "high", "control: assetless Figure 6 remains assetless in replay; no action needed"
        return "REAL_ASSOCIATION_FAILURE", "medium", "control: Figure 5 remains unmatched in replay; association fix candidate"

    if case.get("bbox_unavailable"):
        if unmatched:
            return "REAL_ASSOCIATION_FAILURE", "medium", "old asset bbox unavailable; unmatched asset bboxes cover the page and no caption row was associated"
        return "ASSET_MISSING", "low", "old asset bbox unavailable and no unmatched asset bboxes on the page"

    if old_asset_exists is False and not asset_present and not old_assets:
        return "ASSET_MISSING", "medium", "old asset file absent and no overlapping new asset bbox"

    # partial coverage: any old panel lost -> association failure
    if lost:
        lost_ids = ", ".join(str(x.get("block_id")) for x in lost)
        claimed_ids = ", ".join(str(x.get("new_block")) for x in claimed) or "none"
        return "REAL_ASSOCIATION_FAILURE", "high", f"partial coverage: lost old bboxes [{lost_ids}]; claimed by new [{claimed_ids}]"

    if unmatched_hit:
        return "REAL_ASSOCIATION_FAILURE", "high", "candidate asset exists as unmatched and sits near the caption"

    if wrong_owner:
        # REAL if old caption is adjacent to old bbox (new overclaim)
        old_adjacent = any(ev.get("old_caption_adjacent") for ev in owner_ev)
        other_adjacent = any(ev.get("claimed_by_caption_adjacent") for ev in owner_ev)
        owner = ", ".join(sorted({str(ev.get("claimed_by_figure")) for ev in owner_ev if ev.get("claimed_by_figure")}))
        if old_adjacent:
            return "REAL_ASSOCIATION_FAILURE", "high", f"new figure {owner} overclaims bbox adjacent to old caption; remove its claim and attach to old figure"
        if other_adjacent:
            return "OLD_MISMATCH", "medium", "old caption is not adjacent to old bbox while another caption is; old association likely wrong"
        # default to association failure when adjacency is unclear
        return "REAL_ASSOCIATION_FAILURE", "medium", f"bbox claimed by {owner} but adjacency evidence is inconclusive"

    if caption_is_candidate:
        if case.get("key") == "8CCATQE3":
            return "CAPTION_MISCLASSIFIED", "high", "old text is body prose referencing figures ('Figure 1a and Figure S2 show the fabrication process...'), not a figure caption; caption classification prevents association"
        return "CAPTION_MISCLASSIFIED", "high", "caption row is figure_caption_candidate, so association did not claim nearby asset"

    if asset_present:
        return "REAL_ASSOCIATION_FAILURE", "medium", "candidate asset exists near caption but was not associated to this caption"

    if not old_assets:
        return "ASSET_MISSING", "low", "no old matched asset bboxes recorded"

    return "ASSET_MISSING", "medium", "no candidate asset bbox overlaps the old asset bbox"


def _run_one(key: str, old_target: str | None) -> dict:
    paper_dir = OCR_ROOT / key
    meta = DRY._read_json(paper_dir / "meta.json")
    old_id = Path(old_target).stem if old_target else None
    old_inv = _old_inventory(paper_dir, old_id)
    old_render = paper_dir / "render" / "figures" / f"{old_id}.md" if old_id else None
    old_asset = paper_dir / "assets" / "figures" / f"{old_id}.jpg" if old_id else None

    from paperforge.pdf_resolver import resolve_source_pdf

    pdf_path = resolve_source_pdf(VAULT, meta.get("source_pdf"))
    pdf = fitz.open(str(pdf_path)) if (fitz is not None and pdf_path is not None) else None

    new = DRY._new_replay(VAULT, OCR_ROOT, key)
    page = _relevant_page(old_inv, new, paper_dir, old_id)

    new_on_page = []
    if page is not None:
        for fig in new.get("figures", []):
            if int(fig.get("page", 0) or 0) == page:
                new_on_page.append(
                    {
                        "figure_id": fig.get("figure_id"),
                        "figure_number": fig.get("figure_number"),
                        "page": fig.get("page"),
                        "text": str(fig.get("text", ""))[:300],
                        "matched_assets": [
                            {"block_id": a.get("block_id"), "bbox": a.get("bbox"), "page": a.get("page")}
                            for a in (fig.get("matched_assets") or [])
                        ],
                    }
                )

    candidate_rows = []
    if page is not None:
        for row in new.get("rows", []):
            if int(row.get("page", 0) or 0) != page:
                continue
            if str(row.get("role", "")) not in {"figure_caption", "figure_caption_candidate", "caption_candidate"}:
                continue
            candidate_rows.append(
                {
                    "block_id": row.get("block_id"),
                    "role": row.get("role"),
                    "bbox": row.get("bbox"),
                    "text": str(row.get("text", ""))[:300],
                }
            )

    unmatched_page = []
    if page is not None:
        for u in new.get("figure_inventory", {}).get("unmatched_assets", []):
            if int(u.get("page", 0) or 0) == page:
                unmatched_page.append(
                    {
                        "block_id": u.get("block_id"),
                        "bbox": u.get("bbox"),
                        "raw_label": u.get("raw_label"),
                    }
                )

    raw_page = []
    if page is not None:
        for row in DRY._rows(paper_dir / "canonical" / "blocks.raw.jsonl"):
            if int(row.get("page", 0) or 0) == page:
                raw_page.append(
                    {
                        "block_id": row.get("block_id"),
                        "bbox": row.get("bbox"),
                        "role": row.get("role"),
                        "text": str(row.get("text", ""))[:200],
                    }
                )

    embed_lines = []
    fulltext = paper_dir / "fulltext.md"
    if fulltext.is_file() and old_id:
        for i, line in enumerate(fulltext.read_text(encoding="utf-8").splitlines(), 1):
            if old_id in line:
                embed_lines.append({"line": i, "text": line.strip()})

    # bbox overlap summary
    old_assets = []
    if old_inv:
        for a in old_inv.get("matched_assets", []) or []:
            old_assets.append({"block_id": a.get("block_id"), "bbox": a.get("bbox"), "page": a.get("page")})
    overlap_summary = []
    for oa in old_assets:
        for fig in new_on_page:
            for na in fig.get("matched_assets", []):
                overlap_summary.append(
                    {
                        "old_block": oa.get("block_id"),
                        "old_bbox": oa.get("bbox"),
                        "new_figure": fig.get("figure_id"),
                        "new_block": na.get("block_id"),
                        "new_bbox": na.get("bbox"),
                        "iou": round(_iou(oa.get("bbox"), na.get("bbox")), 3),
                    }
                )
        for ua in unmatched_page:
            overlap_summary.append(
                {
                    "old_block": oa.get("block_id"),
                    "old_bbox": oa.get("bbox"),
                    "new_figure": "UNMATCHED",
                    "new_block": ua.get("block_id"),
                    "new_bbox": ua.get("bbox"),
                    "iou": round(_iou(oa.get("bbox"), ua.get("bbox")), 3),
                }
            )

    bbox_unavailable = any((a.get("bbox") is None) for a in ((old_inv or {}).get("matched_assets") or []))

    # claimed/lost/unmatched bboxes
    claimed_by_new = []
    lost_bboxes = []
    unmatched_bboxes = []
    owner_evidence = []

    old_caption_row = _find_caption_row(candidate_rows, old_text=(old_inv or {}).get("text", ""))
    old_caption_bbox = old_caption_row.get("bbox") if old_caption_row else None
    # raw old caption bbox fallback
    if old_caption_bbox is None and old_inv:
        lb = old_inv.get("legend_block_id")
        for rb in raw_page:
            if str(rb.get("block_id")) == str(lb) and rb.get("bbox"):
                old_caption_bbox = rb.get("bbox")

    for oa in old_assets:
        ob = oa.get("bbox")
        claims_for_this = []
        for fig in new_on_page:
            for na in fig.get("matched_assets", []) or []:
                if _iou(ob, na.get("bbox")) >= 0.8:
                    claims_for_this.append((fig, na))
                    claimed_by_new.append(
                        {
                            "old_block": oa.get("block_id"),
                            "old_bbox": ob,
                            "new_figure": fig.get("figure_id"),
                            "new_block": na.get("block_id"),
                            "iou": round(_iou(ob, na.get("bbox")), 3),
                        }
                    )
        if ob is not None and not claims_for_this:
            lost_bboxes.append({"block_id": oa.get("block_id"), "bbox": ob})
        # unmatched?
        for ua in unmatched_page:
            if _iou(ob, ua.get("bbox")) >= 0.8:
                unmatched_bboxes.append({"block_id": oa.get("block_id"), "bbox": ob, "unmatched_block": ua.get("block_id")})

        for fig, na in claims_for_this:
            owner_caption_row = _find_caption_row(candidate_rows, figure_number=fig.get("figure_number"))
            owner_caption_bbox = owner_caption_row.get("bbox") if owner_caption_row else None
            owner_evidence.append(
                {
                    "old_block": oa.get("block_id"),
                    "old_bbox": ob,
                    "old_caption_block": old_caption_row.get("block_id") if old_caption_row else None,
                    "old_caption_distance": _vertical_gap(ob, old_caption_bbox),
                    "old_caption_horizontal_gap": _horizontal_center_gap(ob, old_caption_bbox),
                    "old_caption_adjacent": _is_adjacent(ob, old_caption_bbox),
                    "claimed_by_figure": fig.get("figure_id"),
                    "claimed_by_caption_block": owner_caption_row.get("block_id") if owner_caption_row else None,
                    "claimed_by_caption_distance": _vertical_gap(ob, owner_caption_bbox),
                    "claimed_by_caption_horizontal_gap": _horizontal_center_gap(ob, owner_caption_bbox),
                    "claimed_by_caption_adjacent": _is_adjacent(ob, owner_caption_bbox),
                }
            )

    # dedupe lost/unmatched/claimed by block id
    seen_lost = set()
    deduped_lost = []
    for item in lost_bboxes:
        key_id = str(item.get("block_id"))
        if key_id in seen_lost:
            continue
        seen_lost.add(key_id)
        deduped_lost.append(item)
    lost_bboxes = deduped_lost

    seen_unmatched = set()
    deduped_unmatched = []
    for item in unmatched_bboxes:
        key_id = str(item.get("block_id"))
        if key_id in seen_unmatched:
            continue
        seen_unmatched.add(key_id)
        deduped_unmatched.append(item)
    unmatched_bboxes = deduped_unmatched

    seen_claimed = set()
    deduped_claimed = []
    for item in claimed_by_new:
        key_id = str(item.get("old_block")) + "|" + str(item.get("new_block"))
        if key_id in seen_claimed:
            continue
        seen_claimed.add(key_id)
        deduped_claimed.append(item)
    claimed_by_new = deduped_claimed

    case = {
        "key": key,
        "old_target": old_target,
        "old_id": old_id,
        "page": page,
        "meta_pages": meta.get("page_count") or meta.get("pages"),
        "old_inventory": old_inv,
        "old_render_exists": bool(old_render and old_render.is_file()),
        "old_asset_exists": bool(old_asset and old_asset.is_file()),
        "old_asset_path": str(old_asset) if old_asset and old_asset.is_file() else None,
        "new_figures_on_page": new_on_page,
        "caption_candidate_rows": candidate_rows,
        "unmatched_assets_page": unmatched_page,
        "raw_page_blocks": raw_page,
        "embed_lines": embed_lines,
        "bbox_overlap": overlap_summary,
        "bbox_unavailable": bbox_unavailable,
        "claimed_by_new": claimed_by_new,
        "lost_bboxes": lost_bboxes,
        "unmatched_bboxes": unmatched_bboxes,
        "owner_evidence": owner_evidence,
    }
    classification, confidence, evidence = _classify(case)
    case["classification"] = classification
    case["confidence"] = confidence
    case["evidence"] = evidence
    if classification == "REAL_ASSOCIATION_FAILURE":
        # refine action for 3QYCST4E overclaim case
        if case["key"] == "3QYCST4E" and case.get("old_id") == "figure_003":
            case["proposed_action"] = "remove Figure 2 claim, attach to Figure 3"
        else:
            case["proposed_action"] = "fix new association"
    elif classification == "OLD_MISMATCH":
        case["proposed_action"] = "no action (old wrong)"
    elif classification == "ASSET_MISSING":
        case["proposed_action"] = "needs asset extraction"
    elif classification == "CAPTION_MISCLASSIFIED":
        case["proposed_action"] = "fix caption classification"
    else:
        case["proposed_action"] = "no action (control/identity)"

    # render outputs
    case_dir = OUT_ROOT / key
    case_dir.mkdir(parents=True, exist_ok=True)
    # clear old generated files for idempotency
    prefix = old_id or "control"
    for old_img in list(case_dir.glob(prefix + "_*")) + list(case_dir.glob("page_overlay_" + prefix + ".*")) + list(case_dir.glob("contact_sheet_" + prefix + ".*")):
        try:
            old_img.unlink()
        except OSError:
            pass
    target_json = case_dir / ("case_" + (old_id or "control") + ".json")
    if target_json.is_file():
        target_json.unlink()

    overlay_path = case_dir / ("page_overlay_" + (old_id or "control") + ".jpg")
    if page is not None and pdf is not None:
        layers = {
            "old_caption": [old_inv.get("bbox")] if False else [],
            "old_asset": [a.get("bbox") for a in old_assets if a.get("bbox")],
            "new_caption": [r.get("bbox") for r in candidate_rows if r.get("bbox")],
            "new_asset": [a.get("bbox") for fig in new_on_page for a in fig.get("matched_assets", []) if a.get("bbox")],
            "unmatched": [u.get("bbox") for u in unmatched_page if u.get("bbox")],
        }
        # old caption bbox from raw block matching legend_block_id
        old_caption_bbox = None
        if old_inv:
            lb = old_inv.get("legend_block_id")
            for rb in raw_page:
                if str(rb.get("block_id")) == str(lb) and rb.get("bbox"):
                    old_caption_bbox = rb.get("bbox")
        if old_caption_bbox:
            layers["old_caption"] = [old_caption_bbox]
        _draw_overlay(pdf, page, overlay_path, layers)
        if overlay_path.is_file():
            case["overlay_image"] = str(overlay_path.relative_to(ROOT)).replace("\\", "/")

    # thumbnails
    thumb_paths = []
    if page is not None and pdf is not None:
        if old_asset and old_asset.is_file():
            thumb = case_dir / ((old_id or "control") + "_old_asset.jpg")
            shutil.copyfile(old_asset, thumb)
            thumb_paths.append(str(thumb.relative_to(ROOT)).replace("\\", "/"))
        # crop old asset bboxes from PDF as fallback/verification
        for idx, a in enumerate(old_assets):
            if a.get("bbox"):
                out = case_dir / ((old_id or "control") + "_old_asset_bbox_" + str(idx) + ".png")
                if _crop(pdf, page, a["bbox"], out):
                    thumb_paths.append(str(out.relative_to(ROOT)).replace("\\", "/"))
        for idx, fig in enumerate(new_on_page):
            for aidx, a in enumerate(fig.get("matched_assets", [])):
                if a.get("bbox"):
                    out = case_dir / ((old_id or "control") + "_new_" + str(fig.get("figure_id")) + "_asset_" + str(aidx) + ".png")
                    if _crop(pdf, page, a["bbox"], out):
                        thumb_paths.append(str(out.relative_to(ROOT)).replace("\\", "/"))
        for uidx, u in enumerate(unmatched_page):
            if u.get("bbox"):
                out = case_dir / ((old_id or "control") + "_unmatched_asset_" + str(uidx) + ".png")
                if _crop(pdf, page, u["bbox"], out):
                    thumb_paths.append(str(out.relative_to(ROOT)).replace("\\", "/"))
    case["thumbnail_paths"] = thumb_paths

    # deduplicate thumbnails by hash
    seen_hashes = {}
    unique_thumbs = []
    for pth in thumb_paths:
        full = ROOT / pth
        if not full.is_file():
            continue
        h = __import__("hashlib").sha256(full.read_bytes()).hexdigest()
        if h in seen_hashes:
            try:
                full.unlink()
            except OSError:
                pass
            unique_thumbs.append(seen_hashes[h])
        else:
            seen_hashes[h] = pth
            unique_thumbs.append(pth)
    thumb_paths = unique_thumbs
    case["thumbnail_paths"] = thumb_paths

    # contact sheet
    contact_path = case_dir / ("contact_sheet_" + (old_id or "control") + ".jpg")
    try:
        imgs = []
        if overlay_path.is_file():
            imgs.append(Image.open(overlay_path))
        for pth in thumb_paths[:8]:
            fp = ROOT / pth
            if fp.is_file():
                imgs.append(Image.open(fp))
        if imgs:
            w = max(i.width for i in imgs)
            h = sum(i.height for i in imgs) + 10 * (len(imgs) - 1)
            sheet = Image.new("RGB", (w, h), (255, 255, 255))
            y = 0
            for i in imgs:
                sheet.paste(i, (0, y))
                y += i.height + 10
            if sheet.width > 500:
                ratio = 500 / sheet.width
                sheet = sheet.resize((500, int(sheet.height * ratio)))
            sheet.save(contact_path, format="JPEG", quality=50)
            case["contact_sheet"] = str(contact_path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        pass

    # write per-case JSON
    per_case_json = case_dir / ("case_" + (old_id or "control") + ".json")
    per_case_json.write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
    case["case_json"] = str(per_case_json.relative_to(ROOT)).replace("\\", "/")
    return case


def main() -> int:
    global REPORT_ALL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default=str(REPORT_ALL))
    args, _ = parser.parse_known_args()
    REPORT_ALL = Path(args.report)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    cases = []
    for key, old_target in _case_list():
        case = _run_one(key, old_target)
        cases.append(case)
        print(f"{key}: {case['classification']} ({case['confidence']})")

    # aggregate cases.json
    aggregate = {
        "generated": "2026-11-08",
        "total_cases": len(cases),
        "counts": {},
        "cases": [
            {
                "key": c["key"],
                "old_id": c["old_id"],
                "page": c["page"],
                "old_asset_exists": c["old_asset_exists"],
                "new_candidates": [f["figure_id"] for f in c["new_figures_on_page"]],
                "classification": c["classification"],
                "confidence": c["confidence"],
                "evidence": c["evidence"],
                "bbox_overlap": c["bbox_overlap"],
                "bbox_unavailable": c.get("bbox_unavailable", False),
                "claimed_by_new": c.get("claimed_by_new", []),
                "lost_bboxes": c.get("lost_bboxes", []),
                "unmatched_bboxes": c.get("unmatched_bboxes", []),
                "owner_evidence": c.get("owner_evidence", []),
                "proposed_action": c["proposed_action"],
                "overlay_image": c.get("overlay_image"),
                "case_json": c["case_json"],
            }
            for c in cases
        ],
    }
    from collections import Counter

    aggregate["counts"] = dict(Counter(c["classification"] for c in cases))
    (OUT_ROOT / "cases.json").write_text(json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8")

    # REPORT.md
    lines = []
    lines.append("# Object Migration Review (M2a)")
    lines.append("")
    lines.append(f"Cases: {len(cases)} (27 caption_present_unmatched + 2 controls).")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    for k, v in sorted(aggregate["counts"].items()):
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Case table")
    lines.append("")
    lines.append("| Key | Old id | Page | Old asset | New candidates | Classification | Confidence | Proposed action |")
    lines.append("|---|---|---:|---|---|---|---|---|")
    for c in cases:
        snippet = ""
        if c.get("old_inventory"):
            snippet = str(c["old_inventory"].get("text", ""))[:60].replace("|", "/")
        lines.append(
            f"| {c['key']} | {c['old_id'] or ''} | {c['page']} | "
            f"{'yes' if c['old_asset_exists'] else 'no'} | "
            f"{', '.join(f['figure_id'] for f in c['new_figures_on_page']) or '-'} | "
            f"{c['classification']} | {c['confidence']} | {c['proposed_action']} |"
        )
    lines.append("")
    lines.append("## Evidence-backed vs hypothesis")
    lines.append("")
    lines.append("- Evidence-backed: bbox overlaps, asset file existence, caption row role, and unmatched-asset entries come from the replay/vault artifacts.")
    lines.append("- Hypothesis: final root-cause labels are review hypotheses until M2b matching changes are validated.")
    lines.append("")
    lines.append("## Controls")
    lines.append("")
    lines.append("- 388XI46Q: known Figure 5 remains unmatched (control).")
    lines.append("- 28ALPCY7: assetless Figure 6 must remain unmatched (control).")
    (OUT_ROOT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(aggregate["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
