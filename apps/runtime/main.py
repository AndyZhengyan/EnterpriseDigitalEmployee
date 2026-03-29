"""Runtime 服务 FastAPI 入口

规格依据：specs/runtime-spec.md
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from apps.runtime.executor import RuntimeExecutor
from apps.runtime.memory import MemoryManager
from apps.runtime.models import (
    CancelResponse,
    ExecuteRequest,
    ExecuteResponse,
    HealthResponse,
    PlanRequest,
    PlanResponse,
    StatusResponse,
    StepInfo,
    TaskInput,
    TaskResult,
    TaskStatus,
)
from common.errors import ErrorCode
from common.models import BaseResponse, ErrorDetail
from common.tracing import get_logger, new_trace_id

# ============== 全局状态 ==============

memory_manager = MemoryManager()
executors: Dict[str, RuntimeExecutor] = {}
_task_store: Dict[str, Dict[str, Any]] = {}

RUNTIME_VERSION = "0.1.0"


def _get_or_create_executor(employee_id: str, task_id: str) -> RuntimeExecutor:
    # 注意：RuntimeExecutor 需要 employee_id 和 task_id
    if employee_id not in executors:
        executors[employee_id] = RuntimeExecutor(employee_id=employee_id, task_id=task_id)
    return executors[employee_id]


def _store_task(task_id: str, status: str, employee_id: str, **kwargs) -> None:
    _task_store[task_id] = {
        "task_id": task_id,
        "status": status,
        "employee_id": employee_id,
        "created_at": datetime.now(timezone.utc),
        "started_at": None,
        "completed_at": None,
        "steps": [],
        "current_step": 0,
        "total_steps": 0,
        "trace_id": new_trace_id(),
        **kwargs,
    }


def _update_task(task_id: str, **updates) -> None:
    if task_id in _task_store:
        _task_store[task_id].update(updates)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log = get_logger("runtime")
    log.info("runtime_startup", version=RUNTIME_VERSION)
    yield
    log.info("runtime_shutdown")
    executors.clear()
    _task_store.clear()


app = FastAPI(
    title="e-Agent-OS Runtime",
    description="运行时层 — Plan → Act → Reflect 执行循环",
    version=RUNTIME_VERSION,
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    trace_id = new_trace_id()
    log = get_logger("runtime")
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


@app.get("/runtime/health", response_model=HealthResponse, tags=["健康检查"])
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version=RUNTIME_VERSION,
        timestamp=datetime.now(timezone.utc),
        checks={"memory": "ok", "piagent": "ok"},
        stats={
            "active_tasks": sum(1 for t in _task_store.values() if t["status"] == "running"),
            "total_tasks": len(_task_store),
            "executor_count": len(executors),
        },
    )


@app.post("/runtime/execute", response_model=ExecuteResponse, tags=["执行"])
async def execute_task(req: ExecuteRequest, request: Request) -> ExecuteResponse:
    task_id = req.task_id or f"task-{uuid.uuid4().hex[:8]}"
    trace_id = new_trace_id()
    _store_task(task_id, "queued", req.employee_id, trace_id=trace_id)

    executor = _get_or_create_executor(req.employee_id, task_id=task_id)
    _update_task(task_id, status="running", started_at=datetime.now(timezone.utc))

    try:
        # 获取 query
        query = ""
        if isinstance(req.input, TaskInput):
            query = req.input.query
        elif isinstance(req.input, dict):
            query = req.input.get("query", "")
        else:
            query = str(req.input)

        # 提取技能列表
        available_skills = []
        if req.context and "skills" in req.context:
            available_skills = req.context["skills"]

        import asyncio
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FUTimeoutError

        loop = asyncio.get_event_loop()
        # 这里为了演示简单使用同步等待。实际生产中应该使用 background tasks
        with ThreadPoolExecutor(max_workers=1) as pool:
            try:
                # 调用 executor.run(task_content, available_skills)
                result = pool.submit(
                    lambda: loop.run_until_complete(
                        executor.run(query, available_skills)
                    )
                ).result(timeout=30)
            except FUTimeoutError:
                _update_task(task_id, status="failed")
                return ExecuteResponse(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    result=TaskResult(error="Task execution timed out"),
                    trace_id=trace_id,
                    duration_ms=30000,
                )

        _update_task(task_id, status="completed", completed_at=datetime.now(timezone.utc))

        # 兼容处理返回结果
        answer = ""
        sources = []
        actions = []
        if isinstance(result, dict):
            answer = result.get("answer", "")
            sources = result.get("sources", [])
            actions = result.get("actions", [])
        else:
            answer = str(result)

        return ExecuteResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result=TaskResult(
                answer=answer,
                sources=sources,
                actions=actions,
            ),
            trace_id=trace_id,
            duration_ms=0,
        )

    except Exception as e:
        _update_task(task_id, status="failed")
        return ExecuteResponse(
            task_id=task_id,
            status=TaskStatus.FAILED,
            result=TaskResult(error=str(e)),
            trace_id=trace_id,
        )


@app.post("/runtime/plan", response_model=PlanResponse, tags=["计划"])
async def generate_plan(req: PlanRequest, request: Request) -> PlanResponse:
    plan_id = f"plan-{uuid.uuid4().hex[:8]}"
    task_id = f"task-{uuid.uuid4().hex[:8]}"
    trace_id = new_trace_id()
    executor = _get_or_create_executor(req.employee_id, task_id=task_id)

    try:
        plan = await executor.generate_plan(
            task=req.task,
            available_skills=req.available_skills,
        )
        _store_task(task_id, "planned", req.employee_id, trace_id=trace_id, plan=plan)

        # 处理 steps
        steps_data = plan.get("steps", [])

        return PlanResponse(
            plan_id=plan_id,
            task_id=task_id,
            steps=steps_data,
            estimated_duration_ms=plan.get("estimated_duration_ms", 0),
            confidence=plan.get("confidence", 0.0),
            trace_id=trace_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/runtime/status/{task_id}", response_model=StatusResponse, tags=["状态"])
async def get_status(task_id: str, request: Request) -> StatusResponse:
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail="Task not found")
    task = _task_store[task_id]

    current_step = task.get("current_step", 0)
    total_steps = task.get("total_steps", 0)
    progress = 0.0
    if total_steps > 0:
        progress = float(current_step) / total_steps

    return StatusResponse(
        task_id=task_id,
        status=TaskStatus(task["status"]),
        current_step=current_step,
        total_steps=total_steps,
        progress=progress,
        started_at=task.get("started_at"),
        estimated_finish_at=None,
        steps=task.get("steps", []),
        trace_id=task.get("trace_id"),
    )


@app.post("/runtime/cancel/{task_id}", response_model=CancelResponse, tags=["取消"])
async def cancel_task(task_id: str, request: Request) -> CancelResponse:
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail="Task not found")
    task = _task_store[task_id]
    if task["status"] in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in status: {task['status']}")
    _update_task(task_id, status="cancelled", completed_at=datetime.now(timezone.utc))
    return CancelResponse(
        task_id=task_id,
        status=TaskStatus.CANCELLED,
        cancelled_at=datetime.now(timezone.utc),
        reason="user_requested",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.runtime.main:app", host="0.0.0.0", port=8001, reload=True)
