"""A05 — credentials reach the keyring, never argv, never the vault.

Ported from the H case that saves a key in Settings.  Two properties matter and
both are file-level facts here:

* the secret is stored in the keyring (this case's isolated backend, so the
  machine's real credential store is never read or written);
* the secret appears in **no** file inside the vault and in **no** argv — the
  repository's stdin-only credential contract.

The native-keyring question (Windows Credential Manager behaviour, locked
stores) stays an owner/W20 item; this case proves the authority seam.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.harness

CASE_ID = "A05"
TITLE = "A credential lands in the keyring, never in argv or the vault"
HOST_SPEC_CASE = (
    "A05 credential storage: a key saved in Settings reaches the keyring — never "
    "config/vault — and clearing it disables the gated action"
)

SECRET = "pf-harness-secret-3f9a1c7e"


def _status(cli) -> dict:
    result = cli.json("auth", "status", "ocr")
    data = result.data if isinstance(result.data, dict) else {}
    rows = data.get("credentials")
    if isinstance(rows, list) and rows:
        return rows[0]
    return data


def test_secret_reaches_the_keyring_only(cli, vault, case) -> None:
    stored = cli.json("auth", "set", "ocr", "--stdin", "--replace", stdin=f"{SECRET}\n")
    case.check("auth set exits 0", stored.returncode == 0, stored.tail())

    status = _status(cli)
    case.check(
        "the credential is available from the keyring",
        status.get("state") == "available" and status.get("source") == "keyring",
        str(status)[:300],
    )

    store = vault.parent / f"{vault.name}-keyring.json"
    case.check(
        "the isolated keyring holds the secret",
        store.is_file() and SECRET in store.read_text(encoding="utf-8"),
        f"{store.name} exists={store.is_file()}",
    )

    # The contract that keeps secrets out of logs and process listings.
    argv_leak = [
        command["argv"]
        for command in case.commands
        if any(SECRET in str(part) for part in command["argv"])
    ]
    case.check("the secret never appears in argv", not argv_leak, str(argv_leak)[:200])

    offenders = []
    for path in sorted(vault.rglob("*")):
        if not path.is_file() or path.suffix in {".jpg", ".png", ".pdf"}:
            continue
        try:
            if SECRET in path.read_text(encoding="utf-8", errors="ignore"):
                offenders.append(path.relative_to(vault).as_posix())
        except OSError:
            continue
    case.check("the secret appears in no vault file", not offenders, str(offenders)[:200])

    cleared = cli.json("auth", "delete", "ocr", "--yes", expect=None)
    case.check("auth delete exits 0", cleared.returncode == 0, cleared.tail())
    after = _status(cli)
    case.check(
        "the credential is gone from the keyring",
        after.get("source") != "keyring" or after.get("state") != "available",
        str(after)[:300],
    )

    case.artifact("keyring-store", store)
    case.artifact("vault-digest", vault / "Resources")
