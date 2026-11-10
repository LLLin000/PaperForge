#!/usr/bin/env python
"""R2a: audit JSON parse failures without silently accepting bad bytes.

Classifies each failing JSON file by source hash/header/parse result, then (for a
sample) runs the real rebuild in an isolated vault and compares the same file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from paperforge.config import bootstrap_config  # noqa: E402
from paperforge.pdf_resolver import resolve_source_pdf  # noqa: E402
from paperforge.worker.ocr_rebuild import _rebuild_one_paper  # noqa: E402


def parse_state(path: Path) -> dict:
    if not path.is_file():
        return {"exists": False, "parse": "missing"}
    data = path.read_bytes()
    state = {
        "exists": True,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "head_hex": data[:16].hex(),
    }
    try:
        json.loads(data.decode("utf-8"))
        state["parse"] = "valid_utf8_json"
    except UnicodeDecodeError as exc:
        state["parse"] = "invalid_utf8"
        state["error"] = str(exc)
    except Exception as exc:
        state["parse"] = "invalid_json"
        state["error"] = str(exc)
    return state


def find_file(paper: Path, name: str) -> Path:
    matches = sorted(paper.rglob(name))
    return matches[0] if matches else paper / name


def audit_one(vault: Path, key: str, filenames: list[str]) -> dict:
    source = vault / "System" / "PaperForge" / "ocr" / key
    temp = Path(tempfile.mkdtemp(prefix=f"r2a-{key}-"))
    try:
        v = temp / "vault"
        paper = v / "System" / "PaperForge" / "ocr" / key
        shutil.copytree(source, paper, ignore=shutil.ignore_patterns("backups", "versions"))
        meta = json.loads((paper / "meta.json").read_text(encoding="utf-8"))
        pdf = resolve_source_pdf(vault, meta.get("source_pdf"))
        if pdf is not None:
            meta["source_pdf"] = str(pdf)
            (paper / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        bootstrap_config(v)
        result = _rebuild_one_paper(v, key)
        files = []
        for name in filenames:
            before = parse_state(find_file(source, name))
            after = parse_state(find_file(paper, name))
            if before.get("sha256") and before.get("sha256") == after.get("sha256"):
                classification = "preserved_legacy_bytes"
            elif after.get("parse") == "valid_utf8_json":
                classification = "regenerated_valid"
            elif after.get("parse") == "missing":
                classification = "removed_after_rebuild"
            else:
                classification = "regenerated_invalid"
            files.append({"name": name, "source": before, "rebuilt": after, "classification": classification})
        return {"key": key, "rebuild_status": result.get("status"), "files": files}
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default="D:/L/OB/Literature-hub")
    ap.add_argument("--summary", default=str(REPO / "docs/evidence/r2/full-ready-summary.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", type=int, default=5, help="number of keys to rebuild")
    args = ap.parse_args()

    vault = Path(args.vault).resolve()
    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    by_key: dict[str, list[str]] = {}
    for failure in summary.get("failures", []):
        for error in failure.get("errors", []):
            if error.startswith("json_parse:"):
                parts = error.split(":", 3)
                if len(parts) >= 2:
                    by_key.setdefault(failure["key"], []).append(parts[1])
    source_rows = []
    for key, names in sorted(by_key.items()):
        paper = vault / "System" / "PaperForge" / "ocr" / key
        source_rows.append({
            "key": key,
            "files": [{"name": name, **parse_state(find_file(paper, name))} for name in sorted(set(names))],
        })
    sample = [row["key"] for row in source_rows[: max(0, args.sample)]]
    rebuild_rows = [audit_one(vault, key, sorted(set(by_key[key]))) for key in sample]
    out = {
        "schema": "paperforge.r2.json_audit.v1",
        "keys": len(source_rows),
        "source_parse": {
            state: sum(1 for row in source_rows for f in row["files"] if f["parse"] == state)
            for state in ("valid_utf8_json", "invalid_utf8", "invalid_json", "missing")
        },
        "source": source_rows,
        "rebuild_sample": rebuild_rows,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"keys": out["keys"], "source_parse": out["source_parse"],
                      "sample": len(rebuild_rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
