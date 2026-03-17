# MVP Core

该目录包含最小可运行 MVP：
- 外围企业编排层（Orchestrator）
- 基础控制台（数字员工、任务、告警）
- 高速事故处理场景 Demo（地图态势 + 联动日志）

## 架构原则（这版重点）
- **优先保持 PiAgent 内核不动**：通过外部桥接接口调用 PiAgent 产出计划。
- 本服务只负责企业外围能力：任务接入、审计、告警、风险提示、命令下发。
- 当 PiAgent bridge 不可用时，按顺序降级到 OpenAI-compatible，再降级到内置 SOP。

## 运行
```bash
cd apps/mvp-core
python3 server.py
```

访问：
- 首页: http://localhost:8100/
- 控制台: http://localhost:8100/console
- 场景: http://localhost:8100/scenario

## Planner 后端优先级
1. `PIAGENT_PLANNER_URL`（推荐，保留 PiAgent 原生运行时）
2. `OPENAI_BASE_URL + OPENAI_API_KEY`（兼容路径）
3. 内置 fallback SOP（兜底）

## 环境变量
### PiAgent Bridge（推荐）
- `PIAGENT_PLANNER_URL`：PiAgent 规划桥接服务 URL（POST）
- `PIAGENT_API_KEY`：可选鉴权 Bearer Token

### OpenAI Compatible（可选）
- `OPENAI_API_KEY`：模型密钥
- `OPENAI_BASE_URL`：默认 `https://api.openai.com/v1`
- `OPENAI_MODEL`：默认 `gpt-4o-mini`

### 通用
- `MODEL_TIMEOUT_SEC`：单次规划请求超时（默认 35）
- `MODEL_MAX_RETRY`：每个后端重试次数（默认 2）

示例（桥接 PiAgent）：
```bash
PIAGENT_PLANNER_URL=http://localhost:18789/planner \
PIAGENT_API_KEY=xxx \
python3 server.py
```

## API（核心）
- `GET /api/health`
- `GET /api/employees`
- `GET /api/employees/{id}`
- `GET /api/employees/{id}/metrics`
- `GET /api/tasks`
- `GET /api/tasks/{id}`
- `POST /api/tasks`
- `POST /api/tasks/{id}/retry`
- `POST /api/tasks/{id}/escalate`
- `GET /api/scenario`
- `POST /api/scenario/reset`
- `GET /api/alerts`
- `POST /api/alerts/{id}/ack`
- `GET /api/commands`
- `GET /api/audit-logs`（支持 `trace_id` 过滤）
- `GET /api/agent-runtime`
