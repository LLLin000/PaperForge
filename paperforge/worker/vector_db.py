from __future__ import annotations

import os


def _preflight_check(vault, settings: dict) -> dict:
    """Check prerequisites for embed build. Returns {ok: bool, error: str, fix: str}."""
    from pathlib import Path

    from paperforge.worker._utils import pipeline_paths

    # 1. chromadb
    try:
        import chromadb  # noqa: F401
    except ImportError:
        return {"ok": False, "error": "chromadb is not installed", "fix": 'Run: pip install "paperforge[vector]"'}

    # 2. Mode-specific deps
    mode = settings.get("vector_db_mode", "local")
    if mode == "local":
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            return {
                "ok": False,
                "error": "sentence-transformers not installed",
                "fix": 'Run: pip install "paperforge[vector]" or switch to API mode',
            }
    elif mode == "api":
        try:
            import openai  # noqa: F401
        except ImportError:
            return {
                "ok": False,
                "error": "openai not installed",
                "fix": 'Run: pip install "paperforge[vector]" or switch to local mode',
            }
        api_key = settings.get("vector_db_api_key") or os.environ.get("OPENAI_API_KEY") or os.environ.get("VECTOR_DB_API_KEY")
        if not api_key:
            return {"ok": False, "error": "API key not configured", "fix": "Set API Key in plugin settings or OPENAI_API_KEY in .env"}

    # 3. OCR done papers
    paths = pipeline_paths(vault)
    idx_path = paths.get("indexes", Path("")) / "formal-library.json" if paths.get("indexes") else None
    if idx_path and idx_path.exists():
        import json

        data = json.loads(idx_path.read_text(encoding="utf-8"))
        items = data.get("items", []) if isinstance(data, dict) else data
        done = sum(1 for i in (items or []) if i.get("ocr_status") == "done")
        if done == 0:
            return {"ok": False, "error": "No papers with OCR completed", "fix": "Run paperforge ocr first"}

    return {"ok": True}


def get_embed_status(vault) -> dict:
    """Check if vector index exists and has content."""
    from pathlib import Path
    from paperforge.config import paperforge_paths
    paths = paperforge_paths(vault)
    vectors_dir = paths.get("vectors", paths.get("paperforge", Path()) / "vectors")
    
    status = {"exists": False, "chunk_count": 0, "collection_name": ""}
    
    if not vectors_dir or not vectors_dir.exists():
        return status
    
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(vectors_dir))
        collections = client.list_collections()
        if collections:
            col = collections[0]
            status["exists"] = True
            status["collection_name"] = col.name
            status["chunk_count"] = col.count()
    except Exception:
        pass
    
    return status
