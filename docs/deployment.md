# Deployment Guide — e-Agent-OS

## Architecture Overview

```
                    ┌─────────────┐
                    │   Gateway   │  :8000
                    │  (FastAPI)  │
                    └──────┬──────┘
                           │ REST
         ┌─────────────────┼─────────────────┐
         │                 │                  │
    ┌────▼────┐       ┌────▼────┐         ┌────▼────┐
    │ Runtime │  :8001│ModelHub │  :8002  │Governance│ :8007
    └────┬────┘       └────┬────┘         └────┬────┘
         │                 │                  │
    ┌────▼────┐       ┌────▼────┐         ┌────▼────┐
    │SkillHub │ :8004 │Connector│  :8003  │ConfigCtr│ :8008
    └─────────┘       └─────────┘         └─────────┘
         │
    ┌────▼────┐
    │Knowledge│ :8005
    │  Hub    │
    └─────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Gateway | 8000 | Request routing and dispatch |
| Runtime | 8001 | Task execution engine |
| ModelHub | 8002 | Multi-model LLM routing |
| ConnectorHub | 8003 | External connector registry |
| SkillHub | 8004 | Skill registry and invocation |
| KnowledgeHub | 8005 | AgenticRAG with BM25 + vector store |
| OpsCenter | 8006 | Operational metrics and alerting |
| Governance | 8007 | RBAC/ABAC + approval workflows |
| ConfigCenter | 8008 | Centralized config management |

## Deployment Options

### Option 1: Docker Compose (Development / Staging)

```bash
cp .env.example .env
# Fill in API keys in .env

docker compose up          # foreground
docker compose up -d       # background
docker compose down
```

### Option 2: Kubernetes

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml   # Edit first!
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/services.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/ingress.yaml
```

### Option 3: Direct Python (Development Only)

```bash
pip install -e ".[dev]"

# Start each service in separate terminals:
python -m uvicorn apps.gateway.main:app --port 8000
python -m uvicorn apps.runtime.main:app --port 8001
python -m uvicorn apps.model_hub.main:app --port 8002
python -m uvicorn apps.governance.main:app --port 8007
python -m uvicorn apps.config_center.main:app --port 8008
```

## Environment Variables

### Required for Production

| Variable | Description | Example |
|----------|-------------|---------|
| `JWT_SECRET` | Secret for signing JWT tokens | `32+ random chars` |
| `SECRET_KEY` | Gateway dispatch secret | `32+ random chars` |
| `MINIMAX_API_KEY` | MiniMax API key | `Bearer eyJ...` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_HUB_ENABLED` | `true` | Enable ModelHub for LLM routing |
| `KNOWLEDGE_RAG_ENABLED` | `true` | Enable KnowledgeHub RAG |
| `LOG_LEVEL` | `INFO` | Logging level |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRY_SECONDS` | `3600` | JWT token TTL |

## Docker Image Build

```bash
# Build
docker build -t ghcr.io/andyzhengyan/enterprise-agent-employee:latest .

# Push (requires GHCR login)
docker push ghcr.io/andyzhengyan/enterprise-agent-employee:latest

# Or build with BuildKit for faster builds
DOCKER_BUILDKIT=1 docker build -t ghcr.io/andyzhengyan/enterprise-agent-employee:latest .
```

## Health Checks

All services expose a `/health` endpoint returning JSON:

```bash
curl http://localhost:8000/health
# {"status": "healthy", "version": "x.y.z", ...}
```

## Database / Storage

- **Redis** — session state, RAG index, ops metrics, usage tracking
- **In-memory** — RBAC roles, ABAC policies, approval workflows, config items
  - For production, migrate to persistent stores (PostgreSQL, etcd)

## Security Checklist

- [ ] Change `JWT_SECRET` and `SECRET_KEY` from defaults
- [ ] Set `MINIMAX_API_KEY` in production
- [ ] Enable Redis AUTH if exposed outside cluster
- [ ] Configure TLS termination at ingress
- [ ] Restrict ingress to internal network
- [ ] Enable audit logging for governance endpoints
