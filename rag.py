import re
import chromadb
from ollama import embeddings

EMBEDDING_MODEL = "nomic-embed-text"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "store_policies"
RELEVANCE_THRESHOLD = 0.55  # Cosine distance cutoff (lower = higher similarity)

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)


def load_policy():
    try:
        with open("documents/store_policy.txt", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        print("Error: documents/store_policy.txt not found.")
        return ""


def split_into_chunks(text):
    if not text:
        return []

    # Split text by blank lines (paragraphs)
    return [
        chunk.strip()
        for chunk in re.split(r"\n\s*\n", text)
        if chunk.strip()
    ]


def create_embedding(text, is_query=False):
    # Nomic requires task-specific prefixes for search vs indexing
    prefix = "search_query: " if is_query else "search_document: "

    response = embeddings(
        model=EMBEDDING_MODEL,
        prompt=f"{prefix}{text}"
    )

    return response["embedding"]


def build_knowledge_base():
    text = load_policy()

    if not text:
        return

    chunks = split_into_chunks(text)

    if not chunks:
        print("No policy chunks found.")
        return

    vectors = [
        create_embedding(chunk, is_query=False)
        for chunk in chunks
    ]

    # Upsert lets us rebuild the index without creating duplicates.
    collection.upsert(
        ids=[f"policy_{i}" for i in range(len(chunks))],
        documents=chunks,
        embeddings=vectors
    )

    print(f"Indexed {len(chunks)} policy chunks in ChromaDB.")


def search_policy(query: str, n_results: int = 2):
    n_results = max(1, int(n_results))

    query_embedding = create_embedding(
        query,
        is_query=True
    )

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    documents = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not documents:
        return [{"error": "No policy documents found."}]

    # Don't return the result if even the closest match is too weak.
    if distances[0] > RELEVANCE_THRESHOLD:
        return [
            {
                "error": (
                    "No sufficiently relevant policy "
                    "information was found."
                )
            }
        ]

    return documents


if __name__ == "__main__":
    build_knowledge_base()

    result = search_policy(
        "How long do I have to return a product?"
    )

    print("\nRetrieved information:", result)