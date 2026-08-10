"""Credential authority tests (#173 / C1, #138).

The conftest autouse fixture injects an in-memory fake keyring, so every
test is hermetic: the real OS keyring is never consulted and canonical env
vars never leak from the dev machine.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from paperforge import credentials as c
from paperforge.credentials import (
    BACKEND_UNAVAILABLE,
    CONFLICT,
    CredentialError,
    CredentialKey,
    CredentialStatus,
    delete,
    env_value,
    resolve,
    status,
    store,
)

from tests.conftest import canonical_test_config

CANON_OCR = "PAPERFORGE_CREDENTIAL_OCR__DEFAULT"
CANON_EMB = "PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT"


def _fake_keyring() -> object:
    """The conftest-installed fake keyring."""
    assert c._keyring_override is not None, "hermetic keyring fixture missing"
    return c._keyring_override


# ── provider contract ─────────────────────────────────────────────────────

class TestProviderContract:
    def test_key_contract(self) -> None:
        key = CredentialKey("ocr")
        assert key.env_name == CANON_OCR
        assert key.keyring_username == "ocr:default"
        with pytest.raises(ValueError):
            CredentialKey("bogus")  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            CredentialKey("ocr", "Bad-Profile")
        assert CredentialKey("embedding", "local_openai").env_name == (
            "PAPERFORGE_CREDENTIAL_EMBEDDING__LOCAL_OPENAI"
        )

    def test_missing_raises_typed_error(self) -> None:
        with pytest.raises(CredentialError) as exc:
            resolve(CredentialKey("ocr"))
        assert exc.value.code == "credential.missing"

    def test_env_precedence_over_keyring(self) -> None:
        store(CredentialKey("ocr"), "keyring-value")
        assert resolve(CredentialKey("ocr")) == "keyring-value"
        # Explicit canonical env wins without touching keyring.
        assert resolve(CredentialKey("ocr"), env={CANON_OCR: "env-value"}) == "env-value"
        st = status(CredentialKey("ocr"), env={CANON_OCR: "env-value"})
        assert st.state == "available" and st.source == "environment"
        # The stored keyring value is untouched.
        assert resolve(CredentialKey("ocr")) == "keyring-value"

    def test_store_conflict_and_replace(self) -> None:
        store(CredentialKey("embedding"), "v1")
        with pytest.raises(CredentialError) as exc:
            store(CredentialKey("embedding"), "v2")
        assert exc.value.code == CONFLICT
        assert resolve(CredentialKey("embedding")) == "v1"
        store(CredentialKey("embedding"), "v2", replace=True)
        assert resolve(CredentialKey("embedding")) == "v2"

    def test_empty_secret_rejected(self) -> None:
        with pytest.raises(CredentialError) as exc:
            store(CredentialKey("ocr"), "")
        assert exc.value.code == "credential.input_required"

    def test_delete_idempotent(self) -> None:
        store(CredentialKey("ocr"), "x")
        assert delete(CredentialKey("ocr")) is True
        assert delete(CredentialKey("ocr")) is False
        assert status(CredentialKey("ocr")).state == "missing"

    def test_status_never_returns_value(self) -> None:
        store(CredentialKey("ocr"), "super-secret")
        st = status(CredentialKey("ocr"))
        assert st.state == "available"
        assert st.source == "keyring"
        assert st.backend == "FakeKeyring"
        assert "super-secret" not in repr(st)

    def test_keyring_failure_mapping(self) -> None:
        class BoomKeyring:
            class errors:
                class PasswordDeleteError(Exception):
                    pass

            def get_password(self, service: str, username: str) -> str | None:
                raise RuntimeError("no backend available for this platform")

            def set_password(self, service: str, username: str, password: str) -> None:
                raise RuntimeError("no backend available")

            def delete_password(self, service: str, username: str) -> None:
                raise RuntimeError("no backend available")

            def get_keyring(self) -> object:
                return "BoomKeyring"

        c.set_keyring_override(BoomKeyring())
        try:
            st = status(CredentialKey("ocr"))
            assert st.state == "backend_unavailable"
            assert st.remediation_code == "credential.backend_unavailable_remediation"
            with pytest.raises(CredentialError) as exc:
                resolve(CredentialKey("ocr"))
            assert exc.value.code == BACKEND_UNAVAILABLE
        finally:
            c.set_keyring_override(_fake_keyring())


# ── CLI contract ──────────────────────────────────────────────────────────

def _run_cli(*argv: str, stdin: str = "") -> tuple[int, dict]:
    """Run the auth CLI through the real main() dispatch."""
    from paperforge.cli import main

    import io as _io

    old_in, old_out = sys.stdin, sys.stdout
    sys.stdin = _io.StringIO(stdin)
    buf = _io.StringIO()
    sys.stdout = buf
    try:
        rc = main(list(argv))
    finally:
        sys.stdin, sys.stdout = old_in, old_out
    return rc, json.loads(buf.getvalue())


class TestCliContract:
    def test_status_json_shape(self) -> None:
        store(CredentialKey("ocr"), "tok")
        rc, payload = _run_cli("--vault", "/tmp/v", "auth", "status", "ocr", "--json")
        assert rc == 0 and payload["ok"] is True
        assert payload["command"] == "auth.status"
        cred = payload["data"]["credentials"][0]
        assert cred["kind"] == "ocr" and cred["state"] == "available"
        assert cred["source"] == "keyring"
        # never a value
        assert "tok" not in json.dumps(payload)

    def test_status_all_profiles(self) -> None:
        rc, payload = _run_cli("--vault", "/tmp/v", "auth", "status", "--json")
        assert rc == 0
        kinds = {cred["kind"] for cred in payload["data"]["credentials"]}
        assert kinds == {"ocr", "embedding"}

    def test_set_via_stdin(self) -> None:
        rc, payload = _run_cli("--vault", "/tmp/v", "auth", "set", "ocr", "--stdin", "--json", stdin="sekrit\n")
        assert rc == 0
        assert payload["data"]["state"] == "available"
        assert resolve(CredentialKey("ocr")) == "sekrit"

    def test_set_conflict_and_replace(self) -> None:
        store(CredentialKey("ocr"), "old")
        rc, payload = _run_cli("--vault", "/tmp/v", "auth", "set", "ocr", "--stdin", "--json", stdin="new\n")
        assert rc == 1 and payload["error"]["code"] == "credential.conflict"
        rc, payload = _run_cli("--vault", "/tmp/v", "auth", "set", "ocr", "--stdin", "--replace", "--json", stdin="new\n")
        assert rc == 0
        assert resolve(CredentialKey("ocr")) == "new"

    def test_set_empty_stdin_rejected(self) -> None:
        rc, payload = _run_cli("--vault", "/tmp/v", "auth", "set", "ocr", "--stdin", "--json", stdin="\n")
        assert rc == 1 and payload["error"]["code"] == "credential.input_required"

    def test_delete_requires_yes(self) -> None:
        rc, payload = _run_cli("--vault", "/tmp/v", "auth", "delete", "ocr", "--json")
        assert rc == 2 and payload["error"]["code"] == "credential.confirm_required"
        store(CredentialKey("ocr"), "x")
        rc, payload = _run_cli("--vault", "/tmp/v", "auth", "delete", "ocr", "--yes", "--json")
        assert rc == 0 and payload["data"]["deleted"] is True
        assert status(CredentialKey("ocr")).state == "missing"

    def test_delete_with_env_override_warns(self) -> None:
        store(CredentialKey("ocr"), "x")
        rc, payload = _run_cli(
            "--vault", "/tmp/v", "auth", "delete", "ocr", "--yes", "--json",
        )
        # env cleared by the hermetic fixture — no warning expected here
        assert payload["data"]["environment_override_present"] is False

    def test_migrate_environment_dry_run_and_real(self, monkeypatch) -> None:
        monkeypatch.setenv("PADDLEOCR_API_TOKEN", "legacy-tok")
        rc, payload = _run_cli("--vault", "/tmp/v", "auth", "migrate", "--from", "environment", "--dry-run", "--json")
        assert rc == 0
        assert payload["data"]["dry_run"] is True
        assert [m["source_name"] for m in payload["data"]["migrated"]] == ["PADDLEOCR_API_TOKEN"]
        # dry-run never stores
        assert status(CredentialKey("ocr")).state == "missing"

        rc, payload = _run_cli("--vault", "/tmp/v", "auth", "migrate", "--from", "environment", "--json")
        assert rc == 0
        assert resolve(CredentialKey("ocr")) == "legacy-tok"
        # env is never silently deleted — manual cleanup listed
        assert payload["data"]["manual_cleanup"] == ["environment:PADDLEOCR_API_TOKEN"]

    def test_migrate_environment_conflict(self, monkeypatch) -> None:
        store(CredentialKey("ocr"), "durable")
        monkeypatch.setenv("PADDLEOCR_API_TOKEN", "legacy-tok")
        rc, payload = _run_cli("--vault", "/tmp/v", "auth", "migrate", "--from", "environment", "--json")
        assert rc == 1
        assert [m["source_name"] for m in payload["data"]["conflicts"]] == ["PADDLEOCR_API_TOKEN"]
        assert resolve(CredentialKey("ocr")) == "durable"
        rc, payload = _run_cli("--vault", "/tmp/v", "auth", "migrate", "--from", "environment", "--replace", "--json")
        assert rc == 0
        assert resolve(CredentialKey("ocr")) == "legacy-tok"

    def test_migrate_dotenv_scrubs_after_verified_store(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        env_file = vault / ".env"
        env_file.write_text(
            "PADDLEOCR_API_TOKEN=dotenv-tok\nPADDLEOCR_JOB_URL=https://example.com\n",
            encoding="utf-8",
        )
        rc, payload = _run_cli("--vault", str(vault), "auth", "migrate", "--from", "dotenv", "--json")
        assert rc == 0
        assert resolve(CredentialKey("ocr")) == "dotenv-tok"
        # verified store → the .env secret row is scrubbed; non-secret rows stay
        text = env_file.read_text(encoding="utf-8")
        assert "PADDLEOCR_API_TOKEN" not in text
        assert "PADDLEOCR_JOB_URL" in text

    def test_migrate_dotenv_dry_run_never_touches(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        env_file = vault / ".env"
        env_file.write_text("PADDLEOCR_API_TOKEN=dotenv-tok\n", encoding="utf-8")
        rc, payload = _run_cli("--vault", str(vault), "auth", "migrate", "--from", "dotenv", "--dry-run", "--json")
        assert rc == 0
        assert "PADDLEOCR_API_TOKEN" in env_file.read_text(encoding="utf-8")
        assert status(CredentialKey("ocr")).state == "missing"

    def test_no_secret_in_argv_or_output(self) -> None:
        # The secret travels only via stdin; the JSON output must not
        # contain it (masking is a hard contract).
        rc, payload = _run_cli("--vault", "/tmp/v", "auth", "set", "ocr", "--stdin", "--json", stdin="do-not-leak\n")
        assert rc == 0
        assert "do-not-leak" not in json.dumps(payload)


# ── consumers ─────────────────────────────────────────────────────────────

class TestStoreRollback:
    """#173 corrective: the write/verify phase is one transaction — ANY
    failure after the write began restores the prior value or deletes the
    partial write."""

    class _VerifyBoomKeyring:
        class errors:
            class PasswordDeleteError(Exception):
                pass

        def __init__(self) -> None:
            self._d: dict[tuple[str, str], str] = {}
            self._boom_next_get = False

        def get_password(self, service: str, username: str) -> str | None:
            if self._boom_next_get:
                self._boom_next_get = False
                raise RuntimeError("verify read boom")
            return self._d.get((service, username))

        def set_password(self, service: str, username: str, password: str) -> None:
            self._boom_next_get = True  # the verification read throws
            self._d[(service, username)] = password

        def delete_password(self, service: str, username: str) -> None:
            if (service, username) not in self._d:
                raise self.errors.PasswordDeleteError()
            del self._d[(service, username)]

        def get_keyring(self) -> object:
            return "VerifyBoomKeyring"

    def test_verification_failure_restores_prior_value(self) -> None:
        kr = self._VerifyBoomKeyring()
        kr._d[("paperforge", "ocr:default")] = "old-value"
        c.set_keyring_override(kr)
        try:
            with pytest.raises(CredentialError) as exc:
                store(CredentialKey("ocr"), "new-value", replace=True)
            assert exc.value.code == "credential.backend_error"
            assert kr._d[("paperforge", "ocr:default")] == "old-value"
        finally:
            c.set_keyring_override(_fake_keyring())

    def test_verification_failure_deletes_partial_write(self) -> None:
        kr = self._VerifyBoomKeyring()
        c.set_keyring_override(kr)
        try:
            with pytest.raises(CredentialError):
                store(CredentialKey("ocr"), "brand-new")
            assert ("paperforge", "ocr:default") not in kr._d
        finally:
            c.set_keyring_override(_fake_keyring())


class TestFailLoud:
    """#173 corrective: backend faults never degrade into missing-key."""

    class _BoomKeyring:
        class errors:
            class PasswordDeleteError(Exception):
                pass

        def get_password(self, service: str, username: str) -> str | None:
            raise RuntimeError("no backend available for this platform")

        def set_password(self, service: str, username: str, password: str) -> None:
            raise RuntimeError("no backend available")

        def delete_password(self, service: str, username: str) -> None:
            raise RuntimeError("no backend available")

        def get_keyring(self) -> object:
            return "BoomKeyring"

    def test_ocr_resolver_raises_on_backend_fault_not_empty(self, tmp_path: Path) -> None:
        from paperforge.worker.ocr import _resolve_paddleocr_token

        c.set_keyring_override(self._BoomKeyring())
        try:
            with pytest.raises(CredentialError) as exc:
                _resolve_paddleocr_token(tmp_path)
            assert exc.value.code == BACKEND_UNAVAILABLE
        finally:
            c.set_keyring_override(_fake_keyring())

    def test_embedding_resolver_raises_on_backend_fault_not_empty(self, tmp_path: Path) -> None:
        from paperforge.embedding._config import get_api_key

        c.set_keyring_override(self._BoomKeyring())
        try:
            with pytest.raises(CredentialError) as exc:
                get_api_key(tmp_path)
            assert exc.value.code == BACKEND_UNAVAILABLE
        finally:
            c.set_keyring_override(_fake_keyring())

    def test_preflight_distinguishes_backend_fault_from_missing(self, tmp_path: Path) -> None:
        from paperforge.embedding.preflight import _preflight_check

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        c.set_keyring_override(self._BoomKeyring())
        try:
            result = _preflight_check(vault)
            assert result["ok"] is False
            assert "unavailable" in result["error"]
            assert "API key not configured" not in result["error"]
        finally:
            c.set_keyring_override(_fake_keyring())

    def test_ocr_diagnostics_raise_on_backend_fault(self) -> None:
        from paperforge.ocr_diagnostics import ocr_doctor

        c.set_keyring_override(self._BoomKeyring())
        try:
            with pytest.raises(CredentialError) as exc:
                ocr_doctor(config=None, live=False)
            assert exc.value.code == BACKEND_UNAVAILABLE
        finally:
            c.set_keyring_override(_fake_keyring())


    def test_ocr_diagnose_backend_fault_text_mode(self, monkeypatch, capsys, tmp_path: Path) -> None:
        """`ocr --diagnose` reports a backend fault as a diagnostic finding —
        never a crash, never a missing-key disguise."""
        from paperforge.commands.ocr import _diagnose
        from paperforge.credentials import CredentialError

        def boom(config=None, live=False):
            raise CredentialError("credential.backend_unavailable", "no secure backend")

        monkeypatch.setattr("paperforge.ocr_diagnostics.ocr_doctor", boom)
        rc = _diagnose(tmp_path)
        out = capsys.readouterr().out
        assert rc == 1
        assert "OCR Doctor" in out
        assert "backend_unavailable" in out
        assert "auth status ocr" in out


class TestConsumers:
    def test_ocr_token_resolver_uses_authority(self, monkeypatch, tmp_path: Path) -> None:
        from paperforge.worker.ocr import _resolve_paddleocr_token

        assert _resolve_paddleocr_token(tmp_path) == ""  # missing
        monkeypatch.setenv(CANON_OCR, "env-tok")
        assert _resolve_paddleocr_token(tmp_path) == "env-tok"
        store(CredentialKey("ocr"), "keyring-tok")
        monkeypatch.delenv(CANON_OCR, raising=False)
        assert _resolve_paddleocr_token(tmp_path) == "keyring-tok"

    def test_embedding_key_resolver_uses_authority(self, monkeypatch, tmp_path: Path) -> None:
        from paperforge.embedding._config import get_api_key

        assert get_api_key(tmp_path) == ""
        monkeypatch.setenv(CANON_EMB, "emb-tok")
        assert get_api_key(tmp_path) == "emb-tok"

    def test_probe_ocr_credential_gate_is_status(self, monkeypatch, tmp_path: Path) -> None:
        """probe_ocr's readiness gate reads the authority status — with a
        hermetic missing credential the envelope is missing_input, and with
        the canonical env it reaches the ready tail."""
        from paperforge.commands.probe import probe_ocr

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")

        class HealthyRow:
            status = "done"
            health = "green"
            display_action = "none"

        monkeypatch.setattr(
            "paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda v: [HealthyRow()],
        )
        monkeypatch.setattr("paperforge.ocr_diagnostics.ocr_doctor", lambda config=None, live=False: {"passed": True})

        env = probe_ocr(vault)
        assert env["reason"]["code"] == "ocr.api_key_missing"
        monkeypatch.setenv(CANON_OCR, "test-token")
        env = probe_ocr(vault)
        assert env["capability_state"] == "ready"
        assert env["reason"]["code"] == "ocr.ready"

    def test_preflight_uses_authority(self, monkeypatch, tmp_path: Path) -> None:
        from paperforge.embedding.preflight import _preflight_check

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        monkeypatch.setenv(CANON_EMB, "emb-tok")
        # The fix must mention the auth command, never legacy env names.
        result = _preflight_check(vault)
        fix = str(result.get("fix", "")) if isinstance(result, dict) else ""
        assert "auth set embedding" in fix or result.get("ok") is not False
