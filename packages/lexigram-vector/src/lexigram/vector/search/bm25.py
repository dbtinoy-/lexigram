"""BM25 keyword retrieval for hybrid search.

Extracted from ``hybrid.py`` to keep that module under the 500-LOC limit.
"""

from __future__ import annotations

from collections import Counter
import math
import re
from typing import Protocol

from lexigram.contracts.ai.vector import Document, RAGSearchResult

SearchResult = RAGSearchResult


class Tokenizer(Protocol):
    """Protocol for text tokenization."""

    def tokenize(self, text: str) -> list[str]:
        """Tokenize text into terms.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        ...


class SimpleTokenizer:
    """Simple whitespace and punctuation tokenizer.

    Example:
        >>> tokenizer = SimpleTokenizer()
        >>> tokens = tokenizer.tokenize("Hello, world!")
        >>> print(tokens)
        ['hello', 'world']
    """

    def __init__(self, lowercase: bool = True, remove_punctuation: bool = True):
        """Initialize tokenizer.

        Args:
            lowercase: Convert to lowercase
            remove_punctuation: Remove punctuation
        """
        self.lowercase = lowercase
        self.remove_punctuation = remove_punctuation

    def tokenize(self, text: str) -> list[str]:
        """Tokenize text.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        if self.lowercase:
            text = text.lower()

        if self.remove_punctuation:
            text = re.sub(r"[^\w\s]", " ", text)

        # Split on whitespace and filter empty strings
        return list(filter(lambda t: t, text.split()))


class BM25Scorer:
    """BM25 scoring algorithm for keyword-based retrieval.

    Implements Okapi BM25 ranking function.

    Example:
        >>> scorer = BM25Scorer(k1=1.5, b=0.75)
        >>> docs = [["hello", "world"], ["hello", "python"]]
        >>> scorer.fit(docs)
        >>> scores = scorer.score(["hello", "world"])
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75, epsilon: float = 0.25):
        """Initialize BM25 scorer.

        Args:
            k1: Term frequency saturation parameter (default: 1.5)
            b: Length normalization parameter (default: 0.75)
            epsilon: Floor value for IDF (default: 0.25)
        """
        self.k1 = k1
        self.b = b
        self.epsilon = epsilon

        # Fitted statistics
        self.doc_count = 0
        self.avg_doc_len = 0.0
        self.doc_freqs: dict[str, int] = {}
        self.doc_lens: list[int] = []
        self.idf_scores: dict[str, float] = {}

    def fit(self, tokenized_docs: list[list[str]]) -> None:
        """Fit BM25 scorer on tokenized documents.

        Args:
            tokenized_docs: List of tokenized documents
        """
        self.doc_count = len(tokenized_docs)
        self.doc_lens = [len(doc) for doc in tokenized_docs]
        self.avg_doc_len = (
            sum(self.doc_lens) / self.doc_count if self.doc_count > 0 else 0
        )

        # Calculate document frequencies
        self.doc_freqs = {}
        for doc in tokenized_docs:
            unique_terms = set(doc)
            for term in unique_terms:
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        # Calculate IDF scores
        self.idf_scores = {}
        for term, df in self.doc_freqs.items():
            idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1)
            self.idf_scores[term] = max(idf, self.epsilon)

    def score(
        self,
        query_tokens: list[str],
        doc_idx: int,
        doc_tokens: list[str],
    ) -> float:
        """Score a document for a query.

        Args:
            query_tokens: Tokenized query
            doc_idx: Document index
            doc_tokens: Tokenized document

        Returns:
            BM25 score
        """
        if doc_idx >= len(self.doc_lens):
            return 0.0

        score = 0.0
        doc_len = self.doc_lens[doc_idx]
        term_freqs = Counter(doc_tokens)

        for term in query_tokens:
            if term not in self.idf_scores:
                continue

            tf = term_freqs.get(term, 0)
            idf = self.idf_scores[term]

            # BM25 formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (
                1 - self.b + self.b * doc_len / self.avg_doc_len
            )
            score += idf * (numerator / denominator)

        return score


class BM25Retriever:
    """BM25-based keyword retrieval.

    Example:
        >>> retriever = BM25Retriever()
        >>> docs = [
        ...     Document(id="1", text="Python programming"),
        ...     Document(id="2", text="Java programming")
        ... ]
        >>> retriever.add_documents(docs)
        >>> results = retriever.search("python", k=5)
    """

    def __init__(
        self,
        tokenizer: Tokenizer | None = None,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        """Initialize BM25 retriever.

        Args:
            tokenizer: Text tokenizer (default: SimpleTokenizer)
            k1: BM25 k1 parameter
            b: BM25 b parameter
        """
        self.tokenizer = tokenizer or SimpleTokenizer()
        self.scorer = BM25Scorer(k1=k1, b=b)
        self.documents: list[Document] = []
        self.tokenized_docs: list[list[str]] = []

    def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the index.

        Args:
            documents: Documents to add
        """
        self.documents.extend(documents)
        new_tokenized = [self.tokenizer.tokenize(doc.text) for doc in documents]
        self.tokenized_docs.extend(new_tokenized)

        # Refit scorer with all documents
        if self.tokenized_docs:
            self.scorer.fit(self.tokenized_docs)

    def search(
        self,
        query: str,
        k: int = 10,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Search for documents using BM25.

        Args:
            query: Search query
            k: Number of results to return
            min_score: Minimum score threshold

        Returns:
            List of search results
        """
        if not self.documents:
            return []

        query_tokens = self.tokenizer.tokenize(query)
        if not query_tokens:
            return []

        # Score all documents
        scores: list[tuple[int, float]] = []
        for idx in range(len(self.documents)):
            score = self.scorer.score(query_tokens, idx, self.tokenized_docs[idx])
            # Only include documents with non-zero scores above minimum
            if score > min_score:
                scores.append((idx, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        # Take top k and create results
        results = []
        for rank, (idx, score) in enumerate(scores[:k]):
            results.append(
                SearchResult(
                    document=self.documents[idx],
                    score=score,
                    rank=rank,
                ),
            )

        return results

    def clear(self) -> None:
        """Clear all documents."""
        self.documents = []
        self.tokenized_docs = []
        self.scorer = BM25Scorer(k1=self.scorer.k1, b=self.scorer.b)
