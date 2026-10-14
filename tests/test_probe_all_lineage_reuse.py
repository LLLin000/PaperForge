import contextlib
import io
import json

from tests.conftest import canonical_test_config


def _run_probe_all_counted(monkeypatch, tmp_path, module="probe"):
    import paperforge.commands.probe as probe_mod
    import paperforge.lineage as lin

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)

    calls = {"n": 0}
    original = lin.probe_lineage

    def wrapper(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(lin, "probe_lineage", wrapper)

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert probe_mod._run_probe_all(vault, json_output=False) == 0
    return calls["n"], vault, out.getvalue()


def test_probe_all_computes_lineage_once(monkeypatch, tmp_path):
    n, vault, _ = _run_probe_all_counted(monkeypatch, tmp_path)
    assert n == 1, n


def test_probe_ocr_standalone_computes_lineage(monkeypatch, tmp_path):
    import paperforge.commands.probe as probe_mod
    import paperforge.lineage as lin

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)

    calls = {"n": 0}
    original = lin.probe_lineage

    def wrapper(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(lin, "probe_lineage", wrapper)
    probe_mod.probe_ocr(vault)
    assert calls["n"] == 1, calls["n"]


def test_probe_all_output_invariant_on_fixture_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)

    import subprocess, sys

    result = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(vault), "probe", "all", "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["module"] == "all"
    assert sorted(payload["modules"].keys()) == [
        "help", "installation", "library", "maintenance", "memory", "ocr",
    ]
    # maintenance mirrors the base modules without re-running them
    maintenance = payload["modules"]["maintenance"]
    assert "items" in maintenance and "orphan" in maintenance
