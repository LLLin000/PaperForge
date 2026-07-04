"""Human feedback sidecar for OCR quality.

Standalone module for collecting, storing, and resolving human validation
marks on OCR quality assessments. No dashboard UI — sidecar API only.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "ocr_quality_feedback_v1"


def read_feedback(path: Path) -> dict[str, Any] | None:
    """Read feedback JSON. Returns None if file doesn't exist."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_feedback(path: Path, feedback: dict[str, Any]) -> None:
    """Atomically write feedback JSON via temp file + rename.

    Validates the marks list is not empty.
    """
    marks = feedback.get("marks", [])
    if not marks:
        raise ValueError("feedback must contain at least one mark")

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(
        json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp.replace(path)


def append_mark(
    path: Path,
    mark: dict[str, Any],
    *,
    current_result_hash: str,
    current_fulltext_hash: str,
) -> dict[str, Any]:
    """Append a human validation mark to the feedback file.

    Hashes are injected automatically from *current_result_hash* and
    *current_fulltext_hash* — the caller must not set them manually.
    Old marks with different hashes are preserved for audit.
    """
    feedback = read_feedback(path)
    if feedback is None:
        feedback = {
            "schema_version": SCHEMA_VERSION,
            "paper_id": "",
            "marks": [],
        }

    # Inject hashes automatically
    mark["result_hash"] = current_result_hash
    mark["fulltext_hash"] = current_fulltext_hash

    if "marked_at" not in mark:
        mark["marked_at"] = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    feedback["marks"].append(mark)
    write_feedback(path, feedback)
    return feedback


def resolve_human_validation(
    feedback: dict[str, Any], current_result_hash: str
) -> dict[str, Any]:
    """Resolve the human validation status from feedback data.

    Status logic
    ------------
    - No marks                      → ``"unreviewed"``
    - Latest mark's hash != current → ``"stale"`` (overrides everything)
    - Latest overall is ``"correct"`` or ``"usable_with_minor_issues"``
                                    → ``"confirmed"``
    - Latest overall is ``"bad"``   → ``"disputed"``
    """
    marks = feedback.get("marks", [])
    if not marks:
        status: str = "unreviewed"
        latest_mark = None
    else:
        latest_mark = marks[-1]
        if latest_mark.get("result_hash") != current_result_hash:
            status = "stale"
        elif latest_mark.get("overall") in (
            "correct",
            "usable_with_minor_issues",
        ):
            status = "confirmed"
        else:
            status = "disputed"

    return {
        "status": status,
        "mark_count": len(marks),
        "latest_mark": latest_mark,
        "feedback_path": "",
    }
