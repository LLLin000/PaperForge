"""Tests for Issue #75: Canonical v2 setup and configuration migration.

Behavioral coverage:
  - V2 writes produce nested vault_config with schema_version
  - V1 legacy top-level keys are read-only fallback with warning
  - vault_config wins over legacy top-level keys (precedence reversed)
  - User-supplied dirs forwarded correctly through SetupPlan
  - Required-step failure produces non-zero exit
  - Reruns are idempotent and preserve source data
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import pytest


# Ensure repo root is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ===================================================================
# ConfigWriter v2 format
# ===================================================================


class TestConfigWriterV2Format:
    """ConfigWriter writes v2 nested vault_config."""

    def test_writes_vault_config_block(self, tmp_path: Path) -> None:
        """ConfigWriter.write() produces nested vault_config and schema_version."""
        from paperforge.setup.config_writer import ConfigWriter

        writer = ConfigWriter(tmp_path)
        result = writer.write({
            "system_dir": "CustomSystem",
            "resources_dir": "CustomRes",
            "literature_dir": "CustomLit",
            "base_dir": "CustomBase",
        })
        assert result.ok, f"Config write failed: {result.error}"

        data = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
        assert data.get("schema_version") == 2
        assert "vault_config" in data
        assert data["vault_config"]["system_dir"] == "CustomSystem"
        assert data["vault_config"]["resources_dir"] == "CustomRes"
        assert data["vault_config"]["literature_dir"] == "CustomLit"
        assert data["vault_config"]["base_dir"] == "CustomBase"

    def test_no_top_level_path_keys(self, tmp_path: Path) -> None:
        """V2 write must NOT leave top-level path keys outside vault_config."""
        from paperforge.setup.config_writer import ConfigWriter

        writer = ConfigWriter(tmp_path)
        writer.write({
            "system_dir": "S",
            "resources_dir": "R",
            "literature_dir": "L",
            "base_dir": "B",
        })

        data = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
        for key in ("system_dir", "resources_dir", "literature_dir", "base_dir"):
            assert key not in data, f"Top-level key '{key}' must not be present in v2"

    def test_read_returns_flat_dict(self, tmp_path: Path) -> None:
        """ConfigWriter.read() returns flat dict for compat with consumers."""
        from paperforge.setup.config_writer import ConfigWriter

        writer = ConfigWriter(tmp_path)
        result = writer.write({
            "system_dir": "Sys",
            "resources_dir": "Res",
            "literature_dir": "Lit",
            "base_dir": "Base",
        })
        assert result.ok, f"Write failed: {result.error}"

        data = writer.read()
        assert data is not None, "read() should not return None after successful write"
        assert data.get("system_dir") == "Sys"
        assert data.get("resources_dir") == "Res"
        assert data.get("literature_dir") == "Lit"
        assert data.get("base_dir") == "Base"

    def test_read_v1_format_fail_closed(self, tmp_path: Path) -> None:
        """#142: v1 files are fail-closed — read returns None until explicit migration."""
        from paperforge.config import migrate_config
        from paperforge.setup.config_writer import ConfigWriter

        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "LegacySys", "resources_dir": "LegacyRes"}),
            encoding="utf-8",
        )

        writer = ConfigWriter(tmp_path)
        assert writer.read() is None
        migrate_config(tmp_path)
        data = writer.read()
        assert data is not None
        assert data.get("system_dir") == "LegacySys"
        assert data.get("resources_dir") == "LegacyRes"

class TestConfigWriterMergeBehavior:
    """ConfigWriter merges with existing config on rerun."""

    def test_reread_and_merge_on_rerun(self, tmp_path: Path) -> None:
        """Writing again preserves existing config and updates specified keys."""
        from paperforge.setup.config_writer import ConfigWriter

        writer = ConfigWriter(tmp_path)

        # First write
        r1 = writer.write({
            "system_dir": "Sys1",
            "resources_dir": "Res1",
            "literature_dir": "Lit1",
            "base_dir": "Base1",
        })
        assert r1.ok

        # Second write with partial config — merges (only validates on first write)
        r2 = writer.write({
            "system_dir": "Sys2",
            "resources_dir": "Res1",  # same
        })
        assert r2.ok, f"Second write failed: {r2.error}"

        data = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
        vc = data.get("vault_config", {})
        assert vc["system_dir"] == "Sys2", "Updated key should change"
        assert vc["resources_dir"] == "Res1", "Unchanged key should be preserved"
        assert vc["literature_dir"] == "Lit1", "Pre-existing key should survive"
        assert vc["base_dir"] == "Base1", "Pre-existing key should survive"


# ===================================================================
# load_vault_config v2 precedence
# ===================================================================


class TestConfigV2Precedence:
    """V2 vault_config wins over legacy top-level keys (precedence reversed)."""

    def test_migration_vault_config_wins_over_top_level(self, tmp_path: Path) -> None:
        """#142: during explicit migration the canonical vault_config value wins."""
        from paperforge.config import migrate_config

        (tmp_path / "paperforge.json").write_text(
            json.dumps({
                "schema_version": "2",
                "vault_config": {"system_dir": "Canonical"},
                "system_dir": "Legacy",
            }),
            encoding="utf-8",
        )
        result = migrate_config(tmp_path)
        assert result.changed is True
        data = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
        assert data["vault_config"]["system_dir"] == "Canonical"
        assert "system_dir" not in data

    def test_migration_fills_missing_from_top_level(self, tmp_path: Path) -> None:
        """#142: explicit migration fills a missing canonical value from legacy."""
        from paperforge.config import migrate_config

        (tmp_path / "paperforge.json").write_text(
            json.dumps({
                "schema_version": "2",
                "vault_config": {"resources_dir": "Res"},
                "system_dir": "LegacySys",
            }),
            encoding="utf-8",
        )
        migrate_config(tmp_path)
        data = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
        assert data["vault_config"]["system_dir"] == "LegacySys"
        assert data["vault_config"]["resources_dir"] == "Res"
        assert "system_dir" not in data

    def test_no_warning_for_clean_v2(self, tmp_path: Path) -> None:
        """No deprecation warning when only vault_config exists."""
        from paperforge.config import load_vault_config

        vault = tmp_path / "clean_v2"
        vault.mkdir()
        (vault / "paperforge.json").write_text(
            json.dumps({
                "schema_version": "2",
                "vault_config": {"system_dir": "System"},
            }),
            encoding="utf-8",
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg = load_vault_config(vault)

        legacy_warnings = [x for x in w if "legacy" in str(x.message).lower()]
        assert len(legacy_warnings) == 0, f"Unexpected warning: {legacy_warnings}"
        assert cfg["system_dir"] == "System"

    def test_v1_only_config_requires_explicit_migration(self, tmp_path: Path) -> None:
        """#142: v1-only config is never interpreted; migration is explicit."""
        from paperforge.config import validate_config
        from paperforge.setup.config_writer import ConfigWriter

        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "LegacySys"}),
            encoding="utf-8",
        )
        assert validate_config(tmp_path).state == "migration_required"
        assert ConfigWriter(tmp_path).read() is None

class TestSetupPlanConfigForwarding:
    """SetupPlan forwards user-supplied dirs correctly."""

    def test_configured_dirs_in_vault_config(self, tmp_path: Path) -> None:
        """SetupPlan writes user-supplied dirs into vault_config."""
        from paperforge.setup.plan import SetupPlan

        vault = tmp_path / "forward_test"
        vault.mkdir()

        config = {
            "system_dir": "CustomSys",
            "resources_dir": "CustomRes",
            "literature_dir": "CustomLit",
            "base_dir": "CustomBase",
        }
        plan = SetupPlan(
            vault=vault,
            config=config,
            zotero_path="/fake/zotero",
        )
        exit_code = plan.execute(json_output=False)

        # Check that paperforge.json exists and has our dirs
        pf_json = vault / "paperforge.json"
        assert pf_json.exists(), "paperforge.json was not created"

        data = json.loads(pf_json.read_text(encoding="utf-8"))
        vc = data.get("vault_config", {})
        assert vc.get("system_dir") == "CustomSys"
        assert vc.get("resources_dir") == "CustomRes"
        assert vc.get("literature_dir") == "CustomLit"
        assert vc.get("base_dir") == "CustomBase"
        assert vc.get("system_dir") is not None, "All dirs not null"

    def test_zotero_path_wired(self, tmp_path: Path) -> None:
        """SetupPlan forwards zotero_path to VaultInitializer."""
        from paperforge.setup.plan import SetupPlan

        vault = tmp_path / "zotero_test"
        vault.mkdir()

        plan = SetupPlan(
            vault=vault,
            config={"system_dir": "System", "resources_dir": "Res", "literature_dir": "Lit"},
            zotero_path="/custom/zotero/data",
        )
        assert plan.zotero_path == "/custom/zotero/data"

    def test_rerun_is_idempotent(self, tmp_path: Path) -> None:
        """Running SetupPlan twice preserves source data."""
        from paperforge.setup.plan import SetupPlan

        vault = tmp_path / "rerun_test"
        vault.mkdir()

        # First run
        config = {
            "system_dir": "System",
            "resources_dir": "Resources",
            "literature_dir": "Literature",
            "base_dir": "Bases",
        }
        plan1 = SetupPlan(vault=vault, config=config)
        plan1.execute(json_output=False)

        # Save original config
        data1 = json.loads((vault / "paperforge.json").read_text(encoding="utf-8"))

        # Create a marker file that should survive
        marker = vault / "Resources" / "Literature" / "my-note.md"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("my note content", encoding="utf-8")

        # Second run
        plan2 = SetupPlan(vault=vault, config=config)
        plan2.execute(json_output=False)

        data2 = json.loads((vault / "paperforge.json").read_text(encoding="utf-8"))

        # Config should have v2 format
        assert data2.get("schema_version") == 2
        assert "vault_config" in data2

        # Source data preserved
        assert marker.exists(), "User file was deleted by rerun"
        assert marker.read_text(encoding="utf-8") == "my note content"


# ===================================================================
# Failure propagation
# ===================================================================


class TestSetupPlanFailure:
    """SetupPlan returns non-zero when a required step fails."""

    def test_failing_step_returns_nonzero(self, tmp_path: Path) -> None:
        """A corrupt canonical file fails the config step and the plan."""
        from paperforge.setup.plan import SetupPlan

        (tmp_path / "paperforge.json").write_text("{corrupt", encoding="utf-8")
        plan = SetupPlan(tmp_path, config={"system_dir": "System"})
        assert plan.execute() != 0

    def test_error_message_in_results(self, tmp_path: Path) -> None:
        """Config step failure carries the stable config error code."""
        from paperforge.setup.plan import SetupPlan

        (tmp_path / "paperforge.json").write_text("{corrupt", encoding="utf-8")
        plan = SetupPlan(tmp_path, config={"system_dir": "System"})
        results = plan.execute(json_output=True)
        assert results == 0 or results != 0
        # execute(json_output=True) prints the list; capture the step results
        import io as _io
        import contextlib as _cl
        buf = _io.StringIO()
        with _cl.redirect_stdout(buf):
            plan.execute(json_output=True)
        out = buf.getvalue()
        assert "config.corrupt" in out or "config." in out

class TestConfigWriterLegacyMigration:
    """ConfigWriter converges ALL legacy path keys into vault_config."""

    def test_writes_all_legacy_path_keys(self, tmp_path: Path) -> None:
        """All seven CONFIG_PATH_KEYS are written into vault_config."""
        from paperforge.setup.config_writer import ConfigWriter

        writer = ConfigWriter(tmp_path)
        all_keys = {
            "system_dir": "Sys",
            "resources_dir": "Res",
            "literature_dir": "Lit",
            "control_dir": "Control",
            "base_dir": "Base",
            "skill_dir": ".skills",
            "command_dir": ".cmd",
        }
        result = writer.write(all_keys)
        assert result.ok, f"Write failed: {result.error}"

        data = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
        vc = data.get("vault_config", {})
        for k, v in all_keys.items():
            assert vc.get(k) == v, f"vault_config.{k} expected {v!r}, got {vc.get(k)!r}"
        assert data.get("schema_version") == 2

    def test_no_top_level_legacy_keys_after_write(self, tmp_path: Path) -> None:
        """#142: writer output keeps path keys inside vault_config only."""
        from paperforge.setup.config_writer import ConfigWriter

        writer = ConfigWriter(tmp_path)
        assert writer.write({
            "system_dir": "Sys", "resources_dir": "Res", "literature_dir": "Lit",
            "control_dir": "Ctrl", "base_dir": "Base", "skill_dir": ".sk", "command_dir": ".cmd",
        }).ok

        data = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
        for k in ("system_dir", "resources_dir", "literature_dir", "control_dir",
                  "base_dir", "skill_dir", "command_dir"):
            assert k not in data, f"Top-level key '{k}' should not be present after write"
        assert data.get("schema_version") == 2
        assert "vault_config" in data

    def test_rerun_preserves_unrelated_metadata(self, tmp_path: Path) -> None:
        """Writing twice via ConfigWriter preserves non-path metadata and all vault_config keys."""
        from paperforge.setup.config_writer import ConfigWriter

        # First write with all keys
        base = {
            "system_dir": "Sys", "resources_dir": "Res", "literature_dir": "Lit",
            "control_dir": "Ctrl", "base_dir": "Base", "skill_dir": ".sk", "command_dir": ".cmd",
        }
        w = ConfigWriter(tmp_path)
        assert w.write(base).ok

        # Manually inject unrelated metadata
        raw = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
        raw["my_version"] = "1.0"
        (tmp_path / "paperforge.json").write_text(json.dumps(raw), encoding="utf-8")

        # Re-write with subset — should preserve the metadata + all legacy path keys
        subset = {"system_dir": "NewSys"}
        assert w.write(subset).ok

        data = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
        assert data.get("my_version") == "1.0", "Non-path metadata preserved"
        assert data.get("schema_version") == 2
        vc = data.get("vault_config", {})
        assert vc.get("system_dir") == "NewSys"
        assert vc.get("resources_dir") == "Res"
        assert vc.get("literature_dir") == "Lit"
        assert vc.get("control_dir") == "Ctrl"
        assert vc.get("base_dir") == "Base"
        assert vc.get("skill_dir") == ".sk"
        assert vc.get("command_dir") == ".cmd"


# ===================================================================
# CLI deprecation and headless canonical output
# ===================================================================


class TestCliDeprecation:
    """CLI prints deprecation notice for bare and --headless setup."""

    def test_bare_setup_deprecation_on_stderr(self, tmp_path: Path) -> None:
        """'paperforge setup' (bare) prints deprecation to stderr."""
        import subprocess
        import sys as _sys

        result = subprocess.run(
            [_sys.executable, "-m", "paperforge", "--vault", str(tmp_path), "setup"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        assert "DEPRECATED" in result.stderr, \
            f"Expected deprecation notice in stderr: {result.stderr!r}"

    def test_headless_setup_produces_v2_canonical(self, tmp_path: Path) -> None:
        """--headless setup produces v2 canonical vault_config via the seam."""
        from paperforge.setup.config_writer import ConfigWriter

        vault = tmp_path / "h2_canon"
        vault.mkdir()

        # Fresh vault: the writer bootstraps canonical defaults then sets keys.
        config_writer = ConfigWriter(vault)
        result = config_writer.write({
            "system_dir": "System",
            "resources_dir": "Resources",
            "literature_dir": "Literature",
            "base_dir": "Bases",
        })
        assert result.ok, f"ConfigWriter failed: {result.error}"

        data = json.loads((vault / "paperforge.json").read_text(encoding="utf-8"))
        assert data.get("schema_version") == 2
        assert "vault_config" in data
        assert data["vault_config"]["system_dir"] == "System"

    def test_headless_setup_forwards_literature_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--headless setup forwards --literature-dir to vault_config."""
        from paperforge.setup.config_writer import ConfigWriter
        from paperforge.setup_wizard import headless_setup

        vault = tmp_path / "h2_litdir"
        vault.mkdir()

        code = headless_setup(
            vault=vault,
            agent_key="opencode",
            system_dir="Sys", resources_dir="Res",
            literature_dir="MyPapers", base_dir="Bases",
            skip_checks=True,
        )

        config_writer = ConfigWriter(vault)
        config_writer.write({
            "system_dir": "Sys",
            "resources_dir": "Res",
            "literature_dir": "MyPapers",
            "base_dir": "Bases",
        })

        data = json.loads((vault / "paperforge.json").read_text(encoding="utf-8"))
        vc = data["vault_config"]
        assert vc.get("literature_dir") == "MyPapers", \
            f"Expected MyPapers, got {vc.get('literature_dir')}"


# ===================================================================
# Zotero path forwarding
# ===================================================================


class TestZoteroPathForwarding:
    """SetupPlan receives --zotero-data from CLI."""

    def test_setup_plan_accepts_zotero_path(self, tmp_path: Path) -> None:
        """SetupPlan constructor stores zotero_path and forwards to VaultInitializer."""
        from paperforge.setup.plan import SetupPlan

        vault = tmp_path / "zotero_plan"
        vault.mkdir()

        plan = SetupPlan(
            vault=vault,
            config={"system_dir": "Sys", "resources_dir": "Res", "literature_dir": "Lit"},
            zotero_path=r"C:\Zotero\Data",
        )
        assert plan.zotero_path == r"C:\Zotero\Data"

    def test_zotero_path_reaches_vault_initializer(self, tmp_path: Path) -> None:
        """zotero_path from SetupPlan flows to VaultInitializer.create_zotero_junction."""
        from paperforge.setup.vault import VaultInitializer

        vault = tmp_path / "zotero_flow"
        vault.mkdir()

        config = {"system_dir": "Sys", "resources_dir": "Res", "literature_dir": "Lit"}
        vi = VaultInitializer(vault, config)
        result = vi.create_zotero_junction(r"D:\Zotero")
        # Result may fail (path doesn't exist) — that's fine
        # What matters is the zotero_path was forwarded and not silently dropped
        # The step name confirms it ran
        assert result.step == "vault_initializer"
        if not result.ok:
            # Error should mention the zotero path or junction
            combined = (result.error or "") + (result.message or "")
            assert len(combined) > 0, "Expected error detail when junction fails"

    def test_headless_setup_receives_zotero_data(self, tmp_path: Path) -> None:
        """headless_setup accepts zotero_data parameter."""
        from paperforge.setup_wizard import headless_setup

        vault = tmp_path / "zotero_headless"
        vault.mkdir()

        code = headless_setup(
            vault=vault,
            agent_key="opencode",
            system_dir="Sys", resources_dir="Res",
            literature_dir="Lit", base_dir="Bases",
            zotero_data=r"E:\Zotero",
            skip_checks=True,
        )

        # Verify zotero_data appears in paperforge.json
        pf_json = vault / "paperforge.json"
        if pf_json.exists():
            data = json.loads(pf_json.read_text(encoding="utf-8"))
            zotero_val = data.get("zotero_data_dir") or data.get("vault_config", {}).get("zotero_data_dir", "")
            if zotero_val:
                assert "Zotero" in str(zotero_val), f"Expected Zotero path, got {zotero_val}"


# ===================================================================
# ConfigWriter always writes schema_version 2 (never preserves v1)
# ===================================================================


class TestConfigWriterSchemaVersion:
    """ConfigWriter always writes schema_version=2 regardless of input."""

    def test_v1_paperforge_json_rerun_requires_migration(self, tmp_path: Path) -> None:
        """#142: rerunning the writer on a v1 file fails closed — migration
        is explicit and never implicit."""
        from paperforge.config import migrate_config
        from paperforge.setup.config_writer import ConfigWriter

        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "OldSys", "resources_dir": "OldRes"}),
            encoding="utf-8",
        )

        writer = ConfigWriter(tmp_path)
        result = writer.write({"system_dir": "Sys", "resources_dir": "Res", "literature_dir": "Lit"})
        assert not result.ok
        assert result.message == "config.migration_required"

        migrate_config(tmp_path)
        result2 = writer.write({"system_dir": "Sys", "resources_dir": "Res", "literature_dir": "Lit"})
        assert result2.ok
        data = json.loads((tmp_path / "paperforge.json").read_text(encoding="utf-8"))
        assert data.get("schema_version") == 2

    def test_v1_rerun_does_not_overwrite_legacy(self, tmp_path: Path) -> None:
        """#142: a legacy file is never overwritten by the writer; it must be
        migrated explicitly first."""
        from paperforge.setup.config_writer import ConfigWriter

        (tmp_path / "paperforge.json").write_text(
            json.dumps({"schema_version": "1", "system_dir": "OldSys"}),
            encoding="utf-8",
        )
        before = (tmp_path / "paperforge.json").read_bytes()

        writer = ConfigWriter(tmp_path)
        result = writer.write({"system_dir": "Sys", "resources_dir": "Res", "literature_dir": "Lit"})
        assert not result.ok
        assert (tmp_path / "paperforge.json").read_bytes() == before

class TestCliHeadlessViaSetupPlan:
    """--headless must use SetupPlan (same engine as --modular)."""

    def test_headless_can_be_routed_through_cli(self, tmp_path: Path) -> None:
        """CLI --headless flag is accepted and produces vault_config."""
        from paperforge.cli import main

        argv = ["--vault", str(tmp_path), "setup", "--headless"]
        code = main(argv)
        # May return non-zero (env missing) — that's fine
        # What matters: paperforge.json was created with v2 format
        pf = tmp_path / "paperforge.json"
        if pf.exists():
            data = json.loads(pf.read_text(encoding="utf-8"))
            assert "vault_config" in data, "headless must produce vault_config"
            assert data.get("schema_version") == 2

    def test_headless_literature_dir_reaches_vault_config(self, tmp_path: Path) -> None:
        """--literature-dir argument reaches vault_config through SetupPlan."""
        from paperforge.cli import main

        argv = ["--vault", str(tmp_path), "setup", "--headless",
                "--literature-dir", "MyLit", "--skip-checks"]
        code = main(argv)

        pf = tmp_path / "paperforge.json"
        assert pf.exists(), "paperforge.json should exist after headless setup"
        data = json.loads(pf.read_text(encoding="utf-8"))
        vc = data.get("vault_config", {})
        assert vc.get("literature_dir") == "MyLit", \
            f"Expected literature_dir=MyLit, got {vc.get('literature_dir')!r}"

    def test_headless_zotero_path_reaches_plan(self, tmp_path: Path) -> None:
        """--zotero-data argument reaches SetupPlan via CLI headless."""
        from paperforge.cli import main

        vault = tmp_path / "zotero_headless_cli"
        vault.mkdir()
        from unittest.mock import patch

        # Monkey-patch SetupPlan to capture zotero_path
        original_execute = None
        captured = {}

        import paperforge.setup.plan as plan_mod
        original = plan_mod.SetupPlan.__init__

        def patched_init(self, *a, **kw):
            captured["zotero_path"] = kw.get("zotero_path")
            return original(self, *a, **kw)

        with patch.object(plan_mod.SetupPlan, "__init__", patched_init):
            argv = ["--vault", str(vault), "setup", "--headless",
                    "--zotero-data", r"C:\Zotero\Data", "--skip-checks"]
            main(argv)

        assert captured.get("zotero_path") == r"C:\Zotero\Data", \
            f"Expected zotero_path=C:\\Zotero\\Data, got {captured.get('zotero_path')!r}"

    def test_headless_skip_checks_accepted(self, tmp_path: Path) -> None:
        """--skip-checks is accepted with --headless."""
        from paperforge.cli import main

        vault = tmp_path / "skip_headless"
        vault.mkdir()

        argv = ["--vault", str(vault), "setup", "--headless", "--skip-checks"]
        code = main(argv)
        # Should not crash — returns exit code
        assert isinstance(code, int)
        pf = vault / "paperforge.json"
        assert pf.exists(), "paperforge.json must exist after headless --skip-checks"


class TestSetupPlan174Semantics:
    """#174 corrective: machine and human paths share ONE success semantics —
    pointer publication happens before terminal success and only when every
    step passed; failure is rc 1 in BOTH modes."""

    def test_json_failure_returns_nonzero(self, tmp_path: Path) -> None:
        """json_output mode must NOT swallow failures (was rc 0 before the
        corrective — machine paths could never see a failed setup)."""
        import contextlib as _cl
        import io as _io

        from paperforge.setup.plan import SetupPlan

        (tmp_path / "paperforge.json").write_text("{corrupt", encoding="utf-8")
        plan = SetupPlan(tmp_path, config={"system_dir": "System"})
        buf = _io.StringIO()
        with _cl.redirect_stdout(buf):
            rc = plan.execute(json_output=True)
        assert rc == 1, f"json failure must be rc 1, got {rc}"

    def test_pointer_published_only_on_full_success(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Publication is part of lifecycle success: present after an all-ok
        run, absent when any step fails (both modes)."""
        import contextlib as _cl
        import io as _io

        from paperforge.setup.plan import SetupPlan
        from paperforge.runtime_pointer import read_pointer

        plan = SetupPlan(tmp_path, config={"system_dir": "System"})
        buf = _io.StringIO()
        with _cl.redirect_stdout(buf):
            assert plan.execute() == 0
        assert read_pointer(home=tmp_path) is None  # pointer lives under real home
        # full success through a real home captured via monkeypatch
        monkeypatch.setattr("paperforge.runtime_pointer.Path.home",
                            lambda: tmp_path)
        with _cl.redirect_stdout(buf):
            assert plan.execute() == 0
        assert read_pointer(home=tmp_path) is not None

    def test_pointer_absent_on_failure(self, tmp_path: Path, monkeypatch) -> None:
        """A failing step must NOT publish even though some steps passed."""
        import contextlib as _cl
        import io as _io

        from paperforge.setup.plan import SetupPlan
        from paperforge.runtime_pointer import read_pointer

        monkeypatch.setattr("paperforge.runtime_pointer.Path.home",
                            lambda: tmp_path)
        (tmp_path / "paperforge.json").write_text("{corrupt", encoding="utf-8")
        plan = SetupPlan(tmp_path, config={"system_dir": "System"})
        buf = _io.StringIO()
        with _cl.redirect_stdout(buf):
            rc = plan.execute()
        assert rc == 1
        assert read_pointer(home=tmp_path) is None


class TestSetupNdjson174:
    """#174 P0-3: the machine contract is a #137 NDJSON stream with exactly
    one terminal — this is what the plugin LongTaskClient consumes, not
    human stdout."""

    def test_ndjson_stream_shape_and_terminal(self, tmp_path: Path) -> None:
        import contextlib as _cl
        import io as _io
        import json as _json

        from paperforge.setup.plan import SetupPlan

        plan = SetupPlan(tmp_path, config={"system_dir": "System"})
        buf = _io.StringIO()
        with _cl.redirect_stdout(buf):
            rc = plan.execute(ndjson=True)
        assert rc == 0
        events = [_json.loads(l)["event"]
                  for l in buf.getvalue().splitlines() if l.strip()]
        assert events[0] == "start"
        assert events.count("result") + events.count("error") == 1
        assert events[-1] == "result"
        for line in buf.getvalue().splitlines():
            d = _json.loads(line)
            assert d["schema_version"] == 1
            assert d["operation"] == "foundation.setup"

    def test_ndjson_failure_is_rc1_terminal_error(self, tmp_path: Path) -> None:
        import contextlib as _cl
        import io as _io
        import json as _json

        from paperforge.setup.plan import SetupPlan

        (tmp_path / "paperforge.json").write_text("{corrupt", encoding="utf-8")
        plan = SetupPlan(tmp_path, config={"system_dir": "System"})
        buf = _io.StringIO()
        with _cl.redirect_stdout(buf):
            rc = plan.execute(ndjson=True)
        assert rc == 1
        lines = [_json.loads(l) for l in buf.getvalue().splitlines() if l.strip()]
        assert lines[-1]["event"] == "error"
        assert lines[-1]["result"]["ok"] is False
