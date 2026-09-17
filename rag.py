import re
from pathlib import Path

import chromadb
from ollama import embeddings


EMBEDDING_MODEL = "nomic-embed-text"

BASE_DIR = Path(__file__).resolve().parent
POLICY_PATH = BASE_DIR / "documents" / "store_policy.txt"
CHROMA_PATH = BASE_DIR / "chroma_db"

COLLECTION_NAME = "store_policies"

# Chroma uses cosine distance here.
# Lower distance means the retrieved text is more similar to the query.
RELEVANCE_THRESHOLD = 0.55

DEFAULT_RESULTS = 3
MAX_RESULTS = 5


client = chromadb.PersistentClient(path=str(CHROMA_PATH))

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)


def load_policy():
    """Load the store policy from disk."""
    try:
        return POLICY_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def split_into_chunks(text):
    """
    Split the policy into meaningful sections.

    The policy uses ALL-CAPS section headers such as RETURNS and
    SHIPPING. Each section becomes a retrieval chunk instead of
    splitting every paragraph or bullet point into its own chunk.
    """

    if not text or not text.strip():
        return []

    text = text.strip()

    # Remove the document title if it is present.
    text = re.sub(
        r"^D2C Store Customer Policy\s*",
        "",
        text,
        flags=re.IGNORECASE
    ).strip()

    # A section header is an otherwise standalone line written
    # entirely in uppercase letters and spaces.
    header_pattern = r"(?m)^([A-Z][A-Z ]{2,})$"

    matches = list(re.finditer(header_pattern, text))

    if not matches:
        return [
            chunk.strip()
            for chunk in re.split(r"\n\s*\n", text)
            if chunk.strip()
        ]

    chunks = []

    for index, match in enumerate(matches):
        header = match.group(1).strip()

        start = match.end()
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )

        body = text[start:end].strip()

        if not body:
            continue

        # Remove excessive blank lines while keeping each statement
        # readable inside the section.
        lines = [
            line.strip()
            for line in body.splitlines()
            if line.strip()
        ]

        body = "\n".join(lines)

        chunks.append(
            f"{header}\n\n{body}"
        )

    return chunks


def create_embedding(text, is_query=False):
    """
    Create an embedding using Nomic's task-specific input format.

    Nomic uses different prefixes when embedding documents and
    search queries, so the same text is represented differently
    depending on how it is being used.
    """

    if not text or not text.strip():
        raise ValueError("Cannot create an embedding for empty text.")

    prefix = (
        "search_query: "
        if is_query
        else "search_document: "
    )

    response = embeddings(
        model=EMBEDDING_MODEL,
        prompt=f"{prefix}{text}"
    )

    return response["embedding"]


def build_knowledge_base():
    """
    Build or refresh the Chroma collection from the store policy.

    Existing chunks are updated through upsert(). Chunks that no
    longer exist in the policy are removed so stale policy text
    does not remain searchable.
    """

    text = load_policy()

    if not text:
        print("Policy file not found or empty.")
        return False

    chunks = split_into_chunks(text)

    if not chunks:
        print("No policy chunks found.")
        return False

    documents = []
    embeddings_list = []
    ids = []
    metadatas = []

    for index, chunk in enumerate(chunks):
        documents.append(chunk)

        embeddings_list.append(
            create_embedding(
                chunk,
                is_query=False
            )
        )

        ids.append(f"policy_{index}")

        metadatas.append({
            "source": POLICY_PATH.name,
            "chunk_index": index
        })

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings_list,
        metadatas=metadatas
    )

    # If the policy previously contained more sections, remove
    # those old chunks so they cannot appear in future searches.
    existing = collection.get(include=[])

    valid_ids = set(ids)

    stale_ids = [
        chunk_id
        for chunk_id in existing["ids"]
        if chunk_id not in valid_ids
    ]

    if stale_ids:
        collection.delete(ids=stale_ids)

    print(
        f"Indexed {len(chunks)} policy section chunks in ChromaDB."
    )

    return True


def search_policy(query, n_results=DEFAULT_RESULTS):
    """
    Retrieve policy sections relevant to a customer question.

    Results are filtered using RELEVANCE_THRESHOLD so weak
    semantic matches are not passed to the agent.
    """

    if not isinstance(query, str) or not query.strip():
        return [{
            "error": "Policy search requires a non-empty query."
        }]

    try:
        n_results = int(n_results)
    except (TypeError, ValueError):
        n_results = DEFAULT_RESULTS

    n_results = max(
        1,
        min(n_results, MAX_RESULTS)
    )

    if collection.count() == 0:
        return [{
            "error": "No policy documents have been indexed."
        }]

    try:
        query_embedding = create_embedding(
            query,
            is_query=True
        )

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

    except Exception as exc:
        return [{
            "error": f"Policy search failed: {exc}"
        }]

    documents = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        return [{
            "error": "No policy documents found."
        }]

    matches = []

    for document, distance, metadata in zip(
        documents,
        distances,
        metadatas
    ):
        if distance > RELEVANCE_THRESHOLD:
            continue

        matches.append({
            "text": document,
            "source": metadata.get(
                "source",
                "unknown"
            ),
            "chunk_index": metadata.get(
                "chunk_index"
            ),
            "distance": distance
        })

    if not matches:
        return [{
            "error": (
                "No sufficiently relevant policy "
                "information was found."
            )
        }]

    return matches


if __name__ == "__main__":
    # Rebuild the index from the current policy file.
    build_knowledge_base()

    query = "How long do I have to return a product?"

    print(f"\nQuery: {query}")
    print("\nTop retrieval results:")

    results = search_policy(
        query,
        n_results=MAX_RESULTS
    )

    for result in results:
        if "error" in result:
            print(f"\nError: {result['error']}")
            continue

        print(f"\nDistance: {result['distance']}")
        print(f"Metadata: {result['source']} / chunk {result['chunk_index']}")
        print(f"Text:\n{result['text']}")