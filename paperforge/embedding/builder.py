from __future__ import annotations
from dataclasses import dataclass

import logging
from pathlib import Path

from paperforge.embedding._chroma import get_collection
from paperforge.retrieval.manifest import RETRIEVAL_POLICY_VERSION, compute_body_units_hash, compute_object_units_hash
from paperforge.embedding.backends import get_vector_backend
from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider
from paperforge.memory.db import get_connection, get_memory_db_path

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingPayload:
    """准备阶段产出的载荷：未 encode。"""
    collection_name: str
    texts: list[str]
    ids: list[str]
    metadatas: list[dict]


@dataclass
class EncodedPayload:
    """encode 后的载荷。必须带 texts（不可从 metadata 反推）。"""
    collection_name: str
    texts: list[str]
    ids: list[str]
    metadatas: list[dict]
    embeddings: list[list[float]]


@dataclass
class PaperEmbeddingJob:
    """一篇论文的所有载荷。"""
    paper_id: str
    payloads: list[EmbeddingPayload]


@dataclass
class PaperEncodedBundle:
    """一篇论文 encode 完成后的结果。"""
    paper_id: str
    payloads: list[EncodedPayload]
    chunk_count: int


def prepare_legacy_payload(zotero_key: str, chunks: list[dict]) -> EmbeddingPayload:
    texts = [c["text"] for c in chunks]
    ids = [f"{zotero_key}_{c['chunk_index']}" for c in chunks]
    metadatas = [
        {
            "paper_id": zotero_key,
            "section": c.get("section", ""),
            "page_number": c.get("page_number", 0),
            "chunk_index": c.get("chunk_index", i),
            "token_estimate": c.get("token_estimate", 0),
        }
        for i, c in enumerate(chunks)
    ]
    return EmbeddingPayload(
        collection_name="paperforge_fulltext",
        texts=texts, ids=ids, metadatas=metadatas,
    )


def prepare_body_payload(zotero_key: str, body_units: list[dict]) -> EmbeddingPayload:
    current_hash = compute_body_units_hash(body_units)
    texts = [u["unit_text"] for u in body_units]
    ids = [u["unit_id"] for u in body_units]
    metadatas = [
        {
            "paper_id": zotero_key,
            "section_path": u.get("section_path", ""),
            "unit_id": u["unit_id"],
            "unit_kind": "body",
            "body_units_hash": current_hash,
            "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
            "token_estimate": u.get("token_estimate", 0),
        }
        for u in body_units
    ]
    return EmbeddingPayload(
        collection_name="paperforge_body",
        texts=texts, ids=ids, metadatas=metadatas,
    )


def prepare_object_payload(zotero_key: str, object_units: list[dict]) -> EmbeddingPayload:
    current_hash = compute_object_units_hash(object_units)
    texts = [
        "\n".join(
            x for x in [
                u.get("object_label", ""),
                u.get("caption_text", ""),
                u.get("nearby_body_text", ""),
            ]
            if x
        )
        for u in object_units
    ]
    ids = [u["unit_id"] for u in object_units]
    metadatas = [
        {
            "paper_id": zotero_key,
            "section_path": u.get("section_path", ""),
            "unit_id": u["unit_id"],
            "unit_kind": "object",
            "object_kind": u.get("object_kind", ""),
            "object_label": u.get("object_label", ""),
            "object_units_hash": current_hash,
            "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
            "token_estimate": u.get("token_estimate", 0),
        }
        for u in object_units
    ]
    return EmbeddingPayload(
        collection_name="paperforge_objects",
        texts=texts, ids=ids, metadatas=metadatas,
    )


def encode_payload(vault: Path, payload: EmbeddingPayload,
                    provider: OpenAICompatibleProvider | None = None) -> EncodedPayload:
    if provider is None:
        provider = OpenAICompatibleProvider(vault)
    embeddings = provider.encode(payload.texts)
    return EncodedPayload(
        collection_name=payload.collection_name,
        texts=payload.texts,
        ids=payload.ids,
        metadatas=payload.metadatas,
        embeddings=embeddings,
    )


def encode_paper_job(vault: Path, job: PaperEmbeddingJob) -> PaperEncodedBundle:
    provider = OpenAICompatibleProvider(vault)
    encoded_payloads: list[EncodedPayload] = []
    total_chunks = 0
    for payload in job.payloads:
        encoded = encode_payload(vault, payload, provider=provider)
        encoded_payloads.append(encoded)
        total_chunks += len(payload.ids)
    return PaperEncodedBundle(
        paper_id=job.paper_id,
        payloads=encoded_payloads,
        chunk_count=total_chunks,
    )


def write_encoded_payload(vault: Path, encoded: EncodedPayload):
    col = get_collection(vault, name=encoded.collection_name)
    col.add(
        ids=encoded.ids,
        embeddings=encoded.embeddings,
        documents=encoded.texts,
        metadatas=encoded.metadatas,
    )


def prepare_payloads_for_entry(vault: Path, key: str, has_body: bool, has_object: bool,
                                body_units: list, object_units: list,
                                fulltext_rel: str = "") -> list[EmbeddingPayload] | None:
    payloads: list[EmbeddingPayload] = []
    if has_body and body_units:
        payloads.append(prepare_body_payload(key, body_units))
    if has_object and object_units:
        payloads.append(prepare_object_payload(key, object_units))
    if not has_body and not has_object and fulltext_rel:
        from paperforge.memory.chunker import chunk_fulltext
        fulltext_path = vault / fulltext_rel
        chunks = chunk_fulltext(fulltext_path)
        if chunks:
            payloads.append(prepare_legacy_payload(key, chunks))
    return payloads if payloads else None


def embed_paper(vault: Path, zotero_key: str, chunks: list[dict]) -> int:
    """Embed chunks for one paper using API and insert into vector DB. Returns count."""
    payload = prepare_legacy_payload(zotero_key, chunks)
    encoded = encode_payload(vault, payload)
    write_encoded_payload(vault, encoded)
    return len(chunks)

def embed_body_units(vault: Path, zotero_key: str, body_units: list[dict]) -> int:
    """Embed body units into the paperforge_body collection. Returns count."""
    if not body_units:
        return 0
    payload = prepare_body_payload(zotero_key, body_units)
    encoded = encode_payload(vault, payload)
    write_encoded_payload(vault, encoded)
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


def get_object_units_for_embedding(vault: Path, key: str) -> list[dict]:
    """Fetch object_units from the memory DB for a given paper."""
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return []
    conn = get_connection(db_path, read_only=True)
    try:
        rows = conn.execute(
            """SELECT unit_id, paper_id, section_path,
                      object_kind, object_label, caption_text, nearby_body_text,
                      page_span_json, token_estimate
               FROM object_units
               WHERE paper_id=? AND indexable=1
               ORDER BY unit_id""",
            (key,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def embed_object_units(vault: Path, zotero_key: str, object_units: list[dict]) -> int:
    """Embed object_units into paperforge_objects collection."""
    if not object_units:
        return 0
    payload = prepare_object_payload(zotero_key, object_units)
    encoded = encode_payload(vault, payload)
    write_encoded_payload(vault, encoded)
    return len(object_units)
