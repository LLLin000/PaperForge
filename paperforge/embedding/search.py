from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding._chroma import get_collection
from paperforge.embedding.backends import get_vector_backend
from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

RETRIEVAL_COLLECTIONS = ["paperforge_fulltext", "paperforge_body", "paperforge_objects"]


def retrieve_chunks(vault: Path, query: str, limit: int = 5, expand: bool = True) -> list[dict]:
    """Search chunks via API embedding. Returns list with metadata and similarity scores."""
    backend = get_vector_backend(vault)
    provider = OpenAICompatibleProvider(vault)
    query_embedding = provider.encode_single(query)
    return backend.query(query_embedding=query_embedding, limit=limit * 3 if expand else limit)


def merge_retrieve(vault: Path, query: str, limit: int = 5, expand: bool = True) -> list[dict]:
    """Query both collections, merge with unit-level dedup and per-paper cap."""
    provider = OpenAICompatibleProvider(vault)
    q_emb = provider.encode_single(query)
    n = limit * 2 if expand else limit

    all_results: list[dict] = []
    for name in RETRIEVAL_COLLECTIONS:
        try:
            col = get_collection(vault, name=name)
            res = col.query(
                query_embeddings=[q_emb],
                n_results=n,
                include=["documents", "metadatas", "distances"],
            )
            for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
                all_results.append({
                    "paper_id": meta.get("paper_id", ""),
                    "section_path": meta.get("section_path", meta.get("section", "")),
                    "chunk_text": doc,
                    "score": round(1.0 - dist, 4),
                    "source": {
                        "paperforge_fulltext": "legacy_chunk",
                        "paperforge_body": "body_unit",
                        "paperforge_objects": "object_unit",
                    }[name],
                    "unit_id": meta.get("unit_id") or meta.get("chunk_index", ""),
                    "object_kind": meta.get("object_kind", ""),
                    "object_label": meta.get("object_label", ""),
                })
        except Exception as exc:
            logger.warning("merge_retrieve: collection %s query failed: %s", name, exc)
            continue

    all_results.sort(key=lambda r: r["score"], reverse=True)
    seen: set = set()
    per_paper: dict[str, int] = {}
    merged: list[dict] = []
    for r in all_results:
        dedupe_key = (r["source"], r["unit_id"]) if r.get("unit_id") else (
            r["source"], r["paper_id"], hash(r["chunk_text"])
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        pid = r["paper_id"]
        if per_paper.get(pid, 0) >= 2:
            continue
        per_paper[pid] = per_paper.get(pid, 0) + 1
        merged.append(r)
        if len(merged) >= limit:
            break
    return merged
