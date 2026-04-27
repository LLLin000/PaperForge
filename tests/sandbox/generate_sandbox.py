#!/usr/bin/env python3
"""Generate minimal pre-install sandbox for testing PaperForge Lite setup wizard.

Run from repo root:
    python tests/sandbox/generate_sandbox.py

Creates tests/sandbox/ with:
- TestZoteroData/         — mock Zotero data dir (wizard creates junction to this)
  - storage/              — 5 PDFs with keys matching exports JSON
  - zotero.sqlite         — fake sqlite (satisfies Zotero path detection)
- exports/                — Better BibTeX JSON exports (keys match storage filenames)
- 00_TestVault/          — empty vault root (wizard generates everything here)

Wizard creates inside 00_TestVault/:
  00_System/Zotero -> junction -> TestZoteroData (user points to our TestZoteroData)
"""

from __future__ import annotations

import json
from pathlib import Path

SANDBOX = Path(__file__).parent
ZOTERO_DATA = SANDBOX / "TestZoteroData"
STORAGE = ZOTERO_DATA / "storage"
EXPORTS = SANDBOX / "exports"
VAULT = SANDBOX / "00_TestVault"

# Keys in JSON must match PDF filenames in storage (minus .pdf)
PAPERS = {
    "骨科": [
        {
            "key": "TSTONE001",
            "title": "Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair",
            "creators": [{"creatorType": "author", "firstName": "James", "lastName": "Burkhardt"}],
            "date": "2024",
            "publicationTitle": "Journal of Shoulder and Elbow Surgery",
            "DOI": "10.1016/j.jses.2024.01.001",
            "abstractNote": "BACKGROUND: Suture anchor fixation is critical for rotator cuff repair. We compared pull-out strength across 3 anchor types.",
            "has_pdf": True,
        },
        {
            "key": "TSTONE002",
            "title": "Machine Learning Prediction of Anterior Cruciate Ligament Injury Risk in Athletes",
            "creators": [{"creatorType": "author", "firstName": "Wei", "lastName": "Zhang"}],
            "date": "2023",
            "publicationTitle": "American Journal of Sports Medicine",
            "DOI": "10.1177/03635465231123456",
            "abstractNote": "PURPOSE: To develop and validate an ML model for predicting ACL injury risk using biomechanical and demographic features.",
            "has_pdf": True,
        },
        {
            "key": "TSTONE003",
            "title": "Platelet-Rich Plasma for Knee Osteoarthritis: RCT",
            "creators": [{"creatorType": "author", "firstName": "Sarah", "lastName": "Johnson"}],
            "date": "2022",
            "publicationTitle": "Osteoarthritis and Cartilage",
            "DOI": "10.1016/j.joca.2022.03.012",
            "abstractNote": "OBJECTIVE: To evaluate PRP injections vs hyaluronic acid for symptomatic knee OA in a double-blind RCT (n=192).",
            "has_pdf": False,
        },
    ],
    "运动医学": [
        {
            "key": "TSTTWO001",
            "title": "Return to Sport After ACL Reconstruction: A Systematic Review",
            "creators": [{"creatorType": "author", "firstName": "Lisa", "lastName": "Park"}],
            "date": "2024",
            "publicationTitle": "Sports Health",
            "DOI": "10.1177/19417381241234567",
            "abstractNote": "DATA SOURCES: PubMed, Embase, Cochrane. 23 studies included. Return-to-sport criteria varied widely across studies.",
            "has_pdf": True,
        },
        {
            "key": "TSTTWO002",
            "title": "Ultrasound-Guided Achilles Tendon Repair: Case Series",
            "creators": [{"creatorType": "author", "firstName": "Carlos", "lastName": "Rodriguez"}],
            "date": "2023",
            "publicationTitle": "Foot and Ankle International",
            "DOI": "10.1177/107110072311234",
            "abstractNote": "CASE SERIES: 28 patients with acute Achilles ruptures. Primary outcomes: AOFAS score, time to weight-bearing, complications.",
            "has_pdf": True,
        },
    ],
}


def _write_minimal_pdf(path: Path) -> None:
    path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n199\n"
        b"%%EOF\n"
    )


def build() -> None:
    import shutil

    for p in [ZOTERO_DATA, EXPORTS, VAULT]:
        if p.exists():
            shutil.rmtree(p)

    print(f"Generating sandbox at: {SANDBOX}")

    # --- TestZoteroData (wizard creates junction inside vault pointing here) ---
    STORAGE.mkdir(parents=True)
    (ZOTERO_DATA / "zotero.sqlite").write_bytes(b"SQLite format 3" * 4)

    for domain, papers in PAPERS.items():
        for paper in papers:
            key = paper["key"]
            if paper["has_pdf"]:
                pdf_dir = STORAGE / key
                pdf_dir.mkdir(parents=True, exist_ok=True)
                _write_minimal_pdf(pdf_dir / f"{key}.pdf")

    # --- exports (BBT JSON, keys must match storage filenames) ---
    EXPORTS.mkdir(parents=True)
    for domain, papers in PAPERS.items():
        items = []
        for paper in papers:
            item = {
                "key": paper["key"],
                "itemType": "journalArticle",
                "title": paper["title"],
                "creators": paper["creators"],
                "date": paper["date"],
                "publicationTitle": paper["publicationTitle"],
                "DOI": paper["DOI"],
                "abstractNote": paper["abstractNote"],
                "collections": [domain],
            }
            if paper["has_pdf"]:
                item["attachments"] = [{"path": f"{paper['key']}/{paper['key']}.pdf", "contentType": "application/pdf"}]
            else:
                item["attachments"] = []
            items.append(item)

        export_path = EXPORTS / f"{domain}.json"
        export_path.write_text(
            json.dumps({"items": items}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # --- empty vault root (wizard fills everything) ---
    VAULT.mkdir(parents=True)

    # --- README ---
    vault_abs = str(VAULT.resolve())
    zotero_abs = str(ZOTERO_DATA.resolve())
    exports_abs = str(EXPORTS.resolve())

    readme = SANDBOX / "README.md"
    readme.write_text(
        f"""# PaperForge Lite — Test Sandbox

## 用途
测试 PaperForge Lite 安装向导 `setup_wizard.py` 的完整流程。

## 目录结构

```
tests/sandbox/
  TestZoteroData/          ← 模拟 Zotero 数据目录（setup wizard 会在 vault 内建 junction 指向这里）
    storage/              ← 5 PDFs（4篇有附件，1篇无）
    zotero.sqlite         ← 伪造（让 Zotero 路径检测通过）
  exports/               ← Better BibTeX JSON 导出（2个域，5篇文献，keys 匹配 storage 文件名）
  00_TestVault/          ← 空目录（安装向导会在这里创建所有子目录）
  README.md              ← 本文件
```

## 测试步骤

```powershell
# 1. 进入仓库根目录
cd D:\\...\\github-release

# 2. 运行安装向导，指向空 vault
python setup_wizard.py --vault {vault_abs}

# 3. 安装向导中：
#    - Agent 平台：选你的（opencode / cursor / claude 等）
#    - Zotero 数据目录：填 {zotero_abs}
#      （向导会在 vault 内创建 junction: 00_TestVault/00_System/Zotero -> 指向这里）
#    - BBT 导出目录：填 {exports_abs}
#      （向导会检测到 exports/ 下的 JSON 文件）
#    - 其他步骤默认即可

# 4. 安装完成后，测试 pipeline：
cd {vault_abs}
paperforge selection-sync
paperforge index-refresh
paperforge ocr run
paperforge status
```

## 预期结果

| 检查项 | 预期 |
|--------|------|
| wizard 检测 TestZoteroData | 通过（有 storage/ 和 zotero.sqlite）|
| wizard 检测 exports/ | 通过（2个 JSON，keys 有效）|
| selection-sync | 生成 5 条 library-records |
| TSTONE003 ocr_status | nopdf（无 PDF） |
| TSTTWO001/002 有 PDF | ocr_status: pending |

## 注意
- 目录名故意和真实 vault 不同，避免硬编码测试不出来
- PDF 是最小化假文件（pymupdf 可读，内容为空）
- 不要往 sandbox 加真实数据
""",
        encoding="utf-8",
    )

    pdf_count = sum(1 for papers in PAPERS.values() for p in papers if p["has_pdf"])
    paper_count = sum(len(papers) for papers in PAPERS.values())
    print(f"\nSandbox ready: {SANDBOX}")
    print(f"  TestZoteroData/storage/  — {pdf_count} PDFs")
    print(f"  exports/                   — {len(PAPERS)} BBT JSON files ({paper_count} papers)")
    print("  00_TestVault/             — EMPTY (wizard fills this)")
    print("\nRun:")
    print(f"  python setup_wizard.py --vault {VAULT.resolve()}")


if __name__ == "__main__":
    build()
