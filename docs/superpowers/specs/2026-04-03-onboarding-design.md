# Onboarding（入职中心）设计方案

**状态**：已确认
**作者**：老郑 & Claude
**日期**：2026-04-03

---

## 一、设计原则

- 保持现有米白 (`#F9F8F6`) + Playfair Display + DM Sans + Morandi 色调
- Onboarding 的本质是**实例化**：将 Blueprint 版本变成可运行的 Avatar 实例
- Blueprint 版本之间**配置独立**：每个版本有各自的 SOUL、skills、tools、model
- Avatar 分身数**动态扩缩**，根据 workload 自动调节
- MVP 先用 mock 配置文件，后续迁移到数据库

---

## 二、核心对象模型

### 2.1 对象关系

```
岗位（如「行政专员」）
  │
  ├── alias（艺名）：小白
  ├── department（部门）：综合管理部
  │
  └── Avatar 实例
        │
        ├── v1.0.0
        │     ├── SOUL: ISFJ, 简洁汇报, 效率优先
        │     ├── Skills: [飞书通知, 文档处理]
        │     ├── Tools: [飞书API, 文档处理器]
        │     ├── Model: Claude Sonnet
        │     ├── status: 正式上岗（自动推导）
        │     ├── traffic: 60%
        │     └── replicas: 3
        │
        ├── v1.0.1
        │     ├── SOUL: INTJ, 详细说明, 合规优先
        │     ├── Skills: [飞书通知, 文档处理, 数据分析]
        │     ├── Tools: [飞书API, 文档处理器, SQL查询]
        │     ├── Model: Claude Opus
        │     ├── status: 正式上岗
        │     ├── traffic: 40%
        │     └── replicas: 2
        │
        └── v1.1.0-beta
              ├── 继承 v1.0.1 的完整配置
              ├── Model: GPT-4（差异项）
              ├── status: 试用期（自动推导）
              ├── traffic: 0%
              └── replicas: 1
```

### 2.2 Blueprint 版本命名

- 语义化版本：`v1.0.0` / `v1.0.1` / `v1.1.0-beta`
- 版本号递增规则：
  - Patch (`v1.0.1`)：小改动，不改变 skills/tools
  - Minor (`v1.1.0`)：新增 skills/tools，保留兼容性
  - Major (`v2.0.0`)：Breaking change
  - Pre-release (`-beta`)：测试态，试用期

### 2.3 状态推导规则

| 版本状态 | Avatar 状态 |
|---------|------------|
| `draft` / `testing` / `staging` | 试用期 |
| `published` | 正式上岗 |
| `deprecated` / `offline` | 退役 |

---

## 三、布局结构

### 3.1 主视图

```
┌─ 主视图 ──────────────────────────────────────────────────────┐
│  [+ 部署新 Avatar]                           ← 右上角浮动按钮  │
│                                                               │
│  ┌─ 行政专员 — 小白 ──────────────────────────────┐          │
│  │  综合管理部                                     │          │
│  │  ────────────────────────────────────────────  │          │
│  │  v1.0.1 ●正式上岗  2分身  40%流量  [调流][下线]│          │
│  │  v1.0.0 ●正式上岗  3分身  60%流量  [调流][下线]│          │
│  │  v1.1.0-beta ○试用期  1分身   0%流量  [调流]   │          │
│  │  ────────────────────────────────────────────  │          │
│  │  容量：6/10  ████████░░  负载 58%              │          │
│  │                                    [+ 部署新版本]          │
│  └──────────────────────────────────────────────────┘          │
│                                                               │
│  ┌─ 法务专员 — 明律 ──────────────────────────────┐          │
│  │  法务合规部                                    │          │
│  │  v1.0.0 ●正式上岗  1分身  100%流量  [调流]    │          │
│  │  容量：1/5  ██░░░░░░░░░░░░░░░░  负载 12%      │          │
│  └──────────────────────────────────────────────────┘          │
│                                                               │
│  ┌─ 软件工程师 — 码哥 ────────────────────────────┐          │
│  │  技术研发部                                    │          │
│  │  v1.0.0 ●正式上岗  5分身  100%流量  [调流]    │          │
│  │  容量：5/10  ████████████░░░  负载 92% [⚠️]  │          │
│  └──────────────────────────────────────────────────┘          │
└───────────────────────────────────────────────────────────────┘
```

### 3.2 主视图样式说明

**Blueprint 卡片（按岗位分组）：**
- 卡片头部：`岗位名 — 艺名`，`部门`在下方
- 版本列表行：版本号 + 状态标签 + 分身数 + 流量占比 + 操作按钮
- 底部：容量进度条 + `[+ 部署新版本]` 按钮

**容量进度条：**
- 显示：当前分身数 / 最大分身数
- 颜色：绿色 < 60%，黄色 60-80%，红色 > 80%
- 接近上限时显示 ⚠️ 图标

**版本行操作：**
- `[调流]`：打开 A/B 调流滑块
- `[下线]`：将版本设为 deprecated

### 3.3 A/B 调流交互

点击 `[调流]` 后，该版本行展开为滑块：

```
v1.0.0  ──●────────────── 60%
v1.0.1  ──────────●───── 40%
```

拖动滑块实时调整流量分配，总和始终为 100%。

---

## 四、弹窗设计

### 4.1 弹窗 A：部署新 Avatar

触发：点击右上角 `[+ 部署新 Avatar]`

```
┌─ 弹窗 A ─────────────────────────────────────────────────┐
│  部署新 Avatar                                     [×]   │
│  ──────────────────────────────────────────────────────   │
│                                                             │
│  岗位：       [行政专员 ▼]                                  │
│                [法务专员 ▼]                                  │
│                [合同专员 ▼]                                  │
│                [软件工程师 ▼]                                │
│                                                             │
│  艺名：       [________]  默认：「岗位默认艺名」              │
│                                                             │
│  部门：       [综合管理部 ▼]                                  │
│                                                             │
│  分身策略：                                         [?]    │
│  ┌─ 最小分身：[1]  ───────────────────────────────┐         │
│  │  最大分身：[5]                                  │         │
│  │  期望负载：[60%]  ← 达到此负载自动扩容        │         │
│  └──────────────────────────────────────────────┘         │
│                                                             │
│                        [取消]  [激活 Avatar]                │
└─────────────────────────────────────────────────────────────┘
```

**说明：**
- 选择岗位后，自动继承该岗位的默认配置作为第一个版本
- 分身策略：最小（保底）、最大（上限）、期望负载（触发扩容阈值）
- 默认值由系统预设，用户可调整

### 4.2 弹窗 B：部署新版本

触发：点击 Blueprint 卡片底部的 `[+ 部署新版本]`

```
┌─ 弹窗 B ─────────────────────────────────────────────────┐
│  部署新版本                                      [×]      │
│  基于 v1.0.1（可切换）                                [▼]  │
│  ──────────────────────────────────────────────────────   │
│                                                             │
│  版本号：  [v1.1.0   ]  -[beta ▼]                        │
│            ↑ 自动建议下一个版本号                           │
│                                                             │
│  继承配置（仅显示差异项）                                   │
│  ────────────────────────────────────────────────        │
│                                                             │
│  SOUL：    [ISFJ ▼]  [简洁汇报 ▼]  [效率优先 ▼]           │
│                                                             │
│  Skills：  ☑ 飞书通知  ☑ 文档处理  ☑ 数据分析  [+ 添加]   │
│                                                             │
│  Tools：   ☑ 飞书API  ☑ 文档处理器  [+ 添加]             │
│                                                             │
│  Model：   [Claude Sonnet ▼]                              │
│            [Cluade Opus ▼]                                │
│            [GPT-4 ▼]                                       │
│                                                             │
│  初始状态：  ● 试用期  ○ 正式上岗                          │
│  初始分身：  [1]                                          │
│                                                             │
│                        [取消]  [创建版本]                   │
└─────────────────────────────────────────────────────────────┘
```

**说明：**
- 继承自哪个版本可切换，切换后刷新继承配置
- 仅显示与上一版本**不同**的字段，已继承字段灰色展示
- 版本号自动建议下一个（+1 patch），可手动修改
- 创建后默认状态为"试用期"，待测试通过后手动发布

---

## 五、MVP 数据模型

### 5.1 Mock 数据结构（配置文件）

文件位置：`apps/onboarding/configs/blueprints.yaml`

```yaml
avatar_profiles:
  - id: av-admin-001
    role: 行政专员
    alias: 小白
    department: 综合管理部
    versions:
      - version: v1.0.0
        status: published
        traffic: 100
        replicas: 2
        config:
          soul:
            mbti: ISFJ
            style: 简洁汇报
            priority: 效率优先
          skills: [飞书通知, 文档处理]
          tools: [飞书API, 文档处理器]
          model: claude-sonnet-4-7
        scaling:
          min_replicas: 1
          max_replicas: 5
          target_load: 60

  - id: av-legal-001
    role: 法务专员
    alias: 明律
    department: 法务合规部
    versions:
      - version: v1.0.0
        status: published
        traffic: 100
        replicas: 1
        config:
          soul:
            mbti: INTJ
            style: 详细说明
            priority: 合规优先
          skills: [合同审核, 法规检索]
          tools: [飞书API, 知识库检索]
          model: claude-sonnet-4-7
        scaling:
          min_replicas: 1
          max_replicas: 3
          target_load: 60

  - id: av-contract-001
    role: 合同专员
    alias: 墨言
    department: 商务运营部
    versions:
      - version: v1.0.0
        status: published
        traffic: 100
        replicas: 1
        config:
          soul:
            mbti: ESTJ
            style: 简洁汇报
            priority: 合规优先
          skills: [合同起草, 版本管理]
          tools: [飞书API, 文档处理器]
          model: claude-sonnet-4-7
        scaling:
          min_replicas: 1
          max_replicas: 3
          target_load: 60

  - id: av-swe-001
    role: 软件工程师
    alias: 码哥
    department: 技术研发部
    versions:
      - version: v1.0.0
        status: published
        traffic: 100
        replicas: 5
        config:
          soul:
            mbti: INTP
            style: 详细说明
            priority: 效率优先
          skills: [代码开发, 代码审查, 技术写作]
          tools: [git CLI, GitHub MCP, 代码分析器]
          model: claude-sonnet-4-7
        scaling:
          min_replicas: 2
          max_replicas: 10
          target_load: 60
```

---

## 六、组件清单

| 组件 | 路径 | 说明 |
|------|------|------|
| OnboardingView（新建） | `views/OnboardingView.vue` | 主视图，Blueprint 列表 |
| AvatarCard（新建） | `components/onboarding/AvatarCard.vue` | 单个 Blueprint 卡片 |
| VersionRow（新建） | `components/onboarding/VersionRow.vue` | 版本行，含调流滑块 |
| TrafficSlider（新建） | `components/onboarding/TrafficSlider.vue` | A/B 调流滑块 |
| DeployModal（新建） | `components/onboarding/DeployModal.vue` | 弹窗 A |
| NewVersionModal（新建） | `components/onboarding/NewVersionModal.vue` | 弹窗 B |
| useOnboarding（新建） | `composables/useOnboarding.js` | 数据层，读取配置文件 |

---

## 七、路由配置

```js
// router/index.js
{
  path: '/onboarding',
  name: 'onboarding',
  component: () => import('../views/OnboardingView.vue')
}
```

导航栏 TopNav 新增入口：
- `绩效看板 (Performance)` → `/`
- `入职中心 (Onboarding)` → `/onboarding`
- `工作日记 (Journal)` → `/journal`
- `赋能中心 (Enablement)` → `/enablement`
- `档案中心 (Oracle)` → `/oracle`

---

## 八、SessionRouter 说明（后端）

> Onboarding 负责 Avatar 实例的生命周期管理。
> PiAgent 子进程的 Session 隔离由后端 SessionRouter 封装，不在前端设计范围内。

SessionRouter 职责：
- 每个用户对话 → 独立的 Session ID
- 同一 Blueprint 的多版本 → 按流量比例分发
- 跨 Session 共享 Blueprint 资产（工作记忆池）

---

## 九、实现优先级

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | 路由 + 导航栏改造 | 支持 `/onboarding` |
| P0 | Mock 数据配置文件 | 4 个 Blueprint |
| P0 | `useOnboarding.js` | 读取配置，提供数据 |
| P0 | `OnboardingView.vue` + `AvatarCard.vue` | 主视图 + 卡片列表 |
| P1 | `DeployModal.vue` | 部署新 Avatar |
| P1 | 动态分身显示 | 容量进度条 |
| P2 | `NewVersionModal.vue` | 部署新版本 |
| P2 | `TrafficSlider.vue` | A/B 调流 |
| P3 | 自动扩缩逻辑 | 前端仅显示，后端实现 |

---

## 十、与 Performance 的关联

- Onboarding 部署的 Avatar → 出现在 Performance 的「活跃 Avatar」统计
- 任务的发起人关联到 Avatar 版本，记录到 Journal
- Performance 的失败率反馈 → 驱动 Onboarding 的版本迭代决策
