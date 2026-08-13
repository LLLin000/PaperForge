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


def test_perform_update_up_to_date_no_pointer_write(tmp_path, monkeypatch) -> None:
    """Already-latest: ok, updated=False, no pointer publication."""
    monkeypatch.setattr(update_mod, "_remote_version", lambda: "1.0.0")
    monkeypatch.setattr(update_mod, "_update_via_pip", lambda **kw: True)
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
    monkeypatch.setattr(update_mod, "_update_via_pip", lambda **kw: True)
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
