"""Canonical OCR result hash contract (#126 PR A).

The derived result hash guards the memory layer against half-built or stale
OCR artifacts:

- `compute_ocr_result_hash()` — SHA-256 over the three canonical artifacts in
  fixed order; missing any artifact returns None (never a partial hash).
- `result-hash.pending` — crash-surviving publication marker. Created BEFORE
  any derived mutation; removed only after a verified publish. While present,
  the reader must neither trust the stale `result-hash.txt` nor consume the
  paper's artifacts.
- `publish_ocr_result_hash()` — temp file + `os.replace` atomic publish.

The previous Level-1 write convention (hand-written `result-hash.txt`) is
gone; every derived-success path (new OCR postprocess, derived rebuild,
legacy backfill) publishes through this module.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

OCR_RESULT_HASH_ARTIFACTS = (
    "structure/blocks.structured.jsonl",
    "index/structure-tree.json",
    "index/role-index.json",
)
PENDING_MARKER = "index/result-hash.pending"
HASH_FILE = "index/result-hash.txt"


def compute_ocr_result_hash(paper_root: Path) -> str | None:
    """SHA-256 over the three canonical artifacts in fixed order.

    Returns None when any artifact is missing — a partial hash must never be
    published or trusted.
    """
    digest = hashlib.sha256()
    for rel in OCR_RESULT_HASH_ARTIFACTS:
        path = paper_root / rel
        if not path.exists():
            return None
        digest.update(path.read_bytes())
    return digest.hexdigest()


def has_result_hash_pending(paper_root: Path) -> bool:
    return (paper_root / PENDING_MARKER).exists()


def create_result_hash_pending(paper_root: Path) -> None:
    """Atomically create the publication marker BEFORE any derived mutation."""
    marker = paper_root / PENDING_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("pending", encoding="utf-8")


def clear_result_hash_pending(paper_root: Path) -> None:
    (paper_root / PENDING_MARKER).unlink(missing_ok=True)


def publish_ocr_result_hash(paper_root: Path) -> str | None:
    """Atomically publish the canonical hash; returns the digest or None.

    The caller must have verified the three artifacts; a missing artifact
    returns None and leaves any pending marker in place.
    """
    digest = compute_ocr_result_hash(paper_root)
    if digest is None:
        return None
    target = paper_root / HASH_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".result-hash-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(digest)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return digest
