# Journal 设计文档

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan.

**Goal:** 为审计/合规人员提供完整操作审计视图——左列表+右详情的分栏布局，完整字段（输入/输出摘要/token/版本），支持时间/角色/部门筛选 + 全文搜索。

**Architecture:** 复用现有 `task_executions` 表（ops.db），新增 Ops API endpoint 提供 Journal 查询接口，前端 Vue 页面消费该接口。

**Tech Stack:** FastAPI（apps/ops）、Vue 3、SQLite

---

## 目标用户

审计/合规人员：查看 Avatar 执行操作的完整审计链，可追溯、可筛选。

## 数据来源

复用现有 `task_executions` 表（`ops.db`），无需新建表。

Schema:
```sql
CREATE TABLE task_executions (
    id          TEXT PRIMARY KEY,
    run_id      TEXT,
    blueprint_id TEXT,
    alias       TEXT,
    role        TEXT,
    dept        TEXT,
    message     TEXT,       -- 原始输入
    status      TEXT,       -- ok / error
    token_input INTEGER,
    token_completion INTEGER,
    token_analysis INTEGER,
    duration_ms INTEGER,
    summary     TEXT,       -- 输出摘要
    created_at  TEXT,
);
```

## 页面布局

**左列表 + 右详情**（分栏固定布局）：

```
┌─────────────────────────────────────────┬──────────────────────────────┐
│  筛选栏（时间/角色/部门/状态）            │                              │
│  🔍 全文搜索                             │   选中记录详情                │
├────────────────────────────────────────┤                              │
│  列表卡片                                │   操作类型：合同审阅          │
│  · 09:12 码哥 · 代码审查  ✓ 2.3s       │   执行人：明律 / 法务专员     │
│  · 09:05 小白 · 周报生成  ✓ 5.1s       │   Blueprint：av-legal-001 v1.2│
│  · 08:58 明律 · 合同审阅  ✗ 3.8s       │   时间：2026-04-07 09:05     │
│                                         │                              │
│                                         │   原始输入：                  │
│                                         │   "帮我审查这份采购合同..."   │
│                                         │                              │
│                                         │   输出摘要：                  │
│                                         │   "发现3处风险条款..."        │
│                                         │                              │
│                                         │   Token：1234 in / 567 out   │
│                                         │   耗时：3.8s                 │
└────────────────────────────────────────┴──────────────────────────────┘
```

## 字段映射

| 审计字段        | 来源                          |
|----------------|-------------------------------|
| 时间戳          | `task_executions.created_at`   |
| 执行人别名       | `task_executions.alias`        |
| Avatar 角色     | `task_executions.role`         |
| 部门           | `task_executions.dept`         |
| 操作类型        | 从 `message` 推断或固定字段      |
| 执行结果        | `task_executions.status`       |
| 耗时           | `task_executions.duration_ms`  |
| 原始输入        | `task_executions.message`      |
| 输出摘要        | `task_executions.summary`       |
| Token 消耗      | `token_input + token_completion + token_analysis` |
| Blueprint 版本  | `task_executions.blueprint_id` |

## 筛选能力

- **时间范围**：今天 / 本周 / 本月 / 自定义日期范围
- **Avatar 角色**：下拉多选（软件工程师 / 法务专员 / 行政专员 / 合同专员...）
- **部门**：下拉多选
- **执行结果**：全部 / 成功 / 失败
- **全文搜索**：对 `message`（输入）和 `summary`（输出摘要）做 LIKE 搜索

## API 设计

```
GET /api/journal/executions
    Query params:
        - start_date: ISO date
        - end_date: ISO date
        - roles: comma-separated role names
        - depts: comma-separated department names
        - status: "ok" | "error" | ""
        - q: full-text search query
        - limit: int (default 50, max 200)
        - offset: int (for pagination)
    Response: { total: int, items: [ExecutionRecord] }

GET /api/journal/executions/:id
    Response: ExecutionRecord (with full detail)
```

## 实现范围（MVP）

1. `GET /api/journal/executions` — 查询接口，支持所有筛选参数
2. `GET /api/journal/executions/:id` — 单条详情
3. Vue 页面：左列表 + 右详情分栏布局
4. 筛选栏：时间范围 + 角色 + 部门 + 状态 + 搜索框
5. 无导出功能（后续迭代）
