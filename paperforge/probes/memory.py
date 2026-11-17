"""paperforge.probes.memory — memory capability reader (P1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from paperforge.probes.envelope import (build_action_primary, build_envelope, CAPABILITY_OPTIONAL, CAPABILITY_REQUIRED, SAFETY_DESTRUCTIVE, TTL_MEMORY, USER_STATE_ACTION_REQUIRED, USER_STATE_DETECTION_FAILED, USER_STATE_READY, USER_STATE_SETUP_REQUIRED)


def _resume_feasible(vault: Path) -> bool:
    """Resume is feasible when:
    - a surviving shadow candidate exists → shadow-recover continues it
      regardless of substrate state; or
    - no candidate, but the substrate is compatible (identity established) →
      in-place incremental embedding works.
    Only a GLOBAL substrate defect with no candidate forces embed.build."""
    try:
        from paperforge.embedding.substrate import (
            assess_vector_substrate,
            effective_vector_db,
        )
        from paperforge.memory.db import get_memory_db_path

        if effective_vector_db(vault) != get_memory_db_path(vault):
            return True  # surviving candidate → recover
        sub = assess_vector_substrate(vault)
        return bool(sub.db_exists and sub.compatible)
    except Exception:  # noqa: BLE001
        return False


def probe_memory(vault: Path) -> dict[str, Any]:
    """Probe the Memory module.

    Wraps the decision tree with a structured ``details`` block (single
    source of truth for the settings panel's info card): the frontend
    renders API-key / database / build-progress rows from these fields —
    never from its own caches or snapshot files.
    """
    env = _probe_memory_impl(vault)
    env["details"] = _memory_panel_details(vault)
    return env


def _memory_panel_details(vault: Path) -> dict[str, Any]:
    """Structured memory facts for the Smart Retrieval settings panel.

    Each field is computed from the SAME authority the probe decision tree
    uses, so the panel's text can never contradict the state machine:
    credential presence from ``auth status``, DB counts from the live DB
    status, build progress from build_state.  Any single failure degrades
    to a conservative value — never an exception.
    """
    try:
        from paperforge.credentials import CredentialKey
        from paperforge.credentials import status as credential_status

        api_key_configured = credential_status(CredentialKey("embedding")).state == "available"
    except Exception:  # noqa: BLE001
        api_key_configured = False
    try:
        from paperforge.memory.query import get_memory_status

        _st = get_memory_status(vault)
        paper_count_db = int(_st.get("paper_count_db", 0) or 0)
        paper_count_index = int(_st.get("paper_count_index", 0) or 0)
    except Exception:  # noqa: BLE001
        paper_count_db = 0
        paper_count_index = 0
    try:
        from paperforge.embedding.build_state import read_vector_build_state

        _bs = read_vector_build_state(vault)
        build_state = {
            "status": _bs.get("status", "idle"),
            "current": int(_bs.get("current", 0) or 0),
            "total": int(_bs.get("total", 0) or 0),
        }
    except Exception:  # noqa: BLE001
        build_state = {"status": "unknown", "current": 0, "total": 0}
    return {
        "api_key_configured": api_key_configured,
        "paper_count_db": paper_count_db,
        "paper_count_index": paper_count_index,
        "build_state": build_state,
    }


def _probe_memory_impl(vault: Path) -> dict[str, Any]:
    """Probe the Memory module.

    Decision tree (resolved by grilling 2026-07-23):
    1. Module disabled → not_enabled
    2. No paperforge.db → build memory
    3. Schema mismatch → rebuild / restore
    4. Index stale → rebuild index
    5. build_state routes the vector backend:
       a. completed → ready (+ API key notice if missing)
       b. running  → ready + activity
       c. failed   → rebuild vector
       d. absent   → build vector
    """
    # ── Gate 0: canonical config present (fail closed, #142) ────────────
    from paperforge.config import ConfigError as _ConfigError
    from paperforge.config import load_config as _load_canonical_config

    try:
        _load_canonical_config(vault)
    except _ConfigError as exc:
        return build_envelope(
            module="memory", capability_state="missing_input", severity="warning",
            reason_code="memory.config_missing",
            reason_text=f"paperforge.json unavailable ({exc.code}) — run config init/setup",
            user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
            action_primary=build_action_primary(
                action_id="foundation.setup", verb="setup",
                label="Setup PaperForge",
            ),
            ttl_seconds=TTL_MEMORY,
        )

    # ── Gates 1-4: DB-based checks ────────────────────────────────────
    try:
        from paperforge.memory.query import get_memory_status
        status = get_memory_status(vault)
    except Exception:
        return build_envelope(
            module="memory", capability_state="unknown", severity="unknown",
            reason_code="memory.probe_failed", reason_text="Memory status check failed — probe to retry",
            user_state=USER_STATE_DETECTION_FAILED, capability_kind=CAPABILITY_OPTIONAL,
            action_primary=build_action_primary(
                action_id="memory.probe", verb="probe", label="Retry",
            ),
            ttl_seconds=TTL_MEMORY,
        )

    db_exists: bool = status.get("db_exists", False)
    schema_ok: bool = status.get("schema_ok", False)
    fresh: bool = status.get("fresh", False)
    paper_count_db: int = status.get("paper_count_db", 0)
    paper_count_index: int = status.get("paper_count_index", 0)

    if not db_exists:
        return build_envelope(
            module="memory", capability_state="needs_action", severity="warning",
            reason_code="memory.db_missing", reason_text="Memory database has not been built yet",
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
            action_primary=build_action_primary(
                action_id="memory.build", verb="run", label="Build memory",
            ),
            ttl_seconds=TTL_MEMORY,
        )

    # Reader-barrier timeout / DB busy is TRANSIENT — never corruption.  The
    # plugin's polling can pile up readers on the mutex barrier; reporting a
    # healthy DB as corrupted sent users to restore-from-backup for nothing.
    if status.get("locked"):
        return build_envelope(
            module="memory", capability_state="unknown", severity="warning",
            reason_code="memory.db_busy",
            reason_text="Memory database is busy (another PaperForge operation is running) — retry shortly",
            user_state=USER_STATE_DETECTION_FAILED, capability_kind=CAPABILITY_OPTIONAL,
            action_primary=build_action_primary(
                action_id="memory.probe", verb="probe", label="Retry",
            ),
            ttl_seconds=60,
        )

    # Schema check failed
    if not schema_ok:
        if paper_count_db > 0:
            # DB has papers but old schema → needs rebuild
            return build_envelope(
                module="memory", capability_state="needs_action", severity="warning",
                reason_code="memory.migration_needed",
                reason_text="Memory database schema version is outdated — rebuild to update",
                user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
                maintenance_eligible=True,
                action_primary=build_action_primary(
                    action_id="memory.rebuild",
                    verb="rebuild_index", label="Rebuild database",
                ),
                ttl_seconds=TTL_MEMORY,
            )
        # DB exists but empty/unreadable — rebuild or restore from backup
        from paperforge.config import paperforge_paths
        paths = paperforge_paths(vault)
        backup_exists = (paths["paperforge"] / "indexes" / "paperforge.db.backup").exists()
        notices: list[dict[str, Any]] = []
        if backup_exists:
            return build_envelope(
                module="memory", capability_state="unavailable", severity="error",
                reason_code="memory.db_corrupt",
                reason_text="Memory database is corrupted — a verified backup is available for restore",
                user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
                maintenance_eligible=True,
                user_impact="Search and retrieval are unavailable until the database is restored",
                action_primary=build_action_primary(
                    action_id="memory.restore_backup",
                    verb="restore_backup", label="Restore from backup",
                    safety_class=SAFETY_DESTRUCTIVE,
                    replacement_facts=["Current corrupted database"],
                    preservation_facts=["Corrupted database saved as timestamped snapshot"],
                    confirmation_required=True,
                    confirmation_prompt="This will replace the memory database with the backup copy. The corrupted database will be preserved. Proceed?",
                ),
                notices=notices, ttl_seconds=TTL_MEMORY,
            )
        return build_envelope(
            module="memory", capability_state="unavailable", severity="error",
            reason_code="memory.db_corrupt",
            reason_text="Memory database is corrupted or uninitialized — rebuild required (source data preserved)",
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
            maintenance_eligible=True,
            user_impact="Search and retrieval are unavailable until the database is rebuilt",
            action_primary=build_action_primary(
                action_id="memory.rebuild",
                verb="run", label="Rebuild memory",
            ),
            notices=notices, ttl_seconds=TTL_MEMORY,
        )

    # Index behind the database: search still works, its data is stale.
    # Outstanding work, not a fault — ready with an informational notice.
    if not fresh:
        _stale_notice = (
            "Memory index is behind the database — rebuild to refresh search ("
            + (
                f"{paper_count_index} of {paper_count_db} papers indexed"
                if paper_count_db != paper_count_index
                else f"content changed since the last build; {paper_count_db} papers"
            )
            + ")"
        )
        return build_envelope(
            module="memory", capability_state="ready", severity="ok",
            reason_code="memory.index_stale",
            reason_text=_stale_notice,
            user_state=USER_STATE_READY, capability_kind=CAPABILITY_OPTIONAL,
            notices=[{"level": "info", "message": _stale_notice}],
            action_primary=None,
            ttl_seconds=TTL_MEMORY,
        )

    # ── Vector backend health via build_state ────────────────────────────
    notices: list[dict[str, Any]] = []
    try:
        from paperforge.embedding.build_state import read_vector_build_state

        build_state = read_vector_build_state(vault)
        bs_status = build_state.get("status", "idle")

        # Gate 5a: completed → ready
        if bs_status == "completed":
            # ADR-0002 P0-D: SERVING truth = the LIVE db (the retrieval
            # gateway reads live, never the candidate).  publish_pending is
            # decided by the CANDIDATE ALONE (exists + rows + completed,
            # never published) — independent of whether live is empty or
            # holds old vectors.  probe and reconcile share this SSOT.
            from paperforge.embedding.substrate import (
                assess_vector_publication,
                assess_vector_substrate,
            )
            from paperforge.memory.db import get_memory_db_path

            _publication = assess_vector_publication(vault)
            if _publication["publish_pending"]:
                return build_envelope(
                    module="memory", capability_state="needs_action", severity="warning",
                    reason_code="memory.vector_publish_pending",
                    reason_text=(
                        "A completed vector build exists but has not been "
                        "published — the serving (live) database is still "
                        "serving the old state. Resume to publish it."
                    ),
                    user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
                    action_primary=build_action_primary(
                        action_id="embed.resume",
                        verb="run", label="Publish vector build",
                    ),
                    ttl_seconds=TTL_MEMORY,
                )
            # The published identity must match config — a completed build
            # under an OLD model/endpoint is not searchable with the
            # current one (substrate says identity_changed) and must
            # surface a rebuild, agreeing with embed status and reconcile.
            _live_sub = assess_vector_substrate(
                vault, db_path=get_memory_db_path(vault)
            )
            _substrate_mismatch = bool(_live_sub.identity_changed or _live_sub.layout_incompatible)
            _substrate_reason = next(
                (c for c in _live_sub.reason_codes if c.startswith("vector.")), ""
            )
            if _substrate_mismatch:
                return build_envelope(
                    module="memory", capability_state="needs_action", severity="warning",
                    reason_code="memory.vector_identity_changed",
                    reason_text=(
                        f"Embedding configuration changed (model or endpoint "
                        f"{_substrate_reason or 'mismatch'}); existing vectors were "
                        f"built under the previous configuration. Rebuild to match "
                        f"the current one."
                    ),
                    user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
                    action_primary=build_action_primary(
                        action_id="embed.build",
                        verb="run", label="Rebuild vector index",
                    ),
                    ttl_seconds=TTL_MEMORY,
                )
            # #119: the vector stack (openai + sqlite-vec) is a hard runtime
            # requirement for Build Index / Retrieve — a healthy-looking DB
            # with missing deps must NOT report ready.
            _dep_missing: list[str] = []
            try:
                import openai  # noqa: F401
            except ImportError:
                _dep_missing.append("openai")
            try:
                import sqlite_vec  # noqa: F401
            except ImportError:
                _dep_missing.append("sqlite_vec")
            if _dep_missing:
                return build_envelope(
                    module="memory", capability_state="needs_action", severity="warning",
                    reason_code="memory.dependencies_missing",
                    reason_text=f"Smart Retrieval deps missing: {', '.join(_dep_missing)} — run `paperforge runtime repair` outside Obsidian",
                    user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
                    notices=[{"kind": "warning", "text": f"Missing: {', '.join(_dep_missing)}. Restore the managed runtime with `paperforge runtime repair` outside Obsidian."}],
                    action_primary=build_action_primary(
                        action_id="memory.install_vector_deps", verb="install",
                        label="Install Smart Retrieval dependencies",
        
                    ),
                    ttl_seconds=TTL_MEMORY,
                )
            # Quick credential presence check (#173/C1: auth status, no value)
            from paperforge.credentials import CredentialKey
            from paperforge.credentials import status as credential_status

            if credential_status(CredentialKey("embedding")).state != "available":
                notices.append({
                    "kind": "warning",
                    "text": "API key not configured — search works, but the next rebuild needs one",
                })
            return build_envelope(
                module="memory", capability_state="ready", severity="ok",
                reason_code="memory.ready",
                reason_text=f"Memory database healthy ({paper_count_db} papers, {paper_count_index} indexed)",
                user_state=USER_STATE_READY, capability_kind=CAPABILITY_OPTIONAL,
                notices=notices, action_primary=None, ttl_seconds=TTL_MEMORY,
            )

        # Gate 5b: running → ready + activity
        if bs_status == "running":
            # RC UX Seam: a build_state stuck at "running" whose pid is dead
            # (crash / kill / Obsidian restart) is a zombie — the previous
            # process can never write a terminal state.  Reporting ready
            # leaves the user with no way to recover.  Treat it as an
            # interrupted build: needs_action with the resume path.
            pid = build_state.get("pid", 0)
            pid_alive = False
            try:
                from paperforge.commands import embed

                pid_alive = embed._pid_alive(int(pid)) if pid else False
            except Exception:
                pid_alive = False
            if not pid_alive:
                try:
                    _can_resume = _resume_feasible(vault)
                except Exception:  # noqa: BLE001
                    _can_resume = False
                _bs_current = int(build_state.get("current", 0) or 0)
                _bs_total = int(build_state.get("total", 0) or 0)
                return build_envelope(
                    module="memory", capability_state="needs_action", severity="warning",
                    reason_code="memory.vector_build_interrupted",
                    reason_text=(
                        f"Vector index is partially built: {_bs_current}/{_bs_total} "
                        f"papers embedded (the previous build process is no longer "
                        f"running). Resume to embed the remaining "
                        f"{max(_bs_total - _bs_current, 0)} papers."
                    ),
                    user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
                    action_primary=build_action_primary(
                        action_id="embed.build" if not _can_resume else "embed.resume",
                        verb="run",
                        label=(
                            "Resume vector build"
                            if _can_resume
                            else "Rebuild vector index"
                        ),
                    ),
                    notices=notices, ttl_seconds=TTL_MEMORY,
                )
            act_label = f"Building vector index ({build_state.get('current', 0)}/{build_state.get('total', 0)})"
            act_progress = {
                "current": build_state.get("current", 0),
                "total": build_state.get("total", 0),
            }
            return build_envelope(
                module="memory", capability_state="ready", severity="ok",
                reason_code="memory.ready",
                reason_text=f"Memory database healthy ({paper_count_db} papers, {paper_count_index} indexed)",
                user_state=USER_STATE_READY, capability_kind=CAPABILITY_OPTIONAL,
                activity_state="running", activity_label=act_label,
                activity_progress=act_progress,
                notices=notices, action_primary=None, ttl_seconds=TTL_MEMORY,
            )

        # Gate 5c: interrupted (explicit stop) → resume
        if bs_status == "interrupted":
            try:
                _can_resume = _resume_feasible(vault)
            except Exception:  # noqa: BLE001
                _can_resume = False
            _bs_current = int(build_state.get("current", 0) or 0)
            _bs_total = int(build_state.get("total", 0) or 0)
            return build_envelope(
                module="memory", capability_state="needs_action", severity="warning",
                reason_code="memory.vector_build_interrupted",
                reason_text=(
                    f"Vector index is partially built: {_bs_current}/{_bs_total} "
                    f"papers embedded. Resume to embed the remaining "
                    f"{max(_bs_total - _bs_current, 0)} papers."
                ),
                user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
                action_primary=build_action_primary(
                    action_id="embed.build" if not _can_resume else "embed.resume",
                    verb="run",
                    label=(
                        "Resume vector build"
                        if _can_resume
                        else "Rebuild vector index"
                    ),
                ),
                notices=notices, ttl_seconds=TTL_MEMORY,
            )

        # Gate 5d: failed → rebuild
        if bs_status == "failed":
            msg = build_state.get("message", "unknown error")
            # Resume is feasible unless the substrate itself is incompatible
            # (identity change / legacy layout) — either a surviving shadow
            # candidate or in-place incremental works.
            try:
                _can_resume = _resume_feasible(vault)
            except Exception:  # noqa: BLE001
                _can_resume = False
            return build_envelope(
                module="memory", capability_state="needs_action", severity="warning",
                reason_code="memory.vector_build_failed",
                reason_text=(
                    f"Last embedding attempt failed: {msg}. Papers embedded "
                    f"so far remain searchable — resume to continue or retry."
                ),
                user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
                action_primary=build_action_primary(
                    action_id="embed.build" if not _can_resume else "embed.resume",
                    verb="run",
                    label=(
                        "Resume vector build"
                        if _can_resume
                        else "Rebuild vector index"
                    ),
                ),
                notices=notices, ttl_seconds=TTL_MEMORY,
            )

        # Gate 5d: build_state absent (idle / never built / 1.5.15)
        # Check if vec0 already has data (build_state may have been lost)
        from paperforge.memory.db import ensure_vec_extension, get_memory_db_path, open_live_reader

        db_path = get_memory_db_path(vault)
        vec0_has_data = False
        if db_path.exists():
            try:
                with open_live_reader(vault, db_path) as conn:
                    ensure_vec_extension(conn)
                    row = conn.execute("SELECT COUNT(*) AS cnt FROM vec_body_meta LIMIT 1").fetchone()
                    vec0_has_data = bool(row and row["cnt"] > 0)
            except Exception:
                pass

        if vec0_has_data:
            # vec0 has data — build_state was lost, treat as ready
            return build_envelope(
                module="memory", capability_state="ready", severity="ok",
                reason_code="memory.ready",
                reason_text=f"Memory database healthy ({paper_count_db} papers, {paper_count_index} indexed)",
                user_state=USER_STATE_READY, capability_kind=CAPABILITY_OPTIONAL,
                notices=notices, action_primary=None, ttl_seconds=TTL_MEMORY,
            )

        # No vec0 data — vectors were never built
        return build_envelope(
            module="memory", capability_state="needs_action", severity="warning",
            reason_code="memory.index_stale",
            reason_text="Vector index has not been built — rebuild to enable semantic search",
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
            action_primary=build_action_primary(
                action_id="embed.build",
                verb="run", label="Build vector index",
            ),
            notices=notices, ttl_seconds=TTL_MEMORY,
        )

    except Exception:
        return build_envelope(
            module="memory", capability_state="unknown", severity="unknown",
            reason_code="memory.vector_probe_failed",
            reason_text="Vector index health check failed — probe to retry",
            user_state=USER_STATE_DETECTION_FAILED, capability_kind=CAPABILITY_OPTIONAL,
            action_primary=build_action_primary(
                action_id="memory.probe", verb="probe", label="Retry",
            ),
            notices=notices, ttl_seconds=TTL_MEMORY,
        )
