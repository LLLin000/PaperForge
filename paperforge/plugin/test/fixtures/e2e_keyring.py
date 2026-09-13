"""Ephemeral keyring backend for the real-provider E2E test only."""

from __future__ import annotations

import json
import os
from pathlib import Path

from keyring.backend import KeyringBackend


class Keyring(KeyringBackend):
    priority: float = 1.0

    def _path(self) -> Path:
        value = os.environ.get("PAPERFORGE_E2E_KEYRING_FILE", "").strip()
        if not value:
            raise RuntimeError("PAPERFORGE_E2E_KEYRING_FILE is required")
        return Path(value)

    def _read(self) -> dict[str, str]:
        path = self._path()
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}
        return {
            str(key): str(value)
            for key, value in payload.items()
            if isinstance(key, str) and isinstance(value, str)
        }

    def get_password(self, service: str, username: str) -> str | None:
        return self._read().get(f"{service}:{username}")

    def set_password(self, service: str, username: str, password: str) -> None:
        path = self._path()
        values = self._read()
        values[f"{service}:{username}"] = password
        _ = path.write_text(json.dumps(values), encoding="utf-8")

    def delete_password(self, service: str, username: str) -> None:
        path = self._path()
        values = self._read()
        _ = values.pop(f"{service}:{username}", None)
        _ = path.write_text(json.dumps(values), encoding="utf-8")
