"""Derived lifecycle, health, maturity, and next-step computation for canonical index entries.

Pure functions — no side effects, no filesystem access.  Each function takes a
canonical index entry dict (as produced by ``asset_index._build_entry()``) and
returns a derived value.

Exports:
    compute_lifecycle(entry) -> str    — Six progressive lifecycle states
    compute_health(entry) -> dict      — Per-dimension health findings with fix paths
    compute_maturity(entry) -> dict    — Level 1-6 with check breakdown
    compute_next_step(entry) -> str    — Recommended next action
"""

from __future__ import annotations


def compute_lifecycle(entry: dict) -> str:
    """Derive the current lifecycle state from an index entry.

    Six progressive states (deepest achieved wins):
    - **indexed**: has_pdf=False (entry exists in index, no PDF available)
    - **pdf_ready**: has_pdf=True, ocr NOT validated done
    - **fulltext_ready**: ocr_status == "done" (validated), deep_reading NOT done
    - **deep_read_done**: OCR done AND deep-reading done, but workspace paths incomplete
    - **ai_context_ready**: OCR done AND deep-reading done AND all four workspace paths
      (ai_path, fulltext_path, deep_reading_path, main_note_path) are non-empty strings

    Uses .get() with safe defaults for all field accesses.
    """
    has_pdf = bool(entry.get("has_pdf", False))
    ocr_status = entry.get("ocr_status", "pending")
    deep_reading_status = entry.get("deep_reading_status", "pending")

    # indexed: no PDF available — base state, short-circuit everything else
    if not has_pdf:
        return "indexed"

    # OCR validated done opens the door to fulltext_ready and beyond
    if ocr_status == "done":
        # ai_context_ready: deep-reading also done AND all workspace paths present
        if deep_reading_status == "done":
            ai_path = entry.get("ai_path", "")
            fulltext_path = entry.get("fulltext_path", "")
            deep_reading_path = entry.get("deep_reading_path", "")
            main_note_path = entry.get("main_note_path", "")
            if all([ai_path, fulltext_path, deep_reading_path, main_note_path]):
                return "ai_context_ready"
            return "deep_read_done"

        # fulltext_ready: OCR done but deep-reading not yet done
        return "fulltext_ready"

    # pdf_ready: has PDF attachment but OCR not validated done
    return "pdf_ready"


def compute_health(entry: dict) -> dict[str, str]:
    """Compute per-dimension health findings with concrete fix instructions.

    Returns a dict with four keys:
    - **pdf_health**: PDF path validity
    - **ocr_health**: OCR status with actionable fix paths
    - **note_health**: Formal note existence
    - **asset_health**: Workspace path completeness

    Each value is "healthy" or a descriptive issue string with a fix instruction.
    """
    has_pdf = bool(entry.get("has_pdf", False))
    pdf_path = entry.get("pdf_path", "")
    ocr_status = entry.get("ocr_status", "pending")
    note_path = entry.get("note_path", "")

    # PDF health
    if not has_pdf:
        pdf_health = "healthy"
    elif not pdf_path:
        pdf_health = "PDF path missing: run `paperforge sync` to regenerate"
    else:
        pdf_health = "healthy"

    # OCR health — map ocr_status to concrete message
    ocr_messages = {
        "done": "healthy",
        "pending": "OCR pending: run `paperforge ocr`",
        "processing": "OCR in progress: wait for completion",
        "failed": "OCR failed: check meta.json error, then re-run `paperforge ocr`",
        "blocked": "OCR blocked: check PDF accessibility, then re-run `paperforge ocr`",
        "nopdf": "No PDF available for OCR: add PDF to Zotero entry",
        "done_incomplete": "OCR incomplete: results validation failed — re-run `paperforge ocr`",
    }
    ocr_health = ocr_messages.get(ocr_status, "OCR pending: run `paperforge ocr`")

    # Note health
    note_health = (
        "Formal note missing: run `paperforge sync` to regenerate"
        if not note_path
        else "healthy"
    )

    # Asset health — check all four workspace paths
    workspace_paths = {
        "fulltext_path": entry.get("fulltext_path", ""),
        "deep_reading_path": entry.get("deep_reading_path", ""),
        "main_note_path": entry.get("main_note_path", ""),
        "ai_path": entry.get("ai_path", ""),
    }
    missing = [name for name, val in workspace_paths.items() if not val]

    if not missing:
        asset_health = "healthy"
    else:
        missing_str = ", ".join(sorted(missing))
        asset_health = f"Missing workspace paths: {missing_str}. Run `paperforge sync` to regenerate"

    return {
        "pdf_health": pdf_health,
        "ocr_health": ocr_health,
        "note_health": note_health,
        "asset_health": asset_health,
    }


def compute_maturity(entry: dict) -> dict:
    """Compute maturity level 1-6 with per-check pass/fail breakdown.

    Maturity levels (progressive, each level requires all previous):
    1. **Metadata**: always True (entry existence implies metadata)
    2. **PDF Ready**: has_pdf=True
    3. **Fulltext Ready**: ocr_status="done"
    4. **Figure Ready**: OCR done AND ocr_json_path non-empty
    5. **AI Ready**: lifecycle == "ai_context_ready"
    6. **Review Ready**: all checks pass

    Returns a dict with:
    - ``level``: int (1-6)
    - ``level_name``: str (human-readable)
    - ``checks``: dict[str, bool] per dimension
    - ``blocking``: str | None (which check blocks next level, or None at level 6)

    Delegates to ``compute_lifecycle`` internally — no duplicate derivation logic.
    """
    lifecycle = compute_lifecycle(entry)
    has_pdf = bool(entry.get("has_pdf", False))
    ocr_status = entry.get("ocr_status", "pending")
    ocr_json_path = entry.get("ocr_json_path", "")

    checks = {
        "metadata": True,  # entry exists means it has metadata
        "pdf": has_pdf,
        "fulltext": ocr_status == "done",
        "figure": ocr_status == "done" and bool(ocr_json_path),
        "ai": lifecycle == "ai_context_ready",
        "review": lifecycle == "ai_context_ready",  # all previous checks pass
    }

    level_names = [
        "Metadata",
        "PDF Ready",
        "Fulltext Ready",
        "Figure Ready",
        "AI Ready",
        "Review Ready",
    ]
    check_order = ["metadata", "pdf", "fulltext", "figure", "ai", "review"]

    # Determine level: highest level where all checks up to that point pass
    level = 1
    for i, check_name in enumerate(check_order):
        if checks[check_name]:
            level = i + 1
        else:
            break

    # blocking: first failing check after the achieved level, or None at level 6
    blocking = None
    if level < 6:
        blocking = check_order[level]  # the first check that failed

    return {
        "level": level,
        "level_name": level_names[level - 1],
        "checks": checks,
        "blocking": blocking,
    }


def compute_next_step(entry: dict) -> str:
    """Recommend the next action for this literature asset.

    Returns one of: ``"sync"`` | ``"ocr"`` | ``"repair"`` | ``"/pf-deep"`` |
    ``"rebuild index"`` | ``"ready"``

    Priority-ordered decision:
    1. ocr_status in (failed, blocked, done_incomplete) → "ocr" (retry OCR)
    2. has_pdf=False → "sync" (add PDF in Zotero)
    3. has_pdf=True AND ocr_status in (pending, nopdf) → "ocr"
    4. ocr_status="processing" → "ready" (OCR already running)
    5. ocr_status="done" AND deep_reading_status="pending" → "/pf-deep"
    6. note_path empty → "sync"
    7. Any workspace path empty → "sync"
    8. Otherwise → "ready"
    """
    has_pdf = bool(entry.get("has_pdf", False))
    ocr_status = entry.get("ocr_status", "pending")
    deep_reading_status = entry.get("deep_reading_status", "pending")
    note_path = entry.get("note_path", "")

    # 1. OCR in error state → retry OCR
    if ocr_status in ("failed", "blocked", "done_incomplete"):
        return "ocr"

    # 2. No PDF → sync
    if not has_pdf:
        return "sync"

    # 3. PDF exists but OCR not started → ocr
    if ocr_status in ("pending", "nopdf"):
        return "ocr"

    # 4. OCR already processing → ready
    if ocr_status == "processing":
        return "ready"

    # 5. OCR done, deep reading pending → /pf-deep
    if ocr_status == "done" and deep_reading_status == "pending":
        return "/pf-deep"

    # 6. Formal note missing → sync
    if not note_path:
        return "sync"

    # 7. Any workspace path missing → sync
    workspace_paths = [
        entry.get("fulltext_path", ""),
        entry.get("deep_reading_path", ""),
        entry.get("main_note_path", ""),
        entry.get("ai_path", ""),
    ]
    if not all(workspace_paths):
        return "sync"

    # 8. Everything ready
    return "ready"
