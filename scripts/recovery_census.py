"""READ-ONLY recovery census — classify the 684 restored-corrupt OCR papers
against the materialization contract.  Never writes anything; the probe's
judging functions are read-only.  Outputs cluster counts per layer, not
per-paper dumps (use --detail for a paper list).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

def _vault() -> Path:
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        return Path(sys.argv[1])
    raise SystemExit("usage: python scripts/recovery_census.py <vault> [--detail]")

VAULT = _vault()
OCR = VAULT / "System" / "PaperForge" / "ocr"
DB = VAULT / "System" / "PaperForge" / "indexes" / "paperforge.db"

from paperforge.materialization.ocr import (
    detail,
    provenance_state,
    raw_state,
    top_state,
)
from paperforge.materialization.retrieval import (
    policy_currency,
    snapshot_integrity,
)
from paperforge.lineage import _resolve_canonical_pdf


def main() -> int:
    # corrupt raw papers (the recovery cohort)
    corrupt_keys: list[str] = []
    for d in sorted(OCR.iterdir()):
        raw = d / "canonical" / "blocks.raw.jsonl"
        if not raw.exists():
            continue
        try:
            raw.read_text(encoding="utf-8")
        except Exception:
            corrupt_keys.append(d.name)
    print(f"cohort: {len(corrupt_keys)} papers with unreadable raw", file=sys.stderr)

    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn2 = conn
    body_keys = {r[0] for r in conn.execute("SELECT DISTINCT paper_id FROM body_units")}
    obj_keys = {r[0] for r in conn.execute("SELECT DISTINCT paper_id FROM object_units")}
    vec_body = {r[0] for r in conn.execute("SELECT DISTINCT paper_id FROM vec_body_meta")}
    vec_obj = {r[0] for r in conn.execute("SELECT DISTINCT paper_id FROM vec_objects_meta")}
    vec_ft = {r[0] for r in conn.execute("SELECT DISTINCT paper_id FROM vec_fulltext_meta")}
    lineage = {r[0] for r in conn.execute("SELECT DISTINCT paper_id FROM lineage")}
    # conn stays open for per-paper integrity queries; closed at the end

    raw_c = Counter()
    top_c = Counter()
    prov_c = Counter()
    meta_c = Counter()
    frontier_c = Counter()
    db_c = Counter()
    detail_papers: list[tuple[str, str]] = []

    for key in corrupt_keys:
        paper_dir = OCR / key
        # meta readable?
        meta_ok = True
        try:
            (paper_dir / "meta.json").read_text(encoding="utf-8")
        except Exception:
            meta_ok = False
        meta_c["meta_ok" if meta_ok else "meta_unreadable"] += 1
        # OCR layer judging
        raw = raw_state(paper_dir)
        raw_c[raw or "raw_valid"] += 1
        prov = provenance_state(paper_dir, _resolve_canonical_pdf(VAULT, paper_dir))
        prov_c[prov or "prov_ok"] += 1
        top = top_state(paper_dir)
        top_c[top or "current_candidate"] += 1
        det = detail(paper_dir, _resolve_canonical_pdf(VAULT, paper_dir))
        # DB layer facts (separate carrier truth)
        has_units = key in body_keys or key in obj_keys
        has_vec = key in vec_body or key in vec_obj or key in vec_ft
        has_lineage = key in lineage
        if has_units:
            db_c["has_retrieval_units"] += 1
        if has_vec:
            db_c["has_vectors"] += 1
        if has_lineage:
            db_c["has_lineage"] += 1
        if has_units and has_vec and has_lineage:
            db_c["full_chain"] += 1
        # P1-D: retrieval snapshot integrity classification (serving facts)
        if has_units:
            mrow = conn2.execute(
                "SELECT value FROM meta WHERE key = ?", (f"manifest:{key}",)
            ).fetchone()
            manifest = None
            if mrow:
                try:
                    manifest = json.loads(mrow[0])
                except Exception:
                    manifest = None
            body_rows = [dict(r) for r in conn2.execute(
                "SELECT * FROM body_units WHERE paper_id = ?", (key,)
            )]
            obj_rows = [dict(r) for r in conn2.execute(
                "SELECT * FROM object_units WHERE paper_id = ?", (key,)
            )]
            integ = snapshot_integrity(
                manifest, body_rows, obj_rows,
                body_count=len(body_rows), object_count=len(obj_rows),
            )
            pol = policy_currency(manifest)
            if integ == "verified" and pol == "current":
                db_c["intact_current"] += 1
            elif integ == "verified" and pol == "old":
                db_c["intact_old"] += 1
            elif integ == "corrupt":
                db_c["corrupt"] += 1
            else:
                db_c["unverifiable_legacy"] += 1
        # first broken frontier (OCR file layer only — raw is the repair
        # frontier; DB carriers are serving facts, judged separately)
        frontier = "raw" if raw else ("provenance" if prov else "derived")
        frontier_c[frontier] += 1
        detail_papers.append((key, det or ""))

    conn.close()
    print("=== raw layer ===")
    for k, v in raw_c.most_common():
        print(f"  {k}: {v}")
    print("=== provenance ===")
    for k, v in prov_c.most_common():
        print(f"  {k}: {v}")
    print("=== top state ===")
    for k, v in top_c.most_common():
        print(f"  {k}: {v}")
    print("=== meta ===")
    for k, v in meta_c.most_common():
        print(f"  {k}: {v}")
    print("=== first broken frontier ===")
    for k, v in frontier_c.most_common():
        print(f"  {k}: {v}")
    print("=== DB carrier (serving facts, independent of file layer) ===")
    for k, v in db_c.most_common():
        print(f"  {k}: {v}")
    if "--detail" in sys.argv:
        for key, det in detail_papers:
            print(f"  {key}: {det}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
