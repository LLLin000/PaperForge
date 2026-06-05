from __future__ import annotations

# Version constants - single source of truth
EXPECTED_OCR_PROVIDER = "PaddleOCR"
EXPECTED_OCR_RAW_SCHEMA_VERSION = "1.0.0"
EXPECTED_CANONICAL_BLOCK_VERSION = "1.0.0"
EXPECTED_STRUCTURE_VERSION = "1.0.0"
EXPECTED_METADATA_RESOLVER_VERSION = "1.0.0"
EXPECTED_ASSET_EXTRACTOR_VERSION = "1.0.0"
EXPECTED_RENDERER_VERSION = "2.0.0"
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
