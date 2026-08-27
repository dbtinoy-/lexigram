"""In-memory vector store — simple vector storage for demo purposes."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any


@dataclass
class Document:
    """A document in the vector store."""

    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)


class InMemoryVectorStore:
    """Simple in-memory vector store for demo purposes."""

    def __init__(self, dimension: int = 128) -> None:
        self._dimension = dimension
        self._documents: dict[str, Document] = {}

    async def add(self, content: str, metadata: dict[str, Any] | None = None) -> Document:
        """Add a document to the store."""
        doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        embedding = self._generate_embedding(content)
        doc = Document(
            id=doc_id,
            content=content,
            metadata=metadata or {},
            embedding=embedding,
        )
        self._documents[doc_id] = doc
        return doc

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search for similar documents."""
        query_embedding = self._generate_embedding(query)
        scores = []

        for doc in self._documents.values():
            score = self._cosine_similarity(query_embedding, doc.embedding)
            scores.append((doc, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc, score in scores[:top_k]:
            results.append({
                "id": doc.id,
                "content": doc.content,
                "metadata": doc.metadata,
                "score": score,
            })
        return results

    async def get(self, doc_id: str) -> Document | None:
        """Get a document by ID."""
        return self._documents.get(doc_id)

    async def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False

    async def count(self) -> int:
        """Get the number of documents."""
        return len(self._documents)

    async def clear(self) -> int:
        """Clear all documents."""
        count = len(self._documents)
        self._documents.clear()
        return count

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate a simple embedding from text (for demo purposes)."""
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        embedding = []
        for i in range(self._dimension):
            byte_val = hash_bytes[i % len(hash_bytes)]
            embedding.append(float(byte_val) / 255.0)
        return embedding

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot_product = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)
