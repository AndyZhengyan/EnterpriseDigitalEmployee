"""ConnectorHub errors — re-export 4xxx codes from common/errors."""

from __future__ import annotations

from typing import Any, Optional

from common.errors import ErrorCode

# Re-export 4xxx error codes from common.errors
CONNECTOR_NOT_FOUND = ErrorCode.CONNECTOR_NOT_FOUND
CONNECTOR_CAPABILITY_NOT_FOUND = ErrorCode.CONNECTOR_CAPABILITY_NOT_FOUND
CONNECTOR_EXECUTION_FAILED = ErrorCode.CONNECTOR_EXECUTION_FAILED
CONNECTOR_TIMEOUT = ErrorCode.CONNECTOR_TIMEOUT
CONNECTOR_UNHEALTHY = ErrorCode.CONNECTOR_UNHEALTHY


class ConnectorHubError(Exception):
    """Base exception for ConnectorHub errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.CONNECTOR_EXECUTION_FAILED,
        connector_id: Optional[str] = None,
        capability: Optional[str] = None,
        **extra: Any,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.connector_id = connector_id
        self.capability = capability


class ConnectorNotFoundError(ConnectorHubError):
    """Raised when a connector ID is not found in the registry."""

    def __init__(self, connector_id: str, **extra: Any):
        super().__init__(
            f"Connector not found: {connector_id}",
            code=ErrorCode.CONNECTOR_NOT_FOUND,
            connector_id=connector_id,
            **extra,
        )


class ConnectorCapabilityNotFoundError(ConnectorHubError):
    """Raised when a connector does not have the requested capability."""

    def __init__(self, connector_id: str, capability: str, **extra: Any):
        super().__init__(
            f"Capability '{capability}' not found on connector '{connector_id}'",
            code=ErrorCode.CONNECTOR_CAPABILITY_NOT_FOUND,
            connector_id=connector_id,
            capability=capability,
            **extra,
        )


class ConnectorExecutionFailedError(ConnectorHubError):
    """Raised when connector invocation fails."""

    def __init__(self, connector_id: str, reason: str, **extra: Any):
        super().__init__(
            f"Connector '{connector_id}' execution failed: {reason}",
            code=ErrorCode.CONNECTOR_EXECUTION_FAILED,
            connector_id=connector_id,
            **extra,
        )


class ConnectorTimeoutError(ConnectorHubError):
    """Raised when connector invocation times out."""

    def __init__(self, connector_id: str, timeout_seconds: int, **extra: Any):
        super().__init__(
            f"Connector '{connector_id}' timed out after {timeout_seconds}s",
            code=ErrorCode.CONNECTOR_TIMEOUT,
            connector_id=connector_id,
            **extra,
        )


class ConnectorHealthError(ConnectorHubError):
    """Raised when a connector health check fails."""

    def __init__(self, connector_id: str, reason: str, **extra: Any):
        super().__init__(
            f"Connector '{connector_id}' is unhealthy: {reason}",
            code=ErrorCode.CONNECTOR_UNHEALTHY,
            connector_id=connector_id,
            **extra,
        )
