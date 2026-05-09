from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from paperforge.adapters.bbt import (
    extract_authors,
    _identify_main_pdf,
    _normalize_attachment_path,
    load_export_rows,
    resolve_item_collection_paths,
)
from paperforge.adapters.obsidian_frontmatter import (
    candidate_markdown,
    read_frontmatter_dict,
    update_frontmatter_field,
)
from paperforge.adapters.zotero_paths import (
    absolutize_vault_path,
    obsidian_wikilink_for_path,
    obsidian_wikilink_for_pdf,
)

logger = logging.getLogger(__name__)


class SyncService:
    """Orchestrates the sync lifecycle: load BBT exports, match entries, generate notes."""

    def __init__(self, vault: Path):
        self.vault = vault
        self.paths: dict[str, Path] = {}
        self._resolved = False

    def resolve_paths(self) -> dict[str, Path]:
        """Resolve vault paths using pipeline_paths."""
        from paperforge.worker._utils import pipeline_paths
        self.paths = pipeline_paths(self.vault)
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

    def run_sync(self, verbose: bool = False, json_output: bool = False) -> int | dict:
        """Full sync orchestration. Delegates to run_selection_sync logic.

        Returns int (exit code) for CLI mode, dict for json_output mode.
        """
        from paperforge.worker.sync import run_selection_sync
        return run_selection_sync(self.vault, verbose=verbose, json_output=json_output)
