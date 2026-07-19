from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    def encode_single(self, text: str) -> list[float]:
        ...
