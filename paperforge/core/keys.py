"""Canonical paper-key normalization (P0-4, owner review 2026-08-16).

Windows scripts and paste commonly smuggle ``\\r``, a BOM, blank lines, or
duplicate keys into key lists; the 709-paper recovery repeatedly hit keys
that were silently dropped (``ABC12345\\r`` never matched, ``cat``
concatenation merged lines into 16-char fragments).  Every consumer
(action scope, ocr run, rebuild, …) must see the same canonical keys, so
the cleaning lives here once instead of in every worker.
"""

from __future__ import annotations


def normalize_paper_keys(raw: object, *, known_keys: set[str] | None = None) -> list[str]:
    """Canonicalize a key list from any common source.

    Accepts a string / bytes (whitespace, comma, or newline separated), or
    an iterable of keys.  Decodes UTF-8-SIG (a BOM is tolerated), strips
    each token, drops empties and trailing ``\\r``, and dedupes stably.
    When ``known_keys`` is given, tokens absent from it are DROPPED
    (canonical membership validation — a stray fragment must never reach
    a worker and fail with ``unknown paper keys``).
    """
    tokens: list[str] = []
    if isinstance(raw, (str, bytes)):
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8-sig", errors="replace")
        text = raw.lstrip("\ufeff")
        tokens = [t.strip() for t in text.replace(",", " ").split()]
    else:
        items = raw if isinstance(raw, (list, tuple, set, frozenset)) else []
        for item in items:
            if isinstance(item, (str, bytes)):
                tokens.extend(normalize_paper_keys(item))
            elif item:
                tokens.append(str(item).strip())
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        t = t.strip().rstrip("\r")
        if not t or t in seen:
            continue
        if known_keys is not None and t not in known_keys:
            continue
        seen.add(t)
        out.append(t)
    return out
