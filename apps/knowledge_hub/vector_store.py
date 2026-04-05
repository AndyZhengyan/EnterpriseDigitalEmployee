"""Vector store abstraction and in-memory implementation."""

from __future__ import annotations

import math
import re
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from apps.knowledge_hub.models import KnowledgeDocument
from common.tracing import get_logger

log = get_logger("knowledge_hub.vector_store")


class VectorStore(ABC):
    """Abstract vector store interface."""

    @abstractmethod
    def upsert(self, document: KnowledgeDocument) -> None:
        """Index a document."""

    @abstractmethod
    def upsert_batch(self, documents: list[KnowledgeDocument]) -> None:
        """Index multiple documents."""

    @abstractmethod
    def search(
        self,
        query_text: str,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 5,
        similarity_threshold: Optional[float] = None,
        tags_filter: Optional[list[str]] = None,
    ) -> list[tuple[KnowledgeDocument, float]]:
        """Search for similar documents. Returns [(doc, score)]."""

    @abstractmethod
    def delete(self, document_id: str) -> None:
        """Delete a document by ID."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of indexed documents."""

    @abstractmethod
    def get(self, document_id: str) -> Optional[KnowledgeDocument]:
        """Get a document by ID."""

    @abstractmethod
    def list_all(self) -> List[KnowledgeDocument]:
        """List all documents."""


class InMemoryVectorStore(VectorStore):
    """In-memory vector store with BM25 text search.

    Uses BM25 for text matching (no external embedding service required).
    Vector similarity search is available if documents have pre-computed embeddings.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._docs: Dict[str, KnowledgeDocument] = {}
        # BM25 index: term -> doc_id -> count
        self._bm25_index: Dict[str, Dict[str, int]] = {}
        self._doc_term_counts: Dict[str, Dict[str, int]] = {}  # doc_id -> {term: count}

    # BM25 parameters (standard values)
    _k1 = 1.5
    _b = 0.75

    def _tokenize(self, text: str) -> list[str]:
        """Simple whitespace/punctuation tokenizer."""
        return [w.lower().strip() for w in re.split(r"[^\w]+", text) if w.strip()]

    def _update_bm25(self, doc: KnowledgeDocument) -> None:
        """Update BM25 index for a document."""
        text = f"{doc.title} {doc.content}"
        terms = self._tokenize(text)
        term_counts: Dict[str, int] = {}
        for t in terms:
            term_counts[t] = term_counts.get(t, 0) + 1
        self._doc_term_counts[doc.id] = term_counts

        for term, count in term_counts.items():
            if term not in self._bm25_index:
                self._bm25_index[term] = {}
            self._bm25_index[term][doc.id] = count

    def _remove_from_bm25(self, doc_id: str) -> None:
        """Remove a document from BM25 index."""
        if doc_id not in self._doc_term_counts:
            return
        for term in self._doc_term_counts[doc_id]:
            if term in self._bm25_index:
                self._bm25_index[term].pop(doc_id, None)
                if not self._bm25_index[term]:
                    del self._bm25_index[term]
        del self._doc_term_counts[doc_id]

    def _bm25_score(self, query_terms: list[str], doc_id: str) -> float:
        """Compute BM25 score for a document given query terms."""
        if doc_id not in self._doc_term_counts:
            return 0.0
        doc_terms = self._doc_term_counts[doc_id]
        doc_len = sum(doc_terms.values())
        avg_doc_len = sum(sum(t.values()) for t in self._doc_term_counts.values()) / max(len(self._doc_term_counts), 1)
        score = 0.0
        for term in query_terms:
            if term not in self._bm25_index:
                continue
            df = len(self._bm25_index[term])  # document frequency
            idf = math.log((len(self._doc_term_counts) - df + 0.5) / (df + 0.5) + 1)
            tf = doc_terms.get(term, 0)
            numerator = tf * (self._k1 + 1)
            denominator = tf + self._k1 * (1 - self._b + self._b * doc_len / max(avg_doc_len, 1))
            score += idf * numerator / denominator
        return score

    def upsert(self, document: KnowledgeDocument) -> None:
        with self._lock:
            self._update_bm25(document)
            self._docs[document.id] = document

    def upsert_batch(self, documents: list[KnowledgeDocument]) -> None:
        with self._lock:
            for doc in documents:
                self.upsert(doc)

    def search(
        self,
        query_text: str,
        query_embedding: Optional[list[float]] = None,
        top_k: int = 5,
        similarity_threshold: Optional[float] = None,
        tags_filter: Optional[list[str]] = None,
    ) -> list[tuple[KnowledgeDocument, float]]:
        del query_embedding  # In-memory store doesn't compute embeddings; BM25 only
        query_terms = self._tokenize(query_text)

        scores: list[tuple[KnowledgeDocument, float]] = []
        with self._lock:
            for doc_id, doc in self._docs.items():
                if tags_filter and not any(t in doc.tags for t in tags_filter):
                    continue
                score = self._bm25_score(query_terms, doc_id)
                if score > 0:
                    if similarity_threshold is not None and score < similarity_threshold:
                        continue
                    scores.append((doc, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def delete(self, document_id: str) -> None:
        with self._lock:
            self._remove_from_bm25(document_id)
            self._docs.pop(document_id, None)

    def count(self) -> int:
        with self._lock:
            return len(self._docs)

    def get(self, document_id: str) -> Optional[KnowledgeDocument]:
        with self._lock:
            return self._docs.get(document_id)

    def list_all(self) -> list[KnowledgeDocument]:
        with self._lock:
            return list(self._docs.values())


# Singleton instance
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Return the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = InMemoryVectorStore()
    return _vector_store


def init_vector_store(provider: str = "inmemory", **kwargs: Any) -> VectorStore:
    """Initialise the global vector store. Can be called to reconfigure."""
    global _vector_store
    if provider == "inmemory":
        _vector_store = InMemoryVectorStore()
    else:
        raise ValueError(f"Unknown vector store provider: {provider}")
    return _vector_store
