"""ConfigWriter — atomic paperforge.json writer."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from paperforge.setup import SetupStepResult


class ConfigWriter:
    """Write paperforge.json atomically using tempfile + os.replace."""

    REQUIRED_KEYS = ["system_dir", "resources_dir", "literature_dir", "control_dir"]

    def __init__(self, vault: Path):
        self.vault = vault
        self.config_path = vault / "paperforge.json"

    def write(self, config: dict) -> SetupStepResult:
        """Write paperforge.json atomically."""
        # Validate required keys
        missing = [k for k in self.REQUIRED_KEYS if k not in config]
        if missing:
            return SetupStepResult(
                step="config_writer",
                ok=False,
                message="Missing required config keys",
                error=f"Missing: {', '.join(missing)}",
                details={"missing_keys": missing},
            )

        try:
            # Write to temp file, then atomic replace
            fd, tmp_path = tempfile.mkstemp(
                suffix=".json",
                prefix="paperforge_",
                dir=str(self.vault),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, str(self.config_path))
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                raise

            return SetupStepResult(
                step="config_writer",
                ok=True,
                message=f"paperforge.json written to {self.config_path}",
                details={"path": str(self.config_path), "keys": list(config.keys())},
            )
        except Exception as e:
            return SetupStepResult(
                step="config_writer",
                ok=False,
                message="Failed to write config",
                error=str(e),
            )

    def read(self) -> dict | None:
        """Read existing config, return None if not exists."""
        if not self.config_path.exists():
            return None
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def exists(self) -> bool:
        """Check if config file exists."""
        return self.config_path.exists()
