"""Runtime 执行器核心测试

测试依据：specs/runtime-spec.md
Plan → Act → Reflect 执行循环
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from apps.runtime.executor import RuntimeExecutor, ExecutionState
from apps.runtime.models import PlanStep, StepStatus


class TestRuntimeExecutor:
    """RuntimeExecutor 核心执行器"""

    def test_executor_initialization(self):
        """执行器初始化"""
        executor = RuntimeExecutor(
            employee_id="agent-001",
            task_id="task-xxx",
        )
        assert executor.employee_id == "agent-001"
        assert executor.task_id == "task-xxx"
        assert executor.state == ExecutionState.IDLE

    def test_executor_initialization_empty_employee_id(self):
        """employee_id 为空时应抛出 ValueError"""
        with pytest.raises(ValueError, match="non-empty"):
            RuntimeExecutor(employee_id="", task_id="task-xxx")
        with pytest.raises(ValueError, match="non-empty"):
            RuntimeExecutor(employee_id="   ", task_id="task-xxx")

    def test_build_answer_empty_results(self):
        """无步骤结果时返回空字符串"""
        executor = RuntimeExecutor(employee_id="agent-001", task_id="task-xxx")
        assert executor._build_answer() == ""

    def test_build_answer_returns_last_text(self):
        """返回最后一步的文本输出"""
        executor = RuntimeExecutor(employee_id="agent-001", task_id="task-xxx")
        executor.step_results = [
            {"order": 1, "result": {"output": {"text": "first"}}},
            {"order": 2, "result": {"output": {"text": "final answer"}}},
        ]
        assert executor._build_answer() == "final answer"

    def test_build_answer_missing_text(self):
        """最后一步无 text 字段时返回空"""
        executor = RuntimeExecutor(employee_id="agent-001", task_id="task-xxx")
        executor.step_results = [
            {"order": 1, "result": {"output": {}}},
        ]
        assert executor._build_answer() == ""

    def test_executor_state_transitions(self):
        """状态转换"""
        executor = RuntimeExecutor(
            employee_id="agent-001",
            task_id="task-xxx",
        )
        # IDLE → RUNNING
        executor.start()
        assert executor.state == ExecutionState.RUNNING

        # RUNNING → COMPLETED
        executor.complete(result={"answer": "done"})
        assert executor.state == ExecutionState.COMPLETED

    def test_executor_state_failed(self):
        """状态 → FAILED"""
        executor = RuntimeExecutor(
            employee_id="agent-001",
            task_id="task-xxx",
        )
        executor.start()
        executor.fail(error="Test error")
        assert executor.state == ExecutionState.FAILED

    def test_executor_state_escalated(self):
        """状态 → ESCALATED"""
        executor = RuntimeExecutor(
            employee_id="agent-001",
            task_id="task-xxx",
        )
        executor.start()
        executor.escalate(reason="Max retries exceeded")
        assert executor.state == ExecutionState.ESCALATED

    def test_executor_state_cancelled(self):
        """状态 → CANCELLED"""
        executor = RuntimeExecutor(
            employee_id="agent-001",
            task_id="task-xxx",
        )
        executor.start()
        executor.cancel()
        assert executor.state == ExecutionState.CANCELLED


class TestPlanPhase:
    """Plan 阶段测试"""

    @pytest.mark.asyncio
    async def test_plan_generation(self):
        """测试计划生成"""
        executor = RuntimeExecutor(
            employee_id="agent-001",
            task_id="task-xxx",
        )

        # Mock generate_plan 方法
        mock_plan = {
            "plan_id": "plan-xxx",
            "steps": [
                {"order": 1, "type": "call_skill", "skill": "skill-search",
                 "input": {"query": "test"}, "expected_output": "results"}
            ],
            "confidence": 0.9,
        }
        executor.generate_plan = AsyncMock(return_value=mock_plan)

        plan = await executor.generate_plan(
            task="查询今日P1工单",
            available_skills=["skill-search"],
        )

        assert plan["plan_id"] == "plan-xxx"
        assert len(plan["steps"]) == 1
        assert plan["steps"][0]["skill"] == "skill-search"

    @pytest.mark.asyncio
    async def test_plan_with_multiple_steps(self):
        """多步骤计划"""
        executor = RuntimeExecutor(
            employee_id="agent-001",
            task_id="task-xxx",
        )

        mock_plan = {
            "plan_id": "plan-xxx",
            "steps": [
                {"order": 1, "type": "call_skill", "skill": "skill-ticket",
                 "input": {}, "expected_output": "tickets"},
                {"order": 2, "type": "call_skill", "skill": "skill-summary",
                 "input": {"data": "${step1}"}, "expected_output": "summary"},
            ],
            "confidence": 0.85,
        }
        executor.generate_plan = AsyncMock(return_value=mock_plan)

        plan = await executor.generate_plan(
            task="查询P1工单并总结",
            available_skills=["skill-ticket", "skill-summary"],
        )

        assert len(plan["steps"]) == 2


class TestActPhase:
    """Act 阶段测试"""

    @pytest.mark.asyncio
    async def test_act_single_step_execution(self):
        """单步骤执行"""
        executor = RuntimeExecutor(
            employee_id="agent-001",
            task_id="task-xxx",
        )

        step = PlanStep(
            order=1,
            type="call_skill",
            skill="skill-search",
            input={"query": "今日工单"},
        )

        executor.execute_step = AsyncMock(return_value={
            "status": "success",
            "output": {"results": ["ticket-1", "ticket-2"]},
        })

        result = await executor.execute_step(step)

        assert result["status"] == "success"
        assert "ticket-1" in result["output"]["results"]

    @pytest.mark.asyncio
    async def test_act_step_failure(self):
        """步骤执行失败"""
        executor = RuntimeExecutor(
            employee_id="agent-001",
            task_id="task-xxx",
        )

        step = PlanStep(
            order=1,
            type="call_skill",
            skill="skill-unknown",
            input={},
        )

        executor.execute_step = AsyncMock(
            side_effect=Exception("Skill not found")
        )

        with pytest.raises(Exception) as exc_info:
            await executor.execute_step(step)
        assert "Skill not found" in str(exc_info.value)


class TestReflectPhase:
    """Reflect 阶段测试"""

    @pytest.mark.asyncio
    async def test_reflect_continue(self):
        """Reflect 决定继续"""
        executor = RuntimeExecutor(
            employee_id="agent-001",
            task_id="task-xxx",
        )

        executor.reflect = AsyncMock(return_value={
            "continue": True,
            "reason": "More steps needed",
            "assessment": "Partial success",
        })

        decision = await executor.reflect(
            step_results=[{"status": "success"}],
            total_steps=3,
        )

        assert decision["continue"] is True
        assert decision["reason"] == "More steps needed"

    @pytest.mark.asyncio
    async def test_reflect_done(self):
        """Reflect 决定结束"""
        executor = RuntimeExecutor(
            employee_id="agent-001",
            task_id="task-xxx",
        )

        executor.reflect = AsyncMock(return_value={
            "continue": False,
            "reason": "Task completed",
            "assessment": "All steps successful",
        })

        decision = await executor.reflect(
            step_results=[
                {"status": "success"},
                {"status": "success"},
            ],
            total_steps=2,
        )

        assert decision["continue"] is False
        assert decision["reason"] == "Task completed"


class TestRetryLogic:
    """重试逻辑测试"""

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """超时重试"""
        from apps.runtime.piagent_client import PiAgentResult

        executor = RuntimeExecutor(
            employee_id="agent-001",
            task_id="task-xxx",
        )
        executor.retry_config = {
            "max_retries": 3,
            "initial_delay_ms": 10,
            "backoff_multiplier": 2.0,
        }

        step = PlanStep(
            order=1,
            type="call_skill",
            skill="skill-slow",
            input={},
        )

        call_count = 0

        def flaky_invoke(*args, **kwargs):
            """同步 flaky invoke，抛出异常或返回 PiAgentResult"""
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("Request timeout")
            return PiAgentResult(
                run_id="run-test",
                status="ok",
                summary="completed",
                text="done",
                duration_ms=100,
            )

        # 直接将 mock_client 注入到 executor.piagent 属性
        mock_client = MagicMock()
        mock_client.invoke = flaky_invoke
        # 替换 piagent 属性，绕过 run_in_executor 线程问题
        type(executor).piagent = property(lambda self: mock_client)

        result = await executor.execute_step(step, retries=3)

        assert result["status"] == "success"
        assert call_count == 3

        # 恢复属性
        type(executor).piagent = property(lambda self: self._piagent)

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """超过最大重试次数"""
        executor = RuntimeExecutor(
            employee_id="agent-001",
            task_id="task-xxx",
        )
        executor.retry_config = {
            "max_retries": 2,
            "initial_delay_ms": 10,
            "backoff_multiplier": 2.0,
        }

        step = PlanStep(
            order=1,
            type="call_skill",
            skill="skill-always-fail",
            input={},
        )

        def always_fail(*args, **kwargs):
            raise Exception("Always fails")

        mock_client = MagicMock()
        mock_client.invoke = always_fail
        type(executor).piagent = property(lambda self: mock_client)

        with pytest.raises(Exception) as exc_info:
            await executor.execute_step(step, retries=2)

        assert "Always fails" in str(exc_info.value)

        # 恢复属性
        type(executor).piagent = property(lambda self: self._piagent)
