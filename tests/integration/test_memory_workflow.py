from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

from paperforge.memory.db import get_memory_db_path


@pytest.mark.integration
def test_memory_build_and_status_with_test_vault(test_vault: Path):
    """End-to-end: sync -> memory build -> memory status -> paper-status."""
    pf = ["python", "-m", "paperforge", "--vault", str(test_vault)]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    # 1. Sync to ensure formal-library.json exists
    result = subprocess.run(
        pf + ["sync", "--json"], capture_output=True, text=True, encoding="utf-8", env=env
    )
    if result.returncode != 0:
        pytest.skip("Sync failed -- test vault may lack export files")

    # 2. Memory build
    result = subprocess.run(
        pf + ["memory", "build", "--json"], capture_output=True, text=True, encoding="utf-8", env=env
    )
    assert result.returncode == 0, f"memory build failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["ok"] is True, f"build result not ok: {data}"
    assert data["data"]["papers_indexed"] > 0, "expected at least 1 paper indexed"

    # 3. Memory status
    result = subprocess.run(
        pf + ["memory", "status", "--json"], capture_output=True, text=True, encoding="utf-8", env=env
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["data"]["fresh"] is True, f"memory not fresh: {data['data']}"
    assert data["data"]["needs_rebuild"] is False

    # 4. Paper-status lookup by zotero_key
    papers_json = subprocess.run(
        pf + ["memory", "status", "--json"], capture_output=True, text=True, encoding="utf-8", env=env
    )
    status_data = json.loads(papers_json.stdout)
    paper_count = status_data["data"]["paper_count_db"]

    if paper_count > 0:
        # Get first paper's zotero_key from the db
        db_path = get_memory_db_path(test_vault)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT zotero_key FROM papers LIMIT 1").fetchone()
        conn.close()

        if row:
            key = row["zotero_key"]
            result = subprocess.run(
                pf + ["paper-status", key, "--json"],
                capture_output=True, text=True, encoding="utf-8", env=env,
            )
            assert result.returncode == 0
            data = json.loads(result.stdout)
            assert data["ok"] is True
            assert data["data"]["resolved"] is True
