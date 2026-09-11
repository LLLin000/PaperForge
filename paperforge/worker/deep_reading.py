from __future__ import annotations

from pathlib import Path

from paperforge.adapters.obsidian_frontmatter import has_deep_reading_content
from paperforge.worker._utils import get_analyze_queue


def run_deep_reading(vault: Path, verbose: bool = False) -> int:
    """Read and report the deep-reading queue without changing the vault.

    The command is a status check. It observes note content and the indexed
    queue in memory; sync, base-view, report, and memory-index writes belong to
    their owning commands and must not happen on this path.
    """
    records = get_analyze_queue(vault)
    status_mismatches = 0
    pending_queue: list[dict] = []

    for record in records:
        key = record["zotero_key"]
        has_content = False
        note_path = record["note_path"]
        if note_path and note_path.exists():
            note_text = note_path.read_text(encoding="utf-8")
            has_content = has_deep_reading_content(note_text)
        correct_status = "done" if has_content else "pending"

        if record["deep_reading_status"] != correct_status:
            status_mismatches += 1

        if correct_status == "pending":
            pending_queue.append(
                {
                    "zotero_key": key,
                    "domain": record["domain"],
                    "title": record["title"],
                    "ocr_status": record["ocr_status"],
                    "is_analyze": True,
                    "is_do_ocr": record["do_ocr"],
                }
            )

    # `verbose` remains part of the worker API for callers that pass it, but a
    # read-only status command must not materialize a report as a side effect.
    del verbose
    print(
        "deep-reading: observed "
        f"{status_mismatches} status mismatches, {len(pending_queue)} pending"
    )
    return 0
