"""Skill deployment service — single source of truth for agent skill installation and updates.

Used by both setup wizard (install) and update worker (update).
All deployments are vault-local only.
"""

from __future__ import annotations

import shutil
from pathlib import Path

# ── Agent Platform Configurations ──
# Canonical source of truth. setup_wizard.py imports from here.

AGENT_CONFIGS = {
    "opencode": {
        "name": "OpenCode",
        "skill_dir": ".opencode/skills",
        "command_dir": ".opencode/command",
        "format": "flat_command",
        "prefix": "/",
        "config_file": None,
    },
    "claude": {
        "name": "Claude Code",
        "skill_dir": ".claude/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": ".claude/skills.json",
    },
    "codex": {
        "name": "Codex",
        "skill_dir": ".codex/skills",
        "format": "skill_directory",
        "prefix": "$",
        "config_file": None,
    },
    "cursor": {
        "name": "Cursor",
        "skill_dir": ".cursor/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": ".cursor/settings.json",
    },
    "windsurf": {
        "name": "Windsurf",
        "skill_dir": ".windsurf/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": None,
    },
    "github_copilot": {
        "name": "GitHub Copilot",
        "skill_dir": ".github/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": ".github/copilot-instructions.md",
    },
    "cline": {
        "name": "Cline",
        "skill_dir": ".clinerules",
        "format": "rules_file",
        "prefix": "/",
        "config_file": ".clinerules",
    },
    "augment": {
        "name": "Augment",
        "skill_dir": ".augment/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": None,
    },
    "trae": {
        "name": "Trae",
        "skill_dir": ".trae/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": None,
    },
}


def _resolve_source_root() -> Path:
    """Resolve the paperforge package root (where skills/ lives)."""
    import paperforge
    return Path(paperforge.__file__).parent


def _substitute_vars(text: str, system_dir: str, resources_dir: str, literature_dir: str, base_dir: str, skill_dir: str, prefix: str = "/") -> str:
    for old, new in [
        ("<system_dir>", system_dir),
        ("<resources_dir>", resources_dir),
        ("<literature_dir>", literature_dir),
        ("<base_dir>", base_dir),
        ("<skill_dir>", skill_dir),
        ("<prefix>", prefix),
    ]:
        text = text.replace(old, new)
    return text


# ── Deploy helpers ──

def _deploy_skill_directory(vault: Path, skill_dir: str, source_root: Path, system_dir: str, resources_dir: str, literature_dir: str, base_dir: str, prefix: str = "/", overwrite: bool = False) -> list[str]:
    """Deploy pf-* skills as independent SKILL.md directories (Claude Code, Codex, Cursor, etc.)."""
    imported = []
    src_scripts = source_root / "skills" / "literature-qa" / "scripts"
    src_charts = source_root / "skills" / "literature-qa" / "chart-reading"
    src_prompt = source_root / "skills" / "literature-qa" / "prompt_deep_subagent.md"

    for skill_file in sorted(src_scripts.glob("pf-*.md")):
        skill_name = skill_file.stem
        skill_dst = vault / skill_dir / skill_name
        skill_dst.mkdir(parents=True, exist_ok=True)
        text = skill_file.read_text(encoding="utf-8")
        text = _substitute_vars(text, system_dir, resources_dir, literature_dir, base_dir, skill_dir, prefix)
        dst_file = skill_dst / "SKILL.md"
        if overwrite or not dst_file.exists():
            dst_file.write_text(text, encoding="utf-8")
        imported.append(skill_name)

    # pf-deep extras: scripts, chart-reading, subagent prompt
    pf_deep_dst = vault / skill_dir / "pf-deep"
    pf_deep_dst.mkdir(parents=True, exist_ok=True)
    ld_dst = pf_deep_dst / "scripts" / "ld_deep.py"
    ld_src = src_scripts / "ld_deep.py"
    if ld_src.exists() and (overwrite or not ld_dst.exists()):
        ld_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ld_src, ld_dst)
    prompt_dst = pf_deep_dst / "prompt_deep_subagent.md"
    if src_prompt.exists() and (overwrite or not prompt_dst.exists()):
        shutil.copy2(src_prompt, prompt_dst)
    if src_charts.exists() and src_charts.is_dir():
        chart_dst = pf_deep_dst / "chart-reading"
        if overwrite and chart_dst.exists():
            shutil.rmtree(chart_dst)
        chart_dst.mkdir(parents=True, exist_ok=True)
        for f in src_charts.glob("*.md"):
            if overwrite or not (chart_dst / f.name).exists():
                shutil.copy2(f, chart_dst / f.name)

    return imported


def _deploy_flat_command(vault: Path, command_dir: str, source_root: Path, system_dir: str, resources_dir: str, literature_dir: str, base_dir: str, skill_dir: str, overwrite: bool = False) -> list[str]:
    """Deploy skills in flat .md command format (OpenCode)."""
    imported = []
    command_src = source_root / "skills" / "literature-qa" / "scripts"
    command_dst = vault / command_dir
    if not (command_src.exists() and command_src.is_dir()):
        return imported

    command_dst.mkdir(parents=True, exist_ok=True)
    for f in command_src.glob("pf-*.md"):
        text = f.read_text(encoding="utf-8")
        text = _substitute_vars(text, system_dir, resources_dir, literature_dir, base_dir, skill_dir)
        dst_file = command_dst / f.name
        if overwrite or not dst_file.exists():
            dst_file.write_text(text, encoding="utf-8")
        imported.append(f.stem)

    return imported


def _deploy_rules_file(vault: Path, skill_dir: str, source_root: Path, system_dir: str, resources_dir: str, literature_dir: str, base_dir: str, overwrite: bool = False) -> list[str]:
    """Deploy skills as .clinerules directory (Cline)."""
    imported = []
    src_scripts = source_root / "skills" / "literature-qa" / "scripts"
    src_charts = source_root / "skills" / "literature-qa" / "chart-reading"
    src_prompt = source_root / "skills" / "literature-qa" / "prompt_deep_subagent.md"

    pf_deep_dst = vault / skill_dir / "pf-deep"
    pf_deep_dst.mkdir(parents=True, exist_ok=True)
    ld_src = src_scripts / "ld_deep.py"
    ld_dst = pf_deep_dst / "scripts" / "ld_deep.py"
    if ld_src.exists() and (overwrite or not ld_dst.exists()):
        ld_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ld_src, ld_dst)
    prompt_dst = pf_deep_dst / "prompt_deep_subagent.md"
    if src_prompt.exists() and (overwrite or not prompt_dst.exists()):
        shutil.copy2(src_prompt, prompt_dst)
    if src_charts.exists() and src_charts.is_dir():
        chart_dst = pf_deep_dst / "chart-reading"
        if overwrite and chart_dst.exists():
            shutil.rmtree(chart_dst)
        chart_dst.mkdir(parents=True, exist_ok=True)
        for f in src_charts.glob("*.md"):
            if overwrite or not (chart_dst / f.name).exists():
                shutil.copy2(f, chart_dst / f.name)

    imported.append("clinerules")
    return imported


# ── Main entry point ──

def deploy_skills(
    vault: Path,
    agent_key: str = "opencode",
    system_dir: str = "System",
    resources_dir: str = "Resources",
    literature_dir: str = "Literature",
    base_dir: str = "Bases",
    overwrite: bool = False,
) -> dict:
    """Deploy skills, commands, and AGENTS.md for a given agent platform.

    Args:
        vault: Obsidian vault root
        agent_key: Agent platform key (opencode, cursor, claude, etc.)
        overwrite: True for update (overwrite existing), False for install (skip)

    Returns:
        dict with 'skills', 'commands', 'agents_md', 'errors' keys
    """
    agent_config = AGENT_CONFIGS.get(agent_key)
    if not agent_config:
        return {"skills": [], "commands": [], "agents_md": False, "errors": [f"Unknown agent: {agent_key}"]}

    source_root = _resolve_source_root()
    if not (source_root / "skills" / "literature-qa").exists():
        return {"skills": [], "commands": [], "agents_md": False, "errors": ["Skills source not found in package"]}

    skill_dir = agent_config.get("skill_dir", ".opencode/skills")
    fmt = agent_config.get("format", "skill_directory")
    prefix = agent_config.get("prefix", "/")
    imported_skills: list[str] = []
    errors: list[str] = []

    # Deploy skills by format
    try:
        if fmt == "flat_command":
            imported_skills = _deploy_flat_command(vault, agent_config["command_dir"], source_root, system_dir, resources_dir, literature_dir, base_dir, skill_dir, overwrite)
            imported_skills += _deploy_skill_directory(vault, skill_dir, source_root, system_dir, resources_dir, literature_dir, base_dir, prefix, overwrite)
        elif fmt == "rules_file":
            imported_skills = _deploy_rules_file(vault, agent_config["skill_dir"], source_root, system_dir, resources_dir, literature_dir, base_dir, overwrite)
        else:
            imported_skills = _deploy_skill_directory(vault, skill_dir, source_root, system_dir, resources_dir, literature_dir, base_dir, prefix, overwrite)
    except Exception as e:
        errors.append(f"Skill deploy failed: {e}")

    # Deploy AGENTS.md
    agents_ok = False
    agents_src = source_root.parent / "AGENTS.md"
    if agents_src.exists():
        try:
            agents_dst = vault / "AGENTS.md"
            text = agents_src.read_text(encoding="utf-8")
            text = _substitute_vars(text, system_dir, resources_dir, literature_dir, base_dir, skill_dir, prefix)
            if overwrite or not agents_dst.exists():
                agents_dst.write_text(text, encoding="utf-8")
            agents_ok = True
        except Exception as e:
            errors.append(f"AGENTS.md deploy failed: {e}")

    return {
        "skills": imported_skills,
        "commands": imported_skills,
        "agents_md": agents_ok,
        "errors": errors,
    }
