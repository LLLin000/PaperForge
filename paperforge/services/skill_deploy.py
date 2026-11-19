"""Skill deployment service — deploys the unified paperforge skill to the vault.

Used by both setup wizard (install) and update worker (update).
All deployments are vault-local only.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

# Skill target dir is caller-chosen (agents know their harness).  Only the
# shared default lives here, from paperforge.config.
from paperforge.config import AGENT_SHARED_SKILL_DIR

logger = logging.getLogger(__name__)


def _skill_state_path(vault: Path) -> Path:
    try:
        from paperforge.config import paperforge_paths

        return paperforge_paths(vault)["paperforge"] / "indexes" / "skill-deploy-state.json"
    except Exception:  # noqa: BLE001 — fallback when called on unconfigured vault
        for cand in (vault / ".paperforge", vault / "System" / "PaperForge"):
            if cand.exists():
                return cand / "indexes" / "skill-deploy-state.json"
        return vault / ".paperforge" / "indexes" / "skill-deploy-state.json"


def _read_skill_state(vault: Path) -> dict:
    path = _skill_state_path(vault)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_skill_state(vault: Path, target_rel: str, digest: str) -> None:
    if not digest:
        return
    try:
        from paperforge import __version__ as pf_version
    except Exception:  # noqa: BLE001
        pf_version = ""
    path = _skill_state_path(vault)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        state = _read_skill_state(vault)
        targets = state.get("targets")
        if not isinstance(targets, dict):
            targets = {}
        targets[target_rel] = {
            "deployed_digest": digest,
            "paperforge_version": pf_version,
        }
        state["targets"] = targets
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(str(tmp), str(path))
    except OSError:
        pass


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
            # Whole package-owned tree identity: relative path + content
            # hash of EVERY managed file.  A references/ or scripts/ change
            # with an unchanged SKILL.md must NOT be a noop.
            identical = (
                dst_skill.exists()
                and _skill_tree_digest(src_skill) == _skill_tree_digest(dst_skill)
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
        if skill_deployed and not errors:
            _write_skill_state(vault, target_dir, _skill_tree_digest(src_skill))
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


def sync_skills_if_unmodified(
    vault: Path,
    target_dir: str | None = None,
) -> dict:
    """Safely upgrade deployed Vault skills only if untouched since last official deploy."""
    target_rel = target_dir or AGENT_SHARED_SKILL_DIR
    target = _validate_target(vault, target_rel)
    if target is None:
        return {
            "synced": False,
            "status": "error",
            "target_dir": target_rel,
            "errors": [f"target dir must stay inside the vault (got {target_rel!r})"],
        }

    source_root = _resolve_source_root()
    src_skill = source_root / "skills" / "paperforge"
    if not src_skill.exists():
        return {
            "synced": False,
            "status": "error",
            "target_dir": target_rel,
            "errors": ["Skills source not found in package"],
        }

    dst_skill = target / "paperforge"
    if not dst_skill.exists():
        return {
            "synced": False,
            "status": "not_deployed",
            "target_dir": target_rel,
            "errors": [],
        }

    src_digest = _skill_tree_digest(src_skill)
    dst_digest = _skill_tree_digest(dst_skill)
    if dst_digest == src_digest:
        _write_skill_state(vault, target_rel, src_digest)
        return {
            "synced": False,
            "status": "up_to_date",
            "target_dir": target_rel,
            "errors": [],
        }

    state = _read_skill_state(vault)
    targets = state.get("targets") if isinstance(state.get("targets"), dict) else {}
    recorded = targets.get(target_rel) if isinstance(targets, dict) else None
    recorded_digest = str(recorded.get("deployed_digest", "") or "") if isinstance(recorded, dict) else ""

    if recorded_digest and dst_digest == recorded_digest:
        res = deploy_skills(vault, overwrite=True, target_dir=target_rel)
        return {
            "synced": bool(res.get("skill_deployed") and not res.get("errors")),
            "status": "updated" if not res.get("errors") else "error",
            "target_dir": target_rel,
            "errors": list(res.get("errors") or []),
        }

    return {
        "synced": False,
        "status": "customized_preserved",
        "target_dir": target_rel,
        "errors": [],
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


def _skill_tree_digest(root: Path) -> str:
    """Deterministic digest over every managed file: relative path + bytes,
    sorted, CRLF-normalized (platform checkout variance must not matter)."""
    import hashlib

    h = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\x00")
        h.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()
