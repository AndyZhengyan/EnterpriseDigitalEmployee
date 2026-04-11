<!-- frontend/src/components/onboarding/AvatarCard.vue -->
<!-- e-Agent-OS OpCenter — 单个 Blueprint 卡片，含版本列表 -->
<script setup>
import { ref } from 'vue';
import { opsApi } from '../../services/api.js';
import { useOnboarding } from '../../composables/useOnboarding.js';

const props = defineProps({
  blueprint: { type: Object, required: true },
});

const emit = defineEmits(['deploy-version']);

const { adjustTraffic, deprecateVersion } = useOnboarding();

const STATUS_LABEL = {
  published: '正式上岗',
  testing: '试用期',
  staging: '灰度中',
  draft: '草稿',
  deprecated: '退役',
};

const STATUS_COLOR = {
  published: 'var(--success)',
  testing: 'var(--warning)',
  staging: 'var(--accent-primary)',
  draft: 'var(--text-disabled)',
  deprecated: 'var(--text-disabled)',
};

function capacityColor(pct) {
  if (pct >= 80) return 'var(--danger)';
  if (pct >= 60) return 'var(--warning)';
  return 'var(--success)';
}

function totalReplicas(bp) {
  return bp.versions.reduce((s, v) => s + v.replicas, 0);
}
function loadPct(bp) {
  const total = totalReplicas(bp);
  return bp.capacity.max > 0 ? Math.round((total / bp.capacity.max) * 100) : 0;
}

// Execute task state
const showTaskInput = ref(false);
const taskMessage = ref('');
const taskRunning = ref(false);
const taskResult = ref(null);
const taskError = ref(null);

// Traffic adjustment state
const adjustingIdx = ref(null);
const _adjustingTraffic = ref(0);

const deprecatingIdx = ref(null);

function startAdjustTraffic(v, idx) {
  adjustingIdx.value = idx;
  _adjustingTraffic.value = v.traffic;
}

async function confirmTrafficAdjustment(v, idx) {
  if (props.blueprint.id.startsWith('av-')) {
    await adjustTraffic(props.blueprint.id, idx, _adjustingTraffic.value).catch(() => {});
  }
  v.traffic = _adjustingTraffic.value;
  adjustingIdx.value = null;
}

function cancelTrafficAdjustment() {
  adjustingIdx.value = null;
}

function startDeprecate(idx) {
  deprecatingIdx.value = idx;
}

async function confirmDeprecate(v, idx) {
  if (props.blueprint.id.startsWith('av-')) {
    await deprecateVersion(props.blueprint.id, idx);
  }
  v.traffic = 0;
  v.status = 'deprecated';
  deprecatingIdx.value = null;
}

// Deploy new version state
const showDeployForm = ref(false);
const newVersion = ref({ version: '', replicas: 1 });

function submitNewVersion() {
  if (!newVersion.value.version.trim()) return;
  props.blueprint.versions.push({
    version: newVersion.value.version.trim(),
    status: 'draft',
    traffic: 0,
    replicas: newVersion.value.replicas,
    config: { soul: {}, skills: [], tools: [], model: '' },
    scaling: { minReplicas: 1, maxReplicas: 5, targetLoad: 70 },
  });
  newVersion.value = { version: '', replicas: 1 };
  showDeployForm.value = false;
}

async function executeTask() {
  if (!taskMessage.value.trim()) return;
  taskRunning.value = true;
  taskError.value = null;
  taskResult.value = null;

  try {
    const res = await opsApi.execute({
      message: taskMessage.value,
      blueprint_id: props.blueprint.id,
      alias: props.blueprint.alias,
      role: props.blueprint.role,
      dept: props.blueprint.department,
    });
    taskResult.value = res.data;
  } catch (e) {
    // Show error message for both API errors and network failures
    const msg = e?.response?.data?.detail || e?.message || '网络请求失败，请检查服务状态';
    taskError.value = msg;
  } finally {
    taskRunning.value = false;
  }
}

function closeTaskPanel() {
  showTaskInput.value = false;
  taskMessage.value = '';
  taskResult.value = null;
  taskError.value = null;
}
</script>

<template>
  <div class="avatar-card">
    <!-- 卡片头部 -->
    <div class="card-header">
      <div class="card-title">
        <span class="role-name">{{ blueprint.role }}</span>
        <span class="role-alias">{{ blueprint.alias }}</span>
      </div>
      <div class="card-dept">{{ blueprint.department }}</div>
    </div>

    <!-- 版本列表 -->
    <div class="version-list">
      <div
        v-for="v in blueprint.versions"
        :key="v.version"
        class="version-row"
        :class="{ 'version-row--offline': v.traffic === 0 }"
      >
        <span class="v-tag">{{ v.version }}</span>
        <span
          class="v-status-dot"
          :style="{ background: STATUS_COLOR[v.status] }"
        ></span>
        <span class="v-status-label">{{ STATUS_LABEL[v.status] }}</span>
        <span class="v-replicas">{{ v.replicas }}分身</span>
        <span class="v-traffic" v-if="v.traffic > 0">{{ v.traffic }}%</span>
        <span class="v-traffic v-traffic--zero" v-else>—</span>

        <!-- 调流 -->
        <template v-if="adjustingIdx !== $index">
          <button class="v-btn" @click="startAdjustTraffic(v, $index)">调流</button>
        </template>
        <template v-else>
          <input
            type="range" min="0" max="100" step="5"
            v-model.number="_adjustingTraffic"
            class="v-traffic-slider"
          />
          <span class="v-traffic-val">{{ _adjustingTraffic }}%</span>
          <button class="v-btn v-btn--ok" @click="confirmTrafficAdjustment(v, $index)">✓</button>
          <button class="v-btn" @click="cancelTrafficAdjustment">✕</button>
        </template>

        <!-- 下线 -->
        <template v-if="deprecatingIdx !== $index && v.status !== 'deprecated'">
          <button class="v-btn v-btn--danger" @click="startDeprecate($index)">下线</button>
        </template>
        <template v-else-if="deprecatingIdx === $index">
          <button class="v-btn v-btn--danger" @click="confirmDeprecate(v, $index)">确认</button>
          <button class="v-btn" @click="deprecatingIdx = null">取消</button>
        </template>
      </div>
    </div>

    <!-- 部署新版本表单 -->
    <div v-if="showDeployForm" class="deploy-form">
      <div class="deploy-form-row">
        <label class="deploy-label">版本号</label>
        <input
          v-model="newVersion.version"
          class="deploy-input"
          placeholder="如 v1.2.0"
          @keydown.enter="submitNewVersion"
        />
      </div>
      <div class="deploy-form-row">
        <label class="deploy-label">初始分身</label>
        <div class="deploy-btn-group">
          <button
            v-for="n in [1, 2, 3]"
            :key="n"
            class="deploy-btn"
            :class="{ active: newVersion.replicas === n }"
            @click="newVersion.replicas = n"
          >{{ n }}</button>
        </div>
      </div>
      <div class="deploy-form-actions">
        <button class="btn-cancel" @click="showDeployForm = false">取消</button>
        <button
          class="btn-confirm"
          @click="submitNewVersion"
          :disabled="!newVersion.version.trim()"
        >确认部署</button>
      </div>
    </div>

    <!-- 底部：容量条 + 按钮行 -->
    <div class="card-footer">
      <div class="capacity-row">
        <span class="capacity-label">容量</span>
        <span class="capacity-numbers">
          {{ totalReplicas(blueprint) }}/{{ blueprint.capacity.max }}
        </span>
        <div class="capacity-track">
          <div
            class="capacity-fill"
            :style="{
              width: `${loadPct(blueprint)}%,
              background: ${capacityColor(loadPct(blueprint))}`
            }"
          ></div>
        </div>
        <span
          v-if="loadPct(blueprint) >= 80"
          class="capacity-warn"
          title="接近容量上限"
        >⚠️</span>
        <span class="capacity-pct">{{ loadPct(blueprint) }}%</span>
      </div>
      <div class="btn-row">
        <button class="btn-action" @click="showTaskInput = true">
          执行任务
        </button>
        <button class="btn-deploy" @click="showDeployForm = !showDeployForm">
          {{ showDeployForm ? '收起' : '部署新版本' }}
        </button>
      </div>
    </div>

    <!-- 任务执行面板 -->
    <div v-if="showTaskInput" class="task-panel" @click.self="closeTaskPanel">
      <div class="panel-content">
        <div class="panel-header">
          <h3 class="panel-title">{{ blueprint.alias }} · 执行任务</h3>
          <button class="panel-close" @click="closeTaskPanel">✕</button>
        </div>

        <!-- 结果展示 -->
        <div v-if="taskResult" class="task-result">
          <div class="result-status" :class="taskResult.status">
            <span class="dot" :style="{ background: taskResult.status === 'ok' ? 'var(--success)' : 'var(--danger)' }"></span>
            {{ taskResult.status === 'ok' ? '执行完成' : '执行失败' }}
          </div>
          <p class="result-summary">{{ taskResult.summary }}</p>
          <div class="result-meta">
            <span>{{ taskResult.tokenTotal?.toLocaleString() }} tokens</span>
            <span>{{ (taskResult.durationMs / 1000).toFixed(1) }}s</span>
          </div>
        </div>

        <!-- 错误提示 -->
        <div v-if="taskError" class="task-error">
          {{ taskError }}
        </div>

        <!-- 输入框 -->
        <textarea
          v-model="taskMessage"
          class="task-input"
          placeholder="输入任务指令…"
          rows="3"
          :disabled="taskRunning"
          @keydown.ctrl.enter="executeTask"
        ></textarea>

        <div class="panel-actions">
          <button class="btn cancel" @click="closeTaskPanel" :disabled="taskRunning">取消</button>
          <button
            class="btn primary"
            @click="executeTask"
            :disabled="!taskMessage.trim() || taskRunning"
          >
            <span v-if="taskRunning" class="spinner-inline"></span>
            {{ taskRunning ? '执行中…' : '发送任务 (Ctrl+Enter)' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.avatar-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-header {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.role-name {
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}

.role-alias {
  font-size: 12px;
  color: var(--text-secondary);
}

.card-dept {
  font-size: 11px;
  color: var(--text-disabled);
  margin-left: auto;
}

/* 版本列表 */
.version-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 0;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}

.version-row {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  overflow: hidden;
}

.version-row--offline {
  opacity: 0.5;
}

.v-tag {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
  min-width: 60px;
}

.v-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.v-status-label {
  font-size: 11px;
  color: var(--text-secondary);
  min-width: 44px;
}

.v-replicas {
  font-size: 11px;
  color: var(--text-secondary);
  min-width: 36px;
}

.v-traffic {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-primary);
  min-width: 28px;
  text-align: right;
}
.v-traffic--zero {
  color: var(--text-disabled);
}

.v-btn {
  font-size: 11px;
  color: var(--text-secondary);
  background: none;
  border: none;
  padding: 2px 4px;
  cursor: pointer;
  border-radius: 3px;
  transition: color 120ms, background 120ms;
  margin-left: auto;
}
.v-btn:hover {
  color: var(--text-primary);
  background: var(--bg-elevated);
}
.v-traffic-slider {
  flex: 1;
  height: 3px;
  accent-color: var(--accent-primary);
  cursor: pointer;
}

.v-traffic-val {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-primary);
  min-width: 28px;
  text-align: right;
}

.v-btn--ok {
  color: var(--success);
}
.v-btn--ok:hover {
  color: var(--success);
  background: rgba(73, 137, 110, 0.1);
}

.v-btn--danger:hover {
  color: var(--danger);
  background: rgba(184, 74, 60, 0.06);
}

/* 容量条 */
.card-footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.capacity-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.capacity-label {
  font-size: 11px;
  color: var(--text-disabled);
  min-width: 24px;
}

.capacity-numbers {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
  min-width: 36px;
}

.capacity-track {
  flex: 1;
  height: 3px;
  background: var(--bg-elevated);
  border-radius: 2px;
  overflow: hidden;
}

.capacity-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 400ms ease;
}

.capacity-warn {
  font-size: 11px;
}

.capacity-pct {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
  min-width: 28px;
  text-align: right;
}

/* 按钮行 */
.btn-row {
  display: flex;
  gap: 8px;
}

.btn-action {
  flex: 1;
  padding: 7px 0;
  font-size: 12px;
  font-weight: 500;
  color: var(--bg-card);
  background: var(--text-primary);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: opacity 120ms;
  font-family: var(--font-sans);
}
.btn-action:hover {
  opacity: 0.85;
}

.btn-deploy {
  flex: 1;
  padding: 7px 0;
  font-size: 12px;
  font-weight: 500;
  color: var(--accent-primary);
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 120ms, border-color 120ms;
  font-family: var(--font-sans);
}
.btn-deploy:hover {
  background: var(--bg-elevated);
  border-color: var(--accent-primary);
}

/* 任务面板 overlay */
.task-panel {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.panel-content {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  padding: 20px;
  width: 420px;
  max-width: 90vw;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  font-family: var(--font-serif);
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0;
}

.panel-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 3px;
}
.panel-close:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

/* 任务结果 */
.task-result {
  padding: 12px;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.result-status {
  font-size: 13px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}

.result-status .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.result-summary {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}

.result-meta {
  display: flex;
  gap: 16px;
  font-size: 11px;
  color: var(--text-disabled);
  font-family: var(--font-mono);
}

/* 错误提示 */
.task-error {
  padding: 8px 12px;
  background: rgba(184, 74, 60, 0.08);
  border: 1px solid rgba(184, 74, 60, 0.2);
  border-radius: var(--radius-sm);
  color: var(--danger);
  font-size: 12px;
}

/* 任务输入框 */
.task-input {
  width: 100%;
  padding: 10px 12px;
  font-size: 13px;
  font-family: var(--font-sans);
  color: var(--text-primary);
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  resize: none;
  outline: none;
  transition: border-color 120ms;
  box-sizing: border-box;
}
.task-input:focus {
  border-color: var(--accent-primary);
}
.task-input:disabled {
  opacity: 0.6;
}

/* 面板底部按钮 */
.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.panel-actions .btn {
  padding: 7px 16px;
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-family: var(--font-sans);
  transition: background 120ms, opacity 120ms;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  background: transparent;
}
.panel-actions .btn:hover:not(:disabled) {
  background: var(--bg-elevated);
  color: var(--text-primary);
}
.panel-actions .btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.panel-actions .btn.primary {
  color: var(--bg-card);
  background: var(--text-primary);
  border-color: transparent;
}
.panel-actions .btn.primary:hover:not(:disabled) {
  opacity: 0.85;
}

/* Deploy new version form */
.deploy-form {
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.deploy-form-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.deploy-label {
  font-size: 11px;
  color: var(--text-disabled);
  min-width: 48px;
}

.deploy-input {
  flex: 1;
  padding: 5px 8px;
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--text-primary);
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  outline: none;
}
.deploy-input:focus {
  border-color: var(--accent-primary);
}

.deploy-btn-group {
  display: flex;
  gap: 4px;
}

.deploy-btn {
  padding: 4px 10px;
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 120ms;
}
.deploy-btn:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}
.deploy-btn.active {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: #fff;
}

.deploy-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 4px;
}

.btn-cancel {
  padding: 5px 12px;
  font-size: 12px;
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-family: var(--font-sans);
}
.btn-cancel:hover {
  color: var(--text-primary);
  background: var(--bg-elevated);
}

.btn-confirm {
  padding: 5px 14px;
  font-size: 12px;
  font-weight: 500;
  color: var(--bg-card);
  background: var(--accent-primary);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-family: var(--font-sans);
  transition: opacity 120ms;
}
.btn-confirm:hover:not(:disabled) {
  opacity: 0.85;
}
.btn-confirm:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Loading spinner inline */
.spinner-inline {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-right: 6px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
