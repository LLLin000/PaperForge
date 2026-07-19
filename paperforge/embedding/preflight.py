from __future__ import annotations

import os
from pathlib import Path


def _preflight_check(vault: Path, settings: dict | None = None) -> dict:
    """Check prerequisites for embed build. Returns {ok: bool, error: str, fix: str}."""

    # 1. openai package
    try:
        import openai  # noqa: F401
    except ImportError:
        return {
            "ok": False,
            "error": "openai is not installed",
            "fix": 'Run: pip install "paperforge[vector]"',
        }

    # 3. API key
    api_key = None
    if settings:
        api_key = settings.get("vector_db_api_key")
    if not api_key:
        api_key = os.environ.get("VECTOR_DB_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        env_path = vault / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("VECTOR_DB_API_KEY=") or line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        return {
            "ok": False,
            "error": "API key not configured",
            "fix": "Set VECTOR_DB_API_KEY or OPENAI_API_KEY in .env or plugin settings",
        }

    # 4. OCR done papers
    from paperforge.worker._utils import pipeline_paths
    paths = pipeline_paths(vault)
    idx_path = paths.get("indexes", Path("")) / "formal-library.json" if paths.get("indexes") else None
    if idx_path and idx_path.exists():
        import json
        data = json.loads(idx_path.read_text(encoding="utf-8"))
        items = data.get("items", []) if isinstance(data, dict) else data
        done = sum(1 for i in (items or []) if i.get("ocr_status") == "done")
        if done == 0:
            return {
                "ok": False,
                "error": "No papers with OCR completed",
                "fix": "Run paperforge ocr first",
            }

    return {"ok": True}
