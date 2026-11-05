"""Machine-wide PaperForge runtime pointer, published only by the external installer.

`~/.paperforge/runtime/pointer.json` is the machine-wide rendezvous point:

    {
      "schema_version": 1,
      "python_path": "<absolute executable>",
      "environment_root": "<managed candidate environment>",
      "paperforge_version": "<version>"
    }

- Only `paperforge runtime install|update|repair` publishes the pointer, after
  candidate version and dependency verification.
- Vault setup never publishes or mutates this pointer; Obsidian is a reader.
- Failed candidates leave the currently published runtime untouched.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

POINTER_SCHEMA_VERSION = 1
POINTER_FILENAME = "pointer.json"

DEFAULT_ENVIRONMENT_ROOT_NAME = "runtime"
DEFAULT_HOME_DIR_NAME = ".paperforge"


def pointer_dir(home: Path | None = None) -> Path:
    """~/.paperforge/runtime — the canonical pointer directory."""
    base = home or Path.home()
    return base / DEFAULT_HOME_DIR_NAME / DEFAULT_ENVIRONMENT_ROOT_NAME


def pointer_path(home: Path | None = None) -> Path:
    return pointer_dir(home) / POINTER_FILENAME


def read_pointer(home: Path | None = None) -> dict | None:
    """Read the published pointer; None when absent or invalid (reader
    never crashes on a half-written pointer — the writer is atomic).

    Schema v1 requires ALL four fields, typed, non-empty, with absolute
    paths for python_path and environment_root; unknown additive fields
    are ignored."""
    path = pointer_path(home)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict) or raw.get("schema_version") != POINTER_SCHEMA_VERSION:
        return None
    for key in ("python_path", "environment_root", "paperforge_version"):
        value = raw.get(key)
        if not isinstance(value, str) or not value:
            return None
    if not Path(raw["python_path"]).is_absolute():
        return None
    if not Path(raw["environment_root"]).is_absolute():
        return None
    return raw


def publish_pointer(
    *,
    python_path: str | None = None,
    environment_root: str | None = None,
    paperforge_version: str | None = None,
    home: Path | None = None,
) -> Path:
    """Atomically publish the runtime pointer (tmp + os.replace) — the ONLY
    writer (#143).  Defaults: the running interpreter, its environment root,
    and the installed PaperForge version."""
    from paperforge import __version__

    payload = {
        "schema_version": POINTER_SCHEMA_VERSION,
        "python_path": python_path or sys.executable,
        "environment_root": environment_root or str(
            Path(sys.prefix)
        ),
        "paperforge_version": paperforge_version or __version__,
    }
    path = pointer_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(str(tmp), str(path))
    return path
