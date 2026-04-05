# Performance（绩效看板）设计方案

**状态**：已确认
**作者**：老郑 & Claude
**日期**：2026-04-03

---

## 一、设计原则

- 保持现有米白 (`#F9F8F6`) + Playfair Display + DM Sans + Morandi 色调
- 指标卡扁平化，单位去权化
- 所有 Avatar 以**岗位角色**为单位出现，不出现真实人名在前台

---

## 二、布局总览

```
┌─ Stats Row（4张扁平卡片）───────────────────────────────┐
│ [活跃 Avatar]  [任务完成]   [任务成功率]   [Token 效率] │
└────────────────────────────────────────────────────────┘

┌─ Middle Row（各 50%）─────────────────────────────────┐
│  状态环形图          │  近7天任务 & Token 消耗（双柱图） │
│  正式上岗 / 试用期    │  ████ 任务  ░░░░ Token         │
│  沙盒态 / 退役        │  左右双 Y 轴，无网格线            │
│  中心：总员工 N       │                                  │
└──────────────────────┴────────────────────────────────┘

┌─ Bottom Row（35% / 65%）──────────────────────────────┐
│  能力分布               │  最近动态                        │
│  ▓▓▓▓▓▓▓░░  73%       │  ● 小龙（数据分析师 -- 商业智能部）│
│  ▓▓░░░░░░░░  18%       │    完成了「月度报表」  3分钟前    │
│  ▓░░░░░░░░░   9%       │  ● 墨白（内容创作员 -- 市场部）  │
│  横向柱状图              │    失败「产品文案」  12分钟前      │
└────────────────────────┴────────────────────────────────┘
```

---

## 三、Stats Row — 4 张指标卡

### 3.1 卡片清单

| 顺序 | 标签 | 核心数字 | 单位 | 副文字 |
|------|------|---------|------|--------|
| 1 | 活跃 Avatar | N | 个 | "正式上岗" / "试用期" |
| 2 | 任务完成 | N,NNN | 个 | 环比变化 % |
| 3 | 任务成功率 | XX.X | % | 环比变化 % |
| 4 | Token 效率 | X.X | 任务/M | 环比变化 % |

### 3.2 样式规范

- **卡片高度**：扁平，padding `14px 18px 12px`
- **标签**：`10px`，`tracking-widest`，`text-disabled`，全大写
- **数字**：Playfair Display，`30px`，`text-primary`，无粗体
- **单位**：JetBrains Mono，`12px`，`text-disabled`，与数字基线对齐
- **副文字**：DM Sans，`11px`，`text-disabled`
- **间距**：`gap: 24px`，`border-radius: 10px`，`shadow-sm` + `ring-1 ring-black/5`

---

## 四、Middle Row — 图表区（各 50%）

### 4.1 左侧：状态环形图（复用）

- 4 色段：正式上岗 / 试用期 / 沙盒态 / 退役
- 中心：总员工数（大号衬线字）
- 下方"总员工"：`9px`，`text-disabled`
- 右侧 legend：岗位标签 + 数量 + 百分比

### 4.2 右侧：近7天任务 & Token 双柱图

- **类型**：同图双 Y 轴柱状图
- **Y 轴 1（左侧）**：任务数，陶土橙 `#D97757`
- **Y 轴 2（右侧）**：Token 消耗（单位 M），沙石灰 `#8E9AAF`
- **X 轴**：Mon–Sun，淡灰刻度文字，无网格线
- **数据源**：`tokenTrend` + 新增 Token 日消耗端点

---

## 五、Bottom Row — 能力分布 + 动态流（35% / 65%）

### 5.1 左侧（35%）：能力分布横向柱状图

- 展示各岗位类型的任务完成占比
- 每条：`岗位名（左侧对齐） + 百分比 + 横向柱条`
- 柱条颜色：陶土橙渐变，按占比高低递减明度
- 最多显示 6 个岗位，超出折叠

### 5.2 右侧（65%）：最近动态

- **Avatar 名字格式**：`艺名（岗位角色 -- 部门）`
  ```
    小龙
    数据分析师 -- 商业智能部
  ```
- **艺名**：Playfair Display，`font-semibold`，`text-base`，`text-primary`
- **岗位 -- 部门**：DM Sans，`text-xs`，`text-secondary`，下一行
- **失败任务**：用 `var(--danger)` 色高亮"失败"关键词
- 时间戳：`10px`，`text-disabled`，右对齐

---

## 六、数据层需求

### 6.1 新增 stats 字段

```js
{
  taskSuccessRate: number,    // 0–100，成功率%
  tokenEfficiency: number,    // 每 M Token 完成任务数
  taskTrend: {
    success: number[],        // 近7天每日成功任务数
    failed: number[]          // 近7天每日失败任务数
  },
  tokenDaily: number[],       // 近7天每日 Token 消耗（M）
  capabilityDist: [           // 能力分布
    { role: string, name: string, dept: string, pct: number }
  ]
}
```

### 6.2 API 端点

- `GET /api/dashboard/stats` → 新增 `taskSuccessRate`、`tokenEfficiency`
- `GET /api/dashboard/task-trend` → 返回 `{ success[], failed[] }` 双数组
- `GET /api/dashboard/token-daily` → 返回每日 Token 消耗
- `GET /api/dashboard/capability-dist` → 返回能力分布

---

## 七、组件清单

| 组件 | 路径 | 改动 |
|------|------|------|
| StatsCard | `components/dashboard/StatsCard.vue` | 指标项调整 |
| StatusDonut | `components/dashboard/StatusDonut.vue` | 复用，无需改动 |
| TaskChart（新建） | `components/dashboard/TaskChart.vue` | 双柱图，左右双 Y 轴 |
| ActivityFeed | `components/dashboard/ActivityFeed.vue` | 艺名格式改造 |
| CapabilityChart（新建） | `components/dashboard/CapabilityChart.vue` | 能力分布横向柱状图 |
| DashboardView | `views/DashboardView.vue` | 布局调整 |
| useDashboard | `composables/useDashboard.js` | 新增数据字段 |

---

## 八、实现优先级

1. 修改 `useDashboard.js` + 后端 API（数据层先行）
2. `TaskChart.vue`（双柱图，新建）
3. `CapabilityChart.vue`（能力分布，新建）
4. `ActivityFeed.vue`（艺名格式改造）
5. `StatsCard.vue`（指标卡调整）
6. `DashboardView.vue`（布局更新）
