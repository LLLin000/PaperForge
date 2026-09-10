#!/usr/bin/env python3
"""Build the disposable e2e vault (real content, deterministic).

`npm run test:e2e` invokes this first. The vault is generated from the
repo's own fixtures (BBT export + OCR outputs) and then put through the REAL
`paperforge sync`, so the e2e specs exercise the frontend against a genuine
canonical index, workspace, and OCR lineage — not hand-written stubs.

Seeded content:
- paperforge.json (canonical schema via bootstrap_config)
- System/PaperForge/exports/骨科.json  (BBT export fixture)
- System/PaperForge/ocr/TSTONE001/     (completed OCR fixture)
- after sync: canonical index, migrated workspace, per-paper notes
- versions/v1 + v2 + manifest, one legacy pre-rebuild backup
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PLUGIN_DIR = Path(__file__).resolve().parents[2]
VAULT = PLUGIN_DIR / "test" / "vaults" / "e2e"
EXPORT_FIXTURE = REPO_ROOT / "tests" / "sandbox" / "exports" / "骨科.json"
OCR_FIXTURE = REPO_ROOT / "tests" / "sandbox" / "ocr-complete" / "TSTONE001"
KEY = "TSTONE001"


def _run(*args: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(VAULT), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"paperforge {' '.join(args)} failed ({result.returncode}):\n"
            f"{result.stdout[-800:]}\n{result.stderr[-800:]}"
        )


def _restore_canonical_fulltext() -> None:
    """Restore the canonical OCR fulltext the legacy backfill overwrote (#219).

    The first sync on a vault whose OCR artifacts predate the derived layout
    renders from raw and writes the rendered markdown over
    ``ocr/<key>/fulltext.md``, while ``meta.page_count`` keeps the original
    value. ``validate_ocr_meta`` then rejects the artifact the pipeline just
    produced, so the paper silently degrades to ``done_incomplete``. Re-seed
    the canonical artifact and make ``meta`` agree with it, so the fixture is a
    valid baseline — and, verified below, a sync fixed point.
    """
    canonical = (OCR_FIXTURE / "fulltext.md").read_text(encoding="utf-8")
    target = VAULT / "System" / "PaperForge" / "ocr" / KEY / "fulltext.md"
    target.write_text(canonical, encoding="utf-8")

    import json as _json  # noqa: PLC0415

    from paperforge.worker.ocr_fulltext_state import (  # noqa: PLC0415
        compute_disk_fulltext_hash,
    )

    meta_path = target.parent / "meta.json"
    meta = _json.loads(meta_path.read_text(encoding="utf-8"))
    meta["machine_fulltext_hash"] = compute_disk_fulltext_hash(target)
    meta_path.write_text(
        _json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def _assert_ocr_invariant() -> None:
    """The fixture must ship a VALID completed OCR state, not an assumed one.

    A hand-written stub that claims ``done`` while the artifacts fail the
    pipeline's own validator is what let #219 hide behind a green suite.
    """
    from paperforge.config import resolve_paths  # noqa: PLC0415
    from paperforge.worker.ocr import validate_ocr_meta  # noqa: PLC0415

    meta_path = VAULT / "System" / "PaperForge" / "ocr" / KEY / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    status, reason = validate_ocr_meta(resolve_paths(VAULT), meta)
    if status != "done":
        raise SystemExit(
            f"e2e fixture OCR invariant violated for {KEY}: "
            f"validate_ocr_meta -> {status!r} ({reason})"
        )


def build() -> None:
    if VAULT.exists():
        shutil.rmtree(VAULT)
    VAULT.mkdir(parents=True)

    sys.path.insert(0, str(REPO_ROOT))
    from paperforge.config import bootstrap_config, set_config  # noqa: PLC0415

    bootstrap_config(VAULT)
    for key, value in {
        "system_dir": "System",
        "resources_dir": "Resources",
        "literature_dir": "Literature",
        "control_dir": "LiteratureControl",
        "base_dir": "Bases",
        "skill_dir": ".opencode/skills",
    }.items():
        set_config(VAULT, key, value)

    exports_dir = VAULT / "System" / "PaperForge" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EXPORT_FIXTURE, exports_dir / EXPORT_FIXTURE.name)

    ocr_target = VAULT / "System" / "PaperForge" / "ocr" / KEY
    shutil.copytree(OCR_FIXTURE, ocr_target, dirs_exist_ok=True)

    # REAL sync: selection → index → workspace migration. On this first pass
    # the legacy backfill rewrites the canonical fulltext (see #219).
    _run("sync", "--json")

    # Version authority reads the OCR root (System/PaperForge/ocr/<key>/),
    # so seed the version artifacts there — not in the workspace.
    paper_root = VAULT / "System" / "PaperForge" / "ocr" / KEY
    (paper_root / "render").mkdir(parents=True, exist_ok=True)
    (paper_root / "render" / "fulltext.md").write_text(
        "# Current render\n\ncurrent body\n", encoding="utf-8"
    )
    versions = paper_root / "versions"
    (versions / "v1").mkdir(parents=True, exist_ok=True)
    (versions / "v2").mkdir(parents=True, exist_ok=True)
    (versions / "v1" / "fulltext.md").write_text(
        "# Version one\n\nfirst body\n", encoding="utf-8"
    )
    (versions / "v2" / "fulltext.md").write_text(
        "# Version two\n\nsecond body\n", encoding="utf-8"
    )
    (versions / "manifest.json").write_text(
        json.dumps(
            {
                "versions": [
                    {
                        "label": "v1",
                        "created_at": "2026-01-01T00:00:00Z",
                        "source": "pre-rebuild",
                        "fulltext_size": 24,
                    },
                    {
                        "label": "v2",
                        "created_at": "2026-01-02T00:00:00Z",
                        "source": "pre-rebuild",
                        "fulltext_size": 24,
                    },
                ],
                "current": {"label": "v2"},
            }
        ),
        encoding="utf-8",
    )
    backups = paper_root / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    (backups / "fulltext.pre-rebuild.20260909T123456Z.md").write_text(
        "# Legacy backup\n\nlegacy body\n", encoding="utf-8"
    )

    # Restore the canonical artifact, then sync again: this second pass is
    # stable (no derived rebuild), so the fixture ends as a sync fixed point.
    _restore_canonical_fulltext()
    _run("sync", "--json")

    # REAL memory build last, so FTS reflects the final state.
    _run("memory", "build", "--json")

    _assert_ocr_invariant()

    print(f"e2e vault ready: {VAULT}")


if __name__ == "__main__":
    build()
