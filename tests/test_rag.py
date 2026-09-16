from unittest.mock import patch

import pytest
import rag


def test_split_into_chunks_empty_text():
    # Empty input should give us nothing to index.
    assert rag.split_into_chunks("") == []


def test_split_into_chunks_single_paragraph():
    text = "Returns are allowed within 30 days."

    result = rag.split_into_chunks(text)

    assert result == [
        "Returns are allowed within 30 days."
    ]


def test_split_into_chunks_multiple_paragraphs():
    text = (
        "Returns are allowed within 30 days.\n\n"
        "Refunds are processed within 5-7 business days.\n\n"
        "Orders can be cancelled before shipping."
    )

    result = rag.split_into_chunks(text)

    assert result == [
        "Returns are allowed within 30 days.",
        "Refunds are processed within 5-7 business days.",
        "Orders can be cancelled before shipping."
    ]


def test_create_embedding_uses_query_prefix():
    # We don't need to call the real Nomic model for a unit test.
    with patch("rag.embeddings") as mock_embeddings:
        mock_embeddings.return_value = {
            "embedding": [0.1, 0.2, 0.3]
        }

        result = rag.create_embedding(
            "Can I cancel my order?",
            is_query=True
        )

    assert result == [0.1, 0.2, 0.3]

    mock_embeddings.assert_called_once_with(
        model="nomic-embed-text",
        prompt="search_query: Can I cancel my order?"
    )


def test_create_embedding_uses_document_prefix():
    # Documents use a different Nomic prefix when they are indexed.
    with patch("rag.embeddings") as mock_embeddings:
        mock_embeddings.return_value = {
            "embedding": [0.4, 0.5, 0.6]
        }

        result = rag.create_embedding(
            "Orders can be cancelled before shipping.",
            is_query=False
        )

    assert result == [0.4, 0.5, 0.6]

    mock_embeddings.assert_called_once_with(
        model="nomic-embed-text",
        prompt=(
            "search_document: "
            "Orders can be cancelled before shipping."
        )
    )


def test_search_policy_returns_relevant_documents():
    with patch("rag.embeddings") as mock_embeddings:
        mock_embeddings.return_value = {
            "embedding": [0.1, 0.2, 0.3]
        }

        # Keep the real Chroma collection, but fake the database query.
        with patch.object(rag.collection, "query") as mock_query:
            mock_query.return_value = {
                "documents": [[
                    "Orders can be cancelled before shipping."
                ]],
                "distances": [[0.3]]
            }

            result = rag.search_policy("cancel order")

    assert result == [
        "Orders can be cancelled before shipping."
    ]

    mock_query.assert_called_once_with(
        query_embeddings=[[0.1, 0.2, 0.3]],
        n_results=2
    )


def test_search_policy_returns_error_when_no_documents():
    with patch("rag.embeddings") as mock_embeddings:
        mock_embeddings.return_value = {
            "embedding": [0.1, 0.2, 0.3]
        }

        with patch.object(rag.collection, "query") as mock_query:
            # Simulate Chroma having nothing to return.
            mock_query.return_value = {
                "documents": [[]],
                "distances": [[]]
            }

            result = rag.search_policy(
                "What is your warranty policy?"
            )

    assert result == [
        {"error": "No policy documents found."}
    ]


def test_search_policy_rejects_weak_match():
    with patch("rag.embeddings") as mock_embeddings:
        mock_embeddings.return_value = {
            "embedding": [0.1, 0.2, 0.3]
        }

        with patch.object(rag.collection, "query") as mock_query:
            # Higher cosine distance means the result is less similar.
            mock_query.return_value = {
                "documents": [["Some unrelated policy text."]],
                "distances": [[0.8]]
            }

            result = rag.search_policy("cancel order")

    assert result == [
        {
            "error": (
                "No sufficiently relevant policy "
                "information was found."
            )
        }
    ]