from __future__ import annotations


def test_version_state_distinguishes_raw_vs_derived_drift() -> None:
    from paperforge.worker.ocr_versions import classify_version_state

    state = classify_version_state(
        meta={
            "raw_version": {"ocr_model": "PaddleOCR-VL-1.5", "pdf_fingerprint": "sha256:a"},
            "derived_version": {"renderer_version": "1.0.0-compat"},
        },
        expected_raw={
            "ocr_model": "PaddleOCR-VL-1.6",
            "pdf_fingerprint": "sha256:a",
        },
        expected_derived={
            "renderer_version": "2.0.0",
        },
    )

    assert state["raw_upgradable"] is True
    assert state["derived_stale"] is True
