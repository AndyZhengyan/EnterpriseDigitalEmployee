"""Runtime API 请求/响应模型

规格依据：specs/runtime-spec.md
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)

# ============== 枚举定义 ==============


class TaskType(str, Enum):
    """任务类型"""

    INQUIRY = "inquiry"
    ACTION = "action"
    ANALYSIS = "analysis"


class TaskStatus(str, Enum):
    """任务状态"""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class StepType(str, Enum):
    """步骤类型"""

    CALL_SKILL = "call_skill"
    CALL_CONNECTOR = "call_connector"
    CALL_MODEL = "call_model"
    REFLECT = "reflect"
    COMPLETE = "complete"


class StepStatus(str, Enum):
    """步骤状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============== Execute 接口 ==============


class TaskInput(BaseModel):
    """任务输入"""

    query: str
    params: Dict[str, Any] = Field(default_factory=dict)


class TaskContext(BaseModel):
    """任务上下文"""

    session_id: str
    user_id: str
    skills: List[str] = Field(default_factory=list)
    attachments: List[str] = Field(default_factory=list)


class ExecuteRequest(BaseModel):
    """POST /runtime/execute 请求"""

    employee_id: str
    task_id: Optional[str] = None
    task_type: TaskType = TaskType.INQUIRY
    input: TaskInput
    context: Optional[TaskContext] = None

    model_config = {"use_enum_values": True}


class TaskResult(BaseModel):
    """任务结果"""

    answer: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class ExecuteResponse(BaseModel):
    """POST /runtime/execute 响应"""

    task_id: str
    status: TaskStatus
    result: Optional[TaskResult] = None
    trace_id: Optional[str] = None
    duration_ms: Optional[int] = None

    model_config = {"use_enum_values": True}


# ============== Plan 接口 ==============


class PlanRequest(BaseModel):
    """POST /runtime/plan 请求"""

    employee_id: str
    task: str
    available_skills: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)


class PlanStep(BaseModel):
    """计划步骤"""

    order: int
    type: StepType
    skill: Optional[str] = None
    connector: Optional[str] = None
    input: Dict[str, Any] = Field(default_factory=dict)
    expected_output: Optional[str] = None

    model_config = {"use_enum_values": True}


class PlanResponse(BaseModel):
    """POST /runtime/plan 响应"""

    plan_id: str
    task_id: str
    steps: List[PlanStep]
    estimated_duration_ms: int = 0
    confidence: float = 0.0
    trace_id: Optional[str] = None


# ============== Status 接口 ==============


class StepInfo(BaseModel):
    """步骤信息"""

    order: int
    type: str
    status: StepStatus
    skill: Optional[str] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None

    model_config = {"use_enum_values": True}


class StatusResponse(BaseModel):
    """GET /runtime/status/{task_id} 响应"""

    task_id: str
    status: TaskStatus
    current_step: int = 0
    total_steps: int = 0
    progress: float = 0.0
    started_at: Optional[datetime] = None
    estimated_finish_at: Optional[datetime] = None
    steps: List[StepInfo] = Field(default_factory=list)
    trace_id: Optional[str] = None

    model_config = {"use_enum_values": True}


# ============== Cancel 接口 ==============


class CancelResponse(BaseModel):
    """POST /runtime/cancel/{task_id} 响应"""

    task_id: str
    status: TaskStatus
    cancelled_at: datetime = Field(default_factory=_utc_now)
    reason: str = "user_requested"

    model_config = {"use_enum_values": True}


# ============== Health 接口 ==============


class HealthResponse(BaseModel):
    """GET /runtime/health 响应"""

    status: str  # healthy / degraded / unhealthy
    version: str
    timestamp: datetime = Field(default_factory=_utc_now)
    checks: Dict[str, str] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)
