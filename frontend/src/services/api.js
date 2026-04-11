// frontend/src/services/api.js
// e-Agent-OS OpCenter — API Service Layer
import axios from 'axios';
import {
  MOCK_EMPLOYEES,
  MOCK_DASHBOARD_STATS,
  MOCK_STATUS_DIST,
  MOCK_TOKEN_TREND,
  MOCK_TASK_TREND,
  MOCK_ACTIVITY,
} from '../mock/data.js';
import {
  MOCK_BLUEPRINTS,
  DEPARTMENTS,
} from '../mock/blueprints.js';

const USE_MOCK = false; // flip to false when connecting to real backend

const api = axios.create({
  baseURL: '/api',
  timeout: 300_000,  // 5 minutes — agent tasks can take time
});

// ---- Mock Implementations ----

function mockGetEmployees({ status, department, title, search } = {}) {
  let result = [...MOCK_EMPLOYEES];
  if (status) result = result.filter(e => e.status === status);
  if (department) result = result.filter(e => e.department === department);
  if (title) result = result.filter(e => e.title === title);
  if (search) {
    const q = search.toLowerCase();
    result = result.filter(
      e =>
        e.name.toLowerCase().includes(q) ||
        e.id.toLowerCase().includes(q) ||
        e.title.toLowerCase().includes(q),
    );
  }
  return Promise.resolve({ data: result });
}

function mockGetEmployee(id) {
  const emp = MOCK_EMPLOYEES.find(e => e.id === id);
  if (!emp) return Promise.reject({ response: { status: 404 } });
  return Promise.resolve({ data: emp });
}

function mockGetDashboardStats() {
  return Promise.resolve({ data: MOCK_DASHBOARD_STATS });
}

function mockGetStatusDist() {
  return Promise.resolve({ data: MOCK_STATUS_DIST });
}

function mockGetTokenTrend() {
  return Promise.resolve({ data: MOCK_TOKEN_TREND });
}

function mockGetTaskTrend() {
  return Promise.resolve({ data: MOCK_TASK_TREND });
}

function mockGetActivity({ limit = 10 } = {}) {
  return Promise.resolve({ data: MOCK_ACTIVITY.slice(0, limit) });
}

function mockGetBlueprints() {
  return Promise.resolve({ data: MOCK_BLUEPRINTS });
}

function mockDeploy(payload) {
  const id = `av-${payload.role}-${Date.now()}`;
  return Promise.resolve({
    data: {
      id,
      role: payload.role,
      alias: payload.alias || payload.role,
      department: payload.department,
      versions: [
        {
          version: 'v1.0.0',
          status: 'published',
          traffic: 100,
          replicas: payload.scaling?.minReplicas ?? 1,
          config: { soul: payload.soul || {}, skills: [], tools: [], model: '' },
          scaling: payload.scaling || { minReplicas: 1, maxReplicas: 5, targetLoad: 70 },
        },
      ],
      capacity: {
        used: payload.scaling?.minReplicas ?? 1,
        max: payload.scaling?.maxReplicas ?? 5,
      },
    },
  });
}

function mockAdjustTraffic(blueprintId, versionIndex, traffic) {
  return Promise.resolve({
    data: { blueprintId, versionIndex, traffic },
  });
}

// ---- Public API Functions ----

export const employeeApi = {
  list: (params) =>
    USE_MOCK ? mockGetEmployees(params) : api.get('/employees', { params }),
  get: (id) =>
    USE_MOCK ? mockGetEmployee(id) : api.get(`/employees/${id}`),
};

export const dashboardApi = {
  stats: () =>
    USE_MOCK ? mockGetDashboardStats() : api.get('/dashboard/stats'),
  statusDist: () =>
    USE_MOCK ? mockGetStatusDist() : api.get('/dashboard/status-dist'),
  tokenTrend: () =>
    USE_MOCK ? mockGetTokenTrend() : api.get('/dashboard/token-trend'),
  taskTrend: () =>
    USE_MOCK ? mockGetTaskTrend() : api.get('/dashboard/task-trend'),
  activity: (params) =>
    USE_MOCK ? mockGetActivity(params) : api.get('/activity', { params }),
};

export const opsApi = {
  execute: (payload) =>
    USE_MOCK
      ? Promise.resolve({
          data: {
            status: 'ok',
            summary: 'mock',
            tokenTotal: 100,
            durationMs: 2000,
          },
        })
      : api.post('/ops/execute', payload),
};

export const onboardingApi = {
  list: () =>
    USE_MOCK ? mockGetBlueprints() : api.get('/onboarding/blueprints'),
  deploy: (payload) =>
    USE_MOCK ? mockDeploy(payload) : api.post('/onboarding/deploy', payload),
  adjustTraffic: (blueprintId, versionIndex, traffic) =>
    USE_MOCK
      ? mockAdjustTraffic(blueprintId, versionIndex, traffic)
      : api.put(`/onboarding/blueprints/${blueprintId}/traffic`, {
          version_index: versionIndex,
          traffic,
        }),
  deprecateVersion: (blueprintId, versionIndex) =>
    api.put(`/onboarding/blueprints/${blueprintId}/versions/${versionIndex}/deprecate`),
};

// ---- Mock Journal Data ----

const MOCK_JOURNAL = [
  {
    id: 'exec-001',
    alias: '码哥',
    role: '软件工程师',
    dept: '技术研发部',
    blueprintId: 'av-swe-001',
    status: 'ok',
    message: '帮我审查代码',
    input: '用户发送了一段 Python 代码，要求审查是否存在安全漏洞和性能问题。\n\n```python\ndef process_user_data(user_input):\n    eval(user_input)\n    return "Done"\n```',
    summary: '审查完成，发现 1 个高风险漏洞（eval 注入）和 1 个性能问题。已在代码中标注。',
    tokenTotal: 1500,
    durationMs: 2300,
    createdAt: '2026-04-07T09:00:00Z',
  },
  {
    id: 'exec-002',
    alias: '明律',
    role: '法务专员',
    dept: '法务合规部',
    blueprintId: 'av-legal-001',
    status: 'error',
    message: '审阅采购合同',
    input: '请审阅以下采购合同，重点检查违约责任条款和知识产权归属。\n\n甲方：A公司\n乙方：B公司\n金额：500万元\n期限：2年',
    summary: '合同存在重大风险：1）违约金条款过重；2）知识产权默认归甲方所有。建议修改第8条和第12条。',
    tokenTotal: 700,
    durationMs: 3800,
    createdAt: '2026-04-07T10:15:00Z',
  },
  {
    id: 'exec-003',
    alias: '行行',
    role: '行政专员',
    dept: '综合管理部',
    blueprintId: 'av-admin-001',
    status: 'ok',
    message: '安排下周会议',
    input: '需要安排一个周一至周五的工作会议，参与者：王总、李经理、张助理，地点在公司大会议室。',
    summary: '已安排：周四下午2:00，公司大会议室。已发送日历邀请给所有参与者。',
    tokenTotal: 420,
    durationMs: 1100,
    createdAt: '2026-04-07T11:30:00Z',
  },
  {
    id: 'exec-004',
    alias: '合同小秘',
    role: '合同专员',
    dept: '商务运营部',
    blueprintId: 'av-legal-002',
    status: 'ok',
    message: '起草劳动合同',
    input: '为新入职员工起草一份标准劳动合同，岗位：高级产品经理，基本月薪35000元，合同期限3年。',
    summary: '劳动合同已起草完成，包含标准条款：试用期、工作内容、薪酬福利、保密协议、竞业限制。',
    tokenTotal: 980,
    durationMs: 2800,
    createdAt: '2026-04-07T14:00:00Z',
  },
  {
    id: 'exec-005',
    alias: '码哥',
    role: '软件工程师',
    dept: '技术研发部',
    blueprintId: 'av-swe-001',
    status: 'ok',
    message: '解释分布式锁原理',
    input: 'Redis 分布式锁的实现原理是什么？如何避免死锁？',
    summary: 'Redis 分布式锁基于 SET NX EX 原子命令实现。避免死锁需设置过期时间，并使用唯一 value 标识持有者，释放时先检查再删除。',
    tokenTotal: 2100,
    durationMs: 1500,
    createdAt: '2026-04-07T15:45:00Z',
  },
  {
    id: 'exec-006',
    alias: '明律',
    role: '法务专员',
    dept: '法务合规部',
    blueprintId: 'av-legal-001',
    status: 'ok',
    message: '提供数据合规建议',
    input: '我们的 App 即将上线，需要确认是否符合《个人信息保护法》要求。',
    summary: '建议补充：1）隐私政策公示；2）用户同意书；3）数据删除机制；4）未成年人保护条款。上线前需完成个人信息保护影响评估。',
    tokenTotal: 1200,
    durationMs: 4200,
    createdAt: '2026-04-07T16:30:00Z',
  },
];

function mockListExecutions({ status, role, dept, q } = {}) {
  let result = [...MOCK_JOURNAL];
  if (status && status !== 'all') {
    result = result.filter((e) => e.status === status);
  }
  if (role && role !== 'all') {
    result = result.filter((e) => e.role === role);
  }
  if (dept && dept !== 'all') {
    result = result.filter((e) => e.dept === dept);
  }
  if (q) {
    const lower = q.toLowerCase();
    result = result.filter(
      (e) =>
        e.message.toLowerCase().includes(lower) ||
        e.summary.toLowerCase().includes(lower) ||
        e.alias.toLowerCase().includes(lower),
    );
  }
  return Promise.resolve({ data: { total: result.length, items: result } });
}

function mockGetExecution(id) {
  const exec = MOCK_JOURNAL.find((e) => e.id === id);
  if (!exec) return Promise.reject({ response: { status: 404 } });
  return Promise.resolve({ data: exec });
}

// ---- Mock Oracle Data ----

const MOCK_ARCHIVES = [
  {
    id: 'arch-001',
    source: 'avatar',
    title: '团队代码审查 SOP v2.1',
    contributor: '码哥',
    tags: ['SOP', 'Code Review', '安全'],
    createdAt: '2026-04-05T10:00:00Z',
    summary: '定义了代码审查流程：提交前必须通过静态分析、安全扫描、单元测试覆盖率 >= 80%。',
  },
  {
    id: 'arch-002',
    source: 'avatar',
    title: '数据安全合规检查清单',
    contributor: '明律',
    tags: ['合规', 'PIPL', 'GDPR'],
    createdAt: '2026-04-04T14:30:00Z',
    summary: '覆盖《个人信息保护法》核心要求，包括数据收集最小化、存储加密、用户删除权等。',
  },
  {
    id: 'arch-003',
    source: 'avatar',
    title: '合同起草标准模板说明',
    contributor: '合同小秘',
    tags: ['合同', '模板', '法务'],
    createdAt: '2026-04-03T09:15:00Z',
    summary: '标准劳动合同、采购合同、服务合同三大模板的使用场景及注意事项。',
  },
  {
    id: 'arch-004',
    source: 'import',
    title: '会议纪要 — Q1 产品规划会',
    contributor: '产品部',
    tags: ['会议', '规划'],
    createdAt: '2026-04-02T16:00:00Z',
    summary: 'Q1 产品规划会会议纪要，确认了三个核心功能的优先级和交付时间节点。',
  },
  {
    id: 'arch-005',
    source: 'import',
    title: '员工手册 — 考勤与报销制度',
    contributor: '行政部',
    tags: ['HR', '考勤', '报销'],
    createdAt: '2026-04-01T11:00:00Z',
    summary: '最新版本员工手册，包含考勤打卡规则、请假流程、差旅报销标准等。',
  },
  {
    id: 'arch-006',
    source: 'import',
    title: '技术架构选型决策记录',
    contributor: '架构组',
    tags: ['架构', '决策'],
    createdAt: '2026-03-28T10:30:00Z',
    summary: '微服务架构选型评估，含 Redis vs etcd 对比、Kafka vs RabbitMQ 性能基准测试结果。',
  },
];

function mockListArchives({ source } = {}) {
  let result = [...MOCK_ARCHIVES];
  if (source === 'avatar') {
    result = result.filter(a => a.source === 'avatar');
  } else if (source === 'import') {
    result = result.filter(a => a.source === 'import');
  }
  return Promise.resolve({ data: { total: result.length, items: result } });
}

const MOCK_ARCHIVE_CONTENT = {
  'arch-001': `## 团队代码审查 SOP v2.1

### 适用范围
所有后端（Python/Go）和前端（TypeScript）代码提交到 main 分支前必须通过审查。

### 审查流程

1. **提交前检查**
   - 静态分析通过（ruff / eslint）
   - 安全扫描通过（bandit / semgrep）
   - 单元测试覆盖率 >= 80%

2. **Pull Request 要求**
   - 必须填写 Template
   - 至少 1 人 Approve
   - CI 所有 checks green

3. **审查重点**
   - 逻辑正确性
   - 安全漏洞（注入、越权、敏感信息泄露）
   - 性能问题（N+1、冷路径优化）
   - 可读性与文档

### 评分标准

| 级别 | 问题类型 | 处理方式 |
|------|----------|----------|
| Blocker | 安全漏洞、信息泄露 | 必须修复 |
| Major | 逻辑错误、严重性能问题 | 必须修复 |
| Minor | 代码风格、可读性 | 建议修复 |
| Nit | 微小优化 | 可忽略 |

### 附录

- 静态分析配置：\`ruff.toml\`
- 安全扫描配置：\`bandit.yaml\``,
  'arch-002': `## 数据安全合规检查清单

### 法规依据
- 《中华人民共和国个人信息保护法》(PIPL)
- 《中华人民共和国数据安全法》
- 《通用数据保护条例》(GDPR) — 如涉及欧盟用户

### 检查清单

#### 1. 数据收集
- [ ] 最小化原则：仅收集业务必需数据
- [ ] 告知同意：用户明确同意数据收集目的
- [ ] 敏感数据：生物信息、位置、健康数据需额外授权

#### 2. 数据存储
- [ ] 加密存储：敏感字段使用 AES-256 加密
- [ ] 密钥管理：禁止硬编码，使用 KMS
- [ ] 日志脱敏：禁止明文记录手机号、身份证

#### 3. 数据使用
- [ ] 目的限制：数据仅用于声明目的
- [ ] 跨境传输：如需跨境需通过安全评估
- [ ] 第三方共享：需签订数据处理协议

#### 4. 用户权利
- [ ] 查阅权：用户提供查询入口
- [ ] 删除权：提供账号注销 + 数据删除
- [ ] 可携带权：支持数据导出（JSON/CSV）`,
  'arch-003': `## 合同起草标准模板说明

### 模板分类

#### A. 劳动合同
- 适用场景：新员工入职
- 关键条款：试用期、薪酬福利、保密协议、竞业限制
- 注意事项：
  - 试用期最长不超过 6 个月
  - 竞业限制补偿金不低于月薪 30%
  - 加班需支付加班费或安排调休

#### B. 采购合同
- 适用场景：采购设备、软件、服务
- 关键条款：标的规格、交付时间、付款方式、违约责任
- 注意事项：
  - 违约金上限为合同金额 20%
  - 知识产权默认归甲方所有
  - 争议解决首选仲裁

#### C. 服务合同
- 适用场景：外包开发、咨询服务
- 关键条款：服务范围、工作量估算、验收标准
- 注意事项：
  - 明确验收标准和验收期限
  - 保留变更单据作为合同附件`,
  'arch-004': `## Q1 产品规划会 — 会议纪要

**时间**: 2026年4月2日 14:00-16:00
**地点**: 大会议室 + Zoom 远程
**参会人**: 王总、李经理、张助理、产品团队

### 议程

1. Q1 工作复盘
2. Q2 功能优先级确认
3. 资源分配讨论

### 决议事项

#### 优先级 P0（Q2 内必须上线）
- **功能A**: 用户画像 2.0 — 个性化推荐引擎升级
- **功能B**: 权限体系重构 — RBAC 到 ABAC 升级

#### 优先级 P1（Q2 尽量上线）
- **功能C**: 数据分析看板 v2 — 支持自定义指标
- **功能D**: 通知中心重构 — 统一消息推送

### 时间节点
- 4月15日：功能A 设计评审
- 4月30日：功能A 开发完成，进入测试
- 5月15日：功能A 上线

### 待跟进
- [ ] 张助理：协调设计资源
- [ ] 李经理：与技术团队确认工期
- [ ] 王总：确认 ABAC 供应商选型`,
  'arch-005': `## 员工手册 — 考勤与报销制度（2026版）

### 第一章 考勤制度

#### 工作时间
- 上班时间：9:00
- 下班时间：18:00
- 午休时间：12:00-13:00

#### 请假类型
| 类型 | 天数上限 | 是否带薪 |
|------|----------|----------|
| 年假 | 按工龄 | 是 |
| 病假 | 12天/年 | 前3天带薪 |
| 事假 | 3天/年 | 否 |
| 婚假 | 3天 | 是 |
| 产假 | 98天 | 是 |

#### 打卡规则
- 公司园区内必须人脸识别打卡
- 外勤需在 OA 系统提交外出申请
- 补卡每月最多 2 次，需部门负责人审批

---

### 第二章 报销制度

#### 差旅报销标准

| 级别 | 机票 | 酒店 | 餐补 |
|------|------|------|------|
| 总监及以上 | 经济舱 | 实报 | 200元/天 |
| 经理 | 经济舱 | <= 500元 | 150元/天 |
| 员工 | 经济舱 | <= 350元 | 100元/天 |

#### 报销流程
1. 事前：在 OA 提交出差申请
2. 事中：保留发票（电子/纸质均可）
3. 事后：30天内提交报销单，逾期不予报销

#### 注意事项
- 单笔超过 2000 元需总监审批
- 发票抬头必须为公司全称
- 滴滴出行行程单可替代发票`,
  'arch-006': `## 技术架构选型决策记录

**日期**: 2026年3月28日
**架构组**: 技术研发部
**状态**: 已批准

### 1. 缓存层：Redis vs etcd

| 维度 | Redis | etcd |
|------|-------|------|
| 吞吐量 | 100k+ QPS | ~20k QPS |
| 持久化 | RDB+AOF | WAL + Snapshot |
| 生态 | 丰富 | Kubernetes 原生 |
| 适用场景 | 缓存、会话 | 服务发现、配置中心 |

**决策**: 选择 **Redis**，原因：吞吐量更高，运维成熟，支持多种数据结构。

---

### 2. 消息队列：Kafka vs RabbitMQ

#### 基准测试结果

| 场景 | Kafka TPS | RabbitMQ TPS |
|------|-----------|--------------|
| 单消费者 | 45,000 | 12,000 |
| 10消费者 | 280,000 | 95,000 |
| 消息大小 1KB | 延迟 < 5ms | 延迟 < 10ms |

**决策**: 选择 **Kafka**，原因：高吞吐、低延迟、生态完善（Kafka Connect、Schema Registry）。

---

### 3. 部署架构

架构图：

[Nginx Gateway]
      |
      +-- Service A -- Redis Cluster -- Kafka
      +-- Service B -- Redis Cluster -- PostgreSQL
      +-- Service C -- Redis Cluster -- S3`,
};

function mockGetArchive(id) {
  const archive = MOCK_ARCHIVES.find((a) => a.id === id);
  if (!archive) return Promise.reject({ response: { status: 404 } });
  return Promise.resolve({
    data: {
      ...archive,
      content: MOCK_ARCHIVE_CONTENT[id] || '# 暂无内容\n\n该档案内容正在补充中。',
    },
  });
}

// ---- Oracle API ----

export const oracleApi = {
  list: (params) =>
    USE_MOCK ? mockListArchives(params) : api.get('/oracle/archives', { params }),
  get: (id) =>
    USE_MOCK ? mockGetArchive(id) : api.get(`/oracle/archives/${encodeURIComponent(id)}`),
  upload: (payload) => api.post('/oracle/archives/upload', payload),
};

// ---- Journal API ----

export const journalApi = {
  list: (filters) =>
    USE_MOCK ? mockListExecutions(filters) : api.get('/journal/executions', { params: filters }),
  get: (id) =>
    USE_MOCK ? mockGetExecution(id) : api.get(`/journal/executions/${id}`),
};

export { DEPARTMENTS };
export default api;
