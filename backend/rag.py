"""RAG retrieval: query the medical knowledge vector store."""

import os
import chromadb
from google import genai

from config import GOOGLE_API_KEY, EMBEDDING_MODEL, CHROMA_PERSIST_DIR

_collection = None
_genai_client = None


def _get_collection():
    global _collection, _genai_client
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = client.get_collection(name="medical_triage")
        _genai_client = genai.Client(api_key=GOOGLE_API_KEY)
    return _collection, _genai_client


def retrieve_context(query: str, k: int = 4) -> str:
    try:
        collection, client = _get_collection()
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=[query],
        )
        query_embedding = result.embeddings[0].values

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
        )

        if not results["documents"] or not results["documents"][0]:
            return ""

        chunks = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            source = meta.get("source", "unknown")
            chunks.append(f"[Source: {source}]\n{doc}")
        return "\n\n---\n\n".join(chunks)
    except Exception as e:
        print(f"RAG retrieval error: {e}")
        return ""
