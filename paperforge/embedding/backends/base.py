from __future__ import annotations

from pathlib import Path
from typing import Protocol


class VectorBackend(Protocol):
    """Adapter protocol for vector database backends.

    The backend wraps all vector DB operations behind a single interface,
    so the rest of the codebase never depends on a specific vector DB library.
    """

    def add(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None: ...

    def query(
        self, *, query_embedding: list[float], limit: int
    ) -> list[dict]: ...

    def delete_paper(self, paper_id: str) -> int: ...

    def health(self) -> dict: ...
