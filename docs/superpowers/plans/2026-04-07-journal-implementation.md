# Journal 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为审计/合规人员提供完整操作审计视图——左列表+右详情的分栏布局，完整字段（输入/输出摘要/token/版本），支持时间/角色/部门筛选 + 全文搜索。

**Architecture:** 复用现有 `task_executions` 表（ops.db），新增 `GET /api/journal/executions` 查询接口，前端 Vue 页面消费该接口。左筛选右详情布局。

**Tech Stack:** FastAPI（apps/ops）、Vue 3、SQLite、Axios

---

## 文件结构

```
apps/ops/main.py              — 新增 /api/journal/executions 和 /:id endpoint
frontend/src/services/api.js  — 新增 journalApi
frontend/src/views/JournalView.vue  — 左列表+右详情分栏布局
frontend/src/composables/useJournal.js  — journal 状态管理 composable
frontend/src/components/journal/ExecutionCard.vue    — 列表卡片组件
frontend/src/components/journal/ExecutionDetail.vue   — 右侧详情组件
frontend/src/components/journal/FilterBar.vue        — 筛选栏组件
tests/integration/test_journal_api.py  — journal API 测试
```

---

## Task 1: 后端 — Journal API 查询接口

**Files:**
- Modify: `apps/ops/main.py`（在文件末尾 `@app.delete` 路由之后添加 journal 路由）
- Create: `tests/integration/test_journal_api.py`

- [ ] **Step 1: 写测试**

```python
# tests/integration/test_journal_api.py
"""Integration tests for Journal API — queries task_executions table."""
import pytest


def _init_test_db(tmp_path, monkeypatch):
    """Set up temp DB with schema and seed data."""
    monkeypatch.setenv("OPS_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("PIAGENT_CLI_STUB", "true")
    from apps.ops import db as db_module
    db_module.DB_PATH = str(tmp_path / "ops.db")
    from apps.ops.db import get_db, init_db
    init_db()
    # Seed some test executions
    conn = get_db()
    conn.execute(
        "INSERT INTO task_executions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("exec-001", "run-001", "av-swe-001", "码哥", "软件工程师", "技术研发部",
         "帮我审查代码", "ok", 1000, 500, 0, 2300, "审查完成，无风险", "2026-04-07T09:00:00Z"),
    )
    conn.execute(
        "INSERT INTO task_executions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("exec-002", "run-002", "av-legal-001", "明律", "法务专员", "法务合规部",
         "审阅采购合同", "error", 500, 200, 0, 3800, "合同有风险", "2026-04-07T10:00:00Z"),
    )
    conn.commit()
    conn.close()
    from apps.ops import main as ops_main
    ops_main._runner_active = False
    ops_main._init_key_manager(str(tmp_path / "ops.db"))
    ops_main._force_dev_mode()


def test_executions_list_returns_all(client, db_path, monkeypatch):
    _init_test_db(db_path, monkeypatch)
    resp = client.get("/api/journal/executions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_executions_filter_by_role(client, db_path, monkeypatch):
    _init_test_db(db_path, monkeypatch)
    resp = client.get("/api/journal/executions?roles=软件工程师")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_executions_filter_by_status(client, db_path, monkeypatch):
    _init_test_db(db_path, monkeypatch)
    resp = client.get("/api/journal/executions?status=error")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_executions_filter_by_keyword(client, db_path, monkeypatch):
    _init_test_db(db_path, monkeypatch)
    resp = client.get("/api/journal/executions?q=合同")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_execution_detail(client, db_path, monkeypatch):
    _init_test_db(db_path, monkeypatch)
    resp = client.get("/api/journal/executions/exec-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "exec-001"
    assert data["status"] == "ok"
    assert data["message"] == "帮我审查代码"


def test_execution_detail_404(client, db_path, monkeypatch):
    _init_test_db(db_path, monkeypatch)
    resp = client.get("/api/journal/executions/nonexistent")
    assert resp.status_code == 404
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python3 -m pytest tests/integration/test_journal_api.py -v`
Expected: FAIL (endpoints not defined)

- [ ] **Step 3: 实现后端接口**

在 `apps/ops/main.py` 末尾添加：

```python
# ── Journal — Audit Log ────────────────────────────────────────


@app.get("/api/journal/executions")
def list_executions(
    start_date: str | None = None,
    end_date: str | None = None,
    roles: str | None = None,
    depts: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _: bool = Depends(verify_api_key),
):
    """
    Query task executions with filters.
    - roles: comma-separated role names
    - depts: comma-separated department names
    - q: full-text search (LIKE %q% on message and summary)
    - limit: max 200
    """
    limit = min(limit, 200)
    conn = get_db()
    cur = conn.cursor()

    where_clauses = []
    params = []

    if start_date:
        where_clauses.append("created_at >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("created_at <= ?")
        params.append(end_date)
    if roles:
        role_list = [r.strip() for r in roles.split(",") if r.strip()]
        placeholders = ",".join("?" * len(role_list))
        where_clauses.append(f"role IN ({placeholders})")
        params.extend(role_list)
    if depts:
        dept_list = [d.strip() for d in depts.split(",") if d.strip()]
        placeholders = ",".join("?" * len(dept_list))
        where_clauses.append(f"dept IN ({placeholders})")
        params.extend(dept_list)
    if status:
        where_clauses.append("status = ?")
        params.append(status)
    if q:
        where_clauses.append("(message LIKE ? OR summary LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Count total
    cur.execute(f"SELECT COUNT(*) FROM task_executions WHERE {where_sql}", params)
    total = cur.fetchone()[0]

    # Fetch items
    cur.execute(
        f"""
        SELECT id, run_id, blueprint_id, alias, role, dept, message,
               status, token_input, token_completion, token_analysis,
               duration_ms, summary, created_at
        FROM task_executions
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    )
    rows = cur.fetchall()
    conn.close()

    items = [
        {
            "id": r[0],
            "runId": r[1],
            "blueprintId": r[2],
            "alias": r[3],
            "role": r[4],
            "dept": r[5],
            "message": r[6],
            "status": r[7],
            "tokenInput": r[8],
            "tokenCompletion": r[9],
            "tokenAnalysis": r[10],
            "tokenTotal": (r[8] or 0) + (r[9] or 0) + (r[10] or 0),
            "durationMs": r[11],
            "summary": r[12],
            "createdAt": r[13],
        }
        for r in rows
    ]
    return {"total": total, "items": items}


@app.get("/api/journal/executions/{exec_id}")
def get_execution(exec_id: str, _: bool = Depends(verify_api_key)):
    """Get a single execution by ID with full detail."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, run_id, blueprint_id, alias, role, dept, message,
               status, token_input, token_completion, token_analysis,
               duration_ms, summary, created_at
        FROM task_executions WHERE id = ?
        """,
        (exec_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Execution not found")
    return {
        "id": row[0],
        "runId": row[1],
        "blueprintId": row[2],
        "alias": row[3],
        "role": row[4],
        "dept": row[5],
        "message": row[6],
        "status": row[7],
        "tokenInput": row[8],
        "tokenCompletion": row[9],
        "tokenAnalysis": row[10],
        "tokenTotal": (row[8] or 0) + (row[9] or 0) + (row[10] or 0),
        "durationMs": row[11],
        "summary": row[12],
        "createdAt": row[13],
    }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python3 -m pytest tests/integration/test_journal_api.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: 提交**

```bash
git add apps/ops/main.py tests/integration/test_journal_api.py
git commit -m "feat(ops): add Journal API — list/detail executions with filters"
```

---

## Task 2: 前端 — JournalView.vue 布局 + 组件

**Files:**
- Create: `frontend/src/components/journal/ExecutionCard.vue`
- Create: `frontend/src/components/journal/ExecutionDetail.vue`
- Create: `frontend/src/components/journal/FilterBar.vue`
- Create: `frontend/src/composables/useJournal.js`
- Modify: `frontend/src/services/api.js`
- Modify: `frontend/src/views/JournalView.vue`

- [ ] **Step 1: 写 FilterBar 组件**

```vue
<!-- frontend/src/components/journal/FilterBar.vue -->
<script setup>
defineProps({
  filters: { type: Object, required: true },
  roles: { type: Array, default: () => [] },
  depts: { type: Array, default: () => [] },
});
defineEmits(['update:filters', 'search']);
</script>

<template>
  <div class="filter-bar">
    <div class="filter-row">
      <select :value="filters.status" @change="$emit('update:filters', { ...filters, status: $event.target.value })">
        <option value="">全部状态</option>
        <option value="ok">成功</option>
        <option value="error">失败</option>
      </select>
      <select :value="filters.role" @change="$emit('update:filters', { ...filters, role: $event.target.value })">
        <option value="">全部角色</option>
        <option v-for="r in roles" :key="r" :value="r">{{ r }}</option>
      </select>
      <select :value="filters.dept" @change="$emit('update:filters', { ...filters, dept: $event.target.value })">
        <option value="">全部部门</option>
        <option v-for="d in depts" :key="d" :value="d">{{ d }}</option>
      </select>
      <input
        type="text"
        class="search-input"
        placeholder="搜索输入/输出关键词..."
        :value="filters.q"
        @input="$emit('update:filters', { ...filters, q: $event.target.value })"
        @keyup.enter="$emit('search')"
      />
      <button class="btn btn-primary" @click="$emit('search')">搜索</button>
    </div>
  </div>
</template>

<style scoped>
.filter-bar { padding: 16px; border-bottom: 1px solid var(--border); }
.filter-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
select, .search-input {
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  background: var(--bg-surface);
  color: var(--text-primary);
}
.search-input { flex: 1; min-width: 180px; }
</style>
```

- [ ] **Step 2: 写 ExecutionCard 组件**

```vue
<!-- frontend/src/components/journal/ExecutionCard.vue -->
<script setup>
defineProps({
  item: { type: Object, required: true },
  selected: { type: Boolean, default: false },
});
defineEmits(['select']);
function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
}
</script>

<template>
  <div
    class="exec-card"
    :class="{ selected }"
    @click="$emit('select', item)"
  >
    <div class="card-header">
      <span class="time">{{ formatTime(item.createdAt) }}</span>
      <span class="alias">{{ item.alias }}</span>
      <span class="status-badge" :class="item.status">
        {{ item.status === 'ok' ? '✓' : '✗' }}
      </span>
    </div>
    <div class="card-body">
      <span class="role">{{ item.role }}</span>
      <span class="dept">{{ item.dept }}</span>
    </div>
    <div class="card-summary">{{ item.summary || item.message || '—' }}</div>
    <div class="card-meta">
      <span>{{ item.tokenTotal }} token</span>
      <span>{{ item.durationMs ? (item.durationMs / 1000).toFixed(1) + 's' : '—' }}</span>
    </div>
  </div>
</template>

<style scoped>
.exec-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  margin-bottom: 8px;
  transition: border-color 0.15s;
}
.exec-card:hover { border-color: var(--primary); }
.exec-card.selected { border-color: var(--primary); background: var(--bg-surface); }
.card-header { display: flex; gap: 8px; align-items: center; margin-bottom: 4px; }
.time { font-size: 12px; color: var(--text-disabled); }
.alias { font-weight: 600; font-size: 14px; flex: 1; }
.status-badge { font-size: 12px; font-weight: bold; }
.status-badge.ok { color: #38a169; }
.status-badge.error { color: #e53e3e; }
.card-body { display: flex; gap: 8px; font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }
.card-summary { font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-meta { display: flex; gap: 12px; font-size: 11px; color: var(--text-disabled); }
</style>
```

- [ ] **Step 3: 写 ExecutionDetail 组件**

```vue
<!-- frontend/src/components/journal/ExecutionDetail.vue -->
<script setup>
defineProps({
  item: { type: Object, default: null },
});
function fmt(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
}
</script>

<template>
  <div class="detail">
    <div v-if="!item" class="empty">选择一条记录查看详情</div>
    <template v-else>
      <div class="detail-header">
        <span class="status-badge" :class="item.status">
          {{ item.status === 'ok' ? '成功' : '失败' }}
        </span>
        <span class="time">{{ fmt(item.createdAt) }}</span>
      </div>
      <div class="detail-grid">
        <div class="field"><label>执行人</label><span>{{ item.alias }}</span></div>
        <div class="field"><label>角色</label><span>{{ item.role }}</span></div>
        <div class="field"><label>部门</label><span>{{ item.dept }}</span></div>
        <div class="field"><label>Blueprint</label><span>{{ item.blueprintId }}</span></div>
        <div class="field"><label>Token</label><span>{{ item.tokenInput }} in / {{ item.tokenCompletion }} out</span></div>
        <div class="field"><label>耗时</label><span>{{ item.durationMs ? (item.durationMs / 1000).toFixed(1) + 's' : '—' }}</span></div>
      </div>
      <div class="section">
        <label>原始输入</label>
        <pre class="content">{{ item.message }}</pre>
      </div>
      <div class="section">
        <label>输出摘要</label>
        <pre class="content">{{ item.summary }}</pre>
      </div>
    </template>
  </div>
</template>

<style scoped>
.detail { padding: 20px; }
.empty { color: var(--text-disabled); text-align: center; padding: 60px 0; font-size: 14px; }
.detail-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.status-badge { padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.status-badge.ok { background: #f0fff4; color: #38a169; }
.status-badge.error { background: #fff5f5; color: #e53e3e; }
.time { font-size: 12px; color: var(--text-disabled); }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
.field { display: flex; flex-direction: column; gap: 2px; }
.field label { font-size: 11px; color: var(--text-disabled); text-transform: uppercase; }
.field span { font-size: 13px; color: var(--text-primary); }
.section { margin-bottom: 16px; }
.section label { font-size: 11px; color: var(--text-disabled); text-transform: uppercase; display: block; margin-bottom: 4px; }
.content { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 6px; padding: 10px; font-size: 12px; white-space: pre-wrap; word-break: break-all; margin: 0; max-height: 200px; overflow-y: auto; }
</style>
```

- [ ] **Step 4: 写 useJournal.js composable**

```js
// frontend/src/composables/useJournal.js
import { ref, reactive } from 'vue';
import { journalApi } from '../services/api.js';

export function useJournal() {
  const executions = ref([]);
  const selected = ref(null);
  const total = ref(0);
  const loading = ref(false);

  const filters = reactive({
    roles: '',
    depts: '',
    status: '',
    q: '',
  });

  const roles = ['软件工程师', '法务专员', '行政专员', '合同专员'];
  const depts = ['技术研发部', '法务合规部', '综合管理部', '商务运营部'];

  async function fetchExecutions() {
    loading.value = true;
    try {
      const resp = await journalApi.list(filters);
      executions.value = resp.data.items;
      total.value = resp.data.total;
      if (executions.value.length > 0 && !selected.value) {
        selected.value = executions.value[0];
      }
    } finally {
      loading.value = false;
    }
  }

  function selectItem(item) {
    selected.value = item;
  }

  return { executions, selected, total, loading, filters, roles, depts, fetchExecutions, selectItem };
}
```

- [ ] **Step 5: 添加 journalApi 到 api.js**

在 `export const onboardingApi` 之后添加：

```javascript
export const journalApi = {
  list: (filters) =>
    api.get('/journal/executions', { params: filters }),
  get: (id) =>
    api.get(`/journal/executions/${id}`),
};
```

- [ ] **Step 6: 实现 JournalView.vue**

```vue
<!-- frontend/src/views/JournalView.vue -->
<script setup>
import { onMounted } from 'vue';
import { useJournal } from '../composables/useJournal.js';
import FilterBar from '../components/journal/FilterBar.vue';
import ExecutionCard from '../components/journal/ExecutionCard.vue';
import ExecutionDetail from '../components/journal/ExecutionDetail.vue';

const { executions, selected, total, loading, filters, roles, depts, fetchExecutions, selectItem } = useJournal();

onMounted(() => { fetchExecutions(); });
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">工作日记</h1>
        <p class="page-sub">操作审计 · 共 {{ total }} 条记录</p>
      </div>
    </div>
    <div class="journal-layout">
      <div class="left-panel">
        <FilterBar :filters="filters" :roles="roles" :depts="depts" @search="fetchExecutions" />
        <div class="card-list">
          <div v-if="loading" class="loading">加载中...</div>
          <div v-else-if="executions.length === 0" class="empty">暂无记录</div>
          <ExecutionCard
            v-for="item in executions"
            :key="item.id"
            :item="item"
            :selected="selected?.id === item.id"
            @select="selectItem"
          />
        </div>
      </div>
      <div class="right-panel">
        <ExecutionDetail :item="selected" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; margin: 0 auto; padding: var(--space-xl) var(--space-lg); min-height: calc(100vh - 56px); }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: var(--space-xl); }
.page-title { font-family: var(--font-serif); font-size: 24px; font-weight: 400; color: var(--text-primary); margin: 0 0 4px; }
.page-sub { font-size: 13px; color: var(--text-disabled); margin: 0; }
.journal-layout { display: flex; gap: 16px; height: calc(100vh - 160px); }
.left-panel { width: 400px; flex-shrink: 0; display: flex; flex-direction: column; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.right-panel { flex: 1; border: 1px solid var(--border); border-radius: 12px; overflow-y: auto; background: var(--bg-surface); }
.card-list { flex: 1; overflow-y: auto; padding: 12px; }
.loading, .empty { text-align: center; padding: 40px; color: var(--text-disabled); font-size: 14px; }
@media (max-width: 768px) { .journal-layout { flex-direction: column; height: auto; } .left-panel { width: 100%; } }
</style>
```

- [ ] **Step 7: 提交**

```bash
git add frontend/src/views/JournalView.vue frontend/src/composables/useJournal.js \
  frontend/src/components/journal/ frontend/src/services/api.js
git commit -m "feat(frontend): implement Journal page — left list + right detail layout"
```

---

## Task 3: 验收测试 — Playwright E2E

**Files:**
- Create: `frontend/tests/e2e/journal.page.ts`

- [ ] **Step 1: 写 E2E 测试**

```typescript
// frontend/tests/e2e/journal.page.ts
import { test, expect } from '@playwright/test';

test('Journal page loads with layout', async ({ page }) => {
  await page.goto('/journal');
  await expect(page.getByRole('heading', { name: '工作日记' })).toBeVisible();
  await expect(page.locator('.journal-layout')).toBeVisible();
  await expect(page.locator('.left-panel')).toBeVisible();
  await expect(page.locator('.right-panel')).toBeVisible();
});

test('Journal filter bar has all controls', async ({ page }) => {
  await page.goto('/journal');
  await expect(page.locator('select').first()).toBeVisible();
  await expect(page.locator('input.search-input')).toBeVisible();
  await expect(page.getByRole('button', { name: '搜索' })).toBeVisible();
});

test('Journal shows execution cards', async ({ page }) => {
  await page.goto('/journal');
  // Wait for loading to finish
  await page.waitForSelector('.exec-card', { timeout: 5000 });
  const cards = page.locator('.exec-card');
  await expect(cards.first()).toBeVisible();
  // Click a card and verify detail appears
  await cards.first().click();
  await expect(page.locator('.detail .detail-grid')).toBeVisible();
});
```

- [ ] **Step 2: 运行 E2E 测试**

Run: `cd frontend && npm run test` (需要 `USE_MOCK=false` 或 mock 数据)
Expected: Tests pass with mock data

- [ ] **Step 3: 提交**

```bash
git add frontend/tests/e2e/journal.page.ts
git commit -m "test(e2e): add Journal page E2E tests"
```

---

## 验证步骤

```bash
# 后端
cd apps/ops && python -m uvicorn apps.ops.main:app --reload
# 浏览器访问 http://localhost:8000/api/journal/executions （需 X-API-Key header）

# 前端
cd frontend && npm run dev
# 浏览器访问 http://localhost:5173/journal

# 全量测试
python3 -m pytest tests/integration/test_journal_api.py -v
```

## 注意事项

- 前端 API 调用使用 `USE_MOCK=false` 模式时需要正确的 `X-API-Key` header，E2E 测试需在 Playwright 配置中添加
- `task_executions.message` 字段可能为空，detail 组件需处理 `null`
- 列表卡片高度固定 + 右侧详情滚动，保证大列表时不卡
