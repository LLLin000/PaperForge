"""Context command — generate traceable AI context packs from the canonical index.

Reads the canonical literature asset index and outputs JSON-formatted
entries with provenance traces and AI readiness explanations.

Modes:
    ``paperforge context <key>``       — single paper (single JSON object)
    ``paperforge context --domain D``   — all entries in a domain (JSON array)
    ``paperforge context --collection P`` — entries matching collection path (JSON array)
    ``paperforge context --all``        — full canonical index (JSON array)

Per D-01 (Phase 26), the canonical index entry IS the AI context.
No separate "context pack" format is designed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone


def _format_context_entry(entry: dict) -> dict:
    """Wrap a canonical index entry with provenance and readiness metadata.

    Args:
        entry: A single canonical index entry dict (as produced by
            ``asset_index._build_entry()``).

    Returns:
        A formatted dict with metadata subset + ``_provenance`` +
        ``_ai_readiness`` blocks.
    """
    lifecycle = entry.get("lifecycle", "indexed")
    health = entry.get("health", {})

    maturity_info = entry.get("maturity", {})
    blocking = maturity_info.get("blocking", []) if isinstance(maturity_info, dict) else []

    readiness: dict = {
        "ai_context_ready": lifecycle == "ai_context_ready",
        "lifecycle": lifecycle,
        "maturity_level": maturity_info.get("level", 1) if isinstance(maturity_info, dict) else 1,
        "blocking_factors": blocking,
        "next_step": entry.get("next_step", ""),
    }

    # AIC-04: If not ready, explain why
    if lifecycle != "ai_context_ready":
        reasons: list[str] = []
        if not entry.get("has_pdf"):
            reasons.append("No PDF attachment -- run sync to import")
        elif entry.get("ocr_status") != "done":
            reasons.append(f"OCR status is '{entry.get('ocr_status', 'pending')}' -- run ocr")
        elif entry.get("deep_reading_status") != "done":
            reasons.append("Deep reading not complete -- run /pf-deep")
        if health and isinstance(health, dict):
            unhealthy = [k for k, v in health.items() if v != "healthy"]
            if unhealthy:
                reasons.append(f"Unhealthy asset(s): {', '.join(unhealthy)} -- run repair")
        readiness["blocking_explanation"] = "; ".join(reasons) if reasons else "Unknown blocking state"

    # AIC-02 / AIC-04: Provenance trace — all source asset paths
    provenance: dict = {
        "paper_root": entry.get("paper_root", ""),
        "main_note_path": entry.get("main_note_path", ""),
        "fulltext_path": entry.get("fulltext_path", ""),
        "ocr_md_path": entry.get("ocr_md_path", ""),
        "pdf_path": entry.get("pdf_path", ""),
        "deep_reading_path": entry.get("deep_reading_path", ""),
        "ai_path": entry.get("ai_path", ""),
        "note_path": entry.get("note_path", ""),
        "deep_reading_md_path": entry.get("deep_reading_md_path", ""),
    }

    # Assemble output: metadata subset + provenance + readiness
    output: dict = {
        "_format_version": "1",
        "_context": "Canonical index entry -- the AI context per PaperForge D-01",
        "_generated_at": datetime.now(timezone.utc).isoformat(),
        "zotero_key": entry.get("zotero_key", ""),
        "domain": entry.get("domain", ""),
        "title": entry.get("title", ""),
        "authors": entry.get("authors", []),
        "abstract": entry.get("abstract", ""),
        "journal": entry.get("journal", ""),
        "year": entry.get("year", ""),
        "doi": entry.get("doi", ""),
        "pmid": entry.get("pmid", ""),
        "collections": entry.get("collections", []),
        "_provenance": provenance,
        "_ai_readiness": readiness,
    }
    return output


def run(args: argparse.Namespace) -> int:
    """Execute the context command.

    Args:
        args: Parsed CLI arguments with ``key``, ``domain``, ``collection``,
            ``all``, and ``vault_path`` attributes.

    Returns:
        Exit code: 0 on success, 1 on errors (key not found, no mode specified).
    """
    vault = getattr(args, "vault_path", None)
    if vault is None:
        from paperforge.config import resolve_vault

        vault = resolve_vault(cli_vault=getattr(args, "vault", None))

    # Lazy import to follow established command module pattern
    from paperforge.worker.asset_index import read_index

    data = read_index(vault)
    if data is None:
        print("Error: Canonical index not found. Run 'paperforge sync --rebuild-index' first.", file=sys.stderr)
        return 1

    # Extract items from envelope (or handle legacy bare-list format)
    if isinstance(data, dict):
        items = data.get("items", [])
    elif isinstance(data, list):
        items = data
    else:
        print("Error: Unexpected index format.", file=sys.stderr)
        return 1

    key = getattr(args, "key", None)
    domain = getattr(args, "domain", None)
    collection = getattr(args, "collection", None)
    all_mode = getattr(args, "all", False)

    # Determine mode
    if key:
        # Single-key mode: find exact match
        for entry in items:
            if entry.get("zotero_key") == key:
                output = _format_context_entry(entry)
                print(json.dumps(output, ensure_ascii=False, indent=2))
                return 0

        # Key not found
        print(f"Error: Paper with key '{key}' not found in canonical index.", file=sys.stderr)
        return 1

    elif domain:
        # Domain filter: exact match on "domain" field
        filtered = [e for e in items if e.get("domain") == domain]

    elif collection:
        # Collection filter: prefix match on any element in "collections" list
        filtered = [
            e for e in items if any(isinstance(c, str) and c.startswith(collection) for c in e.get("collections", []))
        ]

    elif all_mode:
        # All entries
        filtered = list(items)

    else:
        print("Error: Specify a key, --domain, --collection, or --all.", file=sys.stderr)
        return 1

    # Multi-entry output (always a JSON array)
    output_list = [_format_context_entry(e) for e in filtered]
    print(json.dumps(output_list, ensure_ascii=False, indent=2))
    return 0
