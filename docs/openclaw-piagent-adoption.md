# 采用 OpenClaw PiAgent 作为企业数字员工内核的落地方案

## 1. 目标与原则
- **内核统一**：以 OpenClaw PiAgent 作为唯一 Agent Runtime，避免自研重复轮子。
- **生态兼容**：原生兼容 OpenClaw `Channel`、`ClawHub Skill` 市场。
- **企业可控**：在不破坏 OpenClaw 生态能力前提下，补齐企业级的权限、审计、合规与多租户治理。

---

## 2. 与现有架构图的映射关系

### 2.1 Brain（Agentic 大脑）
- 直接替换为 **PiAgent Runtime**（负责计划、执行、反思、工具调用编排）。
- 在 PiAgent 外层增加企业编排器：
  - 任务路由（按岗位/优先级/成本）
  - 风险策略（高风险动作二次确认）
  - 人工接管（HITL）

### 2.2 Tools & Auth（工具与权限）
- 工具接入层优先遵循 OpenClaw Channel 协议。
- 企业系统（OA/CRM/ERP）统一包装成 Channel Connector。
- Skill 调用权限由企业 IAM 统一发令牌，并映射到 PiAgent 可见权限域。

### 2.3 Work Memory（工作记忆）
- 保留 PiAgent 会话上下文机制。
- 叠加企业任务线程模型（Task/Step/Action/Event），支持跨会话续跑与审计回放。

### 2.4 Long-term Memory（长期记忆）
- 使用企业自有 Knowledge/Memory 服务（向量库 + 结构化事实库）。
- 通过 PiAgent Memory Adapter 暴露检索与写入能力。
- 强制“写入审核”与“引用溯源”，降低幻觉和脏数据污染。

### 2.5 Job Resp. & Role（岗位职责）
- 岗位配置下沉为 PiAgent 的 Persona + Policy + Workflow 模板。
- 一岗一模板，模板版本化，支持灰度发布。

### 2.6 Model Gateway
- 作为 PiAgent 上游模型抽象层：统一模型路由、成本治理、脱敏审查。

---

## 3. 分层技术架构（推荐）

1. **Experience Layer**：飞书/企微/Web 门户（任务下发、状态回传、验收反馈）
2. **Orchestration Layer**：Enterprise Orchestrator（岗位路由、SLA、人工接管）
3. **Agent Runtime Layer**：OpenClaw PiAgent（核心决策与执行）
4. **Ecosystem Layer**：Channel Connectors + ClawHub Skills
5. **Governance Layer**：IAM、审计、合规、成本看板
6. **Data/Memory Layer**：企业知识库、事实库、会话与任务事件存储

---

## 4. 生态兼容规范（Channel + ClawHub）

### 4.1 Channel 兼容要点
- 协议：严格遵循 OpenClaw Channel 消息规范。
- 鉴权：企业统一签发短期 Token，支持最小权限。
- 幂等：每个 Channel Action 要有 request_id，支持重放保护。
- 可观测：统一输出 action_trace_id，串联审计链路。

### 4.2 ClawHub Skill 兼容要点
- Skill 包管理：支持“官方市场 + 企业私有镜像仓”。
- Skill 安装策略：
  - 白名单/黑名单
  - 版本冻结与回滚
  - 依赖扫描（许可证与安全漏洞）
- Skill 运行策略：
  - 沙箱隔离
  - 出网/文件系统权限控制
  - 资源配额（CPU/内存/超时）

---

## 5. 企业级增强（在 PiAgent 之上）

1. **权限治理**：人-岗-技能-工具四级权限矩阵。
2. **审计合规**：Prompt、上下文、工具调用、结果全量留痕。
3. **质量护栏**：
   - 关键任务必须“证据引用 + 自检”
   - 高风险域（财务/法务）默认人工复核
4. **成本控制**：模型路由、缓存复用、配额与预算报警。
5. **可靠性**：重试、熔断、降级（失败时回退到规则流或人工）。

---

## 6. 实施路线图

### 阶段 1（2~4 周）：内核接入验证
- 跑通 PiAgent Runtime。
- 打通 1 个 Channel（如飞书）+ 1 个企业系统 Connector。
- 接入 3~5 个基础 Skills（检索、总结、工单操作）。

**验收**：可完成端到端单任务闭环（接收 -> 执行 -> 汇报）。

### 阶段 2（4~8 周）：企业治理补齐
- 上线 IAM 映射、审计日志、模型网关策略。
- 上线岗位模板化与版本灰度。
- 上线私有 Skill 仓与审批流。

**验收**：满足企业试点部门安全要求。

### 阶段 3（8~12 周）：规模化复制
- 扩展多岗位（销售运营/客服/HR 助理）。
- 建立 KPI 看板（完成率、一次通过率、人工接管率、成本）。
- 建立持续运营机制（Prompt/Skill/流程迭代闭环）。

---

## 7. MVP 最小可交付清单
- PiAgent Runtime 服务
- Channel Gateway（飞书/企微至少一个）
- Skill Manager（接 ClawHub + 私有仓）
- IAM Adapter（SSO + RBAC）
- Audit Service（全链路日志）
- Memory Adapter（知识检索 + 会话存储）
- Ops Console（岗位配置、策略开关、运行看板）

---

## 8. 风险与应对
- **生态版本变动风险**：锁定 PiAgent/Skill API 版本，建立兼容测试。
- **Skill 供应链风险**：引入签名校验、漏洞扫描、准入审批。
- **数据泄漏风险**：最小权限 + 脱敏 + 审计追踪。
- **幻觉风险**：强制检索增强与引用校验。

---

## 9. 结论
建议采用“**PiAgent 原生内核 + 企业治理外壳**”模式：
- 充分复用 OpenClaw 生态速度（Channel + ClawHub）；
- 同时满足企业上线的安全、合规与可运营要求；
- 能够从单岗位 MVP 快速扩展到组织级数字员工矩阵。

---

## 10. 模块细化（可直接分工）

### 10.1 Experience Layer（飞书/企微/Web）
**职责**
- 接收用户任务、展示进度与结果、收集反馈与验收。

**关键接口**
- `POST /tasks`：创建任务。
- `GET /tasks/{id}`：任务状态查询。
- `POST /tasks/{id}/approve`：人工验收或驳回。

**数据对象**
- TaskCard：标题、责任岗位、状态、ETA、风险等级。
- ResultCard：结果摘要、证据链接、下一步建议。

**验收标准**
- 用户可在 IM 内完整完成“提需求 -> 看进度 -> 验收”。

### 10.2 Enterprise Orchestrator（企业编排层）
**职责**
- 任务拆分、路由、重试、SLA 管理、人工接管。

**关键接口**
- `dispatch(role_id, task_id)`
- `escalate(task_id, reason)`
- `retry(step_id, policy)`

**规则引擎**
- 优先级规则：P0/P1/P2。
- 风险规则：高风险动作强制人工确认。
- 超时规则：超时自动升级。

**验收标准**
- 失败任务可自动重试并最终归因（模型/工具/权限/数据）。

### 10.3 PiAgent Runtime（Agent 内核）
**职责**
- 计划（Plan）/执行（Act）/反思（Reflect）闭环。

**运行模式**
- 标准模式：单 Agent 直连工具。
- 复杂模式：Planner + Executor + Reviewer 多 Agent 协作。

**策略要求**
- 关键步骤必须输出“计划摘要 + 执行证据 + 结论”。

**验收标准**
- 单任务成功率 >= 70%（试点阶段）。

### 10.4 Channel Gateway（生态连接层）
**职责**
- 统一接入企业系统与第三方应用，标准化为 Channel Action。

**连接器模板**
- Auth Adapter（OAuth/AKSK/Session）
- API Mapper（企业 API <-> Channel Schema）
- Error Mapper（业务错误码标准化）

**验收标准**
- 新增一个连接器可在 2~3 天内完成上线。

### 10.5 Skill Manager（ClawHub + 私有技能中心）
**职责**
- Skill 生命周期管理：引入、审批、安装、冻结、下线。

**关键能力**
- Skill 准入扫描（漏洞、许可证、签名）。
- Skill 版本策略（固定版本 + 灰度发布）。
- Skill 可观测（调用次数、失败率、平均耗时）。

**验收标准**
- 任一 Skill 的来源、版本、审批人可追溯。

### 10.6 IAM & AuthZ（权限与身份）
**职责**
- 将企业用户身份映射为 Agent 可执行权限。

**权限模型**
- `User -> Role -> Skill -> Tool -> Action` 五段式授权。

**必做策略**
- 短期 Token、最小权限、敏感动作二次确认。

**验收标准**
- 越权调用拦截率 100%。

### 10.7 Memory Platform（短期 + 长期记忆）
**职责**
- 维护会话记忆、任务记忆、企业知识记忆。

**数据分层**
- Session Memory（分钟~天）
- Task Memory（天~周）
- Knowledge Memory（月~年）

**治理策略**
- 写入审核、TTL、版本标签、引用溯源。

**验收标准**
- 关键回答可定位引用来源。

### 10.8 Model Gateway（模型网关）
**职责**
- 多模型路由、脱敏、成本与延迟控制。

**路由策略**
- 低成本模型：分类/摘要。
- 高能力模型：复杂推理/跨工具规划。

**验收标准**
- 成本可观测，单任务 Token 成本有基线和告警。

### 10.9 Audit & Observability（审计与观测）
**职责**
- 全链路日志、指标告警、可回放。

**核心追踪字段**
- `trace_id`, `task_id`, `agent_run_id`, `tool_call_id`, `request_id`。

**验收标准**
- 任一异常任务 10 分钟内可完成链路定位。

### 10.10 Ops Console（运营控制台）
**职责**
- 岗位模板配置、策略开关、发布灰度、运行报表。

**关键看板**
- 业务指标：完成率、一次通过率、满意度。
- 运行指标：失败率、人工接管率、平均时延、成本。

**验收标准**
- 非研发角色可独立完成岗位模板发布。

---

## 11. 实施步骤（按周执行）

### Step 0：项目启动（第 0 周）
- 确定试点岗位（建议“销售运营助理”）和 3 个高频任务。
- 输出 RACI（产品/算法/后端/前端/安全/业务负责人）。
- 冻结成功指标：自动完成率、时效、满意度、成本。

### Step 1：基础骨架（第 1~2 周）
- 部署 PiAgent Runtime 与基础运行环境。
- 打通一个 IM Channel（飞书或企微）消息收发。
- 搭建任务主流程：任务创建、状态流转、结果回传。

**里程碑 M1**：用户可在 IM 发起任务并收到自动回复。

### Step 2：可执行闭环（第 3~4 周）
- 接入 1 个企业系统 Connector（如工单或 CRM）。
- 上线 3 个基础 Skills（检索、摘要、系统更新）。
- 增加错误重试与人工接管入口。

**里程碑 M2**：单任务闭环跑通（含失败回退）。

### Step 3：治理上线（第 5~6 周）
- 接入 SSO/RBAC，完成权限映射。
- 上线审计日志与 trace 追踪。
- 接入模型网关（脱敏、路由、预算告警）。

**里程碑 M3**：通过安全与合规最小门槛。

### Step 4：岗位模板化（第 7~8 周）
- 把试点岗位沉淀为 Persona + Policy + Workflow 模板。
- 支持模板版本管理与灰度发布。
- 建立岗位评估面板（完成率、一次通过率、接管率）。

**里程碑 M4**：同一岗位可稳定复制到第二个业务组。

### Step 5：扩展复制（第 9~12 周）
- 复制到第二、第三岗位（客服/HR 助理等）。
- 建立私有 Skill 仓审批机制。
- 完成季度复盘：收益、风险、优化清单。

**里程碑 M5**：形成“可持续运营”的组织级机制。

---

## 12. 交付物清单（每一步都有产物）
- 架构设计文档（本文件）
- 任务流程图与状态机定义
- 岗位模板规范（Persona/Policy/Workflow）
- Connector 开发模板与准入清单
- Skill 准入与版本治理规范
- IAM 权限矩阵与审计字段规范
- 上线检查清单（安全/性能/回滚）
