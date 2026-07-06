from __future__ import annotations

from pathlib import Path

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
