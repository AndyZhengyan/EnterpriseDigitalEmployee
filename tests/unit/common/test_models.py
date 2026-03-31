"""common.models 单元测试"""

import pytest
from pydantic import ValidationError

from common.errors import ErrorCode
from common.models import (
    AgentFamily,
    AgentConfig,
    AgentIdentity,
    AgentPolicy,
    AgentSoul,
    Connector,
    ConnectorCapability,
    Message,
    ModelCallResult,
    ModelUsage,
    Priority,
    RiskLevel,
    Session,
    Skill,
    SkillCapability,
    Task,
    TaskContext,
    TaskStatus,
    TaskStep,
    TaskType,
)


# ============== Task 模型测试 ==============

class TestTaskModel:
    def test_task_creation_defaults(self):
        task = Task(
            employee_id="agent-001",
            source_channel="feishu",
            task_type="inquiry",
            input_content="查询今日工单",
        )
        assert task.id.startswith("task-")
        assert task.status == TaskStatus.QUEUED
        assert task.priority == Priority.NORMAL
        assert len(task.trace_id) > 10  # UUID format

    def test_task_with_context(self):
        ctx = TaskContext(
            user_id="user-001",
            session_id="sess-001",
            tenant_id="tenant-001",
            employee_id="agent-001",
        )
        task = Task(
            employee_id="agent-001",
            source_channel="feishu",
            task_type="action",
            input_content="更新工单",
            context=ctx,
        )
        assert task.context is not None
        assert task.context.user_id == "user-001"
        assert task.context.session_id == "sess-001"

    def test_task_priority_values(self):
        assert Priority.LOW.value == "low"
        assert Priority.NORMAL.value == "normal"
        assert Priority.HIGH.value == "high"
        assert Priority.CRITICAL.value == "critical"

    def test_task_type_values(self):
        assert TaskType.INQUIRY.value == "inquiry"
        assert TaskType.ACTION.value == "action"
        assert TaskType.ANALYSIS.value == "analysis"

    def test_task_input_content_max_length(self):
        """input_content 超过 max_length=10000 应被拒绝"""
        long_content = "x" * 10001
        with pytest.raises(ValidationError):
            Task(
                employee_id="agent-001",
                source_channel="feishu",
                task_type="inquiry",
                input_content=long_content,
            )

    def test_task_input_content_at_limit(self):
        """input_content 正好 10000 应通过"""
        content = "x" * 10000
        task = Task(
            employee_id="agent-001",
            source_channel="feishu",
            task_type="inquiry",
            input_content=content,
        )
        assert len(task.input_content) == 10000


# ============== TaskStep 模型测试 ==============

class TestTaskStepModel:
    def test_task_step_creation(self):
        step = TaskStep(
            task_id="task-001",
            step_order=1,
            step_type="plan",
            action_name="generate_plan",
        )
        assert step.id.startswith("step-")
        assert step.task_id == "task-001"
        assert step.step_order == 1
        assert step.status == TaskStatus.QUEUED

    def test_task_step_serialization(self):
        step = TaskStep(
            task_id="task-001",
            step_order=1,
            step_type="call_skill",
            action_name="skill-search",
            input_snapshot={"query": "test"},
        )
        data = step.model_dump()
        assert data["task_id"] == "task-001"
        assert data["input_snapshot"]["query"] == "test"


# ============== Session 模型测试 ==============

class TestSessionModel:
    def test_session_creation(self):
        session = Session(
            employee_id="agent-001",
            user_id="user-001",
            tenant_id="tenant-001",
        )
        assert session.id.startswith("sess-")
        assert session.messages == []
        assert session.working_context == {}

    def test_session_with_messages(self):
        session = Session(
            employee_id="agent-001",
            user_id="user-001",
            tenant_id="tenant-001",
            messages=[
                Message(role="user", content="你好"),
                Message(role="assistant", content="你好，我是数字员工"),
            ],
        )
        assert len(session.messages) == 2
        assert session.messages[0].role == "user"


# ============== AgentFamily 模型测试 ==============

class TestAgentFamilyModel:
    def test_agent_family_minimal(self):
        family = AgentFamily(
            family_id="legal-specialist",
            family_name="法务专员",
            identity=AgentIdentity(
                role="公司法务专员",
                employee_id="DE-AI-001",
            ),
        )
        assert family.family_id == "legal-specialist"
        assert family.soul.communication_style == "专业、简洁"
        assert family.soul.risk_preference == "medium"

    def test_agent_family_full_config(self):
        family = AgentFamily(
            family_id="rd-engineer",
            family_name="软件开发工程师",
            soul=AgentSoul(
                mbti="INTP",
                communication_style="技术导向、简洁",
                risk_preference="low",
            ),
            identity=AgentIdentity(
                role="软件开发工程师",
                employee_id="DE-AI-002",
                organization="研发部",
                reporting_to="研发总监",
            ),
            agent=AgentConfig(
                responsibilities=["代码审查", "功能开发", "Bug修复"],
                service_for=["产品经理", "测试团队"],
                boundaries=["不直接部署到生产", "不修改他人代码未review"],
                kpi=[
                    {"metric": "代码审查时效", "target": "<24小时"},
                    {"metric": "Bug修复率", "target": ">95%"},
                ],
            ),
            policy=AgentPolicy(
                skills=["code-review", "git-management"],
                tools=["github-cli", "git", "docker"],
                approval_required=["production-deploy"],
            ),
        )
        assert family.soul.mbti == "INTP"
        assert "代码审查" in family.agent.responsibilities
        assert "production-deploy" in family.policy.approval_required


# ============== Skill 模型测试 ==============

class TestSkillModel:
    def test_skill_creation(self):
        skill = Skill(
            id="skill-search",
            name="通用检索",
            description="在企业知识库中检索相关信息",
            level="L1",
        )
        assert skill.id == "skill-search"
        assert skill.version == "1.0"
        assert skill.status == "draft"

    def test_skill_with_capabilities(self):
        cap = SkillCapability(
            name="search",
            description="执行语义检索",
            risk_level=RiskLevel.LOW,
        )
        skill = Skill(
            id="skill-enterprise-search",
            name="企业搜索",
            description="企业级全文+语义搜索",
            capabilities=[cap],
        )
        assert len(skill.capabilities) == 1
        assert skill.capabilities[0].risk_level == RiskLevel.LOW


# ============== Connector 模型测试 ==============

class TestConnectorModel:
    def test_connector_creation(self):
        connector = Connector(
            id="connector-ticket",
            name="工单系统",
            type="api",
        )
        assert connector.id == "connector-ticket"
        assert connector.timeout_seconds == 30

    def test_connector_with_capabilities(self):
        caps = [
            ConnectorCapability(
                name="search_tickets",
                description="搜索工单",
                risk_level=RiskLevel.LOW,
            ),
            ConnectorCapability(
                name="update_ticket",
                description="更新工单",
                risk_level=RiskLevel.MEDIUM,
                requires_approval=True,
            ),
        ]
        connector = Connector(
            id="connector-ticket",
            name="工单系统",
            type="api",
            capabilities=caps,
        )
        assert len(connector.capabilities) == 2
        assert connector.capabilities[1].requires_approval is True


# ============== Model 用量测试 ==============

class TestModelModels:
    def test_model_usage(self):
        usage = ModelUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        assert usage.total_tokens == 150

    def test_model_call_result(self):
        result = ModelCallResult(
            content="这是模型响应",
            model="gpt-4o-mini",
            usage=ModelUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            latency_ms=320,
        )
        assert result.content == "这是模型响应"
        assert result.model == "gpt-4o-mini"
        assert result.latency_ms == 320
        assert result.status == "success"
