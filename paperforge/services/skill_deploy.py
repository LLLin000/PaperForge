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
        overwrite: If True, overwrite existing files (used by update).
        target_dir: Vault-relative skill directory to deploy into; defaults
            to the shared cross-agent dir ``.agents/skills``.  Agents choose
            their own target (e.g. ``.omp/skills``) and pass it explicitly —
            PaperForge does not route per platform anymore.

    Returns:
        dict with 'skill_deployed', 'agents_md', 'target_dir', 'errors'.
    """
    errors: list[str] = []
    target_dir = target_dir or AGENT_SHARED_SKILL_DIR

    # ── Deploy paperforge skill ──
    skill_deployed = False
    source_root = _resolve_source_root()
    src_skill = source_root / "skills" / "paperforge"

    if src_skill.exists():
        dst_skill = vault / target_dir / "paperforge"
        try:
            if overwrite and dst_skill.exists():
                try:
                    shutil.rmtree(dst_skill)
                except OSError as exc:
                    logger.warning("skill_deploy: failed to remove %s: %s", dst_skill, exc)
            dst_skill.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src_skill, dst_skill, dirs_exist_ok=True)
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
        "errors": errors,
    }
