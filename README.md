# EnterpriseAgentEmployee
企业数字员工中心


## 系统设计稿（V1）
- `docs/enterprise-agent-employee-system-design.md`：基于行业洞察的企业数字员工完整系统设计方案（含架构、治理、运营与分阶段路线图）

## OpenClaw PiAgent 方案
已新增《采用 OpenClaw PiAgent 作为企业数字员工内核的落地方案》，用于指导本项目以 PiAgent 为内核并兼容 OpenClaw 生态（Channel、ClawHub Skill 市场）。

- 方案文档：`docs/openclaw-piagent-adoption.md`
- 重点策略：PiAgent 原生内核 + 企业治理外壳


## 分层实施规划（L1 基线 → L4 完善）
- `docs/mvp-scope-piagent-portal.md`：企业数字员工分层演进实施方案（L1 基线可用到 L4 企业完善）


## 应用目录规划
- `apps/admin-portal/`：企业数字员工后台管理应用（管理端）
- `apps/highway-rescue-demo/`：高速无人协同救援前端演示（地图 + Mock 服务）


## 部署
- `apps/highway-rescue-demo/` 已支持 GitHub Pages 自动部署（见 `.github/workflows/deploy-highway-demo-pages.yml`）
- 新增全仓 CI 工作流：`.github/workflows/ci.yml`（Python 语法检查 + 两个 Demo 服务 API 冒烟检查）


## 核心基线运行入口（L1 Sandbox）
- `apps/mvp-core/`：L1 基线能力沙箱（核心 Agent + 控制台 + 场景 Demo），后续能力在同一底座叠加


## 协作提交流程
- `docs/git-sync-workflow.md`：提交前拉取最新代码、处理冲突并重新提交的标准流程
