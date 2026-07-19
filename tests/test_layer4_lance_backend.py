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


class TestAvailableBackends:
    """Status-level backend enumeration (always available, no lancedb dependency)."""

    def test_get_available_backends_lists_chroma_and_lance(self):
        from paperforge.embedding.status import get_available_backends

        backends = get_available_backends()

        assert "chroma" in backends
        assert backends["chroma"]["installed"] is True
        assert backends["chroma"]["selected"] is True

        assert "lancedb" in backends
        assert backends["lancedb"]["installed"] is False
        assert backends["lancedb"]["selected"] is False
        assert backends["lancedb"]["supports_hybrid"] is True
        assert backends["lancedb"]["supports_multimodal"] is True

    def test_get_available_backends_returns_dict_with_expected_keys(self):
        from paperforge.embedding.status import get_available_backends

        backends = get_available_backends()
        for name, info in backends.items():
            for key in ("installed", "selected", "supports_hybrid", "supports_multimodal"):
                assert key in info, f"{name} missing {key}"
