from __future__ import annotations

import pytest


class TestLanceBackendCapabilities:
    """LanceDB backend capability reporting (optional — skips when lancedb missing)."""

    def test_lance_backend_advertises_file_based_capabilities(self):
        pytest.importorskip("lancedb")
        from paperforge.embedding.backends.lance_backend import LanceBackend

        backend = LanceBackend("/tmp/lance")
        caps = backend.capabilities()
        assert caps["backend"] == "lancedb"
        assert caps["supports_hybrid"] is True
        assert caps["supports_multimodal"] is True


