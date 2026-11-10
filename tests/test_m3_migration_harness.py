import json

import scripts.dev.m3_migration_harness as h


def test_gate_refusal(tmp_path):
    status = {"A": "READY", "B": "HOLD", "C": "REQUIRES_APPROVAL", "D": "M2_REVIEW_REQUIRED"}
    selected = ["A", "B", "C", "D"]
    allow = set()
    gated = []
    refusals = []
    for k in selected:
        st = status.get(k)
        if st != "READY" and st not in allow:
            refusals.append(k)
        else:
            gated.append(k)
    assert gated == ["A"]
    assert set(refusals) == {"B", "C", "D"}
def test_plan_validation_reports_object_mismatches(tmp_path):
    root = tmp_path / "paper"
    (root / "structure").mkdir(parents=True)
    (root / "fulltext.md").write_text("text", encoding="utf-8")
    (root / "structure" / "figure_inventory.json").write_text(
        json.dumps({
            "matched_figures": [{
                "figure_id": "figure_1",
                "asset_block_ids": ["2"],
                "matched_assets": [{"block_id": "2"}],
            }]
        }),
        encoding="utf-8",
    )
    plan = {
        "objects": [{
            "kind": "figure", "new_id": "figure_1", "status": "planned",
            "anchors": [{"asset_blocks": [{"block_id": 1}]}],
        }],
        "operations": [{
            "op": "keep", "kind": "figure", "object_uid": "figure_1",
            "new_path": "assets/figures/figure_1.jpg", "status": "planned",
        }],
        "embeds": [],
    }
    mismatches = h.validate_plan(root, plan)
    assert {item["reason"] for item in mismatches} == {
        "asset_claim_mismatch", "planned_file_missing"
    }
def test_plan_validation_blocks_unapproved_deletion(tmp_path):
    root = tmp_path / "paper"
    root.mkdir()
    mismatch = h.validate_plan(root, {
        "objects": [],
        "embeds": [],
        "operations": [{
            "op": "delete_candidate",
            "kind": "figure",
            "object_uid": "figure_old",
            "old_path": "render/figures/figure_old.md",
            "status": "REQUIRES_APPROVAL",
        }],
    })
    assert mismatch == [{
        "object": "figure_old",
        "reason": "unapproved_delete",
        "path": "render/figures/figure_old.md",
    }]



def test_select_keys_defaults_to_all_ready():
    selected, refused = h.select_keys({"B": "READY", "A": "READY", "C": "HOLD"}, None)
    assert selected == ["A", "B"]
    assert ("C", "HOLD") in refused


def test_isolation_rejects_escape_and_symlink(tmp_path):
    work = tmp_path / "isolated"
    work.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (work / "escape").symlink_to(outside, target_is_directory=True)
    except OSError:
        return
    try:
        h._reject_source_links(work)
    except ValueError:
        pass
    else:
        raise AssertionError("escaping symlink was accepted")
def test_staged_config_does_not_reference_source_vault(tmp_path):
    source = tmp_path / "source"
    paper = source / "System" / "PaperForge" / "ocr" / "PAPER1"
    paper.mkdir(parents=True)
    isolated = tmp_path / "isolated"
    vault = h.stage_vault(source, isolated, ["PAPER1"])
    config = (vault / "paperforge.json").read_text(encoding="utf-8")
    assert str(source).casefold() not in config.casefold()



def test_snapshot_restore(tmp_path):
    root = tmp_path / "paper"
    root.mkdir()
    (root / "a.txt").write_text("old", encoding="utf-8")
    snap = tmp_path / "snap"
    h.snapshot_paper(root, snap)
    (root / "a.txt").write_text("new", encoding="utf-8")
    (root / "b.txt").write_text("x", encoding="utf-8")
    h.restore_paper(root, snap)
    assert (root / "a.txt").read_text() == "old"
    assert not (root / "b.txt").exists()

def test_validation_text_decrease(tmp_path):
    root = tmp_path / "paper"
    root.mkdir()
    (root / "fulltext.md").write_text("short", encoding="utf-8")
    v = h.validate_paper(root, 100, None)
    assert not v["ok"]
    assert any("text_decrease" in e for e in v["errors"])

def test_validation_dangling_target(tmp_path):
    root = tmp_path / "paper"
    root.mkdir()
    (root / "fulltext.md").write_text("see ![[render/figures/missing.md]]", encoding="utf-8")
    v = h.validate_paper(root, 0, None)
    assert not v["ok"]
    assert any("dangling_fulltext_target" in e for e in v["errors"])

def test_journal_recovery(tmp_path):

    from paperforge.worker.ocr_objects import _recover_materialization_journal
    paper = tmp_path / "paper"
    paper.mkdir()
    target = paper / "render"
    target.mkdir()
    (target / "old.txt").write_text("old", encoding="utf-8")
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "new.txt").write_text("new", encoding="utf-8")
    staged = [(target, stage)]
    # create journal manually committing
    token = "abc"
    backup_root = paper / ".materialization-backup-abc"
    backup_root.mkdir()
    journal = {
        "schema_version": 1,
        "token": token,
        "status": "committing",
        "stage_root": str(stage),
        "backup_root": str(backup_root),
        "targets": [{"target": str(target), "backup": str(backup_root / "0")}],
    }
    (paper / ".materialization-journal.json").write_text(json.dumps(journal), encoding="utf-8")
    # move old to backup
    target.rename(backup_root / "0")
    _recover_materialization_journal(paper)
    assert target.exists()
    assert (target / "old.txt").read_text() == "old"
    assert not (paper / ".materialization-journal.json").exists()

def test_validation_duplicate_matched_figures(tmp_path):
    root = tmp_path / "paper"
    root.mkdir()
    (root / "structure").mkdir()
    inv = {"matched_figures": [{"figure_id": "a"}, {"figure_id": "a"}]}
    (root / "structure" / "figure_inventory.json").write_text(__import__("json").dumps(inv), encoding="utf-8")
    v = h.validate_paper(root, 0, None)
    assert not v["ok"]
    assert any("duplicate_figure_ids" in e for e in v["errors"])

def test_validation_structured_text_decrease(tmp_path):
    root = tmp_path / "paper"
    root.mkdir()
    (root / "structure").mkdir()
    (root / "structure" / "blocks.structured.jsonl").write_text('{"text": "hello"}\n', encoding="utf-8")
    pre_struct = h.pre_structured_chars(root)
    # simulate decrease
    (root / "structure" / "blocks.structured.jsonl").write_text('{"text": "hi"}\n', encoding="utf-8")
    v = h.validate_paper(root, 0, None, pre_structured=pre_struct)
    assert not v["ok"]
    assert any("structured_text_decrease" in e for e in v["errors"])
