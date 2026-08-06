"""#129 — display-restore drift derivation and provenance semantics."""
from __future__ import annotations

from paperforge.worker.ocr_maintenance import _restore_drift_override


class TestRestoreDriftOverride:
    def test_older_restored_version_overrides_to_drift(self):
        meta = {
            "ocr_finished_at": "2026-08-05T10:00:00Z",
            "restore_provenance": {
                "label": "v3",
                "restored_at": "2026-08-06T00:00:00Z",
                "version_created_at": "2026-07-01T00:00:00Z",
            },
        }
        assert _restore_drift_override(meta) is True

    def test_newer_or_same_version_no_override(self):
        meta = {
            "ocr_finished_at": "2026-08-05T10:00:00Z",
            "restore_provenance": {
                "label": "v5",
                "restored_at": "2026-08-06T00:00:00Z",
                "version_created_at": "2026-08-05T11:00:00Z",
            },
        }
        assert _restore_drift_override(meta) is False

    def test_no_provenance_no_override(self):
        assert _restore_drift_override({"ocr_finished_at": "2026-08-05T10:00:00Z"}) is False
        assert _restore_drift_override({}) is False

    def test_missing_timestamps_no_override(self):
        meta = {
            "restore_provenance": {"label": "v3", "restored_at": "2026-08-06T00:00:00Z"},
        }
        assert _restore_drift_override(meta) is False
        meta = {
            "ocr_finished_at": "2026-08-05T10:00:00Z",
            "restore_provenance": {"label": "v3"},
        }
        assert _restore_drift_override(meta) is False
