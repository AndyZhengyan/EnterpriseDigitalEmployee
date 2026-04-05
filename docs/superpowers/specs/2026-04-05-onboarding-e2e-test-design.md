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

## 2.1 Issue 追踪（暂缓项）

以下功能未实现，留待后续迭代：

| Issue | 说明 | 关联 |
|-------|------|------|
| `#onboard-traffic-api` | 后端缺少调流 API（PUT traffic endpoint） | E2E-ON-05, 06 |
| `#onboard-deprecate-api` | 后端缺少下线 API（PUT deprecate endpoint） | E2E-ON-07 |
| `#onboard-delete-api` | 后端缺少删除 Blueprint API | E2E-ON-08 |
| `#onboard-vue-index-bug` | Vue `$index` 类型比较 bug | 调流/下线交互 |
| `#onboard-openclaw-stub` | CI openclaw stub 模式 | CI e2e job |

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

| ID | 名称 | 步骤 | 预期结果 | 状态 |
|----|------|------|---------|------|
| E2E-ON-01 | 部署新 Avatar | 1. 点击"+ 部署新 Avatar" → 2. 填写别名/部门/分身策略 → 3. 点击"激活 Avatar" | 卡片列表新增一项，Blueprint 写入 SQLite，id 以 `av-` 开头 | ✅ 本轮实现 |
| E2E-ON-02 | 部署新版本（前端本地） | 1. 点击卡片底部"部署新版本" → 2. 填写版本号/初始分身 → 3. 点击"确认部署" | 版本列表追加新版本，traffic=0（前端 ref，无持久化） | ✅ 本轮实现 |

### 4.2 查（Read）

| ID | 名称 | 步骤 | 预期结果 | 状态 |
|----|------|------|---------|------|
| E2E-ON-03 | 加载 Blueprint 列表 | 页面打开 | 4 张卡片，显示角色/别名/部门/版本/容量条 | ✅ 本轮实现 |
| E2E-ON-04 | 任务执行 + 结果展示 | 1. 点击"执行任务" → 2. 输入任务 → 3. Ctrl+Enter | 结果面板出现 summary/token/duration，exec 记录写入 SQLite | ✅ 本轮实现 |

### 4.3 改（Update）— 暂缓，见 `#onboard-traffic-api`

| ID | 名称 | 步骤 | 预期结果 | 状态 |
|----|------|------|---------|------|
| E2E-ON-05 | 调流 | 1. 点击某版本"调流" → 2. 拖动滑块 → 3. 点 ✓ | 该版本 traffic 更新，capacity 百分比变化 | 🔲 挂起 |
| E2E-ON-06 | 调流取消 | 1. 点击"调流" → 2. 拖动 → 3. 点 ✕ | traffic 保持原值 | 🔲 挂起 |
| E2E-ON-07 | 下线 | 1. 点击"下线" → 2. 点"确认" | traffic=0，status=deprecated，容量条更新 | 🔲 挂起 |

### 4.4 删（Delete）— 暂缓，见 `#onboard-delete-api`

| ID | 名称 | 步骤 | 预期结果 | 状态 |
|----|------|------|---------|------|
| E2E-ON-08 | 删除 Blueprint | 通过后端 API 删除刚创建的 Blueprint | 列表中该 Blueprint 消失，DB 中对应记录被 DELETE | 🔲 挂起 |

---

## 5. Phase 2 待实现（挂起）

详见 Issue: `#onboard-traffic-api`, `#onboard-deprecate-api`, `#onboard-delete-api`, `#onboard-vue-index-bug`, `#onboard-openclaw-stub`

---

## 6. CI Stub 机制（Phase 2 实现）

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

## 7. CI 配置变更

### 7.1 新增 job: `e2e`（Phase 2）

Phase 1 先用 Playwright + mock 数据跑本地验证，Phase 2 再接入真实后端 stub。

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

## 8. 测试数据初始化

测试 DB 文件：`data/ops.test.db`

- 启动时由 `init_test_db()` 创建
- Seed 数据：固定的 4 个 Blueprint（id 固定，测试用例依赖这些 id）
- 测试隔离：
  - Create 类测试：插入 → 验证 → DELETE
  - 用 `beforeEach`/`afterEach` 保证每个测试独立

---

## 9. 实现顺序

### Phase 1（本轮，先跑通已实现的）

1. **[FIX] Vue $index bug** — Set.has() 方案
2. **[FEAT] Playwright 配置** — `playwright.config.ts` + `tests/e2e/` 目录
3. **[FEAT] E2E 测试用例 Phase 1** — 4 个测试（E2E-ON-01 ~ 04），前端 mock 模式
4. **[TEST] 本地全链路验证** — Playwright 跑通，useMock=true

### Phase 2（后续迭代）

5. **[FEAT] 后端补充 3 个 API** — traffic PUT + deprecate PUT + delete DELETE
6. **[FEAT] CI stub 模式** — `OPENCLAW_CLI_STUB` 环境变量
7. **[FEAT] E2E 测试用例 Phase 2** — E2E-ON-05 ~ 08
8. **[CI] 新增 e2e job** — `.github/workflows/ci.yml`
9. **[TEST] CI green**

---

## 10. 验收标准

### Phase 1
- [ ] `npm run build` (frontend) → success
- [ ] Vue $index bug 修复，调流/下线 UI 行为正确
- [ ] Playwright E2E: E2E-ON-01 ~ 04 全部 green（mock 模式）
- [ ] 本地全链路：页面加载 → 部署新 Avatar → 任务执行 → 结果展示

### Phase 2
- [ ] 后端 3 个 API 就绪
- [ ] CI stub 模式正常
- [ ] Playwright E2E: E2E-ON-05 ~ 08 全部 green
- [ ] GitHub Actions `e2e` job → green on PR
