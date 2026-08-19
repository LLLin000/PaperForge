"""VaultInitializer -- creates vault directory structure and Zotero junction.

Layout authority: ALL paths come from ``paperforge.config.resolve_paths``
(the single resolver).  This module holds NO path defaults and never
constructs paths from raw config keys — the resolved layout is the only
input.  ``paperforge.json`` is written by ConfigWriter, never here.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from paperforge.setup import SetupStepResult


class VaultInitializer:
    """Create vault directory structure and Zotero junction from a resolved
    layout (``resolve_paths`` output)."""

    def __init__(self, vault: Path, layout: dict):
        self.vault = Path(vault).resolve()
        self.layout = layout

    def create_directories(self) -> SetupStepResult:
        """Create exactly the resolved layout directories: paperforge root,
        resources, literature (nested under resources), control (nested
        under resources), and bases.  No file writes — config owns the
        config file."""
        dirs = [
            self.layout["paperforge"],
            self.layout["resources"],
            self.layout["literature"],
            self.layout["control"],
            self.layout["bases"],
        ]
        created = []
        existing = []
        for d in dirs:
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
                try:
                    created.append(str(d.relative_to(self.vault)))
                except ValueError:
                    created.append(str(d))
            else:
                try:
                    existing.append(str(d.relative_to(self.vault)))
                except ValueError:
                    existing.append(str(d))

        return SetupStepResult(
            step="vault_initializer",
            ok=True,
            message=f"Created {len(created)} director(ies), {len(existing)} already exist",
            details={"created": created, "existing": existing},
        )

    def create_zotero_junction(self, zotero_path: str | None = None) -> SetupStepResult:
        """Create Zotero junction/symlink to vault at the resolved system
        dir's Zotero link point."""
        system = Path(self.layout["system"])
        zotero_link = system / "Zotero"

        if zotero_link.exists() or zotero_link.is_symlink():
            return SetupStepResult(
                step="vault_initializer",
                ok=True,
                message=f"Zotero link already exists at {zotero_link}",
                details={"path": str(zotero_link)},
            )

        if not zotero_path:
            return SetupStepResult(
                step="vault_initializer",
                ok=True,
                message="Zotero path not provided -- skipping junction creation",
                details={"skipped": True},
            )

        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(zotero_link), zotero_path],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                )
                if result.returncode != 0:
                    return SetupStepResult(
                        step="vault_initializer",
                        ok=False,
                        message="Failed to create Zotero junction",
                        error=result.stderr.strip() or result.stdout.strip(),
                    )
            else:
                zotero_link.symlink_to(zotero_path, target_is_directory=True)

            return SetupStepResult(
                step="vault_initializer",
                ok=True,
                message=f"Zotero junction created: {zotero_link} -> {zotero_path}",
                details={"source": str(zotero_link), "target": zotero_path},
            )
        except OSError as exc:
            return SetupStepResult(
                step="vault_initializer",
                ok=False,
                message="Failed to create Zotero junction",
                error=str(exc),
            )

    def merge_env(self, env_values: dict[str, str]) -> SetupStepResult:
        """Merge values into .env file."""
        env_path = self.vault / ".env"
        try:
            existing_text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
        except OSError as exc:
            return SetupStepResult(
                step="vault_initializer",
                ok=False,
                message="Failed to read .env",
                error=str(exc),
            )
        lines = [line for line in existing_text.splitlines() if line.strip()]
        existing_keys = {line.split("=", 1)[0] for line in lines if "=" in line}
        for key, value in env_values.items():
            if key in existing_keys:
                lines = [key + "=" + value if line.startswith(key + "=") else line for line in lines]
            else:
                lines.append(f"{key}={value}")
        try:
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            return SetupStepResult(
                step="vault_initializer",
                ok=False,
                message="Failed to write .env",
                error=str(exc),
            )
        return SetupStepResult(
            step="vault_initializer",
            ok=True,
            message=f".env updated at {env_path}",
            details={"path": str(env_path), "keys": list(env_values.keys())},
        )
