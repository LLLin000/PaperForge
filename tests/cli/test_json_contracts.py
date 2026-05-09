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
    """Contract: 'paperforge paths --json' returns valid JSON with correct value types."""

    REQUIRED_KEYS = {"vault", "worker_script", "ld_deep_script"}

    def test_paths_json_value_semantics(self, cli_invoker):
        """paths --json returns paths with correct value types (all non-empty strings)."""
        result = cli_invoker(["paths", "--json"])
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr}"
        data = assert_valid_json(result.stdout)
        assert_json_shape(data, self.REQUIRED_KEYS)
        for key in self.REQUIRED_KEYS:
            val = data[key]
            assert isinstance(val, str), f"{key} should be string, got {type(val).__name__}"
            assert len(val) > 0, f"{key} should not be empty"
        assert data.get("vault", "").startswith("<") or len(data.get("vault", "")) > 0

    def test_paths_no_json_text_output(self, cli_invoker):
        """paths without --json outputs human-readable text."""
        result = cli_invoker(["paths"])
        assert result.returncode == 0
        assert ":" in result.stdout, "Expected key: value format"
        lines = result.stdout.strip().split("\n")
        assert len(lines) >= 3, "Expected at least 3 path entries"


class TestStatusJson:
    """Contract: 'paperforge status --json' returns JSON with correct value semantics."""

    REQUIRED_KEYS = {"total_papers", "version", "vault", "system_dir", "resources_dir"}
    OPTIONAL_KEYS = {
        "formal_notes", "exports", "domains", "bases", "path_errors",
        "env_configured", "ocr",
        "lifecycle_level_counts", "health_aggregate", "maturity_distribution",
    }

    def test_status_json_value_semantics(self, cli_invoker):
        """status --json returns valid JSON with all contract keys and correct value types."""
        result = cli_invoker(["status", "--json"])
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr}"
        data = assert_valid_json(result.stdout)
        assert_json_shape(data, self.REQUIRED_KEYS, self.OPTIONAL_KEYS)
        total = data.get("total_papers", -1)
        assert isinstance(total, int) and total >= 0, f"total_papers should be non-negative int, got {total}"
        ver = data.get("version", "")
        assert isinstance(ver, str) and len(ver) > 0, f"version should be non-empty string, got {ver}"
        assert data.get("system_dir", "") == "System", f"system_dir should be 'System', got {data.get('system_dir')}"
        assert data.get("resources_dir", "") == "Resources", f"resources_dir should be 'Resources', got {data.get('resources_dir')}"
        if "ocr" in data:
            ocr = data["ocr"]
            for field in ("total", "pending", "processing", "done", "failed"):
                assert isinstance(ocr.get(field), int), f"ocr.{field} should be int, got {type(ocr.get(field)).__name__}"

    def test_status_json_snapshot_regression(self, cli_invoker, snapshot):
        """status --json snapshot for regression detection (value semantics tested separately)."""
        result = cli_invoker(["status", "--json"])
        assert result.returncode == 0
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
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
