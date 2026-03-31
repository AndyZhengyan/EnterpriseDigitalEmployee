"""Runtime 记忆管理

规格依据：specs/runtime-spec.md
Session Context 与记忆压缩
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class Message:
    """会话消息"""

    def __init__(self, role: str, content: str):
        self.role = role  # user / assistant / system
        self.content = content
        self.timestamp = datetime.now(timezone.utc)


class SessionContext:
    """
    单个会话的上下文。

    包含对话历史、工作记忆、产物等。
    """

    def __init__(
        self,
        session_id: str,
        employee_id: str,
        user_id: str,
    ):
        self.session_id = session_id
        self.employee_id = employee_id
        self.user_id = user_id

        # 对话历史
        self.messages: List[Message] = []

        # 当前任务
        self.current_task_id: Optional[str] = None
        self.task_history: List[Dict[str, Any]] = []

        # 工作记忆
        self.working_memory: Dict[str, Any] = {}

        # 产物
        self.artifacts: List[Dict[str, Any]] = []

        # 元信息
        self.created_at = datetime.now(timezone.utc)
        self.last_active_at = datetime.now(timezone.utc)
        self.message_count = 0

    def add_message(self, role: str, content: str) -> None:
        """添加消息"""
        self.messages.append(Message(role, content))
        self.message_count += 1
        self.last_active_at = datetime.now(timezone.utc)

    def set_memory(self, key: str, value: Any) -> None:
        """设置工作记忆"""
        self.working_memory[key] = value
        self.last_active_at = datetime.now(timezone.utc)

    def get_memory(self, key: str, default: Any = None) -> Any:
        """获取工作记忆"""
        return self.working_memory.get(key, default)

    def clear_memory(self) -> None:
        """清空工作记忆"""
        self.working_memory = {}

    def add_artifact(self, artifact: Dict[str, Any]) -> None:
        """添加产物"""
        self.artifacts.append(artifact)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "employee_id": self.employee_id,
            "user_id": self.user_id,
            "message_count": self.message_count,
            "last_active_at": self.last_active_at.isoformat(),
        }


class MemoryManager:
    """
    记忆管理器。

    管理多个 Session Context，支持会话数量限制和记忆压缩。
    """

    def __init__(
        self,
        max_sessions: int = 100,
        compression_threshold: int = 50,
        max_recent_messages: int = 20,
    ):
        self.max_sessions = max_sessions
        self.compression_threshold = compression_threshold
        self.max_recent_messages = max_recent_messages
        self.sessions: OrderedDict[str, SessionContext] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        session_id: str,
        employee_id: str,
        user_id: str,
    ) -> SessionContext:
        """
        获取或创建会话。

        如果会话存在但需要压缩，会自动压缩。
        使用 asyncio.Lock 保护并发访问。
        """
        async with self._lock:
            if session_id in self.sessions:
                ctx = self.sessions[session_id]
                # 移动到末尾（最新）
                self.sessions.move_to_end(session_id)
                # 检查是否需要压缩
                if self.should_compress(ctx):
                    self.compress(ctx)
                return ctx

            # 检查会话数量限制
            if len(self.sessions) >= self.max_sessions:
                # 删除最旧的会话
                oldest_key = next(iter(self.sessions))
                del self.sessions[oldest_key]

            # 创建新会话
            ctx = SessionContext(
                session_id=session_id,
                employee_id=employee_id,
                user_id=user_id,
            )
            self.sessions[session_id] = ctx
            return ctx

    def get(self, session_id: str) -> Optional[SessionContext]:
        """获取会话，不存在则返回 None（无需锁，直接读取）"""
        return self.sessions.get(session_id)

    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        async with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False

    def should_compress(self, ctx: SessionContext) -> bool:
        """检查是否需要压缩"""
        return len(ctx.messages) > self.compression_threshold

    def compress(self, ctx: SessionContext) -> None:
        """
        压缩记忆。

        策略：
        1. 保留系统消息
        2. 保留最近 N 条消息
        3. 中间消息摘要化
        """
        if len(ctx.messages) <= self.max_recent_messages:
            return

        system_messages = [m for m in ctx.messages if m.role == "system"]
        other_messages = [m for m in ctx.messages if m.role != "system"]

        # 保留最近的消息
        recent = other_messages[-self.max_recent_messages :]
        older = other_messages[: -self.max_recent_messages]

        # 摘要旧消息
        summary_content = self._summarize_messages(older)

        # 构建新消息列表
        compressed = system_messages.copy()
        if summary_content:
            compressed.append(Message("system", f"<摘要: {summary_content}>"))
        compressed.extend(recent)

        ctx.messages = compressed

    def _summarize_messages(self, messages: List[Message]) -> str:
        """摘要消息列表"""
        if not messages:
            return ""

        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]

        summary_parts = []
        if user_messages:
            summary_parts.append(f"讨论了{len(user_messages)}个用户消息")
        if assistant_messages:
            summary_parts.append(f"助手回复了{len(assistant_messages)}次")

        return "，".join(summary_parts) if summary_parts else ""

    async def cleanup_expired(self, ttl_hours: int = 24) -> int:
        """
        清理过期的会话。

        返回清理的会话数量。
        """
        async with self._lock:
            now = datetime.now(timezone.utc)
            expired_keys = []

            for session_id, ctx in self.sessions.items():
                age_hours = (now - ctx.last_active_at).total_seconds() / 3600
                if age_hours > ttl_hours:
                    expired_keys.append(session_id)

            for key in expired_keys:
                del self.sessions[key]

            return len(expired_keys)
