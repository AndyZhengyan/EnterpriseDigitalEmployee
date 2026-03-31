"""Runtime 记忆管理测试

测试依据：specs/runtime-spec.md
Session Context 记忆压缩
"""

import pytest

from apps.runtime.memory import MemoryManager, SessionContext


class TestSessionContext:
    """Session Context 测试"""

    def test_session_context_creation(self):
        """会话上下文创建"""
        ctx = SessionContext(
            session_id="sess-xxx",
            employee_id="agent-001",
            user_id="user-001",
        )
        assert ctx.session_id == "sess-xxx"
        assert ctx.employee_id == "agent-001"
        assert ctx.messages == []
        assert ctx.working_memory == {}

    def test_session_add_message(self):
        """添加消息"""
        ctx = SessionContext(
            session_id="sess-xxx",
            employee_id="agent-001",
            user_id="user-001",
        )
        ctx.add_message("user", "你好")
        ctx.add_message("assistant", "你好，我是数字员工")

        assert len(ctx.messages) == 2
        assert ctx.messages[0].role == "user"
        assert ctx.messages[1].role == "assistant"

    def test_session_working_memory(self):
        """工作记忆读写"""
        ctx = SessionContext(
            session_id="sess-xxx",
            employee_id="agent-001",
            user_id="user-001",
        )
        ctx.set_memory("current_task", "查询P1工单")
        ctx.set_memory("filter", {"priority": "P1"})

        assert ctx.get_memory("current_task") == "查询P1工单"
        assert ctx.get_memory("filter") == {"priority": "P1"}
        assert ctx.get_memory("nonexistent") is None

    def test_session_clear_memory(self):
        """清空工作记忆"""
        ctx = SessionContext(
            session_id="sess-xxx",
            employee_id="agent-001",
            user_id="user-001",
        )
        ctx.set_memory("key1", "value1")
        ctx.set_memory("key2", "value2")

        ctx.clear_memory()
        assert ctx.working_memory == {}


class TestMemoryManager:
    """记忆管理器测试"""

    def test_memory_manager_creation(self):
        """记忆管理器创建"""
        manager = MemoryManager(max_sessions=100)
        assert manager.max_sessions == 100
        assert len(manager.sessions) == 0

    @pytest.mark.asyncio
    async def test_get_or_create_session(self):
        """获取或创建会话"""
        manager = MemoryManager()

        ctx1 = await manager.get_or_create(
            session_id="sess-xxx",
            employee_id="agent-001",
            user_id="user-001",
        )

        # 同一个 session_id 返回同一实例
        ctx2 = await manager.get_or_create(
            session_id="sess-xxx",
            employee_id="agent-001",
            user_id="user-001",
        )

        assert ctx1 is ctx2
        assert len(manager.sessions) == 1

    def test_get_nonexistent_session(self):
        """获取不存在的会话"""
        manager = MemoryManager()
        ctx = manager.get("nonexistent-session")
        assert ctx is None

    @pytest.mark.asyncio
    async def test_session_limit(self):
        """会话数量限制"""
        manager = MemoryManager(max_sessions=2)

        # 创建两个会话
        await manager.get_or_create("sess-1", "agent-001", "user-001")
        await manager.get_or_create("sess-2", "agent-001", "user-001")

        assert len(manager.sessions) == 2

        # 创建第三个会话时，最旧的应该被清理
        await manager.get_or_create("sess-3", "agent-001", "user-001")

        assert len(manager.sessions) == 2
        # sess-1 应该是最新的（被访问过）
        assert "sess-3" in manager.sessions
        assert "sess-2" in manager.sessions

    @pytest.mark.asyncio
    async def test_delete_session(self):
        """删除会话"""
        manager = MemoryManager()
        await manager.get_or_create("sess-xxx", "agent-001", "user-001")

        assert len(manager.sessions) == 1

        deleted = await manager.delete("sess-xxx")
        assert deleted is True
        assert len(manager.sessions) == 0

        # 删除不存在的会话
        deleted = await manager.delete("nonexistent")
        assert deleted is False


class TestMemoryCompression:
    """记忆压缩测试"""

    @pytest.mark.asyncio
    async def test_compression_trigger(self):
        """压缩触发条件"""
        manager = MemoryManager()
        ctx = await manager.get_or_create("sess-xxx", "agent-001", "user-001")

        # 添加 51 条消息（超过默认阈值 50）
        for i in range(51):
            ctx.add_message("user", f"Message {i}")

        assert len(ctx.messages) == 51
        assert manager.should_compress(ctx) is True

    @pytest.mark.asyncio
    async def test_compression_preserves_recent(self):
        """压缩保留最近消息"""
        manager = MemoryManager()
        ctx = await manager.get_or_create("sess-xxx", "agent-001", "user-001")

        # 添加消息
        for i in range(60):
            ctx.add_message("user", f"Message {i}")

        # 压缩
        manager.compress(ctx)

        # 应该保留最近 20 条 + 1 条摘要 = <= 21
        assert len(ctx.messages) <= 21

    @pytest.mark.asyncio
    async def test_compression_preserves_system(self):
        """压缩保留系统消息"""
        manager = MemoryManager()
        ctx = await manager.get_or_create("sess-xxx", "agent-001", "user-001")

        ctx.add_message("system", "你是企业数字员工")
        for i in range(50):
            ctx.add_message("user", f"Message {i}")

        manager.compress(ctx)

        # 系统消息应该保留
        roles = [m.role for m in ctx.messages]
        assert "system" in roles

    @pytest.mark.asyncio
    async def test_auto_compression_on_access(self):
        """访问时自动压缩"""
        # 阈值 5 + max_recent 5：10 条消息时压缩到 5 条
        manager = MemoryManager(compression_threshold=5, max_recent_messages=5)
        ctx = await manager.get_or_create("sess-xxx", "agent-001", "user-001")

        # 添加超过阈值的消息
        for i in range(10):
            ctx.add_message("user", f"Message {i}")

        # 访问会话触发压缩
        ctx = await manager.get_or_create("sess-xxx", "agent-001", "user-001")

        # 消息数量应该减少到 max_recent_messages（不超过 5），
        # 加上 1 条摘要消息
        assert len(ctx.messages) <= 6
