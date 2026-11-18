"""Unit tests for Commit 3B: Agent cognitive loop closure, pf_deep/pf_bootstrap updates, and collection tree."""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sqlite3
import sys
from contextlib import redirect_stdout
from pathlib import Path

from paperforge.adapters.obsidian_frontmatter import has_deep_reading_content
from paperforge.commands.agent_context import COMMANDS as AGENT_COMMANDS
from paperforge.commands.agent_context import RULES as AGENT_RULES
from paperforge.commands.paper_context import run as run_paper_context
from paperforge.memory.builder import build_for_keys
from paperforge.memory.context import _build_collection_tree
from paperforge.services.annotations_service import add_annotation
from tests.conftest import canonical_test_config

REPO_ROOT = Path(__file__).resolve().parents[2]
PF_DEEP_PATH = REPO_ROOT / "paperforge" / "skills" / "paperforge" / "scripts" / "pf_deep.py"
PF_BOOTSTRAP_PATH = REPO_ROOT / "paperforge" / "skills" / "paperforge" / "scripts" / "pf_bootstrap.py"


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _setup_agent_loop_vault(tmp_path: Path, *, key: str = "LOOP0001") -> tuple[Path, Path, Path]:
    import pymupdf

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")

    pf = vault / ".paperforge"
    ws = vault / "Resources" / "Literature" / "Ortho" / f"{key} - Loop Paper"
    ws.mkdir(parents=True)
    note_path = ws / f"{key} - Loop Paper.md"
    note_path.write_text(
        f'---\nzotero_key: "{key}"\ndomain: Ortho\nanalyze: true\ndo_ocr: true\nocr_status: done\n---\n\n# Loop Paper\n',
        encoding="utf-8",
    )

    zot_storage = pf / "Zotero" / "storage" / "ZZ01"
    zot_storage.mkdir(parents=True)
    pdf_path = zot_storage / "loop.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page(width=600, height=800)
        page.insert_text((72, 120), "PEMF stimulation at 75 Hz improved GAG synthesis.")
        page.draw_rect(pymupdf.Rect(60, 260, 480, 520), color=(0, 0, 1), fill=(0.9, 0.95, 1.0))
        doc.save(pdf_path)

    idx_path = pf / "indexes" / "formal-library.json"
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx_path.write_text(
        json.dumps(
            {
                "version": 1,
                "items": [
                    {
                        "zotero_key": key,
                        "citation_key": "lin2026loop",
                        "domain": "Ortho",
                        "title": "Loop Paper",
                        "authors": ["Lin"],
                        "first_author": "Lin",
                        "year": "2026",
                        "journal": "JOR",
                        "collections": ["骨科/脊柱", "骨科/创伤"],
                        "collection_path": "骨科/脊柱 | 骨科/创伤",
                        "has_pdf": True,
                        "analyze": True,
                        "do_ocr": True,
                        "ocr_status": "done",
                        "pdf_path": "storage:ZZ01/loop.pdf",
                        "paper_root": f"Resources/Literature/Ortho/{key} - Loop Paper/",
                        "main_note_path": f"Resources/Literature/Ortho/{key} - Loop Paper/{key} - Loop Paper.md",
                        "note_path": f"Resources/Literature/Ortho/{key} - Loop Paper/{key} - Loop Paper.md",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    ocr_dir = pf / "ocr" / key
    (ocr_dir / "structure").mkdir(parents=True)
    (ocr_dir / "index").mkdir(parents=True)
    (ocr_dir / "assets" / "figures").mkdir(parents=True)
    (ocr_dir / "assets" / "figures" / "figure_001.jpg").write_bytes(b"\xff\xd8\xff\xe0MOCKJPG")

    (ocr_dir / "meta.json").write_text(json.dumps({"ocr_status": "done"}), encoding="utf-8")
    (ocr_dir / "fulltext.md").write_text(
        "<!-- page 1 -->\n\n### 3.2 Loop Results\n\n"
        "Figure 1. PEMF response curve across doses.\n\n"
        "![[assets/figures/figure_001.jpg]]\n",
        encoding="utf-8",
    )
    (ocr_dir / "index" / "structure-tree.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "node_id": "sec_results",
                        "title": "3.2 Loop Results",
                        "own_block_ids": ["blk_p1_001"],
                        "subtree_block_ids": ["blk_p1_001"],
                        "page_span": [1, 1],
                        "children": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (ocr_dir / "index" / "result-hash.txt").write_text("sha256:loop-hash-001", encoding="utf-8")

    return vault, note_path, ocr_dir


def test_paper_context_includes_user_annotations_and_dot_paperforge_structure(tmp_path: Path):
    vault, _note, _ocr = _setup_agent_loop_vault(tmp_path)
    key = "LOOP0001"

    add_annotation(
        vault,
        key,
        page=1,
        rects=[[0.1, 0.14, 0.7, 0.18]],
        kind="highlight",
        color="red",
        intent="question",
        exact_text="75 Hz",
        comment="Need sample size breakdown",
    )
    add_annotation(
        vault,
        key,
        page=1,
        rects=[[0.1, 0.32, 0.8, 0.65]],
        kind="area",
        color="green",
        intent="evidence",
        comment="Key dose curve",
    )
    build_for_keys(vault)

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = run_paper_context(argparse.Namespace(vault_path=vault, key=key, structure=True, json=True))
    assert rc == 0, buf.getvalue()
    payload = json.loads(buf.getvalue())
    assert payload["ok"] is True
    data = payload["data"]

    # StructureTree loaded from hidden .paperforge/ocr/<KEY>/index/structure-tree.json
    assert data["structure"] is not None
    assert data["structure"]["nodes"][0]["node_id"] == "sec_results"

    # User annotations split into questions and highlights
    ua = data["user_annotations"]
    assert ua["total"] == 2
    assert len(ua["questions"]) == 1
    assert ua["questions"][0]["comment"] == "Need sample size breakdown"
    assert len(ua["highlights"]) == 1
    assert ua["highlights"][0]["intent"] == "evidence"
    assert key in ua["highlights"][0]["embed_wikilink"]

    # Removing formal-library.json leaves SQLite fallback working cleanly
    (vault / ".paperforge" / "indexes" / "formal-library.json").unlink()
    buf2 = io.StringIO()
    with redirect_stdout(buf2):
        rc2 = run_paper_context(argparse.Namespace(vault_path=vault, key=key, structure=False, json=True))
    assert rc2 == 0
    payload2 = json.loads(buf2.getvalue())
    assert payload2["data"]["user_annotations"]["total"] == 2


def test_pf_deep_scaffold_assets_and_validation(tmp_path: Path):
    pf_deep = _load_script("pf_deep_mod_test", PF_DEEP_PATH)
    vault, note_path, _ocr = _setup_agent_loop_vault(tmp_path, key="DEEP0001")

    # 1. render_study_scaffold must NOT emit duplicate #### 遗留问题 / **遗留问题**
    scaffold = pf_deep.render_study_scaffold([])
    assert pf_deep.validate_redundant_headings(scaffold) == []
    assert "#### 遗留问题" in scaffold
    filled_note = (
        scaffold.replace("- **Clarity**（清晰度）：", "- **Clarity**（清晰度）：Clear rationale")
        .replace("- 关键主图：", "- 关键主图：Figure 1 Dose curve")
        .replace("#### 遗留问题\n- ", "#### 遗留问题\n- Checked question p.1")
    )
    assert has_deep_reading_content(f"---\ntitle: t\n---\n\n{filled_note}\n")

    # 2. prepare_deep_reading materializes <KEY>_figure_*.jpg and embeds unique name
    prep = pf_deep.prepare_deep_reading(vault, "DEEP0001")
    assert prep["status"] == "ok", prep
    mat_fig = note_path.parent / "assets" / "DEEP0001_figure_001.jpg"
    assert mat_fig.exists()
    updated_note = note_path.read_text(encoding="utf-8")
    assert "![[DEEP0001_figure_001.jpg]]" in updated_note

    # 3. validate_selected_blocks accepts both unique key-prefixed embed & assets/ variant
    fig_entry = pf_deep.FigureEntry(
        number="1",
        image_id="figure_001",
        title="PEMF response curve",
        image_link="assets/figures/figure_001.jpg",
        page=1,
        caption="PEMF response curve",
        is_supplementary=False,
    )
    assert pf_deep.validate_selected_blocks(updated_note, [fig_entry]) == []
    alt_note = updated_note.replace("![[DEEP0001_figure_001.jpg]]", "![[assets/DEEP0001_figure_001.jpg]]")
    assert pf_deep.validate_selected_blocks(alt_note, [fig_entry]) == []

    # 4. postprocess_pass2 permits _ann_ screenshot embeds outside Figure callouts
    note_with_ann = (
        "### Pass 2: 精读还原\n\n"
        "> [!note]- Figure 1：PEMF response curve\n"
        "> ![[DEEP0001_figure_001.jpg]]\n"
        ">\n"
        + "".join(f"> **{h}**\n> detail\n" for h in pf_deep.FIGURE_SUBHEADINGS)
        + "\n![[DEEP0001_ann_ab12cd.jpg]]\n"
    )
    ann_errs = pf_deep.postprocess_pass2(note_with_ann, figure_count=1)
    assert [e for e in ann_errs if e["type"] == "image_bounds"] == []


def test_pf_bootstrap_uses_dot_paperforge_when_configured(tmp_path: Path, monkeypatch):
    pf_bootstrap = _load_script("pf_bootstrap_mod_test", PF_BOOTSTRAP_PATH)
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")

    monkeypatch.setattr(sys, "argv", ["pf_bootstrap.py", "--vault", str(vault)])
    buf = io.StringIO()
    with redirect_stdout(buf):
        pf_bootstrap.main()
    data = json.loads(buf.getvalue())
    assert data["ok"] is True
    assert Path(data["paths"]["paperforge_dir"]) == (vault / ".paperforge").resolve()
    assert Path(data["paths"]["ocr_dir"]) == (vault / ".paperforge" / "ocr").resolve()


def test_agent_context_rules_and_collection_tree():
    assert "annotations" in AGENT_COMMANDS
    assert any("annotations" in r and ".paperforge" in r for r in AGENT_RULES)
    assert not any("skip retrieve" in r for r in AGENT_RULES)

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE papers (collection_path TEXT)")
    conn.execute("INSERT INTO papers (collection_path) VALUES (?)", ("骨科/脊柱 | 骨科/创伤",))
    conn.execute("INSERT INTO papers (collection_path) VALUES (?)", ("心血管 | 冠心病",))

    tree = {row["name"]: row for row in _build_collection_tree(conn)}
    assert tree["骨科"]["count"] == 1
    assert tree["骨科"]["sub"] == ["创伤", "脊柱"]
    assert tree["心血管"]["count"] == 1
    assert tree["心血管"]["sub"] == ["冠心病"]
