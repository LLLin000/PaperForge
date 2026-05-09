"""Dashboard command.

Returns a PFResult with aggregated stats and permissions for the plugin dashboard.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from paperforge import __version__
from paperforge.config import load_vault_config, paperforge_paths, resolve_vault
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult

logger = logging.getLogger(__name__)


def run(args) -> int:
    """Run dashboard command and print PFResult JSON to stdout."""
    vault = getattr(args, "vault_path", None)
    if vault is None:
        try:
            vault = resolve_vault(cli_vault=getattr(args, "vault", None))
        except FileNotFoundError as exc:
            result = PFResult(
                ok=False,
                command="dashboard",
                version=__version__,
                error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
            )
            print(result.to_json())
            return 1

    try:
        data = _gather_dashboard_data(vault)
        result = PFResult(ok=True, command="dashboard", version=__version__, data=data)
        print(result.to_json())
        return 0
    except Exception as exc:
        logger.exception("Dashboard gathering failed")
        result = PFResult(
            ok=False,
            command="dashboard",
            version=__version__,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
        print(result.to_json())
        return 1


def _gather_dashboard_data(vault: Path) -> dict:
    """Gather stats and permissions for dashboard display."""
    cfg = load_vault_config(vault)
    paths = paperforge_paths(vault, cfg)

    # ── Papers / formal note count ──
    _skip_names = {"fulltext.md", "deep-reading.md", "discussion.md"}
    record_count = 0
    if paths["literature"].exists():
        for p in paths["literature"].rglob("*.md"):
            if p.name not in _skip_names:
                record_count += 1

    # ── Domain counts (first-level subdirs under literature) ──
    domain_counts: dict[str, int] = {}
    if paths["literature"].exists():
        for domain_dir in sorted(paths["literature"].iterdir()):
            if domain_dir.is_dir():
                count = sum(
                    1 for p in domain_dir.rglob("*.md") if p.name not in _skip_names
                )
                if count > 0:
                    domain_counts[domain_dir.name] = count

    # ── PDF health & OCR health from frontmatter ──
    pdf_healthy = 0
    pdf_broken = 0
    pdf_missing = 0
    ocr_pending = 0
    ocr_done = 0
    ocr_failed = 0

    _path_error_pat = re.compile(r'^path_error:\s*"(.+?)"\s*$', re.MULTILINE)
    _pdf_path_pat = re.compile(r'^pdf_path:\s*".*?"\s*$', re.MULTILINE)
    _ocr_status_pat = re.compile(r'^ocr_status:\s*(\S+)', re.MULTILINE)
    _do_ocr_pat = re.compile(r'^do_ocr:\s*true\s*$', re.MULTILINE)

    if paths["literature"].exists():
        for note_path in paths["literature"].rglob("*.md"):
            if note_path.name in _skip_names:
                continue
            try:
                text = note_path.read_text(encoding="utf-8")
            except Exception:
                continue

            # PDF health
            path_error_m = _path_error_pat.search(text)
            if path_error_m:
                error_type = path_error_m.group(1)
                if error_type == "not_found":
                    pdf_missing += 1
                else:
                    pdf_broken += 1
            elif _pdf_path_pat.search(text):
                pdf_healthy += 1

            # OCR health
            ocr_status_m = _ocr_status_pat.search(text)
            if ocr_status_m:
                status = ocr_status_m.group(1).strip().lower().strip('"')
                if status == "done":
                    ocr_done += 1
                elif status in ("pending", "queued", "processing", "running", ""):
                    ocr_pending += 1
                else:
                    ocr_failed += 1
            elif _do_ocr_pat.search(text):
                ocr_pending += 1

    # ── Permissions ──
    export_files = sorted(paths["exports"].glob("*.json")) if paths["exports"].exists() else []
    can_sync = len(export_files) > 0

    paddle_token = (
        os.environ.get("PADDLEOCR_API_TOKEN")
        or os.environ.get("PADDLEOCR_API_KEY")
        or os.environ.get("OCR_TOKEN")
    )
    can_ocr = bool(paddle_token)

    can_copy_context = False
    pf_dir = paths.get("paperforge", vault / cfg["system_dir"] / "PaperForge")
    if pf_dir.exists():
        try:
            pf_dir.parent.mkdir(parents=True, exist_ok=True)
            test_file = pf_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            can_copy_context = True
        except (OSError, PermissionError):
            pass

    return {
        "stats": {
            "papers": record_count,
            "pdf_health": {
                "healthy": pdf_healthy,
                "broken": pdf_broken,
                "missing": pdf_missing,
            },
            "ocr_health": {
                "pending": ocr_pending,
                "done": ocr_done,
                "failed": ocr_failed,
            },
            "domain_counts": domain_counts,
        },
        "permissions": {
            "can_sync": can_sync,
            "can_ocr": can_ocr,
            "can_copy_context": can_copy_context,
        },
    }
