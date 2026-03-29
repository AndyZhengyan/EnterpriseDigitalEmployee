"""e-Agent-OS 核心数据模型"""

from __future__ import annotations

import uuid
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

    INQUIRY = "inquiry"  # 查询类
    ACTION = "action"  # 操作类
    ANALYSIS = "analysis"  # 分析类


class TaskStatus(str, Enum):
    """任务状态"""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"  # 升级人工


class Priority(str, Enum):
    """任务优先级"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Channel(str, Enum):
    """请求渠道"""

    FEISHU = "feishu"
    WEBHOOK = "webhook"
    SCHEDULED = "scheduled"
    API = "api"


class RiskLevel(str, Enum):
    """风险等级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============== 基础模型 ==============


class BaseResponse(BaseModel):
    """统一响应格式"""

    success: bool = True
    data: Any = None
    error: Optional[ErrorDetail] = None
    trace_id: str = Field(default_factory=lambda: f"trace-{uuid.uuid4().hex[:16]}")
    timestamp: datetime = Field(default_factory=_utc_now)


class ErrorDetail(BaseModel):
    """错误详情"""

    code: int
    message: str
    details: Optional[str] = None
    task_id: Optional[str] = None
    recoverable: bool = True
    suggestion: Optional[str] = None


# ============== 任务模型 ==============


class TaskContext(BaseModel):
    """任务上下文"""

    user_id: str
    session_id: str
    tenant_id: str
    employee_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskInput(BaseModel):
    """任务输入"""

    query: str
    params: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """任务"""

    id: str = Field(default_factory=lambda: f"task-{uuid.uuid4().hex[:12]}")
    employee_id: str
    source_channel: Channel
    task_type: TaskType
    priority: Priority = Priority.NORMAL
    status: TaskStatus = TaskStatus.QUEUED
    input_content: str
    output_content: Optional[str] = None
    error_message: Optional[str] = None
    context: Optional[TaskContext] = None
    callback_url: Optional[str] = None
    trace_id: str = Field(default_factory=lambda: f"trace-{uuid.uuid4().hex[:16]}")
    created_at: datetime = Field(default_factory=_utc_now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    model_config = {"use_enum_values": True}


class TaskStep(BaseModel):
    """任务步骤"""

    id: str = Field(default_factory=lambda: f"step-{uuid.uuid4().hex[:12]}")
    task_id: str
    step_order: int
    step_type: str  # plan / call_skill / call_connector / reflect / complete
    action_name: Optional[str] = None
    input_snapshot: Optional[Dict[str, Any]] = None
    output_snapshot: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    status: TaskStatus = TaskStatus.QUEUED
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    latency_ms: Optional[int] = None

    model_config = {"use_enum_values": True}


# ============== Session 模型 ==============


class Message(BaseModel):
    """会话消息"""

    role: str  # user / assistant / system
    content: str
    timestamp: datetime = Field(default_factory=_utc_now)


class Session(BaseModel):
    """会话"""

    id: str = Field(default_factory=lambda: f"sess-{uuid.uuid4().hex[:12]}")
    employee_id: str
    user_id: str
    tenant_id: str
    messages: List[Message] = Field(default_factory=list)
    working_context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


# ============== AgentFamily 模型 ==============


class AgentSoul(BaseModel):
    """Agent人格配置"""

    mbti: Optional[str] = None
    communication_style: str = "专业、简洁"
    risk_preference: str = "medium"  # low / medium / high


class AgentIdentity(BaseModel):
    """Agent身份配置"""

    role: str  # 岗位角色
    employee_id: str  # 工号
    feishu_id: Optional[str] = None
    organization: Optional[str] = None
    reporting_to: Optional[str] = None


class AgentConfig(BaseModel):
    """Agent工作配置"""

    responsibilities: List[str] = Field(default_factory=list)
    service_for: List[str] = Field(default_factory=list)
    boundaries: List[str] = Field(default_factory=list)
    kpi: List[Dict[str, str]] = Field(default_factory=list)
    collaboration_matrix: List[Dict[str, str]] = Field(default_factory=list)


class AgentPolicy(BaseModel):
    """Agent治理策略"""

    skills: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    approval_required: List[str] = Field(default_factory=list)
    max_single_task_cost: Optional[str] = None


class AgentFamily(BaseModel):
    """AgentFamily（岗位族）"""

    family_id: str
    family_name: str
    description: Optional[str] = None
    soul: AgentSoul = Field(default_factory=AgentSoul)
    identity: AgentIdentity
    agent: AgentConfig = Field(default_factory=AgentConfig)
    policy: AgentPolicy = Field(default_factory=AgentPolicy)
    version: str = "1.0"
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


# ============== Skill 模型 ==============


class SkillCapability(BaseModel):
    """技能能力"""

    name: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    idempotent: bool = True
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False


class Skill(BaseModel):
    """技能"""

    id: str
    name: str
    description: str
    level: str = "L2"  # L1 / L2 / L3
    version: str = "1.0"
    capabilities: List[SkillCapability] = Field(default_factory=list)
    agent_families: List[str] = Field(default_factory=list)  # 绑定的AgentFamily
    status: str = "draft"  # draft / testing / staging / published / deprecated
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    model_config = {"use_enum_values": True}


# ============== Model 模型 ==============


class ModelProvider(BaseModel):
    """模型提供商"""

    name: str
    endpoint: str
    api_key_env: str  # 环境变量名
    models: List[str]
    priority: int = 0  # 路由优先级


class ModelUsage(BaseModel):
    """模型用量"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ModelCallResult(BaseModel):
    """模型调用结果"""

    content: Optional[str] = None
    model: str
    usage: ModelUsage
    latency_ms: int
    status: str = "success"  # success / failed
    error_message: Optional[str] = None


# ============== Connector 模型 ==============


class RetryPolicy(BaseModel):
    """重试策略"""

    max_retries: int = 2
    backoff_multiplier: float = 2.0
    initial_delay_ms: int = 100


class ConnectorCapability(BaseModel):
    """连接器能力"""

    name: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    idempotent: bool = True
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False


class Connector(BaseModel):
    """连接器"""

    id: str
    name: str
    type: str  # cli / mcp / api / db / cu
    config: Dict[str, Any] = Field(default_factory=dict)
    capabilities: List[ConnectorCapability] = Field(default_factory=list)
    health_check_url: Optional[str] = None
    timeout_seconds: int = 30
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    status: str = "active"  # active / inactive / degraded
