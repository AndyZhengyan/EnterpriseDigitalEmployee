# e-Agent-OS 顶层设计规格书

> **项目**: e-Agent-OS（Enterprise Agent Employee / 企业数字员工操作系统）
> **版本**: v1.0 — 顶层设计
> **日期**: 2026-04-03
> **范围**: 全系统架构设计，为后续所有子模块设计提供锚点
> **阅读指引**: 本文档是所有设计的"北极星"。后续任何子模块设计，均须先回读本文档对齐意图，再进入子模块 brainstorming。

---

## 一、产品愿景与战略定位

### 1.1 一句话定位

**e-Agent-OS = 企业数字员工的兵工厂 + 运营中心**

不是另一个 AI Chatbot 平台，而是企业数字员工的完整生命周期管理系统——让 AI 像员工一样被雇佣、上岗、培训、绩效考核、持续运营。

### 1.2 核心价值主张

| 维度 | 传统 SaaS | e-Agent-OS |
|------|-----------|------------|
| AI 能力 | 分散在各业务系统 | 集中管控，按需调度 |
| 数字员工 | 无 | 分钟级创建，模板化量产 |
| 技能管理 | 无 | 三层技能体系（通用→岗位→临时）|
| 运营 | 黑盒 | 全链路可观测、可审计 |
| 模型 | 绑定单一供应商 | 多 MaaS 隔离，智能路由 |

### 1.3 市场定位

**对标产品**：
- Microsoft Copilot Studio：企业 Copilot 管理平台，绑定 Microsoft 生态
- Salesforce Agentforce：CRM 驱动的 Agent 自动化，绑定 Salesforce 生态
- CrewAI / AutoGen：开发者友好的多 Agent 框架，面向技术团队
- AWS Bedrock Agents：云原生 Agent 编排，绑定 AWS 生态

**差异化定位**：
- **飞书原生**：以飞书机器人为核心交互入口，切入国内企业协作场景
- **岗位化设计**：AgentFamily = 岗位族，不是通用 Chatbot
- **运营闭环**：Badcase → 能效 → 审计，三环紧扣，不是只有任务执行
- **四层 IT 对接**：CLI > MCP > API > CU/BU，务实落地，不是空谈 API 优先

---

## 二、核心设计哲学

### 2.1 三条铁律

1. **Agent 即生产力，Agent 即企业数字员工**
   - 不是工具，是员工。所有管理制度、权限体系、知识体系均须按"员工"维度建模。

2. **赋予 Agent 员工的一切条件，让 Agent 像员工一样工作**
   - 岗位身份、企业 IT 权限、技能培训、历史记忆、绩效考核
   - Agent 的边界 = 员工岗位边界，不是"无限能力的 Chatbot"

3. **以模型为中心，最小化外置工程，基于模型能力提升获得最大化增益**
   - 不在工程复杂度上内卷，模型即能力。工程层只做必要的连接编排。
   - 供应商解耦，智能路由，让最强模型处理最关键任务。

### 2.2 架构分层原则

```
体验层（Channel）     → 用户感知：飞书、webhook、定时调度
      ↓
网关层（Gateway）     → 统一入口：鉴权、路由、限流、会话编排
      ↓
运行时层（Runtime）   → 任务执行：规划、执行、记忆、工具调度
      ↓
能力层（Hub）         → SkillHub · KnowledgeHub · ModelHub
      ↓
连接层（Connector）   → IT 系统对接：CLI / MCP / API / CU-BU
      ↓
治理层（Governance）  → 审计、Badcase、ROI、合规
```

**分层原则**：每一层只知道自己上下的邻居，不跨层调用。

---

## 三、核心对象模型

### 3.1 对象关系

```
Tenant（企业租户）
│
├── AgentFamily（岗位族）              ← 核心隔离单元
│   ├── SOUL        人格配置           │  MBTI / 沟通风格 / 价值观
│   ├── IDENTITY    身份配置           │  岗位职责 / 花名 / 工号 / 飞书ID
│   ├── AGENT       角色配置           │  工作范围 / KPI / 周边协同矩阵
│   └── Policy      策略配置           │  工具权限 / 审批规则 / 资源配额
│       │
│       └── AgentInstance[]（数字分身） ← 共享 Family 资产，独立 Session
│               ├── Session（会话隔离）│  每个用户对话独立，不共享上下文
│               ├── SkillBinding[]    │  绑定 Family 技能 + 个人扩展
│               └── Memory（短记忆）   │  仅限本次会话
│
├── Skill（技能）    L1通用 / L2岗位 / L3临时
├── Knowledge（知识）文档 / 案例 / SOP / AIGC沉淀
└── Model（模型）    MaaS接入 / 路由策略 / 配额
```

### 3.2 关键设计逻辑

| 设计点 | 规则 |
|--------|------|
| AgentFamily 之间 | 完全隔离，跨 Family 不可互相访问 |
| AgentInstance 之间 | 共享 Skill / Knowledge / Permission 模板，Session 完全隔离 |
| 飞书集成 | 超级数字员工（总入口） + N 个岗位数字员工（专属服务）|
| 配置同步 | AgentCore 配置由远端推送/拉取，Serverless 弹性扩缩容 |
| 知识沉淀 | AgentFamily 历史作业 → 案例提取 → COE 审核 → Skill 或 Knowledge |

### 3.3 AgentFamily 三段配置详解

#### SOUL（人格层）
定义 Agent 的性格底色，不影响任务能力，但影响交互风格。
- MBTI 人格类型
- 沟通风格（简洁汇报 / 详细说明 / 谨慎确认）
- 价值观锚点（合规优先 / 效率优先 / 用户体验优先）

#### IDENTITY（身份层）
定义 Agent 在企业中的岗位身份。
- 花名、工号、企业邮箱
- 岗位名称、职级、所属部门
- 向谁汇报、与谁协同（沟通矩阵）
- 飞书机器人账号绑定

#### AGENT（角色层）
定义 Agent 的工作职责边界，是整个系统的核心业务锚点。
- **工作范围**：负责什么，不负责什么
- **服务对象**：解决谁的什么问题
- **度量指标**：KPI（任务完成率 / 响应时长 / Token 效率）
- **管理要求**：合规检查点 / 审批流 / 升级规则
- **协同矩阵**：需要与哪些系统/角色交互

---

## 四、系统架构设计

### 4.1 逻辑架构总图

```
╔══════════════════════════════════════════════════════════════════╗
║                    渠道层 Channel Layer                           ║
║         飞书机器人(1+N) │ Webhook │ 定时调度 │ 事件触发           ║
╚════════════════════════════════╬══════════════════════════════════╝
                                 │
╔════════════════════════════════▼══════════════════════════════════╗
║                    网关层 Agent Gateway                           ║
║  飞书鉴权 │ 租户隔离 │ 路由分发 │ TLS加密 │ 限流熔断 │ 会话编排    ║
╚════════════════════════════════╬══════════════════════════════════╝
                                 │
╔════════════════════════════════▼══════════════════════════════════╗
║             运行时层 Agent Runtime Orchestrator                   ║
║  AgentFamily调度 │ Session管理 │ Task规划 │ Tool编排 │ HITL审批    ║
╚════════════════════════════════╬══════════════════════════════════╝
                                 │
      ┌──────────────────────────┼──────────────────────────┐
      │                          │                          │
╔═════▼═══════╗        ╔════════▼════════╗        ╔══════▼══════╗
║  技能中心   ║        ║     知识中心      ║        ║  模型中心   ║
║  SkillHub  ║        ║  KnowledgeHub    ║        ║  ModelHub   ║
║ 三层技能体系║        ║  AgenticRAG     ║        ║ 多MaaS接入  ║
║ 发布流水线  ║        ║ 多向量引擎       ║        ║ 智能路由    ║
║ 安全质检    ║        ║ AIGC知识沉淀     ║        ║ 流控与配额  ║
╚══════╤══════╝        ╚════════╤════════╝        ╚══════╤══════╝
       │                          │                        │
       └──────────────────────────┼────────────────────────┘
                                  │
╔═════════════════════════════════▼══════════════════════════════════╗
║                      连接器层 ConnectorHub                          ║
║            CLI适配器 >> MCP适配器 >> API适配器 >> CU/BU             ║
╚════════════════════════════════╬═══════════════════════════════════╝
                                  │
╔═════════════════════════════════▼══════════════════════════════════╗
║                    治理与运营层 Governance & Ops                   ║
║      审计Trace │ Badcase运营 │ ROI看板 │ 配置中心(推拉同步)         ║
╚═══════════════════════════════════════════════════════════════════╝
```

### 4.2 核心模块职责

#### Gateway（网关层）
- **定位**：统一入口，单一信任边界
- **职责**：飞书 JWT 鉴权 / 租户上下文注入 / AgentFamily 路由 / Session ID 生成 / 限流熔断
- **关键设计**：Session 前缀路由确保不同飞书用户命中不同 AgentInstance
- **部署**：1-2 个无状态实例，前置 SLB

#### Runtime（运行时层）
- **定位**：任务执行引擎，核心价值链
- **职责**：Agent 实例生命周期 / 任务规划（Plan→Act→Reflect）/ 工具调用编排 / 短期记忆管理
- **关键设计**：HITL（Human-in-the-Loop）审批节点，敏感操作必须人工确认
- **部署**：N 个实例，无状态，水平扩缩容

#### SkillHub（技能中心）
- **定位**：企业技能资产库 + 发布流水线
- **三层技能**：
  - L1 通用：邮件发送、飞书通知、审批流发起
  - L2 岗位：工单处理、报表生成、代码审查
  - L3 临时：一次性任务，一次用完即弃
- **生命周期**：Draft → Testing → Staging → Published → Deprecated
- **发布流水线**：Skill 创建 → 安全扫描 → 测试用例执行 → COE 审核 → 上架
- **部署**：1 实例（轻量），状态存储在 PostgreSQL

#### KnowledgeHub（知识中心）
- **定位**：企业知识资产化 + AIGC 自动沉淀
- **核心能力**：
  - AgenticRAG：多路召回（向量+全文+关键词）→ 融合重排 → 证据组装
  - 全模态解析：PDF/Word/飞书文档/代码
  - AIGC 沉淀：AgentFamily 历史案例 → COE 审核 → 写入 Skill 或 Knowledge
- **关键设计**：渐进式检索，小查询先命中 L3/L2，大查询触发 L1 全面检索
- **部署**：1-2 实例 + Qdrant 向量数据库

#### ModelHub（模型中心）
- **定位**：多 MaaS 统一接入，智能路由
- **核心能力**：
  - 多模型统一接入（Claude / GPT / 通义 / Kimi 等）
  - 动态路由策略（按任务类型 / 成本 / SLA / 可用性）
  - Token 配额管理（Tenant 级 / AgentFamily 级 / Instance 级）
  - 失败自动降级（主模型不可用 → 降级模型 → 人工兜底）
- **路由策略示例**：

  | 任务类型 | 首选 | 降级 | 说明 |
  |----------|------|------|------|
  | planning | Claude 3.5 | GPT-4o | 复杂规划需要强推理 |
  | fast | GPT-4o-mini | 通义turbo | 快回复低成本 |
  | code | Claude 3.5 | GPT-4o | 代码质量优先 |
  | sensitive | Claude 3.5 | — | 合规场景不用国产 |

- **部署**：1-2 实例，MaaS API Key 统一管理

#### ConnectorHub（连接器中心）
- **定位**：企业 IT 系统的统一接入层
- **四层优先级**：

  ```
  优先级1: CLI 适配器     → 最高可靠性，最低延迟（如 git CLI, gh CLI）
  优先级2: MCP 适配器     → 标准化协议（如 GitHub MCP, Filesystem MCP）
  优先级3: API 适配器     → REST/GraphQL，接口封装（如 JIRA API, 飞书 API）
  优先级4: CU/BU 适配器  → 最后手段，准确率有限，需人工兜底
  ```

- **关键设计**：每类连接器独立健康检查，故障自动摘除
- **部署**：按需部署，每类 IT 系统一个 Connector 实例

#### OpsCenter（运营中心）
- **定位**：数字员工的"HR + 财务 + 审计"三合一
- **三大闭环**：
  1. **Badcase 运营**：受理（用户反馈/系统检测）→ 分类分流（IT未覆盖/知识未覆盖/Skill健壮性）→ 根因修复 → 验证闭环 → COE 复盘
  2. **能效运营**：AgentFamily 级 / Instance 级 / Skill 级指标看板，Token 消耗、任务成功率、响应时长、负荷
  3. **审计 Trace**：全链路事件日志（每次任务分配 TraceID），支持回放、合规审计、运维调优

#### Governance（治理模块）
- **定位**：平台规则引擎，不是业务模块
- **职责**：RBAC/ABAC 权限模型 / AgentFactory 配额管控 / 合规策略执行
- **角色定义**：

  | 角色 | 权限范围 |
  |------|----------|
  | platform_admin | 全平台所有权限 |
  | tenant_admin | 租户内所有权限 |
  | tenant_operator | 租户内运营权限（不包含删除）|
  | employee_user | 基础使用权限 |

---

## 五、IT 系统对接策略

### 5.1 优先级矩阵

| 优先级 | 方式 | 适用场景 | 准确率 | 实施成本 |
|--------|------|----------|--------|----------|
| P0 | CLI | GitHub, GitLab, kubectl, aws cli | 极高 | 低 |
| P1 | MCP | 有官方 MCP Server 的系统 | 高 | 中 |
| P2 | API | 有 REST/GraphQL 的系统（JIRA, 飞书）| 高 | 高（接口封装）|
| P3 | CU/BU | 无 API 的遗留系统 | 低 | 高（需人工兜底）|

### 5.2 接入决策树

```
新系统接入评估：
1. 有 CLI 吗？→ 是 → P0 CLI 适配器
2. 有 MCP Server 吗？→ 是 → P1 MCP 适配器
3. 有稳定 API 吗？→ 是 → P2 API 适配器（评估接口覆盖率）
4. 以上均无 → 评估 CU/BU 成本，或提需求给该系统供应商
```

---

## 六、产品形态设计

### 6.1 飞书 Channel 接入（主力入口）

```
飞书 App
    │
    ├── [1] 超级数字员工（总入口）
    │         用户描述需求 → 超级数字员工理解 → 分发至对应岗位数字员工
    │
    └── [N] 岗位数字员工矩阵
              数据分析专员 AgentFamily
              软件开发工程师 AgentFamily
              法务专员 AgentFamily
              需求分析师 AgentFamily
              ...
```

**超级数字员工职责**：
- 意图理解 + AgentFamily 推荐
- 跨 Family 协调任务
- 主动推荐（基于用户行为推荐合适的数字员工）
- 统一呈现，不暴露底层技术细节

### 6.2 后台服务开放

```
Webhook 回调：
  IT系统 → e-Agent-OS Webhook API → 任务入队 → 执行 → 回调通知

定时调度：
  定时任务配置 → 触发 Agent 执行 → 结果推送/存储

任务托管：
  用户发起任务 → 选择 AgentFamily → 设置参数 → 托管执行 → 通知结果
```

### 6.3 运营管理 Portal

```
数字员工中心（运营Portal）
├── 数字员工生产中心：构建数字员工 / 构建岗位技能
├── 数字员工运营中心：运营数字员工（Badcase / 能效 / 审计）
├── 企业知识中心：知识生产 / 接入 / 解析 / 表征 / 消费
└── AI大模型中心：模型网关配置 / 消费运营
```

> 注：前端运营 Portal 的 Phase 1 设计详见 `2026-04-02-enterpriseagentforce-frontend-design.md`

---

## 七、数据模型

### 7.1 核心实体

```
Tenant（租户）
    ├── TenantMember（租户成员）
    ├── AgentFamily（岗位族）
    │       ├── SOUL（人格配置，JSON）
    │       ├── IDENTITY（身份配置，JSON）
    │       ├── AGENT（角色配置，JSON）
    │       ├── Policy（策略配置，JSON）
    │       └── AgentInstance（数字分身）
    │               ├── Session（会话）
    │               │       └── Task（任务）
    │               │               └── TaskStep（任务步骤）
    │               ├── SkillBinding（技能绑定）
    │               └── Memory（短记忆）
    ├── Skill（技能）
    │       └── SkillVersion（技能版本）
    ├── Knowledge（知识）
    │       └── Document（文档）
    │               └── Chunk（知识片段）
    └── ModelEndpoint（模型接入点）
```

### 7.2 主要数据表

| 表名 | 说明 |
|------|------|
| tenants | 租户表 |
| tenant_members | 租户成员表 |
| agent_families | 岗位族表（含 SOUL/IDENTITY/AGENT JSON）|
| agent_instances | 数字分身表 |
| sessions | 会话表 |
| tasks | 任务表 |
| task_steps | 任务步骤表（含 TraceID）|
| skills | 技能表 |
| skill_versions | 技能版本表 |
| skill_capabilities | 技能能力描述表 |
| knowledge_documents | 知识文档表 |
| document_chunks | 文档分块表（向量+原文）|
| model_endpoints | 模型接入点表 |
| model_calls | 模型调用记录表（计费用）|
| audit_logs | 审计日志表（全链路）|
| badcases | Badcase 记录表 |
| connectors | 连接器注册表 |

---

## 八、部署架构

### 8.1 服务拆分

```
apps/
├── gateway/            # 网关服务（1-2 实例，无状态）
├── runtime/           # 运行时服务（N 实例，弹性扩缩）
├── model-hub/         # 模型中心（1-2 实例）
├── connector-hub/     # 连接器中心（按需，每系统 1 实例）
├── skill-hub/        # 技能中心（1 实例）
├── knowledge-hub/    # 知识中心（1-2 实例）
├── governance/       # 治理服务（1-2 实例）
├── ops-center/       # 运营中心（1 实例）
└── admin-portal/     # 管理 Portal（1 实例）
```

### 8.2 基础设施选型

| 组件 | 推荐方案 | 说明 |
|------|----------|------|
| 数据库 | PostgreSQL | 主数据，向量插件（pgvector）|
| 缓存/消息 | Redis + BullMQ | Session、限流、异步任务队列 |
| 向量数据库 | Qdrant | 知识检索，向量召回 |
| 对象存储 | S3/MinIO | 文档、日志、审计记录 |
| 日志 | Loki + Grafana | 日志收集 + 可视化 |
| 监控 | Prometheus + Grafana | 指标监控大盘 |
| 部署 | Docker + Kubernetes | 容器化，弹性扩缩 |

### 8.3 弹性扩缩策略

- **Runtime**：根据飞书 Channel 并发消息量，K8s HPA 自动扩缩（目标 CPU 60%，冷启动 <30s）
- **ConnectorHub**：按 IT 系统独立部署，故障隔离
- **配置同步**：AgentCore 配置从 ConfigCenter 拉取，支持热更新（无需重启 Agent）

---

## 九、技术选型

### 9.1 Agent Core 选型决策

| 方案 | 优势 | 劣势 | 结论 |
|------|------|------|------|
| **PiAgent（openclaw）** | 轻量、MIT 许可、易定制、子进程调用简单 | 生态较新 | **推荐** — 架构简单好维护 |
| Claude Code | 能力强、工具生态好 | 商业许可复杂、定制成本高 | 备选，特定岗位可引入 |
| LangChain/LangGraph | Python 生态成熟 | 过度工程化、隐藏复杂性 | 明确不用 — 过度设计 |

> 详见 `2026-03-31-piagent-sidecar-design.md`

### 9.2 技术栈总结

| 层级 | 技术选型 |
|------|----------|
| 后端语言 | Python 3.13 + FastAPI + Pydantic |
| 数据库 | PostgreSQL + Qdrant |
| 缓存/队列 | Redis + BullMQ |
| 可观测性 | OpenTelemetry + Prometheus + Grafana |
| 前端 | Vue 3 + Vite + TypeScript |
| AgentCore | openclaw（pi-mono via subprocess CLI）|
| 部署 | Docker + Kubernetes |

---

## 十、发展路线图

| 阶段 | 周期 | 里程碑 | 交付物 |
|------|------|--------|--------|
| **Phase 0** | Week 1-4 | 核心闭环：Gateway + Runtime + ModelHub + 1 个连接器（飞书）| 飞书机器人可对话，任务执行全链路跑通 |
| **Phase 1** | Week 5-8 | 能力丰富：SkillHub + KnowledgeHub + 运营看板（Dashboard）| 技能市场上架，知识库 RAG 生效，运营数据可看 |
| **Phase 2** | Week 9-12 | 治理增强：RBAC + 审批流 + 多租户 + Badcase 运营 | 权限体系完整，Badcase 闭环可运作 |
| **Phase 3** | Week 13-16 | 规模化：多连接器 + 高级运营（ROI 看板）+ 多 AgentFamily | 多 IT 系统接入，ROI 可量化 |

---

## 十一、关键设计决策记录

> 以下是本设计中的核心决策点及其依据。新增决策持续追加至此，便于日后 review。

| ID | 决策 | 依据 | 替代方案 |
|----|------|------|----------|
| D-01 | AgentCore 选用 PiAgent/openclaw | 轻量、MIT 许可、子进程集成简单、易定制 | Claude Code（商业许可复杂）|
| D-02 | 飞书作为主力 Channel | 国内企业协作入口，用户习惯好，BOT API 成熟 | 企业微信（生态较封闭）|
| D-03 | 三层技能 L1/L2/L3 | 企业通用技能复用 vs 岗位专用性 vs 临时灵活性 | 两层（太粗）或四层（太复杂）|
| D-04 | IT 对接 CLI > MCP > API > CU/BU | 可靠性优先，不是覆盖优先 | 直接 API 优先（部分系统 API 不稳定）|
| D-05 | Session 完全隔离，Family 共享资产 | 模拟真实企业：同一岗位不同员工共享工具和知识，但不共享当前任务 | 所有 Agent 完全共享（无隔离，风险高）|

---

## 十二、参考文献

- 用户原始构想记录（2026-04-03）
- ARCHITECTURE.md（现有架构文档）
- `2026-04-02-enterpriseagentforce-frontend-design.md`（前端设计规格书）
- `2026-03-31-piagent-sidecar-design.md`（PiAgent 集成设计）
- Microsoft Copilot Studio vs Salesforce AgentForce（行业对标）
- CrewAI / AutoGen / LangGraph（开源框架对标）

---

**文档版本**: v1.0
**创建日期**: 2026-04-03
**下次审查**: 每次涉及 e-Agent-OS 架构设计的子模块工作开始前
