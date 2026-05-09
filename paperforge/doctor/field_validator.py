"""Field registry validation — used by paperforge doctor to detect state drift."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_entry_fields(
    entry: dict,
    owner: str,
    registry: dict,
    entry_label: str = "",
) -> list[dict]:
    """Validate a single entry's fields against the field registry.

    Returns list of issues, each with:
    - severity: "error" | "warning" | "info"
    - code: "MISSING_REQUIRED" | "UNKNOWN_FIELD" | "DRIFT" | "TYPE_MISMATCH"
    - message: human-readable description
    - field: field name
    """
    issues = []
    owner_fields = registry.get(owner, {})

    if not owner_fields:
        return issues

    # Check 1: Required fields present
    for field_name, meta in owner_fields.items():
        if meta.get("required", False) and field_name not in entry:
            issues.append({
                "severity": "error",
                "code": "MISSING_REQUIRED",
                "field": field_name,
                "message": f"Missing required field '{field_name}' in {owner} entry{(' (' + entry_label + ')') if entry_label else ''}",
                "suggestion": f"Add '{field_name}' to the entry with appropriate value ({meta.get('type', 'str')})",
            })
        elif not meta.get("required", True) and field_name not in entry:
            issues.append({
                "severity": "info",
                "code": "MISSING_OPTIONAL",
                "field": field_name,
                "message": f"Missing optional field '{field_name}' in {owner} entry{(' (' + entry_label + ')') if entry_label else ''}",
            })

    # Check 2: Unknown fields (drift detection)
    known_fields = set(owner_fields.keys())
    for key in entry:
        if key not in known_fields:
            issues.append({
                "severity": "warning",
                "code": "DRIFT",
                "field": key,
                "message": f"Unknown field '{key}' in {owner} entry{(' (' + entry_label + ')') if entry_label else ''} — not in field registry",
                "suggestion": f"Either remove '{key}' or add it to field_registry.yaml under '{owner}'",
            })

    return issues


def validate_collection(
    entries: list[dict],
    owner: str,
    registry: dict,
) -> dict:
    """Validate a collection of entries against field registry.

    Returns aggregate diagnostics:
    - total_entries: int
    - entries_with_errors: int
    - entries_with_warnings: int
    - issues: list[dict] (all individual issues)
    - summary: dict (per-code counts)
    - summary_text: str (human-readable)
    """
    all_issues = []
    error_entries = set()
    warning_entries = set()

    for i, entry in enumerate(entries):
        label = entry.get("zotero_key", f"entry_{i}")
        issues = validate_entry_fields(entry, owner, registry, label)
        has_error = False
        has_warning = False
        for issue in issues:
            all_issues.append(issue)
            if issue["severity"] == "error":
                has_error = True
            elif issue["severity"] == "warning":
                has_warning = True
        if has_error:
            error_entries.add(label)
        if has_warning:
            warning_entries.add(label)

    # Summary
    code_counts: dict[str, int] = {}
    for issue in all_issues:
        code = issue["code"]
        code_counts[code] = code_counts.get(code, 0) + 1

    lines = []
    if all_issues:
        lines.append(f"Found {len(all_issues)} field issue(s) across {len(entries)} {owner} entries:")
        lines.append(f"  Entries with errors: {len(error_entries)}")
        lines.append(f"  Entries with warnings: {len(warning_entries)}")
        for code, count in sorted(code_counts.items()):
            lines.append(f"  {code}: {count}")
    else:
        lines.append(f"All {len(entries)} {owner} entries are valid against field registry.")

    # Add per-entry details for actionable items
    if all_issues:
        lines.append("")
        lines.append("Details:")
        for issue in all_issues[:20]:  # cap display
            lines.append(f"  [{issue['severity'].upper()}] {issue['message']}")
            if issue.get("suggestion"):
                lines.append(f"    Suggestion: {issue['suggestion']}")
        if len(all_issues) > 20:
            lines.append(f"  ... and {len(all_issues) - 20} more issues")

    return {
        "total_entries": len(entries),
        "entries_with_errors": len(error_entries),
        "entries_with_warnings": len(warning_entries),
        "issues": all_issues,
        "summary": code_counts,
        "summary_text": "\n".join(lines),
    }


def validate_frontmatter_from_file(
    file_path: Path,
    registry: dict,
) -> list[dict]:
    """Read a single formal note and validate its frontmatter against registry."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception:
        return [{"severity": "error", "code": "READ_ERROR", "field": "", "message": f"Cannot read {file_path}"}]

    # Parse frontmatter
    import re
    fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not fm_match:
        return [{"severity": "warning", "code": "NO_FRONTMATTER", "field": "", "message": f"No frontmatter found in {file_path.name}"}]

    frontmatter = {}
    for line in fm_match.group(1).splitlines():
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            frontmatter[key.strip()] = val.strip()

    return validate_entry_fields(frontmatter, "frontmatter", registry, file_path.stem)
