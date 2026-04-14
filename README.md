# e-Agent-OS

> 企业数字员工操作系统（Enterprise Agent Operating System）

## 项目概述

构建企业数字员工的**兵工厂 + 运营中心**：

- **生产工厂**：一套模板，N个岗位，分钟级创建数字员工
- **运营中心**：效率/成本/质量三维可观测，ROI可量化
- **知识中心**：企业知识资产化，AIGC自动沉淀
- **模型中心**：供应商解耦，智能路由，成本可控

## 快速开始

### 安装依赖

```bash
pip install uv  # 如未安装
uv sync
```

### 运行测试

```bash
pytest tests/ -v
```

### 运行各层服务

你可以分别启动网关、运行时、运营中心以及前端，或使用快捷方式。

```bash
# 1. 运营中心 (Dashboard/Onboarding API)
python -m apps.ops.main

# 2. 网关 (API Gateway)
python -m apps.gateway.main

# 3. 运行时 (Agent Execute Cycle)
python -m apps.runtime.main

# 4. 前端 (Vue3 Dashboard)
cd frontend && npm run dev
```

> **注意**：本地开发默认使用 Redis 和 SQLite，请确保环境已安装 `redis` 并正在运行。

## 文档导航

| 文档 | 说明 |
|------|------|
| [AGENTS.md](AGENTS.md) | 开发地图，入口导航 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 完整架构设计 |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 开发军规与流程 |
| [QUALITY.md](QUALITY.md) | 质量标准 |

## 开发原则

> **人类掌舵，AI执行。** 纪律体现在支撑结构上，而非代码本身。

详见 [DEVELOPMENT.md](DEVELOPMENT.md)。

## 团队

- **产品Owner**：老郑
- **AI开发助手**：Claude Code
