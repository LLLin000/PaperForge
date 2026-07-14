"""ConfigWriter — atomic paperforge.json writer (v2 vault_config format).

Writes ``schema_version`` and a nested ``vault_config`` block.  Reads are
backward-compatible — ``read()`` returns the flat dict (top-level keys for v1,
or ``vault_config`` entries for v2), so existing consumers that call ``read()``
keep working without changes.

On rerun, ``write()`` merges with the existing paperforge.json: it reads the
current content, preserves non-overlapping keys, and writes only the merged
result.  This makes reruns idempotent.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from paperforge.setup import SetupStepResult


class ConfigWriter:
    """Write paperforge.json atomically using tempfile + os.replace.

    Output is v2 canonical format:

    .. code:: json

        {
            "schema_version": "2",
            "vault_config": {
                "system_dir": "...",
                "resources_dir": "...",
                "literature_dir": "...",
                "base_dir": "..."
            }
        }
    """

    PATH_KEYS = ["system_dir", "resources_dir", "literature_dir", "control_dir", "base_dir", "skill_dir", "command_dir"]

    def __init__(self, vault: Path):
        self.vault = vault
        self.config_path = vault / "paperforge.json"

    def write(self, config: dict, overwrite: bool = False) -> SetupStepResult:
        """Write paperforge.json atomically in v2 canonical format.

        Args:
            config: Flat dict of path keys (system_dir, resources_dir, etc.).
            overwrite: If True, replace the entire vault_config with the
                       supplied keys.  If False (default), merge with any
                       existing vault_config — new keys win, missing keys
                       are preserved.
        """
        try:
            # Read existing (if any) for merge
            existing: dict = {}
            file_exists = self.config_path.exists()
            if file_exists and not overwrite:
                try:
                    existing = json.loads(
                        self.config_path.read_text(encoding="utf-8")
                    )
                except (json.JSONDecodeError, OSError):
                    existing = {}

            # Validate required keys only on first write (fresh vault)
            if not file_exists:
                missing = [k for k in self.PATH_KEYS[:3] if k not in config]
                if missing:
                    return SetupStepResult(
                        step="config_writer",
                        ok=False,
                        message="Missing required config keys",
                        error=f"Missing: {', '.join(missing)}",
                        details={"missing_keys": missing},
                    )

            # Build output in v2 canonical format
            output: dict = {}

            # Preserve non-path top-level keys from existing config
            if isinstance(existing, dict):
                for k, v in existing.items():
                    if k not in ("vault_config", "schema_version") and not (
                        k in self.PATH_KEYS
                    ):
                        output[k] = v

            # Always write schema_version as 2 (never preserve v1)
            output["schema_version"] = "2"

            # Build vault_config: start from existing, overlay new
            vault_config: dict = {}
            if isinstance(existing, dict) and isinstance(
                existing.get("vault_config"), dict
            ):
                vault_config = dict(existing["vault_config"])

            # Overlay with new config keys
            for k in self.PATH_KEYS:
                if k in config:
                    vault_config[k] = config[k]

            output["vault_config"] = vault_config

            # Write atomically
            fd, tmp_path = tempfile.mkstemp(
                suffix=".json",
                prefix="paperforge_",
                dir=str(self.vault),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, str(self.config_path))
            except Exception:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                raise

            return SetupStepResult(
                step="config_writer",
                ok=True,
                message=f"paperforge.json written to {self.config_path}",
                details={
                    "path": str(self.config_path),
                    "keys": list(vault_config.keys()),
                },
            )
        except Exception as e:
            return SetupStepResult(
                step="config_writer",
                ok=False,
                message="Failed to write config",
                error=str(e),
            )

    def read(self) -> dict | None:
        """Read config, returning flat keys for backward compat.

        For v2 files this extracts ``vault_config`` entries to top level.
        Returns None if the file does not exist.
        """
        if not self.config_path.exists():
            return None
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        if not isinstance(data, dict):
            return None

        # v2 format: extract vault_config to flat keys
        vc = data.get("vault_config", {})
        if isinstance(vc, dict) and vc:
            return dict(vc)

        # v1 (legacy) format: return as-is, filtering to path keys
        return {k: data[k] for k in self.PATH_KEYS if k in data}

    def exists(self) -> bool:
        """Check if config file exists."""
        return self.config_path.exists()
