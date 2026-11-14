import hashlib
import json
from pathlib import Path

from PIL import Image
import pytest

from scripts.dev.figure_review_html import build
from scripts.dev.figure_review_apply import apply

FIELDS = ("caption_ok", "panels_ok", "crop_ok", "delivery_ok")
BINDINGS = ("snapshot_fingerprint", "source_pdf_sha256", "asset_sha256", "render_sha256", "fulltext_sha256")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def setup(tmp_path):
    evidence = tmp_path / "evidence"
    work = tmp_path / "work"
    snap = tmp_path / "snap"
    for rel in ("assets/figures", "renders", ""):
        (snap / rel).mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (4, 4), "red").save(snap / "assets/figures/crop.jpg")
    (work / "A/review_context").mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (4, 4), "blue").save(work / "A/review_context/page_001.jpg")
    (snap / "renders/one.txt").write_text("render text", encoding="utf-8")
    (snap / "fulltext.md").write_text("page=1 render/figures/one.png", encoding="utf-8")
    rows = [
        {"key": "A", "kind": "matched_figure", "figure_id": "f1", "page": 1, "block_id": None, "current_assets": "1", "snapshot_fingerprint": "s", "source_pdf_sha256": "p", "asset_sha256": "a", "render_sha256": "r", "fulltext_sha256": "t", **dict.fromkeys(FIELDS, None), "reviewer": "", "reviewed_at": None, "notes": ""},
        {"key": "A", "kind": "unmatched_legend", "figure_id": "", "page": 1, "block_id": 2, "current_assets": "", "snapshot_fingerprint": "s", "source_pdf_sha256": "p", "asset_sha256": None, "render_sha256": None, "fulltext_sha256": "t", **dict.fromkeys(FIELDS, None), "reviewer": "", "reviewed_at": None, "notes": ""},
        {"key": "A", "kind": "matched_figure", "figure_id": "f2", "page": 1, "block_id": None, "current_assets": "1", "snapshot_fingerprint": "s", "source_pdf_sha256": "p", "asset_sha256": "missing", "render_sha256": "r", "fulltext_sha256": "t", **dict.fromkeys(FIELDS, None), "reviewer": "", "reviewed_at": None, "notes": ""},
    ]
    labels = evidence / "A/labels.jsonl"
    labels.parent.mkdir(parents=True)
    labels.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    zero = evidence / "B"
    zero.mkdir(parents=True)
    census = {"papers": [
        {"key": "A", "evidence_dir": str(evidence / "A"), "rebuilt_state": {"snapshot_path": str(snap), "snapshot_fingerprint": "s", "source_pdf_sha256": "p", "delivery": {"figures": {"f1": {"state": "RESOLVED", "asset_path": "assets/figures/crop.jpg", "render_path": "renders/one.txt", "asset_sha256": "a", "render_sha256": "r"}, "f2": {"state": "RESOLVED", "asset_path": "assets/figures/absent.jpg", "render_path": "renders/one.txt"}}}}, "historical_state": {}},
        {"key": "B", "evidence_dir": str(zero), "rebuilt_state": {}, "historical_state": {}},
    ]}
    census_path = tmp_path / "census.json"
    write_json(census_path, census)
    sample = tmp_path / "sample.json"
    write_json(sample, {"selected_keys": ["A", "B"]})
    pack = tmp_path / "pack"
    pack.mkdir()
    write_json(pack / "index.json", {})
    out = tmp_path / "html"
    build(census_path, sample, pack, work, out, 1)
    return census_path, pack, out, labels, rows


def test_generator_embeds_evidence_and_reports_zero_label(tmp_path, capsys):
    _, _, out, _, _ = setup(tmp_path)
    text = (out / "batch-1.html").read_text(encoding="utf-8")
    assert 'data:image/jpeg;base64,' in text
    assert "http://" not in text and "https://" not in text and "<script src=" not in text
    assert "evidence missing: crop" in text
    assert "<img src=\"placeholder" not in text
    assert "B" in capsys.readouterr().out


def test_apply_binding_refusal_is_atomic_and_valid_verdict_preserves_other_row(tmp_path):
    census, pack, out, labels, initial = setup(tmp_path)
    before = labels.read_bytes()
    wrong = dict(initial[0], asset_sha256="changed", caption_ok=True)
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps(wrong) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="asset_sha256"):
        apply(census, [bad], out, False)
    assert labels.read_bytes() == before
    current = [json.loads(x) for x in labels.read_text().splitlines()]
    current[1]["crop_ok"] = True
    current[1]["reviewer"] = "Existing"
    labels.write_text("".join(json.dumps(x) + "\n" for x in current), encoding="utf-8")
    patch_row = dict(initial[0], caption_ok=True, reviewer="Reviewer", reviewed_at="now")
    patch = tmp_path / "valid.jsonl"
    patch.write_text(json.dumps(patch_row) + "\n", encoding="utf-8")
    apply(census, [patch], out)
    saved = [json.loads(x) for x in labels.read_text().splitlines()]
    assert saved[0]["caption_ok"] is True and saved[0]["panels_ok"] is None
    assert saved[1]["crop_ok"] is True and saved[1]["reviewer"] == "Existing"


def test_apply_refuses_stale_census_manifest(tmp_path):
    census, _, out, _, _ = setup(tmp_path)
    write_json(out / "manifest.json", {"census_sha256": "sha256:stale"})
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="stale manifest"):
        apply(census, [empty], out)
