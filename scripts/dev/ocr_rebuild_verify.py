"""
Rebuild and verify OCR regression papers.

Usage:
    PAPERFORGE_REAL_OCR_VAULT=/path/to/vault \
    PAPERFORGE_REAL_OCR_KEYS=SAN9AYVR,2GN9LMCW,7C8829BD \
    python scripts/dev/ocr_rebuild_verify.py
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from pathlib import Path

from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys


BIOGRAPHY_PATTERNS = [
    r"Dr\s+Qiang\s+Zhang",
    r"Xingcan\s+Huang",
    r"integrate technologies of tissue engineering",
    r"published over 40 papers",
    r"He has published",
    r"She has published",
    r"Dr\.\s+\w+\s+\w+\s+is\s+(?:a|an)\s+(?:Professor|professor|Associate|associate)",
    r"\bis\s+(?:a|an)\s+(?:Professor|professor|Research|researcher)\s+(?:at|of|in|and)",
    r"His research interests include",
    r"Her research interests include",
    r"received (?:his|her)\s+(?:PhD|Ph\.D\.|B\.S\.|M\.S\.)",
    r"has published over \d+",
]

AUTHOR_LINE_PATTERNS = [
    r"Dr\.?\s+Qiang\s+Zhang",
    r"Xingcan\s+Huang",
]

MATH_SPACING_ANOMALY = re.compile(r"\$\s+[^$]+\s+\$")
DEFAULT_KEYS = ["SAN9AYVR", "2GN9LMCW", "7C8829BD"]


def _parse_keys(raw: str) -> list[str]:
    keys = [item.strip() for item in raw.replace(";", ",").split(",")]
    return [k for k in keys if k]


def _resolve_config() -> tuple[Path, list[str]]:
    vault_raw = os.environ.get("PAPERFORGE_REAL_OCR_VAULT", "").strip()
    keys_raw = os.environ.get("PAPERFORGE_REAL_OCR_KEYS", "").strip()
    if not vault_raw:
        raise SystemExit("PAPERFORGE_REAL_OCR_VAULT is required")
    vault = Path(vault_raw)
    if not vault.exists():
        raise SystemExit(f"Vault path does not exist: {vault}")
    keys = _parse_keys(keys_raw) or DEFAULT_KEYS
    return vault, keys


def check_author_bio_clean(fulltext: str, paper_key: str) -> list[str]:
    issues = []
    for pattern in BIOGRAPHY_PATTERNS:
        matches = re.finditer(pattern, fulltext, re.IGNORECASE)
        for m in matches:
            start = max(0, m.start() - 60)
            end = min(len(fulltext), m.end() + 60)
            context = fulltext[start:end].replace("\n", " ")
            issues.append(f"  BIO HIT [{paper_key}]: '{pattern}' -> ...{context}...")
    return issues


def check_author_line(fulltext: str, paper_key: str) -> list[str]:
    issues = []
    for pattern in AUTHOR_LINE_PATTERNS:
        matches = list(re.finditer(pattern, fulltext, re.IGNORECASE))
        if matches:
            issues.append(f"  AUTHOR LINE [{paper_key}]: '{pattern}' found {len(matches)} time(s)")
    return issues


def check_math_spacing(fulltext: str, paper_key: str) -> list[str]:
    issues = []
    for m in MATH_SPACING_ANOMALY.finditer(fulltext):
        if len(m.group()) > 80:
            continue
        start = max(0, m.start() - 20)
        end = min(len(fulltext), m.end() + 20)
        context = fulltext[start:end].replace("\n", " ")
        issues.append(f"  MATH SPACE [{paper_key}]: '{m.group()}' in context ...{context}...")
    return issues


def check_glued_math(fulltext: str, paper_key: str) -> list[str]:
    issues = []
    glued_patterns = [
        re.compile(r"[a-z]\$[0-9\\]"),
        re.compile(r"\$[0-9\\][a-z]"),
    ]
    for p in glued_patterns:
        for m in p.finditer(fulltext):
            start = max(0, m.start() - 30)
            end = min(len(fulltext), m.end() + 30)
            context = fulltext[start:end].replace("\n", " ")
            issues.append(f"  GLUED MATH [{paper_key}]: '{m.group()}' in ...{context}...")
    return issues


def check_metadata_authors(meta_path: Path) -> list[str]:
    if not meta_path.exists():
        return ["  META MISSING: resolved_metadata.json not found"]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    authors = meta.get("authors", meta.get("author", []))
    if not authors:
        return ["  META WARN: no authors found in resolved_metadata.json"]
    issues = []
    author_str = json.dumps(authors, ensure_ascii=False)
    bio_names = ["Qiang Zhang", "Xingcan Huang"]
    for name in bio_names:
        if name in author_str:
            issues.append(f"  META BIO NAME: '{name}' found in authors list")
    return issues


def verify_paper(vault: Path, key: str, issues: list[str]) -> int:
    paper_root = vault / "System" / "PaperForge" / "ocr" / key
    fulltext_path = paper_root / "fulltext.md"
    meta_path = paper_root / "metadata" / "resolved_metadata.json"
    figures_dir = paper_root / "render" / "figures"
    tables_dir = paper_root / "render" / "tables"

    count = 0
    if fulltext_path.exists():
        text = fulltext_path.read_text(encoding="utf-8", errors="replace")
        bio = check_author_bio_clean(text, key)
        issues.extend(bio)
        count += len(bio)
        al = check_author_line(text, key)
        issues.extend(al)
        count += len(al)
        ms = check_math_spacing(text, key)
        issues.extend(ms)
        count += len(ms)
        gm = check_glued_math(text, key)
        issues.extend(gm)
        count += len(gm)
    else:
        issues.append(f"  [!] fulltext.md not found for {key}")
        count += 1

    meta_issues = check_metadata_authors(meta_path)
    issues.extend(meta_issues)
    count += len(meta_issues)

    if figures_dir.exists():
        for fpath in sorted(figures_dir.glob("*.md")):
            text = fpath.read_text(encoding="utf-8", errors="replace")
            ms = check_math_spacing(text, f"{key}/{fpath.name}")
            issues.extend(ms)
            count += len(ms)

    if tables_dir.exists():
        for fpath in sorted(tables_dir.glob("*.md")):
            text = fpath.read_text(encoding="utf-8", errors="replace")
            ms = check_math_spacing(text, f"{key}/{fpath.name}")
            issues.extend(ms)
            count += len(ms)

    return count


def summary_line(key: str, success: bool, details: str = "") -> str:
    icon = "[OK]" if success else "[!!]"
    return f"  {icon} {key}{': ' + details if details else ''}"


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    vault, keys = _resolve_config()

    print("=" * 70)
    print("  OCR FINAL POLISH - REBUILD AND VERIFY")
    print("=" * 70)

    all_issues: dict[str, list[str]] = {}
    all_pass = True

    for key in keys:
        print(f"\n--- Rebuilding {key} ---")
        result = run_derived_rebuild_for_keys(vault, [key])
        print(f"  Rebuild result: {json.dumps(result)}")

    for key in keys:
        print(f"\n--- Verifying {key} ---")
        issues: list[str] = []
        count = verify_paper(vault, key, issues)
        all_issues[key] = issues

        paper_ok = count == 0
        if paper_ok:
            print(summary_line(key, True, "all checks passed"))
        else:
            print(summary_line(key, False, f"{count} issue(s)"))
            for iss in issues:
                print(iss)
        if not paper_ok:
            all_pass = False

    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    for key in keys:
        ics = all_issues.get(key, [])
        status = "PASS" if len(ics) == 0 else "FAIL"
        print(f"  [{status}] {key}: {len(ics)} issues")
        for iss in ics:
            print(f"         {iss}")

    print(f"\n  Overall: {'ALL PASS' if all_pass else 'SOME FAILED'}")
    if not all_pass:
        sys.exit(1)
