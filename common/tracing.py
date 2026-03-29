"""e-Agent-OS 结构化日志与链路追踪

设计原则（来自 Harness Engineering）：
- 所有关键操作有结构化日志
- 每个请求有唯一 trace_id
- 日志包含：level, timestamp, trace_id, module, message
"""

from __future__ import annotations

import contextvars
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Optional

import structlog

# ============== Trace Context ==============

# 使用 contextvars 实现线程安全的 trace context
_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_task_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("task_id", default="")
_tenant_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("tenant_id", default="")
_module_var: contextvars.ContextVar[str] = contextvars.ContextVar("module", default="")


def get_trace_id() -> str:
    """获取当前 trace_id"""
    return _trace_id_var.get() or ""


def get_task_id() -> str:
    """获取当前 task_id"""
    return _task_id_var.get() or ""


def get_tenant_id() -> str:
    """获取当前 tenant_id"""
    return _tenant_id_var.get() or ""


def new_trace_id() -> str:
    """生成新的 trace_id"""
    return f"trace-{uuid.uuid4().hex[:16]}"


@contextmanager
def trace_context(
    trace_id: Optional[str] = None,
    task_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    module: Optional[str] = None,
):
    """设置 trace context"""
    trace_id = trace_id or new_trace_id()
    token_trace = _trace_id_var.set(trace_id)
    token_task = _task_id_var.set(task_id or "")
    token_tenant = _tenant_id_var.set(tenant_id or "")
    token_module = _module_var.set(module or "")

    try:
        yield trace_id
    finally:
        _trace_id_var.reset(token_trace)
        _task_id_var.reset(token_task)
        _tenant_id_var.reset(token_tenant)
        _module_var.reset(token_module)


# ============== Structlog 配置 ==============


def configure_logging(log_level: str = "INFO") -> None:
    """配置 structlog"""

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ============== 日志器工厂 ==============


def get_logger(name: Optional[str] = None, **kwargs: Any):
    """
    获取日志器。

    用法：
        log = get_logger("gateway")
        log.info("请求处理", employee_id="agent-001", duration_ms=100)

    输出格式：
        level=INFO ts=2026-03-28T10:00:00.000Z trace_id=trace-xxx module=gateway event=请求处理
    """
    module = _module_var.get() or (name if name else "app")
    logger = structlog.get_logger(module)

    # 注入 trace context 到日志
    ctx: Dict[str, Any] = {}
    trace_id = get_trace_id()
    if trace_id:
        ctx["trace_id"] = trace_id
    task_id = get_task_id()
    if task_id:
        ctx["task_id"] = task_id
    tenant_id = get_tenant_id()
    if tenant_id:
        ctx["tenant_id"] = tenant_id

    if ctx:
        logger = logger.bind(**ctx)

    if kwargs:
        logger = logger.bind(**kwargs)

    return logger


# ============== 便捷日志装饰器 ==============


def log_entry_exit(logger: Any = None):
    """记录函数入口出口的装饰器"""

    def decorator(func):
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            log = logger or get_logger(func.__module__)
            log.debug("entry", function=func.__name__, args=str(args)[:200])
            try:
                result = func(*args, **kwargs)
                log.debug("exit", function=func.__name__)
                return result
            except Exception as e:
                log.error("exception", function=func.__name__, error=str(e))
                raise

        return wrapper

    return decorator
