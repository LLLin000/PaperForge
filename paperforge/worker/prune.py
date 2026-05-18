from __future__ import annotations

import logging
import shutil
from pathlib import Path

from paperforge.config import paperforge_paths
from paperforge.embedding._chroma import delete_paper_vectors

logger = logging.getLogger(__name__)


def _collect_orphan_candidates(lit_dir: Path, fresh_keys: set[str]) -> list[dict]:
    if not lit_dir.exists():
        return []

    candidates: list[dict] = []
    for domain_dir in sorted(lit_dir.iterdir()):
        if not domain_dir.is_dir():
            continue
        try:
            entries = sorted(domain_dir.iterdir())
        except OSError as exc:
            logger.warning("prune: cannot scan %s: %s", domain_dir, exc)
            continue
        for sub in entries:
            if not sub.is_dir():
                continue
            parts = sub.name.split(" - ", 1)
            if len(parts) < 2:
                continue
            key = parts[0]
            if not key:
                continue
            if key in fresh_keys:
                continue
            candidates.append(
                {
                    "key": key,
                    "domain": domain_dir.name,
                    "workspace_dir": sub,
                    "ocr_dir": None,
                }
            )

    return candidates


def _resolve_ocr_dir(vault: Path, key: str) -> Path:
    cfg = paperforge_paths(vault)
    ocr_root = cfg.get("ocr", vault / "System" / "PaperForge" / "ocr")
    return ocr_root / key


def prune_orphan_papers(
    vault: Path,
    *,
    fresh_index: dict,
    dry_run: bool = True,
) -> dict:
    cfg = paperforge_paths(vault)
    lit_dir = cfg.get("literature")
    if not lit_dir:
        return {"preview": [], "deleted": [], "counts": {}}

    fresh_keys = {item["zotero_key"] for item in fresh_index.get("items", []) if item.get("zotero_key")}

    candidates = _collect_orphan_candidates(lit_dir, fresh_keys)
    if not candidates:
        return {"preview": [], "deleted": [], "counts": {}}

    for c in candidates:
        c["ocr_dir"] = _resolve_ocr_dir(vault, c["key"])

    preview = [
        {
            "key": c["key"],
            "domain": c["domain"],
            "workspace": str(c["workspace_dir"]),
            "ocr_dir": str(c["ocr_dir"]) if c["ocr_dir"].exists() else None,
        }
        for c in candidates
    ]

    if dry_run:
        return {"preview": preview, "deleted": [], "counts": {}}

    deleted: list[str] = []
    counts = {"workspace": 0, "ocr": 0, "vectors": 0, "failed": 0}

    for c in candidates:
        key = c["key"]
        try:
            ocr = c["ocr_dir"]
            if ocr and ocr.exists():
                shutil.rmtree(ocr, ignore_errors=True)
                if not ocr.exists():
                    counts["ocr"] += 1

            ws = c["workspace_dir"]
            if ws.exists():
                shutil.rmtree(ws, ignore_errors=True)
                if not ws.exists():
                    counts["workspace"] += 1

            try:
                n = delete_paper_vectors(vault, key)
                if n > 0:
                    counts["vectors"] += n
            except Exception as vec_err:
                logger.warning("prune: failed to delete vectors for %s: %s", key, vec_err)
                counts["failed"] += 1

            deleted.append(key)

        except Exception as exc:
            logger.error("prune: failed to clean up %s: %s", key, exc)
            counts["failed"] += 1

    return {"preview": preview, "deleted": deleted, "counts": counts}
