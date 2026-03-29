"""e-Agent-OS 错误码定义

错误码规范：
  1xxx  - 网关层
  2xxx  - 运行时层
  3xxx  - 模型层
  4xxx  - 连接器层
  5xxx  - 技能层
  6xxx  - 知识层
  9xxx  - 系统层
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(Enum):
    # ========== 网关层 (1xxx) ==========
    GATEWAY_AUTH_FAILED = (1001, "鉴权失败", True)
    GATEWAY_TOKEN_EXPIRED = (1002, "Token已过期", True)
    GATEWAY_RATE_LIMITED = (1003, "请求频率超限", True)
    GATEWAY_TENANT_NOT_FOUND = (1004, "租户不存在", False)
    GATEWAY_CIRCUIT_OPEN = (1005, "服务熔断中，请稍后重试", True)
    GATEWAY_INVALID_REQUEST = (1006, "无效请求", False)
    GATEWAY_SESSION_NOT_FOUND = (1007, "会话不存在", False)

    # ========== 运行时层 (2xxx) ==========
    RUNTIME_TASK_NOT_FOUND = (2001, "任务不存在", False)
    RUNTIME_TASK_CANCELLED = (2002, "任务已取消", False)
    RUNTIME_PLAN_FAILED = (2003, "生成执行计划失败", True)
    RUNTIME_EXECUTION_FAILED = (2004, "任务执行失败", True)
    RUNTIME_TIMEOUT = (2005, "任务执行超时", True)
    RUNTIME_ESCALATED = (2006, "任务已升级人工处理", False)
    RUNTIME_AGENT_NOT_FOUND = (2007, "Agent不存在", False)
    RUNTIME_SKILL_NOT_FOUND = (2008, "所需技能未找到", False)
    RUNTIME_INVALID_CONTEXT = (2009, "任务上下文无效", False)

    # ========== 模型层 (3xxx) ==========
    MODEL_PROVIDER_ERROR = (3001, "模型服务商错误", True)
    MODEL_QUOTA_EXCEEDED = (3002, "模型配额超限", True)
    MODEL_INVALID_REQUEST = (3003, "模型请求无效", False)
    MODEL_TIMEOUT = (3004, "模型响应超时", True)
    MODEL_NOT_AVAILABLE = (3005, "请求的模型不可用", True)
    MODEL_ROUTING_FAILED = (3006, "模型路由失败", True)

    # ========== 连接器层 (4xxx) ==========
    CONNECTOR_NOT_FOUND = (4001, "连接器不存在", False)
    CONNECTOR_CAPABILITY_NOT_FOUND = (4002, "连接器能力不存在", False)
    CONNECTOR_EXECUTION_FAILED = (4003, "连接器执行失败", True)
    CONNECTOR_TIMEOUT = (4004, "连接器执行超时", True)
    CONNECTOR_UNHEALTHY = (4005, "连接器不健康", False)
    CONNECTOR_APPROVAL_REQUIRED = (4006, "此操作需要人工审批", False)

    # ========== 技能层 (5xxx) ==========
    SKILL_NOT_FOUND = (5001, "技能不存在", False)
    SKILL_INVOCATION_FAILED = (5002, "技能调用失败", True)
    SKILL_NOT_APPLICABLE = (5003, "当前技能不适用于此任务", False)
    SKILL_DEPRECATED = (5004, "技能已废弃", False)

    # ========== 知识层 (6xxx) ==========
    KNOWLEDGE_NOT_FOUND = (6001, "知识不存在", False)
    KNOWLEDGE_INDEX_FAILED = (6002, "知识索引失败", True)
    KNOWLEDGE_RETRIEVAL_FAILED = (6003, "知识检索失败", True)
    KNOWLEDGE_UNAUTHORIZED = (6004, "无权访问此知识", False)

    # ========== 系统层 (9xxx) ==========
    SYSTEM_INTERNAL_ERROR = (9001, "系统内部错误", True)
    SYSTEM_UNAVAILABLE = (9002, "系统服务不可用", True)
    SYSTEM_DATABASE_ERROR = (9003, "数据库错误", True)
    SYSTEM_CONFIG_ERROR = (9004, "配置错误", False)

    def __init__(self, code: int, message: str, recoverable: bool):
        self.code = code
        self.message = message
        self.recoverable = recoverable

    def to_dict(self, details: Optional[str] = None, task_id: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
        """转换为错误响应字典"""
        result = {
            "code": self.code,
            "message": self.message,
            "details": details,
            "recoverable": self.recoverable,
        }
        if task_id:
            result["task_id"] = task_id
        result.update(extra)
        return result


class EAgentError(Exception):
    """e-Agent-OS 基础异常"""

    def __init__(
        self,
        error_code: ErrorCode,
        details: Optional[str] = None,
        task_id: Optional[str] = None,
        **extra: Any,
    ):
        self.error_code = error_code
        self.details = details
        self.task_id = task_id
        self.extra = extra
        super().__init__(error_code.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为错误响应字典"""
        return self.error_code.to_dict(
            details=self.details,
            task_id=self.task_id,
            **self.extra,
        )


# ========== 网关层异常 ==========


class GatewayAuthError(EAgentError):
    def __init__(self, details: Optional[str] = None):
        super().__init__(ErrorCode.GATEWAY_AUTH_FAILED, details=details)


class GatewayRateLimitError(EAgentError):
    def __init__(self, details: Optional[str] = None):
        super().__init__(ErrorCode.GATEWAY_RATE_LIMITED, details=details)


class GatewayTenantNotFoundError(EAgentError):
    def __init__(self, tenant_id: str):
        super().__init__(ErrorCode.GATEWAY_TENANT_NOT_FOUND, details=f"租户 {tenant_id} 不存在")


class GatewayCircuitOpenError(EAgentError):
    def __init__(self):
        super().__init__(ErrorCode.GATEWAY_CIRCUIT_OPEN)


# ========== 运行时层异常 ==========


class RuntimeTaskNotFoundError(EAgentError):
    def __init__(self, task_id: str):
        super().__init__(ErrorCode.RUNTIME_TASK_NOT_FOUND, task_id=task_id)


class RuntimePlanFailedError(EAgentError):
    def __init__(self, details: Optional[str] = None):
        super().__init__(ErrorCode.RUNTIME_PLAN_FAILED, details=details)


class RuntimeExecutionError(EAgentError):
    def __init__(self, task_id: str, details: Optional[str] = None):
        super().__init__(ErrorCode.RUNTIME_EXECUTION_FAILED, task_id=task_id, details=details)


class RuntimeTimeoutError(EAgentError):
    def __init__(self, task_id: str):
        super().__init__(ErrorCode.RUNTIME_TIMEOUT, task_id=task_id)


class RuntimeEscalatedError(EAgentError):
    def __init__(self, task_id: str):
        super().__init__(ErrorCode.RUNTIME_ESCALATED, task_id=task_id)


# ========== 模型层异常 ==========


class ModelProviderError(EAgentError):
    def __init__(self, details: Optional[str] = None):
        super().__init__(ErrorCode.MODEL_PROVIDER_ERROR, details=details)


class ModelQuotaExceededError(EAgentError):
    def __init__(self, details: Optional[str] = None):
        super().__init__(ErrorCode.MODEL_QUOTA_EXCEEDED, details=details)


class ModelTimeoutError(EAgentError):
    def __init__(self, details: Optional[str] = None):
        super().__init__(ErrorCode.MODEL_TIMEOUT, details=details)


class ModelRoutingError(EAgentError):
    def __init__(self, details: Optional[str] = None):
        super().__init__(ErrorCode.MODEL_ROUTING_FAILED, details=details)


# ========== 连接器层异常 ==========


class ConnectorNotFoundError(EAgentError):
    def __init__(self, connector_id: str):
        super().__init__(ErrorCode.CONNECTOR_NOT_FOUND, details=f"连接器 {connector_id} 不存在")


class ConnectorExecutionError(EAgentError):
    def __init__(self, connector_id: str, details: Optional[str] = None):
        super().__init__(
            ErrorCode.CONNECTOR_EXECUTION_FAILED,
            details=f"连接器 {connector_id} 执行失败: {details}" if details else None,
        )


class ConnectorTimeoutError(EAgentError):
    def __init__(self, connector_id: str):
        super().__init__(
            ErrorCode.CONNECTOR_TIMEOUT,
            details=f"连接器 {connector_id} 执行超时",
        )


class ConnectorApprovalRequiredError(EAgentError):
    def __init__(self, action: str):
        super().__init__(
            ErrorCode.CONNECTOR_APPROVAL_REQUIRED,
            details=f"操作 {action} 需要人工审批",
        )
