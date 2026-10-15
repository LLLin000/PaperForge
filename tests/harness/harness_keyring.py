"""Isolated keyring backend for the harness - never the developer's real store.

A credential case that ran against the machine's keyring would read (and could
clobber) the tokens of whoever executes the suite, and "the secret reaches the
keyring, never the vault" would be untestable.  Child processes select this
backend through ``PAPERFORGE_KEYRING_BACKEND`` (mapped to
``PYTHON_KEYRING_BACKEND`` by paperforge.credentials) and point it at a file the
harness fixture owns.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from keyring.backend import KeyringBackend

ENV_FILE = "PAPERFORGE_HARNESS_KEYRING_FILE"


class Keyring(KeyringBackend):
    """A JSON file standing in for the OS credential store."""

    priority: float = 1.0

    def _path(self) -> Path:
        value = os.environ.get(ENV_FILE, "").strip()
        if not value:
            raise RuntimeError(f"{ENV_FILE} is required")
        return Path(value)

    def _read(self) -> dict[str, str]:
        path = self._path()
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        return {
            str(key): str(value)
            for key, value in payload.items()
            if isinstance(key, str) and isinstance(value, str)
        }

    def _write(self, values: dict[str, str]) -> None:
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def get_password(self, service: str, username: str) -> str | None:
        return self._read().get(f"{service}:{username}")

    def set_password(self, service: str, username: str, password: str) -> None:
        values = self._read()
        values[f"{service}:{username}"] = password
        self._write(values)

    def delete_password(self, service: str, username: str) -> None:
        values = self._read()
        values.pop(f"{service}:{username}", None)
        self._write(values)
