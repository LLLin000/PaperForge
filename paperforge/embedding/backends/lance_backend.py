from __future__ import annotations

import lancedb


class LanceBackend:
    """LanceDB-based vector backend (evaluation seam, not the default).

    This backend advertises hybrid and multimodal capabilities that the
    Chroma backend does not support, making it suitable for evaluation
    without switching the production default.
    """

    def __init__(self, dataset_path: str) -> None:
        self.db = lancedb.connect(str(dataset_path))

    def capabilities(self) -> dict:
        return {
            "backend": "lancedb",
            "supports_hybrid": True,
            "supports_multimodal": True,
        }
