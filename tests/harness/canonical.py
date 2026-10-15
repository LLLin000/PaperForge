"""Reading canonical artifacts of a case's vault (no product imports)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def frontmatter(note: Path) -> dict[str, Any]:
    """The YAML frontmatter of a formal note ({} when there is none)."""
    parts = note.read_text(encoding="utf-8").split("---", 2)
    if len(parts) < 3:
        return {}
    import yaml

    value = yaml.safe_load(parts[1])
    return value if isinstance(value, dict) else {}


def formal_notes(vault: Path) -> list[Path]:
    """Every formal note, wherever the workspace layout put it."""
    return sorted((vault / "Resources" / "Literature").rglob("*.md"))


def vault_config(vault: Path) -> dict[str, Any]:
    """The canonical config document (paperforge.json)."""
    import json

    path = vault / "paperforge.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}
