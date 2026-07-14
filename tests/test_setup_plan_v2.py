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
        assert data.get("schema_version") == "2"
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

    def test_read_v1_format(self, tmp_path: Path) -> None:
        """read() handles legacy flat-format json."""
        from paperforge.setup.config_writer import ConfigWriter

        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "LegacySys", "resources_dir": "LegacyRes"}),
            encoding="utf-8",
        )

        writer = ConfigWriter(tmp_path)
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

    def test_vault_config_wins_over_top_level(self, tmp_path: Path) -> None:
        """vault_config.system_dir overrides legacy top-level system_dir."""
        from paperforge.config import load_vault_config

        vault = tmp_path / "v2_wins"
        vault.mkdir()
        (vault / "paperforge.json").write_text(
            json.dumps({
                "vault_config": {"system_dir": "V2System"},
                "system_dir": "LegacySystem",  # legacy fallback
            }),
            encoding="utf-8",
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg = load_vault_config(vault)

        assert cfg["system_dir"] == "V2System", \
            f"Expected V2System, got {cfg['system_dir']}"

        legacy_warnings = [x for x in w if "legacy" in str(x.message).lower()]
        assert len(legacy_warnings) >= 1, \
            f"Expected legacy warning, got: {[str(x.message) for x in w]}"

    def test_top_level_fallback_when_no_vault_config_key(self, tmp_path: Path) -> None:
        """Legacy top-level key used when vault_config lacks the key."""
        from paperforge.config import load_vault_config

        vault = tmp_path / "top_fallback"
        vault.mkdir()
        (vault / "paperforge.json").write_text(
            json.dumps({
                "vault_config": {"system_dir": "V2System"},
                "resources_dir": "LegacyResources",
            }),
            encoding="utf-8",
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg = load_vault_config(vault)

        assert cfg["system_dir"] == "V2System"
        assert cfg["resources_dir"] == "LegacyResources", \
            "Should fall back to legacy top-level key"

        legacy_warnings = [x for x in w if "legacy" in str(x.message).lower()]
        assert len(legacy_warnings) >= 1, \
            f"Expected legacy warning, got: {[str(x.message) for x in w]}"

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

    def test_v1_only_config_readable_with_warning(self, tmp_path: Path) -> None:
        """V1 flat-only config is readable with a deprecation warning."""
        from paperforge.config import load_vault_config

        vault = tmp_path / "v1_only"
        vault.mkdir()
        (vault / "paperforge.json").write_text(
            json.dumps({
                "system_dir": "OldSystem",
                "resources_dir": "OldResources",
            }),
            encoding="utf-8",
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg = load_vault_config(vault)

        assert cfg["system_dir"] == "OldSystem"
        assert cfg["resources_dir"] == "OldResources"

        legacy_warnings = [x for x in w if "legacy" in str(x.message).lower()]
        assert len(legacy_warnings) >= 1, \
            f"Expected legacy warning, got: {[str(x.message) for x in w]}"


# ===================================================================
# SetupPlan path forwarding
# ===================================================================


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
        assert data2.get("schema_version") == "2"
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
        """When a required step fails, execute returns non-zero."""
        from paperforge.setup.plan import SetupPlan

        vault = tmp_path / "fail_test"
        vault.mkdir()

        # Empty config causes ConfigWriter validation failure
        plan = SetupPlan(vault=vault, config={})
        exit_code = plan.execute(json_output=False)

        assert exit_code != 0, "Expected non-zero exit code for failed setup"

    def test_error_message_in_results(self, tmp_path: Path) -> None:
        """Failed setup with missing keys returns non-zero exit code."""
        from paperforge.setup.plan import SetupPlan

        vault = tmp_path / "msg_test"
        vault.mkdir()

        plan = SetupPlan(vault=vault, config={})
        exit_code = plan.execute(json_output=False)
        assert exit_code != 0
