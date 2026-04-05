"""KnowledgeHub request/response models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RetrievalStrategy(str, Enum):
    """Retrieval strategy for knowledge search."""

    VECTOR = "vector"  # Vector similarity search
    BM25 = "bm25"  # Keyword/BM25 search
    HYBRID = "hybrid"  # Vector + BM25 fusion


class KnowledgeDocument(BaseModel):
    """A knowledge document stored in the hub."""

    id: str
    title: str
    content: str
    source: str = ""  # e.g. "employee-handbook", "faq"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = Field(default=None, description="Vector embedding, omit to auto-generate")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"extra": "ignore"}


class IndexRequest(BaseModel):
    """Request to index a document."""

    document: KnowledgeDocument

    model_config = {"extra": "ignore"}


class BulkIndexRequest(BaseModel):
    """Request to index multiple documents."""

    documents: List[KnowledgeDocument]

    model_config = {"extra": "ignore"}


class SearchRequest(BaseModel):
    """Request to search knowledge."""

    query: str = Field(..., description="Search query text")
    top_k: int = Field(5, ge=1, le=100, description="Number of results to return")
    strategy: RetrievalStrategy = Field(RetrievalStrategy.HYBRID)
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    similarity_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    employee_id: Optional[str] = None

    model_config = {"extra": "ignore"}


class SearchResult(BaseModel):
    """A single search result."""

    document: KnowledgeDocument
    score: float = Field(description="Relevance score (higher = more relevant)")
    rank: int = Field(description="Rank position (1 = best)")

    model_config = {"extra": "ignore"}


class SearchResponse(BaseModel):
    """Response for knowledge search."""

    query: str
    results: List[SearchResult]
    total_indexed: int = Field(description="Total documents in the index")
    latency_ms: int = 0

    model_config = {"extra": "ignore"}


class DocumentListResponse(BaseModel):
    """Response for listing documents."""

    documents: List[KnowledgeDocument]
    total: int

    model_config = {"extra": "ignore"}


class KnowledgeHubHealthResponse(BaseModel):
    """Response for GET /knowledge-hub/health."""

    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    document_count: int = 0
    vector_store: str = "inmemory"

    model_config = {"extra": "ignore"}
