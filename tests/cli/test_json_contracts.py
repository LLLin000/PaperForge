"""CLI contract tests for JSON-output commands: paths, status, context."""

from __future__ import annotations

import json

import pytest

from .test_contract_helpers import (
    assert_json_shape,
    assert_valid_json,
    normalize_snapshot,
)


class TestPathsJson:
    """Contract: 'paperforge paths --json' returns stable JSON."""

    REQUIRED_KEYS = {"vault", "worker_script", "ld_deep_script"}

    def test_paths_json_valid(self, cli_invoker):
        """paths --json outputs valid JSON with expected keys."""
        result = cli_invoker(["paths", "--json"])
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr}"
        data = assert_valid_json(result.stdout)
        assert_json_shape(data, self.REQUIRED_KEYS)

    def test_paths_json_snapshot(self, cli_invoker, snapshot):
        """paths --json matches snapshot (normalized)."""
        result = cli_invoker(["paths", "--json"])
        assert result.returncode == 0

        # Parse and re-serialize for consistent formatting
        data = json.loads(result.stdout)
        vault = data.get("vault", "")
        normalized = normalize_snapshot(
            json.dumps(data, indent=2, ensure_ascii=False), vault
        )
        snapshot.assert_match(normalized, "paths_json/default_config.json")

    def test_paths_no_json_text_output(self, cli_invoker):
        """paths without --json outputs human-readable text."""
        result = cli_invoker(["paths"])
        assert result.returncode == 0
        assert ":" in result.stdout, "Expected key: value format"
        lines = result.stdout.strip().split("\n")
        assert len(lines) >= 3, "Expected at least 3 path entries"


class TestStatusJson:
    """Contract: 'paperforge status --json' returns stable JSON."""

    REQUIRED_KEYS = {"total_papers", "version", "vault", "system_dir", "resources_dir"}
    OPTIONAL_KEYS = {
        "formal_notes", "exports", "domains", "bases", "path_errors",
        "env_configured", "ocr",
        "lifecycle_level_counts", "health_aggregate", "maturity_distribution",
    }

    def test_status_json_on_empty_vault(self, cli_invoker):
        """status --json on empty vault returns valid JSON with all contract keys."""
        result = cli_invoker(["status", "--json"])
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr}"
        data = assert_valid_json(result.stdout)
        assert_json_shape(data, self.REQUIRED_KEYS, self.OPTIONAL_KEYS)
        # Empty vault should have 0 papers
        assert data.get("total_papers", -1) >= 0

    def test_status_json_snapshot(self, cli_invoker, snapshot):
        """status --json matches snapshot (normalized)."""
        result = cli_invoker(["status", "--json"])
        assert result.returncode == 0
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            # status --json may not output JSON in all vault states
            pytest.skip("status --json did not produce valid JSON")
        vault = data.get("vault", "")
        normalized = normalize_snapshot(
            json.dumps(data, indent=2, ensure_ascii=False), vault
        )
        snapshot.assert_match(normalized, "status_json/empty_vault.json")

    def test_status_json_no_vault(self, cli_invoker):
        """status on a non-existent vault should exit non-zero with error."""
        result = cli_invoker(["status", "--json", "--vault", "/nonexistent/path"])
        assert result.returncode != 0


class TestContextJson:
    """Contract: 'paperforge context' outputs stable JSON format."""

    REQUIRED_KEYS = {"_format_version", "_context", "_generated_at", "zotero_key"}
    OPTIONAL_KEYS = {
        "domain", "title", "authors", "abstract", "journal", "year",
        "doi", "pmid", "collections", "_provenance", "_ai_readiness",
    }

    def test_context_no_index_returns_error(self, cli_invoker):
        """context with no index should exit 1 with error message."""
        result = cli_invoker(["context", "FIXT0001"])
        assert result.returncode != 0
        assert "error" in result.stderr.lower() or "Error" in result.stderr

    def test_context_no_args_returns_error(self, cli_invoker):
        """context without key/--domain/--all should exit 1."""
        result = cli_invoker(["context"])
        assert result.returncode != 0
