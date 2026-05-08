"""Shared helpers for CLI contract tests — normalization, shape assertions."""

from __future__ import annotations

import json
import re
from pathlib import Path


def normalize_snapshot(output: str, vault_path: str | None = None) -> str:
    """Normalize dynamic fields in CLI output for snapshot comparison.

    Replaces:
    - Absolute vault paths with '<VAULT>'
    - ISO timestamps with '<TIMESTAMP>'
    - Version strings with '<VERSION>'
    - UUIDs with '<UUID>'

    Args:
        output: Raw CLI output string (stdout)
        vault_path: Optional vault path to normalize

    Returns:
        Normalized output string ready for snapshot comparison
    """
    result = output

    # Normalize vault paths (absolute paths containing /tmp/ or \\tmp\\)
    if vault_path:
        escaped = re.escape(str(vault_path))
        result = re.sub(escaped, "<VAULT>", result)

    # Fallback: any path containing /tmp/pf_vault_ (Unix) or pf_vault_ (Windows)
    result = re.sub(r'/tmp/pf_vault_[^/\s"\']+', "<VAULT>", result)
    result = re.sub(r'\\\\temp\\\\pf_vault_[^\\\\\s"\']+', "<VAULT>", result)
    # Broader: any string ending in pf_vault_XXXXX as a path component
    result = re.sub(r'[A-Za-z]:[\\/][^\s"\']*pf_vault_[a-z0-9]+', "<VAULT>", result)

    # Normalize ISO timestamps: 2026-05-08T12:34:56.789012+00:00
    result = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?[+-]\d{2}:\d{2}",
        "<TIMESTAMP>",
        result,
    )

    # Normalize version strings in JSON: "version": "x.y.z" or "x.y.zrcN"
    result = re.sub(
        r'"version":\s*"\d+\.\d+\.\d+[^"]*"', '"version": "<VERSION>"', result
    )
    result = re.sub(
        r'"paperforge_version":\s*"\d+\.\d+\.\d+[^"]*"',
        '"paperforge_version": "<VERSION>"',
        result,
    )
    result = re.sub(
        r'"format_version":\s*"\d+\.\d+\.\d+[^"]*"',
        '"format_version": "<VERSION>"',
        result,
    )

    # Normalize _generated_at in context output
    result = re.sub(
        r'"_generated_at":\s*"[^"]*"', '"_generated_at": "<TIMESTAMP>"', result
    )

    return result


def assert_valid_json(output: str) -> dict:
    """Assert that output is valid JSON and return the parsed dict."""
    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"Output is not valid JSON: {e}\n---\n{output[:500]}"
        )


def assert_json_shape(
    data: dict,
    required_keys: set[str],
    optional_keys: set[str] | None = None,
):
    """Assert that a JSON object has the expected shape (required keys present)."""
    optional = optional_keys or set()
    all_allowed = required_keys | optional
    missing = required_keys - set(data.keys())
    extra = set(data.keys()) - all_allowed
    errors: list[str] = []
    if missing:
        errors.append(f"Missing required keys: {missing}")
    if extra:
        errors.append(f"Unexpected keys: {extra}")
    if errors:
        raise AssertionError("; ".join(errors))
