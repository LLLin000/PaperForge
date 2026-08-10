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

    # 3. API key (#173/C1: credential authority; the preflight consumes the
    #    STATUS read model so backend faults are distinguishable from a
    #    genuinely missing credential)
    from paperforge.credentials import CredentialKey, status as credential_status

    cred_state = credential_status(CredentialKey("embedding")).state
    if cred_state == "missing":
        return {
            "ok": False,
            "error": "API key not configured",
            "fix": "Run `paperforge auth set embedding --stdin` or supply PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT",
        }
    if cred_state != "available":
        return {
            "ok": False,
            "error": f"Embedding credential unavailable ({cred_state})",
            "fix": "Run `paperforge auth status embedding` for remediation",
        }
    # #173 review: preflight stays a pure presence/status read model — the
    # secret value is never retrieved here; handlers resolve it.

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
