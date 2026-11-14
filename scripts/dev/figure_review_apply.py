from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IDENTITY_FIELDS = ("key", "kind", "figure_id", "page", "block_id")
BINDING_FIELDS = ("snapshot_fingerprint", "source_pdf_sha256", "asset_sha256", "render_sha256", "fulltext_sha256")
REVIEW_FIELDS = ("caption_ok", "panels_ok", "crop_ok", "delivery_ok")


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []


def identity(row: dict) -> tuple:
    return tuple(row.get(field) for field in IDENTITY_FIELDS)


def apply(census_path: Path, patches: list[Path], pack: Path, dry_run: bool = False) -> int:
    manifest_path = pack / "manifest.json" if pack.is_dir() else pack
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual_sha = "sha256:" + hashlib.sha256(census_path.read_bytes()).hexdigest()
    if manifest.get("census_sha256") != actual_sha:
        raise ValueError(f"stale manifest census sha256: expected {actual_sha}, got {manifest.get('census_sha256')}")
    census = json.loads(census_path.read_text(encoding="utf-8"))
    papers = {p["key"]: p for p in census["papers"]}
    originals: dict[Path, list[dict]] = {}
    targets: dict[tuple, tuple[Path, dict]] = {}
    for key, paper in papers.items():
        path = Path(paper.get("evidence_dir") or census_path.parent / key) / "labels.jsonl"
        originals[path] = rows(path)
        for row in originals[path]:
            ident = identity(row)
            if ident in targets:
                raise ValueError(f"duplicate label identity: {ident}")
            targets[ident] = (path, row)
    selected, errors = {}, []
    seen = set()
    for patch_path in patches:
        for patch in rows(patch_path):
            ident = identity(patch)
            if ident in seen:
                errors.append(f"duplicate patch row: {ident}")
                continue
            seen.add(ident)
            if ident not in targets:
                errors.append(f"patch row has no matching label: {ident}")
                continue
            path, current = targets[ident]
            mismatches = [field for field in BINDING_FIELDS if patch.get(field) != current.get(field)]
            if mismatches:
                errors.append(f"{ident}: binding mismatch fields {', '.join(mismatches)}")
                continue
            if any(patch.get(field) not in (None, True, False) for field in REVIEW_FIELDS):
                errors.append(f"{ident}: invalid verdict value")
                continue
            if not any(patch.get(field) is not None for field in REVIEW_FIELDS):
                continue
            selected[ident] = (path, current, patch)
    if errors:
        raise ValueError("\\n".join(errors))
    updated = {path: [dict(row) for row in values] for path, values in originals.items()}
    changes = 0
    for ident, (path, current, patch) in selected.items():
        target = next(row for row in updated[path] if identity(row) == ident)
        for field in REVIEW_FIELDS:
            if patch.get(field) is not None:
                target[field] = patch[field]
        if str(patch.get("reviewer") or "").strip():
            target["reviewer"] = patch["reviewer"]
        if patch.get("reviewed_at"):
            target["reviewed_at"] = patch["reviewed_at"]
        if patch.get("notes") is not None:
            target["notes"] = patch["notes"]
        changes += 1
    print(f"planned changes: {changes}")
    if dry_run or not changes:
        return changes
    for path, values in updated.items():
        if values == originals[path]:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in values))
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply reviewed label patches after verifying snapshot bindings.")
    parser.add_argument("--census", type=Path, required=True)
    parser.add_argument("--patch", type=Path, nargs="+", required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        apply(args.census, args.patch, args.pack, args.dry_run)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
