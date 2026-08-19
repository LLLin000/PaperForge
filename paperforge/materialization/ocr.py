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

import hashlib
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
TREE_INCONSISTENT = "tree_inconsistent"  # dangling block refs (P1-C)

ROLE_INDEX_MISSING = "role_index_missing"
ROLE_INDEX_INVALID = "role_index_invalid"
ROLE_INDEX_NOT_FILE = "role_index_not_file"
ROLE_INDEX_UNREADABLE = "role_index_unreadable"
ROLE_INDEX_PERMISSION = "role_index_permission"

PROVENANCE_KEY_MISMATCH = "provenance_key_mismatch"
PROVENANCE_PDF_CHANGED = "provenance_pdf_changed"
PROVENANCE_RAW_MISMATCH = "provenance_raw_mismatch"
PROVENANCE_UNKNOWN = "provenance_unknown"

PROVENANCE_DEFECTS = frozenset({
    PROVENANCE_KEY_MISMATCH,
    PROVENANCE_PDF_CHANGED,
    PROVENANCE_RAW_MISMATCH,
})

PUBLISH_PENDING_RECENT = "publish_pending_recent"  # publishing → wait


def provenance_state(
    paper_dir: Path, canonical_pdf: Path | None, meta: dict | None = None
) -> str | None:
    """[2] OCR ownership / source provenance — is this raw OCR actually
    this paper's, from THIS PDF?

    Chain (P0-B, owner review 2026-08-15):
        expected key == meta.zotero_key
        fingerprint(canonical library main PDF) == meta.raw_version.pdf_fingerprint
        sha256(canonical/blocks.raw.jsonl) == meta.raw_version.raw_blocks_hash

    FAIL-CLOSED (P0-B corrective): a claim that cannot be VERIFIED is
    unknown, never passed.
    - missing EITHER strong evidence (fingerprint OR raw hash) → UNKNOWN
      (a legacy fp without a raw hash cannot prove the current raw is the
      original raw);
    - canonical PDF unresolvable/unreadable → UNKNOWN (cannot disprove,
      but also cannot prove);
    - raw file missing/unreadable → UNKNOWN;
    - verified mismatch → the specific PROVENANCE_* defect;
    - everything verified matching → None (current).
    PDF path is a LOCATOR, never an identity — bytes are the identity.

    ``meta`` may be injected by a caller that already read meta.json once
    for the same observation (probe reads it a single time per paper).
    """
    if meta is None:
        meta = read_meta(paper_dir)
    if not meta:
        # Meta missing OR unreadable (restore corruption) — NO provenance
        # claim can be verified.  Fail-closed: unknown, never pass.  (The
        # lifecycle owns the never-ran case; here we are post-materialization
        # and meta is still unreadable → cannot prove anything.)
        return PROVENANCE_UNKNOWN
    if str(meta.get("zotero_key", "") or "") != paper_dir.name:
        return PROVENANCE_KEY_MISMATCH
    raw_version = meta.get("raw_version") or {}
    recorded_fp = str(raw_version.get("pdf_fingerprint", "") or "")
    recorded_raw_hash = str(raw_version.get("raw_blocks_hash", "") or "")
    # Fail-closed: missing either strong evidence → cannot prove → unknown.
    if not recorded_fp or not recorded_raw_hash:
        return PROVENANCE_UNKNOWN
    # PDF verification against the CANONICAL library main PDF.
    if canonical_pdf is None or not canonical_pdf.exists():
        return PROVENANCE_UNKNOWN  # unresolvable canonical PDF
    try:
        import hashlib as _hashlib

        current_fp = "sha256:" + _hashlib.sha256(canonical_pdf.read_bytes()).hexdigest()
    except OSError:
        return PROVENANCE_UNKNOWN  # unreadable canonical PDF
    if current_fp != recorded_fp:
        return PROVENANCE_PDF_CHANGED
    # Raw content verification.
    raw = paper_dir / "canonical" / "blocks.raw.jsonl"
    if not raw.exists():
        return PROVENANCE_UNKNOWN  # raw missing — cannot verify
    try:
        import hashlib as _hashlib

        current_raw = "sha256:" + _hashlib.sha256(raw.read_bytes()).hexdigest()
    except OSError:
        return PROVENANCE_UNKNOWN  # raw unreadable — cannot verify
    if current_raw != recorded_raw_hash:
        return PROVENANCE_RAW_MISMATCH
    return None
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


def meta_lifecycle(paper_dir: Path, meta: dict | None = None) -> tuple[str | None, str | None]:
    """[1] meta.json ocr_status → (detail, top-level state).

    Covers the REAL worker lifecycle enum, not a subset: none/pending,
    queued/running/processing (with zombie timeout), retryable_error,
    fatal_error/error, blocked, nopdf, AND the legacy "failed" value that
    older metas still carry (→ failed/failed_legacy, never dropped through
    to artifact checks where complete old artifacts would look current).
    done* values fall through to artifact checks.

    ``meta`` may be injected by a caller that already read meta.json once
    (probe reads it a single time per paper).
    """
    if meta is None:
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


def is_old_pipeline(paper_dir: Path, meta: dict | None = None) -> bool:
    """True when the paper was produced by an older OCR pipeline version
    than the current one — the product may be structurally fine (current)
    or incomplete, but the version fact is part of the state machine."""
    try:
        from paperforge.worker.ocr_versions import OCR_PIPELINE_VERSION
    except Exception:  # noqa: BLE001
        return False
    if meta is None:
        meta = read_meta(paper_dir)
    if not meta:
        return False
    v = str(meta.get("ocr_pipeline_version", "") or "")
    return bool(v) and v != OCR_PIPELINE_VERSION


def top_state(paper_dir: Path | None, meta: dict | None = None) -> str | None:
    """The top-level OCR state (judging only, no hash identity):
    not_started / running / failed / blocked / missing / incomplete —
    or None when the chain is fully materialized (caller does the hash
    comparison to decide current vs stale).

    Order: [1] lifecycle → [3] RAW → [5] publish marker → [4] derived →
    [5] published hash.  A pending marker must never shadow a broken raw
    layer (raw is publish's upstream).

    ``meta`` may be injected by a caller that already read meta.json once
    (probe reads it a single time per paper).
    """
    if paper_dir is None or not paper_dir.exists():
        return "missing"
    _lc_detail, lc_state = meta_lifecycle(paper_dir, meta)
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


def detail(
    paper_dir: Path | None,
    canonical_pdf: Path | None = None,
    meta: dict | None = None,
) -> str | None:
    """Fine-grained WHY for the ocr state — one namespace, each value one
    meaning (see the constants).  A version fact is a FLAG, never a
    failure reason occupying this slot.

    ``meta`` may be injected by a caller that already read meta.json once
    (probe reads it a single time per paper).
    """
    if paper_dir is None or not paper_dir.exists():
        return NOT_STARTED
    lc_detail, _ = meta_lifecycle(paper_dir, meta)
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
    return provenance_state(paper_dir, canonical_pdf, meta=meta)

RAW_DEFECTS = frozenset({
    RAW_MISSING, RAW_EMPTY, RAW_UNREADABLE, RAW_INVALID,
    RAW_PARTIAL, RAW_NOT_FILE, RAW_PERMISSION,
})
DERIVED_DEFECTS = frozenset({
    BLOCKS_MISSING, BLOCKS_EMPTY, BLOCKS_UNREADABLE, BLOCKS_INVALID,
    BLOCKS_PARTIAL, BLOCKS_NOT_FILE, BLOCKS_PERMISSION,
    TREE_MISSING, TREE_EMPTY, TREE_UNREADABLE, TREE_INVALID,
    TREE_NOT_FILE, TREE_PERMISSION, TREE_INCONSISTENT,
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


def _tree_block_refs(tree: dict) -> set[str]:
    """Every block reference the tree makes, normalized to pN:id form."""
    refs: set[str] = set()
    for n in tree.get("nodes", []) or []:
        if not isinstance(n, dict):
            continue
        page = n.get("page")
        bid = n.get("block_id")
        if page is not None and bid is not None:
            refs.add(f"p{page}:{bid}")
        for key in ("own_block_ids", "subtree_block_ids"):
            for r in (n.get(key, []) or []):
                if isinstance(r, str):
                    refs.add(r)
    return refs


def tree_blocks_consistency(paper_dir: Path) -> str | None:
    """P1-C: every block reference in the tree must resolve to a block in
    blocks.structured.jsonl.  Dangling refs → TREE_INCONSISTENT (stale or
    foreign tree), never silently accepted.  None = consistent."""
    blocks = paper_dir / "structure" / "blocks.structured.jsonl"
    if not blocks.exists():
        return None  # blocks state is judged separately
    block_ids: set[str] = set()
    try:
        for line in blocks.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            page = obj.get("page")
            bid = obj.get("block_id")
            if page is not None and bid is not None:
                block_ids.add(f"p{page}:{bid}")
    except Exception:  # noqa: BLE001 — unreadable blocks judged separately
        return None
    tree = paper_dir / "index" / "structure-tree.json"
    if not tree.exists():
        return None
    try:
        data = json.loads(tree.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — tree state judged separately
        return None
    if not isinstance(data, dict):
        return None
    dangling = _tree_block_refs(data) - block_ids
    if dangling:
        return TREE_INCONSISTENT
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
    consistency = tree_blocks_consistency(paper_dir)
    if consistency is not None:
        return consistency
    role = _role_index_state(paper_dir)
    if role is not None:
        return role
    return _published_state(paper_dir)

def published_identity_hash(paper_dir: Path) -> str:
    """[5] OCR publication identity — the CURRENT canonical OCR result hash
    (single source of truth; memory/retrieval consumers call THIS, never
    re-implement hash resolution).

    Three-level fallback (moved from memory/builder._resolve_ocr_result_hash,
    ADR-0002: materialization owns the judgment):
    1. index/result-hash.txt (fastest, preferred)
    2. canonical hash of the structured artifacts
    3. meta.json derived_version hash

    While ``index/result-hash.pending`` exists, neither the stale Level-1
    file nor half-built artifacts may be trusted — return "" so consumers
    skip the paper entirely.
    """
    try:
        from paperforge.worker.ocr_hash import (
            compute_ocr_result_hash,
            has_result_hash_pending,
        )
    except Exception:  # noqa: BLE001
        return ""
    if has_result_hash_pending(paper_dir):
        return ""
    rp = paper_dir / "index" / "result-hash.txt"
    if rp.exists():
        try:
            return rp.read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    canonical = compute_ocr_result_hash(paper_dir)
    if canonical is not None:
        return canonical
    meta_p = paper_dir / "meta.json"
    if meta_p.exists():
        try:
            import json as _json

            dv = _json.loads(meta_p.read_bytes()).get("derived_version", {})
            return hashlib.sha256(_json.dumps(dv, sort_keys=True).encode()).hexdigest()
        except Exception:  # noqa: BLE001
            pass
    return ""

def identity_state(paper_dir: Path) -> tuple[str | None, str | None]:
    """[5] OCR publication identity state — (state, hash): current | stale
    | (None, None) when unverifiable.

    Compares the PUBLISHED hash (index/result-hash.txt) against the
    recomputed canonical artifact hash.  Single source of truth — probe,
    reconcile, and memory all consume this; nobody re-implements the
    comparison.  Missing published hash → (None, None) (publish_metadata
    missing is judged by the artifact chain, not here)."""
    try:
        from paperforge.worker.ocr_hash import (
            compute_ocr_result_hash,
            has_result_hash_pending,
        )
    except Exception:  # noqa: BLE001
        return None, None
    if has_result_hash_pending(paper_dir):
        return None, None  # publishing in flight — unverifiable
    stored = None
    rp = paper_dir / "index" / "result-hash.txt"
    if rp.exists():
        try:
            stored = rp.read_text(encoding="utf-8").strip()
        except OSError:
            stored = None
    recomputed = compute_ocr_result_hash(paper_dir)
    if recomputed is None:
        return None, None
    if stored is None:
        # published metadata missing — the artifact chain reports
        # publish_metadata_missing; identity itself is unverifiable here.
        return None, None
    if stored != recomputed:
        return "stale", recomputed
    return "current", recomputed
