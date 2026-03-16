# MVP Core

该目录包含本次最小可运行 MVP：
- 核心 Agent（任务执行状态机，模拟 PiAgent Plan/Act/Review/Complete）
- 核心控制台（数字员工、任务、告警）
- 高速事故处理场景 Demo（地图态势 + 联动日志）

## 运行
```bash
cd apps/mvp-core
python3 server.py
```

访问：
- 首页: http://localhost:8100/
- 控制台: http://localhost:8100/console
- 场景: http://localhost:8100/scenario

## API（核心）
- `GET /api/health`
- `GET /api/employees`
- `GET /api/tasks`
- `GET /api/tasks/{id}`
- `POST /api/tasks`
- `GET /api/scenario`
- `POST /api/scenario/reset`
- `GET /api/alerts`
- `GET /api/commands`
- `GET /api/audit-logs`
- `GET /api/agent-runtime`
