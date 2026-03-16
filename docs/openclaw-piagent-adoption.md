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

## 4.1 Channel 兼容要点
- 协议：严格遵循 OpenClaw Channel 消息规范。
- 鉴权：企业统一签发短期 Token，支持最小权限。
- 幂等：每个 Channel Action 要有 request_id，支持重放保护。
- 可观测：统一输出 action_trace_id，串联审计链路。

## 4.2 ClawHub Skill 兼容要点
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

## 阶段 1（2~4 周）：内核接入验证
- 跑通 PiAgent Runtime。
- 打通 1 个 Channel（如飞书）+ 1 个企业系统 Connector。
- 接入 3~5 个基础 Skills（检索、总结、工单操作）。

**验收**：可完成端到端单任务闭环（接收 -> 执行 -> 汇报）。

## 阶段 2（4~8 周）：企业治理补齐
- 上线 IAM 映射、审计日志、模型网关策略。
- 上线岗位模板化与版本灰度。
- 上线私有 Skill 仓与审批流。

**验收**：满足企业试点部门安全要求。

## 阶段 3（8~12 周）：规模化复制
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
