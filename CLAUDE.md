# CLAUDE.md — e-Agent-OS

## 项目概述

- **项目名**: e-Agent-OS (Enterprise Agent Employee)
- **仓库**: github.com/AndyZhengyan/enterprise-agent-employee
- **技术栈**: Python 3.11, FastAPI, Pydantic, OpenTelemetry, Redis
- **分支策略**: `main` 是主分支，PR review 后合并

## 授权规则

处理 PR 或 CI 问题时，**自动执行以下操作**，无需中途确认：

- 运行 `ruff check --fix`、`ruff format`、`mypy` 并修复所有 lint/mypy 错误
- 解决 rebase 时产生的冲突，选择正确的版本（安全修复 > 功能代码 > 格式调整）
- Push 到 PR 分支（使用 `--force-with-lease`）
- 触发并监控 CI 运行（`gh run list` / `gh run rerun`）
- PR 合并条件满足时，通知用户可以合并

**需要用户确认的情况**（发现问题时再问，不要事前问）：

- 需要删除或重写非自己创建的 commit
- 需要修改 CI workflow 本身的逻辑
- 发现代码有逻辑 bug 而非风格问题
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
