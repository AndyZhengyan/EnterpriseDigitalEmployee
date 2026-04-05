"""ModelHub request/response models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from common.models import ModelUsage


class TaskType(str, Enum):
    """Task classification for routing."""

    PLANNING = "planning"
    FAST = "fast"
    CODE = "code"


class ChatRequest(BaseModel):
    """Request to generate a model response."""

    messages: List[Dict[str, Any]] = Field(..., description="OpenAI-style messages array")
    model: Optional[str] = Field(None, description="Explicit model override (provider/model-id)")
    task_type: TaskType = Field(TaskType.FAST, description="Task type for routing")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    session_id: Optional[str] = Field(None, description="Conversation session ID")
    employee_id: Optional[str] = Field(None)
    thinking_level: Optional[str] = Field(None, description="off|minimal|low|medium|high|xhigh")
    tools: Optional[List[Dict[str, Any]]] = Field(default=None)
    timeout_seconds: int = Field(120, ge=1, le=600)

    model_config = {"extra": "ignore"}


class ChatResponse(BaseModel):
    """Model response."""

    content: str
    model: str = ""
    provider: str = ""
    usage: ModelUsage = Field(default_factory=ModelUsage)
    latency_ms: int = 0
    session_id: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    finish_reason: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    model_config = {"extra": "ignore"}


class ModelInfo(BaseModel):
    """Single model description."""

    id: str
    name: str
    provider: str
    supports: List[str] = Field(default_factory=list)  # e.g. ["text", "vision"]
    context_window: Optional[int] = None
    cost_per_1m_input: Optional[float] = None
    cost_per_1m_output: Optional[float] = None

    model_config = {"extra": "ignore"}


class ProviderInfo(BaseModel):
    """Provider with its models."""

    name: str
    base_url: str
    api_key_env: str
    models: List[ModelInfo] = Field(default_factory=list)
    healthy: bool = True

    model_config = {"extra": "ignore"}


class ProviderListResponse(BaseModel):
    """Response for GET /model/providers."""

    providers: List[ProviderInfo]
    default_task_type: str


class UsageRecord(BaseModel):
    """Per-employee usage record."""

    employee_id: str
    date: str  # YYYY-MM-DD
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    request_count: int = 0

    model_config = {"extra": "ignore"}


class UsageResponse(BaseModel):
    """Response for GET /model/usage/{employee}."""

    employee_id: str
    period: str = "daily"
    usage: List[UsageRecord]
    daily_limit: int = 0

    model_config = {"extra": "ignore"}


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    timestamp: datetime
    providers: Dict[str, bool] = Field(default_factory=dict)  # provider name -> healthy
    stats: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}
