// frontend/src/mock/blueprints.js
// Onboarding MVP — Mock Blueprint Data

export const MOCK_BLUEPRINTS = [
  {
    id: 'av-admin-001',
    role: '行政专员',
    alias: '小白',
    department: '综合管理部',
    versions: [
      {
        version: 'v1.0.0',
        status: 'published',
        traffic: 60,
        replicas: 3,
        config: {
          soul: { mbti: 'ISFJ', style: '简洁汇报', priority: '效率优先' },
          skills: ['飞书通知', '文档处理'],
          tools: ['飞书API', '文档处理器'],
          model: 'claude-sonnet-4-7',
        },
        scaling: { minReplicas: 1, maxReplicas: 5, targetLoad: 60 },
      },
      {
        version: 'v1.0.1',
        status: 'published',
        traffic: 40,
        replicas: 2,
        config: {
          soul: { mbti: 'ISFJ', style: '简洁汇报', priority: '效率优先' },
          skills: ['飞书通知', '文档处理', '数据录入'],
          tools: ['飞书API', '文档处理器', '数据库连接器'],
          model: 'claude-sonnet-4-7',
        },
        scaling: { minReplicas: 1, maxReplicas: 5, targetLoad: 60 },
      },
      {
        version: 'v1.1.0-beta',
        status: 'testing',
        traffic: 0,
        replicas: 1,
        config: {
          soul: { mbti: 'INTJ', style: '详细说明', priority: '合规优先' },
          skills: ['飞书通知', '文档处理', '数据分析', '合规检查'],
          tools: ['飞书API', '文档处理器', '数据分析引擎'],
          model: 'claude-opus-4-7',
        },
        scaling: { minReplicas: 1, maxReplicas: 3, targetLoad: 70 },
      },
    ],
    capacity: { used: 6, max: 10 },
  },
  {
    id: 'av-legal-001',
    role: '法务专员',
    alias: '明律',
    department: '法务合规部',
    versions: [
      {
        version: 'v1.0.0',
        status: 'published',
        traffic: 100,
        replicas: 1,
        config: {
          soul: { mbti: 'INTJ', style: '详细说明', priority: '合规优先' },
          skills: ['合同审核', '法规检索', '合规检查'],
          tools: ['飞书API', '知识库检索', '合规引擎'],
          model: 'claude-opus-4-7',
        },
        scaling: { minReplicas: 1, maxReplicas: 3, targetLoad: 60 },
      },
    ],
    capacity: { used: 1, max: 5 },
  },
  {
    id: 'av-contract-001',
    role: '合同专员',
    alias: '墨言',
    department: '商务运营部',
    versions: [
      {
        version: 'v1.0.0',
        status: 'published',
        traffic: 100,
        replicas: 2,
        config: {
          soul: { mbti: 'ESTJ', style: '简洁汇报', priority: '合规优先' },
          skills: ['合同起草', '版本管理', '文档归档'],
          tools: ['飞书API', '文档处理器', '版本追踪器'],
          model: 'claude-sonnet-4-7',
        },
        scaling: { minReplicas: 1, maxReplicas: 5, targetLoad: 65 },
      },
    ],
    capacity: { used: 2, max: 5 },
  },
  {
    id: 'av-swe-001',
    role: '软件工程师',
    alias: '码哥',
    department: '技术研发部',
    versions: [
      {
        version: 'v1.0.0',
        status: 'published',
        traffic: 100,
        replicas: 5,
        config: {
          soul: { mbti: 'INTP', style: '详细说明', priority: '效率优先' },
          skills: ['代码开发', '代码审查', '技术写作'],
          tools: ['git CLI', 'GitHub MCP', '代码分析器'],
          model: 'claude-sonnet-4-7',
        },
        scaling: { minReplicas: 2, maxReplicas: 10, targetLoad: 60 },
      },
    ],
    capacity: { used: 5, max: 10 },
  },
];

// 所有可选部门
export const DEPARTMENTS = [
  '综合管理部',
  '法务合规部',
  '商务运营部',
  '技术研发部',
  '商业智能部',
  '市场部',
  '人力资源部',
  '财务部',
  '产品部',
  '客服部',
];
