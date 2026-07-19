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

    REQUIRED_KEYS = {"vault", "worker_script", "pf_deep_script", "ld_deep_script"}

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
    """Contract: 'paperforge status --json' returns PFResult with correct value semantics."""

    ENVELOPE_KEYS = {"ok", "command", "version", "data", "error"}
    REQUIRED_KEYS = {"total_papers", "vault", "system_dir", "resources_dir"}
    OPTIONAL_KEYS = {
        "version",  # duplicated from envelope (old format preserved in data)
        "formal_notes", "exports", "domains", "bases", "path_errors",
        "env_configured", "ocr",         "structured_ocr_health",
        "lifecycle_level_counts", "health_aggregate", "maturity_distribution",
        "ocr_version_state",
    }

    def test_status_json_value_semantics(self, cli_invoker):
        """status --json returns valid PFResult with all contract keys and correct value types."""
        result = cli_invoker(["status", "--json"])
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr}"
        envelope = assert_valid_json(result.stdout)
        assert_json_shape(envelope, self.ENVELOPE_KEYS)
        assert envelope["ok"] is True
        assert envelope["command"] == "status"
        assert isinstance(envelope["version"], str) and len(envelope["version"]) > 0

        data = envelope["data"]
        assert_json_shape(data, self.REQUIRED_KEYS, self.OPTIONAL_KEYS)
        total = data.get("total_papers", -1)
        assert isinstance(total, int) and total >= 0, f"total_papers should be non-negative int, got {total}"
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
            envelope = json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.skip("status --json did not produce valid JSON")
        vault = envelope.get("data", {}).get("vault", "")
        normalized = normalize_snapshot(
            json.dumps(envelope, indent=2, ensure_ascii=False), vault
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


class TestSearchJson:
    """Contract: 'paperforge search --json' returns PFResult with data.matches."""

    ENVELOPE_KEYS = {"ok", "command", "version", "data", "error"}

    def test_search_no_memory_db_returns_error(self, cli_invoker):
        """search on a vault without memory DB returns ok:false with error."""
        result = cli_invoker(["search", "test", "--json"])
        parsed = assert_valid_json(result.stdout)
        assert_json_shape(parsed, self.ENVELOPE_KEYS)
        assert parsed["ok"] is False
        assert "code" in parsed["error"], "error.code is missing"
        assert "message" in parsed["error"], "error.message is missing"
        assert result.returncode != 0

    def test_search_matches_key_present(self, cli_invoker):
        """search --json output has top-level PFResult envelope and data.matches key when successful."""
        result = cli_invoker(["search", "test", "--json"])
        parsed = assert_valid_json(result.stdout)
        assert_json_shape(parsed, self.ENVELOPE_KEYS)
        if parsed["ok"]:
            data = parsed["data"]
            assert "matches" in data, "data.matches key is missing"
            assert isinstance(data["matches"], list), "data.matches should be a list"
            assert "count" in data, "data.count is missing"
            # Verify unified field names on first match if any
            if data["matches"]:
                m = data["matches"][0]
                for field in ("zotero_key", "title", "first_author", "year", "journal", "domain", "abstract", "score", "text", "heading", "source"):
                    assert field in m, f"match field '{field}' is missing"

    def test_search_matches_field_types(self, cli_invoker):
        """search match fields have correct types when results exist."""
        result = cli_invoker(["search", "test", "--json", "--limit", "5"])
        parsed = assert_valid_json(result.stdout)
        if parsed["ok"] and parsed["data"]["matches"]:
            m = parsed["data"]["matches"][0]
            assert isinstance(m["zotero_key"], str), "zotero_key should be str"
            assert isinstance(m["title"], str), "title should be str"
            assert isinstance(m["score"], (int, float)), "score should be numeric"


class TestRetrieveJson:
    """Contract: 'paperforge retrieve --json' returns PFResult with data.matches."""

    ENVELOPE_KEYS = {"ok", "command", "version", "data", "error"}

    def test_retrieve_no_memory_db_returns_error(self, cli_invoker):
        """retrieve on a vault without memory DB returns ok:false with error."""
        result = cli_invoker(["retrieve", "test", "--json"])
        parsed = assert_valid_json(result.stdout)
        assert_json_shape(parsed, self.ENVELOPE_KEYS)
        assert parsed["ok"] is False
        assert "code" in parsed["error"], "error.code is missing"
        assert "message" in parsed["error"], "error.message is missing"
        assert result.returncode != 0

    def test_retrieve_matches_key_present(self, cli_invoker):
        """retrieve --json output has data.matches key when successful."""
        result = cli_invoker(["retrieve", "test", "--json"])
        parsed = assert_valid_json(result.stdout)
        assert_json_shape(parsed, self.ENVELOPE_KEYS)
        if parsed["ok"]:
            data = parsed["data"]
            assert "matches" in data, "data.matches key is missing"
            assert isinstance(data["matches"], list), "data.matches should be a list"
            if data["matches"]:
                m = data["matches"][0]
                for field in ("zotero_key", "title", "first_author", "year", "journal", "domain", "abstract", "score", "text", "heading", "source"):
                    assert field in m, f"match field '{field}' is missing"

    def test_retrieve_deep_flag_accepted(self, cli_invoker):
        """retrieve --deep --json is accepted (may return empty results on minimal vault)."""
        result = cli_invoker(["retrieve", "test", "--deep", "--json"])
        parsed = assert_valid_json(result.stdout)
        assert_json_shape(parsed, self.ENVELOPE_KEYS)
        # --deep may succeed (ok:true) or fail (ok:false) depending on vault state — just validate shape
        if parsed["ok"]:
            assert "matches" in parsed["data"], "data.matches key is missing"

    def test_retrieve_matches_field_types(self, cli_invoker):
        """retrieve match fields have correct types when results exist."""
        result = cli_invoker(["retrieve", "test", "--json", "--limit", "5"])
        parsed = assert_valid_json(result.stdout)
        if parsed["ok"] and parsed["data"]["matches"]:
            m = parsed["data"]["matches"][0]
            assert isinstance(m["zotero_key"], str), "zotero_key should be str"
            assert isinstance(m["score"], (int, float)), "score should be numeric"
            assert isinstance(m["text"], str), "text should be str"
