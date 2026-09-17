from unittest.mock import patch
from textwrap import dedent

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


def test_split_into_chunks_policy_sections():
    text = dedent("""
    D2C Store Customer Policy

    RETURNS

    Customers may request a return within 30 days of delivery.

    REFUNDS

    Refunds are processed within 5-7 business days.

    SHIPPING

    Shipping normally takes 3-7 business days.

    WARRANTY

    Electronics products include a 12-month limited warranty.

    CANCELLATIONS

    Orders can be cancelled before they are shipped.
    """)

    result = rag.split_into_chunks(text)

    assert len(result) == 5

    assert result[0].startswith("RETURNS")
    assert result[1].startswith("REFUNDS")
    assert result[2].startswith("SHIPPING")
    assert result[3].startswith("WARRANTY")
    assert result[4].startswith("CANCELLATIONS")


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

        # Fake the Chroma query so this test does not depend on
        # the actual local vector database.
        with patch.object(rag.collection, "query") as mock_query:
            mock_query.return_value = {
                "documents": [[
                    "CANCELLATIONS\n\n"
                    "Orders can be cancelled before shipping."
                ]],
                "distances": [[0.3]],
                "metadatas": [[
                    {
                        "source": "store_policy.txt",
                        "chunk_index": 4
                    }
                ]]
            }

            result = rag.search_policy("cancel order")

    assert result == [
        {
            "text": (
                "CANCELLATIONS\n\n"
                "Orders can be cancelled before shipping."
            ),
            "source": "store_policy.txt",
            "chunk_index": 4,
            "distance": 0.3
        }
    ]

    mock_query.assert_called_once_with(
        query_embeddings=[[0.1, 0.2, 0.3]],
        n_results=3
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
                "distances": [[]],
                "metadatas": [[]]
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
                "distances": [[0.8]],
                "metadatas": [[
                    {
                        "source": "store_policy.txt",
                        "chunk_index": 0
                    }
                ]]
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


def test_search_policy_rejects_empty_query():
    result = rag.search_policy("")

    assert result == [
        {
            "error": (
                "Policy search requires a non-empty query."
            )
        }
    ]


def test_search_policy_clamps_result_count():
    with patch("rag.embeddings") as mock_embeddings:
        mock_embeddings.return_value = {
            "embedding": [0.1, 0.2, 0.3]
        }

        with patch.object(rag.collection, "query") as mock_query:
            mock_query.return_value = {
                "documents": [[
                    "RETURNS\n\n"
                    "Customers may request a return within 30 days."
                ]],
                "distances": [[0.2]],
                "metadatas": [[
                    {
                        "source": "store_policy.txt",
                        "chunk_index": 0
                    }
                ]]
            }

            rag.search_policy(
                "return policy",
                n_results=100
            )

    mock_query.assert_called_once_with(
        query_embeddings=[[0.1, 0.2, 0.3]],
        n_results=rag.MAX_RESULTS
    )