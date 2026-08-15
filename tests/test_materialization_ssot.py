"""Architecture guard — the materialization contract's single source of
truth (ADR-0002, P0-A corrective).

OCR judging lives in ONE place: paperforge/materialization/ocr.py.
lineage.py may only DELEGATE to it (thin wrappers + hash identity); it
must never reimplement lifecycle / artifact / publish judgment.  This test
pins that boundary so a future edit cannot silently reintroduce a second
definition (the 2026-08-15 BLOCKER: a stale duplicate block at the tail of
lineage.py shadowed the thin wrappers at runtime).
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LINEAGE = REPO / "paperforge" / "lineage.py"
MATERIALIZATION_OCR = REPO / "paperforge" / "materialization" / "ocr.py"

# Judgment implementations that belong ONLY in materialization/ocr.py.
FORBIDDEN_IN_LINEAGE = (
    "def _ocr_meta_lifecycle",
    "def _publish_state",
    "def _read_ocr_meta",
    "def _queued_is_zombie",
    "def _is_old_pipeline",
    "def _blocks_valid",
    "def _tree_shape",
    "def _role_index_shape",
    "def _json_valid",
    "OCR_DETAIL_",
)


def test_lineage_has_no_ocr_judgment_implementation() -> None:
    src = LINEAGE.read_text(encoding="utf-8")
    offenders = [f for f in FORBIDDEN_IN_LINEAGE if f in src]
    assert not offenders, (
        "lineage.py must not reimplement OCR judging — the single source of "
        "truth is paperforge/materialization/ocr.py (ADR-0002). Found: "
        + ", ".join(offenders)
    )


def test_lineage_wrappers_delegate_to_materialization() -> None:
    src = LINEAGE.read_text(encoding="utf-8")
    # _probe_ocr_state / _ocr_detail must import their judging from
    # materialization.ocr — never re-derive locally.
    assert "from paperforge.materialization.ocr import" in src
    assert "top_state" in src
    assert "provenance_state" in src
    assert "from paperforge.materialization.ocr import detail" in src


def test_materialization_ocr_owns_the_judging() -> None:
    src = MATERIALIZATION_OCR.read_text(encoding="utf-8")
    for fn in (
        "def top_state(",
        "def detail(",
        "def ocr_artifact_detail(",
        "def raw_state(",
        "def meta_lifecycle(",
        "def publish_marker_state(",
    ):
        assert fn in src, f"materialization/ocr.py must define {fn}"
