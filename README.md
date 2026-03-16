# EnterpriseAgentEmployee
企业数字员工中心


## 系统设计稿（V1）
- `docs/enterprise-agent-employee-system-design.md`：基于行业洞察的企业数字员工完整系统设计方案（含架构、治理、运营与分阶段路线图）

## OpenClaw PiAgent 方案
已新增《采用 OpenClaw PiAgent 作为企业数字员工内核的落地方案》，用于指导本项目以 PiAgent 为内核并兼容 OpenClaw 生态（Channel、ClawHub Skill 市场）。

- 方案文档：`docs/openclaw-piagent-adoption.md`
- 重点策略：PiAgent 原生内核 + 企业治理外壳


## MVP 规划
- `docs/mvp-scope-piagent-portal.md`：PiAgent + 企业数字员工管理 Portal 的最小 MVP 范围与实施步骤


## 应用目录规划
- `apps/admin-portal/`：企业数字员工后台管理应用（管理端）
- `apps/highway-rescue-demo/`：高速无人协同救援前端演示（地图 + Mock 服务）


## 部署
- `apps/highway-rescue-demo/` 已支持 GitHub Pages 自动部署（见 `.github/workflows/deploy-highway-demo-pages.yml`）


## 核心 MVP 运行入口
- `apps/mvp-core/`：核心 Agent + 核心控制台 + 高速事故处理场景 Demo（一体化可运行）


## 协作提交流程
- `docs/git-sync-workflow.md`：提交前拉取最新代码、处理冲突并重新提交的标准流程
