# 基于 OpenClaw PiAgent 的企业数字员工 MVP 范围（含管理 Portal）

## 1. MVP 目标（8 周内）
在不追求“大而全”的前提下，先做一个可演示、可试点、可扩展的最小闭环：
- 以 **PiAgent** 作为唯一 Agent 内核。
- 支持 **1 个岗位模板** + **3 个高频任务类型**。
- 打通 **1 个 IM Channel（飞书或企微）** + **1 个企业系统 Connector（如工单/CRM）**。
- 提供一个最小可用的 **企业数字员工管理 Portal**，可查看每个数字员工运行情况与任务情况。

---

## 2. MVP 边界（做什么 / 不做什么）

### 2.1 In Scope（必须做）
1. **Agent 执行闭环**：接收任务 -> 规划执行 -> 调工具 -> 返回结果 -> 状态记录。
2. **岗位化配置（最小版）**：仅支持 1 个岗位模板（Persona/Policy/Workflow）。
3. **基础治理**：
   - RBAC 最小权限
   - 高风险动作人工确认
   - 关键链路审计日志
4. **Portal 最小看板**：
   - 员工运行状态（在线/忙碌/异常）
   - 任务状态（待处理/进行中/已完成/失败）
   - 成功率、失败率、人工接管率、平均耗时

### 2.2 Out of Scope（本期不做）
- 多组织多租户复杂隔离（先单租户）
- 大规模 Skill 市场运营能力（先基础引入与白名单）
- 复杂多 Agent 协同编排（先单 Agent 为主）
- 高级财务/法务自动审批（默认人工复核）

---

## 3. MVP 功能清单

## 3.1 PiAgent Runtime MVP
- 任务执行流程（Plan/Act/Reflect）
- 基础失败重试（最多 2 次）
- 人工接管（失败或高风险动作）

**验收**
- 3 类任务可稳定跑通，自动完成率 >= 50%。

## 3.2 Channel + Connector MVP
- Channel：飞书或企微二选一
- Connector：工单系统或 CRM 二选一
- Skill：检索、总结、更新记录（3 个基础 Skill）

**验收**
- 用户可在 IM 发起任务并收到结构化结果卡片。

## 3.3 Portal MVP（重点）

### A. 员工列表页（Digital Employees）
- 字段：员工名、岗位、当前状态、24h 成功率、运行中任务数、最近异常时间
- 支持按岗位/状态筛选

### B. 员工详情页（Employee Detail）
- 基本信息：岗位模板版本、权限范围、启用 Skill 列表
- 运行指标：今日任务数、成功率、平均耗时、人工接管率
- 最近任务：最近 20 条任务（状态、耗时、失败原因）

### C. 任务中心（Tasks）
- 任务列表与状态筛选
- 任务详情（输入、执行步骤、工具调用记录、结果、错误原因）
- 人工操作（重试、转人工、关闭）

### D. 运行告警（Alerts）
- 告警类型：失败率突增、连接器异常、权限拒绝、模型超预算
- 告警处理状态：待处理/处理中/已恢复

**验收**
- 运营人员可在 Portal 中定位“哪个员工、哪类任务、为什么失败”。

---

## 4. MVP 最小数据模型

### 4.1 digital_employee
- id
- name
- role_template_id
- status (online/busy/error/offline)
- enabled_skills (json)
- created_at / updated_at

### 4.2 task
- id
- employee_id
- source_channel
- task_type
- priority
- status (queued/running/succeeded/failed/escalated)
- started_at / finished_at
- duration_ms
- fail_reason

### 4.3 task_step
- id
- task_id
- step_name
- tool_name
- status
- input_snapshot
- output_snapshot
- error_code
- timestamp

### 4.4 alert
- id
- alert_type
- severity
- related_employee_id
- related_task_id
- status
- created_at

### 4.5 audit_log
- id
- trace_id
- actor_type (user/agent/system)
- action
- target
- result
- timestamp

---

## 5. MVP API（建议最小集）

### 员工相关
- `GET /api/employees`
- `GET /api/employees/{id}`
- `GET /api/employees/{id}/metrics`

### 任务相关
- `POST /api/tasks`
- `GET /api/tasks`
- `GET /api/tasks/{id}`
- `POST /api/tasks/{id}/retry`
- `POST /api/tasks/{id}/escalate`

### 告警相关
- `GET /api/alerts`
- `POST /api/alerts/{id}/ack`

### 观测审计
- `GET /api/audit-logs?trace_id=`

---

## 6. 实施步骤（8 周）

### Week 1-2：内核与主流程
- PiAgent Runtime 部署
- IM Channel 打通
- 任务主流程打通

**里程碑**：可从 IM 创建任务并返回结果。

### Week 3-4：工具接入与任务闭环
- 接入 1 个企业系统 Connector
- 上线 3 个基础 Skill
- 接入任务状态持久化（task/task_step）

**里程碑**：3 类任务闭环跑通。

### Week 5-6：Portal 最小功能
- 员工列表页 + 详情页
- 任务中心页（列表 + 详情 + 重试）
- 基础指标 API 与图表

**里程碑**：可看见每个员工运行与任务情况。

### Week 7：治理与告警
- RBAC 最小权限
- 审计日志接入
- 告警规则与 Alerts 页面

**里程碑**：异常可发现、可追溯。

### Week 8：联调与试点上线
- 压测与稳定性优化
- 试点部门上线
- 周度复盘机制建立

**里程碑**：满足试点可用标准。

---

## 7. MVP 成功标准（试点）
- 自动完成率 >= 50%
- 人工接管率 <= 40%
- P1 任务平均处理时长下降 >= 30%
- Portal 可在 10 分钟内定位异常任务根因
- 试点用户满意度 >= 4.2 / 5

---

## 8. 团队分工建议（最小配置）
- 后端工程师 x2：PiAgent 接入、任务服务、API
- 前端工程师 x1：Portal（员工页/任务页/告警页）
- 平台/DevOps x1：部署、监控、日志
- 产品经理 x1：流程定义、验收标准
- 业务运营 x1：岗位模板与试点反馈

---

## 9. 下一步（MVP 之后）
- 岗位从 1 扩展到 3（销售运营、客服、HR 助理）
- Connector 从 1 扩展到 3
- Skill 管理从“白名单”升级为“审批 + 灰度 + 回滚”
- 引入多模型路由和成本优化策略
