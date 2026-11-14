import hashlib
import importlib.util
import json
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "scripts" / "dev" / "figure_quality_eval.py"
SPEC = importlib.util.spec_from_file_location("figure_quality_eval", MOD_PATH)
assert SPEC and SPEC.loader
FQE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FQE)


def _make_pdf(path: Path, pages: int) -> None:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"page {i + 1}")
    doc.save(str(path))
    doc.close()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _setup_paper(ocr_root, key, vault, pdf, expected_pages, expected_fp, stale_meta_locator=None):
    paper_dir = ocr_root / key
    (paper_dir / "raw").mkdir(parents=True, exist_ok=True)
    (paper_dir / "structure").mkdir(parents=True, exist_ok=True)
    locator = f"[[System/Zotero/storage/{pdf.parent.name}/{pdf.name}]]"
    meta = {
        "source_pdf": stale_meta_locator or locator,
        "page_count": expected_pages,
        "raw_version": {"pdf_fingerprint": expected_fp},
    }
    (paper_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (paper_dir / "raw" / "raw_meta.json").write_text(json.dumps({"pdf_fingerprint": expected_fp}), encoding="utf-8")
    (paper_dir / "raw" / "source_metadata.json").write_text(json.dumps({"source_pdf": locator}), encoding="utf-8")
    target = vault / "System" / "Zotero" / "storage" / pdf.parent.name / pdf.name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(pdf.read_bytes())



def _make_snapshot(snapshot_dir: Path, pdf: Path, figure_id: str | None = None) -> dict:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    manifest = {"assets": [], "render": []}
    if figure_id:
        asset = snapshot_dir / "assets" / "figures" / f"{figure_id}.jpg"
        render = snapshot_dir / "render" / "figures" / f"{figure_id}.md"
        asset.parent.mkdir(parents=True, exist_ok=True)
        render.parent.mkdir(parents=True, exist_ok=True)
        image = FQE.Image.new("RGB", (8, 8), color="white")
        image.save(asset, "JPEG")
        render.write_text(f"![[assets/figures/{figure_id}.jpg]]\n", encoding="utf-8")
        manifest = {
            "assets": [f"assets/figures/{figure_id}.jpg"],
            "render": [f"render/figures/{figure_id}.md"],
        }
        for path in (asset, render):
            files[path.relative_to(snapshot_dir).as_posix()] = {
                "sha256": _sha256(path), "bytes": path.stat().st_size,
            }
    fulltext = snapshot_dir / "fulltext.md"
    fulltext.write_text(
        f"![[render/figures/{figure_id}.md]]\n" if figure_id else "",
        encoding="utf-8",
    )
    files["fulltext.md"] = {"sha256": _sha256(fulltext), "bytes": fulltext.stat().st_size}
    source_pdf_sha256 = _sha256(pdf)
    fingerprint = "sha256:" + hashlib.sha256(
        json.dumps(
            {"source_pdf_sha256": source_pdf_sha256, "manifest": manifest, "files": files},
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "fingerprint": fingerprint,
        "directory": str(snapshot_dir),
        "source_pdf_sha256": source_pdf_sha256,
        "manifest": manifest,
        "files": files,
    }

def test_supplemental_source_selected_and_matching(tmp_path):
    vault = tmp_path / "vault"
    ocr_root = tmp_path / "ocr"
    key = "2ZBAK9VY"
    supp = tmp_path / "supp.pdf"
    _make_pdf(supp, 15)
    _setup_paper(ocr_root, key, vault, supp, 15, _sha256(supp), stale_meta_locator="[[System/Zotero/storage/OLD/main.pdf]]")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    res = FQE.run_key(vault, ocr_root, key, out_dir)
    case = res["case"]
    assert not case.get("source_mismatch", False)
    assert case.get("status") != "SOURCE_MISMATCH"
    provenance = case["source_provenance"]
    assert provenance["expected"] == provenance["observed"]
    assert provenance["observed"]["page_count"] == 15
    assert provenance["observed"]["fingerprint"] == _sha256(supp)


def test_genuine_fingerprint_mismatch(tmp_path):
    vault = tmp_path / "vault"
    ocr_root = tmp_path / "ocr"
    key = "MISMATCH"
    pdf = tmp_path / "paper.pdf"
    _make_pdf(pdf, 5)
    _setup_paper(ocr_root, key, vault, pdf, 5, "sha256:" + "0" * 64)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    res = FQE.run_key(vault, ocr_root, key, out_dir)
    case = res["case"]
    assert case.get("source_mismatch") is True
    assert case.get("status") == "SOURCE_MISMATCH"
    assert case["observed"]["fingerprint"] == _sha256(pdf)
    assert case["expected"]["fingerprint"] == "sha256:" + "0" * 64


def test_page_count_mismatch_is_reported_as_source_mismatch(tmp_path):
    vault = tmp_path / "vault"
    ocr_root = tmp_path / "ocr"
    pdf = tmp_path / "paper.pdf"
    _make_pdf(pdf, 5)
    _setup_paper(ocr_root, "PAGES", vault, pdf, 4, _sha256(pdf))

    result = FQE.run_key(vault, ocr_root, "PAGES", tmp_path / "out")

    assert result["case"]["status"] == "SOURCE_MISMATCH"
    assert result["case"]["expected"]["page_count"] == 4
    assert result["case"]["observed"]["page_count"] == 5


def test_missing_source_identity_fields_fail_closed():
    observed = {
        "path": "source.pdf",
        "page_count": 15,
        "fingerprint": "sha256:" + "a" * 64,
    }
    for expected in (
        {"path": None, "page_count": 15, "fingerprint": observed["fingerprint"]},
        {"path": "other.pdf", "page_count": 15, "fingerprint": observed["fingerprint"]},
        {"path": "source.pdf", "page_count": None, "fingerprint": observed["fingerprint"]},
        {"path": "source.pdf", "page_count": 15, "fingerprint": None},
    ):
        assert FQE._source_identity_mismatch(expected, observed)


def test_evaluator_uses_isolated_rebuild_replay(monkeypatch, tmp_path):
    vault = tmp_path / "vault"
    ocr_root = tmp_path / "ocr"
    pdf = tmp_path / "paper.pdf"
    _make_pdf(pdf, 1)
    _setup_paper(ocr_root, "REBUILD", vault, pdf, 1, _sha256(pdf))
    rebuilt = {
        "figures": [],
        "tables": [],
        "rows": [],
        "manifest": {},
        "figure_inventory": {"unmatched_legends": [], "unmatched_assets": []},
        "snapshot": _make_snapshot(tmp_path / "snapshot", pdf),
    }
    calls = {"rebuild": 0, "fast": 0}

    def rebuild(*args, **kwargs):
        calls["rebuild"] += 1
        return rebuilt

    def fast(*args):
        calls["fast"] += 1
        return rebuilt

    monkeypatch.setattr(FQE.DRY, "_rebuild_replay", rebuild)
    monkeypatch.setattr(FQE.DRY, "_new_replay", fast)
    monkeypatch.setattr(FQE, "structural_baseline", lambda *args: {})

    result = FQE.run_key(vault, ocr_root, "REBUILD", tmp_path / "out")

    assert calls == {"rebuild": 1, "fast": 0}
    assert result["entry"].get("error") is None


def test_cross_page_review_uses_rebuild_crop_and_asset_page(monkeypatch, tmp_path):
    vault = tmp_path / "vault"
    ocr_root = tmp_path / "ocr"
    pdf = tmp_path / "paper.pdf"
    _make_pdf(pdf, 2)
    _setup_paper(ocr_root, "CROSSPAGE", vault, pdf, 2, _sha256(pdf))
    snapshot = _make_snapshot(tmp_path / "snapshot", pdf, "figure_001")
    figure = {
        "figure_id": "figure_001",
        "page": 1,
        "matched_assets": [{
            "page": 2, "block_id": "asset-2", "bbox": [10, 10, 80, 80],
        }],
    }
    rebuilt = {
        "figures": [figure],
        "tables": [],
        "rows": [
            {"page": 1, "page_width": 100, "page_height": 100, "role": "figure_caption"},
            {
                "page": 2, "page_width": 200, "page_height": 200, "role": "media_asset",
                "block_id": "asset-2", "bbox": [10, 10, 80, 80],
            },
        ],
        "manifest": {},
        "figure_inventory": {"unmatched_legends": [], "unmatched_assets": []},
        "embeds": [{
            "kind": "figures", "target": "render/figures/figure_001.md",
            "object_id": "figure_001",
        }],
        "snapshot": snapshot,
    }
    calls = {"rebuild": 0, "fast": 0}
    rendered_pages = []
    crop_pages = []
    monkeypatch.setattr(FQE.DRY, "audit_key", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        FQE.DRY, "_rebuild_replay",
        lambda *args, **kwargs: (calls.__setitem__("rebuild", calls["rebuild"] + 1) or rebuilt),
    )
    monkeypatch.setattr(
        FQE.DRY, "_new_replay",
        lambda *args: (calls.__setitem__("fast", calls["fast"] + 1) or rebuilt),
    )
    monkeypatch.setattr(FQE, "structural_baseline", lambda *args: {})
    monkeypatch.setattr(
        FQE, "_render_page_with_overlays",
        lambda pdf_path, page, *args: rendered_pages.append(page),
    )


    result = FQE.run_key(vault, ocr_root, "CROSSPAGE", tmp_path / "out")

    assert calls == {"rebuild": 1, "fast": 0}
    assert set(rendered_pages) == {1, 2}
    assert crop_pages == []
    assert result["case"]["rebuilt_delivery"]["figure_states"]["figure_001"] == "RESOLVED"


def test_image_evidence_fingerprints_include_snapshot_pages_crops_and_renders(tmp_path):
    review_dir = tmp_path / "review_context"
    snapshot_dir = tmp_path / "snapshot"
    page = review_dir / "page_003.jpg"
    crop = snapshot_dir / "assets" / "figures" / "figure_001.jpg"
    render = snapshot_dir / "render" / "figures" / "figure_001.md"
    unrelated = review_dir / "notes.jpg"
    page.parent.mkdir(parents=True)
    crop.parent.mkdir(parents=True)
    render.parent.mkdir(parents=True)
    page.write_bytes(b"page evidence")
    crop.write_bytes(b"crop evidence")
    render.write_bytes(b"render evidence")
    unrelated.write_bytes(b"not reviewed evidence")
    snapshot = {
        "files": {
            path.relative_to(snapshot_dir).as_posix(): {"sha256": _sha256(path)}
            for path in (crop, render)
        }
    }

    fingerprints = FQE._image_evidence_fingerprints(review_dir, snapshot)

    assert fingerprints == {
        "page_images": {"page_003.jpg": _sha256(page)},
        "crop_images": {"figure_001.jpg": _sha256(crop)},
        "render_files": {"figure_001.md": _sha256(render)},
    }

def test_source_override_cannot_bypass_recorded_identity(monkeypatch, tmp_path):
    vault = tmp_path / "vault"
    ocr_root = tmp_path / "ocr"
    main_pdf = tmp_path / "main.pdf"
    supplemental_pdf = tmp_path / "supplement.pdf"
    _make_pdf(main_pdf, 15)
    _make_pdf(supplemental_pdf, 8)
    _setup_paper(
        ocr_root, "SOURCE_OVERRIDE", vault, supplemental_pdf, 15, _sha256(supplemental_pdf)
    )
    source_override = {
        "source_pdf": str(main_pdf.resolve()),
        "page_count": 15,
        "fingerprint": _sha256(main_pdf),
    }
    replay_called = False

    def replay(*args, **kwargs):
        nonlocal replay_called
        replay_called = True
        raise AssertionError("mismatched source must not be replayed")

    monkeypatch.setattr(FQE.DRY, "_rebuild_replay", replay)
    result = FQE.run_key(
        vault, ocr_root, "SOURCE_OVERRIDE", tmp_path / "out", source_override=source_override
    )

    case = result["case"]
    provenance = case["source_provenance"]
    assert case["status"] == "SOURCE_MISMATCH"
    assert provenance["recorded"]["path"].endswith("supplement.pdf")
    assert provenance["recorded"]["fingerprint"] == _sha256(supplemental_pdf)
    assert provenance["expected"]["path"] == str(main_pdf.resolve())
    assert provenance["observed"]["fingerprint"] == _sha256(main_pdf)
    assert provenance["checks"] == {
        "recorded_identity_match": False,
        "selected_identity_match": True,
    }
    assert replay_called is False


def test_source_override_replays_when_recorded_identity_matches(monkeypatch, tmp_path):
    vault = tmp_path / "vault"
    ocr_root = tmp_path / "ocr"
    main_pdf = tmp_path / "main.pdf"
    _make_pdf(main_pdf, 15)
    _setup_paper(ocr_root, "SOURCE_OVERRIDE", vault, main_pdf, 15, _sha256(main_pdf))
    paper_dir = ocr_root / "SOURCE_OVERRIDE"
    source_locator = json.loads(
        (paper_dir / "raw" / "source_metadata.json").read_text(encoding="utf-8")
    )["source_pdf"]
    source_override = {
        "source_pdf": source_locator,
        "page_count": 15,
        "fingerprint": _sha256(main_pdf),
    }
    rebuilt = {
        "figures": [],
        "tables": [],
        "rows": [],
        "manifest": {},
        "figure_inventory": {"unmatched_legends": [], "unmatched_assets": []},
        "snapshot": _make_snapshot(tmp_path / "snapshot", main_pdf),
    }
    replay_source = {}

    def replay(v, root, key, source_pdf_override=None, snapshot_root=None):
        replay_source["path"] = source_pdf_override
        replay_source["snapshot_root"] = snapshot_root
        return rebuilt

    monkeypatch.setattr(FQE.DRY, "_rebuild_replay", replay)
    monkeypatch.setattr(FQE.DRY, "audit_key", lambda *args, **kwargs: {})
    monkeypatch.setattr(FQE, "structural_baseline", lambda *args: {})
    result = FQE.run_key(
        vault, ocr_root, "SOURCE_OVERRIDE", tmp_path / "out", source_override=source_override
    )

    case = result["case"]
    assert case.get("status") != "SOURCE_MISMATCH"
    assert case["structural_pass"] is True
    assert case["visual_pass"] is False
    assert case["accepted"] is False
    assert case["acceptance_blocked_by"] == ["human_visual_review_incomplete"]
    assert case["source_provenance"]["checks"] == {
        "recorded_identity_match": True,
        "selected_identity_match": True,
    }
    assert replay_source["path"] == Path(case["source_provenance"]["recorded"]["path"])
def test_review_labels_are_bound_to_actual_rebuild_snapshot(monkeypatch, tmp_path):
    vault = tmp_path / "vault"
    ocr_root = tmp_path / "ocr"
    pdf = tmp_path / "paper.pdf"
    _make_pdf(pdf, 1)
    _setup_paper(ocr_root, "SNAPSHOT", vault, pdf, 1, _sha256(pdf))
    snapshot = _make_snapshot(tmp_path / "snapshot", pdf, "figure_001")
    figure = {
        "figure_id": "figure_001",
        "page": 1,
        "legend_block_id": "caption-1",
        "matched_assets": [{"block_id": "asset-1", "page": 1, "bbox": [10, 10, 80, 80]}],
    }
    rebuilt = {
        "figures": [figure],
        "tables": [],
        "rows": [
            {
                "page": 1, "page_width": 100, "page_height": 100,
                "role": "figure_caption", "block_id": "caption-1",
                "bbox": [10, 10, 80, 20],
            },
            {
                "page": 1, "page_width": 100, "page_height": 100,
                "role": "media_asset", "block_id": "asset-1",
                "bbox": [10, 10, 80, 80],
            },
        ],
        "manifest": {},
        "figure_inventory": {"matched_figures": [figure], "unmatched_legends": [], "unmatched_assets": []},
        "embeds": [{"kind": "figures", "target": "render/figures/figure_001.md", "object_id": "figure_001"}],
        "snapshot": snapshot,
    }
    audit_inputs = {}

    def replay(_vault, _root, _key, source_pdf_override=None, snapshot_root=None):
        audit_inputs["snapshot_root"] = snapshot_root
        return rebuilt

    def audit(_vault, _root, _key, plan=False, replay=None):
        audit_inputs["replay"] = replay
        return {}

    monkeypatch.setattr(FQE.DRY, "_rebuild_replay", replay)
    monkeypatch.setattr(FQE.DRY, "audit_key", audit)
    monkeypatch.setattr(FQE, "structural_baseline", lambda *args: {})
    monkeypatch.setattr(FQE, "_render_page_with_overlays", lambda *args: None)


    result = FQE.run_key(vault, ocr_root, "SNAPSHOT", tmp_path / "out")

    labels_path = Path(result["out_dir"]) / "labels.jsonl"
    label = json.loads(labels_path.read_text(encoding="utf-8").splitlines()[0])
    assert audit_inputs["replay"] is rebuilt
    assert audit_inputs["snapshot_root"] is not None
    assert result["case"]["snapshot_fingerprint"] == snapshot["fingerprint"]
    assert label["snapshot_fingerprint"] == snapshot["fingerprint"]
    assert label["source_pdf_sha256"] == _sha256(pdf)
    assert label["asset_sha256"] == snapshot["files"]["assets/figures/figure_001.jpg"]["sha256"]
    assert label["render_sha256"] == snapshot["files"]["render/figures/figure_001.md"]["sha256"]
    assert label["fulltext_sha256"] == snapshot["files"]["fulltext.md"]["sha256"]
    assert result["case"]["rebuilt_delivery"]["figure_states"]["figure_001"] == "RESOLVED"

    label.update({
        "reviewer": "reviewer-1",
        "caption_ok": True,
        "panels_ok": True,
        "crop_ok": True,
        "delivery_ok": True,
        "asset_sha256": "sha256:stale",
    })
    labels_path.write_text(json.dumps(label) + "\n", encoding="utf-8")
    rerun = FQE.run_key(vault, ocr_root, "SNAPSHOT", tmp_path / "out")
    assert rerun["case"]["visual_review_status"] == "UNKNOWN_STALE_LABELS"
    assert rerun["case"]["visual_label_counts"]["reviewed"] == 0
    assert rerun["case"]["visual_label_counts"]["stale"] == 1


def test_rebuild_snapshot_is_addressed_by_inputs_and_refuses_tampering(tmp_path):
    pdf = tmp_path / "paper.pdf"
    _make_pdf(pdf, 1)
    source = tmp_path / "source"
    (source / "canonical").mkdir(parents=True)
    (source / "raw").mkdir()
    (source / "index").mkdir()
    (source / "canonical" / "blocks.raw.jsonl").write_text("{}\n", encoding="utf-8")
    (source / "raw" / "source_metadata.json").write_text(
        json.dumps({"source_pdf": str(pdf)}), encoding="utf-8"
    )
    (source / "meta.json").write_text(json.dumps({"source_pdf": str(pdf)}), encoding="utf-8")
    (source / "index" / "result-hash.txt").write_text("old-hash\n", encoding="utf-8")

    rebuilt = tmp_path / "rebuilt"
    for relative in (
        "structure/figure_inventory.json",
        "structure/table_inventory.json",
        "structure/blocks.structured.jsonl",
        "index/result-hash.txt",
        "meta.json",
        "fulltext.md",
        "assets/figures/figure_001.jpg",
        "render/figures/figure_001.md",
    ):
        path = rebuilt / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("materialized\n", encoding="utf-8")
    manifest = {
        "figures": ["figure_001"],
        "tables": [],
        "orphans": [],
        "assets": [str(rebuilt / "assets/figures/figure_001.jpg")],
        "render": [str(rebuilt / "render/figures/figure_001.md")],
    }
    snapshot_root = tmp_path / "snapshots"

    first = FQE.DRY._persist_rebuild_snapshot(rebuilt, snapshot_root, "PAPER", source, pdf, manifest)
    second = FQE.DRY._persist_rebuild_snapshot(rebuilt, snapshot_root, "PAPER", source, pdf, manifest)

    assert first["fingerprint"] == second["fingerprint"]
    assert first["files"]["assets/figures/figure_001.jpg"]["sha256"] == _sha256(
        Path(first["directory"]) / "assets/figures/figure_001.jpg"
    )
    (Path(first["directory"]) / "assets/figures/figure_001.jpg").write_bytes(b"tampered")
    try:
        FQE.DRY._persist_rebuild_snapshot(rebuilt, snapshot_root, "PAPER", source, pdf, manifest)
    except RuntimeError as exc:
        assert "snapshot content mismatch" in str(exc)
    else:
        assert False, "tampered snapshot was reused"