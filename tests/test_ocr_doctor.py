# Tests for paperforge.ocr_diagnostics — tiered L1-L4 checks.

import json
import os
from unittest.mock import MagicMock, patch

from paperforge.ocr_diagnostics import ocr_doctor


# ---------------------------------------------------------------------------
# L1 — Token presence
# ---------------------------------------------------------------------------
def test_l1_missing_token():
    """Empty env → level 1 failed."""
    with patch.dict(os.environ, {}, clear=True):
        result = ocr_doctor(config=None, live=False)

    assert result["level"] == 1
    assert result["passed"] is False
    assert "PADDLEOCR_API_TOKEN" in result["error"]
    assert "Set PADDLEOCR_API_TOKEN" in result["fix"]


# ---------------------------------------------------------------------------
# L2 — URL reachability
# ---------------------------------------------------------------------------
def test_l2_bad_url():
    """Mock POST returning 404 → level 2 failed."""
    env = {"PADDLEOCR_API_TOKEN": "test-token"}
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    with patch.dict(os.environ, env, clear=True):
        with patch("paperforge.ocr_diagnostics.requests.post", return_value=mock_resp):
            result = ocr_doctor(config=None, live=False)

    assert result["level"] == 2
    assert result["passed"] is False
    assert "404" in result["error"]
    assert "PADDLEOCR_JOB_URL" in result["fix"]


def test_l2_unauthorized():
    """Mock POST returning 401 → level 2 failed with auth message."""
    env = {"PADDLEOCR_API_TOKEN": "bad-token"}
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch.dict(os.environ, env, clear=True):
        with patch("paperforge.ocr_diagnostics.requests.post", return_value=mock_resp):
            result = ocr_doctor(config=None, live=False)

    assert result["level"] == 2
    assert result["passed"] is False
    assert "401" in result["error"]
    assert "token is invalid" in result["fix"]


def test_l2_400_accepted():
    """Mock POST returning 400 → level 2 passes (reachable, incomplete request)."""
    env = {"PADDLEOCR_API_TOKEN": "test-token"}
    mock_resp = MagicMock()
    mock_resp.status_code = 400

    with patch.dict(os.environ, env, clear=True):
        with patch("paperforge.ocr_diagnostics.requests.post", return_value=mock_resp):
            result = ocr_doctor(config=None, live=False)

    # 400 must NOT be an L2 failure — it proves URL reachable
    assert result["level"] != 2, f"Expected L2 to pass, got level {result['level']}"


# ---------------------------------------------------------------------------
# L3 — API response structure
# ---------------------------------------------------------------------------
def test_l3_schema_mismatch():
    """Mock POST returning JSON without data.jobId → level 3 failed."""
    env = {"PADDLEOCR_API_TOKEN": "test-token"}
    get_resp = MagicMock()
    get_resp.status_code = 200
    post_resp = MagicMock()
    post_resp.status_code = 200
    post_resp.text = json.dumps({"message": "ok"})
    post_resp.json.return_value = {"message": "ok"}

    with patch.dict(os.environ, env, clear=True):
        with patch("paperforge.ocr_diagnostics.requests.get", return_value=get_resp):
            with patch("paperforge.ocr_diagnostics.requests.post", return_value=post_resp):
                result = ocr_doctor(config=None, live=False)

    assert result["level"] == 3
    assert result["passed"] is False
    assert "data.jobId" in result["error"]
    assert "raw_response" in result


def test_l3_success():
    """Mock POST returning valid jobId → level 3 passed."""
    env = {"PADDLEOCR_API_TOKEN": "test-token"}
    get_resp = MagicMock()
    get_resp.status_code = 200
    post_resp = MagicMock()
    post_resp.status_code = 200
    post_resp.text = json.dumps({"data": {"jobId": "123"}})
    post_resp.json.return_value = {"data": {"jobId": "123"}}
    delete_resp = MagicMock()
    delete_resp.status_code = 204

    with patch.dict(os.environ, env, clear=True):
        with patch("paperforge.ocr_diagnostics.requests.get", return_value=get_resp):
            with patch("paperforge.ocr_diagnostics.requests.post", return_value=post_resp):
                with patch("paperforge.ocr_diagnostics.requests.delete", return_value=delete_resp):
                    result = ocr_doctor(config=None, live=False)

    assert result["level"] == 3
    assert result["passed"] is True
    assert "All diagnostics passed" in result["message"]


# ---------------------------------------------------------------------------
# L4 — Live PDF test
# ---------------------------------------------------------------------------
def test_l4_live_success():
    """Mock POST + GET poll returning done → level 4 passed."""
    env = {"PADDLEOCR_API_TOKEN": "test-token"}
    get_resp = MagicMock()
    get_resp.status_code = 200
    post_resp = MagicMock()
    post_resp.status_code = 200
    post_resp.text = json.dumps({"data": {"jobId": "456"}})
    post_resp.json.return_value = {"data": {"jobId": "456"}}
    poll_resp = MagicMock()
    poll_resp.status_code = 200
    poll_resp.json.return_value = {"data": {"state": "done"}}
    delete_resp = MagicMock()
    delete_resp.status_code = 204

    with (
        patch.dict(os.environ, env, clear=True),
        patch(
            "paperforge.ocr_diagnostics.requests.get",
            side_effect=[get_resp] + [poll_resp] * 10,
        ),
        patch("paperforge.ocr_diagnostics.requests.post", return_value=post_resp),
    ):
        with patch("paperforge.ocr_diagnostics.requests.delete", return_value=delete_resp):
            with patch("paperforge.ocr_diagnostics.time.sleep"):
                result = ocr_doctor(config=None, live=True)

    assert result["level"] == 4
    assert result["passed"] is True
    assert "All diagnostics passed" in result["message"]


def test_l4_live_failure():
    """Mock POST + GET poll returning error → level 4 failed."""
    env = {"PADDLEOCR_API_TOKEN": "test-token"}
    get_resp = MagicMock()
    get_resp.status_code = 200
    post_resp = MagicMock()
    post_resp.status_code = 200
    post_resp.text = json.dumps({"data": {"jobId": "789"}})
    post_resp.json.return_value = {"data": {"jobId": "789"}}
    poll_resp = MagicMock()
    poll_resp.status_code = 200
    poll_resp.json.return_value = {"data": {"state": "error", "errorMsg": "bad pdf"}}
    delete_resp = MagicMock()
    delete_resp.status_code = 204

    with (
        patch.dict(os.environ, env, clear=True),
        patch(
            "paperforge.ocr_diagnostics.requests.get",
            side_effect=[get_resp] + [poll_resp] * 10,
        ),
        patch("paperforge.ocr_diagnostics.requests.post", return_value=post_resp),
    ):
        with patch("paperforge.ocr_diagnostics.requests.delete", return_value=delete_resp):
            with patch("paperforge.ocr_diagnostics.time.sleep"):
                result = ocr_doctor(config=None, live=True)

    assert result["level"] == 4
    assert result["passed"] is False
    assert "bad pdf" in result["error"]
