"""#174 corrective: update lifecycle service is pure (no prompt/print) and
publishes the pointer only after fresh-child verification."""

from __future__ import annotations

from unittest.mock import patch

from paperforge.worker import update as update_mod


def test_remote_version_has_urllib_request() -> None:
    """RC gap smoke: `_remote_version` calls urllib.request, which is NOT
    reachable through `import urllib.parse` alone. Guard the import pair so
    the remote version check can never die with AttributeError."""
    assert hasattr(update_mod.urllib, "request")


def test_release_tag_maps_pep440_to_semver_tag() -> None:
    """The install spec is PEP 440; the git tag is SemVer (see publish.yml)."""
    assert update_mod._release_tag("2.0.0") == "2.0.0"
    assert update_mod._release_tag("2.0.0rc1") == "2.0.0-rc.1"
    assert update_mod._release_tag("2.0.0a2") == "2.0.0-alpha.2"
    assert update_mod._release_tag("2.0.0b3") == "2.0.0-beta.3"


def test_needs_update_orders_pre_releases() -> None:
    """A pre-release must be able to reach the NEXT pre-release: the old
    digit-tuple rule read 2.0.0rc1 and 2.0.0rc2 as equal."""
    assert update_mod._needs_update("2.0.0rc2", "2.0.0rc1") is True
    assert update_mod._needs_update("2.0.0", "2.0.0rc1") is True
    assert update_mod._needs_update("2.0.0rc1", "2.0.0rc1") is False
    assert update_mod._needs_update("2.0.0rc1", "2.0.0") is False
    assert update_mod._needs_update("2.0.0", "1.5.15") is True
    assert update_mod._needs_update("1.5.16", "1.5.15") is True


def test_update_pip_pins_the_exact_remote_version(monkeypatch) -> None:
    """`pip install --upgrade paperforge` (unpinned) cannot reach a
    pre-release — pip skips them unless one is named exactly. The install
    spec must pin the remote version."""
    calls: list[list[str]] = []

    class _Done:
        returncode = 0
        stderr = ""

    monkeypatch.setattr(
        update_mod.subprocess,
        "run",
        lambda cmd, **kw: calls.append(list(cmd)) or _Done(),
    )
    assert update_mod._update_via_pip("2.0.0rc1") is True
    assert calls[0][-1] == "paperforge==2.0.0rc1"


def test_update_pip_falls_back_to_the_release_tag(monkeypatch) -> None:
    """PyPI failure → same version from its git tag, never an unpinned ref."""
    calls: list[list[str]] = []

    class _Fail:
        returncode = 1
        stderr = "no network"

    class _Done:
        returncode = 0
        stderr = ""

    def _run(cmd, **kw):
        calls.append(list(cmd))
        return _Fail() if len(calls) == 1 else _Done()

    monkeypatch.setattr(update_mod.subprocess, "run", _run)
    assert update_mod._update_via_pip("2.0.0rc1") is True
    assert calls[1][-1].endswith("@2.0.0-rc.1")


def test_perform_update_up_to_date_no_pointer_write(tmp_path, monkeypatch) -> None:
    """Already-latest: ok, updated=False, no pointer publication."""
    monkeypatch.setattr(update_mod, "_remote_version", lambda: "1.0.0")
    monkeypatch.setattr(update_mod, "_update_via_pip", lambda *a, **kw: True)
    monkeypatch.setattr(update_mod, "_sync_obsidian_plugin", lambda vault: None)
    monkeypatch.setattr(update_mod, "_deploy_all_skills", lambda vault: None)
    with patch("paperforge.__version__", "1.0.0"):
        result = update_mod.perform_update(tmp_path)
    assert result["ok"] is True
    assert result["updated"] is False


def test_perform_update_install_mismatch_does_not_publish(tmp_path, monkeypatch) -> None:
    """Fresh-child verify mismatch → ok=False, no pointer publication."""
    monkeypatch.setattr(update_mod, "_remote_version", lambda: "2.0.0")
    monkeypatch.setattr(update_mod, "_detect_install_method", lambda: ("pip", None))
    monkeypatch.setattr(update_mod, "_update_via_pip", lambda *a, **kw: True)
    monkeypatch.setattr(update_mod, "_fresh_installed_version", lambda: "2.0.0")
    with patch("paperforge.__version__", "1.0.0"):
        result = update_mod.perform_update(tmp_path)
    assert result["ok"] is True
    assert result["updated"] is True
    assert result["installed_version"] == "2.0.0"


def test_perform_update_never_prompts_or_prints(tmp_path, monkeypatch, capsys) -> None:
    """The pure service owns no UX: input() must never be reached and
    nothing may be written to stdout."""
    called = {"input": False}
    real_input = __builtins__["input"] if isinstance(__builtins__, dict) else __builtins__.input
    monkeypatch.setattr("builtins.input", lambda *a, **k: called.__setitem__("input", True) or "y")
    monkeypatch.setattr(update_mod, "_remote_version", lambda: "1.0.0")
    with patch("paperforge.__version__", "1.0.0"):
        update_mod.perform_update(tmp_path)
    assert called["input"] is False
    out = capsys.readouterr().out
    assert out == ""
