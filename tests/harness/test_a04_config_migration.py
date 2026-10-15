"""A04 — legacy config migrates losslessly, and a second run is byte-identical.

Ported from the two H cases that drive the settings form.  The subject is the
canonical document itself, so the oracle is its bytes: legacy path keys move under
``vault_config``, ``agent_key`` becomes ``agent_platform``, a key the migration does
not know survives verbatim, the derived mirrors are dropped, and running it again
changes nothing.
"""

from __future__ import annotations

import json

import pytest

from .canonical import vault_config

pytestmark = pytest.mark.harness

CASE_ID = "A04"
TITLE = "Legacy config migrates losslessly and the second run is byte-identical"
HOST_SPEC_CASE = (
    "A04 legacy migration: the plugin migrates a legacy config without losing values "
    "and shows them"
)

PATH_KEYS = {
    "system_dir": "System",
    "resources_dir": "Resources",
    "literature_dir": "Literature",
    "control_dir": "LiteratureControl",
    "base_dir": "LegacyBases",
    "skill_dir": ".opencode/skills",
    "command_dir": "Commands",
}
DERIVED_KEYS = ("paperforge_path", "zotero_link")
UNKNOWN_KEY = "custom_legacy_note"


def test_legacy_migration_is_lossless_and_idempotent(cli, vault, case) -> None:
    config_path = vault / "paperforge.json"
    legacy = {
        **PATH_KEYS,
        "agent_key": "claude",
        "paperforge_path": "derived-mirror",
        "zotero_link": "derived-mirror",
        "ocr_profile": "legacy_profile",
        UNKNOWN_KEY: "keep-me",
    }
    config_path.write_text(json.dumps(legacy, indent=2), encoding="utf-8")

    migrated = cli.json("config", "migrate")
    case.check("config migrate exits 0", migrated.returncode == 0, migrated.tail())

    document = vault_config(vault)
    nested = document.get("vault_config") if isinstance(document.get("vault_config"), dict) else {}
    for key, expected in PATH_KEYS.items():
        case.check(
            f"the legacy path key moves under vault_config: {key}",
            str(nested.get(key, "")) == expected,
            f"{nested.get(key)!r}",
        )
    case.check(
        "agent_key becomes agent_platform",
        str(document.get("agent_platform", "")) == "claude" and "agent_key" not in document,
        f"agent_platform={document.get('agent_platform')!r} agent_key_present={'agent_key' in document}",
    )
    case.check(
        "an unknown legacy key survives verbatim",
        str(document.get(UNKNOWN_KEY, "")) == "keep-me",
        str(document.get(UNKNOWN_KEY)),
    )
    for key in DERIVED_KEYS:
        case.check(f"the derived mirror is dropped: {key}", key not in document, f"{key} still present")

    validated = cli.json("config", "validate")
    case.check(
        "the migrated document validates",
        (validated.data or {}).get("state") == "valid",
        json.dumps(validated.data)[:200],
    )

    first = config_path.read_bytes()
    again = cli.json("config", "migrate")
    case.check("a second migrate exits 0", again.returncode == 0, again.tail())
    case.check(
        "a second migrate is byte-identical",
        config_path.read_bytes() == first,
        "the canonical document changed on the second migrate",
    )

    case.artifact("paperforge.json", config_path)
