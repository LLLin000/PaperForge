from __future__ import annotations


def test_sync_preflight_flags_dirty_ocr_runtime_modules(tmp_path):
    from paperforge.services.sync_service import detect_ocr_runtime_preflight_issues

    issues = detect_ocr_runtime_preflight_issues(
        dirty_files=[
            "paperforge/worker/ocr_render.py",
            "paperforge/worker/ocr_objects.py",
        ]
    )

    assert issues
    assert any("ocr_render.py" in issue for issue in issues)
