"""OCR materialization — layers [1] lifecycle, [2] provenance, [3] raw,
[4] derived, [5] published identity of the state contract.

Moved from `paperforge/lineage.py::_ocr_artifact_detail` and extended:
- [3] RAW OCR truth (`canonical/blocks.raw.jsonl`) is now checked FIRST —
  a broken raw layer means `ocr.run` (only fix), while a broken derived
  layer with healthy raw means `ocr.rebuild_derived` (local, no remote).
- Artifact file conditions are the full suffix set
  (missing/empty/unreadable/invalid/partial/not_file/permission).
"""

from __future__ import annotations

import json
from pathlib import Path

# ── detail states (probe + reconcile vocabulary) ──────────────────────────

RAW_MISSING = "raw_missing"            # canonical/blocks.raw.jsonl absent → ocr.run
RAW_EMPTY = "raw_empty"                # zero bytes / zero rows → ocr.run
RAW_UNREADABLE = "raw_unreadable"      # cannot decode (random bytes) → ocr.run
RAW_INVALID = "raw_invalid"            # decodes but JSON parse fails → ocr.run
RAW_PARTIAL = "raw_partial"            # some rows valid, then broken → ocr.run
RAW_NOT_FILE = "raw_not_file"          # directory where file expected → ocr.run
RAW_PERMISSION = "raw_permission"      # exists but unreadable by ACL → ocr.run

BLOCKS_MISSING = "blocks_missing"      # derived, healthy raw → rebuild_derived
BLOCKS_EMPTY = "blocks_empty"
BLOCKS_UNREADABLE = "blocks_unreadable"
BLOCKS_INVALID = "blocks_invalid"
BLOCKS_PARTIAL = "blocks_partial"
BLOCKS_NOT_FILE = "blocks_not_file"
BLOCKS_PERMISSION = "blocks_permission"

TREE_MISSING = "tree_missing"          # derived → rebuild_derived
TREE_EMPTY = "tree_empty"
TREE_UNREADABLE = "tree_unreadable"
TREE_INVALID = "tree_invalid"
TREE_NOT_FILE = "tree_not_file"
TREE_PERMISSION = "tree_permission"

ROLE_INDEX_MISSING = "role_index_missing"
ROLE_INDEX_INVALID = "role_index_invalid"
ROLE_INDEX_NOT_FILE = "role_index_not_file"
ROLE_INDEX_UNREADABLE = "role_index_unreadable"
ROLE_INDEX_PERMISSION = "role_index_permission"

PUBLISH_PENDING_RECENT = "publish_pending_recent"  # publishing → wait
PUBLISH_PENDING_STALE = "publish_pending_stale"    # interrupted publish → rebuild_derived
PUBLISH_METADATA_MISSING = "publish_metadata_missing"  # result-hash missing → local repair
PUBLISH_STALE_SECONDS = 3600

NOT_STARTED = "not_started"
QUEUED = "queued"
QUEUED_INTERRUPTED = "queued_interrupted"
RETRYABLE_ERROR = "retryable_error"
FATAL_ERROR = "fatal_error"
FAILED_LEGACY = "failed_legacy"
BLOCKED = "blocked"
NO_PDF = "no_pdf"
VERSION_OLD = "version_old"


def read_meta(paper_dir: Path) -> dict | None:
    """Read meta.json (the OCR lifecycle authority) defensively."""
    try:
        return json.loads((paper_dir / "meta.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def queued_is_zombie(paper_dir: Path, meta: dict | None) -> bool:
    """A queued/running paper past the worker's zombie timeout (default 30
    minutes, PAPERFORGE_ZOMBIE_TIMEOUT_MINUTES) is an orphaned run: the
    worker's own zombie-reset only fires on the NEXT ocr.run, so the probe
    must surface it as interrupted (→ ocr.run) instead of waiting forever."""
    if not meta:
        return False
    started = str(meta.get("ocr_started_at", "") or "")
    if not started:
        return False
    try:
        import os as _os
        from datetime import datetime, timezone

        timeout_min = int(_os.environ.get("PAPERFORGE_ZOMBIE_TIMEOUT_MINUTES", "30"))
        started_dt = datetime.fromisoformat(started)
        if started_dt.tzinfo is None:
            started_dt = started_dt.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - started_dt).total_seconds()
        return age > timeout_min * 60
    except Exception:  # noqa: BLE001 — unparseable start → treat as fresh
        return False


def meta_lifecycle(paper_dir: Path) -> tuple[str | None, str | None]:
    """[1] meta.json ocr_status → (detail, top-level state).

    Covers the REAL worker lifecycle enum, not a subset: none/pending,
    queued/running/processing (with zombie timeout), retryable_error,
    fatal_error/error, blocked, nopdf, AND the legacy "failed" value that
    older metas still carry (→ failed/failed_legacy, never dropped through
    to artifact checks where complete old artifacts would look current).
    done* values fall through to artifact checks."""
    meta = read_meta(paper_dir)
    if not meta:
        return None, None
    st = str(meta.get("ocr_status", "") or "")
    if st in ("none", "pending", ""):
        return NOT_STARTED, "missing"
    if st in ("queued", "running", "processing"):
        if queued_is_zombie(paper_dir, meta):
            return QUEUED_INTERRUPTED, "failed"
        return QUEUED, "missing"
    if st == "retryable_error":
        return RETRYABLE_ERROR, "failed"
    if st in ("fatal_error", "error"):
        return FATAL_ERROR, "failed"
    if st == "failed":
        return FAILED_LEGACY, "failed"
    if st == "blocked":
        return BLOCKED, "missing"
    if st == "nopdf":
        return NO_PDF, "missing"
    return None, None  # done / done_incomplete / done_degraded → artifacts


def publish_marker_state(paper_dir: Path) -> tuple[str | None, str | None]:
    """[5] result-hash.pending (crash-surviving publication marker):
    fresh ⇒ the producer is actively publishing → unknown/wait; stale ⇒
    the producer crashed mid-publish → incomplete/rebuild (never wait
    forever)."""
    marker = paper_dir / "index" / "result-hash.pending"
    if not marker.exists():
        return None, None
    try:
        import time as _time

        age = _time.time() - marker.stat().st_mtime
        if age < PUBLISH_STALE_SECONDS:
            return PUBLISH_PENDING_RECENT, "unknown"
    except OSError:
        pass
    return PUBLISH_PENDING_STALE, "incomplete"


def is_old_pipeline(paper_dir: Path) -> bool:
    """True when the paper was produced by an older OCR pipeline version
    than the current one — the product may be structurally fine (current)
    or incomplete, but the version fact is part of the state machine."""
    try:
        from paperforge.worker.ocr_versions import OCR_PIPELINE_VERSION
    except Exception:  # noqa: BLE001
        return False
    meta = read_meta(paper_dir)
    if not meta:
        return False
    v = str(meta.get("ocr_pipeline_version", "") or "")
    return bool(v) and v != OCR_PIPELINE_VERSION


def top_state(paper_dir: Path | None) -> str | None:
    """The top-level OCR state (judging only, no hash identity):
    not_started / running / failed / blocked / missing / incomplete —
    or None when the chain is fully materialized (caller does the hash
    comparison to decide current vs stale).

    Order: [1] lifecycle → [3] RAW → [5] publish marker → [4] derived →
    [5] published hash.  A pending marker must never shadow a broken raw
    layer (raw is publish's upstream).
    """
    if paper_dir is None or not paper_dir.exists():
        return "missing"
    _lc_detail, lc_state = meta_lifecycle(paper_dir)
    if lc_state is not None:
        return lc_state
    raw = raw_state(paper_dir)
    if raw is not None:
        return "missing"  # raw_* → ocr.run
    _pub_detail, pub_state = publish_marker_state(paper_dir)
    if pub_state is not None:
        return pub_state
    art_detail = ocr_artifact_detail(paper_dir)
    if art_detail is not None:
        # raw_* already handled above; remaining are derived_*/publish_* →
        # incomplete → local ocr.rebuild_derived.
        return "incomplete"
    return None  # materialized — caller compares hash → current/stale


def detail(paper_dir: Path | None) -> str | None:
    """Fine-grained WHY for the ocr state — one namespace, each value one
    meaning (see the constants).  A version fact is a FLAG, never a
    failure reason occupying this slot."""
    if paper_dir is None or not paper_dir.exists():
        return NOT_STARTED
    lc_detail, _ = meta_lifecycle(paper_dir)
    if lc_detail is not None:
        return lc_detail
    raw = raw_state(paper_dir)
    if raw is not None:
        return raw
    pub_detail, _ = publish_marker_state(paper_dir)
    if pub_detail is not None:
        return pub_detail
    art_detail = ocr_artifact_detail(paper_dir)
    if art_detail is not None:
        return art_detail
    return None

RAW_DEFECTS = frozenset({
    RAW_MISSING, RAW_EMPTY, RAW_UNREADABLE, RAW_INVALID,
    RAW_PARTIAL, RAW_NOT_FILE, RAW_PERMISSION,
})
DERIVED_DEFECTS = frozenset({
    BLOCKS_MISSING, BLOCKS_EMPTY, BLOCKS_UNREADABLE, BLOCKS_INVALID,
    BLOCKS_PARTIAL, BLOCKS_NOT_FILE, BLOCKS_PERMISSION,
    TREE_MISSING, TREE_EMPTY, TREE_UNREADABLE, TREE_INVALID,
    TREE_NOT_FILE, TREE_PERMISSION,
    ROLE_INDEX_MISSING, ROLE_INDEX_INVALID, ROLE_INDEX_NOT_FILE,
    ROLE_INDEX_UNREADABLE, ROLE_INDEX_PERMISSION,
    PUBLISH_PENDING_STALE, PUBLISH_METADATA_MISSING,
})


# ── low-level file condition helpers ───────────────────────────────────────

def _file_condition(path: Path) -> str | None:
    """Return the condition suffix for a JSONL artifact or None when valid.

    Order: missing → not_file → empty → unreadable → permission →
    invalid → partial.  Whole-file streaming: every non-blank line must
    parse; a line that fails AFTER earlier lines parsed is `partial`
    (interrupted write).  Used for raw/blocks (JSONL).  Single-JSON files
    (tree/role-index) use their own checks where a truncated JSON is
    simply invalid (no partial state).
    """
    if not path.exists():
        return "missing"
    if path.is_dir():
        return "not_file"
    try:
        if path.stat().st_size == 0:
            return "empty"
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "unreadable"
    except OSError:
        return "permission"
    parsed = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            json.loads(line)
            parsed += 1
        except json.JSONDecodeError:
            if parsed > 0:
                return "partial"
            return "invalid"
    if parsed == 0:
        return "empty"
    return None  # every row parsed


def raw_state(paper_dir: Path) -> str | None:
    """[3] RAW OCR truth — canonical/blocks.raw.jsonl.

    Returns a RAW_* defect or None when raw is healthy."""
    raw = paper_dir / "canonical" / "blocks.raw.jsonl"
    cond = _file_condition(raw)
    if cond is None:
        return None
    return {
        "missing": RAW_MISSING,
        "empty": RAW_EMPTY,
        "unreadable": RAW_UNREADABLE,
        "invalid": RAW_INVALID,
        "partial": RAW_PARTIAL,
        "not_file": RAW_NOT_FILE,
        "permission": RAW_PERMISSION,
    }[cond]


def _blocks_state(paper_dir: Path) -> str | None:
    blocks = paper_dir / "structure" / "blocks.structured.jsonl"
    cond = _file_condition(blocks)
    if cond is not None:
        return {
            "missing": BLOCKS_MISSING,
            "empty": BLOCKS_EMPTY,
            "unreadable": BLOCKS_UNREADABLE,
            "invalid": BLOCKS_INVALID,
            "partial": BLOCKS_PARTIAL,
            "not_file": BLOCKS_NOT_FILE,
            "permission": BLOCKS_PERMISSION,
        }[cond]
    # shape: the first non-blank line must be a BLOCK object (dict with an
    # identity field) — `["not a block"]` or a bare number parses as JSON
    # but is not a block.  Whole-file validation stays in doctor.
    try:
        with blocks.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        return BLOCKS_INVALID
                    if not any(k in obj for k in ("block_id", "page", "role", "raw_order")):
                        return BLOCKS_INVALID
                    break
    except Exception:  # noqa: BLE001
        return BLOCKS_INVALID
    return None


def _tree_state(paper_dir: Path) -> str | None:
    tree = paper_dir / "index" / "structure-tree.json"
    if not tree.exists():
        return TREE_MISSING
    if tree.is_dir():
        return TREE_NOT_FILE
    try:
        data = json.loads(tree.read_text(encoding="utf-8"))
    except PermissionError:
        return TREE_PERMISSION
    except OSError:
        return TREE_PERMISSION
    except UnicodeDecodeError:
        return TREE_UNREADABLE
    except json.JSONDecodeError:
        # Truncated/partial JSON is INVALID for a single-JSON file — there
        # is no meaningful "partial" state (see contract §5 #6).
        return TREE_INVALID
    except Exception:  # noqa: BLE001 — structure
        return TREE_INVALID
    # shape: root dict + nodes list of dicts; empty list is valid shape
    if not isinstance(data, dict):
        return TREE_INVALID
    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        return TREE_INVALID
    if not all(isinstance(n, dict) for n in nodes[:5]):
        return TREE_INVALID
    if not nodes:
        return TREE_EMPTY
    return None


def _role_index_state(paper_dir: Path) -> str | None:
    role = paper_dir / "index" / "role-index.json"
    if not role.exists():
        return ROLE_INDEX_MISSING
    if role.is_dir():
        return ROLE_INDEX_NOT_FILE
    try:
        data = json.loads(role.read_text(encoding="utf-8"))
    except PermissionError:
        return ROLE_INDEX_PERMISSION
    except OSError:
        return ROLE_INDEX_PERMISSION
    except UnicodeDecodeError:
        return ROLE_INDEX_UNREADABLE
    except json.JSONDecodeError:
        return ROLE_INDEX_INVALID
    except Exception:  # noqa: BLE001
        return ROLE_INDEX_INVALID
    if not isinstance(data, dict) or not any(isinstance(v, list) for v in data.values()):
        return ROLE_INDEX_INVALID
    return None


def _published_state(paper_dir: Path) -> str | None:
    """[5] OCR publication identity — result-hash presence.

    Marker AGE is judged ONLY by publish_marker_state() (single threshold);
    this function only checks whether the published hash file exists —
    missing → publish_metadata_missing (local repair), never silent
    current.  Stored-vs-recomputed hash comparison is the caller's job."""
    if (paper_dir / "index" / "result-hash.txt").exists():
        return None
    return PUBLISH_METADATA_MISSING


def ocr_artifact_detail(paper_dir: Path) -> str | None:
    """First-broken frontier across [3] raw → [4] derived → [5] published.

    Returns a detail string or None when the whole chain is present and
    valid.  Caller (probe) adds lifecycle/version/hash decisions around it.

    Routing contract (reconcile consumes this):
    - raw_*      → ocr.run  (remote OCR — the only fix for a broken raw layer)
    - derived_*  → ocr.rebuild_derived (local, from healthy raw)
    - publish_*  → rebuild_derived / wait / local repair
    """
    raw = raw_state(paper_dir)
    if raw is not None:
        return raw
    blocks = _blocks_state(paper_dir)
    if blocks is not None:
        return blocks
    tree = _tree_state(paper_dir)
    if tree is not None:
        return tree
    role = _role_index_state(paper_dir)
    if role is not None:
        return role
    return _published_state(paper_dir)
