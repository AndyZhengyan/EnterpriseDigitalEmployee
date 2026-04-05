# Onboarding E2E 测试工程设计

**日期**: 2026-04-05
**状态**: 设计中

---

## 1. 目标

为入职中心（Onboarding）页面建立完整的增删改查 + 任务下发 E2E 测试体系，满足：

1. 页面增删改查全链路真实验证（前端 → 后端 → SQLite）
2. 任务下发真实执行（前端 → 后端 → openclaw CLI）
3. CI 可跑（GitHub Actions，零手动干预）
4. 测试数据隔离（每个测试独立，互不干扰）

---

## 2. 当前状态

| 层 | 状态 | 说明 |
|----|------|------|
| 前端 UI | 有一 bug | `$index` 是 string，`!==` 比较失效，调流/下线按钮激活时所有行同时显示 |
| 前端 API | `USE_MOCK=true` | Mock 数据正常，切换到真实 API 需验证 |
| 后端 API | 基本完整 | `/onboarding/blueprints` GET、`/onboarding/deploy` POST、`/ops/execute` POST 已实现 |
| 后端缺 | 2 个端点 | `PUT /onboarding/blueprints/{id}/traffic`（调流）、`PUT /onboarding/blueprints/{id}/versions/{idx}/deprecate`（下线） |
| 测试框架 | 无 | 前端无 Playwright/Vitest，CI 无前端 job |
| openclaw | CI 不可用 | openclaw CLI 在 GitHub Actions runner 不存在，需 mock |

---

## 3. 架构设计

```
┌─────────────────────────────────────────────────────┐
│  GitHub Actions CI                                  │
│                                                     │
│  jobs:                                              │
│  ├── lint            (Python)                       │
│  ├── test            (pytest)                       │
│  ├── security        (pip-audit)                   │
│  └── e2e             (Playwright + Frontend)  ← 新增│
│       ├── Setup test DB (seed 固定数据)              │
│       ├── Start backend (uvicorn)                   │
│       ├── Start frontend (vite preview / dev)       │
│       ├── Install Playwright browsers               │
│       └── Run: npx playwright test                  │
└─────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│  测试数据策略                                        │
│                                                     │
│  测试 DB: data/ops.test.db (独立文件)               │
│  Seed: 固定 4 个 Blueprint（id 固定）               │
│  隔离: 每个测试用例用 Blueprint.id 做前缀，           │
│        测试结束后 DELETE 掉本次插入的数据            │
│  CI openclaw: stub 返回固定 JSON，不真实调用 CLI      │
└─────────────────────────────────────────────────────┘
```

---

## 4. 测试用例设计

### 4.1 增（Create）

| ID | 名称 | 步骤 | 预期结果 |
|----|------|------|---------|
| E2E-ON-01 | 部署新 Avatar | 1. 点击"+ 部署新 Avatar" → 2. 填写别名/部门/分身策略 → 3. 点击"激活 Avatar" | 卡片列表新增一项，Blueprint 写入 SQLite，id 以 `av-` 开头 |
| E2E-ON-02 | 部署新版本 | 1. 点击卡片底部"部署新版本" → 2. 填写版本号/初始分身 → 3. 点击"确认部署" | 版本列表追加新版本，traffic=0 |

### 4.2 查（Read）

| ID | 名称 | 步骤 | 预期结果 |
|----|------|------|---------|
| E2E-ON-03 | 加载 Blueprint 列表 | 页面打开 | 4 张卡片，显示角色/别名/部门/版本/容量条 |
| E2E-ON-04 | 查看任务执行结果 | 1. 点击"执行任务" → 2. 输入任务 → 3. Ctrl+Enter | 结果面板出现 summary/token/duration |

### 4.3 改（Update）

| ID | 名称 | 步骤 | 预期结果 |
|----|------|------|---------|
| E2E-ON-05 | 调流 | 1. 点击某版本"调流" → 2. 拖动滑块 → 3. 点 ✓ | 该版本 traffic 更新，capacity 百分比变化 |
| E2E-ON-06 | 调流取消 | 1. 点击"调流" → 2. 拖动 → 3. 点 ✕ | traffic 保持原值 |
| E2E-ON-07 | 下线 | 1. 点击"下线" → 2. 点"确认" | traffic=0，status=deprecated，容量条更新 |

### 4.4 删（Delete）

| ID | 名称 | 步骤 | 预期结果 |
|----|------|------|---------|
| E2E-ON-08 | 删除 Blueprint | 通过 deploy modal 删除刚创建的 Blueprint | 列表中该 Blueprint 消失，DB 中对应记录被 DELETE |

---

## 5. 后端 API 补充

### 5.1 PUT `/api/onboarding/blueprints/{id}/traffic`

更新指定版本 traffic 权重。

**Request**:
```json
{ "version_index": 0, "traffic": 30 }
```

**Response**: 更新后的 Blueprint 对象

### 5.2 PUT `/api/onboarding/blueprints/{id}/versions/{idx}/deprecate`

将指定版本下线（traffic=0, status=deprecated）。

**Response**: 更新后的 Blueprint 对象

### 5.3 CI Stub 机制

在 `apps/ops/main.py` 中，通过环境变量 `OPENCLAW_CLI_STUB=true` 启用桩模式：

```python
if os.environ.get("OPENCLAW_CLI_STUB") == "true":
    return {
        "status": "ok",
        "runId": f"stub-{uuid.uuid4().hex[:8]}",
        "summary": "这是 CI stub 返回的摘要",
        "result": {
            "meta": {
                "agentMeta": {
                    "usage": {"input": 1200, "output": 340, "cacheRead": 0}
                },
                "durationMs": 2100
            }
        }
    }
```

---

## 6. CI 配置变更

### 6.1 新增 job: `e2e`

```yaml
e2e:
  name: E2E
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: "20"
        cache: "frontend/node_modules"

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.13"
        cache: pip

    - name: Install frontend deps
      run: cd frontend && npm ci

    - name: Install backend deps
      run: pip install -e ".[dev]"

    - name: Build frontend
      run: cd frontend && npm run build

    - name: Start backend (stub mode)
      run: |
        export OPS_DB_PATH="$PWD/data/ops.test.db"
        export OPENCLAW_CLI_STUB=true
        uvicorn apps.ops.main:app --port 8002 &
        sleep 3

    - name: Serve frontend dist
      run: |
        npx serve dist -l 5173 &
        sleep 2

    - name: Install Playwright
      run: npx playwright install --with-deps chromium

    - name: Run E2E tests
      run: npx playwright test tests/e2e/

    - name: Upload test results
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: playwright-report
        path: playwright-report/
```

---

## 7. 测试数据初始化

测试 DB 文件：`data/ops.test.db`

- 启动时由 `init_test_db()` 创建
- Seed 数据：固定的 4 个 Blueprint（id 固定，测试用例依赖这些 id）
- 测试隔离：
  - Create 类测试：插入 → 验证 → DELETE
  - Update 类测试：基于固定 seed 数据修改 → 验证 → ROLLBACK
  - 用 `beforeEach`/`afterEach` 保证每个测试独立

---

## 8. 实现顺序

1. **[FIX] Vue $index bug** — `!=` 改 `!adjustingIndices.has($index)`
2. **[FEAT] 后端补充 2 个 API 端点** — traffic PUT + deprecate PUT
3. **[FEAT] CI stub 模式** — `OPENCLAW_CLI_STUB` 环境变量
4. **[FEAT] Playwright 配置** — `playwright.config.ts` + `tests/e2e/` 目录
5. **[FEAT] E2E 测试用例** — 8 个测试（E2E-ON-01 ~ 08）
6. **[CI] 新增 e2e job** — `.github/workflows/ci.yml`
7. **[TEST] 全链路验证** — CI green + 本地 Playwright 手动验证

---

## 9. 验收标准

- [ ] `ruff check apps/ common/` → 0 errors
- [ ] `pytest tests/` → all pass
- [ ] `npm run build` (frontend) → success
- [ ] Playwright E2E: 8 个测试全部 green
- [ ] GitHub Actions `e2e` job → green on PR
- [ ] 本地 `openclaw agent --message "hi" --json` → 真实返回（dev 模式）
