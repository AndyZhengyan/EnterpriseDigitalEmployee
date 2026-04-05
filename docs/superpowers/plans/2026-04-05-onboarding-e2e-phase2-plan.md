# Onboarding E2E Phase 2 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完成入职中心增删改查全链路：后端 API 补全 + 前端切真实 API + CI e2e job + Phase 2 E2E 测试（E2E-ON-05~08）。

**架构说明（重要）：**
- pi-agent 通过 `openclaw agent` CLI subprocess 调用（`apps/runtime/piagent_client.py`）
- `apps/ops/main.py` 中的 stub 环境变量为 `PIAGENT_CLI_STUB=true`
- 前端 `USE_MOCK=false`，所有调用走真实后端

---

## Phase 2 任务列表

| # | 任务 | 依赖 |
|---|------|------|
| 1 | 后端 API × 3 + PIAGENT_CLI_STUB | 无 |
| 2 | 前端切真实 API（USE_MOCK=false） | Task 1 |
| 3 | 前端添加调流/下线 API 调用 | Task 1 |
| 4 | Phase 2 E2E 测试（E2E-ON-05~08） | Task 2+3 |
| 5 | CI e2e job | Task 4 |

---

## Task 1: 后端 API × 3 + PIAGENT_CLI_STUB

**文件:** `apps/ops/main.py`

### 1a. 修改 `_run_openclaw` 为 `_run_piagent`，加入 stub

找到 `_run_openclaw` 函数（约第 72 行），在函数开头加入 stub 判断：

```python
def _run_piagent(message: str, agent_id: str = "chat", timeout: int = 60) -> Dict[str, Any]:
    """Call openclaw CLI and return parsed JSON result. Stub for CI."""
    # CI stub — openclaw CLI not available in GitHub Actions runner
    if os.environ.get("PIAGENT_CLI_STUB") == "true":
        import uuid
        return {
            "status": "ok",
            "runId": f"stub-{uuid.uuid4().hex[:8]}",
            "summary": "CI stub response — this is a simulated agent execution",
            "result": {
                "meta": {
                    "agentMeta": {
                        "usage": {"input": 1200, "output": 340, "cacheRead": 0},
                        "durationMs": 2100,
                    }
                }
            },
        }

    token = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    if token:
        pass  # ... 保留原有逻辑（不变）
```

**注意：** 只加 stub 分支，不要改动原有 `openclaw` CLI 调用逻辑。

### 1b. 修改 `execute_task` 使用 `_run_piagent`

```python
raw = _run_piagent(message, agent_id, timeout=120)
```

（找到原 `raw = _run_openclaw(...)`，改为 `_run_piagent`）

### 1c. 添加 PUT `/api/onboarding/blueprints/{id}/traffic`

在 `apps/ops/main.py` 末尾（在 `@app.post("/api/onboarding/deploy")` 之后）添加：

```python
@app.put("/api/onboarding/blueprints/{bp_id}/traffic")
def update_traffic(bp_id: str, req: dict):
    """更新指定版本的 traffic 权重。"""
    version_idx = req.get("version_index")
    new_traffic = req.get("traffic")
    if new_traffic is None or version_idx is None:
        raise HTTPException(status_code=400, detail="version_index and traffic are required")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, versions, capacity FROM blueprints WHERE id = ?", (bp_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Blueprint not found")

    versions = json.loads(row[1])
    if version_idx < 0 or version_idx >= len(versions):
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid version_index")

    versions[version_idx]["traffic"] = new_traffic

    # 重新计算 capacity used
    total_used = sum(v["replicas"] for v in versions if v["traffic"] > 0)
    capacity = json.loads(row[2])
    capacity["used"] = total_used

    cur.execute(
        "UPDATE blueprints SET versions = ?, capacity = ? WHERE id = ?",
        (json.dumps(versions), json.dumps(capacity), bp_id),
    )
    conn.commit()
    conn.close()

    return {
        "id": bp_id,
        "versions": versions,
        "capacity": capacity,
    }
```

### 1d. 添加 PUT `/api/onboarding/blueprints/{bp_id}/versions/{idx}/deprecate`

```python
@app.put("/api/onboarding/blueprints/{bp_id}/versions/{idx}/deprecate")
def deprecate_version(bp_id: str, idx: int):
    """将指定版本下线（traffic=0, status=deprecated）。"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, versions, capacity FROM blueprints WHERE id = ?", (bp_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Blueprint not found")

    versions = json.loads(row[1])
    if idx < 0 or idx >= len(versions):
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid version index")

    versions[idx]["traffic"] = 0
    versions[idx]["status"] = "deprecated"

    # 重新计算 capacity used
    total_used = sum(v["replicas"] for v in versions if v["traffic"] > 0)
    capacity = json.loads(row[2])
    capacity["used"] = total_used

    cur.execute(
        "UPDATE blueprints SET versions = ?, capacity = ? WHERE id = ?",
        (json.dumps(versions), json.dumps(capacity), bp_id),
    )
    conn.commit()
    conn.close()

    return {"id": bp_id, "versions": versions, "capacity": capacity}
```

### 1e. 添加 DELETE `/api/onboarding/blueprints/{bp_id}`

```python
@app.delete("/api/onboarding/blueprints/{bp_id}")
def delete_blueprint(bp_id: str):
    """删除指定 Blueprint。"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM blueprints WHERE id = ?", (bp_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Blueprint not found")
    cur.execute("DELETE FROM blueprints WHERE id = ?", (bp_id,))
    conn.commit()
    conn.close()
    return {"deleted": bp_id}
```

### 验证

```bash
cd /Users/zhengyan/Projects/ai-project/e-agent-os
# 启动后端 stub 模式
PIAGENT_CLI_STUB=true OPS_DB_PATH=data/ops.test.db uvicorn apps.ops.main:app --port 8002 &
sleep 3
# 测试 traffic 端点
curl -s -X PUT http://localhost:8002/api/onboarding/blueprints/av-admin-001/traffic \
  -H "Content-Type: application/json" \
  -d '{"version_index": 0, "traffic": 30}' | python -m json.tool
# 测试 deprecate 端点
curl -s -X PUT http://localhost:8002/api/onboarding/blueprints/av-admin-001/versions/0/deprecate \
  | python -m json.tool
# 测试 delete 端点
curl -s -X DELETE http://localhost:8002/api/onboarding/blueprints/av-admin-001 | python -m json.tool
# 确认 blueprint 列表不再有 av-admin-001
curl -s http://localhost:8002/api/onboarding/blueprints | python -m json.tool | grep av-admin
# 期望：没有输出
```

### Commit

```bash
git add apps/ops/main.py
git commit -m "feat(ops): add traffic/deprecate/delete API endpoints + PIAGENT_CLI_STUB

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: 前端切真实 API（USE_MOCK=false）

**文件:** `frontend/src/services/api.js`

将 `USE_MOCK` 改为 `false`，同时确保 `onboardingApi.list` 调用真实后端。

**注意：** 当前 `api.js` 已有 `onboardingApi.list` 指向 `/api/onboarding/blueprints`，无需额外修改，只改 flag。

```javascript
const USE_MOCK = false; // 切换为真实后端
```

同时在 `vite.config.js` 中确认 proxy 配置正确（已确认有 `/api` → `localhost:8002`）。

### 验证

```bash
cd frontend && npm run build
# 预期：成功
```

---

## Task 3: 前端添加调流/下线 API 调用

**文件:** `frontend/src/composables/useOnboarding.js`

在 `useOnboarding` composable 中添加两个新函数：

```javascript
function adjustTraffic(blueprintId, versionIndex, traffic) {
  return onboardingApi.adjustTraffic(blueprintId, versionIndex, traffic)
    .then(res => {
      const bp = blueprints.value.find(b => b.id === blueprintId);
      if (bp && res.data) {
        bp.versions = res.data.versions;
        bp.capacity = res.data.capacity;
      }
    });
}

function deprecateVersion(blueprintId, versionIndex) {
  return onboardingApi.deprecateVersion(blueprintId, versionIndex)
    .then(res => {
      const bp = blueprints.value.find(b => b.id === blueprintId);
      if (bp && res.data) {
        bp.versions = res.data.versions;
        bp.capacity = res.data.capacity;
      }
    });
}
```

**文件:** `frontend/src/services/api.js`

在 `onboardingApi` 中添加：

```javascript
export const onboardingApi = {
  list: () =>
    USE_MOCK ? mockGetBlueprints() : api.get('/onboarding/blueprints'),
  deploy: (payload) =>
    USE_MOCK ? Promise.resolve({ data: null }) : api.post('/onboarding/deploy', payload),
  adjustTraffic: (blueprintId, versionIndex, traffic) =>
    api.put(`/onboarding/blueprints/${blueprintId}/traffic`, {
      version_index: versionIndex,
      traffic,
    }),
  deprecateVersion: (blueprintId, versionIndex) =>
    api.put(`/onboarding/blueprints/${blueprintId}/versions/${versionIndex}/deprecate`),
  deleteBlueprint: (blueprintId) =>
    api.delete(`/onboarding/blueprints/${blueprintId}`),
};
```

**文件:** `frontend/src/composables/useOnboarding.js`

在 `export function useOnboarding()` 的 return 中添加：

```javascript
adjustTraffic,
deprecateVersion,
```

**文件:** `frontend/src/components/onboarding/AvatarCard.vue`

修改模板中的确认按钮，改为调用真实 API：

```html
<!-- 调流确认 -->
<button class="v-btn v-btn--ok" @click="confirmTrafficAdjust(v, $index)">✓</button>

<!-- 下线确认 -->
<button class="v-btn v-btn--danger" @click="confirmDeprecate(v, $index)">确认</button>
```

在 script 中：

```typescript
import { opsApi } from '../../services/api.js';
// 以及 useOnboarding 中的 adjustTraffic, deprecateVersion

const {
  // ... existing
  adjustTraffic,
  deprecateVersion,
} = useOnboarding();

// 改写 confirmTrafficAdjustment：
async function confirmTrafficAdjustment(v, idx) {
  if (!props.blueprint.id.startsWith('av-')) return; // mock 模式不做持久化
  await adjustTraffic(props.blueprint.id, idx, _adjustingTraffic.value);
  adjustingIdx.value = null;
}

// 改写 confirmDeprecate：
async function confirmDeprecate(v, idx) {
  if (!props.blueprint.id.startsWith('av-')) return;
  await deprecateVersion(props.blueprint.id, idx);
  deprecatingIdx.value = null;
}
```

### 验证

```bash
cd frontend && npm run build
# 预期：成功
```

---

## Task 4: Phase 2 E2E 测试（E2E-ON-05~08）

**文件:** `frontend/tests/e2e/onboarding.spec.ts`

在现有测试文件末尾追加：

```typescript
  // ═══ Phase 2: 真实 API 测试 ══════════════════════

  test('E2E-ON-05: 调流（真实 API）', async ({ page: p }) => {
    const onboarding = new OnboardingPage(p);
    await onboarding.goto();

    const firstCard = onboarding.getCard(0);
    const firstVersionRow = firstCard.locator('.version-row').first();

    // 点击调流
    await firstVersionRow.locator('.v-btn', { hasText: '调流' }).click();

    // 滑块出现（前端 UI）
    await expect(firstVersionRow.locator('.v-traffic-slider')).toBeVisible();

    // 点确认（会调用 API）
    await firstVersionRow.locator('.v-btn--ok').click();

    // UI 确认 slider 消失，traffic 数字已更新
    await expect(firstVersionRow.locator('.v-traffic-slider')).not.toBeVisible();
  });

  test('E2E-ON-06: 下线（真实 API）', async ({ page: p }) => {
    const onboarding = new OnboardingPage(p);
    await onboarding.goto();

    const firstCard = onboarding.getCard(0);
    // 找到有"下线"按钮的版本行（published 版本）
    const publishedRow = firstCard.locator('.version-row').filter({ hasNotText: '退役' }).first();

    await publishedRow.locator('.v-btn--danger').click();

    // 确认按钮出现
    await expect(publishedRow.locator('button', { hasText: '确认' })).toBeVisible();
    await publishedRow.locator('button', { hasText: '确认' }).click();

    // 版本状态变为退役，traffic 显示 —
    await expect(publishedRow.locator('.v-status-label')).toContainText('退役');
    await expect(publishedRow.locator('.v-traffic--zero')).toBeVisible();
  });

  test('E2E-ON-07: 调流取消', async ({ page: p }) => {
    const onboarding = new OnboardingPage(p);
    await onboarding.goto();

    const firstCard = onboarding.getCard(0);
    const firstVersionRow = firstCard.locator('.version-row').first();

    // 记下原始 traffic
    const originalTraffic = await firstVersionRow.locator('.v-traffic').textContent();

    // 点击调流 → 拖动 → 点取消
    await firstVersionRow.locator('.v-btn', { hasText: '调流' }).click();
    await expect(firstVersionRow.locator('.v-traffic-slider')).toBeVisible();
    await firstVersionRow.locator('.v-btn', { hasText: '✕' }).click();

    // traffic 保持原值
    await expect(firstVersionRow.locator('.v-traffic')).toHaveText(originalTraffic);
  });
```

### 验证

```bash
cd frontend
npm run dev &
sleep 5
npx playwright test --project=chromium --grep "Phase 2"
# 预期：3 PASSED
```

### Commit

```bash
git add apps/ops/main.py frontend/src/
git commit -m "feat(ops+frontend): add Phase 2 API endpoints and wire to UI

- backend: PUT traffic, PUT deprecate, DELETE blueprint
- PIAGENT_CLI_STUB env var for CI
- frontend: wire adjustTraffic/deprecateVersion to API
- E2E-ON-05/06/07 tests

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: CI e2e job

**文件:** `.github/workflows/ci.yml`

在现有 `ci.yml` 末尾（在 `security` job 之后）添加：

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

      - name: Install Playwright
        run: cd frontend && npx playwright install --with-deps chromium

      - name: Start backend (stub mode)
        working-directory: .
        run: |
          export OPS_DB_PATH="$PWD/data/ops.test.db"
          export PIAGENT_CLI_STUB=true
          uvicorn apps.ops.main:app --port 8002 &
          sleep 3

      - name: Serve frontend dist
        run: |
          npx serve frontend/dist -l 5173 &
          sleep 2

      - name: Run E2E tests
        run: |
          cd frontend
          npx playwright test --project=chromium

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

### Commit

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add e2e job with Playwright + stub backend

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 验收清单

- [ ] 后端 3 个 API + PIAGENT_CLI_STUB 实现
- [ ] `npm run build` (frontend) → success
- [ ] 前端 USE_MOCK=false，调流/下线走真实 API
- [ ] Playwright E2E: E2E-ON-05/06/07 全部 green
- [ ] GitHub Actions e2e job → green on PR
