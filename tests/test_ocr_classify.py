"""Tests for paperforge.ocr_diagnostics.classify_error().

Maps exceptions to (state, suggestion) pairs per the D-03 taxonomy.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import requests

from paperforge.ocr_diagnostics import classify_error


class TestClassifyError:
    """Tests for classify_error exception taxonomy."""

    def test_connection_error_blocked(self):
        """ConnectionError → blocked, check URL."""
        exc = requests.exceptions.ConnectionError("Connection refused")
        state, suggestion = classify_error(exc, None)
        assert state == "blocked"
        assert "PADDLEOCR_JOB_URL" in suggestion

    def test_timeout_error(self):
        """Timeout → error, retry suggestion."""
        exc = requests.exceptions.Timeout("Request timed out")
        state, suggestion = classify_error(exc, None)
        assert state == "error"
        assert "timed out" in suggestion

    def test_read_timeout_error(self):
        """ReadTimeout → error, retry suggestion."""
        exc = requests.exceptions.ReadTimeout("Read timed out")
        state, suggestion = classify_error(exc, None)
        assert state == "error"
        assert "timed out" in suggestion

    def test_http_error_401_blocked(self):
        """HTTPError 401 → blocked, invalid token."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        exc = requests.exceptions.HTTPError("401 Unauthorized", response=mock_resp)
        state, suggestion = classify_error(exc, mock_resp)
        assert state == "blocked"
        assert "token" in suggestion.lower()

    def test_http_error_404(self):
        """HTTPError 404 → error, job not found."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        exc = requests.exceptions.HTTPError("404 Not Found", response=mock_resp)
        state, suggestion = classify_error(exc, mock_resp)
        assert state == "error"
        assert "not found" in suggestion.lower()

    def test_http_error_503(self):
        """HTTPError 503 → error, provider issue."""
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        exc = requests.exceptions.HTTPError("503 Service Unavailable", response=mock_resp)
        state, suggestion = classify_error(exc, mock_resp)
        assert state == "error"
        assert "provider" in suggestion.lower()

    def test_http_error_generic(self):
        """HTTPError 418 → error, generic HTTP message."""
        mock_resp = MagicMock()
        mock_resp.status_code = 418
        exc = requests.exceptions.HTTPError("418 I'm a teapot", response=mock_resp)
        state, suggestion = classify_error(exc, mock_resp)
        assert state == "error"
        assert "418" in suggestion

    def test_json_decode_error(self):
        """JSONDecodeError -> error, format changed."""
        exc = json.JSONDecodeError("Expecting value", "doc", 0)
        state, suggestion = classify_error(exc, None)
        assert state == "error"
        assert "format changed" in suggestion.lower()

    def test_key_error(self):
        """KeyError → error, missing fields."""
        exc = KeyError("data")
        state, suggestion = classify_error(exc, None)
        assert state == "error"
        assert "missing expected fields" in suggestion

    def test_file_not_found_blocked(self):
        """FileNotFoundError → blocked, check attachment."""
        exc = FileNotFoundError("missing.pdf")
        state, suggestion = classify_error(exc, None)
        assert state == "blocked"
        assert "attachment" in suggestion.lower()

    def test_generic_exception(self):
        """Generic Exception → error, unexpected."""
        exc = ValueError("something weird")
        state, suggestion = classify_error(exc, None)
        assert state == "error"
        assert "something weird" in suggestion
        assert "diagnose" in suggestion.lower()
