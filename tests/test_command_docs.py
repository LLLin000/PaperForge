"""
Test suite for PaperForge command documentation.

Ensures user-facing docs use stable `paperforge ...` commands
instead of unresolved <system_dir> token paths.

Scope: User-run command examples in markdown files.
Excluded: Architecture diagrams, frontmatter field examples in AGENTS.md.
"""

from __future__ import annotations

import re
from pathlib import Path

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
        "pf-status": base / "pf-status.md",
        "pf-sync": base / "pf-sync.md",
        "pf-ocr": base / "pf-ocr.md",
        "pf-deep": base / "pf-deep.md",
        "pf-paper": base / "pf-paper.md",
    }


@pytest.fixture
def user_facing_docs() -> dict[str, Path]:
    return {
        "README": REPO_ROOT / "README.md",
        "INSTALLATION": REPO_ROOT / "docs" / "INSTALLATION.md",
        "setup-guide": REPO_ROOT / "docs" / "setup-guide.md",
        "AGENTS": REPO_ROOT / "AGENTS.md",
    }


# ---------------------------------------------------------------------------
# Task 1 tests — stable commands present
# ---------------------------------------------------------------------------


class TestStableCommandsPresent:
    """Verify command docs contain stable paperforge commands."""

    @pytest.mark.parametrize(
        "doc_key,expected_cmd",
        [
            ("pf-status", "paperforge status"),
            ("pf-sync", "paperforge sync"),
            ("pf-ocr", "paperforge ocr"),
        ],
    )
    def test_pf_doc_contains_stable_command(
        self,
        command_docs: dict[str, Path],
        doc_key: str,
        expected_cmd: str,
    ) -> None:
        """pf-* command docs must show stable paperforge commands."""
        content = read_fileutf8(command_docs[doc_key])
        code_lines = code_block_lines(content)
        # Join all lines for substring search
        combined = "\n".join(code_lines)
        assert (
            expected_cmd in combined
        ), f"[{doc_key}] Expected stable command '{expected_cmd}' not found in code blocks. Code lines:\n{code_lines}"

    def test_pf_deep_mentions_paperforge_deep_reading(
        self,
        command_docs: dict[str, Path],
    ) -> None:
        """pf-deep.md must mention 'paperforge deep-reading' for queue preflight."""
        content = read_fileutf8(command_docs["pf-deep"])
        assert (
            "paperforge deep-reading" in content
        ), "pf-deep.md must mention 'paperforge deep-reading' for queue preflight"

    def test_pf_deep_mentions_paperforge_paths_json(
        self,
        command_docs: dict[str, Path],
    ) -> None:
        """pf-deep.md must reference 'paperforge paths --json' for path resolution."""
        content = read_fileutf8(command_docs["pf-deep"])
        assert (
            "paperforge paths --json" in content or "paperforge paths" in content
        ), "pf-deep.md must reference 'paperforge paths' or 'paperforge paths --json' for script path discovery"


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
            "pf-status",
            "pf-sync",
            "pf-ocr",
        ],
    )
    def test_pf_doc_no_legacy_python_literature_pipeline(
        self,
        command_docs: dict[str, Path],
        doc_key: str,
    ) -> None:
        """pf-* docs must NOT have legacy python <system_dir>/.../literature_pipeline.py commands."""
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
        assert (
            match is None
        ), f"[README] Found legacy unresolved token path in code blocks: {match.group(0)!r}\nCode lines:\n{code_lines}"

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
        assert re.search(
            pattern, content
        ), f"[{doc_key}] Expected to find stable paperforge command pattern {pattern!r} in user-facing documentation."


# ---------------------------------------------------------------------------
# New tests — unified commands present in user-facing docs
# ---------------------------------------------------------------------------


class TestUnifiedCommandsInUserDocs:
    """AGENTS.md, README must reference new unified commands, not old ones."""

    @pytest.mark.parametrize(
        "doc_key",
        ["README", "AGENTS"],
    )
    def test_no_old_selection_sync_in_user_docs(
        self,
        user_facing_docs: dict[str, Path],
        doc_key: str,
    ) -> None:
        """User-facing docs should not reference old 'paperforge selection-sync' as primary."""
        content = read_fileutf8(user_facing_docs[doc_key])
        # Allow in migration section only
        lines = content.splitlines()
        migration_started = False
        for line in lines:
            if "命令迁移说明" in line or "迁移" in line.lower() or "migration" in line.lower():
                migration_started = True
            if "paperforge selection-sync" in line and not migration_started:
                pytest.fail(
                    f"[{doc_key}] Found old command 'paperforge selection-sync' outside migration section: {line}"
                )

    @pytest.mark.parametrize(
        "doc_key",
        ["README", "AGENTS"],
    )
    def test_no_old_index_refresh_in_user_docs(
        self,
        user_facing_docs: dict[str, Path],
        doc_key: str,
    ) -> None:
        """User-facing docs should not reference old 'paperforge index-refresh' as primary."""
        content = read_fileutf8(user_facing_docs[doc_key])
        lines = content.splitlines()
        migration_started = False
        for line in lines:
            if "命令迁移说明" in line or "迁移" in line.lower() or "migration" in line.lower():
                migration_started = True
            if "paperforge index-refresh" in line and not migration_started:
                pytest.fail(
                    f"[{doc_key}] Found old command 'paperforge index-refresh' outside migration section: {line}"
                )

    @pytest.mark.parametrize(
        "doc_key",
        ["README", "AGENTS"],
    )
    def test_no_old_ocr_run_in_user_docs(
        self,
        user_facing_docs: dict[str, Path],
        doc_key: str,
    ) -> None:
        """User-facing docs should not reference old 'paperforge ocr run' as primary."""
        content = read_fileutf8(user_facing_docs[doc_key])
        lines = content.splitlines()
        migration_started = False
        for line in lines:
            if "命令迁移说明" in line or "迁移" in line.lower() or "migration" in line.lower():
                migration_started = True
            if "paperforge ocr run" in line and not migration_started:
                pytest.fail(f"[{doc_key}] Found old command 'paperforge ocr run' outside migration section: {line}")


# ---------------------------------------------------------------------------
# Run all tests when invoked directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-q"])
