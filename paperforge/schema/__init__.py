"""Field registry: schema definitions for all field-carrying structures."""

from __future__ import annotations

from pathlib import Path


def load_field_registry(path: Path | None = None) -> dict:
    """Load field registry from YAML file.

    Returns nested dict: {owner: {field: {type, required, public, description}}}
    """
    import yaml

    if path is None:
        path = Path(__file__).resolve().parent / "field_registry.yaml"

    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data if isinstance(data, dict) else {}


def get_owner_fields(registry: dict, owner: str) -> dict:
    """Get all field definitions for a given owner."""
    return registry.get(owner, {})


def get_field_info(registry: dict, owner: str, field_name: str) -> dict | None:
    """Get metadata for a specific field in an owner."""
    owner_fields = get_owner_fields(registry, owner)
    return owner_fields.get(field_name)
