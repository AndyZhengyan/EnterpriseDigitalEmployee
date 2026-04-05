"""KnowledgeHub vector store and search tests."""
from __future__ import annotations

import pytest

from apps.knowledge_hub.models import KnowledgeDocument
from apps.knowledge_hub.vector_store import InMemoryVectorStore


class TestInMemoryVectorStore:
    """InMemoryVectorStore + BM25 tests."""

    def test_upsert_and_get(self):
        """Document is retrievable after indexing."""
        store = InMemoryVectorStore()
        doc = KnowledgeDocument(
            id="doc-1",
            title="Employee Handbook",
            content="Vacation policy: 15 days per year",
            source="hr",
        )
        store.upsert(doc)
        retrieved = store.get("doc-1")
        assert retrieved is not None
        assert retrieved.title == "Employee Handbook"
        assert retrieved.id == "doc-1"

    def test_delete(self):
        """Deleted document is no longer retrievable."""
        store = InMemoryVectorStore()
        doc = KnowledgeDocument(id="doc-2", title="Test", content="Test content")
        store.upsert(doc)
        assert store.get("doc-2") is not None
        store.delete("doc-2")
        assert store.get("doc-2") is None

    def test_count(self):
        """Count reflects indexed documents."""
        store = InMemoryVectorStore()
        store.upsert(KnowledgeDocument(id="a", title="A", content="alpha"))
        store.upsert(KnowledgeDocument(id="b", title="B", content="beta"))
        assert store.count() == 2

    def test_list_all(self):
        """list_all returns all documents."""
        store = InMemoryVectorStore()
        store.upsert(KnowledgeDocument(id="x", title="X", content="x-ray"))
        store.upsert(KnowledgeDocument(id="y", title="Y", content="yankee"))
        docs = store.list_all()
        assert len(docs) == 2
        ids = {d.id for d in docs}
        assert ids == {"x", "y"}

    def test_bm25_search_returns_relevant_results(self):
        """BM25 search for 'vacation' returns the handbook doc."""
        store = InMemoryVectorStore()
        store.upsert(KnowledgeDocument(id="handbook", title="Employee Handbook", content="Vacation policy: 15 days per year"))
        store.upsert(KnowledgeDocument(id="payroll", title="Payroll Guide", content="Pay periods are bi-weekly on Fridays"))

        results = store.search(query_text="vacation days policy", top_k=3)
        assert len(results) >= 1
        doc, score = results[0]
        assert doc.id == "handbook"
        assert score > 0

    def test_bm25_search_ranked_by_score(self):
        """Results are ordered by descending BM25 score."""
        store = InMemoryVectorStore()
        store.upsert(KnowledgeDocument(id="exact", title="Python Guide", content="Python programming language tutorial"))
        store.upsert(KnowledgeDocument(id="partial", title="Intro", content="Learn about Python basics"))
        store.upsert(KnowledgeDocument(id="unrelated", title="Cooking", content="How to bake a cake"))

        results = store.search(query_text="Python tutorial", top_k=3)
        ids = [doc.id for doc, _ in results]
        # 'exact' should be first (highest term overlap)
        assert ids[0] == "exact"

    def test_search_with_tags_filter(self):
        """Tags filter excludes documents without matching tags."""
        store = InMemoryVectorStore()
        store.upsert(KnowledgeDocument(id="hr-doc", title="HR", content="HR policies", tags=["hr", "internal"]))
        store.upsert(KnowledgeDocument(id="it-doc", title="IT", content="IT policies", tags=["it"]))

        results = store.search(query_text="policies", top_k=5, tags_filter=["hr"])
        assert all("hr" in doc.tags for doc, _ in results)

    def test_search_returns_empty_when_no_match(self):
        """No results when query doesn't match any document."""
        store = InMemoryVectorStore()
        store.upsert(KnowledgeDocument(id="d", title="Doc", content="Python tutorial"))
        results = store.search(query_text="cooking recipe chocolate cake", top_k=5)
        assert len(results) == 0

    def test_upsert_updates_existing_document(self):
        """Re-upserting the same ID updates the document."""
        store = InMemoryVectorStore()
        store.upsert(KnowledgeDocument(id="dup", title="V1", content="Original"))
        store.upsert(KnowledgeDocument(id="dup", title="V2", content="Updated"))
        doc = store.get("dup")
        assert doc is not None
        assert doc.title == "V2"
        assert doc.content == "Updated"
        assert store.count() == 1

    def test_search_is_case_insensitive(self):
        """BM25 is case-insensitive."""
        store = InMemoryVectorStore()
        store.upsert(KnowledgeDocument(id="d", title="Python", content="Python tutorial"))
        results = store.search(query_text="PYTHON", top_k=3)
        assert len(results) >= 1
        assert results[0][0].id == "d"
