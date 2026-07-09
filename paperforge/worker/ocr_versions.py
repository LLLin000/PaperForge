from __future__ import annotations

import datetime
import shutil
from pathlib import Path

from paperforge.core.io import read_json, write_json

# Version constants - single source of truth
EXPECTED_OCR_PROVIDER = "PaddleOCR"
EXPECTED_OCR_RAW_SCHEMA_VERSION = "1.0.0"
EXPECTED_CANONICAL_BLOCK_VERSION = "1.0.0"
EXPECTED_STRUCTURE_VERSION = "1.0.0"
EXPECTED_METADATA_RESOLVER_VERSION = "1.0.0"
EXPECTED_ASSET_EXTRACTOR_VERSION = "1.0.0"
EXPECTED_RENDERER_VERSION = "2.1.0"
EXPECTED_DOCTOR_VERSION = "1.0.0"


def expected_raw_payload(*, ocr_model: str) -> dict:
    return {
        "ocr_provider": EXPECTED_OCR_PROVIDER,
        "ocr_model": ocr_model,
        "ocr_raw_schema_version": EXPECTED_OCR_RAW_SCHEMA_VERSION,
    }


def expected_derived_payload() -> dict:
    return {
        "canonical_block_version": EXPECTED_CANONICAL_BLOCK_VERSION,
        "structure_version": EXPECTED_STRUCTURE_VERSION,
        "metadata_resolver_version": EXPECTED_METADATA_RESOLVER_VERSION,
        "asset_extractor_version": EXPECTED_ASSET_EXTRACTOR_VERSION,
        "renderer_version": EXPECTED_RENDERER_VERSION,
        "doctor_version": EXPECTED_DOCTOR_VERSION,
    }


def classify_legacy_ocr_state(
    meta: dict,
    ocr_dir: Path | None = None,
) -> dict:
    """Classify if a paper has legacy (pre-structured-pipeline) OCR output.

    A paper is legacy when ocr_status == "done" but neither raw_version
    nor derived_version exist in meta. That means its OCR was produced
    before the structured pipeline was introduced.

    Args:
        meta: The contents of meta.json for the paper.
        ocr_dir: Optional path to the paper's OCR directory, for
            file-level checks like existence of json/result.json.

    Returns:
        Dict with is_legacy, can_backfill, has_version_state,
        missing_keys, has_result_json, ocr_status.
    """
    has_raw = "raw_version" in meta
    has_derived = "derived_version" in meta
    has_version_state = has_raw or has_derived
    ocr_done = meta.get("ocr_status") == "done"

    is_legacy = ocr_done and not has_version_state

    has_result_json = False
    if ocr_dir is not None:
        has_result_json = (ocr_dir / "json" / "result.json").exists()

    can_backfill = bool(is_legacy and (ocr_dir is None or has_result_json))

    missing_keys: list[str] = []
    if not is_legacy:
        if not has_raw:
            missing_keys.append("raw_version")
        if not has_derived:
            missing_keys.append("derived_version")

    return {
        "is_legacy": is_legacy,
        "can_backfill": can_backfill,
        "has_version_state": has_version_state,
        "missing_keys": missing_keys,
        "has_result_json": has_result_json,
        "ocr_status": ocr_done,
    }


def classify_version_state(
    meta: dict,
    expected_raw: dict,
    expected_derived: dict,
) -> dict:
    stored_raw = meta.get("raw_version", {})
    stored_derived = meta.get("derived_version", {})

    raw_reasons: list[str] = []
    derived_reasons: list[str] = []

    for key, expected_value in expected_raw.items():
        stored_value = stored_raw.get(key)
        if stored_value is None:
            raw_reasons.append(f"raw.{key}: missing in meta")
        elif stored_value != expected_value:
            raw_reasons.append(f"raw.{key}: {stored_value} != {expected_value}")

    for key, expected_value in expected_derived.items():
        stored_value = stored_derived.get(key)
        if stored_value is None:
            derived_reasons.append(f"derived.{key}: missing in meta")
        elif stored_value != expected_value:
            derived_reasons.append(f"derived.{key}: {stored_value} != {expected_value}")

    return {
        "raw_upgradable": bool(raw_reasons),
        "derived_stale": bool(derived_reasons),
        "raw_reasons": raw_reasons,
        "derived_reasons": derived_reasons,
        "has_version_state": "raw_version" in meta or "derived_version" in meta,
    }


def compute_structured_hash(vault: Path, key: str) -> str | None:
    """Compute xxhash of blocks.structured.jsonl for a paper.

    Returns hex digest string, or None if the file doesn't exist.
    """
    from paperforge.worker._utils import pipeline_paths
    from paperforge.worker.ocr_artifacts import artifact_paths_for_root

    import xxhash

    ocr_root = Path(pipeline_paths(vault)["ocr"])
    artifacts = artifact_paths_for_root(ocr_root, key)

    if not artifacts.blocks_structured.exists():
        return None

    hasher = xxhash.xxh64()
    with artifacts.blocks_structured.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def backup_render_before_rebuild(paper_root: Path) -> str | None:
    """Backup current render/ before rebuild overwrites it.

    Copies render/fulltext.md (and related artifacts) to versions/v{N}/.
    Creates or updates versions/manifest.json. Idempotent: skips when
    render/fulltext.md doesn't exist (no prior render to preserve).

    Returns version label (e.g. "v1") or None if nothing was backed up.
    """
    render_dir = paper_root / "render"
    ft_path = render_dir / "fulltext.md"
    if not ft_path.exists():
        return None

    versions_root = paper_root / "versions"
    manifest_path = versions_root / "manifest.json"

    # Read existing manifest
    manifest: dict = {"versions": [], "current": {}}
    if manifest_path.exists():
        try:
            manifest = read_json(manifest_path)
        except Exception:
            manifest = {"versions": [], "current": {}}

    # Determine next version label
    existing = manifest.get("versions", [])
    next_num = 1
    if existing:
        labels = [v.get("label", "") for v in existing]
        nums = [int(l[1:]) for l in labels if l.startswith("v") and l[1:].isdigit()]
        if nums:
            next_num = max(nums) + 1
    label = f"v{next_num}"

    # Copy backup files
    dest = versions_root / label
    dest.mkdir(parents=True, exist_ok=True)
    for fname in ["fulltext.md", "render-map.json", "heading-events.json"]:
        src = render_dir / fname
        if src.exists():
            shutil.copy2(src, dest / fname)

    # Build version entry
    entry: dict = {
        "label": label,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": "pre-rebuild",
        "fulltext_size": ft_path.stat().st_size,
    }

    # Carry forward structured_content_hash from meta.json if available
    meta_path = paper_root / "meta.json"
    if meta_path.exists():
        try:
            meta = read_json(meta_path)
            h = meta.get("structured_content_hash")
            if h:
                entry["structured_content_hash"] = h
            rv = meta.get("derived_version", {})
            if rv:
                entry["renderer_version"] = rv.get("renderer_version", "")
        except Exception:
            pass

    existing.append(entry)
    manifest["versions"] = existing
    manifest["current"] = {"label": label}

    write_json(manifest_path, manifest)
    return label
