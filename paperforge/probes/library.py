"""paperforge.probes.library — library capability reader (P1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from paperforge.probes.envelope import (_load_pf_config, build_action_primary, build_envelope, CAPABILITY_REQUIRED, TTL_LIBRARY, USER_STATE_ACTION_REQUIRED, USER_STATE_DETECTION_FAILED, USER_STATE_READY, USER_STATE_SETUP_REQUIRED)


def probe_library(vault: Path, last_operation_exit_code: int | None = None) -> dict[str, Any]:
    """Probe the Library module using canonical sources.

    When last_operation_exit_code is non-zero, the probe reports a sync failure
    envelope after validating config/path, skipping index freshness checks.
    """
    data, err = _load_pf_config(vault)
    if data is None:
        if err == "corrupt":
            return build_envelope(
                module="library", capability_state="unavailable", severity="error",
                reason_code="library.config_corrupt",
                reason_text="paperforge.json is corrupt — library sync cannot proceed",
                user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
                maintenance_eligible=True,
                action_primary=build_action_primary(
                    action_id="library.setup", verb="setup", label="Setup",
                ),
                ttl_seconds=TTL_LIBRARY,
            )
        return build_envelope(
            module="library", capability_state="missing_input", severity="warning",
            reason_code="library.config_missing",
            reason_text="paperforge.json not found — cannot check library configuration",
            user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            action_primary=build_action_primary(
                action_id="library.configure", verb="set_config", label="Set config",
            ),
            ttl_seconds=TTL_LIBRARY,
        )

    # ── zotero_data_dir check ──
    vault_cfg = data.get("vault_config", {}) if isinstance(data.get("vault_config"), dict) else {}
    zotero_dir = vault_cfg.get("zotero_data_dir") or data.get("zotero_data_dir", "")
    zotero_dir = (zotero_dir or "").strip()

    if not zotero_dir:
        return build_envelope(
            module="library", capability_state="missing_input", severity="warning",
            reason_code="library.zotero_missing", reason_text="Zotero data directory not configured",
            user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            action_primary=build_action_primary(
                action_id="library.configure", verb="set_config", label="Configure Zotero",

            ),
            ttl_seconds=TTL_LIBRARY,
        )

    zotero_path = Path(zotero_dir).expanduser()
    if not zotero_path.is_absolute():
        zotero_path = (vault / zotero_path).resolve()
    if not zotero_path.exists():
        return build_envelope(
            module="library", capability_state="missing_input", severity="error",
            reason_code="library.zotero_not_found",
            reason_text=f"Zotero data directory not found: {zotero_dir}",
            user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            maintenance_eligible=True,
            action_primary=build_action_primary(
                action_id="library.configure", verb="set_config", label="Configure Zotero",

            ),
            ttl_seconds=TTL_LIBRARY,
        )

    # ── Sync failure probe: backend-owned envelope after failed manual sync ──
    if last_operation_exit_code and last_operation_exit_code != 0:
        return build_envelope(
            module="library", capability_state="needs_action", severity="error",
            reason_code="library.sync_failed",
            reason_text=f"Library sync failed (exit code {last_operation_exit_code}) — re-run or check logs",
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            maintenance_eligible=True,
            action_primary=build_action_primary(
                action_id="library.sync", verb="sync", label="Sync library",
            ),
            ttl_seconds=TTL_LIBRARY,
        )

    # ── Explicit Zotero scope authorization check when SQLite DB is present ──
    zotero_mode = str(
        vault_cfg.get("zotero_source_mode") or data.get("zotero_source_mode") or "sqlite"
    ).strip().lower()
    if zotero_mode == "sqlite" and (zotero_path / "zotero.sqlite").is_file():
        import json as _json

        raw_sel = vault_cfg.get("zotero_selected_collections")
        if raw_sel is None:
            raw_sel = data.get("zotero_selected_collections")
        has_scope = False
        if isinstance(raw_sel, list):
            has_scope = any(str(x).strip() for x in raw_sel)
        elif isinstance(raw_sel, str):
            raw_str = raw_sel.strip()
            if raw_str.startswith("["):
                try:
                    parsed = _json.loads(raw_str)
                    has_scope = isinstance(parsed, list) and any(str(x).strip() for x in parsed)
                except ValueError:
                    has_scope = False
            elif raw_str and raw_str.lower() not in ("null", "none"):
                has_scope = any(s.strip() for s in raw_str.split(","))
        if not has_scope:
            return build_envelope(
                module="library", capability_state="missing_input", severity="warning",
                reason_code="library.zotero_scope_required",
                reason_text="Zotero directory is connected, but no collection scope or full-library authorization is selected",
                user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
                action_primary=build_action_primary(
                    action_id="library.configure", verb="set_config", label="Select Zotero folders",
                ),
                ttl_seconds=TTL_LIBRARY,
            )

    # ── Canonical index check via paperforge_paths ──
    from paperforge.config import paperforge_paths
    from paperforge.memory.db import get_memory_db_path
    paths = paperforge_paths(vault)
    index_path = paths.get("index")  # canonical formal-library.json

    if index_path is None or not index_path.exists():
        exports_dir = paths.get("exports")
        if exports_dir is not None and exports_dir.exists():
            json_exports = sorted(exports_dir.glob("*.json"))
            if json_exports:
                from paperforge.adapters.bbt import detect_bbt_export_problem

                for exp in json_exports:
                    problem = detect_bbt_export_problem(exp)
                    if problem:
                        return build_envelope(
                            module="library", capability_state="missing_input", severity="error",
                            reason_code="library.bbt_invalid_format",
                            reason_text=problem,
                            user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
                            action_primary=build_action_primary(
                                action_id="library.sync", verb="sync", label="Sync library",
                            ),
                            ttl_seconds=TTL_LIBRARY,
                        )
            else:
                bib_exports = sorted(exports_dir.glob("*.bib"))
                if bib_exports:
                    return build_envelope(
                        module="library", capability_state="missing_input", severity="error",
                        reason_code="library.bbt_invalid_format",
                        reason_text=(
                            f"Found {bib_exports[0].name} (.bib), but PaperForge requires "
                            "'Better BibTeX JSON' (.json). Re-export with Keep updated checked."
                        ),
                        user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
                        action_primary=build_action_primary(
                            action_id="library.sync", verb="sync", label="Sync library",
                        ),
                        ttl_seconds=TTL_LIBRARY,
                    )
        return build_envelope(
            module="library", capability_state="needs_action", severity="warning",
            reason_code="library.index_missing", reason_text="Canonical index has not been built — run sync",
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            action_primary=build_action_primary(
                action_id="library.sync", verb="sync", label="Sync library",
            ),
            ttl_seconds=TTL_LIBRARY,
        )

    # ── Index freshness: canonical export hash (Issue #78) ──
    notices: list[dict[str, Any]] = []
    try:
        from paperforge.worker import asset_index
        envelope = asset_index.read_index(vault)
        if envelope is not None and isinstance(envelope, dict):
            stored_hash = envelope.get("export_hash", "")
            current_hash = asset_index.compute_export_hash(paths)
            paper_count = envelope.get("paper_count", 0)

            if not stored_hash or stored_hash != current_hash:
                env = build_envelope(
                    module="library", capability_state="needs_action", severity="warning",
                    reason_code="library.index_stale",
                    reason_text=f"Library index is stale ({paper_count} papers — export files changed since last sync)",
                    user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
                    action_primary=build_action_primary(
                        action_id="library.sync", verb="sync", label="Sync library",
                    ),
                    ttl_seconds=TTL_LIBRARY,
                )
                env["details"] = {"paper_count": paper_count}
                return env

            # Cross-validate DB canonical_index_hash
            try:
                items = envelope.get("items", [])
                from paperforge.memory.builder import compute_hash
                index_hash = compute_hash(items)
                db_path = get_memory_db_path(vault)
                if db_path.exists():
                    from paperforge.memory.db import open_live_reader

                    with open_live_reader(vault, db_path) as conn:
                        row = conn.execute("SELECT value FROM meta WHERE key = 'canonical_index_hash'").fetchone()
                        db_stored = row[0] if row else ""
                        if db_stored and db_stored != index_hash:
                            notices.append({"level": "warning", "message": "DB canonical_index_hash is out of sync with index"})
            except Exception:
                pass
            # Surface diagnostic notice if a .paperforge v2 vault lost its manifest
            try:
                if Path(paths["system"]).name == ".paperforge":
                    from paperforge.services.vault_engine import CURRENT_LAYOUT_VERSION, read_vault_manifest

                    mf = read_vault_manifest(vault)
                    if mf is None or int(mf.get("layout_version") or 0) < CURRENT_LAYOUT_VERSION:
                        notices.append(
                            {
                                "level": "warning",
                                "code": "vault.manifest_missing",
                                "message": (
                                    ".paperforge/vault-manifest.json is missing or outdated; "
                                    "re-run setup or vault upgrade to repair layout metadata"
                                ),
                            }
                        )
            except Exception:
                pass
            # Export hash valid and index healthy → ready
            env = build_envelope(
                module="library", capability_state="ready", severity="ok",
                reason_code="library.ready",
                reason_text=f"Library synced and index is fresh ({paper_count} papers)",
                user_state=USER_STATE_READY, capability_kind=CAPABILITY_REQUIRED,
                notices=notices, action_primary=None, ttl_seconds=TTL_LIBRARY,
            )
            env["details"] = {"paper_count": paper_count}
            return env
        elif envelope is not None:
            # Legacy list format
            return build_envelope(
                module="library", capability_state="needs_action", severity="warning",
                reason_code="library.index_legacy",
                reason_text="Canonical index is in legacy format — run sync to migrate",
                user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
                maintenance_eligible=True,
                action_primary=build_action_primary(
                    action_id="library.sync", verb="sync", label="Sync library",
                ),
                ttl_seconds=TTL_LIBRARY,
            )
        else:
            return build_envelope(
                module="library", capability_state="needs_action", severity="warning",
                reason_code="library.index_missing", reason_text="Canonical index is empty — run sync",
                user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
                action_primary=build_action_primary(
                    action_id="library.sync", verb="sync", label="Sync library",
                ),
                ttl_seconds=TTL_LIBRARY,
            )
    except Exception:
        # Validation exception → never fall through to ready; report unknown
        return build_envelope(
            module="library", capability_state="unknown", severity="unknown",
            reason_code="library.index_validation_failed",
            reason_text="Library index validation failed — probe to retry",
            user_state=USER_STATE_DETECTION_FAILED, capability_kind=CAPABILITY_REQUIRED,
            action_primary=build_action_primary(
                action_id="library.probe", verb="probe", label="Retry",
            ),
            ttl_seconds=TTL_LIBRARY,
        )
