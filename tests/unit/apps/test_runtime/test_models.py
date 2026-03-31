"""Runtime API 请求/响应模型测试

测试依据：specs/runtime-spec.md
"""

from apps.runtime.models import (
    CancelResponse,
    ExecuteRequest,
    ExecuteResponse,
    HealthResponse,
    PlanRequest,
    PlanResponse,
    PlanStep,
    StatusResponse,
    StepStatus,
)


class TestExecuteRequest:
    """POST /runtime/execute 请求模型"""

    def test_execute_request_required_fields(self):
        """必填字段：employee_id, input"""
        req = ExecuteRequest(
            employee_id="agent-001",
            input={"query": "查询今日工单"},
        )
        assert req.employee_id == "agent-001"
        assert req.input.query == "查询今日工单"

    def test_execute_request_optional_fields(self):
        """可选字段：task_id, context"""
        req = ExecuteRequest(
            employee_id="agent-001",
            input={"query": "查询今日工单"},
            task_id="task-xxx",
            context={
                "session_id": "sess-xxx",
                "user_id": "user-xxx",
            },
        )
        assert req.task_id == "task-xxx"
        assert req.context.session_id == "sess-xxx"

    def test_execute_request_task_type_defaults(self):
        """task_type 默认为 inquiry"""
        req = ExecuteRequest(
            employee_id="agent-001",
            input={"query": "查询今日工单"},
        )
        assert req.task_type.value == "inquiry"

    def test_execute_request_full(self):
        """完整请求示例"""
        req = ExecuteRequest(
            employee_id="agent-001",
            task_id="task-xxx",
            task_type="action",
            input={
                "query": "更新工单状态",
                "params": {"ticket_id": "T-001", "status": "closed"},
            },
            context={
                "session_id": "sess-xxx",
                "user_id": "user-xxx",
                "skills": ["skill-ticket-update"],
                "attachments": [],
            },
        )
        assert req.task_type == "action"
        assert req.input.params["ticket_id"] == "T-001"


class TestExecuteResponse:
    """POST /runtime/execute 响应模型"""

    def test_execute_response_success(self):
        """成功响应"""
        resp = ExecuteResponse(
            task_id="task-xxx",
            status="completed",
            result={
                "answer": "今日有3个P1工单",
                "sources": ["kb-001"],
                "actions": [],
            },
            duration_ms=1250,
        )
        assert resp.status == "completed"
        assert resp.result.answer == "今日有3个P1工单"
        assert resp.duration_ms == 1250

    def test_execute_response_running(self):
        """运行中响应"""
        resp = ExecuteResponse(
            task_id="task-xxx",
            status="running",
        )
        assert resp.status == "running"
        assert resp.result is None

    def test_execute_response_with_trace(self):
        """响应包含 trace_id"""
        resp = ExecuteResponse(
            task_id="task-xxx",
            status="completed",
            trace_id="trace-abc123",
        )
        assert resp.trace_id == "trace-abc123"


class TestPlanRequest:
    """POST /runtime/plan 请求模型"""

    def test_plan_request_minimal(self):
        """最小请求"""
        req = PlanRequest(
            employee_id="agent-001",
            task="查询今日P1工单并总结",
        )
        assert req.employee_id == "agent-001"
        assert req.available_skills == []

    def test_plan_request_with_skills(self):
        """带技能列表的请求"""
        req = PlanRequest(
            employee_id="agent-001",
            task="查询今日P1工单并总结",
            available_skills=["skill-ticket", "skill-summary"],
        )
        assert len(req.available_skills) == 2


class TestPlanResponse:
    """POST /runtime/plan 响应模型"""

    def test_plan_response_structure(self):
        """计划响应结构"""
        resp = PlanResponse(
            plan_id="plan-xxx",
            task_id="task-xxx",
            steps=[
                PlanStep(
                    order=1,
                    type="call_skill",
                    skill="skill-ticket",
                    input={"filter": "priority=P1"},
                    expected_output="P1工单列表",
                ),
                PlanStep(
                    order=2,
                    type="call_skill",
                    skill="skill-summary",
                    input={"data": "${step1.output}"},
                    expected_output="工单总结",
                ),
            ],
            estimated_duration_ms=3000,
            confidence=0.85,
        )
        assert len(resp.steps) == 2
        assert resp.steps[0].order == 1
        assert resp.steps[1].order == 2
        assert resp.confidence == 0.85

    def test_plan_step_types(self):
        """支持的步骤类型"""
        for step_type in ["call_skill", "call_connector", "reflect", "complete"]:
            step = PlanStep(order=1, type=step_type)
            assert step.type == step_type


class TestStatusResponse:
    """GET /runtime/status/{task_id} 响应模型"""

    def test_status_response_running(self):
        """运行中状态"""
        resp = StatusResponse(
            task_id="task-xxx",
            status="running",
            current_step=2,
            total_steps=3,
            progress=0.67,
        )
        assert resp.status == "running"
        assert resp.current_step == 2
        assert resp.progress == 0.67

    def test_status_response_completed(self):
        """已完成状态"""
        resp = StatusResponse(
            task_id="task-xxx",
            status="completed",
            current_step=3,
            total_steps=3,
            progress=1.0,
        )
        assert resp.status == "completed"
        assert resp.progress == 1.0

    def test_step_status_values(self):
        """步骤状态枚举"""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.RUNNING.value == "running"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"


class TestCancelResponse:
    """POST /runtime/cancel/{task_id} 响应模型"""

    def test_cancel_response(self):
        """取消响应"""
        resp = CancelResponse(
            task_id="task-xxx",
            status="cancelled",
            reason="user_requested",
        )
        assert resp.status == "cancelled"
        assert resp.reason == "user_requested"


class TestHealthResponse:
    """GET /runtime/health 响应模型"""

    def test_health_response(self):
        """健康检查响应"""
        resp = HealthResponse(
            status="healthy",
            version="0.1.0",
            stats={
                "active_tasks": 5,
                "completed_tasks_today": 123,
            },
        )
        assert resp.status == "healthy"
        assert resp.stats["active_tasks"] == 5
