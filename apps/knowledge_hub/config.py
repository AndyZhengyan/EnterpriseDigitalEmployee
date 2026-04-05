"""KnowledgeHub configuration."""

from __future__ import annotations

from common.config import BaseSettings


class KnowledgeHubSettings(BaseSettings):
    """KnowledgeHub settings."""

    model_config = {"env_prefix": "KNOWLEDGEHUB_", "extra": "ignore"}

    host: str = "127.0.0.1"
    port: int = 8005
    # Vector store provider: "inmemory" | "qdrant"
    vector_store: str = "inmemory"
    # Qdrant connection (used when vector_store="qdrant")
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "knowledge"
    # Default retrieval parameters
    default_top_k: int = 5
    default_similarity_threshold: float = 0.7
