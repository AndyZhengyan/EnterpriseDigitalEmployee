"""ModelHub errors — uses common/errors.py ErrorCode (3xxx prefix)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from common.errors import EAgentError, ErrorCode

# Re-export for convenience
MODEL_PROVIDER_ERROR = ErrorCode.MODEL_PROVIDER_ERROR
MODEL_QUOTA_EXCEEDED = ErrorCode.MODEL_QUOTA_EXCEEDED
MODEL_INVALID_REQUEST = ErrorCode.MODEL_INVALID_REQUEST
MODEL_TIMEOUT = ErrorCode.MODEL_TIMEOUT
MODEL_NOT_AVAILABLE = ErrorCode.MODEL_NOT_AVAILABLE
MODEL_ROUTING_FAILED = ErrorCode.MODEL_ROUTING_FAILED


class ModelHubError(EAgentError):
    """Raised by ModelHub on provider or routing errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.MODEL_PROVIDER_ERROR,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **extra: Any,
    ):
        super().__init__(error_code=code, details=message, **extra)
        self.provider = provider
        self.model = model

    def to_dict(self) -> Dict[str, Any]:
        d = self.error_code.to_dict(details=self.details, task_id=self.task_id)
        if self.provider:
            d["provider"] = self.provider
        if self.model:
            d["model"] = self.model
        d.update(self.extra)
        return d


class ModelProviderError(ModelHubError):
    def __init__(self, message: str, provider: str, model: Optional[str] = None, **extra: Any):
        super().__init__(message, ErrorCode.MODEL_PROVIDER_ERROR, provider=provider, model=model, **extra)


class ModelQuotaExceededError(ModelHubError):
    def __init__(self, message: str, provider: str, employee_id: str, **extra: Any):
        super().__init__(message, ErrorCode.MODEL_QUOTA_EXCEEDED, provider=provider, **extra)
        self.extra["employee_id"] = employee_id


class ModelTimeoutError(ModelHubError):
    def __init__(self, message: str, provider: str, model: Optional[str] = None):
        super().__init__(message, ErrorCode.MODEL_TIMEOUT, provider=provider, model=model)


class ModelNotAvailableError(ModelHubError):
    def __init__(self, message: str, provider: str, model: Optional[str] = None):
        super().__init__(message, ErrorCode.MODEL_NOT_AVAILABLE, provider=provider, model=model)


class ModelRoutingFailedError(ModelHubError):
    def __init__(self, message: str):
        super().__init__(message, ErrorCode.MODEL_ROUTING_FAILED)


class ModelSidecarStartupError(ModelHubError):
    """Raised when the piagent sidecar process fails to start."""

    def __init__(self, message: str, provider: str):
        # Use SYSTEM_INTERNAL_ERROR since no 3xxx slot available for this specific case
        super().__init__(message, ErrorCode.SYSTEM_INTERNAL_ERROR, provider=provider)
