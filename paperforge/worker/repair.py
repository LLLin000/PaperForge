from __future__ import annotations

import logging
import re
from pathlib import Path

from paperforge.config import load_vault_config, paperforge_paths
from paperforge.worker.asset_index import refresh_index_entry
from paperforge.worker._domain import load_domain_config
from paperforge.worker._utils import (
    _resolve_formal_note_path,
    read_json,
    write_json,
)
from paperforge.worker.ocr import validate_ocr_meta
from paperforge.worker.sync import (
    load_export_rows,
    obsidian_wikilink_for_pdf,
    update_frontmatter_field,
)

logger = logging.getLogger(__name__)


def _find_export_for_domain(paths: dict[str, Path], domain: str) -> Path | None:
    """Find the BBT export JSON file for a given domain."""
    for export_path in sorted(paths["exports"].glob("*.json")):
        if export_path.stem == domain:
            return export_path
    return None


def _detect_path_errors(paths: dict[str, Path], verbose: bool = False) -> dict:
    """Scan library-records for path_error fields.

    Returns dict with:
        - total: total count of records with path_error
        - by_type: dict mapping error type -> count
        - records: list of record dicts with keys: path, zotero_key, domain, path_error, bbt_path_raw
    """
    result: dict = {"total": 0, "by_type": {}, "records": []}
    if not paths["library_records"].exists():
        return result
    for record_path in paths["library_records"].rglob("*.md"):
        try:
            text = record_path.read_text(encoding="utf-8")
        except Exception as e:
            if verbose:
                logger.error("error reading %s: %s", record_path, e)
            continue
        err_match = re.search(r'^path_error:\s*"(.*?)"\s*$', text, re.MULTILINE)
        if not err_match:
            continue
        path_error = err_match.group(1).strip()
        if not path_error:
            continue
        key_match = re.search(r'^zotero_key:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        if not key_match:
            continue
        zotero_key = key_match.group(1).strip()
        domain = record_path.parent.name
        bbt_match = re.search(r'^bbt_path_raw:\s*"(.*?)"\s*$', text, re.MULTILINE)
        bbt_path_raw = bbt_match.group(1) if bbt_match else ""
        result["total"] += 1
        result["by_type"][path_error] = result["by_type"].get(path_error, 0) + 1
        result["records"].append(
            {
                "path": record_path,
                "zotero_key": zotero_key,
                "domain": domain,
                "path_error": path_error,
                "bbt_path_raw": bbt_path_raw,
                "text": text,
            }
        )
    return result


def repair_pdf_paths(
    vault: Path,
    paths: dict[str, Path],
    error_records: list[dict],
    verbose: bool = False,
) -> int:
    """Re-resolve PDF paths for items with path_error.

    Returns number of paths successfully fixed.
    """
    fixed = 0
    from paperforge.pdf_resolver import resolve_pdf_path

    cfg = load_vault_config(vault)
    zotero_dir = vault / cfg.get("system_dir", "99_System") / "Zotero"

    # Cache export rows by domain to avoid reloading
    domain_exports: dict[str, list[dict]] = {}

    for record in error_records:
        record_path = record["path"]
        zotero_key = record["zotero_key"]
        domain = record["domain"]
        path_error = record["path_error"]
        text = record["text"]

        # For not_found errors, try to find the item in BBT export and re-process
        if path_error == "not_found":
            export_rows = domain_exports.get(domain)
            if export_rows is None:
                export_path = _find_export_for_domain(paths, domain)
                if export_path and export_path.exists():
                    try:
                        export_rows = load_export_rows(export_path)
                        domain_exports[domain] = export_rows
                    except Exception as e:
                        if verbose:
                            logger.error("error loading export for %s: %s", domain, e)
                        export_rows = []
                else:
                    export_rows = []
                    domain_exports[domain] = export_rows

            item = next((r for r in export_rows if r["key"] == zotero_key), None)
            if item:
                pdf_path = item.get("pdf_path", "")
                if pdf_path:
                    new_wikilink = obsidian_wikilink_for_pdf(pdf_path, vault, zotero_dir)
                    if new_wikilink:
                        new_text = update_frontmatter_field(text, "pdf_path", new_wikilink)
                        new_text = update_frontmatter_field(new_text, "path_error", "")
                        new_text = update_frontmatter_field(
                            new_text,
                            "bbt_path_raw",
                            item.get("bbt_path_raw", ""),
                        )
                        new_text = update_frontmatter_field(
                            new_text,
                            "zotero_storage_key",
                            item.get("zotero_storage_key", ""),
                        )
                        if new_text != text:
                            record_path.write_text(new_text, encoding="utf-8")
                            fixed += 1
                            if verbose:
                                logger.info("fixed path for %s: %s", zotero_key, new_wikilink)
                            try:
                                refresh_index_entry(vault, zotero_key)
                            except Exception as e:
                                logger.warning("Failed to refresh index for %s: %s", zotero_key, e)
                        continue

        # For all errors, try resolving the current pdf_path
        pdf_match = re.search(r'^pdf_path:\s*"(.*?)"\s*$', text, re.MULTILINE)
        if pdf_match:
            current_pdf = pdf_match.group(1).strip()
            if current_pdf:
                raw_path = current_pdf.strip("[]")
                resolved = resolve_pdf_path(raw_path, True, vault, zotero_dir)
                    if resolved:
                        new_text = update_frontmatter_field(text, "path_error", "")
                        if new_text != text:
                            record_path.write_text(new_text, encoding="utf-8")
                            fixed += 1
                            if verbose:
                                logger.info("cleared path_error for %s", zotero_key)
                            try:
                                refresh_index_entry(vault, zotero_key)
                            except Exception as e:
                                logger.warning("Failed to refresh index for %s: %s", zotero_key, e)
                else:
                    if verbose:
                        logger.warning("%s path still unresolved", zotero_key)
            else:
                if verbose:
                    logger.warning("%s has empty pdf_path (not_found)", zotero_key)
        else:
            if verbose:
                logger.warning("%s has no pdf_path field", zotero_key)

    return fixed


def run_repair(vault: Path, paths: dict, verbose: bool = False, fix: bool = False, fix_paths: bool = False) -> dict:
    """Scan all domains for three-way state divergence and optionally repair.

    Compares three sources of ocr_status:
    1. library_record.md frontmatter ocr_status
    2. formal_note.md frontmatter ocr_status
    3. meta.json ocr_status (post-validate_ocr_meta())

    Returns:
        dict with scanned, divergent, fixed, errors counts
    """
    result = {"scanned": 0, "divergent": [], "fixed": 0, "errors": []}
    config = load_domain_config(paths)
    {entry["export_file"]: entry["domain"] for entry in config["domains"]}
    record_paths = list(paths["library_records"].rglob("*.md"))
    for record_path in record_paths:
        try:
            record_text = record_path.read_text(encoding="utf-8")
        except Exception as e:
            result["errors"].append({"file": str(record_path), "error": str(e)})
            continue
        key_match = re.search('^zotero_key:\\s*"?(.+?)"?\\s*$', record_text, re.MULTILINE)
        if not key_match:
            continue
        zotero_key = key_match.group(1).strip()
        domain = record_path.parent.name
        result["scanned"] += 1
        lib_ocr_match = re.search('^ocr_status:\\s*"?(.+?)"?\\s*$', record_text, re.MULTILINE)
        lib_ocr_status = lib_ocr_match.group(1).strip() if lib_ocr_match else "pending"
        note_path = _resolve_formal_note_path(vault, zotero_key, domain)
        note_ocr_status = None
        if note_path and note_path.exists():
            try:
                note_text = note_path.read_text(encoding="utf-8")
                note_status_match = re.search('^ocr_status:\\s*"?(.+?)"?\\s*$', note_text, re.MULTILINE)
                note_ocr_status = note_status_match.group(1).strip() if note_status_match else None
            except Exception:
                pass
        meta_path = paths["ocr"] / zotero_key / "meta.json"
        meta_ocr_status = None
        meta_validated_status = None
        validated_status = None
        validated_error = ""
        if meta_path.exists():
            try:
                meta = read_json(meta_path)
                validated_status, validated_error = validate_ocr_meta(paths, meta)
                meta_validated_status = validated_status
                if validated_error and verbose:
                    logger.warning("%s meta validation error: %s", zotero_key, validated_error)
                raw_status = str(meta.get("ocr_status", "") or "").strip().lower()
                meta_ocr_status = raw_status if raw_status else None
                if meta_validated_status == "done_incomplete":
                    meta_ocr_status = "done_incomplete"
            except Exception as e:
                result["errors"].append({"file": str(meta_path), "error": str(e)})
                meta_ocr_status = None
        is_divergent = False
        div_reason = ""
        if meta_validated_status == "done_incomplete":
            is_divergent = True
            div_reason = f"meta validation: done_incomplete ({validated_error})"
        elif lib_ocr_status == "done" and meta_ocr_status in ("pending", "processing", None):
            is_divergent = True
            div_reason = f"library_record done but meta {meta_ocr_status or 'missing'}"
        elif note_ocr_status == "done" and (meta_ocr_status is None or meta_validated_status == "done_incomplete"):
            is_divergent = True
            div_reason = "formal_note done but meta.json missing/invalid"
        elif (
            lib_ocr_status != "pending"
            and meta_ocr_status is not None
            and meta_validated_status is not None
            and lib_ocr_status != meta_validated_status
        ):
            is_divergent = True
            div_reason = f"library_record={lib_ocr_status} vs meta post-validation={meta_validated_status}"
        if is_divergent:
            item = {
                "zotero_key": zotero_key,
                "domain": domain,
                "library_record_ocr_status": lib_ocr_status,
                "formal_note_ocr_status": note_ocr_status,
                "meta_ocr_status": meta_validated_status or meta_ocr_status,
                "reason": div_reason,
            }
            result["divergent"].append(item)
            if verbose:
                logger.info("divergent: %s | %s", zotero_key, div_reason)
            if fix:
                fixed_library_record = False
                fixed_formal_note = False
                fixed_meta = False
                new_status = "pending"
                if meta_ocr_status is None or meta_validated_status == "done_incomplete":
                    new_status = "pending"
                    new_record_text = update_frontmatter_field(record_text, "ocr_status", new_status)
                    if new_record_text != record_text:
                        record_path.write_text(new_record_text, encoding="utf-8")
                        fixed_library_record = True
                    if note_path and note_path.exists():
                        try:
                            note_text = note_path.read_text(encoding="utf-8")
                            new_note_text = update_frontmatter_field(note_text, "ocr_status", new_status)
                            if new_note_text != note_text:
                                note_path.write_text(new_note_text, encoding="utf-8")
                                fixed_formal_note = True
                        except Exception:
                            pass
                    if meta_validated_status is not None and meta_validated_status != "done":
                        if meta_path.exists():
                            try:
                                meta = read_json(meta_path)
                                meta["ocr_status"] = "pending"
                                write_json(meta_path, meta)
                                fixed_meta = True
                            except Exception:
                                pass
                    record_do_ocr_match = re.search(r"^do_ocr:\s*(true|false)$", new_record_text, re.MULTILINE)
                    is_do_ocr = record_do_ocr_match and record_do_ocr_match.group(1) == "true"
                    if not is_do_ocr:
                        final_record_text = update_frontmatter_field(new_record_text, "do_ocr", "true")
                        if final_record_text != new_record_text:
                            record_path.write_text(final_record_text, encoding="utf-8")
                            fixed_library_record = True
                elif lib_ocr_status == "done" and meta_ocr_status in ("pending", "processing"):
                    new_status = "pending"
                    new_record_text = update_frontmatter_field(record_text, "ocr_status", new_status)
                    if new_record_text != record_text:
                        record_path.write_text(new_record_text, encoding="utf-8")
                        fixed_library_record = True
                    if note_path and note_path.exists():
                        try:
                            note_text = note_path.read_text(encoding="utf-8")
                            new_note_text = update_frontmatter_field(note_text, "ocr_status", new_status)
                            if new_note_text != note_text:
                                note_path.write_text(new_note_text, encoding="utf-8")
                                fixed_formal_note = True
                        except Exception:
                            pass
                    if meta_path.exists():
                        try:
                            meta = read_json(meta_path)
                            meta["ocr_status"] = "pending"
                            write_json(meta_path, meta)
                            fixed_meta = True
                        except Exception:
                            pass
                    record_do_ocr_match = re.search(r"^do_ocr:\s*(true|false)$", new_record_text, re.MULTILINE)
                    is_do_ocr = record_do_ocr_match and record_do_ocr_match.group(1) == "true"
                    if not is_do_ocr:
                        final_record_text = update_frontmatter_field(new_record_text, "do_ocr", "true")
                        if final_record_text != new_record_text:
                            record_path.write_text(final_record_text, encoding="utf-8")
                            fixed_library_record = True
                fixed_count = sum([fixed_library_record, fixed_formal_note, fixed_meta])
                result["fixed"] += fixed_count
                if verbose and fixed_count > 0:
                    logger.info("fixed %d files for %s", fixed_count, zotero_key)
                if fixed_count > 0:
                    try:
                        refresh_index_entry(vault, zotero_key)
                    except Exception as e:
                        logger.warning("Failed to refresh index for %s: %s", zotero_key, e)
    # Path error detection and repair
    path_errors = _detect_path_errors(paths, verbose)
    if path_errors["total"] > 0:
        error_summary = ", ".join(f"{count} {err}" for err, count in sorted(path_errors["by_type"].items()))
        print(f"[repair] Found {path_errors['total']} items with path errors: {error_summary}")
        if fix_paths:
            fixed_count = repair_pdf_paths(vault, paths, path_errors["records"], verbose)
            print(f"[repair] Fixed {fixed_count} PDF paths")
        else:
            print("[repair] Tip: run with --fix-paths to attempt auto-resolution")
    elif verbose:
        print("[repair] No path errors found")

    result["path_errors"] = path_errors
    return result
