# CLAUDE.md — e-Agent-OS

## Harness 工程方法论（必须遵守）

> 人类掌舵，AI执行。纪律体现在支撑结构上，而非代码本身。

### 角色分工

- **老郑（人类）**：设计环境、明确意图、构建反馈回路、验收结果
- **Claude（AI）**：编写代码、测试、文档、维护 PR

### 铁律

1. **代码仓库是唯一真实来源**
   - Codex 看不到的 = 不存在（Google Docs / Slack / 大脑 = 不可见）
   - 所有决策、设计、会议结论必须 commit 到仓库
   - 代码仓库内的才是真实来源

2. **渐进式披露**
   - AGENTS.md ≈ 100行，作为目录，不是百科全书
   - 避免上下文过载：按需阅读 ARCHITECTURE.md / docs/ / specs/
   - 小的、稳定的入口 > 大而全的说明书

3. **架构约束必须机械执行**
   - 任何架构规则必须有对应的 linter / test / schema 验证
   - 没有机械验证的规则 = 不存在的规则
   - 违反即修复，不跳过

4. **人类品味必须编码进系统**
   - 发现 bug → 修复 + 写 regression test + 检查同类
   - Review 评论中的偏好 → 翻译成 linter rule 或测试用例
   - 不只修个案，把品味固化防止同类问题复发

5. **熵管理自动化**
   - 定期后台任务：扫描代码漂移、更新质量等级、发起清理 PR
   - 技术债务像高息贷款，小额定期偿还 > 一次性清理
   - 人类品味一旦被捕获，持续应用于每一行代码

6. **纠错成本低，等待成本高**
   - PR 生命周期 < 24小时
   - 测试偶发失败 → 快速重跑，不无限阻塞
   - 快速小步前进 > 等待完美方案

### 机械执行的架构规则

| 规则 | 验证方式 |
|------|----------|
| AgentFamily 配置必须有 SOUL/IDENTITY/AGENT 三段 | schema validator |
| 禁止跨层直接调用（分层架构） | 结构化测试 |
| 禁止 bare except | ruff F401 |
| 禁止 print（用结构化日志） | ruff T201 |

> 发现新规则 → 必须编码成可验证的形式，否则无效。

---

## 项目概述

- **项目名**: e-Agent-OS (Enterprise Agent Employee)
- **仓库**: github.com/AndyZhengyan/enterprise-agent-employee
- **技术栈**: Python 3.13, FastAPI, Pydantic, OpenTelemetry, Redis
- **分支策略**: `main` 是主分支，PR review 后合并

## 授权规则

处理 PR 或 CI 问题时，**自动执行以下操作**，无需中途确认：

- 运行 `ruff check --fix`、`ruff format`、`mypy` 并修复所有 lint/mypy 错误
- 解决 rebase 时产生的冲突，选择正确的版本（安全修复 > 功能代码 > 格式调整）
- Push 到 PR 分支（使用 `--force-with-lease`）
- 触发并监控 CI 运行（`gh run list` / `gh run rerun`）
- PR 合并条件满足时，通知用户可以合并
- **发现 bug 或 badcase**：自动扩展处理（见下方问题处理顺序），不只修个案

**发现问题的处理顺序（自动执行）**：

```
1. 修复代码
2. 写/更新 regression test
3. 检查同类问题是否存在
4. 提出是否需要新增 linter rule 或 schema validator
```

**需要用户确认的情况**（发现问题时再问，不要事前问）：

- 需要删除或重写非自己创建的 commit
- 需要修改 CI workflow 本身的逻辑
- 发现代码有逻辑 bug 而非风格问题（风格问题 AI 直接修）
- 授权范围外的任何操作

## CI/CD

- CI 配置在 `.github/workflows/ci.yml`
- 三阶段: `Lint` (ruff + mypy) → `Test` (pytest) → `Security` (pip-audit)
- 所有 jobs 必须 green 才能合并
- PR 合并条件: `mergeable_state: clean` + 所有 CI checks passed

## 代码风格

- **Lint**: `ruff check apps/ common/`
- **Format**: `ruff format apps/ common/`
- **Type check**: `mypy apps/ common/`
- **Tests**: `pytest tests/ -v`
- 所有检查必须通过后才能 push

## Git 约定

- Commit message 格式: `type(scope): description` (Conventional Commits)
- PR 分支命名: `ci/*`, `security/*`, `feat/*`, `fix/*`
- 推送到 PR 分支时使用 `--force-with-lease`
- 推送后自动验证 CI 状态，失败时自动修复

## 本地开发

```bash
# 安装依赖
pip install -e ".[dev]"

# 运行所有检查
ruff check apps/ common/ && ruff format apps/ common/ && mypy apps/ common/ && pytest tests/

# 启动服务
python -m apps.gateway.main   # Gateway
python -m apps.runtime.main   # Runtime
```
