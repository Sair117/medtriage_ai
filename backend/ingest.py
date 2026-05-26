"""Ingest knowledge base markdown files into ChromaDB vector store."""

import os
import glob
import shutil
import chromadb
from google import genai

from config import GOOGLE_API_KEY, EMBEDDING_MODEL, CHROMA_PERSIST_DIR, KNOWLEDGE_BASE_DIR


def load_documents(kb_dir: str) -> list[dict]:
    docs = []
    for filepath in glob.glob(os.path.join(kb_dir, "*.md")):
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        filename = os.path.basename(filepath)
        docs.append({"text": text, "source": filename})
    return docs


def chunk_text(text: str, chunk_size=800, overlap=150) -> list[str]:
    separators = ["\n## ", "\n### ", "\n- ", "\n\n", "\n"]
    chunks = [text]
    for sep in separators:
        new_chunks = []
        for chunk in chunks:
            if len(chunk) > chunk_size:
                parts = chunk.split(sep)
                current = ""
                for part in parts:
                    candidate = current + sep + part if current else part
                    if len(candidate) > chunk_size and current:
                        new_chunks.append(current.strip())
                        current = part
                    else:
                        current = candidate
                if current.strip():
                    new_chunks.append(current.strip())
            else:
                new_chunks.append(chunk)
        chunks = new_chunks
    return [c for c in chunks if c.strip()]


def embed_texts(client: genai.Client, texts: list[str]) -> list[list[float]]:
    all_embeddings = []
    batch_size = 5
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        for text in batch:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
            )
            all_embeddings.append(result.embeddings[0].values)
        print(f"  Embedded batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}")
    return all_embeddings


def build_vector_store():
    docs = load_documents(KNOWLEDGE_BASE_DIR)
    if not docs:
        print("No documents found in knowledge_base/")
        return

    texts = []
    metadatas = []
    for doc in docs:
        chunks = chunk_text(doc["text"])
        for chunk in chunks:
            texts.append(chunk)
            metadatas.append({"source": doc["source"]})

    print(f"Split into {len(texts)} chunks from {len(docs)} documents")

    genai_client = genai.Client(api_key=GOOGLE_API_KEY)
    embeddings = embed_texts(genai_client, texts)

    if os.path.exists(CHROMA_PERSIST_DIR):
        shutil.rmtree(CHROMA_PERSIST_DIR)

    chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    collection = chroma_client.get_or_create_collection(name="medical_triage")

    ids = [f"doc_{i}" for i in range(len(texts))]
    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(f"Done. {len(texts)} chunks stored in {CHROMA_PERSIST_DIR}")


if __name__ == "__main__":
    build_vector_store()
