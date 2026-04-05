# e-Agent-OS OpCenter 前端实现计划 (Phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 e-Agent-OS 数字员工运营中心 Phase 1 前端：指挥大屏 + 员工卡片墙 + 员工详情页，全部使用 mock 数据，不依赖后端。

**Architecture:** Vue 3 + Vite，单文件组件，CSS 变量承载设计系统，Pinia 状态管理，Vue Router 路由，Chart.js 图表，Axios 封装 API 层（mock 开关控制）。

**Tech Stack:** vue 3.5, vue-router 4.5, pinia 3.0, axios 1.7, chart.js 4.4

---

## 文件结构

```
frontend/src/
├── main.js                          # 挂载 App，注册 Router/Pinia
├── App.vue                          # 根组件，含 router-view
├── router/index.js                  # 路由配置
├── style.css                        # 全局 CSS 变量（设计系统）
├── mock/data.js                      # Mock 员工数据 + Dashboard 数据
├── services/api.js                   # Axios 实例 + mock 拦截器
├── stores/employeeStore.js           # Pinia store
├── composables/
│   ├── useEmployees.js              # 员工列表/筛选逻辑
│   └── useDashboard.js              # Dashboard 统计数据逻辑
├── components/
│   ├── layout/
│   │   ├── TopNav.vue               # 顶部导航栏（56px，含 Logo + 导航 + 用户）
│   │   └── SideBar.vue              # 可折叠侧边栏
│   ├── dashboard/
│   │   ├── StatsCard.vue            # 统计卡片（数字 + 标注 + 进度条）
│   │   ├── StatusDonut.vue          # SVG 环形图 + 状态图例
│   │   ├── TokenChart.vue            # Chart.js 柱状图（7天Token）
│   │   ├── TaskTrend.vue            # Chart.js 折线图（7天任务趋势）
│   │   └── ActivityFeed.vue         # 时间轴活动流
│   └── employee/
│       ├── EmployeeCard.vue          # 员工卡片（头像+姓名+状态+负荷+数据）
│       ├── EmployeeFilters.vue        # 筛选栏（搜索+状态下拉+部门+岗位）
│       └── EmployeeStatusBadge.vue    # 状态徽章（灯+文字+角标）
└── views/
    ├── DashboardView.vue            # 指挥大屏（/）
    ├── EmployeesView.vue             # 员工卡片墙（/employees）
    └── EmployeeDetailView.vue        # 员工详情（/employees/:id）
```

---

## 依赖安装

先在 frontend/ 下安装所有依赖：

- vue-router@4
- pinia@3
- axios@1
- chart.js@4
- @fontsource/playfair-display（档案感衬线字体）
- @fontsource/dm-sans（界面无衬线字体）
- @fontsource/jetbrains-mono（等宽数字字体）

```bash
cd frontend
npm install vue-router@4 pinia@3 axios@1 chart.js@4 @fontsource/playfair-display @fontsource/dm-sans @fontsource/jetbrains-mono
```

---

## 任务清单

---

### Task 1: 全局 CSS 设计系统

**Files:**
- Modify: `frontend/src/style.css`（完全重写）

- [ ] **Step 1: 重写 style.css**

覆盖原有全部内容，写入完整 CSS 变量体系：

```css
/* ============================================
   e-Agent-OS Design System
   ============================================ */

/* Google Fonts */
@import '@fontsource/playfair-display/400.css';
@import '@fontsource/dm-sans/400.css';
@import '@fontsource/dm-sans/500.css';
@import '@fontsource/dm-sans/600.css';
@import '@fontsource/jetbrains-mono/400.css';
@import '@fontsource/jetbrains-mono/500.css';

/* ---------- Design Tokens ---------- */
:root {
  /* Backgrounds */
  --bg-page:      #F5F0E8;
  --bg-card:      #FFFFFF;
  --bg-elevated:  #FAFAF8;

  /* Text */
  --text-primary:   #2C2A28;
  --text-secondary: #8A8279;
  --text-disabled:  #C4BFB8;

  /* Accent */
  --accent-primary: #2D5B7B;
  --accent-hover:   #3A7299;

  /* Status */
  --status-sandbox:  #9A9490;
  --status-shadow:   #C47A3D;
  --status-active:   #4A7C59;
  --status-archived: #A8A29E;

  /* Functional */
  --success: #4A7C59;
  --warning: #C47A3D;
  --danger:  #B84A3C;
  --info:    #2D5B7B;

  /* Borders & Shadows */
  --border-subtle: rgba(44, 42, 40, 0.08);
  --shadow-card: 0 2px 8px rgba(44, 42, 40, 0.06), 0 1px 2px rgba(44, 42, 40, 0.04);
  --shadow-elevated: 0 4px 16px rgba(44, 42, 40, 0.10), 0 2px 4px rgba(44, 42, 40, 0.06);
  --shadow-modal: 0 20px 60px rgba(44, 42, 40, 0.20);

  /* Spacing */
  --space-xs:  4px;
  --space-sm:  8px;
  --space-md:  16px;
  --space-lg:  24px;
  --space-xl:  32px;
  --space-2xl: 48px;

  /* Radius */
  --radius-sm:  6px;
  --radius-md:  10px;
  --radius-lg:  16px;

  /* Fonts */
  --font-serif: 'Playfair Display', 'Source Serif 4', Georgia, serif;
  --font-sans:  'DM Sans', system-ui, sans-serif;
  --font-mono:  'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
}

/* Dark Mode */
@media (prefers-color-scheme: dark) {
  :root {
    --bg-page:      #1A1917;
    --bg-card:      #242220;
    --bg-elevated:  #2E2C29;
    --text-primary:   #F0EDE6;
    --text-secondary: #9A9490;
    --text-disabled:  #5A5750;
    --accent-primary: #5A9EC4;
    --accent-hover:   #6FB3D9;
    --border-subtle: rgba(240, 237, 230, 0.08);
    --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.30), 0 1px 2px rgba(0, 0, 0, 0.20);
    --shadow-elevated: 0 4px 16px rgba(0, 0, 0, 0.40), 0 2px 4px rgba(0, 0, 0, 0.30);
  }
}

/* ---------- Base Styles ---------- */
*, *::before, *::after { box-sizing: border-box; }

body {
  margin: 0;
  font-family: var(--font-sans);
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-page);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Typography */
h1, h2, h3 { margin: 0; font-weight: 500; }
h1 { font-size: 32px; }
h2 { font-size: 22px; }
h3 { font-size: 18px; }
p  { margin: 0; }

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 150ms ease;
  border: none;
  text-decoration: none;
}

.btn-primary {
  background: var(--accent-primary);
  color: #fff;
}
.btn-primary:hover { background: var(--accent-hover); }

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}
.btn-ghost:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

/* Cards */
.card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: var(--space-lg);
  transition: transform 150ms ease, box-shadow 150ms ease;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-elevated);
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--border-subtle);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: var(--text-disabled); }
```

- [ ] **Step 2: 确认效果**

Run: `cd frontend && npm run dev`，打开浏览器，确认页面加载无报错，CSS 变量正常（背景是象牙白 `#F5F0E8`）。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/style.css
git commit -m "feat(frontend): implement design system CSS tokens"
```

---

### Task 2: Mock 数据

**Files:**
- Create: `frontend/src/mock/data.js`

- [ ] **Step 1: 创建 mock/data.js**

手写 18 个员工数据，覆盖所有部门和状态：

```javascript
// frontend/src/mock/data.js

export const MOCK_EMPLOYEES = [
  // 正式上岗
  {
    id: 'EMP-20260401-001',
    name: '李明阳',
    avatar: 'preset-1',
    title: '数据分析专员',
    department: '数智部',
    status: 'active',
    skills: ['SQL', 'Python', 'BI报表', 'A/B测试'],
    workload: 52,
    tokenUsage: 1_240_000,
    taskCount: 234,
    joinedAt: '2026-01-15T08:00:00Z',
    lastActiveAt: '2026-04-02T09:30:00Z',
    avgResponseMs: 3400,
    successRate: 0.94,
  },
  {
    id: 'EMP-20260401-002',
    name: '陈小红',
    avatar: 'preset-2',
    title: '客服运营专员',
    department: '客服部',
    status: 'active',
    skills: ['工单处理', '情感分析', '多语言', 'FAQ维护'],
    workload: 78,
    tokenUsage: 2_180_000,
    taskCount: 521,
    joinedAt: '2026-01-20T08:00:00Z',
    lastActiveAt: '2026-04-02T10:15:00Z',
    avgResponseMs: 2100,
    successRate: 0.97,
  },
  {
    id: 'EMP-20260401-003',
    name: '王海涛',
    avatar: 'preset-3',
    title: '后端开发工程师',
    department: '研发部',
    status: 'active',
    skills: ['Go', 'Kubernetes', 'PostgreSQL', 'Redis'],
    workload: 35,
    tokenUsage: 890_000,
    taskCount: 89,
    joinedAt: '2026-02-01T08:00:00Z',
    lastActiveAt: '2026-04-02T08:45:00Z',
    avgResponseMs: 5600,
    successRate: 0.91,
  },
  {
    id: 'EMP-20260401-004',
    name: '张晓敏',
    avatar: 'preset-4',
    title: 'HRBP 专员',
    department: '人力资源部',
    status: 'active',
    skills: ['员工关系', '数据统计', '制度解读'],
    workload: 61,
    tokenUsage: 560_000,
    taskCount: 143,
    joinedAt: '2026-02-10T08:00:00Z',
    lastActiveAt: '2026-04-01T17:30:00Z',
    avgResponseMs: 4200,
    successRate: 0.89,
  },
  {
    id: 'EMP-20260401-005',
    name: '刘铁柱',
    avatar: 'preset-5',
    title: '运维工程师',
    department: '基础设施部',
    status: 'active',
    skills: ['Shell', 'Docker', '监控告警', '灾备'],
    workload: 88,
    tokenUsage: 3_400_000,
    taskCount: 678,
    joinedAt: '2026-01-08T08:00:00Z',
    lastActiveAt: '2026-04-02T10:00:00Z',
    avgResponseMs: 1800,
    successRate: 0.99,
  },
  {
    id: 'EMP-20260401-006',
    name: '周文静',
    avatar: 'preset-6',
    title: '内容运营专员',
    department: '市场部',
    status: 'active',
    skills: ['文案撰写', 'SEO优化', '数据分析', '社媒运营'],
    workload: 44,
    tokenUsage: 720_000,
    taskCount: 167,
    joinedAt: '2026-02-15T08:00:00Z',
    lastActiveAt: '2026-04-02T09:00:00Z',
    avgResponseMs: 3800,
    successRate: 0.93,
  },
  // 试用期
  {
    id: 'EMP-20260401-007',
    name: '吴浩宇',
    avatar: 'preset-1',
    title: '算法工程师',
    department: '研发部',
    status: 'shadow',
    skills: ['机器学习', 'Python', 'R', '特征工程'],
    workload: 25,
    tokenUsage: 340_000,
    taskCount: 42,
    joinedAt: '2026-03-20T08:00:00Z',
    lastActiveAt: '2026-04-02T10:20:00Z',
    avgResponseMs: 8900,
    successRate: 0.76,
  },
  {
    id: 'EMP-20260401-008',
    name: '赵雪琴',
    avatar: 'preset-2',
    title: '财务分析师',
    department: '财务部',
    status: 'shadow',
    skills: ['财务报表', '预算编制', 'Python'],
    workload: 18,
    tokenUsage: 210_000,
    taskCount: 29,
    joinedAt: '2026-03-25T08:00:00Z',
    lastActiveAt: '2026-04-01T16:00:00Z',
    avgResponseMs: 7200,
    successRate: 0.82,
  },
  // 沙盒态
  {
    id: 'EMP-20260402-009',
    name: '孙建国',
    avatar: 'preset-3',
    title: '法务专员',
    department: '法务部',
    status: 'sandbox',
    skills: ['合同审查', '法规检索', '风险评估'],
    workload: 0,
    tokenUsage: 0,
    taskCount: 0,
    joinedAt: '2026-04-01T08:00:00Z',
    lastActiveAt: null,
    avgResponseMs: null,
    successRate: null,
  },
  // 退役
  {
    id: 'EMP-20260301-010',
    name: '钱多多',
    avatar: 'preset-4',
    title: '测试工程师',
    department: '研发部',
    status: 'archived',
    skills: ['自动化测试', 'Selenium', 'API测试'],
    workload: 0,
    tokenUsage: 4_200_000,
    taskCount: 1023,
    joinedAt: '2026-01-05T08:00:00Z',
    lastActiveAt: '2026-03-28T18:00:00Z',
    avgResponseMs: 2900,
    successRate: 0.95,
  },
  {
    id: 'EMP-20260315-011',
    name: '黄莉娜',
    avatar: 'preset-5',
    title: '行政专员',
    department: '行政部',
    status: 'archived',
    skills: ['日程管理', '会议纪要', '采购协调'],
    workload: 0,
    tokenUsage: 890_000,
    taskCount: 445,
    joinedAt: '2026-01-10T08:00:00Z',
    lastActiveAt: '2026-03-15T12:00:00Z',
    avgResponseMs: 3100,
    successRate: 0.88,
  },
  {
    id: 'EMP-20260401-012',
    name: '郑凯文',
    avatar: 'preset-6',
    title: '前端工程师',
    department: '研发部',
    status: 'active',
    skills: ['Vue', 'React', 'TypeScript', 'CSS'],
    workload: 55,
    tokenUsage: 980_000,
    taskCount: 198,
    joinedAt: '2026-02-20T08:00:00Z',
    lastActiveAt: '2026-04-02T09:45:00Z',
    avgResponseMs: 4100,
    successRate: 0.92,
  },
  {
    id: 'EMP-20260401-013',
    name: '林雅婷',
    avatar: 'preset-1',
    title: '产品经理',
    department: '产品部',
    status: 'active',
    skills: ['需求分析', 'PRD撰写', '数据分析', '用户调研'],
    workload: 67,
    tokenUsage: 1_540_000,
    taskCount: 312,
    joinedAt: '2026-01-25T08:00:00Z',
    lastActiveAt: '2026-04-02T10:30:00Z',
    avgResponseMs: 2600,
    successRate: 0.96,
  },
  {
    id: 'EMP-20260401-014',
    name: '徐志强',
    avatar: 'preset-2',
    title: '安全工程师',
    department: '基础设施部',
    status: 'active',
    skills: ['渗透测试', 'SIEM', '应急响应', '合规审计'],
    workload: 42,
    tokenUsage: 760_000,
    taskCount: 87,
    joinedAt: '2026-03-01T08:00:00Z',
    lastActiveAt: '2026-04-02T08:00:00Z',
    avgResponseMs: 6500,
    successRate: 0.98,
  },
  {
    id: 'EMP-20260402-015',
    name: '马玉龙',
    avatar: 'preset-3',
    title: '数据标注员',
    department: '数智部',
    status: 'active',
    skills: ['图像标注', '文本清洗', '质量审核'],
    workload: 91,
    tokenUsage: 4_100_000,
    taskCount: 1204,
    joinedAt: '2026-02-05T08:00:00Z',
    lastActiveAt: '2026-04-02T10:35:00Z',
    avgResponseMs: 1200,
    successRate: 0.99,
  },
  {
    id: 'EMP-20260402-016',
    name: '唐静怡',
    avatar: 'preset-4',
    title: '品牌设计师',
    department: '市场部',
    status: 'shadow',
    skills: ['品牌视觉', '海报设计', 'Illustrator'],
    workload: 12,
    tokenUsage: 95_000,
    taskCount: 14,
    joinedAt: '2026-04-01T08:00:00Z',
    lastActiveAt: '2026-04-02T09:00:00Z',
    avgResponseMs: 11000,
    successRate: 0.71,
  },
  {
    id: 'EMP-20260402-017',
    name: '董浩然',
    avatar: 'preset-5',
    title: '客户成功经理',
    department: '客服部',
    status: 'active',
    skills: ['客户培训', '健康度分析', '增值推荐'],
    workload: 58,
    tokenUsage: 1_120_000,
    taskCount: 267,
    joinedAt: '2026-02-08T08:00:00Z',
    lastActiveAt: '2026-04-02T10:10:00Z',
    avgResponseMs: 3300,
    successRate: 0.94,
  },
  {
    id: 'EMP-20260402-018',
    name: '白小丽',
    avatar: 'preset-6',
    title: '合规专员',
    department: '法务部',
    status: 'sandbox',
    skills: ['合规检查', '报告撰写', '政策解读'],
    workload: 0,
    tokenUsage: 0,
    taskCount: 0,
    joinedAt: '2026-04-02T08:00:00Z',
    lastActiveAt: null,
    avgResponseMs: null,
    successRate: null,
  },
];

// Dashboard 全局统计
export const MOCK_DASHBOARD_STATS = {
  onlineCount: MOCK_EMPLOYEES.filter(e => e.status === 'active').length, // 10
  totalTokenUsage: MOCK_EMPLOYEES.reduce((sum, e) => sum + e.tokenUsage, 0),
  monthlyTasks: MOCK_EMPLOYEES.reduce((sum, e) => sum + e.taskCount, 0),
  systemLoad: 68,
  taskTrend: {
    change: 12.4,  // 环比 +12.4%
    direction: 'up', // 'up' | 'down'
  },
};

// 状态分布
export const MOCK_STATUS_DIST = [
  { status: 'active',   label: '正式上岗', count: 10, color: '#4A7C59' },
  { status: 'shadow',   label: '试用期',   count: 4,  color: '#C47A3D' },
  { status: 'sandbox',  label: '沙盒态',   count: 2,  color: '#9A9490' },
  { status: 'archived', label: '退役',     count: 2,  color: '#A8A29E' },
];

// 近7天 Token 消耗
export const MOCK_TOKEN_TREND = [
  { date: '03-27', value: 1_820_000 },
  { date: '03-28', value: 2_340_000 },
  { date: '03-29', value: 1_560_000 },
  { date: '03-30', value: 980_000 },
  { date: '03-31', value: 3_120_000 },
  { date: '04-01', value: 2_780_000 },
  { date: '04-02', value: 1_640_000 },
];

// 近7天任务完成趋势
export const MOCK_TASK_TREND = [
  { date: '03-27', value: 145 },
  { date: '03-28', value: 198 },
  { date: '03-29', value: 112 },
  { date: '03-30', value: 87 },
  { date: '03-31', value: 234 },
  { date: '04-01', value: 201 },
  { date: '04-02', value: 118 },
];

// 最近活动流
export const MOCK_ACTIVITY = [
  {
    id: 'act-001',
    type: 'task_completed',
    employeeId: 'EMP-20260401-015',
    employeeName: '马玉龙',
    content: '完成了「月度数据标注质量报告」',
    timestamp: new Date(Date.now() - 3 * 60_000).toISOString(),
  },
  {
    id: 'act-002',
    type: 'shadow_pass',
    employeeId: 'EMP-20260401-002',
    employeeName: '陈小红',
    content: '试用期产出比对通过',
    timestamp: new Date(Date.now() - 18 * 60_000).toISOString(),
  },
  {
    id: 'act-003',
    type: 'employee_joined',
    employeeName: '孙建国',
    content: '新员工入职（沙盒态）',
    timestamp: new Date(Date.now() - 60 * 60_000).toISOString(),
  },
  {
    id: 'act-004',
    type: 'task_failed',
    employeeId: 'EMP-20260401-005',
    employeeName: '刘铁柱',
    content: '任务执行失败，请检查日志',
    timestamp: new Date(Date.now() - 2 * 60 * 60_000).toISOString(),
  },
  {
    id: 'act-005',
    type: 'task_completed',
    employeeId: 'EMP-20260401-013',
    employeeName: '林雅婷',
    content: '完成了「用户调研报告 v2.3」',
    timestamp: new Date(Date.now() - 3 * 60 * 60_000).toISOString(),
  },
  {
    id: 'act-006',
    type: 'task_completed',
    employeeId: 'EMP-20260401-007',
    employeeName: '吴浩宇',
    content: '完成了「推荐算法准确性验证」',
    timestamp: new Date(Date.now() - 5 * 60 * 60_000).toISOString(),
  },
  {
    id: 'act-007',
    type: 'status_changed',
    employeeId: 'EMP-20260402-016',
    employeeName: '唐静怡',
    content: '状态变更为「试用期」',
    timestamp: new Date(Date.now() - 8 * 60 * 60_000).toISOString(),
  },
  {
    id: 'act-008',
    type: 'task_completed',
    employeeId: 'EMP-20260401-012',
    employeeName: '郑凯文',
    content: '完成了「前端组件库升级评估」',
    timestamp: new Date(Date.now() - 12 * 60 * 60_000).toISOString(),
  },
];

// 预设头像 SVG（6种几何图形风格）
export const PRESET_AVATARS = {
  'preset-1': `<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
    <rect width="64" height="64" rx="32" fill="#E8D5C4"/>
    <circle cx="32" cy="24" r="12" fill="#8B7355"/>
    <path d="M12 56c0-11 9-20 20-20s20 9 20 20" fill="#8B7355"/>
  </svg>`,
  'preset-2': `<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
    <rect width="64" height="64" rx="32" fill="#D4E8D4"/>
    <circle cx="32" cy="24" r="12" fill="#4A7C59"/>
    <path d="M12 56c0-11 9-20 20-20s20 9 20 20" fill="#4A7C59"/>
  </svg>`,
  'preset-3': `<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
    <rect width="64" height="64" rx="32" fill="#D4DDE8"/>
    <circle cx="32" cy="24" r="12" fill="#2D5B7B"/>
    <path d="M12 56c0-11 9-20 20-20s20 9 20 20" fill="#2D5B7B"/>
  </svg>`,
  'preset-4': `<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
    <rect width="64" height="64" rx="32" fill="#E8DCD4"/>
    <circle cx="32" cy="24" r="12" fill="#C47A3D"/>
    <path d="M12 56c0-11 9-20 20-20s20 9 20 20" fill="#C47A3D"/>
  </svg>`,
  'preset-5': `<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
    <rect width="64" height="64" rx="32" fill="#E4D4E8"/>
    <circle cx="32" cy="24" r="12" fill="#7B5BA0"/>
    <path d="M12 56c0-11 9-20 20-20s20 9 20 20" fill="#7B5BA0"/>
  </svg>`,
  'preset-6': `<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
    <rect width="64" height="64" rx="32" fill="#D4E4E8"/>
    <circle cx="32" cy="24" r="12" fill="#5A8A9E"/>
    <path d="M12 56c0-11 9-20 20-20s20 9 20 20" fill="#5A8A9E"/>
  </svg>`,
};
```

- [ ] **Step 2: 确认数据合理性**

数据覆盖：18个员工，10个 active、4个 shadow、2个 sandbox、2个 archived。部门分布合理。Commit。

```bash
git add frontend/src/mock/data.js
git commit -m "feat(frontend): add mock data for 18 employees and dashboard"
```

---

### Task 3: 路由和入口

**Files:**
- Modify: `frontend/src/main.js`
- Create: `frontend/src/router/index.js`

- [ ] **Step 1: 创建 router/index.js**

```javascript
// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router';
import DashboardView from '../views/DashboardView.vue';
import EmployeesView from '../views/EmployeesView.vue';
import EmployeeDetailView from '../views/EmployeeDetailView.vue';

const routes = [
  { path: '/', name: 'dashboard', component: DashboardView },
  { path: '/employees', name: 'employees', component: EmployeesView },
  { path: '/employees/:id', name: 'employee-detail', component: EmployeeDetailView },
  // Phase 2 placeholder routes
  { path: '/forge', redirect: '/employees' },
  { path: '/assets', redirect: '/employees' },
];

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});
```

- [ ] **Step 2: 更新 main.js**

```javascript
// frontend/src/main.js
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import router from './router/index.js';
import './style.css';
import App from './App.vue';

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');
```

- [ ] **Step 3: 更新 App.vue**

```vue
<!-- frontend/src/App.vue -->
<script setup>
import TopNav from './components/layout/TopNav.vue';
</script>

<template>
  <TopNav />
  <main>
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </main>
</template>

<style scoped>
main {
  padding-top: 56px; /* height of TopNav */
  min-height: 100vh;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 200ms ease-out;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/main.js frontend/src/router/index.js frontend/src/App.vue
git commit -m "feat(frontend): set up Vue Router, Pinia, and App shell"
```

---

### Task 4: API 服务层（mock 拦截）

**Files:**
- Create: `frontend/src/services/api.js`

- [ ] **Step 1: 创建 API 服务**

```javascript
// frontend/src/services/api.js
import axios from 'axios';
import {
  MOCK_EMPLOYEES,
  MOCK_DASHBOARD_STATS,
  MOCK_STATUS_DIST,
  MOCK_TOKEN_TREND,
  MOCK_TASK_TREND,
  MOCK_ACTIVITY,
} from '../mock/data.js';

const USE_MOCK = true; // 切换为 false 对接真实后端

const api = axios.create({
  baseURL: '/api',
  timeout: 5000,
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
  return Promise.resolve({
    data: MOCK_ACTIVITY.slice(0, limit),
  });
}

// ---- Public API Functions ----

export const employeeApi = {
  list: (params) => (USE_MOCK ? mockGetEmployees(params) : api.get('/employees', { params })),
  get: (id) => (USE_MOCK ? mockGetEmployee(id) : api.get(`/employees/${id}`)),
};

export const dashboardApi = {
  stats: () => (USE_MOCK ? mockGetDashboardStats() : api.get('/dashboard/stats')),
  statusDist: () => (USE_MOCK ? mockGetStatusDist() : api.get('/dashboard/status-dist')),
  tokenTrend: () => (USE_MOCK ? mockGetTokenTrend() : api.get('/dashboard/token-trend')),
  taskTrend: () => (USE_MOCK ? mockGetTaskTrend() : api.get('/dashboard/task-trend')),
  activity: (params) => (USE_MOCK ? mockGetActivity(params) : api.get('/activity', { params })),
};

export default api;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/api.js
git commit -m "feat(frontend): implement API service layer with mock toggle"
```

---

### Task 5: Pinia Store

**Files:**
- Create: `frontend/src/stores/employeeStore.js`

- [ ] **Step 1: 创建 Pinia Store**

```javascript
// frontend/src/stores/employeeStore.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { employeeApi } from '../services/api.js';

export const useEmployeeStore = defineStore('employees', () => {
  const employees = ref([]);
  const loading = ref(false);
  const error = ref(null);

  // Filters
  const filterStatus = ref('');
  const filterDepartment = ref('');
  const filterTitle = ref('');
  const filterSearch = ref('');

  const filteredEmployees = computed(() => {
    let result = employees.value;
    if (filterStatus.value) result = result.filter(e => e.status === filterStatus.value);
    if (filterDepartment.value) result = result.filter(e => e.department === filterDepartment.value);
    if (filterTitle.value) result = result.filter(e => e.title === filterTitle.value);
    if (filterSearch.value) {
      const q = filterSearch.value.toLowerCase();
      result = result.filter(
        e =>
          e.name.toLowerCase().includes(q) ||
          e.id.toLowerCase().includes(q) ||
          e.title.toLowerCase().includes(q),
      );
    }
    return result;
  });

  const departments = computed(() => [...new Set(employees.value.map(e => e.department))]);
  const titles = computed(() => [...new Set(employees.value.map(e => e.title))]);

  async function fetchEmployees() {
    loading.value = true;
    error.value = null;
    try {
      const res = await employeeApi.list();
      employees.value = res.data;
    } catch (e) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  }

  function getEmployee(id) {
    return employees.value.find(e => e.id === id);
  }

  function resetFilters() {
    filterStatus.value = '';
    filterDepartment.value = '';
    filterTitle.value = '';
    filterSearch.value = '';
  }

  return {
    employees,
    filteredEmployees,
    loading,
    error,
    filterStatus,
    filterDepartment,
    filterTitle,
    filterSearch,
    departments,
    titles,
    fetchEmployees,
    getEmployee,
    resetFilters,
  };
});
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/employeeStore.js
git commit -m "feat(frontend): add Pinia employee store"
```

---

### Task 6: Composable — useDashboard

**Files:**
- Create: `frontend/src/composables/useDashboard.js`

- [ ] **Step 1: 创建 useDashboard.js**

```javascript
// frontend/src/composables/useDashboard.js
import { ref } from 'vue';
import { dashboardApi } from '../services/api.js';

export function useDashboard() {
  const stats = ref(null);
  const statusDist = ref([]);
  const tokenTrend = ref([]);
  const taskTrend = ref([]);
  const activity = ref([]);
  const loading = ref(false);
  const error = ref(null);

  async function fetchAll() {
    loading.value = true;
    error.value = null;
    try {
      const [statsRes, distRes, tokenRes, taskRes, actRes] = await Promise.all([
        dashboardApi.stats(),
        dashboardApi.statusDist(),
        dashboardApi.tokenTrend(),
        dashboardApi.taskTrend(),
        dashboardApi.activity({ limit: 10 }),
      ]);
      stats.value = statsRes.data;
      statusDist.value = distRes.data;
      tokenTrend.value = tokenRes.data;
      taskTrend.value = taskRes.data;
      activity.value = actRes.data;
    } catch (e) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  }

  return { stats, statusDist, tokenTrend, taskTrend, activity, loading, error, fetchAll };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/composables/useDashboard.js
git commit -m "feat(frontend): add useDashboard composable"
```

---

### Task 7: 布局组件 — TopNav

**Files:**
- Create: `frontend/src/components/layout/TopNav.vue`

- [ ] **Step 1: 创建 TopNav.vue**

```vue
<!-- frontend/src/components/layout/TopNav.vue -->
<script setup>
import { ref } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const isCollapsed = ref(false);

const navItems = [
  { label: '指挥大厅', path: '/', icon: 'grid' },
  { label: '工匠中心', path: '/forge', icon: 'plus-circle' },
  { label: '资产库', path: '/assets', icon: 'archive' },
];

function isActive(path) {
  return route.path === path;
}
</script>

<template>
  <header class="topnav">
    <div class="topnav-left">
      <div class="logo">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="8" r="4" fill="currentColor"/>
          <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <span class="logo-text">e-Agent-OS</span>
      </div>
    </div>

    <nav class="topnav-center">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
      >
        {{ item.label }}
      </router-link>
    </nav>

    <div class="topnav-right">
      <div class="user-avatar">
        <svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
          <rect width="32" height="32" rx="16" fill="var(--accent-primary)"/>
          <circle cx="16" cy="12" r="5" fill="white"/>
          <path d="M6 28c0-5.5 4.5-10 10-10s10 4.5 10 10" fill="white"/>
        </svg>
      </div>
    </div>
  </header>
</template>

<style scoped>
.topnav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-lg);
  z-index: 100;
}

.topnav-left { display: flex; align-items: center; min-width: 180px; }

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--accent-primary);
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 500;
  letter-spacing: -0.3px;
}

.topnav-center {
  display: flex;
  align-items: center;
  gap: var(--space-xl);
}

.nav-item {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  padding-bottom: 2px;
  border-bottom: 2px solid transparent;
  transition: color 150ms ease, border-color 150ms ease;
}
.nav-item:hover { color: var(--text-primary); }
.nav-item.active {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
}

.topnav-right { display: flex; align-items: center; min-width: 180px; justify-content: flex-end; }

.user-avatar svg { width: 32px; height: 32px; display: block; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/layout/TopNav.vue
git commit -m "feat(frontend): add TopNav layout component"
```

---

### Task 8: 员工状态徽章组件

**Files:**
- Create: `frontend/src/components/employee/EmployeeStatusBadge.vue`

- [ ] **Step 1: 创建 EmployeeStatusBadge.vue**

```vue
<!-- frontend/src/components/employee/EmployeeStatusBadge.vue -->
<script setup>
const props = defineProps({
  status: {
    type: String,
    required: true,
    // 'sandbox' | 'shadow' | 'active' | 'archived'
  },
  size: { type: String, default: 'md' }, // 'sm' | 'md'
});

const STATUS_CONFIG = {
  sandbox:  { label: '沙盒态',  color: 'var(--status-sandbox)',  badge: false },
  shadow:   { label: '试用期',  color: 'var(--status-shadow)',  badge: true  },
  active:   { label: '正式上岗', color: 'var(--status-active)',  badge: false },
  archived: { label: '退役',    color: 'var(--status-archived)', badge: false },
};

const config = $computed(() => STATUS_CONFIG[props.status] ?? STATUS_CONFIG.sandbox);
</script>

<template>
  <span class="status-badge" :class="[`size-${size}`, { 'has-badge': config.badge }]">
    <span class="dot" :style="{ background: config.color }"></span>
    <span class="label" :style="{ color: config.color }">{{ config.label }}</span>
    <span v-if="config.badge" class="badge-tag" :style="{ background: config.color }">试</span>
  </span>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.label { font-size: 13px; font-weight: 500; }
.size-sm .label { font-size: 12px; }

.badge-tag {
  font-size: 10px;
  font-weight: 600;
  color: white;
  padding: 1px 5px;
  border-radius: 3px;
  letter-spacing: 0.5px;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/employee/EmployeeStatusBadge.vue
git commit -m "feat(frontend): add EmployeeStatusBadge component"
```

---

### Task 9: 员工卡片组件

**Files:**
- Create: `frontend/src/components/employee/EmployeeCard.vue`

- [ ] **Step 1: 创建 EmployeeCard.vue**

```vue
<!-- frontend/src/components/employee/EmployeeCard.vue -->
<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { PRESET_AVATARS } from '../../mock/data.js';
import EmployeeStatusBadge from './EmployeeStatusBadge.vue';

const props = defineProps({
  employee: { type: Object, required: true },
});

const router = useRouter();

const avatarSvg = computed(() => PRESET_AVATARS[props.employee.avatar] ?? PRESET_AVATARS['preset-1']);

const visibleSkills = computed(() => props.employee.skills.slice(0, 3));
const extraSkillCount = computed(() => Math.max(0, props.employee.skills.length - 3));

const workloadColor = computed(() => {
  const w = props.employee.workload;
  if (w >= 80) return 'var(--danger)';
  if (w >= 60) return 'var(--warning)';
  return 'var(--success)';
});

const workloadWidth = computed(() => `${Math.min(100, props.employee.workload)}%`);

function formatToken(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

function goDetail() {
  router.push({ name: 'employee-detail', params: { id: props.employee.id } });
}
</script>

<template>
  <article
    class="employee-card"
    :class="`status-${employee.status}`"
    @click="goDetail"
    role="button"
    tabindex="0"
    @keydown.enter="goDetail"
  >
    <!-- Avatar -->
    <div class="card-avatar" v-html="avatarSvg"></div>

    <!-- Identity -->
    <h3 class="card-name">{{ employee.name }}</h3>
    <p class="card-title">{{ employee.title }}</p>
    <p class="card-dept">
      {{ employee.department }}
      <EmployeeStatusBadge :status="employee.status" size="sm" />
    </p>

    <!-- Skills -->
    <div class="card-skills" v-if="visibleSkills.length">
      <span v-for="skill in visibleSkills" :key="skill" class="skill-tag">{{ skill }}</span>
      <span v-if="extraSkillCount > 0" class="skill-tag extra">+{{ extraSkillCount }}</span>
    </div>

    <!-- Workload Bar -->
    <div class="workload-row" v-if="employee.status !== 'sandbox' && employee.status !== 'archived'">
      <span class="workload-label">负荷</span>
      <div class="workload-track">
        <div class="workload-fill" :style="{ width: workloadWidth, background: workloadColor }"></div>
      </div>
      <span class="workload-pct" :style="{ color: workloadColor }">{{ employee.workload }}%</span>
    </div>

    <!-- Stats -->
    <div class="card-stats">
      <div class="stat">
        <span class="stat-val">{{ formatToken(employee.tokenUsage) }}</span>
        <span class="stat-key">Token</span>
      </div>
      <div class="stat">
        <span class="stat-val">{{ employee.taskCount }}</span>
        <span class="stat-key">任务</span>
      </div>
    </div>

    <!-- Actions -->
    <div class="card-actions">
      <button class="btn btn-ghost btn-sm" @click.stop="goDetail">查看详情</button>
      <button class="btn btn-primary btn-sm" @click.stop>指派任务 →</button>
    </div>
  </article>
</template>

<style scoped>
.employee-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: var(--space-lg);
  cursor: pointer;
  transition: transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease;
  border: 1px solid transparent;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  outline: none;
}
.employee-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-elevated);
  border-color: var(--accent-primary);
}
.employee-card:focus-visible {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(45, 91, 123, 0.2);
}

/* Status variants */
.status-sandbox {
  border-style: dashed;
  border-color: var(--status-sandbox);
  opacity: 0.75;
}
.status-archived .card-name {
  text-decoration: line-through;
  color: var(--text-secondary);
}
.status-archived { opacity: 0.6; }

/* Avatar */
.card-avatar { width: 64px; height: 64px; }
.card-avatar :deep(svg) { width: 64px; height: 64px; border-radius: 50%; }

/* Identity */
.card-name {
  font-family: var(--font-serif);
  font-size: 20px;
  font-weight: 400;
  color: var(--text-primary);
  margin-top: var(--space-xs);
}
.card-title {
  font-size: 14px;
  color: var(--text-secondary);
}
.card-dept {
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

/* Skills */
.card-skills {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
  margin-top: var(--space-xs);
}
.skill-tag {
  font-size: 12px;
  padding: 2px 8px;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}
.skill-tag.extra { color: var(--accent-primary); }

/* Workload */
.workload-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-top: var(--space-sm);
}
.workload-label { font-size: 12px; color: var(--text-secondary); min-width: 24px; }
.workload-track {
  flex: 1;
  height: 4px;
  background: var(--bg-elevated);
  border-radius: 2px;
  overflow: hidden;
}
.workload-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 600ms ease;
}
.workload-pct { font-size: 12px; font-family: var(--font-mono); min-width: 32px; text-align: right; }

/* Stats */
.card-stats {
  display: flex;
  gap: var(--space-lg);
  padding: var(--space-sm) 0;
  border-top: 1px solid var(--border-subtle);
  margin-top: var(--space-xs);
}
.stat { display: flex; flex-direction: column; gap: 2px; }
.stat-val {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 500;
  color: var(--accent-primary);
}
.stat-key { font-size: 12px; color: var(--text-secondary); }

/* Actions */
.card-actions {
  display: flex;
  gap: var(--space-sm);
  margin-top: var(--space-xs);
}
.btn-sm { font-size: 13px; padding: 6px 12px; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/employee/EmployeeCard.vue
git commit -m "feat(frontend): add EmployeeCard component with status variants"
```

---

### Task 10: 筛选栏组件

**Files:**
- Create: `frontend/src/components/employee/EmployeeFilters.vue`

- [ ] **Step 1: 创建 EmployeeFilters.vue**

```vue
<!-- frontend/src/components/employee/EmployeeFilters.vue -->
<script setup>
import { useEmployeeStore } from '../../stores/employeeStore.js';

const store = useEmployeeStore();

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '正式上岗' },
  { value: 'shadow', label: '试用期' },
  { value: 'sandbox', label: '沙盒态' },
  { value: 'archived', label: '退役' },
];
</script>

<template>
  <div class="filters">
    <div class="search-wrap">
      <svg class="search-icon" viewBox="0 0 20 20" fill="none">
        <circle cx="9" cy="9" r="6" stroke="currentColor" stroke-width="1.5"/>
        <path d="M14 14l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <input
        v-model="store.filterSearch"
        class="search-input"
        type="text"
        placeholder="搜索花名、工号、岗位…"
      />
    </div>

    <select v-model="store.filterStatus" class="filter-select">
      <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>

    <select v-model="store.filterDepartment" class="filter-select">
      <option value="">全部部门</option>
      <option v-for="dept in store.departments" :key="dept" :value="dept">{{ dept }}</option>
    </select>

    <select v-model="store.filterTitle" class="filter-select">
      <option value="">全部岗位</option>
      <option v-for="t in store.titles" :key="t" :value="t">{{ t }}</option>
    </select>

    <button class="btn btn-ghost" @click="store.resetFilters" v-if="store.filterSearch || store.filterStatus || store.filterDepartment || store.filterTitle">
      重置
    </button>

    <router-link to="/forge" class="btn btn-primary ml-auto">
      + 新员工
    </router-link>
  </div>
</template>

<style scoped>
.filters {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-wrap: wrap;
  padding: var(--space-lg);
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}

.search-wrap {
  position: relative;
  flex: 1;
  min-width: 200px;
}
.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: var(--text-secondary);
  pointer-events: none;
}
.search-input {
  width: 100%;
  padding: 8px 12px 8px 34px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-page);
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--text-primary);
  outline: none;
  transition: border-color 150ms;
}
.search-input:focus { border-color: var(--accent-primary); }
.search-input::placeholder { color: var(--text-disabled); }

.filter-select {
  padding: 8px 32px 8px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-page);
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--text-primary);
  cursor: pointer;
  outline: none;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M2 4l4 4 4-4' stroke='%238A8279' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  transition: border-color 150ms;
}
.filter-select:focus { border-color: var(--accent-primary); }

.ml-auto { margin-left: auto; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/employee/EmployeeFilters.vue
git commit -m "feat(frontend): add EmployeeFilters component"
```

---

### Task 11: Dashboard — 统计卡片

**Files:**
- Create: `frontend/src/components/dashboard/StatsCard.vue`

- [ ] **Step 1: 创建 StatsCard.vue**

```vue
<!-- frontend/src/components/dashboard/StatsCard.vue -->
<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  sub: { type: String, default: '' },
  trend: { type: Number, default: null },   // e.g. 12.4
  trendDir: { type: String, default: null }, // 'up' | 'down'
  type: { type: String, default: 'number' }, // 'number' | 'percent' | 'load'
  loadValue: { type: Number, default: null }, // 0-100, only for type='load'
});

function formatValue(type, value) {
  if (type === 'percent' || type === 'load') return `${value}%`;
  if (typeof value === 'number' && value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (typeof value === 'number' && value >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return String(value);
}

const trendColor = (dir) => dir === 'up' ? 'var(--success)' : 'var(--danger)';
const trendArrow = (dir) => dir === 'up' ? '↑' : '↓';
</script>

<template>
  <div class="stats-card card">
    <div class="stats-top">
      <span class="stats-label">{{ label }}</span>
      <span v-if="trend !== null" class="stats-trend" :style="{ color: trendColor(trendDir) }">
        {{ trendArrow(trendDir) }} {{ trend }}%
      </span>
    </div>

    <div class="stats-value">{{ formatValue(type, value) }}</div>

    <div v-if="sub" class="stats-sub">{{ sub }}</div>

    <!-- Load bar -->
    <div v-if="type === 'load'" class="load-track">
      <div
        class="load-fill"
        :style="{
          width: `${loadValue}%`,
          background: loadValue >= 80 ? 'var(--danger)' : loadValue >= 60 ? 'var(--warning)' : 'var(--success)'
        }"
      ></div>
    </div>
  </div>
</template>

<style scoped>
.stats-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}
.stats-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.stats-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.stats-trend { font-size: 13px; font-weight: 600; }
.stats-value {
  font-family: var(--font-mono);
  font-size: 32px;
  font-weight: 500;
  color: var(--accent-primary);
  line-height: 1;
}
.stats-sub {
  font-size: 13px;
  color: var(--text-secondary);
}
.load-track {
  height: 6px;
  background: var(--bg-elevated);
  border-radius: 3px;
  overflow: hidden;
  margin-top: var(--space-xs);
}
.load-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 800ms ease-out;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/dashboard/StatsCard.vue
git commit -m "feat(frontend): add StatsCard component"
```

---

### Task 12: Dashboard — 环形图 + 活动流

**Files:**
- Create: `frontend/src/components/dashboard/StatusDonut.vue`
- Create: `frontend/src/components/dashboard/ActivityFeed.vue`

- [ ] **Step 1: 创建 StatusDonut.vue（SVG 实现，无需 Chart.js）**

```vue
<!-- frontend/src/components/dashboard/StatusDonut.vue -->
<script setup>
import { computed } from 'vue';

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{ status, label, count, color }]
});

const total = computed(() => props.data.reduce((s, d) => s + d.count, 0));

// Compute SVG dasharray for donut segments
const segments = computed(() => {
  const circumference = 2 * Math.PI * 40; // r=40
  let offset = 0;
  return props.data.map(item => {
    const pct = total.value > 0 ? item.count / total.value : 0;
    const dash = pct * circumference;
    const seg = { ...item, dash, offset, circumference, pct };
    offset += dash;
    return seg;
  });
});

const cx = 60, cy = 60, r = 40;
</script>

<template>
  <div class="donut-wrap card">
    <div class="donut-svg-wrap">
      <!-- Donut -->
      <svg viewBox="0 0 120 120" class="donut-svg">
        <!-- Background ring -->
        <circle :cx="cx" :cy="cy" :r="r" fill="none" stroke="var(--border-subtle)" stroke-width="14"/>
        <!-- Segments -->
        <circle
          v-for="seg in segments"
          :key="seg.status"
          :cx="cx"
          :cy="cy"
          :r="r"
          fill="none"
          :stroke="seg.color"
          stroke-width="14"
          :stroke-dasharray="`${seg.dash} ${seg.circumference}`"
          :stroke-dashoffset="-seg.offset + seg.circumference * 0.25"
          stroke-linecap="butt"
          style="transition: stroke-dasharray 600ms ease"
        />
        <!-- Center text -->
        <text x="60" y="56" text-anchor="middle" class="donut-total">{{ total }}</text>
        <text x="60" y="70" text-anchor="middle" class="donut-sub">总员工</text>
      </svg>
    </div>

    <!-- Legend -->
    <div class="donut-legend">
      <div v-for="item in data" :key="item.status" class="legend-row">
        <span class="legend-dot" :style="{ background: item.color }"></span>
        <span class="legend-label">{{ item.label }}</span>
        <span class="legend-count">{{ item.count }}</span>
        <span class="legend-pct">{{ total > 0 ? Math.round(item.count / total * 100) : 0 }}%</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.donut-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-xl);
}
.donut-svg-wrap { flex-shrink: 0; }
.donut-svg { width: 120px; height: 120px; }
.donut-total {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 500;
  fill: var(--text-primary);
}
.donut-sub { font-size: 10px; fill: var(--text-secondary); }
.donut-legend { flex: 1; display: flex; flex-direction: column; gap: var(--space-sm); }
.legend-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.legend-label { font-size: 13px; color: var(--text-secondary); flex: 1; }
.legend-count {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  min-width: 24px;
  text-align: right;
}
.legend-pct { font-size: 12px; color: var(--text-secondary); min-width: 32px; text-align: right; }
</style>
```

- [ ] **Step 2: 创建 ActivityFeed.vue**

```vue
<!-- frontend/src/components/dashboard/ActivityFeed.vue -->
<script setup>
const props = defineProps({
  items: { type: Array, default: () => [] },
});

const TYPE_CONFIG = {
  task_completed:  { icon: '✓', color: 'var(--success)',  label: '完成' },
  task_failed:     { icon: '✗', color: 'var(--danger)',   label: '失败' },
  shadow_pass:     { icon: '★', color: 'var(--warning)',  label: '转正' },
  employee_joined: { icon: '↑', color: 'var(--info)',     label: '入职' },
  status_changed:  { icon: '⟳', color: 'var(--text-secondary)', label: '状态' },
};

function relativeTime(iso) {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return '刚刚';
  if (m < 60) return `${m}分钟前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}小时前`;
  return `${Math.floor(h / 24)}天前`;
}
</script>

<template>
  <div class="activity-feed card">
    <h3 class="feed-title">最近动态</h3>
    <ul class="feed-list">
      <li v-for="item in items" :key="item.id" class="feed-item">
        <span class="feed-icon" :style="{ color: TYPE_CONFIG[item.type]?.color ?? 'var(--text-secondary)' }">
          {{ TYPE_CONFIG[item.type]?.icon ?? '•' }}
        </span>
        <div class="feed-body">
          <span class="feed-name">{{ item.employeeName }}</span>
          <span class="feed-content">{{ item.content }}</span>
        </div>
        <span class="feed-time">{{ relativeTime(item.timestamp) }}</span>
      </li>
      <li v-if="!items.length" class="feed-empty">暂无动态</li>
    </ul>
  </div>
</template>

<style scoped>
.activity-feed { padding: var(--space-lg); }
.feed-title {
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 500;
  margin-bottom: var(--space-lg);
  color: var(--text-primary);
}
.feed-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-md); }
.feed-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md);
}
.feed-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--bg-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  margin-top: 2px;
}
.feed-body {
  flex: 1;
  font-size: 14px;
  line-height: 1.5;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.feed-name { font-weight: 500; color: var(--text-primary); }
.feed-content { color: var(--text-secondary); }
.feed-time { font-size: 12px; color: var(--text-disabled); white-space: nowrap; margin-top: 3px; }
.feed-empty { font-size: 14px; color: var(--text-disabled); text-align: center; padding: var(--space-xl); }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/StatusDonut.vue frontend/src/components/dashboard/ActivityFeed.vue
git commit -m "feat(frontend): add StatusDonut (SVG) and ActivityFeed components"
```

---

### Task 13: Dashboard — Chart.js 图表

**Files:**
- Create: `frontend/src/components/dashboard/TokenChart.vue`
- Create: `frontend/src/components/dashboard/TaskTrend.vue`

- [ ] **Step 1: 创建 TokenChart.vue（柱状图）**

```vue
<!-- frontend/src/components/dashboard/TokenChart.vue -->
<script setup>
import { ref, onMounted, watch } from 'vue';
import { Chart, BarController, BarElement, CategoryScale, LinearScale, Tooltip } from 'chart.js';

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip);

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{ date, value }]
});

const canvas = ref(null);
let chart = null;

function formatTick(v) {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return v;
}

function renderChart() {
  if (chart) chart.destroy();
  chart = new Chart(canvas.value, {
    type: 'bar',
    data: {
      labels: props.data.map(d => d.date),
      datasets: [{
        data: props.data.map(d => d.value),
        backgroundColor: 'rgba(45, 91, 123, 0.7)',
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${formatTick(ctx.raw)} Token`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: 'var(--text-secondary)', font: { size: 11 } },
        },
        y: {
          grid: { color: 'var(--border-subtle)' },
          ticks: {
            color: 'var(--text-secondary)',
            font: { family: 'JetBrains Mono', size: 11 },
            callback: (v) => formatTick(v),
          },
        },
      },
    },
  });
}

onMounted(renderChart);
watch(() => props.data, renderChart);
</script>

<template>
  <div class="chart-card card">
    <h3 class="chart-title">近7天 Token 消耗</h3>
    <div class="chart-wrap">
      <canvas ref="canvas"></canvas>
    </div>
  </div>
</template>

<style scoped>
.chart-card { padding: var(--space-lg); }
.chart-title {
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 500;
  margin-bottom: var(--space-lg);
  color: var(--text-primary);
}
.chart-wrap { height: 180px; position: relative; }
</style>
```

- [ ] **Step 2: 创建 TaskTrend.vue（折线图）**

```vue
<!-- frontend/src/components/dashboard/TaskTrend.vue -->
<script setup>
import { ref, onMounted, watch } from 'vue';
import { Chart, LineController, LineElement, PointElement, CategoryScale, LinearScale, Tooltip } from 'chart.js';

Chart.register(LineController, LineElement, PointElement, CategoryScale, LinearScale, Tooltip);

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{ date, value }]
});

const canvas = ref(null);
let chart = null;

function renderChart() {
  if (chart) chart.destroy();
  chart = new Chart(canvas.value, {
    type: 'line',
    data: {
      labels: props.data.map(d => d.date),
      datasets: [{
        data: props.data.map(d => d.value),
        borderColor: 'var(--status-active)',
        backgroundColor: 'rgba(74, 124, 89, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: 'var(--status-active)',
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => ` ${ctx.raw} 任务` } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: 'var(--text-secondary)', font: { size: 11 } } },
        y: {
          grid: { color: 'var(--border-subtle)' },
          ticks: { color: 'var(--text-secondary)', font: { family: 'JetBrains Mono', size: 11 } },
        },
      },
    },
  });
}

onMounted(renderChart);
watch(() => props.data, renderChart);
</script>

<template>
  <div class="chart-card card">
    <h3 class="chart-title">近7天任务完成趋势</h3>
    <div class="chart-wrap">
      <canvas ref="canvas"></canvas>
    </div>
  </div>
</template>

<style scoped>
.chart-card { padding: var(--space-lg); }
.chart-title {
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 500;
  margin-bottom: var(--space-lg);
  color: var(--text-primary);
}
.chart-wrap { height: 180px; position: relative; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/TokenChart.vue frontend/src/components/dashboard/TaskTrend.vue
git commit -m "feat(frontend): add TokenChart and TaskTrend with Chart.js"
```

---

### Task 14: Dashboard 视图

**Files:**
- Create: `frontend/src/views/DashboardView.vue`

- [ ] **Step 1: 创建 DashboardView.vue**

```vue
<!-- frontend/src/views/DashboardView.vue -->
<script setup>
import { onMounted } from 'vue';
import { useDashboard } from '../composables/useDashboard.js';
import StatsCard from '../components/dashboard/StatsCard.vue';
import StatusDonut from '../components/dashboard/StatusDonut.vue';
import TokenChart from '../components/dashboard/TokenChart.vue';
import TaskTrend from '../components/dashboard/TaskTrend.vue';
import ActivityFeed from '../components/dashboard/ActivityFeed.vue';

const { stats, statusDist, tokenTrend, taskTrend, activity, loading, error, fetchAll } = useDashboard();

onMounted(fetchAll);
</script>

<template>
  <div class="dashboard">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>加载中…</p>
    </div>

    <template v-else-if="stats">
      <!-- Stats Row -->
      <section class="stats-row">
        <StatsCard
          label="在线员工"
          :value="stats.onlineCount"
          sub="正式上岗"
          type="number"
        />
        <StatsCard
          label="本月 Token 消耗"
          :value="stats.totalTokenUsage"
          type="number"
        />
        <StatsCard
          label="本月完成任务"
          :value="stats.monthlyTasks"
          :trend="stats.taskTrend.change"
          :trend-dir="stats.taskTrend.direction"
          type="number"
        />
        <StatsCard
          label="系统负载"
          :value="stats.systemLoad"
          type="load"
          :load-value="stats.systemLoad"
        />
      </section>

      <!-- Charts Row -->
      <section class="charts-row">
        <StatusDonut :data="statusDist" />
        <div class="charts-pair">
          <TokenChart :data="tokenTrend" />
          <TaskTrend :data="taskTrend" />
        </div>
      </section>

      <!-- Activity -->
      <section class="activity-row">
        <ActivityFeed :items="activity" />
      </section>
    </template>

    <div v-else-if="error" class="error-state">
      <p>加载失败：{{ error }}</p>
      <button class="btn btn-primary" @click="fetchAll">重试</button>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
}
@media (max-width: 900px) { .stats-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 500px) { .stats-row { grid-template-columns: 1fr; } }

.charts-row {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: var(--space-md);
  align-items: start;
}
@media (max-width: 900px) { .charts-row { grid-template-columns: 1fr; } }

.charts-pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md);
}
@media (max-width: 700px) { .charts-pair { grid-template-columns: 1fr; } }

.loading-state, .error-state {
  text-align: center;
  padding: var(--space-2xl);
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}
.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/DashboardView.vue
git commit -m "feat(frontend): implement DashboardView with all components"
```

---

### Task 15: 员工卡片墙视图

**Files:**
- Create: `frontend/src/views/EmployeesView.vue`

- [ ] **Step 1: 创建 EmployeesView.vue**

```vue
<!-- frontend/src/views/EmployeesView.vue -->
<script setup>
import { onMounted } from 'vue';
import { useEmployeeStore } from '../stores/employeeStore.js';
import EmployeeCard from '../components/employee/EmployeeCard.vue';
import EmployeeFilters from '../components/employee/EmployeeFilters.vue';

const store = useEmployeeStore();
onMounted(() => store.fetchEmployees());
</script>

<template>
  <div class="employees-page">
    <div class="page-header">
      <h1 class="page-title">数字员工</h1>
      <p class="page-sub">{{ store.filteredEmployees.length }} 位员工</p>
    </div>

    <EmployeeFilters />

    <!-- Loading -->
    <div v-if="store.loading" class="loading-state">
      <div class="loading-spinner"></div>
    </div>

    <!-- Grid -->
    <div v-else-if="store.filteredEmployees.length" class="employee-grid">
      <EmployeeCard
        v-for="emp in store.filteredEmployees"
        :key="emp.id"
        :employee="emp"
      />
    </div>

    <!-- Empty -->
    <div v-else class="empty-state">
      <p>没有符合条件的员工</p>
      <button class="btn btn-ghost" @click="store.resetFilters">清除筛选</button>
    </div>
  </div>
</template>

<style scoped>
.employees-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.page-header {
  display: flex;
  align-items: baseline;
  gap: var(--space-md);
}
.page-title {
  font-family: var(--font-serif);
  font-size: 28px;
  color: var(--text-primary);
}
.page-sub { font-size: 14px; color: var(--text-secondary); }

.employee-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-md);
}

.loading-state, .empty-state {
  text-align: center;
  padding: var(--space-2xl);
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}
.loading-spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/EmployeesView.vue
git commit -m "feat(frontend): implement EmployeesView with gallery grid"
```

---

### Task 16: 员工详情页视图

**Files:**
- Create: `frontend/src/views/EmployeeDetailView.vue`

- [ ] **Step 1: 创建 EmployeeDetailView.vue**

```vue
<!-- frontend/src/views/EmployeeDetailView.vue -->
<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useEmployeeStore } from '../stores/employeeStore.js';
import { PRESET_AVATARS } from '../mock/data.js';
import EmployeeStatusBadge from '../components/employee/EmployeeStatusBadge.vue';

const route = useRoute();
const router = useRouter();
const store = useEmployeeStore();

const activeTab = ref('overview');

const employee = computed(() => store.getEmployee(route.params.id));
const avatarSvg = computed(() => employee.value ? (PRESET_AVATARS[employee.value.avatar] ?? PRESET_AVATARS['preset-1']) : '');

onMounted(() => {
  if (!store.employees.length) store.fetchEmployees();
});

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });
}
function formatToken(n) {
  if (!n) return '0';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}
function lastActive(iso) {
  if (!iso) return '从未活跃';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return '刚刚';
  if (m < 60) return `${m}分钟前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}小时前`;
  return `${Math.floor(h / 24)}天前`;
}
</script>

<template>
  <div class="detail-page" v-if="employee">
    <!-- Back -->
    <button class="back-btn btn btn-ghost" @click="router.push('/employees')">
      ← 返回列表
    </button>

    <!-- Profile Header -->
    <div class="profile-header card">
      <div class="profile-avatar" v-html="avatarSvg"></div>
      <div class="profile-info">
        <h1 class="profile-name">{{ employee.name }}</h1>
        <p class="profile-title">{{ employee.title }}</p>
        <p class="profile-dept">
          {{ employee.department }}
          <EmployeeStatusBadge :status="employee.status" />
        </p>
      </div>
      <div class="profile-meta">
        <div class="meta-item">
          <span class="meta-key">工号</span>
          <span class="meta-val">{{ employee.id }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-key">入职日期</span>
          <span class="meta-val">{{ formatDate(employee.joinedAt) }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-key">最后活跃</span>
          <span class="meta-val">{{ lastActive(employee.lastActiveAt) }}</span>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        v-for="tab in ['overview', 'stats', 'tasks', 'config']"
        :key="tab"
        class="tab-btn"
        :class="{ active: activeTab === tab }"
        @click="activeTab = tab"
      >
        {{ { overview: '概览', stats: '运营数据', tasks: '历史任务', config: '配置' }[tab] }}
      </button>
    </div>

    <!-- Tab: Overview -->
    <div v-if="activeTab === 'overview'" class="tab-content card">
      <h3>技能标签</h3>
      <div class="skills-list">
        <span v-for="s in employee.skills" :key="s" class="skill-tag">{{ s }}</span>
      </div>

      <h3 style="margin-top: var(--space-xl)">本月概况</h3>
      <div class="overview-stats">
        <div class="overview-stat">
          <span class="o-val">{{ formatToken(employee.tokenUsage) }}</span>
          <span class="o-key">Token 消耗</span>
        </div>
        <div class="overview-stat">
          <span class="o-val">{{ employee.taskCount }}</span>
          <span class="o-key">完成任务</span>
        </div>
        <div class="overview-stat">
          <span class="o-val">{{ employee.avgResponseMs ? `${(employee.avgResponseMs/1000).toFixed(1)}s` : '—' }}</span>
          <span class="o-key">平均响应</span>
        </div>
        <div class="overview-stat">
          <span class="o-val">{{ employee.successRate != null ? `${Math.round(employee.successRate * 100)}%` : '—' }}</span>
          <span class="o-key">成功率</span>
        </div>
      </div>
    </div>

    <!-- Tab: Stats (placeholder Chart.js area) -->
    <div v-if="activeTab === 'stats'" class="tab-content card">
      <p style="color: var(--text-secondary)">Token 消耗趋势图表（Phase 1b 实现）</p>
    </div>

    <!-- Tab: Tasks (placeholder) -->
    <div v-if="activeTab === 'tasks'" class="tab-content card">
      <p style="color: var(--text-secondary)">历史任务时间轴（Phase 1b 实现）</p>
    </div>

    <!-- Tab: Config -->
    <div v-if="activeTab === 'config'" class="tab-content card">
      <div class="config-row">
        <span>当前状态</span>
        <EmployeeStatusBadge :status="employee.status" />
      </div>
      <div class="config-row">
        <span>编辑技能</span>
        <button class="btn btn-ghost btn-sm">编辑</button>
      </div>
      <div class="config-row danger-zone" v-if="employee.status === 'archived'">
        <span>删除员工</span>
        <button class="btn btn-danger btn-sm">删除</button>
      </div>
    </div>
  </div>

  <!-- Not found -->
  <div v-else class="not-found">
    <p>未找到该员工</p>
    <button class="btn btn-primary" @click="router.push('/employees')">返回列表</button>
  </div>
</template>

<style scoped>
.detail-page {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.back-btn { align-self: flex-start; }

.profile-header {
  display: flex;
  align-items: center;
  gap: var(--space-xl);
  flex-wrap: wrap;
}
.profile-avatar { width: 80px; height: 80px; flex-shrink: 0; }
.profile-avatar :deep(svg) { width: 80px; height: 80px; border-radius: 50%; }
.profile-info { flex: 1; min-width: 200px; }
.profile-name {
  font-family: var(--font-serif);
  font-size: 26px;
  font-weight: 400;
  color: var(--text-primary);
}
.profile-title { font-size: 15px; color: var(--text-secondary); margin-top: 4px; }
.profile-dept { font-size: 14px; color: var(--text-secondary); margin-top: 4px; display: flex; align-items: center; gap: var(--space-sm); flex-wrap: wrap; }
.profile-meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}
.meta-item { display: flex; flex-direction: column; gap: 2px; }
.meta-key { font-size: 11px; color: var(--text-disabled); text-transform: uppercase; letter-spacing: 0.5px; }
.meta-val { font-family: var(--font-mono); font-size: 13px; color: var(--text-primary); }

.tabs {
  display: flex;
  gap: var(--space-sm);
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 0;
}
.tab-btn {
  padding: var(--space-sm) var(--space-md);
  border: none;
  background: none;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color 150ms, border-color 150ms;
}
.tab-btn:hover { color: var(--text-primary); }
.tab-btn.active { color: var(--accent-primary); border-bottom-color: var(--accent-primary); }

.tab-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}
.tab-content h3 {
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}

.skills-list { display: flex; flex-wrap: wrap; gap: var(--space-sm); }
.skill-tag {
  font-size: 13px;
  padding: 4px 10px;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}

.overview-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
}
@media (max-width: 600px) { .overview-stats { grid-template-columns: repeat(2, 1fr); } }
.overview-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-md);
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
}
.o-val {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 500;
  color: var(--accent-primary);
}
.o-key { font-size: 12px; color: var(--text-secondary); }

.config-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) 0;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 14px;
  color: var(--text-primary);
}
.danger-zone { color: var(--danger); }
.btn-danger { background: var(--danger); color: white; }
.btn-sm { font-size: 13px; padding: 6px 12px; }

.not-found {
  text-align: center;
  padding: var(--space-2xl);
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/EmployeeDetailView.vue
git commit -m "feat(frontend): implement EmployeeDetailView with tab navigation"
```

---

### Task 17: 最终验证 + index.html 标题

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: 更新 index.html title**

```html
<!-- frontend/index.html -->
<!-- 把 <title>frontend</title> 改为： -->
<title>e-Agent-OS 运营中心</title>
```

- [ ] **Step 2: 运行 dev server 验证**

```bash
cd frontend && npm run dev
```

验证清单（浏览器中检查）：
1. 首页 `/` 显示 4 张统计卡 + 环形图 + 2 个图表 + 活动流
2. 导航栏 Logo 正确显示 "e-Agent-OS"
3. 点击导航到 `/employees` 显示员工卡片墙（18 张卡片，响应式网格）
4. 点击卡片跳转 `/employees/:id` 显示详情页，4 个 Tab 切换正常
5. 筛选搜索功能可用
6. Dark mode 切换正常（浏览器 devtools 切换 prefers-color-scheme）

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat(frontend): update page title and finalize Phase 1"
```

---

## 自检清单（执行者填写）

- [ ] 所有 17 个任务完成
- [ ] `npm run dev` 无报错
- [ ] 4 种员工状态视觉区分明显
- [ ] 响应式网格（4/2/1列）正常
- [ ] 筛选搜索生效
- [ ] 图表正常渲染（柱状图 + 折线图）
- [ ] SVG 环形图正确
- [ ] Dark mode 配色正确
- [ ] 路由跳转正常（Dashboard → Gallery → Detail）
- [ ] `git log --oneline` 确认每次 commit 逻辑完整
