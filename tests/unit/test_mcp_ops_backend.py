"""Unit tests for Python MCP ops backend upgrades & friction fixes."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from paperforge.memory.builder import build_for_keys
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import ensure_schema
from paperforge.worker.asset_index import atomic_write_index, build_envelope, get_index_path
from tests.conftest import canonical_test_config


def _run_cli(vault: Path, argv: list[str], *, stdin_text: str | None = None) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(vault), *argv],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.stdout.strip(), (
        f"Expected JSON on stdout (rc={proc.returncode}); stderr={proc.stderr!r}"
    )
    payload = json.loads(proc.stdout)
    return proc.returncode, payload


def _setup_multipage_non_ocr_vault(tmp_path: Path, *, build_db: bool = True) -> Path:
    import pymupdf

    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    canonical_test_config(vault, system_dir=".paperforge")

    pf = vault / ".paperforge"
    zot_dir = pf / "Zotero" / "storage"
    (zot_dir / "ST01").mkdir(parents=True)
    (zot_dir / "ST02").mkdir(parents=True)

    pdf1 = zot_dir / "ST01" / "study1.pdf"
    with pymupdf.open() as doc:
        for i in range(1, 5):
            page = doc.new_page(width=600, height=800)
            page.insert_text((72, 100), f"Introduction section on page {i}.\nPEMF 75 Hz parameter window.")
        doc.save(pdf1)

    pdf2 = zot_dir / "ST02" / "study2.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page(width=600, height=800)
        page.insert_text((72, 100), "Second paper content.")
        doc.save(pdf2)

    for key, dom in (("NOOCR001", "Ortho"), ("DONE0002", "Spine")):
        ws = vault / "Resources" / "Literature" / dom / f"{key} - Study"
        ws.mkdir(parents=True, exist_ok=True)
        (ws / f"{key}.md").write_text(f'---\nzotero_key: "{key}"\ndomain: "{dom}"\n---\n', encoding="utf-8")

    items = [
        {
            "key": "NOOCR001",
            "zotero_key": "NOOCR001",
            "citation_key": "lin2026pemf",
            "title": "PEMF Cartilage Study",
            "domain": "Ortho",
            "collections": ["Ortho/Cartilage"],
            "collection_path": "Ortho/Cartilage",
            "has_pdf": True,
            "pdf_path": "storage:ST01/study1.pdf",
            "ocr_status": "pending",
            "paper_root": "Resources/Literature/Ortho/NOOCR001 - Study/",
            "main_note_path": "Resources/Literature/Ortho/NOOCR001 - Study/NOOCR001.md",
            "note_path": "Resources/Literature/Ortho/NOOCR001 - Study/NOOCR001.md",
        },
        {
            "key": "DONE0002",
            "zotero_key": "DONE0002",
            "citation_key": "chen2025spine",
            "title": "Spine Fusion Study",
            "domain": "Spine",
            "collections": ["Spine/Fusion"],
            "collection_path": "Spine/Fusion",
            "has_pdf": True,
            "pdf_path": "storage:ST02/study2.pdf",
            "ocr_status": "done",
            "paper_root": "Resources/Literature/Spine/DONE0002 - Study/",
            "main_note_path": "Resources/Literature/Spine/DONE0002 - Study/DONE0002.md",
            "note_path": "Resources/Literature/Spine/DONE0002 - Study/DONE0002.md",
        },
        {
            "key": "NOPDF003",
            "zotero_key": "NOPDF003",
            "citation_key": "nopdf2025",
            "title": "Abstract Only Paper",
            "domain": "Ortho",
            "collections": ["Ortho/Cartilage"],
            "collection_path": "Ortho/Cartilage",
            "has_pdf": False,
            "pdf_path": "",
            "ocr_status": "pending",
        },
    ]
    atomic_write_index(get_index_path(vault), build_envelope(items))
    if build_db:
        build_for_keys(vault)
    return vault


def test_read_non_ocr_pdf_pages_max_chars_and_json(tmp_path: Path) -> None:
    vault = _setup_multipage_non_ocr_vault(tmp_path)

    rc, res = _run_cli(vault, ["read", "NOOCR001", "--pages", "2-3", "--json"])
    assert rc == 0
    assert res["ok"] is True
    data = res["data"]
    assert data["paper_key"] == "NOOCR001"
    assert data["source"] == "native_pdf"
    assert data["page_count"] == 4
    assert data["pages_returned"] == [2, 3]
    assert data["truncated"] is False
    assert "--- Page 2 ---" in data["content"]
    assert "--- Page 3 ---" in data["content"]
    assert "--- Page 1 ---" not in data["content"]
    assert "page 2" in data["content"]

    # Truncation with --max-chars
    rc2, res2 = _run_cli(vault, ["read", "NOOCR001", "--pages", "1-4", "--max-chars", "45", "--json"])
    assert rc2 == 0
    assert res2["data"]["truncated"] is True
    assert len(res2["data"]["content"]) == 45

    # No readable source returns PATH_NOT_FOUND
    rc3, res3 = _run_cli(vault, ["read", "NOPDF003", "--pages", "1", "--json"])
    assert rc3 == 1
    assert res3["ok"] is False
    assert res3["error"]["code"] == "PATH_NOT_FOUND"


def test_memory_card_refine_with_input_file_and_stdin_chinese_quotes(tmp_path: Path) -> None:
    vault = _setup_multipage_non_ocr_vault(tmp_path)

    # 1. File input with JSON containing Chinese quotes
    json_file = tmp_path / "refine.json"
    json_file.write_text(
        json.dumps(
            {
                "facet": "methods_params",
                "content": "关键参数：“75 Hz PEMF” 每天 2 小时，连续 14 天 [p.2]。",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    rc, res = _run_cli(vault, ["memory-card", "refine", "NOOCR001", "--input", str(json_file), "--json"])
    assert rc == 0
    assert res["ok"] is True
    assert res["data"]["updated"]["facet"] == "methods_params"
    assert "“75 Hz PEMF”" in res["data"]["updated"]["content"]

    # 2. Stdin JSON input
    stdin_payload = json.dumps(
        {
            "facet": "idea_logic",
            "content": "核心逻辑：通过“双内参标定”消除批次漂移 [p.1]。",
        },
        ensure_ascii=False,
    )
    rc2, res2 = _run_cli(
        vault,
        ["memory-card", "refine", "NOOCR001", "--input", "-", "--json"],
        stdin_text=stdin_payload,
    )
    assert rc2 == 0
    assert res2["ok"] is True
    assert res2["data"]["updated"]["revision"] == 1
    assert "“双内参标定”" in res2["data"]["updated"]["content"]

    # 3. Stdin raw text + --facet
    rc3, res3 = _run_cli(
        vault,
        ["memory-card", "refine", "NOOCR001", "--facet", "critique_limits", "--input", "-", "--json"],
        stdin_text="局限性：“样本量较小”且缺少远期随访 [p.3]。",
    )
    assert rc3 == 0
    assert res3["ok"] is True
    assert res3["data"]["updated"]["facet"] == "critique_limits"


def test_runtime_health_missing_logs_dir_on_writable_vault(tmp_path: Path) -> None:
    vault = _setup_multipage_non_ocr_vault(tmp_path)
    logs_dir = vault / ".paperforge" / "logs"
    assert not logs_dir.exists()

    rc, res = _run_cli(vault, ["runtime-health", "--json"])
    assert rc == 0
    assert res["ok"] is True
    data = res["data"]
    assert data["summary"]["safe_write"] is True
    assert data["layers"]["write"]["status"] == "ok"
    assert data["capabilities"]["reading_log_write"] is True
    assert data["capabilities"]["project_log_write"] is True
    assert "mkdir -p" not in json.dumps(data)
    # Must remain side-effect free (logs_dir not created by health check)
    assert not logs_dir.exists()


def test_targeted_ocr_dry_run_paper_status_logs_and_embed_status(tmp_path: Path) -> None:
    vault = _setup_multipage_non_ocr_vault(tmp_path)

    # Targeted OCR --dry-run by collection (skips NOPDF003 automatically)
    rc, res = _run_cli(vault, ["ocr", "run", "--collection", "Ortho/Cartilage", "--dry-run", "--json"])
    assert rc == 0
    assert res["ok"] is True
    assert res["data"]["dry_run"] is True
    assert res["data"]["selected_keys"] == ["NOOCR001"]
    assert "NOPDF003" in res["data"]["skipped_no_pdf"]

    # Targeted OCR --dry-run on already-done key skips without --force, includes with --force
    rc_skip, res_skip = _run_cli(vault, ["ocr", "run", "--keys", "DONE0002", "--dry-run", "--json"])
    assert rc_skip == 0
    assert res_skip["data"]["selected_keys"] == []
    assert res_skip["data"]["skipped_done"] == ["DONE0002"]

    rc_force, res_force = _run_cli(vault, ["ocr", "run", "--keys", "DONE0002", "--force", "--dry-run", "--json"])
    assert rc_force == 0
    assert res_force["data"]["selected_keys"] == ["DONE0002"]

    # Multi-key paper-status
    rc_ps, res_ps = _run_cli(vault, ["paper-status", "--keys", "NOOCR001", "DONE0002", "MISSING1", "--json"])
    assert rc_ps == 0
    assert res_ps["data"]["count"] == 2
    assert res_ps["data"]["missing"] == ["MISSING1"]

    # Embed status JSON
    rc_emb, res_emb = _run_cli(vault, ["embed", "status", "--json"])
    assert rc_emb == 0
    assert res_emb["ok"] is True
    assert "build_state" in res_emb["data"]

    # Log writes via stdin JSON (reading_log, project_log, methodology)
    rc_rl, res_rl = _run_cli(
        vault,
        ["reading-log", "--write", "NOOCR001", "--input", "-", "--json"],
        stdin_text=json.dumps(
            {
                "section": "Methods p.1",
                "excerpt": "PEMF 75 Hz parameter window.",
                "usage": "parameter justification",
                "context": "Introduction section on page 1. PEMF 75 Hz parameter window.",
                "project": "CartilageReview",
            }
        ),
    )
    assert rc_rl == 0
    assert res_rl["ok"] is True

    rc_pl, res_pl = _run_cli(
        vault,
        ["project-log", "--write", "--project", "CartilageReview", "--input", "-", "--json"],
        stdin_text=json.dumps({"type": "decision", "title": "Use 75 Hz window", "decisions": ["Lock 75 Hz"]}),
    )
    assert rc_pl == 0
    assert res_pl["ok"] is True

    rc_meth, res_meth = _run_cli(
        vault,
        ["project-log", "--write-methodology", "--input", "-", "--json"],
        stdin_text=json.dumps(
            {
                "id": "pemf-param-audit",
                "title": "PEMF Parameter Audit",
                "use_when": "Auditing PEMF frequency claims",
                "content": "## Procedure\n1. Check primary page.\n",
            }
        ),
    )
    assert rc_meth == 0
    assert res_meth["ok"] is True
    assert (vault / ".paperforge" / "methodology" / "archive" / "pemf-param-audit.md").is_file()
