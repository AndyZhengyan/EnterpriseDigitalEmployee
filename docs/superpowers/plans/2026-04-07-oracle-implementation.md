# Oracle 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Oracle 是 Avatar 的长期记忆中心。按知识主题组织档案，档案以 Markdown 文件存储于 `data/oracle/` 目录，支持手工上传 md 文件和 Markdown 内容渲染。

**Architecture:** 档案存储在文件系统（`data/oracle/`），按 `avatar/` 和 `import/` 两个子目录分类。Ops API 扫描目录提供索引，并读取 md 文件内容。无需新建数据库表。

**Tech Stack:** FastAPI（apps/ops）、Vue 3、Axios、marked（Markdown 渲染）

---

## 文件结构

```
apps/ops/main.py              — 新增 /api/oracle/archives 路由
data/oracle/                 — 档案存储目录（新建）
data/oracle/avatar/          — Avatar 记忆 md 文件
data/oracle/import/          — 导入档案 md 文件
frontend/src/services/api.js  — 新增 oracleApi
frontend/src/views/OracleView.vue — 档案中心页面
frontend/src/composables/useOracle.js  — oracle 状态管理 composable
frontend/src/components/oracle/ArchiveCard.vue   — 档案卡片组件
frontend/src/components/oracle/ArchiveDetail.vue  — 档案详情组件（Markdown 渲染）
tests/integration/test_oracle_api.py  — oracle API 测试
```

---

## Task 1: 后端 — Oracle API 接口

**Files:**
- Modify: `apps/ops/main.py`（在 journal 路由之后添加 oracle 路由）
- Create: `tests/integration/test_oracle_api.py`

- [ ] **Step 1: 写测试**

```python
# tests/integration/test_oracle_api.py
"""Integration tests for Oracle API — archives via filesystem."""
import os, pytest


def _init_oracle_dir(tmp_path):
    """Create oracle directory structure with sample archives."""
    oracle_dir = tmp_path / "oracle"
    avatar_dir = oracle_dir / "avatar"
    import_dir = oracle_dir / "import"
    avatar_dir.mkdir(parents=True)
    import_dir.mkdir(parents=True)
    # Avatar archive
    (avatar_dir / "合同风险识别.md").write_text(
        "---\ntitle: 合同风险识别\nsource: avatar\ncontributor: 明律\ncreated_at: 2026-04-07\ntags: [合同, 法务]\n---\n\n# 合同风险识别\n\n这份档案记录了明律Avatar在合同审阅任务中积累的风险识别经验。"
    )
    # Import archive
    (import_dir / "采购流程规范.md").write_text(
        "---\ntitle: 采购流程规范\nsource: import\ncontributor: 管理员\ncreated_at: 2026-04-06\ntags: [采购, 流程]\n---\n\n# 采购流程规范\n\n企业采购流程标准操作规程。"
    )
    return oracle_dir


def _init_test_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ORACLE_DIR", str(tmp_path / "oracle"))
    monkeypatch.setenv("OPS_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("PIAGENT_CLI_STUB", "true")
    from apps.ops import main as ops_main
    ops_main._runner_active = False
    from apps.ops.db import init_db
    init_db()
    ops_main._init_key_manager(str(tmp_path / "ops.db"))
    ops_main._force_dev_mode()
    from fastapi.testclient import TestClient
    from apps.ops.main import app
    return TestClient(app)


def test_list_archives(tmp_path, monkeypatch):
    _init_oracle_dir(tmp_path)
    client = _init_test_app(tmp_path, monkeypatch)
    resp = client.get("/api/oracle/archives")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    titles = [a["title"] for a in data["items"]]
    assert "合同风险识别" in titles
    assert "采购流程规范" in titles


def test_list_archives_filter_by_source(tmp_path, monkeypatch):
    _init_oracle_dir(tmp_path)
    client = _init_test_app(tmp_path, monkeypatch)
    resp = client.get("/api/oracle/archives?source=avatar")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "合同风险识别"


def test_get_archive_detail(tmp_path, monkeypatch):
    _init_oracle_dir(tmp_path)
    client = _init_test_app(tmp_path, monkeypatch)
    resp = client.get("/api/oracle/archives/%E5%90%88%E5%90%8C%E9%A3%8E%E9%99%A9%E8%AF%86%E5%88%AB")
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["title"] == "合同风险识别"
    assert "合同风险识别" in data["content"]


def test_get_archive_not_found(tmp_path, monkeypatch):
    _init_oracle_dir(tmp_path)
    client = _init_test_app(tmp_path, monkeypatch)
    resp = client.get("/api/oracle/archives/nonexistent-档案")
    assert resp.status_code == 404
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python3 -m pytest tests/integration/test_oracle_api.py -v`
Expected: FAIL (routes not defined)

- [ ] **Step 3: 初始化示例档案目录结构**

```bash
mkdir -p data/oracle/avatar data/oracle/import
```

创建示例档案文件：

```
data/oracle/avatar/合同风险识别.md
data/oracle/avatar/供应商管理.md
data/oracle/import/采购流程规范.md
```

每个文件包含 Frontmatter + Markdown 内容（见数据模型）。

- [ ] **Step 4: 实现后端接口**

在 `apps/ops/main.py` 添加：

```python
# ── Oracle — Avatar 长期记忆中心 ──────────────────────────────


ORACLE_DIR = Path(os.environ.get("ORACLE_DIR", str(BASE_DIR / "data" / "oracle")))


def _read_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content. Returns (meta, body)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}, content
    import yaml
    meta = yaml.safe_load(content[4:end]) or {}
    body = content[end + 5 :]
    return meta, body


def _scan_archives() -> list[dict]:
    """Scan data/oracle/ directory and return list of archive metadata."""
    archives = []
    for source_dir in ("avatar", "import"):
        dir_path = ORACLE_DIR / source_dir
        if not dir_path.is_dir():
            continue
        for md_file in dir_path.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            meta, _ = _read_frontmatter(content)
            slug = md_file.stem  # filename without extension
            archives.append(
                {
                    "id": slug,
                    "title": meta.get("title", slug),
                    "source": source_dir,
                    "contributor": meta.get("contributor", ""),
                    "createdAt": meta.get("created_at", ""),
                    "tags": meta.get("tags", []),
                    "path": str(md_file.relative_to(ORACLE_DIR)),
                }
            )
    return sorted(archives, key=lambda a: a.get("createdAt", ""), reverse=True)


@app.get("/api/oracle/archives")
def list_archives(
    source: str | None = None,
    _: bool = Depends(verify_api_key),
):
    """List all archives. Optionally filter by source (avatar | import)."""
    all_archives = _scan_archives()
    if source:
        all_archives = [a for a in all_archives if a["source"] == source]
    return {"total": len(all_archives), "items": all_archives}


@app.get("/api/oracle/archives/{archive_id}")
def get_archive(archive_id: str, _: bool = Depends(verify_api_key)):
    """Get archive content by ID (slug = filename without .md)."""
    archive_id = unquote(archive_id)  # decode URL-encoded slug
    for source_dir in ("avatar", "import"):
        file_path = ORACLE_DIR / source_dir / f"{archive_id}.md"
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            meta, body = _read_frontmatter(content)
            return {
                "meta": {
                    "id": archive_id,
                    "title": meta.get("title", archive_id),
                    "source": source_dir,
                    "contributor": meta.get("contributor", ""),
                    "createdAt": meta.get("created_at", ""),
                    "tags": meta.get("tags", []),
                },
                "content": body.strip(),
            }
    raise HTTPException(status_code=404, detail="Archive not found")


@app.post("/api/oracle/archives/upload")
def upload_archive(
    req: dict,
    _: bool = Depends(verify_api_key),
):
    """Upload a markdown file as an archive.
    Body: { title, source: 'avatar'|'import', content: markdown_string, contributor: str }
    """
    title = req.get("title", "").strip()
    source = req.get("source", "import")
    content_body = req.get("content", "")
    contributor = req.get("contributor", "管理员")
    import datetime
    created_at = datetime.date.today().isoformat()

    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    if source not in ("avatar", "import"):
        raise HTTPException(status_code=400, detail="source must be 'avatar' or 'import'")

    slug = title  # simple slug: use title as filename
    safe_slug = re.sub(r"[^\w\s-]", "", slug).replace(" ", "-")
    file_path = ORACLE_DIR / source / f"{safe_slug}.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    frontmatter = f"---\ntitle: {title}\nsource: {source}\ncontributor: {contributor}\ncreated_at: {created_at}\ntags: []\n---\n\n"
    file_path.write_text(frontmatter + content_body, encoding="utf-8")

    return {
        "id": safe_slug,
        "path": str(file_path.relative_to(ORACLE_DIR)),
        "message": "上传成功",
    }
```

在文件顶部添加导入（如果尚未存在）：

```python
from urllib.parse import unquote
import re
```

依赖：`PyYAML`（用于 frontmatter 解析），检查是否已安装：

```bash
python3 -c "import yaml; print('ok')"
```

如果报错需添加到依赖。

- [ ] **Step 5: 运行测试验证通过**

Run: `python3 -m pytest tests/integration/test_oracle_api.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: 提交**

```bash
git add apps/ops/main.py tests/integration/test_oracle_api.py data/oracle/
git commit -m "feat(ops): add Oracle API — archive list/detail/upload via filesystem"
```

---

## Task 2: 前端 — OracleView.vue + 组件

**Files:**
- Create: `frontend/src/components/oracle/ArchiveCard.vue`
- Create: `frontend/src/components/oracle/ArchiveDetail.vue`
- Create: `frontend/src/composables/useOracle.js`
- Modify: `frontend/src/services/api.js`
- Modify: `frontend/src/views/OracleView.vue`
- Modify: `frontend/package.json` — 添加 marked 依赖

- [ ] **Step 1: 添加 marked 依赖**

```bash
cd frontend && npm install marked
```

修改 `package.json` 确保依赖包含：

```json
"dependencies": {
  ...
  "marked": "^12.0.0"
}
```

- [ ] **Step 2: 写 ArchiveCard 组件**

```vue
<!-- frontend/src/components/oracle/ArchiveCard.vue -->
<script setup>
defineProps({
  archive: { type: Object, required: true },
  selected: { type: Boolean, default: false },
});
defineEmits(['select']);
function sourceLabel(src) { return src === 'avatar' ? 'Avatar 记忆' : '导入档案'; }
</script>

<template>
  <div class="archive-card" :class="{ selected }" @click="$emit('select', archive)">
    <div class="card-header">
      <span class="source-tag" :class="archive.source">{{ sourceLabel(archive.source) }}</span>
    </div>
    <div class="card-title">{{ archive.title }}</div>
    <div class="card-meta">
      <span>{{ archive.contributor }}</span>
      <span>{{ archive.createdAt }}</span>
    </div>
    <div class="card-tags">
      <span v-for="tag in (archive.tags || [])" :key="tag" class="tag">{{ tag }}</span>
    </div>
  </div>
</template>

<style scoped>
.archive-card { border: 1px solid var(--border); border-radius: 8px; padding: 12px; cursor: pointer; margin-bottom: 8px; transition: border-color 0.15s; }
.archive-card:hover { border-color: var(--primary); }
.archive-card.selected { border-color: var(--primary); background: var(--bg-surface); }
.card-header { margin-bottom: 6px; }
.source-tag { font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: 500; }
.source-tag.avatar { background: #e8f4fd; color: #2176ff; }
.source-tag.import { background: #f0fff4; color: #38a169; }
.card-title { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
.card-meta { display: flex; gap: 8px; font-size: 12px; color: var(--text-disabled); margin-bottom: 6px; }
.card-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.tag { font-size: 11px; padding: 1px 6px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 4px; color: var(--text-secondary); }
</style>
```

- [ ] **Step 3: 写 ArchiveDetail 组件（含 Markdown 渲染）**

```vue
<!-- frontend/src/components/oracle/ArchiveDetail.vue -->
<script setup>
import { computed } from 'vue';
import { marked } from 'marked';

const props = defineProps({
  archive: { type: Object, default: null },
});
const rendered = computed(() => {
  if (!props.archive?.content) return '';
  return marked(props.archive.content);
});
function sourceLabel(src) { return src === 'avatar' ? 'Avatar 记忆' : '导入档案'; }
</script>

<template>
  <div class="detail">
    <div v-if="!archive" class="empty">选择一份档案查看内容</div>
    <template v-else>
      <div class="detail-header">
        <span class="source-tag" :class="archive.meta.source">{{ sourceLabel(archive.meta.source) }}</span>
        <h1 class="title">{{ archive.meta.title }}</h1>
        <div class="meta-row">
          <span>{{ archive.meta.contributor }}</span>
          <span>{{ archive.meta.createdAt }}</span>
        </div>
        <div class="tags" v-if="archive.meta.tags?.length">
          <span v-for="tag in archive.meta.tags" :key="tag" class="tag">{{ tag }}</span>
        </div>
      </div>
      <div class="content" v-html="rendered"></div>
    </template>
  </div>
</template>

<style scoped>
.detail { padding: 20px; }
.empty { color: var(--text-disabled); text-align: center; padding: 60px 0; font-size: 14px; }
.detail-header { margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 16px; }
.source-tag { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 500; display: inline-block; margin-bottom: 8px; }
.source-tag.avatar { background: #e8f4fd; color: #2176ff; }
.source-tag.import { background: #f0fff4; color: #38a169; }
.title { font-family: var(--font-serif); font-size: 22px; font-weight: 400; margin: 0 0 8px; }
.meta-row { display: flex; gap: 16px; font-size: 12px; color: var(--text-disabled); margin-bottom: 8px; }
.tags { display: flex; gap: 6px; flex-wrap: wrap; }
.tag { font-size: 11px; padding: 2px 8px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 4px; color: var(--text-secondary); }
.content { font-size: 14px; line-height: 1.7; color: var(--text-primary); }
.content :deep(h1), .content :deep(h2), .content :deep(h3) { font-family: var(--font-serif); margin-top: 24px; margin-bottom: 8px; }
.content :deep(code) { background: var(--bg-surface); padding: 2px 6px; border-radius: 4px; font-size: 13px; }
.content :deep(pre) { background: var(--bg-surface); padding: 12px; border-radius: 8px; overflow-x: auto; }
.content :deep(p) { margin-bottom: 12px; }
</style>
```

- [ ] **Step 4: 写 useOracle.js composable**

```js
// frontend/src/composables/useOracle.js
import { ref } from 'vue';
import { oracleApi } from '../services/api.js';

export function useOracle() {
  const archives = ref([]);
  const selected = ref(null);
  const total = ref(0);
  const loading = ref(false);
  const activeSource = ref('');  // '' | 'avatar' | 'import'

  async function fetchArchives(source = '') {
    loading.value = true;
    activeSource.value = source;
    try {
      const params = source ? { source } : {};
      const resp = await oracleApi.list(params);
      archives.value = resp.data.items;
      total.value = resp.data.total;
    } finally {
      loading.value = false;
    }
  }

  async function selectArchive(archive) {
    selected.value = null;  // clear while loading
    const resp = await oracleApi.get(archive.id);
    selected.value = resp.data;
  }

  return { archives, selected, total, loading, activeSource, fetchArchives, selectArchive };
}
```

- [ ] **Step 5: 添加 oracleApi 到 api.js**

在 `export const journalApi` 之后添加：

```javascript
export const oracleApi = {
  list: (params) => api.get('/oracle/archives', { params }),
  get: (id) => api.get(`/oracle/archives/${encodeURIComponent(id)}`),
  upload: (payload) => api.post('/oracle/archives/upload', payload),
};
```

- [ ] **Step 6: 实现 OracleView.vue**

```vue
<!-- frontend/src/views/OracleView.vue -->
<script setup>
import { onMounted, ref } from 'vue';
import { useOracle } from '../composables/useOracle.js';
import ArchiveCard from '../components/oracle/ArchiveCard.vue';
import ArchiveDetail from '../components/oracle/ArchiveDetail.vue';

const { archives, selected, total, loading, activeSource, fetchArchives, selectArchive } = useOracle();

onMounted(() => { fetchArchives(); });

function setSource(src) {
  if (activeSource.value === src) {
    fetchArchives('');  // toggle off
  } else {
    fetchArchives(src);
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">档案中心</h1>
        <p class="page-sub">Avatar 长期记忆 · 共 {{ total }} 份档案</p>
      </div>
    </div>
    <div class="oracle-layout">
      <div class="left-panel">
        <div class="source-filters">
          <button
            class="filter-btn"
            :class="{ active: activeSource === '' }"
            @click="setSource('')"
          >全部</button>
          <button
            class="filter-btn"
            :class="{ active: activeSource === 'avatar' }"
            @click="setSource('avatar')"
          >Avatar 记忆</button>
          <button
            class="filter-btn"
            :class="{ active: activeSource === 'import' }"
            @click="setSource('import')"
          >导入档案</button>
        </div>
        <div class="card-list">
          <div v-if="loading" class="loading">加载中...</div>
          <div v-else-if="archives.length === 0" class="empty">暂无档案</div>
          <ArchiveCard
            v-for="a in archives"
            :key="a.id"
            :archive="a"
            :selected="selected?.meta?.id === a.id"
            @select="selectArchive"
          />
        </div>
      </div>
      <div class="right-panel">
        <ArchiveDetail :archive="selected" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; margin: 0 auto; padding: var(--space-xl) var(--space-lg); min-height: calc(100vh - 56px); }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: var(--space-xl); }
.page-title { font-family: var(--font-serif); font-size: 24px; font-weight: 400; color: var(--text-primary); margin: 0 0 4px; }
.page-sub { font-size: 13px; color: var(--text-disabled); margin: 0; }
.oracle-layout { display: flex; gap: 16px; height: calc(100vh - 160px); }
.left-panel { width: 360px; flex-shrink: 0; display: flex; flex-direction: column; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.source-filters { display: flex; padding: 12px; gap: 6px; border-bottom: 1px solid var(--border); }
.filter-btn { padding: 4px 12px; border-radius: 16px; border: 1px solid var(--border); background: transparent; font-size: 13px; cursor: pointer; color: var(--text-secondary); }
.filter-btn.active { background: var(--primary); color: white; border-color: var(--primary); }
.card-list { flex: 1; overflow-y: auto; padding: 12px; }
.loading, .empty { text-align: center; padding: 40px; color: var(--text-disabled); font-size: 14px; }
.right-panel { flex: 1; border: 1px solid var(--border); border-radius: 12px; overflow-y: auto; background: var(--bg-surface); }
@media (max-width: 768px) { .oracle-layout { flex-direction: column; height: auto; } .left-panel { width: 100%; } }
</style>
```

- [ ] **Step 7: 提交**

```bash
git add frontend/src/views/OracleView.vue \
  frontend/src/composables/useOracle.js \
  frontend/src/components/oracle/ \
  frontend/src/services/api.js \
  frontend/package.json
git commit -m "feat(frontend): implement Oracle page — archive list + Markdown detail"
```

---

## Task 3: 验收测试 — Playwright E2E

**Files:**
- Create: `frontend/tests/e2e/oracle.page.ts`

- [ ] **Step 1: 写 E2E 测试**

```typescript
// frontend/tests/e2e/oracle.page.ts
import { test, expect } from '@playwright/test';

test('Oracle page loads with layout', async ({ page }) => {
  await page.goto('/oracle');
  await expect(page.getByRole('heading', { name: '档案中心' })).toBeVisible();
  await expect(page.locator('.oracle-layout')).toBeVisible();
});

test('Oracle source filter buttons work', async ({ page }) => {
  await page.goto('/oracle');
  await page.waitForSelector('.archive-card', { timeout: 5000 });
  const avatarBtn = page.getByRole('button', { name: 'Avatar 记忆' });
  await avatarBtn.click();
  // Should filter to avatar-only archives
  const cards = page.locator('.archive-card');
  await expect(cards.first()).toBeVisible();
});

test('Oracle archive detail renders markdown', async ({ page }) => {
  await page.goto('/oracle');
  await page.waitForSelector('.archive-card', { timeout: 5000 });
  await page.locator('.archive-card').first().click();
  await expect(page.locator('.detail .content')).toBeVisible();
});
```

- [ ] **Step 2: 提交**

```bash
git add frontend/tests/e2e/oracle.page.ts
git commit -m "test(e2e): add Oracle page E2E tests"
```

---

## 验证步骤

```bash
# 后端
cd apps/ops && python -m uvicorn apps.ops.main:app --reload
# curl http://localhost:8000/api/oracle/archives (需 X-API-Key)

# 前端
cd frontend && npm install && npm run dev
# 浏览器访问 http://localhost:5173/oracle

# 全量测试
python3 -m pytest tests/integration/test_oracle_api.py -v
```
