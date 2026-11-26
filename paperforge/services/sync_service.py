from __future__ import annotations

import logging
import re
from pathlib import Path

from paperforge import __version__
from paperforge.adapters.bbt import (
    load_export_rows,
)
from paperforge.adapters.obsidian_frontmatter import (
    candidate_markdown,
    read_frontmatter_dict,
)
from paperforge.core import timing
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult

logger = logging.getLogger(__name__)

_OCR_RUNTIME_FILES: tuple[str, ...] = (
    "paperforge/worker/ocr_render.py",
    "paperforge/worker/ocr_objects.py",
)


def _get_dirty_files() -> list[str]:
    """Return list of files with unstaged changes via git diff --name-only."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        pass
    return []


def detect_ocr_runtime_preflight_issues(dirty_files: list[str]) -> list[str]:
    """Check if any watched OCR runtime files have uncommitted changes.

    Args:
        dirty_files: Relative paths of files with uncommitted changes.

    Returns:
        List of warning strings. Empty if no issues.
    """
    watched = {f.replace("\\", "/") for f in _OCR_RUNTIME_FILES}
    warnings: list[str] = []
    for dirty in dirty_files:
        normalized = dirty.replace("\\", "/")
        if normalized in watched:
            warnings.append(f"OCR runtime file has uncommitted changes: {dirty}")
    return warnings


def summarize_ocr_version_actions(papers: list[dict]) -> dict:
    """Summarize OCR version actions across a list of paper version states.

    Args:
        papers: List of paper dicts with derived_stale and raw_upgradable flags.

    Returns:
        Dict with derived_rebuild_count, raw_upgrade_count, and paper list.
    """
    derived_stale = [p for p in papers if p.get("derived_stale")]
    raw_upgradable = [p for p in papers if p.get("raw_upgradable")]
    return {
        "derived_rebuild_count": len(derived_stale),
        "raw_upgrade_count": len(raw_upgradable),
        "derived_stale_keys": [p["zotero_key"] for p in derived_stale],
        "raw_upgrade_keys": [p["zotero_key"] for p in raw_upgradable],
    }


def summarize_ocr_runtime_followups(
    papers: list[dict],
    dirty_runtime_files: bool = False,
) -> dict:
    """Summarize OCR runtime follow-up actions with scheduling mode.

    When dirty_runtime_files is True, auto-derived-rebuild is suppressed
    and the mode is 'suppressed_dirty_runtime'. Otherwise the mode is
    'deferred' --- sync records what needs doing but does not execute inline.
    """
    derived_stale = [p for p in papers if p.get("derived_stale") and not p.get("raw_upgradable")]
    raw_upgradable = [p for p in papers if p.get("raw_upgradable")]
    legacy = [p for p in papers if p.get("is_legacy")]

    mode = "suppressed_dirty_runtime" if dirty_runtime_files else "deferred"

    result: dict = {
        "derived_rebuild_count": len(derived_stale),
        "raw_upgrade_count": len(raw_upgradable),
        "derived_stale_keys": [p["zotero_key"] for p in derived_stale],
        "raw_upgrade_keys": [p["zotero_key"] for p in raw_upgradable],
        "derived_rebuild_mode": mode,
        "legacy_count": len(legacy),
        "legacy_keys": [p["zotero_key"] for p in legacy],
        "backfill_count": len(legacy),
        "backfill_keys": [p["zotero_key"] for p in legacy],
    }

    if mode == "suppressed_dirty_runtime":
        result["suppressed_keys"] = [p["zotero_key"] for p in derived_stale]

    return result


class SyncService:
    """Orchestrates the sync lifecycle: load BBT exports, match entries, generate notes.

    v2.1: This service currently delegates heavy lifting to worker/sync.py.
    The load_exports / build_candidates methods are functional; run() wraps
    the legacy worker and enforces the PFResult contract.  Full migration
    of note-writing logic is planned for v2.2.
    """

    def __init__(self, vault: Path):
        self.vault = vault
        self.paths: dict[str, Path] = {}
        self._resolved = False

    def resolve_paths(self) -> dict[str, Path]:
        """Resolve vault paths using paperforge_paths."""
        from paperforge.config import paperforge_paths

        self.paths = paperforge_paths(self.vault)
        self._resolved = True
        return self.paths

    def load_exports(self) -> list[dict]:
        """Load all BBT export JSON files."""
        from paperforge.config import paperforge_paths

        exports_dir = paperforge_paths(self.vault)["exports"]
        if not exports_dir.exists():
            logger.warning("Exports directory not found: %s", exports_dir)
            return []

        rows = []
        json_files = sorted(
            p for p in exports_dir.iterdir() if p.is_file() and p.suffix.lower() == ".json"
        )
        for f in json_files:
            try:
                rows.extend(load_export_rows(f))
            except Exception as e:
                logger.error("Failed to load %s: %s", f.name, e)
        return rows

    def clean_orphaned_records(
        self, exports: dict[str, dict[str, dict]], paths: dict[str, Path], json_output: bool = False
    ) -> int:
        """Remove formal notes whose title duplicates an exported item but lacks PDF.

        Migrated from worker/sync.py run_index_refresh (v2.2).
        Returns number of orphaned records deleted.
        """
        from paperforge.config import paperforge_paths

        _paths = paths if paths else paperforge_paths(self.vault)
        lit_dir = _paths.get("literature")
        if not lit_dir or not lit_dir.exists():
            return 0

        total_deleted = 0
        for domain_dir in lit_dir.iterdir():
            if not domain_dir.is_dir():
                continue
            domain = domain_dir.name
            domain_export_keys = set(exports.get(domain, {}).keys())
            records_by_title: dict[str, list[str]] = {}
            records_info: dict[str, dict] = {}

            for record_file in domain_dir.rglob("*.md"):
                if record_file.name in ("fulltext.md", "deep-reading.md", "discussion.md"):
                    continue
                try:
                    content = record_file.read_text(encoding="utf-8")
                    fm = read_frontmatter_dict(content)
                    key = str(fm.get("zotero_key", "")).strip()
                    if not key:
                        continue
                    title = str(fm.get("title", ""))
                    has_pdf = fm.get("has_pdf", False) is True
                    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", title.lower())
                    if not normalized:
                        continue
                    records_info[key] = {
                        "file": record_file,
                        "title": title,
                        "has_pdf": has_pdf,
                        "normalized": normalized,
                    }
                    if normalized not in records_by_title:
                        records_by_title[normalized] = []
                    records_by_title[normalized].append(key)
                except Exception:
                    continue

            to_delete: list[str] = []
            for _normalized, keys in records_by_title.items():
                keys_in_export = [k for k in keys if k in domain_export_keys]
                keys_not_in_export = [k for k in keys if k not in domain_export_keys]
                if keys_in_export and keys_not_in_export:
                    for k in keys_not_in_export:
                        if not records_info[k]["has_pdf"]:
                            to_delete.append(k)

            from paperforge.worker.trash import trash_remove

            deleted = 0
            for key in to_delete:
                try:
                    rec = trash_remove(
                        records_info[key]["file"],
                        vault=self.vault,
                        allowed_root=domain_dir,
                        operation="sync.clean_orphaned_records",
                        paper_key=key,
                    )
                    if rec is not None:
                        deleted += 1
                except Exception:
                    pass
            if deleted > 0 and not json_output:
                print(f"index-refresh: cleaned {deleted} orphaned records in {domain}")
            total_deleted += deleted

        return total_deleted

    def clean_flat_notes(self, paths: dict[str, Path], json_output: bool = False) -> int:
        """Quarantine flat formal notes whose verified workspace equivalent exists.

        Uses structured ``zotero_key`` identity anchors rather than title-slug
        path guessing and moves duplicates to ``.paperforge/trash/`` via
        ``quarantine_move`` instead of calling ``unlink()``.
        """
        from paperforge.config import paperforge_paths
        from paperforge.services.identity_resolver import scan_vault_identities
        from paperforge.services.vault_engine import quarantine_move

        _paths = paths if paths else paperforge_paths(self.vault)
        lit_dir = _paths.get("literature")
        if not lit_dir or not lit_dir.exists():
            return 0

        scan = scan_vault_identities(lit_dir)
        if not scan.workspaces or not scan.flat_notes:
            return 0

        cleaned = 0
        for flat in scan.flat_notes:
            if flat.classification != "verified_legacy_flat":
                continue
            ws = scan.workspaces.get(flat.zotero_key)
            if ws is None or ws.main_note_path is None or not ws.main_note_path.is_file():
                continue
            try:
                rec = quarantine_move(
                    flat.note_path,
                    vault=self.vault,
                    allowed_root=lit_dir,
                    operation="clean_migrated_flat_note",
                    paper_key=flat.zotero_key,
                )
                if rec is not None:
                    cleaned += 1
            except Exception:
                pass

        if cleaned > 0 and not json_output:
            print(f"index-refresh: quarantined {cleaned} flat note(s) (migrated to workspace)")

        return cleaned

    def build_candidates(self, rows: list[dict]) -> list[dict]:
        """Generate candidate markdown entries from BBT rows."""
        candidates = []
        for row in rows:
            try:
                markdown = candidate_markdown(row)
                candidates.append({"row": row, "markdown": markdown})
            except Exception as e:
                logger.error("Failed to build candidate: %s", e)
        return candidates

    def _compute_sync_fastpath_digest(self, paths: dict[str, Path]) -> str:
        """Stat-based digest across exports, OCR meta.json, paperforge.json, workspace notes, and Zotero storage."""
        import hashlib
        import os as _os

        h = hashlib.sha256()
        cfg_file = self.vault / "paperforge.json"
        if cfg_file.exists():
            try:
                st = cfg_file.stat()
                h.update(f"cfg:{st.st_size}:{st.st_mtime_ns}\n".encode("utf-8"))
            except OSError:
                pass
        exports_dir = paths.get("exports")
        if exports_dir and exports_dir.exists():
            for ep in sorted(exports_dir.glob("*.json")):
                try:
                    st = ep.stat()
                    h.update(f"exp:{ep.name}:{st.st_size}:{st.st_mtime_ns}\n".encode("utf-8"))
                except OSError:
                    pass
        ocr_dir = paths.get("ocr")
        if ocr_dir and ocr_dir.exists():
            try:
                with _os.scandir(ocr_dir) as it:
                    entries = sorted((e.name, e.path) for e in it if e.is_dir())
                for name, pdir in entries:
                    mp = Path(pdir) / "meta.json"
                    if mp.exists():
                        st = mp.stat()
                        h.update(f"ocr:{name}:{st.st_size}:{st.st_mtime_ns}\n".encode("utf-8"))
            except OSError:
                pass
        lit_dir = paths.get("literature")
        if lit_dir and lit_dir.exists():
            try:
                with _os.scandir(lit_dir) as d_it:
                    doms = sorted((d.name, d.path) for d in d_it if d.is_dir())
                for dname, dpath in doms:
                    with _os.scandir(dpath) as n_it:
                        for ne in sorted(n_it, key=lambda x: x.name):
                            if ne.is_file() and ne.name.endswith(".md"):
                                st = ne.stat()
                                h.update(f"note:{dname}/{ne.name}:{st.st_size}:{st.st_mtime_ns}\n".encode("utf-8"))
                            elif ne.is_dir():
                                try:
                                    ws_st = _os.stat(ne.path)
                                    h.update(f"ws:{dname}/{ne.name}:{ws_st.st_mtime_ns}\n".encode("utf-8"))
                                    with _os.scandir(ne.path) as ws_it:
                                        for wse in sorted(ws_it, key=lambda x: x.name):
                                            if wse.is_file() and wse.name.endswith(".md"):
                                                wst = _os.stat(wse.path)
                                                h.update(
                                                    f"wsn:{dname}/{ne.name}/{wse.name}:{wst.st_size}:{wst.st_mtime_ns}\n".encode("utf-8")
                                                )
                                except OSError:
                                    pass
            except OSError:
                pass
        zdir = paths.get("zotero_dir")
        if zdir:
            for zname in ("zotero.sqlite", "zotero.sqlite-wal"):
                zp = zdir / zname
                if zp.is_file():
                    try:
                        st = zp.stat()
                        h.update(f"zot:{zname}:{st.st_size}:{st.st_mtime_ns}\n".encode("utf-8"))
                    except OSError:
                        pass
            storage_dir = zdir / "storage"
            if storage_dir.is_dir():
                try:
                    h.update(f"zst:{storage_dir.stat().st_mtime_ns}\n".encode("utf-8"))
                    with _os.scandir(storage_dir) as s_it:
                        for se in sorted(s_it, key=lambda x: x.name):
                            if se.is_dir():
                                h.update(f"zsd:{se.name}:{_os.stat(se.path).st_mtime_ns}\n".encode("utf-8"))
                                with _os.scandir(se.path) as f_it:
                                    for fe in sorted(f_it, key=lambda x: x.name):
                                        if fe.is_file():
                                            fst = fe.stat()
                                            h.update(f"zsf:{se.name}/{fe.name}:{fst.st_size}:{fst.st_mtime_ns}\n".encode("utf-8"))
                except OSError:
                    pass
        return h.hexdigest()

    def _materialize_sqlite_exports_if_enabled(self, paths: dict[str, Path]) -> None:
        """Direct read-only sync from zotero.sqlite when enabled. Fails closed on DB errors."""
        enabled, zdir, domain_mode, selected = self._validate_sqlite_source_if_enabled(paths)
        if not enabled or zdir is None:
            return
        from paperforge.adapters.zotero_sqlite import materialize_zotero_sqlite_exports

        materialize_zotero_sqlite_exports(
            self.vault,
            paths["exports"],
            zdir,
            selected_collections=selected,
            domain_mode=domain_mode,
        )

    def _check_fastpath_preflight(self) -> tuple[dict[str, Path] | None, PFResult | None]:
        """Delegate to bottom-defined helper."""
        return self._check_fastpath_or_sqlite_preflight()

    def run(
        self, verbose: bool = False, json_output: bool = False, selection_only: bool = False, index_only: bool = False,
        prune: bool = False, prune_force: bool = False, rebuild_index: bool = False,
    ) -> PFResult:
        """Full sync orchestration. Returns PFResult contract."""
        import json as _json
        import os as _os

        fastpath_eligible = not (selection_only or index_only or rebuild_index or prune or prune_force)
        fastpath_paths: dict[str, Path] | None = None
        fastpath_digest = ""
        if fastpath_eligible:
            fastpath_paths, fp_err_or_hit = self._check_fastpath_or_sqlite_preflight()
            if fp_err_or_hit is not None:
                return fp_err_or_hit

        # ── Phase 0: Direct zotero.sqlite materialization (when fastpath missed) ──
        if fastpath_paths is None:
            fastpath_paths = self.resolve_paths()
        mat_err = self._safe_materialize_sqlite_phase0(fastpath_paths)
        if mat_err is not None:
            return mat_err

        # ── Pre-check: BBT / materialized exports ──
        _export_code = "ok"
        try:
            with timing.phase("sync.load_exports"):
                rows = self.load_exports()
            if not rows:
                _export_code = "BBT_EXPORT_NOT_FOUND"
        except PermissionError as exc:
            return PFResult(
                ok=False,
                command="sync",
                version=__version__,
                error=PFError(
                    code=ErrorCode.SYNC_FAILED,
                    message=f"Permission denied reading exports directory: {exc}",
                    details={"phase": "load_exports", "exception_type": type(exc).__name__},
                ),
            )
        except Exception:
            _export_code = "BBT_EXPORT_INVALID"

        selection_result: dict = {"new": 0, "updated": 0, "skipped": 0, "failed": 0, "errors": []}
        _prune_preview: list[dict] = []
        ocr_runtime_summary: dict = {
            "derived_rebuild_count": 0, "raw_upgrade_count": 0,
            "derived_stale_keys": [], "raw_upgrade_keys": [],
            "derived_rebuild_mode": "deferred",
        }

        # ── Phase 1: Select ──
        import time as _time

        if not index_only:
            from paperforge.worker.sync import run_selection_sync

            _t0 = _time.time()
            try:
                with timing.phase("sync.selection"):
                    selection_result = run_selection_sync(self.vault, verbose=verbose, json_output=json_output)
                _t1 = _time.time()
                logger.info("select: %d items in %.1fs", selection_result.get("updated", 0), _t1 - _t0)
            except Exception as exc:
                return PFResult(
                    ok=False,
                    command="sync",
                    version=__version__,
                    error=PFError(
                        code=ErrorCode.SYNC_FAILED,
                        message=str(exc),
                        details={"phase": "selection", "exception_type": type(exc).__name__},
                    ),
                )

        # ── Phase 2: Index ──
        index_count = 0
        orphaned = 0
        flat_cleaned = 0

        if not selection_only:
            from paperforge.worker._domain import load_domain_config
            from paperforge.worker.base_views import ensure_base_views

            with timing.phase("sync.resolve_paths"):
                paths = self.resolve_paths()
                config = load_domain_config(paths)
                ensure_base_views(self.vault, paths, config)
            domain_lookup = {entry["export_file"]: entry["domain"] for entry in config["domains"]}

            from paperforge.config import load_vault_config

            load_vault_config(self.vault)
            exports: dict[str, dict[str, dict]] = {}
            with timing.phase("sync.load_export_rows"):
                for export_path in sorted(paths["exports"].glob("*.json")):
                    domain = domain_lookup.get(export_path.name, export_path.stem)
                    export_rows = load_export_rows(export_path)
                    exports[domain] = {row["key"]: row for row in export_rows}

            from paperforge.worker.sync import migrate_to_workspace

            with timing.phase("sync.migrate_to_workspace"):
                migrate_to_workspace(self.vault, paths)

            import paperforge.worker.asset_index as asset_index

            _t2 = _time.time()
            with timing.phase("sync.build_index"):
                index_count = asset_index.build_index(self.vault, verbose, force_rebuild=rebuild_index)
            _t3 = _time.time()
            logger.info("build_index: %d entries in %.1fs", index_count, _t3 - _t2)

            # ── Phase 3: Clean ──
            with timing.phase("sync.cleanup"):
                orphaned = self.clean_orphaned_records(exports, paths, json_output=json_output)
                flat_cleaned = self.clean_flat_notes(paths, json_output=json_output)

            if orphaned > 0 or flat_cleaned > 0:
                with timing.phase("sync.rebuild_index_after_cleanup"):
                    index_count = asset_index.build_index(self.vault, verbose, force_rebuild=rebuild_index)

            # ── Phase 4: Prune orphans ──
            prune_data = None
            try:
                # Zotero is the authority (2026-08-14): orphans = workspace
                # papers absent from the LIVE export.  The index snapshot
                # may lag a freshly added Zotero paper and falsely orphan
                # its workspace — never compare against the index here.
                _zotero_keys = {
                    k for _domain in exports.values() for k in _domain
                }
                _source_ok = _export_code == "ok" and bool(_zotero_keys)
                with timing.phase("sync.prune_preview"):
                    prune_data = self.prune(paths, fresh_keys=_zotero_keys, dry_run=True, source_ok=_source_ok)
                if prune_force:
                    prune_data = self.prune(
                        paths, fresh_keys=_zotero_keys, dry_run=False, source_ok=_source_ok
                    )
            except Exception as exc:
                logger.warning("prune skipped: %s", exc)
                prune_data = {"preview": [], "deleted": [], "counts": {"workspace": 0, "ocr": 0, "vectors": 0, "failed": 0}}
            if prune or prune_force:
                if not json_output:
                    pdata = prune_data or {}
                    preview = pdata.get("preview", [])
                    if preview:
                        print(f"prune: found {len(preview)} orphan paper(s)")
                        if not prune_force:
                            print("prune: dry-run (pass --prune-force to delete)")
                        else:
                            counts = pdata.get("counts", {})
                            msg = (f"prune: deleted {len(pdata.get('deleted', []))} paper(s) "
                                   f"(ws={counts.get('workspace',0)} ocr={counts.get('ocr',0)} "
                                   f"vec={counts.get('vectors',0)})")
                            print(msg)
                    else:
                        print("prune: no orphans found")
            # always include prune preview in result (for plugin consumption)
            _prune_preview = prune_data.get("preview", []) if prune_data else []

            if not json_output:
                print(f"index-refresh: {index_count} entries in index")
                total = sum(1 for _ in paths["literature"].rglob("*.md")) if paths["literature"].exists() else 0
                print(f"index-refresh: {total} formal note(s) in literature")

            # ── Phase 5: OCR version scan ──
            try:
                from paperforge.core.io import read_json

                from paperforge.worker._utils import pipeline_paths
                from paperforge.worker.ocr_versions import (
                    classify_legacy_ocr_state,
                    classify_version_state,
                    expected_derived_payload,
                    expected_raw_payload,
                )

                ocr_root = pipeline_paths(self.vault)["ocr"]
                if ocr_root.exists():
                    papers: list[dict] = []
                    for paper_dir in ocr_root.iterdir():
                        if not paper_dir.is_dir():
                            continue
                        meta_path = paper_dir / "meta.json"
                        if not meta_path.exists():
                            continue
                        meta = read_json(meta_path)
                        raw_ver = meta.get("raw_version", {})
                        state = classify_version_state(
                            meta=meta,
                            expected_raw=expected_raw_payload(ocr_model=raw_ver.get("ocr_model", "unknown")),
                            expected_derived=expected_derived_payload(),
                        )

                        legacy_state = classify_legacy_ocr_state(
                            meta=meta,
                            ocr_dir=paper_dir,
                        )

                        papers.append({
                            "zotero_key": paper_dir.name,
                            "derived_stale": state["derived_stale"],
                            "raw_upgradable": state["raw_upgradable"],
                            "derived_reasons": state["derived_reasons"],
                            "raw_reasons": state["raw_reasons"],
                            "is_legacy": legacy_state["is_legacy"],
                            "can_backfill": legacy_state["can_backfill"],
                        })

                    # Check for dirty runtime files only when explicitly enabled
                    _dirty = (
                        _get_dirty_files()
                        if _os.environ.get("PAPERFORGE_CHECK_GIT_DIRTY") == "1"
                        else []
                    )
                    watched_dirty = bool(detect_ocr_runtime_preflight_issues(_dirty))

                    ocr_runtime_summary = summarize_ocr_runtime_followups(
                        papers=papers,
                        dirty_runtime_files=watched_dirty,
                    )

                    if ocr_runtime_summary["derived_rebuild_count"] > 0 and not json_output:
                        mode = ocr_runtime_summary["derived_rebuild_mode"]
                        count = ocr_runtime_summary["derived_rebuild_count"]
                        if mode == "suppressed_dirty_runtime":
                            print(f"ocr: {count} derived-stale paper(s) deferred (dirty runtime files)")
                        elif mode == "deferred":
                            print(f"ocr: {count} derived-stale paper(s) identified (deferred)")

                    if ocr_runtime_summary["raw_upgrade_count"] > 0 and not json_output:
                        print(f"ocr: {ocr_runtime_summary['raw_upgrade_count']} paper(s) can be upgraded (redo available)")

                    # Legacy backfill: can_backfill papers get derived artifacts rebuilt
                    if ocr_runtime_summary.get("backfill_count", 0) > 0:
                        from paperforge.worker.ocr_rebuild import (
                            backfill_from_result,
                            select_legacy_papers_for_backfill,
                        )

                        backfill_keys = select_legacy_papers_for_backfill(papers)
                        backfill_results: list[dict] = []
                        for bk in backfill_keys:
                            br = backfill_from_result(self.vault, bk)
                            backfill_results.append(br)

                        ocr_runtime_summary["backfill_results"] = backfill_results
                        done_count = sum(1 for r in backfill_results if r.get("backfill_status") == "done")

                        if not json_output and done_count > 0:
                            print(f"ocr: backfilled {done_count} legacy paper(s) with derived artifacts")

            except Exception as exc:
                logger.warning("ocr version scan skipped: %s", exc)

        is_ok = selection_result.get("failed", 0) == 0 and not selection_result.get("errors")

        result = PFResult(
            ok=is_ok,
            command="sync",
            version=__version__,
            data={
                "selection": selection_result,
                "index": {"updated": index_count, "orphaned_cleaned": orphaned, "flat_cleaned": flat_cleaned},
                "prune": {"preview": _prune_preview} if _prune_preview else None,
                "ocr_runtime": ocr_runtime_summary,
            },
        )

        if _export_code != "ok":
            result.warnings.append(f"BBT exports: {_export_code}")

        # ── Preflight: OCR runtime dirty files (opt-in dev check) ──
        _dirty = (
            _get_dirty_files()
            if _os.environ.get("PAPERFORGE_CHECK_GIT_DIRTY") == "1"
            else []
        )
        if _dirty:
            result.warnings.extend(detect_ocr_runtime_preflight_issues(_dirty))

        if fastpath_eligible and is_ok:
            try:
                _fp_paths = fastpath_paths or self.resolve_paths()
                _fp_file = _fp_paths["paperforge"] / "indexes" / ".sync-fastpath.json"
                _fp_file.parent.mkdir(parents=True, exist_ok=True)
                _new_digest = self._compute_sync_fastpath_digest(_fp_paths)
                _fp_file.write_text(
                    _json.dumps({"digest": _new_digest, "data": result.data}, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception:
                pass

        return result

    def prune(
        self,
        paths: dict,
        fresh_index: dict | None = None,
        *,
        fresh_keys: set[str] | None = None,
        dry_run: bool = True,
        source_ok: bool = True,
    ) -> dict:
        """Run orphan paper cleanup. Default dry_run=True (preview only).

        Zotero is the authority: pass ``fresh_keys`` = the live export key
        set so an orphan is a workspace paper absent from Zotero (the index
        snapshot can lag a fresh Zotero addition and falsely orphan it)."""
        from paperforge.worker.prune import prune_orphan_papers

        return prune_orphan_papers(
            self.vault,
            fresh_index=fresh_index,
            fresh_keys=fresh_keys,
            dry_run=dry_run,
            source_ok=source_ok,
        )

    # ── Legacy passthrough (backward-compat for commands/sync.py) ──

    def run_sync(self, verbose: bool = False, json_output: bool = False) -> PFResult:
        """Alias for run(). Returns PFResult (not int|dict)."""
        return self.run(verbose=verbose, json_output=json_output)

    def _validate_sqlite_source_if_enabled(self, paths: dict[str, Path]) -> tuple[bool, Path | None, str, list[str] | None]:
        """Check Zotero SQLite configuration & readability; fail closed on missing/locked/corrupt DB."""
        from paperforge.config import load_config

        snap = load_config(self.vault)
        mode = str(snap.values["zotero_source_mode"].value or "sqlite")
        if mode != "sqlite":
            return (False, None, "per_collection", None)

        raw_zdir_cfg = str(snap.values["zotero_data_dir"].value or "").strip()
        zdir = paths.get("zotero_dir")
        db_file = (zdir / "zotero.sqlite") if zdir else None

        if raw_zdir_cfg:
            if not zdir or not db_file or not db_file.is_file():
                raise FileNotFoundError(
                    f"Configured Zotero database not found: {db_file or raw_zdir_cfg}"
                )
        elif not zdir or not db_file or not db_file.is_file():
            return (False, None, "per_collection", None)

        with open(db_file, "rb") as fh:
            hdr = fh.read(16)
        if hdr != b"SQLite format 3\x00":
            raise ValueError(f"Invalid or corrupt Zotero SQLite database header: {db_file}")

        domain_mode = str(snap.values["domain_mode"].value or "per_collection")
        raw_sel = str(snap.values["zotero_selected_collections"].value or "").strip()
        selected: list[str] | None = None
        if raw_sel:
            if raw_sel.startswith("["):
                import json as _json

                parsed = _json.loads(raw_sel)
                if isinstance(parsed, list):
                    selected = [str(x).strip() for x in parsed if str(x).strip()]
            else:
                selected = [s.strip() for s in raw_sel.split(",") if s.strip()]
        return (True, zdir, domain_mode, selected)

    def _check_fastpath_or_sqlite_preflight(self) -> tuple[dict[str, Path] | None, PFResult | None]:
        import json as _json

        try:
            fastpath_paths = self.resolve_paths()
            self._validate_sqlite_source_if_enabled(fastpath_paths)
            fp_file = fastpath_paths["paperforge"] / "indexes" / ".sync-fastpath.json"
            idx_file = fastpath_paths["index"]
            if fp_file.exists() and idx_file.exists():
                fastpath_digest = self._compute_sync_fastpath_digest(fastpath_paths)
                cached = _json.loads(fp_file.read_text(encoding="utf-8"))
                if cached.get("digest") == fastpath_digest and isinstance(cached.get("data"), dict):
                    return fastpath_paths, PFResult(
                        ok=True, command="sync", version=__version__, data=cached["data"]
                    )
            return fastpath_paths, None
        except (FileNotFoundError, PermissionError, OSError, ValueError) as exc:
            return None, PFResult(
                ok=False,
                command="sync",
                version=__version__,
                error=PFError(
                    code=ErrorCode.SYNC_FAILED,
                    message=f"Zotero SQLite source unreadable: {exc}",
                    details={"phase": "sqlite_preflight", "exception_type": type(exc).__name__},
                ),
            )
        except Exception:
            return None, None

    def _safe_materialize_sqlite_phase0(self, fastpath_paths: dict[str, Path]) -> PFResult | None:
        try:
            self._materialize_sqlite_exports_if_enabled(fastpath_paths)
            return None
        except Exception as exc:
            return PFResult(
                ok=False,
                command="sync",
                version=__version__,
                error=PFError(
                    code=ErrorCode.SYNC_FAILED,
                    message=f"Zotero SQLite materialization failed: {exc}",
                    details={"phase": "sqlite_materialization", "exception_type": type(exc).__name__},
                ),
            )
