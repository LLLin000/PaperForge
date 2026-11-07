"""Real-paper invariants for the read-only layout plan.

Skipped when the owner's production vault is not present (CI). The plan must
be able to describe a real page without inventing or dropping blocks.
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

import pytest

VAULT = Path(os.environ.get("PAPERFORGE_VAULT", r"D:/L/OB/Literature-hub"))
OCR_ROOT = VAULT / "System/PaperForge/ocr"
PAPERS = ("2332GHPT", "2AGGSMVQ", "24A2QUAH")


def _load_rows(key: str) -> list[dict] | None:
    paper = OCR_ROOT / key
    raw_path = paper / "canonical/blocks.raw.jsonl"
    meta_path = paper / "raw/source_metadata.json"
    if not raw_path.exists() or not meta_path.exists():
        return None
    sys_path = str(Path(__file__).resolve().parents[1])
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    rows, _ = build_structured_blocks(raw, source_metadata=meta, normalize_mode="seed_only")
    return rows


@pytest.mark.skipif(not OCR_ROOT.exists(), reason="requires the owner's production vault")
@pytest.mark.parametrize("key", PAPERS)
def test_real_paper_plan_covers_every_block_once(key: str) -> None:
    from paperforge.worker.layout import build_layout_plan, collect_block_refs

    rows = _load_rows(key)
    if rows is None:
        pytest.skip(f"{key} not present in the vault")

    plan = build_layout_plan(rows)
    seen: list[str] = []
    for page in plan.pages:
        for region in page.regions:
            seen.extend(region.members)

    assert len(seen) == len(set(seen)), "a block is owned by two regions"
    assert set(seen) == {ref.uid for ref in collect_block_refs(rows)}
    assert len(plan.pages) == max(int(row.get("page", 0) or 0) for row in rows)


@pytest.mark.skipif(not OCR_ROOT.exists(), reason="requires the owner's production vault")
@pytest.mark.parametrize("key", PAPERS)
def test_real_paper_plan_is_shuffle_invariant_and_read_only(key: str) -> None:
    from paperforge.worker.layout import build_layout_plan

    rows = _load_rows(key)
    if rows is None:
        pytest.skip(f"{key} not present in the vault")

    snapshot = copy.deepcopy(rows)
    forward = build_layout_plan(rows).to_dict()
    backward = build_layout_plan(list(reversed(rows))).to_dict()

    # `order_inversion` and `cross_column_jump` compare against the OCR order,
    # which is the evidence that shuffling changes; everything else must hold.
    geometry_kinds = {"missing_geometry", "ambiguous_column", "overlapping_membership", "container_leak"}
    for first, second in zip(forward["pages"], backward["pages"]):
        assert first["regions"] == second["regions"]
        def geometry(page: dict) -> list[dict]:
            return [c for c in page["conflicts"] if c["kind"] in geometry_kinds]

        assert geometry(first) == geometry(second)
        held = set(first["holds"]) | set(second["holds"])
        assert [uid for uid in first["order"] if uid not in held] == [
            uid for uid in second["order"] if uid not in held
        ]
    assert rows == snapshot
