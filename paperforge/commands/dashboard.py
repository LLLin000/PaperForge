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


def _dashboard_from_db(vault: Path) -> dict | None:
    """Build dashboard stats from paperforge.db. Returns None if DB unavailable."""
    from pathlib import Path as _P
    db_path = vault / "System" / "PaperForge" / "indexes" / "paperforge.db"
    if not db_path.exists():
        return None
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        # Aggregate stats via single GROUP BY
        rows = conn.execute("""
            SELECT has_pdf,
                   CASE WHEN ocr_status='done' THEN 'done'
                        WHEN ocr_status IN ('failed','blocked') THEN 'failed'
                        ELSE 'pending' END as ocr,
                   COUNT(*) as cnt
            FROM papers GROUP BY has_pdf, ocr
        """).fetchall()
        total = sum(r["cnt"] for r in rows)
        pdf_healthy = sum(r["cnt"] for r in rows if r["has_pdf"] == 1 and r["ocr"] != "failed")
        pdf_missing = sum(r["cnt"] for r in rows if r["has_pdf"] == 0)
        pdf_broken = total - pdf_healthy - pdf_missing
        ocr_done = sum(r["cnt"] for r in rows if r["ocr"] == "done")
        ocr_failed = sum(r["cnt"] for r in rows if r["ocr"] == "failed")
        ocr_pending = total - ocr_done - ocr_failed
        # Domain counts
        rows = conn.execute("SELECT domain, COUNT(*) as cnt FROM papers GROUP BY domain").fetchall()
        domain_counts = {r["domain"]: r["cnt"] for r in rows}
        conn.close()
        return {
            "stats": {
                "papers": total,
                "pdf_health": {"healthy": pdf_healthy, "missing": pdf_missing, "broken": pdf_broken},
                "ocr_health": {"pending": ocr_pending, "done": ocr_done, "failed": ocr_failed},
                "domain_counts": domain_counts,
            },
        }
    except Exception:
        return None


def _check_permissions(vault: Path) -> dict:
    """Check sync/OCR/context permissions (lightweight filesystem check)."""
    cfg = load_vault_config(vault)
    paths = paperforge_paths(vault, cfg)

    export_files = sorted(paths["exports"].glob("*.json")) if paths["exports"].exists() else []
    can_sync = len(export_files) > 0

    paddle_token = (
        os.environ.get("PADDLEOCR_API_TOKEN") or os.environ.get("PADDLEOCR_API_KEY") or os.environ.get("OCR_TOKEN")
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
        "can_sync": can_sync,
        "can_ocr": can_ocr,
        "can_copy_context": can_copy_context,
    }


def _dashboard_from_files(vault: Path) -> dict:
    """Gather stats and permissions by scanning literature files."""
    cfg = load_vault_config(vault)
    paths = paperforge_paths(vault, cfg)

    _skip_names = {"fulltext.md", "deep-reading.md", "discussion.md"}
    record_count = 0
    if paths["literature"].exists():
        for p in paths["literature"].rglob("*.md"):
            if p.name not in _skip_names:
                record_count += 1

    domain_counts: dict[str, int] = {}
    if paths["literature"].exists():
        for domain_dir in sorted(paths["literature"].iterdir()):
            if domain_dir.is_dir():
                count = sum(1 for p in domain_dir.rglob("*.md") if p.name not in _skip_names)
                if count > 0:
                    domain_counts[domain_dir.name] = count

    pdf_healthy = 0
    pdf_broken = 0
    pdf_missing = 0
    ocr_pending = 0
    ocr_done = 0
    ocr_failed = 0

    _path_error_pat = re.compile(r'^path_error:\s*"(.+?)"\s*$', re.MULTILINE)
    _pdf_path_pat = re.compile(r'^pdf_path:\s*".*?"\s*$', re.MULTILINE)
    _ocr_status_pat = re.compile(r"^ocr_status:\s*(\S+)", re.MULTILINE)
    _do_ocr_pat = re.compile(r"^do_ocr:\s*true\s*$", re.MULTILINE)

    if paths["literature"].exists():
        for note_path in paths["literature"].rglob("*.md"):
            if note_path.name in _skip_names:
                continue
            try:
                text = note_path.read_text(encoding="utf-8")
            except Exception:
                continue

            path_error_m = _path_error_pat.search(text)
            if path_error_m:
                error_type = path_error_m.group(1)
                if error_type == "not_found":
                    pdf_missing += 1
                else:
                    pdf_broken += 1
            elif _pdf_path_pat.search(text):
                pdf_healthy += 1

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
        "permissions": _check_permissions(vault),
    }


def _gather_dashboard_data(vault: Path) -> dict:
    # Try DB first
    data = _dashboard_from_db(vault)
    if data is not None:
        data["permissions"] = _check_permissions(vault)
        return data
    # Fallback to file scanning
    data = _dashboard_from_files(vault)
    data["permissions"] = _check_permissions(vault)
    return data
