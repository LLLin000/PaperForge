from __future__ import annotations

from unittest.mock import Mock, patch

from paperforge.embedding.status import get_embed_status


def _mock_backend(health_result: dict) -> Mock:
    backend = Mock()
    backend.health.return_value = health_result
    return backend


def test_get_embed_status_reports_corruption_when_count_fails(tmp_path):
    vault = tmp_path / "vault"
    vectors_dir = vault / "System" / "PaperForge" / "indexes" / "vectors"
    vectors_dir.mkdir(parents=True)

    mock_backend = _mock_backend({
        "healthy": False,
        "chunk_count": 0,
        "error": "Error loading hnsw index",
        "corrupted": True,
    })

    with patch("paperforge.embedding.status.get_vector_backend", return_value=mock_backend):
        status = get_embed_status(vault)

    assert status["db_exists"] is True
    assert status["chunk_count"] == 0
    assert status["healthy"] is False
    assert "hnsw" in status["error"].lower()


def test_get_embed_status_uses_indexes_vectors_path_from_config(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        '{"vault_config":{"system_dir":"System"}}',
        encoding="utf-8",
    )
    vectors_dir = vault / "System" / "PaperForge" / "indexes" / "vectors"
    vectors_dir.mkdir(parents=True)

    mock_backend = _mock_backend({
        "healthy": True,
        "chunk_count": 12,
    })

    with patch("paperforge.embedding.status.get_vector_backend", return_value=mock_backend):
        status = get_embed_status(vault)

    assert status["db_exists"] is True
    assert status["chunk_count"] == 12
