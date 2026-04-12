# Onboarding + Enablement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite Onboarding page as left-sidebar + right-tab wizard, implement Enablement Tools 货架 with CRUD, and add backend APIs that assemble structured config into OpenClaw file format.

**Architecture:**
- Backend: FastAPI on port 8006. Exposes APIs for Tools CRUD and Avatar config read/write. On save, assembles structured data into OpenClaw markdown files and writes to `~/.openclaw/agents/<agent-id>/agent/`.
- Frontend: Vue 3 with Pinia-like composables. Onboarding view rebuilt as split-panel with 4 tabs. Enablement view rebuilt as Tools 货架 list.
- Database: SQLite `ops.db` extended with `tools` table and enriched `blueprints` table for avatar config.

**Tech Stack:** FastAPI, SQLite, Vue 3, Axios, OpenClaw filesystem

---

## Task 1: Backend — Tools Registry Table & API

**Files:**
- Modify: `apps/ops/db.py` — add `tools` table + seed data
- Create: `apps/ops/tools_registry.py` — tools CRUD logic
- Modify: `apps/ops/main.py` — add `/api/enablement/tools` routes
- Modify: `frontend/src/services/api.js` — add `toolsApi`

- [ ] **Step 1: Add `tools` table to `apps/ops/db.py`**

Find the `init_db()` function in `apps/ops/db.py`. After the `blueprints` table creation, add:

```python
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tools (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        created_at TEXT
    );
    """)
```

- [ ] **Step 2: Add seed function for OpenClaw built-in tools in `apps/ops/db.py`**

After the `seed_data()` function, add:

```python
OPENCLAW_BUILTIN_TOOLS = [
    ("exec", "运行 Shell 命令，管理后台进程"),
    ("code_execution", "沙箱远程 Python 分析"),
    ("browser", "控制 Chromium 浏览器"),
    ("web_search", "网络搜索"),
    ("web_fetch", "抓取网页内容"),
    ("read", "读取文件内容"),
    ("write", "写入文件内容"),
    ("edit", "编辑文件内容"),
    ("apply_patch", "多区块文件补丁"),
    ("message", "跨渠道发送消息"),
    ("canvas", "Node Canvas 控制"),
    ("nodes", "发现和定位配对设备"),
    ("cron", "定时任务管理"),
    ("gateway", "网关操作"),
    ("image", "图片分析/生成"),
    ("music_generate", "音乐生成"),
    ("video_generate", "视频生成"),
    ("tts", "文字转语音"),
    ("subagents", "子 Agent 管理"),
    ("session_status", "会话状态查询"),
]

def seed_tools():
    """Seed OpenClaw built-in tools if tools table is empty."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tools")
    if cur.fetchone()[0] > 0:
        conn.close()
        return
    for name, description in OPENCLAW_BUILTIN_TOOLS:
        cur.execute(
            "INSERT OR IGNORE INTO tools (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (name, name, description, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        )
    conn.commit()
    conn.close()
```

Call `seed_tools()` at the end of `init_db()`.

- [ ] **Step 3: Add tools CRUD functions in `apps/ops/tools_registry.py`**

Create `apps/ops/tools_registry.py`:

```python
# apps/ops/tools_registry.py
from apps.ops.db import get_db

def list_tools():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, description, created_at FROM tools ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "description": r[2], "created_at": r[3]} for r in rows]

def create_tool(name: str, description: str) -> dict:
    import uuid
    from datetime import datetime, timezone
    conn = get_db()
    cur = conn.cursor()
    tool_id = f"custom-{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur.execute(
        "INSERT INTO tools (id, name, description, created_at) VALUES (?, ?, ?, ?)",
        (tool_id, name, description, created_at),
    )
    conn.commit()
    conn.close()
    return {"id": tool_id, "name": name, "description": description, "created_at": created_at}

def update_tool(tool_id: str, description: str) -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE tools SET description = ? WHERE id = ?", (description, tool_id))
    conn.commit()
    cur.execute("SELECT id, name, description, created_at FROM tools WHERE id = ?", (tool_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "description": row[2], "created_at": row[3]}

def delete_tool(tool_id: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0
```

- [ ] **Step 4: Add tools API routes in `apps/ops/main.py`**

Find the `@app.get("/health")` route near the top of `apps/ops/main.py`. Add this block after it:

```python
from apps.ops.tools_registry import list_tools, create_tool, update_tool, delete_tool

@app.get("/enablement/tools")
def get_tools():
    return list_tools()

@app.post("/enablement/tools")
def post_tools(req: dict):
    name = req.get("name", "").strip()
    description = req.get("description", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    return create_tool(name, description)

@app.put("/enablement/tools/{tool_id}")
def put_tools(tool_id: str, req: dict):
    description = req.get("description", "").strip()
    result = update_tool(tool_id, description)
    if not result:
        raise HTTPException(status_code=404, detail="Tool not found")
    return result

@app.delete("/enablement/tools/{tool_id}")
def del_tools(tool_id: str):
    if not delete_tool(tool_id):
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"message": "deleted"}
```

- [ ] **Step 5: Add frontend `toolsApi` to `frontend/src/services/api.js`**

Find the `export const oracleApi` block. Add before it:

```javascript
export const toolsApi = {
  list: () => api.get('/enablement/tools'),
  create: (payload) => api.post('/enablement/tools', payload),
  update: (id, payload) => api.put(`/enablement/tools/${id}`, payload),
  delete: (id) => api.delete(`/enablement/tools/${id}`),
};
```

- [ ] **Step 6: Run backend and verify tools API**

Start the backend:
```bash
python -m apps.ops.main &
```

Test:
```bash
curl http://localhost:8006/enablement/tools | python -m json.tool
```

Expected: JSON array of 20 built-in tools.

- [ ] **Step 7: Commit**

```bash
git add apps/ops/db.py apps/ops/tools_registry.py apps/ops/main.py frontend/src/services/api.js
git commit -m "feat(enablement): tools registry CRUD API and OpenClaw seed data"
```

---

## Task 2: Backend — Avatar Config Assembly (Write OpenClaw Files)

**Files:**
- Create: `apps/ops/avatar_assembler.py` — assemble structured config into OpenClaw .md files
- Modify: `apps/ops/db.py` — add avatar config fields to blueprints table or new table
- Modify: `apps/ops/main.py` — add avatar config read/write endpoints

- [ ] **Step 1: Check current blueprints table schema in `apps/ops/db.py`**

Find the `CREATE TABLE IF NOT EXISTS blueprints` block. Note the existing columns: `id`, `role`, `alias`, `department`, `versions`, `capacity`.

We need to extend blueprints with avatar config fields: `openclaw_agent_id`, `soul_content`, `agents_content`, `tools_enabled` (JSON array of tool names), `user_content`, `selected_model`.

- [ ] **Step 2: Add avatar config columns to `blueprints` table in `apps/ops/db.py`**

After the `CREATE TABLE IF NOT EXISTS blueprints` block, add migration:

```python
    cur.execute("ALTER TABLE blueprints ADD COLUMN openclaw_agent_id TEXT");
    cur.execute("ALTER TABLE blueprints ADD COLUMN soul_content TEXT DEFAULT ''");
    cur.execute("ALTER TABLE blueprints ADD COLUMN agents_content TEXT DEFAULT ''");
    cur.execute("ALTER TABLE blueprints ADD COLUMN user_content TEXT DEFAULT ''");
    cur.execute("ALTER TABLE blueprints ADD COLUMN tools_enabled TEXT DEFAULT '[]'")  # JSON
    cur.execute("ALTER TABLE blueprints ADD COLUMN selected_model TEXT DEFAULT ''")
```

Wrap each in try/except to handle already-exists gracefully:
```python
    try:
        cur.execute("ALTER TABLE blueprints ADD COLUMN openclaw_agent_id TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists
```

- [ ] **Step 3: Add avatar config read/write functions in `apps/ops/db.py`**

After the `seed_tools()` function, add:

```python
def get_blueprint_config(bp_id: str):
    """Return full avatar config for a blueprint."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT id, role, alias, department, openclaw_agent_id,
                  soul_content, agents_content, user_content,
                  tools_enabled, selected_model
           FROM blueprints WHERE id = ?""",
        (bp_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    import json
    return {
        "id": row[0], "role": row[1], "alias": row[2], "department": row[3],
        "openclaw_agent_id": row[4] or row[0],
        "soul_content": row[5] or "", "agents_content": row[6] or "",
        "user_content": row[7] or "", "tools_enabled": json.loads(row[8] or "[]"),
        "selected_model": row[9] or "",
    }

def save_blueprint_config(bp_id: str, config: dict):
    """Save avatar config fields for a blueprint."""
    import json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE blueprints SET
          soul_content = ?, agents_content = ?, user_content = ?,
          tools_enabled = ?, selected_model = ?
        WHERE id = ?
    """, (
        config.get("soul_content", ""),
        config.get("agents_content", ""),
        config.get("user_content", ""),
        json.dumps(config.get("tools_enabled", [])),
        config.get("selected_model", ""),
        bp_id,
    ))
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Create `apps/ops/avatar_assembler.py`**

Create this file:

```python
# apps/ops/avatar_assembler.py
# Assemble structured avatar config into OpenClaw .md files
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

OPENCLAW_DIR = Path(os.environ.get("OPENCLAW_DIR", str(Path.home() / ".openclaw")))
AGENTS_DIR = OPENCLAW_DIR / "agents"

def _backup_file(filepath: Path):
    """Create timestamped backup before writing."""
    if filepath.exists():
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_path = filepath.parent / f"{filepath.name}.backup.{ts}"
        shutil.copy2(filepath, backup_path)

def _ensure_agent_dir(agent_id: str) -> Path:
    agent_dir = AGENTS_DIR / agent_id / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    return agent_dir

def assemble_identity(config: dict) -> str:
    """Assemble IDENTITY.md content."""
    return f"""# IDENTITY.md

> {config.get('alias', '')}（{config.get('role', '')}）。{config.get('department', '')}。

---

## Core Identity [LOCKED]

**Name:** {config.get('alias', '')}
**Role:** {config.get('role', '')}
**Department:** {config.get('department', '')}
**Blueprint ID:** {config.get('id', '')}

"""

def assemble_soul(config: dict) -> str:
    """Assemble SOUL.md content from soul_content field."""
    content = config.get("soul_content", "")
    if content:
        return content
    # Default minimal SOUL from identity
    return f"""# SOUL.md — Who I Am

> {config.get('alias', '')}（{config.get('role', '')}）。

---

## Core Identity [LOCKED]

**Name:** {config.get('alias', '')}
**Role:** {config.get('role', '')}
**Department:** {config.get('department', '')}

"""

def assemble_agents(config: dict) -> str:
    """Assemble AGENTS.md from agents_content or use minimal default."""
    content = config.get("agents_content", "")
    if content:
        return content
    return """# AGENTS.md — Constitution

> This file is your operating law.

## Session Protocol

1. Read `SOUL.md` — this is who you are
2. Read `USER.md` — this is who you are helping
3. Read `memory/` — recent context

"""

def assemble_user(config: dict) -> str:
    """Assemble USER.md from user_content."""
    content = config.get("user_content", "")
    if content:
        return content
    return f"""# USER.md

**称呼:** 用户
**时区:** Asia/Shanghai

## 沟通偏好

- 结论先行
- 简洁直接

"""

def assemble_tools(config: dict) -> str:
    """Assemble TOOLS.md with enabled tools list."""
    tools = config.get("tools_enabled", [])
    if not tools:
        return "# TOOLS.md\n\nNo tools enabled.\n"
    lines = ["# TOOLS.md\n", "## 已启用工具\n"]
    for tool in tools:
        lines.append(f"- **{tool}**")
    return "\n".join(lines) + "\n"

def write_avatar_files(config: dict):
    """Write all OpenClaw .md files for an avatar."""
    agent_id = config.get("openclaw_agent_id") or config.get("id")
    agent_dir = _ensure_agent_dir(agent_id)

    files = {
        "IDENTITY.md": assemble_identity(config),
        "SOUL.md": assemble_soul(config),
        "AGENTS.md": assemble_agents(config),
        "USER.md": assemble_user(config),
        "TOOLS.md": assemble_tools(config),
    }

    for filename, content in files.items():
        filepath = agent_dir / filename
        _backup_file(filepath)
        filepath.write_text(content, encoding="utf-8")

def get_assembled_config(agent_id: str) -> dict:
    """Read current .md files and return as structured dict."""
    agent_dir = AGENTS_DIR / agent_id / "agent"
    def read_md(name):
        p = agent_dir / name
        return p.read_text(encoding="utf-8") if p.exists() else ""

    return {
        "soul_content": read_md("SOUL.md"),
        "agents_content": read_md("AGENTS.md"),
        "user_content": read_md("USER.md"),
    }
```

- [ ] **Step 5: Add avatar config API endpoints in `apps/ops/main.py`**

Add imports:
```python
from apps.ops.avatar_assembler import write_avatar_files, get_assembled_config
from apps.ops.db import get_blueprint_config, save_blueprint_config
```

Add these routes (find a logical spot, e.g. near the onboarding blueprints routes):

```python
@app.get("/onboarding/blueprints/{bp_id}/config")
def get_avatar_config(bp_id: str, _: bool = Depends(verify_api_key)):
    """Get full avatar config for a blueprint, merging DB fields + assembled files."""
    db_config = get_blueprint_config(bp_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    # Merge with live file content
    agent_id = db_config.get("openclaw_agent_id") or bp_id
    file_content = get_assembled_config(agent_id)
    return {**db_config, **file_content}

@app.put("/onboarding/blueprints/{bp_id}/config")
def put_avatar_config(bp_id: str, config: dict, _: bool = Depends(verify_api_key)):
    """Save avatar config to DB and write OpenClaw .md files."""
    db_config = get_blueprint_config(bp_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    # Save structured fields to DB
    save_blueprint_config(bp_id, config)
    # Assemble and write to OpenClaw files
    full_config = {**db_config, **config}
    write_avatar_files(full_config)
    return {"message": "saved", "blueprint_id": bp_id}
```

- [ ] **Step 6: Test avatar config API**

```bash
curl http://localhost:8006/onboarding/blueprints/av-admin-001/config \
  -H "X-API-Key: $(cat ~/.openclaw/.ops_api_key 2>/dev/null || echo test)"
```

Expected: JSON with soul_content, agents_content, etc.

```bash
curl -X PUT http://localhost:8006/onboarding/blueprints/av-admin-001/config \
  -H "X-API-Key: $(cat ~/.openclaw/.ops_api_key 2>/dev/null || echo test)" \
  -H "Content-Type: application/json" \
  -d '{"soul_content": "# SOUL.md\\n\\nTest soul content"}'
```

Then check: `cat ~/.openclaw/agents/av-admin-001/agent/SOUL.md`

- [ ] **Step 7: Commit**

```bash
git add apps/ops/db.py apps/ops/avatar_assembler.py apps/ops/main.py
git commit -m "feat(onboarding): avatar config assembly → OpenClaw .md files"
```

---

## Task 3: Frontend — Enablement Tools 货架

**Files:**
- Create: `frontend/src/composables/useTools.js`
- Modify: `frontend/src/views/EnablementView.vue` — rebuild as tools 货架
- Modify: `frontend/src/components/layout/TopNav.vue` — update nav label

- [ ] **Step 1: Create `frontend/src/composables/useTools.js`**

```javascript
// frontend/src/composables/useTools.js
import { ref } from 'vue';
import { toolsApi } from '../services/api.js';

const tools = ref([]);
const loading = ref(false);

async function fetchTools() {
  loading.value = true;
  const res = await toolsApi.list();
  tools.value = res.data;
  loading.value = false;
}

async function createTool({ name, description }) {
  const res = await toolsApi.create({ name, description });
  tools.value.push(res.data);
  return res.data;
}

async function updateTool(id, { description }) {
  const res = await toolsApi.update(id, { description });
  const idx = tools.value.findIndex(t => t.id === id);
  if (idx !== -1) tools.value[idx] = res.data;
  return res.data;
}

async function deleteTool(id) {
  await toolsApi.delete(id);
  tools.value = tools.value.filter(t => t.id !== id);
}

export function useTools() {
  return { tools, loading, fetchTools, createTool, updateTool, deleteTool };
}
```

- [ ] **Step 2: Rewrite `frontend/src/views/EnablementView.vue`**

Replace the placeholder with a full tools 货架:

```vue
<!-- frontend/src/views/EnablementView.vue -->
<script setup>
import { ref, onMounted } from 'vue';
import { useTools } from '../composables/useTools.js';

const { tools, loading, fetchTools, createTool, updateTool, deleteTool } = useTools();

onMounted(() => fetchTools());

const showModal = ref(false);
const editingTool = ref(null);
const form = ref({ name: '', description: '' });

function openAdd() {
  editingTool.value = null;
  form.value = { name: '', description: '' };
  showModal.value = true;
}

function openEdit(tool) {
  editingTool.value = tool;
  form.value = { name: tool.name, description: tool.description };
  showModal.value = true;
}

async function handleSubmit() {
  if (editingTool.value) {
    await updateTool(editingTool.value.id, form.value);
  } else {
    await createTool(form.value);
  }
  showModal.value = false;
}

async function handleDelete(id) {
  if (!confirm('确认删除此工具？')) return;
  await deleteTool(id);
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">赋能中心 · 工具货架</h1>
        <p class="page-sub">管理 Avatar 可用工具</p>
      </div>
      <button class="btn btn-primary" @click="openAdd">+ 添加工具</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else class="tools-grid">
      <div v-for="tool in tools" :key="tool.id" class="tool-card">
        <div class="tool-name">{{ tool.name }}</div>
        <div class="tool-desc">{{ tool.description || '暂无描述' }}</div>
        <div class="tool-actions">
          <button class="btn btn-sm" @click="openEdit(tool)">编辑</button>
          <button class="btn btn-sm btn-danger" @click="handleDelete(tool.id)">删除</button>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
        <div class="modal">
          <h3>{{ editingTool ? '编辑工具' : '添加工具' }}</h3>
          <form @submit.prevent="handleSubmit">
            <div class="form-group">
              <label>工具名称</label>
              <input v-model="form.name" :disabled="!!editingTool" required placeholder="如 web_search" />
            </div>
            <div class="form-group">
              <label>描述</label>
              <textarea v-model="form.description" rows="3" placeholder="工具用途说明"></textarea>
            </div>
            <div class="modal-actions">
              <button type="button" class="btn" @click="showModal = false">取消</button>
              <button type="submit" class="btn btn-primary">保存</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.tool-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}
.tool-name {
  font-weight: 600;
  font-family: monospace;
  margin-bottom: 8px;
}
.tool-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}
.tool-actions {
  display: flex;
  gap: 8px;
}
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
}
.modal {
  background: white;
  border-radius: 12px;
  padding: 24px;
  width: 480px;
  max-width: 90vw;
}
.form-group {
  margin-bottom: 16px;
}
.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 4px;
}
.form-group input, .form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 14px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.loading { padding: 40px; text-align: center; color: var(--text-secondary); }
</style>
```

- [ ] **Step 3: Run frontend dev server and verify Enablement page**

```bash
cd frontend && npm run dev &
# Open http://localhost:5173/enablement
```

Verify: 20 tools listed, add/edit/delete work.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/composables/useTools.js frontend/src/views/EnablementView.vue
git commit -m "feat(enablement): tools shelf UI with CRUD"
```

---

## Task 4: Frontend — Onboarding Page Rework (Left Sidebar + Right Tab Wizard)

**Files:**
- Create: `frontend/src/composables/useAvatarConfig.js`
- Create: `frontend/src/components/onboarding/AvatarList.vue`
- Create: `frontend/src/components/onboarding/BasicInfoTab.vue`
- Create: `frontend/src/components/onboarding/SoulTab.vue`
- Create: `frontend/src/components/onboarding/CapabilityTab.vue`
- Create: `frontend/src/components/onboarding/DeployTab.vue`
- Modify: `frontend/src/views/OnboardingView.vue` — split panel layout + tabs
- Modify: `frontend/src/services/api.js` — add avatar config API calls

- [ ] **Step 1: Add avatar config API to `frontend/src/services/api.js`**

Find `export const onboardingApi`. Add to it:

```javascript
  getConfig: (bpId) => api.get(`/onboarding/blueprints/${bpId}/config`),
  saveConfig: (bpId, config) => api.put(`/onboarding/blueprints/${bpId}/config`, config),
```

- [ ] **Step 2: Create `frontend/src/composables/useAvatarConfig.js`**

```javascript
// frontend/src/composables/useAvatarConfig.js
import { ref } from 'vue';
import { onboardingApi } from '../services/api.js';

const currentBlueprint = ref(null);
const config = ref({
  soul_content: '',
  agents_content: '',
  user_content: '',
  tools_enabled: [],
  selected_model: '',
});

async function loadConfig(bpId) {
  const res = await onboardingApi.getConfig(bpId);
  currentBlueprint.value = res.data;
  config.value = {
    soul_content: res.data.soul_content || '',
    agents_content: res.data.agents_content || '',
    user_content: res.data.user_content || '',
    tools_enabled: res.data.tools_enabled || [],
    selected_model: res.data.selected_model || '',
  };
}

async function saveConfig() {
  if (!currentBlueprint.value) return;
  await onboardingApi.saveConfig(currentBlueprint.value.id, config.value);
}

function resetConfig() {
  currentBlueprint.value = null;
  config.value = { soul_content: '', agents_content: '', user_content: '', tools_enabled: [], selected_model: '' };
}

export function useAvatarConfig() {
  return { currentBlueprint, config, loadConfig, saveConfig, resetConfig };
}
```

- [ ] **Step 3: Rewrite `frontend/src/views/OnboardingView.vue`**

Replace current content with split-panel layout:

```vue
<!-- frontend/src/views/OnboardingView.vue -->
<script setup>
import { ref, onMounted } from 'vue';
import { useOnboarding } from '../composables/useOnboarding.js';
import { useAvatarConfig } from '../composables/useAvatarConfig.js';
import { useTools } from '../composables/useTools.js';
import AvatarList from '../components/onboarding/AvatarList.vue';
import BasicInfoTab from '../components/onboarding/BasicInfoTab.vue';
import SoulTab from '../components/onboarding/SoulTab.vue';
import CapabilityTab from '../components/onboarding/CapabilityTab.vue';
import DeployTab from '../components/onboarding/DeployTab.vue';

const { blueprints, fetchBlueprints } = useOnboarding();
const { currentBlueprint, config, loadConfig, saveConfig, resetConfig } = useAvatarConfig();
const { tools: allTools, fetchTools } = useTools();

onMounted(async () => {
  await fetchBlueprints();
  await fetchTools();
});

const activeTab = ref('basic');

const tabs = [
  { id: 'basic', label: '基本信息' },
  { id: 'soul', label: '灵魂' },
  { id: 'capability', label: '能力' },
  { id: 'deploy', label: '部署' },
];

async function handleSelectBlueprint(bp) {
  await loadConfig(bp.id);
  activeTab.value = 'basic';
}

async function handleNewAvatar() {
  resetConfig();
  activeTab.value = 'basic';
}

async function handleSave() {
  await saveConfig();
  alert('配置已保存');
}
</script>

<template>
  <div class="page-layout">
    <!-- Left: Avatar list -->
    <div class="sidebar">
      <div class="sidebar-header">
        <h2 class="sidebar-title">Avatar 列表</h2>
      </div>
      <AvatarList
        :blueprints="blueprints"
        :selectedId="currentBlueprint?.id"
        @select="handleSelectBlueprint"
        @new="handleNewAvatar"
      />
    </div>

    <!-- Right: Config panel -->
    <div class="config-panel">
      <div class="config-header">
        <div class="config-title">
          {{ currentBlueprint ? currentBlueprint.alias || currentBlueprint.id : '新 Avatar' }}
        </div>
        <div class="tab-bar">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            :class="['tab-btn', { active: activeTab === tab.id }]"
            @click="activeTab = tab.id"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>

      <div class="tab-content">
        <BasicInfoTab v-if="activeTab === 'basic'" :config="config" :blueprint="currentBlueprint" />
        <SoulTab v-if="activeTab === 'soul'" :config="config" />
        <CapabilityTab v-if="activeTab === 'capability'" :config="config" :allTools="allTools" />
        <DeployTab v-if="activeTab === 'deploy'" :config="config" :blueprint="currentBlueprint" @save="handleSave" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-layout {
  display: flex;
  min-height: calc(100vh - 56px);
}
.sidebar {
  width: 320px;
  border-right: 1px solid var(--border);
  flex-shrink: 0;
  overflow-y: auto;
}
.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid var(--border);
}
.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}
.config-panel {
  flex: 1;
  overflow-y: auto;
}
.config-header {
  padding: 20px 24px 0;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  background: white;
  z-index: 1;
}
.config-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
}
.tab-bar {
  display: flex;
  gap: 4px;
}
.tab-btn {
  padding: 8px 16px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-secondary);
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.tab-btn.active {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
  font-weight: 500;
}
.tab-content {
  padding: 24px;
}
</style>
```

- [ ] **Step 4: Create `frontend/src/components/onboarding/AvatarList.vue`**

```vue
<!-- frontend/src/components/onboarding/AvatarList.vue -->
<script setup>
defineProps({ blueprints: Array, selectedId: String });
const emit = defineEmits(['select', 'new']);
</script>
<template>
  <div class="avatar-list">
    <div
      v-for="bp in blueprints"
      :key="bp.id"
      :class="['avatar-item', { selected: bp.id === selectedId }]"
      @click="emit('select', bp)"
    >
      <div class="avatar-alias">{{ bp.alias || bp.id }}</div>
      <div class="avatar-meta">{{ bp.role }} · {{ bp.department }}</div>
    </div>
    <div class="avatar-item new-item" @click="emit('new')">
      <div class="avatar-alias">+ 部署新 Avatar</div>
    </div>
  </div>
</template>
<style scoped>
.avatar-list { padding: 12px; }
.avatar-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 8px;
  border: 1px solid transparent;
}
.avatar-item:hover { background: var(--bg-hover); }
.avatar-item.selected { border-color: var(--accent-primary); background: var(--bg-active); }
.avatar-alias { font-weight: 600; font-size: 14px; }
.avatar-meta { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
.new-item { color: var(--accent-primary); font-weight: 500; text-align: center; border: 1px dashed var(--border); }
</style>
```

- [ ] **Step 5: Create `frontend/src/components/onboarding/BasicInfoTab.vue`**

```vue
<!-- frontend/src/components/onboarding/BasicInfoTab.vue -->
<script setup>
defineProps({ config: Object, blueprint: Object });
</script>
<template>
  <div class="tab-form">
    <div class="form-group">
      <label>Blueprint ID</label>
      <input :value="blueprint?.id || ''" disabled />
    </div>
    <div class="form-group">
      <label>Avatar 名称</label>
      <input v-model="config._alias" placeholder="如 小白" />
    </div>
    <div class="form-group">
      <label>角色</label>
      <input v-model="config._role" placeholder="如 行政专员" />
    </div>
    <div class="form-group">
      <label>部门</label>
      <input v-model="config._dept" placeholder="如 综合管理部" />
    </div>
  </div>
</template>
<style scoped>
.tab-form { max-width: 560px; }
.form-group { margin-bottom: 20px; }
.form-group label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px; }
.form-group input { width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; }
.form-group input:disabled { background: var(--bg-disabled); color: var(--text-secondary); }
</style>
```

- [ ] **Step 6: Create `frontend/src/components/onboarding/SoulTab.vue`**

```vue
<!-- frontend/src/components/onboarding/SoulTab.vue -->
<script setup>
defineProps({ config: Object });
</script>
<template>
  <div class="tab-form">
    <div class="form-group">
      <label>性格描述</label>
      <textarea v-model="config.soul_content" rows="12" placeholder="输入 SOUL.md 内容..."></textarea>
    </div>
    <div class="form-group">
      <label>用户说明书</label>
      <textarea v-model="config.user_content" rows="6" placeholder="输入 USER.md 内容..."></textarea>
    </div>
  </div>
</template>
<style scoped>
.tab-form { max-width: 720px; }
.form-group { margin-bottom: 20px; }
.form-group label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px; }
.form-group textarea { width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; font-family: monospace; resize: vertical; }
</style>
```

- [ ] **Step 7: Create `frontend/src/components/onboarding/CapabilityTab.vue`**

```vue
<!-- frontend/src/components/onboarding/CapabilityTab.vue -->
<script setup>
import { ref } from 'vue';
const props = defineProps({ config: Object, allTools: Array });
const search = ref('');
const filteredTools = computed(() =>
  (props.allTools || []).filter(t => t.name.includes(search.value))
);
function toggleTool(name) {
  const list = props.config.tools_enabled;
  const idx = list.indexOf(name);
  if (idx === -1) list.push(name);
  else list.splice(idx, 1);
}
</script>
<template>
  <div class="tab-form">
    <div class="form-group">
      <label>AGENTS.md 工作流程</label>
      <textarea v-model="config.agents_content" rows="8" placeholder="输入 AGENTS.md 内容..."></textarea>
    </div>
    <div class="form-group">
      <label>模型选择</label>
      <input v-model="config.selected_model" placeholder="如 anthropic/claude-opus-4-6" />
    </div>
    <div class="form-group">
      <label>工具集</label>
      <input v-model="search" placeholder="搜索工具..." style="margin-bottom:8px" />
      <div class="tools-checkboxes">
        <label v-for="tool in filteredTools" :key="tool.id" class="tool-check">
          <input
            type="checkbox"
            :checked="config.tools_enabled.includes(tool.name)"
            @change="toggleTool(tool.name)"
          />
          <span class="tool-name">{{ tool.name }}</span>
          <span class="tool-desc">{{ tool.description }}</span>
        </label>
      </div>
    </div>
  </div>
</template>
<style scoped>
.tab-form { max-width: 720px; }
.form-group { margin-bottom: 24px; }
.form-group label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px; }
.form-group textarea, .form-group input { width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; font-family: monospace; resize: vertical; }
.tools-checkboxes { display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow-y: auto; border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
.tool-check { display: flex; align-items: flex-start; gap: 8px; cursor: pointer; }
.tool-check input { margin-top: 2px; }
.tool-name { font-family: monospace; font-weight: 600; min-width: 140px; }
.tool-desc { font-size: 12px; color: var(--text-secondary); }
</style>
```

- [ ] **Step 8: Create `frontend/src/components/onboarding/DeployTab.vue`**

```vue
<!-- frontend/src/components/onboarding/DeployTab.vue -->
<script setup>
defineProps({ config: Object, blueprint: Object });
const emit = defineEmits(['save']);
</script>
<template>
  <div class="deploy-tab">
    <div class="summary-section">
      <h3>基本信息</h3>
      <div class="summary-item">ID: {{ blueprint?.id || '新 Avatar' }}</div>
    </div>
    <div class="summary-section">
      <h3>灵魂预览</h3>
      <pre class="preview-box">{{ config.soul_content || '(未填写)' }}</pre>
    </div>
    <div class="summary-section">
      <h3>能力</h3>
      <div>模型: {{ config.selected_model || '(未选择)' }}</div>
      <div>工具: {{ config.tools_enabled?.join(', ') || '(未选择)' }}</div>
    </div>
    <button class="btn btn-primary deploy-btn" @click="emit('save')">
      保存并部署
    </button>
  </div>
</template>
<style scoped>
.deploy-tab { max-width: 720px; }
.summary-section { margin-bottom: 24px; }
.summary-section h3 { font-size: 14px; font-weight: 600; margin-bottom: 8px; color: var(--text-secondary); }
.summary-item { font-size: 14px; margin-bottom: 4px; }
.preview-box { background: var(--bg-disabled); padding: 12px; border-radius: 6px; font-size: 13px; font-family: monospace; white-space: pre-wrap; max-height: 200px; overflow-y: auto; }
.deploy-btn { width: 100%; padding: 12px; font-size: 16px; }
</style>
```

- [ ] **Step 9: Run frontend and verify Onboarding page**

Open http://localhost:5173/onboarding

Verify: left sidebar shows avatar list, clicking an avatar loads config in right panel with 4 tabs, tabs switch correctly.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/views/OnboardingView.vue \
  frontend/src/components/onboarding/AvatarList.vue \
  frontend/src/components/onboarding/BasicInfoTab.vue \
  frontend/src/components/onboarding/SoulTab.vue \
  frontend/src/components/onboarding/CapabilityTab.vue \
  frontend/src/components/onboarding/DeployTab.vue \
  frontend/src/composables/useAvatarConfig.js \
  frontend/src/services/api.js
git commit -m "feat(onboarding): split-panel wizard with 4 tabs (基本信息/灵魂/能力/部署)"
```

---

## Verification Checklist

After all tasks complete:

- [ ] `curl http://localhost:8006/enablement/tools` returns 20 tools
- [ ] Frontend Enablement page shows tools list at `/enablement`
- [ ] Add/edit/delete a tool via Enablement UI
- [ ] Onboarding page at `/onboarding` shows left sidebar + 4 tabs
- [ ] Clicking an avatar loads config; switch tabs shows correct form
- [ ] Deploy tab "保存并部署" calls API successfully
- [ ] `cat ~/.openclaw/agents/av-admin-001/agent/SOUL.md` reflects saved content
