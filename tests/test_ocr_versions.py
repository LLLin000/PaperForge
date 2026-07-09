from __future__ import annotations

from unittest.mock import MagicMock


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


class TestComputeStructuredHash:
    """Tests for compute_structured_hash."""

    PATCH_PP = "paperforge.worker._utils.pipeline_paths"
    PATCH_ART = "paperforge.worker.ocr_artifacts.artifact_paths_for_root"

    def test_returns_hex_digest(self, tmp_path, mocker):
        """Hash of a known file returns a 64-bit hex string (16 chars)."""
        from paperforge.worker.ocr_versions import compute_structured_hash

        vault = tmp_path / "vault"
        ocr_root = vault / "ocr"
        paper_dir = ocr_root / "key"
        blocks_path = paper_dir / "structure" / "blocks.structured.jsonl"
        blocks_path.parent.mkdir(parents=True)
        blocks_path.write_text('{"test": "content"}\n', encoding="utf-8")

        mocker.patch(self.PATCH_PP, return_value={"ocr": str(ocr_root)})
        mocker.patch(self.PATCH_ART, return_value=MagicMock(
            blocks_structured=blocks_path,
        ))

        result = compute_structured_hash(vault, "key")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_returns_none_when_file_missing(self, tmp_path, mocker):
        """No blocks.structured.jsonl → None."""
        from paperforge.worker.ocr_versions import compute_structured_hash

        vault = tmp_path / "vault"
        ocr_root = vault / "ocr"
        paper_dir = ocr_root / "key"
        blocks_path = paper_dir / "structure" / "blocks.structured.jsonl"
        blocks_path.parent.mkdir(parents=True)
        # Do NOT create the file

        mocker.patch(self.PATCH_PP, return_value={"ocr": str(ocr_root)})
        mocker.patch(self.PATCH_ART, return_value=MagicMock(
            blocks_structured=blocks_path,
        ))

        assert compute_structured_hash(vault, "key") is None

    def test_deterministic(self, tmp_path, mocker):
        """Same content produces the same hash."""
        from paperforge.worker.ocr_versions import compute_structured_hash

        vault = tmp_path / "vault"
        ocr_root = vault / "ocr"
        paper_dir = ocr_root / "key"
        blocks_path = paper_dir / "structure" / "blocks.structured.jsonl"
        blocks_path.parent.mkdir(parents=True)
        blocks_path.write_text('{"stable": "data"}\n', encoding="utf-8")

        mocker.patch(self.PATCH_PP, return_value={"ocr": str(ocr_root)})
        mocker.patch(self.PATCH_ART, return_value=MagicMock(
            blocks_structured=blocks_path,
        ))

        h1 = compute_structured_hash(vault, "key")
        h2 = compute_structured_hash(vault, "key")
        assert h1 == h2
        assert h1 is not None
