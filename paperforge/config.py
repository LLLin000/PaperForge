"""PaperForge — shared configuration and path resolver.

Configuration precedence (D-Configuration Hierarchy):
  1. Explicit overrides (function parameter)
  2. Process environment variables (PAPERFORGE_*)
  3. paperforge.json nested vault_config block
  4. paperforge.json top-level keys (legacy backward-compat)
  5. Built-in defaults

All path construction uses pathlib.Path. No OCR secrets are loaded here.
No global os.environ mutation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# .env loader
# ---------------------------------------------------------------------------


def load_simple_env(env_path: Path) -> None:
    """Load key=value pairs from a .env file into os.environ (no overwrite)."""
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = value


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict[str, str] = {
    "system_dir": "99_System",
    "resources_dir": "03_Resources",
    "literature_dir": "Literature",
    "control_dir": "LiteratureControl",
    "base_dir": "05_Bases",
    "skill_dir": ".opencode/skills",
    "command_dir": ".opencode/command",
}

# Environment variable name map — maps config key to PAPERFORGE_* env var
ENV_KEYS: dict[str, str] = {
    "vault": "PAPERFORGE_VAULT",
    "system_dir": "PAPERFORGE_SYSTEM_DIR",
    "resources_dir": "PAPERFORGE_RESOURCES_DIR",
    "literature_dir": "paperforgeRATURE_DIR",
    "control_dir": "PAPERFORGE_CONTROL_DIR",
    "base_dir": "PAPERFORGE_BASE_DIR",
    "skill_dir": "PAPERFORGE_SKILL_DIR",
    "command_dir": "PAPERFORGE_COMMAND_DIR",
}

# All config keys accepted by load_vault_config
CONFIG_KEYS: set[str] = set(DEFAULT_CONFIG.keys())


# ---------------------------------------------------------------------------
# JSON reader
# ---------------------------------------------------------------------------


def read_paperforge_json(vault: Path) -> dict[str, Any]:
    """Read and parse paperforge.json, returning raw key-value pairs.

    Supports both legacy top-level keys and nested ``vault_config`` block.

    Returns an empty dict if the file does not exist or is invalid JSON.
    """
    path = vault / "paperforge.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


# ---------------------------------------------------------------------------
# Vault resolution
# ---------------------------------------------------------------------------


def resolve_vault(
    cli_vault: Path | None = None,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> Path:
    """Resolve the vault path using the locked precedence order.

    Returns:
        Path to the vault root directory.

    Precedence:
      1. Explicit ``cli_vault`` argument
      2. ``PAPERFORGE_VAULT`` environment variable
      3. Current directory or nearest parent containing ``paperforge.json``
      4. ``cwd`` argument as final fallback
    """
    # 1. Explicit CLI vault
    if cli_vault is not None:
        return Path(cli_vault).expanduser().resolve()

    env = env if env is not None else os.environ

    # 2. Environment variable
    if ENV_KEYS["vault"] in env:
        return Path(env[ENV_KEYS["vault"]]).expanduser().resolve()

    # 3. Scan cwd upward for paperforge.json
    if cwd is not None:
        search: Path | None = Path(cwd).expanduser().resolve()
    else:
        search = Path.cwd()

    while search is not None and search != search.parent:
        if (search / "paperforge.json").exists():
            return search
        search = search.parent

    # 4. Fallback to cwd
    return Path(cwd).expanduser().resolve() if cwd is not None else Path.cwd()


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def load_vault_config(
    vault: Path,
    env: dict[str, str] | None = None,
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    """Load the full PaperForge configuration for a vault.

    Merges configuration sources in locked precedence order:
      1. Built-in defaults
      2. paperforge.json nested ``vault_config`` block
      3. paperforge.json top-level keys (legacy backward-compat)
      4. Process environment variables
      5. Explicit ``overrides`` dict

    Args:
        vault: Path to the vault root.
        env: Optional dict of environment variables. If None, uses os.environ.
        overrides: Optional dict of explicit overrides. Highest precedence.

    Returns:
        Dict with keys: system_dir, resources_dir, literature_dir, control_dir,
        base_dir, skill_dir, command_dir.
    """
    env = env if env is not None else os.environ

    # Start with defaults
    config: dict[str, str] = dict(DEFAULT_CONFIG)

    # Read paperforge.json
    pf_data = read_paperforge_json(vault)

    # 2. Merge nested vault_config block
    nested = pf_data.get("vault_config", {})
    if isinstance(nested, dict):
        for key in CONFIG_KEYS:
            if key in nested and nested[key]:
                config[key] = nested[key]

    # 3. Merge top-level legacy keys (override nested for backward compat)
    for key in CONFIG_KEYS:
        if key in pf_data and pf_data[key]:
            config[key] = pf_data[key]

    # 4. Merge environment variables
    for config_key, env_var in ENV_KEYS.items():
        if config_key == "vault":
            continue  # vault is handled separately in resolve_vault
        if env_var in env and env[env_var]:
            config[config_key] = env[env_var]

    # 5. Merge explicit overrides (highest precedence)
    if overrides:
        for key in CONFIG_KEYS:
            if key in overrides and overrides[key]:
                config[key] = overrides[key]

    return config


# ---------------------------------------------------------------------------
# Path construction
# ---------------------------------------------------------------------------


def paperforge_paths(
    vault: Path,
    cfg: dict[str, str] | None = None,
) -> dict[str, Path]:
    """Build the complete PaperForge path inventory for a vault.

    Returns absolute Path objects for every user-facing and worker-facing
    location used by PaperForge.

    Args:
        vault: Path to the vault root.
        cfg: Optional config dict from load_vault_config. If None, loads it.

    Returns:
        Dict with keys:
          - vault: vault root
          - system: <vault>/<system_dir>
          - paperforge: <vault>/<system_dir>/PaperForge
          - exports: <paperforge>/exports  (Better BibTeX JSON exports)
          - ocr: <paperforge>/ocr
          - resources: <vault>/<resources_dir>
          - literature: <resources>/<literature_dir>
          - control: <resources>/<control_dir>
          - library_records: <control>/library-records
          - bases: <vault>/<base_dir>
          - worker_script: pipeline/worker/scripts/literature_pipeline.py
          - skill_dir: <vault>/<skill_dir>
          - ld_deep_script: <skill_dir>/literature-qa/scripts/ld_deep.py
    """
    if cfg is None:
        cfg = load_vault_config(vault)

    vault = Path(vault).expanduser().resolve()
    system_dir = cfg["system_dir"]
    resources_dir = cfg["resources_dir"]
    literature_dir = cfg["literature_dir"]
    control_dir = cfg["control_dir"]
    base_dir = cfg["base_dir"]
    skill_dir = cfg["skill_dir"]

    system = vault / system_dir
    paperforge = system / "PaperForge"
    resources = vault / resources_dir
    literature = resources / literature_dir
    control = resources / control_dir
    bases = vault / base_dir
    skill_path = vault / skill_dir

    zotero_dir_val = os.environ.get("ZOTERO_DATA_DIR", "").strip()
    if not zotero_dir_val:
        zotero_dir_val = str(system / "Zotero")

    # worker_script: paperforge worker package (pipeline/ removed in v1.3)
    worker_script = Path(__file__).parent / "worker" / "__init__.py"
    # ld_deep_script: look relative to skill_dir first, then repo paperforge/skills for dev
    ld_deep_script = skill_path / "literature-qa" / "scripts" / "ld_deep.py"
    if not ld_deep_script.exists():
        repo_skill = Path(__file__).parent / "skills" / "literature-qa" / "scripts" / "ld_deep.py"
        if repo_skill.exists():
            ld_deep_script = repo_skill
        else:
            # Backward compat: old skills/ location during transition
            old_repo_skill = Path(__file__).parent.parent / "skills" / "literature-qa" / "scripts" / "ld_deep.py"
            if old_repo_skill.exists():
                ld_deep_script = old_repo_skill

    return {
        "vault": vault,
        "system": system,
        "paperforge": paperforge,
        "exports": paperforge / "exports",
        "ocr": paperforge / "ocr",
        "zotero_dir": Path(zotero_dir_val),
        "resources": resources,
        "literature": literature,
        "control": control,
        "library_records": control / "library-records",
        "bases": bases,
        "worker_script": worker_script,
        "skill_dir": skill_path,
        "ld_deep_script": ld_deep_script,
    }


def paths_as_strings(paths: dict[str, Path]) -> dict[str, str]:
    """Convert a paperforge_paths dict to JSON-serializable dict[str, str].

    All Path values are converted to their string representation.
    Key names are preserved exactly.

    Args:
        paths: Output of paperforge_paths().

    Returns:
        dict mapping path names to string paths.
    """
    return {name: str(path) for name, path in paths.items()}
