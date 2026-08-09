"""ConfigWriter — atomic paperforge.json writer (v2 vault_config format).

#142 / C0: this is a thin setup facade over the canonical configuration seam.
There is exactly ONE writer primitive in PaperForge (``paperforge.config``);
setup never owns a second writer.
"""

from __future__ import annotations

from pathlib import Path

from paperforge.config import ConfigError, bootstrap_config, set_config
from paperforge.setup import SetupStepResult


class ConfigWriter:
    """Write paperforge.json through the canonical seam (bootstrap + set)."""

    PATH_KEYS = ["system_dir", "resources_dir", "literature_dir", "control_dir", "base_dir", "skill_dir", "command_dir"]

    def __init__(self, vault: Path):
        self.vault = vault
        self.config_path = vault / "paperforge.json"

    def write(self, config: dict, overwrite: bool = False) -> SetupStepResult:
        """Write paperforge.json via the seam: bootstrap explicit defaults for
        a fresh vault, then atomically set each supplied key.  ``overwrite`` is
        accepted for call-site compatibility; the seam's per-key semantics
        apply (canonical values win, unknown fields preserved)."""
        try:
            if not self.config_path.exists():
                bootstrap_config(self.vault)
            for key, value in config.items():
                set_config(self.vault, key, value)
        except ConfigError as exc:
            return SetupStepResult(
                step="config_writer",
                ok=False,
                message=exc.code,
                error=str(dict(exc.details)),
                details=dict(exc.details),
            )
        return SetupStepResult(
            step="config_writer",
            ok=True,
            message=f"paperforge.json written to {self.config_path}",
            details={"path": str(self.config_path), "keys": list(config.keys())},
        )

    def read(self) -> dict | None:
        """Read resolved path-key values through the seam (fail-closed)."""
        from paperforge.config import ConfigError as _CE
        from paperforge.config import load_config

        try:
            snapshot = load_config(self.vault)
        except _CE:
            return None
        return {key: str(cv.value) for key, cv in snapshot.values.items()
                if key in self.PATH_KEYS}

    def exists(self) -> bool:
        """Check if config file exists."""
        return self.config_path.exists()

