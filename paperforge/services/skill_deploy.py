"""Skill deployment service — deploys the unified paperforge skill to the vault.

Used by both setup wizard (install) and update worker (update).
All deployments are vault-local only.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Skill target dir is caller-chosen (agents know their harness).  Only the
# shared default lives here, from paperforge.config.
from paperforge.config import AGENT_SHARED_SKILL_DIR


def _resolve_source_root() -> Path:
    """Resolve the paperforge package root (where skills/ lives)."""
    import paperforge

    return Path(paperforge.__file__).parent


def deploy_skills(
    vault: Path,
    agent_key: str = "opencode",
    overwrite: bool = False,
    target_dir: str | None = None,
) -> dict:
    """Deploy paperforge skill and AGENTS.md to the vault.

    Args:
        vault: Vault root.
        agent_key: Agent platform key (kept for call-site compatibility;
            no longer used for path routing).
        overwrite: If True, replace an existing differing skill dir (used
            by update).  Without it, an existing identical skill is a no-op
            and an existing differing skill is reported ``already_exists``
            — never silently merged.
        target_dir: Vault-relative skill directory to deploy into; defaults
            to the shared cross-agent dir ``.agents/skills``.  Must stay
            inside the vault (relative, no ``..`` escape, not the vault
            root).

    Returns:
        dict with 'skill_deployed', 'agents_md', 'target_dir',
        'already_exists', 'noop', 'errors'.
    """
    errors: list[str] = []
    target_dir = target_dir or AGENT_SHARED_SKILL_DIR
    target = _validate_target(vault, target_dir)
    if target is None:
        return {
            "skill_deployed": False,
            "agents_md": False,
            "target_dir": target_dir,
            "already_exists": False,
            "noop": False,
            "errors": [f"target dir must stay inside the vault (got {target_dir!r})"],
        }

    # ── Deploy paperforge skill ──
    skill_deployed = False
    already_exists = False
    noop = False
    source_root = _resolve_source_root()
    src_skill = source_root / "skills" / "paperforge"

    if src_skill.exists():
        dst_skill = target / "paperforge"
        if dst_skill.exists():
            src_meta = src_skill / "SKILL.md"
            dst_meta = dst_skill / "SKILL.md"
            identical = (
                src_meta.exists()
                and dst_meta.exists()
                and src_meta.read_bytes() == dst_meta.read_bytes()
            )
            if identical:
                noop = True
                skill_deployed = True
            elif not overwrite:
                already_exists = True
                errors.append(
                    f"existing paperforge skill differs at {dst_skill} — "
                    "rerun with --overwrite to replace it"
                )
            else:
                try:
                    shutil.rmtree(dst_skill)
                except OSError as exc:
                    logger.warning("skill_deploy: failed to remove %s: %s", dst_skill, exc)
        if not (noop or already_exists):
            try:
                dst_skill.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src_skill, dst_skill, dirs_exist_ok=False)
                skill_deployed = True
            except Exception as e:
                errors.append(f"Skill deploy failed: {e}")
    else:
        errors.append("Skills source not found in package")

    # ── Deploy AGENTS.md (only if it does not exist — users customise it) ──
    agents_ok = False
    agents_src = source_root.parent / "AGENTS.md"
    if agents_src.exists():
        try:
            agents_dst = vault / "AGENTS.md"
            if not agents_dst.exists():
                shutil.copy2(agents_src, agents_dst)
            agents_ok = True
        except Exception as e:
            errors.append(f"AGENTS.md deploy failed: {e}")

    return {
        "skill_deployed": skill_deployed,
        "agents_md": agents_ok,
        "target_dir": target_dir,
        "already_exists": already_exists,
        "noop": noop,
        "errors": errors,
    }


def _validate_target(vault: Path, target_dir: str) -> Path | None:
    """Resolve the deploy target inside the vault; None when the path would
    escape the vault (absolute, ``..``, or the vault root itself)."""
    import os as _os

    t = Path(target_dir)
    if t.is_absolute():
        return None
    vault_r = vault.resolve()
    resolved = (vault / target_dir).resolve()
    if resolved == vault_r:
        return None
    if not str(resolved).startswith(str(vault_r) + _os.sep):
        return None
    return resolved
