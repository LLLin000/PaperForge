"""Production-path regression gate for OCR-v2 real papers.

Primary: fixture-backed deterministic replay via build_raw_blocks_for_result_lines
         -> build_structured_blocks -> figure/table inventory -> render_fulltext_markdown.

Secondary: env-driven audit tests (marker: @pytest.mark.audit, skip if
           PAPERFORGE_REAL_OCR_VAULT not set).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "ocr_real_papers"
LEDGER_PATH = Path(__file__).resolve().parents[1] / "audit" / "coverage_ledger.json"
MANIFEST_PATH = LEDGER_PATH

# ---------------------------------------------------------------------------
# Fixture helper loaders
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_ocr_payload(key: str) -> list[dict]:
    path = FIXTURE_ROOT / key / "ocr_payload.json"
    if not path.exists():
        pytest.skip(f"ocr_payload.json not found for {key}")
    return _load_json(path)  # type: ignore[return-value]


def _load_source_metadata(key: str) -> dict:
    path = FIXTURE_ROOT / key / "source_metadata.json"
    if not path.exists():
        pytest.skip(f"source_metadata.json not found for {key}")
    return _load_json(path)  # type: ignore[return-value]


def _load_expectations(key: str) -> dict:
    path = FIXTURE_ROOT / key / "expectations.json"
    if not path.exists():
        pytest.skip(f"expectations.json not found for {key}")
    return _load_json(path)  # type: ignore[return-value]


def _iter_expected_object_ownership(expectations: dict) -> list[tuple[str, dict]]:
    rows: list[tuple[str, dict]] = []
    for page_str, page_exp in expectations.get("pages", {}).items():
        for obj in page_exp.get("expected_object_ownership", []):
            rows.append((page_str, obj))
    return rows


def _reader_figure_index(reader_payload: dict) -> tuple[dict[int, dict], dict[int, dict]]:
    normalized = reader_payload.get("normalized_inputs", {})
    matched = {
        int(item["figure_number"]): item
        for item in normalized.get("matched_figures", [])
        if item.get("figure_number") is not None
    }
    ambiguous = {
        int(item["figure_number"]): item
        for item in normalized.get("ambiguous_figures", [])
        if item.get("figure_number") is not None
    }
    return matched, ambiguous


def _load_reader_payload_from_vault(key: str) -> dict:
    vault = _real_ocr_vault()
    if vault is None:
        pytest.skip("PAPERFORGE_REAL_OCR_VAULT not set for vault fallback read")
    path = vault / "System" / "PaperForge" / "ocr" / key / "structure" / "reader_figures.json"
    return _load_json(path)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Replay harness — runs the real production path
# ---------------------------------------------------------------------------


def replay_production_pipeline(key: str, tmp_path: Path) -> dict:
    """Run the full production pipeline on fixture data; return all artifacts.

    Pipeline: build_raw_blocks_for_result_lines -> build_structured_blocks
    -> build_figure_inventory -> synthesize_reader_figures
    -> build_table_inventory -> render_fulltext_markdown

    PDF span backfill is skipped (no source PDF in fixtures).
    normalize_document_structure() is called internally by build_structured_blocks().
    """
    from paperforge.worker.ocr_blocks import (
        build_raw_blocks_for_result_lines,
        build_structured_blocks,
    )
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures
    from paperforge.worker.ocr_figures import build_figure_inventory
    from paperforge.worker.ocr_metadata import resolve_metadata
    from paperforge.worker.ocr_render import render_fulltext_markdown
    from paperforge.worker.ocr_tables import build_table_inventory

    ocr_payload = _load_ocr_payload(key)
    source_metadata = _load_source_metadata(key)

    # Step 1: raw blocks from PaddleOCR result lines
    raw_blocks = build_raw_blocks_for_result_lines(key, ocr_payload)

    # Step 2: structured blocks (role assignment + normalize_document_structure)
    structured_blocks, doc_structure = build_structured_blocks(
        raw_blocks,
        source_metadata=source_metadata,
        structure_output_dir=str(tmp_path),
    )

    # Step 3: figure inventory
    figure_inventory = build_figure_inventory(structured_blocks)

    # Step 4: reader figure synthesis
    reader_payload = synthesize_reader_figures(figure_inventory, structured_blocks, doc_structure)

    # Step 5: table inventory
    table_inventory = build_table_inventory(structured_blocks)

    resolved_metadata = (
        resolve_metadata(source_metadata, page_blocks=raw_blocks, structured_blocks=structured_blocks)
        if isinstance(source_metadata.get("title"), str)
        else source_metadata
    )

    # Step 6: render fulltext markdown
    page_count = (
        max((b.get("page", 1) for b in structured_blocks), default=1)
        if structured_blocks
        else None
    )
    rendered = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata=resolved_metadata,
        figure_inventory=figure_inventory,
        table_inventory=table_inventory,
        page_count=page_count,
        document_structure=doc_structure,
        reader_payload=reader_payload,
    )

    return {
        "raw_blocks": raw_blocks,
        "structured_blocks": structured_blocks,
        "doc_structure": doc_structure,
        "figure_inventory": figure_inventory,
        "reader_payload": reader_payload,
        "table_inventory": table_inventory,
        "rendered": rendered,
    }


def _dump_debug_bundle(key: str, result: dict | None, tmp_path: Path) -> None:
    """Write debug artifacts on assertion failure."""
    if result is None:
        return

    structured = result.get("structured_blocks")
    if structured:
        (tmp_path / "structured_blocks.failed.jsonl").write_text(
            "\n".join(json.dumps(b, ensure_ascii=False) for b in structured),
            encoding="utf-8",
        )

    doc_structure = result.get("doc_structure")
    if doc_structure is not None:
        import dataclasses

        try:
            if hasattr(doc_structure, "_asdict"):
                data = doc_structure._asdict()
            elif dataclasses.is_dataclass(doc_structure):
                data = dataclasses.asdict(doc_structure)
            else:
                data = str(doc_structure)
        except Exception:
            data = str(doc_structure)
        (tmp_path / "document_structure.failed.json").write_text(
            json.dumps(data, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )

    for name in ("figure_inventory", "reader_payload", "table_inventory"):
        value = result.get(name)
        if value:
            (tmp_path / f"{name}.failed.json").write_text(
                json.dumps(value, indent=2, default=str, ensure_ascii=False),
                encoding="utf-8",
            )

    rendered = result.get("rendered")
    if rendered:
        (tmp_path / "rendered.failed.md").write_text(rendered, encoding="utf-8")


# ---------------------------------------------------------------------------
# Primary regression tests (fixture-backed deterministic replay)
# ---------------------------------------------------------------------------


def test_caqnw9q2_production_pipeline_structure(tmp_path: Path) -> None:
    key = "CAQNW9Q2"
    expectations = _load_expectations(key)
    result = None

    try:
        result = replay_production_pipeline(key, tmp_path)
        structured_blocks = result["structured_blocks"]
        roles = [b.get("role") for b in structured_blocks]

        doc_exp = expectations.get("document", {})
        if doc_exp.get("expected_abstract_span"):
            assert "abstract" in roles, "No abstract role found in CAQNW9Q2"

        pages_exp = expectations.get("pages", {})
        for page_str, page_exp in pages_exp.items():
            page_blocks = [b for b in structured_blocks if str(b.get("page")) == page_str]
            page_roles = [b.get("role") for b in page_blocks]

            if "expected_non_body" in page_exp:
                for idx in page_exp["expected_non_body"]:
                    if idx < len(page_roles):
                        assert page_roles[idx] != "body_paragraph", (
                            f"Block {idx} on page {page_str} should not be body_paragraph, "
                            f"got {page_roles[idx]}"
                        )

            for rule in page_exp.get("expected_reference_rules", []):
                if rule.get("must_not_render_references_as_body"):
                    ref_bodies = [
                        b
                        for b in page_blocks
                        if b.get("role") == "body_paragraph"
                        and b.get("style_family") == "reference_like"
                    ]
                    assert len(ref_bodies) == 0, (
                        f"Reference-like blocks rendered as body_paragraph on page {page_str}"
                    )

            for rel in page_exp.get("expected_order_relations", []):
                before = rel["before_text"].lower()
                after = rel["after_text"].lower()
                rendered = result["rendered"].lower()
                bp = rendered.find(before)
                ap = rendered.find(after)
                if bp >= 0 and ap >= 0:
                    assert bp < ap, (
                        f"'{rel['before_text']}' must appear before '{rel['after_text']}'"
                    )
    except AssertionError:
        _dump_debug_bundle(key, result, tmp_path)
        raise


def test_dwqqk2yb_production_pipeline_figures(tmp_path: Path) -> None:
    key = "DWQQK2YB"
    expectations = _load_expectations(key)
    result = None

    try:
        result = replay_production_pipeline(key, tmp_path)

        doc_exp = expectations.get("document", {})
        min_rf = doc_exp.get("expected_reader_figure_count_min", 0)
        rf_count = len(result["reader_payload"].get("reader_figures", []))
        assert rf_count >= min_rf, f"Expected >= {min_rf} reader figures, got {rf_count}"

        pages_exp = expectations.get("pages", {})
        for page_str, page_exp in pages_exp.items():
            for obj in page_exp.get("expected_object_ownership", []):
                if obj.get("object_type") != "figure":
                    continue
                if obj.get("must_not_render_caption_blocks_as_body"):
                    structured = result["structured_blocks"]
                    page_blocks = [b for b in structured if str(b.get("page")) == page_str]
                    leaked = [
                        b
                        for b in page_blocks
                        if b.get("role") == "body_paragraph"
                        and f"Fig. {obj['figure_number']}" in str(b.get("text", ""))
                        and b.get("style_family") in ("legend_like", "figure_caption_like")
                    ]
                    assert len(leaked) == 0, (
                        f"Figure {obj['figure_number']} caption leaked into body_paragraph "
                        f"on page {page_str}"
                    )

        for invariant in expectations.get("expected_render_invariants", []):
            if invariant.get("type") == "no_duplicate_caption":
                import re as _re

                pattern = invariant["caption_regex"]
                matches = _re.findall(
                    rf"!\[\[render/figures/.*{pattern}.*\]\]",
                    result["rendered"],
                    _re.IGNORECASE,
                )
                assert len(matches) >= 1, f"No rendered figure matching '{pattern}' found"
    except AssertionError:
        _dump_debug_bundle(key, result, tmp_path)
        raise


def test_a8e7srvs_page_level_production_pipeline(tmp_path: Path) -> None:
    key = "A8E7SRVS"
    expectations = _load_expectations(key)
    result = None

    try:
        result = replay_production_pipeline(key, tmp_path)
        pages_exp = expectations.get("pages", {})

        for page_str, page_exp in pages_exp.items():
            for obj in page_exp.get("expected_object_ownership", []):
                otype = obj.get("object_type")
                if otype == "figure":
                    num = obj.get("figure_number")
                    rendered = result["rendered"]
                    assert (
                        f"Figure {num}" in rendered or f"Fig. {num}" in rendered
                    ), f"Figure {num} not found in rendered output"
                elif otype == "table":
                    num = obj.get("table_number")
                    assert f"Table {num}" in result["rendered"], (
                        f"Table {num} not found in rendered output"
                    )

        for page_str, page_exp in pages_exp.items():
            for cons in page_exp.get("expected_consumption", []):
                if cons.get("must_not_render_as_body"):
                    structured = result["structured_blocks"]
                    page_blocks = [b for b in structured if str(b.get("page")) == page_str]
                    hint = cons.get("block_id_comment", "").lower()
                    leaked = [
                        b
                        for b in page_blocks
                        if b.get("role") == "body_paragraph"
                        and hint in str(b.get("text", "")).lower()
                    ]
                    assert len(leaked) == 0, (
                        f"Content from '{cons['block_id_comment']}' leaked into "
                        f"body_paragraph on page {page_str}"
                    )

        for page_str, page_exp in pages_exp.items():
            for inv in page_exp.get("expected_render_invariants", []):
                if inv.get("type") == "before_text":
                    before = inv["before"].lower()
                    after = inv["after"].lower()
                    rendered = result["rendered"].lower()
                    bp = rendered.find(before)
                    ap = rendered.find(after)
                    if bp >= 0 and ap >= 0:
                        assert bp < ap, (
                            f"'{inv['before']}' must appear before '{inv['after']}'"
                        )
                elif inv.get("type") == "not_in_body":
                    text = inv["text_contains"].lower()
                    structured = result["structured_blocks"]
                    leaked = [
                        b
                        for b in structured
                        if b.get("role") == "body_paragraph"
                        and text in str(b.get("text", "")).lower()
                    ]
                    assert len(leaked) == 0, (
                        f"'{inv['text_contains']}' leaked into body_paragraph"
                    )
    except AssertionError:
        _dump_debug_bundle(key, result, tmp_path)
        raise


def test_gold_figure_merge_ownership_contracts(tmp_path: Path) -> None:
    manifest = _load_manifest()
    keys = [paper["paper_key"] for paper in manifest.get("papers", [])]
    failures: list[str] = []
    for key in keys:
        expectations = _load_expectations(key)
        ownership_rules = [
            obj
            for _page_str, obj in _iter_expected_object_ownership(expectations)
            if obj.get("object_type") == "figure"
            and (
                obj.get("asset_block_ids")
                or obj.get("must_not_claim_asset_block_ids")
            )
        ]
        if not ownership_rules:
            continue

        fixture_payload = FIXTURE_ROOT / key / "ocr_payload.json"
        fixture_meta = FIXTURE_ROOT / key / "source_metadata.json"
        if fixture_payload.exists() and fixture_meta.exists():
            result = replay_production_pipeline(key, tmp_path / key)
            reader_payload = result["reader_payload"]
        else:
            reader_payload = _load_reader_payload_from_vault(key)
        matched, ambiguous = _reader_figure_index(reader_payload)

        for obj in ownership_rules:
            figure_number = int(obj["figure_number"])
            expected_ids = set(obj.get("asset_block_ids", []))
            forbidden_ids = set(obj.get("must_not_claim_asset_block_ids", []))

            matched_item = matched.get(figure_number)
            ambiguous_item = ambiguous.get(figure_number)

            if expected_ids:
                if matched_item is None:
                    failures.append(
                        f"{key}: Figure {figure_number} not present in matched_figures; "
                        f"ambiguous={ambiguous_item is not None}"
                    )
                else:
                    actual_ids = set(matched_item.get("asset_block_ids", []))
                    if actual_ids != expected_ids:
                        failures.append(
                            f"{key}: Figure {figure_number} expected merged asset ids "
                            f"{sorted(expected_ids)}, got {sorted(actual_ids)}"
                        )

            if forbidden_ids:
                if matched_item is not None:
                    actual_ids = set(matched_item.get("asset_block_ids", []))
                    overlap = actual_ids.intersection(forbidden_ids)
                    if overlap:
                        failures.append(
                            f"{key}: Figure {figure_number} incorrectly claimed forbidden asset ids "
                            f"{sorted(overlap)}"
                        )
                if ambiguous_item is not None:
                    candidate_ids = set(ambiguous_item.get("asset_block_ids", []))
                    overlap = candidate_ids.intersection(forbidden_ids)
                    if overlap:
                        failures.append(
                            f"{key}: Figure {figure_number} still ambiguous over forbidden asset ids "
                            f"{sorted(overlap)}"
                        )

    if failures:
        pytest.fail("\n" + "\n".join(failures))


def test_dwqqk2yb_ownership_no_longer_mega_merges_same_page_assets(tmp_path: Path) -> None:
    result = replay_production_pipeline("DWQQK2YB", tmp_path)
    reader_payload = result["reader_payload"]
    matched, ambiguous = _reader_figure_index(reader_payload)

    fig2 = matched.get(2)
    fig4 = matched.get(4)

    assert fig2 is not None, "Fig 2 should be matched"
    assert fig2.get("page") == 38, "Fig 2 should be on page 38"
    assert fig4 is not None, "Fig 4 should be matched"
    assert fig4.get("page") == 41, "Fig 4 should be on page 41"
    # Fig 3 should at least be captured (ambiguous is acceptable for now;
    # the group-first figure inventory refactor will resolve its ownership)
    assert 3 in matched or 3 in ambiguous, "Fig 3 should be captured"


def test_dwqqk2yb_figure3_is_fully_owned_not_merely_captured(tmp_path: Path) -> None:
    """Gate 2 regression: DW Figure 3 must be strictly matched, not left ambiguous."""
    result = replay_production_pipeline("DWQQK2YB", tmp_path)
    reader_payload = result["reader_payload"]
    matched, ambiguous = _reader_figure_index(reader_payload)
    assert 3 in matched, f"Fig 3 should be matched, not left ambiguous. matched keys={list(matched.keys())}, ambiguous keys={list(ambiguous.keys())}"
    assert 3 not in ambiguous, "Fig 3 ambiguity is no longer acceptable after Gate 2"


def test_6fgdbfqn_same_page_narrow_caption_ownership(tmp_path: Path) -> None:
    key = "6FGDBFQN"
    expectations = _load_expectations(key)

    fixture_payload = FIXTURE_ROOT / key / "ocr_payload.json"
    fixture_meta = FIXTURE_ROOT / key / "source_metadata.json"
    if fixture_payload.exists() and fixture_meta.exists():
        result = replay_production_pipeline(key, tmp_path)
        reader_payload = result["reader_payload"]
    else:
        reader_payload = _load_reader_payload_from_vault(key)
    matched, ambiguous = _reader_figure_index(reader_payload)

    failures: list[str] = []
    for _page_str, obj in _iter_expected_object_ownership(expectations):
        if obj.get("object_type") != "figure":
            continue
        if not obj.get("asset_block_ids"):
            continue
        figure_number = int(obj["figure_number"])
        expected_ids = set(obj["asset_block_ids"])
        matched_item = matched.get(figure_number)
        ambiguous_item = ambiguous.get(figure_number)
        if matched_item is None:
            failures.append(
                f"{key}: Figure {figure_number} not matched; ambiguous={ambiguous_item is not None}"
            )
            continue
        actual_ids = set(matched_item.get("asset_block_ids", []))
        if actual_ids != expected_ids:
            failures.append(
                f"{key}: Figure {figure_number} expected {sorted(expected_ids)}, got {sorted(actual_ids)}"
            )

    if failures:
        pytest.fail("\n" + "\n".join(failures))


# ===========================================================================
# Secondary: env-driven audit tests (preserved from original)
#
# These require PAPERFORGE_REAL_OCR_VAULT set to a real vault path.
# Run with: pytest -m audit
# ===========================================================================

REAL_VAULT_ENV = "PAPERFORGE_REAL_OCR_VAULT"
REAL_KEYS_ENV = "PAPERFORGE_REAL_OCR_KEYS"

PROBLEM_KEYS = ["TSCKAVIS", "CAQNW9Q2", "A8E7SRVS", "K7R8PEKW", "DWQQK2YB", "M36WA39N"]
CONTROL_KEYS = ["SAN9AYVR", "2GN9LMCW", "7C8829BD"]


def _real_ocr_vault() -> Path | None:
    value = os.environ.get(REAL_VAULT_ENV)
    return Path(value) if value else None


def _real_ocr_keys() -> list[str]:
    value = os.environ.get(REAL_KEYS_ENV, "")
    return [k.strip() for k in value.split(",") if k.strip()]


def _get_vault() -> Path:
    vault = _real_ocr_vault()
    if vault is None:
        pytest.skip(f"Set {REAL_VAULT_ENV} and {REAL_KEYS_ENV} for real OCR integration tests")
    return vault


def _get_ocr_root(vault: Path) -> Path:
    return vault / "System" / "PaperForge" / "ocr"


def _get_keys() -> list[str]:
    keys = _real_ocr_keys()
    if not keys:
        vault = _real_ocr_vault()
        if vault is None:
            pytest.skip(f"Set {REAL_VAULT_ENV} and {REAL_KEYS_ENV} for real OCR integration tests")
        return PROBLEM_KEYS + CONTROL_KEYS
    return keys


def _paper_root(ocr_root: Path, key: str) -> Path:
    return ocr_root / key


def _structured_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "structure" / "blocks.structured.jsonl"


def _fulltext_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "fulltext.md"


def _health_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "health" / "ocr_health.json"


def _reader_figures_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "structure" / "reader_figures.json"


def _figure_inventory_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "structure" / "figure_inventory.json"


def _metadata_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "metadata" / "resolved_metadata.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _require_artifacts(ocr_root: Path, key: str) -> None:
    missing = [
        str(path)
        for path in [
            _structured_path(ocr_root, key),
            _fulltext_path(ocr_root, key),
            _health_path(ocr_root, key),
            _metadata_path(ocr_root, key),
        ]
        if not path.exists()
    ]
    if missing:
        pytest.skip(f"OCR artifacts not present for {key}: {missing}")


@pytest.fixture(scope="session")
def _vault() -> Path:
    return _get_vault()


@pytest.fixture(scope="session")
def _ocr_root(_vault: Path) -> Path:
    return _get_ocr_root(_vault)


@pytest.fixture(scope="session")
def _all_keys() -> list[str]:
    return _get_keys()


@pytest.fixture(scope="session")
def rebuilt_real_papers(_vault: Path, _all_keys: list[str]) -> dict:
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    result = run_derived_rebuild_for_keys(_vault, _all_keys)
    assert result.get("rebuild_count", 0) >= 1, result
    return result


@pytest.mark.audit
@pytest.mark.parametrize("key", PROBLEM_KEYS + CONTROL_KEYS)
def test_real_paper_artifacts_exist(_ocr_root: Path, key: str) -> None:
    _require_artifacts(_ocr_root, key)


@pytest.mark.audit
def test_real_paper_rebuild_runs(rebuilt_real_papers: dict) -> None:
    assert rebuilt_real_papers.get("rebuild_count", 0) >= 1


BODY_RETENTION = {
    "CAQNW9Q2": {"min_body": 27, "max_non_body_insert": 8},
    "A8E7SRVS": {"min_body": 42, "max_non_body_insert": 8},
    "K7R8PEKW": {"min_body": 60, "max_non_body_insert": 8},
    "TSCKAVIS": {"min_body": 48, "max_non_body_insert": 12},
    "DWQQK2YB": {"min_body": 25, "max_non_body_insert": 12},
    "M36WA39N": {"min_body": 45, "max_non_body_insert": 8},
}


def _role_texts(blocks: list[dict], role: str) -> list[str]:
    return [str(block.get("text") or block.get("block_content") or "") for block in blocks if block.get("role") == role]


@pytest.mark.audit
@pytest.mark.parametrize("key", sorted(BODY_RETENTION))
def test_problem_papers_retain_body_and_avoid_mass_insert_suppression(
    rebuilt_real_papers: dict, _ocr_root: Path, key: str
) -> None:
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))
    roles = [block.get("role") for block in blocks]
    thresholds = BODY_RETENTION[key]

    assert roles.count("body_paragraph") >= thresholds["min_body"], roles.count("body_paragraph")
    assert roles.count("non_body_insert") <= thresholds["max_non_body_insert"], roles.count("non_body_insert")


@pytest.mark.audit
def test_a8e7srvs_no_frontmatter_body_before_introduction(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "A8E7SRVS"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))

    intro_idx = len(blocks)
    for idx, b in enumerate(blocks):
        if (
            b.get("role") in ("section_heading", "subsection_heading")
            and "introduction" in str(b.get("text", "")).lower()
        ):
            intro_idx = idx
            break

    assert intro_idx < len(blocks), "No 'Introduction' heading found in A8E7SRVS"

    before_intro = blocks[:intro_idx]
    fm_bodies = [
        b
        for b in before_intro
        if b.get("role") == "body_paragraph"
        and any(
            s in (b.get("text") or "").lower()
            for s in [
                "received:",
                "accepted:",
                "published online",
                "copyright",
                "each author certifies",
                "icmje conflict",
            ]
        )
    ]
    assert len(fm_bodies) == 0, (
        f"Frontmatter-side text leaked into body_paragraph before Introduction "
        f"(block_ids={[b['block_id'] for b in fm_bodies]})"
    )


@pytest.mark.audit
def test_tsckavis_frontmatter_and_key_points_are_callout(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "TSCKAVIS"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))
    fulltext = _fulltext_path(_ocr_root, key).read_text(encoding="utf-8", errors="replace")
    heading_text = "\n".join(
        _role_texts(blocks, "section_heading")
        + _role_texts(blocks, "subsection_heading")
        + _role_texts(blocks, "sub_subsection_heading")
    ).lower()

    assert "review article" not in heading_text
    assert "steve stegen" not in heading_text
    assert "geert carmeliet" not in heading_text

    assert "key points" in fulltext.lower()
    assert "[!NOTE]" in fulltext
    assert "skeletal stem and progenitor cells display a high metabolic flexibility" in fulltext.lower()

    meta = _read_json(_metadata_path(_ocr_root, key))
    assert len(meta.get("title", {}).get("value", "")) > 10, meta.get("title")
    assert len(meta.get("authors", {}).get("value", [])) > 0, meta.get("authors")
    assert meta.get("authors_display", "") != "", f"authors_display is empty: {meta}"
    assert meta.get("year", {}).get("value", 0), meta.get("year")
    assert meta.get("journal", {}).get("value", ""), meta.get("journal")
    assert meta.get("doi", {}).get("value", ""), meta.get("doi")


@pytest.mark.audit
def test_tsckavis_no_table_display_as_heading(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "TSCKAVIS"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))

    heading_text = "\n".join(
        _role_texts(blocks, "section_heading")
        + _role_texts(blocks, "subsection_heading")
        + _role_texts(blocks, "sub_subsection_heading")
    ).lower()

    assert "published online" not in heading_text, "'Published online' leaked into heading roles for TSCKAVIS"

    body_with_fig = [
        b
        for b in blocks
        if b.get("role") == "body_paragraph"
        and b.get("text", "").strip().lower().startswith("fig. ")
        and any(c.isdigit() for c in b.get("text", "")[:10])
    ]
    assert len(body_with_fig) == 0, (
        f"Figure-like text in body_paragraph: block_ids={[b['block_id'] for b in body_with_fig]}"
    )


CONTROL_MIN_BODY = {
    "SAN9AYVR": 213,
    "2GN9LMCW": 25,
    "7C8829BD": 65,
}


@pytest.mark.audit
@pytest.mark.parametrize("key", sorted(CONTROL_MIN_BODY))
def test_control_papers_keep_body_and_tail_stability(rebuilt_real_papers: dict, _ocr_root: Path, key: str) -> None:
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))
    roles = [block.get("role") for block in blocks]
    fulltext = _fulltext_path(_ocr_root, key).read_text(encoding="utf-8", errors="replace")

    assert roles.count("body_paragraph") >= CONTROL_MIN_BODY[key]
    assert any(w in fulltext for w in ["References", "references", "REFERENCE", "Bibliography"]), (
        "Tail reference marker not found"
    )


@pytest.mark.audit
@pytest.mark.parametrize("key", PROBLEM_KEYS)
def test_problem_papers_keep_reference_roles_and_exclude_legend_family_from_body(
    rebuilt_real_papers: dict,
    _ocr_root: Path,
    key: str,
) -> None:
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))

    assert any(block.get("role") == "reference_item" for block in blocks)
    assert any(block.get("style_family") for block in blocks), f"No style_family artifacts found for {key}"
    leaked = []
    for block in blocks:
        if block.get("role") != "body_paragraph":
            continue
        style_family = block.get("style_family")
        if style_family not in {"legend_like", "table_caption_like", "reference_like"}:
            continue
        text = str(block.get("text") or "")
        raw_label = str(block.get("raw_label") or "")
        zone = str(block.get("zone") or "")
        if style_family == "reference_like":
            leaked.append(block)
            continue
        if (
            style_family in {"legend_like", "table_caption_like"}
            and zone == "display_zone"
            and raw_label == "figure_title"
        ):
            continue
        leaked.append(block)

    assert not leaked, f"Residual non-body leaks remain for {key}: {[b.get('block_id') for b in leaked][:8]}"


@pytest.mark.audit
def test_dwqqk2yb_post_preproof_not_body(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "DWQQK2YB"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))

    corr_bodies = [
        b
        for b in blocks
        if b.get("role") == "body_paragraph"
        and any(
            phrase in (b.get("text") or "").lower()
            for phrase in ["corresponding author", "correspondence", "highlights"]
        )
    ]
    assert len(corr_bodies) == 0, (
        f"Post-preproof frontmatter leaked into body_paragraph: block_ids={[b['block_id'] for b in corr_bodies]}"
    )

    total_refs = sum(1 for b in blocks if b.get("role") == "reference_item")
    body_zone_refs = sum(1 for b in blocks if b.get("zone") == "body_zone" and b.get("role") == "reference_item")
    assert body_zone_refs < total_refs, f"All {total_refs} reference items remain in body_zone for {key}"


@pytest.mark.audit
def test_m36wa39n_editorial_furniture_not_body(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "M36WA39N"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))
    body_text = "\n".join(str(b.get("text", "")) for b in blocks if b.get("role") == "body_paragraph").lower()

    forbidden = ["edited by:", "reviewed by:", "correspondence:", "specialty section:", "citation:"]
    for phrase in forbidden:
        assert phrase not in body_text, f"'{phrase}' found in body_paragraph for {key}"

    tail_phrases = ["ethics statement", "author contributions"]
    for phrase in tail_phrases:
        assert phrase not in body_text, f"'{phrase}' collapsed into body_paragraph for {key}"


@pytest.mark.audit
def test_caqnw9q2_heading_preservation_and_ref_classification(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "CAQNW9Q2"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))

    headings = [
        b for b in blocks if b.get("role") in ("section_heading", "subsection_heading", "sub_subsection_heading")
    ]
    assert len(headings) >= 5, f"Too few headings ({len(headings)}) for {key}"

    heading_text = "\n".join(_role_texts(blocks, "section_heading")).lower()
    assert "conclusion" in heading_text, f"'Conclusion' heading not found for {key}"

    ref_items = [b for b in blocks if b.get("role") == "reference_item"]
    ref_like = [b for b in ref_items if b.get("style_family") == "reference_like"]
    assert len(ref_like) > 0, (
        f"No reference items have reference_like style_family for {key} "
        f"(style families present: {set(b.get('style_family') for b in ref_items)})"
    )


@pytest.mark.audit
def test_tsckavis_key_points_render_as_callout(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "TSCKAVIS"
    _require_artifacts(_ocr_root, key)
    fulltext = _fulltext_path(_ocr_root, key).read_text(encoding="utf-8", errors="replace")

    kp_lower = fulltext.lower()
    assert "key points" in kp_lower, "Key points heading not found in fulltext -- content was silently dropped"
    assert "[!NOTE]" in fulltext, "Key points not rendered as a callout block ([!NOTE]) in fulltext"
    assert "skeletal stem and progenitor cells display a high metabolic flexibility" in kp_lower, (
        "Key points body content missing from fulltext"
    )


@pytest.mark.audit
def test_tsckavis_table_display_does_not_render_as_body_heading(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "TSCKAVIS"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))
    fulltext = _fulltext_path(_ocr_root, key).read_text(encoding="utf-8", errors="replace")

    heading_roles = ("section_heading", "subsection_heading", "sub_subsection_heading")
    heading_texts = [str(b.get("text", "")).lower() for b in blocks if b.get("role") in heading_roles]

    for ht in heading_texts:
        assert "table 1" not in ht, f"Table display content leaked into heading role: '{ht[:80]}'"

    heading_pattern = re.compile(r"^#{1,6}\s+.*table\s+1", re.MULTILINE | re.IGNORECASE)
    heading_matches = heading_pattern.findall(fulltext)
    assert len(heading_matches) == 0, (
        f"Table display content rendered as markdown heading in fulltext: {heading_matches[:3]}"
    )


@pytest.mark.audit
def test_caqnw9q2_old_style_references_gain_reference_like_family(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "CAQNW9Q2"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))

    ref_items = [b for b in blocks if b.get("role") == "reference_item"]
    assert len(ref_items) >= 50, f"Expected many reference items for {key}, got {len(ref_items)}"

    ref_like = [b for b in ref_items if b.get("style_family") == "reference_like"]
    ref_ratio = len(ref_like) / max(len(ref_items), 1)
    assert ref_ratio >= 0.8, (
        f"Only {len(ref_like)}/{len(ref_items)} ({ref_ratio:.0%}) reference items have reference_like "
        f"style_family for {key}. Style families present: "
        f"{set(b.get('style_family') for b in ref_items)}"
    )


@pytest.mark.audit
def test_m36wa39n_same_page_tail_nonref_and_references_split_correctly(
    rebuilt_real_papers: dict, _ocr_root: Path
) -> None:
    key = "M36WA39N"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))

    tail_nonref_bodies = [
        b
        for b in blocks
        if b.get("role") == "body_paragraph"
        and any(
            phrase in (b.get("text") or "").lower()
            for phrase in [
                "conflict of interest",
                "publisher's note",
                "copyright",
                "the remaining authors declare",
            ]
        )
    ]
    assert len(tail_nonref_bodies) == 0, (
        f"Tail non-reference content leaked into body_paragraph for {key}: "
        f"block_ids={[b['block_id'] for b in tail_nonref_bodies]}"
    )


@pytest.mark.audit
def test_real_paper_legends_do_not_silently_disappear_from_object_inventory(
    rebuilt_real_papers: dict, _ocr_root: Path
) -> None:
    expected_min_visible_objects = {
        "TSCKAVIS": 2,
        "CAQNW9Q2": 2,
        "A8E7SRVS": 2,
        "DWQQK2YB": 2,
        "M36WA39N": 2,
    }
    for key, min_visible in expected_min_visible_objects.items():
        _require_artifacts(_ocr_root, key)
        inventory = _read_json(_figure_inventory_path(_ocr_root, key))
        reader_payload = _read_json(_reader_figures_path(_ocr_root, key))
        fulltext = _fulltext_path(_ocr_root, key).read_text(encoding="utf-8", errors="replace")

        artifact_visible = (
            len(inventory.get("matched_figures", []))
            + len(inventory.get("held_figures", []))
            + len(inventory.get("ambiguous_figures", []))
            + len(inventory.get("unmatched_legends", []))
            + len(inventory.get("unresolved_clusters", []))
        )
        assert artifact_visible >= min_visible, (
            f"{key}: expected at least {min_visible} visible figure artifacts, found {artifact_visible}"
        )
        assert len(reader_payload.get("reader_figures", [])) >= min_visible, (
            f"{key}: expected at least {min_visible} reader figures, "
            f"found {len(reader_payload.get('reader_figures', []))}"
        )
        rendered_count = fulltext.count("> **Figure") + fulltext.count("![[render/figures/figure_")
        assert rendered_count >= min_visible, (
            f"{key}: expected at least {min_visible} rendered figure outputs, found {rendered_count}"
        )


@pytest.mark.audit
def test_reader_figures_persist_after_rebuild(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    for key in PROBLEM_KEYS + CONTROL_KEYS:
        rfp = _reader_figures_path(_ocr_root, key)
        assert rfp.exists(), f"reader_figures.json not found for {key}"


@pytest.mark.audit
def test_reader_coverage_metrics_in_health(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    for key in PROBLEM_KEYS + CONTROL_KEYS:
        health = _read_json(_health_path(_ocr_root, key))
        assert "figure_reader_coverage_total" in health, f"{key}: missing figure_reader_coverage_total"
        assert "figure_reader_coverage_accounted" in health, f"{key}: missing figure_reader_coverage_accounted"
        assert "figure_reader_coverage_ratio" in health, f"{key}: missing figure_reader_coverage_ratio"
        assert health["figure_reader_coverage_total"] >= 0, f"{key}: negative reader coverage total"


@pytest.mark.audit
def test_fulltext_has_no_debug_artifact_names(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    forbidden = ["unmatched_legend_", "unresolved_cluster_", "orphan_", "asset_block_id", "legend_block_id"]
    for key in PROBLEM_KEYS + CONTROL_KEYS:
        _require_artifacts(_ocr_root, key)
        fulltext = _fulltext_path(_ocr_root, key).read_text(encoding="utf-8", errors="replace")
        for token in forbidden:
            assert token not in fulltext, f"{key}: debug artifact '{token}' leaked into fulltext"


def test_caqnw9q2_page7_conclusion_survives_same_page_reference_boundary(tmp_path: Path) -> None:
    result = replay_production_pipeline("CAQNW9Q2", tmp_path)
    blocks = result["structured_blocks"]

    conclusion_blocks = [
        b for b in blocks
        if b.get("page") == 7 and "conclusion" in str(b.get("text") or "").lower()
    ]
    assert conclusion_blocks, "Expected CAQNW9Q2 page-7 conclusion block"
    assert all(b.get("zone") == "body_zone" for b in conclusion_blocks)
    assert all(b.get("role") in {"section_heading", "body_paragraph"} for b in conclusion_blocks)


def test_dwqqk2yb_preproof_page_one_is_absent_from_structured_blocks(tmp_path: Path) -> None:
    result = replay_production_pipeline("DWQQK2YB", tmp_path)
    blocks = result["structured_blocks"]
    assert not any(int(b.get("page", 0) or 0) == 1 for b in blocks)


def test_k7r8pekw_margin_band_publishers_stay_noise(tmp_path: Path) -> None:
    result = replay_production_pipeline("K7R8PEKW", tmp_path)
    watermark_blocks = [
        b for b in result["structured_blocks"]
        if "Downloaded from" in str(b.get("text") or "")
    ]

    assert watermark_blocks, "Expected at least one publisher watermark block"
    assert all(b.get("role") == "noise" for b in watermark_blocks)


def test_dwqqk2yb_first_surviving_page_keeps_title_and_authors(tmp_path: Path) -> None:
    result = replay_production_pipeline("DWQQK2YB", tmp_path)
    page2_blocks = [b for b in result["structured_blocks"] if int(b.get("page", 0) or 0) == 2]

    title_block = next(
        b for b in page2_blocks if "Magnetoresponsive Stem Cell Spheroid" in str(b.get("text") or "")
    )
    authors_block = next(
        b for b in page2_blocks if "Ami Yoo" in str(b.get("text") or "") or "Ami Yoo" in str(b.get("block_content") or "")
    )

    assert title_block.get("role") == "paper_title"
    assert authors_block.get("role") in {"authors", "frontmatter_support"}
    assert title_block.get("zone") == "frontmatter_main_zone"
    assert authors_block.get("zone") == "frontmatter_main_zone"


def test_dwqqk2yb_first_surviving_page_support_blocks_stay_frontmatter_support(tmp_path: Path) -> None:
    result = replay_production_pipeline("DWQQK2YB", tmp_path)
    page2_blocks = [b for b in result["structured_blocks"] if int(b.get("page", 0) or 0) == 2]

    equal_block = next(b for b in page2_blocks if "contributed equally" in str(b.get("text") or "").lower())
    corr_block = next(b for b in page2_blocks if "corresponding author" in str(b.get("text") or "").lower())

    assert equal_block.get("role") == "frontmatter_support"
    assert corr_block.get("role") == "frontmatter_support"


def test_caqnw9q2_page1_correspondence_is_not_frontmatter_noise(tmp_path: Path) -> None:
    result = replay_production_pipeline("CAQNW9Q2", tmp_path)
    blocks = result["structured_blocks"]
    candidates = [
        b for b in blocks
        if b.get("page") == 1 and "correspondence" in str(b.get("text") or "").lower()
    ]
    assert candidates, "Expected a correspondence-related block on CAQNW9Q2 page 1"
    assert any(b.get("role") == "frontmatter_support" for b in candidates)
    assert not all(b.get("role") == "frontmatter_noise" for b in candidates)
