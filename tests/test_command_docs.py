# -*- coding: utf-8 -*-
"""
Test suite for PaperForge Lite command documentation.

Ensures user-facing docs use stable `paperforge ...` commands
instead of unresolved <system_dir> token paths.

Scope: User-run command examples in markdown files.
Excluded: Architecture diagrams, frontmatter field examples in AGENTS.md.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.resolve()


def read_fileutf8(path: Path) -> str:
    """Read a file as UTF-8, fail gracefully if missing."""
    if not path.exists():
        pytest.fail(f"File does not exist: {path}")
    return path.read_text(encoding="utf-8")


def find_code_blocks(content: str) -> list[tuple[str, str]]:
    """Return list of (lang, code) tuples from a markdown file.

    lang is '' for blocks without a language tag.
    Only blocks in ``` fences are captured.
    """
    results: list[tuple[str, str]] = []
    # Normalize line endings
    content = content.replace("\r\n", "\n")
    pattern = re.compile(r"^```(\w*)\n(.*?)```", re.MULTILINE | re.DOTALL)
    for m in pattern.finditer(content):
        lang = m.group(1)
        code = m.group(2)
        results.append((lang, code))
    return results


def code_block_lines(content: str) -> list[str]:
    """Flatten all code-block lines from a markdown file."""
    lines: list[str] = []
    for _lang, code in find_code_blocks(content):
        lines.extend(code.splitlines())
    return lines


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def command_docs() -> dict[str, Path]:
    base = REPO_ROOT / "command"
    return {
        "lp-status": base / "lp-status.md",
        "lp-selection-sync": base / "lp-selection-sync.md",
        "lp-index-refresh": base / "lp-index-refresh.md",
        "lp-ocr": base / "lp-ocr.md",
        "ld-deep": base / "ld-deep.md",
        "ld-paper": base / "ld-paper.md",
    }


@pytest.fixture
def user_facing_docs() -> dict[str, Path]:
    return {
        "README": REPO_ROOT / "README.md",
        "INSTALLATION": REPO_ROOT / "docs" / "INSTALLATION.md",
        "setup-guide": REPO_ROOT / "docs" / "setup-guide.md",
    }


# ---------------------------------------------------------------------------
# Task 1 tests — stable commands present
# ---------------------------------------------------------------------------

class TestStableCommandsPresent:
    """Verify command docs contain stable paperforge commands."""

    @pytest.mark.parametrize(
        "doc_key,expected_cmd",
        [
            ("lp-status", "paperforge status"),
            ("lp-selection-sync", "paperforge selection-sync"),
            ("lp-index-refresh", "paperforge index-refresh"),
            ("lp-ocr", "paperforge ocr run"),
        ],
    )
    def test_lp_doc_contains_stable_command(
        self,
        command_docs: dict[str, Path],
        doc_key: str,
        expected_cmd: str,
    ) -> None:
        """lp-* command docs must show stable paperforge commands."""
        content = read_fileutf8(command_docs[doc_key])
        code_lines = code_block_lines(content)
        # Join all lines for substring search
        combined = "\n".join(code_lines)
        assert expected_cmd in combined, (
            f"[{doc_key}] Expected stable command '{expected_cmd}' "
            f"not found in code blocks. Code lines:\n{code_lines}"
        )

    def test_ld_deep_mentions_paperforge_deep_reading(
        self,
        command_docs: dict[str, Path],
    ) -> None:
        """ld-deep.md must mention 'paperforge deep-reading' for queue preflight."""
        content = read_fileutf8(command_docs["ld-deep"])
        assert "paperforge deep-reading" in content, (
            "ld-deep.md must mention 'paperforge deep-reading' for queue preflight"
        )

    def test_ld_deep_mentions_paperforge_paths_json(
        self,
        command_docs: dict[str, Path],
    ) -> None:
        """ld-deep.md must reference 'paperforge paths --json' for path resolution."""
        content = read_fileutf8(command_docs["ld-deep"])
        assert "paperforge paths --json" in content or "paperforge paths" in content, (
            "ld-deep.md must reference 'paperforge paths' or 'paperforge paths --json' "
            "for script path discovery"
        )


# ---------------------------------------------------------------------------
# Task 1 tests — unresolved tokens absent from user-run examples
# ---------------------------------------------------------------------------

class TestUnresolvedTokensAbsentFromUserRunExamples:
    """
    Limit unresolved-token rejection to user-run command examples.
    Architecture diagrams and frontmatter field examples in AGENTS.md are excluded.
    """

    LEGACY_PYTHON_LITERATURE_PIPELINE = re.compile(
        r"python\s+<system_dir>/PaperForge/worker/scripts/literature_pipeline\.py"
    )

    @pytest.mark.parametrize(
        "doc_key",
        [
            "lp-status",
            "lp-selection-sync",
            "lp-index-refresh",
            "lp-ocr",
        ],
    )
    def test_lp_doc_no_legacy_python_literature_pipeline(
        self,
        command_docs: dict[str, Path],
        doc_key: str,
    ) -> None:
        """lp-* docs must NOT have legacy python <system_dir>/.../literature_pipeline.py commands."""
        content = read_fileutf8(command_docs[doc_key])
        code_lines = code_block_lines(content)
        combined = "\n".join(code_lines)
        match = self.LEGACY_PYTHON_LITERATURE_PIPELINE.search(combined)
        assert match is None, (
            f"[{doc_key}] Found legacy unresolved token path in code blocks: {match.group(0)!r}\n"
            f"Code lines:\n{code_lines}"
        )

    def test_readme_no_legacy_python_literature_pipeline_in_examples(
        self,
        user_facing_docs: dict[str, Path],
    ) -> None:
        """README.md must not show legacy python <system_dir>/... in user-run examples."""
        content = read_fileutf8(user_facing_docs["README"])
        code_lines = code_block_lines(content)
        combined = "\n".join(code_lines)
        match = self.LEGACY_PYTHON_LITERATURE_PIPELINE.search(combined)
        assert match is None, (
            f"[README] Found legacy unresolved token path in code blocks: {match.group(0)!r}\n"
            f"Code lines:\n{code_lines}"
        )

    def test_installation_no_legacy_python_literature_pipeline_in_examples(
        self,
        user_facing_docs: dict[str, Path],
    ) -> None:
        """docs/INSTALLATION.md must not show legacy python <system_dir>/... in user-run examples."""
        content = read_fileutf8(user_facing_docs["INSTALLATION"])
        code_lines = code_block_lines(content)
        combined = "\n".join(code_lines)
        match = self.LEGACY_PYTHON_LITERATURE_PIPELINE.search(combined)
        assert match is None, (
            f"[INSTALLATION] Found legacy unresolved token path in code blocks: {match.group(0)!r}\n"
            f"Code lines:\n{code_lines}"
        )


# ---------------------------------------------------------------------------
# Task 1 tests — paperforge paths/status examples in user-facing docs
# ---------------------------------------------------------------------------

class TestPaperforgeCommandExamplesInUserDocs:
    """README, INSTALLATION, setup-guide must show stable paperforge command examples."""

    @pytest.mark.parametrize(
        "doc_key,pattern",
        [
            ("README", r"paperforge (status|paths)"),
            ("INSTALLATION", r"paperforge (status|paths)"),
            ("setup-guide", r"paperforge (status|paths)"),
        ],
    )
    def test_user_doc_contains_paperforge_stable_example(
        self,
        user_facing_docs: dict[str, Path],
        doc_key: str,
        pattern: str,
    ) -> None:
        """User-facing docs must contain at least one 'paperforge status' or 'paperforge paths' example."""
        content = read_fileutf8(user_facing_docs[doc_key])
        assert re.search(pattern, content), (
            f"[{doc_key}] Expected to find stable paperforge command pattern {pattern!r} "
            f"in user-facing documentation."
        )


# ---------------------------------------------------------------------------
# Run all tests when invoked directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-q"])
