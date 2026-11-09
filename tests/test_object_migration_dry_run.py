"""Identity/claims diff used by the migration dry-run."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "object_migration_dry_run",
    Path(__file__).resolve().parents[1] / "scripts/dev/object_migration_dry_run.py",
)
assert _SPEC and _SPEC.loader
module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(module)



import hashlib
import json
import tempfile
from pathlib import Path


def _make_paper(tmp_path: Path, files: list[str]) -> Path:
    paper = tmp_path / "paper"
    paper.mkdir()
    for rel in files:
        p = paper / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(rel.encode())
    return paper
def test_delivery_gate_checks_assets_and_renders_for_manifest_ids(tmp_path: Path):
    paper = tmp_path / "paper"
    manifest = {
        "figures": ["figure_new", "missing_asset", "missing_render"],
        "assets": [
            str(paper / "assets/figures/figure_new.jpg"),
            str(paper / "assets/figures/missing_render.jpg"),
        ],
        "render": [
            str(paper / "render/figures/figure_new.md"),
            str(paper / "render/figures/missing_asset.md"),
        ],
    }

    result = module._delivery_diff(paper, manifest, {}, {}, [], [])

    assert result["manifest_delivery"] == {
        "figure_ids": ["figure_new", "missing_asset", "missing_render"],
        "missing_assets": ["missing_asset"],
        "missing_renders": ["missing_render"],
    }




def test_plan_unique_rename_hash_backup(tmp_path):
    paper = _make_paper(tmp_path, ["render/figures/old.md", "assets/figures/old.jpg"])
    old = {
        "entries": 1, "ids": ["old"], "duplicate_extra": 0,
        "anchors": {(1, "L1"): "old"}, "claims": {"old": []},
        "entries_detail": [{"figure_id": "old", "figure_number": 1, "page": 1, "legend_block_id": "L1", "text": "cap", "assets": []}],
    }
    new = {
        "figures": [{"figure_id": "new", "page": 1, "legend_block_id": "L1", "text": "cap"}],
        "tables": [],
        "rows": [],
        "manifest": {"figures": ["new"], "tables": [], "orphans": [], "render": [str(paper / "render/figures/new.md")], "assets": [str(paper / "assets/figures/new.jpg")]},
    }
    identity = module._identity_diff(old, new["figures"])
    plan = module._plan_key(paper, old, new, identity)
    renames = [op for op in plan["operations"] if op["op"] == "rename"]
    r = next(op for op in renames if op["old_path"] == "render/figures/old.md")
    assert r["old_sha256"] == hashlib.sha256(b"render/figures/old.md").hexdigest()
    backup_paths = {f["path"] for f in plan["backup"]["files"]}
    assert "render/figures/old.md" in backup_paths


def test_plan_duplicate_old_id_hold_approval(tmp_path):
    paper = _make_paper(tmp_path, ["render/figures/old.md"])
    old = {
        "entries": 2, "ids": ["old", "old"], "duplicate_extra": 1,
        "anchors": {(1, "L1"): "old", (2, "L2"): "old"}, "claims": {"old": []},
        "entries_detail": [
            {"figure_id": "old", "figure_number": 1, "page": 1, "legend_block_id": "L1", "text": "", "assets": []},
            {"figure_id": "old", "figure_number": 2, "page": 2, "legend_block_id": "L2", "text": "", "assets": []},
        ],
    }
    new = {
        "figures": [
            {"figure_id": "new1", "page": 1, "legend_block_id": "L1", "text": ""},
            {"figure_id": "new2", "page": 2, "legend_block_id": "L2", "text": ""},
        ],
        "tables": [],
        "rows": [],
        "manifest": {"figures": ["new1", "new2"], "tables": [], "orphans": [], "render": [str(paper / "render/figures/new1.md"), str(paper / "render/figures/new2.md")], "assets": []},
    }
    identity = module._identity_diff(old, new["figures"])
    plan = module._plan_key(paper, old, new, identity)
    assert plan["status"] == module.STATUS_HOLD
    deletes = [op for op in plan["operations"] if op["op"] == "delete_candidate" and op.get("kind") == "figure"]
    assert deletes and all(op["status"] == module.STATUS_REQUIRES_APPROVAL for op in deletes)


def test_plan_assetless_embed_removal(tmp_path):
    paper = _make_paper(tmp_path, ["fulltext.md", "render/figures/old.md"])
    (paper / "fulltext.md").write_text("![[render/figures/old.md]]\n", encoding="utf-8")
    old = {
        "entries": 1, "ids": ["old"], "duplicate_extra": 0,
        "anchors": {(1, "L1"): "old"}, "claims": {"old": ["b1"]},
        "entries_detail": [{"figure_id": "old", "figure_number": 1, "page": 1, "legend_block_id": "L1", "text": "cap", "assets": [{"block_id": "b1", "page": 1, "bbox": None}]}],
    }
    new = {
        "figures": [],
        "tables": [],
        "rows": [],
        "manifest": {"figures": [], "tables": [], "orphans": [], "render": [], "assets": []},
    }
    identity = module._identity_diff(old, new["figures"])
    plan = module._plan_key(paper, old, new, identity)
    embed_deletes = [op for op in plan["operations"] if op["op"] == "delete_candidate" and op.get("kind") == "embed"]
    assert embed_deletes and all(op["status"] == module.STATUS_REQUIRES_APPROVAL for op in embed_deletes)


def test_plan_caption_present_unmatched_m2(tmp_path):
    paper = _make_paper(tmp_path, ["fulltext.md", "render/figures/old.md"])
    (paper / "fulltext.md").write_text("![[render/figures/old.md]]\n", encoding="utf-8")
    old = {
        "entries": 1, "ids": ["old"], "duplicate_extra": 0,
        "anchors": {(1, "L1"): "old"}, "claims": {"old": ["b1"]},
        "entries_detail": [{"figure_id": "old", "figure_number": 1, "page": 1, "legend_block_id": "L1", "text": "cap", "assets": [{"block_id": "b1", "page": 1, "bbox": None}]}],
    }
    new = {
        "figures": [],
        "tables": [],
        "rows": [{"role": "figure_caption", "text": "cap"}],
        "manifest": {"figures": [], "tables": [], "orphans": [], "render": [], "assets": []},
    }
    identity = module._identity_diff(old, new["figures"])
    plan = module._plan_key(paper, old, new, identity)
    assert plan["status"] == module.STATUS_M2_REVIEW


def test_plan_dangling_embed_target(tmp_path):
    paper = _make_paper(tmp_path, ["fulltext.md"])
    (paper / "fulltext.md").write_text("![[render/figures/old.md]]\n", encoding="utf-8")
    old = {
        "entries": 1, "ids": ["old"], "duplicate_extra": 0,
        "anchors": {(1, "L1"): "old"}, "claims": {"old": []},
        "entries_detail": [{"figure_id": "old", "figure_number": 1, "page": 1, "legend_block_id": "L1", "text": "cap", "assets": []}],
    }
    # map old->new but manifest lacks render target
    new = {
        "figures": [{"figure_id": "new", "page": 1, "legend_block_id": "L1", "text": "cap"}],
        "tables": [],
        "rows": [],
        "manifest": {"figures": ["new"], "tables": [], "orphans": [], "render": [], "assets": []},
    }
    identity = module._identity_diff(old, new["figures"])
    plan = module._plan_key(paper, old, new, identity)
    assert plan["dangling"]


def test_plan_collision_detection(tmp_path):
    paper = _make_paper(tmp_path, ["render/figures/old.md", "render/figures/new.md"])
    old = {
        "entries": 1, "ids": ["old"], "duplicate_extra": 0,
        "anchors": {(1, "L1"): "old"}, "claims": {"old": []},
        "entries_detail": [{"figure_id": "old", "figure_number": 1, "page": 1, "legend_block_id": "L1", "text": "cap", "assets": []}],
    }
    new = {
        "figures": [{"figure_id": "new", "page": 1, "legend_block_id": "L1", "text": "cap"}],
        "tables": [],
        "rows": [],
        "manifest": {"figures": ["new"], "tables": [], "orphans": [], "render": [str(paper / "render/figures/new.md")], "assets": []},
    }
    identity = module._identity_diff(old, new["figures"])
    plan = module._plan_key(paper, old, new, identity)
    assert plan["collisions"]
def test_identity_diff_maps_by_page_and_legend_anchor() -> None:
    old = {
        "entries": 3,
        "ids": ["figure_002", "figure_002", "figure_003"],
        "duplicate_extra": 1,
        "anchors": {(4, "9"): "figure_002", (4, "10"): "figure_002", (5, "2"): "figure_003"},
        "claims": {"figure_002": ["8"], "figure_003": ["3"]},
    }
    new = [
        {"figure_id": "figure_002", "page": 4, "legend_block_id": "9", "matched_assets": [{"block_id": "8"}]},
        {"figure_id": "figure_002_10", "page": 4, "legend_block_id": "10", "matched_assets": [{"block_id": "4"}]},
        {"figure_id": "figure_003", "page": 5, "legend_block_id": "2", "matched_assets": [{"block_id": "3"}]},
    ]
    diff = module._identity_diff(old, new)
    assert diff["new"]["entries"] == 3
    assert diff["new"]["duplicate_extra"] == 0
    assert ["figure_002", "figure_002_10"] in diff["renamed"]
    assert diff["claims_changed"][0]["new_assets"] == ["4"]
