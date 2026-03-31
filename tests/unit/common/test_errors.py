"""common.errors 单元测试"""

from common.errors import (
    ConnectorApprovalRequiredError,
    ConnectorExecutionError,
    ConnectorNotFoundError,
    ConnectorTimeoutError,
    EAgentError,
    ErrorCode,
    GatewayAuthError,
    GatewayRateLimitError,
    GatewayTenantNotFoundError,
    ModelQuotaExceededError,
    ModelRoutingError,
    ModelTimeoutError,
    RuntimeEscalatedError,
    RuntimeExecutionError,
    RuntimePlanFailedError,
    RuntimeTaskNotFoundError,
    RuntimeTimeoutError,
)


class TestErrorCode:
    def test_all_errors_have_unique_codes(self):
        """确保所有错误码唯一"""
        codes = [e.value[0] if hasattr(e.value, "__getitem__") else e.code for e in ErrorCode]
        assert len(codes) == len(set(codes))

    def test_gateway_error_codes_start_with_1(self):
        """网关层错误码以 1xxx 开头"""
        assert ErrorCode.GATEWAY_AUTH_FAILED.code == 1001
        assert ErrorCode.GATEWAY_RATE_LIMITED.code == 1003

    def test_runtime_error_codes_start_with_2(self):
        """运行时层错误码以 2xxx 开头"""
        assert ErrorCode.RUNTIME_TASK_NOT_FOUND.code == 2001
        assert ErrorCode.RUNTIME_PLAN_FAILED.code == 2003

    def test_model_error_codes_start_with_3(self):
        """模型层错误码以 3xxx 开头"""
        assert ErrorCode.MODEL_PROVIDER_ERROR.code == 3001
        assert ErrorCode.MODEL_QUOTA_EXCEEDED.code == 3002

    def test_connector_error_codes_start_with_4(self):
        """连接器层错误码以 4xxx 开头"""
        assert ErrorCode.CONNECTOR_NOT_FOUND.code == 4001
        assert ErrorCode.CONNECTOR_EXECUTION_FAILED.code == 4003


class TestEAgentError:
    def test_base_error_to_dict(self):
        """测试基础异常转换为字典"""
        err = EAgentError(
            ErrorCode.GATEWAY_AUTH_FAILED,
            details="Token已过期",
        )
        result = err.to_dict()
        assert result["code"] == 1001
        assert result["message"] == "鉴权失败"
        assert result["details"] == "Token已过期"
        assert result["recoverable"] is True

    def test_error_with_task_id(self):
        """测试带 task_id 的错误"""
        err = RuntimeTaskNotFoundError(task_id="task-abc123")
        result = err.to_dict()
        assert result["task_id"] == "task-abc123"
        assert result["code"] == 2001


class TestGatewayErrors:
    def test_gateway_auth_error(self):
        err = GatewayAuthError(details="无效Token")
        assert err.error_code == ErrorCode.GATEWAY_AUTH_FAILED
        assert err.to_dict()["code"] == 1001

    def test_gateway_rate_limit_error(self):
        err = GatewayRateLimitError()
        assert err.error_code == ErrorCode.GATEWAY_RATE_LIMITED

    def test_gateway_tenant_not_found_error(self):
        err = GatewayTenantNotFoundError(tenant_id="tenant-xxx")
        result = err.to_dict()
        assert "tenant-xxx" in result["details"]


class TestRuntimeErrors:
    def test_runtime_task_not_found_error(self):
        err = RuntimeTaskNotFoundError(task_id="task-001")
        result = err.to_dict()
        assert result["task_id"] == "task-001"
        assert result["code"] == 2001

    def test_runtime_plan_failed_error(self):
        err = RuntimePlanFailedError(details="模型响应超时")
        result = err.to_dict()
        assert result["code"] == 2003
        assert "模型响应超时" in result["details"]

    def test_runtime_execution_error(self):
        err = RuntimeExecutionError(task_id="task-001", details="技能调用失败")
        result = err.to_dict()
        assert result["task_id"] == "task-001"
        assert result["code"] == 2004

    def test_runtime_timeout_error(self):
        err = RuntimeTimeoutError(task_id="task-001")
        result = err.to_dict()
        assert result["code"] == 2005
        assert result["recoverable"] is True

    def test_runtime_escalated_error(self):
        err = RuntimeEscalatedError(task_id="task-001")
        result = err.to_dict()
        assert result["code"] == 2006
        assert result["recoverable"] is False  # 升级人工不可恢复


class TestModelErrors:
    def test_model_quota_exceeded_error(self):
        err = ModelQuotaExceededError(details="今日配额已用完")
        result = err.to_dict()
        assert result["code"] == 3002
        assert result["recoverable"] is True

    def test_model_timeout_error(self):
        err = ModelTimeoutError()
        result = err.to_dict()
        assert result["code"] == 3004

    def test_model_routing_error(self):
        err = ModelRoutingError(details="无可用模型")
        result = err.to_dict()
        assert result["code"] == 3006


class TestConnectorErrors:
    def test_connector_not_found_error(self):
        err = ConnectorNotFoundError(connector_id="connector-xxx")
        result = err.to_dict()
        assert result["code"] == 4001
        assert "connector-xxx" in result["details"]

    def test_connector_execution_error(self):
        err = ConnectorExecutionError(
            connector_id="connector-ticket",
            details="API返回500",
        )
        result = err.to_dict()
        assert result["code"] == 4003

    def test_connector_timeout_error(self):
        err = ConnectorTimeoutError(connector_id="connector-ticket")
        result = err.to_dict()
        assert result["code"] == 4004

    def test_connector_approval_required_error(self):
        err = ConnectorApprovalRequiredError(action="delete_ticket")
        result = err.to_dict()
        assert result["code"] == 4006
        assert result["recoverable"] is False
