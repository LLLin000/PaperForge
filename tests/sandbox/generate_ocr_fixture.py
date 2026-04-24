#!/usr/bin/env python3
"""Generate OCR-complete fixture for TSTONE001.

Run once to create deterministic fixture files:
    python tests/sandbox/generate_ocr_fixture.py

The generated fixtures are committed to git and used by smoke tests.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "sandbox" / "ocr-complete" / "TSTONE001"
EXPORT_JSON = REPO_ROOT / "tests" / "sandbox" / "exports" / "骨科.json"

# Ensure repo root is in sys.path for imports
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


SYNTHETIC_FULLTEXT = """<!-- page 1 -->

Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair

John Smith, Jane Doe
Journal of Shoulder and Elbow Surgery, 2024

## Abstract

This study compares the biomechanical properties of various suture anchor configurations used in rotator cuff repair surgery.

## Introduction

Rotator cuff tears are a common shoulder pathology. Surgical repair using suture anchors remains the gold standard treatment.

![[page_001_fig_01.png]]

Figure 1: Overview of suture anchor placement techniques. (A) Single row repair. (B) Double row repair. (C) Transosseous equivalent repair.

## Methods

### Patient Demographics

![[page_002_table_01.png]]

Table 1: Patient demographics and baseline characteristics (n=45).

### Biomechanical Testing

![[page_002_fig_02.png]]

Figure 2: Biomechanical testing setup. (A) Custom loading fixture. (B) Cyclic loading protocol.

<!-- page 2 -->

## Results

### Load to Failure

![[page_003_fig_03.png]]

Figure 3: Load to failure comparison. Error bars represent standard deviation. *p < 0.05 vs single row.

### Stiffness Analysis

![[page_003_fig_04.png]]

Figure 4: Stiffness comparison between repair techniques.

![[page_003_table_02.png]]

Table 2: Biomechanical properties summary.

<!-- page 3 -->

## Discussion

The double row technique demonstrated significantly higher load to failure compared to single row repair.

## Conclusion

Double row suture anchor fixation provides superior biomechanical properties for rotator cuff repair.
"""


def generate_fixtures() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    # Write fulltext.md
    fulltext_path = FIXTURE_DIR / "fulltext.md"
    fulltext_path.write_text(SYNTHETIC_FULLTEXT, encoding="utf-8")
    print(f"[INFO] Wrote {fulltext_path}")

    # Generate figure-map.json using ld_deep.py
    figure_map_path = FIXTURE_DIR / "figure-map.json"
    ld_deep_script = REPO_ROOT / "skills" / "literature-qa" / "scripts" / "ld_deep.py"

    result = subprocess.run(
        [
            sys.executable,
            str(ld_deep_script),
            "figure-map",
            str(fulltext_path),
            "--key", "TSTONE001",
            "--out", str(figure_map_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        print(f"[ERROR] figure-map failed: {result.stderr}")
        sys.exit(1)
    print(f"[INFO] Generated {figure_map_path}")

    # Generate chart-type-map.json
    chart_type_map_path = FIXTURE_DIR / "chart-type-map.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ld_deep_script),
            "chart-type-scan",
            str(figure_map_path),
            "--out", str(chart_type_map_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        print(f"[ERROR] chart-type-scan failed: {result.stderr}")
        sys.exit(1)
    print(f"[INFO] Generated {chart_type_map_path}")

    # Write meta.json
    meta_path = FIXTURE_DIR / "meta.json"
    meta = {
        "zotero_key": "TSTONE001",
        "ocr_status": "done",
        "page_count": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[INFO] Wrote {meta_path}")

    print("[OK] All fixtures generated successfully.")


if __name__ == "__main__":
    generate_fixtures()
