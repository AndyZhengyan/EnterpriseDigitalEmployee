"""ModelHub FastAPI service — port 8002."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from apps.model_hub import __version__
from apps.model_hub.config import ModelHubSettings
from apps.model_hub.errors import ModelProviderError
from apps.model_hub.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ProviderInfo,
    ProviderListResponse,
    UsageResponse,
)
from apps.model_hub.providers.piagent import PiAgentProvider
from apps.model_hub.router import ModelRouter
from apps.model_hub.usage import UsageTracker
from common.tracing import get_logger

log = get_logger("model_hub")

settings = ModelHubSettings()
router_engine = ModelRouter()
usage_tracker = UsageTracker()

# Global provider instance
_pi_agent_provider: PiAgentProvider | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pi_agent_provider
    _pi_agent_provider = PiAgentProvider(
        base_url=f"http://127.0.0.1:{settings.sidecar_http_port}",
        timeout=settings.provider_timeout_seconds,
    )
    log.info("model_hub.started", port=settings.port, sidecar_port=settings.sidecar_http_port)
    yield
    if _pi_agent_provider:
        await _pi_agent_provider.close()
    log.info("model_hub.stopped")


app = FastAPI(title="ModelHub", version=__version__, lifespan=lifespan)


@app.get("/model-hub/health")
async def health() -> HealthResponse:
    providers: dict[str, bool] = {}
    if _pi_agent_provider:
        try:
            healthy = await _pi_agent_provider.health_check()
            providers["piagent"] = healthy
        except Exception as e:
            log.warning("health_check.failed", provider="piagent", error=str(e))
            providers["piagent"] = False

    return HealthResponse(
        status="healthy" if all(providers.values()) else "degraded",
        version=__version__,
        timestamp=datetime.now(timezone.utc),
        providers=providers,
        stats={},
    )


@app.get("/model/providers", response_model=ProviderListResponse)
async def list_providers() -> ProviderListResponse:
    if _pi_agent_provider is None:
        raise HTTPException(status_code=503, detail="Provider not initialised")
    models = _pi_agent_provider.list_models()
    provider_info = ProviderInfo(
        name="piagent",
        base_url=_pi_agent_provider.base_url,
        api_key_env=_pi_agent_provider.api_key_env,
        models=models,
        healthy=True,
    )
    return ProviderListResponse(
        providers=[provider_info],
        default_task_type=settings.default_task_type,
    )


@app.post("/model/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    task_type = req.task_type
    preferred = None

    if req.model:
        if "/" in req.model:
            provider_id, model_id = req.model.split("/", 1)
            preferred = (provider_id, model_id)
        else:
            preferred = ("minimax-cn", req.model)

    chain = router_engine.route(task_type, preferred=preferred)
    if not chain:
        raise HTTPException(
            status_code=404,
            detail=f"No available models for task_type={task_type.value}",
        )

    last_error: Exception | None = None
    for provider_name, model_id in chain:
        if _pi_agent_provider is None:
            raise HTTPException(status_code=503, detail="Provider not initialised")

        try:
            resp = await _pi_agent_provider.chat(
                messages=req.messages,
                model=model_id,
                session_id=req.session_id,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                thinking_level=req.thinking_level,
                tools=req.tools,
                timeout_seconds=req.timeout_seconds,
            )

            # Record usage
            usage = resp.usage
            usage_tracker.record(
                employee_id=req.employee_id or "unknown",
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                cost_usd=0.0,  # sidecar doesn't expose cost; track at billing layer
                provider=provider_name,
                model=model_id,
            )

            return resp

        except ModelProviderError as e:
            log.warning("chat.provider_failed", provider=provider_name, model=model_id, error=str(e))
            last_error = e
            continue

    # All providers in chain failed
    raise HTTPException(
        status_code=502,
        detail=f"All providers failed for {task_type.value}: {last_error}",
    )


@app.get("/model/usage/{employee_id}", response_model=UsageResponse)
async def get_usage(employee_id: str, days: int = 7) -> UsageResponse:
    records = usage_tracker.get_usage(employee_id, days=days)
    return UsageResponse(
        employee_id=employee_id,
        period="daily",
        usage=records,
        daily_limit=settings.daily_token_limit,
    )
