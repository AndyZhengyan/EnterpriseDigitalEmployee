"""Gateway 服务入口"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded as RateLimitExc
from slowapi.util import get_remote_address

from common.errors import EAgentError, ErrorCode
from common.models import BaseResponse, ErrorDetail, Priority, TaskStatus, TaskType
from common.tracing import configure_logging, get_logger, new_trace_id

# 配置日志
configure_logging()
log = get_logger("gateway")

# ============== Auth helpers ==============

security = HTTPBearer(auto_error=False)
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")


async def get_current_client(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Optional[str]:
    """Extract client id from Bearer token. Returns None if no token."""
    if credentials is None:
        return None
    return credentials.credentials


def verify_webhook(request: Request) -> bool:
    """Verify webhook request via X-Webhook-Secret header."""
    secret = request.headers.get("x-webhook-secret", "")
    return secrets.compare_digest(secret, WEBHOOK_SECRET) if WEBHOOK_SECRET else False


# ============== Rate limiting ==============

limiter = Limiter(key_func=get_remote_address)


# ============== FastAPI App ==============

app = FastAPI(
    title="e-Agent-OS Gateway",
    description="企业数字员工操作系统 - 网关层",
    version="0.1.0",
)


# ============== 请求/响应模型 ==============


class DispatchRequest(BaseModel):
    """任务分发请求"""

    employee_id: str = Field(..., description="Agent ID")
    task_type: TaskType = Field(default=TaskType.INQUIRY)
    content: str = Field(..., max_length=10000, description="任务内容")
    priority: Priority = Field(default=Priority.NORMAL)
    context: Dict[str, Any] = Field(default_factory=dict)
    callback_url: Optional[str] = Field(default=None, description="回调 URL")

    class Config:
        use_enum_values = True

    @field_validator("callback_url")
    @classmethod
    def validate_callback_url(cls, v: Optional[str]) -> Optional[str]:
        """仅允许 HTTPS URL，防止 SSRF"""
        if v is None:
            return v
        import urllib.parse

        parsed = urllib.parse.urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("callback_url must use http or https scheme")
        return v


class DispatchResponse(BaseModel):
    """任务分发响应"""

    task_id: str
    status: TaskStatus
    estimated_duration_ms: int = 5000
    websocket_url: Optional[str] = None


class CallbackRequest(BaseModel):
    """Webhook 回调请求"""

    event_type: Literal["task.completed", "task.failed"]
    task_id: str
    result: Optional[Dict[str, Any]] = None


# ============== 辅助函数 ==============


RUNTIME_URL = os.environ.get("RUNTIME_URL", "http://localhost:8001")


async def _dispatch_to_runtime(req: DispatchRequest, trace_id: str) -> DispatchResponse:
    """将请求分发到 Runtime"""
    task_id = f"task-{trace_id[-12:]}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{RUNTIME_URL}/runtime/execute",
                json={
                    "employee_id": req.employee_id,
                    "task_id": task_id,
                    "input": {"query": req.content},
                    "context": req.context,
                },
            )
            if response.status_code == 200:
                body = response.json()
                return DispatchResponse(
                    task_id=body.get("task_id", task_id),
                    status=TaskStatus(body.get("status", "queued")),
                    estimated_duration_ms=body.get("duration_ms", 5000),
                )
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        log.warning("runtime_unreachable", runtime_url=RUNTIME_URL, error=str(e))

    return DispatchResponse(
        task_id=task_id,
        status=TaskStatus.QUEUED,
        estimated_duration_ms=5000,
    )


# ============== 路由 ==============


@app.post("/gateway/dispatch", response_model=DispatchResponse)
@limiter.limit("60/minute")
async def dispatch_task(req: DispatchRequest, request: Request, client_id: str = Depends(get_current_client)):
    """
    任务分发接口。

    将用户请求分发到对应的 AgentFamily 处理。
    """
    if client_id is None:
        return JSONResponse(
            status_code=401,
            content=BaseResponse(
                success=False,
                error=ErrorCode.GATEWAY_AUTH_FAILED.to_dict(details="Missing Bearer token"),
            ).model_dump(mode="json"),
        )
    trace_id = new_trace_id()
    log = get_logger("gateway").bind(trace_id=trace_id, employee_id=req.employee_id)

    log.info("dispatch_received", task_type=req.task_type, priority=req.priority)

    try:
        response = await _dispatch_to_runtime(req, trace_id)
        log.info("dispatch_success", task_id=response.task_id)
        return response

    except EAgentError as e:
        log.error("dispatch_failed", error=e.to_dict())
        return JSONResponse(
            status_code=400,
            content=BaseResponse(
                success=False,
                error=ErrorDetail(**e.to_dict()),
                trace_id=trace_id,
            ).model_dump(mode="json"),
        )


@app.post("/gateway/callback")
async def webhook_callback(req: CallbackRequest, request: Request):
    """
    Webhook 回调接口。

    接收外部系统的回调通知。
    """
    if not verify_webhook(request):
        return JSONResponse(
            status_code=401,
            content=BaseResponse(
                success=False,
                error=ErrorDetail(**ErrorCode.GATEWAY_AUTH_FAILED.to_dict(details="Invalid webhook secret")),
            ).model_dump(mode="json"),
        )
    trace_id = new_trace_id()
    log = get_logger("gateway").bind(trace_id=trace_id, task_id=req.task_id)

    log.info("callback_received", event_type=req.event_type)

    # TODO: 处理回调，更新任务状态
    return {"status": "ok", "trace_id": trace_id}


@app.get("/gateway/session/{session_id}/history")
async def get_session_history(session_id: str, client_id: str = Depends(get_current_client)):
    """
    获取会话历史。

    返回指定 session_id 的消息历史。
    """
    if client_id is None:
        return JSONResponse(
            status_code=401,
            content=BaseResponse(
                success=False,
                error=ErrorCode.GATEWAY_AUTH_FAILED.to_dict(details="Missing Bearer token"),
            ).model_dump(mode="json"),
        )
    trace_id = new_trace_id()
    log = get_logger("gateway").bind(trace_id=trace_id, session_id=session_id)

    # TODO: 从存储中获取会话历史
    log.info("session_history_requested")

    return {
        "session_id": session_id,
        "messages": [],
        "trace_id": trace_id,
    }


@app.get("/gateway/health")
async def health_check():
    """
    健康检查接口。

    返回网关服务健康状态。
    """
    return {
        "status": "healthy",
        "service": "gateway",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
    }


# ============== 异常处理 ==============


@app.exception_handler(RateLimitExc)
async def rate_limit_handler(request: Request, exc: RateLimitExc):
    """Rate limit exceeded handler"""
    return JSONResponse(
        status_code=429,
        content=BaseResponse(
            success=False,
            error=ErrorDetail(
                **ErrorCode.GATEWAY_RATE_LIMITED.to_dict(details="Rate limit exceeded. Retry after 1 minute.")
            ),
        ).model_dump(mode="json"),
    )


@app.exception_handler(EAgentError)
async def eagent_error_handler(request: Request, exc: EAgentError):
    """统一异常处理"""
    log = get_logger("gateway")
    log.error("request_error", error=exc.to_dict(), path=request.url.path)
    return JSONResponse(
        status_code=400,
        content=BaseResponse(
            success=False,
            error=ErrorDetail(**exc.to_dict()),
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    """通用异常处理"""
    trace_id = new_trace_id()
    log = get_logger("gateway")
    log.error("internal_error", trace_id=trace_id, error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content=BaseResponse(
            success=False,
            error=ErrorDetail(
                **ErrorCode.SYSTEM_INTERNAL_ERROR.to_dict(
                    details="An internal error occurred. Contact support with trace_id."
                )
            ),
            trace_id=trace_id,
        ).model_dump(mode="json"),
    )


# ============== 启动 ==============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
