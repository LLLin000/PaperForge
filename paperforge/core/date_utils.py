from __future__ import annotations

import re


def extract_year(value: str) -> str:
    """Extract a 4-digit year (19xx or 20xx) from a date string.

    Returns empty string if no year found.

    Examples:
        extract_year("2024-03-15") -> "2024"
        extract_year("March 2023") -> "2023"
        extract_year("n.d.") -> ""
    """
    match = re.search(r"(19|20)\d{2}", value or "")
    return match.group(0) if match else ""
