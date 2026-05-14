from __future__ import annotations

from pathlib import Path


def get_runtime_health(vault: Path) -> dict:
    """Compute full runtime health for a vault. Returns layers + summary + capabilities."""
    layers = {
        "bootstrap": _check_bootstrap(vault),
        "read": _check_read(vault),
        "write": _check_write(vault),
        "index": _check_index(vault),
        "vector": _check_vector(vault),
    }
    summary = _derive_summary(layers)
    capabilities = _derive_capabilities(layers)
    return {
        "summary": summary,
        "layers": layers,
        "capabilities": capabilities,
    }


def _layer(status: str, evidence: list, next_action: str = "", repair_command: str = "") -> dict:
    return {
        "status": status,
        "evidence": evidence,
        "next_action": next_action,
        "repair_command": repair_command,
    }


def _check_bootstrap(vault: Path) -> dict:
    pf_json = vault / "paperforge.json"
    if not pf_json.exists():
        return _layer("blocked", [f"paperforge.json not found at {vault}"],
                      "Run paperforge setup to initialize vault",
                      "paperforge setup --headless")
    try:
        import json
        cfg = json.loads(pf_json.read_text(encoding="utf-8"))
    except Exception as e:
        return _layer("blocked", [f"Cannot read paperforge.json: {e}"],
                      "Fix paperforge.json syntax",
                      "paperforge doctor")
    system_dir = cfg.get("vault_config", {}).get("system_dir") or cfg.get("system_dir", "System")
    pf_root = vault / system_dir / "PaperForge"
    if not pf_root.exists():
        return _layer("degraded", [f"PaperForge directory not found at {pf_root}"],
                      "Run setup to create directory structure",
                      "paperforge doctor")
    return _layer("ok", [f"paperforge.json ok at {pf_json}"])


def _check_read(vault: Path) -> dict:
    from paperforge.memory.db import get_memory_db_path
    from paperforge.config import paperforge_paths

    paths = paperforge_paths(vault)
    index_path = paths.get("index")
    if index_path and not Path(index_path).exists():
        return _layer("degraded", ["Canonical index not found"],
                      "Run paperforge sync --rebuild-index",
                      "paperforge sync --rebuild-index")

    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return _layer("degraded", ["Memory DB not found, can be rebuilt"],
                      "Run paperforge memory build",
                      "paperforge memory build")

    logs_dir = paths.get("paperforge", vault / "System" / "PaperForge") / "logs"
    if not logs_dir.exists():
        return _layer("degraded", ["JSONL logs directory missing"],
                      "Create logs directory or run sync",
                      "mkdir -p \"$logs_dir\"")

    return _layer("ok", ["Canonical index found", "Memory DB exists", "JSONL logs dir found"])


def _check_write(vault: Path) -> dict:
    from paperforge.config import paperforge_paths
    paths = paperforge_paths(vault)
    pf_root = paths.get("paperforge", vault / "System" / "PaperForge")
    logs_dir = pf_root / "logs"
    evidence = []
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        test_file = logs_dir / ".health-check"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        evidence.append("JSONL logs dir writable")
    except Exception as e:
        return _layer("blocked", [f"JSONL logs dir not writable: {e}"],
                      "Check filesystem permissions", "")
    return _layer("ok", evidence)


def _check_index(vault: Path) -> dict:
    from paperforge.memory.db import get_connection, get_memory_db_path
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return _layer("blocked", ["Memory DB not found"],
                      "Run paperforge memory build",
                      "paperforge memory build")
    try:
        conn = get_connection(db_path, read_only=True)
        version = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        conn.close()
        if version:
            return _layer("ok", [f"Schema version: {version['value']}"])
        return _layer("degraded", ["Schema version unknown"],
                      "Rebuild memory DB", "paperforge memory build --force")
    except Exception as e:
        return _layer("blocked", [f"DB query failed: {e}"],
                      "Rebuild memory DB",
                      "paperforge memory build --force")


def _check_vector(vault: Path) -> dict:
    from paperforge.memory.vector_db import get_vector_db_path, read_vector_build_state

    settings_path = vault / ".obsidian" / "plugins" / "paperforge" / "data.json"
    vector_enabled = False
    if settings_path.exists():
        try:
            import json
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            vector_enabled = bool(data.get("features", {}).get("vector_db", False))
        except Exception:
            pass

    if not vector_enabled:
        return _layer("ok", ["Vector DB disabled by user"])

    build_state = read_vector_build_state(vault)
    job_status = build_state.get("status", "idle")
    if job_status == "running":
        return _layer("degraded", ["Vector build in progress"],
                      "Wait for build to complete",
                      "paperforge embed status --json")
    if job_status == "failed":
        return _layer("degraded", [f"Last build failed: {build_state.get('message', '')}"],
                      "Check error and rebuild",
                      "paperforge embed build --resume")

    db_path = get_vector_db_path(vault)
    if not db_path.exists():
        return _layer("degraded", ["Vector DB not built yet"],
                      "Run embed build",
                      "paperforge embed build --resume")

    return _layer("ok", ["Vector DB exists"])


def _derive_summary(layers: dict) -> dict:
    bootstrap_s = layers["bootstrap"]["status"]
    read_s = layers["read"]["status"]
    write_s = layers["write"]["status"]
    index_s = layers["index"]["status"]
    vector_s = layers["vector"]["status"]

    blocked = False
    degraded = False
    reasons = []

    if bootstrap_s == "blocked":
        blocked = True
        reasons.append("Bootstrap blocked")
    if read_s == "blocked" and write_s == "blocked":
        blocked = True
        reasons.append("Read and write both blocked")
    if read_s in ("degraded", "blocked"):
        degraded = True
        reasons.append("Read layer degraded")
    if write_s in ("degraded", "blocked"):
        degraded = True
        reasons.append("Write layer degraded")
    if index_s in ("degraded", "blocked"):
        degraded = True
        reasons.append("Index layer degraded")
    if vector_s in ("degraded", "blocked"):
        degraded = True
        if vector_s == "degraded":
            reasons.append("Vector build degraded")
        else:
            reasons.append("Vector DB blocked")

    if blocked:
        status = "blocked"
    elif degraded:
        status = "degraded"
    else:
        status = "ok"
        reasons.append("All systems operational")

    return {
        "status": status,
        "reason": "; ".join(reasons),
        "safe_read": read_s == "ok",
        "safe_write": write_s == "ok",
        "safe_build": index_s == "ok",
        "safe_vector": vector_s == "ok",
    }


def _derive_capabilities(layers: dict) -> dict:
    read_ok = layers["read"]["status"] == "ok"
    write_ok = layers["write"]["status"] == "ok"
    vector_ok = layers["vector"]["status"] == "ok"
    return {
        "paper_context": read_ok,
        "reading_log_write": write_ok,
        "project_log_write": write_ok,
        "fts_search": read_ok,
        "vector_retrieve": vector_ok,
    }
