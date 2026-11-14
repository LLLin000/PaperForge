from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
REVIEW_FIELDS = ("caption_ok", "panels_ok", "crop_ok", "delivery_ok")
BINDING_FIELDS = ("snapshot_fingerprint", "source_pdf_sha256", "asset_sha256", "render_sha256", "fulltext_sha256")
IDENTITY_FIELDS = ("key", "kind", "figure_id", "page", "block_id")
LABEL_SCHEMA = ("key", "kind", "figure_id", "page", "block_id", "expected_owner", "current_assets", *BINDING_FIELDS, *REVIEW_FIELDS, "reviewer", "reviewed_at", "notes")


def read_labels(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []


def inline_image(path: Path) -> str | None:
    if not path.is_file():
        return None
    with Image.open(path) as im:
        im.thumbnail((900, 900))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="JPEG", quality=65)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def build(census_path: Path, sample_path: Path, pack: Path, work_root: Path, out: Path, batch_count: int) -> dict:
    census = json.loads(census_path.read_text(encoding="utf-8"))
    papers = {p["key"]: p for p in census["papers"]}
    keys = json.loads(sample_path.read_text(encoding="utf-8"))["selected_keys"]
    missing_keys = sorted(set(keys) - papers.keys())
    if missing_keys:
        raise ValueError(f"sample keys absent from census: {missing_keys}")
    # Pack is retained as an explicit input to make this review surface bound to that run.
    pack_index = json.loads((pack / "index.json").read_text(encoding="utf-8"))
    _ = pack_index
    rows, zero = [], []
    for key in keys:
        paper = papers[key]
        rebuilt = paper.get("rebuilt_state") or {}
        snap = Path(rebuilt.get("snapshot_path") or "")
        evidence_dir = Path(paper.get("evidence_dir") or census_path.parent / key)
        labels = read_labels(evidence_dir / "labels.jsonl")
        if not labels:
            zero.append(key)
        delivery = ((rebuilt.get("delivery") or {}).get("figures") or {})
        for label in labels:
            fid = label.get("figure_id") or ""
            fig = delivery.get(fid) or {}
            crop_path = snap / str(fig.get("asset_path") or "") if label.get("kind") == "matched_figure" and fig.get("asset_path") else None
            render_path = snap / str(fig.get("render_path") or "") if label.get("kind") == "matched_figure" and fig.get("render_path") else None
            page_path = work_root / key / "review_context" / f"page_{int(label.get('page') or 0):03d}.jpg"
            crop_uri = inline_image(crop_path) if crop_path else None
            page_uri = inline_image(page_path)
            missing = []
            if label.get("kind") == "matched_figure" and not crop_uri:
                missing.append("crop")
            if not page_uri:
                missing.append("page preview")
            render = render_path.read_text(encoding="utf-8", errors="replace") if render_path and render_path.is_file() else ""
            if label.get("kind") == "unmatched_legend":
                full = snap / "fulltext.md"
                if full.is_file():
                    render = "\n".join(line for line in full.read_text(encoding="utf-8", errors="replace").splitlines() if "render/figures/" in line and (f"page={label.get('page')}" in line or f"page {label.get('page')}" in line))
            row = {"label": label, "paper": paper, "figure": fig, "crop_uri": crop_uri, "page_uri": page_uri, "render": render, "missing": missing}
            rows.append(row)
    rows.sort(key=lambda r: (0 if (r["paper"].get("historical_state") or {}).get("census_status") == "UNEXPECTED" else 1, 0 if (r["figure"].get("state") != "RESOLVED") else 1, str(r["label"].get("key", "")), int(r["label"].get("page") or 0), str(r["label"].get("figure_id") or ""), str(r["label"].get("block_id") or "")))
    batch_count = max(1, batch_count)
    batches = [rows[i * len(rows) // batch_count:(i + 1) * len(rows) // batch_count] for i in range(batch_count)]
    out.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    for n, batch in enumerate(batches, 1):
        cards = []
        for index, item in enumerate(batch):
            label, fig = item["label"], item["figure"]
            ident = f"r{n}-{index}"
            parts = [f'<article class="row" data-id="{ident}" data-evidence-complete="{str(not item["missing"]).lower()}">', f'<h2>{esc(label.get("key"))} — {esc(label.get("kind"))} — {"figure " + esc(label.get("figure_id")) if label.get("figure_id") else "legend block " + esc(label.get("block_id"))} — page {esc(label.get("page"))}</h2>', f'<p>Delivery: {esc(fig.get("state", "N/A"))}; reasons: {esc(json.dumps(fig.get("reasons", []), ensure_ascii=False))}</p>']
            for what in item["missing"]:
                parts.append(f'<p class="missing">evidence missing: {esc(what)}</p>')
            for name, uri in (("Crop", item["crop_uri"]), ("Page preview", item["page_uri"])):
                if uri:
                    parts.append(f'<h3>{name}</h3><img src="{uri}" alt="{name}">')
            parts.extend([f'<p>asset_sha256: {esc(label.get("asset_sha256"))}</p>', f'<h3>Render text</h3><pre>{esc(item["render"])}</pre>'])
            for field in BINDING_FIELDS:
                parts.append(f'<p>{field}: {esc(label.get(field))}</p>')
            parts.append('<fieldset><legend>Verdicts</legend>')
            for field in REVIEW_FIELDS:
                value = label.get(field)
                selected_true = ' selected' if value is True else ''
                selected_false = ' selected' if value is False else ''
                selected_unset = ' selected' if value is None else ''
                parts.append(f'<label>{field} <select data-field="{field}"><option value=""{selected_unset}>unset</option><option value="true"{selected_true}>true</option><option value="false"{selected_false}>false</option></select></label> ')
            parts.extend(['</fieldset>', f'<label>reviewer <input data-field="reviewer" value="{esc(label.get("reviewer"))}"></label>', f'<label>notes <textarea data-field="notes">{esc(label.get("notes"))}</textarea></label>', '</article>'])
            cards.append("\n".join(parts))
            manifest_rows.append({**{field: label.get(field) for field in IDENTITY_FIELDS}, "batch": n, "evidence_complete": not item["missing"]})
        filename = f"batch-{n}.html"
        script = f'''<script>const schema={json.dumps(LABEL_SCHEMA)};function exportBatch(){{const out=[];document.querySelectorAll('.row').forEach(card=>{{const item={{}};for(const k of schema){{const el=card.querySelector('[data-field="'+k+'"]');let v=el?el.value:null;if(["caption_ok","panels_ok","crop_ok","delivery_ok"].includes(k))v=v===""?null:v==="true";if(k==="reviewed_at")v=card.querySelector('[data-field="reviewer"]').value.trim()?new Date().toISOString():null;item[k]=v;}}if(!item.reviewer)item.reviewed_at=null;out.push(item);}});const blob=new Blob([out.map(x=>JSON.stringify(x)).join('\\n')+'\\n'],{{type:'application/x-ndjson'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='labels-batch-{n}.jsonl';a.click();URL.revokeObjectURL(a.href);}}</script>'''
        document = '<!doctype html><html><head><meta charset="utf-8"><title>Visual review batch</title><style>body{font:16px sans-serif;max-width:1000px;margin:auto;padding:1em}.row{border:1px solid #aaa;padding:1em;margin:1em 0}img{max-width:100%;height:auto}pre{white-space:pre-wrap}.missing{color:#a00;font-weight:bold}label{display:inline-block;margin:.5em}textarea{display:block;width:95%;height:5em}</style></head><body><h1>Visual review batch '+str(n)+'</h1><p>A RESOLVED delivery is not a visual PASS. Leave unset if you cannot judge.</p><button onclick="exportBatch()">Export this batch</button>'+"\n".join(cards)+script+'</body></html>'
        (out / filename).write_text(document, encoding="utf-8")
    sha = "sha256:" + hashlib.sha256(census_path.read_bytes()).hexdigest()
    manifest = {"schema": "paperforge.figure_review_html.v1", "census_sha256": sha, "rows": manifest_rows}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    merge = f'python scripts/dev/figure_review_apply.py --census "{census_path}" --pack "{out}" --patch ' + " ".join(f'"{out / f"labels-batch-{n}.jsonl"}"' for n in range(1, batch_count + 1))
    entries = "".join(f'<li><a href="batch-{n}.html">batch-{n}.html</a>: {len(batch)} rows</li>' for n, batch in enumerate(batches, 1))
    (out / "index.html").write_text(f'<!doctype html><html><head><meta charset="utf-8"><title>Review batches</title></head><body><h1>Review batches</h1><ul>{entries}</ul><p>Merge command: <code>{esc(merge)}</code></p></body></html>', encoding="utf-8")
    print("rows per batch:", ", ".join(str(len(b)) for b in batches))
    print("incomplete evidence:", sum(bool(r["missing"]) for r in rows))
    print("zero-label papers:", ", ".join(zero) if zero else "none")
    return manifest


def main() -> int:
    p = argparse.ArgumentParser(description="Build a self-contained visual review surface.")
    p.add_argument("--census", type=Path, default=ROOT / "docs/evidence/r3-reattribution/reattribution-census.json")
    p.add_argument("--sample", type=Path, default=ROOT / "docs/evidence/r3/sample-manifest.json")
    p.add_argument("--pack", type=Path, default=ROOT / "docs/evidence/r3-review-pack")
    p.add_argument("--work-root", type=Path, default=ROOT / ".work/r3-reattribution")
    p.add_argument("--out", type=Path, default=ROOT / "docs/evidence/r3-review-pack/html")
    p.add_argument("--batch-count", type=int, default=4)
    a = p.parse_args()
    build(a.census, a.sample, a.pack, a.work_root, a.out, a.batch_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
