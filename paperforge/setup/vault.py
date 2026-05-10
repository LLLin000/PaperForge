"""VaultInitializer -- creates vault directory structure and env config."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from paperforge.setup import SetupStepResult


class VaultInitializer:
    """Create vault directory structure, Zotero junction, and .env file."""

    DEFAULT_DIRS = {
        "system_dir": "99_System",
        "resources_dir": "03_Resources",
        "literature_dir": "Literature",
        # control_dir 已淘汰 (v2.1+ workspace 架构)
    }

    def __init__(self, vault: Path, config: dict):
        self.vault = vault
        self.config = config

    def create_directories(self) -> SetupStepResult:
        """Create all required vault directories."""
        dirs_to_create = [
            self.vault / "paperforge.json",
        ]

        for key in ("system_dir", "resources_dir", "literature_dir"):
            rel = self.config.get(key, self.DEFAULT_DIRS.get(key, ""))
            if rel:
                dirs_to_create.append(self.vault / rel)

        created = []
        existing = []
        for d in dirs_to_create:
            if d.suffix:
                d.parent.mkdir(parents=True, exist_ok=True)
                continue
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
                created.append(str(d.relative_to(self.vault)))
            else:
                existing.append(str(d.relative_to(self.vault)))

        return SetupStepResult(
            step="vault_initializer",
            ok=True,
            message=f"Created {len(created)} director(ies), {len(existing)} already exist",
            details={"created": created, "existing": existing},
        )

    def create_zotero_junction(self, zotero_path: str | None = None) -> SetupStepResult:
        """Create Zotero junction/symlink to vault."""
        system_dir = self.vault / self.config.get("system_dir", self.DEFAULT_DIRS["system_dir"])
        zotero_link = system_dir / "Zotero"

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
        except Exception as e:
            return SetupStepResult(
                step="vault_initializer",
                ok=False,
                message="Failed to create Zotero junction",
                error=str(e),
            )

    def merge_env(self, env_values: dict[str, str]) -> SetupStepResult:
        """Merge values into .env file."""
        env_path = self.vault / ".env"

        existing = {}
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        existing[key.strip()] = val.strip()
            except Exception:
                pass

        updated = dict(existing)
        updated.update(env_values)

        try:
            lines = [f"{k}={v}\n" for k, v in updated.items()]
            env_path.write_text("".join(lines), encoding="utf-8")

            added = [k for k in env_values if k not in existing]
            return SetupStepResult(
                step="vault_initializer",
                ok=True,
                message=f"Created .env with {len(updated)} entries ({len(added)} new)",
                details={
                    "path": str(env_path),
                    "total_keys": len(updated),
                    "new_keys": added,
                },
            )
        except Exception as e:
            return SetupStepResult(
                step="vault_initializer",
                ok=False,
                message="Failed to write .env",
                error=str(e),
            )
