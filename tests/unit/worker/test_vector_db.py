from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from paperforge.embedding.status import get_embed_status


def test_get_embed_status_reports_corruption_when_count_fails(tmp_path):
    vault = tmp_path / "vault"
    vectors_dir = vault / "System" / "PaperForge" / "vectors"
    vectors_dir.mkdir(parents=True)

    mock_collection = Mock()
    mock_collection.name = "paperforge_fulltext"
    mock_collection.count.side_effect = RuntimeError("Error loading hnsw index")
    mock_client = Mock()
    mock_client.list_collections.return_value = [mock_collection]

    with patch("chromadb.PersistentClient", return_value=mock_client):
        status = get_embed_status(vault)

    assert status["db_exists"] is True
    assert status["chunk_count"] == 0
    assert status["healthy"] is False
    assert "hnsw index" in status["error"]


def test_get_embed_status_uses_indexes_vectors_path_from_config(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        '{"vault_config":{"system_dir":"System","resources_dir":"Resources","literature_dir":"Literature","control_dir":"LiteratureControl","base_dir":"Bases","skill_dir":".opencode/skills"}}',
        encoding="utf-8",
    )
    vectors_dir = vault / "System" / "PaperForge" / "indexes" / "vectors"
    vectors_dir.mkdir(parents=True)

    mock_collection = Mock()
    mock_collection.name = "paperforge_fulltext"
    mock_collection.count.return_value = 12
    mock_client = Mock()
    mock_client.list_collections.return_value = [mock_collection]

    with patch("chromadb.PersistentClient", return_value=mock_client):
        status = get_embed_status(vault)

    assert status["db_exists"] is True
    assert status["chunk_count"] == 12
