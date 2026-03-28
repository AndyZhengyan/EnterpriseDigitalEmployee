"""Runtime 执行器核心

规格依据：specs/runtime-spec.md
Plan → Act → Reflect 执行循环，PiAgent 作为执行引擎。
"""

from __future__ import annotations

import asyncio
import enum
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from apps.runtime.models import PlanStep, TaskResult

from .piagent_client import PiAgentClient, PiAgentError, PiAgentResult, PiAgentTimeoutError


class ExecutionState(enum.Enum):
    """执行状态"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"


class RuntimeExecutor:
    """
    Runtime 执行器。

    负责任务的 Plan → Act → Reflect 执行循环。
    PiAgent 作为执行引擎，Runtime 作为企业治理壳。

    PiAgent 角色映射：
    - chat: 前台调度（小虾米）- 简单任务
    - deep-work: 深度专家（小龙）- 复杂多步任务
    - super-work: 超级专家（大龙）- 高风险/关键任务
    """

    # Agent 选择策略
    AGENT_FOR_SIMPLE = "chat"
    AGENT_FOR_COMPLEX = "deep-work"
    AGENT_FOR_CRITICAL = "super-work"

    def __init__(
        self,
        employee_id: str,
        task_id: str,
        retry_config: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        gateway_token: Optional[str] = None,
        timeout_seconds: int = 300,
    ):
        self.employee_id = employee_id
        self.task_id = task_id
        self.agent_id = agent_id or self.AGENT_FOR_SIMPLE
        self.timeout_seconds = timeout_seconds
        self.state = ExecutionState.IDLE
        self.retry_config = retry_config or {
            "max_retries": 3,
            "initial_delay_ms": 500,
            "backoff_multiplier": 2.0,
        }
        self.current_step_index = 0
        self.step_results: List[Dict[str, Any]] = []
        self.result: Optional[TaskResult] = None
        self.error: Optional[str] = None
        self.escalation_reason: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self._piagent: Optional[PiAgentClient] = None
        self._gateway_token = gateway_token

    @property
    def piagent(self) -> PiAgentClient:
        """懒加载 PiAgent 客户端"""
        if self._piagent is None:
            self._piagent = PiAgentClient(
                agent_id=self.agent_id,
                timeout_seconds=self.timeout_seconds,
                gateway_token=self._gateway_token,
            )
        return self._piagent

    def start(self) -> None:
        """开始执行"""
        self.state = ExecutionState.RUNNING
        self.started_at = datetime.utcnow()

    def complete(self, result: Dict[str, Any]) -> None:
        """标记完成"""
        self.state = ExecutionState.COMPLETED
        self.result = TaskResult(**result)

    def fail(self, error: str) -> None:
        """标记失败"""
        self.state = ExecutionState.FAILED
        self.error = error
        self.result = TaskResult(error=error)

    def escalate(self, reason: str) -> None:
        """升级人工"""
        self.state = ExecutionState.ESCALATED
        self.escalation_reason = reason
        self.result = TaskResult(error=f"Escalated: {reason}")

    def cancel(self) -> None:
        """取消执行"""
        self.state = ExecutionState.CANCELLED

    def _select_agent(self, task: str, available_skills: List[str]) -> str:
        """
        根据任务特征选择 Agent。

        策略：
        - 高风险关键词（删除、支付、取消）→ super-work
        - 复杂任务（多步骤、分析、总结）→ deep-work
        - 默认 → chat
        """
        critical_keywords = ["删除", "取消", "支付", "退款", "清空", "drop", "cancel", "delete", "payment"]
        complex_keywords = ["分析", "总结", "对比", "研究", "调查", "analyze", "compare", "research"]

        task_lower = task.lower()
        if any(kw in task_lower for kw in critical_keywords):
            return self.AGENT_FOR_CRITICAL
        if any(kw in task_lower for kw in complex_keywords) or len(available_skills) > 2:
            return self.AGENT_FOR_COMPLEX
        return self.AGENT_FOR_SIMPLE

    async def generate_plan(
        self,
        task: str,
        available_skills: List[str],
    ) -> Dict[str, Any]:
        """
        生成执行计划。

        通过 PiAgent 生成 Plan。
        使用 ReAct 风格的 prompt 让 Agent 分解任务。
        """
        # 选择合适的 Agent
        agent = self._select_agent(task, available_skills)
        if self.agent_id != agent:
            self.agent_id = agent
            self._piagent = None  # 重置客户端

        skills_desc = ", ".join(available_skills) if available_skills else "（无可用技能）"
        prompt = (
            f"你是一个任务规划专家。用户请求：{task}\n"
            f"当前可用的技能：{skills_desc}\n"
            f"请将任务分解为明确的执行步骤（Plan）。\n"
            f"以 JSON 格式返回，格式如下：\n"
            f'{{"plan_id": "<唯一ID>", "steps": ['
            f'{{"order": 1, "type": "call_skill", "skill": "<技能名>", '
            f'"input": {{"<参数>": "<值>"}}, "expected_output": "<预期输出>"}}'
            f'], "confidence": 0.85}}\n'
            f"只返回 JSON，不要解释。"
        )

        loop = asyncio.get_event_loop()
        try:
            piagent_result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self.piagent.invoke(prompt)),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise PiAgentTimeoutError(
                f"Plan generation timed out after {self.timeout_seconds}s",
                agent_id=self.agent_id,
            )

        if not piagent_result.text:
            raise PiAgentError("Empty response from PiAgent during plan generation", agent_id=self.agent_id)

        # 解析 JSON 计划
        return self._parse_plan(piagent_result.text)

    def _parse_plan(self, text: str) -> Dict[str, Any]:
        """从 Agent 输出中解析计划 JSON"""
        import json
        import re

        # 尝试从 markdown 代码块中提取 JSON
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试直接解析整个文本
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试找到 JSON 对象（宽松匹配）
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        raise PiAgentError(
            f"Cannot parse plan JSON from PiAgent response: {text[:300]}",
            agent_id=self.agent_id,
        )

    async def execute_step(
        self,
        step: PlanStep,
        retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        执行单个步骤。

        通过 PiAgent 调用指定的 Skill。
        """
        import json as json_module

        max_retries = retries if retries is not None else self.retry_config["max_retries"]
        delay_ms = self.retry_config["initial_delay_ms"]

        last_error: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                # 构建调用 prompt
                if step.type == "call_skill":
                    skill_name = step.skill or step.skill
                    input_json = json_module.dumps(step.input, ensure_ascii=False)
                    prompt = (
                        f"执行技能：{skill_name}\n"
                        f"输入参数：{input_json}\n"
                        f"请调用该技能并返回结果。只返回结果，不要解释。"
                    )
                elif step.type == "call_connector":
                    connector_name = step.connector or ""
                    input_json = json_module.dumps(step.input, ensure_ascii=False)
                    prompt = (
                        f"执行连接器：{connector_name}\n"
                        f"输入参数：{input_json}\n"
                        f"请执行并返回结果。"
                    )
                else:
                    prompt = f"执行步骤：{step.type}\n输入：{json_module.dumps(step.input, ensure_ascii=False)}"

                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.piagent.invoke(prompt)),
                    timeout=self.timeout_seconds,
                )

                return {
                    "status": "success",
                    "output": {"text": result.text, "raw": result.raw},
                    "duration_ms": result.duration_ms,
                    "run_id": result.run_id,
                }

            except PiAgentError as e:
                last_error = e
                if attempt < max_retries:
                    await asyncio.sleep(delay_ms / 1000.0)
                    delay_ms = int(delay_ms * self.retry_config["backoff_multiplier"])
                continue
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    await asyncio.sleep(delay_ms / 1000.0)
                    delay_ms = int(delay_ms * self.retry_config["backoff_multiplier"])
                continue

        # 所有重试都失败
        raise last_error or Exception("Unknown error in execute_step")

    async def reflect(
        self,
        step_results: List[Dict[str, Any]],
        total_steps: int,
    ) -> Dict[str, Any]:
        """
        反思评估。

        通过 PiAgent 评估当前进度，决定是否继续执行。
        """
        import json as json_module

        results_summary = json_module.dumps(step_results, ensure_ascii=False, default=str)
        completed = len(step_results)
        remaining = total_steps - completed

        prompt = (
            f"任务进度：已完成 {completed}/{total_steps} 个步骤\n"
            f"剩余步骤：{remaining}\n"
            f"最近结果：{results_summary[-500:]}\n"
            f"请评估：\n"
            f'1. 当前进度是否正常？\n'
            f'2. 是否应该继续执行剩余步骤？\n'
            f"以 JSON 格式返回：\n"
            f'{{"continue": true/false, "reason": "<原因>", "assessment": "<评估>"}}\n'
            f"只返回 JSON。"
        )

        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: self.piagent.invoke(prompt)),
            timeout=self.timeout_seconds,
        )

        if not result.text:
            return {"continue": remaining > 0, "reason": "No reflection response", "assessment": "Unknown"}

        return self._parse_reflect(result.text)

    def _parse_reflect(self, text: str) -> Dict[str, Any]:
        """从 Agent 输出中解析反思 JSON"""
        import json
        import re

        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return {"continue": True, "reason": "Parse failed", "assessment": text[:200]}

    async def run(self, task: str, available_skills: List[str]) -> TaskResult:
        """
        运行完整执行循环。

        Plan → Act → Reflect → ... → Complete
        """
        self.start()

        try:
            # 1. Plan
            plan = await self.generate_plan(task, available_skills)
            steps = plan.get("steps", [])

            # 2. Act + Reflect 循环
            for i, step_data in enumerate(steps):
                # 检查是否被取消
                if self.state == ExecutionState.CANCELLED:
                    break

                self.current_step_index = i
                step = PlanStep(**step_data)

                try:
                    # Act
                    result = await self.execute_step(step)
                    self.step_results.append({
                        "order": step.order,
                        "result": result,
                    })

                    # Reflect
                    reflect_decision = await self.reflect(
                        self.step_results,
                        len(steps),
                    )

                    if not reflect_decision.get("continue", False):
                        # 结束
                        break

                except Exception as e:
                    # 步骤失败，尝试重试
                    max_retries = self.retry_config["max_retries"]
                    if max_retries > 0:
                        # 重试
                        await asyncio.sleep(0.1)
                        result = await self.execute_step(
                            step,
                            retries=max_retries - 1,
                        )
                        self.step_results.append({
                            "order": step.order,
                            "result": result,
                        })
                    else:
                        # 重试耗尽
                        if self.retry_config.get("enable_escalation", True):
                            self.escalate(str(e))
                        else:
                            self.fail(str(e))
                        break

            # 3. 完成
            if self.state == ExecutionState.RUNNING:
                self.complete({
                    "answer": self._build_answer(),
                    "sources": [],
                    "actions": [],
                })

        except Exception as e:
            self.fail(str(e))

        return self.result
