"""Setup authority closure regressions (#190 review, 2026-08-19).

Layout authority: ALL setup paths come from the single resolver
(``paperforge.config.resolve_paths``); setup modules carry no path
defaults; rerun never clobbers an existing custom layout; fresh installs
create exactly the resolved layout (nested resources/literature, base,
control) with no stray vault-level dirs.
"""

from __future__ import annotations

from pathlib import Path

from paperforge.config import load_config, resolve_paths, set_config
from paperforge.setup.config_writer import ConfigWriter
from paperforge.setup.vault import VaultInitializer
from tests.conftest import canonical_test_config


def _vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    return vault


# ── A. Layout authority ───────────────────────────────────────────────────

def test_setup_modules_have_no_path_defaults() -> None:
    """A1: active setup modules must not carry their own directory defaults
    or legacy 99_System/03_Resources constants."""
    src = Path("paperforge/setup/vault.py").read_text(encoding="utf-8")
    assert "DEFAULT_DIRS" not in src
    assert "99_System" not in src
    assert "03_Resources" not in src
    assert "vault / \"System\"" not in src and "vault / 'System'" not in src
    checker_src = Path("paperforge/setup/checker.py").read_text(encoding="utf-8")
    assert "99_System" not in checker_src


def test_fresh_default_layout_created_exactly(tmp_path: Path) -> None:
    """A3/A5/A6: fresh default setup creates exactly the resolved layout —
    resources/literature nested, control + bases present, no stray
    vault-level dirs."""
    vault = _vault(tmp_path)
    canonical_test_config(vault)
    layout = resolve_paths(vault)
    vi = VaultInitializer(vault, layout)
    result = vi.create_directories()
    assert result.ok
    for d in ("paperforge", "resources", "literature", "control", "bases"):
        assert layout[d].exists(), f"resolved {d} not created: {layout[d]}"
    assert layout["literature"].parent == layout["resources"], "literature must nest under resources"
    assert layout["control"].parent == layout["resources"], "control must nest under resources"
    # No stray top-level dirs beyond the resolved ones.
    created_top = {p.name for p in vault.iterdir() if p.is_dir()}
    expected_top = {layout["system"].name, layout["resources"].name, layout["bases"].name}
    assert created_top <= expected_top, f"stray top-level dirs: {created_top - expected_top}"


def test_custom_layout_created_exactly(tmp_path: Path) -> None:
    """A4: custom dirs flow through resolve_paths into exact creation."""
    vault = _vault(tmp_path)
    canonical_test_config(vault)
    set_config(vault, "system_dir", "99_System")
    set_config(vault, "resources_dir", "03_Resources")
    layout = resolve_paths(vault)
    assert layout["literature"].parent == layout["resources"]
    vi = VaultInitializer(vault, layout)
    assert vi.create_directories().ok
    assert layout["literature"].exists()
    assert (vault / "Literature").exists() is False, "stray vault/Literature must not exist"


# ── B. Rerun semantics ────────────────────────────────────────────────────

def test_rerun_with_empty_config_preserves_custom_values(tmp_path: Path) -> None:
    """B2/B3: `setup` with no explicit dir args writes nothing -> existing
    custom layout is preserved."""
    vault = _vault(tmp_path)
    canonical_test_config(vault)
    set_config(vault, "system_dir", "99_System")
    set_config(vault, "resources_dir", "03_Resources")

    # Rerun with an empty config (unspecified args) must not clobber.
    assert ConfigWriter(vault).write({}).ok
    snap = load_config(vault)
    assert snap.values["system_dir"].value == "99_System"
    assert snap.values["resources_dir"].value == "03_Resources"


def test_explicit_override_changes_only_that_field(tmp_path: Path) -> None:
    """B4: one explicit field changes only that field."""
    vault = _vault(tmp_path)
    canonical_test_config(vault)
    set_config(vault, "system_dir", "99_System")
    ConfigWriter(vault).write({"literature_dir": "MyLit"})
    snap = load_config(vault)
    assert snap.values["literature_dir"].value == "MyLit"
    assert snap.values["system_dir"].value == "99_System", "unrelated field must not change"


def test_fresh_bootstrap_uses_canonical_defaults(tmp_path: Path) -> None:
    """B1: fresh config defaults come from FIELD_SPECS (System/Resources/
    LiteratureControl/Bases), never setup-module constants."""
    vault = _vault(tmp_path)
    assert ConfigWriter(vault).write({}).ok
    snap = load_config(vault)
    assert snap.values["system_dir"].value == "System"
    assert snap.values["resources_dir"].value == "Resources"
    assert snap.values["literature_dir"].value == "Literature"
    assert snap.values["control_dir"].value == "LiteratureControl"
    assert snap.values["base_dir"].value == "Bases"


# ── setup fail-fast (checker / agent substeps) and skill deploy contract ──


def test_checker_failure_blocks_all_mutation(tmp_path, monkeypatch) -> None:
    """T1: checker FAIL -> zero downstream mutation (config/vault/runtime/
    agent never run, pointer never published)."""
    import paperforge.setup.plan as plan_mod
    from paperforge.setup import SetupStepResult

    vault = _vault(tmp_path)
    ran = []

    monkeypatch.setattr(
        plan_mod, "SetupChecker",
        lambda vault: type("C", (), {"run": lambda self: SetupStepResult(step="checker", ok=False, message="boom")})(),
    )
    monkeypatch.setattr(
        plan_mod.ConfigWriter, "write",
        lambda self, cfg: ran.append("config") or SetupStepResult(step="config_writer", ok=True),
    )
    monkeypatch.setattr(
        plan_mod, "VaultInitializer",
        lambda vault, layout: type("V", (), {
            "create_directories": lambda self: ran.append("vault") or SetupStepResult(step="vault", ok=True),
            "create_zotero_junction": lambda self, p=None: SetupStepResult(step="zotero", ok=True),
        })(),
    )
    monkeypatch.setattr("paperforge.setup.runtime.ensure_runtime_dependencies", lambda: ran.append("runtime") or SetupStepResult(step="runtime", ok=True))
    monkeypatch.setattr(plan_mod, "AgentInstaller", lambda vault, agent_type="opencode": type("A", (), {"steps": lambda self: iter([])})())
    monkeypatch.setattr("paperforge.runtime_pointer.publish_pointer", lambda: ran.append("pointer"))

    rc = plan_mod.SetupPlan(vault, config={}).execute()
    assert rc == 1
    assert ran == [], f"checker failure must block all mutation, ran={ran}"


def test_agent_substep_failure_stops_later_substeps(tmp_path, monkeypatch) -> None:
    """T6: first agent substep FAIL -> later substeps never run."""
    import paperforge.setup.plan as plan_mod
    from paperforge.setup import SetupStepResult

    vault = _vault(tmp_path)
    canonical_test_config(vault)
    ran = []
    monkeypatch.setattr(plan_mod, "SetupChecker", lambda vault: type("C", (), {"run": lambda self: SetupStepResult(step="checker", ok=True)})())
    monkeypatch.setattr(plan_mod.ConfigWriter, "write", lambda self, cfg: SetupStepResult(step="config_writer", ok=True))
    monkeypatch.setattr(plan_mod, "VaultInitializer", lambda vault, layout: type("V", (), {
        "create_directories": lambda self: SetupStepResult(step="vault", ok=True),
        "create_zotero_junction": lambda self, p=None: SetupStepResult(step="zotero", ok=True),
    })())
    monkeypatch.setattr("paperforge.setup.runtime.ensure_runtime_dependencies", lambda: SetupStepResult(step="runtime", ok=True))

    def fake_steps(self):
        yield lambda: (ran.append("s1") or SetupStepResult(step="agent.s1", ok=False, message="deploy fail"))
        yield lambda: (ran.append("s2") or SetupStepResult(step="agent.s2", ok=True))

    monkeypatch.setattr(plan_mod, "AgentInstaller", lambda vault, agent_type="opencode": type("A", (), {"steps": fake_steps})())
    monkeypatch.setattr("paperforge.runtime_pointer.publish_pointer", lambda: ran.append("pointer"))

    rc = plan_mod.SetupPlan(vault, config={}).execute()
    assert rc == 1
    assert ran == ["s1"], f"later substeps must not run after failure, ran={ran}"
    assert "pointer" not in ran


def test_skill_deploy_rejects_escape_paths(tmp_path) -> None:
    """--to must stay inside the vault (absolute / .. / vault root rejected)."""
    from paperforge.services.skill_deploy import deploy_skills

    vault = _vault(tmp_path)
    for bad in ("../escape", str(tmp_path.parent / "outside"), ".", "/abs/path"):
        result = deploy_skills(vault, target_dir=bad)
        assert not result["skill_deployed"], bad
        assert result["errors"], bad


def test_skill_deploy_overwrite_contract(tmp_path) -> None:
    """Install -> identical noop -> differs without overwrite = already_exists
    -> differs with overwrite = replaced."""
    from paperforge.services.skill_deploy import deploy_skills

    vault = _vault(tmp_path)
    dst = vault / ".agents" / "skills" / "paperforge"

    r1 = deploy_skills(vault)
    assert r1["skill_deployed"] and not r1["noop"], r1
    assert dst.exists()

    r2 = deploy_skills(vault)
    assert r2["noop"] and r2["skill_deployed"] and not r2["errors"], r2

    (dst / "SKILL.md").write_text("DIFFERENT CONTENT", encoding="utf-8")
    r3 = deploy_skills(vault)
    assert r3["already_exists"] and not r3["skill_deployed"], r3
    assert any("--overwrite" in e for e in r3["errors"]), r3

    r4 = deploy_skills(vault, overwrite=True)
    assert r4["skill_deployed"] and not r4["already_exists"] and not r4["errors"], r4
    assert (dst / "SKILL.md").read_text(encoding="utf-8") != "DIFFERENT CONTENT"


def test_skill_deploy_whole_tree_identity(tmp_path) -> None:
    """A change in a non-SKILL.md managed file must NOT be a noop (whole
    tree digest, not just SKILL.md)."""
    from paperforge.services.skill_deploy import deploy_skills

    vault = _vault(tmp_path)
    dst = vault / ".agents" / "skills" / "paperforge"
    assert deploy_skills(vault)["skill_deployed"]
    # Same tree -> noop
    assert deploy_skills(vault)["noop"]
    # Touch a managed non-SKILL.md file (scripts/…) -> differs, no overwrite
    scripts = dst / "scripts"
    if scripts.exists():
        (scripts / "marker.txt").write_text("changed", encoding="utf-8")
    else:
        (dst / "atoms" / "marker.txt").write_text("changed", encoding="utf-8")
    r = deploy_skills(vault)
    assert r["already_exists"] and not r["noop"], r
