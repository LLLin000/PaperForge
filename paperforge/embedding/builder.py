from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding._chroma import get_collection
from paperforge.embedding.backends import get_vector_backend
from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider
from paperforge.memory.db import get_connection, get_memory_db_path

logger = logging.getLogger(__name__)


def embed_paper(vault: Path, zotero_key: str, chunks: list[dict]) -> int:
    """Embed chunks for one paper using API and insert into vector DB. Returns count."""
    backend = get_vector_backend(vault)
    provider = OpenAICompatibleProvider(vault)

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

    embeddings = provider.encode(texts)
    backend.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return len(chunks)


def embed_body_units(vault: Path, zotero_key: str, body_units: list[dict]) -> int:
    """Embed body units into the paperforge_body collection. Returns count."""
    if not body_units:
        return 0
    provider = OpenAICompatibleProvider(vault)

    texts = [u["unit_text"] for u in body_units]
    ids = [u["unit_id"] for u in body_units]
    metadatas = [
        {
            "paper_id": zotero_key,
            "section_path": u.get("section_path", ""),
            "unit_id": u["unit_id"],
            "unit_kind": u.get("unit_kind", "body"),
            "section_level": u.get("section_level", 0),
            "token_estimate": u.get("token_estimate", 0),
        }
        for u in body_units
    ]

    embeddings = provider.encode(texts)
    collection = get_collection(vault, name="paperforge_body")
    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return len(body_units)


def get_body_units_for_embedding(vault: Path, key: str) -> list[dict]:
    """Read indexable body_units from paperforge.db for a paper."""
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return []
    conn = get_connection(db_path, read_only=True)
    try:
        rows = conn.execute(
            """SELECT unit_id, paper_id, section_path, section_level,
                      section_title, unit_text, unit_kind, part_ordinal,
                      page_span_json, token_estimate
               FROM body_units
               WHERE paper_id=? AND indexable=1
               ORDER BY unit_id""",
            (key,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
