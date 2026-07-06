"""Tests for PR9B: Embed Parallel Encode."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

import paperforge.config
from paperforge.worker._utils import pipeline_paths as _pp

paperforge.config.pipeline_paths = _pp

from paperforge.embedding.builder import (
    EmbeddingPayload,
    EncodedPayload,
    PaperEmbeddingJob,
    PaperEncodedBundle,
    prepare_legacy_payload,
    prepare_body_payload,
    prepare_object_payload,
    prepare_payloads_for_entry,
    encode_payload,
    encode_paper_job,
    write_encoded_payload,
    embed_paper,
)


# ---------------------------------------------------------------------------
# prepare_legacy_payload
# ---------------------------------------------------------------------------

class TestPrepareLegacyPayload:
    """Tests for prepare_legacy_payload."""

    def test_creates_correct_structure(self):
        chunks = [
            {"text": "Hello", "chunk_index": 0, "section": "intro",
             "page_number": 1, "token_estimate": 5},
            {"text": "World", "chunk_index": 1, "section": "methods",
             "page_number": 2, "token_estimate": 10},
        ]
        payload = prepare_legacy_payload("key123", chunks)
        assert payload.collection_name == "paperforge_fulltext"
        assert payload.texts == ["Hello", "World"]
        assert payload.ids == ["key123_0", "key123_1"]
        assert payload.metadatas[0]["paper_id"] == "key123"
        assert payload.metadatas[0]["section"] == "intro"
        assert payload.metadatas[1]["section"] == "methods"
        assert payload.metadatas[0]["page_number"] == 1
        assert payload.metadatas[1]["page_number"] == 2
        assert payload.metadatas[0]["chunk_index"] == 0
        assert payload.metadatas[1]["chunk_index"] == 1
        assert payload.metadatas[0]["token_estimate"] == 5
        assert payload.metadatas[1]["token_estimate"] == 10
        assert len(payload.texts) == 2
        assert len(payload.ids) == 2
        assert len(payload.metadatas) == 2

    def test_handles_single_chunk(self):
        chunks = [{"text": "Only", "chunk_index": 0}]
        payload = prepare_legacy_payload("k1", chunks)
        assert payload.texts == ["Only"]
        assert payload.ids == ["k1_0"]

    def test_handles_empty_chunks(self):
        payload = prepare_legacy_payload("k1", [])
        assert payload.texts == []
        assert payload.ids == []
        assert payload.metadatas == []


# ---------------------------------------------------------------------------
# prepare_body_payload
# ---------------------------------------------------------------------------

class TestPrepareBodyPayload:
    """Tests for prepare_body_payload."""

    def test_creates_correct_structure(self):
        body_units = [
            {"unit_text": "body1", "unit_id": "bid1", "section_path": "1.1",
             "token_estimate": 5},
            {"unit_text": "body2", "unit_id": "bid2", "section_path": "1.2",
             "token_estimate": 8},
        ]
        payload = prepare_body_payload("key123", body_units)
        assert payload.collection_name == "paperforge_body"
        assert payload.texts == ["body1", "body2"]
        assert payload.ids == ["bid1", "bid2"]
        assert payload.metadatas[0]["unit_kind"] == "body"
        assert payload.metadatas[0]["paper_id"] == "key123"
        assert payload.metadatas[0]["section_path"] == "1.1"
        assert payload.metadatas[1]["section_path"] == "1.2"
        assert payload.metadatas[0]["unit_id"] == "bid1"
        assert payload.metadatas[1]["unit_id"] == "bid2"
        assert payload.metadatas[0]["token_estimate"] == 5
        assert payload.metadatas[1]["token_estimate"] == 8
        assert "body_units_hash" in payload.metadatas[0]
        assert "retrieval_policy_version" in payload.metadatas[0]
        assert len(payload.texts) == 2
        assert len(payload.ids) == 2
        assert len(payload.metadatas) == 2

    def test_handles_empty_units(self):
        payload = prepare_body_payload("k1", [])
        assert payload.texts == []
        assert payload.ids == []
        assert payload.metadatas == []


# ---------------------------------------------------------------------------
# prepare_object_payload
# ---------------------------------------------------------------------------

class TestPrepareObjectPayload:
    """Tests for prepare_object_payload."""

    def test_creates_correct_structure(self):
        object_units = [
            {"unit_id": "oid1", "paper_id": "key123", "object_kind": "figure",
             "object_label": "Fig 1", "section_path": "2",
             "token_estimate": 10},
            {"unit_id": "oid2", "paper_id": "key123", "object_kind": "table",
             "object_label": "Table 1", "section_path": "3",
             "token_estimate": 8},
        ]
        payload = prepare_object_payload("key123", object_units)
        assert payload.collection_name == "paperforge_objects"
        assert payload.ids == ["oid1", "oid2"]
        assert payload.metadatas[0]["unit_kind"] == "object"
        assert payload.metadatas[0]["object_kind"] == "figure"
        assert payload.metadatas[1]["object_kind"] == "table"
        assert payload.metadatas[0]["object_label"] == "Fig 1"
        assert payload.metadatas[1]["object_label"] == "Table 1"
        assert payload.metadatas[0]["paper_id"] == "key123"
        assert payload.metadatas[0]["section_path"] == "2"
        assert payload.metadatas[1]["section_path"] == "3"
        assert payload.metadatas[0]["unit_id"] == "oid1"
        assert payload.metadatas[1]["unit_id"] == "oid2"
        assert payload.metadatas[0]["token_estimate"] == 10
        assert payload.metadatas[1]["token_estimate"] == 8
        assert "object_units_hash" in payload.metadatas[0]
        assert "retrieval_policy_version" in payload.metadatas[0]
        assert len(payload.ids) == 2
        assert len(payload.metadatas) == 2
    def test_texts_include_label_and_caption(self):
        object_units = [
            {"unit_id": "oid1", "paper_id": "key123", "object_kind": "figure",
             "object_label": "Fig 1", "caption_text": "A caption",
             "nearby_body_text": "Nearby", "section_path": "2",
             "token_estimate": 10},
        ]
        payload = prepare_object_payload("key123", object_units)
        assert len(payload.texts) == 1
        assert "Fig 1" in payload.texts[0]
        assert "A caption" in payload.texts[0]
        assert "Nearby" in payload.texts[0]

    def test_handles_empty_units(self):
        payload = prepare_object_payload("k1", [])
        assert payload.texts == []
        assert payload.ids == []
        assert payload.metadatas == []


# ---------------------------------------------------------------------------
# prepare_payloads_for_entry — routing
# ---------------------------------------------------------------------------

class TestPreparePayloadsForEntry:
    """Tests for prepare_payloads_for_entry routing."""

    def test_returns_body_payload_when_has_body(self):
        result = prepare_payloads_for_entry(
            Path("/vault"), "key123",
            has_body=True, has_object=False,
            body_units=[{"unit_text": "body1", "unit_id": "bid1",
                          "section_path": "1.1", "token_estimate": 5}],
            object_units=[],
        )
        assert result is not None
        assert len(result) == 1
        assert result[0].collection_name == "paperforge_body"

    def test_returns_body_and_object_payloads(self):
        result = prepare_payloads_for_entry(
            Path("/vault"), "key123",
            has_body=True, has_object=True,
            body_units=[{"unit_text": "body1", "unit_id": "bid1",
                          "section_path": "1.1", "token_estimate": 5}],
            object_units=[{"unit_id": "oid1", "paper_id": "key123",
                           "object_kind": "figure", "object_label": "Fig 1",
                           "section_path": "2", "token_estimate": 10}],
        )
        assert result is not None
        assert len(result) == 2
        assert result[0].collection_name == "paperforge_body"
        assert result[1].collection_name == "paperforge_objects"

    def test_returns_none_when_no_units_and_no_fulltext(self):
        result = prepare_payloads_for_entry(
            Path("/vault"), "key123",
            has_body=False, has_object=False,
            body_units=[], object_units=[], fulltext_rel="",
        )
        assert result is None

    def test_returns_legacy_payload_when_no_units_with_fulltext(self):
        with patch("paperforge.memory.chunker.chunk_fulltext") as mock_chunk:
            mock_chunk.return_value = [
                {"text": "chunk1", "chunk_index": 0, "section": "",
                 "page_number": 1, "token_estimate": 5},
            ]
            result = prepare_payloads_for_entry(
                Path("/vault"), "key123",
                has_body=False, has_object=False,
                body_units=[], object_units=[], fulltext_rel="fulltext/key123.md",
            )
        assert result is not None
        assert len(result) == 1
        assert result[0].collection_name == "paperforge_fulltext"

    def test_returns_none_when_no_units_and_empty_fulltext_path(self):
        result = prepare_payloads_for_entry(
            Path("/vault"), "key123",
            has_body=False, has_object=False,
            body_units=[], object_units=[], fulltext_rel="",
        )
        assert result is None

# ---------------------------------------------------------------------------
# encode_payload
# ---------------------------------------------------------------------------

class TestEncodePayload:
    """Tests for encode_payload."""

    @patch("paperforge.embedding.builder.OpenAICompatibleProvider")
    def test_encodes_texts_and_returns_encoded_payload(self, mock_provider_cls):
        mock_provider = MagicMock()
        mock_provider.encode.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_provider_cls.return_value = mock_provider

        payload = EmbeddingPayload(
            collection_name="paperforge_body",
            texts=["hello", "world"],
            ids=["a", "b"],
            metadatas=[{"paper_id": "k1"}, {"paper_id": "k1"}],
        )
        result = encode_payload(Path("/vault"), payload)

        assert isinstance(result, EncodedPayload)
        assert len(result.embeddings) == 2
        assert result.embeddings == [[0.1, 0.2], [0.3, 0.4]]
        assert result.collection_name == "paperforge_body"
        assert result.texts == ["hello", "world"]
        assert result.ids == ["a", "b"]
        assert result.metadatas == [{"paper_id": "k1"}, {"paper_id": "k1"}]

    @patch("paperforge.embedding.builder.OpenAICompatibleProvider")
    def test_handles_empty_texts(self, mock_provider_cls):
        mock_provider = MagicMock()
        mock_provider.encode.return_value = []
        mock_provider_cls.return_value = mock_provider

        payload = EmbeddingPayload(
            collection_name="paperforge_body",
            texts=[], ids=[], metadatas=[],
        )
        result = encode_payload(Path("/vault"), payload)
        assert result.embeddings == []
        assert result.texts == []

    @patch("paperforge.embedding.builder.OpenAICompatibleProvider")
    def test_single_embedding(self, mock_provider_cls):
        mock_provider = MagicMock()
        mock_provider.encode.return_value = [[0.99]]
        mock_provider_cls.return_value = mock_provider

        payload = EmbeddingPayload(
            collection_name="paperforge_body",
            texts=["x"], ids=["x1"], metadatas=[{"paper_id": "k"}],
        )
        result = encode_payload(Path("/vault"), payload)
        assert result.embeddings == [[0.99]]


# ---------------------------------------------------------------------------
# encode_paper_job
# ---------------------------------------------------------------------------

class TestEncodePaperJob:
    """Tests for encode_paper_job."""

    @patch("paperforge.embedding.builder.OpenAICompatibleProvider")
    def test_bundles_all_payloads(self, mock_provider_cls):
        mock_provider = MagicMock()
        mock_provider.encode.return_value = [[0.1]]
        mock_provider_cls.return_value = mock_provider

        job = PaperEmbeddingJob(
            paper_id="key123",
            payloads=[
                EmbeddingPayload(
                    collection_name="paperforge_body",
                    texts=["body1"], ids=["b1"],
                    metadatas=[{"paper_id": "key123"}],
                ),
                EmbeddingPayload(
                    collection_name="paperforge_objects",
                    texts=["obj1"], ids=["o1"],
                    metadatas=[{"paper_id": "key123"}],
                ),
            ],
        )
        bundle = encode_paper_job(Path("/vault"), job)

        assert bundle.paper_id == "key123"
        assert bundle.chunk_count == 2
        assert len(bundle.payloads) == 2
        assert bundle.payloads[0].collection_name == "paperforge_body"
        assert bundle.payloads[1].collection_name == "paperforge_objects"
        assert bundle.payloads[0].embeddings == [[0.1]]
        assert bundle.payloads[1].embeddings == [[0.1]]

    @patch("paperforge.embedding.builder.OpenAICompatibleProvider")
    def test_empty_payloads(self, mock_provider_cls):
        mock_provider = MagicMock()
        mock_provider.encode.return_value = []
        mock_provider_cls.return_value = mock_provider

        job = PaperEmbeddingJob(paper_id="k1", payloads=[])
        bundle = encode_paper_job(Path("/vault"), job)
        assert bundle.paper_id == "k1"
        assert bundle.chunk_count == 0
        assert bundle.payloads == []


# ---------------------------------------------------------------------------
# write_encoded_payload
# ---------------------------------------------------------------------------

class TestWriteEncodedPayload:
    """Tests for write_encoded_payload."""

    @patch("paperforge.embedding.builder.get_collection")
    def test_calls_collection_add(self, mock_get_collection):
        mock_col = MagicMock()
        mock_get_collection.return_value = mock_col

        encoded = EncodedPayload(
            collection_name="paperforge_body",
            texts=["hello"], ids=["a"],
            metadatas=[{"paper_id": "k1"}],
            embeddings=[[0.1]],
        )
        write_encoded_payload(Path("/vault"), encoded)

        mock_get_collection.assert_called_once_with(
            Path("/vault"), name="paperforge_body",
        )
        mock_col.add.assert_called_once_with(
            ids=["a"],
            embeddings=[[0.1]],
            documents=["hello"],
            metadatas=[{"paper_id": "k1"}],
        )

    @patch("paperforge.embedding.builder.get_collection")
    def test_multiple_rows(self, mock_get_collection):
        mock_col = MagicMock()
        mock_get_collection.return_value = mock_col

        encoded = EncodedPayload(
            collection_name="paperforge_objects",
            texts=["a", "b"], ids=["a1", "b1"],
            metadatas=[{"paper_id": "k"}, {"paper_id": "k"}],
            embeddings=[[0.1], [0.2]],
        )
        write_encoded_payload(Path("/vault"), encoded)

        mock_col.add.assert_called_once_with(
            ids=["a1", "b1"],
            embeddings=[[0.1], [0.2]],
            documents=["a", "b"],
            metadatas=[{"paper_id": "k"}, {"paper_id": "k"}],
        )


# ---------------------------------------------------------------------------
# embed_paper — legacy wrapper
# ---------------------------------------------------------------------------

class TestEmbedPaperLegacyWrapper:
    """Tests that embed_paper still works as a legacy wrapper."""

    @patch("paperforge.embedding.builder.write_encoded_payload")
    @patch("paperforge.embedding.builder.OpenAICompatibleProvider")
    def test_calls_through_to_new_functions(self, mock_provider_cls, mock_write):
        mock_provider = MagicMock()
        mock_provider.encode.return_value = [[0.1]]
        mock_provider_cls.return_value = mock_provider

        n = embed_paper(
            Path("/vault"), "key123",
            [{"text": "hello", "chunk_index": 0}],
        )
        assert n == 1
        assert mock_write.called

    @patch("paperforge.embedding.builder.write_encoded_payload")
    @patch("paperforge.embedding.builder.OpenAICompatibleProvider")
    def test_returns_chunk_count(self, mock_provider_cls, mock_write):
        mock_provider = MagicMock()
        mock_provider.encode.return_value = [[0.1], [0.2]]
        mock_provider_cls.return_value = mock_provider

        n = embed_paper(
            Path("/vault"), "key123",
            [
                {"text": "a", "chunk_index": 0},
                {"text": "b", "chunk_index": 1},
            ],
        )
        assert n == 2

    @patch("paperforge.embedding.builder.write_encoded_payload")
    @patch("paperforge.embedding.builder.OpenAICompatibleProvider")
    def test_empty_chunks(self, mock_provider_cls, mock_write):
        mock_provider = MagicMock()
        mock_provider.encode.return_value = []
        mock_provider_cls.return_value = mock_provider

        n = embed_paper(Path("/vault"), "key123", [])
        assert n == 0
