# Tests for paperforge_lite CLI paths command output.
# These tests prove the locked command surface without invoking real workers.

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest


# ----------------------------------------------------------------------
# Test fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def mock_vault(tmp_path):
    """Create a minimal mock vault with paperforge.json."""
    pf_cfg = {
        "system_dir": "99_System",
        "resources_dir": "03_Resources",
        "literature_dir": "Literature",
        "control_dir": "LiteratureControl",
        "base_dir": "05_Bases",
    }
    (tmp_path / "paperforge.json").write_text(json.dumps(pf_cfg), encoding="utf-8")
    return tmp_path


# ----------------------------------------------------------------------
# Tests — paths --json
# ----------------------------------------------------------------------
def test_paths_json_structure(mock_vault):
    """main(['paths', '--json']) prints valid JSON with D-Path keys."""
    from paperforge_lite.cli import main

    argv = ["--vault", str(mock_vault), "paths", "--json"]
    f = io.StringIO()
    with redirect_stdout(f):
        code = main(argv)
    assert code == 0, f"main() returned {code}, expected 0"
    output = f.getvalue()

    # Must be valid JSON
    data = json.loads(output)

    # D-Path Output keys (from plan interface contract)
    required_keys = {"vault", "worker_script", "ld_deep_script"}
    for key in required_keys:
        assert key in data, f"Missing required JSON key: {key}"

    # No unresolved tokens in any value
    for key, value in data.items():
        if isinstance(value, str):
            assert "<system_dir>" not in value, f"Found unresolved <system_dir> in {key}"
            assert "<resources_dir>" not in value, f"Found unresolved <resources_dir> in {key}"


def test_paths_json_no_unresolved_tokens(mock_vault):
    """paths --json output must not contain <system_dir> or <resources_dir> placeholders."""
    from paperforge_lite.cli import main

    argv = ["--vault", str(mock_vault), "paths", "--json"]
    f = io.StringIO()
    with redirect_stdout(f):
        main(argv)
    output = f.getvalue()

    assert "<system_dir>" not in output, "Found unresolved <system_dir> placeholder"
    assert "<resources_dir>" not in output, "Found unresolved <resources_dir> placeholder"
    # Must still be valid JSON
    json.loads(output)


def test_paths_text_no_unresolved_tokens(mock_vault):
    """paths (text mode) output must not contain unresolved path tokens."""
    from paperforge_lite.cli import main

    argv = ["--vault", str(mock_vault), "paths"]
    f = io.StringIO()
    with redirect_stdout(f):
        main(argv)
    output = f.getvalue()

    # Text mode prints "key: absolute_path" lines — no placeholders
    assert "<system_dir>" not in output, "Found unresolved <system_dir> placeholder"
    assert "<resources_dir>" not in output, "Found unresolved <resources_dir> placeholder"
    # Should contain at least the vault key
    assert "vault:" in output, "Expected 'vault:' in output"
