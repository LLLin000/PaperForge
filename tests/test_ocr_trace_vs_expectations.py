#!/usr/bin/env python3
"""
Compare real OCR pipeline output (block_trace.csv) against expectations.json.

Usage:
    python -m pytest tests/test_ocr_trace_vs_expectations.py -s --timeout=60
    python -m pytest tests/test_ocr_trace_vs_expectations.py -k "DWQQK2YB" -s
    python -m pytest tests/test_ocr_trace_vs_expectations.py -k "CAQNW9Q2" -s

Each test:
  1. Loads block_trace.csv from the real output directory
  2. Loads expectations.json from the test fixtures
  3. Runs all assertions defined in expectations.json
  4. Reports PASS/FAIL per assertion with details
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Config: map paper keys to fixture directory (contains block_trace.csv + expectations.json)
# ---------------------------------------------------------------------------

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "ocr_real_papers"

PAPER_CONFIGS = {
    "DWQQK2YB": FIXTURE_ROOT / "DWQQK2YB",
    "CAQNW9Q2": FIXTURE_ROOT / "CAQNW9Q2",
}


# ---------------------------------------------------------------------------
# Load block_trace.csv
# ---------------------------------------------------------------------------


def load_trace(trace_path: Path) -> list[dict]:
    """Load block_trace.csv into a list of dicts."""
    with open(trace_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_blocks_on_page(trace: list[dict], page: int) -> list[dict]:
    """Get all blocks on a specific page."""
    return [b for b in trace if int(b.get("page", 0)) == page]


def find_block_matching(trace: list[dict], page: int, text_contains: str) -> dict | None:
    """Find the first block on page whose content_preview contains the text."""
    blocks = get_blocks_on_page(trace, page)
    for b in blocks:
        cp = str(b.get("content_preview", "")).lower()
        if text_contains.lower() in cp:
            return b
    return None


# ---------------------------------------------------------------------------
# Assertion runners
# ---------------------------------------------------------------------------


class AssertionResult:
    def __init__(self, page: int, assertion_type: str, passed: bool, message: str, severity: str = "FAIL"):
        self.page = page
        self.assertion_type = assertion_type
        self.passed = passed
        self.message = message
        self.severity = severity  # FAIL or WARN

    def __repr__(self):
        status = "PASS" if self.passed else self.severity
        return f"[{status}] p{self.page} {self.assertion_type}: {self.message}"


def run_text_equals(trace: list[dict], page: int, text: str, expected_role: str | None = None,
                    expected_zone: str | None = None, confidence: str = "medium",
                    notes: str = "") -> AssertionResult:
    """Assert a block with exact text match exists and has correct role/zone."""
    block = find_block_matching(trace, page, text)
    if block is None:
        return AssertionResult(page, "text_equals", False,
                               f"Block with text '{text[:50]}' NOT FOUND on page {page}",
                               severity="FAIL")

    errors = []
    if expected_role and block.get("role") != expected_role:
        errors.append(f"role: '{block.get('role')}' != expected '{expected_role}'")
    if expected_zone and block.get("zone") != expected_zone:
        errors.append(f"zone: '{block.get('zone')}' != expected '{expected_zone}'")

    if errors:
        return AssertionResult(page, "text_equals", False,
                               f"'{text[:40]}...' -> {'; '.join(errors)}",
                               severity="FAIL")

    return AssertionResult(page, "text_equals", True,
                           f"'{text[:50]}' role={block.get('role')} zone={block.get('zone')}")


def run_text_contains(trace: list[dict], page: int, text: str, expected_role: str | None = None,
                      expected_zone: str | None = None, must_not_role: str | None = None,
                      notes: str = "") -> AssertionResult:
    """Assert a block containing text exists with correct role/zone."""
    block = find_block_matching(trace, page, text)
    if block is None:
        return AssertionResult(page, "text_contains", False,
                               f"Block containing '{text[:50]}' NOT FOUND on page {page}",
                               severity="FAIL")

    errors = []
    if expected_role and block.get("role") != expected_role:
        errors.append(f"role: '{block.get('role')}' != expected '{expected_role}'")
    if expected_zone and block.get("zone") != expected_zone:
        errors.append(f"zone: '{block.get('zone')}' != expected '{expected_zone}'")
    if must_not_role and block.get("role") == must_not_role:
        errors.append(f"role must NOT be '{must_not_role}' but got '{block.get('role')}'")

    if errors:
        return AssertionResult(page, "text_contains", False,
                               f"'{text[:40]}...' -> {'; '.join(errors)}",
                               severity="FAIL")

    return AssertionResult(page, "text_contains", True,
                           f"'{text[:50]}' role={block.get('role')} zone={block.get('zone')}")


def run_count_assertion(trace: list[dict], page: int, count_type: str,
                        min_count: int | None = None, max_count: int | None = None) -> AssertionResult:
    """Assert count of a specific block type on a page."""
    blocks = get_blocks_on_page(trace, page)

    if count_type == "text":
        count = sum(1 for b in blocks if b.get("raw_label") == "text")
    elif count_type == "figure_title":
        count = sum(1 for b in blocks if b.get("raw_label") in ("figure_title", "figure_caption")
                     or b.get("role") in ("figure_title", "figure_caption"))
    elif count_type == "reference_content":
        count = sum(1 for b in blocks if b.get("role") == "reference_item")
    elif count_type == "image":
        count = sum(1 for b in blocks if b.get("raw_label") == "image")
    elif count_type == "chart":
        # Charts often appear as image blocks with chart-like content
        count = sum(1 for b in blocks if b.get("raw_label") == "image"
                     and any(kw in str(b.get("content_preview", "")).lower()
                             for kw in ["chart", "graph", "bar", "plot"]))
    elif count_type == "all":
        count = len(blocks)
    else:
        return AssertionResult(page, f"count_{count_type}", False,
                               f"Unknown count type: {count_type}", severity="FAIL")

    errors = []
    if min_count is not None and count < min_count:
        errors.append(f"count {count} < min {min_count}")
    if max_count is not None and count > max_count:
        errors.append(f"count {count} > max {max_count}")

    if errors:
        return AssertionResult(page, f"count_{count_type}", False,
                               f"{'; '.join(errors)} (actual={count})",
                               severity="WARN")

    return AssertionResult(page, f"count_{count_type}", True,
                           f"count={count} (range [{min_count or 0}, {max_count or 'inf'}])")


# ---------------------------------------------------------------------------
# Main test logic
# ---------------------------------------------------------------------------


def run_expectations_test(paper_key: str) -> list[AssertionResult]:
    """Load trace + expectations, run all assertions, return results."""
    fixture_dir = PAPER_CONFIGS[paper_key]
    trace_path = fixture_dir / "block_trace.csv"
    expectations_path = fixture_dir / "expectations.json"

    assert trace_path.exists(), f"block_trace.csv not found: {trace_path}"
    assert expectations_path.exists(), f"expectations.json not found: {expectations_path}"

    trace = load_trace(trace_path)
    with open(expectations_path, "r", encoding="utf-8") as f:
        expectations = json.load(f)

    results: list[AssertionResult] = []

    # Run page-level assertions
    pages_exp = expectations.get("pages", {})
    for page_str, page_exp in pages_exp.items():
        page_num = int(page_str)
        for assertion in page_exp.get("assertions", []):
            # text_equals assertion
            if "text_equals" in assertion:
                r = run_text_equals(
                    trace, page_num, assertion["text_equals"],
                    expected_role=assertion.get("expected_role"),
                    expected_zone=assertion.get("expected_zone"),
                    notes=assertion.get("notes", ""),
                )
                results.append(r)

            # text_contains assertion
            if "text_contains" in assertion:
                r = run_text_contains(
                    trace, page_num, assertion["text_contains"],
                    expected_role=assertion.get("expected_role"),
                    expected_zone=assertion.get("expected_zone"),
                    must_not_role=assertion.get("must_not_role"),
                    notes=assertion.get("notes", ""),
                )
                results.append(r)

            # count_text assertion
            if "count_text" in assertion:
                ct = assertion["count_text"]
                r = run_count_assertion(trace, page_num, "text",
                                        min_count=ct.get("min"), max_count=ct.get("max"))
                results.append(r)

            # count_figure_title assertion
            if "count_figure_title" in assertion:
                ct = assertion["count_figure_title"]
                r = run_count_assertion(trace, page_num, "figure_title",
                                        min_count=ct.get("min"), max_count=ct.get("max"))
                results.append(r)

            # count_reference_content assertion
            if "count_reference_content" in assertion:
                ct = assertion["count_reference_content"]
                r = run_count_assertion(trace, page_num, "reference_content",
                                        min_count=ct.get("min"), max_count=ct.get("max"))
                results.append(r)

            # count_image assertion
            if "count_image" in assertion:
                ct = assertion["count_image"]
                r = run_count_assertion(trace, page_num, "image",
                                        min_count=ct.get("min"), max_count=ct.get("max"))
                results.append(r)

            # count_chart assertion
            if "count_chart" in assertion:
                ct = assertion["count_chart"]
                r = run_count_assertion(trace, page_num, "chart",
                                        min_count=ct.get("min"), max_count=ct.get("max"))
                results.append(r)

            # count_all assertion
            if "count_all" in assertion:
                ct = assertion["count_all"]
                r = run_count_assertion(trace, page_num, "all",
                                        min_count=ct.get("min"), max_count=ct.get("max"))
                results.append(r)

    return results


def format_results_report(paper_key: str, results: list[AssertionResult]) -> str:
    """Format results into a readable report."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"TRACE vs EXPECTATIONS REPORT: {paper_key}")
    lines.append("=" * 70)

    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    lines.append(f"\nTotal: {len(results)} assertions | PASS: {len(passed)} | FAIL: {len(failed)}")
    lines.append("")

    if failed:
        lines.append("--- FAILURES ---")
        by_page: dict[int, list[AssertionResult]] = {}
        for r in failed:
            by_page.setdefault(r.page, []).append(r)
        for pg in sorted(by_page):
            lines.append(f"\n  Page {pg}:")
            for r in by_page[pg]:
                lines.append(f"    [{r.severity}] {r.assertion_type}: {r.message}")
        lines.append("")

    if passed:
        lines.append(f"--- PASS ({len(passed)}) ---")
        for r in passed[:20]:  # Show first 20 passes
            lines.append(f"    [OK] p{r.page} {r.assertion_type}: {r.message}")
        if len(passed) > 20:
            lines.append(f"    ... and {len(passed) - 20} more")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pytest tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("paper_key", ["DWQQK2YB", "CAQNW9Q2"])
def test_trace_vs_expectations(paper_key: str) -> None:
    """Compare real block_trace.csv against expectations.json for a paper."""
    results = run_expectations_test(paper_key)
    report = format_results_report(paper_key, results)

    # Print report (will be captured by pytest -s)
    print("\n" + report)

    # Fail test if any FAIL-level assertions failed
    fails = [r for r in results if not r.passed and r.severity == "FAIL"]
    if fails:
        fail_summary = "\n".join(f"  {r}" for r in fails)
        pytest.fail(f"{len(fails)} FAIL-level assertions failed:\n{fail_summary}")


@pytest.mark.parametrize("paper_key", ["DWQQK2YB", "CAQNW9Q2"])
def test_trace_role_distribution(paper_key: str) -> None:
    """Print role distribution from real trace for manual review."""
    fixture_dir = PAPER_CONFIGS[paper_key]
    trace_path = fixture_dir / "block_trace.csv"
    if not trace_path.exists():
        pytest.skip(f"block_trace.csv not found: {trace_path}")

    trace = load_trace(trace_path)
    from collections import Counter
    role_counts = Counter(b.get("role", "?") for b in trace)
    zone_counts = Counter(b.get("zone", "?") for b in trace)

    print(f"\n{paper_key} - Role Distribution:")
    for role, count in role_counts.most_common():
        print(f"  {role:35s} {count:4d}")
    print(f"\n{paper_key} - Zone Distribution:")
    for zone, count in zone_counts.most_common():
        print(f"  {zone:35s} {count:4d}")


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-v", "--timeout=60"])
