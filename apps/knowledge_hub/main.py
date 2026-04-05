"""KnowledgeHub FastAPI service — port 8005."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException

from apps.knowledge_hub import __version__
from apps.knowledge_hub.config import KnowledgeHubSettings
from apps.knowledge_hub.models import (
    BulkIndexRequest,
    DocumentListResponse,
    IndexRequest,
    KnowledgeDocument,
    KnowledgeHubHealthResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from apps.knowledge_hub.vector_store import get_vector_store, init_vector_store
from common.tracing import get_logger

log = get_logger("knowledge_hub")

settings = KnowledgeHubSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_vector_store(provider=settings.vector_store)
    vs = get_vector_store()
    log.info(
        "knowledge_hub.started",
        port=settings.port,
        vector_store=settings.vector_store,
        document_count=vs.count(),
    )
    yield
    log.info("knowledge_hub.stopped")


app = FastAPI(title="KnowledgeHub", version=__version__, lifespan=lifespan)


@app.get("/knowledge-hub/health", response_model=KnowledgeHubHealthResponse)
async def hub_health() -> KnowledgeHubHealthResponse:
    """Overall health of KnowledgeHub."""
    vs = get_vector_store()
    return KnowledgeHubHealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.now(timezone.utc),
        document_count=vs.count(),
        vector_store=settings.vector_store,
    )


@app.post("/knowledge/index", status_code=201)
async def index_document(req: IndexRequest) -> dict:
    """Index a single knowledge document."""
    vs = get_vector_store()
    doc = req.document
    vs.upsert(doc)
    log.info("knowledge.indexed", document_id=doc.id, source=doc.source)
    return {"document_id": doc.id, "indexed": True}


@app.post("/knowledge/index/bulk", status_code=201)
async def bulk_index(req: BulkIndexRequest) -> dict:
    """Index multiple documents at once."""
    vs = get_vector_store()
    vs.upsert_batch(req.documents)
    log.info("knowledge.bulk_indexed", count=len(req.documents))
    return {"indexed": len(req.documents)}


@app.get("/knowledge/documents", response_model=DocumentListResponse)
async def list_documents(tags: Optional[str] = None) -> DocumentListResponse:
    """List all indexed documents, optionally filtered by tags."""
    vs = get_vector_store()
    docs = vs.list_all()
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        docs = [d for d in docs if any(t in d.tags for t in tag_list)]
    return DocumentListResponse(documents=docs, total=len(docs))


@app.get("/knowledge/{document_id}", response_model=KnowledgeDocument)
async def get_document(document_id: str) -> KnowledgeDocument:
    """Get a specific document by ID."""
    vs = get_vector_store()
    doc = vs.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
    return doc


@app.delete("/knowledge/{document_id}", status_code=204)
async def delete_document(document_id: str) -> None:
    """Delete a document from the index."""
    vs = get_vector_store()
    if vs.get(document_id) is None:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
    vs.delete(document_id)
    log.info("knowledge.deleted", document_id=document_id)


@app.post("/knowledge/search", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    """Search indexed knowledge with BM25 text retrieval."""
    start = time.monotonic()
    vs = get_vector_store()

    try:
        raw_results = vs.search(
            query_text=req.query,
            query_embedding=None,
            top_k=req.top_k,
            similarity_threshold=req.similarity_threshold,
            tags_filter=req.tags,
        )
    except Exception as e:
        log.warning("knowledge.search.failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {e}") from e

    results = [SearchResult(document=doc, score=score, rank=i + 1) for i, (doc, score) in enumerate(raw_results)]

    duration_ms = int((time.monotonic() - start) * 1000)
    log.info(
        "knowledge.search",
        query=req.query,
        result_count=len(results),
        latency_ms=duration_ms,
    )
    return SearchResponse(
        query=req.query,
        results=results,
        total_indexed=vs.count(),
        latency_ms=duration_ms,
    )
