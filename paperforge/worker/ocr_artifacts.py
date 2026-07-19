from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OCRArtifactPaths:
    paper_root: Path
    meta_json: Path
    result_json: Path
    compat_fulltext: Path
    raw_meta: Path
    source_metadata: Path
    blocks_raw: Path
    blocks_structured: Path


def artifact_paths_for_root(ocr_root: Path, zotero_key: str) -> OCRArtifactPaths:
    paper_root = ocr_root / zotero_key
    return OCRArtifactPaths(
        paper_root=paper_root,
        meta_json=paper_root / "meta.json",
        result_json=paper_root / "json" / "result.json",
        compat_fulltext=paper_root / "fulltext.md",
        raw_meta=paper_root / "raw" / "raw_meta.json",
        source_metadata=paper_root / "raw" / "source_metadata.json",
        blocks_raw=paper_root / "canonical" / "blocks.raw.jsonl",
        blocks_structured=paper_root / "structure" / "blocks.structured.jsonl",
    )


def artifact_paths_for_key(vault: Path, zotero_key: str) -> OCRArtifactPaths:
    from paperforge.worker._utils import pipeline_paths
    paths = pipeline_paths(vault)
    return artifact_paths_for_root(paths["ocr"], zotero_key)


def build_version_payload(
    *,
    pdf_fingerprint: str,
    result_json_hash: str,
    ocr_model: str,
) -> dict:
    from paperforge.worker.ocr_versions import expected_derived_payload, expected_raw_payload
    return {
        "raw_version": {
            **expected_raw_payload(ocr_model=ocr_model),
            "pdf_fingerprint": pdf_fingerprint,
            "result_json_hash": result_json_hash,
        },
        "derived_version": {
            **expected_derived_payload(),
        },
    }


def _sha256_hexdigest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def compute_pdf_fingerprint(pdf_path: Path) -> str:
    try:
        return _sha256_hexdigest(pdf_path.read_bytes())
    except (FileNotFoundError, OSError):
        return "unknown"


def compute_json_hash(data: list | dict) -> str:
    if isinstance(data, list):
        data = {"data": data}
    return _sha256_hexdigest(json.dumps(data, sort_keys=True).encode("utf-8"))


def cleanup_ocr_artifact_cache(paper_root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Remove regenerable cache artifacts while preserving canonical data.

    Canonical (kept):
      canonical/, structure/, metadata/, assets/, render/, health/, index/
      raw/, meta.json, fulltext.md

    Cache (removed):
      pages/ — page render cache, always regenerable from source PDF

    Returns a summary dict with paths removed per category.
    """
    report: dict[str, Any] = {"pages_removed": [], "errors": []}

    pages_dir = paper_root / "pages"
    if pages_dir.is_dir():
        for f in sorted(pages_dir.iterdir()):
            if f.suffix in {".jpg", ".png", ".webp"}:
                if not dry_run:
                    try:
                        f.unlink()
                    except OSError as e:
                        report["errors"].append(str(e))
                report["pages_removed"].append(f.name)
        if not dry_run:
            try:
                remaining = list(pages_dir.iterdir())
                if not remaining:
                    pages_dir.rmdir()
            except OSError:
                pass

    return report
