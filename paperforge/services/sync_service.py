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
        from paperforge.config import load_vault_config

        cfg = load_vault_config(self.vault)
        system_dir = self.vault / cfg.get("system_dir", "99_System")
        exports_dir = system_dir / "PaperForge" / "exports"
        if not exports_dir.exists():
            logger.warning("Exports directory not found: %s", exports_dir)
            return []

        rows = []
        for f in sorted(exports_dir.glob("*.json")):
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
                    normalized = re.sub(r"[^a-z0-9]", "", title.lower())[:20]
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

            deleted = 0
            for key in to_delete:
                try:
                    records_info[key]["file"].unlink()
                    deleted += 1
                except Exception:
                    pass
            if deleted > 0 and not json_output:
                print(f"index-refresh: cleaned {deleted} orphaned records in {domain}")
            total_deleted += deleted

        return total_deleted

    def clean_flat_notes(self, paths: dict[str, Path], json_output: bool = False) -> int:
        """Delete flat formal notes whose workspace equivalent exists.

        Migrated from worker/sync.py run_index_refresh (v2.2).
        Returns number of flat notes deleted.
        """
        from paperforge.config import paperforge_paths
        from paperforge.worker._utils import slugify_filename

        try:
            from paperforge.worker.asset_index import read_index as _read_idx

            index_data = _read_idx(self.vault)
        except Exception:
            index_data = None

        _paths = paths if paths else paperforge_paths(self.vault)
        lit_dir = _paths.get("literature")
        if not lit_dir or not lit_dir.exists():
            return 0

        ws_keys: set[str] = set()
        if isinstance(index_data, dict):
            for item in index_data.get("items", []):
                ws_dir = (
                    lit_dir
                    / item.get("domain", "")
                    / (item.get("zotero_key", "") + " - " + slugify_filename(item.get("title", "")))
                )
                if ws_dir.is_dir():
                    ws_keys.add(item.get("zotero_key"))

        if not ws_keys:
            return 0

        cleaned = 0
        for domain_dir in sorted(lit_dir.iterdir()):
            if not domain_dir.is_dir():
                continue
            for flat_note in list(domain_dir.glob("*.md")):
                try:
                    text = flat_note.read_text(encoding="utf-8")
                    fm = read_frontmatter_dict(text)
                    key = str(fm.get("zotero_key", "")).strip()
                except Exception:
                    continue
                if key and key in ws_keys:
                    try:
                        flat_note.unlink()
                        cleaned += 1
                    except Exception:
                        pass

        if cleaned > 0 and not json_output:
            print(f"index-refresh: cleaned {cleaned} flat note(s) (migrated to workspace)")

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

    def run(
        self, verbose: bool = False, json_output: bool = False, selection_only: bool = False, index_only: bool = False,
        prune: bool = False, prune_force: bool = False, rebuild_index: bool = False,
    ) -> PFResult:
        """Full sync orchestration. Returns PFResult contract.

        v2.2: Service now orchestrates the full sync lifecycle:
        1. Load BBT exports
        2. Selection sync (count items from worker)
        3. Build canonical index (asset_index)
        4. Clean orphaned records + flat notes
        5. Return PFResult

        Args:
            selection_only: Skip index build + cleanup phases.
            index_only: Skip selection sync phase.
        """
        # ── Pre-check: BBT exports ──
        _export_code = "ok"
        try:
            rows = self.load_exports()
            if not rows:
                _export_code = "BBT_EXPORT_NOT_FOUND"
        except Exception:
            _export_code = "BBT_EXPORT_INVALID"

        selection_result: dict = {"new": 0, "updated": 0, "skipped": 0, "failed": 0, "errors": []}
        _prune_preview: list[dict] = []

        # ── Phase 1: Select ──
        if not index_only:
            import time as _time

            from paperforge.worker.sync import run_selection_sync

            _t0 = _time.time()
            try:
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

            paths = self.resolve_paths()
            config = load_domain_config(paths)
            ensure_base_views(self.vault, paths, config)
            domain_lookup = {entry["export_file"]: entry["domain"] for entry in config["domains"]}

            from paperforge.config import load_vault_config

            load_vault_config(self.vault)
            exports: dict[str, dict[str, dict]] = {}
            for export_path in sorted(paths["exports"].glob("*.json")):
                domain = domain_lookup.get(export_path.name, export_path.stem)
                export_rows = load_export_rows(export_path)
                exports[domain] = {row["key"]: row for row in export_rows}

            from paperforge.worker.sync import migrate_to_workspace

            migrate_to_workspace(self.vault, paths)

            import paperforge.worker.asset_index as asset_index

            _t2 = _time.time()
            index_count = asset_index.build_index(self.vault, verbose, force_rebuild=rebuild_index)
            _t3 = _time.time()
            logger.info("build_index: %d entries in %.1fs", index_count, _t3 - _t2)

            # ── Phase 3: Clean ──
            orphaned = self.clean_orphaned_records(exports, paths, json_output=json_output)
            flat_cleaned = self.clean_flat_notes(paths, json_output=json_output)

            if orphaned > 0 or flat_cleaned > 0:
                index_count = asset_index.build_index(self.vault, verbose, force_rebuild=rebuild_index)

            # ── Phase 4: Prune orphans ──
            prune_data = None
            try:
                prune_data = self.prune(paths, fresh_index=None, dry_run=True)
                if prune_force:
                    prune_data = self.prune(paths, fresh_index=None, dry_run=False)
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

        is_ok = selection_result.get("failed", 0) == 0 and not selection_result.get("errors")

        result = PFResult(
            ok=is_ok,
            command="sync",
            version=__version__,
            data={
                "selection": selection_result,
                "index": {"updated": index_count, "orphaned_cleaned": orphaned, "flat_cleaned": flat_cleaned},
                "prune": {"preview": _prune_preview} if _prune_preview else None,
            },
        )

        if _export_code != "ok":
            result.warnings.append(f"BBT exports: {_export_code}")

        # ── Preflight: OCR runtime dirty files ──
        _dirty = _get_dirty_files()
        if _dirty:
            result.warnings.extend(detect_ocr_runtime_preflight_issues(_dirty))

        return result

    def prune(self, paths: dict, fresh_index: dict | None = None, *, dry_run: bool = True) -> dict:
        """Run orphan paper cleanup. Default dry_run=True (preview only)."""
        if fresh_index is None:
            from paperforge.worker.asset_index import read_index
            fresh_index = read_index(self.vault)
        from paperforge.worker.prune import prune_orphan_papers
        return prune_orphan_papers(self.vault, fresh_index=fresh_index, dry_run=dry_run)

    # ── Legacy passthrough (backward-compat for commands/sync.py) ──

    def run_sync(self, verbose: bool = False, json_output: bool = False) -> PFResult:
        """Alias for run(). Returns PFResult (not int|dict)."""
        return self.run(verbose=verbose, json_output=json_output)
