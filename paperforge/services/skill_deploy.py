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


def _atomic_replace_skill_tree(src_skill: Path, dst_skill: Path) -> None:
    """Stage & digest-verify *src_skill* before swapping *dst_skill* atomically with rollback."""
    import uuid

    dst_skill.parent.mkdir(parents=True, exist_ok=True)
    for item in src_skill.rglob("*"):
        if item.is_symlink():
            raise OSError(f"Refusing to deploy symlink inside skill bundle: {item}")
    stage_dir = dst_skill.parent / f".paperforge-skill-stage-{uuid.uuid4().hex[:8]}"
    backup_dir: Path | None = None
    try:
        shutil.copytree(src_skill, stage_dir, dirs_exist_ok=False)
        if _skill_tree_digest(stage_dir) != _skill_tree_digest(src_skill):
            raise RuntimeError("Staged skill digest verification failed")
        if dst_skill.exists():
            backup_dir = dst_skill.parent / f".paperforge-skill-backup-{uuid.uuid4().hex[:8]}"
            dst_skill.rename(backup_dir)
            try:
                stage_dir.rename(dst_skill)
            except Exception:
                if backup_dir.exists() and not dst_skill.exists():
                    backup_dir.rename(dst_skill)
                raise
            try:
                shutil.rmtree(backup_dir)
            except OSError as exc:
                logger.warning("skill_deploy: failed to remove backup %s: %s", backup_dir, exc)
        else:
            stage_dir.rename(dst_skill)
    finally:
        if stage_dir.exists():
            try:
                shutil.rmtree(stage_dir)
            except OSError as exc:
                logger.warning("skill_deploy: failed to remove stage %s: %s", stage_dir, exc)


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
        if not (noop or already_exists):
            try:
                _atomic_replace_skill_tree(src_skill, dst_skill)
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
    sorted by POSIX relative path, CRLF-normalized, ignoring __pycache__/.pyc."""
    import hashlib

    files = [
        p
        for p in root.rglob("*")
        if not p.is_symlink()
        and p.is_file()
        and "__pycache__" not in p.relative_to(root).parts
        and p.suffix.lower() != ".pyc"
    ]
    files.sort(key=lambda p: p.relative_to(root).as_posix())
    h = hashlib.sha256()
    for path in files:
        rel = path.relative_to(root).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\x00")
        h.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def machine_skill_source_dir(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".paperforge" / "skills" / "paperforge"


def machine_skill_meta_path(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".paperforge" / "skills" / ".skill-meta.json"


def agent_installs_registry_path(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".paperforge" / "agent-installs.json"


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(path))


def _is_link_to_hub(dst: Path, hub_dir: Path) -> bool:
    try:
        return (
            dst.exists()
            and hub_dir.exists()
            and dst.resolve() == hub_dir.resolve()
            and dst != hub_dir
        )
    except OSError:
        return False


def _is_safe_registered_skill_dir(dst: Path, *, home: Path | None = None) -> bool:
    """Allow skill sync only inside known agent skill folders named ``paperforge``."""
    if not dst.is_absolute() or ".." in dst.parts or dst.name != "paperforge":
        return False
    parent = dst.parent
    if parent == dst:
        return False
    actual_home = (home or Path.home()).resolve()
    try:
        if dst.resolve() == actual_home or parent.resolve() == actual_home:
            return False
    except OSError:
        return False
    parent_name = parent.name.lower()
    if (
        parent_name in {"skills", ".skills"}
        or parent_name.endswith(("_skills", "-skills"))
        or (not dst.is_symlink() and (dst / "SKILL.md").is_file())
    ):
        return True
    return False


def sync_registered_agent_skills(*, home: Path | None = None) -> dict:
    """Propagate machine Skill Hub updates to all registered external Agent copies.

    - Symlinks / Windows NTFS junctions resolve live to the hub and just refresh
      their recorded digest.
    - Unmodified official copies (digest == recorded ``last_synced_digest``) are
      atomically replaced from the hub.
    - User-customized copies (digest != hub_digest and != last_synced_digest) are
      never overwritten.
    - Deleted paths are pruned from the registry.
    """
    hub_dir = machine_skill_source_dir(home)
    reg_path = agent_installs_registry_path(home)
    if not hub_dir.exists():
        return {"hub_digest": "", "updated": 0, "up_to_date": 0, "customized_preserved": 0, "pruned": 0}
    hub_digest = _skill_tree_digest(hub_dir)

    if not reg_path.exists():
        return {"hub_digest": hub_digest, "updated": 0, "up_to_date": 0, "customized_preserved": 0, "pruned": 0}

    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        installs = reg.get("installs") if isinstance(reg, dict) else []
        if not isinstance(installs, list):
            installs = []
    except (OSError, ValueError):
        return {"hub_digest": hub_digest, "updated": 0, "up_to_date": 0, "customized_preserved": 0, "pruned": 0}

    updated = 0
    up_to_date = 0
    customized_preserved = 0
    pruned = 0
    next_installs: list[dict] = []

    for entry in installs:
        if not isinstance(entry, dict):
            continue
        raw_dir = str(entry.get("skill_dir") or "").strip()
        if not raw_dir:
            pruned += 1
            continue
        dst = Path(raw_dir)
        if not _is_safe_registered_skill_dir(dst):
            pruned += 1
            continue
        if not dst.exists() and not dst.is_symlink():
            pruned += 1
            continue
        if dst.is_symlink() and not _is_link_to_hub(dst, hub_dir):
            pruned += 1
            continue

        item = dict(entry)
        if _is_link_to_hub(dst, hub_dir):
            item["link_mode"] = "link"
            item["last_synced_digest"] = hub_digest
            up_to_date += 1
            next_installs.append(item)
            continue

        cur_digest = _skill_tree_digest(dst)
        recorded = str(item.get("last_synced_digest") or "")
        if cur_digest == hub_digest:
            item["last_synced_digest"] = hub_digest
            up_to_date += 1
        elif recorded and cur_digest == recorded:
            _atomic_replace_skill_tree(hub_dir, dst)
            item["last_synced_digest"] = hub_digest
            updated += 1
        else:
            customized_preserved += 1
        next_installs.append(item)

    try:
        _atomic_write_json(reg_path, {"schema_version": 1, "installs": next_installs})
    except OSError:
        pass

    return {
        "hub_digest": hub_digest,
        "updated": updated,
        "up_to_date": up_to_date,
        "customized_preserved": customized_preserved,
        "pruned": pruned,
    }


def sync_machine_skill_hub(
    *,
    home: Path | None = None,
    source_skill_dir: Path | None = None,
) -> dict:
    """Sync canonical packaged PaperForge skill to ``~/.paperforge/skills/paperforge``
    and propagate updates to all registered Agent installs."""
    from datetime import datetime, timezone

    src = source_skill_dir or (_resolve_source_root() / "skills" / "paperforge")
    if not src.exists():
        return {"ok": False, "hub_updated": False, "error": "Skills source not found"}

    src_digest = _skill_tree_digest(src)
    hub_dir = machine_skill_source_dir(home)
    hub_updated = False
    if not hub_dir.exists() or _skill_tree_digest(hub_dir) != src_digest:
        _atomic_replace_skill_tree(src, hub_dir)
        hub_updated = True

    try:
        from paperforge import __version__ as pf_version
    except Exception:  # noqa: BLE001
        pf_version = ""

    meta_payload = {
        "schema_version": 1,
        "digest": src_digest,
        "paperforge_version": pf_version,
        "source_dir": str(hub_dir),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        _atomic_write_json(machine_skill_meta_path(home), meta_payload)
    except OSError:
        pass

    sync_res = sync_registered_agent_skills(home=home)
    return {
        "ok": True,
        "hub_dir": str(hub_dir),
        "hub_updated": hub_updated,
        **sync_res,
    }
