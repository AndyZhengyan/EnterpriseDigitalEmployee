# Design: Blueprint → Openclaw Agent Auto-Sync

## Problem

前端创建的 Blueprint（角色）与 openclaw 的 agent 之间存在断层。当前所有角色都硬编码发到 `chat` agent，忽略了 blueprint_id。

## Principle

| Rule | Meaning |
|------|---------|
| e-agent-os is the source of truth | openclaw 目录是 e-agent-os 的输出，不是输入 |
| e-agent-os 管创建，openclaw 管执行 | 创建时自动生成，执行只传 `--agent {blueprint_id}` |
| 禁止手工介入 openclaw 微调 | 所有同步从 e-agent-os 单向驱动 |

## Architecture

### Trigger Map

| Event | Action |
|-------|--------|
| `POST /api/onboarding/deploy` | 创建新 agent 目录 + 注册 blueprint |
| `PUT /api/onboarding/blueprints/{id}/soul` | 更新 SOUL.md（覆盖写入） |
| `DELETE /api/onboarding/blueprints/{id}` | 删除对应 agent 目录 |

### Directory Structure

For each blueprint (e.g. `av-admin-001`):

```
~/.openclaw/agents/av-admin-001/agent/
├── SOUL.md              ← 根据 alias/role/department/soul 自动生成
├── auth-profiles.json   ← 从 ~/.openclaw/openclaw.json 继承模板
└── models.json          ← 从 ~/.openclaw/openclaw.json 继承模板
```

### SOUL.md Template

```markdown
# SOUL.md — Who I Am
> {alias}（{role}）。{department}。

## Core Identity [LOCKED]
**Name:** {alias}
**Role:** {role}
**Department:** {department}
**Blueprint ID:** {blueprint_id}

**Personality:**
{soul.description}

**Voice:**
- 专业、结构化
- {soul.communication_style}

## Working Style [AUTONOMOUS]
**Primary Responsibilities:**
- 以 {role} 身份处理本部门相关任务
- 遵循 {department} 的规范和流程

## Evolution Log
**{created_date}** — Created from blueprint {blueprint_id} via e-agent-os.

---
_此文件由 e-agent-os 自动创建，请勿手工修改。_
```

### Blueprint soul config

```json
{
  "soul": {
    "description": "专业细致的行政专员，擅长流程规范撰写",
    "communication_style": "清晰简洁，条理分明"
  }
}
```

### API Changes

1. **`POST /api/onboarding/deploy`** — 现有端点，添加 soul 参数支持，调用 OpenclawAgentRegistry
2. **`PUT /api/onboarding/blueprints/{bp_id}/soul`** — 新增端点，更新 agent SOUL.md
3. **`DELETE /api/onboarding/blueprints/{bp_id}`** — 现有端点，添加 agent 目录清理
4. **`_run_piagent()`** — 改用 `--agent {blueprint_id}` 替代硬编码 `chat`

### Module: `apps/ops/openclaw_registry.py`

```python
class OpenclawAgentRegistry:
    def register_agent(blueprint_id, alias, role, department, soul, models)
    def update_soul(blueprint_id, soul)
    def remove_agent(blueprint_id)
    def _generate_soul_md(blueprint_id, alias, role, department, soul)
    def _copy_openclaw_config(agent_dir)
```

### Data Flow

```
POST /api/onboarding/deploy
  → OpenclawAgentRegistry.register_agent()
    → mkdir ~/.openclaw/agents/{blueprint_id}/agent/
    → write SOUL.md
    → copy auth-profiles.json from openclaw.json
    → copy models.json from openclaw.json
  → INSERT into blueprints table

POST /api/ops/execute { blueprint_id: "av-admin-001", ... }
  → _run_piagent(message, agent_id=blueprint_id)
  → openclaw agent --agent av-admin-001 --message "..."
```

### Error Handling

| Failure | Response |
|---------|----------|
| `~/.openclaw/` not found | HTTP 500, "openclaw not configured" |
| Agent creation failed | Rollback DB insert, return 500 |
| openclaw CLI not found | HTTP 500 on execute (existing behavior) |
| Blueprint deleted but agent dir remains | Log warning, non-blocking |
