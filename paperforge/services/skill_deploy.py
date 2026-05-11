"""Skill deployment service — single copytree for all platforms.

Used by both setup wizard (install) and update worker (update).
All deployments are vault-local only.
"""

from __future__ import annotations

import shutil
from pathlib import Path

# ── Agent platform → vault-local skill directory ──
AGENT_SKILL_DIRS: dict[str, str] = {
    "opencode":       ".opencode/skills",
    "claude":         ".claude/skills",
    "codex":          ".codex/skills",
    "cursor":         ".cursor/skills",
    "windsurf":       ".windsurf/skills",
    "github_copilot": ".github/skills",
    "cline":          ".clinerules",
    "augment":        ".augment/skills",
    "trae":           ".trae/skills",
}


def _resolve_source_root() -> Path:
    """Resolve the paperforge package root (where skills/ lives)."""
    import paperforge

    return Path(paperforge.__file__).parent


def deploy_skills(
    vault: Path,
    agent_key: str = "opencode",
    overwrite: bool = False,
) -> dict:
    """Deploy literature-qa skill and AGENTS.md to the vault.

    Args:
        vault: Obsidian vault root.
        agent_key: Agent platform key (opencode, claude, etc.).
        overwrite: If True, overwrite existing files (used by update).

    Returns:
        dict with 'skill_deployed', 'agents_md', 'errors' keys.
    """
    errors: list[str] = []

    # ── Deploy literature-qa skill ──
    skill_deployed = False
    source_root = _resolve_source_root()
    src_skill = source_root / "skills" / "literature-qa"

    if src_skill.exists():
        skill_dir_name = AGENT_SKILL_DIRS.get(agent_key)
        if skill_dir_name:
            dst_skill = vault / skill_dir_name / "literature-qa"
            try:
                if overwrite and dst_skill.exists():
                    shutil.rmtree(dst_skill, ignore_errors=True)
                dst_skill.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src_skill, dst_skill, dirs_exist_ok=True)
                skill_deployed = True
            except Exception as e:
                errors.append(f"Skill deploy failed: {e}")
        else:
            errors.append(f"Unknown agent: {agent_key}")
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
        "errors": errors,
    }
