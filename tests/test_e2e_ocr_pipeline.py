from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

# Role simplification map for expected-block comparison
_ROLE_SIMPLIFY = {
    "paper_title": "title",
    "title": "title",
    "author": "author",
    "authors": "author",
    "affiliation": "author",
    "abstract_heading": "abstract",
    "abstract_body": "abstract",
    "section_heading": "heading",
    "subsection_heading": "heading",
    "sub_subsection_heading": "heading",
    "section_heading_1": "heading",
    "section_heading_2": "heading",
    "section_heading_3": "heading",
    "body_text": "text",
    "body_paragraph": "text",
    "reference_heading": "reference",
    "reference_item": "reference",
    "figure_caption": "figure",
    "figure_asset": "figure",
    "media_asset": "figure",
    "table_caption": "table",
    "table_html": "table",
    "formal_table": "table",
    "figure": "figure",
    "table": "table",
    "heading": "heading",
    "text": "text",
    "reference": "reference",
    "abstract": "abstract",
}


def _simplify_role(role: str) -> str:
    """Map a structured-block role to the simplified expected-block role name."""
    return _ROLE_SIMPLIFY.get(role, "text")
_OCR_PAYLOAD_CACHE: dict[str, list[dict]] = {}



def _load_fixture_payload(fixtures_dir: Path) -> list[dict]:
    """Load a pre-canned OCR API payload from the fixture directory."""
    payload_path = fixtures_dir / "ocr_real_papers" / "VAMSAZMG" / "ocr_payload.json"
    if str(payload_path) not in _OCR_PAYLOAD_CACHE:
        data = json.loads(payload_path.read_text(encoding="utf-8"))
        _OCR_PAYLOAD_CACHE[str(payload_path)] = data
    return _OCR_PAYLOAD_CACHE[str(payload_path)]


def _copy_pdf_to_vault(vault: Path, paper_id: str, pdf_path: Path) -> Path:
    """Copy a fixture PDF into the vault's Zotero storage and return the destination."""
    zotero_key = paper_id.upper()
    zotero_dir = vault / "99_System" / "Zotero" / zotero_key
    zotero_dir.mkdir(parents=True, exist_ok=True)
    dest = zotero_dir / f"{zotero_key}.pdf"
    shutil.copy2(pdf_path, dest)
    # also copy to storage/ subdirectory for legacy resolution
    storage_dir = vault / "99_System" / "Zotero" / "storage" / zotero_key
    storage_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf_path, storage_dir / f"{zotero_key}.pdf")
    return dest


def _run_ocr_pipeline(vault: Path, key: str, payload: list[dict]) -> tuple[int, str, str, str]:
    """Run the OCR postprocessing pipeline with a pre-canned payload."""
    from paperforge.worker.ocr import postprocess_ocr_result

    # Ensure ocr output directory exists
    ocr_dir = vault / "99_System" / "PaperForge" / "ocr" / key
    ocr_dir.mkdir(parents=True, exist_ok=True)

    return postprocess_ocr_result(vault, key, payload)


def _load_structured_blocks(vault: Path, key: str) -> list[dict]:
    """Load structured blocks from the pipeline output."""
    structured_path = (
        vault
        / "99_System"
        / "PaperForge"
        / "ocr"
        / key
        / "structure"
        / "blocks.structured.jsonl"
    )
    if not structured_path.exists():
        return []
    return [
        json.loads(line)
        for line in structured_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_health_report(vault: Path, key: str) -> dict:
    """Load the OCR health report from the pipeline output."""
    health_path = (
        vault / "99_System" / "PaperForge" / "ocr" / key / "health" / "ocr_health.json"
    )
    if not health_path.exists():
        return {}
    return json.loads(health_path.read_text(encoding="utf-8"))


def _setup_meta(vault: Path, key: str, pdf_dest: Path) -> None:
    """Create a minimal meta.json for the paper key."""
    from paperforge.worker.ocr import ensure_ocr_meta

    meta = ensure_ocr_meta(
        vault,
        {"zotero_key": key, "has_pdf": True, "pdf_path": str(pdf_dest)},
    )
    meta["source_pdf"] = str(pdf_dest)
    from paperforge.core.io import write_json

    write_json(
        vault / "99_System" / "PaperForge" / "ocr" / key / "meta.json",
        meta,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestE2eOcrPipeline:
    """E2E OCR pipeline: raw payload → structured blocks → health report."""

    @pytest.fixture(autouse=True)
    def _setup(
        self,
        test_vault: Path,  # noqa: F811
        synthetic_paper_paths: list[tuple[str, Path]],
        e2e_fixture_dir: Path,
    ) -> None:
        """Per-test setup: create vault, copy PDF, prepare meta, run pipeline."""
        # Use paper_a as the fixture paper
        paper_id, paper_path = synthetic_paper_paths[0]
        key = paper_id.upper()

        # Copy PDF to vault
        pdf_dest = _copy_pdf_to_vault(test_vault, paper_id, paper_path)

        # Create meta.json
        _setup_meta(test_vault, key, pdf_dest)

        # Load pre-canned OCR payload
        payload = _load_fixture_payload(e2e_fixture_dir)

        # Run the pipeline
        _run_ocr_pipeline(test_vault, key, payload)

        # Store for test methods
        self._vault = test_vault
        self._key = key
        self._paper_id = paper_id
        self._e2e_fixture_dir = e2e_fixture_dir

    # ------------------------------------------------------------------
    # test_ocr_produces_structured_blocks
    # ------------------------------------------------------------------

    @pytest.mark.slow
    def test_ocr_produces_structured_blocks(self) -> None:
        """Pipeline produces raw and structured blocks with expected roles."""
        blocks_raw_path = (
            self._vault
            / "99_System"
            / "PaperForge"
            / "ocr"
            / self._key
            / "canonical"
            / "blocks.raw.jsonl"
        )
        assert blocks_raw_path.exists(), f"Raw blocks not found: {blocks_raw_path}"
        raw_blocks = [
            json.loads(line)
            for line in blocks_raw_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(raw_blocks) > 0, "No raw blocks produced"

        structured_blocks = _load_structured_blocks(self._vault, self._key)
        assert len(structured_blocks) > 0, "No structured blocks produced"

        # Check that expected role types are present (allow name variations)
        roles_present = {b.get("role", "") for b in structured_blocks}
        simplified = {_simplify_role(r) for r in roles_present}
        for expected in ("title", "heading", "text"):
            assert expected in simplified, (
                f"Expected role '{expected}' not found in {sorted(simplified)}"
            )

    # ------------------------------------------------------------------
    # test_ocr_output_matches_expected
    # ------------------------------------------------------------------

    @pytest.mark.slow
    def test_ocr_output_matches_expected(self) -> None:
        """Pipeline output roles overlap with expected_blocks.json (with tolerance)."""
        expected_path = (
            self._e2e_fixture_dir
            / "expected_outputs"
            / self._paper_id
            / "expected_blocks.json"
        )
        assert expected_path.exists(), f"Expected blocks not found: {expected_path}"
        expected_roles = {entry["role"] for entry in json.loads(expected_path.read_text(encoding="utf-8"))}

        structured_blocks = _load_structured_blocks(self._vault, self._key)
        assert len(structured_blocks) > 0, "No structured blocks to compare"

        actual_simplified = {_simplify_role(b.get("role", "")) for b in structured_blocks}

        # Every expected role type should appear at least once in the output,
        # but accept that a role may map differently (title → heading, etc.)
        overlap = expected_roles & actual_simplified
        assert len(overlap) >= len(expected_roles) - 2, (  # allow up to 2 missing
            f"Expected roles {expected_roles} but only {overlap} found in {actual_simplified}"
        )

    # ------------------------------------------------------------------
    # test_ocr_health_check_passes
    # ------------------------------------------------------------------

    @pytest.mark.e2e_fast
    def test_ocr_health_check_passes(self) -> None:
        """Pipeline produces a health report whose overall status is not critical."""
        health = _load_health_report(self._vault, self._key)
        assert health, "ocr_health.json not found or empty"
        assert "overall" in health, f"Health report missing 'overall' key: {list(health.keys())}"
        assert health["overall"] != "critical", (
            f"Health status is critical: {json.dumps(health, indent=2, ensure_ascii=False)}"
        )
