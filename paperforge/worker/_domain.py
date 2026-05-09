"""Shared domain config module — single source of truth for domain-collections.json.

This module replaces 7 copy-pasted copies of load_domain_config scattered across
worker files. It performs a FULL REBUILD from export files on every call,
ensuring stale domains are cleaned up and new ones are added automatically.

Data classification:
  P2 derived cache — always rebuilt from exports/*.json (ground truth)
"""

from __future__ import annotations

import logging
from pathlib import Path

from paperforge.worker._utils import read_json, write_json
from paperforge.adapters.collections import build_collection_lookup

logger = logging.getLogger(__name__)


# ── Collection tree utilities ────────────────────────────────────────────────
# build_collection_lookup re-exported from paperforge.adapters.collections


def export_collection_paths(export_path: Path) -> list[str]:
    """Extract all unique collection paths from a BBT export JSON file."""
    data = read_json(export_path)
    if not isinstance(data, dict):
        return []
    collections = data.get("collections", {})
    if not isinstance(collections, dict):
        return []
    lookup = build_collection_lookup(collections)
    paths = sorted(
        {path for path in lookup.get("path_by_key", {}).values() if str(path or "").strip()},
        key=lambda value: (value.count("/"), value),
    )
    return paths


# ── Domain config ────────────────────────────────────────────────────────────


def load_domain_config(paths: dict[str, Path]) -> dict:
    """Load or FULLY REBUILD the domain-collections.json config.

    Every call scans exports/*.json as ground truth:
      - Adds domains for new export files
      - Removes domains whose export files no longer exist
      - Updates allowed_collections from actual Zotero collection tree

    Returns: {"domains": [{"domain": ..., "export_file": ..., "allowed_collections": [...]}, ...]}
    """
    config_path = paths["config"]

    try:
        existing = read_json(config_path) if config_path.exists() else {"domains": []}
    except Exception:
        existing = {"domains": []}

    old_entries = existing.get("domains", [])
    export_files = sorted(paths["exports"].glob("*.json"))

    fresh_entries = []
    for export_path in export_files:
        domain = export_path.stem
        try:
            collections = export_collection_paths(export_path)
        except Exception:
            logger.warning("Failed to parse export file: %s", export_path.name)
            collections = []
        fresh_entries.append(
            {
                "domain": domain,
                "export_file": export_path.name,
                "allowed_collections": collections,
            }
        )

    config = {"domains": fresh_entries}

    # Compare before/after to decide write
    old_sorted = sorted(old_entries, key=lambda e: e.get("domain", ""))
    new_sorted = sorted(fresh_entries, key=lambda e: e.get("domain", ""))
    if old_sorted != new_sorted:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(config_path, config)

    return config


def load_domain_collections(paths: dict[str, Path]) -> dict[str, list[str]]:
    """Convenience: return {domain: [collection_path, ...]} mapping.

    Used by candidate collection resolution in sync.py.
    """
    config = load_domain_config(paths)
    return {
        entry["domain"]: entry.get("allowed_collections", [])
        for entry in config.get("domains", [])
        if entry.get("domain")
    }
