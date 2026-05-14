from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy imports to avoid requiring chromadb unless actually used
_chroma = None
_ST = None

def _get_chroma():
    global _chroma
    if _chroma is None:
        import chromadb
        _chroma = chromadb
    return _chroma

def _get_st():
    global _ST
    if _ST is None:
        from sentence_transformers import SentenceTransformer
        _ST = SentenceTransformer
    return _ST


def _read_plugin_settings(vault: Path) -> dict:
    """Read plugin data.json for vector_db settings."""
    data_path = vault / ".obsidian" / "plugins" / "paperforge" / "data.json"
    if data_path.exists():
        return json.loads(data_path.read_text(encoding="utf-8"))
    return {}


def get_vector_db_path(vault: Path) -> Path:
    """Return the ChromaDB persistence directory."""
    from paperforge.config import paperforge_paths
    paths = paperforge_paths(vault)
    return (paths.get("memory_db", paths.get("index", vault / "System" / "PaperForge"))).parent / "vectors"


def get_collection(vault: Path):
    """Get or create the ChromaDB collection for paperforge."""
    chroma = _get_chroma()
    db_path = get_vector_db_path(vault)
    db_path.mkdir(parents=True, exist_ok=True)
    client = chroma.PersistentClient(path=str(db_path))
    # Delete and recreate if schema changed
    try:
        return client.get_or_create_collection(
            name="paperforge_fulltext",
            metadata={"hnsw:space": "cosine"},
        )
    except Exception:
        client.delete_collection("paperforge_fulltext")
        return client.create_collection(
            name="paperforge_fulltext",
            metadata={"hnsw:space": "cosine"},
        )


_cached_model = None
_cached_model_name = None


def get_embedding_model(vault: Path):
    """Load the embedding model based on plugin settings or default. Cached after first load."""
    global _cached_model, _cached_model_name
    settings = _read_plugin_settings(vault)
    mode = settings.get("vector_db_mode", "local")

    if mode == "api":
        return None

    model_name = settings.get("vector_db_model", "BAAI/bge-small-en-v1.5")

    if _cached_model is not None and _cached_model_name == model_name:
        return _cached_model

    ST = _get_st()
    logger.info("Loading embedding model: %s", model_name)

    hf_endpoint = settings.get("vector_db_hf_endpoint", "") or os.environ.get("HF_ENDPOINT", "")

    if hf_endpoint:
        local_path = _download_model_via_mirror(model_name, hf_endpoint)
        if local_path and (local_path / "modules.json").exists():
            logger.info("Loading from local mirror copy: %s", local_path)
            _cached_model = ST(str(local_path))
            _cached_model_name = model_name
            return _cached_model

    _cached_model = ST(model_name)
    _cached_model_name = model_name
    return _cached_model


def _download_model_via_mirror(model_name: str, mirror: str) -> Path | None:
    """Download model files from a mirror URL to a local cache directory.
    Bypasses huggingface_hub entirely by using urllib directly."""
    try:
        import urllib.request
    except Exception:
        return None

    mirror = mirror.rstrip("/")
    base_url = f"{mirror}/{model_name}/resolve/main"
    local_dir = Path.home() / ".cache" / "paperforge" / "models" / model_name.replace("/", "--")

    files = [
        "config.json", "modules.json", "config_sentence_transformers.json",
        "sentence_bert_config.json", "special_tokens_map.json",
        "tokenizer.json", "tokenizer_config.json", "vocab.txt",
        "model.safetensors", "pytorch_model.bin",
        "1_Pooling/config.json",
    ]

    local_dir.mkdir(parents=True, exist_ok=True)

    # Build headers from HF_TOKEN
    hf_token = os.environ.get("HF_TOKEN", "")
    headers = {}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    for f in files:
        dest = local_dir / f
        if dest.exists() and dest.stat().st_size > 0:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f"{base_url}/{f}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=600) as resp:
                with open(dest, "wb") as out:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        out.write(chunk)
        except Exception:
            pass

    # Return path only if core files exist
    has_weights = (local_dir / "model.safetensors").exists() or (local_dir / "pytorch_model.bin").exists()
    has_config = (local_dir / "modules.json").exists() and (local_dir / "config.json").exists()
    return local_dir if has_weights and has_config else None
    return _cached_model


def embed_paper(vault: Path, zotero_key: str, chunks: list[dict]) -> int:
    """Embed chunks for one paper and insert into ChromaDB. Returns count."""
    collection = get_collection(vault)
    model = get_embedding_model(vault)

    if model is None:
        # API mode
        return _embed_paper_api(vault, zotero_key, chunks, collection)

    # Local mode
    texts = [c["text"] for c in chunks]
    ids = [f"{zotero_key}_{c['chunk_index']}" for c in chunks]
    metadatas = [
        {
            "paper_id": zotero_key,
            "section": c["section"],
            "page_number": c["page_number"],
            "chunk_index": c["chunk_index"],
            "token_estimate": c["token_estimate"],
        }
        for c in chunks
    ]

    embeddings = model.encode(texts, show_progress_bar=False).tolist()

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    return len(chunks)


def _embed_paper_api(vault, zotero_key, chunks, collection) -> int:
    """Embed using OpenAI API."""
    settings = _read_plugin_settings(vault)
    api_key = settings.get("vector_db_api_key", "")
    if not api_key:
        env_file = vault / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not api_key:
        raise ValueError("No API key configured for vector DB")

    texts = [c["text"] for c in chunks]
    ids = [f"{zotero_key}_{c['chunk_index']}" for c in chunks]
    metadatas = [
        {"paper_id": zotero_key, "section": c["section"],
         "page_number": c["page_number"], "chunk_index": c["chunk_index"],
         "token_estimate": c["token_estimate"]}
        for c in chunks
    ]

    from openai import OpenAI
    api_model = os.environ.get("VECTOR_DB_API_MODEL", "") or settings.get("vector_db_api_model", "text-embedding-3-small")
    api_base = os.environ.get("VECTOR_DB_API_BASE", "") or settings.get("vector_db_api_base", None) or None
    api_key = os.environ.get("VECTOR_DB_API_KEY", "") or api_key
    logger.info("API mode: base_url=%s, model=%s", api_base or "(default OpenAI)", api_model)
    client = OpenAI(api_key=api_key, base_url=api_base)
    response = client.embeddings.create(model=api_model, input=texts)
    embeddings = [e.embedding for e in response.data]

    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return len(chunks)


def delete_paper_vectors(vault: Path, zotero_key: str) -> int:
    """Delete all chunks for a paper from ChromaDB."""
    collection = get_collection(vault)
    try:
        results = collection.get(where={"paper_id": zotero_key})
        ids = results.get("ids", [])
        if ids:
            collection.delete(ids=ids)
        return len(ids)
    except Exception:
        return 0


def retrieve_chunks(vault: Path, query: str, limit: int = 5, expand: bool = True) -> list[dict]:
    """Search for chunks matching the query. Returns list with adjacent context."""
    collection = get_collection(vault)
    model = get_embedding_model(vault)

    if model is None:
        # API mode
        settings = _read_plugin_settings(vault)
        api_key = settings.get("vector_db_api_key", "")
        env_file = vault / ".env"
        if not api_key and env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
        if not api_key:
            raise ValueError("No API key configured for vector DB")
        from openai import OpenAI
        api_base = os.environ.get("VECTOR_DB_API_BASE", "") or settings.get("vector_db_api_base", None) or None
        api_key = os.environ.get("VECTOR_DB_API_KEY", "") or api_key
        client = OpenAI(api_key=api_key, base_url=api_base)
        api_model = os.environ.get("VECTOR_DB_API_MODEL", "") or settings.get("vector_db_api_model", "text-embedding-3-small")
        response = client.embeddings.create(model=api_model, input=query)
        query_embedding = response.data[0].embedding
    else:
        query_embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=limit * 3 if expand else limit,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        chunks.append({
            "paper_id": meta["paper_id"],
            "section": meta.get("section", "Text"),
            "page_number": meta.get("page_number", 1),
            "chunk_index": meta.get("chunk_index", 0),
            "chunk_text": doc,
            "score": round(1.0 - dist, 4),  # cosine distance → similarity
        })

    return chunks


def get_embed_status(vault: Path) -> dict:
    """Get vector DB status."""
    db_path = get_vector_db_path(vault)
    exists = db_path.exists()
    chunk_count = 0
    if exists:
        try:
            collection = get_collection(vault)
            chunk_count = collection.count()
        except Exception:
            pass

    settings = _read_plugin_settings(vault)
    mode = settings.get("vector_db_mode", "local")
    model = settings.get("vector_db_api_model", "text-embedding-3-small") if mode == "api" else settings.get("vector_db_model", "BAAI/bge-small-en-v1.5")
    return {
        "db_exists": exists,
        "chunk_count": chunk_count,
        "model": model,
        "mode": mode,
    }
