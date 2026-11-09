"""Figure quality evaluation harness (read-only replay, no vault writes)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_DRYRUN_PATH = ROOT / "scripts" / "dev" / "object_migration_dry_run.py"
_SPEC = importlib.util.spec_from_file_location("object_migration_dry_run", _DRYRUN_PATH)
assert _SPEC and _SPEC.loader
DRY = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(DRY)

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover
    fitz = None
try:
    from PIL import Image, ImageDraw  # type: ignore
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None

VAULT_DEFAULT = Path("D:/L/OB/Literature-hub")
OCR_DEFAULT = None
SET_DIR = ROOT / "docs" / "evidence" / "figure-quality" / "sets"
OUT_ROOT = ROOT / "docs" / "evidence" / "figure-quality"

LABEL_FIELDS = ["key", "figure_id", "page", "expected_owner", "current_assets", "caption_ok",
                "panels_ok", "crop_ok", "delivery_ok", "notes", "reviewer", "reviewed_at"]


def load_set(name: str) -> list[str]:
    path = SET_DIR / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("keys", []))


def reviewed(label: dict[str, Any]) -> bool:
    reviewer = str(label.get("reviewer", "") or "").strip().lower()
    return reviewer not in {"", "unreviewed", "todo", "tbd"}


def filter_reviewed(labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [lb for lb in labels if reviewed(lb)]


def score_association(labels: list[dict[str, Any]], replay_figures: list[dict[str, Any]]) -> dict[str, Any]:
    """Precision/recall of figure->asset association against reviewed labels."""
    by_id = {str(f.get("figure_id")): f for f in replay_figures}
    tp = fp = fn = 0
    for lb in filter_reviewed(labels):
        fid = str(lb.get("figure_id"))
        rf = by_id.get(fid, {})
        replay_assets = {
            str(a.get("block_id")) for a in (rf.get("matched_assets") or [])
            if a.get("block_id") is not None
        }
        expected_raw = lb.get("expected_owner", "")
        if isinstance(expected_raw, (list, tuple)):
            expected = {str(x) for x in expected_raw}
        else:
            expected = {x for x in str(expected_raw).replace(",", " ").split() if x}
        tp += len(replay_assets & expected)
        fp += len(replay_assets - expected)
        fn += len(expected - replay_assets)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
            "f1": (2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) else 1.0}


def score_labels(labels: list[dict[str, Any]], replay: dict[str, Any] | None = None) -> dict[str, Any]:
    """Aggregate scoring; only reviewed rows count for visual metrics."""
    rev = filter_reviewed(labels)
    out = {
        "total_labels": len(labels),
        "reviewed": len(rev),
        "unreviewed": len(labels) - len(rev),
        "crop_failures": sum(1 for lb in rev if lb.get("crop_ok") is False),
        "delivery_failures": sum(1 for lb in rev if lb.get("delivery_ok") is False),
        "caption_failures": sum(1 for lb in rev if lb.get("caption_ok") is False),
        "panel_failures": sum(1 for lb in rev if lb.get("panels_ok") is False),
    }
    if replay is not None:
        out["association"] = score_association(rev, replay.get("figures", []))
    return out


def diff_results(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Per-case fixed/regressed diff between two result JSONs."""
    prev_cases = {c.get("key"): c for c in previous.get("cases", []) if "key" in c}
    curr_cases = {c.get("key"): c for c in current.get("cases", []) if "key" in c}
    fixed = []
    regressed = []
    for key in sorted(set(prev_cases) | set(curr_cases)):
        p = prev_cases.get(key, {})
        c = curr_cases.get(key, {})
        p_ok = p.get("passed", p.get("ok"))
        c_ok = c.get("passed", c.get("ok"))
        if p_ok is False and c_ok is True:
            fixed.append(key)
        elif p_ok is True and c_ok is False:
            regressed.append(key)
    return {"fixed": fixed, "regressed": regressed,
            "fixed_count": len(fixed), "regressed_count": len(regressed)}


def structural_baseline(key: str, dry_entry: dict[str, Any], ocr_root: Path) -> dict[str, Any]:
    ident = dry_entry.get("identity", {})
    new = ident.get("new", {})
    old = ident.get("old", {})
    delivery = dry_entry.get("delivery", {})
    content = dry_entry.get("content", {})
    paper_dir = ocr_root / key
    # count missing manifest files
    # dangling embeds
    dangling = len(delivery.get("embeds_missing_new_id", []) or [])
    unique_ok = (new.get("unique_ids", 0) == new.get("entries", 0)) if new else False
    text_decrease = content.get("new_text_chars", 0) < content.get("old_text_chars", 0) if content else False
    pending = 0
    inv = paper_dir / "structure" / "figure_inventory.json"
    if inv.is_file():
        try:
            d = json.loads(inv.read_text(encoding="utf-8"))
            pending = len(d.get("held_figures", []) or []) + len(d.get("unresolved_clusters", []) or [])
        except Exception:
            pending = 0
    return {
        "key": key,
        "unique_ids_ok": bool(unique_ok),
        "dangling_fulltext_targets": dangling,
        "pending_markers": pending,
        "text_decrease": bool(text_decrease),
        "old_text_chars": content.get("old_text_chars"),
        "new_text_chars": content.get("new_text_chars"),
        "old_entries": old.get("entries"),
        "new_entries": new.get("entries"),
    }


def _render_page_png(pdf_path: Path, page_num: int, out_path: Path, scale: float = 1.0) -> None:
    if fitz is None or Image is None:
        return
    doc = fitz.open(str(pdf_path))
    if page_num - 1 >= len(doc):
        doc.close()
        return
    page = doc[page_num - 1]
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    if img.width > 1000:
        ratio = 1000 / img.width
        img = img.resize((1000, int(img.height * ratio)))
    img.save(out_path, "JPEG", quality=55, optimize=True)
    doc.close()


def _overlay_crop(pdf_path: Path, page_num: int, bbox: list, out_path: Path, scale: float = 1.0) -> None:
    if fitz is None or Image is None:
        return
    doc = fitz.open(str(pdf_path))
    if page_num - 1 >= len(doc):
        doc.close()
        return
    page = doc[page_num - 1]
    mat = fitz.Matrix(scale, scale)
    # crop manually
    full = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [full.width, full.height], full.samples)
    x0, y0, x1, y1 = [int(v * scale) for v in bbox]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.width, x1), min(img.height, y1)
    crop = img.crop((x0, y0, x1, y1))
    crop.save(out_path, "JPEG", quality=55, optimize=True)
    doc.close()


def _vault_ocr_root(vault: Path, ocr_root: Path | None) -> Path:
    return ocr_root if ocr_root else vault / "System" / "PaperForge" / "ocr"


def run_key(vault: Path, ocr_root: Path, key: str, out_dir: Path) -> dict[str, Any]:
    paper_dir = ocr_root / key
    meta = DRY._read_json(paper_dir / "meta.json")
    from paperforge.pdf_resolver import resolve_source_pdf
    pdf = resolve_source_pdf(vault, meta.get("source_pdf"))
    entry = DRY.audit_key(vault, ocr_root, key, plan=False)
    # replay figures
    try:
        new = DRY._new_replay(vault, ocr_root, key)
        replay_figures = new["figures"]
    except Exception as exc:  # noqa: BLE001
        replay_figures = []
        entry["replay_error"] = f"{type(exc).__name__}: {exc}"

    kdir = out_dir / key
    kdir.mkdir(parents=True, exist_ok=True)

    # labels template
    labels_path = kdir / "labels.jsonl"
    if not labels_path.is_file():
        lines = []
        for f in replay_figures:
            asset_ids = [
                str(a.get("block_id")) for a in (f.get("matched_assets") or [])
                if a.get("block_id") is not None
            ]
            row = {
                "key": key,
                "figure_id": str(f.get("figure_id")),
                "page": int(f.get("page", 0) or 0),
                "expected_owner": "",
                "current_assets": " ".join(asset_ids),
                "caption_ok": None,
                "panels_ok": None,
                "crop_ok": None,
                "delivery_ok": None,
                "notes": "",
                "reviewer": "",
                "reviewed_at": "",
            }
            lines.append(json.dumps(row, ensure_ascii=False))
        labels_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    # per-figure crops + page overlays
    if pdf is not None:
        # group figures by page
        pages = sorted({int(f.get("page", 0) or 0) for f in replay_figures if f.get("page")})
        for pg in pages:
            out_path = kdir / f"page_{pg:03d}.jpg"
            if not out_path.is_file():
                _render_page_png(pdf, pg, out_path)
        for f in replay_figures:
            fid = str(f.get("figure_id"))
            pg = int(f.get("page", 0) or 0)
            for ai, a in enumerate(f.get("matched_assets") or []):
                bbox = a.get("bbox")
                if bbox and len(bbox) == 4:
                    crop_path = kdir / f"{fid}_asset{ai}.jpg"
                    if not crop_path.is_file():
                        import contextlib
                        with contextlib.suppress(Exception):
                            _overlay_crop(pdf, pg, bbox, crop_path)

    baseline = structural_baseline(key, entry, ocr_root)
    (kdir / "baseline.json").write_text(
        json.dumps({"dry_run": entry, "structural": baseline}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    case_result = {
        "key": key,
        "passed": not (
            entry.get("error") or baseline.get("text_decrease") or baseline.get("dangling_fulltext_targets")
        ),
        "figures": len(replay_figures),
        "structural": baseline,
    }
    return {"key": key, "entry": entry, "baseline": baseline, "case": case_result, "out_dir": str(kdir)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", default=str(VAULT_DEFAULT))
    parser.add_argument("--ocr-root", default="")
    parser.add_argument("--keys", nargs="*", default=[])
    parser.add_argument("--set", dest="set_name", default="")
    parser.add_argument("--out", default="", help="output root (default docs/evidence/figure-quality/<set>)")
    parser.add_argument("--score", action="store_true", help="scoring mode: read labels and previous result")
    parser.add_argument("--previous", default="", help="previous result JSON for diff")
    parser.add_argument("--result-out", default="", help="write result JSON")
    args = parser.parse_args()

    vault = Path(args.vault)
    ocr_root = Path(args.ocr_root) if args.ocr_root else vault / "System" / "PaperForge" / "ocr"

    keys = list(args.keys)
    if args.set_name:
        keys = keys + load_set(args.set_name)
    keys = sorted(set(keys))

    set_name = args.set_name or "adhoc"
    out_root = Path(args.out) if args.out else (OUT_ROOT / set_name)
    out_root.mkdir(parents=True, exist_ok=True)

    cases = []
    baselines = []
    for key in keys:
        r = run_key(vault, ocr_root, key, out_root)
        cases.append(r["case"])
        baselines.append(r["baseline"])

    result = {
        "set": set_name,
        "keys": keys,
        "cases": cases,
        "baselines": baselines,
        "totals": {
            "papers": len(keys),
            "passed": sum(1 for c in cases if c.get("passed")),
            "failed": sum(1 for c in cases if not c.get("passed")),
        },
    }

    # scoring from labels
    score_summary = {}
    for key in keys:
        kdir = out_root / key
        lp = kdir / "labels.jsonl"
        labels = []
        if lp.is_file():
            labels = [json.loads(line) for line in lp.read_text(encoding="utf-8").splitlines() if line.strip()]
        # replay figures
        try:
            new = DRY._new_replay(vault, ocr_root, key)
            rf = new["figures"]
        except Exception:
            rf = []
        sc = score_labels(labels, {"figures": rf})
        score_summary[key] = sc
    result["scores"] = score_summary

    if args.previous:
        try:
            prev = json.loads(Path(args.previous).read_text(encoding="utf-8"))
            result["diff"] = diff_results(prev, result)
        except Exception as exc:  # noqa: BLE001
            result["diff_error"] = f"{type(exc).__name__}: {exc}"

    out_path = Path(args.result_out) if args.result_out else (out_root / "result.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result["totals"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
