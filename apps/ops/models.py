# apps/ops/models.py — Pydantic models for ops API
from typing import Optional

from pydantic import BaseModel, Field


def to_camel(s: str) -> str:
    """Convert snake_case to camelCase for JSON response."""
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class DashboardStats(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    online_count: int = Field(alias="onlineCount")
    total_token_usage: int = Field(alias="totalTokenUsage")
    monthly_tasks: int = Field(alias="monthlyTasks")
    system_load: int = Field(alias="systemLoad")
    task_success_rate: float = Field(alias="taskSuccessRate")
    token_efficiency: float = Field(alias="tokenEfficiency")
    task_trend_change: float = Field(alias="tokenTrendChange")
    success_rate_change: float = Field(alias="successRateChange")
    # nested object as camelCase
    task_trend_change_val: float = Field(default=0, alias="taskTrendChangeVal")
    task_trend_direction: str = Field(default="up", alias="taskTrendDirection")


class StatusItem(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    status: str
    label: str
    count: int
    color: str


class TrendItem(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    date: str
    value: float


class TaskDetail(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    dates: list[str]
    success: list[int]
    failed: list[int]


class CapabilityItem(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    role: str
    alias: str
    dept: str
    pct: int


class ActivityItem(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    id: str
    type: str
    employee_id: Optional[str] = Field(default=None, alias="employeeId")
    alias: str
    role: str
    dept: str
    content: str
    timestamp: str


# Onboarding models
class SoulConfig(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    mbti: str
    style: str
    priority: str


class ScalingConfig(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    min_replicas: int = Field(alias="minReplicas")
    max_replicas: int = Field(alias="maxReplicas")
    target_load: int = Field(alias="targetLoad")


class VersionConfig(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    soul: SoulConfig
    skills: list[str]
    tools: list[str]
    model: str


class BlueprintVersion(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    version: str
    status: str
    traffic: int
    replicas: int
    config: VersionConfig
    scaling: ScalingConfig


class Capacity(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    used: int
    max: int


class Blueprint(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    id: str
    role: str
    alias: str
    department: str
    versions: list[BlueprintVersion]
    capacity: Capacity


# Deploy request
class DeployRequest(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    role: str
    alias: str
    department: str
    scaling: ScalingConfig
