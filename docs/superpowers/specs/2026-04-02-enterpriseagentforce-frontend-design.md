# e-Agent-OS 运营中心前端设计规格书

> **项目**: e-Agent-OS (Enterprise Agent Employee) — 数字员工运营中心 (OpCenter)
> **版本**: v1.0
> **日期**: 2026-04-02
> **范围**: Phase 1 — 指挥大屏 + 员工卡片墙
> **技术栈**: Vue 3 + Vite + TypeScript + Tailwind CSS (或纯 CSS 变量)

---

## 一、产品愿景

e-Agent-OS OpCenter 是数字员工的"管控驾驶舱"——让运营人员像管理真实员工一样管理数字员工。

**设计哲学**: 档案感 / 暖调克制 / 纸质感 / 有温度的管控台

不同于冰冷的传统 B 端 SaaS，界面传递的是"这是我们团队的一员"的感觉——但底层依然是专业、精准、可审计的企业级工具。

---

## 二、视觉设计规范

### 2.1 色彩系统

```css
:root {
  /* 背景层 */
  --bg-page:       #F5F0E8;  /* 象牙白页面底 */
  --bg-card:       #FFFFFF;  /* 纯白卡片 */
  --bg-elevated:   #FAFAF8;  /* 微微凸起的区块 */

  /* 文字层 */
  --text-primary:   #2C2A28;  /* 深炭灰 主文字 */
  --text-secondary: #8A8279;  /* 暖灰 副文字 */
  --text-disabled:  #C4BFB8;  /* 禁用态 */

  /* 强调色 */
  --accent-primary:  #2D5B7B;  /* 深海蓝 主操作 */
  --accent-hover:    #3A7299;  /* 深海蓝悬停 */

  /* 员工状态色 */
  --status-sandbox:  #9A9490;  /* 雾灰 沙盒态 */
  --status-shadow:   #C47A3D;  /* 陶土橙 试用期 */
  --status-active:   #4A7C59;  /* 青苔绿 正式上岗 */
  --status-archived: #A8A29E;  /* 暗灰 退役 */

  /* 功能色 */
  --success: #4A7C59;
  --warning: #C47A3D;
  --danger:  #B84A3C;
  --info:    #2D5B7B;

  /* 边框与阴影 */
  --border-subtle:  rgba(44, 42, 40, 0.08);
  --shadow-card: 0 2px 8px rgba(44, 42, 40, 0.06), 0 1px 2px rgba(44, 42, 40, 0.04);
  --shadow-elevated: 0 4px 16px rgba(44, 42, 40, 0.1), 0 2px 4px rgba(44, 42, 40, 0.06);
}
```

### 2.2 字体系统

```css
/* 档案感：员工姓名、岗位、部门 */
--font-serif: 'Playfair Display', 'Source Serif 4', Georgia, serif;

/* 界面元素：数据、按钮、导航 */
--font-sans: 'DM Sans', 'Inter var', system-ui, sans-serif;

/* 等宽：数字指标、工号 */
--font-mono: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
```

**使用规则**:
- 员工花名 / 岗位名 / 部门名 → Serif
- 所有数据指标（Token数、任务数）→ Mono + 数字强调色
- 导航 / 按钮 / 标签 / 表单 → Sans-serif
- 正文字号 15px，行高 1.6
- 指标大字 32px，卡片标题 18px

### 2.3 间距与圆角

```css
--space-xs:  4px;
--space-sm:  8px;
--space-md:  16px;
--space-lg:  24px;
--space-xl:  32px;
--space-2xl: 48px;

--radius-sm:  6px;   /* 标签、小按钮 */
--radius-md:  10px;  /* 卡片 */
--radius-lg:  16px;  /* 模态框、大面板 */
```

### 2.4 阴影策略

不用重线框，用阴影建立层级感：
- 普通卡片: `--shadow-card`
- 悬停卡片: `--shadow-elevated` + `translateY(-2px)`
- 模态框: `0 20px 60px rgba(44, 42, 40, 0.2)`
- 侧边栏: `4px 0 20px rgba(44, 42, 40, 0.08)`

### 2.5 动效规范

- 页面切换: 淡入淡出 200ms ease-out
- 卡片悬停: `transform: translateY(-2px)`, 150ms ease
- 数字增长: 计数器动画 800ms ease-out
- 状态变化: 颜色渐变 300ms
- 侧边栏展开: 宽度动画 250ms cubic-bezier(0.4, 0, 0.2, 1)
- 禁止: 花哨的弹跳、过度旋转、分裂动画

---

## 三、页面结构

### 3.1 整体布局

```
┌──────────────────────────────────────────────────────┐
│  [e-Agent-OS Logo]  │  指挥大厅  │  工匠中心  │ 资产库  │ [User]│  ← 顶部导航栏 (56px)
├──────────┴───────────────────────────────────────────┤
│                                                      │
│              <路由页面内容>                            │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**路由设计**:
- `/` → 指挥大屏（Dashboard）
- `/employees` → 员工卡片墙（Gallery）
- `/employees/:id` → 员工详情页
- `/forge` → 工匠中心（向导创建）- Phase 2
- `/assets` → 资产库 - Phase 2

---

## 四、指挥大屏（Dashboard）

**路由**: `/`

### 4.1 顶部统计卡（Stats Row）

4 张等宽统计卡，间隔 16px：

| 指标 | 示例值 | 视觉处理 |
|------|--------|---------|
| 在线员工 | 12 | 大数字 + "正式上岗" 标注 |
| 本月Token消耗 | 2.4M | 数字用 accent-primary 色 |
| 本月完成任务 | 847 | 含环比箭头（绿↑ / 红↓） |
| 系统负载 | 68% | 进度条可视化 |

### 4.2 员工状态分布（Status Donut）

左半部分：SVG 环形图，内圈显示总数。
右半部分：状态图例。

```
        ┌──────┐
  环形图  │  28  │  ← 总数
         └──┬──┘
    Active ─── 9  ████████████░░░░  32%
   Shadow  ─── 2  ██░░░░░░░░░░░░░░  7%
  Sandbox  ─── 1  █░░░░░░░░░░░░░░░  4%
 Archived  ─── 3  ██░░░░░░░░░░░░░░  11%
   [未知]  ─── 13 █████████████░░░  46%
```

### 4.3 近7天Token消耗（柱状图）

纯 CSS 或轻量 Chart.js 柱状图，7根柱子，悬停显示具体数值。
Y 轴：Token 消耗量（K/M 格式）
配色：深海蓝渐变柱体

### 4.4 近7天任务完成趋势（折线图）

7天折线，悬停 tooltip。
配色：青苔绿线条

### 4.5 最近任务动态（Activity Feed）

实时时间轴，最大显示 10 条，超出后"查看更多"折叠。

每条格式：
```
● 李明阳 完成了「周报生成」任务     3分钟前
● 陈小红 试用期产出比对通过          18分钟前
● 系统   新员工「王五」入职（沙盒态）  1小时前
● 刘铁柱 任务执行失败，请检查日志     2小时前
```

---

## 五、员工卡片墙（Gallery）

**路由**: `/employees`

### 5.1 筛选栏（Filter Bar）

```
[搜索框]  [全部状态 ▾]  [全部部门 ▾]  [全部岗位 ▾]  [+ 新员工]
```

- 搜索: 按花名、工号模糊匹配
- 状态筛选: 全部 / 沙盒态 / 试用期 / 正式上岗 / 退役
- 部门筛选: 下拉选择
- 岗位筛选: 下拉选择
- 新员工按钮: 深海蓝实心按钮 → 跳转 `/forge`

### 5.2 员工卡片网格

响应式: 桌面 4列 / 平板 2列 / 手机 1列，卡片最小宽度 260px。

### 5.3 员工卡片组件

```
┌────────────────────────────────────┐
│  [头像 64px]                       │
│                                    │
│  李明阳                             │  ← Serif 22px, primary色
│  数据分析专员                        │  ← Sans 14px, secondary色
│  数智部 · 正式上岗                   │  ← 部门 · 状态灯+文字
│                                    │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐       │
│  │SQL │ │Py  │ │BI  │ │+2  │       │  ← 技能标签，最多显示3个
│  └────┘ └────┘ └────┘ └────┘       │
│                                    │
│  ██████████░░░░░░░░  负荷 52%      │  ← 进度条，颜色随负荷变化
│                                    │
│  本月 1.2M Token     任务 234件     │  ← Mono字体数字
│                                    │
│  [查看详情]      [指派任务 →]       │  ← ghost按钮 + 实心按钮
└────────────────────────────────────┘
```

**状态灯样式**:
- `沙盒态`: 雾灰圆点，虚线边框卡片
- `试用期`: 陶土橙圆点，"试用期"角标贴片
- `正式上岗`: 青苔绿圆点，实线边框
- `退役`: 暗灰圆点，名字加删除线，卡片整体降低透明度

**卡片悬停**: 上移 2px + 阴影加深 + 边框轻微accent色

### 5.4 员工详情页

**路由**: `/employees/:id`

Tab 结构：

| Tab | 内容 |
|-----|------|
| 概览 | 头像 + 花名 + 工号 + 岗位 + 部门 + 入职日期 + 当前状态 + 技能标签 |
| 运营数据 | Token消耗趋势图 / 任务完成率 / 平均响应时长 |
| 历史任务 | 时间轴列表，最新20条，含任务名 + 状态 + 时长 |
| 配置 | 状态切换下拉 / 技能编辑 / 删除（仅退役态可删除）|

---

## 六、导航设计

### 6.1 顶部导航栏

- 高度: 56px
- 背景: `--bg-card`
- 底部细线: 1px `--border-subtle`
- Logo: 左侧，品牌名 "e-Agent-OS"
- 导航项: 指挥大厅 / 工匠中心 / 资产库
- 当前页面: 深海蓝下划线指示器
- 右侧: 用户头像 + 下拉菜单

### 6.2 侧边栏（可折叠）

收起时: 48px 宽，只显示图标
展开时: 220px 宽，图标+文字

```
┌────┐
│ 🏠 │  指挥大厅
│ ⚙️ │  工匠中心
│ 📦 │  资产库
│ 📊 │  效能度量（Phase 2）
│ 🔍 │  审计追踪（Phase 2）
└────┘
```

注：侧边栏导航与顶层导航共用，桌面端侧边栏展开，移动端收起。

---

## 七、API 接口（前端依赖）

Phase 1 前端需对接以下后端接口（后端尚未实现，前端先 mock）：

### 7.1 员工管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/employees` | GET | 获取员工列表，支持 ?status=&dept=&search= 筛选 |
| `/api/employees/:id` | GET | 获取员工详情 |
| `/api/employees` | POST | 创建员工（工匠中心） |
| `/api/employees/:id` | PATCH | 更新员工（状态/技能/信息） |
| `/api/employees/:id` | DELETE | 删除员工（退役态） |

### 7.2 运营数据

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/dashboard/stats` | GET | 全局统计：在线数/Token/任务/负载 |
| `/api/dashboard/status-dist` | GET | 各状态员工分布 |
| `/api/dashboard/token-trend` | GET | 近7天Token消耗 |
| `/api/dashboard/task-trend` | GET | 近7天任务完成趋势 |
| `/api/activity` | GET | 最近动态，?limit=10 |

### 7.3 数据模型

**Employee（员工）**:
```typescript
interface Employee {
  id: string;            // 系统生成工号 "EMP-20260402-001"
  name: string;          // 花名
  avatar: string;         // 头像 URL 或预设编号
  title: string;         // 岗位
  department: string;     // 部门
  status: 'sandbox' | 'shadow' | 'active' | 'archived';
  skills: string[];      // 技能标签列表
  workload: number;      // 负荷 0-100
  tokenUsage: number;    // 本月Token消耗
  taskCount: number;     // 本月完成任务数
  joinedAt: string;       // ISO 日期
  lastActiveAt: string;  // 最后活跃时间
}
```

**DashboardStats（全局统计）**:
```typescript
interface DashboardStats {
  onlineCount: number;
  totalTokenUsage: number;
  monthlyTasks: number;
  systemLoad: number;    // 0-100
}
```

---

## 八、技术实现规范

### 8.1 项目结构

```
frontend/
├── src/
│   ├── main.js
│   ├── App.vue
│   ├── router/
│   │   └── index.js
│   ├── views/
│   │   ├── DashboardView.vue
│   │   ├── EmployeesView.vue
│   │   └── EmployeeDetailView.vue
│   ├── components/
│   │   ├── layout/
│   │   │   ├── TopNav.vue
│   │   │   └── SideBar.vue
│   │   ├── dashboard/
│   │   │   ├── StatsCard.vue
│   │   │   ├── StatusDonut.vue
│   │   │   ├── TokenChart.vue
│   │   │   ├── TaskTrend.vue
│   │   │   └── ActivityFeed.vue
│   │   └── employee/
│   │       ├── EmployeeCard.vue
│   │       ├── EmployeeFilters.vue
│   │       └── EmployeeStatusBadge.vue
│   ├── composables/
│   │   ├── useEmployees.js
│   │   └── useDashboard.js
│   ├── services/
│   │   └── api.js           # Axios 封装，mock 开关
│   ├── stores/
│   │   └── employeeStore.js  # Pinia store
│   ├── style.css            # 全局 CSS 变量
│   └── mock/
│       └── data.js          # Mock 数据
├── index.html
├── vite.config.js
└── package.json
```

### 8.2 依赖

```json
{
  "dependencies": {
    "vue": "^3.5.30",
    "vue-router": "^4.5.0",
    "pinia": "^3.0.0",
    "axios": "^1.7.0",
    "chart.js": "^4.4.0"
  }
}
```

### 8.3 Mock 策略

在 `src/services/api.js` 中：
- 通过 `VITE_USE_MOCK=true` 环境变量切换
- Mock 数据使用 Faker.js 或手写 JSON
- Mock 数据应包含 15-20 个不同类型/部门的员工卡片数据
- 统计数字应合理（总员工 20+，在线 10+）

---

## 九、Phase 规划

| Phase | 内容 | 优先级 |
|-------|------|--------|
| Phase 1a | Dashboard 骨架 + 员工卡片墙（当前） | 高 |
| Phase 1b | 员工详情页 + 筛选搜索 | 高 |
| Phase 2 | 工匠中心（对话式向导） | 中 |
| Phase 2 | 资产库（知识/技能管理） | 中 |
| Phase 3 | 思维链追踪器（笔记本 UI） | 低 |
| Phase 3 | HITL 审批队列 | 低 |

---

## 十、验收标准

- [ ] Dashboard 4个统计卡数值正确显示
- [ ] 环形图正确反映各状态人数
- [ ] 员工卡片墙网格响应式（4/2/1列）
- [ ] 4种状态（沙盒/试用/上岗/退役）视觉区分明显
- [ ] 筛选搜索按花名/部门/状态生效
- [ ] 点击卡片跳转详情页，Tab切换正常
- [ ] Token 消耗柱状图显示7天数据
- [ ] 活动流时间轴按时间倒序
- [ ] 深浅色主题（dark mode）完整适配
- [ ] 页面切换无白屏，骨架屏/loading 状态处理
